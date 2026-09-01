"use client";

import { useState } from "react";
import {
  api,
  ApiError,
  canEvaluateYield,
  canVerifyReconciliation,
  newIdempotencyKey,
  type MutationReceipt,
} from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { StatePill } from "@/components/ui/StatePill";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";

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
        subtitle="Document 17 — theoretical vs actual quantities, tolerance outcome, and the verifier signature that clears a batch for release."
      />

      <Card pad className="mb-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
          className="flex items-end gap-4"
        >
          <Field label="Batch ID">
            <Input value={batchId} onChange={(e) => setBatchId(e.target.value)} placeholder="batch UUID" style={{ minWidth: 320 }} />
          </Field>
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
                      <td className="fs-2 tabular" style={{ wordBreak: "break-word" }}>
                        {r.item_ref ? JSON.stringify(r.item_ref) : "—"}
                      </td>
                      <td className="fs-1 tabular" style={{ wordBreak: "break-word" }}>
                        {r.quantities ? JSON.stringify(r.quantities) : "—"} {r.uom ?? ""}
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
        <div className="mt-6">
          <EvaluateYieldCard onEvaluated={() => load()} defaultBatchId={batchId} />
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
          title={`Verify — ${verifyTarget.label}`}
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

function EvaluateYieldCard({ onEvaluated, defaultBatchId }: { onEvaluated: () => void; defaultBatchId: string }) {
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
        Runs the Document 17 §3 yield formula (actual ÷ theoretical × 100) against the batch and records the
        tolerance outcome. Decimal quantities are exact strings.
      </p>
      <form onSubmit={submit} className="grid grid-cols-3 gap-4">
        <Field label="Batch ID" required>
          <Input value={batchId} onChange={(e) => setBatchId(e.target.value)} required />
        </Field>
        <Field label="Phase code" hint="Optional — omit for a whole-batch yield.">
          <Input value={phaseCode} onChange={(e) => setPhaseCode(e.target.value)} />
        </Field>
        <Field label="UOM" required>
          <Input value={uom} onChange={(e) => setUom(e.target.value)} required />
        </Field>
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
      {done && <p className="fs-2 mt-2">Yield evaluated — see the calculations table above.</p>}
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
