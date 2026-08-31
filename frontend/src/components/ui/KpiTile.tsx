import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

/** `.kpi-tile` from the design system. `tone` colours the delta line only — the value stays
 * ink-primary so a row of tiles reads as one scale rather than a traffic light. */
export function KpiTile({
  label,
  value,
  delta,
  icon,
  tone,
}: {
  label: ReactNode;
  value: ReactNode;
  delta?: ReactNode;
  icon?: IconName;
  tone?: "ok" | "warn" | "critical";
}) {
  // The design system's status text tokens (ebmr-tokens.css) — the same three the `.state` pills use,
  // so a tile's delta and a pill for the same condition are never two different reds.
  const deltaColor =
    tone === "critical"
      ? "var(--status-critical-text)"
      : tone === "warn"
        ? "var(--status-warning-text)"
        : tone === "ok"
          ? "var(--status-good-text)"
          : undefined;

  return (
    <div className="kpi-tile">
      <div className="kpi-label">
        {icon && <Icon name={icon} />}
        {label}
      </div>
      <div className="kpi-value tabular">{value}</div>
      {delta && (
        <div className="kpi-delta" style={deltaColor ? { color: deltaColor } : undefined}>
          {delta}
        </div>
      )}
    </div>
  );
}

/** Responsive row of KPI tiles — auto-fits at a 190px minimum so three to six tiles all sit well. */
export function KpiRow({ children }: { children: ReactNode }) {
  return (
    <div
      className="mb-4"
      style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: "var(--space-4)" }}
    >
      {children}
    </div>
  );
}
