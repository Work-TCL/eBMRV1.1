"use client";

import { use, useState } from "react";
import {
  api,
  hasPermission,
  formatDate,
  formatDateTime,
  isOverdue,
  newIdempotencyKey,
  type Capa,
  type CapaAction,
} from "@/lib/api";
import { useApiResource, useEntityOptions, useMe } from "@/lib/hooks";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
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
import { SeverityPill, WorkflowStatePill } from "@/components/ui/StatePill";

interface EffectivenessCheck {
  id: string;
  criterion: string;
  data_source: string;
  observation_start: string | null;
  observation_end: string | null;
  due_date: string | null;
  result: string | null;
  evidence: Record<string, unknown> | null;
  reviewer_subject_id: string | null;
  evaluated_at: string | null;
}

interface CapaDetail extends Capa {
  scope_refs: unknown[] | null;
  root_cause_ref: Record<string, unknown> | null;
  effectiveness_plan: Record<string, unknown> | null;
  corrective_action: Record<string, unknown> | null;
  preventive_action: Record<string, unknown> | null;
  recurrence_links: unknown[] | null;
  cancel_reason: string | null;
  extension_history: unknown[];
  closure_history: unknown[];
  reopen_history: unknown[];
  actions: CapaAction[];
  effectiveness_checks: EffectivenessCheck[];
}

type Transition =
  | "plan"
  | "add_action"
  | "define_effectiveness"
  | "record_effectiveness_result"
  | "extend"
  | "close"
  | "cancel"
  | "reopen";

// Mirrors each command's own state guard in app/modules/qms/capa_commands.py exactly (several diverge
// from the declared CAPA_ALLOWED_TRANSITIONS table with a narrower, hardcoded check — e.g. add_capa_action
// only accepts entering from PLAN or already being in IMPLEMENTATION, not every state
// CAPA_ALLOWED_TRANSITIONS lists as eventually reaching IMPLEMENTATION).
const ALLOWED_FROM: Record<string, Transition[]> = {
  OPEN: ["plan"],
  PLAN: ["add_action", "extend", "cancel"],
  IMPLEMENTATION: ["add_action", "extend", "cancel"],
  IMPLEMENTATION_VERIFIED: ["define_effectiveness", "extend", "cancel"],
  EFFECTIVENESS_MONITORING: ["define_effectiveness", "record_effectiveness_result", "extend", "cancel"],
  EFFECTIVENESS_REVIEW: ["close", "extend", "cancel"],
  EFFECTIVENESS_FAILED: ["reopen", "extend", "cancel"],
  CLOSED: ["reopen"],
  REOPENED: ["define_effectiveness", "close", "extend", "cancel"],
};

// Document 106 row 80 (capa_record/close — resolved, seed.py:1339): "Approved" by an independent QA
// Releaser. close_capa() resolves this same policy under action="close" for BOTH the close path
// (conclusion) and the cancel path (cancellation_reason) — see capa_commands.py::close_capa.
const SIGNATURE_GATED: Transition[] = ["close", "cancel"];

const LABEL: Record<Transition, string> = {
  plan: "Record plan",
  add_action: "Add action",
  define_effectiveness: "Define effectiveness check",
  record_effectiveness_result: "Record effectiveness result",
  extend: "Extend target",
  close: "Close",
  cancel: "Cancel",
  reopen: "Reopen",
};

// The exact permission code app/modules/qms/capa_router.py checks for each transition -- checking these
// directly (rather than a shared "investigator vs approver" role-set helper) means this page stays
// correct even if a customer edits which roles hold which of these codes.
const PERMISSION_FOR_TRANSITION: Record<Transition, string> = {
  plan: "capa.plan",
  add_action: "capa.action.add",
  define_effectiveness: "capa.effectiveness",
  record_effectiveness_result: "capa.effectiveness",
  extend: "capa.extend",
  // close_capa() resolves action="close" for both the close and cancel paths (capa_commands.py).
  close: "capa.close",
  cancel: "capa.close",
  reopen: "capa.reopen",
};

