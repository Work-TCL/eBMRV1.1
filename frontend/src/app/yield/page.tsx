"use client";

import { useEffect, useState } from "react";
import {
  api,
  ApiError,
  canEvaluateYield,
  canVerifyReconciliation,
  clientPagedFetcher,
  listAll,
  newIdempotencyKey,
  type MutationReceipt,
} from "@/lib/api";
import { useApiResource, useEntityOptions, useMe, useSiteId, type EntityOption, type EntityOptionsStatus } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/Table";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { Field, RowButtonSlot } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { UomSelect } from "@/components/ui/UomSelect";
import { Icon } from "@/components/ui/Icon";
import { Modal } from "@/components/ui/Modal";
import { Fact, FactGrid } from "@/components/ui/FactGrid";
import { StatePill } from "@/components/ui/StatePill";
import { JsonPanel, summarizeJson } from "@/components/ui/JsonPanel";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import {
  KeyValueRows,
  RepeatableRows,
  buildKvObject,
  buildRepeatArray,
  type KvRow,
  type RepeatRow,
  type RepeatSubField,
} from "@/components/shared/RepeatableFields";

// GET /reconciliation/v1/batches/{batch_id}/summary — app/modules/yield_reconciliation/commands.py::get_batch_summary
interface Calculation {
  id: string;
  calculation_type: string;
  phase_code: string | null;
  scope_type: string;
  device_unit_id: string | null;
  device_unit_serial: string | null;
  input_refs: Record<string, unknown> | null;
  theoretical_quantity: string | null;
  actual_quantity: string | null;
  uom: string | null;
  result: Record<string, unknown> | null;
  state: string;
  min_percent: string | null;
  max_percent: string | null;
  evaluated_by_username: string | null;
  evaluated_at: string | null;
  verified_by_username: string | null;
  verified_at: string | null;
  supersedes_id: string | null;
  supersedes_version: number | null;
  verified: boolean;
  version: number;
}

interface Reconciliation {
  id: string;
  reconciliation_type: string;
  item_ref: Record<string, unknown> | null;
  device_unit_id: string | null;
  device_unit_serial: string | null;
  quantities: Record<string, unknown> | null;
  uom: string | null;
  tolerance_rule: Record<string, unknown> | null;
  loss_reasons: Record<string, unknown>[] | null;
  external_reference: Record<string, unknown> | null;
  external_comparison: Record<string, unknown> | null;
  evaluated_by_username: string | null;
  verified_by_username: string | null;
  verified_at: string | null;
  supersedes_id: string | null;
  supersedes_version: number | null;
  state: string;
  version: number;
  verified?: boolean;
}

interface BatchSummary {
  batch_id: string;
  release_blocked: boolean;
  calculations: Calculation[];
  reconciliations: Reconciliation[];
}

type VerifyTarget =
  | { kind: "CALCULATION"; id: string; version: number; label: string }
  | { kind: "RECONCILIATION"; id: string; version: number; label: string };

const RESULT_STATE: Record<string, "accepted" | "failed" | "conflict" | "stale" | "missing"> = {
  VERIFIED: "accepted",
  WITHIN_TOLERANCE: "accepted",
  PASS: "accepted",
  OUT_OF_TOLERANCE: "failed",
  FAIL: "failed",
  PENDING_VERIFICATION: "stale",
  EVALUATED: "stale",
  DRAFT: "missing",
};

function resultPill(state: string) {
  const s = RESULT_STATE[state.toUpperCase()] ?? "conflict";
  return (
    <StatePill state={s} icon={s === "accepted" ? "check-circle" : s === "failed" ? "x" : "clock"}>
      {state}
    </StatePill>
  );
}

