import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

const TONE_ICON: Record<string, IconName> = {
  info: "info",
  ok: "check-circle",
  warn: "alert-triangle",
  critical: "alert-triangle",
};

export function Banner({
  tone,
  title,
  children,
  icon,
}: {
  tone: "info" | "ok" | "warn" | "critical";
  title?: ReactNode;
  children?: ReactNode;
  icon?: IconName;
}) {
  return (
    <div className="banner" data-tone={tone}>
      <Icon name={icon ?? TONE_ICON[tone]} />
      <div>
        {title && <p className="font-semibold">{title}</p>}
        {children && <p className="fs-3 mt-1">{children}</p>}
      </div>
    </div>
  );
}
