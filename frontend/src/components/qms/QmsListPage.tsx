"use client";

import type { ReactNode } from "react";
import { RecordListPage } from "@/components/shared/RecordListPage";
import type { DataTableColumn } from "@/components/ui/DataTable";
import type { IconName } from "@/components/ui/Icon";

/** WP-05 QMS registers list identically — site-scoped, state-filtered, searchable by record number.
 * The generic scaffold now lives in `RecordListPage`; this preserves the QMS call signature and the
 * "Search by record number…" placeholder every QMS register was built against. */
export function QmsListPage<T>(props: {
  title: ReactNode;
  subtitle: ReactNode;
  path: string;
  columns: DataTableColumn<T>[];
  states: readonly string[];
  emptyIcon: IconName | string;
  emptyMessage: ReactNode;
  rowHref?: (row: T) => string;
  action?: ReactNode;
  reloadToken?: number;
  defaultSort?: { by: string; dir: "asc" | "desc" };
  children?: ReactNode;
}) {
  return <RecordListPage<T> searchPlaceholder="Search by record number…" {...props} />;
}
