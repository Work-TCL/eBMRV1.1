"use client";

import { useEffect, useState } from "react";
import { api, ApiError, listAll, newIdempotencyKey, type MutationReceipt, type Permission, type Role } from "@/lib/api";
import { computeActivities } from "@/lib/roleActivities";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { StatePill } from "@/components/ui/StatePill";

/**
 * Template-first "New role" flow (client gap-analysis follow-up, 2026-10-06, project-owner-directed:
 * "template-first, still editable" -- raw permission editing stays available on the Advanced edit page,
 * this is just the easier front door). A "template" is simply any existing Role row -- on a fresh
 * deployment the only roles that exist are the ~27 seeded, fully-permissioned ones
 * (scripts/seed.py ROLE_PERMISSIONS, reconciled live by scripts/sync_permissions.py), so cloning "any
 * existing role" is a strict superset of "clone one of the 27 seeded ones", with no schema change and
 * no new backend endpoint -- clone = POST /roles (create) -> GET /roles/{source}/permissions (read) ->
 * POST /roles/{new}/permissions (apply), the same three endpoints admin/roles/[id]/page.tsx already
 * uses for a manual edit.
 */
export function RoleTemplateGallery({ onCreated, onCancel }: { onCreated: (roleId: string, sourceName: string) => void; onCancel: () => void }) {
  const [roles, setRoles] = useState<Role[]>([]);
  const [allPermissions, setAllPermissions] = useState<Permission[]>([]);
  const [sourceRoleId, setSourceRoleId] = useState("");
  // Tagged with the roleId it was fetched for, so switching the selection away and back never shows
  // stale permissions from a different role while cleanup from the previous effect run is still in
  // flight -- see `sourcePermissions` derivation below.
  const [fetchedPermissions, setFetchedPermissions] = useState<{ roleId: string; permissions: Permission[] } | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listAll<Role>("/roles").then(setRoles);
    api.get<Permission[]>("/permissions").then(setAllPermissions);
  }, []);

  useEffect(() => {
    if (!sourceRoleId) return;
    let cancelled = false;
    api
      .get<Permission[]>(`/roles/${sourceRoleId}/permissions`)
      .then((perms) => {
        if (!cancelled) setFetchedPermissions({ roleId: sourceRoleId, permissions: perms });
      });
    return () => {
      cancelled = true;
    };
  }, [sourceRoleId]);

  const sourceRole = roles.find((r) => r.id === sourceRoleId) ?? null;
  const sourcePermissions = fetchedPermissions && fetchedPermissions.roleId === sourceRoleId ? fetchedPermissions.permissions : null;
  // Derived rather than its own state -- true exactly while a role is selected but its permissions
  // haven't arrived (or don't match the current selection) yet.
  const permissionsLoading = sourceRoleId !== "" && sourcePermissions === null;
  const grantedIds = sourcePermissions ? new Set(sourcePermissions.map((p) => p.id)) : null;
  const activities = grantedIds ? computeActivities(allPermissions, grantedIds) : [];

  async function onConfirm(e: React.FormEvent) {
    e.preventDefault();
    if (!sourceRole || !sourcePermissions) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.post<MutationReceipt>("/roles", {
        idempotency_key: newIdempotencyKey(),
        name,
        description: description || null,
      });
      await api.post<MutationReceipt>(`/roles/${created.aggregate_id}/permissions`, {
        idempotency_key: newIdempotencyKey(),
        role_id: created.aggregate_id,
        permission_ids: sourcePermissions.map((p) => p.id),
      });
      onCreated(created.aggregate_id, sourceRole.name);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create role from template");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onConfirm}>
      <Field label="Start from" required hint="Any existing role can be used as a starting point, including the built-in ones.">
        <Select value={sourceRoleId} onChange={(e) => setSourceRoleId(e.target.value)} required>
          <option value="">Select a role to clone</option>
          {roles.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </Select>
      </Field>

      {sourceRoleId && (
        <div className="card mb-3" style={{ padding: "10px 14px" }}>
          {permissionsLoading ? (
            <p className="fs-2 text-muted">Loading what this role covers…</p>
          ) : activities.length > 0 ? (
            <>
              <p className="fs-2 text-muted mb-2">This role covers:</p>
              <div className="flex flex-wrap gap-2">
                {activities.map((a) => (
                  <StatePill key={a.key} state="accepted" icon="check">
                    {a.label}
                  </StatePill>
                ))}
              </div>
            </>
          ) : (
            <p className="fs-2 text-muted">This role has no permissions granted yet.</p>
          )}
        </div>
      )}

      <Field label="New role name" required>
        <Input value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
      </Field>
      <Field label="Description">
        <Input value={description} onChange={(e) => setDescription(e.target.value)} />
      </Field>

      {error && <p className="error-text mb-3">{error}</p>}

      <div className="flex justify-between gap-3 mt-4">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" disabled={busy || !sourceRoleId || permissionsLoading}>
          {busy ? "Creating…" : "Create role from template"}
        </Button>
      </div>
    </form>
  );
}
