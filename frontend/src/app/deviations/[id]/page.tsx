"use client";

import { use, useState } from "react";
import {
  api,
  canApproveQms,
  canInvestigateQms,
  formatDate,
  formatDateTime,
  isOverdue,
  newIdempotencyKey,
  type Deviation,
} from "@/lib/api";
import { useApiResource, useEntityOptions, useMe, type EntityOption } from "@/lib/hooks";
import { QmsDetailShell, useCommand } from "@/components/qms/QmsDetailShell";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { Fact, IdFact } from "@/components/ui/FactGrid";
import { Tabs } from "@/components/ui/Tabs";
import { Card } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { HistoryPanel, JsonPanel } from "@/components/ui/JsonPanel";
import { BoolPill, SeverityPill } from "@/components/ui/StatePill";

interface ImpactLink {
  id: string;
  impacted_record_type: string;
  impacted_record_id: string;
  impacted_record_version: number | null;
  impact_category: string | null;
  hold_disposition_reference: string | null;
  created_at: string;
}

interface DeviationDetail extends Deviation {
  planned_scope: Record<string, unknown> | null;
  immediate_correction: Record<string, unknown> | null;
  containment: Record<string, unknown> | null;
  investigation_plan: Record<string, unknown> | null;
  cross_batch_ids: string[] | null;
  root_cause: Record<string, unknown> | null;
  impact_assessment: Record<string, unknown> | null;
  disposition_rationale: string | null;
  capa_rationale: string | null;
  change_control_rationale: string | null;
  training_rationale: string | null;
  extension_history: unknown[];
  closure_history: unknown[];
  reopen_history: unknown[];
  impact_links: ImpactLink[];
}

type Transition = "triage" | "contain" | "investigation" | "impact" | "disposition" | "extend" | "close" | "reopen";

// Which transitions the backend's state machine (app/modules/qms/commands.py) will accept from a state.
const ALLOWED_FROM: Record<string, Transition[]> = {
  OPEN: ["triage"],
  TRIAGE: ["contain", "investigation"],
  CONTAINMENT: ["investigation"],
  INVESTIGATION: ["investigation", "impact", "extend"],
  IMPACT_ASSESSMENT: ["impact", "disposition", "extend"],
  DISPOSITION: ["close"],
  CLOSED: ["reopen"],
  REOPENED: ["impact", "investigation"],
};

// Document 106 rows 71/73 (2026-09-09, resolved — signature policy seeded: `deviation_record`
// disposition/close, QA Releaser, independent of the record's own investigator_subject_id/
// owner_subject_id per Document 107 IND-005). The backend enforces the role+independence check itself
// (SOD_INDEPENDENCE_REQUIRED) before the password ceremony, so a QA Releaser who is also this record's
// owner or investigator is still correctly refused.
const SIGNATURE_GATED: Transition[] = ["disposition", "close"];

const TRANSITION_LABEL: Record<Transition, string> = {
  triage: "Triage",
  contain: "Record containment",
  investigation: "Investigation",
  impact: "Impact assessment",
  disposition: "Disposition",
  extend: "Extend due date",
  close: "Close",
  reopen: "Reopen",
};

const DISPOSITION_CODES = [
  "CONTINUE", "HOLD", "REJECT", "REWORK", "REPROCESS", "ADDITIONAL_TEST", "DESTROY", "FIELD_ACTION_ASSESSMENT",
];

// app/modules/qms/commands.py::IMPACT_CATEGORIES — all six must be answered before disposition.
const IMPACT_CATEGORIES = [
  ["quality_impact", "Quality impact"],
  ["patient_user_impact", "Patient / user impact"],
  ["released_distributed_product_impact", "Released / distributed product impact"],
  ["validation_impact", "Validation impact"],
  ["data_integrity_impact", "Data integrity impact"],
  ["regulatory_impact", "Regulatory impact"],
] as const;

// Which of useEntityOptions()'s lists a given source_type resolves against — same mapping the "Raise
// deviation" picker on the list page uses to build its dropdown, kept here so a plain id can be turned
// back into the record's human-readable label instead of showing the raw UUID.
function sourceOptionsFor(sourceType: string, entities: ReturnType<typeof useEntityOptions>): EntityOption[] | null {
  switch (sourceType) {
    case "batch":
      return entities.batches;
    case "qc":
      return entities.qcSamples;
    case "material":
      return entities.materialLots;
    case "equipment":
      return entities.equipment;
    case "supplier":
      return entities.suppliers;
    default:
      return null;
  }
}

