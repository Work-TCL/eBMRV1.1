"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/Icon";

export interface ContextItem {
  k: string;
  v: string;
}

export function ContextBar({
  items,
  commit,
}: {
  items: ContextItem[];
  commit?: { state: "committed" | "uncommitted" | "offline"; label: string };
}) {
  const [now, setNow] = useState<string | null>(null);

  useEffect(() => {
    const format = () =>
      new Date().toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    // The clock reads the browser's local time, unknowable during server rendering — this is
    // exactly what an effect is for, so the rule is suppressed deliberately, as in AuthGuard.tsx.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setNow(format());
    const id = setInterval(() => setNow(format()), 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="context-bar">
      {commit && (
        <span className="context-item">
          <span className="commit-indicator" data-commit={commit.state}>
            <span className="dot" /> {commit.label}
          </span>
        </span>
      )}
      {items.map((item) => (
        <span className="context-item" key={item.k}>
          <span className="k">{item.k}</span>
          <span className="v">{item.v}</span>
        </span>
      ))}
      {now && (
        <span className="context-clock">
          <Icon name="clock" /> {now}
        </span>
      )}
    </div>
  );
}
