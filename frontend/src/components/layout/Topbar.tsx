"use client";

import { usePathname } from "next/navigation";
import { Icon } from "@/components/ui/Icon";
import { Breadcrumb, type Crumb } from "@/components/ui/Breadcrumb";

const SECTION_LABEL: Record<string, string> = {
  products: "Products",
  recipes: "Recipes",
  batches: "Batches",
};

function crumbsFor(pathname: string): Crumb[] {
  const [section, ...rest] = pathname.split("/").filter(Boolean);
  const sectionLabel = SECTION_LABEL[section] ?? section;
  if (rest.length === 0) return [{ label: sectionLabel }];

  const sectionHref = `/${section}`;
  const [sub] = rest;
  const subLabel = sub === "new" ? "New" : sub;
  return [
    { label: sectionLabel, href: sectionHref },
    { label: subLabel },
  ];
}

export function Topbar({ onToggleSidebar }: { onToggleSidebar: () => void }) {
  const pathname = usePathname();
  return (
    <header className="topbar">
      <button className="btn-icon btn-ghost" onClick={onToggleSidebar} aria-label="Toggle navigation">
        <Icon name="menu" />
      </button>
      <Breadcrumb items={crumbsFor(pathname)} />
    </header>
  );
}
