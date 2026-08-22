import { ICONS, type IconName } from "./icons";

export type { IconName };

export function Icon({ name, className }: { name: IconName | string; className?: string }) {
  const inner = ICONS[name];
  if (!inner) return null;
  return (
    <svg
      className={`icon${className ? ` ${className}` : ""}`}
      viewBox="0 0 24 24"
      width="16"
      height="16"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: inner }}
    />
  );
}