export default function YieldPage() {
  const { me, loading: meLoading } = useMe();
  const entities = useEntityOptions();
  const [batchId, setBatchId] = useState("");
  const [summary, setSummary] = useState<BatchSummary | null>(null);
  const [summaryVersion, setSummaryVersion] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verifyTarget, setVerifyTarget] = useState<VerifyTarget | null>(null);
  const [viewCalculation, setViewCalculation] = useState<Calculation | null>(null);
  const [viewReconciliation, setViewReconciliation] = useState<Reconciliation | null>(null);

  const [yieldOpen, setYieldOpen] = useState(false);
  const [potencyOpen, setPotencyOpen] = useState(false);
  const [materialOpen, setMaterialOpen] = useState(false);
  const [packagingOpen, setPackagingOpen] = useState(false);
  const [labelOpen, setLabelOpen] = useState(false);
  const [componentOpen, setComponentOpen] = useState(false);

  async function load(id = batchId) {
    if (!id.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setSummary(await api.get<BatchSummary>(`/reconciliation/v1/batches/${id.trim()}/summary`));
      setSummaryVersion((n) => n + 1);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }

  // clientPagedFetcher adapts the already-loaded `summary.calculations`/`.reconciliations` arrays (no
  // "every batch's calculations" endpoint exists — only a per-batch summary) to DataTable's page/sort/
  // search contract; recreated every render so it always closes over the latest `summary`, same pattern
  // as Vault's own `fetchVersions`.
  const fetchCalculations = clientPagedFetcher<Calculation>(
    async () => summary?.calculations ?? [],
    {
      searchText: (c) => `${c.calculation_type} ${c.phase_code ?? ""} ${c.state}`,
      sortValue: (c, sortBy) => (sortBy === "state" ? c.state : sortBy === "calculation_type" ? c.calculation_type : null),
    }
  );
  const fetchReconciliations = clientPagedFetcher<Reconciliation>(
    async () => summary?.reconciliations ?? [],
    {
      searchText: (r) => `${r.reconciliation_type} ${r.state} ${summarizeJson(r.item_ref)}`,
      sortValue: (r, sortBy) => (sortBy === "state" ? r.state : sortBy === "reconciliation_type" ? r.reconciliation_type : null),
    }
  );

  const calculationColumns: DataTableColumn<Calculation>[] = [
    { key: "calculation_type", header: "Type", sortable: true, render: (c) => <span className="fs-2">{c.calculation_type}</span> },
    { key: "phase_code", header: "Phase", render: (c) => <span className="fs-2">{c.phase_code ?? "—"}</span> },
    {
      key: "theoretical_quantity",
      header: "Theoretical",
      align: "right",
      render: (c) => <span className="tabular fs-2">{c.theoretical_quantity ?? "—"} {c.uom ?? ""}</span>,
    },
    {
      key: "actual_quantity",
      header: "Actual",
      align: "right",
      render: (c) => <span className="tabular fs-2">{c.actual_quantity ?? "—"} {c.uom ?? ""}</span>,
    },
    {
      key: "limits",
      header: "Limits %",
      align: "right",
      render: (c) => <span className="tabular fs-2">{c.min_percent ?? "—"} – {c.max_percent ?? "—"}</span>,
    },
    { key: "state", header: "State", sortable: true, render: (c) => resultPill(c.state) },
    {
      key: "open",
      header: "",
      align: "right",
      render: (c) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={(e) => {
            e.stopPropagation();
            setViewCalculation(c);
          }}
        >
          View
        </Button>
      ),
    },
  ];

  const reconciliationColumns: DataTableColumn<Reconciliation>[] = [
    { key: "reconciliation_type", header: "Type", sortable: true, render: (r) => <span className="fs-2">{r.reconciliation_type}</span> },
    {
      key: "item_ref",
      header: "Item",
      render: (r) => <span className="fs-2" style={{ wordBreak: "break-word" }}>{summarizeJson(r.item_ref)}</span>,
    },
    {
      key: "quantities",
      header: "Quantities",
      align: "right",
      render: (r) => (
        <span className="tabular fs-2" style={{ wordBreak: "break-word" }}>
          {summarizeJson(r.quantities)} {r.uom ?? ""}
        </span>
      ),
    },
    { key: "state", header: "State", sortable: true, render: (r) => resultPill(r.state) },
    {
      key: "open",
      header: "",
      align: "right",
      render: (r) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={(e) => {
            e.stopPropagation();
            setViewReconciliation(r);
          }}
        >
          View
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHead
        title="Yield & reconciliation"
        subtitle="Theoretical vs actual quantities, tolerance outcome, and the verifier signature that clears a batch for release."
      />

      {/* `items-start` (not `items-end`) — `EntityPickerField`'s "Batch" control can carry its own hint
          text (empty/error states), which would make that Field taller than a bare Button next to it;
          `RowButtonSlot` keeps the button level with the input either way instead of only working by
          coincidence when no hint happens to be showing. */}
      <Card pad className="mb-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
          className="flex flex-wrap items-start gap-4"
        >
          <EntityPickerField
            label="Batch"
            value={batchId}
            onChange={setBatchId}
            options={entities.batches}
            status={entities.batchesStatus}
            kind="batch"
          />
          <RowButtonSlot>
            <Button type="submit" variant="secondary" disabled={loading || !batchId.trim()}>
              <Icon name="search" /> {loading ? "Loading…" : "Load batch summary"}
            </Button>
          </RowButtonSlot>
        </form>
        {error && <p className="error-text mt-3">{error}</p>}
      </Card>

      {summary && (
        <>
          <Banner
            tone={summary.release_blocked ? "critical" : "ok"}
            title={summary.release_blocked ? "Release blocked" : "No unresolved calculations or reconciliations"}
          >
            {summary.release_blocked
              ? "One or more yield calculations or reconciliations for this batch are unresolved or out of tolerance."
              : "Every calculation and reconciliation on this batch is within tolerance and verified."}
          </Banner>

          <Card className="mt-4">
            <CardHeader
              title={`Calculations (${summary.calculations.length})`}
              meta={
                meLoading ? (
                  <Skeleton width={190} height={30} radius="var(--radius-md)" />
                ) : canEvaluateYield(me) ? (
                  <div className="flex gap-2">
                    <Button size="sm" variant="secondary" onClick={() => setYieldOpen(true)}>
                      <Icon name="plus" /> Evaluate yield
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => setPotencyOpen(true)}>
                      <Icon name="plus" /> Evaluate potency
                    </Button>
                  </div>
                ) : undefined
              }
            />
            {summary.calculations.length === 0 ? (
              <EmptyState icon="gauge">No yield or potency calculations recorded for this batch.</EmptyState>
            ) : (
              <DataTable
                columns={calculationColumns}
                fetchPage={fetchCalculations}
                rowKey={(c) => c.id}
                searchPlaceholder="Search type, phase or state…"
                defaultSort={{ by: "calculation_type", dir: "asc" }}
                onRowClick={setViewCalculation}
                reloadToken={summaryVersion}
              />
            )}
          </Card>

          <Card className="mt-4">
            <CardHeader
              title={`Reconciliations (${summary.reconciliations.length})`}
              meta={
                meLoading ? (
                  <Skeleton width={260} height={30} radius="var(--radius-md)" />
                ) : canEvaluateYield(me) ? (
                  <div className="flex gap-2">
                    <Button size="sm" variant="secondary" onClick={() => setMaterialOpen(true)}>
                      <Icon name="plus" /> Material
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => setPackagingOpen(true)}>
                      <Icon name="plus" /> Packaging
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => setLabelOpen(true)}>
                      <Icon name="plus" /> Label
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => setComponentOpen(true)}>
                      <Icon name="plus" /> Component
                    </Button>
                  </div>
                ) : undefined
              }
            />
            {summary.reconciliations.length === 0 ? (
              <EmptyState icon="list-checks">No material, packaging, label or component reconciliations recorded.</EmptyState>
            ) : (
              <DataTable
                columns={reconciliationColumns}
                fetchPage={fetchReconciliations}
                rowKey={(r) => r.id}
                searchPlaceholder="Search type, item or state…"
                defaultSort={{ by: "reconciliation_type", dir: "asc" }}
                onRowClick={setViewReconciliation}
                reloadToken={summaryVersion}
              />
            )}
          </Card>
        </>
      )}

      {viewCalculation && (
        <Modal
          open
          onClose={() => setViewCalculation(null)}
          title={`${viewCalculation.calculation_type}${viewCalculation.phase_code ? ` / ${viewCalculation.phase_code}` : ""}`}
        >
          <FactGrid>
            <Fact label="Scope type">{viewCalculation.scope_type}</Fact>
            {viewCalculation.device_unit_id && (
              <Fact label="Device unit">{viewCalculation.device_unit_serial ?? viewCalculation.device_unit_id}</Fact>
            )}
            <Fact label="Theoretical">{viewCalculation.theoretical_quantity ?? "—"} {viewCalculation.uom ?? ""}</Fact>
            <Fact label="Actual">{viewCalculation.actual_quantity ?? "—"} {viewCalculation.uom ?? ""}</Fact>
            <Fact label="Limits %">{viewCalculation.min_percent ?? "—"} – {viewCalculation.max_percent ?? "—"}</Fact>
            <Fact label="State">{resultPill(viewCalculation.state)}</Fact>
            <Fact label="Evaluated by">{viewCalculation.evaluated_by_username ?? "—"}</Fact>
            {viewCalculation.verified && (
              <>
                <Fact label="Verified by">{viewCalculation.verified_by_username ?? "—"}</Fact>
                <Fact label="Verified at">{viewCalculation.verified_at ?? "—"}</Fact>
              </>
            )}
            {viewCalculation.supersedes_id && (
              <Fact label="Supersedes">
                {viewCalculation.supersedes_version != null ? `v${viewCalculation.supersedes_version}` : viewCalculation.supersedes_id}
              </Fact>
            )}
            <Fact label="Record version">{viewCalculation.version}</Fact>
          </FactGrid>
          <JsonPanel title="Input references" value={viewCalculation.input_refs} />
          <JsonPanel title="Result" value={viewCalculation.result} />
          {!viewCalculation.verified && canVerifyReconciliation(me) && (
            <Button
              className="mt-3"
              variant="secondary"
              onClick={() =>
                setVerifyTarget({
                  kind: "CALCULATION",
                  id: viewCalculation.id,
                  version: viewCalculation.version,
                  label: `${viewCalculation.calculation_type}${viewCalculation.phase_code ? ` / ${viewCalculation.phase_code}` : ""}`,
                })
              }
            >
              Verify
            </Button>
          )}
        </Modal>
      )}

      {viewReconciliation && (
        <Modal open onClose={() => setViewReconciliation(null)} title={viewReconciliation.reconciliation_type}>
          <FactGrid>
            {viewReconciliation.device_unit_id && (
              <Fact label="Device unit">{viewReconciliation.device_unit_serial ?? viewReconciliation.device_unit_id}</Fact>
            )}
            <Fact label="Item">{summarizeJson(viewReconciliation.item_ref)}</Fact>
            <Fact label="Quantities">{summarizeJson(viewReconciliation.quantities)} {viewReconciliation.uom ?? ""}</Fact>
            <Fact label="Tolerance rule">{summarizeJson(viewReconciliation.tolerance_rule)}</Fact>
            <Fact label="State">{resultPill(viewReconciliation.state)}</Fact>
            <Fact label="Evaluated by">{viewReconciliation.evaluated_by_username ?? "—"}</Fact>
            {viewReconciliation.verified && (
              <>
                <Fact label="Verified by">{viewReconciliation.verified_by_username ?? "—"}</Fact>
                <Fact label="Verified at">{viewReconciliation.verified_at ?? "—"}</Fact>
              </>
            )}
            {viewReconciliation.supersedes_id && (
              <Fact label="Supersedes">
                {viewReconciliation.supersedes_version != null ? `v${viewReconciliation.supersedes_version}` : viewReconciliation.supersedes_id}
              </Fact>
            )}
            <Fact label="Record version">{viewReconciliation.version}</Fact>
          </FactGrid>
          {viewReconciliation.loss_reasons && viewReconciliation.loss_reasons.length > 0 && (
            <JsonPanel title="Loss reasons" value={viewReconciliation.loss_reasons} />
          )}
          {viewReconciliation.external_reference && (
            <JsonPanel title="External (ERP/WMS) reference" value={viewReconciliation.external_reference} />
          )}
          {viewReconciliation.external_comparison && (
            <JsonPanel title="External comparison outcome" value={viewReconciliation.external_comparison} />
          )}
          {!viewReconciliation.verified && canVerifyReconciliation(me) && (
            <Button
              className="mt-3"
              variant="secondary"
              onClick={() =>
                setVerifyTarget({
                  kind: "RECONCILIATION",
                  id: viewReconciliation.id,
                  version: viewReconciliation.version,
                  label: viewReconciliation.reconciliation_type,
                })
              }
            >
              Verify
            </Button>
          )}
        </Modal>
      )}

      {yieldOpen && (
        <Modal open onClose={() => setYieldOpen(false)} title="Evaluate yield" large>
          <EvaluateYieldCard
            onEvaluated={() => {
              setYieldOpen(false);
              load();
            }}
            defaultBatchId={batchId}
            entities={entities}
          />
        </Modal>
      )}

      {potencyOpen && (
        <Modal open onClose={() => setPotencyOpen(false)} title="Evaluate potency" large>
          <EvaluatePotencyCard
            onEvaluated={() => {
              setPotencyOpen(false);
              load();
            }}
            defaultBatchId={batchId}
            entities={entities}
          />
        </Modal>
      )}

      {materialOpen && (
        <Modal open onClose={() => setMaterialOpen(false)} title="Evaluate material reconciliation" large>
          <ReconciliationCard
            title="Evaluate material reconciliation"
            postPath="/reconciliation/v1/material/evaluate"
            reconciliationType="MATERIAL"
            onEvaluated={() => {
              setMaterialOpen(false);
              load();
            }}
            defaultBatchId={batchId}
            entities={entities}
          />
        </Modal>
      )}

      {packagingOpen && (
        <Modal open onClose={() => setPackagingOpen(false)} title="Evaluate packaging reconciliation" large>
          <ReconciliationCard
            title="Evaluate packaging reconciliation"
            postPath="/reconciliation/v1/packaging/evaluate"
            reconciliationType="PACKAGING"
            onEvaluated={() => {
              setPackagingOpen(false);
              load();
            }}
            defaultBatchId={batchId}
            entities={entities}
          />
        </Modal>
      )}

      {labelOpen && (
        <Modal open onClose={() => setLabelOpen(false)} title="Evaluate label reconciliation" large>
          <EvaluateLabelReconciliationCard
            onEvaluated={() => {
              setLabelOpen(false);
              load();
            }}
            entities={entities}
          />
        </Modal>
      )}

      {componentOpen && (
        <Modal open onClose={() => setComponentOpen(false)} title="Evaluate component reconciliation" large>
          <EvaluateComponentReconciliationCard
            onEvaluated={() => {
              setComponentOpen(false);
              load();
            }}
            defaultBatchId={batchId}
            entities={entities}
          />
        </Modal>
      )}

      {verifyTarget && (
        <SignatureCeremony
          open
          onClose={() => setVerifyTarget(null)}
          onDone={() => {
            setVerifyTarget(null);
            setViewCalculation(null);
            setViewReconciliation(null);
            load();
          }}
          challengePath={`/reconciliation/v1/${verifyTarget.id}/signature-challenges`}
          challengeBody={{ record_kind: verifyTarget.kind }}
          action="verify"
          title={`Verify - ${verifyTarget.label}`}
          summary={`You are attesting that this ${verifyTarget.kind.toLowerCase()} record is complete and correct. A verified record no longer blocks release.`}
          submitLabel="Sign & verify"
          submitVariant="success"
          onSign={(p) =>
            api.post<MutationReceipt>(`/reconciliation/v1/${verifyTarget.id}/verify`, {
              ...p,
              record_kind: verifyTarget.kind,
              record_id: verifyTarget.id,
              expected_version: verifyTarget.version,
            })
          }
        />
      )}
    </div>
  );
}

