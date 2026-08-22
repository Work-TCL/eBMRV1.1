"use client";

import { useState } from "react";
import { api, ApiError, newIdempotencyKey, pagedFetcher, type Material, type MutationReceipt } from "@/lib/api";
import { useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";

const fetchMaterials = pagedFetcher<Material>("/materials");

const columns: DataTableColumn<Material>[] = [
  {
    key: "code",
    header: "Code",
    sortable: true,
    render: (m) => <span className="font-semibold tabular">{m.code}</span>,
  },
  { key: "name", header: "Name", sortable: true },
  { key: "uom", header: "UOM", sortable: false },
  { key: "status", header: "Status", sortable: true },
];

export default function MaterialsPage() {
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [uom, setUom] = useState("kg");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const { sites } = useSites();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (sites.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      await api.post<MutationReceipt>("/materials", {
        idempotency_key: newIdempotencyKey(),
        site_id: sites[0].id,
        code,
        name,
        uom,
      });
      setCode("");
      setName("");
      setOpen(false);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create material");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHead
        title="Materials"
        subtitle="Raw material and component masters this site receives against."
        action={
          <Button variant="primary" onClick={() => setOpen(true)}>
            <Icon name="plus" /> New material
          </Button>
        }
      />

      <Card>
        <CardHeader title="Materials" />
        <DataTable
          columns={columns}
          fetchPage={fetchMaterials}
          rowKey={(m) => m.id}
          searchPlaceholder="Search by code or name…"
          emptyIcon="scale"
          emptyMessage="No materials yet — create one to get started."
          defaultSort={{ by: "created_at", dir: "desc" }}
          reloadToken={reloadToken}
        />
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="New material">
        <form onSubmit={onSubmit}>
          <Field label="Code" required>
            <Input value={code} onChange={(e) => setCode(e.target.value)} required autoFocus />
          </Field>
          <Field label="Name" required>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label="Unit of measure" required error={error}>
            <Input value={uom} onChange={(e) => setUom(e.target.value)} required />
          </Field>
          <div className="flex justify-between gap-3 mt-4">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={busy}>
              {busy ? "Creating…" : "Create material"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
