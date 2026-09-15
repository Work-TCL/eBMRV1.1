import type { ReactNode } from "react";
import { Table } from "./Table";

/** Many regulated records carry structured detail the backend stores as JSON (`root_cause`,
 * `impact_assessment`, `regulatory_impact`, …). The schema for those blobs is per-record and set by
 * the owning command, so there is nothing stable to lay out as fields — render them faithfully and
 * legibly instead of guessing at a form.
 *
 * A flat object becomes labelled rows; a mixed object's scalar fields render the same way while each
 * nested field recurses into its own sub-block; a uniform array of records becomes a table. Only a
 * value that stays irreducibly nested after that (an array of mixed shapes, an array of arrays) ever
 * falls back to a formatted JSON block. Renders nothing at all when the value is absent, so callers
 * can list every optional block unconditionally. */
export function JsonPanel({ title, value }: { title: ReactNode; value: unknown }) {
  if (value === null || value === undefined) return null;
  if (Array.isArray(value) && value.length === 0) return null;
  if (typeof value === "object" && !Array.isArray(value) && Object.keys(value).length === 0) return null;

  if (Array.isArray(value) && value.every((v) => isPlainObject(v))) {
    return <ObjectListTable title={title} rows={value as Record<string, unknown>[]} />;
  }

  if (isPlainObject(value)) {
    const scalarEntries: Record<string, unknown> = {};
    const nestedEntries: [string, unknown][] = [];
    for (const [k, v] of Object.entries(value)) {
      if (v !== null && typeof v === "object" && (!Array.isArray(v) || v.length > 0)) nestedEntries.push([k, v]);
      else scalarEntries[k] = v;
    }
    if (nestedEntries.length > 0) {
      return (
        <div className="mb-4">
          <p className="fact-k mb-2">{title}</p>
          <FlatFacts obj={scalarEntries} />
          {nestedEntries.map(([k, v]) => (
            <JsonPanel key={k} title={humanize(k)} value={v} />
          ))}
        </div>
      );
    }
  }

  return (
    <div className="mb-4">
      <p className="fact-k mb-2">{title}</p>
      {renderValue(value)}
    </div>
  );
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

/** A flat object's fields as label/value rows, with no nested-field handling — used for the scalar
 * half of a mixed-shape object once its nested fields have been peeled off to recurse separately. */
function FlatFacts({ obj }: { obj: Record<string, unknown> }) {
  const entries = Object.entries(obj);
  if (entries.length === 0) return null;
  return (
    <div>
      {entries.map(([key, entry]) => (
        <div key={key} className="flex gap-3 fs-2" style={{ padding: "3px 0" }}>
          <span className="text-muted" style={{ minWidth: 190, flexShrink: 0 }}>
            {humanize(key)}
          </span>
          <span style={{ wordBreak: "break-word" }}>
            {entry === null || entry === "" ? "—" : String(entry)}
          </span>
        </div>
      ))}
    </div>
  );
}

/** A short reference object (`{lot_id: "..."}`, a nested `device_reference`, …) as plain "Key: value"
 * text instead of raw `{"key":"value"}` JSON — recurses so a reference-within-a-reference never bottoms
 * out in `JSON.stringify` either. Used for table cells, where a block layout doesn't fit. */
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

/** An array of same-shaped records as a compact table instead of one raw JSON dump. Columns are the
 * union of every row's keys in first-seen order, capped so one wide record can't blow out the layout —
 * a cell that's still an object/array falls back to inline "Key: value" text, scoped to that cell. */
function ObjectListTable({ title, rows, cap = 8 }: { title: ReactNode; rows: Record<string, unknown>[]; cap?: number }) {
  if (rows.length === 0) return null;
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
                  {cellValue(row[c]) || <span className="text-muted">—</span>}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}

function renderValue(value: unknown): ReactNode {
  if (value === null || value === undefined) return <span className="text-muted">—</span>;

  if (typeof value !== "object") {
    return <span className="fs-3">{String(value)}</span>;
  }

  if (Array.isArray(value)) {
    const allScalar = value.every((entry) => entry === null || typeof entry !== "object");
    if (allScalar) {
      return <span className="fs-3">{value.map((entry) => String(entry)).join(", ")}</span>;
    }
    return <Pre value={value} />;
  }

  const entries = Object.entries(value as Record<string, unknown>);
  const allScalar = entries.every(([, entry]) => entry === null || typeof entry !== "object");
  if (!allScalar) return <Pre value={value} />;

  return <FlatFacts obj={value as Record<string, unknown>} />;
}

function Pre({ value }: { value: unknown }) {
  return (
    <pre
      className="fs-2 tabular scrollbar-thin"
      style={{
        background: "var(--surface-sunken)",
        border: "1px solid var(--border-hairline)",
        borderRadius: "var(--radius-sm)",
        padding: "var(--space-3)",
        overflowX: "auto",
        margin: 0,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

/** `root_cause_ref` -> `Root cause ref`. Keys come from the backend's own field names. */
function humanize(key: string): string {
  const spaced = key.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/** A one-line, human-readable preview of a JSON value for a table cell — where `JsonPanel`'s block
 * layout doesn't fit. A flat object/array reads as plain text ("material: raw, packaging: —"); anything
 * nested falls back to compact JSON, truncated, so the cell never overflows. */
export function summarizeJson(value: unknown, maxLen = 140): string {
  if (value === null || value === undefined) return "—";
  if (typeof value !== "object") return String(value);

  if (Array.isArray(value)) {
    if (value.length === 0) return "—";
    const allScalar = value.every((entry) => entry === null || typeof entry !== "object");
    if (allScalar) return truncate(value.map((entry) => String(entry)).join(", "), maxLen);
    return truncate(JSON.stringify(value), maxLen);
  }

  const entries = Object.entries(value as Record<string, unknown>);
  if (entries.length === 0) return "—";
  const allScalar = entries.every(([, entry]) => entry === null || typeof entry !== "object");
  if (allScalar) {
    return truncate(
      entries.map(([k, v]) => `${humanize(k)}: ${v === null || v === "" ? "—" : String(v)}`).join(", "),
      maxLen
    );
  }
  return truncate(JSON.stringify(value), maxLen);
}

function truncate(s: string, maxLen: number): string {
  return s.length > maxLen ? `${s.slice(0, maxLen - 1)}…` : s;
}

/** A record's append-only history arrays (`closure_history`, `extension_history`, `review_history`).
 * Renders newest last, matching the order the backend appends. */
export function HistoryPanel({ title, entries }: { title: ReactNode; entries: unknown }) {
  if (!Array.isArray(entries) || entries.length === 0) return null;
  return (
    <div className="mb-4">
      <p className="fact-k mb-2">{title}</p>
      {entries.map((entry, index) => (
        <div
          key={index}
          className="mb-2"
          style={{
            borderLeft: "2px solid var(--border-hairline)",
            paddingLeft: "var(--space-3)",
          }}
        >
          {renderValue(entry)}
        </div>
      ))}
    </div>
  );
}
