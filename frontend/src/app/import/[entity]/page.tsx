"use client";

import { use } from "react";
import Link from "next/link";
import { UsersImportPage } from "@/components/import/UsersImportPage";
import { EquipmentImportPage } from "@/components/import/EquipmentImportPage";
import { ProductMasterImportPage } from "@/components/import/ProductMasterImportPage";
import { PageHead } from "@/components/ui/PageHead";
import { EmptyState } from "@/components/ui/Table";

/**
 * Generic CSV bulk-import route — `/import/users`, `/import/equipment`, `/import/product-master`, one
 * dedicated page per entity rather than a shared textarea/modal popup (own-page follow-up, 2026-10-07:
 * the admin needs to assign different role/site combinations across a 100+-row user import, which a
 * modal's cramped column-mapping step has no room for — see the "Assign values" step in
 * `CsvImportWizard`). Each entity renders its own component so React fully remounts (and re-runs the
 * matching permission guard) when navigating between import types, rather than one component
 * conditionally calling a different guard hook per entity.
 *
 * Adding a new importable entity means adding one case here plus one `*ImportPage` component — no change
 * to the shared wizard.
 */
export default function ImportEntityPage({ params }: { params: Promise<{ entity: string }> }) {
  const { entity } = use(params);

  switch (entity) {
    case "users":
      return <UsersImportPage />;
    case "equipment":
      return <EquipmentImportPage />;
    case "product-master":
      return <ProductMasterImportPage />;
    default:
      return (
        <div>
          <PageHead title="Bulk import" />
          <EmptyState icon="alert-triangle">
            &ldquo;{entity}&rdquo; isn&rsquo;t an importable type. <Link href="/home">Back to home</Link>
          </EmptyState>
        </div>
      );
  }
}
