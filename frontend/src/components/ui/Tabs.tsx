"use client";

import { useState, type ReactNode } from "react";

export interface TabDef {
  id: string;
  label: ReactNode;
  /** Rendered next to the label — a count, usually. Omit rather than pass 0 to hide an empty badge. */
  badge?: ReactNode;
  content: ReactNode;
}

/** The design system's `.tabs` / `.tab-btn` / `.tab-panel` set. Panels are all mounted and toggled by
 * `data-active` (which is how the CSS shows them), so a tab that owns form state keeps it across a
 * switch instead of remounting empty. */
export function Tabs({ tabs, initial }: { tabs: TabDef[]; initial?: string }) {
  const [active, setActive] = useState(initial ?? tabs[0]?.id);

  return (
    <div>
      <div className="tabs" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            className="tab-btn"
            aria-selected={active === tab.id}
            onClick={() => setActive(tab.id)}
          >
            {tab.label}
            {tab.badge !== undefined && tab.badge !== null && (
              <span className="fs-1 text-muted" style={{ marginLeft: 6 }}>
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>
      {tabs.map((tab) => (
        <div
          key={tab.id}
          role="tabpanel"
          className="tab-panel"
          data-active={active === tab.id ? "" : undefined}
          style={{ paddingTop: "var(--space-4)" }}
        >
          {tab.content}
        </div>
      ))}
    </div>
  );
}
