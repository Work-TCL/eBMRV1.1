"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Icon, type IconName } from "@/components/ui/Icon";
import {
  canAuthorRules,
  canReviewAudit,
  canReviewVault,
  canViewProduct,
  canViewQms,
  canViewRecipe,
  isAdminAnywhere,
  logout,
  type Me,
} from "@/lib/api";
import { useMe } from "@/lib/hooks";

interface NavItem {
  href: string;
  label: string;
  icon: IconName;
  /** Per-item gate. Defaults to the section gate. */
  show?: (me: Me | null) => boolean;
}

interface NavSection {
  label: string;
  show: (me: Me | null) => boolean;
  items: NavItem[];
}

const signedIn = (me: Me | null) => me !== null;

/** The navigation model. Each section and item can gate itself on the signed-in user's roles.
 * Order top-to-bottom is render order. */
const SECTIONS: NavSection[] = [
  {
    label: "Production",
    show: signedIn,
    items: [
      { href: "/product-master", label: "Product master", icon: "package", show: canViewProduct },
      { href: "/recipe-master", label: "Recipe master", icon: "database", show: canViewRecipe },
      { href: "/ddcp", label: "DDCP profiles", icon: "layers" },
    ],
  },
  {
    label: "Materials & QC",
    show: signedIn,
    items: [
      { href: "/materials", label: "Materials", icon: "scale" },
      { href: "/material-specifications", label: "Material specifications", icon: "file-text" },
      { href: "/material-receipts", label: "Material receipts", icon: "package" },
      { href: "/material-lots", label: "Material lots", icon: "list-checks" },
      { href: "/inventory", label: "Inventory", icon: "inbox" },
      { href: "/dispensing", label: "Dispensing", icon: "droplet" },
      { href: "/qc", label: "QC testing", icon: "flask" },
      { href: "/quality/oos", label: "OOS / OOT", icon: "alert-triangle" },
    ],
  },
  {
    label: "Operations",
    // Every operational role can reach at least one of these; individual pages enforce their own access.
    show: signedIn,
    items: [
      { href: "/batch-execution", label: "Batch execution", icon: "play" },
      { href: "/equipment", label: "Equipment", icon: "scan" },
      { href: "/cleaning", label: "Cleaning", icon: "droplet" },
      { href: "/line-clearance", label: "Line clearance", icon: "flag" },
      { href: "/sterilization", label: "Sterilization", icon: "flask" },
      { href: "/aseptic", label: "Aseptic operations", icon: "shield-check" },
      { href: "/em", label: "Environmental monitoring", icon: "gauge" },
      { href: "/packaging", label: "Packaging", icon: "package" },
      { href: "/qa-review", label: "QA review", icon: "clipboard" },
      { href: "/release", label: "Release", icon: "badge-check" },
      { href: "/yield", label: "Yield & reconciliation", icon: "gauge" },
      { href: "/genealogy", label: "Genealogy", icon: "layers" },
      { href: "/devices", label: "Devices", icon: "scan" },
      { href: "/suppliers", label: "Suppliers", icon: "building" },
    ],
  },
  {
    label: "Quality system",
    show: canViewQms,
    items: [
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
    ],
  },
  {
    label: "Integrations",
    show: signedIn,
    items: [
      { href: "/integrations/lims", label: "LIMS", icon: "refresh" },
      { href: "/integrations/erp", label: "ERP", icon: "refresh" },
    ],
  },
  {
    label: "Postmarket",
    show: canViewQms,
    items: [{ href: "/postmarket", label: "Safety & reporting", icon: "bell" }],
  },
  {
    label: "Validation",
    show: canViewQms,
    items: [
      { href: "/validation", label: "Validation platform", icon: "clipboard" },
      { href: "/validation/go-live", label: "Deployment · PQ · go-live", icon: "badge-check" },
    ],
  },
  {
    label: "AI",
    show: canViewQms,
    items: [{ href: "/ai", label: "AI governance", icon: "shield-check" }],
  },
  {
    label: "Compliance",
    show: (me) => canReviewAudit(me) || canReviewVault(me),
    items: [
      { href: "/audit", label: "Audit ledger", icon: "history", show: canReviewAudit },
      { href: "/vault", label: "Vault", icon: "lock", show: canReviewVault },
    ],
  },
  {
    label: "Engineering",
    show: canAuthorRules,
    items: [{ href: "/rules", label: "Rules", icon: "gauge" }],
  },
  {
    label: "Admin",
    show: isAdminAnywhere,
    items: [
      { href: "/admin/company", label: "Company", icon: "building" },
      { href: "/admin/sites", label: "Sites", icon: "building" },
      { href: "/admin/users", label: "Users", icon: "users" },
      { href: "/admin/roles", label: "Roles", icon: "users" },
      { href: "/admin/access-review", label: "Access review", icon: "shield-check" },
      { href: "/security", label: "Security", icon: "lock" },
      { href: "/platform", label: "Platform ops", icon: "database" },
      { href: "/edge", label: "Edge gateways", icon: "scan" },
      { href: "/machine-integration", label: "Machine integration", icon: "scan" },
    ],
  },
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
        {SECTIONS.filter((section) => section.show(me)).map((section) => {
          const items = section.items.filter((item) => (item.show ?? section.show)(me));
          if (items.length === 0) return null;
          return (
            <div key={section.label}>
              <div className="sidebar-section">{section.label}</div>
              {items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="sidebar-link"
                  aria-current={pathname.startsWith(item.href) ? "page" : undefined}
                >
                  <Icon name={item.icon} /> {item.label}
                </Link>
              ))}
            </div>
          );
        })}
      </nav>
      <div className="sidebar-foot">
        {me && (
          <div className="role-badge">
            <span className="k">Signed in as</span>
            <span className="v">{me.username}</span>
          </div>
        )}
        <button
          className="sidebar-link sidebar-link--btn"
          onClick={() => {
            void logout().then(() => router.push("/login"));
          }}
        >
          <Icon name="log-out" /> Sign out
        </button>
      </div>
    </aside>
  );
}
