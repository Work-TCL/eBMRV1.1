"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  ApiError,
  canManageEvidenceIntegrity,
  canOperateEvidence,
  clientPagedFetcher,
  downloadEvidence,
  isAdminAnywhere,
  pagedFetcher,
} from "@/lib/api";
import { useEntityOptions, useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Tabs } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { EvidenceObjectOwnerPicker } from "@/components/shared/FormConsole";
import { OpButton, SignedOpButton } from "@/components/shared/OpButtonModal";

interface DataDictionaryEntry {
  entity_type: string;
  authoritative_service: string;
  authoritative_store: string;
  tenant_scoped: boolean;
  site_scoped: boolean;
  classification: string;
  version: number;
}

interface RestoreTestRow {
  id: string;
  backup_id: string;
  target_environment: string;
  started_at: string | null;
  completed_at: string | null;
  result: string;
  evidence_ref: string | null;
}

interface EvidenceObjectRow {
  id: string;
  owner_type: string;
  owner_id: string;
  filename: string | null;
  state: string;
  legal_hold: boolean;
  version: number;
}

/** The rest of this page (data ownership, projections, backup/DR, search, workflow ops, report
 * exports) is platform.administer-gated server-side — Admin only. "Evidence operations" and "Download
 * evidence" are not: Document 72's evidence.upload/evidence.download are also granted to Operator,
 * Supervisor and QA Reviewer (scripts/seed.py). The page used to hard-gate the whole thing on Admin,
 * which meant nobody else could ever reach those two cards through the UI even though the backend
 * already authorized them (2026-09-17 fix, canOperateEvidence in lib/api.ts is the shared check). */
export default function PlatformPage() {
  const { me, loading } = useMe();
  const router = useRouter();
  const isAdmin = isAdminAnywhere(me);
  const canEvidence = canOperateEvidence(me);
  const canEvidenceIntegrity = canManageEvidenceIntegrity(me);

  useEffect(() => {
    if (!loading && !isAdmin && !canEvidence) router.replace("/batch-execution");
  }, [me, loading, isAdmin, canEvidence, router]);

  if (!isAdmin && !canEvidence) return null;

  const evidenceSection = (
    <EvidenceTab canEvidence={canEvidence} canEvidenceIntegrity={canEvidenceIntegrity} />
  );

  return (
    <div>
      <PageHead
        title="Platform operations"
        subtitle={
          isAdmin
            ? "Data ownership, projection health, evidence, search/read models and backup/DR."
            : "Stage, finalize and download evidence objects."
        }
      />

      {isAdmin ? (
        <Tabs
          tabs={[
            { id: "registry", label: "Data & registry", content: <RegistryTab /> },
            { id: "projections", label: "Projections & search", content: <ProjectionsTab /> },
            { id: "backup", label: "Backup & DR", content: <BackupTab /> },
            { id: "evidence", label: "Evidence", content: evidenceSection },
            { id: "workflow", label: "Workflow", content: <WorkflowTab /> },
            { id: "reports", label: "Reports", content: <ReportsTab /> },
          ]}
        />
      ) : (
        evidenceSection
      )}
    </div>
  );
}

function RegistryTab() {
  const columns: DataTableColumn<DataDictionaryEntry>[] = [
    { key: "entity_type", header: "Entity type", sortable: true, render: (e) => <span className="fs-2 font-semibold">{e.entity_type}</span> },
    { key: "authoritative_service", header: "Owning service", render: (e) => <span className="fs-2">{e.authoritative_service}</span> },
    { key: "authoritative_store", header: "Store", sortable: true, render: (e) => <span className="fs-2">{e.authoritative_store}</span> },
    { key: "classification", header: "Classification", render: (e) => <span className="fs-2">{e.classification}</span> },
    { key: "tenant_scoped", header: "Tenant scoped", render: (e) => (e.tenant_scoped ? "Yes" : "No") },
    { key: "site_scoped", header: "Site scoped", render: (e) => (e.site_scoped ? "Yes" : "No") },
  ];
  return (
    <>
      <Card pad className="mb-4">
        <CardHeader
          title="Data dictionary"
          meta="DATA-FR-027 — the authoritative-store registry, generated from every EFFECTIVE entry."
        />
        <DataTable<DataDictionaryEntry>
          columns={columns}
          fetchPage={clientPagedFetcher<DataDictionaryEntry>(
            () => api.get<{ entries: DataDictionaryEntry[] }>("/platform/v1/data-dictionary").then((r) => r.entries),
            { searchText: (e) => `${e.entity_type} ${e.authoritative_service} ${e.authoritative_store}` }
          )}
          rowKey={(e) => e.entity_type}
          searchPlaceholder="Search entity type…"
          emptyIcon="database"
          emptyMessage="No registry entries."
          defaultSort={{ by: "entity_type", dir: "asc" }}
        />
      </Card>
      <Card pad>
        <CardHeader title="Data ownership" meta="Look up one entity type's registry row." />
        <div className="flex gap-2">
          <OpButton
            root="/platform/v1"
            op={{
              path: "data-ownership/{entity_type}",
              label: "Look up data ownership",
              method: "GET",
              fields: [{ name: "entity_type", label: "Entity type", required: true, placeholder: "e.g. batch, material_lot" }],
            }}
          />
        </div>
      </Card>
    </>
  );
}

