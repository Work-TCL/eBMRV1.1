"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useRequireAdmin } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { FormConsole } from "@/components/shared/FormConsole";
import { SignedJsonForm } from "@/components/shared/SignedJsonForm";

export default function MachineIntegrationPage() {
  const { isAdmin } = useRequireAdmin();
  if (!isAdmin) return null;

  return (
    <div>
      <PageHead
        title="Machine integration"
        subtitle="PLC/SCADA signal mappings, batch contexts, machine commands and evidence review."
      />

      <Banner tone="info" title="Machine-to-machine operations aren't shown here">
        Evidence ingest, cycle-evidence-manifest build and machine-command finalize (`POST
        /machine-integration/v1/machine-sources/{'{source_id}'}/evidence:ingest`, `/cycle-evidence-manifests`,
        `machine-commands/{'{request_id}'}/finalize`) are authenticated with the gateway&apos;s own service
        credential, not a signed-in user session - nothing this admin console can call for them.
      </Banner>

      <ReadCard />

      <FormConsole
        title="Batch context operations"
        root="/machine-integration/v1"
        ops={[
          {
            path: "batch-contexts",
            label: "Open a batch context",
            about: "Links a machine source to a batch (and optionally a step) so its evidence is attributable.",
            fields: [
              { name: "source_id", label: "Machine source ID", required: true },
              { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
              { name: "batch_step_id", label: "Batch step ID" },
            ],
          },
          {
            path: "batch-contexts/{context_id}/close",
            label: "Close a batch context",
            fields: [
              { name: "context_id", label: "Batch context ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
            ],
          },
        ]}
      />

      <SignedJsonForm
        title="Signal mapping release - signed"
        subtitle="A signal mapping must be released before it can back live evidence."
        root="/machine-integration/v1"
        ops={[
          {
            postPath: "signal-mappings/{mapping_id}/release",
            challengePath: "signal-mappings/signature-challenges",
            action: "release",
            label: "Release a signal mapping",
            mirrorBodyInChallenge: true,
            fields: [
              { name: "mapping_id", label: "Signal mapping ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
        ]}
      />

      <SignedJsonForm
        title="Machine command submission - signed"
        subtitle="Only an already-released command profile for this operation code authorizes the command."
        root="/machine-integration/v1"
        ops={[
          {
            postPath: "machine-commands",
            challengePath: "machine-commands/signature-challenges",
            action: "submit",
            label: "Submit an approved machine command",
            mirrorBodyInChallenge: true,
            fields: [
              { name: "source_id", label: "Machine source ID", required: true },
              { name: "operation_code", label: "Operation code", required: true },
              { name: "parameters", label: "Parameters", type: "kv" },
              { name: "batch_id", label: "Batch", type: "batchSelect" },
              { name: "batch_state", label: "Batch state" },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
        ]}
      />

      <SignedJsonForm
        title="Historical evidence replay - signed"
        subtitle="Re-processes already-accepted observation events through the routing pipeline (backfill or replay)."
        root="/machine-integration/v1"
        ops={[
          {
            postPath: "sites/{site_id}/evidence-replays",
            challengePath: "evidence-replays/signature-challenges",
            action: "replay",
            label: "Replay historical evidence",
            mirrorBodyInChallenge: true,
            fields: [
              { name: "site_id", label: "Site ID", required: true, pathOnly: true },
              { name: "event_ids", label: "Event IDs", type: "stringList", required: true, itemLabel: "Event ID" },
              { name: "mode", label: "Mode", type: "select", required: true, options: [
                { value: "BACKFILL", label: "Backfill" }, { value: "REPLAY", label: "Replay" }] },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
        ]}
      />
    </div>
  );
}

/** `site_id` fills the `{site_id}` path placeholder above but is not itself a field on
 * `ReplayHistoricalEvidenceCommand` (it's a separate function argument server-side) — same shape
 * `FormConsole.FormField.pathOnly` already documents. */

function ReadCard() {
  const [requestId, setRequestId] = useState("");
  const [manifestId, setManifestId] = useState("");
  const [siteId, setSiteId] = useState("");
  const [limit, setLimit] = useState("50");
  const [result, setResult] = useState<{ label: string; data: unknown } | null>(null);
  const [busy, setBusy] = useState(false);

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
      <CardHeader title="Machine command status, QA evidence review & manifest export" />
      <div className="grid grid-cols-4 gap-4 mb-3">
        <Field label="Machine command request ID">
          <Input value={requestId} onChange={(e) => setRequestId(e.target.value)} />
        </Field>
        <Field label="Cycle evidence manifest ID">
          <Input value={manifestId} onChange={(e) => setManifestId(e.target.value)} />
        </Field>
        <Field label="Site ID (evidence review)">
          <Input value={siteId} onChange={(e) => setSiteId(e.target.value)} />
        </Field>
        <Field label="Limit (evidence review)">
          <Input type="number" value={limit} onChange={(e) => setLimit(e.target.value)} />
        </Field>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          disabled={busy || !requestId.trim()}
          onClick={() => run("Machine command status", `/machine-integration/v1/machine-commands/${encodeURIComponent(requestId.trim())}`)}
        >
          <Icon name="search" /> Machine command status
        </Button>
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() => {
            const q = new URLSearchParams();
            if (siteId.trim()) q.set("site_id", siteId.trim());
            if (limit.trim()) q.set("limit", limit.trim());
            run("Evidence for QA review", `/machine-integration/v1/evidence-review?${q.toString()}`);
          }}
        >
          <Icon name="search" /> Evidence for QA review
        </Button>
        <Button
          variant="secondary"
          disabled={busy || !manifestId.trim()}
          onClick={() =>
            run(
              "Cycle evidence manifest export",
              `/machine-integration/v1/cycle-evidence-manifests/${encodeURIComponent(manifestId.trim())}/export`
            )
          }
        >
          <Icon name="search" /> Manifest export
        </Button>
      </div>
      {result && (
        <div className="mt-3">
          <JsonPanel title={result.label} value={result.data} />
        </div>
      )}
    </Card>
  );
}
