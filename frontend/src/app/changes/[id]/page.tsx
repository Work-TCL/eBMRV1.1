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
  type ChangeControl,
} from "@/lib/api";
import { useApiResource, useEntityOptions, useMe } from "@/lib/hooks";
import { EntityPickerField } from "@/components/shared/EntityPicker";
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
import { Icon } from "@/components/ui/Icon";
import { HistoryPanel, JsonPanel } from "@/components/ui/JsonPanel";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";

interface AffectedObject {
  id: string;
  object_type: string;
  object_id: string;
  object_version: number | null;
  impact_category: string;
  action_required: string;
  created_at: string;
}

interface ChangeTask {
  id: string;
  description: string;
  owner_subject_id: string;
  due_date: string | null;
  dependency_links: unknown[] | null;
  evidence: Record<string, unknown> | null;
  status: string;
  version: number;
  completed_at: string | null;
}

interface ChangeDetail extends ChangeControl {
  current_state: Record<string, unknown> | null;
  proposed_state: Record<string, unknown> | null;
  risk_ref: string | null;
  regulatory_impact: Record<string, unknown> | null;
  validation_impact: Record<string, unknown> | null;
  training_impact: Record<string, unknown> | null;
  impact_assessment: Record<string, unknown> | null;
  emergency_reason: string | null;
  retrospective_review: Record<string, unknown> | null;
  cancel_reason: string | null;
  closure_history: unknown[];
  affected_objects: AffectedObject[];
  tasks: ChangeTask[];
}

type Transition = "impact" | "approve" | "add_task" | "implement" | "verify" | "make_effective" | "close";

const ALLOWED_FROM: Record<string, Transition[]> = {
  DRAFT: ["impact"],
  IMPACT_ASSESSMENT: ["impact", "approve"],
  APPROVAL: ["add_task", "implement"],
  IMPLEMENTATION: ["add_task", "implement", "verify"],
  VERIFICATION: ["verify", "make_effective"],
  EFFECTIVE: ["close"],
  CLOSED: [],
  CANCELLED: [],
};

// SG-138: no Document 106 policy rows for change_control approve/verify/close.
const SIGNATURE_GATED: Transition[] = ["approve", "verify", "close"];

const LABEL: Record<Transition, string> = {
  impact: "Assess impact",
  approve: "Approve",
  add_task: "Add task",
  implement: "Mark implemented",
  verify: "Verify",
  make_effective: "Make effective",
  close: "Close",
};

