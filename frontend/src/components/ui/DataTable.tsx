"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { ApiError, type ListQuery, type Paged } from "@/lib/api";
import { useDebouncedValue } from "@/lib/hooks";
import { Icon } from "./Icon";
import { Input } from "./Input";
import { Select } from "./Select";
import { EmptyState } from "./Table";

export interface DataTableColumn<T> {
  /** Also the `sort_by` value sent to the API when `sortable` is set. */
  key: string;
  header: string;
  sortable?: boolean;
  align?: "left" | "right";
  render?: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  fetchPage: (query: ListQuery) => Promise<Paged<T>>;
  rowKey: (row: T) => string;
  searchPlaceholder?: string;
  emptyIcon?: string;
  emptyMessage?: ReactNode;
  pageSizeOptions?: number[];
  defaultSort?: { by: string; dir: "asc" | "desc" };
  onRowClick?: (row: T) => void;
  /** Bumping this forces a refetch of the current page (e.g. after a create action elsewhere). */
  reloadToken?: number;
}

const DEFAULT_PAGE_SIZES = [10, 20, 50, 100];

export function DataTable<T>({
  columns,
  fetchPage,
  rowKey,
  searchPlaceholder = "Search…",
  emptyIcon = "inbox",
  emptyMessage = "No results.",
  pageSizeOptions = DEFAULT_PAGE_SIZES,
  defaultSort,
  onRowClick,
  reloadToken = 0,
}: DataTableProps<T>) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(pageSizeOptions[1] ?? pageSizeOptions[0]);
  const [qInput, setQInput] = useState("");
  const [sortBy, setSortBy] = useState<string | null>(defaultSort?.by ?? null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">(defaultSort?.dir ?? "asc");
  const [data, setData] = useState<Paged<T> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const debouncedQ = useDebouncedValue(qInput, 350);
  const fetchPageRef = useRef(fetchPage);
  const requestSeq = useRef(0);

  // Keep the ref pointed at the latest callback without forcing it into the fetch effect's
  // dependency array — callers pass fetchPage as an inline closure, so a stable identity can't be
  // assumed the way it can for the rest of the deps below.
  useEffect(() => {
    fetchPageRef.current = fetchPage;
  });

  useEffect(() => {
    const seq = ++requestSeq.current;
    // The canonical data-fetching effect shape (react.dev "You Might Not Need an Effect" lists
    // fetch-on-param-change as a case that does need one) — setLoading here is that effect's own
    // state, not a duplicate of something already derivable at render time.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    fetchPageRef
      .current({ page, page_size: pageSize, q: debouncedQ, sort_by: sortBy, sort_dir: sortDir })
      .then((result) => {
        if (seq !== requestSeq.current) return; // a newer request already landed
        setData(result);
        setError(null);
      })
      .catch((err) => {
        if (seq !== requestSeq.current) return;
        setError(err instanceof ApiError ? err.message : "Failed to load data");
      })
      .finally(() => {
        if (seq === requestSeq.current) setLoading(false);
      });
  }, [page, pageSize, debouncedQ, sortBy, sortDir, reloadToken]);

  function toggleSort(columnKey: string) {
    setPage(1);
    if (sortBy !== columnKey) {
      setSortBy(columnKey);
      setSortDir("asc");
    } else {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    }
  }

  const total = data?.total ?? 0;
  const totalPages = data?.total_pages ?? 1;
  const items = data?.items ?? [];
  const rangeStart = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const rangeEnd = Math.min(page * pageSize, total);

  return (
    <div>
      <div className="table-toolbar">
        <div className="search-field">
          <Icon name="search" />
          <Input
            value={qInput}
            onChange={(e) => {
              setQInput(e.target.value);
              setPage(1);
            }}
            placeholder={searchPlaceholder}
            aria-label="Search"
          />
        </div>
        <span className="table-count">
          {loading ? "Loading…" : `${total} result${total === 1 ? "" : "s"}`}
        </span>
      </div>

      <div className="table-wrap" style={{ border: "none" }}>
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={col.sortable ? "sortable" : undefined}
                  data-active={sortBy === col.key}
                  data-dir={sortBy === col.key ? sortDir : undefined}
                  style={col.align === "right" ? { textAlign: "right" } : undefined}
                >
                  {col.sortable ? (
                    <button type="button" onClick={() => toggleSort(col.key)}>
                      {col.header}
                      <Icon name="chevron-down" className="sort-icon" />
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr className="table-loading-row">
                <td colSpan={columns.length}>Loading…</td>
              </tr>
            ) : error ? (
              <tr className="table-loading-row">
                <td colSpan={columns.length} className="error-text">
                  {error}
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={columns.length} style={{ padding: 0 }}>
                  <EmptyState icon={emptyIcon}>{emptyMessage}</EmptyState>
                </td>
              </tr>
            ) : (
              items.map((row) => (
                <tr
                  key={rowKey(row)}
                  data-clickable={!!onRowClick}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                >
                  {columns.map((col) => (
                    <td key={col.key} style={col.align === "right" ? { textAlign: "right" } : undefined}>
                      {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? "")}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="pager">
        <span className="tabular">
          {total === 0 ? "0 of 0" : `${rangeStart}–${rangeEnd} of ${total}`}
        </span>
        <div className="pager-size">
          <span>Rows per page</span>
          <Select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </Select>
        </div>
        <div className="pager-nav pager-spacer">
          <button
            type="button"
            className="btn btn-ghost btn-icon"
            disabled={page <= 1}
            onClick={() => setPage(1)}
            aria-label="First page"
          >
            <Icon name="arrow-left" />
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-icon"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            aria-label="Previous page"
          >
            <Icon name="chevron-left" />
          </button>
          <span className="tabular" style={{ padding: "0 8px" }}>
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            className="btn btn-ghost btn-icon"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            aria-label="Next page"
          >
            <Icon name="chevron-right" />
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-icon"
            disabled={page >= totalPages}
            onClick={() => setPage(totalPages)}
            aria-label="Last page"
          >
            <Icon name="arrow-right" />
          </button>
        </div>
      </div>
    </div>
  );
}