function EvaluateYieldCard({
  onEvaluated,
  defaultBatchId,
  entities,
}: {
  onEvaluated: () => void;
  defaultBatchId: string;
  entities: ReturnType<typeof useEntityOptions>;
}) {
  const [batchId, setBatchId] = useState(defaultBatchId);
  const [phaseCode, setPhaseCode] = useState("");
  const [theoretical, setTheoretical] = useState("");
  const [actual, setActual] = useState("");
  const [uom, setUom] = useState("kg");
  const [minPercent, setMinPercent] = useState("");
  const [maxPercent, setMaxPercent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      await api.post<MutationReceipt>("/manufacturing-calculations/v1/yield/evaluate", {
        idempotency_key: newIdempotencyKey(),
        batch_id: batchId.trim(),
        scope_type: "BATCH",
        phase_code: phaseCode.trim() || null,
        theoretical_quantity: theoretical.trim(),
        actual_quantity: actual.trim(),
        uom: uom.trim(),
        min_percent: minPercent.trim() || null,
        max_percent: maxPercent.trim() || null,
      });
      setDone(true);
      onEvaluated();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Evaluation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad>
      <CardHeader title="Evaluate yield" />
      <p className="fs-2 text-muted mb-3">
        Runs the yield formula (actual ÷ theoretical × 100) against the batch and records the tolerance
        outcome. Enter the exact measured quantities - they are never rounded.
      </p>
      <form onSubmit={submit} className="grid grid-cols-3 gap-4">
        <EntityPickerField
          label="Batch"
          required
          value={batchId}
          onChange={setBatchId}
          options={entities.batches}
          status={entities.batchesStatus}
          kind="batch"
        />
        <Field label="Phase code" hint="Optional - omit for a whole-batch yield.">
          <Input value={phaseCode} onChange={(e) => setPhaseCode(e.target.value)} />
        </Field>
        <UomSelect value={uom} onChange={setUom} required />
        <Field label="Theoretical quantity" required>
          <Input value={theoretical} onChange={(e) => setTheoretical(e.target.value)} required />
        </Field>
        <Field label="Actual quantity" required>
          <Input value={actual} onChange={(e) => setActual(e.target.value)} required />
        </Field>
        <div />
        <Field label="Min percent" hint="Lower tolerance limit.">
          <Input value={minPercent} onChange={(e) => setMinPercent(e.target.value)} />
        </Field>
        <Field label="Max percent" hint="Upper tolerance limit.">
          <Input value={maxPercent} onChange={(e) => setMaxPercent(e.target.value)} />
        </Field>
        <div />
      </form>
      {error && <p className="error-text mt-2">{error}</p>}
      {done && <p className="fs-2 mt-2">Yield evaluated - see the calculations table above.</p>}
      <div className="mt-3">
        <Button
          type="submit"
          variant="primary"
          onClick={submit}
          disabled={busy || !batchId.trim() || !theoretical.trim() || !actual.trim() || !uom.trim()}
        >
          {busy ? "Evaluating…" : "Evaluate yield"}
        </Button>
      </div>
    </Card>
  );
}

