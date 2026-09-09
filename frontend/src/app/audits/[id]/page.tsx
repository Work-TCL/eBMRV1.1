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
  type AuditFinding,
  type InternalAudit,
} from "@/lib/api";
import { useApiResource, useEntityOptions, useMe } from "@/lib/hooks";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { QmsDetailShell, useCommand } from "@/components/qms/QmsDetailShell";
import { Fact, IdFact } from "@/components/ui/FactGrid";
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
import { StatePill, BoolPill, SeverityPill, WorkflowStatePill } from "@/components/ui/StatePill";

interface AuditDetail extends InternalAudit {
  site_scope: Record<string, unknown> | null;
  process_scope: Record<string, unknown> | null;
  criteria_refs: Record<string, unknown> | null;
  findings: AuditFinding[];
}

type AuditAction = "start" | "add_finding" | "close";
type FindingAction = "respond" | "verify";

// SG-138: no Document 106 policy rows for internal_audit start/close or audit_finding.verify.
const SIGNATURE_GATED: (AuditAction | FindingAction)[] = ["start", "close", "verify"];

const FINDING_SEVERITIES = ["critical", "major", "minor", "observation"];
// app/modules/qms/internal_audit_models.py FINDING_STATES — a finding is closed once VERIFIED.
const FINDING_CLOSED_STATES = ["VERIFIED"];

