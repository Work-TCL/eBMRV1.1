"use client";

import { useState } from "react";
import { api, ApiError, clientPagedFetcher, newIdempotencyKey } from "@/lib/api";
import { useEntityOptions, useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { Modal } from "@/components/ui/Modal";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { EntityPickerField } from "@/components/shared/EntityPicker";

interface MaterialSpecVersion {
  material_spec_version_id: string;
  material_spec_business_id: string;
  version_no: number;
  material_id: string;
  name: string;
  lifecycle_state: string;
  version: number;
}

// Matches app/modules/material_specification/router.py::get_business_ids — one row per distinct
// material_spec_business_id (its highest version_no), same SG-081 read-side precedent as
// product_master's/recipe_master's own business-ids pickers.
interface SpecBusinessIdOption {
  material_spec_version_id: string;
  material_spec_business_id: string;
  name: string;
  version_no: number;
  lifecycle_state: string;
}

export default function MaterialSpecificationsPage() {
  const { me } = useMe();
  const [newDraftOpen, setNewDraftOpen] = useState(false);

  return (
    <div>
      <PageHead
        title="Material specification master"
        subtitle="Draft and release material specification versions (distinct from material lots / inventory - see /materials for that)."
        action={
          me && (
            <Button variant="primary" onClick={() => setNewDraftOpen(true)}>
              <Icon name="plus" /> New specification draft
            </Button>
          )
        }
      />

      <SpecificationsCard />

      {newDraftOpen && (
        <NewDraftModal
          onClose={() => setNewDraftOpen(false)}
          onDone={() => setNewDraftOpen(false)}
        />
      )}
    </div>
  );
}

function SpecificationsCard() {
  const [reloadToken, setReloadToken] = useState(0);
  const [historyBusinessId, setHistoryBusinessId] = useState<string | null>(null);
  const [historyVersions, setHistoryVersions] = useState<MaterialSpecVersion[] | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [releasing, setReleasing] = useState<MaterialSpecVersion | null>(null);
  const [releaseLookupError, setReleaseLookupError] = useState<string | null>(null);

  // GET /material-specifications/v1/business-ids returns a plain array, not the server-side Paged<T>
  // envelope (Phase 1, small row counts — same ceiling product_master's/recipe_master's equivalent
  // lists document) — DataTable's search/sort/paging runs client-side over that array here.
  const fetchSpecs = clientPagedFetcher<SpecBusinessIdOption>(
    () => api.get<SpecBusinessIdOption[]>("/material-specifications/v1/business-ids"),
    { searchText: (s) => `${s.material_spec_business_id} ${s.name}` }
  );

  async function showHistory(businessId: string) {
    setHistoryBusinessId(businessId);
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      setHistoryVersions(
        await api.get<MaterialSpecVersion[]>(`/material-specifications/v1/${encodeURIComponent(businessId)}/versions`)
      );
    } catch (err) {
      setHistoryError(err instanceof ApiError ? err.message : "Could not load specification versions");
      setHistoryVersions(null);
    } finally {
      setHistoryLoading(false);
    }
  }

  // The list row only carries the latest version's id/state, not its record `version` (the release
  // command's optimistic-lock field) — fetch the full version detail before opening the signature
  // ceremony.
  async function releaseFromList(row: SpecBusinessIdOption) {
    setReleaseLookupError(null);
    try {
      setReleasing(await api.get<MaterialSpecVersion>(`/material-specifications/v1/${row.material_spec_version_id}`));
    } catch (err) {
      setReleaseLookupError(err instanceof ApiError ? err.message : "Could not load specification version");
    }
  }

  const columns: DataTableColumn<SpecBusinessIdOption>[] = [
    {
      key: "material_spec_business_id",
      header: "Business ID",
      sortable: true,
      render: (s) => <span className="font-semibold tabular">{s.material_spec_business_id}</span>,
    },
    { key: "name", header: "Name", sortable: true },
    {
      key: "version_no",
      header: "Latest version",
      sortable: true,
      render: (s) => <span className="tabular fs-2">v{s.version_no}</span>,
    },
    { key: "lifecycle_state", header: "State", sortable: true, render: (s) => <WorkflowStatePill state={s.lifecycle_state} /> },
    {
      key: "actions",
      header: "",
      render: (s) => (
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="ghost" onClick={() => showHistory(s.material_spec_business_id)}>
            Versions
          </Button>
          {s.lifecycle_state === "draft" && (
            <Button size="sm" variant="success" onClick={() => releaseFromList(s)}>
              <Icon name="pen" /> Release
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <Card className="mb-4">
      <CardHeader
        title="Material specifications"
        meta="One row per Business ID, its latest version - click Versions for the full history."
      />
      {releaseLookupError && (
        <p className="error-text mb-2" style={{ padding: "0 var(--space-4, 16px)" }}>
          {releaseLookupError}
        </p>
      )}
      <DataTable
        columns={columns}
        fetchPage={fetchSpecs}
        rowKey={(s) => s.material_spec_business_id}
        searchPlaceholder="Search by business ID or name…"
        emptyIcon="flask"
        emptyMessage={<>No material specifications drafted yet - use &quot;New specification draft&quot; above to create one.</>}
        defaultSort={{ by: "material_spec_business_id", dir: "asc" }}
        reloadToken={reloadToken}
      />

      {historyBusinessId && (
        <Card className="mt-4">
          <CardHeader
            title={`Versions - ${historyBusinessId}`}
            meta={
              <Button size="sm" variant="ghost" onClick={() => setHistoryBusinessId(null)}>
                Close
              </Button>
            }
          />
          {historyLoading ? (
            <p className="hint" style={{ padding: "var(--space-4, 16px)" }}>
              Loading…
            </p>
          ) : historyError ? (
            <p className="error-text" style={{ padding: "var(--space-4, 16px)" }}>
              {historyError}
            </p>
          ) : !historyVersions || historyVersions.length === 0 ? (
            <EmptyState icon="flask">No versions for this business ID.</EmptyState>
          ) : (
            <Table>
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Name</th>
                  <th>Material ID</th>
                  <th>State</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {historyVersions.map((v) => (
                  <tr key={v.material_spec_version_id}>
                    <td className="tabular">v{v.version_no}</td>
                    <td className="fs-2">{v.name}</td>
                    <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>{v.material_id}</td>
                    <td>
                      <WorkflowStatePill state={v.lifecycle_state} />
                    </td>
                    <td style={{ textAlign: "right" }}>
                      {v.lifecycle_state === "draft" && (
                        <Button size="sm" variant="success" onClick={() => setReleasing(v)}>
                          <Icon name="pen" /> Release
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}

      {releasing && (
        <ReleaseModal
          version={releasing}
          onClose={() => setReleasing(null)}
          onDone={() => {
            setReleasing(null);
            setReloadToken((n) => n + 1);
            if (historyBusinessId) void showHistory(historyBusinessId);
          }}
        />
      )}
    </Card>
  );
}

function NewDraftModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { siteId } = useSiteId();
  const entities = useEntityOptions();
  const [businessId, setBusinessId] = useState("");
  const [versionNo, setVersionNo] = useState("1");
  const [materialId, setMaterialId] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/material-specifications/v1/drafts", {
        idempotency_key: newIdempotencyKey(),
        material_spec_business_id: businessId.trim(),
        version_no: Number(versionNo),
        material_id: materialId.trim(),
        name: name.trim(),
        site_id: siteId,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not create draft");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="New material specification draft">
      <form onSubmit={submit}>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Business ID" required>
            <Input value={businessId} onChange={(e) => setBusinessId(e.target.value)} placeholder="e.g. MATSPEC-PFS-BODY-001" required autoFocus />
          </Field>
          <Field label="Version number" required>
            <Input type="number" min={1} value={versionNo} onChange={(e) => setVersionNo(e.target.value)} required />
          </Field>
          <EntityPickerField
            label="Material ID"
            required
            value={materialId}
            onChange={setMaterialId}
            options={entities.materials}
            status={entities.materialsStatus}
            kind="material"
          />
        </div>
        <Field label="Name" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={busy || !businessId.trim() || !materialId.trim() || !name.trim() || !siteId}
          >
            {busy ? "Creating…" : "Create draft"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ReleaseModal({
  version,
  onClose,
  onDone,
}: {
  version: MaterialSpecVersion;
  onClose: () => void;
  onDone: () => void;
}) {
  return (
    <>
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        challengePath={`/material-specifications/v1/${version.material_spec_version_id}/signature-challenges`}
        action="release"
        title={`Release - ${version.material_spec_business_id} v${version.version_no}`}
        summary={
          <>
            You are about to release <strong>{version.material_spec_business_id} v{version.version_no}</strong>.
          </>
        }
        reason="none"
        onSign={async (payload) => {
          try {
            return await api.post(`/material-specifications/v1/drafts/${version.material_spec_version_id}/release`, {
              idempotency_key: payload.idempotency_key,
              material_spec_version_id: version.material_spec_version_id,
              expected_version: version.version,
              challenge_id: payload.challenge_id,
              reauth_password: payload.reauth_password,
            });
          } catch (err) {
            throw err instanceof ApiError ? err : new Error("Request failed");
          }
        }}
      />
    </>
  );
}