function ProjectionsTab() {
  return (
    <div className="flex flex-wrap gap-2">
      <Card pad className="mb-0">
        <CardHeader title="Projection & read-model health" />
        <div className="flex flex-wrap gap-2">
          <OpButton
            root="/platform/v1"
            op={{
              path: "projections/{projection_type}/{entity_id}/freshness",
              label: "Projection freshness",
              method: "GET",
              fields: [
                { name: "projection_type", label: "Projection type", required: true },
                { name: "entity_id", label: "Entity ID", required: true },
              ],
            }}
          />
          <OpButton
            root="/platform/v1"
            op={{
              path: "read-models/{model_name}/status",
              label: "Read-model status",
              method: "GET",
              fields: [{ name: "model_name", label: "Read model name", required: true }],
            }}
          />
        </div>
      </Card>
      <Card pad className="mb-0">
        <CardHeader title="Search & read models" meta="The rebuildable search index (never authoritative for a regulated value)." />
        <div className="flex flex-wrap gap-2">
          <OpButton
            root="/search/v1"
            op={{
              path: "{index_type}/{entity_id}",
              label: "Search",
              method: "GET",
              fields: [
                { name: "index_type", label: "Index type", required: true },
                { name: "entity_id", label: "Entity ID (optional)" },
              ],
            }}
          />
          <OpButton
            root="/search/v1"
            op={{
              path: "indexes/{index_type}:rebuild",
              label: "Rebuild a search index",
              fields: [
                { name: "index_type", label: "Index type", required: true, placeholder: "e.g. gxp_batch, material_lot" },
                { name: "source_stream", label: "Source stream" },
                { name: "allowed_fields", label: "Allowed fields", type: "stringList", itemLabel: "Field" },
                { name: "expected_version", label: "Expected version", type: "number" },
                { name: "reason", label: "Reason" },
              ],
            }}
          />
        </div>
      </Card>
    </div>
  );
}