export default function AuditDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const [pending, setPending] = useState<AuditAction | null>(null);
  const [finding, setFinding] = useState<{ record: AuditFinding; action: FindingAction } | null>(null);
  const { data, loading, error, reload } = useApiResource<AuditDetail>(`/qms/v1/audits/${id}`);

  const openFindings = data?.findings.filter((f) => !FINDING_CLOSED_STATES.includes(f.state)) ?? [];

  const canStart = data?.state === "SCHEDULED" && canApproveQms(me);
  const canAddFinding = (data?.state === "IN_PROGRESS" || data?.state === "FINDINGS_OPEN") && canInvestigateQms(me);
  const canClose = data?.state === "FINDINGS_OPEN" && openFindings.length === 0 && canApproveQms(me);

  return (
    <QmsDetailShell
      recordNumber={data?.audit_number ?? ""}
      state={data?.state ?? ""}
      subtitle={data ? `Programme ${data.program_ref}` : undefined}
      backHref="/audits"
      backLabel="Internal audits"
      loading={loading}
      error={error}
      actions={
        <>
          {canStart && (
            <Button variant="primary" onClick={() => setPending("start")}>
              <Icon name="pen" /> Start audit
            </Button>
          )}
          {canAddFinding && (
            <Button variant="secondary" onClick={() => setPending("add_finding")}>
              <Icon name="plus" /> Add finding
            </Button>
          )}
          {canClose && (
            <Button variant="primary" onClick={() => setPending("close")}>
              <Icon name="pen" /> Close audit
            </Button>
          )}
        </>
      }
      facts={
        data && (
          <>
            <Fact label="Scheduled">{formatDate(data.scheduled_at)}</Fact>
            <Fact label="Started">{data.actual_start_at ? formatDateTime(data.actual_start_at) : "—"}</Fact>
            <Fact label="Ended">{data.actual_end_at ? formatDateTime(data.actual_end_at) : "—"}</Fact>
            <Fact label="Findings">{data.findings.length}</Fact>
            <Fact label="Open findings">
              {openFindings.length > 0 ? (
                <StatePill state="conflict" icon="alert-triangle">
                  {String(openFindings.length)}
                </StatePill>
              ) : (
                "0"
              )}
            </Fact>
            <Fact label="Record version">{data.version}</Fact>
            <IdFact label="Lead auditor" value={data.lead_auditor_id} />
            <IdFact label="Quality event" value={data.quality_event_id} />
          </>
        )
      }
    >
      {data && (
        <>
          <Card pad className="mb-4">
            <JsonPanel title="Audit criteria" value={data.criteria_refs} />
            <JsonPanel title="Process scope" value={data.process_scope} />
            <JsonPanel title="Site scope" value={data.site_scope} />
            <JsonPanel title="Audit team" value={data.team} />
            <JsonPanel title="Auditees" value={data.auditees} />
          </Card>

          {openFindings.some((f) => f.severity === "critical") && (
            <Banner tone="critical" title="Critical finding open">
              A critical audit finding remains open on this audit.
            </Banner>
          )}

          <Card>
            <div className="card-header">
              <div className="card-title">Findings</div>
              <span className="fs-2 text-muted">{data.findings.length} total</span>
            </div>
            {data.findings.length === 0 ? (
              <EmptyState icon="clipboard">No findings recorded on this audit.</EmptyState>
            ) : (
              <Table>
                <thead>
                  <tr>
                    <th>Number</th>
                    <th>Requirement</th>
                    <th>Observation</th>
                    <th>Severity</th>
                    <th>Due</th>
                    <th>State</th>
                    <th>Repeat</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data.findings.map((f) => {
                    const closed = FINDING_CLOSED_STATES.includes(f.state);
                    return (
                      <tr key={f.id}>
                        <td className="font-semibold tabular">{f.finding_number}</td>
                        <td className="fs-2">{f.requirement_ref}</td>
                        <td className="fs-2">{f.observation}</td>
                        <td>
                          <SeverityPill severity={f.severity} />
                        </td>
                        <td className={isOverdue(f.due_date) && !closed ? "error-text tabular fs-2" : "tabular fs-2"}>
                          {formatDate(f.due_date)}
                        </td>
                        <td>
                          <WorkflowStatePill state={f.state} />
                        </td>
                        <td>
                          <BoolPill value={f.is_repeat_finding} trueLabel="Repeat" falseLabel="New" />
                        </td>
                        <td style={{ textAlign: "right" }}>
                          <div className="flex gap-2 justify-end">
                            {!closed && canInvestigateQms(me) && (
                              <Button size="sm" variant="secondary" onClick={() => setFinding({ record: f, action: "respond" })}>
                                Respond
                              </Button>
                            )}
                            {!closed && canApproveQms(me) && (
                              <Button size="sm" variant="secondary" onClick={() => setFinding({ record: f, action: "verify" })}>
                                <Icon name="pen" /> Verify
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            )}
          </Card>

          {pending && (
            <AuditActionModal
              audit={data}
              action={pending}
              onClose={() => setPending(null)}
              onDone={() => {
                setPending(null);
                reload();
              }}
            />
          )}
          {finding && (
            <FindingActionModal
              finding={finding.record}
              action={finding.action}
              onClose={() => setFinding(null)}
              onDone={() => {
                setFinding(null);
                reload();
              }}
            />
          )}
        </>
      )}
    </QmsDetailShell>
  );
}

function AuditActionModal({
  audit,
  action,
  onClose,
  onDone,
}: {
  audit: AuditDetail;
  action: AuditAction;
  onClose: () => void;
  onDone: () => void;
}) {
  const { me } = useMe();
  const { busy, error, run } = useCommand(onDone);
  const entities = useEntityOptions();
  const [findingNumber, setFindingNumber] = useState("");
  const [requirementRef, setRequirementRef] = useState("");
  const [observation, setObservation] = useState("");
  const [severity, setSeverity] = useState("minor");
  const [owner, setOwner] = useState(me?.user_id ?? "");
  const [dueDate, setDueDate] = useState("");
  const [conclusion, setConclusion] = useState("");

  const title =
    action === "start" ? "Start audit" : action === "add_finding" ? "Add finding" : "Close audit";

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() => {
      if (action === "start") {
        return api.post(`/qms/v1/audits/${audit.id}/start`, {
          idempotency_key: newIdempotencyKey(),
          audit_id: audit.id,
          expected_version: audit.version,
        });
      }
      if (action === "add_finding") {
        return api.post(`/qms/v1/audits/${audit.id}/findings`, {
          idempotency_key: newIdempotencyKey(),
          audit_id: audit.id,
          audit_expected_version: audit.version,
          finding_number: findingNumber,
          requirement_ref: requirementRef,
          observation,
          severity,
          owner_subject_id: owner,
          due_date: dueDate ? new Date(dueDate).toISOString() : null,
        });
      }
      return api.post(`/qms/v1/audits/${audit.id}/close`, {
        idempotency_key: newIdempotencyKey(),
        audit_id: audit.id,
        expected_version: audit.version,
        conclusion,
      });
    });
  }

  return (
    <Modal open onClose={onClose} title={`${title} — ${audit.audit_number}`} large={action === "add_finding"}>
      <form onSubmit={submit}>
        {SIGNATURE_GATED.includes(action) && (
          <Banner tone="warn" title="This transition requires an electronic signature">
            This action needs a signature policy that hasn&apos;t been configured for this deployment yet, so it will be correctly refused rather than proceeding without one.
          </Banner>
        )}

        {action === "start" && (
          <p className="fs-3 mb-3">
            Starting the audit records the actual start time and moves it to IN_PROGRESS.
          </p>
        )}

        {action === "add_finding" && (
          <>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Finding number" required>
                <Input value={findingNumber} onChange={(e) => setFindingNumber(e.target.value)} required autoFocus />
              </Field>
              <Field label="Severity" required>
                <Select value={severity} onChange={(e) => setSeverity(e.target.value)}>
                  {FINDING_SEVERITIES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Response due">
                <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              </Field>
            </div>
            <Field label="Requirement reference" required hint="The clause or procedure the finding is against.">
              <Input value={requirementRef} onChange={(e) => setRequirementRef(e.target.value)} required />
            </Field>
            <Field label="Observation" required hint="What was seen — factual, not the conclusion drawn from it.">
              <textarea className="input" rows={3} value={observation} onChange={(e) => setObservation(e.target.value)} required />
            </Field>
            <EntityPickerField
              label="Owner"
              required
              value={owner}
              onChange={setOwner}
              options={entities.users}
              status={entities.usersStatus}
              kind="user"
            />
          </>
        )}

        {action === "close" && (
          <Field label="Conclusion" required>
            <textarea className="input" rows={3} value={conclusion} onChange={(e) => setConclusion(e.target.value)} required />
          </Field>
        )}

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Saving…" : title}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function FindingActionModal({
  finding,
  action,
  onClose,
  onDone,
}: {
  finding: AuditFinding;
  action: FindingAction;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [correction, setCorrection] = useState("");
  const [rootCause, setRootCause] = useState("");
  const [actionPlan, setActionPlan] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [capaRequired, setCapaRequired] = useState(false);
  const [capaRationale, setCapaRationale] = useState("");
  const [verificationNotes, setVerificationNotes] = useState("");
  const [effective, setEffective] = useState(true);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const base = {
      idempotency_key: newIdempotencyKey(),
      finding_id: finding.id,
      expected_version: finding.version,
    };
    run(() =>
      action === "respond"
        ? api.post(`/qms/v1/findings/${finding.id}/response`, {
            ...base,
            correction,
            root_cause: rootCause,
            action: actionPlan,
            due_date: dueDate ? new Date(dueDate).toISOString() : null,
            capa_required: capaRequired,
            capa_rationale: capaRationale || null,
          })
        : api.post(`/qms/v1/findings/${finding.id}/verify`, {
            ...base,
            verification_notes: verificationNotes,
            effective,
          })
    );
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`${action === "respond" ? "Respond to" : "Verify"} finding ${finding.finding_number}`}
      large={action === "respond"}
    >
      <form onSubmit={submit}>
        {action === "verify" && (
          <Banner tone="warn" title="This transition requires an electronic signature">
            This action needs a signature policy that hasn&apos;t been configured for this deployment yet, so it will be correctly refused rather than proceeding without one.
          </Banner>
        )}

        <p className="fs-2 text-muted mb-3">{finding.observation}</p>

        {action === "respond" ? (
          <>
            <Field label="Correction" required hint="What was done about the specific instance found.">
              <textarea className="input" rows={2} value={correction} onChange={(e) => setCorrection(e.target.value)} required />
            </Field>
            <Field label="Root cause" required>
              <textarea className="input" rows={2} value={rootCause} onChange={(e) => setRootCause(e.target.value)} required />
            </Field>
            <Field label="Corrective action" required hint="What stops it recurring.">
              <textarea className="input" rows={2} value={actionPlan} onChange={(e) => setActionPlan(e.target.value)} required />
            </Field>
            <Field label="Action due date">
              <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
            </Field>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input type="checkbox" checked={capaRequired} onChange={(e) => setCapaRequired(e.target.checked)} />
              A formal CAPA is required
            </label>
            {capaRequired && (
              <Field label="CAPA rationale" required>
                <textarea className="input" rows={2} value={capaRationale} onChange={(e) => setCapaRationale(e.target.value)} required />
              </Field>
            )}
          </>
        ) : (
          <>
            <Field label="Verification notes" required hint="Evidence the response actually resolved the finding.">
              <textarea
                className="input"
                rows={3}
                value={verificationNotes}
                onChange={(e) => setVerificationNotes(e.target.value)}
                required
              />
            </Field>
            <Field label="Effective">
              <Select value={effective ? "yes" : "no"} onChange={(e) => setEffective(e.target.value === "yes")}>
                <option value="yes">Yes — finding can close</option>
                <option value="no">No — response was not effective</option>
              </Select>
            </Field>
          </>
        )}

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Saving…" : action === "respond" ? "Submit response" : "Verify"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
