"use client";

// Dedicated Recipe Detail page — replaces the old VersionDetailModal. Shows the complete recipe graph
// (every step, parameter, material/equipment/QC/evidence requirement, dependency) with referenced
// entities resolved to human-readable names by the backend (recipe_master/router.py's
// get_version_detail), instead of the old modal's raw/truncated UUIDs.
import { use, useState } from "react";
import { api, ApiError, canAuthorRecipe, canReleaseRecipe, canSuspendRecipe, newIdempotencyKey } from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
import { RecordDetailShell, useCommand } from "@/components/shared/RecordDetailShell";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { Fact, IdFact } from "@/components/ui/FactGrid";
import { Tabs } from "@/components/ui/Tabs";
import { Card } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { BoolPill } from "@/components/ui/StatePill";
import {
  type RecipeVersion,
  type SectionDraft,
  RecipeGraphEditor,
  buildGraphPayload,
  sectionsFromVersion,
  totalStepCount,
  useRoleAndRuleOptions,
} from "../shared";

interface RecipeDiff {
  sections: { added: string[]; removed: string[]; changed: { code: string; changes: Record<string, { from: string; to: string }> }[] };
  steps: { added: string[]; removed: string[]; changed: { code: string; changes: Record<string, { from: string; to: string }> }[] };
}

