"use client";

import { useState } from "react";
import { api, ApiError, newIdempotencyKey, pagedFetcher, type MutationReceipt, type Product } from "@/lib/api";
import { useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";

const fetchProducts = pagedFetcher<Product>("/products");

const columns: DataTableColumn<Product>[] = [
  {
    key: "code",
    header: "Code",
    sortable: true,
    render: (p) => <span className="font-semibold tabular">{p.code}</span>,
  },
  { key: "name", header: "Name", sortable: true },
  { key: "status", header: "Status", sortable: true },
];

export default function ProductsPage() {
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
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
      await api.post<MutationReceipt>("/products", {
        idempotency_key: newIdempotencyKey(),
        site_id: sites[0].id,
        code,
        name,
      });
      setCode("");
      setName("");
      setOpen(false);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create product");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHead
        title="Products"
        subtitle="Product masters this site manufactures against."
        action={
          <Button variant="primary" onClick={() => setOpen(true)}>
            <Icon name="plus" /> New product
          </Button>
        }
      />

      <Card>
        <CardHeader title="Products" />
        <DataTable
          columns={columns}
          fetchPage={fetchProducts}
          rowKey={(p) => p.id}
          searchPlaceholder="Search by code or name…"
          emptyIcon="package"
          emptyMessage="No products yet — create one to get started."
          defaultSort={{ by: "created_at", dir: "desc" }}
          reloadToken={reloadToken}
        />
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="New product">
        <form onSubmit={onSubmit}>
          <Field label="Code" required>
            <Input value={code} onChange={(e) => setCode(e.target.value)} required autoFocus />
          </Field>
          <Field label="Name" required error={error}>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <div className="flex justify-between gap-3 mt-4">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={busy}>
              {busy ? "Creating…" : "Create product"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
