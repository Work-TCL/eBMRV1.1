"use client";

import { useEffect, useState } from "react";
import { api, ApiError, formatDateTime, hasPermission, listAll, newIdempotencyKey, type MutationReceipt } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { StatePill } from "@/components/ui/StatePill";
import { WorkflowActionButton } from "@/components/shared/WorkflowActionButton";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import type { EntityOption, EntityOptionsStatus } from "@/lib/hooks";

// GET /integrations/lims/{instance_id}/health
interface LimsHealth {
  instance_id: string;
  status: string;
  ownership_mode: string;
  pending_message_count: number;
  dead_letter_count: number;
  last_message_at: string | null;
}

// GET /integrations/lims
interface LimsInstanceSummary {
  id: string;
  instance_code: string;
  provider_type: string;
  status: string;
}

/** LIMS instances are provisioned as configuration data (no create screen in this app), so the list is
 * usually tiny — but showing real instance codes beats requiring the operator to already know a raw
 * UUID, and the manual-ID fallback below still covers an instance outside the 100-row cap. */
function useLimsInstances(): { options: EntityOption[]; status: EntityOptionsStatus } {
  const [options, setOptions] = useState<EntityOption[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("loading");
  useEffect(() => {
    let cancelled = false;
    listAll<LimsInstanceSummary>("/integrations/lims")
      .then((rows) => {
        if (cancelled) return;
      setOptions(rows.map((r) => ({ value: r.id, label: `${r.instance_code} - ${r.provider_type} (${r.status})` })));
        setStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return { options, status };
}

export default function LimsPage() {
  const { me } = useMe();
  const [instanceId, setInstanceId] = useState("");
  const [health, setHealth] = useState<LimsHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const instances = useLimsInstances();

  // POST .../reconcile checks integration_reconciliation.manage (Integration Administrator), not
  // lims_sample.cancel -- audit finding 2026-09-18: the old role list also wrongly included QA Reviewer,
  // who holds neither code.
  const canReconcile = hasPermission(me, "integration_reconciliation.manage");

  async function load(id = instanceId) {
    if (!id.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setHealth(await api.get<LimsHealth>(`/integrations/lims/${id.trim()}/health`));
      setInstanceId(id.trim());
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Couldn't load that instance's health. Check the instance and try again.");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHead
        title="LIMS integration"
        subtitle="Per-instance message health, dead letters and the reconciliation trigger."
      />

      <Card pad className="mb-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
          className="flex flex-wrap items-end gap-3"
        >
          <div style={{ minWidth: 260, maxWidth: 360, width: "100%" }}>
            <EntityPickerField
              label="LIMS instance"
              value={instanceId}
              onChange={setInstanceId}
              options={instances.options}
              status={instances.status}
              kind="LIMS instance"
            />
          </div>
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