function labelFor(id: string | null | undefined, options: EntityOption[] | null): string {
  if (!id) return "—";
  return options?.find((o) => o.value === id)?.label ?? id;
}

export default function DeviationDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const entities = useEntityOptions();
  const [pending, setPending] = useState<Transition | null>(null);
  const { data, loading, error, reload } = useApiResource<DeviationDetail>(`/qms/v1/deviations/${id}`);

  const allowed = data ? (ALLOWED_FROM[data.state] ?? []) : [];

  function canDo(t: Transition): boolean {
    if (!allowed.includes(t)) return false;
    if (t === "disposition" || t === "close" || t === "reopen") return canApproveQms(me);
    return canInvestigateQms(me);
  }

  return (
    <QmsDetailShell
      recordNumber={data?.deviation_number ?? ""}
      state={data?.state ?? ""}
      subtitle={data ? `${data.deviation_type} · source: ${data.source_type}` : undefined}
      backHref="/deviations"
      backLabel="Deviations"
      loading={loading}
      error={error}
      actions={(Object.keys(TRANSITION_LABEL) as Transition[])
        .filter(canDo)
        .map((t) => (
          <Button
            key={t}
            variant={t === "close" || t === "disposition" ? "primary" : "secondary"}
            onClick={() => setPending(t)}
          >
            {SIGNATURE_GATED.includes(t) && <Icon name="pen" />} {TRANSITION_LABEL[t]}
          </Button>
        ))}
      facts={
        data && (
          <>
            <Fact label="Severity">
              <SeverityPill severity={data.severity} />
            </Fact>
            <Fact label="Planned">{data.planned ? "Yes" : "No"}</Fact>
            <Fact label="Due date">
              <span className={isOverdue(data.due_date) && data.state !== "CLOSED" ? "error-text" : undefined}>
                {formatDate(data.due_date)}
              </span>
            </Fact>
            <Fact label="Disposition">{data.disposition_code ?? "—"}</Fact>
            <Fact label="CAPA required">
              <BoolPill value={data.capa_required} trueLabel="Required" falseLabel="Not required" />
            </Fact>
            <Fact label="Change control">
              <BoolPill value={data.change_control_required} trueLabel="Required" falseLabel="Not required" />
            </Fact>
            <Fact label="Training">
              <BoolPill value={data.training_required} trueLabel="Required" falseLabel="Not required" />
            </Fact>
            <Fact label="Raised">{formatDateTime(data.created_at)}</Fact>
            <Fact label="Closed">{data.closed_at ? formatDateTime(data.closed_at) : "—"}</Fact>
            <Fact label="Record version">{data.version}</Fact>
            <Fact label="Owner">{labelFor(data.owner_subject_id, entities.users)}</Fact>
            <Fact label="Investigator">{labelFor(data.investigator_subject_id, entities.users)}</Fact>
            <Fact label="Source record">
              {labelFor(data.source_id, sourceOptionsFor(data.source_type, entities))}
            </Fact>
            {/* Not a foreign key - a UUID generated for this deviation itself (Document 26's own
               "quality event" concept), so there's no separate record to resolve a label from. */}
            <IdFact label="Quality event" value={data.quality_event_id} />
          </>
        )
      }
    >
      {data && (
        <>
          {data.planned && data.planned_scope != null && (
            <Banner tone="warn" title="Planned deviation">
              This record has a declared end date. Once it passes, the deviation can no longer be advanced
              through the pipeline.
            </Banner>
          )}

          <Tabs
            tabs={[
              {
                id: "investigation",
                label: "Investigation",
                content: (
                  <Card pad>
                    <JsonPanel title="Planned scope" value={data.planned_scope} />
                    <JsonPanel title="Immediate correction" value={data.immediate_correction} />
                    <JsonPanel title="Containment" value={data.containment} />
                    <JsonPanel title="Investigation plan" value={data.investigation_plan} />
                    <JsonPanel title="Root cause" value={data.root_cause} />
                    <JsonPanel title="Cross-batch records" value={data.cross_batch_ids} />
                    {!data.containment && !data.investigation_plan && !data.root_cause && (
                      <EmptyState icon="help-circle">
                        No containment or investigation recorded yet.
                      </EmptyState>
                    )}
                  </Card>
                ),
              },
              {
                id: "impact",
                label: "Impact",
                badge: data.impact_links.length || undefined,
                content: (
                  <Card pad>
                    <JsonPanel title="Impact assessment" value={data.impact_assessment} />
                    <p className="fact-k mb-2">Impacted records</p>
                    {data.impact_links.length === 0 ? (
                      <EmptyState icon="layers">No impacted records linked.</EmptyState>
                    ) : (
                      <Table>
                        <thead>
                          <tr>
                            <th>Type</th>
                            <th>Record</th>
                            <th>Category</th>
                            <th>Hold / disposition ref</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.impact_links.map((link) => (
                            <tr key={link.id}>
                              <td>{link.impacted_record_type}</td>
                              <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>
                                {link.impacted_record_id}
                              </td>
                              <td>{link.impact_category ?? "—"}</td>
                              <td className="fs-2">{link.hold_disposition_reference ?? "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    )}
                  </Card>
                ),
              },
              {
                id: "disposition",
                label: "Disposition",
                content: (
                  <Card pad>
                    {data.disposition_code ? (
                      <>
                        <p className="mb-3">
                          <span className="fact-k">Code </span>
                          <span className="font-semibold">{data.disposition_code}</span>
                        </p>
                        <JsonPanel title="Rationale" value={data.disposition_rationale} />
                        <JsonPanel title="CAPA rationale" value={data.capa_rationale} />
                        <JsonPanel title="Change control rationale" value={data.change_control_rationale} />
                        <JsonPanel title="Training rationale" value={data.training_rationale} />
                      </>
                    ) : (
                      <EmptyState icon="help-circle">No disposition recorded yet.</EmptyState>
                    )}
                  </Card>
                ),
              },
              {
                id: "history",
                label: "History",
                content: (
                  <Card pad>
                    <HistoryPanel title="Extensions" entries={data.extension_history} />
                    <HistoryPanel title="Closures" entries={data.closure_history} />
                    <HistoryPanel title="Reopens" entries={data.reopen_history} />
                    {data.extension_history.length === 0 &&
                      data.closure_history.length === 0 &&
                      data.reopen_history.length === 0 && (
                        <EmptyState icon="history">No extensions, closures or reopens yet.</EmptyState>
                      )}
                  </Card>
                ),
              },
            ]}
          />

          {pending && (
            <TransitionModal
              deviation={data}
              transition={pending}
              onClose={() => setPending(null)}
              onDone={() => {
                setPending(null);
                reload();
              }}
            />
          )}
        </>
      )}
    </QmsDetailShell>
  );
}

function TransitionModal({
  deviation,
  transition,
  onClose,
  onDone,
}: {
  deviation: DeviationDetail;
  transition: Transition;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const entities = useEntityOptions();

  const [severity, setSeverity] = useState(deviation.severity);
  const [priority, setPriority] = useState("high");
  const [productImpact, setProductImpact] = useState("");
  const [correction, setCorrection] = useState("");
  const [containment, setContainment] = useState("");
  const [investigator, setInvestigator] = useState(deviation.investigator_subject_id ?? deviation.owner_subject_id);
  const [dueDate, setDueDate] = useState("");
  const [rootCauseMethod, setRootCauseMethod] = useState("5-why");
  const [rootCauseConclusion, setRootCauseConclusion] = useState("");
  const [impact, setImpact] = useState<Record<string, string>>({});
  const [dispositionCode, setDispositionCode] = useState(DISPOSITION_CODES[0]);
  const [rationale, setRationale] = useState("");
  const [capaRequired, setCapaRequired] = useState(false);
  const [capaRationale, setCapaRationale] = useState("");
  const [changeControlRequired, setChangeControlRequired] = useState(false);
  const [changeControlRationale, setChangeControlRationale] = useState("");
  const [trainingRequired, setTrainingRequired] = useState(false);
  const [trainingRationale, setTrainingRationale] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [reason, setReason] = useState("");
  const [riskReview, setRiskReview] = useState("");
  const [newEvidence, setNewEvidence] = useState("");

  const base = {
    idempotency_key: newIdempotencyKey(),
    deviation_id: deviation.id,
    expected_version: deviation.version,
  };

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const path = `/qms/v1/deviations/${deviation.id}`;
    run(() => {
      switch (transition) {
        case "triage":
          return api.post(`${path}/triage`, {
            ...base,
            severity,
            investigation_priority: priority,
            product_impact: productImpact || null,
          });
        case "contain":
          return api.post(`${path}/contain`, {
            ...base,
            immediate_correction: correction ? { description: correction } : null,
            containment: containment ? { description: containment } : null,
            reason: reason || null,
          });
        case "investigation":
          return api.post(`${path}/investigation`, {
            ...base,
            investigator_subject_id: investigator,
            due_date: dueDate ? new Date(dueDate).toISOString() : null,
            root_cause: rootCauseConclusion
              ? { method: rootCauseMethod, conclusion: rootCauseConclusion }
              : null,
            reason: reason || null,
          });
        case "impact":
          return api.post(`${path}/impact`, { ...base, impact_assessment: impact, reason: reason || null });
        case "extend":
          return api.post(`${path}/extend`, {
            ...base,
            new_due_date: new Date(dueDate).toISOString(),
            reason,
            risk_review: riskReview,
          });
        case "reopen":
          return api.post(`${path}/reopen`, { ...base, reason, new_evidence: newEvidence });
        default:
          // disposition/close are signature-gated and never reach this form -- see the early returns
          // below that render <SignatureCeremony> for them instead.
          throw new Error(`${transition} does not submit through the plain form`);
      }
    });
  }

  const path = `/qms/v1/deviations/${deviation.id}`;

  // Document 106 rows 71/73: disposition/close are signature-gated (SIGNATURE_GATED above) and
  // independence-checked by the backend against the record's own investigator/owner -- both go through
  // the shared Part 11 ceremony (challenge -> password re-entry -> signed mutation) instead of the plain
  // form the other transitions use below.
  if (transition === "disposition") {
    const dispositionDisabled =
      !rationale.trim() ||
      !capaRationale.trim() ||
      (changeControlRequired && !changeControlRationale.trim()) ||
      (trainingRequired && !trainingRationale.trim());
    return (
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        challengePath={`${path}/signature-challenges`}
        action="disposition"
        title={`Disposition - ${deviation.deviation_number}`}
        summary="Records the final disposition of this deviation. This is a released quality decision - signer must be independent of the record's investigator and owner."
        submitLabel="Sign & record disposition"
        disabled={dispositionDisabled}
        extraFields={
          <>
            <Field label="Disposition code" required>
              <Select value={dispositionCode} onChange={(e) => setDispositionCode(e.target.value)}>
                {DISPOSITION_CODES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Disposition rationale" required>
              <textarea
                className="input"
                rows={3}
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                required
              />
            </Field>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input type="checkbox" checked={capaRequired} onChange={(e) => setCapaRequired(e.target.checked)} />
              CAPA required
            </label>
            <Field
              label="CAPA rationale"
              required
              hint="Required either way - a decision not to raise a CAPA must also be justified."
            >
              <textarea
                className="input"
                rows={2}
                value={capaRationale}
                onChange={(e) => setCapaRationale(e.target.value)}
                required
              />
            </Field>

            <label className="flex items-center gap-2 fs-2 mb-3">
              <input
                type="checkbox"
                checked={changeControlRequired}
                onChange={(e) => setChangeControlRequired(e.target.checked)}
              />
              Change control required
            </label>
            {changeControlRequired && (
              <Field label="Change control rationale" required hint="What the change control needs to cover.">
                <textarea
                  className="input"
                  rows={2}
                  value={changeControlRationale}
                  onChange={(e) => setChangeControlRationale(e.target.value)}
                  required
                />
              </Field>
            )}

            <label className="flex items-center gap-2 fs-2 mb-3">
              <input
                type="checkbox"
                checked={trainingRequired}
                onChange={(e) => setTrainingRequired(e.target.checked)}
              />
              Training / qualification action required
            </label>
            {trainingRequired && (
              <Field label="Training rationale" required hint="Who needs to be retrained or requalified, and why.">
                <textarea
                  className="input"
                  rows={2}
                  value={trainingRationale}
                  onChange={(e) => setTrainingRationale(e.target.value)}
                  required
                />
              </Field>
            )}
          </>
        }
        onSign={(p) =>
          api.post(`${path}/disposition`, {
            idempotency_key: p.idempotency_key,
            deviation_id: deviation.id,
            expected_version: deviation.version,
            challenge_id: p.challenge_id,
            reauth_password: p.reauth_password,
            disposition_code: dispositionCode,
            disposition_rationale: rationale,
            capa_required: capaRequired,
            capa_rationale: capaRationale,
            change_control_required: changeControlRequired,
            change_control_rationale: changeControlRationale || null,
            training_required: trainingRequired,
            training_rationale: trainingRationale || null,
          })
        }
      />
    );
  }

  if (transition === "close") {
    return (
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        challengePath={`${path}/signature-challenges`}
        action="close"
        title={`Close - ${deviation.deviation_number}`}
        summary="Closes the deviation record permanently - signer must be independent of the record's investigator and owner."
        submitLabel="Sign & close"
        submitVariant="success"
        disabled={!conclusion.trim()}
        extraFields={
          <Field label="Conclusion" required>
            <textarea
              className="input"
              rows={3}
              value={conclusion}
              onChange={(e) => setConclusion(e.target.value)}
              required
            />
          </Field>
        }
        onSign={(p) =>
          api.post(`${path}/close`, {
            idempotency_key: p.idempotency_key,
            deviation_id: deviation.id,
            expected_version: deviation.version,
            challenge_id: p.challenge_id,
            reauth_password: p.reauth_password,
            conclusion,
          })
        }
      />
    );
  }

  return (
    <Modal
      open
      onClose={onClose}
      large={transition === "impact"}
      title={`${TRANSITION_LABEL[transition]} - ${deviation.deviation_number}`}
    >
      <form onSubmit={submit}>
        {transition === "triage" && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Severity" required>
                <Select value={severity} onChange={(e) => setSeverity(e.target.value)}>
                  <option value="critical">critical</option>
                  <option value="major">major</option>
                  <option value="minor">minor</option>
                </Select>
              </Field>
              <Field label="Investigation priority" required>
                <Select value={priority} onChange={(e) => setPriority(e.target.value)}>
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                </Select>
              </Field>
            </div>
            <Field label="Product impact" hint="Initial view; the full assessment comes later.">
              <Input value={productImpact} onChange={(e) => setProductImpact(e.target.value)} />
            </Field>
          </>
        )}

        {transition === "contain" && (
          <>
            <Field label="Immediate correction">
              <textarea
                className="input"
                rows={2}
                value={correction}
                onChange={(e) => setCorrection(e.target.value)}
              />
            </Field>
            <Field label="Containment" hint="What stops the problem spreading while it is investigated.">
              <textarea
                className="input"
                rows={2}
                value={containment}
                onChange={(e) => setContainment(e.target.value)}
              />
            </Field>
          </>
        )}

        {transition === "investigation" && (
          <>
            <EntityPickerField
              label="Investigator"
              required
              value={investigator}
              onChange={setInvestigator}
              options={entities.users}
              status={entities.usersStatus}
              kind="user"
            />
            <Field label="Due date" required hint="Required to open an investigation.">
              <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Root cause method">
                <Select value={rootCauseMethod} onChange={(e) => setRootCauseMethod(e.target.value)}>
                  <option value="5-why">5-why</option>
                  <option value="fishbone">fishbone</option>
                  <option value="fault-tree">fault-tree</option>
                  <option value="none">no assignable cause</option>
                </Select>
              </Field>
              <Field label="Conclusion" hint="Required before impact assessment.">
                <Input value={rootCauseConclusion} onChange={(e) => setRootCauseConclusion(e.target.value)} />
              </Field>
            </div>
          </>
        )}

        {transition === "impact" && (
          <>
            <p className="hint mb-3">
              All six categories must be answered before a disposition can be recorded.
            </p>
            {IMPACT_CATEGORIES.map(([key, label]) => (
              <Field key={key} label={label} required>
                <Input
                  value={impact[key] ?? ""}
                  onChange={(e) => setImpact((prev) => ({ ...prev, [key]: e.target.value }))}
                  placeholder="none / describe the impact"
                  required
                />
              </Field>
            ))}
          </>
        )}

        {transition === "extend" && (
          <>
            <Field label="New due date" required>
              <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
            </Field>
            <Field label="Reason" required>
              <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} required />
            </Field>
            <Field label="Risk review" required hint="The risk of the extension itself.">
              <textarea
                className="input"
                rows={2}
                value={riskReview}
                onChange={(e) => setRiskReview(e.target.value)}
                required
              />
            </Field>
          </>
        )}

        {transition === "reopen" && (
          <>
            <Field label="Reason" required>
              <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} required />
            </Field>
            <Field label="New evidence" required hint="A closed record reopens only on new evidence.">
              <textarea
                className="input"
                rows={2}
                value={newEvidence}
                onChange={(e) => setNewEvidence(e.target.value)}
                required
              />
            </Field>
          </>
        )}

        {(transition === "contain" || transition === "investigation" || transition === "impact") && (
          <Field label="Reason" hint="Optional. Recorded in the audit trail.">
            <Input value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
        )}

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Saving…" : TRANSITION_LABEL[transition]}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
