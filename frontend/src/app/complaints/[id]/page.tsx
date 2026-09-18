"use client";

import { use, useState } from "react";
import {
  api,
  hasPermission,
  formatDate,
  formatDateTime,
  isOverdue,
  newIdempotencyKey,
  type Complaint,
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
import { JsonPanel } from "@/components/ui/JsonPanel";
import { BoolPill } from "@/components/ui/StatePill";

interface ReportabilityAssessment {
  id: string;
  applicable_regimes: string[];
  assessment_inputs: Record<string, unknown> | null;
  rationale: string;
  trigger_date: string | null;
  due_date: string | null;
  reviewer_subject_id: string;
  submission_reference: string | null;
  submission_status: string | null;
  capa_required: boolean;
  field_action_required: boolean;
  created_at: string;
}

interface Communication {
  id: string;
  direction: string;
  communication_type: string;
  recipient: string | null;
  channel: string | null;
  occurred_at: string;
  message: string;
  reference: string | null;
}

interface ComplaintDetail extends Complaint {
  lot_batch_serial_refs: Record<string, unknown> | null;
  complainant_info: Record<string, unknown> | null;
  triage: Record<string, unknown> | null;
  no_investigation_reason: string | null;
  investigation_findings: Record<string, unknown> | null;
  related_complaint_ids: string[] | null;
  reportability_assessments: ReportabilityAssessment[];
  communications: Communication[];
}

type Transition = "triage" | "investigation_decision" | "investigation" | "reportability" | "response" | "close";

const ALLOWED_FROM: Record<string, Transition[]> = {
  RECEIVED: ["triage"],
  TRIAGE: ["triage", "investigation_decision"],
  INVESTIGATION: ["investigation", "reportability"],
  NO_INVESTIGATION_JUSTIFIED: ["reportability"],
  REPORTABILITY_ASSESSMENT: ["reportability", "response"],
  RESPONSE: ["response", "close"],
  CLOSED: [],
};

// SG-138: no Document 106 policy rows for complaint_record reportability/close.
const SIGNATURE_GATED: Transition[] = ["reportability", "close"];

const LABEL: Record<Transition, string> = {
  triage: "Triage",
  investigation_decision: "Investigation decision",
  investigation: "Record investigation",
  reportability: "Reportability assessment",
  response: "Record communication",
  close: "Close",
};

// The exact permission code app/modules/qms/complaint_router.py checks for each transition.
const PERMISSION_FOR_TRANSITION: Record<Transition, string> = {
  triage: "complaint.triage",
  investigation_decision: "complaint.investigation_decision",
  investigation: "complaint.investigate",
  reportability: "complaint.reportability",
  response: "complaint.response",
  close: "complaint.close",
};

const REGIMES = ["FDA_MDR", "FDA_FAR", "EU_MDR_VIGILANCE", "HEALTH_CANADA", "NONE"];
// app/modules/qms/complaint_models.py CONSTITUENT_CLASSIFICATIONS.
const CONSTITUENT_CLASSIFICATIONS = [
  "drug", "device", "interface", "combination", "packaging", "label", "usability", "unknown",
];

export default function ComplaintDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const [pending, setPending] = useState<Transition | null>(null);
  const { data, loading, error, reload } = useApiResource<ComplaintDetail>(`/qms/v1/complaints/${id}`);

  const allowed = data ? (ALLOWED_FROM[data.state] ?? []) : [];
  const canDo = (t: Transition) => allowed.includes(t) && hasPermission(me, PERMISSION_FOR_TRANSITION[t]);

  const latestAssessment = data?.reportability_assessments.at(-1);

  return (
    <QmsDetailShell
      recordNumber={data?.complaint_number ?? ""}
      state={data?.state ?? ""}
      subtitle={data ? `${data.nature_code} · received via ${data.source_channel}` : undefined}
      backHref="/complaints"
      backLabel="Complaints"
      loading={loading}
      error={error}
      actions={(Object.keys(LABEL) as Transition[]).filter(canDo).map((t) => (
        <Button key={t} variant={t === "close" ? "primary" : "secondary"} onClick={() => setPending(t)}>
          {SIGNATURE_GATED.includes(t) && <Icon name="pen" />} {LABEL[t]}
        </Button>
      ))}
      facts={
        data && (
          <>
            <Fact label="Received">{formatDate(data.received_at)}</Fact>
            <Fact label="Nature">{data.nature_code}</Fact>
            <Fact label="Channel">{data.source_channel}</Fact>
            <Fact label="Investigation">
              <BoolPill value={data.investigation_required} trueLabel="Required" falseLabel="Justified none" />
            </Fact>
            <Fact label="Possible duplicate">{data.is_potential_duplicate ? "Yes" : "No"}</Fact>
            <Fact label="Constituent class">{data.constituent_classification ?? "—"}</Fact>
            <Fact label="Communications">{data.communications.length}</Fact>
            <Fact label="Logged">{formatDateTime(data.created_at)}</Fact>
            <Fact label="Closed">{data.closed_at ? formatDateTime(data.closed_at) : "—"}</Fact>
            <Fact label="Record version">{data.version}</Fact>
            <IdFact label="Product version" value={data.product_ref} />
            <IdFact label="Quality event" value={data.quality_event_id} />
          </>
        )
      }
    >
      {data && (
        <>
          {latestAssessment?.due_date && isOverdue(latestAssessment.due_date) && !latestAssessment.submission_reference && (
            <Banner tone="critical" title="Regulatory submission overdue">
              Reportability was assessed as {latestAssessment.applicable_regimes.join(", ")} with a due date of{" "}
              {formatDate(latestAssessment.due_date)}, and no submission reference has been recorded.
            </Banner>
          )}

          <Card pad className="mb-4">
            <p className="fact-k mb-2">Complaint as reported</p>
            <p>{data.description}</p>
          </Card>

          <Tabs
            tabs={[
              {
                id: "investigation",
                label: "Investigation",
                content: (
                  <Card pad>
                    <JsonPanel title="Triage" value={data.triage} />
                    <JsonPanel title="Complainant" value={data.complainant_info} />
                    <JsonPanel title="Lot / batch / serial" value={data.lot_batch_serial_refs} />
                    <JsonPanel title="Investigation findings" value={data.investigation_findings} />
                    <JsonPanel title="Conclusion" value={data.investigation_conclusion} />
                    <JsonPanel title="No-investigation justification" value={data.no_investigation_reason} />
                    <JsonPanel title="Related complaints" value={data.related_complaint_ids} />
                  </Card>
                ),
              },
              {
                id: "reportability",
                label: "Reportability",
                badge: data.reportability_assessments.length || undefined,
                content: <ReportabilityTab assessments={data.reportability_assessments} />,
              },
              {
                id: "communications",
                label: "Communications",
                badge: data.communications.length || undefined,
                content: <CommunicationsTab communications={data.communications} />,
              },
            ]}
          />

          {pending && (
            <TransitionModal
              complaint={data}
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

function ReportabilityTab({ assessments }: { assessments: ReportabilityAssessment[] }) {
  if (assessments.length === 0) {
    return <EmptyState icon="shield-check">No reportability assessment recorded yet.</EmptyState>;
  }
  return (
    <div>
      {assessments.map((a) => (
        <Card key={a.id} pad className="mb-3">
          <div className="flex justify-between items-center mb-2">
            <span className="font-semibold">{a.applicable_regimes.join(", ") || "No applicable regime"}</span>
            <span className="fs-2 text-muted">{formatDate(a.created_at)}</span>
          </div>
          <p className="fs-2 mb-3">{a.rationale}</p>
          <div className="fs-2">
            <p>
              <span className="text-muted">Trigger date: </span>
              {formatDate(a.trigger_date)}
              <span className="text-muted"> · Due: </span>
              <span className={isOverdue(a.due_date) && !a.submission_reference ? "error-text" : undefined}>
                {formatDate(a.due_date)}
              </span>
            </p>
            <p>
              <span className="text-muted">Submission: </span>
              {a.submission_reference ?? "Not submitted"}
              {a.submission_status && <span className="text-muted"> ({a.submission_status})</span>}
            </p>
            <p className="flex gap-3 mt-2">
              <span>
                CAPA <BoolPill value={a.capa_required} trueLabel="Required" falseLabel="Not required" />
              </span>
              <span>
                Field action{" "}
                <BoolPill value={a.field_action_required} trueLabel="Required" falseLabel="Not required" />
              </span>
            </p>
          </div>
          <JsonPanel title="Assessment inputs" value={a.assessment_inputs} />
        </Card>
      ))}
    </div>
  );
}

function CommunicationsTab({ communications }: { communications: Communication[] }) {
  if (communications.length === 0) {
    return <EmptyState icon="bell">No communications recorded.</EmptyState>;
  }
  return (
    <Card>
      <Table>
        <thead>
          <tr>
            <th>When</th>
            <th>Direction</th>
            <th>Type</th>
            <th>Recipient</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {communications.map((c) => (
            <tr key={c.id}>
              <td className="tabular fs-2">{formatDateTime(c.occurred_at)}</td>
              <td className="fs-2">{c.direction}</td>
              <td className="fs-2">{c.communication_type}</td>
              <td className="fs-2">{c.recipient ?? "—"}</td>
              <td>{c.message}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}

function TransitionModal({
  complaint,
  transition,
  onClose,
  onDone,
}: {
  complaint: ComplaintDetail;
  transition: Transition;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);

  const [severity, setSeverity] = useState("major");
  const [injuryReported, setInjuryReported] = useState(false);
  const [constituentClass, setConstituentClass] = useState(complaint.constituent_classification ?? "");
  const [investigationRequired, setInvestigationRequired] = useState(true);
  const [noInvestigationReason, setNoInvestigationReason] = useState("");
  const [findings, setFindings] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [regimes, setRegimes] = useState<string[]>([]);
  const [rationale, setRationale] = useState("");
  const [triggerDate, setTriggerDate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [capaRequired, setCapaRequired] = useState(false);
  const [fieldActionRequired, setFieldActionRequired] = useState(false);
  const [direction, setDirection] = useState("outbound");
  const [communicationType, setCommunicationType] = useState("acknowledgment");
  const [message, setMessage] = useState("");
  const [recipient, setRecipient] = useState("");
  const [closeConclusion, setCloseConclusion] = useState("");
  const [reason, setReason] = useState("");

  const base = {
    idempotency_key: newIdempotencyKey(),
    complaint_id: complaint.id,
    expected_version: complaint.version,
  };
  const path = `/qms/v1/complaints/${complaint.id}`;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() => {
      switch (transition) {
        case "triage":
          return api.post(`${path}/triage`, {
            ...base,
            triage: { severity, injury_reported: injuryReported },
            constituent_classification: constituentClass || null,
            reason: reason || null,
          });
        case "investigation_decision":
          return api.post(`${path}/investigation-decision`, {
            ...base,
            investigation_required: investigationRequired,
            no_investigation_reason: investigationRequired ? null : noInvestigationReason,
          });
        case "investigation":
          return api.post(`${path}/investigation`, {
            ...base,
            findings: { description: findings },
            conclusion,
            reason: reason || null,
          });
        case "reportability":
          return api.post(`${path}/reportability`, {
            ...base,
            applicable_regimes: regimes,
            rationale,
            trigger_date: triggerDate ? new Date(triggerDate).toISOString() : null,
            due_date: dueDate ? new Date(dueDate).toISOString() : null,
            capa_required: capaRequired,
            field_action_required: fieldActionRequired,
          });
        case "response":
          return api.post(`${path}/response`, {
            ...base,
            direction,
            communication_type: communicationType,
            message,
            occurred_at: new Date().toISOString(),
            recipient: recipient || null,
          });
        case "close":
          return api.post(`${path}/close`, { ...base, conclusion: closeConclusion });
      }
    });
  }

  return (
    <Modal open onClose={onClose} title={`${LABEL[transition]} - ${complaint.complaint_number}`} large={transition === "reportability"}>
      <form onSubmit={submit}>
        {SIGNATURE_GATED.includes(transition) && (
          <Banner tone="warn" title="This transition requires an electronic signature">
            This action needs a signature policy that hasn&apos;t been configured for this deployment yet, so it will be correctly refused rather than proceeding without one.
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
              <Field label="Constituent classification" hint="Which constituent the complaint concerns.">
                <Select value={constituentClass} onChange={(e) => setConstituentClass(e.target.value)}>
                  <option value="">Not classified</option>
                  {CONSTITUENT_CLASSIFICATIONS.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input type="checkbox" checked={injuryReported} onChange={(e) => setInjuryReported(e.target.checked)} />
              Injury, death or malfunction reported
            </label>
          </>
        )}

        {transition === "investigation_decision" && (
          <>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input
                type="checkbox"
                checked={investigationRequired}
                onChange={(e) => setInvestigationRequired(e.target.checked)}
              />
              Investigation required
            </label>
            {!investigationRequired && (
              <Field
                label="Justification for not investigating"
                required
                hint="820.198 requires a recorded justification whenever a complaint is not investigated."
              >
                <textarea
                  className="input"
                  rows={3}
                  value={noInvestigationReason}
                  onChange={(e) => setNoInvestigationReason(e.target.value)}
                  required
                />
              </Field>
            )}
          </>
        )}

        {transition === "investigation" && (
          <>
            <Field label="Findings" required>
              <textarea className="input" rows={3} value={findings} onChange={(e) => setFindings(e.target.value)} required />
            </Field>
            <Field label="Conclusion" required>
              <textarea className="input" rows={2} value={conclusion} onChange={(e) => setConclusion(e.target.value)} required />
            </Field>
          </>
        )}

        {transition === "reportability" && (
          <>
            <Field label="Applicable regimes" required hint="Select every regime assessed as applicable.">
              <div className="flex flex-wrap gap-3">
                {REGIMES.map((r) => (
                  <label key={r} className="flex items-center gap-2 fs-2">
                    <input
                      type="checkbox"
                      checked={regimes.includes(r)}
                      onChange={(e) =>
                        setRegimes((prev) => (e.target.checked ? [...prev, r] : prev.filter((x) => x !== r)))
                      }
                    />
                    {r}
                  </label>
                ))}
              </div>
            </Field>
            <Field label="Rationale" required>
              <textarea className="input" rows={3} value={rationale} onChange={(e) => setRationale(e.target.value)} required />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Trigger date" hint="When awareness started the reporting clock.">
                <Input type="date" value={triggerDate} onChange={(e) => setTriggerDate(e.target.value)} />
              </Field>
              <Field label="Submission due">
                <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              </Field>
            </div>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 fs-2 mb-3">
                <input type="checkbox" checked={capaRequired} onChange={(e) => setCapaRequired(e.target.checked)} />
                CAPA required
              </label>
              <label className="flex items-center gap-2 fs-2 mb-3">
                <input
                  type="checkbox"
                  checked={fieldActionRequired}
                  onChange={(e) => setFieldActionRequired(e.target.checked)}
                />
                Field action required
              </label>
            </div>
          </>
        )}

        {transition === "response" && (
          <>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Direction" required>
                <Select value={direction} onChange={(e) => setDirection(e.target.value)}>
                  <option value="outbound">outbound</option>
                  <option value="inbound">inbound</option>
                </Select>
              </Field>
              <Field label="Type" required>
                <Select value={communicationType} onChange={(e) => setCommunicationType(e.target.value)}>
                  <option value="acknowledgment">acknowledgment</option>
                  <option value="response">response</option>
                  <option value="update">update</option>
                </Select>
              </Field>
              <Field label="Recipient">
                <Input value={recipient} onChange={(e) => setRecipient(e.target.value)} />
              </Field>
            </div>
            <Field label="Message" required>
              <textarea className="input" rows={3} value={message} onChange={(e) => setMessage(e.target.value)} required />
            </Field>
          </>
        )}

        {transition === "close" && (
          <Field label="Conclusion" required>
            <textarea className="input" rows={3} value={closeConclusion} onChange={(e) => setCloseConclusion(e.target.value)} required />
          </Field>
        )}

        {(transition === "triage" || transition === "investigation") && (
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
            {busy ? "Saving…" : LABEL[transition]}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
