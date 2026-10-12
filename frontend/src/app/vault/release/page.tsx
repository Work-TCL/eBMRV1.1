"use client";

import { useRequirePermission } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { LinkButton } from "@/components/ui/Button";
import { SignedJsonForm } from "@/components/shared/SignedJsonForm";

/** Full-page "Release a master record to the vault" (moved off the `/vault` list page so that page
 * stays a pure lookup/correction surface — same rationale as recipe-master's own `new/page.tsx` split).
 * This is the generic release path (Document 06 section 9 row 2): domain modules that already run their
 * own release ceremony (batch release, material lot disposition, product/recipe release, ...) call
 * `vault_service.release_master` directly inside their own transaction and never reach this endpoint —
 * use it only for a record type with no dedicated release flow of its own. */
export default function VaultReleasePage() {
  const { me } = useRequirePermission("vault.correct", "/vault");

  return (
    <div>
      <PageHead
        title="Release a master record to the vault"
        subtitle="The generic release path - domain modules that already run their own release ceremony (batch release, material lot disposition) never reach this; use it only for a record type with no dedicated release flow of its own."
        action={<LinkButton href="/vault">Back to Vault</LinkButton>}
      />

      <SignedJsonForm
        title="Release a master record - signed"
        root="/vault/v1"
        me={me}
        ops={[
          {
            postPath: "masters/{object_type}/{business_id}/release",
            challengePath: "masters/{object_type}/{business_id}/signature-challenges",
            action: "release",
            label: "Release a master record",
            requiredPermission: "vault.correct",
            mirrorBodyInChallenge: true,
            fields: [
              {
                name: "object_type",
                label: "Object type",
                required: true,
                hint: "Only for a record type with no dedicated release flow of its own (every type already listed on the Vault lookup page has one, and never reaches this generic endpoint) — so this is intentionally free text, not a closed list.",
              },
              { name: "business_id", label: "Business ID", required: true, hint: "The identifier this record is known by (new record — not picked from an existing list)." },
              { name: "canonical_payload", label: "Canonical payload", type: "kv", required: true, hint: "The exact record content being released, as key/value pairs." },
              { name: "business_version_label", label: "Business version label", hint: "Optional." },
              {
                name: "evidence", label: "Evidence", type: "repeat", itemLabel: "Evidence item",
                subFields: [
                  { name: "evidence_id", label: "Evidence object ID", required: true },
                  { name: "evidence_sha256", label: "SHA-256", required: true },
                  { name: "media_type", label: "Media type" },
                  { name: "sequence", label: "Sequence", type: "number" },
                ],
              },
            ],
          },
        ]}
      />
    </div>
  );
}
