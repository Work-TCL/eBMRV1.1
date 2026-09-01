"use client";

import { useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { pagedFetcher } from "@/lib/api";
import { useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Select } from "@/components/ui/Select";
import type { IconName } from "@/components/ui/Icon";

/** The register scaffold every list screen in the app is built from.
 *
 * Generalised from the WP-05 `QmsListPage` (which now re-exports this): a paged, searchable
 * `DataTable` under a `PageHead`, optionally scoped to the active site and optionally filtered by a
 * workflow-state dropdown. Each concrete register file supplies only its columns, its state
 * vocabulary and its create action.
 */
export function RecordListPage<T>({
  title,
  subtitle,
  path,
  columns,
  states,
  stateParam = "state",
  siteScoped = true,
  extraParams,
  searchPlaceholder = "Search…",
  emptyIcon,
  emptyMessage,
  rowHref,
  action,
  reloadToken = 0,
  defaultSort,
  children,
}: {
  title: ReactNode;
  subtitle: ReactNode;
  /** API collection path, e.g. `/qms/v1/deviations`. */
  path: string;
  columns: DataTableColumn<T>[];
  /** Workflow states this aggregate can be in, for the filter dropdown. Omit for no state filter. */
  states?: readonly string[];
  /** Query-param name the state filter sends. Defaults to `state`. */
  stateParam?: string;
  /** When true (default) the list waits for the active site and sends `site_id`. Set false for
   * resources the backend does not scope by site (registries, platform ops). */
  siteScoped?: boolean;
  /** Additional static or reactive query params merged into every request. */
  extraParams?: () => Record<string, string>;
  searchPlaceholder?: string;
  emptyIcon?: IconName | string;
  emptyMessage?: ReactNode;
  /** Given a row, the detail route to open on click. Omit for registers with no detail page. */
  rowHref?: (row: T) => string;
  /** Header action — normally the "create a record" button. */
  action?: ReactNode;
  reloadToken?: number;
  defaultSort?: { by: string; dir: "asc" | "desc" };
  /** Rendered between the page head and the table — KPI rows, banners. */
  children?: ReactNode;
}) {
  const router = useRouter();
  const { siteId, loading: siteLoading } = useSiteId();
  const [state, setState] = useState("");
  const [filterToken, setFilterToken] = useState(0);

  // DataTable holds fetchPage in a ref rather than an effect dependency, so this inline closure reads
  // current filter state directly; changing a filter bumps the token to force the refetch.
  const fetchPage = pagedFetcher<T>(path, () => ({
    ...(siteScoped ? { site_id: siteId ?? "" } : {}),
    ...(states ? { [stateParam]: state } : {}),
    ...(extraParams?.() ?? {}),
  }));

  const waiting = siteScoped && siteLoading;

  return (
    <div>
      <PageHead title={title} subtitle={subtitle} action={action} />
      {children}
      <Card>
        <CardHeader
          title="Register"
          meta={
            states ? (
              <span className="flex items-center gap-2">
                State
                <Select
                  value={state}
                  onChange={(e) => {
                    setState(e.target.value);
                    setFilterToken((n) => n + 1);
                  }}
                >
                  <option value="">All</option>
                  {states.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </Select>
              </span>
            ) : undefined
          }
        />
        {/* Holding the table until the site resolves avoids one unscoped request that would return
            every site's rows and never correct itself (DataTable does not watch `siteId`). */}
        {waiting ? (
          <p className="table-loading-row" style={{ padding: "var(--space-4)" }}>
            Loading…
          </p>
        ) : (
          <DataTable
            columns={columns}
            fetchPage={fetchPage}
            rowKey={(row) => (row as { id: string }).id}
            searchPlaceholder={searchPlaceholder}
            emptyIcon={emptyIcon}
            emptyMessage={emptyMessage}
            defaultSort={defaultSort ?? { by: "created_at", dir: "desc" }}
            reloadToken={reloadToken + filterToken}
            onRowClick={rowHref ? (row) => router.push(rowHref(row)) : undefined}
          />
        )}
      </Card>
    </div>
  );
}
