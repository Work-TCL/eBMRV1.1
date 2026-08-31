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
import { useApiResource, useMe } from "@/lib/hooks";
import { QmsDetailShell, useCommand } from "@/components/qms/QmsDetailShell";
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

// Document 106 has no signature policy row for these (SG-138), so the backend fails them closed. The UI
// still offers them — the resulting SIGNATURE_POLICY_UNRESOLVED is the honest, visible outcome.
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

export default function DeviationDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
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
            <IdFact label="Owner" value={data.owner_subject_id} />
            <IdFact label="Investigator" value={data.investigator_subject_id} />
            <IdFact label="Source record" value={data.source_id} />
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
              through the pipeline (DEV-FR-016).
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
        case "disposition":
          return api.post(`${path}/disposition`, {
            ...base,
            disposition_code: dispositionCode,
            disposition_rationale: rationale,
            capa_required: capaRequired,
            capa_rationale: capaRationale,
          });
        case "extend":
          return api.post(`${path}/extend`, {
            ...base,
            new_due_date: new Date(dueDate).toISOString(),
            reason,
            risk_review: riskReview,
          });
        case "close":
          return api.post(`${path}/close`, { ...base, conclusion });
        case "reopen":
          return api.post(`${path}/reopen`, { ...base, reason, new_evidence: newEvidence });
      }
    });
  }

  const signatureGated = SIGNATURE_GATED.includes(transition);

  return (
    <Modal
      open
      onClose={onClose}
      large={transition === "impact"}
      title={`${TRANSITION_LABEL[transition]} — ${deviation.deviation_number}`}
    >
      <form onSubmit={submit}>
        {signatureGated && (
          <Banner tone="warn" title="This transition requires an electronic signature">
            No Document 106 signature policy row exists yet for this action, so the backend will refuse it
            (SG-138). The error below is the platform failing closed, not a bug in this form.
          </Banner>
        )}

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
            <Field label="Investigator (user ID)" required>
              <Input value={investigator} onChange={(e) => setInvestigator(e.target.value)} required />
            </Field>
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

        {transition === "disposition" && (
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
              hint="Required either way — a decision not to raise a CAPA must also be justified."
            >
              <textarea
                className="input"
                rows={2}
                value={capaRationale}
                onChange={(e) => setCapaRationale(e.target.value)}
                required
              />
            </Field>
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

        {transition === "close" && (
          <Field label="Conclusion" required>
            <textarea
              className="input"
              rows={3}
              value={conclusion}
              onChange={(e) => setConclusion(e.target.value)}
              required
            />
          </Field>
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
