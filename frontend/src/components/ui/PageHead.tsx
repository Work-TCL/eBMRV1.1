import type { ReactNode } from "react";

export function PageHead({ title, subtitle, action }: { title: ReactNode; subtitle?: ReactNode; action?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {/* `.page-head`'s `justify-content: space-between` only pushes `action` to the end while it
          shares a flex line with the title block. A long subtitle (line-clearance) or a wide action
          block (sterilization's 3 header buttons) makes `action` wrap onto its own line, where
          `space-between` has nothing to distribute against and leaves a lone item at the line's
          start instead of its end. `margin-left: auto` pushes it to the end unconditionally, wrapped
          or not. */}
      {action && <div style={{ marginLeft: "auto" }}>{action}</div>}
    </div>
  );
}
