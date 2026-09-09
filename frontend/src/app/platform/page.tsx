"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useRequireAdmin } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { FormConsole } from "@/components/shared/FormConsole";

export default function PlatformPage() {
  const { isAdmin } = useRequireAdmin();
  if (!isAdmin) return null;

  return (
    <div>
      <PageHead
        title="Platform operations"
        subtitle="Data ownership, projection health, evidence, search/read models and backup/DR."
      />

      <GetCard
        title="Data ownership & dictionary"
        subtitle="The authoritative-store registry and the generated data dictionary."
        inputs={[{ name: "entity_type", label: "Entity type", placeholder: "e.g. batch, material_lot" }]}
        endpoints={(v) => [
          { label: "Data ownership", path: v.entity_type ? `/platform/v1/data-ownership/${encodeURIComponent(v.entity_type)}` : null },
          { label: "Data dictionary", path: `/platform/v1/data-dictionary` },
        ]}
      />

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

      <GetCard
        title="Backup & disaster recovery"
        subtitle="Backup health, WAL/PITR coverage and restore-test evidence."
        inputs={[]}
        endpoints={() => [{ label: "Backup health", path: `/platform/v1/backups/health` }]}
      />

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
              { name: "approved_by", label: "Approved by", required: true },
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
                hint: 'Each check performed and whether it passed — enter "true" or "false" as the value, e.g. "checksum_verified" → "true". At least one is required.',
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

      <FormConsole
        title="Evidence operations"
        root="/evidence/v1"
        ops={[
          {
            path: "uploads",
            label: "Stage an evidence upload",
            fields: [
              { name: "owner_type", label: "Owner type", required: true, placeholder: "e.g. batch, oos_record" },
              { name: "owner_id", label: "Owner ID", required: true },
              { name: "filename", label: "Filename", required: true },
              { name: "mime_type", label: "MIME type", required: true, default: "application/pdf" },
              { name: "reason", label: "Reason", required: true },
            ],
          },
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
            path: "{evidence_id}:finalize",
            label: "Finalize an upload",
            fields: [
              { name: "evidence_id", label: "Evidence object ID", required: true, hint: "The ID returned when the upload was staged." },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "content_base64", label: "File", type: "fileBase64", required: true, hint: "The file this evidence object's content hash will be finalized against." },
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
          {
            path: "{evidence_id}/legal-holds",
            label: "Apply a legal hold",
            about: "Document 106 has no signature-policy row for this action yet — if one is later added, this form does not yet request the signature challenge it would require, so the action will correctly fail closed rather than proceed unsigned.",
            fields: [
              { name: "evidence_id", label: "Evidence object ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "hold_ref", label: "Hold reference", required: true },
              { name: "reason", label: "Reason", required: true },
            ],
          },
        ]}
      />

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
    </div>
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
