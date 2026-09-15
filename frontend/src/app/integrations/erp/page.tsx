"use client";

import { useEffect, useState } from "react";
import { api, ApiError, holdsAnyRole, listAll, newIdempotencyKey, type MutationReceipt } from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import type { EntityOption, EntityOptionsStatus } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { WorkflowActionButton } from "@/components/shared/WorkflowActionButton";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { FormConsole } from "@/components/shared/FormConsole";

const ROOT = "/integration/v1";

// GET /integration/v1/instances
interface ErpInstanceSummary {
  id: string;
  instance_name: string;
  vendor: string;
  environment: string;
  status: string;
}

/** Shared by every "ERP instance" field on this page — loaded once per card that needs it, refetched on
 * `refreshToken` change so a newly-registered instance shows up without a remount. */
function useErpInstances(refreshToken: number): { options: EntityOption[]; status: EntityOptionsStatus } {
  const [options, setOptions] = useState<EntityOption[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("loading");
  useEffect(() => {
    let cancelled = false;
    listAll<ErpInstanceSummary>(`${ROOT}/instances`)
      .then((rows) => {
        if (cancelled) return;
      setOptions(rows.map((r) => ({ value: r.id, label: `${r.instance_name} - ${r.vendor}/${r.environment} (${r.status})` })));
        setStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [refreshToken]);
  return { options, status };
}

interface ErpInstance {
  id: string;
  instance_name: string;
  vendor: string;
  environment: string;
  status: string;
  version: number;
  validated: boolean;
}

interface IntegrationCommand {
  id: string;
  command_type: string;
  state: string;
  attempt_count: number;
  external_reference: Record<string, unknown> | null;
  last_error_category: string | null;
  version: number;
}

export default function ErpIntegrationPage() {
  const { me } = useMe();
  const isAdmin = holdsAnyRole(me, ["Admin", "Integration Administrator"]);
  // Bumped after a successful instance registration so every instance picker on the page refetches and
  // includes it immediately, rather than only after a full page reload.
  const [instanceListVersion, setInstanceListVersion] = useState(0);

  return (
    <div>
      <PageHead
        title="ERP integration"
        subtitle="ERP instance registry, capability/health, the outbound command queue and reconciliation."
      />

      {!isAdmin && (
        <Banner tone="info" title="Read-only">
          Registering instances and driving the command queue needs the Integration Administrator role.
        </Banner>
      )}

      <p className="hint mb-4">
        Integration events appear in the Audit ledger with source ERP.
      </p>

      {isAdmin && <RegisterInstanceCard onRegistered={() => setInstanceListVersion((n) => n + 1)} />}
      <InstanceCard canAdmin={isAdmin} instanceListVersion={instanceListVersion} />
      <CommandCard canAdmin={isAdmin} />
      {isAdmin && <MappingCard instanceListVersion={instanceListVersion} />}
      {isAdmin && <ReconciliationCard instanceListVersion={instanceListVersion} />}
      {isAdmin && <MoreOpsConsole />}
    </div>
  );
}

/** The remaining `/integration/v1` operations that don't yet have a bespoke card above — mapping
 * approval/external-change/conflict-resolution, sync checkpoints, the command correct/reconcile-
 * uncertain/compensate lifecycle, bulk jobs, migration-package provenance, inbound event ingest, and
 * the rest of reconciliation (record a difference, resolve one, complete a run). All unsigned: the two
 * commands with an optional `challenge_id` (mapping approve, conflict resolve) both resolve
 * `signature_required=False` from policy today (SG-122, see `erp/commands.py`), same "policy resolves
 * not required" shape as every other unsigned-by-policy op elsewhere in this app. */
function MoreOpsConsole() {
  return (
    <FormConsole
      title="More integration operations"
      root={ROOT}
      ops={[
        {
          path: "mappings/{mapping_id}/approve",
          label: "Approve a master-data mapping",
          fields: [
            { name: "mapping_id", label: "Mapping ID", required: true },
            { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
          ],
        },
        {
          path: "mappings/{mapping_id}/external-change",
          label: "Apply an external mapping change",
          about: "Sync-processor trigger, not typically human-initiated - exposed here for support/replay use.",
          fields: [
            { name: "mapping_id", label: "Mapping ID", required: true },
            { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
            { name: "field_name", label: "Field name", required: true },
            { name: "proposed_value", label: "Proposed value", type: "kv", required: true },
          ],
        },
        {
          path: "mapping-conflicts/{conflict_id}/resolve",
          label: "Resolve a master-data conflict",
          fields: [
            { name: "conflict_id", label: "Conflict ID", required: true },
            { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
            { name: "resolution", label: "Resolution", type: "select", required: true, options: [
              { value: "ACCEPT_PROPOSED", label: "Accept proposed" }, { value: "KEEP_CURRENT", label: "Keep current" }, { value: "REJECT", label: "Reject" }] },
            { name: "resolution_reason", label: "Resolution reason", type: "textarea", required: true },
          ],
        },
        {
          path: "sync-checkpoints",
          label: "Advance a sync checkpoint",
          fields: [
            { name: "erp_instance_id", label: "ERP instance ID", required: true },
            { name: "entity_type", label: "Entity type", required: true },
            { name: "cursor_value", label: "Cursor value", required: true },
            { name: "last_batch_id", label: "Last batch ID", hint: "Optional - the idempotent-resume handle." },
          ],
        },
        {
          path: "commands/{original_command_id}/correct",
          label: "Correct a failed command",
          about: "Creates a brand-new corrected command linked to the original - the original's payload is never mutated.",
          fields: [
            { name: "original_command_id", label: "Original command ID", required: true },
            { name: "corrected_payload", label: "Corrected payload", type: "kv", required: true },
            { name: "reason", label: "Reason", type: "textarea", required: true },
          ],
        },
        {
          path: "commands/{command_id}/reconcile-uncertain",
          label: "Reconcile an uncertain-outcome command",
          about: "Only a command stuck DISPATCHED past a crash can be reconciled - always routes to RETRY_WAIT pending a human external-system lookup.",
          fields: [{ name: "command_id", label: "Command ID", required: true, pathOnly: true }],
        },
        {
          path: "commands/{original_command_id}/compensate",
          label: "Compensate a succeeded command",
          about: "Reverses an operation that already succeeded externally - always a new command, tied to the authorizing GxP decision.",
          fields: [
            { name: "original_command_id", label: "Original command ID", required: true },
            { name: "compensating_command_type", label: "Compensating command type", required: true },
            { name: "compensating_payload", label: "Compensating payload", type: "kv", required: true },
            { name: "gxp_authorization_reference", label: "GxP authorization reference", type: "kv", required: true, hint: "The GxP record/decision that justifies reversing this." },
            { name: "reason", label: "Reason", type: "textarea", required: true },
          ],
        },
        {
          path: "bulk-jobs",
          label: "Start a bulk job",
          fields: [
            { name: "erp_instance_id", label: "ERP instance ID", required: true },
            { name: "job_type", label: "Job type", required: true },
            { name: "entity_type", label: "Entity type", required: true },
            { name: "total_records", label: "Total records", type: "number", hint: "Optional, if known up front." },
          ],
        },
        {
          path: "bulk-jobs/{job_id}/progress",
          label: "Record bulk job progress",
          fields: [
            { name: "job_id", label: "Bulk job ID", required: true },
            { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
            { name: "succeeded_delta", label: "Succeeded this chunk", type: "number", default: "0" },
            {
              name: "newly_failed_records", label: "Newly failed records this chunk", type: "repeat", itemLabel: "Failed record",
              subFields: [{ name: "record_ref", label: "Record reference" }, { name: "reason", label: "Reason" }],
            },
            { name: "resume_cursor", label: "Resume cursor", hint: "Optional - where to continue after a crash." },
          ],
        },
        {
          path: "bulk-jobs/{job_id}/complete",
          label: "Complete a bulk job",
          fields: [
            { name: "job_id", label: "Bulk job ID", required: true },
            { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
          ],
        },
        {
          path: "migration-packages",
          label: "Record a migration package",
          about: "A provenance record, not a workflow.",
          fields: [
            { name: "erp_instance_id", label: "ERP instance ID", hint: "Optional." },
            { name: "site_id", label: "Site ID", hint: "Optional." },
            { name: "package_name", label: "Package name", required: true },
            { name: "source_checksum", label: "Source checksum", required: true },
            { name: "entity_types", label: "Entity types", type: "stringList", itemLabel: "Entity type" },
            { name: "approval_reference", label: "Approval reference", hint: "Set only when this package was already approved elsewhere." },
          ],
        },
        {
          path: "events",
          label: "Ingest an inbound ERP event",
          fields: [
            { name: "erp_instance_id", label: "ERP instance ID", required: true },
            { name: "external_event_id", label: "External event ID", required: true },
            { name: "entity_type", label: "Entity type" },
            { name: "external_entity_id", label: "External entity ID", hint: "Required for staleness detection." },
            { name: "source_version", label: "Source version" },
            { name: "payload", label: "Payload", type: "kv", required: true },
          ],
        },
        {
          path: "reconciliation-runs/{run_id}/differences",
          label: "Record a reconciliation difference",
          fields: [
            { name: "run_id", label: "Reconciliation run ID", required: true },
            { name: "difference_type", label: "Difference type", required: true },
            { name: "internal_ref", label: "Internal reference", type: "kv" },
            { name: "external_ref", label: "External reference", type: "kv" },
            { name: "field_name", label: "Field name" },
            { name: "internal_value", label: "Internal value", type: "kv" },
            { name: "external_value", label: "External value", type: "kv" },
            { name: "requires_qa_hold", label: "Requires QA hold", type: "bool", default: "false" },
          ],
        },
        {
          path: "reconciliation-differences/{difference_id}/resolve",
          label: "Resolve a reconciliation difference",
          fields: [
            { name: "difference_id", label: "Difference ID", required: true },
            { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
            { name: "resolution_status", label: "Resolution status", type: "select", required: true, options: [
              { value: "RESOLVED", label: "Resolved" }, { value: "ESCALATED", label: "Escalated" }] },
            { name: "resolution_reason", label: "Resolution reason", type: "textarea", required: true },
          ],
        },
        {
          path: "reconciliation-runs/{run_id}/complete",
          label: "Complete a reconciliation run",
          fields: [
            { name: "run_id", label: "Reconciliation run ID", required: true },
            { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
            { name: "status", label: "Status", type: "select", required: true, options: [
              { value: "COMPLETED", label: "Completed" }, { value: "FAILED", label: "Failed" }] },
          ],
        },
      ]}
    />
  );
}

function RegisterInstanceCard({ onRegistered }: { onRegistered: () => void }) {
  const { siteId } = useSiteId();
  const [f, setF] = useState({
    instance_name: "",
    vendor: "ERPNEXT",
    environment: "SANDBOX",
    base_url: "",
    auth_method: "API_KEY",
    contract_version: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newId, setNewId] = useState<string | null>(null);

  function set(k: keyof typeof f, v: string) {
    setF((cur) => ({ ...cur, [k]: v }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const receipt = await api.post<MutationReceipt>(`${ROOT}/instances`, {
        idempotency_key: newIdempotencyKey(),
        instance_name: f.instance_name.trim(),
        vendor: f.vendor.trim(),
        environment: f.environment.trim(),
        base_url: f.base_url.trim(),
        auth_method: f.auth_method.trim(),
        contract_version: f.contract_version.trim() || null,
        site_id: siteId,
      });
      setNewId(receipt.aggregate_id);
      onRegistered();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Register failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Register ERP instance" />
      <form onSubmit={submit} className="grid grid-cols-3 gap-4 mt-3">
        <Field label="Instance name" required>
          <Input value={f.instance_name} onChange={(e) => set("instance_name", e.target.value)} required />
        </Field>
        <Field label="Vendor" required>
          <Input value={f.vendor} onChange={(e) => set("vendor", e.target.value)} required />
        </Field>
        <Field label="Environment" required>
          <Input value={f.environment} onChange={(e) => set("environment", e.target.value)} required />
        </Field>
        <Field label="Base URL" required>
          <Input value={f.base_url} onChange={(e) => set("base_url", e.target.value)} required />
        </Field>
        <Field label="Auth method" required>
          <Input value={f.auth_method} onChange={(e) => set("auth_method", e.target.value)} required />
        </Field>
        <Field label="Contract version">
          <Input value={f.contract_version} onChange={(e) => set("contract_version", e.target.value)} />
        </Field>
        <div style={{ gridColumn: "1 / -1" }}>
          {error && <p className="error-text mb-2">{error}</p>}
          {newId && (
            <Banner tone="ok" title="Instance registered">
              Instance ID <span className="tabular">{newId}</span>
            </Banner>
          )}
          <Button type="submit" variant="primary" disabled={busy || !f.instance_name.trim() || !f.base_url.trim()}>
            {busy ? "Registering…" : "Register instance"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function InstanceCard({ canAdmin, instanceListVersion }: { canAdmin: boolean; instanceListVersion: number }) {
  const instances = useErpInstances(instanceListVersion);
  const [id, setId] = useState("");
  const [instance, setInstance] = useState<ErpInstance | null>(null);
  const [caps, setCaps] = useState<Record<string, unknown> | null>(null);
  const [sla, setSla] = useState<Record<string, unknown> | null>(null);
  const [dq, setDq] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [acceptanceRef, setAcceptanceRef] = useState("");

  async function load(target = id) {
    if (!target.trim()) return;
    setError(null);
    try {
      const inst = await api.get<ErpInstance>(`${ROOT}/instances/${target.trim()}`);
      setInstance(inst);
      setId(target.trim());
      const [c, s, d] = await Promise.all([
        api.get<Record<string, unknown>>(`${ROOT}/instances/${target.trim()}/capabilities`).catch(() => null),
        api.get<Record<string, unknown>>(`${ROOT}/instances/${target.trim()}/sla-metrics`).catch(() => null),
        api.get<Record<string, unknown>>(`${ROOT}/instances/${target.trim()}/data-quality-metrics`).catch(() => null),
      ]);
      setCaps(c);
      setSla(s);
      setDq(d);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
      setInstance(null);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="ERP instance" />
      <form
        onSubmit={(e) => {
          e.preventDefault();
          load();
        }}
        className="flex flex-wrap items-end gap-3 mt-3"
      >
        <div style={{ minWidth: 260, maxWidth: 360, width: "100%" }}>
          <EntityPickerField
            label="ERP instance"
            value={id}
            onChange={setId}
            options={instances.options}
            status={instances.status}
            kind="ERP instance"
          />
        </div>
        <Button type="submit" variant="secondary" disabled={!id.trim()}>
          <Icon name="search" /> Look up
        </Button>
      </form>
      {error && <p className="error-text mt-3">{error}</p>}

      {instance && (
        <div className="mt-4">
          <FactGrid>
            <Fact label="Name">{instance.instance_name}</Fact>
            <Fact label="Vendor">{instance.vendor}</Fact>
            <Fact label="Environment">{instance.environment}</Fact>
            <Fact label="Status">
              <StatePill state={instance.status === "ACTIVE" ? "accepted" : "stale"} icon="refresh">
                {instance.status}
              </StatePill>
            </Fact>
            <Fact label="Validated">
              {instance.validated ? (
                <StatePill state="accepted" icon="check-circle">Yes</StatePill>
              ) : (
                <StatePill state="missing" icon="alert-triangle">No</StatePill>
              )}
            </Fact>
            <Fact label="Record version">{instance.version}</Fact>
          </FactGrid>

          {caps && <div className="mt-3"><JsonPanel title="Capabilities" value={caps} /></div>}
          {sla && <div className="mt-3"><JsonPanel title="SLA metrics" value={sla} /></div>}
          {dq && <div className="mt-3"><JsonPanel title="Data-quality metrics" value={dq} /></div>}

          {canAdmin && !instance.validated && (
            <div className="mt-3">
              <WorkflowActionButton
                label="Validate connector"
                title={`Validate - ${instance.instance_name}`}
                summary="Certifies a custom connector against an acceptance profile before it may post any write."
                confirmLabel="Validate"
                variant="primary"
                onDone={() => load()}
                extraFields={
                  <Field label="Acceptance reference" required>
                    <Input value={acceptanceRef} onChange={(e) => setAcceptanceRef(e.target.value)} />
                  </Field>
                }
                disabled={!acceptanceRef.trim()}
                onConfirm={() =>
                  api.post<MutationReceipt>(`${ROOT}/instances/${instance.id}/validate`, {
                    idempotency_key: newIdempotencyKey(),
                    instance_id: instance.id,
                    expected_version: instance.version,
                    acceptance_reference: acceptanceRef.trim(),
                  })
                }
              />
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function CommandCard({ canAdmin }: { canAdmin: boolean }) {
  const [id, setId] = useState("");
  const [cmd, setCmd] = useState<IntegrationCommand | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load(target = id) {
    if (!target.trim()) return;
    setError(null);
    try {
      setCmd(await api.get<IntegrationCommand>(`${ROOT}/commands/${target.trim()}`));
      setId(target.trim());
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
      setCmd(null);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Integration command queue" />
      <form
        onSubmit={(e) => {
          e.preventDefault();
          load();
        }}
        className="flex flex-wrap items-end gap-3 mt-3"
      >
        <Field label="Command ID">
          <Input value={id} onChange={(e) => setId(e.target.value)} style={{ minWidth: 200, maxWidth: 320, width: "100%" }} />
        </Field>
        <Button type="submit" variant="secondary" disabled={!id.trim()}>
          <Icon name="search" /> Look up
        </Button>
      </form>
      {error && <p className="error-text mt-3">{error}</p>}

      {cmd && (
        <div className="mt-4">
          <div className="flex items-center gap-3 mb-3">
            <span className="font-semibold">{cmd.command_type}</span>
            <WorkflowStatePill state={cmd.state} />
          </div>
          <FactGrid>
            <Fact label="Attempts">{cmd.attempt_count}</Fact>
            <Fact label="Last error category">
              {cmd.last_error_category ? (
                <StatePill state="failed" icon="alert-triangle">{cmd.last_error_category}</StatePill>
              ) : (
                "—"
              )}
            </Fact>
            <Fact label="Record version">{cmd.version}</Fact>
            <IdFact label="Command ID" value={cmd.id} />
          </FactGrid>
          {cmd.external_reference && (
            <div className="mt-3"><JsonPanel title="External reference" value={cmd.external_reference} /></div>
          )}

          {canAdmin && (
            <div className="flex flex-wrap gap-2 mt-3">
              <WorkflowActionButton
                label="Dispatch"
                title={`Dispatch - ${cmd.command_type}`}
                summary="Sends the queued command to the ERP now."
                confirmLabel="Dispatch"
                variant="primary"
                onDone={() => load()}
                onConfirm={() =>
                  api.post<MutationReceipt>(`${ROOT}/commands/${cmd.id}/dispatch`, {
                    idempotency_key: newIdempotencyKey(),
                    command_id: cmd.id,
                  })
                }
              />
              <WorkflowActionButton
                label="Retry"
                title={`Retry - ${cmd.command_type}`}
                summary="Replays the exact original payload. Only state and next-attempt time change."
                confirmLabel="Retry"
                reason="required"
                onDone={() => load()}
                onConfirm={(reason) =>
                  api.post<MutationReceipt>(`${ROOT}/commands/${cmd.id}/retry`, {
                    idempotency_key: newIdempotencyKey(),
                    command_id: cmd.id,
                    reason,
                  })
                }
              />
              <WorkflowActionButton
                label="Cancel"
                title={`Cancel - ${cmd.command_type}`}
                summary="Cancels a pending command. Dispatched or succeeded commands can never be cancelled."
                confirmLabel="Cancel command"
                variant="danger"
                reason="required"
                onDone={() => load()}
                onConfirm={(reason) =>
                  api.post<MutationReceipt>(`${ROOT}/commands/${cmd.id}/cancel`, {
                    idempotency_key: newIdempotencyKey(),
                    command_id: cmd.id,
                    reason,
                  })
                }
              />
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function MappingCard({ instanceListVersion }: { instanceListVersion: number }) {
  const instances = useErpInstances(instanceListVersion);
  const [erpInstanceId, setErpInstanceId] = useState("");
  const [entityType, setEntityType] = useState("material");
  const [internalId, setInternalId] = useState("");
  const [externalId, setExternalId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mappingId, setMappingId] = useState<string | null>(null);

  async function propose(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const receipt = await api.post<MutationReceipt>(`${ROOT}/mappings`, {
        idempotency_key: newIdempotencyKey(),
        erp_instance_id: erpInstanceId.trim(),
        entity_type: entityType.trim(),
        internal_id: internalId.trim() || null,
        external_id: externalId.trim(),
      });
      setMappingId(receipt.aggregate_id);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Propose failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Master-data mapping" />
      <form onSubmit={propose} className="grid grid-cols-2 gap-4 mt-3">
        <EntityPickerField
          label="ERP instance"
          required
          value={erpInstanceId}
          onChange={setErpInstanceId}
          options={instances.options}
          status={instances.status}
          kind="ERP instance"
        />
        <Field label="Entity type" required>
          <Input value={entityType} onChange={(e) => setEntityType(e.target.value)} required />
        </Field>
        <Field label="Internal ID">
          <Input value={internalId} onChange={(e) => setInternalId(e.target.value)} />
        </Field>
        <Field label="External ID" required>
          <Input value={externalId} onChange={(e) => setExternalId(e.target.value)} required />
        </Field>
        <div style={{ gridColumn: "1 / -1" }}>
          {error && <p className="error-text mb-2">{error}</p>}
          {mappingId && (
            <Banner tone="ok" title="Mapping proposed">
              Mapping ID <span className="tabular">{mappingId}</span> - awaiting approval.
            </Banner>
          )}
          <Button type="submit" variant="secondary" disabled={busy || !erpInstanceId.trim() || !externalId.trim()}>
            {busy ? "Proposing…" : "Propose mapping"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function ReconciliationCard({ instanceListVersion }: { instanceListVersion: number }) {
  const instances = useErpInstances(instanceListVersion);
  const [erpInstanceId, setErpInstanceId] = useState("");
  const [scope, setScope] = useState("inventory");
  const [reconciliationType, setReconciliationType] = useState("QUANTITY");
  const [cutoffAt, setCutoffAt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const receipt = await api.post<MutationReceipt>(`${ROOT}/reconciliation-runs`, {
        idempotency_key: newIdempotencyKey(),
        erp_instance_id: erpInstanceId.trim(),
        scope: scope.trim(),
        reconciliation_type: reconciliationType.trim(),
        cutoff_at: cutoffAt ? new Date(cutoffAt).toISOString() : new Date().toISOString(),
      });
      setRunId(receipt.aggregate_id);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad>
      <CardHeader title="Reconciliation run" />
      <form onSubmit={create} className="grid grid-cols-2 gap-4 mt-3">
        <EntityPickerField
          label="ERP instance"
          required
          value={erpInstanceId}
          onChange={setErpInstanceId}
          options={instances.options}
          status={instances.status}
          kind="ERP instance"
        />
        <Field label="Scope" required>
          <Input value={scope} onChange={(e) => setScope(e.target.value)} required />
        </Field>
        <Field label="Reconciliation type" required>
          <Input value={reconciliationType} onChange={(e) => setReconciliationType(e.target.value)} required />
        </Field>
        <Field label="Cutoff at" hint="Defaults to now.">
          <Input type="datetime-local" value={cutoffAt} onChange={(e) => setCutoffAt(e.target.value)} />
        </Field>
        <div style={{ gridColumn: "1 / -1" }}>
          {error && <p className="error-text mb-2">{error}</p>}
          {runId && (
            <Banner tone="ok" title="Reconciliation run created">
              Run ID <span className="tabular">{runId}</span>. Differences are recorded against this run;
              complete it when the comparison is done.
            </Banner>
          )}
          <Button type="submit" variant="secondary" disabled={busy || !erpInstanceId.trim()}>
            {busy ? "Creating…" : "Create reconciliation run"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
