"use client";

import { use, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  ApiError,
  newIdempotencyKey,
  type MutationReceipt,
  type Permission,
  type Role,
} from "@/lib/api";
import { useRequireAdmin } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button, LinkButton } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Banner } from "@/components/ui/Banner";
import { Icon } from "@/components/ui/Icon";

// Codes are "<module>.<resource>.<action>" (e.g. "ai_governance.evaluation.run"). There's no separate
// module column in the schema, so the module is parsed from the code prefix -- these short tokens read
// as acronyms, everything else as ordinary words.
const MODULE_ACRONYMS = new Set([
  "ai", "api", "capa", "ddcp", "dr", "em", "erp", "iq", "lims", "ncr", "oos", "oot", "oq", "pq", "qa", "qc", "scar",
]);

function permissionModuleKey(code: string): string {
  const idx = code.indexOf(".");
  return idx === -1 ? code : code.slice(0, idx);
}

function permissionModuleLabel(key: string): string {
  return key
    .split("_")
    .map((word) => (MODULE_ACRONYMS.has(word) ? word.toUpperCase() : word.charAt(0).toUpperCase() + word.slice(1)))
    .join(" ");
}

// Seed descriptions end with a regulatory citation, e.g. "(Document 105, AI-FR-022/024)" or
// "(SG-057, architecture rule C-014)" -- useful for traceability, but noise in an admin grid. Strip only
// parenthetical groups that actually cite a document/requirement/SG number; keep clarifying asides like
// "(create or re-evaluate)" or "(give back)".
function cleanPermissionDescription(description: string | null): string | null {
  if (!description) return description;
  const cleaned = description
    .replace(/\s*\([^()]*\b(?:Documents?\s*\d|SG-\d|[A-Z]{2,6}-FR-\d)[^()]*\)/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
  return cleaned || null;
}

type ModuleSelectState = "all" | "some" | "none";

function GroupCheckboxInput({ state, onChange }: { state: ModuleSelectState; onChange: () => void }) {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = state === "some";
  }, [state]);
  return <input ref={ref} type="checkbox" checked={state === "all"} onChange={onChange} />;
}

