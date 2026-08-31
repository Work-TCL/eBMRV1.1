import type { ReactNode } from "react";

/** The design system's `.fact-grid` / `.fact` / `.fact-k` / `.fact-v` triple (ebmr-components.css
 * §"facts"), wrapped so record-header summaries stop being hand-rolled per page. Auto-fits columns at
 * a 230px minimum, so callers pass facts and let the grid decide the wrap. */
export function FactGrid({ children }: { children: ReactNode }) {
  return <div className="fact-grid">{children}</div>;
}

export function Fact({ label, children }: { label: ReactNode; children: ReactNode }) {
  return (
    <div className="fact">
      <span className="fact-k">{label}</span>
      <span className="fact-v" style={{ wordBreak: "break-word" }}>
        {children}
      </span>
    </div>
  );
}

/** Facts whose value is an id/hash — same slot, monospaced and break-anywhere so a UUID can't push
 * the grid wider than its column. */
export function IdFact({ label, value }: { label: ReactNode; value: string | null | undefined }) {
  return (
    <div className="fact">
      <span className="fact-k">{label}</span>
      <span className="fact-v tabular fs-2" style={{ wordBreak: "break-all" }}>
        {value ?? "—"}
      </span>
    </div>
  );
}
