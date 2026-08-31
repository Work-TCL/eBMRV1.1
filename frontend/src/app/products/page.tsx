"use client";

import { useState } from "react";
import { api, ApiError, newIdempotencyKey, pagedFetcher, type MutationReceipt, type Product } from "@/lib/api";
import { useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";

const fetchProducts = pagedFetcher<Product>("/products");

export default function ProductsPage() {
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const { sites } = useSites();

  const [editing, setEditing] = useState<Product | null>(null);
  const [editName, setEditName] = useState("");
  const [editStatus, setEditStatus] = useState("active");
  const [editError, setEditError] = useState<string | null>(null);
  const [editBusy, setEditBusy] = useState(false);

  const [deleting, setDeleting] = useState<Product | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

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

  function openEdit(p: Product) {
    setEditing(p);
    setEditName(p.name);
    setEditStatus(p.status);
    setEditError(null);
  }

  async function onSaveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setEditBusy(true);
    setEditError(null);
    try {
      await api.patch<MutationReceipt>(`/products/${editing.id}`, {
        idempotency_key: newIdempotencyKey(),
        product_id: editing.id,
        name: editName,
        status: editStatus,
      });
      setEditing(null);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : "Failed to update product");
    } finally {
      setEditBusy(false);
    }
  }

  async function onConfirmDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await api.del<MutationReceipt>(`/products/${deleting.id}`, {
        idempotency_key: newIdempotencyKey(),
        product_id: deleting.id,
      });
      setDeleting(null);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Failed to delete product");
    } finally {
      setDeleteBusy(false);
    }
  }

  const columns: DataTableColumn<Product>[] = [
    {
      key: "code",
      header: "Code",
      sortable: true,
      render: (p) => <span className="font-semibold tabular">{p.code}</span>,
    },
    { key: "name", header: "Name", sortable: true },
    { key: "status", header: "Status", sortable: true },
    {
      key: "actions",
      header: "",
      render: (p) => (
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="secondary" onClick={() => openEdit(p)}>
            Edit
          </Button>
          <Button size="sm" variant="danger" onClick={() => setDeleting(p)}>
            Delete
          </Button>
        </div>
      ),
    },
  ];

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

      <Modal open={editing !== null} onClose={() => setEditing(null)} title="Edit product">
        <form onSubmit={onSaveEdit}>
          <Field label="Code" hint="Code cannot be changed once created.">
            <Input value={editing?.code ?? ""} disabled />
          </Field>
          <Field label="Name" required>
            <Input value={editName} onChange={(e) => setEditName(e.target.value)} required />
          </Field>
          <Field label="Status" required error={editError}>
            <Select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
              <option value="active">active</option>
              <option value="inactive">inactive</option>
            </Select>
          </Field>
          <div className="flex justify-between gap-3 mt-4">
            <Button type="button" variant="secondary" onClick={() => setEditing(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={editBusy}>
              {editBusy ? "Saving…" : "Save changes"}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        title="Delete product?"
        message={
          deleting ? (
            <>
              Delete <strong>{deleting.name}</strong> ({deleting.code})? This cannot be undone. Blocked if
              any recipe or batch still references it.
            </>
          ) : (
            ""
          )
        }
        onConfirm={onConfirmDelete}
        busy={deleteBusy}
        error={deleteError}
      />
    </div>
  );
}