function BackupTab() {
  const [reloadToken, setReloadToken] = useState(0);
  const columns: DataTableColumn<RestoreTestRow>[] = [
    { key: "target_environment", header: "Target environment", sortable: true, render: (r) => <span className="fs-2 font-semibold">{r.target_environment}</span> },
    { key: "started_at", header: "Started", sortable: true, render: (r) => <span className="tabular fs-2">{r.started_at ?? "—"}</span> },
    { key: "completed_at", header: "Completed", render: (r) => <span className="tabular fs-2">{r.completed_at ?? "—"}</span> },
    { key: "result", header: "Result", render: (r) => <WorkflowStatePill state={r.result} /> },
    { key: "evidence_ref", header: "Evidence ref", render: (r) => <span className="fs-2">{r.evidence_ref ?? "—"}</span> },
  ];
  return (
    <>
      <Card pad className="mb-4">
        <CardHeader
          title="Restore test runs"
          meta={
            <div className="flex gap-2">
              <OpButton root="/platform/v1" op={{ path: "backups/health", label: "Backup health", method: "GET" }} />
              <OpButton
                root="/platform/v1"
                op={{
                  path: "recovery-objectives",
                  label: "Create a recovery-objective profile",
                  about: "Sets the RPO/RTO target for one component and the tier it belongs to.",
                  fields: [
                    { name: "component", label: "Component", required: true, placeholder: "e.g. postgres, object-store" },
                    { name: "tier", label: "Tier", type: "select", required: true, options: ["T0", "T1", "T2", "T3", "T4"].map((v) => ({ value: v, label: v })) },
                    { name: "rto_seconds", label: "RTO (seconds)", type: "number", required: true, default: "3600" },
                    { name: "rpo_seconds", label: "RPO (seconds)", type: "number", default: "300" },
                    { name: "approved_by", label: "Approved by", type: "userSelect", required: true },
                    { name: "reason", label: "Reason", required: true },
                  ],
                }}
              />
              <OpButton
                root="/platform/v1"
                op={{
                  path: "restore-tests",
                  label: "Record a restore test",
                  fields: [
                    { name: "backup_id", label: "Backup ID", required: true },
                    { name: "target_environment", label: "Target environment", required: true },
                    { name: "started_at", label: "Started at", type: "datetime", required: true },
                    { name: "completed_at", label: "Completed at", type: "datetime", required: true },
                    {
                      name: "integrity_checks", label: "Integrity checks", type: "kv", required: true,
                      hint: 'Each check performed and whether it passed - enter "true" or "false" as the value, e.g. "checksum_verified" → "true". At least one is required.',
                    },
                    { name: "reason", label: "Reason", required: true },
                  ],
                }}
                variant="primary"
              />
              <Button variant="ghost" onClick={() => setReloadToken((n) => n + 1)}>
                <Icon name="refresh-cw" /> Refresh
              </Button>
            </div>
          }
        />
        <DataTable<RestoreTestRow>
          columns={columns}
          fetchPage={pagedFetcher<RestoreTestRow>("/platform/v1/restore-tests")}
          rowKey={(r) => r.id}
          emptyIcon="shield-check"
          emptyMessage="No restore tests recorded yet."
          defaultSort={{ by: "started_at", dir: "desc" }}
          reloadToken={reloadToken}
        />
      </Card>
      <Card pad>
        <CardHeader title="Rebuild a projection" />
        <OpButton
          root="/platform/v1"
          op={{
            path: "projections/{projection_type}:rebuild",
            label: "Rebuild a projection",
            fields: [
              { name: "projection_type", label: "Projection type", required: true },
              { name: "reason", label: "Reason" },
            ],
          }}
        />
      </Card>
    </>
  );
}

