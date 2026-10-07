"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  ApiError,
  newIdempotencyKey,
  pagedFetcher,
  type MutationReceipt,
  type Role,
} from "@/lib/api";
import { useRequireAdmin } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button, LinkButton } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { RoleTemplateGallery } from "@/components/admin/RoleTemplateGallery";
import { OnboardingReturnLink } from "@/components/admin/OnboardingReturnLink";

const fetchRoles = pagedFetcher<Role>("/roles");

export default function RolesAdminPage() {
  const { isAdmin } = useRequireAdmin();
  const router = useRouter();

  const [reloadToken, setReloadToken] = useState(0);

  const [modalOpen, setModalOpen] = useState(false);
  const [createMode, setCreateMode] = useState<"template" | "blank">("template");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [deleting, setDeleting] = useState<Role | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  if (!isAdmin) return null;

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post<MutationReceipt>("/roles", {
        idempotency_key: newIdempotencyKey(),
        name,
        description: description || null,
      });
      setName("");
      setDescription("");
      setModalOpen(false);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create role");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirmDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await api.del<MutationReceipt>(`/roles/${deleting.id}`, {
        idempotency_key: newIdempotencyKey(),
        role_id: deleting.id,
      });
      setDeleting(null);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Failed to delete role");
    } finally {
      setDeleteBusy(false);
    }
  }

  const columns: DataTableColumn<Role>[] = [
    { key: "name", header: "Name", sortable: true, render: (r) => <span className="font-semibold">{r.name}</span> },
    { key: "description", header: "Description", render: (r) => r.description ?? "—" },
    {
      key: "actions",
      header: "",
      render: (r) => (
        <div className="flex gap-2 justify-end">
          <LinkButton href={`/admin/roles/${r.id}`} size="sm" variant="secondary">
            Edit
          </LinkButton>
          <Button size="sm" variant="danger" onClick={() => setDeleting(r)}>
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHead
        title="Roles"
        subtitle="Roles assignable to users per site. Assign a role to a user from the Users page."
        action={
          <div className="flex gap-2">
            <OnboardingReturnLink />
            <Button
              variant="primary"
              onClick={() => {
                setCreateMode("template");
                setModalOpen(true);
              }}
            >
              <Icon name="plus" /> New role
            </Button>
          </div>
        }
      />

      <Card>
        <CardHeader title="Roles" />
        <DataTable
          columns={columns}
          fetchPage={fetchRoles}
          rowKey={(r) => r.id}
          searchPlaceholder="Search by name…"
          emptyIcon="users"
          emptyMessage="No roles yet."
          reloadToken={reloadToken}
        />
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New role">
        {createMode === "template" ? (
          <>
            <RoleTemplateGallery
              onCreated={(roleId, sourceName) => {
                setModalOpen(false);
                router.push(`/admin/roles/${roleId}?cloned_from=${encodeURIComponent(sourceName)}`);
              }}
              onCancel={() => setModalOpen(false)}
            />
            <p className="fs-2 text-muted mt-3">
              Need a role with no permissions at all?{" "}
              <button type="button" className="link-button" style={{ background: "none", border: "none", padding: 0, color: "var(--brand-600)", textDecoration: "underline", cursor: "pointer" }} onClick={() => setCreateMode("blank")}>
                Start blank instead
              </button>
            </p>
          </>
        ) : (
          <form onSubmit={onCreate}>
            <Field label="Name" required error={error}>
              <Input value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
            </Field>
            <Field label="Description">
              <Input value={description} onChange={(e) => setDescription(e.target.value)} />
            </Field>
            <div className="flex justify-between gap-3 mt-4">
              <Button type="button" variant="secondary" onClick={() => setCreateMode("template")}>
                ← Start from a template instead
              </Button>
              <Button type="submit" variant="primary" disabled={busy}>
                {busy ? "Creating…" : "Create blank role"}
              </Button>
            </div>
          </form>
        )}
      </Modal>

      <ConfirmDialog
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        title="Delete role?"
        message={
          deleting ? (
            <>
              Delete <strong>{deleting.name}</strong>? Blocked if any user still holds this role, or
              it&apos;s referenced by a SoD rule or signature policy.
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
