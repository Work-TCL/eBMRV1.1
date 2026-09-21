"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, canManageEvidenceIntegrity, canOperateEvidence, downloadEvidence, isAdminAnywhere } from "@/lib/api";
import { useEntityOptions, useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { FormConsole, EvidenceObjectOwnerPicker } from "@/components/shared/FormConsole";
import { SignedJsonForm } from "@/components/shared/SignedJsonForm";

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

      {isAdmin && (
        <GetCard
        title="Data ownership & dictionary"
        subtitle="The authoritative-store registry and the generated data dictionary."
        inputs={[{ name: "entity_type", label: "Entity type", placeholder: "e.g. batch, material_lot" }]}
        endpoints={(v) => [
          { label: "Data ownership", path: v.entity_type ? `/platform/v1/data-ownership/${encodeURIComponent(v.entity_type)}` : null },
          { label: "Data dictionary", path: `/platform/v1/data-dictionary` },
        ]}
      />
      )}

      {isAdmin && (
      <GetCard
        title="Projection & read-model health"
        subtitle="Projection freshness and read-model status."
        inputs={[
          { name: "projection_type", label: "Projection type" },
          { name: "entity_id", label: "Entity ID" },
          { name: "model_name", label: "Read model name" },
        ]}
        endpoints={(v) => [
          {
            label: "Projection freshness",
            path:
              v.projection_type && v.entity_id
                ? `/platform/v1/projections/${encodeURIComponent(v.projection_type)}/${encodeURIComponent(v.entity_id)}/freshness`
                : null,
          },
          {
            label: "Read-model status",
            path: v.model_name ? `/platform/v1/read-models/${encodeURIComponent(v.model_name)}/status` : null,
          },
        ]}
      />
      )}

      {isAdmin && (
      <GetCard
        title="Backup & disaster recovery"
        subtitle="Backup health, WAL/PITR coverage and restore-test evidence."
        inputs={[]}
        endpoints={() => [{ label: "Backup health", path: `/platform/v1/backups/health` }]}
      />
      )}

      {isAdmin && (
      <GetCard
        title="Search & read models"
        subtitle="The rebuildable search index (never authoritative for a regulated value)."
        inputs={[
          { name: "index_type", label: "Index type" },
          { name: "entity_id", label: "Entity ID (optional)" },
        ]}
        endpoints={(v) => [
          {
            label: "Search",
            path: v.index_type
              ? `/search/v1/${encodeURIComponent(v.index_type)}${v.entity_id ? `/${encodeURIComponent(v.entity_id)}` : ""}`
              : null,
          },
        ]}
      />
      )}

      {isAdmin && (
      <FormConsole
        title="Backup / DR operations"
        root="/platform/v1"
        ops={[
          {
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
          },
          {
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
          },
          { path: "projections/{projection_type}:rebuild", label: "Rebuild a projection", fields: [
            { name: "projection_type", label: "Projection type", required: true },
            { name: "reason", label: "Reason" },
          ] },
        ]}
      />
      )}

      <FormConsole
        title="Evidence operations"
        root="/evidence/v1"
        ops={[
          {
            path: "uploads",
            label: "Stage an evidence upload",
            about: "Stages the metadata row only. Once staged, use \"Finalize an upload\" below (same panel, pick it from the Operation list above) to attach the actual file and compute its hash.",
            fields: [
              { name: "owner_type", label: "Owner type", type: "ownerTypeSelect", required: true, hint: "Batch step and Batch (whole) are the two owner types this system stages evidence against today; pick \"Other…\" for anything else." },
              { name: "owner_id", label: "Owner ID", type: "ownerIdSelect", required: true, hint: "Picker depends on the Owner type selected above." },
              { name: "filename", label: "Filename", required: true },
              { name: "mime_type", label: "MIME type", required: true, default: "application/pdf" },
              { name: "reason", label: "Reason", required: true },
            ],
          },
          {
            path: "{evidence_id}:finalize",
            label: "Finalize an upload",
            fields: [
              { name: "evidence_id", label: "Evidence object ID", type: "evidenceSelect", required: true, hint: "Pick the staged evidence object by its owner type/ID." },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "content_base64", label: "File", type: "fileBase64", required: true, hint: "The file this evidence object's content hash will be finalized against." },
              { name: "reason", label: "Reason", required: true },
            ],
          },
        ]}
      />

      {/* evidence.manifest/.integrity_check/.legal_hold (Document 72) are Admin + QA Reviewer only —
          narrower than evidence.upload/.download above (also Operator/Supervisor). Split out of the
          console above 2026-09-18 (audit finding): Operator/Supervisor were previously shown these
          three ops in the same console as upload/finalize and got a silent 403 on each. */}
      {canEvidenceIntegrity && (
      <FormConsole
        title="Evidence integrity & manifests"
        root="/evidence/v1"
        ops={[
          {
            path: "integrity-checks",
            label: "Verify evidence integrity",
            fields: [
              { name: "mode", label: "Mode", type: "select", default: "full", options: [{ value: "full", label: "Full" }, { value: "sample", label: "Sample" }] },
              { name: "owner_type", label: "Owner type" },
              { name: "owner_id", label: "Owner ID" },
              { name: "reason", label: "Reason", required: true },
            ],
          },
          {
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
          },
        ]}
      />
      )}

      {canEvidenceIntegrity && (
      <SignedJsonForm
        title="Apply a legal hold"
        subtitle="Document 106 row 142 — 'Performed' by the authorized holder (Production/QA), reason required."
        root="/evidence/v1"
        ops={[
          {
            postPath: "{evidence_id}/legal-holds",
            challengePath: "{evidence_id}/signature-challenges",
            label: "Apply a legal hold",
            action: "legal_hold",
            fields: [
              { name: "evidence_id", label: "Evidence object ID", type: "evidenceSelect", required: true, hint: "Pick the evidence object by its owner type/ID." },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "hold_ref", label: "Hold reference", required: true },
              { name: "reason", label: "Reason", required: true },
            ],
          },
        ]}
      />
      )}

      <DownloadEvidenceCard />

      {isAdmin && (
      <FormConsole
        title="Search & report operations"
        root="/search/v1"
        ops={[
          {
            path: "indexes/{index_type}:rebuild",
            label: "Rebuild a search index",
            fields: [
              { name: "index_type", label: "Index type", required: true, placeholder: "e.g. gxp_batch, material_lot" },
              { name: "source_stream", label: "Source stream" },
              { name: "allowed_fields", label: "Allowed fields", type: "stringList", itemLabel: "Field" },
              { name: "expected_version", label: "Expected version", type: "number" },
              { name: "reason", label: "Reason" },
            ],
          },
        ]}
      />
      )}
      {isAdmin && (
      <FormConsole
      title="Workflow orchestration ops"
        root="/workflowops/v1"
        ops={[
          {
            path: "step-stuck-detection",
            label: "Start step-stuck detection",
            about: "Launches a Temporal workflow that watches one batch step for lack of progress. Unsigned by design - orchestration is never regulatory truth (AG-10).",
            fields: [
              { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
              { name: "step_id", label: "Step ID", required: true },
              { name: "threshold_seconds", label: "Threshold (seconds)", type: "number", default: "900" },
            ],
          },
          {
            path: "step-stuck-detection/{step_id}",
            label: "Get step-stuck detection status",
            method: "GET",
            fields: [{ name: "step_id", label: "Step ID", required: true }],
          },
        ]}
      />
      )}

      {isAdmin && (
      <FormConsole
        title="Async report exports"
        root="/reports/v1"
        ops={[
          {
            path: "exports",
            label: "Generate an async export",
            fields: [
              { name: "report_name", label: "Report name", required: true },
              { name: "source_stream", label: "Source stream", required: true },
              { name: "expected_version", label: "Expected version", type: "number" },
              { name: "reason", label: "Reason", required: true },
            ],
          },
        ]}
      />
      )}
    </div>
  );
}

