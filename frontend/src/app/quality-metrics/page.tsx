"use client";

import { useState } from "react";
import { api, hasPermission, formatDate, newIdempotencyKey } from "@/lib/api";
import { useApiResource, useEntityOptions, useMe, useRequirePermission, useSiteId } from "@/lib/hooks";
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
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { humanizeLabel } from "@/lib/format";

interface DefinitionRow {
  id: string;
  metric_code: string;
  state: string;
  version: number;
  version_no: number;
  owner_subject_id: string;
  frequency: string;
}

interface EffectivenessCheckRow {
  id: string;
  site_id: string;
  source_module: string;
  source_record_id: string;
  source_record_label: string | null;
  criterion: string;
  metric_definition_id: string | null;
  observation_period_start: string;
  observation_period_end: string;
  due_date: string | null;
  result: string | null;
  evidence: Record<string, unknown> | null;
  escalation_required: boolean;
  escalation_rationale: string | null;
  state: string;
  version: number;
  created_at: string;
  evaluated_at: string | null;
}

const EFFECTIVENESS_RESULTS = ["pass", "fail", "inconclusive"];

// The 3 source_model_id values calculate_snapshot()'s AUTO_COMPUTE_SOURCE_MODELS dict recognizes
// (deviation/NCR/OOS, item #8 resolved 2026-10-09) -- omitting result for any other value still 422s.
const AUTO_COMPUTE_SOURCE_MODELS = ["deviation_record", "nonconformance_record", "oos_record"];

interface MetricRow {
  definition_id: string;
  metric_code: string;
  state?: string;
  frequency?: string;
  source_model_id?: string | null;
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
  const { me } = useRequirePermission("quality_metric.dashboard.view");
  const { siteId } = useSiteId();
  const [reloadToken, setReloadToken] = useState(0);
  const [defineOpen, setDefineOpen] = useState(false);
  const [calculateOpen, setCalculateOpen] = useState(false);
  const [releaseOpen, setReleaseOpen] = useState(false);

  const dashboard = useApiResource<MetricsDashboard>(
    siteId ? `/quality-metrics/v1/dashboard?site_id=${siteId}&_=${reloadToken}` : null
  );
  const definitions = useApiResource<DefinitionRow[]>(
    siteId ? `/quality-metrics/v1/definitions?site_id=${siteId}&_=${reloadToken}` : null
  );
  const draftDefinitions = (definitions.data ?? []).filter((d) => d.state === "DRAFT");

  const metrics = dashboard.data?.metrics ?? [];
  const breached = metrics.filter((m) => m.latest_snapshot?.threshold_exceeded).length;

