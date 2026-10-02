"use client";

import { use, useEffect, useState } from "react";
import { api, downloadEvidence, formatDateTime, hasPermission, newIdempotencyKey, type Me } from "@/lib/api";
import { useApiResource, useEntityOptions, useMe, type EntityOption, type EntityOptionsStatus } from "@/lib/hooks";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button, LinkButton } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { Tabs } from "@/components/ui/Tabs";
import { RecordDetailShell, useCommand } from "@/components/shared/RecordDetailShell";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { RepeatableRows, buildRepeatArray, type RepeatRow, type RepeatSubField } from "@/components/shared/RepeatableFields";

interface GxpBatch {
  batch_id: string;
  site_id: string;
  batch_number: string;
  product_version_id: string;
  product_name: string | null;
  product_code: string | null;
  recipe_version_id: string;
  recipe_code: string | null;
  recipe_version_no: number | null;
  recipe_vault_object_id: string | null;
  execution_snapshot_id: string | null;
  target_qty: string;
  target_uom: string;
  state: string;
  version: number;
  production_order_ref: string | null;
  issued_at: string | null;
  started_at: string | null;
}

// §19 #33's own finding: the Batch ID was plain, selectable UUID text with no copy affordance at all --
// a tester had to click-drag/select it by hand. `document.execCommand` fallback isn't needed here: every
// deployment target for this app is a modern browser with the async Clipboard API.
function CopyIdButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      type="button"
      size="sm"
      variant="secondary"
      onClick={() => {
        navigator.clipboard
          .writeText(value)
          .then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          })
          .catch(() => {
            /* clipboard permission denied - the id is still selectable text, nothing else to fall back to */
          });
      }}
    >
      {copied ? "Copied" : "Copy"}
    </Button>
  );
}

function isNumericParameter(dataType: string): boolean {
  return ["numeric", "decimal", "number", "float", "integer"].includes(dataType.toLowerCase());
}
function isBooleanParameter(dataType: string): boolean {
  return ["bool", "boolean"].includes(dataType.toLowerCase());
}

// SG-048 #018, visibility-only — true only when the recipe step declared an expected hold duration AND
// the hold has been open longer than it. Purely a display flag: nothing is blocked or auto-escalated.
function isHoldOverdue(heldAt: string | null, expectedMinutes: number | null | undefined): boolean {
  if (!heldAt || !expectedMinutes) return false;
  const elapsedMinutes = (Date.now() - new Date(heldAt).getTime()) / 60000;
  return elapsedMinutes > expectedMinutes;
}

// Known-limitations fix (docs/testing/demo-gujarati/08 §8.8): the FROZEN requirements
// commands.py::_enforce_step_equipment actually checks at step-start (distinct from any live-recipe
// display-only equipment info elsewhere in this view).
interface StepEquipmentRequirement {
  equipment_class: string;
  equipment_class_id: string | null;
  exact_equipment_optional: boolean;
  require_current_calibration: boolean;
  require_current_qualification: boolean;
  require_current_cleaning: boolean;
}

interface BatchStep {
  step_id: string;
  batch_id: string;
  recipe_step_code: string;
  required_role_code: string | null;
  equipment_requirements: StepEquipmentRequirement[];
  state: string;
  version: number;
  assigned_subject_id: string | null;
  assigned_full_name: string | null;
  assigned_username: string | null;
  started_at: string | null;
  completed_at: string | null;
}

// GET /batches/v1/{id}/execution-view's "blockers" — service.py::get_execution_view() emits one of
// these per step still stuck on a predecessor. A designed list, not a JSON dump (matches the DDCP
// readiness panel's own {code,message}-list convention — components/ddcp/ReadinessPanel.tsx).
interface ExecutionBlocker {
  step_id: string;
  recipe_step_code: string;
  reason: string;
}

// BAT-FR-009 form definition (Document 10's gxp_recipe_parameter, read through the execution view).
interface StepParameter {
  parameter_code: string;
  data_type: string;
  uom: string | null;
  target_value: string | null;
  min_value: string | null;
  max_value: string | null;
  precision_digits: number | null;
  required: boolean;
}

// gxp_step_result (SG-047 partial resolution) — a recorded value against one of the parameters above.
interface StepResultRow {
  result_id: string;
  parameter_code: string;
  data_type: string;
  value_numeric: string | null;
  value_text: string | null;
  value_bool: boolean | null;
  uom: string | null;
  received_at: string | null;
  signature_id: string | null;
  // Computed server-side (commands.py::_step_result_quality_status), informational only — never blocks
  // save/complete. Was already in the API response but not read/shown anywhere in this UI.
  quality_status: "in_range" | "out_of_range" | "not_evaluated" | null;
}

// Recipe-declared material/equipment requirement (Document 10/21, SG-045) — display-only in this view;
// lot consumption/reservation and specific-asset linking at execution time are not built (SG-048 #012/
// #013 stays open).
interface StepMaterialRequirement {
  material_spec_version_id: string;
  material_spec_business_id: string | null;
  material_name: string | null;
  target_value: string | null;
  min_value: string | null;
  max_value: string | null;
  uom: string | null;
  consume_mode: string | null;
  substitution_allowed: boolean;
  genealogy_required: boolean;
}
interface StepEquipmentRequirement {
  equipment_class: string;
  exact_equipment_optional: boolean;
  require_current_calibration: boolean;
  require_current_qualification: boolean;
  require_current_cleaning: boolean;
}

// Recipe-declared evidence requirement (Document 10) — upload itself isn't built yet (SG-047), but the
// requirement is real recipe content and worth showing in step detail.
interface StepEvidenceRequirement {
  evidence_type: string;
  required_count: number;
  allowed_mime_types: string | null;
  retention_class: string | null;
}

// gxp_step_evidence_link (SG-047 half) — a link already recorded against a step. `requirement_code`, when
// set, matches a StepEvidenceRequirement's `evidence_type` one-for-one (same symmetry commands.py's
// complete_step() evidence-count gate uses) — was already in the API response but never read/shown here.
interface StepEvidenceLinkRow {
  id: string;
  evidence_id: string;
  evidence_version: number | null;
  evidence_sha256: string | null;
  media_type: string | null;
  requirement_code: string | null;
  linked_by: string;
  created_at: string | null;
}

// "Step detail" — BAT-FR-005's "immutable parent instruction" + Document 11 §9's execution-UI field list
// (instruction, section, dependencies), read from the live recipe graph (2026-09-09, client-requested).
interface StepDetail {
  step_type: string | null;
  instruction_text: string | null;
  is_critical: boolean | null;
  sequence_hint: number | null;
  section_code: string | null;
  section_name: string | null;
  // SG-048 #018, visibility-only slice — declared by the recipe step (optional); null means no overdue
  // flag is ever computed for a hold on this step.
  expected_hold_duration_minutes: number | null;
  predecessor_codes: string[];
  successor_codes: string[];
  evidence_requirements: StepEvidenceRequirement[];
  material_requirements: StepMaterialRequirement[];
  equipment_requirements: StepEquipmentRequirement[];
}

// Active step-level hold (BAT-FR-020 step scope, SG-047 further partial resolution).
interface ActiveHold {
  reason: string;
  held_at: string | null;
}

// Full StepHold shape (active or released) -- read-path completeness fix: released_at/released_by/
// release_reason were written by resume_step but never surfaced before holds_by_step_id existed.
interface StepHold {
  id: string;
  reason: string;
  held_at: string | null;
  held_by: string;
  held_by_username: string | null;
  hold_signature_id: string | null;
  released_at: string | null;
  released_by: string | null;
  released_by_username: string | null;
  release_reason: string | null;
  release_signature_id: string | null;
}

// gxp_step_comment (BAT-FR-034) -- fetched by execution-view all along, never rendered until now.
interface StepComment {
  comment_id: string;
  comment_text: string;
  created_by: string;
  created_at: string | null;
}

// gxp_step_handover (BAT-FR-025) -- fetched by execution-view all along, never rendered until now.
interface StepHandover {
  handover_id: string;
  from_subject_id: string | null;
  to_subject_id: string;
  reason: string | null;
  created_at: string | null;
}

// gxp_step_result_correction (SG-048 #023) — a request to correct one result on an already-Complete
// step, needing an independent (not the requester) approver's signature before it takes effect.
interface StepResultCorrectionRow {
  correction_id: string;
  original_result_id: string;
  parameter_code: string | null;
  reason_text: string;
  corrected_value_numeric: string | null;
  corrected_value_text: string | null;
  corrected_value_bool: boolean | null;
  status: "requested" | "completed";
  requested_by_user_id: string;
  requested_by_username: string | null;
  approved_by_user_id: string | null;
  approved_by_username: string | null;
  resulting_result_id: string | null;
  created_at: string | null;
  completed_at: string | null;
}

interface ExecutionView {
  batch: GxpBatch;
  steps: BatchStep[];
  blockers: ExecutionBlocker[];
  parameters_by_step_id: Record<string, StepParameter[]>;
  results_by_step_id: Record<string, StepResultRow[]>;
  corrections_by_step_id: Record<string, StepResultCorrectionRow[]>;
  step_detail_by_step_id: Record<string, StepDetail>;
  active_hold_by_step_id: Record<string, ActiveHold>;
  // Read-path completeness fix: full hold history (active and released), not just the current one.
  holds_by_step_id: Record<string, StepHold[]>;
  evidence_links_by_step_id: Record<string, StepEvidenceLinkRow[]>;
  comments_by_step_id: Record<string, StepComment[]>;
  handovers_by_step_id: Record<string, StepHandover[]>;
}

type Action = "issue" | "start" | "hold" | "resume" | "abort";

const ACTION_LABEL: Record<Action, string> = {
  issue: "Issue batch",
  start: "Start batch",
  hold: "Hold",
  resume: "Resume",
  abort: "Abort",
};

