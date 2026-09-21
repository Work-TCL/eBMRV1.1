"use client";

import { useState } from "react";
import { api, ApiError, pagedFetcher, type User } from "@/lib/api";
import { useRequireAdmin, useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { StatePill } from "@/components/ui/StatePill";
import { Field, RowButtonSlot } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

const fetchUsers = pagedFetcher<User>("/users");

interface PolicyDecision {
  decision: "ALLOW" | "DENY";
  action: string;
  reason: string | null;
  message?: string;
  held_roles: string[];
}

const USER_STATE: Record<string, "accepted" | "na" | "failed"> = {
  active: "accepted",
  deactivated: "na",
  locked: "failed",
};

const columns: DataTableColumn<User>[] = [
  { key: "username", header: "Username", sortable: true, render: (u) => <span className="font-semibold">{u.username}</span> },
  { key: "full_name", header: "Name", sortable: true, render: (u) => u.full_name || <span className="text-muted">—</span> },
  {
    key: "status",
    header: "Status",
    render: (u) => (
      <StatePill state={USER_STATE[u.status] ?? "unknown"} icon={u.status === "active" ? "check-circle" : "slash-circle"}>
        {u.status}
      </StatePill>
    ),
  },
  {
    key: "roles",
    header: "Roles @ site",
    render: (u) =>
      u.roles.length ? (
        <span className="flex flex-wrap gap-1">
          {u.roles.map((r) => (
            <span key={r} className="state" data-state="na">
              {r}
            </span>
          ))}
        </span>
      ) : (
        <span className="text-muted">No roles assigned</span>
      ),
  },
];

export default function AccessReviewPage() {
  const { isAdmin } = useRequireAdmin();
  const { sites } = useSites();

  const [action, setAction] = useState("batch.release");
  const [siteId, setSiteId] = useState("");
  const [decision, setDecision] = useState<PolicyDecision | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function runDecision(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setDecision(null);
    try {
      const result = await api.post<PolicyDecision>("/policy/v1/decisions", {
        action: action.trim(),
        site_id: siteId || null,
      });
      setDecision(result);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Decision query failed");
    } finally {
      setBusy(false);
    }
  }

  if (!isAdmin) return null;

  return (
    <div>
      <PageHead
        title="Access review"
        subtitle="Who holds which role at which site, and a live authorization-decision check."
      />

      <Card className="mb-4">
        <CardHeader title="Role assignment matrix" />
        <DataTable
          columns={columns}
          fetchPage={fetchUsers}
          rowKey={(u) => u.id}
          searchPlaceholder="Search by username, name, or email…"
          emptyIcon="users"
          emptyMessage="No users match."
          defaultSort={{ by: "username", dir: "asc" }}
        />
      </Card>

      <Card pad>
        <CardHeader title="Authorization decision check" />
        <p className="fs-2 text-muted mb-3">
          Evaluates whether <strong>you</strong> are currently authorized for an action at a site - the same
          policy the mutation gateway enforces. Read-only; nothing is written.
        </p>
        <form onSubmit={runDecision} className="flex items-start gap-4" style={{ flexWrap: "wrap" }}>
          <Field label="Action" required>
            <Input
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder="e.g. batch.release"
              style={{ minWidth: 220 }}
              required
            />
          </Field>
          <Field label="Site" hint="Leave blank for a site-independent action.">
            <Select value={siteId} onChange={(e) => setSiteId(e.target.value)} style={{ minWidth: 180 }}>
              <option value="">- none -</option>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code}
                </option>
              ))}
            </Select>
          </Field>
          <RowButtonSlot>
            <Button type="submit" variant="secondary" disabled={busy || !action.trim()}>
              <Icon name="shield-check" /> {busy ? "Checking…" : "Check"}
            </Button>
          </RowButtonSlot>
        </form>

        {error && <p className="error-text mt-3">{error}</p>}

        {decision && (
          <div className="mt-4">
            <StatePill
              state={decision.decision === "ALLOW" ? "accepted" : "failed"}
              icon={decision.decision === "ALLOW" ? "check-circle" : "x"}
            >
              {`${decision.decision} - ${decision.action}`}
            </StatePill>
            {decision.reason && (
              <p className="fs-2 mt-2">
                Reason: <span className="tabular">{decision.reason}</span>
                {decision.message ? ` - ${decision.message}` : ""}
              </p>
            )}
            <p className="fs-2 text-muted mt-2">
              Roles held{siteId ? " at this site" : ""}: {decision.held_roles.length ? decision.held_roles.join(", ") : "none"}
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