const LOSS_REASON_SUBFIELDS: RepeatSubField[] = [
  { name: "category", label: "Category", required: true },
  { name: "description", label: "Description", required: true },
  { name: "quantity", label: "Quantity", type: "number" },
];

/** The exact `quantities` key vocabulary `yield_reconciliation/models.py` accepts: `QUANTITY_CATEGORIES`
 * (issued/consumed/returned/samples/rejected/destroyed/approved_loss) for MATERIAL/PACKAGING/LABEL, plus
 * `assembled`/`scrapped` (`COMPONENT_QUANTITY_CATEGORIES`) for COMPONENT. `issued` is the only key the
 * backend actually requires — `_persist_reconciliation` raises on a missing `quantities["issued"]`, while
 * every other category defaults to "0" server-side when omitted (`quantities.get(k, "0")`), so `build()`
 * only sends the ones the user filled in. Replaces a raw key-value editor whose hint text told the user
 * to type these exact key names by hand, with no validation that they had. `item_ref` stays a real
 * key-value editor below (unlike `quantities`, its shape genuinely varies by what's being reconciled —
 * e.g. `material_lot_id` vs a device unit's own `serial_number` — and nothing downstream validates its
 * keys the way `quantities`' categories are validated). */
function useQuantityFields(includeComponentCategories = false) {
  const [issued, setIssued] = useState("");
  const [consumed, setConsumed] = useState("");
  const [returned, setReturned] = useState("");
  const [samples, setSamples] = useState("");
  const [rejected, setRejected] = useState("");
  const [destroyed, setDestroyed] = useState("");
  const [approvedLoss, setApprovedLoss] = useState("");
  const [assembled, setAssembled] = useState("");
  const [scrapped, setScrapped] = useState("");

  function build(): Record<string, string> {
    const q: Record<string, string> = { issued: issued.trim() };
    if (consumed.trim()) q.consumed = consumed.trim();
    if (returned.trim()) q.returned = returned.trim();
    if (samples.trim()) q.samples = samples.trim();
    if (rejected.trim()) q.rejected = rejected.trim();
    if (destroyed.trim()) q.destroyed = destroyed.trim();
    if (approvedLoss.trim()) q.approved_loss = approvedLoss.trim();
    if (includeComponentCategories) {
      if (assembled.trim()) q.assembled = assembled.trim();
      if (scrapped.trim()) q.scrapped = scrapped.trim();
    }
    return q;
  }

  const fields = (
    <div>
      <label className="label">Quantities</label>
      <div className="grid grid-cols-3 gap-3 mt-1">
        <Field label="Issued" required>
          <Input type="number" step="any" value={issued} onChange={(e) => setIssued(e.target.value)} required />
        </Field>
        <Field label="Consumed">
          <Input type="number" step="any" value={consumed} onChange={(e) => setConsumed(e.target.value)} />
        </Field>
        <Field label="Returned">
          <Input type="number" step="any" value={returned} onChange={(e) => setReturned(e.target.value)} />
        </Field>
        <Field label="Samples">
          <Input type="number" step="any" value={samples} onChange={(e) => setSamples(e.target.value)} />
        </Field>
        <Field label="Rejected">
          <Input type="number" step="any" value={rejected} onChange={(e) => setRejected(e.target.value)} />
        </Field>
        <Field label="Destroyed">
          <Input type="number" step="any" value={destroyed} onChange={(e) => setDestroyed(e.target.value)} />
        </Field>
        <Field label="Approved loss" hint="Requires a loss reason below when non-zero.">
          <Input type="number" step="any" value={approvedLoss} onChange={(e) => setApprovedLoss(e.target.value)} />
        </Field>
        {includeComponentCategories && (
          <>
            <Field label="Assembled">
              <Input type="number" step="any" value={assembled} onChange={(e) => setAssembled(e.target.value)} />
            </Field>
            <Field label="Scrapped">
              <Input type="number" step="any" value={scrapped} onChange={(e) => setScrapped(e.target.value)} />
            </Field>
          </>
        )}
      </div>
    </div>
  );

  return { issued, build, fields };
}