// Matches app/modules/batch_execution/models.py::ALLOWED_TRANSITIONS exactly.
const ALLOWED_FROM: Record<string, Action[]> = {
  planned: ["issue"],
  issued: ["start", "abort"],
  in_execution: ["hold", "abort"],
  on_hold: ["resume", "abort"],
  production_complete: ["hold"],
};

// Batch detail — its own page (not a modal) so a batch can be linked to, bookmarked, and reloaded
// directly, matching every other single-record page in this app (deviations/[id], qc/samples/[id], …).
export default function BatchExecutionDetailPage({ params }: { params: Promise<{ batchId: string }> }) {
  const { batchId } = use(params);
  const { me } = useMe();
  const view = useApiResource<ExecutionView>(`/batches/v1/${batchId}/execution-view`);
  const record = useApiResource<BatchRecordView>(`/batches/v1/${batchId}/record`);
  const [action, setAction] = useState<Action | null>(null);
  const [startingStep, setStartingStep] = useState<BatchStep | null>(null);
  const [resultsStep, setResultsStep] = useState<BatchStep | null>(null);
  const [completingStep, setCompletingStep] = useState<BatchStep | null>(null);
  const [detailStep, setDetailStep] = useState<BatchStep | null>(null);
  const [holdingStep, setHoldingStep] = useState<BatchStep | null>(null);
  const [resumingStep, setResumingStep] = useState<BatchStep | null>(null);
  const [linkingEvidenceStep, setLinkingEvidenceStep] = useState<BatchStep | null>(null);
  const [handingOverStep, setHandingOverStep] = useState<BatchStep | null>(null);
  const [completingProduction, setCompletingProduction] = useState(false);
  const [pdfSignOpen, setPdfSignOpen] = useState(false);
  const [pdfEvidenceId, setPdfEvidenceId] = useState<string | null>(null);

  function reloadAll() {
    view.reload();
    record.reload();
  }

  const v = view.data;
  if (!v) {
    return (
      <RecordDetailShell recordNumber="Batch" backHref="/batch-execution" backLabel="Batch execution" facts={null} loading={!view.error} error={view.error}>
        {null}
      </RecordDetailShell>
    );
  }

  const b = v.batch;
  const allowed = ALLOWED_FROM[b.state] ?? [];
  const canExecute = hasPermission(me, "batch_execution.execute");
  const canIssue = hasPermission(me, "batch_execution.issue");
  const hasBlockers = v.blockers.length > 0;

  function offered(a: Action): boolean {
    if (!allowed.includes(a)) return false;
    return a === "issue" ? canIssue : canExecute;
  }

  return (
    <RecordDetailShell
      recordNumber={`Batch ${b.batch_number}`}
      state={b.state}
      backHref="/batch-execution"
      backLabel="Batch execution"
      loading={false}
      error={null}
      actions={
        <>
          <Button size="sm" variant="secondary" onClick={() => setPdfSignOpen(true)}>
            <Icon name="file-text" /> Generate PDF
          </Button>
          {(Object.keys(ACTION_LABEL) as Action[]).filter(offered).map((a) => (
            <Button
              key={a}
              size="sm"
              variant={a === "abort" ? "danger" : a === "hold" ? "secondary" : "primary"}
              onClick={() => setAction(a)}
            >
              {ACTION_LABEL[a]}
            </Button>
          ))}
          {canExecute && b.state === "in_execution" && v.steps.length > 0 && v.steps.every((s) => s.state === "complete") && (
            <Button size="sm" variant="success" onClick={() => setCompletingProduction(true)}>
              <Icon name="check-circle" /> Production complete
            </Button>
          )}
        </>
      }
      facts={
        <>
          <Fact label="Target">
            <span className="tabular">
              {b.target_qty} {b.target_uom}
            </span>
          </Fact>
          <Fact label="Steps">
            {v.steps.filter((s) => s.state === "complete" || s.state === "completed").length} of {v.steps.length}{" "}
            complete
          </Fact>
          <Fact label="Issued">{b.issued_at ? formatDateTime(b.issued_at) : "—"}</Fact>
          <Fact label="Started">{b.started_at ? formatDateTime(b.started_at) : "—"}</Fact>
          <Fact label="Production order">{b.production_order_ref ?? "—"}</Fact>
          <Fact label="Record version">{b.version}</Fact>
          <IdFact
            label="Batch ID"
            value={b.batch_id}
            action={
              <>
                <CopyIdButton value={b.batch_id} />
                {/* §19 #33's own finding: no navigation link, query param or copy-button bridged this page
                 * to /ddcp -- a tester had to manually select/copy this UUID, go to /ddcp from the sidebar,
                 * pick the right Product family by hand, then paste it in. /ddcp now reads ?batch_id= to
                 * pre-fill its Batch field and auto-detects family for PFS/Inhalation (not Autoinjector/
                 * Coated device -- SG-175's own residual gap, not guessed here either). */}
                <LinkButton href={`/ddcp?batch_id=${b.batch_id}`} variant="secondary" size="sm">
                  Open in DDCP <Icon name="arrow-right" />
                </LinkButton>
                <LinkButton href={`/batch-workspace/${b.batch_id}`} variant="secondary" size="sm">
                  Batch Workspace <Icon name="arrow-right" />
                </LinkButton>
              </>
            }
          />
          <Fact label="Product">{b.product_name ? `${b.product_name} (${b.product_code})` : b.product_version_id}</Fact>
          <Fact label="Recipe">{b.recipe_code ? `${b.recipe_code} v${b.recipe_version_no}` : b.recipe_version_id}</Fact>
          <IdFact label="Recipe vault object" value={b.recipe_vault_object_id} />
          <IdFact label="Execution snapshot" value={b.execution_snapshot_id} />
        </>
      }
    >
      {b.state === "on_hold" && (
        <Banner tone="critical" title="Batch is on hold" icon="lock">
          Execution is stopped. No step can be started until the batch is resumed.
        </Banner>
      )}
      {hasBlockers && (
        <Banner tone="warn" title="Execution blockers">
          <div className="mt-1">
            {v.blockers.map((blocker) => (
              <div key={blocker.step_id} className="flex gap-2" style={{ padding: "3px 0" }}>
                <Icon name="alert-triangle" />
                <span>
                  <span className="font-semibold tabular">{blocker.recipe_step_code}</span> -{" "}
                  {blocker.reason}
                </span>
              </div>
            ))}
          </div>
        </Banner>
      )}

      {pdfEvidenceId && (
        <div className="mb-3">
          <Banner tone="ok" title="Batch record PDF generated">
            <Button size="sm" variant="secondary" onClick={() => downloadEvidence(pdfEvidenceId)}>
              <Icon name="download" /> Download PDF
            </Button>
          </Banner>
        </div>
      )}

      <Tabs
        tabs={[
          {
            id: "steps",
            label: "Steps",
            badge: v.steps.length || undefined,
            content:
              v.steps.length === 0 ? (
                <EmptyState icon="clipboard">No step instances yet - they are created when the batch is issued.</EmptyState>
              ) : (
                <Table>
                  <thead>
                    <tr>
                      <th>Step</th>
                      <th>Required role</th>
                      <th>State</th>
                      <th>Assigned</th>
                      <th>Started</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {v.steps.map((s) => (
                      <tr key={s.step_id}>
                        <td className="font-semibold tabular">{s.recipe_step_code}</td>
                        <td className="fs-2">{s.required_role_code ?? <span className="text-muted">any</span>}</td>
                        <td>
                          <WorkflowStatePill state={s.state} />
                          {s.state === "on_hold" && v.active_hold_by_step_id[s.step_id] && (
                            <p className="hint" style={{ marginTop: 2 }}>
                              {v.active_hold_by_step_id[s.step_id].reason}
                              {isHoldOverdue(v.active_hold_by_step_id[s.step_id].held_at, v.step_detail_by_step_id[s.step_id]?.expected_hold_duration_minutes) && (
                                <span className="error-text" style={{ marginLeft: 6 }} title="Open longer than this step's declared expected hold duration — informational only, nothing is blocked or escalated automatically">
                                  <Icon name="alert-triangle" /> overdue
                                </span>
                              )}
                            </p>
                          )}
                        </td>
                        <td className="fs-2" style={{ wordBreak: "break-word" }}>
                          {s.assigned_full_name ? `${s.assigned_full_name} (${s.assigned_username})` : s.assigned_subject_id ?? "—"}
                        </td>
                        <td className="tabular fs-2">{s.started_at ? formatDateTime(s.started_at) : "—"}</td>
                        <td style={{ textAlign: "right" }}>
                          <div className="flex justify-end gap-2 flex-wrap">
                            <Button size="sm" variant="secondary" onClick={() => setDetailStep(s)}>
                              <Icon name="info" /> Detail
                            </Button>
                            {canExecute && b.state === "in_execution" && s.state === "ready" && (
                              <Button size="sm" variant="secondary" onClick={() => setStartingStep(s)}>
                                <Icon name="play" /> Start
                              </Button>
                            )}
                            {canExecute && b.state === "in_execution" && s.state === "in_progress" && (
                              <>
                                {(v.parameters_by_step_id[s.step_id]?.length ?? 0) > 0 && (
                                  <Button size="sm" variant="secondary" onClick={() => setResultsStep(s)}>
                                    <Icon name="clipboard" /> Record results
                                  </Button>
                                )}
                                <Button size="sm" variant="secondary" onClick={() => setLinkingEvidenceStep(s)}>
                                  <Icon name="file-plus-2" /> Link evidence
                                </Button>
                                <Button size="sm" variant="secondary" onClick={() => setHandingOverStep(s)}>
                                  <Icon name="arrow-right" /> Hand over
                                </Button>
                                <Button size="sm" variant="secondary" onClick={() => setHoldingStep(s)}>
                                  <Icon name="lock" /> Hold
                                </Button>
                                <Button size="sm" variant="primary" onClick={() => setCompletingStep(s)}>
                                  <Icon name="check-circle" /> Complete
                                </Button>
                              </>
                            )}
                            {canExecute && b.state === "in_execution" && s.state === "on_hold" && (
                              <Button size="sm" variant="primary" onClick={() => setResumingStep(s)}>
                                <Icon name="play" /> Resume
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              ),
          },
          {
            id: "materials-equipment",
            label: "Materials & equipment",
            content: <MaterialsEquipmentTab execView={v} record={record.data} />,
          },
          {
            id: "evidence",
            label: "Evidence",
            content: <EvidenceTab execView={v} />,
          },
          {
            id: "deviations",
            label: "Deviations",
            badge: record.data?.deviations.length || undefined,
            content: <DeviationsTab execView={v} record={record.data} />,
          },
          {
            id: "corrections",
            label: "Corrections",
            badge: Object.values(v.corrections_by_step_id).reduce((n, c) => n + c.length, 0) || undefined,
            content: (
              <CorrectionsTab
                execView={v}
                batch={b}
                me={me}
                onReload={reloadAll}
              />
            ),
          },
          {
            id: "history",
            label: "History",
            content: <HistoryTab execView={v} record={record.data} />,
          },
          {
            id: "qc",
            label: "QC results",
            badge: record.data?.qc_results.length || undefined,
            content: <QcResultsTab record={record.data} />,
          },
        ]}
      />

      {pdfSignOpen && (
        <SignatureCeremony
          open
          onClose={() => setPdfSignOpen(false)}
          onDone={() => setPdfSignOpen(false)}
          challengePath={`/batches/v1/${batchId}/signature-challenges`}
          action="record_export"
          title={
            <span className="flex items-center gap-2">
              <Icon name="file-text" /> Generate batch record PDF — {b.batch_number}
            </span>
          }
          summary="Generating the batch record PDF is a signed act (SG-137): it renders and stores the complete batch record — steps, results, materials, equipment, evidence, comments, handovers, holds, corrections and status history — as evidence."
          submitLabel="Sign & generate"
          reason="required"
          onSign={(payload) =>
            api.post<{ aggregate_id: string }>(`/batches/v1/${batchId}/record:generate-pdf`, {
              idempotency_key: payload.idempotency_key,
              batch_id: batchId,
              challenge_id: payload.challenge_id,
              reauth_password: payload.reauth_password,
              reason: payload.reason,
            }).then((receipt) => setPdfEvidenceId(receipt.aggregate_id))
          }
        />
      )}
      {action && (
        <BatchActionModal
          batch={b}
          action={action}
          onClose={() => setAction(null)}
          onDone={() => {
            setAction(null);
            reloadAll();
          }}
        />
      )}
      {startingStep && (
        <StartStepModal
          batch={b}
          step={startingStep}
          onClose={() => setStartingStep(null)}
          onDone={() => {
            setStartingStep(null);
            reloadAll();
          }}
        />
      )}
      {resultsStep && (
        <RecordResultsModal
          batch={b}
          step={resultsStep}
          parameters={v.parameters_by_step_id[resultsStep.step_id] ?? []}
          existing={v.results_by_step_id[resultsStep.step_id] ?? []}
          onClose={() => setResultsStep(null)}
          onDone={() => {
            setResultsStep(null);
            reloadAll();
          }}
        />
      )}
      {completingStep && (
        <CompleteStepModal
          batch={b}
          step={completingStep}
          parameters={v.parameters_by_step_id[completingStep.step_id] ?? []}
          existing={v.results_by_step_id[completingStep.step_id] ?? []}
          onClose={() => setCompletingStep(null)}
          onDone={() => {
            setCompletingStep(null);
            reloadAll();
          }}
        />
      )}
      {detailStep && (
        <StepDetailModal
          batch={b}
          step={detailStep}
          detail={v.step_detail_by_step_id[detailStep.step_id]}
          parameters={v.parameters_by_step_id[detailStep.step_id] ?? []}
          results={v.results_by_step_id[detailStep.step_id] ?? []}
          evidenceLinks={v.evidence_links_by_step_id[detailStep.step_id] ?? []}
          me={me}
          onClose={() => setDetailStep(null)}
          onReload={() => {
            reloadAll();
          }}
        />
      )}
      {holdingStep && (
        <HoldStepModal
          batch={b}
          step={holdingStep}
          onClose={() => setHoldingStep(null)}
          onDone={() => {
            setHoldingStep(null);
            reloadAll();
          }}
        />
      )}
      {resumingStep && (
        <ResumeStepModal
          batch={b}
          step={resumingStep}
          activeHold={v.active_hold_by_step_id[resumingStep.step_id]}
          onClose={() => setResumingStep(null)}
          onDone={() => {
            setResumingStep(null);
            reloadAll();
          }}
        />
      )}
      {linkingEvidenceStep && (
        <LinkEvidenceModal
          batch={b}
          step={linkingEvidenceStep}
          requirements={v.step_detail_by_step_id[linkingEvidenceStep.step_id]?.evidence_requirements ?? []}
          existingLinks={v.evidence_links_by_step_id[linkingEvidenceStep.step_id] ?? []}
          onClose={() => setLinkingEvidenceStep(null)}
          onDone={() => {
            setLinkingEvidenceStep(null);
            reloadAll();
          }}
        />
      )}
      {handingOverStep && (
        <HandoverStepModal
          batch={b}
          step={handingOverStep}
          onClose={() => setHandingOverStep(null)}
          onDone={() => {
            setHandingOverStep(null);
            reloadAll();
          }}
        />
      )}
      {completingProduction && (
        <ProductionCompleteModal
          batch={b}
          onClose={() => setCompletingProduction(false)}
          onDone={() => {
            setCompletingProduction(false);
            reloadAll();
          }}
        />
      )}
    </RecordDetailShell>
  );
}

interface BatchRecordView {
  batch: { id: string; batch_number: string; state: string; target_qty: string; target_uom: string };
  steps: {
    id: string;
    recipe_step_code: string;
    state: string;
    started_at: string | null;
    completed_at: string | null;
    results: { parameter_code: string; value: string; uom: string | null; quality_status: string | null }[];
  }[];
  materials_consumed: { internal_lot: string | null; quantity: string; uom: string; issued_at: string; step_id: string | null }[];
  equipment_used: { equipment_asset_id: string; log_type: string; occurred_at: string; step_id: string | null }[];
  // Read-path completeness fix: source_id was already queried but dropped from the response, so a
  // "batch_step" deviation couldn't be attributed to its step client-side.
  deviations: { id: string; deviation_number: string; deviation_type: string; source_type: string; source_id: string; state: string }[];
  qc_results: { sample_number: string; spec_code: string; scope_type: string; test_code: string; order_state: string; outcome: string | null }[];
  status_history: { occurred_at: string; action: string; actor_username: string | null; actor_id: string; signature_id: string | null }[];
}

/** Batch-wide, cross-step view of what the recipe declares each step needs (from step_detail, already
 * fetched by execution-view) alongside what was actually consumed/used (from the batch record) — the
 * old BatchRecordModal only showed the latter; a detail page has room to show both. */
function MaterialsEquipmentTab({ execView, record }: { execView: ExecutionView; record: BatchRecordView | null }) {
  const stepCode = (stepId: string | null) => (stepId ? execView.steps.find((s) => s.step_id === stepId)?.recipe_step_code ?? stepId : "—");
  const materialRows = execView.steps.flatMap((s) =>
    (execView.step_detail_by_step_id[s.step_id]?.material_requirements ?? []).map((m) => ({ step: s.recipe_step_code, m }))
  );
  const equipmentRows = execView.steps.flatMap((s) =>
    (execView.step_detail_by_step_id[s.step_id]?.equipment_requirements ?? []).map((e) => ({ step: s.recipe_step_code, e }))
  );

  return (
    <>
      <p className="fact-k mb-2">Declared material requirements</p>
      {materialRows.length === 0 ? (
        <EmptyState icon="database">No material requirements declared.</EmptyState>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Step</th>
              <th>Material</th>
              <th>Target / range</th>
              <th>Consume mode</th>
              <th>Substitution / genealogy</th>
            </tr>
          </thead>
          <tbody>
            {materialRows.map(({ step, m }, i) => (
              <tr key={i}>
                <td className="tabular fs-2">{step}</td>
                <td className="fs-2">{m.material_name ? `${m.material_name} (${m.material_spec_business_id})` : m.material_spec_version_id}</td>
                <td className="tabular fs-2">
                  {m.target_value ? `target ${m.target_value}${m.uom ? ` ${m.uom}` : ""}` : `${m.min_value ?? "—"}–${m.max_value ?? "—"}${m.uom ? ` ${m.uom}` : ""}`}
                </td>
                <td className="fs-2">{m.consume_mode ?? "—"}</td>
                <td className="fs-2">
                  {m.substitution_allowed ? "Substitution allowed" : "No substitution"}
                  {m.genealogy_required ? ", genealogy required" : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <p className="fact-k mb-2 mt-4">Declared equipment requirements</p>
      {equipmentRows.length === 0 ? (
        <EmptyState icon="database">No equipment requirements declared.</EmptyState>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Step</th>
              <th>Equipment class</th>
              <th>Specific asset required?</th>
              <th>Calibration / qualification / cleaning</th>
            </tr>
          </thead>
          <tbody>
            {equipmentRows.map(({ step, e }, i) => (
              <tr key={i}>
                <td className="tabular fs-2">{step}</td>
                <td className="fs-2">{e.equipment_class}</td>
                <td className="fs-2">{e.exact_equipment_optional ? "No (any qualifying asset)" : "Yes"}</td>
                <td className="fs-2">
                  {[e.require_current_calibration && "calibration", e.require_current_qualification && "qualification", e.require_current_cleaning && "cleaning"]
                    .filter(Boolean)
                    .join(", ") || <span className="text-muted">none required</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <p className="hint mt-2">
        Declared by the recipe, shown for reference only — lot reservation/specific-asset linking at
        execution time is not built yet (SG-045/SG-048).
      </p>

      <p className="fact-k mb-2 mt-4">Materials actually consumed</p>
      {!record ? (
        <p className="hint mb-2">Loading…</p>
      ) : record.materials_consumed.length === 0 ? (
        <EmptyState icon="database">No material consumption recorded.</EmptyState>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Step</th>
              <th>Internal lot</th>
              <th>Quantity</th>
              <th>Recorded at</th>
            </tr>
          </thead>
          <tbody>
            {record.materials_consumed.map((m, i) => (
              <tr key={i}>
                <td className="tabular fs-2">{stepCode(m.step_id)}</td>
                <td className="tabular fs-2">{m.internal_lot ?? "—"}</td>
                <td className="tabular fs-2">
                  {m.quantity} {m.uom}
                </td>
                <td className="fs-2">{formatDateTime(m.issued_at)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <p className="fact-k mb-2 mt-4">Equipment actually used</p>
      {!record ? (
        <p className="hint mb-2">Loading…</p>
      ) : record.equipment_used.length === 0 ? (
        <EmptyState icon="database">No equipment use logged.</EmptyState>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Step</th>
              <th>Equipment asset</th>
              <th>Log type</th>
              <th>Occurred at</th>
            </tr>
          </thead>
          <tbody>
            {record.equipment_used.map((u, i) => (
              <tr key={i}>
                <td className="tabular fs-2">{stepCode(u.step_id)}</td>
                <td className="tabular fs-2">{u.equipment_asset_id}</td>
                <td className="fs-2">{u.log_type}</td>
                <td className="fs-2">{formatDateTime(u.occurred_at)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </>
  );
}

/** Batch-wide evidence links, cross-step — was previously visible only one step at a time inside
 * StepDetailModal. */
function EvidenceTab({ execView }: { execView: ExecutionView }) {
  const rows = execView.steps.flatMap((s) => (execView.evidence_links_by_step_id[s.step_id] ?? []).map((e) => ({ step: s.recipe_step_code, e })));
  if (rows.length === 0) return <EmptyState icon="file-plus-2">No evidence linked to any step yet.</EmptyState>;
  return (
    <Table>
      <thead>
        <tr>
          <th>Step</th>
          <th>Requirement</th>
          <th>SHA-256</th>
          <th>Media type</th>
          <th>Linked by</th>
          <th>Linked at</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ step, e }) => (
          <tr key={e.id}>
            <td className="tabular fs-2">{step}</td>
            <td className="fs-2">{e.requirement_code ?? "—"}</td>
            <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>{e.evidence_sha256 ?? "—"}</td>
            <td className="fs-2">{e.media_type ?? "—"}</td>
            <td className="fs-2">{e.linked_by}</td>
            <td className="fs-2">{e.created_at ? formatDateTime(e.created_at) : "—"}</td>
            <td style={{ textAlign: "right" }}>
              <Button size="sm" variant="secondary" onClick={() => downloadEvidence(e.evidence_id)}>
                <Icon name="download" /> Download
              </Button>
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

/** Deviations attributed to this batch — batch-wide (source_type "batch") and per-step ("batch_step",
 * resolved to its step via source_id, a read-path completeness fix: the field was queried but dropped
 * from the response before this). */
function DeviationsTab({ execView, record }: { execView: ExecutionView; record: BatchRecordView | null }) {
  if (!record) return <p className="hint">Loading…</p>;
  const stepCode = (stepId: string) => execView.steps.find((s) => s.step_id === stepId)?.recipe_step_code ?? stepId;
  if (record.deviations.length === 0) return <EmptyState icon="alert-triangle">No deviations attributed to this batch.</EmptyState>;
  return (
    <Table>
      <thead>
        <tr>
          <th>Deviation</th>
          <th>Type</th>
          <th>Source</th>
          <th>State</th>
        </tr>
      </thead>
      <tbody>
        {record.deviations.map((d) => (
          <tr key={d.id}>
            <td className="tabular fs-2">
              <LinkButton href={`/deviations/${d.id}`} variant="ghost" size="sm">
                {d.deviation_number}
              </LinkButton>
            </td>
            <td className="fs-2">{d.deviation_type}</td>
            <td className="fs-2">{d.source_type === "batch_step" ? `Step ${stepCode(d.source_id)}` : "Batch-wide"}</td>
            <td className="fs-2">{d.state}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

/** "Added-value results" (user's term, clarified) — the StepResultCorrection chain: what changed since
 * the original recorded value, by whom, why, and its independent-approval status. Was previously buried
 * inside a per-step StepDetailModal; promoted to its own batch-wide tab here since it's exactly the kind
 * of cross-step audit trail a dedicated detail page has room to show at once. */
function CorrectionsTab({
  execView,
  batch,
  me,
  onReload,
}: {
  execView: ExecutionView;
  batch: GxpBatch;
  me: Me | null;
  onReload: () => void;
}) {
  const canCorrect = hasPermission(me, "batch_step.correct");
  const [approvingCorrection, setApprovingCorrection] = useState<{ step: BatchStep; correction: StepResultCorrectionRow } | null>(null);
  const rows = execView.steps.flatMap((s) => (execView.corrections_by_step_id[s.step_id] ?? []).map((c) => ({ step: s, c })));

  if (rows.length === 0) return <EmptyState icon="pen">No result corrections requested for this batch.</EmptyState>;

  return (
    <>
      <Table>
        <thead>
          <tr>
            <th>Step</th>
            <th>Parameter</th>
            <th>Requested by</th>
            <th>Reason</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ step, c }) => (
            <tr key={c.correction_id}>
              <td className="tabular fs-2">{step.recipe_step_code}</td>
              <td className="font-semibold tabular fs-2">{c.parameter_code ?? "—"}</td>
              <td className="fs-2">{c.requested_by_username ?? c.requested_by_user_id}</td>
              <td className="fs-2">{c.reason_text}</td>
              <td className="fs-2">
                {c.status === "requested" ? "Awaiting independent approval" : `Approved by ${c.approved_by_username ?? c.approved_by_user_id}`}
              </td>
              <td style={{ textAlign: "right" }}>
                {c.status === "requested" && canCorrect && me?.user_id !== c.requested_by_user_id && (
                  <Button size="sm" variant="primary" onClick={() => setApprovingCorrection({ step, correction: c })}>
                    <Icon name="check-circle" /> Approve
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>

      {approvingCorrection && (
        <ApproveCorrectionModal
          batch={batch}
          step={approvingCorrection.step}
          correction={approvingCorrection.correction}
          onClose={() => setApprovingCorrection(null)}
          onDone={() => {
            setApprovingCorrection(null);
            onReload();
          }}
        />
      )}
    </>
  );
}

/** Comments, handover history and full hold history (active and released) — all three were already
 * fetched by execution-view for a while (comments/handovers) or newly added (holds_by_step_id, a
 * read-path completeness fix: released_at/released_by/release_reason were written by resume_step but
 * never surfaced anywhere before), but never rendered anywhere in this UI until now. Batch-wide status
 * history (from the batch record) rounds out the audit-trail picture in one place. */
function HistoryTab({ execView, record }: { execView: ExecutionView; record: BatchRecordView | null }) {
  const comments = execView.steps.flatMap((s) => (execView.comments_by_step_id[s.step_id] ?? []).map((c) => ({ step: s.recipe_step_code, c })));
  const handovers = execView.steps.flatMap((s) => (execView.handovers_by_step_id[s.step_id] ?? []).map((h) => ({ step: s.recipe_step_code, h })));
  const holds = execView.steps.flatMap((s) => (execView.holds_by_step_id[s.step_id] ?? []).map((h) => ({ step: s.recipe_step_code, h })));

  return (
    <>
      <p className="fact-k mb-2">Step holds</p>
      {holds.length === 0 ? (
        <EmptyState icon="lock">No step has been put on hold in this batch.</EmptyState>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Step</th>
              <th>Held at</th>
              <th>Held by</th>
              <th>Reason</th>
              <th>Released at</th>
              <th>Released by</th>
              <th>Release reason</th>
            </tr>
          </thead>
          <tbody>
            {holds.map(({ step, h }) => (
              <tr key={h.id}>
                <td className="tabular fs-2">{step}</td>
                <td className="fs-2">{h.held_at ? formatDateTime(h.held_at) : "—"}</td>
                <td className="fs-2">{h.held_by_username ?? h.held_by}</td>
                <td className="fs-2">{h.reason}</td>
                <td className="fs-2">{h.released_at ? formatDateTime(h.released_at) : <span className="error-text">still on hold</span>}</td>
                <td className="fs-2">{h.released_by_username ?? h.released_by ?? "—"}</td>
                <td className="fs-2">{h.release_reason ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <p className="fact-k mb-2 mt-4">Comments</p>
      {comments.length === 0 ? (
        <EmptyState icon="file-text">No comments recorded on any step.</EmptyState>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Step</th>
              <th>Comment</th>
              <th>By</th>
              <th>At</th>
            </tr>
          </thead>
          <tbody>
            {comments.map(({ step, c }) => (
              <tr key={c.comment_id}>
                <td className="tabular fs-2">{step}</td>
                <td className="fs-2">{c.comment_text}</td>
                <td className="fs-2">{c.created_by}</td>
                <td className="fs-2">{c.created_at ? formatDateTime(c.created_at) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <p className="fact-k mb-2 mt-4">Handover history</p>
      {handovers.length === 0 ? (
        <EmptyState icon="arrow-right">No step has been handed over in this batch.</EmptyState>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Step</th>
              <th>From</th>
              <th>To</th>
              <th>Reason</th>
              <th>At</th>
            </tr>
          </thead>
          <tbody>
            {handovers.map(({ step, h }) => (
              <tr key={h.handover_id}>
                <td className="tabular fs-2">{step}</td>
                <td className="fs-2">{h.from_subject_id ?? "—"}</td>
                <td className="fs-2">{h.to_subject_id}</td>
                <td className="fs-2">{h.reason ?? "—"}</td>
                <td className="fs-2">{h.created_at ? formatDateTime(h.created_at) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <p className="fact-k mb-2 mt-4">Status history</p>
      {!record ? (
        <p className="hint">Loading…</p>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Occurred at</th>
              <th>Action</th>
              <th>Actor</th>
              <th>Signed</th>
            </tr>
          </thead>
          <tbody>
            {record.status_history.map((e, i) => (
              <tr key={i}>
                <td className="fs-2">{formatDateTime(e.occurred_at)}</td>
                <td className="fs-2">{e.action}</td>
                <td className="fs-2">{e.actor_username ?? e.actor_id}</td>
                <td className="fs-2">{e.signature_id ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </>
  );
}

function QcResultsTab({ record }: { record: BatchRecordView | null }) {
  if (!record) return <p className="hint">Loading…</p>;
  if (record.qc_results.length === 0) return <EmptyState icon="flask">No QC results attributed to this batch.</EmptyState>;
  return (
    <Table>
      <thead>
        <tr>
          <th>Sample</th>
          <th>Spec</th>
          <th>Scope</th>
          <th>Test</th>
          <th>Outcome</th>
        </tr>
      </thead>
      <tbody>
        {record.qc_results.map((q, i) => (
          <tr key={i}>
            <td className="tabular fs-2">{q.sample_number}</td>
            <td className="fs-2">{q.spec_code}</td>
            <td className="fs-2">{q.scope_type}</td>
            <td className="fs-2">{q.test_code}</td>
            <td className="fs-2">{q.outcome ?? "pending"}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

// BAT-FR-020, step scope (SG-047 further partial resolution, 2026-09-09). Signed (Document 106 row 14's
// shape, the nearest analogous batch-level action -- no step-scoped row exists in Document 106 itself).
function HoldStepModal({
  batch,
  step,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  onClose: () => void;
  onDone: () => void;
}) {
  const [reason, setReason] = useState("");

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/batches/v1/${batch.batch_id}/steps/${step.step_id}/signature-challenges`}
      action="hold"
      title={
        <span className="flex items-center gap-2">
          <Icon name="lock" /> Hold step - {step.recipe_step_code}
        </span>
      }
 summary="Holding this step is a signed act and stops only this step - the rest of the batch keeps running."
      submitLabel="Sign & hold"
      reason="none"
      disabled={!reason.trim()}
      extraFields={
        <Field label="Hold reason" required>
          <textarea className="input" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
      }
      onSign={(payload) =>
        api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/hold`, {
          idempotency_key: payload.idempotency_key,
          batch_id: batch.batch_id,
          step_id: step.step_id,
          expected_version: step.version,
          reason: reason.trim(),
          challenge_id: payload.challenge_id,
          reauth_password: payload.reauth_password,
        })
      }
    />
  );
}

// BAT-FR-020 resume — Document 106 row 17's shape ("Approved", the meaning a QA authority attests when
// lifting a hold, distinct from the "Performed" the hold itself used).
function ResumeStepModal({
  batch,
  step,
  activeHold,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  activeHold: ActiveHold | undefined;
  onClose: () => void;
  onDone: () => void;
}) {
  const [reason, setReason] = useState("");

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/batches/v1/${batch.batch_id}/steps/${step.step_id}/signature-challenges`}
      action="resume"
      title={
        <span className="flex items-center gap-2">
          <Icon name="play" /> Resume step - {step.recipe_step_code}
        </span>
      }
      summary={
        activeHold
          ? `Held for: ${activeHold.reason}`
 :"Resuming this step is a signed act."
      }
      submitLabel="Sign & resume"
      reason="none"
      extraFields={
        <Field label="Resume note" hint="Optional - recorded in the audit trail.">
          <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
      }
      onSign={(payload) =>
        api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/resume`, {
          idempotency_key: payload.idempotency_key,
          batch_id: batch.batch_id,
          step_id: step.step_id,
          expected_version: step.version,
          reason: reason.trim() || null,
          challenge_id: payload.challenge_id,
          reauth_password: payload.reauth_password,
        })
      }
    />
  );
}

// BAT-FR-026, steps-completeness sub-clause only (SG-048 #026 partial resolution, 2026-09-09). Document
// 106 row 16's shape ("Performed", qualified performer, no independence).
function ProductionCompleteModal({
  batch,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  onClose: () => void;
  onDone: () => void;
}) {
  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/batches/v1/${batch.batch_id}/signature-challenges`}
      action="production_complete"
      title={
        <span className="flex items-center gap-2">
          <Icon name="check-circle" /> Mark production complete - {batch.batch_number}
        </span>
      }
 summary="Every recipe step is Complete. This is a signed act marking the batch's production phase done. Yield/reconciliation and other production blockers are not checked by this action yet."
      submitLabel="Sign & mark complete"
      reason="none"
      onSign={(payload) =>
        api.post(`/batches/v1/${batch.batch_id}/production-complete`, {
          idempotency_key: payload.idempotency_key,
          batch_id: batch.batch_id,
          expected_version: batch.version,
          challenge_id: payload.challenge_id,
          reauth_password: payload.reauth_password,
        })
      }
    />
  );
}

// "Step detail" — read-only, BAT-FR-005/§9's execution-UI field list (instruction, section, dependencies,
// evidence requirements, target/limits) plus current progress (2026-09-09, client-requested).
function StepDetailModal({
  batch,
  step,
  detail,
  parameters,
  results,
  evidenceLinks,
  me,
  onClose,
  onReload,
}: {
  batch: GxpBatch;
  step: BatchStep;
  detail: StepDetail | undefined;
  parameters: StepParameter[];
  results: StepResultRow[];
  evidenceLinks: StepEvidenceLinkRow[];
  me: Me | null;
  onClose: () => void;
  onReload: () => void;
}) {
  const latestByCode = new Map<string, StepResultRow>();
  for (const r of results) latestByCode.set(r.parameter_code, r);
  const canCorrect = hasPermission(me, "batch_step.correct");
  const [correctingResult, setCorrectingResult] = useState<{ result: StepResultRow; parameter: StepParameter | undefined } | null>(null);
  // requirement_code == evidence_type (commands.py::complete_step()'s own naming symmetry) — counts here
  // mirror exactly what the Complete-step evidence gate checks, so "N of M linked" never disagrees with it.
  const linkedCountByType = new Map<string, number>();
  for (const link of evidenceLinks) {
    if (link.requirement_code) linkedCountByType.set(link.requirement_code, (linkedCountByType.get(link.requirement_code) ?? 0) + 1);
  }

  return (
    <Modal open onClose={onClose} title={`Step detail - ${step.recipe_step_code}`} large>
      <FactGrid>
        <Fact label="State">
          <WorkflowStatePill state={step.state} />
        </Fact>
        <Fact label="Step type">{detail?.step_type ?? "—"}</Fact>
        <Fact label="Section">{detail?.section_name ? `${detail.section_name} (${detail.section_code})` : "—"}</Fact>
        <Fact label="Critical">{detail?.is_critical ? "Yes" : "No"}</Fact>
        <Fact label="Required role">{step.required_role_code ?? <span className="text-muted">any</span>}</Fact>
        <Fact label="Assigned">
          {step.assigned_full_name ? `${step.assigned_full_name} (${step.assigned_username})` : step.assigned_subject_id ?? "—"}
        </Fact>
        <Fact label="Started">{step.started_at ? formatDateTime(step.started_at) : "—"}</Fact>
        <Fact label="Completed">{step.completed_at ? formatDateTime(step.completed_at) : "—"}</Fact>
      </FactGrid>

      <div className="mt-4">
        <p className="fact-k mb-1">Instruction</p>
        {detail?.instruction_text ? (
          <p className="fs-3" style={{ whiteSpace: "pre-wrap" }}>
            {detail.instruction_text}
          </p>
        ) : (
          <p className="hint">This step&apos;s recipe has no instruction text recorded.</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 mt-4">
        <div>
          <p className="fact-k mb-1">Predecessors (must be Complete first)</p>
          {!detail || detail.predecessor_codes.length === 0 ? (
            <p className="hint">None - this step is a root step.</p>
          ) : (
            <p className="tabular fs-2">{detail.predecessor_codes.join(", ")}</p>
          )}
        </div>
        <div>
          <p className="fact-k mb-1">Unblocks next</p>
          {!detail || detail.successor_codes.length === 0 ? (
            <p className="hint">None - this is a terminal step.</p>
          ) : (
            <p className="tabular fs-2">{detail.successor_codes.join(", ")}</p>
          )}
        </div>
      </div>

      <div className="mt-4">
        <p className="fact-k mb-2">Parameters &amp; recorded results</p>
        {parameters.length === 0 ? (
          <p className="hint">This step has no parameters.</p>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Parameter</th>
                <th>Type</th>
                <th>Target / range</th>
                <th>Recorded value</th>
                <th>When</th>
                {step.state === "complete" && canCorrect && <th></th>}
              </tr>
            </thead>
            <tbody>
              {parameters.map((p) => {
                const r = latestByCode.get(p.parameter_code);
                const recorded = r
                  ? r.value_bool !== null
                    ? r.value_bool
                      ? "true"
                      : "false"
                    : (r.value_numeric ?? r.value_text ?? "—")
                  : null;
                return (
                  <tr key={p.parameter_code}>
                    <td className="font-semibold tabular">
                      {p.parameter_code}
                      {p.required && <span className="error-text"> *</span>}
                    </td>
                    <td className="fs-2">
                      {p.data_type}
                      {p.uom ? ` (${p.uom})` : ""}
                    </td>
                    <td className="tabular fs-2">
                      {p.target_value ? `target ${p.target_value}` : p.min_value || p.max_value ? `${p.min_value ?? "—"}–${p.max_value ?? "—"}` : "—"}
                    </td>
                    <td className="tabular fs-2">
                      {recorded ?? <span className="text-muted">not recorded</span>}
                      {r?.quality_status === "out_of_range" && (
                        <span className="error-text" style={{ marginLeft: 6 }} title="Outside the recipe's declared min/max — captured, does not block save or Complete">
                          <Icon name="alert-triangle" /> out of range
                        </span>
                      )}
                    </td>
                    <td className="tabular fs-2">{r?.received_at ? formatDateTime(r.received_at) : "—"}</td>
                    {step.state === "complete" && canCorrect && (
                      <td style={{ textAlign: "right" }}>
                        {r && (
                          <Button size="sm" variant="secondary" onClick={() => setCorrectingResult({ result: r, parameter: p })}>
                            <Icon name="pen" /> Correct
                          </Button>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </div>

      <div className="mt-4">
        <p className="fact-k mb-2">Evidence requirements</p>
        {!detail || detail.evidence_requirements.length === 0 ? (
          <p className="hint">This step has no declared evidence requirement.</p>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Evidence type</th>
                <th>Count required</th>
                <th>Linked so far</th>
                <th>Allowed file types</th>
              </tr>
            </thead>
            <tbody>
              {detail.evidence_requirements.map((e, i) => {
                const linked = linkedCountByType.get(e.evidence_type) ?? 0;
                const met = linked >= e.required_count;
                return (
                  <tr key={`${e.evidence_type}-${i}`}>
                    <td className="fs-2">{e.evidence_type}</td>
                    <td className="tabular fs-2">{e.required_count}</td>
                    <td className="tabular fs-2">
                      {met ? (
                        <span className="flex items-center gap-1">
                          <Icon name="check-circle" /> {linked} of {e.required_count}
                        </span>
                      ) : (
                        <span className="error-text" style={{ marginTop: 0 }}>
                          <Icon name="alert-triangle" /> {linked} of {e.required_count}
                        </span>
                      )}
                    </td>
                    <td className="fs-2">{e.allowed_mime_types ?? <span className="text-muted">any</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
        <p className="hint mt-2">
          Stage and finalize the evidence object itself under Platform ops → Evidence operations, then use
 this step&apos;s &quot;Link evidence&quot; action to attach it here.
        </p>
      </div>

      <div className="mt-4">
        <p className="fact-k mb-2">Material requirements</p>
        {!detail || detail.material_requirements.length === 0 ? (
          <p className="hint">This step has no declared material requirement.</p>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Material</th>
                <th>Target / range</th>
                <th>Consume mode</th>
                <th>Substitution / genealogy</th>
              </tr>
            </thead>
            <tbody>
              {detail.material_requirements.map((m, i) => (
                <tr key={`${m.material_spec_version_id}-${i}`}>
                  <td className="fs-2">
                    {m.material_name ? `${m.material_name} (${m.material_spec_business_id})` : m.material_spec_version_id}
                  </td>
                  <td className="tabular fs-2">
                    {m.target_value ? `target ${m.target_value}${m.uom ? ` ${m.uom}` : ""}` : `${m.min_value ?? "—"}–${m.max_value ?? "—"}${m.uom ? ` ${m.uom}` : ""}`}
                  </td>
                  <td className="fs-2">{m.consume_mode ?? <span className="text-muted">—</span>}</td>
                  <td className="fs-2">
                    {m.substitution_allowed ? "Substitution allowed" : "No substitution"}
                    {m.genealogy_required ? ", genealogy required" : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
        <p className="hint mt-2">
          Declared by the recipe, shown for reference only — lot reservation/consumption at execution
          time is not built yet (SG-045/SG-048).
        </p>
      </div>

      <div className="mt-4">
        <p className="fact-k mb-2">Equipment requirements</p>
        {!detail || detail.equipment_requirements.length === 0 ? (
          <p className="hint">This step has no declared equipment requirement.</p>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Equipment class</th>
                <th>Specific asset required?</th>
                <th>Calibration / qualification / cleaning</th>
              </tr>
            </thead>
            <tbody>
              {detail.equipment_requirements.map((eq, i) => (
                <tr key={`${eq.equipment_class}-${i}`}>
                  <td className="fs-2">{eq.equipment_class}</td>
                  <td className="fs-2">{eq.exact_equipment_optional ? "No (any qualifying asset)" : "Yes"}</td>
                  <td className="fs-2">
                    {[
                      eq.require_current_calibration && "calibration",
                      eq.require_current_qualification && "qualification",
                      eq.require_current_cleaning && "cleaning",
                    ]
                      .filter(Boolean)
                      .join(", ") || <span className="text-muted">none required</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
        <p className="hint mt-2">
          Declared by the recipe, shown for reference only — linking a specific equipment asset at
          execution time is not built yet (SG-045/SG-048).
        </p>
      </div>

      <div className="flex justify-end mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </div>

      {correctingResult && (
        <RequestCorrectionModal
          batch={batch}
          step={step}
          result={correctingResult.result}
          parameter={correctingResult.parameter}
          onClose={() => setCorrectingResult(null)}
          onDone={() => {
            setCorrectingResult(null);
            onReload();
          }}
        />
      )}
    </Modal>
  );
}

// BAT-FR-023, SG-048 #023 — the request half of the existing 2-signature correction flow (backend built
// 2026-09-14, no UI until now). Bound to the *result's* own version/hash, not the step's.
function RequestCorrectionModal({
  batch,
  step,
  result,
  parameter,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  result: StepResultRow;
  parameter: StepParameter | undefined;
  onClose: () => void;
  onDone: () => void;
}) {
  const [reasonText, setReasonText] = useState("");
  const dataType = parameter?.data_type ?? result.data_type;
  const currentDisplay = result.value_bool !== null ? (result.value_bool ? "true" : "false") : (result.value_numeric ?? result.value_text ?? "—");
  const [value, setValue] = useState<string>(result.value_bool !== null ? (result.value_bool ? "true" : "false") : (result.value_numeric ?? result.value_text ?? ""));

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/batches/v1/${batch.batch_id}/steps/${step.step_id}/results/${result.result_id}/signature-challenges`}
      action="correct_request"
      title={
        <span className="flex items-center gap-2">
          <Icon name="pen" /> Request correction - {result.parameter_code}
        </span>
      }
      summary="Requesting a correction to a completed step's result is a signed act. An independent approver (not you) must sign it before the correction takes effect."
      submitLabel="Sign & request"
      reason="none"
      disabled={!reasonText.trim() || !value.trim()}
      extraFields={
        <>
          <Field label="Corrected value" hint={`Current value: ${currentDisplay}`}>
            {isBooleanParameter(dataType) ? (
              <Select value={value} onChange={(e) => setValue(e.target.value)}>
                <option value="">—</option>
                <option value="true">Pass / Yes</option>
                <option value="false">Fail / No</option>
              </Select>
            ) : (
              <Input type={isNumericParameter(dataType) ? "number" : "text"} step="any" value={value} onChange={(e) => setValue(e.target.value)} />
            )}
          </Field>
          <Field label="Reason" required hint="Why this result needs correcting — part of the permanent record.">
            <textarea className="input" rows={3} value={reasonText} onChange={(e) => setReasonText(e.target.value)} />
          </Field>
        </>
      }
      onSign={(payload) =>
        api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/correct`, {
          idempotency_key: payload.idempotency_key,
          batch_id: batch.batch_id,
          step_id: step.step_id,
          result_id: result.result_id,
          reason_text: reasonText,
          challenge_id: payload.challenge_id,
          reauth_password: payload.reauth_password,
          ...(isBooleanParameter(dataType)
            ? { corrected_value_bool: value === "true" }
            : isNumericParameter(dataType)
              ? { corrected_value_numeric: value }
              : { corrected_value_text: value }),
        })
      }
    />
  );
}

// BAT-FR-023, SG-048 #023 — the approval half. SoD is enforced server-side (requester cannot approve
// their own request); the button that opens this modal is already hidden for the requester client-side.
function ApproveCorrectionModal({
  batch,
  step,
  correction,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  correction: StepResultCorrectionRow;
  onClose: () => void;
  onDone: () => void;
}) {
  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/batches/v1/${batch.batch_id}/steps/${step.step_id}/results/${correction.original_result_id}/signature-challenges`}
      action="correct_approve"
      title={
        <span className="flex items-center gap-2">
          <Icon name="check-circle" /> Approve correction - {correction.parameter_code}
        </span>
      }
      summary={`Requested by ${correction.requested_by_username ?? correction.requested_by_user_id}: "${correction.reason_text}". Approving is an independent signed act.`}
      submitLabel="Sign & approve"
      reason="none"
      onSign={(payload) =>
        api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/corrections/${correction.correction_id}/approve`, {
          idempotency_key: payload.idempotency_key,
          correction_id: correction.correction_id,
          challenge_id: payload.challenge_id,
          reauth_password: payload.reauth_password,
        })
      }
    />
  );
}

function BatchActionModal({
  batch,
  action,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  action: Action;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [reason, setReason] = useState("");

  const PATH: Record<Action, string> = {
    issue: "issue",
    start: "start",
    hold: "hold",
    resume: "resume",
    abort: "abort",
  };

  return (
    <Modal open onClose={onClose} title={`${ACTION_LABEL[action]} - ${batch.batch_number}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/batches/v1/${batch.batch_id}/${PATH[action]}`, {
              idempotency_key: newIdempotencyKey(),
              batch_id: batch.batch_id,
              expected_version: batch.version,
              // The issue command takes no reason; the transition commands all accept one.
              ...(action === "issue" ? {} : { reason: reason || null }),
            })
          );
        }}
      >
        {action === "issue" && (
          <p className="fs-3 mb-3">
            Issuing freezes the recipe into an execution snapshot and creates this batch&apos;s step
            instances. The snapshot, not the live recipe, governs execution from here.
          </p>
        )}
        {action === "abort" && (
          <Banner tone="critical" title="Aborting is final">
            An aborted batch cannot be resumed. Material already consumed stays consumed and must be
            reconciled.
          </Banner>
        )}

        {action !== "issue" && (
          <Field
            label="Reason"
            required={action === "hold" || action === "abort"}
            hint="Part of the permanent batch record."
          >
            <textarea
              className="input"
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required={action === "hold" || action === "abort"}
            />
          </Field>
        )}

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant={action === "abort" ? "danger" : "primary"} disabled={busy}>
            {busy ? "Saving…" : ACTION_LABEL[action]}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function StartStepModal({
  batch,
  step,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [overrideReason, setOverrideReason] = useState("");
  const roleMismatch = error?.startsWith("STEP_ROLE_MISMATCH");
  // Known-limitations fix (docs/testing/demo-gujarati/08 §8.8): one picker per declared equipment
  // requirement -- the backend (commands.py::_enforce_step_equipment) is the real authority on whether a
  // chosen asset actually satisfies the requirement (class match + calibration/qualification/cleaning
  // currency), so this picker doesn't try to pre-filter by eligibility, only lets the operator name which
  // asset(s) they're using.
  const equipmentRequirements = step.equipment_requirements ?? [];
  const [equipmentAssetIds, setEquipmentAssetIds] = useState<string[]>(() => equipmentRequirements.map(() => ""));
  const entities = useEntityOptions();
  const equipmentError = error?.startsWith("EQUIPMENT_");

  return (
    <Modal open onClose={onClose} title={`Start step ${step.recipe_step_code}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/start`, {
              idempotency_key: newIdempotencyKey(),
              batch_id: batch.batch_id,
              step_id: step.step_id,
              expected_version: step.version,
              override_reason: overrideReason.trim() || undefined,
              ...(equipmentAssetIds.some((id) => id)
                ? { equipment_asset_ids: equipmentAssetIds.filter((id) => id) }
                : {}),
            })
          );
        }}
      >
        <p className="fs-3 mb-3">
          Starting a step claims it for you and records the start time. Your qualification and role for
          this step are checked by the backend.
        </p>
        <FactGrid>
          <Fact label="Step">{step.recipe_step_code}</Fact>
          <Fact label="Required role">{step.required_role_code ?? "any"}</Fact>
          <Fact label="Current state">
            <WorkflowStatePill state={step.state} />
          </Fact>
        </FactGrid>
        {equipmentRequirements.length > 0 && (
          <div className="mt-3">
            <p className="hint mb-2">
              This step declares {equipmentRequirements.length} equipment requirement
              {equipmentRequirements.length === 1 ? "" : "s"} - name which asset you are using for each.
            </p>
            {equipmentRequirements.map((req, i) => (
              <EntityPickerField
                key={i}
                label={`Equipment for "${req.equipment_class}"${req.exact_equipment_optional ? "" : " (required)"}`}
                hint={
                  [
                    req.require_current_calibration && "requires current calibration",
                    req.require_current_qualification && "requires current qualification",
                    req.require_current_cleaning && "requires current cleaning",
                  ]
                    .filter(Boolean)
                    .join(", ") || undefined
                }
                value={equipmentAssetIds[i] ?? ""}
                onChange={(v) => setEquipmentAssetIds((prev) => prev.map((id, idx) => (idx === i ? v : id)))}
                options={entities.equipment}
                status={entities.equipmentStatus}
                kind="equipment asset"
              />
            ))}
          </div>
        )}
        {step.required_role_code && (
          <div className="mt-3">
            <label className="hint" style={{ display: "block", marginBottom: 4 }}>
              Override reason{" "}
              <span className="text-muted">
 (only needed if you do not hold the {step.required_role_code} role recorded on the audit
                event; requires a Supervisor/Admin)
              </span>
            </label>
            <textarea
              className="input"
              rows={2}
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="e.g. cross-trained lead covering an absent operator, per shift log…"
            />
          </div>
        )}
        {error && (
          <p className="error-text mt-3 mb-2">
            {roleMismatch
              ? "This step is reserved for another role. Enter an override reason above and retry (Supervisor/Admin only)."
              : equipmentError
              ? `Equipment requirement not satisfied: ${error}`
              : error}
          </p>
        )}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            <Icon name="play" /> {busy ? "Starting…" : "Start step"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// GET /evidence/v1/objects?owner_type=&owner_id= — one row per staged/finalized evidence object owned
// by this step (convention: evidence is staged with owner_type "batch_step", owner_id = the step id).
interface EvidenceObjectOption {
  id: string;
  filename: string | null;
  mime_type: string;
  state: string;
  content_hash: string | null;
}

/** Local to this modal only, same "page-local fetch, not promoted to useEntityOptions()" precedent as
 * `useEligibleSterileItems` on the aseptic page — nothing else needs an owner-filtered evidence list yet.
 *
 * Only FINALIZED/ARCHIVED objects are offered — a STAGED object has no `content_hash` yet (it's computed
 * at finalize time), so picking one auto-filled `evidence_sha256` with an empty string, which the backend
 * silently dropped from the request body (an empty coerced value isn't sent) and rejected as a 422
 * "field required" — a confusing failure for what looked like a normal pick-and-submit. `pendingCount`
 * (STAGED objects filtered out) drives a hint distinguishing "nothing staged yet" from "staged but still
 * needs finalizing". */
function useStepEvidenceOptions(stepId: string): {
  options: EntityOption[];
  status: EntityOptionsStatus;
  byId: Map<string, EvidenceObjectOption>;
  pendingCount: number;
} {
  const [rows, setRows] = useState<EvidenceObjectOption[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    api
      .get<{ evidence_objects: EvidenceObjectOption[] }>(`/evidence/v1/objects?owner_type=batch_step&owner_id=${stepId}`)
      .then((res) => {
        if (cancelled) return;
        setRows(res.evidence_objects);
        setStatus(res.evidence_objects.some((r) => r.state === "FINALIZED" || r.state === "ARCHIVED") ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [stepId]);

  const linkable = rows.filter((r) => r.state === "FINALIZED" || r.state === "ARCHIVED");
  const byId = new Map(linkable.map((r) => [r.id, r]));
  const options: EntityOption[] = linkable.map((r) => ({
    value: r.id,
    label: `${r.filename ?? r.id} — ${r.state}${r.content_hash ? ` (${r.content_hash.slice(0, 10)}…)` : ""}`,
  }));
  const pendingCount = rows.length - linkable.length;
  return { options, status, byId, pendingCount };
}

/** `requirementOptions` comes from the step's declared `evidence_requirements` (already in scope on the
 * modal — no extra fetch needed). `complete_step()` gates on `link.requirement_code == req.evidence_type`
 * as a plain, case-sensitive dict-key match (services/gxp-api .../commands.py `complete_step()`), and the
 * live "N of M required" counter above uses the same comparison — a free-text field that doesn't exactly
 * match silently linked evidence nobody's requirement checklist ever counted (the bug this fixes: a link
 * submitted fine, but "photo: 0 of 1 linked" never moved). A dropdown of the real `evidence_type` values
 * makes a mismatch impossible. Left free text when a step has no declared requirements at all. */
function evidenceLinkSubfields(
  evidenceOptions: EntityOption[],
  evidenceOptionsStatus: EntityOptionsStatus,
  requirementOptions: { value: string; label: string }[]
): RepeatSubField[] {
  return [
    {
      name: "evidence_id", label: "Evidence object", required: true,
      type: "customSelect", options: evidenceOptions, optionsStatus: evidenceOptionsStatus,
      optionsNoun: "evidence object", placeholder: "From Platform ops → Evidence operations",
    },
    { name: "evidence_sha256", label: "Evidence SHA-256", required: true },
    { name: "media_type", label: "Media type" },
    requirementOptions.length > 0
      ? {
          name: "requirement_code", label: "Requirement code", required: true,
          type: "select", options: requirementOptions,
        }
      : { name: "requirement_code", label: "Requirement code", placeholder: "No declared requirements for this step" },
  ];
}

/** SG-047 (`gxp_step_evidence_link` half) — unsigned by design (attaching evidence is a capture, not a
 * release/disposition decision). Links already-staged/finalized evidence objects (stage + finalize an
 * upload via Platform ops → Evidence operations first) — this modal offers a picker of evidence already
 * staged for this step (owner_type "batch_step", owner_id this step's id), auto-filling the hash/media
 * type from the real record; manual entry stays available as a fallback (e.g. evidence staged under a
 * different owner_id). */
function LinkEvidenceModal({
  batch,
  step,
  requirements,
  existingLinks,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  requirements: StepEvidenceRequirement[];
  existingLinks: StepEvidenceLinkRow[];
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [links, setLinks] = useState<RepeatRow[]>([]);
  const { options: evidenceOptions, status: evidenceOptionsStatus, byId: evidenceById, pendingCount } = useStepEvidenceOptions(step.step_id);
  const requirementOptions = Array.from(new Set(requirements.map((r) => r.evidence_type))).map((t) => ({ value: t, label: t }));
  const subFields = evidenceLinkSubfields(evidenceOptions, evidenceOptionsStatus, requirementOptions);
  // Live "N of M required" — the same requirement_code<->evidence_type match complete_step()'s gate uses,
  // recomputed with the rows currently staged in this form so it updates as the tester fills them in.
  const linkedCountByType = new Map<string, number>();
  for (const link of existingLinks) {
    if (link.requirement_code) linkedCountByType.set(link.requirement_code, (linkedCountByType.get(link.requirement_code) ?? 0) + 1);
  }
  for (const row of links) {
    const code = row.requirement_code;
    if (code) linkedCountByType.set(code, (linkedCountByType.get(code) ?? 0) + 1);
  }

  function handleLinksChange(rows: RepeatRow[]) {
    // Picking a real evidence object auto-fills its actual hash/media type instead of requiring them
    // typed by hand — only for rows whose evidence_id matches a known fetched object; a manually-typed
    // id (evidence staged under a different owner) leaves those fields untouched.
    setLinks(
      rows.map((row) => {
        const picked = evidenceById.get(row.evidence_id ?? "");
        return picked
          ? { ...row, evidence_sha256: picked.content_hash ?? row.evidence_sha256, media_type: row.media_type || picked.mime_type }
          : row;
      })
    );
  }

  return (
    <Modal open onClose={onClose} title={`Link evidence - ${step.recipe_step_code}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/evidence-links`, {
              idempotency_key: newIdempotencyKey(),
              batch_id: batch.batch_id,
              step_id: step.step_id,
              expected_version: step.version,
              links: buildRepeatArray(subFields, links),
            })
          );
        }}
      >
        <p className="fs-3 mb-3">
          Stage and finalize the evidence object first (Platform ops → Evidence operations, owner type
          &quot;batch_step&quot;, owner ID = this step), then pick it below. Only finalized evidence is
          offered — a staged-but-not-yet-finalized object has no hash yet to link.
        </p>
        {pendingCount > 0 && (
          <p className="fs-2 text-muted mb-3">
            {pendingCount} evidence object{pendingCount === 1 ? "" : "s"} staged for this step{" "}
            {pendingCount === 1 ? "is" : "are"} not yet finalized, so {pendingCount === 1 ? "it isn't" : "they aren't"}{" "}
            listed below — finalize {pendingCount === 1 ? "it" : "them"} via Platform ops → Evidence operations first.
          </p>
        )}
        {requirements.length > 0 && (
          <div className="mb-3">
            <p className="fact-k mb-1">Required evidence</p>
            <ul className="record-list fs-2">
              {requirements.map((req, i) => {
                const linked = linkedCountByType.get(req.evidence_type) ?? 0;
                const met = linked >= req.required_count;
                return (
                  <li key={`${req.evidence_type}-${i}`} className={met ? undefined : "error-text"}>
                    {req.evidence_type}: {linked} of {req.required_count} linked
                    {!met && " (add a link with this requirement code below)"}
                  </li>
                );
              })}
            </ul>
          </div>
        )}
        <RepeatableRows
          label="Evidence links"
          required
          itemLabel="Evidence link"
          subFields={subFields}
          value={links}
          onChange={handleLinksChange}
        />
        {error && <p className="error-text mt-3 mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || links.length === 0}>
            {busy ? "Linking…" : "Link evidence"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function HandoverStepModal({
  batch,
  step,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const entities = useEntityOptions();
  const [toUserId, setToUserId] = useState("");
  const [reason, setReason] = useState("");

  return (
    <Modal open onClose={onClose} title={`Hand over step - ${step.recipe_step_code}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/handover`, {
              idempotency_key: newIdempotencyKey(),
              batch_id: batch.batch_id,
              step_id: step.step_id,
              expected_version: step.version,
              to_user_id: toUserId,
              reason: reason.trim() || null,
            })
          );
        }}
      >
        <p className="fs-3 mb-3">Reassigns this in-progress step to another qualified operator.</p>
        <EntityPickerField
          label="Hand over to"
          required
          value={toUserId}
          onChange={setToUserId}
          options={entities.users}
          status={entities.usersStatus}
          kind="user"
        />
        <Field label="Reason" hint="Optional. Recorded in the audit trail.">
          <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
        {error && <p className="error-text mt-3 mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !toUserId.trim()}>
            {busy ? "Handing over…" : "Hand over"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// BAT-FR-009/010, Document 106 row 21 (batch_step/results) — SG-047 partial resolution. Each recorded
// value's data_type comes from the recipe's own RecipeParameter (parameters prop), not asserted by this
// form -- the widget below is chosen by matching that declared type, purely a rendering decision.
function RecordResultsModal({
  batch,
  step,
  parameters,
  existing,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  parameters: StepParameter[];
  existing: StepResultRow[];
  onClose: () => void;
  onDone: () => void;
}) {
  // `existing` is received_at-ascending (service.get_step_results) -- last write per code wins as the
  // pre-filled starting value, a convenience for correcting a mis-keyed reading before completion.
  const latestByCode = new Map<string, StepResultRow>();
  for (const r of existing) latestByCode.set(r.parameter_code, r);

  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const p of parameters) {
      const prior = latestByCode.get(p.parameter_code);
      if (!prior) continue;
      if (isBooleanParameter(p.data_type)) init[p.parameter_code] = prior.value_bool ? "true" : "false";
      else if (isNumericParameter(p.data_type)) init[p.parameter_code] = prior.value_numeric ?? "";
      else init[p.parameter_code] = prior.value_text ?? "";
    }
    return init;
  });

  const filled = parameters.filter((p) => (values[p.parameter_code] ?? "").trim() !== "");

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/batches/v1/${batch.batch_id}/steps/${step.step_id}/signature-challenges`}
      action="results"
      title={
        <span className="flex items-center gap-2">
          <Icon name="clipboard" /> Record results - {step.recipe_step_code}
        </span>
      }
 summary="Recording a parameter result against this step is a signed act."
      submitLabel="Sign & record"
      reason="none"
      disabled={filled.length === 0}
      extraFields={
        <div className="mb-3">
          {parameters.length === 0 && <p className="hint">This step has no parameters to record.</p>}
          {parameters.map((p) => (
            <Field
              key={p.parameter_code}
              label={`${p.parameter_code}${p.required ? " *" : ""}`}
              hint={
                [
                  p.uom,
                  p.target_value ? `target ${p.target_value}` : null,
                  p.min_value || p.max_value ? `range ${p.min_value ?? "—"}–${p.max_value ?? "—"}` : null,
                ]
                  .filter(Boolean)
                  .join(" · ") || undefined
              }
            >
              {isBooleanParameter(p.data_type) ? (
                <Select
                  value={values[p.parameter_code] ?? ""}
                  onChange={(e) => setValues((v) => ({ ...v, [p.parameter_code]: e.target.value }))}
                >
                  <option value="">—</option>
                  <option value="true">Pass / Yes</option>
                  <option value="false">Fail / No</option>
                </Select>
              ) : (
                <Input
                  type={isNumericParameter(p.data_type) ? "number" : "text"}
                  step="any"
                  value={values[p.parameter_code] ?? ""}
                  onChange={(e) => setValues((v) => ({ ...v, [p.parameter_code]: e.target.value }))}
                />
              )}
            </Field>
          ))}
        </div>
      }
      onSign={(payload) =>
        api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/results`, {
          idempotency_key: payload.idempotency_key,
          batch_id: batch.batch_id,
          step_id: step.step_id,
          expected_version: step.version,
          challenge_id: payload.challenge_id,
          reauth_password: payload.reauth_password,
          results: filled.map((p) => {
            const raw = values[p.parameter_code];
            if (isBooleanParameter(p.data_type)) return { parameter_code: p.parameter_code, value_bool: raw === "true" };
            if (isNumericParameter(p.data_type)) return { parameter_code: p.parameter_code, value_numeric: raw };
            return { parameter_code: p.parameter_code, value_text: raw };
          }),
        })
      }
    />
  );
}

// BAT-FR-006 (runtime)/015/016, Document 106 row 19 (batch_step/complete) — SG-047 partial resolution.
// Blocked client-side (mirrors the server's own PARAMETER_REQUIRED check) whenever a required parameter
// has no recorded result yet.
function CompleteStepModal({
  batch,
  step,
  parameters,
  existing,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  parameters: StepParameter[];
  existing: StepResultRow[];
  onClose: () => void;
  onDone: () => void;
}) {
  const recordedCodes = new Set(existing.map((r) => r.parameter_code));
  const missingRequired = parameters.filter((p) => p.required && !recordedCodes.has(p.parameter_code));
  const [overrideReason, setOverrideReason] = useState("");

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/batches/v1/${batch.batch_id}/steps/${step.step_id}/signature-challenges`}
      action="complete"
      title={
        <span className="flex items-center gap-2">
          <Icon name="check-circle" /> Complete step - {step.recipe_step_code}
        </span>
      }
      summary={
        missingRequired.length > 0 ? (
          <>Missing a recorded result for: {missingRequired.map((p) => p.parameter_code).join(", ")}. Record results first.</>
        ) : (
"Completing this step is a signed act and unblocks the next step once every one of its predecessors is complete."
        )
      }
      submitLabel="Sign & complete"
      reason="none"
      disabled={missingRequired.length > 0}
      extraFields={
        step.required_role_code ? (
          <div className="mb-3">
            <label className="hint" style={{ display: "block", marginBottom: 4 }}>
              Override reason{" "}
              <span className="text-muted">
                (only if you do not hold the {step.required_role_code} role recorded on the audit event;
                requires Supervisor/Admin)
              </span>
            </label>
            <textarea
              className="input"
              rows={2}
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
            />
          </div>
        ) : undefined
      }
      onSign={(payload) =>
        api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/complete`, {
          idempotency_key: payload.idempotency_key,
          batch_id: batch.batch_id,
          step_id: step.step_id,
          expected_version: step.version,
          override_reason: overrideReason.trim() || undefined,
          challenge_id: payload.challenge_id,
          reauth_password: payload.reauth_password,
        })
      }
    />
  );
}
