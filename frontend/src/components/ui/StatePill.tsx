import { Icon, type IconName } from "./Icon";

/** The eight closed states ebmr-components.css defines under `.state[data-state]` — this set is
 * declared closed by the source design system; domain statuses map onto it, nothing new is added. */
export type DesignState = "accepted" | "blocked" | "failed" | "conflict" | "stale" | "missing" | "unknown" | "na";

export function StatePill({ state, icon, children }: { state: DesignState; icon: IconName | string; children: string }) {
  return (
    <span className="state" data-state={state}>
      <Icon name={icon} /> {children}
    </span>
  );
}

const BATCH_STATE: Record<string, { state: DesignState; icon: IconName; label: string }> = {
  planned: { state: "missing", icon: "help-circle", label: "Planned" },
  issued: { state: "stale", icon: "clock", label: "Issued" },
  in_execution: { state: "stale", icon: "clock", label: "In execution" },
  on_hold: { state: "conflict", icon: "alert-triangle", label: "On hold" },
  production_complete: { state: "accepted", icon: "check-circle", label: "Production complete" },
  qa_review: { state: "conflict", icon: "alert-triangle", label: "QA review" },
  released: { state: "accepted", icon: "check-circle", label: "Released" },
  rejected: { state: "failed", icon: "x", label: "Rejected" },
  closed: { state: "na", icon: "slash-circle", label: "Closed" },
};

export function BatchStatePill({ status }: { status: string }) {
  const entry = BATCH_STATE[status] ?? { state: "unknown" as const, icon: "help-circle" as const, label: status };
  return (
    <StatePill state={entry.state} icon={entry.icon}>
      {entry.label}
    </StatePill>
  );
}

const STEP_STATE: Record<string, { state: DesignState; icon: IconName; label: string }> = {
  pending: { state: "missing", icon: "help-circle", label: "Pending" },
  ready: { state: "unknown", icon: "play", label: "Ready" },
  in_progress: { state: "stale", icon: "clock", label: "In progress" },
  completed: { state: "accepted", icon: "check-circle", label: "Completed" },
  skipped: { state: "na", icon: "slash-circle", label: "Skipped" },
};

export function StepStatePill({ status }: { status: string }) {
  const entry = STEP_STATE[status] ?? { state: "unknown" as const, icon: "help-circle" as const, label: status };
  return (
    <StatePill state={entry.state} icon={entry.icon}>
      {entry.label}
    </StatePill>
  );
}

const MATERIAL_LOT_STATE: Record<string, { state: DesignState; icon: IconName; label: string }> = {
  quarantine: { state: "conflict", icon: "alert-triangle", label: "Quarantine" },
  released: { state: "accepted", icon: "check-circle", label: "Released" },
  rejected: { state: "failed", icon: "x", label: "Rejected" },
  consumed: { state: "na", icon: "slash-circle", label: "Consumed" },
  expired: { state: "failed", icon: "alert-circle", label: "Expired" },
};

export function MaterialLotStatePill({ status }: { status: string }) {
  const entry =
    MATERIAL_LOT_STATE[status] ?? { state: "unknown" as const, icon: "help-circle" as const, label: status };
  return (
    <StatePill state={entry.state} icon={entry.icon}>
      {entry.label}
    </StatePill>
  );
}

// --- WP-05 QMS workflow states ------------------------------------------------------------------
//
// The QMS aggregates (deviation, CAPA, NCR, change, complaint, SCAR, field action, audit, risk) each
// run their own state machine, together using 50+ uppercase state names. Enumerating all of them here
// would mean this file drifts out of date every time a command adds a step, so classify by outcome
// instead: a state is terminal-good, terminal-inert, failed, needs-attention, or in-flight. Anything
// unrecognised still renders — as its own name under the neutral "unknown" style — rather than
// vanishing or crashing.

const TERMINAL_GOOD = new Set([
  "CLOSED", "COMPLETE", "COMPLETED", "EFFECTIVE", "RELEASED", "VERIFIED", "ACCEPTED", "QUALIFIED",
  "IMPLEMENTATION_VERIFIED", "APPROVED",
  // Document 38 equipment lifecycle
  "QUALIFIED_AVAILABLE",
]);
const TERMINAL_INERT = new Set([
  "CANCELLED", "OBSOLETE", "SUPERSEDED", "FROZEN", "NO_INVESTIGATION_JUSTIFIED", "SUSPENDED",
]);
const FAILED = new Set(["EFFECTIVENESS_FAILED", "REJECTED", "OUT_OF_SERVICE"]);
const NEEDS_ATTENTION = new Set([
  "OPEN", "REOPENED", "FINDINGS_OPEN", "SEGREGATED", "NEW_VERSION",
  "CALIBRATION_DUE", "MAINTENANCE_DUE",
]);
const NOT_STARTED = new Set([
  "DRAFT", "SCHEDULED", "ASSIGNED", "RECEIVED", "INSTALLED", "QUALIFICATION_PENDING",
]);

/** Title-cases an uppercase state name for display: `IMPACT_ASSESSMENT` -> `Impact assessment`. */
function labelFor(state: string): string {
  const words = state.replace(/_/g, " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function WorkflowStatePill({ state }: { state: string }) {
  const key = state.toUpperCase();
  const [design, icon]: [DesignState, IconName] = TERMINAL_GOOD.has(key)
    ? ["accepted", "check-circle"]
    : FAILED.has(key)
      ? ["failed", "x"]
      : TERMINAL_INERT.has(key)
        ? ["na", "slash-circle"]
        : NEEDS_ATTENTION.has(key)
          ? ["conflict", "alert-triangle"]
          : NOT_STARTED.has(key)
            ? ["missing", "clock"]
            : ["stale", "clock"];

  return (
    <StatePill state={design} icon={icon}>
      {labelFor(state)}
    </StatePill>
  );
}

// Severity is a separate axis from workflow state — a CLOSED deviation can still have been critical —
// so it gets its own pill rather than being folded into the state colour.
const SEVERITY_STATE: Record<string, DesignState> = {
  critical: "failed",
  major: "conflict",
  serious: "conflict",
  moderate: "stale",
  minor: "missing",
  low: "missing",
};

export function SeverityPill({ severity }: { severity: string | null | undefined }) {
  if (!severity) return <span className="text-muted">—</span>;
  const design = SEVERITY_STATE[severity.toLowerCase()] ?? "unknown";
  return (
    <StatePill state={design} icon={design === "failed" ? "alert-circle" : "alert-triangle"}>
      {labelFor(severity)}
    </StatePill>
  );
}

/** Yes/no flags the QMS records carry (`capa_required`, `release_blocker_active`, …). `null` means
 * "not yet assessed", which is a different thing from "no" and is shown as such. */
export function BoolPill({ value, trueLabel = "Yes", falseLabel = "No" }: { value: boolean | null | undefined; trueLabel?: string; falseLabel?: string }) {
  if (value === null || value === undefined) {
    return (
      <StatePill state="missing" icon="help-circle">
        Not assessed
      </StatePill>
    );
  }
  return value ? (
    <StatePill state="conflict" icon="check">
      {trueLabel}
    </StatePill>
  ) : (
    <StatePill state="na" icon="slash-circle">
      {falseLabel}
    </StatePill>
  );
}
