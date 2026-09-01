"use client";

import { useState } from "react";
import { api, ApiError, formatDateTime, holdsAnyRole, newIdempotencyKey, type MutationReceipt } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { StatePill } from "@/components/ui/StatePill";
import { WorkflowActionButton } from "@/components/shared/WorkflowActionButton";

// GET /integrations/lims/{instance_id}/health
interface LimsHealth {
  instance_id: string;
  status: string;
  ownership_mode: string;
  pending_message_count: number;
  dead_letter_count: number;
  last_message_at: string | null;
}

export default function LimsPage() {
  const { me } = useMe();
  const [instanceId, setInstanceId] = useState("");
  const [health, setHealth] = useState<LimsHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canReconcile = holdsAnyRole(me, ["Admin", "Integration Administrator", "QA Reviewer"]);

  async function load(id = instanceId) {
    if (!id.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setHealth(await api.get<LimsHealth>(`/integrations/lims/${id.trim()}/health`));
      setInstanceId(id.trim());
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHead
        title="LIMS integration"
        subtitle="Document 24 — per-instance message health, dead letters and the reconciliation trigger."
      />

      <p className="hint mb-4">
        The platform API exposes LIMS instances by ID, not as a browsable registry — enter an instance ID to
        see its health. A message monitor and dead-letter browser are not available as read endpoints in this
        build.
      </p>

      <Card pad className="mb-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
          className="flex items-end gap-3"
        >
          <Field label="LIMS instance ID">
            <Input value={instanceId} onChange={(e) => setInstanceId(e.target.value)} style={{ minWidth: 320 }} />
          </Field>
          <Button type="submit" variant="secondary" disabled={loading || !instanceId.trim()}>
            <Icon name="search" /> {loading ? "Checking…" : "Check health"}
          </Button>
        </form>
        {error && <p className="error-text mt-3">{error}</p>}
      </Card>

      {health && (
        <Card pad>
          <div className="flex justify-between items-center mb-3">
            <CardHeader title="Instance health" />
            <StatePill
              state={health.status === "active" ? "accepted" : health.status === "suspended" ? "failed" : "stale"}
              icon={health.status === "active" ? "check-circle" : "alert-triangle"}
            >
              {health.status}
            </StatePill>
          </div>
          <FactGrid>
            <Fact label="Ownership mode">{health.ownership_mode}</Fact>
            <Fact label="Pending messages">
              <span className={health.pending_message_count > 0 ? "" : "text-muted"}>{health.pending_message_count}</span>
            </Fact>
            <Fact label="Dead letters">
              {health.dead_letter_count > 0 ? (
                <StatePill state="failed" icon="alert-triangle">
                  {String(health.dead_letter_count)}
                </StatePill>
              ) : (
                <span className="text-muted">0</span>
              )}
            </Fact>
            <Fact label="Last message">{formatDateTime(health.last_message_at)}</Fact>
            <IdFact label="Instance ID" value={health.instance_id} />
          </FactGrid>

          {health.dead_letter_count > 0 && (
            <Banner tone="warn" title="Dead-lettered messages present">
              {health.dead_letter_count} message{health.dead_letter_count === 1 ? "" : "s"} could not be processed.
              Run reconciliation to re-sync sample and result state with the LIMS.
            </Banner>
          )}

          {canReconcile && (
            <div className="mt-3">
              <WorkflowActionButton
                label="Run reconciliation"
                title="Reconcile LIMS instance"
                summary="Compares platform sample/result state against the LIMS and records any differences. Does not auto-accept results."
                confirmLabel="Reconcile"
                variant="secondary"
                onDone={() => load()}
                onConfirm={() =>
                  api.post<MutationReceipt>(`/integrations/lims/${health.instance_id}/reconcile`, {
                    idempotency_key: newIdempotencyKey(),
                    instance_id: health.instance_id,
                  })
                }
              />
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