function EvidenceTab({ canEvidence, canEvidenceIntegrity }: { canEvidence: boolean; canEvidenceIntegrity: boolean }) {
  return (
    <>
      {canEvidence && (
        <Card pad className="mb-4">
          <CardHeader title="Evidence operations" />
          <div className="flex flex-wrap gap-2">
            <OpButton
              root="/evidence/v1"
              op={{
                path: "uploads",
                label: "Stage an evidence upload",
                about: 'Stages the metadata row only. Once staged, use "Finalize an upload" to attach the actual file and compute its hash.',
                fields: [
                  { name: "owner_type", label: "Owner type", type: "ownerTypeSelect", required: true, hint: 'Batch step and Batch (whole) are the two owner types this system stages evidence against today; pick "Other…" for anything else.' },
                  { name: "owner_id", label: "Owner ID", type: "ownerIdSelect", required: true, hint: "Picker depends on the Owner type selected above." },
                  { name: "filename", label: "Filename", required: true },
                  { name: "mime_type", label: "MIME type", required: true, default: "application/pdf" },
                  { name: "reason", label: "Reason", required: true },
                ],
              }}
            />
            <OpButton
              root="/evidence/v1"
              op={{
                path: "{evidence_id}:finalize",
                label: "Finalize an upload",
                fields: [
                  { name: "evidence_id", label: "Evidence object ID", type: "evidenceSelect", required: true, hint: "Pick the staged evidence object by its owner type/ID." },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "content_base64", label: "File", type: "fileBase64", required: true, hint: "The file this evidence object's content hash will be finalized against." },
                  { name: "reason", label: "Reason", required: true },
                ],
              }}
            />
            <DownloadEvidenceButton />
          </div>
        </Card>
      )}

      {/* evidence.manifest/.integrity_check/.legal_hold (Document 72) are Admin + QA Reviewer only —
          narrower than evidence.upload/.download above (also Operator/Supervisor). */}
      {canEvidenceIntegrity && (
        <Card pad className="mb-4">
          <CardHeader title="Evidence integrity & manifests" />
          <div className="flex flex-wrap gap-2">
            <OpButton
              root="/evidence/v1"
              op={{
                path: "integrity-checks",
                label: "Verify evidence integrity",
                fields: [
                  { name: "mode", label: "Mode", type: "select", default: "full", options: [{ value: "full", label: "Full" }, { value: "sample", label: "Sample" }] },
                  { name: "owner_type", label: "Owner type" },
                  { name: "owner_id", label: "Owner ID" },
                  { name: "reason", label: "Reason", required: true },
                ],
              }}
            />
            <OpButton
              root="/evidence/v1"
              op={{
                path: "manifests",
                label: "Create an evidence manifest",
                fields: [
                  { name: "owner_type", label: "Owner type", required: true, placeholder: "e.g. batch, oos_record" },
                  { name: "owner_id", label: "Owner ID", required: true },
                  { name: "owner_version", label: "Owner version", type: "number" },
                  { name: "manifest_type", label: "Manifest type", required: true },
                  { name: "evidence_ids", label: "Evidence object IDs", type: "stringList", required: true, itemLabel: "Evidence object ID" },
                  { name: "renderer_version", label: "Renderer version" },
                  { name: "reason", label: "Reason", required: true },
                ],
              }}
            />
            <SignedOpButton
              root="/evidence/v1"
              op={{
                postPath: "{evidence_id}/legal-holds",
                challengePath: "{evidence_id}/signature-challenges",
                label: "Apply a legal hold",
                action: "legal_hold",
                about: "Document 106 row 142 — 'Performed' by the authorized holder (Production/QA), reason required.",
                fields: [
                  { name: "evidence_id", label: "Evidence object ID", type: "evidenceSelect", required: true, hint: "Pick the evidence object by its owner type/ID." },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "hold_ref", label: "Hold reference", required: true },
                  { name: "reason", label: "Reason", required: true },
                ],
              }}
            />
          </div>
        </Card>
      )}

      {canEvidence && <EvidenceObjectsCard />}
    </>
  );
}

/** Owner-scoped browsable list (GET /evidence/v1/objects) — always owner-scoped, never an unfiltered
 * listing of the whole table (see that endpoint's own docstring), so the DataTable is fed once an owner
 * type/ID pair is entered rather than paging a global collection. */
function EvidenceObjectsCard() {
  // Batch is the only owner type this card offers a picker for today — batch_step evidence is browsed
  // from the batch-execution step detail instead, where the specific step is already in context.
  const ownerType = "batch";
  const [ownerId, setOwnerId] = useState("");
  const [loadedFor, setLoadedFor] = useState<{ type: string; id: string } | null>(null);
  const entities = useEntityOptions();

  const columns: DataTableColumn<EvidenceObjectRow>[] = [
    { key: "filename", header: "Filename", render: (r) => <span className="fs-2 font-semibold">{r.filename ?? "—"}</span> },
    { key: "state", header: "State", render: (r) => <WorkflowStatePill state={r.state} /> },
    { key: "legal_hold", header: "Legal hold", render: (r) => (r.legal_hold ? <span className="error-text">Yes</span> : "No") },
    { key: "id", header: "Evidence ID", render: (r) => <span className="tabular fs-2">{r.id}</span> },
  ];

  return (
    <Card pad>
      <CardHeader title="Evidence objects" meta="Owner-scoped — pick a batch to see what's staged against it." />
      <div className="grid grid-cols-3 gap-4 mb-3 items-end">
        <Field label="Batch">
          <select className="input" value={ownerId} onChange={(e) => setOwnerId(e.target.value)} disabled={entities.batchesStatus === "loading"}>
            <option value="">{entities.batchesStatus === "loading" ? "Loading batches…" : "Select a batch…"}</option>
            {entities.batches.map((b) => (
              <option key={b.value} value={b.value}>
                {b.label}
              </option>
            ))}
          </select>
        </Field>
        <Button variant="secondary" disabled={!ownerId} onClick={() => setLoadedFor({ type: ownerType, id: ownerId })}>
          <Icon name="search" /> Load evidence objects
        </Button>
      </div>
      {loadedFor ? (
        <DataTable<EvidenceObjectRow>
          columns={columns}
          fetchPage={clientPagedFetcher<EvidenceObjectRow>(
            () =>
              api
                .get<{ evidence_objects: EvidenceObjectRow[] }>(
                  `/evidence/v1/objects?owner_type=${encodeURIComponent(loadedFor.type)}&owner_id=${encodeURIComponent(loadedFor.id)}`
                )
                .then((r) => r.evidence_objects),
            { searchText: (r) => r.filename ?? "" }
          )}
          rowKey={(r) => r.id}
          emptyIcon="file"
          emptyMessage="No evidence objects staged against this owner yet."
          reloadToken={loadedFor.id.length}
        />
      ) : (
        <p className="hint">Pick a batch and load to see its evidence objects.</p>
      )}
    </Card>
  );
}

