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
  type RiskRecord,
} from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
import { QmsDetailShell, useCommand } from "@/components/qms/QmsDetailShell";
import { Fact, IdFact } from "@/components/ui/FactGrid";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { HistoryPanel, JsonPanel } from "@/components/ui/JsonPanel";
import { StatePill } from "@/components/ui/StatePill";

interface AssessmentVersion {
  id: string;
  cycle_number: number;
  methodology_version: string | null;
  scoring_inputs: Record<string, unknown> | null;
  initial_score: Record<string, unknown> | null;
  controls: unknown[] | null;
  mitigation_actions: unknown[] | null;
  residual_inputs: Record<string, unknown> | null;
  residual_score: Record<string, unknown> | null;
  acceptance_criteria: Record<string, unknown> | null;
  acceptance: Record<string, unknown> | null;
  review_history: unknown[];
  is_current: boolean;
  created_at: string;
  closed_at: string | null;
}

interface RiskDetail extends RiskRecord {
  methodology_id: string | null;
  context: Record<string, unknown> | null;
  assessment_versions: AssessmentVersion[];
}

type Transition = "assessment" | "controls" | "accept" | "review";

const ALLOWED_FROM: Record<string, Transition[]> = {
  DRAFT: ["assessment"],
  INITIAL_ASSESSMENT: ["assessment", "controls"],
  CONTROLS_MITIGATION: ["controls", "assessment"],
  RESIDUAL_ASSESSMENT: ["accept", "controls"],
  ACCEPTED: ["review"],
  NEW_VERSION: ["assessment"],
};

// SG-138: no Document 106 policy row for risk_record.review.
const SIGNATURE_GATED: Transition[] = ["review"];

const LABEL: Record<Transition, string> = {
  assessment: "Add assessment",
  controls: "Add controls",
  accept: "Accept risk",
  review: "Periodic review",
};