/** The `{type, value, inclusive}` shape is identical across every reconciliation command
 * (`tolerance_rule: dict`) — structured fields here instead of a raw `kv` editor since the shape is
 * fixed and documented, not genuinely free-form. */
function ToleranceRuleFields({
  type,
  setType,
  value,
  setValue,
  inclusive,
  setInclusive,
}: {
  type: string;
  setType: (v: string) => void;
  value: string;
  setValue: (v: string) => void;
  inclusive: string;
  setInclusive: (v: string) => void;
}) {
  return (
    <>
      <Field label="Tolerance type" required>
        <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="percentage">Percentage</option>
          <option value="absolute">Absolute</option>
        </select>
      </Field>
      <Field label="Tolerance value" required>
        <Input value={value} onChange={(e) => setValue(e.target.value)} required />
      </Field>
      <Field label="Inclusive?" required>
        <select className="input" value={inclusive} onChange={(e) => setInclusive(e.target.value)}>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      </Field>
    </>
  );
}

function EvaluatePotencyCard({
  onEvaluated,
  defaultBatchId,
  entities,
}: {
  onEvaluated: () => void;
  defaultBatchId: string;
  entities: ReturnType<typeof useEntityOptions>;
}) {
  const [batchId, setBatchId] = useState(defaultBatchId);
  const [phaseCode, setPhaseCode] = useState("");
  const [ruleId, setRuleId] = useState("");
  const [inputs, setInputs] = useState<KvRow[]>([]);
  const [uom, setUom] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      await api.post<MutationReceipt>("/manufacturing-calculations/v1/potency/evaluate", {
        idempotency_key: newIdempotencyKey(),
        batch_id: batchId.trim(),
        scope_type: "BATCH",
        phase_code: phaseCode.trim() || null,
        rule_id: ruleId.trim(),
        inputs: buildKvObject(inputs),
        uom: uom.trim() || null,
      });
      setDone(true);
      onEvaluated();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Evaluation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad>
      <CardHeader title="Evaluate potency" />
      <p className="fs-2 text-muted mb-3">
      Runs a customer-authored, released potency rule - there is no default pharmaceutical
        formula in this codebase. The rule must already be released at the given rule ID (see /rules).
      </p>
      <form onSubmit={submit} className="grid grid-cols-3 gap-4">
        <EntityPickerField
          label="Batch"
          required
          value={batchId}
          onChange={setBatchId}
          options={entities.batches}
          status={entities.batchesStatus}
          kind="batch"
        />
        <Field label="Phase code" hint="Optional - omit for a whole-batch calculation.">
          <Input value={phaseCode} onChange={(e) => setPhaseCode(e.target.value)} />
        </Field>
        <EntityPickerField
          label="Rule ID"
          required
          value={ruleId}
          onChange={setRuleId}
          options={entities.rules}
          status={entities.rulesStatus}
          kind="rule"
        />
        <UomSelect value={uom} onChange={setUom} hint="Optional." />
      </form>
      <div className="mt-3">
        <KeyValueRows
          label="Rule inputs"
          hint="The exact inputs the released rule expects. At least one is required."
          value={inputs}
          onChange={setInputs}
        />
      </div>
      {error && <p className="error-text mt-2">{error}</p>}
      {done && <p className="fs-2 mt-2">Potency evaluated - see the calculations table above.</p>}
      <div className="mt-3">
        <Button
          type="submit"
          variant="primary"
          onClick={submit}
          disabled={busy || !batchId.trim() || !ruleId.trim() || inputs.length === 0}
        >
          {busy ? "Evaluating…" : "Evaluate potency"}
        </Button>
      </div>
    </Card>
  );
}

