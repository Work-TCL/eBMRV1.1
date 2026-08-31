"use client";

import { useState } from "react";
import { api, ApiError, newIdempotencyKey, pagedFetcher, type Material, type MutationReceipt } from "@/lib/api";
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

const fetchMaterials = pagedFetcher<Material>("/materials");

export default function MaterialsPage() {
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [uom, setUom] = useState("kg");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const { sites } = useSites();

  const [editing, setEditing] = useState<Material | null>(null);
  const [editName, setEditName] = useState("");
  const [editStatus, setEditStatus] = useState("active");
  const [editError, setEditError] = useState<string | null>(null);
  const [editBusy, setEditBusy] = useState(false);

  const [deleting, setDeleting] = useState<Material | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

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

  function openEdit(m: Material) {
    setEditing(m);
    setEditName(m.name);
    setEditStatus(m.status);
    setEditError(null);
  }

  async function onSaveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setEditBusy(true);
    setEditError(null);
    try {
      await api.patch<MutationReceipt>(`/materials/${editing.id}`, {
        idempotency_key: newIdempotencyKey(),
        material_id: editing.id,
        name: editName,
        status: editStatus,
      });
      setEditing(null);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : "Failed to update material");
    } finally {
      setEditBusy(false);
    }
  }

  async function onConfirmDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await api.del<MutationReceipt>(`/materials/${deleting.id}`, {
        idempotency_key: newIdempotencyKey(),
        material_id: deleting.id,
      });
      setDeleting(null);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Failed to delete material");
    } finally {
      setDeleteBusy(false);
    }
  }

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
    {
      key: "actions",
      header: "",
      render: (m) => (
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="secondary" onClick={() => openEdit(m)}>
            Edit
          </Button>
          <Button size="sm" variant="danger" onClick={() => setDeleting(m)}>
            Delete
          </Button>
        </div>
      ),
    },
  ];

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

      <Modal open={editing !== null} onClose={() => setEditing(null)} title="Edit material">
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
        title="Delete material?"
        message={
          deleting ? (
            <>
              Delete <strong>{deleting.name}</strong> ({deleting.code})? This cannot be undone. Blocked if
              any material lot still references it.
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
