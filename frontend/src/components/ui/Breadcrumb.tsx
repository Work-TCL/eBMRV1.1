import Link from "next/link";
import { Icon } from "./Icon";

export interface Crumb {
  label: string;
  href?: string;
}

export function Breadcrumb({ items }: { items: Crumb[] }) {
  return (
    <div className="breadcrumb">
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-2">
          {i > 0 && <Icon name="chevron-right" />}
          {item.href ? (
            <Link href={item.href}>{item.label}</Link>
          ) : (
            <span className="font-semibold" style={{ color: "var(--ink-primary)" }}>
              {item.label}
            </span>
          )}
        </span>
      ))}
    </div>
  );
}
