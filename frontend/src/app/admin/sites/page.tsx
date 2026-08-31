"use client";

import { useEffect, useState } from "react";
import { api, ApiError, newIdempotencyKey, type MutationReceipt, type Site } from "@/lib/api";
import { useRequireAdmin } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";

export default function SitesAdminPage() {
  const { isAdmin } = useRequireAdmin();

  const [siteList, setSiteList] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);
  const [reloadToken, setReloadToken] = useState(0);

  const [modalOpen, setModalOpen] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [editing, setEditing] = useState<Site | null>(null);
  const [editCode, setEditCode] = useState("");
  const [editName, setEditName] = useState("");
  const [editError, setEditError] = useState<string | null>(null);
  const [editBusy, setEditBusy] = useState(false);

  const [deleting, setDeleting] = useState<Site | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    api
      .get<Site[]>("/sites")
      .then(setSiteList)
      .finally(() => setLoading(false));
  }, [reloadToken]);

  if (!isAdmin) return null;

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post<MutationReceipt>("/sites", { idempotency_key: newIdempotencyKey(), code, name });
      setCode("");
      setName("");
      setModalOpen(false);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create site");
    } finally {
      setBusy(false);
    }
  }

  function openEdit(s: Site) {
    setEditing(s);
    setEditCode(s.code);
    setEditName(s.name);
    setEditError(null);
  }

  async function onSaveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setEditBusy(true);
    setEditError(null);
    try {
      await api.patch<MutationReceipt>(`/sites/${editing.id}`, {
        idempotency_key: newIdempotencyKey(),
        site_id: editing.id,
        code: editCode,
        name: editName,
      });
      setEditing(null);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : "Failed to update site");
    } finally {
      setEditBusy(false);
    }
  }

  async function onConfirmDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await api.del<MutationReceipt>(`/sites/${deleting.id}`, {
        idempotency_key: newIdempotencyKey(),
        site_id: deleting.id,
      });
      setDeleting(null);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Failed to delete site");
    } finally {
      setDeleteBusy(false);
    }
  }

  return (
    <div>
      <PageHead
        title="Sites"
        subtitle="Manufacturing facilities under this company."
        action={
          <Button variant="primary" onClick={() => setModalOpen(true)}>
            <Icon name="plus" /> New site
          </Button>
        }
      />

      <Card>
        <CardHeader title="Sites" />
        {loading ? null : siteList.length === 0 ? (
          <EmptyState icon="building">No sites yet.</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {siteList.map((s) => (
                <tr key={s.id}>
                  <td className="font-semibold tabular">{s.code}</td>
                  <td>{s.name}</td>
                  <td style={{ textAlign: "right" }}>
                    <div className="flex gap-2 justify-end">
                      <Button size="sm" variant="secondary" onClick={() => openEdit(s)}>
                        Edit
                      </Button>
                      <Button size="sm" variant="danger" onClick={() => setDeleting(s)}>
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New site">
        <form onSubmit={onCreate}>
          <Field label="Code" required>
            <Input value={code} onChange={(e) => setCode(e.target.value)} required autoFocus />
          </Field>
          <Field label="Name" required error={error}>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <div className="flex justify-between gap-3 mt-4">
            <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={busy}>
              {busy ? "Creating…" : "Create site"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal open={editing !== null} onClose={() => setEditing(null)} title="Edit site">
        <form onSubmit={onSaveEdit}>
          <Field label="Code" required>
            <Input value={editCode} onChange={(e) => setEditCode(e.target.value)} required />
          </Field>
          <Field label="Name" required error={editError}>
            <Input value={editName} onChange={(e) => setEditName(e.target.value)} required />
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
        title="Delete site?"
        message={
          deleting ? (
            <>
              Delete <strong>{deleting.name}</strong> ({deleting.code})? Blocked if any product, material,
              material lot, batch, or role assignment still references it.
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