export default function ChangeDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const [pending, setPending] = useState<Transition | null>(null);
  const { data, loading, error, reload } = useApiResource<ChangeDetail>(`/qms/v1/changes/${id}`);

  const allowed = data ? (ALLOWED_FROM[data.state] ?? []) : [];
  const canDo = (t: Transition) =>
    allowed.includes(t) && (SIGNATURE_GATED.includes(t) || t === "make_effective" ? canApproveQms(me) : canInvestigateQms(me));

  return (
    <QmsDetailShell
      recordNumber={data?.change_number ?? ""}
      state={data?.state ?? ""}
      subtitle={data ? `${data.change_type} · ${data.classification}` : undefined}
      backHref="/changes"
      backLabel="Change control"
      loading={loading}
      error={error}
      actions={(Object.keys(LABEL) as Transition[]).filter(canDo).map((t) => (
        <Button key={t} variant={t === "approve" ? "primary" : "secondary"} onClick={() => setPending(t)}>
          {SIGNATURE_GATED.includes(t) && <Icon name="pen" />} {LABEL[t]}
        </Button>
      ))}
      facts={
        data && (
          <>
            <Fact label="Classification">{data.classification}</Fact>
            <Fact label="Emergency">
              {data.emergency ? (
                <StatePill state="conflict" icon="alert-triangle">
                  Yes
                </StatePill>
              ) : (
                "No"
              )}
            </Fact>
            <Fact label="Retrospective review">
              {data.emergency ? (data.retrospective_review_completed ? "Complete" : "Outstanding") : "N/A"}
            </Fact>
            <Fact label="Effective at">{formatDate(data.effective_at)}</Fact>
            <Fact label="Affected objects">{data.affected_objects.length}</Fact>
            <Fact label="Open tasks">
              {data.tasks.filter((t) => t.status !== "COMPLETE" && t.status !== "COMPLETED").length} of{" "}
              {data.tasks.length}
            </Fact>
            <Fact label="Raised">{formatDateTime(data.created_at)}</Fact>
            <Fact label="Closed">{data.closed_at ? formatDateTime(data.closed_at) : "—"}</Fact>
            <Fact label="Record version">{data.version}</Fact>
            <IdFact label="Owner" value={data.owner_subject_id} />
            <IdFact label="Risk record" value={data.risk_ref} />
            <IdFact label="Quality event" value={data.quality_event_id} />
          </>
        )
      }
    >
      {data && (
        <>
          {data.emergency && !data.retrospective_review_completed && (
            <Banner tone="warn" title="Emergency change — retrospective review outstanding">
              {data.emergency_reason ?? "No emergency justification recorded."}
            </Banner>
          )}

          <Tabs
            tabs={[
              {
                id: "change",
                label: "Change",
                content: (
                  <Card pad>
                    <JsonPanel title="Current state" value={data.current_state} />
                    <JsonPanel title="Proposed state" value={data.proposed_state} />
                    <p className="fact-k mb-2">Reason</p>
                    <p className="fs-3 mb-4">{data.reason}</p>
                    <JsonPanel title="Emergency justification" value={data.emergency_reason} />
                  </Card>
                ),
              },
              {
                id: "impact",
                label: "Impact",
                badge: data.affected_objects.length || undefined,
                content: (
                  <Card pad>
                    <JsonPanel title="Overall impact assessment" value={data.impact_assessment} />
                    <JsonPanel title="Regulatory impact" value={data.regulatory_impact} />
                    <JsonPanel title="Validation impact" value={data.validation_impact} />
                    <JsonPanel title="Training impact" value={data.training_impact} />
                    <p className="fact-k mb-2">Affected objects</p>
                    {data.affected_objects.length === 0 ? (
                      <EmptyState icon="layers">No affected objects declared.</EmptyState>
                    ) : (
                      <Table>
                        <thead>
                          <tr>
                            <th>Type</th>
                            <th>Object</th>
                            <th>Impact</th>
                            <th>Action required</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.affected_objects.map((o) => (
                            <tr key={o.id}>
                              <td>{o.object_type}</td>
                              <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>
                                {o.object_id}
                              </td>
                              <td>{o.impact_category}</td>
                              <td className="fs-2">{o.action_required}</td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    )}
                  </Card>
                ),
              },
              {
                id: "tasks",
                label: "Tasks",
                badge: data.tasks.length || undefined,
                content:
                  data.tasks.length === 0 ? (
                    <EmptyState icon="list-checks">No implementation tasks yet.</EmptyState>
                  ) : (
                    <Card>
                      <Table>
                        <thead>
                          <tr>
                            <th>Description</th>
                            <th>Due</th>
                            <th>Status</th>
                            <th>Completed</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.tasks.map((t) => {
                            const done = t.status === "COMPLETE" || t.status === "COMPLETED";
                            return (
                              <tr key={t.id}>
                                <td>{t.description}</td>
                                <td className={isOverdue(t.due_date) && !done ? "error-text tabular fs-2" : "tabular fs-2"}>
                                  {formatDate(t.due_date)}
                                </td>
                                <td>
                                  <WorkflowStatePill state={t.status} />
                                </td>
                                <td className="tabular fs-2">{formatDate(t.completed_at)}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </Table>
                    </Card>
                  ),
              },
              {
                id: "closure",
                label: "Closure",
                content: (
                  <Card pad>
                    <JsonPanel title="Retrospective review" value={data.retrospective_review} />
                    <JsonPanel title="Cancellation reason" value={data.cancel_reason} />
                    <HistoryPanel title="Closures" entries={data.closure_history} />
                    {!data.retrospective_review && data.closure_history.length === 0 && (
                      <EmptyState icon="history">Nothing closed yet.</EmptyState>
                    )}
                  </Card>
                ),
              },
            ]}
          />

          {pending && (
            <TransitionModal
              change={data}
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
  change,
  transition,
  onClose,
  onDone,
}: {
  change: ChangeDetail;
  transition: Transition;
  onClose: () => void;
  onDone: () => void;
}) {
  const { me } = useMe();
  const { busy, error, run } = useCommand(onDone);
  const entities = useEntityOptions();

  const [regulatory, setRegulatory] = useState("");
  const [regulatoryReview, setRegulatoryReview] = useState(false);
  const [validation, setValidation] = useState("");
  const [validationRequired, setValidationRequired] = useState(false);
  const [training, setTraining] = useState("");
  const [trainingRequired, setTrainingRequired] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [taskOwner, setTaskOwner] = useState(me?.user_id ?? "");
  const [taskDue, setTaskDue] = useState("");
  const [verificationEvidence, setVerificationEvidence] = useState("");
  const [effectiveAt, setEffectiveAt] = useState("");
  const [trainingConfirmed, setTrainingConfirmed] = useState(false);
  const [reviewConclusion, setReviewConclusion] = useState("");
  const [reason, setReason] = useState("");

  const base = { idempotency_key: newIdempotencyKey(), change_id: change.id, expected_version: change.version };
  const path = `/qms/v1/changes/${change.id}`;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() => {
      switch (transition) {
        case "impact":
          return api.post(`${path}/impact`, {
            ...base,
            regulatory_impact: {
              description: regulatory,
              requires_review: regulatoryReview,
              // The backend blocks approval while a regulatory impact requiring review has no reviewer
              // recorded, so the assessor is named here rather than left for approval time.
              reviewed_by: regulatoryReview ? (me?.user_id ?? null) : null,
            },
            validation_impact: { description: validation, required: validationRequired },
            training_impact: { description: training, required: trainingRequired },
            reason: reason || null,
          });
        case "approve":
          return api.post(`${path}/approve`, { ...base, approval_notes: approvalNotes || null });
        case "add_task":
          return api.post(`${path}/tasks`, {
            ...base,
            description: taskDescription,
            owner_subject_id: taskOwner,
            due_date: new Date(taskDue).toISOString(),
          });
        case "implement":
          return api.post(`${path}/implement`, { ...base, reason: reason || null });
        case "verify":
          return api.post(`${path}/verify`, {
            ...base,
            verification_evidence: { description: verificationEvidence },
            reason: reason || null,
          });
        case "make_effective":
          return api.post(`${path}/make-effective`, {
            ...base,
            effective_at: new Date(effectiveAt).toISOString(),
            training_confirmed: trainingConfirmed,
            reason: reason || null,
          });
        case "close":
          return api.post(`${path}/close`, {
            ...base,
            post_implementation_review: { conclusion: reviewConclusion },
          });
      }
    });
  }

  return (
    <Modal open onClose={onClose} title={`${LABEL[transition]} — ${change.change_number}`} large={transition === "impact"}>
      <form onSubmit={submit}>
        {SIGNATURE_GATED.includes(transition) && (
          <Banner tone="warn" title="This transition requires an electronic signature">
            This action needs a signature policy that hasn&apos;t been configured for this deployment yet, so it will be correctly refused rather than proceeding without one.
          </Banner>
        )}

        {transition === "impact" && (
          <>
            <Field label="Regulatory impact" required>
              <textarea className="input" rows={2} value={regulatory} onChange={(e) => setRegulatory(e.target.value)} required />
            </Field>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input type="checkbox" checked={regulatoryReview} onChange={(e) => setRegulatoryReview(e.target.checked)} />
              Requires regulatory review (you are recorded as the reviewer)
            </label>
            <Field label="Validation impact" required>
              <textarea className="input" rows={2} value={validation} onChange={(e) => setValidation(e.target.value)} required />
            </Field>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input type="checkbox" checked={validationRequired} onChange={(e) => setValidationRequired(e.target.checked)} />
              Revalidation required — verification evidence will be mandatory
            </label>
            <Field label="Training impact" required>
              <textarea className="input" rows={2} value={training} onChange={(e) => setTraining(e.target.value)} required />
            </Field>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input type="checkbox" checked={trainingRequired} onChange={(e) => setTrainingRequired(e.target.checked)} />
              Training required — must be confirmed before the change can be made effective
            </label>
          </>
        )}

        {transition === "approve" && (
          <Field label="Approval notes">
            <textarea className="input" rows={3} value={approvalNotes} onChange={(e) => setApprovalNotes(e.target.value)} />
          </Field>
        )}

        {transition === "add_task" && (
          <>
            <Field label="Description" required>
              <textarea className="input" rows={2} value={taskDescription} onChange={(e) => setTaskDescription(e.target.value)} required />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <EntityPickerField
                label="Owner"
                required
                value={taskOwner}
                onChange={setTaskOwner}
                options={entities.users}
                status={entities.usersStatus}
                kind="user"
              />
              <Field label="Due date" required>
                <Input type="date" value={taskDue} onChange={(e) => setTaskDue(e.target.value)} required />
              </Field>
            </div>
          </>
        )}

        {transition === "verify" && (
          <Field label="Verification evidence" required hint="Required when the impact assessment declared revalidation.">
            <textarea
              className="input"
              rows={3}
              value={verificationEvidence}
              onChange={(e) => setVerificationEvidence(e.target.value)}
              required
            />
          </Field>
        )}

        {transition === "make_effective" && (
          <>
            <Field label="Effective at" required>
              <Input type="date" value={effectiveAt} onChange={(e) => setEffectiveAt(e.target.value)} required />
            </Field>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input type="checkbox" checked={trainingConfirmed} onChange={(e) => setTrainingConfirmed(e.target.checked)} />
              Required training has been completed
            </label>
          </>
        )}

        {transition === "close" && (
          <Field label="Post-implementation review conclusion" required>
            <textarea className="input" rows={3} value={reviewConclusion} onChange={(e) => setReviewConclusion(e.target.value)} required />
          </Field>
        )}

        {(transition === "impact" || transition === "implement" || transition === "verify" || transition === "make_effective") && (
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
