import type { CSSProperties, ReactNode } from "react";

export function Card({
  children,
  pad,
  className,
  style,
}: {
  children: ReactNode;
  pad?: boolean;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div className={`card${pad ? " card-pad" : ""}${className ? ` ${className}` : ""}`} style={style}>
      {children}
    </div>
  );
}

export function CardHeader({ title, meta }: { title: ReactNode; meta?: ReactNode }) {
  return (
    <div className="card-header">
      <div className="card-title">{title}</div>
      {meta && <span className="fs-2 text-muted">{meta}</span>}
    </div>
  );
}