export default function RiskDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const [pending, setPending] = useState<Transition | null>(null);
  const { data, loading, error, reload } = useApiResource<RiskDetail>(`/qms/v1/risks/${id}`);

  const allowed = data ? (ALLOWED_FROM[data.state] ?? []) : [];
  const canDo = (t: Transition) =>
    allowed.includes(t) && (t === "accept" || t === "review" ? canApproveQms(me) : canInvestigateQms(me));

  const current = data?.assessment_versions.find((v) => v.is_current);
  const reviewOverdue = data ? isOverdue(data.next_review_due_at) && data.state === "ACCEPTED" : false;

  return (
    <QmsDetailShell
      recordNumber={data?.risk_number ?? ""}
      state={data?.state ?? ""}
      subtitle={data ? `${data.risk_type} risk` : undefined}
      backHref="/risks"
      backLabel="Risk register"
      loading={loading}
      error={error}
      actions={(Object.keys(LABEL) as Transition[]).filter(canDo).map((t) => (
        <Button key={t} variant={t === "accept" ? "primary" : "secondary"} onClick={() => setPending(t)}>
          {SIGNATURE_GATED.includes(t) && <Icon name="pen" />} {LABEL[t]}
        </Button>
      ))}
      facts={
        data && (
          <>
            <Fact label="Risk type">{data.risk_type}</Fact>
            <Fact label="Assessment cycles">{data.assessment_versions.length}</Fact>
            <Fact label="Review due">
              <span className={reviewOverdue ? "error-text" : undefined}>
                {formatDate(data.next_review_due_at)}
              </span>
            </Fact>
            <Fact label="Raised">{formatDateTime(data.created_at)}</Fact>
            <Fact label="Record version">{data.version}</Fact>
            <IdFact label="Owner" value={data.owner_subject_id} />
            <IdFact label="Methodology" value={data.methodology_id} />
            <IdFact label="Quality event" value={data.quality_event_id} />
          </>
        )
      }
    >
      {data && (
        <>
          {reviewOverdue && (
            <Banner tone="critical" title="Periodic review overdue">
              This risk was accepted with a review due {formatDate(data.next_review_due_at)}. An accepted
              risk whose review has lapsed is no longer a current assessment.
            </Banner>
          )}

          <Card pad className="mb-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="fact-k mb-1">Hazard / problem</p>
                <p className="fs-3">{data.hazard_problem}</p>
              </div>
              <div>
                <p className="fact-k mb-1">Potential effect</p>
                <p className="fs-3">{data.potential_effect}</p>
              </div>
            </div>
            <div className="mt-4">
              <JsonPanel title="Context" value={data.context} />
            </div>
          </Card>

          {current && (
            <Card pad className="mb-4">
              <div className="flex justify-between items-center mb-3">
                <span className="font-semibold">Current assessment — cycle {current.cycle_number}</span>
                <StatePill state="accepted" icon="check-circle">
                  Current
                </StatePill>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <JsonPanel title="Initial score" value={current.initial_score} />
                <JsonPanel title="Residual score" value={current.residual_score} />
              </div>
              <JsonPanel title="Scoring inputs" value={current.scoring_inputs} />
              <JsonPanel title="Controls" value={current.controls} />
              <JsonPanel title="Mitigation actions" value={current.mitigation_actions} />
              <JsonPanel title="Acceptance criteria" value={current.acceptance_criteria} />
              <JsonPanel title="Acceptance" value={current.acceptance} />
              <HistoryPanel title="Review history" entries={current.review_history} />
            </Card>
          )}

          {data.assessment_versions.length === 0 && (
            <EmptyState icon="gauge">No assessment recorded yet — add one to score this risk.</EmptyState>
          )}

          {data.assessment_versions.filter((v) => !v.is_current).length > 0 && (
            <Card pad>
              <p className="fact-k mb-3">Superseded assessment cycles</p>
              {data.assessment_versions
                .filter((v) => !v.is_current)
                .map((v) => (
                  <div key={v.id} className="mb-3" style={{ borderLeft: "2px solid var(--border-hairline)", paddingLeft: "var(--space-3)" }}>
                    <p className="fs-2 text-muted mb-1">
                      Cycle {v.cycle_number} · {formatDate(v.created_at)}
                      {v.closed_at && ` – closed ${formatDate(v.closed_at)}`}
                    </p>
                    <JsonPanel title="Residual score" value={v.residual_score} />
                  </div>
                ))}
            </Card>
          )}

          {pending && (
            <TransitionModal
              risk={data}
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
  risk,
  transition,
  onClose,
  onDone,
}: {
  risk: RiskDetail;
  transition: Transition;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);

  const [methodologyId, setMethodologyId] = useState(risk.methodology_id ?? "");
  const [severity, setSeverity] = useState("3");
  const [occurrence, setOccurrence] = useState("3");
  const [detectability, setDetectability] = useState("3");
  const [controlDescription, setControlDescription] = useState("");
  const [controlType, setControlType] = useState("procedural");
  const [mitigation, setMitigation] = useState("");
  const [acceptedRole, setAcceptedRole] = useState("Head of Quality");
  const [rationale, setRationale] = useState("");
  const [nextReview, setNextReview] = useState("");
  const [triggerType, setTriggerType] = useState("periodic");
  const [outcome, setOutcome] = useState("still_current");
  const [reason, setReason] = useState("");

  const base = { idempotency_key: newIdempotencyKey(), risk_id: risk.id, expected_version: risk.version };
  const path = `/qms/v1/risks/${risk.id}`;

  // The scoring dimensions and the product are the methodology's own arithmetic; this form records the
  // three inputs and the resulting RPN rather than inventing a risk-acceptance threshold, which is a
  // regulated decision the methodology owns.
  const rpn = Number(severity) * Number(occurrence) * Number(detectability);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() => {
      switch (transition) {
        case "assessment":
          return api.post(`${path}/assessments`, {
            ...base,
            scoring_inputs: {
              severity: Number(severity),
              occurrence: Number(occurrence),
              detectability: Number(detectability),
            },
            score: { rpn, severity: Number(severity), occurrence: Number(occurrence), detectability: Number(detectability) },
            methodology_id: methodologyId || null,
            reason: reason || null,
          });
        case "controls":
          return api.post(`${path}/controls`, {
            ...base,
            controls: [{ type: controlType, description: controlDescription }],
            mitigation_actions: mitigation ? [{ description: mitigation }] : null,
            reason: reason || null,
          });
        case "accept":
          return api.post(`${path}/accept`, {
            ...base,
            accepted_role: acceptedRole,
            rationale,
            next_review_due_at: nextReview ? new Date(nextReview).toISOString() : null,
          });
        case "review":
          return api.post(`${path}/review`, {
            ...base,
            trigger_type: triggerType,
            outcome,
            rationale,
            next_review_due_at: nextReview ? new Date(nextReview).toISOString() : null,
          });
      }
    });
  }

  return (
    <Modal open onClose={onClose} title={`${LABEL[transition]} — ${risk.risk_number}`}>
      <form onSubmit={submit}>
        {SIGNATURE_GATED.includes(transition) && (
          <Banner tone="warn" title="This transition requires an electronic signature">
            No Document 106 policy row exists yet for <code>risk_record.review</code> (SG-138), so the
            backend fails it closed.
          </Banner>
        )}

        {transition === "assessment" && (
          <>
            <Field
              label="Methodology ID"
              required
              hint="A released rule of type risk_methodology (see the Rules page) — required for the first assessment of a cycle."
            >
              <Input value={methodologyId} onChange={(e) => setMethodologyId(e.target.value)} required />
            </Field>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Severity" required>
                <Input type="number" min={1} max={10} value={severity} onChange={(e) => setSeverity(e.target.value)} required />
              </Field>
              <Field label="Occurrence" required>
                <Input type="number" min={1} max={10} value={occurrence} onChange={(e) => setOccurrence(e.target.value)} required />
              </Field>
              <Field label="Detectability" required>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  value={detectability}
                  onChange={(e) => setDetectability(e.target.value)}
                  required
                />
              </Field>
            </div>
            <p className="hint mb-3">
              Risk priority number: <span className="tabular font-semibold">{rpn}</span>. Whether this
              value is acceptable is the methodology&apos;s decision, recorded at acceptance.
            </p>
          </>
        )}

        {transition === "controls" && (
          <>
            <Field label="Control type" required>
              <Select value={controlType} onChange={(e) => setControlType(e.target.value)}>
                <option value="elimination">elimination</option>
                <option value="engineering">engineering</option>
                <option value="procedural">procedural</option>
                <option value="protective">protective</option>
                <option value="information">information</option>
              </Select>
            </Field>
            <Field label="Control description" required>
              <textarea
                className="input"
                rows={2}
                value={controlDescription}
                onChange={(e) => setControlDescription(e.target.value)}
                required
              />
            </Field>
            <Field label="Mitigation action" hint="A tracked action, if the control needs implementing.">
              <textarea className="input" rows={2} value={mitigation} onChange={(e) => setMitigation(e.target.value)} />
            </Field>
          </>
        )}

        {transition === "accept" && (
          <>
            <Field label="Accepting role" required hint="The role with authority to accept this residual risk.">
              <Input value={acceptedRole} onChange={(e) => setAcceptedRole(e.target.value)} required />
            </Field>
            <Field label="Acceptance rationale" required>
              <textarea className="input" rows={3} value={rationale} onChange={(e) => setRationale(e.target.value)} required />
            </Field>
            <Field label="Next review due" hint="An accepted risk without a review date never comes back for review.">
              <Input type="date" value={nextReview} onChange={(e) => setNextReview(e.target.value)} />
            </Field>
          </>
        )}

        {transition === "review" && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Trigger" required>
                <Select value={triggerType} onChange={(e) => setTriggerType(e.target.value)}>
                  <option value="periodic">periodic</option>
                  <option value="triggered">triggered</option>
                </Select>
              </Field>
              <Field label="Outcome" required>
                <Select value={outcome} onChange={(e) => setOutcome(e.target.value)}>
                  <option value="still_current">still current</option>
                  <option value="reassessment_required">reassessment required</option>
                </Select>
              </Field>
            </div>
            <Field label="Rationale" required>
              <textarea className="input" rows={3} value={rationale} onChange={(e) => setRationale(e.target.value)} required />
            </Field>
            <Field label="Next review due">
              <Input type="date" value={nextReview} onChange={(e) => setNextReview(e.target.value)} />
            </Field>
          </>
        )}

        {(transition === "assessment" || transition === "controls") && (
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
