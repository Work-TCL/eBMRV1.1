"use client";

import { useEffect, useRef, useState } from "react";
import { api, hasPermission, newIdempotencyKey, pagedFetcher, type Me, type MutationReceipt, type Paged } from "@/lib/api";
import { useApiResource, useMe, useSiteId } from "@/lib/hooks";
import { useCommand } from "@/components/shared/RecordDetailShell";
import { Fact, OpsRecordPage, type OpsRecordConfig } from "@/components/shared/OpsRecordPage";
import { KeyValueRows, buildKvObject, type KvRow } from "@/components/shared/RepeatableFields";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Field } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Input } from "@/components/ui/Input";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { EmptyState, Table } from "@/components/ui/Table";
import { humanizeLabel } from "@/lib/format";

const CLEANING_TYPES = ["routine", "product_changeover", "campaign_end", "deep_clean", "sanitization", "manual", "CIP", "COP"];

/** Fallback raw-id display for a `Fact` whose resolved label isn't available (shouldn't normally
 * happen now that the backend resolves these, but keeps the UI honest rather than hiding the field
 * entirely). Plain inline span, not `IdFact`'s own `.fact` wrapper -- `Fact` already provides that, and
 * nesting a second one inside its `fact-v` would put a `div` inside a `span`. */
function RawId({ value }: { value: string | null }) {
  return <span className="tabular fs-2" style={{ wordBreak: "break-all" }}>{value ?? "—"}</span>;
}

// Document 39's own 7-op API list has no create operation for the cleaning *procedure* itself (only
// the *execution* that runs against one) — POST /cleaning/v1/procedure-versions was added 2026-10-08,
// project-owner-directed, same gap class as SG-203 (sterilization cycle profile): asked directly who
// should author a procedure and chose Admin + QA Reviewer, direct-to-RELEASED (no draft stage), same
// "who defines vs who executes" split as sterilization's own canCreateCycleProfile.
const canCreateProcedureVersion = (me: Me | null) => hasPermission(me, "cleaning_procedure_version.create");

// Matches app/modules/equipment/cleaning_router.py::_procedure_summary_dict.
interface ProcedureVersion {
  id: string;
  procedure_number: string;
  version: number;
  cleaning_type: string;
  scope_equipment_id: string | null;
  scope_area_id: string | null;
  state: string;
}

