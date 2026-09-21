"use client";

import { useState } from "react";
import { api, ApiError, newIdempotencyKey, pagedFetcher, STORAGE_CONDITIONS, type Material, type MutationReceipt } from "@/lib/api";
import { useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { CodeField } from "@/components/ui/CodeField";
import { UomSelect } from "@/components/ui/UomSelect";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";

const fetchMaterials = pagedFetcher<Material>("/materials");

export default function MaterialsPage() {
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [uom, setUom] = useState("kg");
  const [isInHouse, setIsInHouse] = useState(false);
  const [defaultStorageCondition, setDefaultStorageCondition] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const { sites } = useSites();

  const [editing, setEditing] = useState<Material | null>(null);
  const [editName, setEditName] = useState("");
  const [editStatus, setEditStatus] = useState("active");
  const [editIsInHouse, setEditIsInHouse] = useState(false);
  const [editDefaultStorageCondition, setEditDefaultStorageCondition] = useState("");
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
        code: code || undefined,
        name,
        uom,
        is_in_house: isInHouse,
        default_storage_condition: defaultStorageCondition || null,
      });
      setCode("");
      setName("");
      setIsInHouse(false);
      setDefaultStorageCondition("");
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
    setEditIsInHouse(m.is_in_house);
    setEditDefaultStorageCondition(m.default_storage_condition ?? "");
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
        is_in_house: editIsInHouse,
        default_storage_condition: editDefaultStorageCondition || null,
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
      key: "storage",
      header: "Storage",
      sortable: false,
      render: (m) => (
        <span className="fs-2 text-muted">
          {m.is_in_house ? "In-house" : "Purchased"}
          {m.default_storage_condition ? ` · ${m.default_storage_condition}` : ""}
        </span>
      ),
    },
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
          emptyMessage="No materials yet - create one to get started."
          defaultSort={{ by: "created_at", dir: "desc" }}
          reloadToken={reloadToken}
        />
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="New material">
        <form onSubmit={onSubmit}>
          <CodeField label="Code" value={code} onChange={setCode} required />
          <Field label="Name" required>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <UomSelect value={uom} onChange={setUom} required />
          <div className="grid grid-cols-2 gap-4">
            <Field label="Default storage condition" hint="Optional.">
              <Select value={defaultStorageCondition} onChange={(e) => setDefaultStorageCondition(e.target.value)}>
                <option value="">—</option>
                {STORAGE_CONDITIONS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </Select>
            </Field>
            <label className="flex items-center gap-2 fs-2" style={{ marginTop: "var(--space-5)" }}>
              <input type="checkbox" checked={isInHouse} onChange={(e) => setIsInHouse(e.target.checked)} />
              Manufactured/maintained in-house
            </label>
          </div>
          {error && <p className="error-text mb-2">{error}</p>}
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
          <div className="grid grid-cols-2 gap-4">
            <Field label="Default storage condition" hint="Optional.">
              <Select value={editDefaultStorageCondition} onChange={(e) => setEditDefaultStorageCondition(e.target.value)}>
                <option value="">—</option>
                {STORAGE_CONDITIONS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </Select>
            </Field>
            <label className="flex items-center gap-2 fs-2" style={{ marginTop: "var(--space-5)" }}>
              <input type="checkbox" checked={editIsInHouse} onChange={(e) => setEditIsInHouse(e.target.checked)} />
              Manufactured/maintained in-house
            </label>
          </div>
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
