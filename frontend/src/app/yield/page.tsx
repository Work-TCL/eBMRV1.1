"use client";

import { useEffect, useState } from "react";
import {
  api,
  ApiError,
  canEvaluateYield,
  canVerifyReconciliation,
  listAll,
  newIdempotencyKey,
  type MutationReceipt,
} from "@/lib/api";
import { useEntityOptions, useMe, type EntityOption, type EntityOptionsStatus } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { UomSelect } from "@/components/ui/UomSelect";
import { Icon } from "@/components/ui/Icon";
import { StatePill } from "@/components/ui/StatePill";
import { summarizeJson } from "@/components/ui/JsonPanel";
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
  theoretical_quantity: string | null;
  actual_quantity: string | null;
  uom: string | null;
  result: Record<string, unknown> | null;
  state: string;
  min_percent: string | null;
  max_percent: string | null;
  verified: boolean;
  version: number;
}

interface Reconciliation {
  id: string;
  reconciliation_type: string;
  item_ref: Record<string, unknown> | null;
  device_unit_id: string | null;
  quantities: Record<string, unknown> | null;
  uom: string | null;
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
  const { me } = useMe();
  const entities = useEntityOptions();
  const [batchId, setBatchId] = useState("");
  const [summary, setSummary] = useState<BatchSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verifyTarget, setVerifyTarget] = useState<VerifyTarget | null>(null);

  async function load(id = batchId) {
    if (!id.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setSummary(await api.get<BatchSummary>(`/reconciliation/v1/batches/${id.trim()}/summary`));
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHead
        title="Yield & reconciliation"
        subtitle="Theoretical vs actual quantities, tolerance outcome, and the verifier signature that clears a batch for release."
      />

      <Card pad className="mb-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
          className="flex flex-wrap items-end gap-4"
        >
          <EntityPickerField
            label="Batch"
            value={batchId}
            onChange={setBatchId}
            options={entities.batches}
            status={entities.batchesStatus}
            kind="batch"
          />
          <Button type="submit" variant="secondary" disabled={loading || !batchId.trim()}>
            <Icon name="search" /> {loading ? "Loading…" : "Load batch summary"}
          </Button>
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
            <CardHeader title={`Calculations (${summary.calculations.length})`} />
            {summary.calculations.length === 0 ? (
              <EmptyState icon="gauge">No yield or potency calculations recorded for this batch.</EmptyState>
            ) : (
              <Table>
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Phase</th>
                    <th>Theoretical</th>
                    <th>Actual</th>
                    <th>Limits %</th>
                    <th>State</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {summary.calculations.map((c) => (
                    <tr key={c.id}>
                      <td>{c.calculation_type}</td>
                      <td>{c.phase_code ?? "—"}</td>
                      <td className="tabular">{c.theoretical_quantity ?? "—"} {c.uom ?? ""}</td>
                      <td className="tabular">{c.actual_quantity ?? "—"} {c.uom ?? ""}</td>
                      <td className="tabular fs-2">
                        {c.min_percent ?? "—"} – {c.max_percent ?? "—"}
                      </td>
                      <td>{resultPill(c.state)}</td>
                      <td style={{ textAlign: "right" }}>
                        {!c.verified && canVerifyReconciliation(me) && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() =>
                              setVerifyTarget({
                                kind: "CALCULATION",
                                id: c.id,
                                version: c.version,
                                label: `${c.calculation_type}${c.phase_code ? ` / ${c.phase_code}` : ""}`,
                              })
                            }
                          >
                            Verify
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>

          <Card className="mt-4">
            <CardHeader title={`Reconciliations (${summary.reconciliations.length})`} />
            {summary.reconciliations.length === 0 ? (
              <EmptyState icon="list-checks">No material, packaging, label or component reconciliations recorded.</EmptyState>
            ) : (
              <Table>
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Item</th>
                    <th>Quantities</th>
                    <th>State</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {summary.reconciliations.map((r) => (
                    <tr key={r.id}>
                      <td>{r.reconciliation_type}</td>
                      <td className="fs-2" style={{ wordBreak: "break-word" }}>
                        {summarizeJson(r.item_ref)}
                      </td>
                      <td className="fs-1" style={{ wordBreak: "break-word" }}>
                        {summarizeJson(r.quantities)} {r.uom ?? ""}
                      </td>
                      <td>{resultPill(r.state)}</td>
                      <td style={{ textAlign: "right" }}>
                        {!r.verified && canVerifyReconciliation(me) && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() =>
                              setVerifyTarget({
                                kind: "RECONCILIATION",
                                id: r.id,
                                version: r.version,
                                label: r.reconciliation_type,
                              })
                            }
                          >
                            Verify
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>
        </>
      )}

      {canEvaluateYield(me) && (
        <div className="mt-6 grid gap-4">
          <EvaluateYieldCard onEvaluated={() => load()} defaultBatchId={batchId} entities={entities} />
          <EvaluatePotencyCard onEvaluated={() => load()} defaultBatchId={batchId} entities={entities} />
          <ReconciliationCard
            title="Evaluate material reconciliation"
            postPath="/reconciliation/v1/material/evaluate"
            reconciliationType="MATERIAL"
            onEvaluated={() => load()}
            defaultBatchId={batchId}
            entities={entities}
          />
          <ReconciliationCard
            title="Evaluate packaging reconciliation"
            postPath="/reconciliation/v1/packaging/evaluate"
            reconciliationType="PACKAGING"
            onEvaluated={() => load()}
            defaultBatchId={batchId}
            entities={entities}
          />
          <EvaluateLabelReconciliationCard onEvaluated={() => load()} entities={entities} />
          <EvaluateComponentReconciliationCard onEvaluated={() => load()} defaultBatchId={batchId} entities={entities} />
        </div>
      )}

      {verifyTarget && (
        <SignatureCeremony
          open
          onClose={() => setVerifyTarget(null)}
          onDone={() => {
            setVerifyTarget(null);
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
  const [quantities, setQuantities] = useState<KvRow[]>([]);
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
        quantities: buildKvObject(quantities),
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
        <KeyValueRows
          label="Quantities"
          hint="e.g. issued, consumed, returned, samples, rejected, destroyed, approved_loss."
          value={quantities}
          onChange={setQuantities}
        />
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
          disabled={busy || !batchId.trim() || !uom.trim() || itemRef.length === 0 || quantities.length === 0 || !toleranceValue.trim()}
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
  const [itemRef, setItemRef] = useState<KvRow[]>([]);
  const [quantities, setQuantities] = useState<KvRow[]>([]);
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
        quantities: buildKvObject(quantities),
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
        <Field label="Device unit ID" hint="Optional - only for a serialized case; must belong to this batch.">
          <Input value={deviceUnitId} onChange={(e) => setDeviceUnitId(e.target.value)} />
        </Field>
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
        <KeyValueRows
          label="Quantities"
          hint="e.g. issued, assembled, rejected, scrapped, returned, samples, destroyed, approved_loss."
          value={quantities}
          onChange={setQuantities}
        />
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
          disabled={busy || !batchId.trim() || !uom.trim() || itemRef.length === 0 || quantities.length === 0 || !toleranceValue.trim()}
        >
          {busy ? "Evaluating…" : "Evaluate component reconciliation"}
        </Button>
      </div>
    </Card>
  );
}
