"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, canCreateSupplier, newIdempotencyKey, pagedFetcher, type Supplier } from "@/lib/api";
import { useRequirePermission } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { CodeField } from "@/components/ui/CodeField";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";
import { RepeatableRows, type RepeatRow } from "@/components/shared/RepeatableFields";

export const ROLE_TYPES = ["supplier", "manufacturer", "both", "service_provider"];

export default function SuppliersPage() {
  const { me } = useRequirePermission("supplier.view");
  const router = useRouter();
  const [reloadToken, setReloadToken] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);

  const fetchSuppliers = pagedFetcher<Supplier>("/suppliers/v1");

  const columns: DataTableColumn<Supplier>[] = [
    {
      key: "supplier_code",
      header: "Code",
      sortable: true,
      render: (s) => <span className="font-semibold tabular">{s.supplier_code}</span>,
    },
    { key: "legal_name", header: "Legal name", sortable: true },
    {
      key: "role_type",
      header: "Role",
      render: (s) => <span className="fs-2">{s.role_type.replace(/_/g, " ")}</span>,
    },
    { key: "country", header: "Country", render: (s) => <span className="fs-2">{s.country ?? "—"}</span> },
    { key: "status", header: "Status", sortable: true, render: (s) => <WorkflowStatePill state={s.status} /> },
  ];

  return (
    <div>
      <PageHead
        title="Suppliers"
        subtitle="The supplier register, its sites, and their qualification status."
        action={
          canCreateSupplier(me) ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> New supplier
            </Button>
          ) : undefined
        }
      />

      <Card>
        <CardHeader title="Supplier register" />
        <DataTable
          columns={columns}
          fetchPage={fetchSuppliers}
          rowKey={(s) => s.id}
          searchPlaceholder="Search by code or legal name…"
          emptyIcon="building"
          emptyMessage="No suppliers registered yet."
          defaultSort={{ by: "created_at", dir: "desc" }}
          reloadToken={reloadToken}
          onRowClick={(s) => router.push(`/suppliers/${s.id}`)}
        />
      </Card>

      {createOpen && (
        <CreateSupplierModal
          onClose={() => setCreateOpen(false)}
          onDone={() => {
            setCreateOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
    </div>
  );
}

const SITE_SUB_FIELDS = [
  { name: "site_name", label: "Site name", required: true },
  { name: "city", label: "City" },
  { name: "country", label: "Country" },
  { name: "manufacturer_flag", label: "Manufactures here", type: "bool" as const },
];

function CreateSupplierModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { busy, error, run } = useCommand(onDone);
  const [supplierCode, setSupplierCode] = useState("");
  const [legalName, setLegalName] = useState("");
  const [roleType, setRoleType] = useState(ROLE_TYPES[0]);
  const [country, setCountry] = useState("");
  // Client follow-up (2026-10-06, project-owner-directed): the create form previously only let you type
  // one site inline; the backend's own CreateSupplierCommand already accepted a full `sites` array, so
  // this is a frontend-only change -- same RepeatableRows pattern used for other repeatable sub-forms.
  const [sites, setSites] = useState<RepeatRow[]>([]);

  return (
    <Modal open onClose={onClose} title="Register a supplier" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post("/suppliers/v1", {
              idempotency_key: newIdempotencyKey(),
              supplier_code: supplierCode || undefined,
              legal_name: legalName,
              role_type: roleType,
              country: country || null,
              sites: sites
                .filter((s) => s.site_name?.trim())
                .map((s) => ({
                  site_name: s.site_name,
                  city: s.city || null,
                  country: s.country || null,
                  manufacturer_flag: s.manufacturer_flag === "true",
                })),
            })
          );
        }}
      >
        <div className="grid grid-cols-3 gap-4">
          <CodeField label="Supplier code" value={supplierCode} onChange={setSupplierCode} />
          <Field label="Role type" required>
            <Select value={roleType} onChange={(e) => setRoleType(e.target.value)}>
              {ROLE_TYPES.map((r) => (
                <option key={r} value={r}>
                  {r
                    .replace(/_/g, " ")
                    .replace(/^./, (char) => char.toUpperCase())}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Country">
            <Input value={country} onChange={(e) => setCountry(e.target.value)} />
          </Field>
        </div>
        <Field label="Legal name" required>
          <Input value={legalName} onChange={(e) => setLegalName(e.target.value)} required />
        </Field>
        <RepeatableRows
          label="Sites (Optional)"
          hint="Add as many sites as this supplier has — more can always be added later from the supplier's own page too."
          itemLabel="site"
          subFields={SITE_SUB_FIELDS}
          value={sites}
          onChange={setSites}
        />
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !legalName.trim()}>
            {busy ? "Registering…" : "Register supplier"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

