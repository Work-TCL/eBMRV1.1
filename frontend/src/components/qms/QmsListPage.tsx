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

/** Shared scaffold for the WP-05 QMS registers.
 *
 * Every QMS aggregate lists the same way — site-scoped, filterable by workflow state, searchable on
 * its record number — because the backend gives them all one list contract (see
 * app/modules/qms/read_support.py). This holds that layout so each register file is only its columns,
 * its state vocabulary and its create action.
 */
export function QmsListPage<T>({
  title,
  subtitle,
  path,
  columns,
  states,
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
  /** Workflow states this aggregate can be in, for the filter dropdown. */
  states: readonly string[];
  emptyIcon: IconName | string;
  emptyMessage: ReactNode;
  /** Given a row, the detail route to open on click. Omit for registers with no detail page. */
  rowHref?: (row: T) => string;
  /** Header action — normally the "raise a record" button. */
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

  // DataTable keeps fetchPage in a ref rather than an effect dependency, so this inline closure reads
  // current filter state directly; changing a filter bumps the token to force the refetch.
  const fetchPage = pagedFetcher<T>(path, () => ({ site_id: siteId ?? "", state }));

  return (
    <div>
      <PageHead title={title} subtitle={subtitle} action={action} />
      {children}
      <Card>
        <CardHeader
          title="Register"
          meta={
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
          }
        />
        {/* DataTable fetches on mount and only refetches when its own inputs change — it does not watch
            `siteId`. Mounting it before the site resolves would issue one unscoped request (returning
            every site's records) and never correct itself, so hold it until the site is known. */}
        {siteLoading ? (
          <p className="table-loading-row" style={{ padding: "var(--space-4)" }}>
            Loading…
          </p>
        ) : (
          <DataTable
            columns={columns}
            fetchPage={fetchPage}
            rowKey={(row) => (row as { id: string }).id}
            searchPlaceholder="Search by record number…"
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
