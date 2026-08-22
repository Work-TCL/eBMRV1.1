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