/** `GET /evidence/v1/{evidence_id}/download` returns raw bytes (`Content-Disposition: attachment`), not
 * JSON — a generic op button can only show a JSON response, so this stays its own small modal using
 * `downloadEvidence()` (lib/api.ts), which fetches with the auth header and hands the browser a save. */
function DownloadEvidenceButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        <Icon name="download" /> Download evidence
      </Button>
      {open && <DownloadEvidenceModal onClose={() => setOpen(false)} />}
    </>
  );
}

function DownloadEvidenceModal({ onClose }: { onClose: () => void }) {
  const [evidenceId, setEvidenceId] = useState("");
  const [purpose, setPurpose] = useState("inspection");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const entities = useEntityOptions();

  async function download() {
    setBusy(true);
    setError(null);
    try {
      await downloadEvidence(evidenceId.trim(), purpose.trim() || "inspection");
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Download failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Download evidence" large>
      <p className="fs-2 text-muted mb-3">Only a FINALIZED or ARCHIVED evidence object can be downloaded.</p>
      <div className="grid grid-cols-3 gap-4 mb-3">
        <EvidenceObjectOwnerPicker
          label="Evidence object ID"
          value={evidenceId}
          onChange={setEvidenceId}
          batchOptions={entities.batches}
          batchOptionsStatus={entities.batchesStatus}
        />
        <Field label="Purpose" hint="Recorded in the audit trail for this download.">
          <Input value={purpose} onChange={(e) => setPurpose(e.target.value)} />
        </Field>
      </div>
      {error && <p className="error-text mb-2">{error}</p>}
      <div className="flex justify-between gap-3">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        <Button variant="primary" disabled={busy || !evidenceId.trim()} onClick={download}>
          <Icon name="download" /> {busy ? "Downloading…" : "Download"}
        </Button>
      </div>
    </Modal>
  );
}

function WorkflowTab() {
  return (
    <Card pad>
      <CardHeader title="Workflow orchestration ops" />
      <div className="flex flex-wrap gap-2">
        <OpButton
          root="/workflowops/v1"
          op={{
            path: "step-stuck-detection",
            label: "Start step-stuck detection",
            about: "Launches a Temporal workflow that watches one batch step for lack of progress. Unsigned by design - orchestration is never regulatory truth (AG-10).",
            fields: [
              { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
              { name: "step_id", label: "Step ID", required: true },
              { name: "threshold_seconds", label: "Threshold (seconds)", type: "number", default: "900" },
            ],
          }}
          variant="primary"
        />
        <OpButton
          root="/workflowops/v1"
          op={{
            path: "step-stuck-detection/{step_id}",
            label: "Get step-stuck detection status",
            method: "GET",
            fields: [{ name: "step_id", label: "Step ID", required: true }],
          }}
        />
      </div>
    </Card>
  );
}

function ReportsTab() {
  return (
    <Card pad>
      <CardHeader title="Async report exports" />
      <OpButton
        root="/reports/v1"
        op={{
          path: "exports",
          label: "Generate an async export",
          fields: [
            { name: "report_name", label: "Report name", required: true },
            { name: "source_stream", label: "Source stream", required: true },
            { name: "expected_version", label: "Expected version", type: "number" },
            { name: "reason", label: "Reason", required: true },
          ],
        }}
        variant="primary"
      />
    </Card>
  );
}
