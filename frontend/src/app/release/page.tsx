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
import { useApiResource, useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";

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

const SCOPE_TYPES = ["batch", "lot", "shipment"];

export default function ReleasePage() {
  const { me } = useMe();
  const [scopeType, setScopeType] = useState(SCOPE_TYPES[0]);
  const [targetId, setTargetId] = useState("");
  const [scopeId, setScopeId] = useState<string | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [decision, setDecision] = useState<"release" | "hold" | "reject" | null>(null);

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
      // Evaluating creates the scope on first call and re-evaluates it thereafter; the receipt's
      // aggregate_id is the scope to read back.
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
        subtitle="Document 15 — release scope eligibility, the blocker set, and the final release decision."
      />

      <p className="hint mb-4">
        DDCP constituent and compatibility detail in the release package (Document 15 §8) is not built —
        see SG-056. Evaluation, blockers and the decision record are the implemented part.
      </p>

      <form onSubmit={evaluate} className="flex items-end gap-4 mb-4">
        <Field label="Scope type">
          <Select value={scopeType} onChange={(e) => setScopeType(e.target.value)}>
            {SCOPE_TYPES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Target ID" hint="The batch, lot or shipment being released.">
          <Input value={targetId} onChange={(e) => setTargetId(e.target.value)} style={{ minWidth: 320 }} />
        </Field>
        {canEvaluateRelease(me) && (
          <Button type="submit" variant="secondary" disabled={evaluating || !targetId.trim()}>
            <Icon name="refresh" /> {evaluating ? "Evaluating…" : "Evaluate eligibility"}
          </Button>
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
          {evaluation?.eligible ? (
            <Banner tone="ok" title="Eligible for release">
              Every release gate passed as at {formatDateTime(evaluation.evaluation_time)}.
            </Banner>
          ) : evaluation ? (
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

            {canDecideRelease(me) && scope.state !== "RELEASED" && scope.state !== "REJECTED" && (
              <div className="flex gap-2 mt-4">
                <Button variant="success" disabled={!evaluation?.eligible} onClick={() => setDecision("release")}>
                  <Icon name="pen" /> Release
                </Button>
                <Button variant="secondary" onClick={() => setDecision("hold")}>
                  <Icon name="lock" /> Hold
                </Button>
                <Button variant="danger" onClick={() => setDecision("reject")}>
                  <Icon name="x" /> Reject
                </Button>
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
                          <td className="error-text">{b.message ?? JSON.stringify(b)}</td>
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
                          <td>{w.message ?? JSON.stringify(w)}</td>
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
  const { busy, error, run } = useCommand(onDone);
  const [reason, setReason] = useState("");
  const [password, setPassword] = useState("");

  const title = { release: "Release", hold: "Place on hold", reject: "Reject" }[decision];

  return (
    <Modal
      open
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          <Icon name="pen" /> {title} — {scope.scope_type} scope
        </span>
      }
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/release/v1/scopes/${scope.scope_id}/${decision}`, {
              idempotency_key: newIdempotencyKey(),
              scope_id: scope.scope_id,
              expected_version: scope.version,
              reason: reason || null,
              reauth_password: password || null,
            })
          );
        }}
      >
        <div className="sig-hint mb-3">
          A release decision is a signed act. If the signature policy requires a challenge, the backend
          will say so rather than committing unsigned.
        </div>
        <Field
          label="Reason"
          required={decision !== "release"}
          hint="Part of the permanent record."
        >
          <textarea
            className="input"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required={decision !== "release"}
          />
        </Field>
        <Field label="Password" hint="Fresh authentication for the step-up signature.">
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant={decision === "reject" ? "danger" : decision === "release" ? "success" : "primary"}
            disabled={busy}
          >
            {busy ? "Submitting…" : title}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
