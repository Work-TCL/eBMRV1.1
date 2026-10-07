"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  canAuthorProduct,
  newIdempotencyKey,
  type BulkImportProductResult,
  type BulkImportProductRow,
  type BulkImportProductRowOutcome,
} from "@/lib/api";
import { useMe, useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Field } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { CsvImportWizard, type CsvFieldDef, type CsvImportRowOutcome } from "@/components/shared/CsvImportWizard";

// Matches MANUFACTURING_PROFILES in app/product-master/page.tsx — reused here for the hint only.
const MANUFACTURING_PROFILES = ["pharma", "device", "injectable_ddcp", "inhalation_ddcp", "drug_eluting_device"];

// Client gap-analysis Phase 8 (2026-10-05, upload+mapping follow-up 2026-10-06, own-page follow-up
// 2026-10-07): sample offered as a downloadable file.
const SAMPLE_CSV =
  "product_code,name,manufacturing_profile_code,product_family_code,combination_product_type,strength_value,strength_uom\n" +
  ",Metformin Tablet 500mg,pharma,,,500,mg\n" +
  ",Insulin Prefilled Syringe,injectable_ddcp,,prefilled_syringe,100,mL";

const FIELDS: CsvFieldDef[] = [
  { key: "product_code", label: "Product code" },
  { key: "name", label: "Name", required: true },
  { key: "manufacturing_profile_code", label: "Manufacturing profile code", required: true, hint: MANUFACTURING_PROFILES.join(", ") },
  {
    key: "product_family_code",
    label: "Product family code",
    ref: {
      kind: "product family",
      fetchOptions: async () =>
        (await api.get<{ family_code: string; name: string }[]>("/products/v1/families")).map((f) => ({
          value: f.family_code,
          label: f.name,
        })),
    },
  },
  { key: "combination_product_type", label: "Combination product type" },
  { key: "strength_value", label: "Strength value" },
  { key: "strength_uom", label: "Strength UOM" },
];

function toProductRow(r: Record<string, string>): BulkImportProductRow {
  return {
    product_code: r.product_code || undefined,
    name: r.name ?? "",
    manufacturing_profile_code: r.manufacturing_profile_code ?? "",
    product_family_code: r.product_family_code || undefined,
    combination_product_type: r.combination_product_type || undefined,
    strength_value: r.strength_value || undefined,
    strength_uom: r.strength_uom || undefined,
  };
}

export function ProductMasterImportPage() {
  const { me, loading } = useMe();
  const { sites } = useSites();
  const router = useRouter();
  const [siteId, setSiteId] = useState("");

  useEffect(() => {
    if (!loading && !canAuthorProduct(me)) router.replace("/product-master");
  }, [me, loading, router]);
  if (!loading && !canAuthorProduct(me)) return null;

  async function onPreview(rows: Record<string, string>[]): Promise<CsvImportRowOutcome[]> {
    const outcomes = await api.post<BulkImportProductRowOutcome[]>("/products/v1/drafts/bulk-import/preview", {
      rows: rows.map(toProductRow),
    });
    return outcomes.map((o) => ({ row_index: o.row_index, label: o.product_code ?? "", ok: o.ok, error: o.error }));
  }

  async function onCommit(rows: Record<string, string>[]) {
    if (!siteId) throw new Error("Select a site first");
    const result = await api.post<BulkImportProductResult>("/products/v1/drafts/bulk-import/commit", {
      idempotency_key: newIdempotencyKey(),
      site_id: siteId,
      rows: rows.map(toProductRow),
    });
    return { createdCount: result.created.length };
  }

  return (
    <div>
      <PageHead title="Bulk import products" subtitle="Upload a CSV, match its columns, then preview and commit." />
      <CsvImportWizard
        description="Product code may be left blank to auto-generate. Always creates version 1 of a brand-new product — Business ID is generated automatically. Nothing is created until you preview and then commit."
        extraFields={
          <Field label="Site" required>
            <Select value={siteId} onChange={(e) => setSiteId(e.target.value)} required>
              <option value="">Select a site…</option>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
          </Field>
        }
        fields={FIELDS}
        sampleCsvContent={SAMPLE_CSV}
        sampleFileName="products-import-sample.csv"
        rowLabel={(r) => r.product_code || r.name}
        onCancel={() => router.push("/product-master")}
        onDone={() => router.push("/product-master")}
        onPreview={onPreview}
        onCommit={onCommit}
      />
    </div>
  );
}
