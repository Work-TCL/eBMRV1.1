"use client";

/** WP-05 QMS detail pages were built against `QmsDetailShell` / `useCommand`. Both are now the
 * generic `RecordDetailShell` primitives; this file keeps the QMS import path working. */
export { RecordDetailShell as QmsDetailShell, useCommand } from "@/components/shared/RecordDetailShell";