export default function CapaDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const [pending, setPending] = useState<Transition | null>(null);
  const [completing, setCompleting] = useState<CapaAction | null>(null);
  const { data, loading, error, reload } = useApiResource<CapaDetail>(`/qms/v1/capas/${id}`);

  const allowed = data ? (ALLOWED_FROM[data.state] ?? []) : [];
  const canDo = (t: Transition) => allowed.includes(t) && hasPermission(me, PERMISSION_FOR_TRANSITION[t]);

  return (
    <QmsDetailShell
      recordNumber={data?.capa_number ?? ""}
      state={data?.state ?? ""}
      subtitle={data ? `${data.scope_type} scope · source: ${data.source_type}` : undefined}
      backHref="/capa"
      backLabel="CAPA"
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
            <Fact label="Risk class">
              <SeverityPill severity={data.risk_class} />
            </Fact>
            <Fact label="Target date">
              <span className={isOverdue(data.target_date) && data.state !== "CLOSED" ? "error-text" : undefined}>
                {formatDate(data.target_date)}
              </span>
            </Fact>
            <Fact label="Open actions">
              {data.actions.filter((a) => a.state !== "COMPLETE" && a.state !== "COMPLETED").length} of{" "}
              {data.actions.length}
            </Fact>
            <Fact label="Effectiveness checks">{data.effectiveness_checks.length}</Fact>
            <Fact label="Raised">{formatDateTime(data.created_at)}</Fact>
            <Fact label="Closed">{data.closed_at ? formatDateTime(data.closed_at) : "—"}</Fact>
            <Fact label="Record version">{data.version}</Fact>
            <IdFact label="Owner" value={data.owner_subject_id} />
            <IdFact label="Source record" value={data.source_id} />
            <IdFact label="Quality event" value={data.quality_event_id} />
          </>
        )
      }
    >
      {data && (
        <>
          <Card pad className="mb-4">
            <p className="fact-k mb-2">Problem statement</p>
            <p>{data.problem_statement}</p>
          </Card>

          {data.state === "EFFECTIVENESS_FAILED" && (
            <Banner tone="critical" title="Effectiveness check failed">
              The corrective action did not demonstrate effectiveness. Reopen the CAPA or close it with a
              documented conclusion.
            </Banner>
          )}

          <Tabs
            tabs={[
              {
                id: "actions",
                label: "Actions",
                badge: data.actions.length || undefined,
                content: (
                  <ActionsTab
                    actions={data.actions}
                    canComplete={hasPermission(me, "capa.action.complete")}
                    onComplete={setCompleting}
                  />
                ),
              },
              {
                id: "plan",
                label: "Plan",
                content: (
                  <Card pad>
                    <JsonPanel title="Root cause reference" value={data.root_cause_ref} />
                    <JsonPanel title="Corrective action" value={data.corrective_action} />
                    <JsonPanel title="Preventive action" value={data.preventive_action} />
                    <JsonPanel title="Effectiveness plan" value={data.effectiveness_plan} />
                    <JsonPanel title="Scope references" value={data.scope_refs} />
                    <JsonPanel title="Recurrence links" value={data.recurrence_links} />
                    {!data.corrective_action && (
                      <EmptyState icon="help-circle">No plan recorded yet.</EmptyState>
                    )}
                  </Card>
                ),
              },
              {
                id: "effectiveness",
                label: "Effectiveness",
                badge: data.effectiveness_checks.length || undefined,
                content: <EffectivenessTab checks={data.effectiveness_checks} />,
              },
              {
                id: "history",
                label: "History",
                content: (
                  <Card pad>
                    <HistoryPanel title="Extensions" entries={data.extension_history} />
                    <HistoryPanel title="Closures" entries={data.closure_history} />
                    <HistoryPanel title="Reopens" entries={data.reopen_history} />
                    <JsonPanel title="Cancellation reason" value={data.cancel_reason} />
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
              capa={data}
              transition={pending}
              onClose={() => setPending(null)}
              onDone={() => {
                setPending(null);
                reload();
              }}
            />
          )}
          {completing && (
            <CompleteActionModal
              action={completing}
              onClose={() => setCompleting(null)}
              onDone={() => {
                setCompleting(null);
                reload();
              }}
            />
          )}
        </>
      )}
    </QmsDetailShell>
  );
}