/** Material and packaging reconciliation are the same `EvaluateReconciliationCommand` shape end to end —
 * only the endpoint path and the required `reconciliation_type` value differ (the backend rejects a
 * mismatch) — so one component covers both rather than two near-duplicate ones. */
function ReconciliationCard({
  title,
  postPath,
  reconciliationType,
  onEvaluated,
  defaultBatchId,
  entities,
}: {
  title: string;
  postPath: string;
  reconciliationType: "MATERIAL" | "PACKAGING";
  onEvaluated: () => void;
  defaultBatchId: string;
  entities: ReturnType<typeof useEntityOptions>;
}) {
  const [batchId, setBatchId] = useState(defaultBatchId);
  const [itemRef, setItemRef] = useState<KvRow[]>([]);
  const quantityFields = useQuantityFields();
  const [uom, setUom] = useState("");
  const [toleranceType, setToleranceType] = useState("percentage");
  const [toleranceValue, setToleranceValue] = useState("");
  const [toleranceInclusive, setToleranceInclusive] = useState("true");
  const [lossReasons, setLossReasons] = useState<RepeatRow[]>([]);
  const [linkedDeviationId, setLinkedDeviationId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      await api.post<MutationReceipt>(postPath, {
        idempotency_key: newIdempotencyKey(),
        batch_id: batchId.trim(),
        reconciliation_type: reconciliationType,
        item_ref: buildKvObject(itemRef),
        quantities: quantityFields.build(),
        uom: uom.trim(),
        tolerance_rule: { type: toleranceType, value: toleranceValue.trim(), inclusive: toleranceInclusive === "true" },
        loss_reasons: lossReasons.length > 0 ? buildRepeatArray(LOSS_REASON_SUBFIELDS, lossReasons) : null,
        linked_deviation_id: linkedDeviationId.trim() || null,
      });
      setDone(true);
      onEvaluated();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Evaluation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad>
      <CardHeader title={title} />
      <form onSubmit={submit} className="grid grid-cols-3 gap-4">
        <EntityPickerField
          label="Batch"
          required
          value={batchId}
          onChange={setBatchId}
          options={entities.batches}
          status={entities.batchesStatus}
          kind="batch"
        />
        <UomSelect value={uom} onChange={setUom} required />
        <EntityPickerField
          label="Linked deviation ID"
          hint="An existing QMS deviation - only relevant alongside an approved_loss quantity."
          value={linkedDeviationId}
          onChange={setLinkedDeviationId}
          options={entities.deviations}
          status={entities.deviationsStatus}
          kind="deviation"
        />
        <ToleranceRuleFields
          type={toleranceType}
          setType={setToleranceType}
          value={toleranceValue}
          setValue={setToleranceValue}
          inclusive={toleranceInclusive}
          setInclusive={setToleranceInclusive}
        />
      </form>
      <div className="grid grid-cols-2 gap-4 mt-3">
        <KeyValueRows label="Item reference" hint="What is being reconciled, e.g. material_lot_id → a lot ID." value={itemRef} onChange={setItemRef} />
        {quantityFields.fields}
      </div>
      <div className="mt-3">
        <RepeatableRows
          label="Loss reasons"
          hint="Required when a non-zero approved_loss quantity is entered above - each entry needs a category and description."
          itemLabel="Loss reason"
          subFields={LOSS_REASON_SUBFIELDS}
          value={lossReasons}
          onChange={setLossReasons}
        />
      </div>
      {error && <p className="error-text mt-2">{error}</p>}
      {done && <p className="fs-2 mt-2">Reconciliation evaluated - see the reconciliations table above.</p>}
      <div className="mt-3">
        <Button
          type="submit"
          variant="primary"
          onClick={submit}
          disabled={busy || !batchId.trim() || !uom.trim() || itemRef.length === 0 || !quantityFields.issued.trim() || !toleranceValue.trim()}
        >
          {busy ? "Evaluating…" : "Evaluate reconciliation"}
        </Button>
      </div>
    </Card>
  );
}

