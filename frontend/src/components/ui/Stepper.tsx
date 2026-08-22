import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

// "pending" deliberately matches none of the CSS-styled states — it falls back to the base
// `.step-marker` look (grey border, muted), which is the correct rendering for "not reachable yet."
export type StepMarkerState = "completed" | "current" | "blocked" | "available" | "pending";

export function Stepper({ children }: { children: ReactNode }) {
  return <div className="stepper">{children}</div>;
}

export function StepItem({
  state,
  number,
  icon,
  title,
  meta,
  action,
}: {
  state: StepMarkerState;
  number: number;
  icon?: IconName;
  title: ReactNode;
  meta?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="step-item" data-step-state={state}>
      <div className="step-marker">{icon ? <Icon name={icon} /> : number}</div>
      <div className="flex-1">
        <div className="step-title">{title}</div>
        {meta && <div className="step-meta">{meta}</div>}
      </div>
      {action}
    </div>
  );
}
