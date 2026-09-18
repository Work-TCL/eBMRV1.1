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
 * the grid wider than its column. `action` is an optional slot (e.g. a copy button, a link to another
 * page keyed off this id) rendered right after the value — added closing
 * DDCP_Client_Demo_Guide_Gujarati.md §19 #33's "Batch ID plain, selectable UUID text ... copy-button
 * નથી, href નથી" finding; every other IdFact caller is unaffected since the prop is optional. */
export function IdFact({ label, value, action }: { label: ReactNode; value: string | null | undefined; action?: ReactNode }) {
  return (
    <div className="fact">
      <span className="fact-k">{label}</span>
      {/* Only wrapped in a flex row when an action is actually passed — a bare flex container can stop
       * a long single text node from wrapping via word-break the way every existing IdFact caller
       * (without an action) relies on to keep a UUID from pushing the grid wider than its column. */}
      {value && action ? (
        <span className="fact-v flex items-center gap-1">
          <span className="tabular fs-2" style={{ wordBreak: "break-all" }}>
            {value}
          </span>
          {action}
        </span>
      ) : (
        <span className="fact-v tabular fs-2" style={{ wordBreak: "break-all" }}>
          {value ?? "—"}
        </span>
      )}
    </div>
  );
}
