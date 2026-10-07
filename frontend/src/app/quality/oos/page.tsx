"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  ApiError,
  newIdempotencyKey,
  pagedFetcher,
  type MutationReceipt,
  type Oos,
  type Oot,
} from "@/lib/api";
import { useEntityOptions } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill, SeverityPill } from "@/components/ui/StatePill";
import { formatDateTime } from "@/lib/api";

// GET /qc/v1/results?batch_id=... — real picker data for a field referencing a `qc_result` row by id
// (qc/router.py::list_results_for_batch's own docstring names DDCP's `qc_record_reference` as the first
// caller this was built for; OOS/OOT's "Source QC result" is the same shape of gap). Scoped to a chosen
// batch, not a flat list — a QC result only makes sense in the context of which batch it came from, so
// this cascades on a batch picker exactly like `inventory/page.tsx`'s lot -> container picker cascades on
// a chosen lot.
interface QcResultOption {
  id: string;
  label: string;
}

const linkBtnStyle: CSSProperties = {
  background: "none",
  border: "none",
  padding: 0,
  color: "var(--brand-600)",
  fontSize: "var(--fs-1)",
  cursor: "pointer",
  textDecoration: "underline",
  marginTop: 4,
};

function useQcResultsForBatch(batchId: string): { options: QcResultOption[]; loading: boolean } {
  const [results, setResults] = useState<QcResultOption[]>([]);
  const [resultsBatchId, setResultsBatchId] = useState<string | null>(null);
  useEffect(() => {
    if (!batchId) return;
    let cancelled = false;
    api
      .get<QcResultOption[]>(`/qc/v1/results?batch_id=${encodeURIComponent(batchId)}`)
      .then((rows) => {
        if (cancelled) return;
        setResults(rows);
        setResultsBatchId(batchId);
      })
      .catch(() => {
        if (!cancelled) {
          setResults([]);
          setResultsBatchId(batchId);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [batchId]);
  const current = resultsBatchId === batchId ? results : [];
  return { options: current, loading: !!batchId && resultsBatchId !== batchId };
}

/** A batch picker plus a dependent QC-result picker scoped to whichever batch is chosen — replaces a raw
 * "Source QC result ID" text box in both create modals below, since there is no flat "browse QC results"
 * page; this cascade is the only way that id is discoverable without going to the database directly. */
function QcResultPickerField({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const entities = useEntityOptions();
  const [batchId, setBatchId] = useState("");
  const { options: results, loading: resultsLoading } = useQcResultsForBatch(batchId);
  const [manual, setManual] = useState(false);

  if (manual) {
    return (
      <Field label="Source QC result ID" required hint="Enter the QC result's ID directly.">
        <Input value={value} onChange={(e) => onChange(e.target.value)} required />
        <button type="button" style={linkBtnStyle} onClick={() => setManual(false)}>
          Choose from a batch&rsquo;s results instead
        </button>
      </Field>
    );
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <Field label="Batch" hint="Pick the batch the QC result belongs to.">
        <Select
          value={batchId}
          onChange={(e) => {
            setBatchId(e.target.value);
            onChange("");
          }}
          disabled={entities.batchesStatus === "loading"}
          style={{ minWidth: 220 }}
        >
          <option value="">{entities.batchesStatus === "loading" ? "Loading batches…" : "Select a batch…"}</option>
          {entities.batches.map((b) => (
            <option key={b.value} value={b.value}>
              {b.label}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Source QC result" required hint={!batchId ? "Pick a batch first." : undefined}>
        <Select value={value} onChange={(e) => onChange(e.target.value)} disabled={!batchId || resultsLoading}>
          <option value="">
            {!batchId ? "—" : resultsLoading ? "Loading results…" : results.length ? "Select a result…" : "No QC results for this batch"}
          </option>
          {results.map((r) => (
            <option key={r.id} value={r.id}>
              {r.label}
            </option>
          ))}
        </Select>
        <button type="button" style={linkBtnStyle} onClick={() => setManual(true)}>
          Can&rsquo;t find it? Enter ID manually
        </button>
      </Field>
    </div>
  );
}

export default function OosOotPage() {
  const router = useRouter();
  const [createOosOpen, setCreateOosOpen] = useState(false);
  const [createOotOpen, setCreateOotOpen] = useState(false);
  const [oosReloadToken, setOosReloadToken] = useState(0);
  const [ootReloadToken, setOotReloadToken] = useState(0);

  const oosColumns: DataTableColumn<Oos>[] = [
    { key: "oos_number", header: "OOS number", sortable: true, render: (r) => <span className="font-semibold tabular">{r.oos_number}</span> },
    { key: "state", header: "State", sortable: true, render: (r) => <WorkflowStatePill state={r.state} /> },
    { key: "severity", header: "Severity", render: (r) => <SeverityPill severity={r.severity} /> },
    { key: "final_classification", header: "Final classification", render: (r) => r.final_classification ?? "—" },
    { key: "opened_at", header: "Opened", sortable: true, render: (r) => <span className="tabular fs-2">{formatDateTime(r.opened_at)}</span> },
    { key: "closed_at", header: "Closed", render: (r) => <span className="tabular fs-2">{r.closed_at ? formatDateTime(r.closed_at) : "—"}</span> },
  ];

  const ootColumns: DataTableColumn<Oot>[] = [
    {
      key: "id",
      header: "OOT record",
      render: (r) => <span className="font-semibold tabular fs-2">{r.id.slice(0, 8)}…</span>,
    },
    {
      key: "source_result_id",
      header: "Source result",
      render: (r) => <span className="tabular fs-2">{r.source_result_id.slice(0, 8)}…</span>,
    },
    { key: "state", header: "State", sortable: true, render: (r) => <WorkflowStatePill state={r.state} /> },
    { key: "opened_at", header: "Opened", sortable: true, render: (r) => <span className="tabular fs-2">{formatDateTime(r.opened_at)}</span> },
    { key: "closed_at", header: "Closed", render: (r) => <span className="tabular fs-2">{r.closed_at ? formatDateTime(r.closed_at) : "—"}</span> },
  ];

  return (
    <div>
      <PageHead
        title="OOS / OOT"
        subtitle="Out-of-specification investigation and out-of-trend evaluation for QC results."
      />

      <Card className="mb-4">
        <CardHeader
          title="Out-of-specification (OOS)"
          meta={
            <Button variant="primary" onClick={() => setCreateOosOpen(true)}>
              <Icon name="plus" /> Open OOS
            </Button>
          }
        />
        <DataTable<Oos>
          columns={oosColumns}
          fetchPage={pagedFetcher<Oos>("/quality/oos/v1")}
          rowKey={(row) => row.id}
          searchPlaceholder="Search OOS number…"
          emptyIcon="alert-triangle"
          emptyMessage="No OOS records opened yet."
          defaultSort={{ by: "opened_at", dir: "desc" }}
          reloadToken={oosReloadToken}
          onRowClick={(row) => router.push(`/quality/oos/${row.id}`)}
        />
      </Card>

      <Card>
        <CardHeader
          title="Out-of-trend (OOT)"
          meta={
            <Button variant="primary" onClick={() => setCreateOotOpen(true)}>
              <Icon name="plus" /> Evaluate for OOT
            </Button>
          }
        />
        <p className="fs-2 text-muted" style={{ padding: "0 var(--space-4)" }}>
          Evaluates a result against its test definition&apos;s trend rule. A record is created either way
          (state <code>open</code> if the trend was breached, <code>not_triggered</code> if not).
        </p>
        <DataTable<Oot>
          columns={ootColumns}
          fetchPage={pagedFetcher<Oot>("/quality/oot/v1")}
          rowKey={(row) => row.id}
          emptyIcon="activity"
          emptyMessage="No OOT evaluations recorded yet."
          defaultSort={{ by: "opened_at", dir: "desc" }}
          reloadToken={ootReloadToken}
          onRowClick={(row) => router.push(`/quality/oot/${row.id}`)}
        />
      </Card>

      {createOosOpen && (
        <OpenOosModal
          onClose={() => setCreateOosOpen(false)}
          onOpened={(id) => {
            setCreateOosOpen(false);
            setOosReloadToken((n) => n + 1);
            router.push(`/quality/oos/${id}`);
          }}
        />
      )}
      {createOotOpen && (
        <EvaluateOotModal
          onClose={() => setCreateOotOpen(false)}
          onOpened={(id) => {
            setCreateOotOpen(false);
            setOotReloadToken((n) => n + 1);
            router.push(`/quality/oot/${id}`);
          }}
        />
      )}
    </div>
  );
}

function OpenOosModal({ onClose, onOpened }: { onClose: () => void; onOpened: (oosId: string) => void }) {
  const [resultId, setResultId] = useState("");
  const [oosNumber, setOosNumber] = useState("");
  const [severity, setSeverity] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const receipt = await api.post<MutationReceipt>(
        `/quality/oos/v1/from-result/${encodeURIComponent(resultId.trim())}`,
        {
          idempotency_key: newIdempotencyKey(),
          source_result_id: resultId.trim(),
          oos_number: oosNumber.trim(),
          severity: severity.trim() || null,
        }
      );
      onOpened(receipt.aggregate_id);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not open OOS");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Open OOS from a result" large>
      <form onSubmit={submit}>
        <QcResultPickerField value={resultId} onChange={setResultId} />
        <div className="grid grid-cols-2 gap-3">
          <Field label="OOS number" required>
            <Input value={oosNumber} onChange={(e) => setOosNumber(e.target.value)} placeholder="OOS-0001" required autoFocus />
          </Field>
          <Field label="Severity" hint="Optional.">
            <Input value={severity} onChange={(e) => setSeverity(e.target.value)} placeholder="e.g. major" />
          </Field>
        </div>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !resultId.trim() || !oosNumber.trim()}>
            {busy ? "Opening…" : "Open OOS"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function EvaluateOotModal({ onClose, onOpened }: { onClose: () => void; onOpened: (ootId: string) => void }) {
  const [resultId, setResultId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const receipt = await api.post<MutationReceipt>("/quality/oot/v1/evaluate", {
        idempotency_key: newIdempotencyKey(),
        source_result_id: resultId.trim(),
      });
      onOpened(receipt.aggregate_id);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not evaluate OOT");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Evaluate a result for OOT" large>
      <form onSubmit={submit}>
        <p className="fs-2 text-muted mb-3">
          Evaluates the chosen result against its test definition&apos;s trend rule. The result&apos;s test
          definition must have a released trend rule attached, or this fails with
          <code> OOT_RULE_NOT_RELEASED</code>.
        </p>
        <QcResultPickerField value={resultId} onChange={setResultId} />
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !resultId.trim()}>
            {busy ? "Evaluating…" : "Evaluate for OOT"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
