"use client";

import { useRouter } from "next/navigation";
import {
  api,
  listAll,
  newIdempotencyKey,
  type BulkImportCommitResult,
  type BulkImportRowOutcome,
  type BulkImportUserRow,
  type Role,
  type Site,
} from "@/lib/api";
import { useRequireAdmin } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { CsvImportWizard, type CsvFieldDef, type CsvImportRowOutcome } from "@/components/shared/CsvImportWizard";

// Client gap-analysis Phase 1 (2026-10-05, upload+mapping follow-up 2026-10-06, own-page follow-up
// 2026-10-07): the first-time-onboarding sample the client asked for, offered as a downloadable file.
const SAMPLE_CSV =
  "full_name,email,role_name,site_code\nJane Operator,jane.operator@example.com,Operator,T1\nSam Supervisor,sam.supervisor@example.com,Supervisor,T1";

const FIELDS: CsvFieldDef[] = [
  { key: "full_name", label: "Full name", required: true },
  { key: "email", label: "Email", required: true },
  {
    key: "role_name",
    label: "Role name",
    required: true,
    hint: "Must match an existing role exactly, e.g. Operator.",
    ref: { kind: "role", fetchOptions: async () => (await listAll<Role>("/roles")).map((r) => ({ value: r.name, label: r.name })) },
  },
  {
    key: "site_code",
    label: "Site code",
    required: true,
    hint: "Must match an existing site code, e.g. T1.",
    // /sites returns a plain array, not the {items,total,...} paginated envelope listAll() expects.
    ref: { kind: "site", fetchOptions: async () => (await api.get<Site[]>("/sites")).map((s) => ({ value: s.code, label: `${s.name} (${s.code})` })) },
  },
];

function toUserRow(r: Record<string, string>): BulkImportUserRow {
  return { full_name: r.full_name ?? "", email: r.email ?? "", role_name: r.role_name ?? "", site_code: r.site_code ?? "" };
}

export function UsersImportPage() {
  useRequireAdmin();
  const router = useRouter();

  async function onPreview(rows: Record<string, string>[]): Promise<CsvImportRowOutcome[]> {
    const outcomes = await api.post<BulkImportRowOutcome[]>("/users/bulk-import/preview", { rows: rows.map(toUserRow) });
    return outcomes.map((o) => ({ row_index: o.row_index, label: o.email, ok: o.ok, error: o.error }));
  }

  async function onCommit(rows: Record<string, string>[]) {
    const result = await api.post<BulkImportCommitResult>("/users/bulk-import/commit", {
      idempotency_key: newIdempotencyKey(),
      rows: rows.map(toUserRow),
    });
    const emailNote =
      result.emails_sent < result.created_count
        ? `${result.emails_sent} of ${result.created_count} invite email(s) sent — the rest couldn't be emailed (no SMTP configured?); share their invite links out-of-band.`
        : `${result.emails_sent} invite email(s) sent.`;
    return { createdCount: result.created_count, summary: `Created ${result.created_count} user(s). ${emailNote}` };
  }

  return (
    <div>
      <PageHead title="Bulk import users" subtitle="Upload a CSV, match its columns, then preview and commit." />
      <CsvImportWizard
        description="Each invited user gets an email with a link to set their own password — nothing is created until you preview and then commit."
        fields={FIELDS}
        sampleCsvContent={SAMPLE_CSV}
        sampleFileName="users-import-sample.csv"
        rowLabel={(r) => (r.email ? `${r.full_name} <${r.email}>` : r.full_name)}
        onCancel={() => router.push("/admin/users")}
        onDone={() => router.push("/admin/users")}
        onPreview={onPreview}
        onCommit={onCommit}
      />
    </div>
  );
}
