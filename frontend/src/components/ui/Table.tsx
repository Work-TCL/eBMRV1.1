import type { ReactNode } from "react";
import { Icon } from "./Icon";

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="table-wrap" style={{ border: "none", borderTop: "1px solid var(--border-hairline)" }}>
      <table className="data-table">{children}</table>
    </div>
  );
}

export function EmptyState({ icon = "inbox", children }: { icon?: string; children: ReactNode }) {
  return (
    <div className="empty-state">
      <Icon name={icon} className="icon" />
      <p>{children}</p>
    </div>
  );
}
