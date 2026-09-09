"use client";

// Re-exported from the app-wide shared hook (`lib/hooks.ts`) — this file previously implemented the
// batch/equipment picker fetch locally; it's now also the basis for the same picker in FormConsole and
// OpsRecordPage, so the fetch/state logic lives in one place. Kept as a thin re-export (rather than
// updating every DDCP import site) so nothing else in `components/ddcp/*` needs to change.
export { useEntityOptions as useDdcpEntityOptions, type EntityOptionsStatus as AsyncStatus } from "@/lib/hooks";
