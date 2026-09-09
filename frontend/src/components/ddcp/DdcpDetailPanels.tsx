import { Table } from "@/components/ui/Table";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { KpiRow, KpiTile } from "@/components/ui/KpiTile";

/** `root_cause_ref` -> `Root cause ref`. Same convention as `JsonPanel`'s own (unexported) helper. */
function humanize(key: string): string {
  const spaced = key.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/** A small reference object (`{lot_id: "..."}`, `{record_id: "..."}`, a doubly-nested
 * `device_reference`, …) as plain "Key: value" text instead of raw `{"key":"value"}` JSON — the exact
 * shape `ObjectListTable`'s own table cells kept falling back to (component_lot_reference, qc_record_
 * reference, device_reference, …), which is unreadable to anyone who doesn't read JSON syntax. Recurses
 * so a nested reference-within-a-reference (device_reference's own stability/retain plan wrapper) never
 * bottoms out in `JSON.stringify` either. */
function cellValue(v: unknown): string {
  if (v === null || v === undefined || v === "") return "";
  if (Array.isArray(v)) return v.map(cellValue).filter(Boolean).join("; ");
  if (typeof v === "object") {
    return Object.entries(v as Record<string, unknown>)
      .map(([k, val]) => `${humanize(k)}: ${cellValue(val) || "—"}`)
      .join(", ");
  }
  return String(v);
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

/** The scalar half of a mixed-shape object as label/value rows — the same rendering `JsonPanel` already
 * gives a *fully* flat object, duplicated locally (JsonPanel doesn't export it) so `AutoSection` can use
 * it for the scalar fields it peels off before handling the nested ones separately. */
function FlatFacts({ obj }: { obj: Record<string, unknown> }) {
  const entries = Object.entries(obj);
  if (entries.length === 0) return null;
  return (
    <div className="mb-2">
      {entries.map(([key, v]) => (
        <div key={key} className="flex gap-3 fs-2" style={{ padding: "3px 0" }}>
          <span className="text-muted" style={{ minWidth: 190, flexShrink: 0 }}>
            {humanize(key)}
          </span>
 <span style={{ wordBreak: "break-word" }}>{v === null || v === "" ? "" : String(v)}</span>
        </div>
      ))}
    </div>
  );
}

/** An array of same-shaped records (a genealogy link list, a review-summary exception list, …) as a
 * compact table instead of one raw JSON dump. Columns are the union of every row's keys in first-seen
 * order, capped so one wide record can't blow out the layout — a cell that's still an object/array
 * falls back to inline JSON, but scoped to that one cell rather than the whole section. */
function ObjectListTable({ title, rows, cap = 8 }: { title: string; rows: Record<string, unknown>[]; cap?: number }) {
  if (rows.length === 0) {
    return (
      <div className="mb-4">
        <p className="fact-k mb-2">{title}</p>
        <p className="fs-2 text-muted">None recorded yet.</p>
      </div>
    );
  }
  const columns: string[] = [];
  for (const row of rows) for (const k of Object.keys(row)) if (!columns.includes(k)) columns.push(k);
  const shown = columns.slice(0, cap);
  return (
    <div className="mb-4">
      <p className="fact-k mb-2">
        {title} <span className="text-muted fs-1">({rows.length})</span>
      </p>
      <Table>
        <thead>
          <tr>
            {shown.map((c) => (
              <th key={c}>{humanize(c)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {shown.map((c) => (
                <td key={c} className="fs-2" style={{ wordBreak: "break-word" }}>
                  {cellValue(row[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}

/** One top-level key of a DDCP read composition (readiness detail / genealogy / review summary),
 * rendered the way its shape actually deserves instead of one shared raw-JSON dump:
 * - an array of records becomes a table (`ObjectListTable`)
 * - a fully flat object goes through the existing `JsonPanel` (already renders nice label/value rows)
 * - a *mixed* object — some scalar fields alongside a nested one, e.g. equipment eligibility's
 *   `{asset_id, state, eligible, reasons: [...]}` — used to fall back to raw JSON for the whole object
 *   just because one field (`reasons`) wasn't scalar. Now the scalar fields render as facts and each
 *   nested field recurses through `AutoSection` on its own, so only a value that's *itself* still
 *   irreducibly nested ever reaches raw JSON, and only for that one field. */
function AutoSection({ title, value }: { title: string; value: unknown }) {
  if (value === null || value === undefined) return null;

  if (Array.isArray(value)) {
    if (value.length === 0) return <ObjectListTable title={title} rows={[]} />;
    if (value.every((v) => isPlainObject(v))) {
      return <ObjectListTable title={title} rows={value as Record<string, unknown>[]} />;
    }
    return <JsonPanel title={title} value={value} />;
  }

  if (isPlainObject(value)) {
    const scalarEntries: Record<string, unknown> = {};
    const nestedEntries: [string, unknown][] = [];
    for (const [k, v] of Object.entries(value)) {
      if (v !== null && typeof v === "object") nestedEntries.push([k, v]);
      else scalarEntries[k] = v;
    }
    if (nestedEntries.length === 0) return <JsonPanel title={title} value={value} />;
    return (
      <div className="mb-4">
        <p className="fact-k mb-2">{title}</p>
        <FlatFacts obj={scalarEntries} />
        {nestedEntries.map(([k, v]) => (
          <AutoSection key={k} title={humanize(k)} value={v} />
        ))}
      </div>
    );
  }

  return <JsonPanel title={title} value={value} />;
}

/** `GET {prefix}/batches/{id}/readiness`'s detail (everything but `ready`/`blockers`, which
 * `ReadinessPanel` already renders): batch/profile as a fact line, then each sub-check
 * (em_readiness/line_clearance/equipment_check) as its own labelled block instead of one shared
 * raw-JSON dump. */
export function ReadinessDetailPanel({ detail }: { detail: Record<string, unknown> }) {
  const { batch_id, profile_version_id, em_readiness, line_clearance, equipment_check, ...rest } = detail;
  return (
    <div>
      <div className="flex gap-4 flex-wrap mb-3 fs-2">
        <span>
          <span className="text-muted">Batch:</span> <span className="tabular">{cellValue(batch_id)}</span>
        </span>
        <span>
          <span className="text-muted">Profile version:</span> <span className="tabular">{cellValue(profile_version_id)}</span>
        </span>
      </div>
      <AutoSection title="EM readiness (area)" value={em_readiness} />
      <AutoSection title="Line clearance" value={line_clearance} />
      <AutoSection title="Filler equipment eligibility" value={equipment_check} />
      {Object.entries(rest).map(([k, v]) => (
        <AutoSection key={k} title={humanize(k)} value={v} />
      ))}
    </div>
  );
}

/** `GET {prefix}/batches/{id}/genealogy` — the incoming-constituent / count / assembly / test /
 * evidence chain for one batch. Each list becomes its own table instead of one shared raw-JSON dump. */
export function GenealogyPanel({ genealogy }: { genealogy: Record<string, unknown> }) {
  const { batch_id, ...sections } = genealogy;
  return (
    <div>
      <p className="fs-2 text-muted mb-3">
 Batch <span className="tabular">{cellValue(batch_id)}</span> every constituent handoff, production
        count, assembly step, test link and evidence package recorded for this batch so far.
      </p>
      {Object.entries(sections).map(([k, v]) => (
        <AutoSection key={k} title={humanize(k)} value={v} />
      ))}
    </div>
  );
}

// Keys shown elsewhere on `ReviewSummaryPanel` (exception_summary as KPI tiles, defect_counts as its
// own section) or deliberately dropped: `batch_id` (the page already shows which batch this is for) and
// `genealogy` (the same data already renders in the dedicated Genealogy panel above it whenever both
// are loaded — PFS is the only family with both — so it isn't repeated twice on the same page).
const REVIEW_SUMMARY_HANDLED_KEYS = new Set(["batch_id", "exception_summary", "defect_counts", "genealogy"]);

/** `GET {prefix}/batches/{id}/review-summary` — review-by-exception: counts up top (as KPI tiles, red
 * when non-zero), full detail lists underneath, each its own table. */

export function ReviewSummaryPanel({ summary }: { summary: Record<string, unknown> }) {
  const exc = (summary.exception_summary ?? {}) as Record<string, unknown>;
  return (
    <div>
      {Object.keys(exc).length > 0 && (
        <KpiRow>
          {Object.entries(exc).map(([k, v]) => (
            <KpiTile
              key={k}
              label={humanize(k)}
              value={cellValue(v)}
              tone={Number(v) > 0 ? "warn" : "ok"}
              delta={Number(v) > 0 ? "Needs review" : "Clear"}
            />
          ))}
        </KpiRow>
      )}
      <AutoSection title="Defect counts" value={summary.defect_counts} />
      {Object.entries(summary)
        .filter(([k]) => !REVIEW_SUMMARY_HANDLED_KEYS.has(k))
        .map(([k, v]) => (
          <AutoSection key={k} title={humanize(k)} value={v} />
        ))}
    </div>
  );
}
