"use client";

import { useState } from "react";
import {
  api,
  ApiError,
  canDecideRelease,
  canEvaluateRelease,
  formatDateTime,
  newIdempotencyKey,
} from "@/lib/api";
import { useApiResource, useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field, RowButtonSlot } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { summarizeJson } from "@/components/ui/JsonPanel";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";

interface Scope {
  scope_id: string;
  site_id: string;
  scope_type: string;
  target_id: string;
  product_version_id: string;
  batch_id: string;
  state: string;
  version: number;
  current_evaluation_id: string | null;
  released_vault_object_id: string | null;
  decision_at: string | null;
}

interface Evaluation {
  evaluation_id: string;
  scope_version: number;
  evaluated_batch_version: number;
  blockers: { code?: string; message?: string }[];
  warnings: { code?: string; message?: string }[];
  eligible: boolean;
  evaluation_time: string;
}

interface Decision {
  decision_id: string;
  decision_code: string;
  reason: string | null;
  signature_id: string | null;
  decision_time: string;
  release_package_hash: string | null;
}

// release/models.py::SCOPE_TYPES = ("batch",) — lot/shipment scopes aren't built yet (SG-056: they need
// deeper Document 12/13 device-lot/serial integration this pass doesn't have). Offering them here would
// just be a dropdown that always fails post_evaluate()'s "Only scope_type 'batch' is supported" check.
const SCOPE_TYPES = ["batch"];

// GET /batches/v1 — same shape batch-execution's picker reads; only the fields the target-ID dropdown
// needs are declared here.
interface BatchOption {
  batch_id: string;
  batch_number: string;
  product_name: string | null;
  product_code: string | null;
  state: string;
}

