"use client";

import { useState } from "react";
import {
  api,
  canAssignTraining,
  canQualifyTraining,
  formatDate,
  isOverdue,
  newIdempotencyKey,
} from "@/lib/api";
import { useApiResource, useEntityOptions, useMe, useSiteId } from "@/lib/hooks";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { KpiRow, KpiTile } from "@/components/ui/KpiTile";
import { Tabs } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";

interface MatrixRow {
  requirement_id: string;
  title: string;
  training_type: string;
  assigned_count: number;
  completed_count: number;
  failed_count: number;
  open_count: number;
}

interface Matrix {
  site_id: string;
  requirements: MatrixRow[];
}

interface Assignment {
  id: string;
  requirement_id: string;
  subject_id: string;
  state: string;
  due_at: string | null;
  completed_at: string | null;
  score: number | null;
  version: number;
}

interface Qualification {
  id: string;
  subject_id: string;
  qualification_code: string;
  status: string;
  effective_from: string | null;
  effective_to: string | null;
}

interface SubjectStatus {
  subject_id: string;
  assignments: Assignment[];
  qualifications: Qualification[];
}

// app/modules/qms/training_models.py TRAINING_TYPES / SOURCE_TYPES.
const TRAINING_TYPES = [
  "read_and_understand", "instructor_led", "practical_ojt", "exam", "demonstration", "qualification",
  "recurring",
];
const SOURCE_TYPES = ["document", "role", "qualification", "change", "capa", "manager_assignment"];

