"use client";

import { useEffect, useState } from "react";
import {
  api,
  ApiError,
  listAll,
  newIdempotencyKey,
  pagedFetcher,
  type MutationReceipt,
  type Role,
  type Site,
  type User,
} from "@/lib/api";
import { useRequireAdmin, useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";

const fetchUsers = pagedFetcher<User>("/users");

export default function UsersAdminPage() {
  const { isAdmin } = useRequireAdmin();
  const { sites } = useSites();

  const [reloadToken, setReloadToken] = useState(0);

  const [modalOpen, setModalOpen] = useState(false);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [editing, setEditing] = useState<User | null>(null);
  const [editEmail, setEditEmail] = useState("");
  const [editFullName, setEditFullName] = useState("");
  const [editError, setEditError] = useState<string | null>(null);
  const [editBusy, setEditBusy] = useState(false);

  const [statusBusyId, setStatusBusyId] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [allRoles, setAllRoles] = useState<Role[]>([]);
  const [assignUserId, setAssignUserId] = useState("");
  const [assignSiteId, setAssignSiteId] = useState("");
  const [assignRoleId, setAssignRoleId] = useState("");
  const [assignError, setAssignError] = useState<string | null>(null);
  const [assignOk, setAssignOk] = useState<string | null>(null);
  const [assignBusy, setAssignBusy] = useState(false);

  useEffect(() => {
    listAll<User>("/users").then(setAllUsers);
  }, [reloadToken]);
  useEffect(() => {
    listAll<Role>("/roles").then(setAllRoles);
  }, []);

  if (!isAdmin) return null;

  // Default to the first site once loaded, without setState-in-effect (react-hooks/set-state-in-effect).
  const selectedSiteId = assignSiteId || sites[0]?.id || "";

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post<MutationReceipt>("/users", {
        idempotency_key: newIdempotencyKey(),
        username,
        email,
        full_name: fullName,
        password,
      });
      setUsername("");
      setEmail("");
      setFullName("");
      setPassword("");
      setModalOpen(false);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create user");
    } finally {
      setBusy(false);
    }
  }

  function openEdit(u: User) {
    setEditing(u);
    setEditEmail(u.email);
    setEditFullName(u.full_name);
    setEditError(null);
  }

  async function onSaveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setEditBusy(true);
    setEditError(null);
    try {
      await api.patch<MutationReceipt>(`/users/${editing.id}`, {
        idempotency_key: newIdempotencyKey(),
        user_id: editing.id,
        email: editEmail,
        full_name: editFullName,
      });
      setEditing(null);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : "Failed to update user");
    } finally {
      setEditBusy(false);
    }
  }

  async function onToggleStatus(u: User) {
    setStatusBusyId(u.id);
    setStatusError(null);
    const action = u.status === "active" ? "deactivate" : "reactivate";
    try {
      await api.post<MutationReceipt>(`/users/${u.id}/${action}`, {
        idempotency_key: newIdempotencyKey(),
        user_id: u.id,
      });
      setReloadToken((n) => n + 1);
    } catch (err) {
      setStatusError(err instanceof ApiError ? err.message : `Failed to ${action} user`);
    } finally {
      setStatusBusyId(null);
    }
  }

  async function onAssignRole(e: React.FormEvent) {
    e.preventDefault();
    if (!assignUserId || !selectedSiteId || !assignRoleId) return;
    setAssignBusy(true);
    setAssignError(null);
    setAssignOk(null);
    try {
      await api.post<MutationReceipt>(`/users/${assignUserId}/roles`, {
        idempotency_key: newIdempotencyKey(),
        user_id: assignUserId,
        site_id: selectedSiteId,
        role_id: assignRoleId,
      });
      setAssignOk("Role assigned.");
      setReloadToken((n) => n + 1);
    } catch (err) {
      setAssignError(err instanceof ApiError ? err.message : "Failed to assign role");
    } finally {
      setAssignBusy(false);
    }
  }

  const columns: DataTableColumn<User>[] = [
    { key: "username", header: "Username", sortable: true, render: (u) => <span className="font-semibold">{u.username}</span> },
    { key: "full_name", header: "Full name", sortable: true },
    { key: "email", header: "Email", sortable: true },
    { key: "status", header: "Status", sortable: true },
    { key: "roles", header: "Roles", render: (u) => (u.roles.length ? u.roles.join(", ") : "—") },
    {
      key: "actions",
      header: "",
      render: (u) => (
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="secondary" onClick={() => openEdit(u)}>
            Edit
          </Button>
          <Button
            size="sm"
            variant={u.status === "active" ? "danger" : "success"}
            disabled={statusBusyId === u.id}
            onClick={() => onToggleStatus(u)}
          >
            {statusBusyId === u.id ? "Working…" : u.status === "active" ? "Deactivate" : "Reactivate"}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHead
        title="Users"
        subtitle="Create users and assign roles per site."
        action={
          <Button variant="primary" onClick={() => setModalOpen(true)}>
            <Icon name="plus" /> New user
          </Button>
        }
      />

      <Card className="mb-4">
        <CardHeader title="Users" />
        {statusError && <p className="error-text px-4 pt-3">{statusError}</p>}
        <DataTable
          columns={columns}
          fetchPage={fetchUsers}
          rowKey={(u) => u.id}
          searchPlaceholder="Search by username, email, or name…"
          emptyIcon="users"
          emptyMessage="No users yet."
          reloadToken={reloadToken}
        />
      </Card>

      <Card pad>
        <CardHeader title="Assign role" />
        <form onSubmit={onAssignRole}>
          <div className="grid grid-cols-3 gap-4">
            <Field label="User" required>
              <Select value={assignUserId} onChange={(e) => setAssignUserId(e.target.value)} required>
                <option value="">Select a user</option>
                {allUsers.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.username}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Site" required>
              <Select value={selectedSiteId} onChange={(e) => setAssignSiteId(e.target.value)} required>
                {sites.map((s: Site) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.code})
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Role" required>
              <Select value={assignRoleId} onChange={(e) => setAssignRoleId(e.target.value)} required>
                <option value="">Select a role</option>
                {allRoles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          {assignError && <p className="error-text mb-3">{assignError}</p>}
          {assignOk && <p className="mb-3">{assignOk}</p>}
          <Button type="submit" variant="primary" disabled={assignBusy}>
            {assignBusy ? "Assigning…" : "Assign role"}
          </Button>
        </form>
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New user">
        <form onSubmit={onCreate}>
          <Field label="Username" required>
            <Input value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
          </Field>
          <Field label="Email" required>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Field>
          <Field label="Full name" required>
            <Input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          </Field>
          <Field label="Password" required error={error}>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
          </Field>
          <div className="flex justify-between gap-3 mt-4">
            <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={busy}>
              {busy ? "Creating…" : "Create user"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal open={editing !== null} onClose={() => setEditing(null)} title="Edit user">
        <form onSubmit={onSaveEdit}>
          <Field label="Username" hint="Username cannot be changed once created.">
            <Input value={editing?.username ?? ""} disabled />
          </Field>
          <Field label="Email" required>
            <Input type="email" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} required />
          </Field>
          <Field label="Full name" required error={editError}>
            <Input value={editFullName} onChange={(e) => setEditFullName(e.target.value)} required />
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
    </div>
  );
}
