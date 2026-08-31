"use client";

import { useRequireAdmin } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card } from "@/components/ui/Card";
import { LinkButton } from "@/components/ui/Button";
import { Icon, type IconName } from "@/components/ui/Icon";

const SECTIONS: { href: string; label: string; description: string; icon: IconName }[] = [
  { href: "/admin/company", label: "Company", description: "Edit this deployment's company name.", icon: "building" },
  { href: "/admin/sites", label: "Sites", description: "Create, edit, and delete manufacturing sites.", icon: "building" },
  { href: "/admin/users", label: "Users", description: "Create users, edit details, and assign roles per site.", icon: "users" },
  { href: "/admin/roles", label: "Roles", description: "Create, edit, and delete roles.", icon: "users" },
];

export default function AdminLandingPage() {
  const { isAdmin } = useRequireAdmin();
  if (!isAdmin) return null;

  return (
    <div>
      <PageHead title="Admin" subtitle="Company, sites, users, and roles." />
      <div className="grid grid-cols-2 gap-4">
        {SECTIONS.map((s) => (
          <Card key={s.href} pad>
            <div className="flex items-start gap-3">
              <Icon name={s.icon} />
              <div className="flex-1">
                <div className="font-semibold fs-3 mb-1">{s.label}</div>
                <p className="text-muted fs-2 mb-3">{s.description}</p>
                <LinkButton href={s.href} variant="secondary">
                  Open
                </LinkButton>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