export default function ReleasePage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [scopeType, setScopeType] = useState(SCOPE_TYPES[0]);
  const [targetId, setTargetId] = useState("");
  const [scopeId, setScopeId] = useState<string | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [decision, setDecision] = useState<"release" | "hold" | "reject" | null>(null);

  const { data: batchList, loading: batchesLoading, error: batchesError } = useApiResource<{ batches: BatchOption[] }>(
    scopeType === "batch" && siteId ? `/batches/v1?site_id=${siteId}` : null
  );
  const batchOptions = batchList?.batches ?? [];

  const eligibility = useApiResource<{ scope: Scope; evaluation: Evaluation | null }>(
    scopeId ? `/release/v1/scopes/${scopeId}/eligibility` : null
  );
  const packageView = useApiResource<{ scope: Scope; evaluation: Evaluation | null; decisions: Decision[] }>(
    scopeId ? `/release/v1/scopes/${scopeId}/package` : null
  );

  async function evaluate(e: React.FormEvent) {
    e.preventDefault();
    setEvaluating(true);
    setError(null);
    try {
      // A scope already in a terminal state (released/rejected) can never be re-evaluated --
      // evaluate_release_scope() correctly refuses with INVALID_TRANSITION ("cannot be re-evaluated from
      // a terminal state"). Without this lookup first, that made an already-decided batch permanently
      // unviewable from this page: every click just failed. Look up any existing scope first; only a
      // still-active one (or none yet) goes through evaluate — re-evaluating an active scope refreshes
      // eligibility as before, and a first-time target still creates + evaluates it.
      const existing = await api.get<{ scope_id: string; state: string } | null>(
        `/release/v1/scopes/${scopeType}/${targetId}`
      );
      if (existing && (existing.state === "released" || existing.state === "rejected")) {
        setScopeId(existing.scope_id);
        return;
      }
      const receipt = await api.post<{ aggregate_id: string }>(
        `/release/v1/scopes/${scopeType}/${targetId}/evaluate`,
        { idempotency_key: newIdempotencyKey(), scope_type: scopeType, scope_id: targetId }
      );
      setScopeId(receipt.aggregate_id);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Evaluation failed");
    } finally {
      setEvaluating(false);
    }
  }

  const scope = eligibility.data?.scope;
  const evaluation = eligibility.data?.evaluation;
  const decisions = packageView.data?.decisions ?? [];

  return (
    <div>
      <PageHead
        title="Release"
        subtitle="Release scope eligibility, the blocker set, and the final release decision."
      />

      <p className="hint mb-4">
        DDCP constituent and compatibility detail is not yet included in the release package evaluation -
        blockers and the decision record are the parts available today.
      </p>

      {/* items-start, not items-end: the Batch field carries a hint line below its select, which
         items-end would bottom-align the row to instead of the select itself — dragging the button down
         below where it visually belongs. RowButtonSlot gives the button a same-height invisible label so
         it lines up with the real inputs regardless of hint presence. */}
      <form onSubmit={evaluate} className="flex flex-wrap items-start gap-4 mb-4">
        <Field label="Scope type">
          <Select value={scopeType} onChange={(e) => setScopeType(e.target.value)}>
            {SCOPE_TYPES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Batch" hint="The batch being released.">
          <Select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            disabled={batchesLoading}
            style={{ minWidth: 260, maxWidth: 380, width: "100%" }}
          >
            <option value="">
              {batchesError ? "Could not load batches" : batchesLoading ? "Loading…" : batchOptions.length ? "Select a batch…" : "No batches at this site"}
            </option>
            {batchOptions.map((b) => (
              <option key={b.batch_id} value={b.batch_id}>
                {b.batch_number} - {b.product_name ? `${b.product_name} (${b.product_code})` : b.batch_id} · {b.state}
              </option>
            ))}
          </Select>
        </Field>
        {canEvaluateRelease(me) && (
          <RowButtonSlot>
            <Button type="submit" variant="secondary" disabled={evaluating || !targetId.trim()}>
              <Icon name="refresh" /> {evaluating ? "Evaluating…" : "Evaluate eligibility"}
            </Button>
          </RowButtonSlot>
        )}
      </form>

      {error && (
        <Banner tone="critical" title="Evaluation failed">
          {error}
        </Banner>
      )}

      {eligibility.error && (
        <Banner tone="critical" title="Could not load this scope">
          {eligibility.error}
        </Banner>
      )}

      {scope && (
        <>
          {/* Explains why no decision buttons render below for a terminal/held scope - otherwise "the
             Release button is missing" reads as a bug rather than the correct, final outcome it is. */}
          {scope.state === "released" && (
            <Banner tone="ok" title="Already released" icon="check-circle">
              This batch was released{scope.decision_at ? ` on ${formatDateTime(scope.decision_at)}` : ""}. That
              decision is final and cannot be repeated - see the decision record below for who signed it.
              Only Hold (a post-release recall) remains available.
            </Banner>
          )}
          {scope.state === "rejected" && (
            <Banner tone="critical" title="Already rejected" icon="x">
              This batch was rejected{scope.decision_at ? ` on ${formatDateTime(scope.decision_at)}` : ""}. That
              decision is final - see the decision record below for who signed it and why.
            </Banner>
          )}
          {scope.state === "hold" && (
            <Banner tone="warn" title="On hold" icon="lock">
              This scope is on hold and cannot be released, held again, or rejected from here - there is no
              resume-from-hold transition in this pass.
            </Banner>
          )}
          {scope.state !== "released" && scope.state !== "rejected" && scope.state !== "hold" && evaluation?.eligible ? (
            <Banner tone="ok" title="Eligible for release">
              Every release gate passed as at {formatDateTime(evaluation.evaluation_time)}.
            </Banner>
          ) : scope.state !== "released" && scope.state !== "rejected" && scope.state !== "hold" && evaluation ? (
            <Banner tone="critical" title={`${evaluation.blockers.length} blocker(s) prevent release`}>
              A release decision cannot be made while any blocker stands.
            </Banner>
          ) : null}

          <Card pad className="mb-4">
            <FactGrid>
              <Fact label="Scope state">
                <WorkflowStatePill state={scope.state} />
              </Fact>
              <Fact label="Scope type">{scope.scope_type}</Fact>
              <Fact label="Eligible">
                {evaluation ? (
                  evaluation.eligible ? (
                    <StatePill state="accepted" icon="check-circle">
                      Yes
                    </StatePill>
                  ) : (
                    <StatePill state="blocked" icon="lock">
                      No
                    </StatePill>
                  )
                ) : (
                  "Not evaluated"
                )}
              </Fact>
              <Fact label="Evaluated batch version">{evaluation?.evaluated_batch_version ?? "—"}</Fact>
              <Fact label="Decision at">{scope.decision_at ? formatDateTime(scope.decision_at) : "—"}</Fact>
              <Fact label="Record version">{scope.version}</Fact>
              <IdFact label="Scope ID" value={scope.scope_id} />
              <IdFact label="Batch" value={scope.batch_id} />
              <IdFact label="Product version" value={scope.product_version_id} />
              <IdFact label="Released vault object" value={scope.released_vault_object_id} />
            </FactGrid>

            {/* release/models.py::ALLOWED_TRANSITIONS is lowercase ("released"/"rejected"/…) and per-action
               ("released" only from "eligible"; "rejected" only from "eligible"/"blocked"; "hold" from
               anything except"hold"/"rejected", including post-release per REL-FR-031) - a single
               uppercase-cased guard around all three (as this used to be) never actually hid anything,
               since scope.state is never "RELEASED"/"REJECTED" literally, and offering an action the
               backend will refuse is exactly the class of bug the live INVALID_TRANSITION report on
               /qa-review turned out to be. */}
            {canDecideRelease(me) && (
              <div className="flex gap-2 mt-4">
                {scope.state === "eligible" && (
                  <Button variant="success" disabled={!evaluation?.eligible} onClick={() => setDecision("release")}>
                    <Icon name="pen" /> Release
                  </Button>
                )}
                {scope.state !== "hold" && scope.state !== "rejected" && (
                  <Button variant="secondary" onClick={() => setDecision("hold")}>
                    <Icon name="lock" /> Hold
                  </Button>
                )}
                {(scope.state === "eligible" || scope.state === "blocked") && (
                  <Button variant="danger" onClick={() => setDecision("reject")}>
                    <Icon name="x" /> Reject
                  </Button>
                )}
              </div>
            )}
          </Card>

          {evaluation && (
            <div className="grid grid-cols-2 gap-4 mb-4">
              <Card>
                <CardHeader title="Blockers" meta={`${evaluation.blockers.length}`} />
                {evaluation.blockers.length === 0 ? (
                  <EmptyState icon="check-circle">No blockers.</EmptyState>
                ) : (
                  <Table>
                    <thead>
                      <tr>
                        <th>Code</th>
                        <th>Message</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evaluation.blockers.map((b, i) => (
                        <tr key={b.code ?? i}>
                          <td className="tabular fs-2">{b.code ?? "—"}</td>
                          <td className="error-text">{b.message ?? summarizeJson(b)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                )}
              </Card>
              <Card>
                <CardHeader title="Warnings" meta={`${evaluation.warnings.length}`} />
                {evaluation.warnings.length === 0 ? (
                  <EmptyState icon="check-circle">No warnings.</EmptyState>
                ) : (
                  <Table>
                    <thead>
                      <tr>
                        <th>Code</th>
                        <th>Message</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evaluation.warnings.map((w, i) => (
                        <tr key={w.code ?? i}>
                          <td className="tabular fs-2">{w.code ?? "—"}</td>
                          <td>{w.message ?? summarizeJson(w)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                )}
              </Card>
            </div>
          )}

          <Card>
            <CardHeader title="Decision history" meta={`${decisions.length} decision(s)`} />
            {decisions.length === 0 ? (
              <EmptyState icon="history">No release decision recorded yet.</EmptyState>
            ) : (
              <Table>
                <thead>
                  <tr>
                    <th>Decision</th>
                    <th>When</th>
                    <th>Reason</th>
                    <th>Signature</th>
                    <th>Package hash</th>
                  </tr>
                </thead>
                <tbody>
                  {decisions.map((d) => (
                    <tr key={d.decision_id}>
                      <td>
                        <WorkflowStatePill state={d.decision_code} />
                      </td>
                      <td className="tabular fs-2">{formatDateTime(d.decision_time)}</td>
                      <td>{d.reason ?? "—"}</td>
                      <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>
                        {d.signature_id ?? "—"}
                      </td>
                      <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>
                        {d.release_package_hash ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>
        </>
      )}

      {decision && scope && (
        <DecisionModal
          scope={scope}
          decision={decision}
          onClose={() => setDecision(null)}
          onDone={() => {
            setDecision(null);
            eligibility.reload();
            packageView.reload();
          }}
        />
      )}
    </div>
  );
}

function DecisionModal({
  scope,
  decision,
  onClose,
  onDone,
}: {
  scope: Scope;
  decision: "release" | "hold" | "reject";
  onClose: () => void;
  onDone: () => void;
}) {
  const [reason, setReason] = useState("");

  const title = { release: "Release", hold: "Place on hold", reject: "Reject" }[decision];
  const variant = decision === "reject" ? "danger" : decision === "release" ? "success" : "primary";

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/release/v1/scopes/${scope.scope_id}/signature-challenges`}
      action={decision}
      title={
        <span className="flex items-center gap-2">
          <Icon name="pen" /> {title} - {scope.scope_type} scope
        </span>
      }
      summary="Records the final release decision for this scope. Signer must be independent of the QA Reviewer who completed this batch's review."
      submitLabel={`Sign & ${title.toLowerCase()}`}
      submitVariant={variant}
      disabled={decision !== "release" && !reason.trim()}
      extraFields={
        <Field label="Reason" required={decision !== "release"} hint="Part of the permanent record.">
          <textarea
            className="input"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required={decision !== "release"}
          />
        </Field>
      }
      onSign={(p) =>
        api.post(`/release/v1/scopes/${scope.scope_id}/${decision}`, {
          idempotency_key: p.idempotency_key,
          scope_id: scope.scope_id,
          expected_version: scope.version,
          reason: reason || null,
          challenge_id: p.challenge_id,
          reauth_password: p.reauth_password,
        })
      }
    />
  );
}
