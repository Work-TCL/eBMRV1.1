"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Icon, type IconName } from "@/components/ui/Icon";
import {
  canAuthorRules,
  canReviewAudit,
  canReviewVault,
  canViewEquipment,
  canViewProduct,
  canViewQms,
  canViewRecipe,
  isAdminAnywhere,
  logout,
} from "@/lib/api";
import { useMe } from "@/lib/hooks";

const PRODUCTION_NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "/products", label: "Products", icon: "package" },
  { href: "/recipes", label: "Recipes", icon: "database" },
  { href: "/batches", label: "Batches", icon: "flask" },
];

const MATERIALS_NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "/materials", label: "Materials", icon: "scale" },
  { href: "/material-lots", label: "Material lots", icon: "list-checks" },
  { href: "/inventory", label: "Inventory", icon: "inbox" },
  { href: "/dispensing", label: "Dispensing", icon: "droplet" },
  { href: "/qc", label: "QC testing", icon: "flask" },
];

const QUALITY_NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "/deviations", label: "Deviations", icon: "alert-triangle" },
  { href: "/capa", label: "CAPA", icon: "shield-check" },
  { href: "/nonconformances", label: "Nonconformances", icon: "cross-medical" },
  { href: "/changes", label: "Change control", icon: "refresh" },
  { href: "/complaints", label: "Complaints", icon: "bell" },
  { href: "/field-actions", label: "Field actions", icon: "flag" },
  { href: "/audits", label: "Internal audits", icon: "clipboard" },
  { href: "/risks", label: "Risk register", icon: "gauge" },
  { href: "/supplier-cases", label: "Supplier cases", icon: "building" },
  { href: "/documents", label: "Documents", icon: "file-text" },
  { href: "/training", label: "Training", icon: "users" },
  { href: "/quality-metrics", label: "Quality metrics", icon: "gauge" },
];

const OPERATIONS_NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "/batch-execution", label: "Batch execution", icon: "play" },
  { href: "/equipment", label: "Equipment", icon: "scan" },
  { href: "/packaging", label: "Packaging", icon: "package" },
  { href: "/qa-review", label: "QA review", icon: "clipboard" },
  { href: "/release", label: "Release", icon: "badge-check" },
  { href: "/genealogy", label: "Genealogy", icon: "layers" },
  { href: "/devices", label: "Devices", icon: "scan" },
  { href: "/suppliers", label: "Suppliers", icon: "building" },
];

const RULES_NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "/rules", label: "Rules", icon: "gauge" },
];

const ADMIN_NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "/admin/company", label: "Company", icon: "building" },
  { href: "/admin/sites", label: "Sites", icon: "building" },
  { href: "/admin/users", label: "Users", icon: "users" },
  { href: "/admin/roles", label: "Roles", icon: "users" },
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
        {canViewProduct(me) && (
          <Link
            href="/product-master"
            className="sidebar-link"
            aria-current={pathname.startsWith("/product-master") ? "page" : undefined}
          >
            <Icon name="package" /> Product Master
          </Link>
        )}
        {canViewRecipe(me) && (
          <Link
            href="/recipe-master"
            className="sidebar-link"
            aria-current={pathname.startsWith("/recipe-master") ? "page" : undefined}
          >
            <Icon name="database" /> Recipe Master
          </Link>
        )}
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
        {canViewEquipment(me) && (
          <>
            <div className="sidebar-section">Operations</div>
            {OPERATIONS_NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="sidebar-link"
                aria-current={pathname.startsWith(item.href) ? "page" : undefined}
              >
                <Icon name={item.icon} /> {item.label}
              </Link>
            ))}
          </>
        )}
        {canViewQms(me) && (
          <>
            <div className="sidebar-section">Quality system</div>
            {QUALITY_NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="sidebar-link"
                aria-current={pathname.startsWith(item.href) ? "page" : undefined}
              >
                <Icon name={item.icon} /> {item.label}
              </Link>
            ))}
          </>
        )}
        {(canReviewAudit(me) || canReviewVault(me)) && (
          <>
            <div className="sidebar-section">Compliance</div>
            {canReviewAudit(me) && (
              <Link href="/audit" className="sidebar-link" aria-current={pathname.startsWith("/audit") ? "page" : undefined}>
                <Icon name="history" /> Audit ledger
              </Link>
            )}
            {canReviewVault(me) && (
              <Link href="/vault" className="sidebar-link" aria-current={pathname.startsWith("/vault") ? "page" : undefined}>
                <Icon name="lock" /> Vault
              </Link>
            )}
          </>
        )}
        {canAuthorRules(me) && (
          <>
            <div className="sidebar-section">Engineering</div>
            {RULES_NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="sidebar-link"
                aria-current={pathname.startsWith(item.href) ? "page" : undefined}
              >
                <Icon name={item.icon} /> {item.label}
              </Link>
            ))}
          </>
        )}
        {isAdminAnywhere(me) && (
          <>
            <div className="sidebar-section">Admin</div>
            {ADMIN_NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="sidebar-link"
                aria-current={pathname.startsWith(item.href) ? "page" : undefined}
              >
                <Icon name={item.icon} /> {item.label}
              </Link>
            ))}
          </>
        )}
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
