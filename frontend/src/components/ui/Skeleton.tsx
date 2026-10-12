import type { CSSProperties } from "react";

/** Base shimmer placeholder — the one visual primitive every loading state in the app should be built
 * from, so a page's "loading" render is shaped like its final content instead of a bare "Loading…"
 * string (which is what every screen did before this: no layout preservation, a jump when real content
 * replaces it). Sized via `width`/`height` per call site; the shimmer itself and its reduced-motion
 * fallback live in `.skeleton` (ebmr-components.css) alongside the rest of the token-driven styles. */
export function Skeleton({
  width = "100%",
  height = 14,
  radius,
  style,
  className,
}: {
  width?: number | string;
  height?: number | string;
  radius?: number | string;
  style?: CSSProperties;
  className?: string;
}) {
  return (
    <span
      className={`skeleton${className ? ` ${className}` : ""}`}
      style={{ width, height, borderRadius: radius, ...style }}
      aria-hidden="true"
    />
  );
}

/** Placeholder for a `FactGrid` (`components/ui/FactGrid.tsx`) — same `.fact-grid`/`.fact` markup, a
 * label-sized bar over a value-sized bar per slot, varied slightly so the grid doesn't read as a single
 * repeated tile. Used by `RecordDetailShell`'s loading state; any other screen that renders a FactGrid
 * from a not-yet-loaded record can reuse this instead of hand-rolling the same shape. */
export function FactGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="fact-grid" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div className="fact" key={i}>
          <Skeleton width={56 + ((i * 7) % 3) * 18} height={10} />
          <Skeleton width={`${64 + ((i * 5) % 4) * 8}%`} height={16} style={{ marginTop: 4 }} />
        </div>
      ))}
    </div>
  );
}

/** Placeholder for a `DataTable` (`components/ui/DataTable.tsx`) before it has mounted at all — e.g.
 * `RecordListPage` while it's still waiting on `siteId`. Renders the real column headers (so nothing
 * shifts once the real table takes over) with skeleton bars standing in for body cells. `DataTable`
 * itself has its own inline skeleton rows for the "mounted but first page still loading" case, since by
 * then it already owns the `<table>`/`<thead>` markup directly. */
export function TableSkeleton({
  columns,
  rows = 6,
}: {
  columns: { header: string; align?: "left" | "right" }[];
  rows?: number;
}) {
  return (
    <div className="table-wrap" style={{ border: "none" }} aria-hidden="true">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th key={i} style={col.align === "right" ? { textAlign: "right" } : undefined}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, r) => (
            <tr key={r}>
              {columns.map((col, c) => (
                <td key={c} style={col.align === "right" ? { textAlign: "right" } : undefined}>
                  <Skeleton width={`${46 + ((r + c * 3) % 4) * 14}%`} height={14} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