export default function RecipeVersionDetailPage({ params }: { params: Promise<{ recipeVersionId: string }> }) {
  const { recipeVersionId } = use(params);
  const { me } = useMe();
  const version = useApiResource<RecipeVersion>(`/recipes/v2/versions/${recipeVersionId}`);
  const eligibility = useApiResource<{ eligible: boolean; checks: Record<string, unknown> }>(
    `/recipes/v2/versions/${recipeVersionId}/issue-eligibility`
  );
  const allVersions = useApiResource<RecipeVersion[]>(
    version.data ? `/recipes/v2/${version.data.recipe_family_id}/versions` : null
  );

  const [simResult, setSimResult] = useState<{ complete: boolean; findings: string[] } | undefined>(undefined);
  const [editOpen, setEditOpen] = useState(false);
  const [releaseSigOpen, setReleaseSigOpen] = useState(false);
  const [suspendSigOpen, setSuspendSigOpen] = useState(false);
  const [reinstateSigOpen, setReinstateSigOpen] = useState(false);
  const [obsoleteSigOpen, setObsoleteSigOpen] = useState(false);
  const [supersedeSigOpen, setSupersedeSigOpen] = useState(false);
  const [supersedingVersionId, setSupersedingVersionId] = useState("");

  const v = version.data;

  function reloadAll() {
    version.reload();
    eligibility.reload();
    allVersions.reload();
  }

  const validateCmd = useCommand(reloadAll);
  const submitCmd = useCommand(reloadAll);
  const [actionError, setActionError] = useState<string | null>(null);

  const simulate = async () => {
    setActionError(null);
    try {
      const result = await api.post<{ complete: boolean; findings: string[] }>(`/recipes/v2/drafts/${recipeVersionId}/simulate`);
      setSimResult(result);
    } catch (err) {
      setActionError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Simulation failed");
    }
  };

  const validate = () =>
    validateCmd.run(() =>
      api.post(`/recipes/v2/drafts/${recipeVersionId}/validate`, {
        idempotency_key: newIdempotencyKey(),
        recipe_version_id: recipeVersionId,
      })
    );

  const submit = () =>
    submitCmd.run(() =>
      api.post(`/recipes/v2/drafts/${recipeVersionId}/submit`, {
        idempotency_key: newIdempotencyKey(),
        recipe_version_id: recipeVersionId,
        expected_version: v!.version,
      })
    );

  const supersessionCandidates = (allVersions.data ?? []).filter(
    (candidate) =>
      candidate.recipe_version_id !== recipeVersionId &&
      candidate.recipe_family_id === v?.recipe_family_id &&
      candidate.lifecycle_state === "released"
  );

  return (
    <RecordDetailShell
      recordNumber={v ? `Recipe v${v.version_no}` : ""}
      state={v?.lifecycle_state}
      subtitle={v?.product_name ? `${v.product_name} (${v.product_code})` : undefined}
      backHref="/recipe-master"
      backLabel="Recipe Master"
      loading={version.loading}
      error={version.error}
      actions={
        v && (
          <>
            {canAuthorRecipe(me) && v.lifecycle_state === "draft" && (
              <>
                <Button variant="secondary" onClick={() => setEditOpen(true)}>
                  <Icon name="pen" /> Edit
                </Button>
                <Button variant="secondary" onClick={simulate}>
                  Simulate
                </Button>
                <Button variant="secondary" onClick={validate} disabled={validateCmd.busy}>
                  Validate
                </Button>
                <Button variant="primary" onClick={submit} disabled={submitCmd.busy}>
                  Submit for review
                </Button>
              </>
            )}
            {canReleaseRecipe(me) && v.lifecycle_state === "under_review" && (
              <Button variant="success" onClick={() => setReleaseSigOpen(true)}>
                Release
              </Button>
            )}
            {canSuspendRecipe(me) && v.lifecycle_state === "released" && (
              <>
                <Button variant="danger" onClick={() => setSuspendSigOpen(true)}>
                  Suspend
                </Button>
                <Button variant="secondary" onClick={() => setObsoleteSigOpen(true)}>
                  Obsolete
                </Button>
                <Button variant="secondary" onClick={() => setSupersedeSigOpen(true)}>
                  Supersede
                </Button>
              </>
            )}
            {canSuspendRecipe(me) && v.lifecycle_state === "suspended" && (
              <Button variant="primary" onClick={() => setReinstateSigOpen(true)}>
                Reinstate
              </Button>
            )}
          </>
        )
      }
      facts={
        v && (
          <>
            <Fact label="Product">{v.product_name ? `${v.product_name} (${v.product_code})` : v.product_version_id}</Fact>
            <Fact label="Site">{v.site_name ? `${v.site_name} (${v.site_code})` : v.site_id}</Fact>
            <Fact label="Batch size">
              {v.batch_size_value ? `${v.batch_size_value}${v.batch_size_uom ? ` ${v.batch_size_uom}` : ""}` : "—"}
            </Fact>
            <Fact label="Sections / Steps">
              {(v.sections?.length ?? 0)} / {(v.steps?.length ?? 0)}
            </Fact>
            {v.superseded_by_version_id && <IdFact label="Superseded by" value={v.superseded_by_version_id} />}
            <IdFact label="Released vault object" value={v.released_vault_object_id} />
            <Fact label="Version hash">
              <span className="tabular fs-2" style={{ wordBreak: "break-all" }}>
                {v.version_hash ?? "—"}
              </span>
            </Fact>
            <Fact label="Record version">{v.version}</Fact>
            {eligibility.data && (
              <Fact label="Issue eligibility">
                <BoolPill value={eligibility.data.eligible} trueLabel="Eligible" falseLabel="Not eligible" />
              </Fact>
            )}
          </>
        )
      }
    >
      {v && (
        <>
          {actionError && <p className="error-text mb-3">{actionError}</p>}
          {validateCmd.error && <p className="error-text mb-3">{validateCmd.error}</p>}
          {submitCmd.error && <p className="error-text mb-3">{submitCmd.error}</p>}
          {simResult && (
            <Card pad className="mb-3">
              <p className="fs-2 font-semibold mb-1">Simulation result</p>
              {simResult.complete ? (
                <p className="fs-2">Graph is complete — ready to submit/release.</p>
              ) : (
                <ul className="fs-2" style={{ paddingLeft: "1.2em" }}>
                  {simResult.findings.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              )}
            </Card>
          )}

          <Tabs
            tabs={[
              {
                id: "graph",
                label: "Steps & sections",
                badge: v.steps?.length || undefined,
                content: <RecipeGraphTree version={v} />,
              },
              {
                id: "materials",
                label: "Materials",
                badge: v.material_requirements?.length || undefined,
                content: <MaterialsTab version={v} />,
              },
              {
                id: "equipment",
                label: "Equipment",
                badge: v.equipment_requirements?.length || undefined,
                content: <EquipmentTab version={v} />,
              },
              {
                id: "qc",
                label: "QC requirements",
                badge: v.qc_requirements?.length || undefined,
                content: <QcTab version={v} />,
              },
              {
                id: "compare",
                label: "Compare & history",
                content: (
                  <CompareTab
                    recipeVersionId={recipeVersionId}
                    currentVersion={v}
                    allVersions={allVersions.data ?? []}
                  />
                ),
              },
            ]}
          />
        </>
      )}

      {editOpen && v && (
        <EditGraphModal
          version={v}
          onClose={() => setEditOpen(false)}
          onDone={() => {
            setEditOpen(false);
            reloadAll();
          }}
        />
      )}

      {v && releaseSigOpen && (
        <SignatureCeremony
          open
          onClose={() => setReleaseSigOpen(false)}
          onDone={() => {
            setReleaseSigOpen(false);
            reloadAll();
          }}
          challengePath={`/recipes/v2/drafts/${recipeVersionId}/signature-challenges`}
          action="release"
          submitVariant="success"
          submitLabel="Sign & release"
          title={`Release recipe - v${v.version_no}`}
          summary={
            <>
              This releases recipe version <strong>v{v.version_no}</strong> - once released its graph is
              locked; a change needs a new version. Signed by a QA Releaser who is <strong>not</strong>{" "}
              the recipe&apos;s author (author ≠ releaser).
            </>
          }
          onSign={(p) =>
            api.post(`/recipes/v2/drafts/${recipeVersionId}/release`, {
              idempotency_key: p.idempotency_key,
              recipe_version_id: recipeVersionId,
              expected_version: v.version,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
            })
          }
        />
      )}

      {v && suspendSigOpen && (
        <SignatureCeremony
          open
          onClose={() => setSuspendSigOpen(false)}
          onDone={() => {
            setSuspendSigOpen(false);
            reloadAll();
          }}
          challengePath={`/recipes/v2/drafts/${recipeVersionId}/signature-challenges`}
          action="suspend"
          submitVariant="danger"
          submitLabel="Sign & suspend"
          reason="required"
          title={`Suspend recipe - v${v.version_no}`}
          summary={
            <>
              This suspends recipe version <strong>v{v.version_no}</strong> - it can no longer be used to
              issue new batches until reinstated.
            </>
          }
          onSign={(p) =>
            api.post(`/recipes/v2/${recipeVersionId}/suspend`, {
              idempotency_key: p.idempotency_key,
              recipe_version_id: recipeVersionId,
              expected_version: v.version,
              reason: p.reason,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
            })
          }
        />
      )}

      {v && reinstateSigOpen && (
        <SignatureCeremony
          open
          onClose={() => setReinstateSigOpen(false)}
          onDone={() => {
            setReinstateSigOpen(false);
            reloadAll();
          }}
          challengePath={`/recipes/v2/drafts/${recipeVersionId}/signature-challenges`}
          action="reinstate"
          submitVariant="primary"
          submitLabel="Sign & reinstate"
          reason="required"
          title={`Reinstate recipe - v${v.version_no}`}
          summary={
            <>
              This reinstates recipe version <strong>v{v.version_no}</strong> back to released. Must be
              signed by someone other than whoever suspended it.
            </>
          }
          onSign={(p) =>
            api.post(`/recipes/v2/${recipeVersionId}/reinstate`, {
              idempotency_key: p.idempotency_key,
              recipe_version_id: recipeVersionId,
              expected_version: v.version,
              reason: p.reason,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
            })
          }
        />
      )}

      {v && obsoleteSigOpen && (
        <SignatureCeremony
          open
          onClose={() => setObsoleteSigOpen(false)}
          onDone={() => {
            setObsoleteSigOpen(false);
            reloadAll();
          }}
          challengePath={`/recipes/v2/drafts/${recipeVersionId}/signature-challenges`}
          action="obsolete"
          submitVariant="danger"
          submitLabel="Sign & obsolete"
          reason="required"
          title={`Obsolete recipe - v${v.version_no}`}
          summary={
            <>
              This retires recipe version <strong>v{v.version_no}</strong> permanently - obsolete is a
              terminal state with no further transitions.
            </>
          }
          onSign={(p) =>
            api.post(`/recipes/v2/${recipeVersionId}/obsolete`, {
              idempotency_key: p.idempotency_key,
              recipe_version_id: recipeVersionId,
              expected_version: v.version,
              reason: p.reason,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
            })
          }
        />
      )}

      {v && supersedeSigOpen && (
        <SignatureCeremony
          open
          onClose={() => setSupersedeSigOpen(false)}
          onDone={() => {
            setSupersedeSigOpen(false);
            setSupersedingVersionId("");
            reloadAll();
          }}
          challengePath={`/recipes/v2/drafts/${recipeVersionId}/signature-challenges`}
          action="supersede"
          submitVariant="danger"
          submitLabel="Sign & supersede"
          reason="required"
          disabled={!supersedingVersionId}
          title={`Supersede recipe - v${v.version_no}`}
          summary={
            <>
              This marks recipe version <strong>v{v.version_no}</strong> as superseded by the released
              version chosen below - terminal, no further transitions.
            </>
          }
          extraFields={
            <Field label="Superseded by" required>
              <Select value={supersedingVersionId} onChange={(e) => setSupersedingVersionId(e.target.value)}>
                <option value="">Select a released version…</option>
                {supersessionCandidates.map((candidate) => (
                  <option key={candidate.recipe_version_id} value={candidate.recipe_version_id}>
                    v{candidate.version_no}
                  </option>
                ))}
              </Select>
              {supersessionCandidates.length === 0 && (
                <p className="hint mt-1">No other released version of this recipe family exists yet.</p>
              )}
            </Field>
          }
          onSign={(p) =>
            api.post(`/recipes/v2/${recipeVersionId}/supersede`, {
              idempotency_key: p.idempotency_key,
              recipe_version_id: recipeVersionId,
              expected_version: v.version,
              reason: p.reason,
              superseding_version_id: supersedingVersionId,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
            })
          }
        />
      )}
    </RecordDetailShell>
  );
}

/** Read-only tree: Section (collapsible) -> its Steps, each showing type/role/critical/dependencies/
 * parameters/materials/equipment/evidence/QC inline, with referenced material/equipment/QC names
 * resolved by the backend instead of shown as raw UUIDs. */
function RecipeGraphTree({ version }: { version: RecipeVersion }) {
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const sections = version.sections ?? [];
  const steps = version.steps ?? [];
  const dependencies = version.dependencies ?? [];
  const parameters = version.parameters ?? [];
  const materialReqs = version.material_requirements ?? [];
  const evidenceReqs = version.evidence_requirements ?? [];
  const equipmentReqs = version.equipment_requirements ?? [];
  const qcReqs = version.qc_requirements ?? [];

  function toggle(id: string) {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (sections.length === 0) {
    return <EmptyState icon="database">No sections declared.</EmptyState>;
  }

  return (
    <div>
      {[...sections]
        .sort((a, b) => a.sequence - b.sequence)
        .map((sec) => {
          const isOpen = !collapsedSections.has(sec.id);
          const stepsInSection = steps.filter((s) => s.section_id === sec.id).sort((a, b) => a.sequence_hint - b.sequence_hint);
          return (
            <div key={sec.id} style={{ border: "1px solid var(--border-hairline, #ddd)", borderRadius: 8, marginBottom: 8 }}>
              <button
                type="button"
                onClick={() => toggle(sec.id)}
                aria-label={isOpen ? "Collapse section" : "Expand section"}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  width: "100%",
                  background: "var(--surface-sunken, #f6f6f6)",
                  border: "none",
                  borderRadius: isOpen ? "8px 8px 0 0" : 8,
                  padding: "8px 10px",
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <Icon name={isOpen ? "chevron-down" : "chevron-right"} />
                <span className="tabular font-semibold">{sec.stable_section_code}</span>
                <span className="fs-2 text-muted">{sec.name}</span>
                {sec.parallel_group && <span className="fs-2 text-muted">parallel group: {sec.parallel_group}</span>}
                {sec.expected_duration_minutes != null && (
                  <span className="fs-2 text-muted">~{sec.expected_duration_minutes} min</span>
                )}
                <span className="fs-2 text-muted" style={{ marginLeft: "auto" }}>
                  {stepsInSection.length} step{stepsInSection.length === 1 ? "" : "s"}
                </span>
              </button>
              {isOpen && (
                <div style={{ padding: "4px 10px 8px" }}>
                  {stepsInSection.length === 0 ? (
                    <p className="hint" style={{ padding: "6px 0" }}>
                      No steps in this section.
                    </p>
                  ) : (
                    stepsInSection.map((s) => {
                      const preds = dependencies
                        .filter((d) => d.successor_step_id === s.id)
                        .map((d) => ({
                          code: steps.find((x) => x.id === d.predecessor_step_id)?.stable_step_code ?? d.predecessor_step_id.slice(0, 8),
                          rule: d.condition_rule_id,
                        }));
                      const stepParams = parameters.filter((p) => p.step_id === s.id);
                      const stepMaterials = materialReqs.filter((m) => m.step_id === s.id);
                      const stepEvidence = evidenceReqs.filter((e) => e.step_id === s.id);
                      const stepEquipment = equipmentReqs.filter((e) => e.step_id === s.id);
                      const stepQc = qcReqs.filter((q) => q.step_id === s.id);
                      return (
                        <div key={s.id} style={{ padding: "6px 2px", borderTop: "1px solid var(--border-hairline, #eee)" }}>
                          <div className="flex flex-wrap items-center gap-3 fs-2">
                            <span className="tabular font-semibold" style={{ minWidth: 110 }}>
                              {s.stable_step_code}
                            </span>
                            <span style={{ minWidth: 110 }}>{s.step_type}</span>
                            <span style={{ minWidth: 140 }}>
                              {s.required_role_code ?? <span className="text-muted">any role</span>}
                            </span>
                            {s.required_qualification_code && <span>qual: {s.required_qualification_code}</span>}
                            {s.is_critical && <span className="error-text">Critical</span>}
                            {preds.length > 0 && (
                              <span className="text-muted">
                                Depends on: {preds.map((p) => (p.rule ? `${p.code} (if ${p.rule})` : p.code)).join(", ")}
                              </span>
                            )}
                          </div>
                          {s.instruction_text && (
                            <div className="fs-2" style={{ paddingLeft: 118, paddingTop: 2 }}>
                              {s.instruction_text}
                            </div>
                          )}
                          {stepParams.length > 0 && (
                            <div className="fs-2 text-muted" style={{ paddingLeft: 118, paddingTop: 2 }}>
                              Parameters:{" "}
                              {stepParams
                                .map((p) => {
                                  const range =
                                    p.target_value != null
                                      ? `target ${p.target_value}${p.uom ? ` ${p.uom}` : ""}`
                                      : p.min_value != null || p.max_value != null
                                        ? `${p.min_value ?? "—"}–${p.max_value ?? "—"}${p.uom ? ` ${p.uom}` : ""}`
                                        : null;
                                  return `${p.parameter_code} (${p.data_type}${range ? `, ${range}` : ""})`;
                                })
                                .join(", ")}
                            </div>
                          )}
                          {stepMaterials.length > 0 && (
                            <div className="fs-2 text-muted" style={{ paddingLeft: 118, paddingTop: 2 }}>
                              Materials:{" "}
                              {stepMaterials
                                .map((m) => {
                                  const range =
                                    m.target_value != null
                                      ? `target ${m.target_value}${m.uom ? ` ${m.uom}` : ""}`
                                      : m.min_value != null || m.max_value != null
                                        ? `${m.min_value ?? "—"}–${m.max_value ?? "—"}${m.uom ? ` ${m.uom}` : ""}`
                                        : null;
                                  const label = m.material_name
                                    ? `${m.material_name} (${m.material_spec_business_id})`
                                    : `${m.material_spec_version_id.slice(0, 8)}…`;
                                  return `${label}${range ? ` (${range})` : ""}`;
                                })
                                .join(", ")}
                            </div>
                          )}
                          {stepEquipment.length > 0 && (
                            <div className="fs-2 text-muted" style={{ paddingLeft: 118, paddingTop: 2 }}>
                              Equipment: {stepEquipment.map((e) => e.equipment_class_name ?? e.equipment_class).join(", ")}
                            </div>
                          )}
                          {stepEvidence.length > 0 && (
                            <div className="fs-2 text-muted" style={{ paddingLeft: 118, paddingTop: 2 }}>
                              Evidence:{" "}
                              {stepEvidence.map((e) => `${e.evidence_type} (x${e.required_count})`).join(", ")}
                            </div>
                          )}
                          {stepQc.length > 0 && (
                            <div className="fs-2 text-muted" style={{ paddingLeft: 118, paddingTop: 2 }}>
                              QC:{" "}
                              {stepQc
                                .map((q) => (q.spec_code ? `${q.spec_code} v${q.spec_version_no}` : q.qc_test_specification_id.slice(0, 8)))
                                .join(", ")}
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          );
        })}
    </div>
  );
}

function stepCodeFor(version: RecipeVersion, stepId: string): string {
  return version.steps?.find((s) => s.id === stepId)?.stable_step_code ?? stepId.slice(0, 8);
}

/** Batch-wide materials table — one row per requirement across every step, with a Step column. A
 * detail page can offer this cross-step view; the old modal's per-step-only tree couldn't. */
function MaterialsTab({ version }: { version: RecipeVersion }) {
  const reqs = version.material_requirements ?? [];
  if (reqs.length === 0) return <EmptyState icon="database">No material requirements declared.</EmptyState>;
  return (
    <Table>
      <thead>
        <tr>
          <th>Step</th>
          <th>Material</th>
          <th>Target / range</th>
          <th>UOM</th>
          <th>Consume mode</th>
          <th>Substitution</th>
          <th>Genealogy</th>
        </tr>
      </thead>
      <tbody>
        {reqs.map((m) => (
          <tr key={m.id}>
            <td className="tabular fs-2">{stepCodeFor(version, m.step_id)}</td>
            <td className="fs-2">
              {m.material_name ? `${m.material_name} (${m.material_spec_business_id})` : m.material_spec_version_id}
            </td>
            <td className="tabular fs-2">
              {m.target_value != null ? `target ${m.target_value}` : m.min_value != null || m.max_value != null ? `${m.min_value ?? "—"}–${m.max_value ?? "—"}` : "—"}
            </td>
            <td className="fs-2">{m.uom ?? "—"}</td>
            <td className="fs-2">{m.consume_mode ?? "—"}</td>
            <td className="fs-2">
              <BoolPill value={m.substitution_allowed} trueLabel="Allowed" falseLabel="Not allowed" />
            </td>
            <td className="fs-2">
              <BoolPill value={m.genealogy_required} trueLabel="Required" falseLabel="Not required" />
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function EquipmentTab({ version }: { version: RecipeVersion }) {
  const reqs = version.equipment_requirements ?? [];
  if (reqs.length === 0) return <EmptyState icon="database">No equipment requirements declared.</EmptyState>;
  return (
    <Table>
      <thead>
        <tr>
          <th>Step</th>
          <th>Equipment class</th>
          <th>Exact equipment optional</th>
          <th>Calibration</th>
          <th>Qualification</th>
          <th>Cleaning</th>
        </tr>
      </thead>
      <tbody>
        {reqs.map((e) => (
          <tr key={e.id}>
            <td className="tabular fs-2">{stepCodeFor(version, e.step_id)}</td>
            <td className="fs-2">{e.equipment_class_name ?? e.equipment_class}</td>
            <td className="fs-2">
              <BoolPill value={e.exact_equipment_optional} trueLabel="Optional" falseLabel="Exact required" />
            </td>
            <td className="fs-2">
              <BoolPill value={e.require_current_calibration} trueLabel="Required" falseLabel="Not required" />
            </td>
            <td className="fs-2">
              <BoolPill value={e.require_current_qualification} trueLabel="Required" falseLabel="Not required" />
            </td>
            <td className="fs-2">
              <BoolPill value={e.require_current_cleaning} trueLabel="Required" falseLabel="Not required" />
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

/** QC requirements were fetched by the old modal but never rendered anywhere — new tab. */
function QcTab({ version }: { version: RecipeVersion }) {
  const reqs = version.qc_requirements ?? [];
  if (reqs.length === 0) return <EmptyState icon="database">No in-process QC requirements declared.</EmptyState>;
  return (
    <Table>
      <thead>
        <tr>
          <th>Step</th>
          <th>QC specification</th>
          <th>Required</th>
        </tr>
      </thead>
      <tbody>
        {reqs.map((q) => (
          <tr key={q.id}>
            <td className="tabular fs-2">{stepCodeFor(version, q.step_id)}</td>
            <td className="fs-2">{q.spec_code ? `${q.spec_code} v${q.spec_version_no}` : q.qc_test_specification_id}</td>
            <td className="fs-2">
              <BoolPill value={q.required} trueLabel="Required" falseLabel="Optional" />
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function CompareTab({
  recipeVersionId,
  currentVersion,
  allVersions,
}: {
  recipeVersionId: string;
  currentVersion: RecipeVersion;
  allVersions: RecipeVersion[];
}) {
  const [compareTo, setCompareTo] = useState("");
  const [diff, setDiff] = useState<RecipeDiff | null>(null);
  const [diffError, setDiffError] = useState<string | null>(null);

  async function runCompare() {
    if (!compareTo) return;
    setDiffError(null);
    setDiff(null);
    try {
      setDiff(await api.get<RecipeDiff>(`/recipes/v2/versions/${recipeVersionId}/compare/${compareTo}`));
    } catch (err) {
      setDiffError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Compare failed");
    }
  }

  return (
    <Card pad>
      <p className="fs-1 text-muted mb-1">Compare with another version</p>
      <div className="flex flex-wrap items-end gap-3">
        <Select value={compareTo} onChange={(e) => setCompareTo(e.target.value)} style={{ minWidth: 200, maxWidth: 220, width: "100%" }}>
          <option value="">- pick a version -</option>
          {allVersions
            .filter((cv) => cv.recipe_version_id !== recipeVersionId && cv.recipe_family_id === currentVersion.recipe_family_id)
            .map((cv) => (
              <option key={cv.recipe_version_id} value={cv.recipe_version_id}>
                v{cv.version_no} ({cv.lifecycle_state})
              </option>
            ))}
        </Select>
        <Button size="sm" variant="secondary" onClick={runCompare} disabled={!compareTo}>
          Compare
        </Button>
      </div>
      {diffError && <p className="error-text fs-2 mt-2">{diffError}</p>}
      {diff && (
        <div className="mt-3">
          {(["sections", "steps"] as const).map((kind) => {
            const d = diff[kind];
            const empty = d.added.length === 0 && d.removed.length === 0 && d.changed.length === 0;
            return (
              <div key={kind} className="mb-3">
                <p className="fs-2 font-semibold" style={{ textTransform: "capitalize" }}>
                  {kind}
                </p>
                {empty ? (
                  <p className="fs-2 text-muted">No differences.</p>
                ) : (
                  <ul className="fs-2" style={{ paddingLeft: "1.2em" }}>
                    {d.added.map((c) => (
                      <li key={`a-${c}`}>
                        <span className="tabular">{c}</span> - added
                      </li>
                    ))}
                    {d.removed.map((c) => (
                      <li key={`r-${c}`}>
                        <span className="tabular">{c}</span> - removed
                      </li>
                    ))}
                    {d.changed.map((c) => (
                      <li key={`c-${c.code}`}>
                        <span className="tabular">{c.code}</span> -{" "}
                        {Object.entries(c.changes)
                          .map(([f, { from, to }]) => `${f}: ${from} → ${to}`)
                          .join("; ")}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

/** Edits an existing draft's whole graph via the same nested block used to create one
 * (`PUT /recipes/v2/drafts/{id}` — full replace, draft state only, code-verified
 * `recipe_master/commands.py::update_draft`). Pre-filled from the version's current sections/steps/
 * dependencies via `sectionsFromVersion`. */
function EditGraphModal({
  version,
  onClose,
  onDone,
}: {
  version: RecipeVersion;
  onClose: () => void;
  onDone: () => void;
}) {
  const [sections, setSections] = useState<SectionDraft[]>(() => sectionsFromVersion(version));
  const [batchSizeValue, setBatchSizeValue] = useState(version.batch_size_value ?? "");
  const [batchSizeUom, setBatchSizeUom] = useState(version.batch_size_uom ?? "");
  const { roleOptions, ruleOptions, materialSpecOptions, qualificationCodeOptions, uomOptions, equipmentClassOptions, qcSpecOptions } = useRoleAndRuleOptions();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const graph = buildGraphPayload(sections);
      await api.put(`/recipes/v2/drafts/${version.recipe_version_id}`, {
        idempotency_key: newIdempotencyKey(),
        recipe_version_id: version.recipe_version_id,
        expected_version: version.version,
        ...(batchSizeValue ? { batch_size_value: batchSizeValue } : {}),
        ...(batchSizeUom ? { batch_size_uom: batchSizeUom } : {}),
        ...graph,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to save changes");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={`Edit draft - v${version.version_no}`} large>
      <form onSubmit={onSubmit}>
        <p className="hint mb-3">
          Product, recipe code, version and site are fixed once a draft exists - sections, steps and
          dependencies can still change while it stays a draft.
        </p>
        {error && <p className="error-text mb-2">{error}</p>}

        <div className="grid grid-cols-3 gap-4 mb-3">
          <Field label="Batch size (optional)">
            <Input value={batchSizeValue} onChange={(e) => setBatchSizeValue(e.target.value)} />
          </Field>
          <Field label="Batch size UOM (optional)">
            <Input list="dl-uom-batch-size" value={batchSizeUom} onChange={(e) => setBatchSizeUom(e.target.value)} />
            <datalist id="dl-uom-batch-size">
              {uomOptions.map((code) => (
                <option key={code} value={code} />
              ))}
            </datalist>
          </Field>
        </div>

        <RecipeGraphEditor sections={sections} onChange={setSections} roleOptions={roleOptions} ruleOptions={ruleOptions} materialSpecOptions={materialSpecOptions} qualificationCodeOptions={qualificationCodeOptions} uomOptions={uomOptions} equipmentClassOptions={equipmentClassOptions} qcSpecOptions={qcSpecOptions} />

        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || sections.length === 0 || totalStepCount(sections) === 0}>
            {busy ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
