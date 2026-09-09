import type { ReactNode } from "react";

/** Many regulated records carry structured detail the backend stores as JSON (`root_cause`,
 * `impact_assessment`, `regulatory_impact`, …). The schema for those blobs is per-record and set by
 * the owning command, so there is nothing stable to lay out as fields — render them faithfully and
 * legibly instead of guessing at a form.
 *
 * Scalar values are shown as a labelled row; anything nested falls back to formatted JSON. Renders
 * nothing at all when the value is absent, so callers can list every optional block unconditionally. */
export function JsonPanel({ title, value }: { title: ReactNode; value: unknown }) {
  if (value === null || value === undefined) return null;
  if (Array.isArray(value) && value.length === 0) return null;
  if (typeof value === "object" && !Array.isArray(value) && Object.keys(value).length === 0) return null;

  return (
    <div className="mb-4">
      <p className="fact-k mb-2">{title}</p>
      {renderValue(value)}
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