function NewProcedureVersionModal({ siteId, onClose, onDone }: { siteId: string | null; onClose: () => void; onDone: () => void }) {
  const { busy, error, run } = useCommand(onDone);
  const [procedureNumber, setProcedureNumber] = useState("");
  const [versionNo, setVersionNo] = useState("1");
  const [cleaningType, setCleaningType] = useState(CLEANING_TYPES[0]);
  const [dirtyHoldLimit, setDirtyHoldLimit] = useState("");
  const [cleanHoldLimit, setCleanHoldLimit] = useState("");
  const [validationReference, setValidationReference] = useState("");
  const [disassemblyRequired, setDisassemblyRequired] = useState(false);
  const [agents, setAgents] = useState<KvRow[]>([]);
  const [steps, setSteps] = useState<KvRow[]>([]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    run(() =>
      api.post<MutationReceipt>("/cleaning/v1/procedure-versions", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        procedure_number: procedureNumber,
        version_no: Number(versionNo) || 1,
        cleaning_type: cleaningType,
        dirty_hold_limit_minutes: dirtyHoldLimit.trim() ? Number(dirtyHoldLimit) : null,
        clean_hold_limit_minutes: cleanHoldLimit.trim() ? Number(cleanHoldLimit) : null,
        validation_reference: validationReference || null,
        disassembly_required: disassemblyRequired,
        agents: agents.length ? buildKvObject(agents) : null,
        steps: steps.length ? buildKvObject(steps) : null,
      })
    );
  }

  return (
    <Modal open onClose={onClose} title="New cleaning procedure version" large>
      <form onSubmit={submit}>
        <p className="hint mb-3">
          Master data - created directly as RELEASED (no draft/review stage exists for this record,
          same shape as the Sterilization module&apos;s own cycle profile). Used as the &quot;Cleaning
          procedure version&quot; a cleaning execution (below) runs against.
        </p>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Procedure number" required hint="Unique together with version below, across all sites.">
            <Input value={procedureNumber} onChange={(e) => setProcedureNumber(e.target.value)} required autoFocus placeholder="CLN-PROC-002" />
          </Field>
          <Field label="Version no." required>
            <Input type="number" min={1} value={versionNo} onChange={(e) => setVersionNo(e.target.value)} required />
          </Field>
          <Field label="Cleaning type" required>
            <Select value={cleaningType} onChange={(e) => setCleaningType(e.target.value)}>
              {CLEANING_TYPES.map((t) => (
                <option key={t} value={t}>
                  {humanizeLabel(t)}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Dirty hold limit (minutes)" hint="Optional - how long equipment/area may stay dirty before CLN-FR exceeded.">
            <Input type="number" min={0} value={dirtyHoldLimit} onChange={(e) => setDirtyHoldLimit(e.target.value)} />
          </Field>
          <Field label="Clean hold limit (minutes)" hint="Optional - how long it stays CLEAN before CLEAN_EXPIRED.">
            <Input type="number" min={0} value={cleanHoldLimit} onChange={(e) => setCleanHoldLimit(e.target.value)} />
          </Field>
          <Field label="Validation reference" hint="Optional - e.g. a cleaning validation protocol ID.">
            <Input value={validationReference} onChange={(e) => setValidationReference(e.target.value)} />
          </Field>
        </div>
        <Field label="Disassembly required" hint="Whether this procedure requires disassembly verification on complete.">
          <Select value={disassemblyRequired ? "true" : "false"} onChange={(e) => setDisassemblyRequired(e.target.value === "true")}>
            <option value="false">No</option>
            <option value="true">Yes</option>
          </Select>
        </Field>
        <KeyValueRows
          label="Agents"
          hint='Optional - cleaning agents this procedure uses, e.g. "agent" → "IPA 70%".'
          value={agents}
          onChange={setAgents}
        />
        <KeyValueRows
          label="Steps"
          hint='Optional - free-form key/value only, e.g. "1" → "RINSE".'
          value={steps}
          onChange={setSteps}
        />

        {error && <p className="error-text mb-2 mt-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !siteId || !procedureNumber.trim()}>
            {busy ? "Saving…" : "Create procedure"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ProcedureVersionListCard({
  procedures,
  loading,
  onOpen,
}: {
  procedures: ProcedureVersion[] | null;
  loading: boolean;
  onOpen: (id: string) => void;
}) {
  return (
    <Card pad className="mb-4">
      <CardHeader title="Cleaning procedure versions" meta="" />
      {loading ? (
        <p className="hint">Loading…</p>
      ) : !procedures || procedures.length === 0 ? (
        <EmptyState>No cleaning procedure versions yet - use &quot;New cleaning procedure version&quot; above to add one.</EmptyState>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Procedure number</th>
              <th>Version</th>
              <th>Cleaning type</th>
              <th>State</th>
            </tr>
          </thead>
          <tbody>
            {procedures.map((p) => (
              <tr key={p.id} onClick={() => onOpen(p.id)} style={{ cursor: "pointer" }}>
                <td className="fs-2">{p.procedure_number}</td>
                <td className="tabular fs-2">v{p.version}</td>
                <td className="fs-2">{p.cleaning_type}</td>
                <td>
                  <StatePill state={p.state === "RELEASED" ? "accepted" : "unknown"} icon={p.state === "RELEASED" ? "check-circle" : "slash-circle"}>
                    {p.state}
                  </StatePill>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function ProcedureVersionDetailModal({ procedureId, onClose }: { procedureId: string; onClose: () => void }) {
  const [result, setResult] = useState<unknown>(undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<unknown>(`/cleaning/v1/procedure-versions/${encodeURIComponent(procedureId)}`)
      .then((r) => {
        if (!cancelled) setResult(r);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Load failed");
      });
    return () => {
      cancelled = true;
    };
  }, [procedureId]);

  // Backend now resolves site_code/site_name alongside the raw site_id (same pattern as recipe_master/
  // batch_execution's detail dicts) -- drop the raw id from display so the modal shows the human name,
  // not a UUID nobody can read.
  const displayValue =
    result && typeof result === "object" && !Array.isArray(result)
      ? Object.fromEntries(Object.entries(result as Record<string, unknown>).filter(([key]) => key !== "site_id"))
      : result;

  return (
    <Modal open onClose={onClose} title="Cleaning procedure version" large>
      {error && <p className="error-text">{error}</p>}
      {result !== undefined ? <JsonPanel title="Procedure version" value={displayValue} /> : !error && <p className="hint">Loading…</p>}
    </Modal>
  );
}

interface CleaningExecution {
  id: string;
  site_id: string;
  equipment_id: string | null;
  equipment_code: string | null;
  area_id: string | null;
  area_code: string | null;
  procedure_version_id: string;
  procedure_number: string | null;
  procedure_version_no: number | null;
  batch_context: Record<string, unknown> | null;
  state: string;
  dirty_since: string;
  clean_until: string | null;
  agents_used: Record<string, unknown> | null;
  inspection_result: Record<string, unknown> | null;
  performer_user_id: string | null;
  performer_username: string | null;
  performer_full_name: string | null;
  reviewer_user_id: string | null;
  reviewer_username: string | null;
  reviewer_full_name: string | null;
  verification_result: string | null;
  dirty_hold_exceeded: boolean;
  requires_deviation: boolean;
  protection_state: Record<string, unknown> | null;
  version: number;
}

// cleaning_execution.create / .complete (Document 39) — Admin, Operator, QA Reviewer, Sanitation
// Operator per scripts/seed.py. Audit finding 2026-09-18: this previously included Supervisor (who
// holds no cleaning_execution.* grant — silent 403) and omitted QA Reviewer (who does hold it — hidden
// feature). Also removed a stray `|| canMaintainEquipment(me)` on the create gate, which wrongly let
// Maintenance Technician (whose only grant is equipment_asset.maintain) start a cleaning execution.
const canOperate = (me: Me | null) => hasPermission(me, "cleaning_execution.create");
const canVerify = (me: Me | null) => hasPermission(me, "cleaning_execution.verify");

const config: OpsRecordConfig<CleaningExecution> = {
  title: "Cleaning executions",
  subtitle: "Equipment cleaning records: steps, agents, completion and independent verification.",
  idLabel: "Cleaning execution ID",
  apiRoot: "/cleaning/v1/executions",
  create: {
    label: "Start cleaning execution",
    can: canOperate,
    path: "/cleaning/v1/executions",
    fields: [
      { name: "procedure_version_id", label: "Cleaning procedure version", type: "cleaningProcedureVersionSelect", required: true },
      { name: "equipment_id", label: "Equipment", type: "equipmentSelect", hint: "Or leave blank and set an area." },
      { name: "area_id", label: "Area", type: "areaSelect" },
      { name: "batch_context", label: "Batch context", type: "kv", hint: "Optional - what batch/product this cleaning relates to." },
    ],
    buildBody: (v, siteId) => ({
      site_id: siteId,
      procedure_version_id: v.procedure_version_id,
      equipment_id: v.equipment_id,
      area_id: v.area_id,
      batch_context: Object.keys((v.batch_context as object) ?? {}).length ? v.batch_context : null,
    }),
  },
  stateOf: (r) => r.state,
  numberOf: (r) => `Cleaning ${r.id.slice(0, 8)}…`,
  facts: (r) => (
    <>
      <Fact label="Verification result">
        {r.verification_result ? (
          <StatePill state={r.verification_result === "pass" ? "accepted" : "failed"} icon={r.verification_result === "pass" ? "check-circle" : "x"}>
            {r.verification_result}
          </StatePill>
        ) : (
          "—"
        )}
      </Fact>
      <Fact label="Dirty hold exceeded">
        {r.dirty_hold_exceeded ? <StatePill state="failed" icon="alert-triangle">Yes</StatePill> : "No"}
      </Fact>
      <Fact label="Requires deviation">{r.requires_deviation ? "Yes" : "No"}</Fact>
      <Fact label="Clean until">{r.clean_until ? new Date(r.clean_until).toLocaleString() : "—"}</Fact>
      <Fact label="Record version">{r.version}</Fact>
      <Fact label="Procedure version">
        {r.procedure_number ? `${r.procedure_number} v${r.procedure_version_no}` : <RawId value={r.procedure_version_id} />}
      </Fact>
      {r.equipment_id && <Fact label="Equipment">{r.equipment_code ?? <RawId value={r.equipment_id} />}</Fact>}
      {r.area_id && <Fact label="Area">{r.area_code ?? <RawId value={r.area_id} />}</Fact>}
      <Fact label="Performer">
        {r.performer_full_name ? `${r.performer_full_name} (${r.performer_username})` : r.performer_user_id ? <RawId value={r.performer_user_id} /> : "—"}
      </Fact>
      <Fact label="Reviewer">
        {r.reviewer_full_name ? `${r.reviewer_full_name} (${r.reviewer_username})` : r.reviewer_user_id ? <RawId value={r.reviewer_user_id} /> : "—"}
      </Fact>
      {r.batch_context && Object.keys(r.batch_context).length > 0 && (
        <Fact label="Batch context">
          {Object.entries(r.batch_context)
            .map(([k, v]) => `${k}: ${v}`)
            .join(", ")}
        </Fact>
      )}
      {r.agents_used && Object.keys(r.agents_used).length > 0 && (
        <Fact label="Agents used">
          {Object.entries(r.agents_used)
            .map(([k, v]) => `${k}: ${v}`)
            .join(", ")}
        </Fact>
      )}
      {r.inspection_result && Object.keys(r.inspection_result).length > 0 && (
        <Fact label="Inspection result">
          {Object.entries(r.inspection_result)
            .map(([k, v]) => `${k}: ${v}`)
            .join(", ")}
        </Fact>
      )}
    </>
  ),
  transitions: [
    {
      key: "steps",
      label: "Record step",
      // cleaning_commands.py::record_cleaning_step() only accepts state === "CLEANING" (InvalidTransitionError
      // otherwise) -- hide the button once the backend would reject it anyway, rather than surfacing the
      // rejection as an error after the user clicks.
      show: (r) => r.state === "CLEANING",
      can: canOperate,
      summary: "Records one executed cleaning step with the agents used.",
      fields: [
        { name: "step_code", label: "Step code", required: true, placeholder: "e.g. RINSE, SCRUB, DRY" },
        { name: "step_result", label: "Step result", placeholder: "e.g. done" },
        { name: "agents_used", label: "Agents used", type: "kv", hint: 'Cleaning agents applied, e.g. "agent" → "IPA 70%".' },
        { name: "disassembly_verified", label: "Disassembly verified", type: "bool" },
      ],
      buildBody: (r, v) => ({
        execution_id: r.id,
        expected_version: r.version,
        step: { step_code: v.step_code, result: v.step_result || undefined },
        agents_used: Object.keys((v.agents_used as object) ?? {}).length ? v.agents_used : null,
        disassembly_verified: v.disassembly_verified === null ? null : v.disassembly_verified === "true",
      }),
    },
    {
      key: "complete",
      label: "Complete (sign)",
      // cleaning_commands.py::complete_cleaning() only accepts state === "CLEANING" too (same guard as
      // "steps" above).
      show: (r) => r.state === "CLEANING",
      signed: true,
      challengeAction: "complete",
      variant: "primary",
      can: canOperate,
      summary: "Attests the cleaning is complete and the previous batch identity has been removed.",
      fields: [
        { name: "previous_batch_identity_removed", label: "Previous batch identity removed", required: true, type: "bool" },
        { name: "inspection_result", label: "Inspection result", type: "kv" },
      ],
      buildBody: (r, v) => ({
        execution_id: r.id,
        expected_version: r.version,
        previous_batch_identity_removed: v.previous_batch_identity_removed === "true",
        inspection_result: Object.keys((v.inspection_result as object) ?? {}).length ? v.inspection_result : null,
      }),
    },
    {
      key: "verify",
      label: "Verify (sign)",
      // cleaning_commands.py::verify_cleaning() only accepts state === "CLEANING_VERIFICATION"
      // (InvalidTransitionError otherwise) -- once verified (CLEAN/HOLD), hide the button rather than
      // let the user hit a rejected-transition error.
      show: (r) => r.state === "CLEANING_VERIFICATION",
      signed: true,
      challengeAction: "verify",
      variant: "success",
      can: canVerify,
      summary: "Independent verification of the cleaning result (SoD - the verifier is not the performer).",
      fields: [
        {
          name: "result", label: "Result", required: true, type: "select",
          options: [{ value: "pass", label: "Pass" }, { value: "fail", label: "Fail" }],
        },
      ],
      buildBody: (r, v) => ({ execution_id: r.id, expected_version: r.version, result: v.result }),
    },
  ],
};

function executionColumns(onOpen: (id: string) => void): DataTableColumn<CleaningExecution>[] {
  return [
    {
      key: "id",
      header: "Cleaning execution",
      sortable: false,
      render: (r) => <span className="fs-2 font-semibold">Cleaning {r.id.slice(0, 8)}…</span>,
    },
    { key: "state", header: "State", sortable: true, render: (r) => <WorkflowStatePill state={r.state} /> },
    {
      key: "verification_result",
      header: "Verification",
      render: (r) =>
        r.verification_result ? (
          <StatePill state={r.verification_result === "pass" ? "accepted" : "failed"} icon={r.verification_result === "pass" ? "check-circle" : "x"}>
            {r.verification_result}
          </StatePill>
        ) : (
          "—"
        ),
    },
    {
      key: "dirty_since",
      header: "Dirty since",
      sortable: true,
      render: (r) => <span className="tabular fs-2">{new Date(r.dirty_since).toLocaleString()}</span>,
    },
    {
      key: "open",
      header: "",
      align: "right",
      // A dedicated button alongside the row's own onRowClick — a row that merely looks clickable is
      // easy to miss; a plain button is not.
      render: (r) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={(e) => {
            e.stopPropagation();
            onOpen(r.id);
          }}
        >
          Open
        </Button>
      ),
    },
  ];
}

function ExecutionListCard({ reloadToken, onOpen }: { reloadToken: number; onOpen: (id: string) => void }) {
  const fetchExecutions = pagedFetcher<CleaningExecution>("/cleaning/v1/executions");
  return (
    <Card pad className="mb-4">
      <CardHeader title="Cleaning executions" />
      <DataTable
        columns={executionColumns(onOpen)}
        fetchPage={fetchExecutions}
        rowKey={(r) => r.id}
        searchPlaceholder="Search by state…"
        emptyMessage='No cleaning executions yet - use "Start cleaning execution" above to add one.'
        defaultSort={{ by: "created_at", dir: "desc" }}
        onRowClick={(r) => onOpen(r.id)}
        reloadToken={reloadToken}
      />
    </Card>
  );
}

export default function CleaningPage() {
  const { me, loading: meLoading } = useMe();
  const { siteId } = useSiteId();
  const [reloadToken, setReloadToken] = useState(0);
  const [newProcedureOpen, setNewProcedureOpen] = useState(false);
  const [openProcedureId, setOpenProcedureId] = useState<string | null>(null);
  const {
    data: procedureVersionsPage,
    loading: proceduresLoading,
    reload: reloadProcedures,
  } = useApiResource<Paged<ProcedureVersion>>("/cleaning/v1/procedure-versions?state=&page_size=100");
  const procedureVersions = procedureVersionsPage?.items ?? null;

  // Deep link from the Workflow Actions bell (`?execution_id=<uuid>`) -- same `window.location.search`
  // shape as release/recipe-master's own deep links. OpsRecordPage's `openRecord` (the "look up by id
  // and open the detail modal" function it hands to `afterHeader`) isn't itself stable across renders,
  // so it's captured in a ref during render rather than read from a dependency array; by the time this
  // mount-only effect runs, the ref is already populated (afterHeader runs during the child's render,
  // which commits before this effect fires).
  const executionOpenerRef = useRef<(id: string) => void>(() => {});
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const linkedExecutionId = params.get("execution_id");
    if (linkedExecutionId) executionOpenerRef.current(linkedExecutionId);
  }, []);

  return (
    <>
      <OpsRecordPage
        config={config}
        collapseCreate
        detailInModal
        hideLookup
        headerAction={
          meLoading ? (
            <Skeleton width={230} height={36} radius="var(--radius-md)" />
          ) : (
            canCreateProcedureVersion(me) && (
              <Button variant="secondary" onClick={() => setNewProcedureOpen(true)}>
                <Icon name="plus" /> New cleaning procedure version
              </Button>
            )
          )
        }
        afterHeader={(openRecord) => {
          executionOpenerRef.current = openRecord;
          return (
            <>
              <ProcedureVersionListCard
                procedures={procedureVersions}
                loading={proceduresLoading}
                onOpen={setOpenProcedureId}
              />
              <ExecutionListCard reloadToken={reloadToken} onOpen={openRecord} />
            </>
          );
        }}
        onCreated={() => setReloadToken((n) => n + 1)}
      />
      {newProcedureOpen && (
        <NewProcedureVersionModal
          siteId={siteId}
          onClose={() => setNewProcedureOpen(false)}
          onDone={() => {
            setNewProcedureOpen(false);
            reloadProcedures();
          }}
        />
      )}
      {openProcedureId && (
        <ProcedureVersionDetailModal procedureId={openProcedureId} onClose={() => setOpenProcedureId(null)} />
      )}
    </>
  );
}
