"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  newIdempotencyKey,
  type BulkImportEquipmentResult,
  type BulkImportEquipmentRow,
  type BulkImportEquipmentRowOutcome,
} from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { canCreateEquipment } from "@/lib/api";
import { PageHead } from "@/components/ui/PageHead";
import { Banner } from "@/components/ui/Banner";
import { CsvImportWizard, type CsvFieldDef, type CsvImportRowOutcome } from "@/components/shared/CsvImportWizard";

// Client gap-analysis Phase 7 (2026-10-05, upload+mapping follow-up 2026-10-06, own-page follow-up
// 2026-10-07): sample offered as a downloadable file.
const SAMPLE_CSV =
  "equipment_code,equipment_class_code,manufacturer,model,serial_no,firmware_version,dedicated,is_computer_operated\n" +
  ",BALANCE,Mettler Toledo,XPE205,SN-00123,,false,false\n" +
  ",AUTOCLAVE,Getinge,GEV-67,SN-00456,v2.1,true,true";

const FIELDS: CsvFieldDef[] = [
  { key: "equipment_code", label: "Equipment code" },
  {
    key: "equipment_class_code",
    label: "Equipment class code",
    required: true,
    hint: "e.g. BALANCE, AUTOCLAVE — must match an existing equipment class.",
    ref: {
      kind: "equipment class",
      fetchOptions: async () =>
        (await api.get<{ class_code: string; name: string }[]>("/equipment/v1/equipment-classes")).map((c) => ({
          value: c.class_code,
          label: `${c.name} (${c.class_code})`,
        })),
    },
  },
  { key: "manufacturer", label: "Manufacturer" },
  { key: "model", label: "Model" },
  { key: "serial_no", label: "Serial no." },
  { key: "firmware_version", label: "Firmware version" },
  { key: "dedicated", label: "Dedicated", hint: "true or false." },
  { key: "is_computer_operated", label: "Computer-operated", required: true, hint: "true or false." },
];

function toEquipmentRow(r: Record<string, string>): BulkImportEquipmentRow {
  return {
    equipment_code: r.equipment_code || undefined,
    equipment_class_code: r.equipment_class_code ?? "",
    manufacturer: r.manufacturer || undefined,
    model: r.model || undefined,
    serial_no: r.serial_no || undefined,
    firmware_version: r.firmware_version || undefined,
    dedicated: r.dedicated?.toLowerCase() === "true",
    is_computer_operated: r.is_computer_operated?.toLowerCase() === "true",
  };
}

export function EquipmentImportPage() {
  const { me, loading } = useMe();
  const { siteId } = useSiteId();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !canCreateEquipment(me)) router.replace("/equipment");
  }, [me, loading, router]);

  if (!loading && !canCreateEquipment(me)) return null;

  async function onPreview(rows: Record<string, string>[]): Promise<CsvImportRowOutcome[]> {
    const outcomes = await api.post<BulkImportEquipmentRowOutcome[]>("/equipment/v1/assets/bulk-import/preview", {
      rows: rows.map(toEquipmentRow),
    });
    return outcomes.map((o) => ({ row_index: o.row_index, label: o.equipment_code ?? "", ok: o.ok, error: o.error }));
  }

  async function onCommit(rows: Record<string, string>[]) {
    if (!siteId) throw new Error("Select a site first");
    const result = await api.post<BulkImportEquipmentResult>("/equipment/v1/assets/bulk-import/commit", {
      idempotency_key: newIdempotencyKey(),
      site_id: siteId,
      rows: rows.map(toEquipmentRow),
    });
    return { createdCount: result.created.length };
  }

  return (
    <div>
      <PageHead title="Bulk import equipment" subtitle="Upload a CSV, match its columns, then preview and commit." />
      {!siteId && <Banner tone="warn">No site resolved for your account yet — commit will be blocked until one is.</Banner>}
      <CsvImportWizard
        description="Equipment code may be left blank to auto-generate. Created under your currently selected site. Nothing is created until you preview and then commit."
        fields={FIELDS}
        sampleCsvContent={SAMPLE_CSV}
        sampleFileName="equipment-import-sample.csv"
        rowLabel={(r) => r.equipment_code || r.model || r.serial_no}
        onCancel={() => router.push("/equipment")}
        onDone={() => router.push("/equipment")}
        onPreview={onPreview}
        onCommit={onCommit}
      />
    </div>
  );
}
