"use client";

import { useState } from "react";
import { api, canApproveQms, canInvestigateQms, formatDate, newIdempotencyKey } from "@/lib/api";
import { useApiResource, useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { KpiRow, KpiTile } from "@/components/ui/KpiTile";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel, summarizeJson } from "@/components/ui/JsonPanel";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";

interface MetricRow {
  definition_id: string;
  metric_code: string;
  state?: string;
  frequency?: string;
  latest_snapshot?: {
    id: string;
    period_start: string;
    period_end: string;
    result: Record<string, unknown> | null;
    threshold_exceeded: boolean;
  } | null;
}

interface MetricsDashboard {
  site_id: string;
  metrics: MetricRow[];
}

const FREQUENCIES = ["monthly", "quarterly", "annual"];

export default function QualityMetricsPage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [reloadToken, setReloadToken] = useState(0);
  const [defineOpen, setDefineOpen] = useState(false);
  const [calculateOpen, setCalculateOpen] = useState(false);

  const dashboard = useApiResource<MetricsDashboard>(
    siteId ? `/quality-metrics/v1/dashboard?site_id=${siteId}&_=${reloadToken}` : null
  );

  const metrics = dashboard.data?.metrics ?? [];
  const breached = metrics.filter((m) => m.latest_snapshot?.threshold_exceeded).length;

  return (
    <div>
      <PageHead
        title="Quality metrics"
        subtitle="Metric definitions, periodic snapshots and the management review package."
        action={
          canInvestigateQms(me) || canApproveQms(me) ? (
            <div className="flex gap-2">
              {canApproveQms(me) && (
                <Button variant="secondary" onClick={() => setDefineOpen(true)}>
                  <Icon name="plus" /> Define metric
                </Button>
              )}
              <Button variant="primary" onClick={() => setCalculateOpen(true)}>
                <Icon name="refresh" /> Calculate snapshot
              </Button>
            </div>
          ) : undefined
        }
      />

      <KpiRow>
        <KpiTile label="Metrics defined" icon="gauge" value={metrics.length} />
        <KpiTile
          label="Threshold breached"
          icon="alert-triangle"
          value={breached}
          delta={breached > 0 ? "Latest snapshot exceeds threshold" : "All within threshold"}
          tone={breached > 0 ? "critical" : "ok"}
        />
        <KpiTile
          label="With snapshots"
          icon="history"
          value={metrics.filter((m) => m.latest_snapshot).length}
          delta="Metrics calculated at least once"
        />
      </KpiRow>

      <p className="hint mb-4">
        Metric values are a rebuildable read model (AG-11). A quality decision is made against the owning
        record, never against a number on this page.
      </p>

      {dashboard.error && (
        <Banner tone="critical" title="Could not load the metrics dashboard">
          {dashboard.error}
        </Banner>
      )}

      <Card>
        <CardHeader title="Metric definitions" meta={`${metrics.length} metric(s)`} />
        {metrics.length === 0 ? (
          <EmptyState icon="gauge">
            No quality metrics defined for this site yet.
          </EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Frequency</th>
                <th>State</th>
                <th>Latest period</th>
                <th>Result</th>
                <th>Threshold</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => (
                <tr key={m.definition_id}>
                  <td className="font-semibold tabular">{m.metric_code}</td>
                  <td className="fs-2">{m.frequency ?? "—"}</td>
                  <td>{m.state ? <WorkflowStatePill state={m.state} /> : <span className="text-muted">—</span>}</td>
                  <td className="tabular fs-2">
                    {m.latest_snapshot
                      ? `${formatDate(m.latest_snapshot.period_start)} – ${formatDate(m.latest_snapshot.period_end)}`
                      : "Never calculated"}
                  </td>
                  <td className="fs-2">
                    {m.latest_snapshot?.result ? (
                      <span>{summarizeJson(m.latest_snapshot.result)}</span>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                  <td>
                    {m.latest_snapshot ? (
                      m.latest_snapshot.threshold_exceeded ? (
                        <StatePill state="failed" icon="alert-triangle">
                          Exceeded
                        </StatePill>
                      ) : (
                        <StatePill state="accepted" icon="check-circle">
                          Within
                        </StatePill>
                      )
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {metrics.some((m) => m.latest_snapshot?.result) && (
        <Card pad className="mt-4">
          <p className="fact-k mb-3">Latest snapshot detail</p>
          {metrics
            .filter((m) => m.latest_snapshot?.result)
            .map((m) => (
              <div key={m.definition_id} className="mb-3">
                <p className="font-semibold fs-3 mb-1">{m.metric_code}</p>
                <JsonPanel title="Result" value={m.latest_snapshot?.result} />
              </div>
            ))}
        </Card>
      )}

      {canApproveQms(me) && siteId && (
        <ManagementReviewCard
          siteId={siteId}
          metrics={metrics}
          onDone={() => setReloadToken((n) => n + 1)}
        />
      )}

      {defineOpen && (
        <DefineMetricModal
          onClose={() => setDefineOpen(false)}
          onDone={() => {
            setDefineOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
      {calculateOpen && (
        <CalculateModal
          metrics={metrics}
          onClose={() => setCalculateOpen(false)}
          onDone={() => {
            setCalculateOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
    </div>
  );
}

function DefineMetricModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { siteId } = useSiteId();
  const { me } = useMe();
  const { busy, error, run } = useCommand(onDone);
  const [metricCode, setMetricCode] = useState("");
  const [sourceModel, setSourceModel] = useState("deviation_record");
  const [frequency, setFrequency] = useState(FREQUENCIES[0]);
  const [numerator, setNumerator] = useState("");
  const [denominator, setDenominator] = useState("");

  return (
    <Modal open onClose={onClose} title="Define a quality metric" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!siteId || !me) return;
          run(() =>
            api.post("/quality-metrics/v1/definitions", {
              idempotency_key: newIdempotencyKey(),
              site_id: siteId,
              metric_code: metricCode,
              owner_subject_id: me.user_id,
              source_model_id: sourceModel,
              frequency,
              numerator_definition: { description: numerator },
              denominator_definition: denominator ? { description: denominator } : null,
            })
          );
        }}
      >
        <div className="grid grid-cols-3 gap-4">
          <Field label="Metric code" required>
            <Input value={metricCode} onChange={(e) => setMetricCode(e.target.value)} placeholder="QM-DEV-ONTIME" required autoFocus />
          </Field>
          <Field label="Source model" required hint="The record type the metric counts.">
            <Input value={sourceModel} onChange={(e) => setSourceModel(e.target.value)} required />
          </Field>
          <Field label="Frequency" required>
            <Select value={frequency} onChange={(e) => setFrequency(e.target.value)}>
              {FREQUENCIES.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <Field label="Numerator definition" required hint="What is counted.">
          <textarea className="input" rows={2} value={numerator} onChange={(e) => setNumerator(e.target.value)} required />
        </Field>
        <Field label="Denominator definition" hint="Leave blank for a plain count rather than a rate.">
          <textarea className="input" rows={2} value={denominator} onChange={(e) => setDenominator(e.target.value)} />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !metricCode.trim() || !siteId}>
            {busy ? "Creating…" : "Define metric"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function CalculateModal({
  metrics,
  onClose,
  onDone,
}: {
  metrics: MetricRow[];
  onClose: () => void;
  onDone: () => void;
}) {
  const { siteId } = useSiteId();
  const { busy, error, run } = useCommand(onDone);
  const [definitionId, setDefinitionId] = useState(metrics[0]?.definition_id ?? "");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [numerator, setNumerator] = useState("");
  const [denominator, setDenominator] = useState("");
  const [thresholdExceeded, setThresholdExceeded] = useState(false);

  const value =
    numerator && denominator && Number(denominator) !== 0
      ? Number(numerator) / Number(denominator)
      : numerator
        ? Number(numerator)
        : null;

  return (
    <Modal open onClose={onClose} title="Calculate a metric snapshot" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!siteId) return;
          run(() =>
            api.post("/quality-metrics/v1/calculate", {
              idempotency_key: newIdempotencyKey(),
              site_id: siteId,
              metric_definition_id: definitionId,
              period_start: new Date(periodStart).toISOString(),
              period_end: new Date(periodEnd).toISOString(),
              result: {
                numerator: numerator ? Number(numerator) : null,
                denominator: denominator ? Number(denominator) : null,
                value,
              },
              threshold_exceeded: thresholdExceeded,
            })
          );
        }}
      >
        <Field label="Metric" required>
          <Select value={definitionId} onChange={(e) => setDefinitionId(e.target.value)} required>
            <option value="">Select a metric…</option>
            {metrics.map((m) => (
              <option key={m.definition_id} value={m.definition_id}>
                {m.metric_code}
              </option>
            ))}
          </Select>
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Period start" required>
            <Input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} required />
          </Field>
          <Field label="Period end" required>
            <Input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} required />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Numerator" required>
            <Input type="number" step="any" value={numerator} onChange={(e) => setNumerator(e.target.value)} required />
          </Field>
          <Field label="Denominator" hint="Blank for a plain count.">
            <Input type="number" step="any" value={denominator} onChange={(e) => setDenominator(e.target.value)} />
          </Field>
        </div>
        {value !== null && (
          <p className="hint mb-3">
            Recorded value: <span className="tabular font-semibold">{value}</span>
          </p>
        )}
        <label className="flex items-center gap-2 fs-2 mb-3">
          <input
            type="checkbox"
            checked={thresholdExceeded}
            onChange={(e) => setThresholdExceeded(e.target.checked)}
          />
          Threshold exceeded for this period
        </label>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !definitionId || !periodStart || !periodEnd}>
            {busy ? "Calculating…" : "Record snapshot"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ManagementReviewCard({
  siteId,
  metrics,
  onDone,
}: {
  siteId: string;
  metrics: MetricRow[];
  onDone: () => void;
}) {
  const withSnapshots = metrics.filter((m) => m.latest_snapshot?.id);
  const [selected, setSelected] = useState<string[]>([]);
  const [sigOpen, setSigOpen] = useState(false);

  function toggle(id: string) {
    setSelected((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  }

  return (
    <Card pad className="mt-4">
      <CardHeader title="Management review package" />
      <p className="fs-2 text-muted mb-3">
        Freezes the selected metric snapshots into one signed management-review package. The snapshot
        values themselves stay authoritative.
      </p>
      {withSnapshots.length === 0 ? (
        <p className="hint">No calculated snapshots to include yet.</p>
      ) : (
        <>
          <div className="mb-3">
            {withSnapshots.map((m) => (
              <label key={m.definition_id} className="flex items-center gap-2 fs-2" style={{ padding: "3px 0" }}>
                <input
                  type="checkbox"
                  checked={selected.includes(m.latest_snapshot!.id)}
                  onChange={() => toggle(m.latest_snapshot!.id)}
                />
                <span className="tabular font-semibold">{m.metric_code}</span>
                <span className="text-muted">
                  {formatDate(m.latest_snapshot!.period_start)} – {formatDate(m.latest_snapshot!.period_end)}
                </span>
              </label>
            ))}
          </div>
          <Button variant="primary" disabled={selected.length === 0} onClick={() => setSigOpen(true)}>
            Freeze &amp; sign package ({selected.length})
          </Button>
        </>
      )}

      {sigOpen && (
        <SignatureCeremony
          open
          onClose={() => setSigOpen(false)}
          onDone={() => {
            setSigOpen(false);
            setSelected([]);
            onDone();
          }}
          challengePath="/quality-metrics/v1/management-review-packages/signature-challenges"
          challengeBody={{ action: "management_review", snapshot_ids: selected }}
          action="management_review"
          title="Freeze management review package"
          summary={`${selected.length} snapshot(s) will be frozen into an immutable, signed package.`}
          submitLabel="Sign & freeze"
          onSign={(p) =>
            api.post("/quality-metrics/v1/management-review-packages", {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              site_id: siteId,
              snapshot_ids: selected,
            })
          }
        />
      )}
    </Card>
  );
}