/** `GET /evidence/v1/{evidence_id}/download` returns raw bytes (`Content-Disposition: attachment`), not
 * JSON — a `FormConsole` op can only show a JSON response, so this is its own small card using
 * `downloadEvidence()` (lib/api.ts), which fetches with the auth header and hands the browser a save. */
function DownloadEvidenceCard() {
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
    <Card pad className="mb-4">
      <CardHeader title="Download evidence" />
      <p className="fs-2 text-muted mb-3">
      Only a FINALIZED or ARCHIVED evidence object can be downloaded.
      </p>
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
      <Button variant="secondary" disabled={busy || !evidenceId.trim()} onClick={download}>
        <Icon name="download" /> {busy ? "Downloading…" : "Download"}
      </Button>
    </Card>
  );
}

interface GetInput {
  name: string;
  label: string;
  placeholder?: string;
}

function GetCard({
  title,
  subtitle,
  inputs,
  endpoints,
}: {
  title: string;
  subtitle: string;
  inputs: GetInput[];
  endpoints: (values: Record<string, string>) => { label: string; path: string | null }[];
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<{ label: string; data: unknown } | null>(null);
  const [busy, setBusy] = useState(false);

  const eps = endpoints(values);

  async function run(label: string, path: string) {
    setBusy(true);
    setResult(null);
    try {
      setResult({ label, data: await api.get<unknown>(path) });
    } catch (err) {
      setResult({ label, data: { error: err instanceof Error ? err.message : String(err) } });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title={title} />
      <p className="fs-2 text-muted mb-3">{subtitle}</p>
      {inputs.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-3">
          {inputs.map((i) => (
            <Field key={i.name} label={i.label}>
              <Input
                value={values[i.name] ?? ""}
                onChange={(e) => setValues((c) => ({ ...c, [i.name]: e.target.value }))}
                placeholder={i.placeholder}
              />
            </Field>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {eps.map((ep) => (
          <Button key={ep.label} variant="secondary" disabled={busy || !ep.path} onClick={() => ep.path && run(ep.label, ep.path)}>
            <Icon name="search" /> {ep.label}
          </Button>
        ))}
      </div>
      {result && (
        <div className="mt-3">
          <JsonPanel title={result.label} value={result.data} />
        </div>
      )}
    </Card>
  );
}