/** Local to this file only (per the picker-fix scope) — `GET /packaging/v1/runs` has no shared hook in
 * `lib/hooks.ts` yet since no other page needs it. Same "fetch once, map to {value,label}" shape as
 * `useEntityOptions`'s other fields; `listAll` handles the paginated envelope
 * (`packaging/router.py::list_packaging_runs` returns the same `{items, ...}` shape every other
 * `listAll` consumer does). */
function usePackagingRuns(): { options: EntityOption[]; status: EntityOptionsStatus } {
  const [options, setOptions] = useState<EntityOption[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    listAll<{ id: string; line_ref: string; state: string }>("/packaging/v1/runs")
      .then((rows) => {
        if (cancelled) return;
        setOptions(rows.map((r) => ({ value: r.id, label: `${r.line_ref} (${r.state})` })));
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

function EvaluateLabelReconciliationCard({
  onEvaluated,
  entities,
}: {
  onEvaluated: () => void;
  entities: ReturnType<typeof useEntityOptions>;
}) {
  const packagingRuns = usePackagingRuns();
  const [packagingRunId, setPackagingRunId] = useState("");
  const [toleranceType, setToleranceType] = useState("percentage");
  const [toleranceValue, setToleranceValue] = useState("");
  const [toleranceInclusive, setToleranceInclusive] = useState("true");
  const [lossReasons, setLossReasons] = useState<RepeatRow[]>([]);
  const [linkedDeviationId, setLinkedDeviationId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      await api.post<MutationReceipt>("/reconciliation/v1/labels/evaluate", {
        idempotency_key: newIdempotencyKey(),
        packaging_run_id: packagingRunId.trim(),
        tolerance_rule: { type: toleranceType, value: toleranceValue.trim(), inclusive: toleranceInclusive === "true" },
        loss_reasons: lossReasons.length > 0 ? buildRepeatArray(LOSS_REASON_SUBFIELDS, lossReasons) : null,
        linked_deviation_id: linkedDeviationId.trim() || null,
      });
      setDone(true);
      onEvaluated();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Evaluation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad>
      <CardHeader title="Evaluate label reconciliation" />
      <p className="fs-2 text-muted mb-3">
        Recomputes the mass balance from the packaging run&apos;s own label counts under your
        tolerance rule - the batch and quantities are derived from the packaging run, not entered here.
      </p>
      <form onSubmit={submit} className="grid grid-cols-3 gap-4">
        <EntityPickerField
          label="Packaging run ID"
          required
          value={packagingRunId}
          onChange={setPackagingRunId}
          options={packagingRuns.options}
          status={packagingRuns.status}
          kind="packaging run"
        />
        <EntityPickerField
          label="Linked deviation ID"
          hint="An existing QMS deviation - only relevant alongside an approved_loss quantity."
          value={linkedDeviationId}
          onChange={setLinkedDeviationId}
          options={entities.deviations}
          status={entities.deviationsStatus}
          kind="deviation"
        />
        <div />
        <ToleranceRuleFields
          type={toleranceType}
          setType={setToleranceType}
          value={toleranceValue}
          setValue={setToleranceValue}
          inclusive={toleranceInclusive}
          setInclusive={setToleranceInclusive}
        />
      </form>
      <div className="mt-3">
        <RepeatableRows
          label="Loss reasons"
          hint="Required when a non-zero approved_loss quantity applies - each entry needs a category and description."
          itemLabel="Loss reason"
          subFields={LOSS_REASON_SUBFIELDS}
          value={lossReasons}
          onChange={setLossReasons}
        />
      </div>
      {error && <p className="error-text mt-2">{error}</p>}
      {done && <p className="fs-2 mt-2">Label reconciliation evaluated - see the reconciliations table above.</p>}
      <div className="mt-3">
        <Button type="submit" variant="primary" onClick={submit} disabled={busy || !packagingRunId.trim() || !toleranceValue.trim()}>
          {busy ? "Evaluating…" : "Evaluate label reconciliation"}
        </Button>
      </div>
    </Card>
  );
}

function EvaluateComponentReconciliationCard({
  onEvaluated,
  defaultBatchId,
  entities,
}: {
  onEvaluated: () => void;
  defaultBatchId: string;
  entities: ReturnType<typeof useEntityOptions>;
}) {
  const [batchId, setBatchId] = useState(defaultBatchId);
  const [deviceUnitId, setDeviceUnitId] = useState("");
  const { siteId } = useSiteId();
  // 2026-10-09 real fix: `GET /devices/v1/units` (added the same day, batch_id-filterable) now exists --
  // this field was left free-text because no list endpoint existed at all; that's no longer true, so
  // it's wired to a real dropdown scoped to the selected batch, same shape as useGenealogyNodeRefs().
  const deviceUnits = useApiResource<{ items: { unit_id: string; serial_number: string | null; udi_di: string | null }[] }>(
    siteId && batchId.trim() ? `/devices/v1/units?site_id=${siteId}&batch_id=${batchId.trim()}` : null
  );
  const deviceUnitOptions: EntityOption[] = (deviceUnits.data?.items ?? []).map((u) => ({
    value: u.unit_id,
    label: u.serial_number ?? u.udi_di ?? u.unit_id,
  }));
  const deviceUnitOptionsStatus: EntityOptionsStatus = deviceUnits.loading
    ? "loading"
    : deviceUnits.error
      ? "error"
      : deviceUnitOptions.length === 0
        ? "empty"
        : "ready";
  const [itemRef, setItemRef] = useState<KvRow[]>([]);
  const quantityFields = useQuantityFields(true);
  const [uom, setUom] = useState("");
  const [toleranceType, setToleranceType] = useState("percentage");
  const [toleranceValue, setToleranceValue] = useState("");
  const [toleranceInclusive, setToleranceInclusive] = useState("true");
  const [lossReasons, setLossReasons] = useState<RepeatRow[]>([]);
  const [linkedDeviationId, setLinkedDeviationId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      await api.post<MutationReceipt>("/reconciliation/v1/components/evaluate", {
        idempotency_key: newIdempotencyKey(),
        batch_id: batchId.trim(),
        reconciliation_type: "COMPONENT",
        device_unit_id: deviceUnitId.trim() || null,
        item_ref: buildKvObject(itemRef),
        quantities: quantityFields.build(),
        uom: uom.trim(),
        tolerance_rule: { type: toleranceType, value: toleranceValue.trim(), inclusive: toleranceInclusive === "true" },
        loss_reasons: lossReasons.length > 0 ? buildRepeatArray(LOSS_REASON_SUBFIELDS, lossReasons) : null,
        linked_deviation_id: linkedDeviationId.trim() || null,
      });
      setDone(true);
      onEvaluated();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Evaluation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad>
      <CardHeader title="Evaluate component reconciliation" />
      <p className="fs-2 text-muted mb-3">
      Serialized or critical-component accountability. Set a device unit ID for a
        serialized case; leave it blank for a batch-level critical-component reconciliation.
      </p>
      <form onSubmit={submit} className="grid grid-cols-3 gap-4">
        <EntityPickerField
          label="Batch"
          required
          value={batchId}
          onChange={setBatchId}
          options={entities.batches}
          status={entities.batchesStatus}
          kind="batch"
        />
        <EntityPickerField
          label="Device unit ID"
          hint="Optional - only for a serialized case; must belong to this batch."
          value={deviceUnitId}
          onChange={setDeviceUnitId}
          options={deviceUnitOptions}
          status={deviceUnitOptionsStatus}
          kind="device unit"
        />
        <UomSelect value={uom} onChange={setUom} required />
        <ToleranceRuleFields
          type={toleranceType}
          setType={setToleranceType}
          value={toleranceValue}
          setValue={setToleranceValue}
          inclusive={toleranceInclusive}
          setInclusive={setToleranceInclusive}
        />
        <EntityPickerField
          label="Linked deviation ID"
          hint="An existing QMS deviation - only relevant alongside an approved_loss quantity."
          value={linkedDeviationId}
          onChange={setLinkedDeviationId}
          options={entities.deviations}
          status={entities.deviationsStatus}
          kind="deviation"
        />
      </form>
      <div className="grid grid-cols-2 gap-4 mt-3">
        <KeyValueRows label="Item reference" value={itemRef} onChange={setItemRef} />
        {quantityFields.fields}
      </div>
      <div className="mt-3">
        <RepeatableRows
          label="Loss reasons"
          hint="Required when a non-zero approved_loss quantity is entered above - each entry needs a category and description."
          itemLabel="Loss reason"
          subFields={LOSS_REASON_SUBFIELDS}
          value={lossReasons}
          onChange={setLossReasons}
        />
      </div>
      {error && <p className="error-text mt-2">{error}</p>}
      {done && <p className="fs-2 mt-2">Component reconciliation evaluated - see the reconciliations table above.</p>}
      <div className="mt-3">
        <Button
          type="submit"
          variant="primary"
          onClick={submit}
          disabled={busy || !batchId.trim() || !uom.trim() || itemRef.length === 0 || !quantityFields.issued.trim() || !toleranceValue.trim()}
        >
          {busy ? "Evaluating…" : "Evaluate component reconciliation"}
        </Button>
      </div>
    </Card>
  );
}