export default function RolePermissionsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { isAdmin } = useRequireAdmin();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [allPermissions, setAllPermissions] = useState<Permission[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState("");

  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveBusy, setSaveBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.get<Role>(`/roles/${id}`),
      api.get<Permission[]>("/permissions"),
      api.get<Permission[]>(`/roles/${id}/permissions`),
    ])
      .then(([r, permissions, granted]) => {
        if (cancelled) return;
        setRole(r);
        setName(r.name);
        setDescription(r.description ?? "");
        setAllPermissions(permissions);
        const grantedIds = new Set(granted.map((p) => p.id));
        setSelectedIds(grantedIds);
        setExpanded(
          new Set(permissions.filter((p) => grantedIds.has(p.id)).map((p) => permissionModuleKey(p.code)))
        );
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(err instanceof ApiError ? err.message : "Failed to load role");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const groups = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    const byModule = new Map<string, Permission[]>();
    for (const p of allPermissions) {
      if (needle) {
        const haystack = `${p.code} ${cleanPermissionDescription(p.description) ?? ""}`.toLowerCase();
        if (!haystack.includes(needle)) continue;
      }
      const key = permissionModuleKey(p.code);
      const list = byModule.get(key);
      if (list) list.push(p);
      else byModule.set(key, [p]);
    }
    return Array.from(byModule.entries())
      .map(([key, permissions]) => ({
        key,
        label: permissionModuleLabel(key),
        permissions: permissions.sort((a, b) => a.code.localeCompare(b.code)),
      }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [allPermissions, filter]);

  function togglePermission(permissionId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(permissionId)) next.delete(permissionId);
      else next.add(permissionId);
      return next;
    });
  }

  function toggleModule(permissions: Permission[]) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      const allSelected = permissions.every((p) => next.has(p.id));
      for (const p of permissions) {
        if (allSelected) next.delete(p.id);
        else next.add(p.id);
      }
      return next;
    });
  }

  function toggleExpanded(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function expandAll() {
    setExpanded(new Set(groups.map((g) => g.key)));
  }

  function collapseAll() {
    setExpanded(new Set());
  }

  function moduleState(permissions: Permission[]): ModuleSelectState {
    const selectedCount = permissions.filter((p) => selectedIds.has(p.id)).length;
    if (selectedCount === 0) return "none";
    if (selectedCount === permissions.length) return "all";
    return "some";
  }

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (!role) return;
    setSaveBusy(true);
    setSaveError(null);
    try {
      await api.patch<MutationReceipt>(`/roles/${role.id}`, {
        idempotency_key: newIdempotencyKey(),
        role_id: role.id,
        name,
        description: description || null,
      });
      await api.post<MutationReceipt>(`/roles/${role.id}/permissions`, {
        idempotency_key: newIdempotencyKey(),
        role_id: role.id,
        permission_ids: Array.from(selectedIds),
      });
      router.push("/admin/roles");
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Failed to update role");
    } finally {
      setSaveBusy(false);
    }
  }

  if (!isAdmin) return null;

  return (
    <div>
      <PageHead
        title={role ? `Edit role: ${role.name}` : "Edit role"}
        subtitle="What this role's users are allowed to do, grouped by module."
        action={
          <LinkButton href="/admin/roles" variant="secondary">
            <Icon name="arrow-left" /> Back to roles
          </LinkButton>
        }
      />

      {loadError && (
        <Banner tone="critical" title="Couldn't load this role">
          {loadError}
        </Banner>
      )}

      {loading && !loadError && <p className="text-muted">Loading…</p>}

      {role && (
        <form onSubmit={onSave}>
          <Card pad className="mb-4">
            <CardHeader title="Role details" />
            <Field label="Name" required>
              <Input value={name} onChange={(e) => setName(e.target.value)} required />
            </Field>
            <Field label="Description">
              <Input value={description} onChange={(e) => setDescription(e.target.value)} />
            </Field>
          </Card>

          <Card pad>
            <CardHeader title="Permissions" meta={`${selectedIds.size} of ${allPermissions.length} selected`} />

            <div className="flex items-end gap-3">
              <div style={{ flex: 1 }}>
                <Field label="Search permissions">
                  <Input
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    placeholder="Filter by name or description…"
                  />
                </Field>
              </div>
              <div className="flex gap-2 mb-4">
                <Button type="button" variant="secondary" size="sm" onClick={expandAll}>
                  Expand all
                </Button>
                <Button type="button" variant="secondary" size="sm" onClick={collapseAll}>
                  Collapse all
                </Button>
              </div>
            </div>

            {saveError && (
              <Banner tone="critical" title="Couldn't save">
                {saveError}
              </Banner>
            )}

            <div className="flex flex-col gap-2 mt-2">
              {groups.map(({ key, label, permissions }) => {
                const state = moduleState(permissions);
                const selectedCount = permissions.filter((p) => selectedIds.has(p.id)).length;
                // While searching, force-open every matching module so results are visible.
                const isOpen = filter.trim().length > 0 || expanded.has(key);
                return (
                  <div key={key} className="card">
                    <div
                      className="flex items-center justify-between gap-3"
                      style={{ padding: "10px 14px", cursor: "pointer" }}
                      onClick={() => toggleExpanded(key)}
                    >
                      <label className="checkbox-row fs-3" onClick={(e) => e.stopPropagation()}>
                        <GroupCheckboxInput state={state} onChange={() => toggleModule(permissions)} />
                        <span className="font-semibold">{label}</span>
                      </label>
                      <span className="flex items-center gap-2 fs-2 text-muted">
                        {selectedCount} / {permissions.length}
                        <Icon name={isOpen ? "chevron-down" : "chevron-right"} />
                      </span>
                    </div>
                    {isOpen && (
                      <div className="flex flex-col gap-2" style={{ padding: "0 14px 14px" }}>
                        {permissions.map((p) => (
                          <label key={p.id} className="checkbox-row fs-3">
                            <input
                              type="checkbox"
                              checked={selectedIds.has(p.id)}
                              onChange={() => togglePermission(p.id)}
                            />
                            <span>
                              <span className="font-semibold">{p.code}</span>
                              {cleanPermissionDescription(p.description) && (
                                <span className="text-muted"> — {cleanPermissionDescription(p.description)}</span>
                              )}
                            </span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
              {groups.length === 0 && <p className="text-muted">No permissions match “{filter}”.</p>}
            </div>

            <div className="flex justify-between gap-3 mt-4">
              <LinkButton href="/admin/roles" variant="secondary">
                Cancel
              </LinkButton>
              <Button type="submit" variant="primary" disabled={saveBusy}>
                {saveBusy ? "Saving…" : "Save changes"}
              </Button>
            </div>
          </Card>
        </form>
      )}
    </div>
  );
}
