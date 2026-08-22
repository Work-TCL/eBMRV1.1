"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Icon, type IconName } from "@/components/ui/Icon";
import { logout } from "@/lib/api";
import { useMe } from "@/lib/hooks";

const PRODUCTION_NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "/products", label: "Products", icon: "package" },
  { href: "/recipes", label: "Recipes", icon: "database" },
  { href: "/batches", label: "Batches", icon: "flask" },
];

const MATERIALS_NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "/materials", label: "Materials", icon: "scale" },
  { href: "/material-lots", label: "Material lots", icon: "list-checks" },
];

export function Sidebar({ open }: { open: boolean }) {
  const pathname = usePathname();
  const router = useRouter();
  const { me } = useMe();

  return (
    <aside className={`sidebar${open ? " open" : ""}`}>
      <div className="sidebar-brand">
        <div className="sidebar-mark">
          <Icon name="layers" />
        </div>
        <div>
          <div className="fs-3 font-bold" style={{ color: "var(--ink-primary)" }}>
            eBMR
          </div>
          <div className="fs-1 text-muted">Electronic Batch Manufacturing Record</div>
        </div>
      </div>
      <nav className="sidebar-nav scrollbar-thin">
        <div className="sidebar-section">Production</div>
        {PRODUCTION_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="sidebar-link"
            aria-current={pathname.startsWith(item.href) ? "page" : undefined}
          >
            <Icon name={item.icon} /> {item.label}
          </Link>
        ))}
        <div className="sidebar-section">Materials &amp; QC</div>
        {MATERIALS_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="sidebar-link"
            aria-current={pathname.startsWith(item.href) ? "page" : undefined}
          >
            <Icon name={item.icon} /> {item.label}
          </Link>
        ))}
      </nav>
      <div className="sidebar-foot">
        {me && (
          <div className="role-badge">
            <span className="k">Signed in as</span>
            <span className="v">{me.username}</span>
          </div>
        )}
        <button
          className="sidebar-link"
          style={{ width: "100%", border: "none", background: "none", cursor: "pointer", font: "inherit", textAlign: "left" }}
          onClick={() => {
            logout();
            router.push("/login");
          }}
        >
          <Icon name="log-out" /> Sign out
        </button>
      </div>
    </aside>
  );
}