export default function TrainingPage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [reloadToken, setReloadToken] = useState(0);
  const [requirementOpen, setRequirementOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const [subjectId, setSubjectId] = useState("");
  const [lookupId, setLookupId] = useState<string | null>(null);
  const entities = useEntityOptions();

  const matrix = useApiResource<Matrix>(
    siteId ? `/training/v1/matrix?site_id=${siteId}&_=${reloadToken}` : null
  );
  const subject = useApiResource<SubjectStatus>(lookupId ? `/training/v1/subjects/${lookupId}/status` : null);

  const rows = matrix.data?.requirements ?? [];
  const totals = rows.reduce(
    (acc, r) => ({
      assigned: acc.assigned + r.assigned_count,
      completed: acc.completed + r.completed_count,
      failed: acc.failed + r.failed_count,
      open: acc.open + r.open_count,
    }),
    { assigned: 0, completed: 0, failed: 0, open: 0 }
  );

  return (
    <div>
      <PageHead
        title="Training"
        subtitle="Training requirements, assignments, assessment and qualification."
        action={
          canAssignTraining(me) ? (
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setRequirementOpen(true)}>
                <Icon name="plus" /> New requirement
              </Button>
              <Button variant="primary" onClick={() => setAssignOpen(true)}>
                <Icon name="user-check" /> Assign training
              </Button>
            </div>
          ) : undefined
        }
      />

      <KpiRow>
        <KpiTile label="Assignments" icon="users" value={totals.assigned} />
        <KpiTile
          label="Completed"
          icon="check-circle"
          value={totals.completed}
          delta={totals.assigned > 0 ? `${Math.round((totals.completed / totals.assigned) * 100)}% complete` : undefined}
          tone="ok"
        />
        <KpiTile
          label="Open"
          icon="clock"
          value={totals.open}
          delta={totals.open > 0 ? "Assigned or awaiting assessment" : "Nothing outstanding"}
          tone={totals.open > 0 ? "warn" : "ok"}
        />
        <KpiTile
          label="Failed"
          icon="alert-triangle"
          value={totals.failed}
          delta={totals.failed > 0 ? "Requires retraining" : "None failed"}
          tone={totals.failed > 0 ? "critical" : "ok"}
        />
      </KpiRow>

      <Tabs
        tabs={[
          {
            id: "matrix",
            label: "Training matrix",
            badge: rows.length || undefined,
            content: (
              <Card>
                <CardHeader title="Requirements" meta={`${rows.length} requirement(s)`} />
                {matrix.error ? (
                  <p className="error-text" style={{ padding: "var(--space-4)" }}>
                    {matrix.error}
                  </p>
                ) : rows.length === 0 ? (
                  <EmptyState icon="users">No training requirements defined for this site.</EmptyState>
                ) : (
                  <Table>
                    <thead>
                      <tr>
                        <th>Requirement</th>
                        <th>Type</th>
                        <th style={{ textAlign: "right" }}>Assigned</th>
                        <th style={{ textAlign: "right" }}>Completed</th>
                        <th style={{ textAlign: "right" }}>Open</th>
                        <th style={{ textAlign: "right" }}>Failed</th>
                        <th>Coverage</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((r) => {
                        const pct = r.assigned_count > 0 ? (r.completed_count / r.assigned_count) * 100 : 0;
                        return (
                          <tr key={r.requirement_id}>
                            <td className="font-semibold">{r.title}</td>
                            <td className="fs-2">{r.training_type}</td>
                            <td className="tabular" style={{ textAlign: "right" }}>
                              {r.assigned_count}
                            </td>
                            <td className="tabular" style={{ textAlign: "right" }}>
                              {r.completed_count}
                            </td>
                            <td className="tabular" style={{ textAlign: "right" }}>
                              {r.open_count}
                            </td>
                            <td
                              className={r.failed_count > 0 ? "error-text tabular" : "tabular"}
                              style={{ textAlign: "right" }}
                            >
                              {r.failed_count}
                            </td>
                            <td style={{ minWidth: 120 }}>
                              <div className="progress-track">
                                <div className="progress-fill" style={{ width: `${pct}%` }} />
                              </div>
                              <span className="fs-1 text-muted tabular">{Math.round(pct)}%</span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </Table>
                )}
              </Card>
            ),
          },
          {
            id: "subject",
            label: "Person record",
            content: (
              <div>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    setLookupId(subjectId.trim() || null);
                  }}
                  className="flex flex-wrap items-end gap-4 mb-4"
                >
                  <div style={{ minWidth: 260, maxWidth: 360, width: "100%" }}>
                    <EntityPickerField
                      label="Person"
                      value={subjectId}
                      onChange={setSubjectId}
                      options={entities.users}
                      status={entities.usersStatus}
                      kind="user"
                    />
                  </div>
                  <Button type="submit" variant="secondary" disabled={!subjectId.trim()}>
                    <Icon name="search" /> Look up
                  </Button>
                  {me && (
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => {
                        setSubjectId(me.user_id);
                        setLookupId(me.user_id);
                      }}
                    >
                      My record
                    </Button>
                  )}
                </form>

                {subject.error && (
                  <Banner tone="critical" title="Could not load training record">
                    {subject.error}
                  </Banner>
                )}

                {subject.data && (
                  <SubjectRecord
                    status={subject.data}
                    canQualify={canQualifyTraining(me)}
                    onChanged={() => {
                      subject.reload();
                      setReloadToken((n) => n + 1);
                    }}
                  />
                )}
              </div>
            ),
          },
        ]}
      />

      {requirementOpen && (
        <RequirementModal
          onClose={() => setRequirementOpen(false)}
          onDone={() => {
            setRequirementOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
      {assignOpen && (
        <AssignModal
          requirements={rows}
          onClose={() => setAssignOpen(false)}
          onDone={() => {
            setAssignOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
    </div>
  );
}

function SubjectRecord({
  status,
  canQualify,
  onChanged,
}: {
  status: SubjectStatus;
  canQualify: boolean;
  onChanged: () => void;
}) {
  const [acting, setActing] = useState<{ assignment: Assignment; action: "complete" | "assess" } | null>(null);

  return (
    <>
      <Card className="mb-4">
        <CardHeader title="Assignments" meta={`${status.assignments.length} assignment(s)`} />
        {status.assignments.length === 0 ? (
          <EmptyState icon="users">No training assigned to this person.</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Assignment</th>
                <th>State</th>
                <th>Due</th>
                <th>Completed</th>
                <th>Score</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {status.assignments.map((a) => {
                const done = a.state === "COMPLETED";
                return (
                  <tr key={a.id}>
                    <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>
                      {a.requirement_id}
                    </td>
                    <td>
                      <WorkflowStatePill state={a.state} />
                    </td>
                    <td className={isOverdue(a.due_at) && !done ? "error-text tabular fs-2" : "tabular fs-2"}>
                      {formatDate(a.due_at)}
                    </td>
                    <td className="tabular fs-2">{formatDate(a.completed_at)}</td>
                    <td className="tabular fs-2">{a.score ?? "—"}</td>
                    <td style={{ textAlign: "right" }}>
                      <div className="flex gap-2 justify-end">
                        {a.state === "ASSIGNED" && (
                          <Button size="sm" variant="secondary" onClick={() => setActing({ assignment: a, action: "complete" })}>
                            <Icon name="pen" /> Complete
                          </Button>
                        )}
                        {a.state === "ASSESSMENT_PENDING" && canQualify && (
                          <Button size="sm" variant="secondary" onClick={() => setActing({ assignment: a, action: "assess" })}>
                            <Icon name="pen" /> Assess
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

      <Card>
        <CardHeader title="Qualifications" meta={`${status.qualifications.length} qualification(s)`} />
        {status.qualifications.length === 0 ? (
          <EmptyState icon="badge-check">No qualifications granted to this person.</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Status</th>
                <th>Effective from</th>
                <th>Expires</th>
              </tr>
            </thead>
            <tbody>
              {status.qualifications.map((q) => (
                <tr key={q.id}>
                  <td className="font-semibold tabular">{q.qualification_code}</td>
                  <td>
                    <WorkflowStatePill state={q.status} />
                  </td>
                  <td className="tabular fs-2">{formatDate(q.effective_from)}</td>
                  <td className={isOverdue(q.effective_to) ? "error-text tabular fs-2" : "tabular fs-2"}>
                    {formatDate(q.effective_to)}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {acting && (
        <AssignmentActionModal
          assignment={acting.assignment}
          action={acting.action}
          onClose={() => setActing(null)}
          onDone={() => {
            setActing(null);
            onChanged();
          }}
        />
      )}
    </>
  );
}

function AssignmentActionModal({
  assignment,
  action,
  onClose,
  onDone,
}: {
  assignment: Assignment;
  action: "complete" | "assess";
  onClose: () => void;
  onDone: () => void;
}) {
  const { me } = useMe();
  const { busy, error, run } = useCommand(onDone);
  const [passed, setPassed] = useState(true);
  const [score, setScore] = useState("");
  const [reason, setReason] = useState("");

  return (
    <Modal open onClose={onClose} title={action === "complete" ? "Complete training" : "Assess training"}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const base = {
            idempotency_key: newIdempotencyKey(),
            assignment_id: assignment.id,
            expected_version: assignment.version,
          };
          run(() =>
            action === "complete"
              ? api.post(`/training/v1/assignments/${assignment.id}/complete`, {
                  ...base,
                  trainer_user_id: me?.user_id ?? null,
                  reason: reason || null,
                })
              : api.post(`/training/v1/assignments/${assignment.id}/assess`, {
                  ...base,
                  passed,
                  score: score ? Number(score) : null,
                  trainer_user_id: me?.user_id ?? null,
                  reason: reason || null,
                })
          );
        }}
      >
        <Banner tone="warn" title="This transition requires an electronic signature">
          This action needs a signature policy that hasn&apos;t been configured for this deployment yet, so it will be correctly refused rather than proceeding without one.
        </Banner>

        {action === "assess" && (
          <>
            <Field label="Outcome" required>
              <Select value={passed ? "pass" : "fail"} onChange={(e) => setPassed(e.target.value === "pass")}>
                <option value="pass">Passed</option>
                <option value="fail">Failed — retraining required</option>
              </Select>
            </Field>
            <Field label="Score">
              <Input type="number" step="any" value={score} onChange={(e) => setScore(e.target.value)} />
            </Field>
          </>
        )}

        <Field label="Reason" hint="Optional. Recorded in the audit trail.">
          <Input value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Saving…" : action === "complete" ? "Complete" : "Record assessment"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function RequirementModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { siteId } = useSiteId();
  const { busy, error, run } = useCommand(onDone);
  const [title, setTitle] = useState("");
  const [trainingType, setTrainingType] = useState(TRAINING_TYPES[0]);
  const [sourceType, setSourceType] = useState(SOURCE_TYPES[0]);
  const [recurrenceDays, setRecurrenceDays] = useState("");
  const [requiresAssessment, setRequiresAssessment] = useState(false);
  const [passScore, setPassScore] = useState("");

  return (
    <Modal open onClose={onClose} title="New training requirement" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!siteId) return;
          run(() =>
            api.post("/training/v1/requirements", {
              idempotency_key: newIdempotencyKey(),
              site_id: siteId,
              title,
              source_type: sourceType,
              training_type: trainingType,
              recurrence_interval_days: recurrenceDays ? Number(recurrenceDays) : null,
              requires_assessment: requiresAssessment,
              pass_score: passScore ? Number(passScore) : null,
            })
          );
        }}
      >
        <Field label="Title" required>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} required autoFocus />
        </Field>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Training type" required>
            <Select value={trainingType} onChange={(e) => setTrainingType(e.target.value)}>
              {TRAINING_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Source type" required>
            <Select value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
              {SOURCE_TYPES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Recurrence (days)" hint="Blank for one-off.">
            <Input type="number" min={1} value={recurrenceDays} onChange={(e) => setRecurrenceDays(e.target.value)} />
          </Field>
        </div>
        <label className="flex items-center gap-2 fs-2 mb-3">
          <input
            type="checkbox"
            checked={requiresAssessment}
            onChange={(e) => setRequiresAssessment(e.target.checked)}
          />
          Requires assessment
        </label>
        {requiresAssessment && (
          <Field label="Pass score">
            <Input type="number" step="any" value={passScore} onChange={(e) => setPassScore(e.target.value)} />
          </Field>
        )}
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !title.trim() || !siteId}>
            {busy ? "Creating…" : "Create requirement"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function AssignModal({
  requirements,
  onClose,
  onDone,
}: {
  requirements: MatrixRow[];
  onClose: () => void;
  onDone: () => void;
}) {
  const { me } = useMe();
  const { busy, error, run } = useCommand(onDone);
  const entities = useEntityOptions();
  const [requirementId, setRequirementId] = useState(requirements[0]?.requirement_id ?? "");
  const [subject, setSubject] = useState(me?.user_id ?? "");
  const [dueAt, setDueAt] = useState("");

  return (
    <Modal open onClose={onClose} title="Assign training">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post("/training/v1/assignments", {
              idempotency_key: newIdempotencyKey(),
              requirement_id: requirementId,
              subject_id: subject,
              due_at: dueAt ? new Date(dueAt).toISOString() : null,
            })
          );
        }}
      >
        <Banner tone="warn" title="This transition requires an electronic signature">
          This action needs a signature policy that hasn&apos;t been configured for this deployment yet, so it will be correctly refused rather than proceeding without one.
        </Banner>

        <Field label="Requirement" required>
          <Select value={requirementId} onChange={(e) => setRequirementId(e.target.value)} required>
            <option value="">Select a requirement…</option>
            {requirements.map((r) => (
              <option key={r.requirement_id} value={r.requirement_id}>
                {r.title}
              </option>
            ))}
          </Select>
        </Field>
        <EntityPickerField
          label="Person"
          required
          value={subject}
          onChange={setSubject}
          options={entities.users}
          status={entities.usersStatus}
          kind="user"
        />
        <Field label="Due date">
          <Input type="date" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !requirementId || !subject.trim()}>
            {busy ? "Assigning…" : "Assign"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