function ActionsTab({
  actions,
  canComplete,
  onComplete,
}: {
  actions: CapaAction[];
  canComplete: boolean;
  onComplete: (action: CapaAction) => void;
}) {
  if (actions.length === 0) {
    return <EmptyState icon="list-checks">No actions on this CAPA plan yet.</EmptyState>;
  }
  return (
    <Card>
      <Table>
        <thead>
          <tr>
            <th>Type</th>
            <th>Description</th>
            <th>Due</th>
            <th>State</th>
            <th>Verification</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {actions.map((a) => {
            const done = a.state === "COMPLETE" || a.state === "COMPLETED";
            return (
              <tr key={a.id}>
                <td className="fs-2">{a.action_type}</td>
                <td>{a.description}</td>
                <td className={isOverdue(a.due_date) && !done ? "error-text tabular fs-2" : "tabular fs-2"}>
                  {formatDate(a.due_date)}
                </td>
                <td>
                  <WorkflowStatePill state={a.state} />
                </td>
                <td className="fs-2">
                  {a.verification_status ?? "—"}
                  {a.verified_at && <span className="text-muted"> · {formatDate(a.verified_at)}</span>}
                </td>
                <td style={{ textAlign: "right" }}>
                  {!done && canComplete && (
                    <Button size="sm" variant="secondary" onClick={() => onComplete(a)}>
                      Complete
                    </Button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </Table>
    </Card>
  );
}

function EffectivenessTab({ checks }: { checks: EffectivenessCheck[] }) {
  if (checks.length === 0) {
    return <EmptyState icon="gauge">No effectiveness checks defined yet.</EmptyState>;
  }
  return (
    <div>
      {checks.map((c) => (
        <Card key={c.id} pad className="mb-3">
          <div className="flex justify-between items-center mb-2">
            <span className="font-semibold">{c.criterion}</span>
            {c.result ? (
              <WorkflowStatePill state={c.result.toUpperCase()} />
            ) : (
              <span className="text-muted fs-2">Not yet evaluated</span>
            )}
          </div>
          <p className="fs-2 text-muted mb-2">
            Source: {c.data_source} · observation {formatDate(c.observation_start)} –{" "}
            {formatDate(c.observation_end)} · due {formatDate(c.due_date)}
          </p>
          <JsonPanel title="Evidence" value={c.evidence} />
        </Card>
      ))}
    </div>
  );
}

function CompleteActionModal({
  action,
  onClose,
  onDone,
}: {
  action: CapaAction;
  onClose: () => void;
  onDone: () => void;
}) {
  const { me } = useMe();
  const { busy, error, run } = useCommand(onDone);
  const entities = useEntityOptions();
  const [description, setDescription] = useState("");
  const [verifiedBy, setVerifiedBy] = useState(me?.user_id ?? "");

  return (
    <Modal open onClose={onClose} title={`Complete action - ${action.action_type}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/qms/v1/actions/${action.id}/complete`, {
              idempotency_key: newIdempotencyKey(),
              action_id: action.id,
              expected_version: action.version,
              implementation_evidence: { description },
              verified_by: verifiedBy,
              verification_status: "verified",
            })
          );
        }}
      >
        <p className="fs-2 mb-3">{action.description}</p>
        <Field label="Implementation evidence" required hint="What was done, and what shows it was done.">
          <textarea
            className="input"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
        </Field>
        <EntityPickerField
          label="Verified by"
          required
          value={verifiedBy}
          onChange={setVerifiedBy}
          options={entities.users}
          status={entities.usersStatus}
          kind="user"
        />
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !description.trim()}>
            {busy ? "Saving…" : "Complete action"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function TransitionModal({
  capa,
  transition,
  onClose,
  onDone,
}: {
  capa: CapaDetail;
  transition: Transition;
  onClose: () => void;
  onDone: () => void;
}) {
  const { me } = useMe();
  const { busy, error, run } = useCommand(onDone);
  const entities = useEntityOptions();

  const [corrective, setCorrective] = useState("");
  const [preventive, setPreventive] = useState("");
  const [effectivenessPlan, setEffectivenessPlan] = useState("");
  const [actionType, setActionType] = useState("corrective");
  const [description, setDescription] = useState("");
  const [actionOwner, setActionOwner] = useState(me?.user_id ?? "");
  const [dueDate, setDueDate] = useState("");
  const [criterion, setCriterion] = useState("");
  const [dataSource, setDataSource] = useState("");
  const [observationStart, setObservationStart] = useState("");
  const [observationEnd, setObservationEnd] = useState("");
  const [effectivenessDueDate, setEffectivenessDueDate] = useState("");
  const [checkId, setCheckId] = useState(
    capa.effectiveness_checks.find((c) => !c.result)?.id ?? ""
  );
  const [result, setResult] = useState("pass");
  const [evidenceDescription, setEvidenceDescription] = useState("");
  const [newTargetDate, setNewTargetDate] = useState("");
  const [reason, setReason] = useState("");
  const [riskReview, setRiskReview] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [cancellationReason, setCancellationReason] = useState("");
  const [newEvidence, setNewEvidence] = useState("");

  const base = { idempotency_key: newIdempotencyKey(), capa_id: capa.id, expected_version: capa.version };
  const path = `/qms/v1/capas/${capa.id}`;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() => {
      switch (transition) {
        case "plan":
          return api.post(`${path}/plan`, {
            ...base,
            corrective_action: { description: corrective },
            preventive_action: preventive ? { description: preventive } : null,
            effectiveness_plan: effectivenessPlan ? { description: effectivenessPlan } : null,
          });
        case "add_action":
          return api.post(`${path}/actions`, {
            ...base,
            action_type: actionType,
            description,
            owner_subject_id: actionOwner,
            due_date: new Date(dueDate).toISOString(),
          });
        case "define_effectiveness":
          // app/modules/qms/capa_commands.py::record_effectiveness — result omitted defines a new
          // check; criterion/data_source/observation_start/observation_end/due_date are all required.
          return api.post(`${path}/effectiveness`, {
            ...base,
            criterion,
            data_source: dataSource,
            observation_start: new Date(observationStart).toISOString(),
            observation_end: new Date(observationEnd).toISOString(),
            due_date: new Date(effectivenessDueDate).toISOString(),
          });
        case "extend":
          return api.post(`${path}/extend`, {
            ...base,
            new_target_date: new Date(newTargetDate).toISOString(),
            reason,
            risk_review: riskReview,
          });
        case "reopen":
          return api.post(`${path}/reopen`, { ...base, reason, new_evidence: newEvidence });
        default:
          // close/cancel/record_effectiveness_result are signature-gated and never reach this form —
          // see the early returns below that render <SignatureCeremony> for them instead.
          throw new Error(`${transition} does not submit through the plain form`);
      }
    });
  }

  // Document 106 row 80 (capa_record/close, resolved seed.py:1339): "Approved" by an independent QA
  // Releaser, via the shared Part 11 ceremony (challenge -> password re-entry -> signed mutation) —
  // same pattern as the deviations detail page's disposition/close. Close and Cancel both post to
  // /close: Close carries `conclusion`, Cancel carries `cancellation_reason` (capa_commands.py::close_capa
  // branches on which one is present).
  if (transition === "close") {
    return (
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        challengePath={`${path}/signature-challenges`}
        action="close"
        title={`Close - ${capa.capa_number}`}
        summary="Closes the CAPA permanently. This is a released quality decision - signer must be independent of the record's owner."
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
            capa_id: capa.id,
            expected_version: capa.version,
            challenge_id: p.challenge_id,
            reauth_password: p.reauth_password,
            conclusion,
          })
        }
      />
    );
  }

  if (transition === "cancel") {
    return (
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        challengePath={`${path}/signature-challenges`}
        action="close"
        title={`Cancel - ${capa.capa_number}`}
        summary="Cancels the CAPA before closure. This is a released quality decision - signer must be independent of the record's owner."
        submitLabel="Sign & cancel"
        submitVariant="danger"
        disabled={!cancellationReason.trim()}
        extraFields={
          <Field label="Cancellation reason" required>
            <textarea
              className="input"
              rows={3}
              value={cancellationReason}
              onChange={(e) => setCancellationReason(e.target.value)}
              required
            />
          </Field>
        }
        onSign={(p) =>
          api.post(`${path}/close`, {
            idempotency_key: p.idempotency_key,
            capa_id: capa.id,
            expected_version: capa.version,
            challenge_id: p.challenge_id,
            reauth_password: p.reauth_password,
            cancellation_reason: cancellationReason,
          })
        }
      />
    );
  }

  // Known-limitations fix (docs/testing/demo-gujarati/10 §10.6 item 2), 2026-09-18,
  // project-owner-directed: recording the effectiveness result is the pass/fail/inconclusive quality
  // conclusion — same "Approved"/QA Releaser/independent-of-owner signature shape as close() above.
  // Defining the check itself stays on the plain form below (it's plan-time criteria, not a conclusion).
  if (transition === "record_effectiveness_result") {
    const openChecks = capa.effectiveness_checks.filter((c) => !c.result);
    return (
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        challengePath={`${path}/signature-challenges`}
        action="effectiveness"
        title={`Record effectiveness result - ${capa.capa_number}`}
        summary="Records the pass/fail/inconclusive effectiveness conclusion. This is a released quality decision - signer must be independent of the record's owner."
        submitLabel="Sign & record result"
        submitVariant="success"
        disabled={openChecks.length === 0 || !checkId || !evidenceDescription.trim()}
        extraFields={
          <>
            {openChecks.length === 0 ? (
              <Banner tone="warn" title="No open effectiveness check">
                Define an effectiveness check first before a result can be recorded against it.
              </Banner>
            ) : (
              <Field label="Effectiveness check" required hint="Which defined check this result answers.">
                <Select value={checkId} onChange={(e) => setCheckId(e.target.value)} required>
                  {openChecks.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.criterion} (due {formatDate(c.due_date)})
                    </option>
                  ))}
                </Select>
              </Field>
            )}
            <Field label="Result" required>
              <Select value={result} onChange={(e) => setResult(e.target.value)} required>
                <option value="pass">pass</option>
                <option value="fail">fail</option>
                <option value="inconclusive">inconclusive</option>
              </Select>
            </Field>
            <Field label="Evidence" required hint="What was observed, and what shows it.">
              <textarea
                className="input"
                rows={3}
                value={evidenceDescription}
                onChange={(e) => setEvidenceDescription(e.target.value)}
                required
              />
            </Field>
          </>
        }
        onSign={(p) =>
          api.post(`${path}/effectiveness`, {
            idempotency_key: p.idempotency_key,
            capa_id: capa.id,
            expected_version: capa.version,
            challenge_id: p.challenge_id,
            reauth_password: p.reauth_password,
            check_id: checkId,
            result,
            evidence: { description: evidenceDescription },
            reviewer_subject_id: me?.user_id ?? null,
          })
        }
      />
    );
  }

  return (
    <Modal open onClose={onClose} title={`${LABEL[transition]} - ${capa.capa_number}`} large={transition === "plan"}>
      <form onSubmit={submit}>
        {transition === "plan" && (
          <>
            <Field label="Corrective action" required hint="What fixes the problem that occurred.">
              <textarea className="input" rows={3} value={corrective} onChange={(e) => setCorrective(e.target.value)} required />
            </Field>
            <Field label="Preventive action" hint="What stops it recurring elsewhere.">
              <textarea className="input" rows={2} value={preventive} onChange={(e) => setPreventive(e.target.value)} />
            </Field>
            <Field label="Effectiveness plan" hint="How effectiveness will be demonstrated later.">
              <textarea
                className="input"
                rows={2}
                value={effectivenessPlan}
                onChange={(e) => setEffectivenessPlan(e.target.value)}
              />
            </Field>
          </>
        )}

        {transition === "add_action" && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Action type" required>
                <Select value={actionType} onChange={(e) => setActionType(e.target.value)}>
                  <option value="corrective">corrective</option>
                  <option value="preventive">preventive</option>
                  <option value="systemic">systemic</option>
                </Select>
              </Field>
              <Field label="Due date" required>
                <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
              </Field>
            </div>
            <Field label="Description" required>
              <textarea className="input" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} required />
            </Field>
            <EntityPickerField
              label="Owner"
              required
              value={actionOwner}
              onChange={setActionOwner}
              options={entities.users}
              status={entities.usersStatus}
              kind="user"
            />
          </>
        )}

        {transition === "define_effectiveness" && (
          <>
            <Field label="Criterion" required hint="The measurable test of whether the CAPA worked.">
              <Input value={criterion} onChange={(e) => setCriterion(e.target.value)} required />
            </Field>
            <Field label="Data source" required>
              <Input value={dataSource} onChange={(e) => setDataSource(e.target.value)} required />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Observation start" required>
                <Input type="date" value={observationStart} onChange={(e) => setObservationStart(e.target.value)} required />
              </Field>
              <Field label="Observation end" required>
                <Input type="date" value={observationEnd} onChange={(e) => setObservationEnd(e.target.value)} required />
              </Field>
            </div>
            <Field label="Due date" required hint="When the result is due to be evaluated by.">
              <Input
                type="date"
                value={effectivenessDueDate}
                onChange={(e) => setEffectivenessDueDate(e.target.value)}
                required
              />
            </Field>
          </>
        )}

        {transition === "extend" && (
          <>
            <Field label="New target date" required>
              <Input type="date" value={newTargetDate} onChange={(e) => setNewTargetDate(e.target.value)} required />
            </Field>
            <Field label="Reason" required>
              <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} required />
            </Field>
            <Field label="Risk review" required>
              <textarea className="input" rows={2} value={riskReview} onChange={(e) => setRiskReview(e.target.value)} required />
            </Field>
          </>
        )}

        {transition === "reopen" && (
          <>
            <Field label="Reason" required>
              <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} required />
            </Field>
            <Field label="New evidence" required>
              <textarea className="input" rows={2} value={newEvidence} onChange={(e) => setNewEvidence(e.target.value)} required />
            </Field>
          </>
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