  return (
    <div>
      <PageHead
        title="Quality metrics"
        subtitle="Metric definitions, periodic snapshots and the management review package."
        action={
          hasPermission(me, "quality_metric.definition.create") ||
          hasPermission(me, "quality_metric.definition.release") ||
          hasPermission(me, "quality_metric.calculate") ? (
            <div className="flex gap-2">
              {hasPermission(me, "quality_metric.definition.create") && (
                <Button variant="secondary" onClick={() => setDefineOpen(true)}>
                  <Icon name="plus" /> Define metric
                </Button>
              )}
              {hasPermission(me, "quality_metric.definition.release") && draftDefinitions.length > 0 && (
                <Button variant="secondary" onClick={() => setReleaseOpen(true)}>
                  <Icon name="check-circle" /> Release metric
                </Button>
              )}
              {hasPermission(me, "quality_metric.calculate") && (
                <Button variant="primary" onClick={() => setCalculateOpen(true)}>
                  <Icon name="refresh" /> Calculate snapshot
                </Button>
              )}
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

      {hasPermission(me, "quality_metric.management_review") && siteId && (
        <ManagementReviewCard
          siteId={siteId}
          metrics={metrics}
          onDone={() => setReloadToken((n) => n + 1)}
        />
      )}

      {siteId && (hasPermission(me, "effectiveness_check.create") || hasPermission(me, "effectiveness_check.view")) && (
        <EffectivenessChecksCard
          siteId={siteId}
          releasedDefinitions={(definitions.data ?? []).filter((d) => d.state === "RELEASED")}
          reloadToken={reloadToken}
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
      {releaseOpen && (
        <ReleaseMetricModal
          definitions={draftDefinitions}
          onClose={() => setReleaseOpen(false)}
          onDone={() => {
            setReleaseOpen(false);
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
  const entities = useEntityOptions();
  const { busy, error, run } = useCommand(onDone);
  const [metricCode, setMetricCode] = useState("");
  const [sourceModel, setSourceModel] = useState("deviation_record");
  const [frequency, setFrequency] = useState(FREQUENCIES[0]);
  const [numerator, setNumerator] = useState("");
  const [denominator, setDenominator] = useState("");
  const [ownerId, setOwnerId] = useState(me?.user_id ?? "");

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
              owner_subject_id: ownerId || me.user_id,
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
                  {humanizeLabel(f)}
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
        <EntityPickerField
          label="Owner"
          required
          hint="Defaults to you. Set someone else here if you intend to release this metric yourself -- release requires a signer independent of the owner."
          value={ownerId}
          onChange={setOwnerId}
          options={entities.users}
          status={entities.usersStatus}
          kind="user"
        />
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

  const selectedMetric = metrics.find((m) => m.definition_id === definitionId);
  // MET-FR-003/009 (count half) resolved 2026-10-09, project-owner-directed: for these 3 source models,
  // omitting Numerator lets calculate_snapshot() run a real internal COUNT(*) instead of requiring a
  // caller-supplied number. Every other source_model_id still needs Numerator (422 otherwise).
  const canAutoCompute = Boolean(selectedMetric?.source_model_id && AUTO_COMPUTE_SOURCE_MODELS.includes(selectedMetric.source_model_id));
  const autoCompute = canAutoCompute && !numerator.trim();

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
              // Omitting result entirely (rather than sending a numerator-less object) is what tells
              // calculate_snapshot() to run its own internal count for this source_model_id.
              result: autoCompute
                ? null
                : {
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
          <Field
            label="Numerator"
            required={!canAutoCompute}
            hint={canAutoCompute ? "Leave blank to auto-compute a real count for this source (deviation/NCR/OOS)." : undefined}
          >
            <Input type="number" step="any" value={numerator} onChange={(e) => setNumerator(e.target.value)} required={!canAutoCompute} />
          </Field>
          <Field label="Denominator" hint="Blank for a plain count.">
            <Input type="number" step="any" value={denominator} onChange={(e) => setDenominator(e.target.value)} disabled={autoCompute} />
          </Field>
        </div>
        {autoCompute ? (
          <p className="hint mb-3">
            Numerator left blank — this metric&apos;s source (<code>{selectedMetric?.source_model_id}</code>) will be
            auto-counted internally for the period instead.
          </p>
        ) : (
          value !== null && (
            <p className="hint mb-3">
              Recorded value: <span className="tabular font-semibold">{value}</span>
            </p>
          )
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

function ReleaseMetricModal({
  definitions,
  onClose,
  onDone,
}: {
  definitions: DefinitionRow[];
  onClose: () => void;
  onDone: () => void;
}) {
  const [definitionId, setDefinitionId] = useState(definitions[0]?.id ?? "");
  const [effectiveFrom, setEffectiveFrom] = useState(() => new Date().toISOString().slice(0, 10));
  const definition = definitions.find((d) => d.id === definitionId);

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={definitionId ? `/quality-metrics/v1/definitions/${definitionId}/signature-challenges` : ""}
      action="release"
      title="Release a quality metric"
      summary="Releases this metric definition for use -- signer must be independent of the definition's owner."
      submitLabel="Sign & release"
      submitVariant="success"
      disabled={!definitionId || !effectiveFrom}
      extraFields={
        <>
          <Field label="Metric" required>
            <Select value={definitionId} onChange={(e) => setDefinitionId(e.target.value)} required>
              <option value="">Select a draft metric…</option>
              {definitions.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.metric_code} (v{d.version_no})
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Effective from" required>
            <Input type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} required />
          </Field>
        </>
      }
      onSign={(p) =>
        api.post(`/quality-metrics/v1/definitions/${definitionId}/release`, {
          idempotency_key: p.idempotency_key,
          definition_id: definitionId,
          expected_version: definition?.version ?? 1,
          effective_from: new Date(effectiveFrom).toISOString(),
          challenge_id: p.challenge_id,
          reauth_password: p.reauth_password,
        })
      }
    />
  );
}

function EffectivenessChecksCard({
  siteId,
  releasedDefinitions,
  reloadToken,
  onDone,
}: {
  siteId: string;
  releasedDefinitions: DefinitionRow[];
  reloadToken: number;
  onDone: () => void;
}) {
  const { me } = useMe();
  const [createOpen, setCreateOpen] = useState(false);
  const [evaluating, setEvaluating] = useState<EffectivenessCheckRow | null>(null);

  const checks = useApiResource<EffectivenessCheckRow[]>(
    `/effectiveness/v1/checks?site_id=${siteId}&_=${reloadToken}`
  );
  const rows = checks.data ?? [];

  return (
    <Card pad className="mt-4">
      <div className="flex items-center justify-between mb-2">
        <CardHeader title="Effectiveness checks" meta={`${rows.length} check(s)`} />
        {hasPermission(me, "effectiveness_check.create") && (
          <Button variant="secondary" onClick={() => setCreateOpen(true)}>
            <Icon name="plus" /> Create effectiveness check
          </Button>
        )}
      </div>
      <p className="fs-2 text-muted mb-3">
        Proves a CAPA/SCAR/Field-Action correction actually worked, over an observation window -- a
        generic hook; no module calls this automatically, each check is raised deliberately.
      </p>
      {rows.length === 0 ? (
        <EmptyState icon="target">No effectiveness checks raised yet.</EmptyState>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Source</th>
              <th>Criterion</th>
              <th>Observation window</th>
              <th>State</th>
              <th>Result</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id}>
                <td className="fs-2 tabular">
                  {c.source_module} / {c.source_record_label ?? `${c.source_record_id.slice(0, 8)}…`}
                </td>
                <td className="fs-2" style={{ maxWidth: 320 }}>
                  {c.criterion}
                </td>
                <td className="fs-2 tabular">
                  {formatDate(c.observation_period_start)} – {formatDate(c.observation_period_end)}
                </td>
                <td>
                  <WorkflowStatePill state={c.state} />
                </td>
                <td>
                  {c.result ? (
                    <StatePill
                      state={c.result === "pass" ? "accepted" : c.result === "fail" ? "failed" : "unknown"}
                      icon={c.result === "pass" ? "check-circle" : c.result === "fail" ? "alert-triangle" : "help-circle"}
                    >
                      {humanizeLabel(c.result)}
                    </StatePill>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </td>
                <td>
                  {c.state === "OBSERVATION" && hasPermission(me, "effectiveness_check.evaluate") && (
                    <Button variant="secondary" size="sm" onClick={() => setEvaluating(c)}>
                      Evaluate
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {createOpen && (
        <CreateEffectivenessCheckModal
          siteId={siteId}
          releasedDefinitions={releasedDefinitions}
          onClose={() => setCreateOpen(false)}
          onDone={() => {
            setCreateOpen(false);
            onDone();
          }}
        />
      )}
      {evaluating && (
        <EvaluateEffectivenessCheckModal
          check={evaluating}
          onClose={() => setEvaluating(null)}
          onDone={() => {
            setEvaluating(null);
            onDone();
          }}
        />
      )}
    </Card>
  );
}

function CreateEffectivenessCheckModal({
  siteId,
  releasedDefinitions,
  onClose,
  onDone,
}: {
  siteId: string;
  releasedDefinitions: DefinitionRow[];
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const entities = useEntityOptions();
  const [sourceModule, setSourceModule] = useState("capa");
  const [sourceRecordId, setSourceRecordId] = useState("");
  const [criterion, setCriterion] = useState("");
  const [metricDefinitionId, setMetricDefinitionId] = useState("");
  const [periodStart, setPeriodStart] = useState(() => new Date().toISOString().slice(0, 10));
  const [periodEnd, setPeriodEnd] = useState("");

  function onSourceModuleChange(next: string) {
    // A record id picked under the previous module is meaningless for the new one.
    setSourceModule(next);
    setSourceRecordId("");
  }

  return (
    <Modal open onClose={onClose} title="Create an effectiveness check" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post("/effectiveness/v1/checks", {
              idempotency_key: newIdempotencyKey(),
              site_id: siteId,
              source_module: sourceModule,
              source_record_id: sourceRecordId,
              criterion,
              observation_period_start: new Date(periodStart).toISOString(),
              observation_period_end: new Date(periodEnd).toISOString(),
              metric_definition_id: metricDefinitionId || null,
            })
          );
        }}
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Source module" required hint="Which module's corrective action this proves out.">
            <Select value={sourceModule} onChange={(e) => onSourceModuleChange(e.target.value)}>
              <option value="capa">CAPA</option>
              <option value="scar">SCAR</option>
              <option value="field_action">Field Action</option>
              <option value="other">Other</option>
            </Select>
          </Field>
          {sourceModule === "capa" && (
            <EntityPickerField
              label="Source record"
              required
              hint="The CAPA this check observes."
              value={sourceRecordId}
              onChange={setSourceRecordId}
              options={entities.capas}
              status={entities.capasStatus}
              kind="CAPA"
            />
          )}
          {sourceModule === "scar" && (
            <EntityPickerField
              label="Source record"
              required
              hint="The SCAR this check observes."
              value={sourceRecordId}
              onChange={setSourceRecordId}
              options={entities.supplierCases}
              status={entities.supplierCasesStatus}
              kind="SCAR"
            />
          )}
          {sourceModule === "field_action" && (
            <EntityPickerField
              label="Source record"
              required
              hint="The Field Action this check observes."
              value={sourceRecordId}
              onChange={setSourceRecordId}
              options={entities.fieldActions}
              status={entities.fieldActionsStatus}
              kind="field action"
            />
          )}
          {sourceModule === "other" && (
            <Field label="Source record ID" required hint="No browsable list exists for 'Other' -- enter the id directly.">
              <Input value={sourceRecordId} onChange={(e) => setSourceRecordId(e.target.value)} required />
            </Field>
          )}
        </div>
        <Field label="Criterion" required hint="What 'effective' looks like -- the pass/fail bar for this observation.">
          <textarea className="input" rows={3} value={criterion} onChange={(e) => setCriterion(e.target.value)} required />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Observation period start" required>
            <Input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} required />
          </Field>
          <Field label="Observation period end" required>
            <Input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} required />
          </Field>
        </div>
        <Field label="Related metric" hint="Optional -- link to a released metric this check is evaluated alongside.">
          <Select value={metricDefinitionId} onChange={(e) => setMetricDefinitionId(e.target.value)}>
            <option value="">None</option>
            {releasedDefinitions.map((d) => (
              <option key={d.id} value={d.id}>
                {d.metric_code}
              </option>
            ))}
          </Select>
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={busy || !sourceRecordId.trim() || !criterion.trim() || !periodStart || !periodEnd}
          >
            {busy ? "Creating…" : "Create check"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function EvaluateEffectivenessCheckModal({
  check,
  onClose,
  onDone,
}: {
  check: EffectivenessCheckRow;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [result, setResult] = useState(EFFECTIVENESS_RESULTS[0]);
  const [evidence, setEvidence] = useState("");
  const [escalationRequired, setEscalationRequired] = useState(false);
  const [escalationRationale, setEscalationRationale] = useState("");

  return (
    <Modal open onClose={onClose} title="Evaluate effectiveness check" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/effectiveness/v1/checks/${check.id}/evaluate`, {
              idempotency_key: newIdempotencyKey(),
              check_id: check.id,
              expected_version: check.version,
              result,
              evidence: evidence ? { description: evidence } : null,
              escalation_required: escalationRequired,
              escalation_rationale: escalationRationale || null,
            })
          );
        }}
      >
        <p className="hint mb-3">{check.criterion}</p>
        <Field label="Result" required>
          <Select value={result} onChange={(e) => setResult(e.target.value)}>
            {EFFECTIVENESS_RESULTS.map((r) => (
              <option key={r} value={r}>
                {humanizeLabel(r)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Evidence" hint="What was observed over the window.">
          <textarea className="input" rows={3} value={evidence} onChange={(e) => setEvidence(e.target.value)} />
        </Field>
        <label className="flex items-center gap-2 fs-2 mb-3">
          <input type="checkbox" checked={escalationRequired} onChange={(e) => setEscalationRequired(e.target.checked)} />
          Escalation required
        </label>
        {escalationRequired && (
          <Field label="Escalation rationale" required>
            <textarea
              className="input"
              rows={2}
              value={escalationRationale}
              onChange={(e) => setEscalationRationale(e.target.value)}
              required
            />
          </Field>
        )}
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || (escalationRequired && !escalationRationale.trim())}>
            {busy ? "Saving…" : "Record evaluation"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
