"use client";

import { useEffect, useState } from "react";
import { api, clientPagedFetcher, formatDateTime, holdsAnyRole, newIdempotencyKey } from "@/lib/api";
import { useApiResource, useEntityOptions, useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table } from "@/components/ui/Table";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Banner } from "@/components/ui/Banner";
import { KpiRow, KpiTile } from "@/components/ui/KpiTile";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { RepeatableRows, buildRepeatArray, type RepeatRow, type RepeatSubField } from "@/components/shared/RepeatableFields";

function isNumericParameter(dataType: string): boolean {
  return ["numeric", "decimal", "number", "float", "integer"].includes(dataType.toLowerCase());
}
function isBooleanParameter(dataType: string): boolean {
  return ["bool", "boolean"].includes(dataType.toLowerCase());
}

interface GxpBatch {
  batch_id: string;
  site_id: string;
  batch_number: string;
  product_version_id: string;
  product_name: string | null;
  product_code: string | null;
  recipe_version_id: string;
  recipe_code: string | null;
  recipe_version_no: number | null;
  recipe_vault_object_id: string | null;
  execution_snapshot_id: string | null;
  target_qty: string;
  target_uom: string;
  state: string;
  version: number;
  production_order_ref: string | null;
  issued_at: string | null;
  started_at: string | null;
}

interface BatchStep {
  step_id: string;
  batch_id: string;
  recipe_step_code: string;
  required_role_code: string | null;
  state: string;
  version: number;
  assigned_subject_id: string | null;
  assigned_full_name: string | null;
  assigned_username: string | null;
  started_at: string | null;
  completed_at: string | null;
}

// GET /batches/v1/{id}/execution-view's "blockers" — service.py::get_execution_view() emits one of
// these per step still stuck on a predecessor. A designed list, not a JSON dump (matches the DDCP
// readiness panel's own {code,message}-list convention — components/ddcp/ReadinessPanel.tsx).
interface ExecutionBlocker {
  step_id: string;
  recipe_step_code: string;
  reason: string;
}

// BAT-FR-009 form definition (Document 10's gxp_recipe_parameter, read through the execution view).
interface StepParameter {
  parameter_code: string;
  data_type: string;
  uom: string | null;
  target_value: string | null;
  min_value: string | null;
  max_value: string | null;
  precision_digits: number | null;
  required: boolean;
}

// gxp_step_result (SG-047 partial resolution) — a recorded value against one of the parameters above.
interface StepResultRow {
  result_id: string;
  parameter_code: string;
  data_type: string;
  value_numeric: string | null;
  value_text: string | null;
  value_bool: boolean | null;
  uom: string | null;
  received_at: string | null;
  signature_id: string | null;
}

// Recipe-declared evidence requirement (Document 10) — upload itself isn't built yet (SG-047), but the
// requirement is real recipe content and worth showing in step detail.
interface StepEvidenceRequirement {
  evidence_type: string;
  required_count: number;
  allowed_mime_types: string | null;
  retention_class: string | null;
}

// "Step detail" — BAT-FR-005's "immutable parent instruction" + Document 11 §9's execution-UI field list
// (instruction, section, dependencies), read from the live recipe graph (2026-09-09, client-requested).
interface StepDetail {
  step_type: string | null;
  instruction_text: string | null;
  is_critical: boolean | null;
  sequence_hint: number | null;
  section_code: string | null;
  section_name: string | null;
  predecessor_codes: string[];
  successor_codes: string[];
  evidence_requirements: StepEvidenceRequirement[];
}

// Active step-level hold (BAT-FR-020 step scope, SG-047 further partial resolution).
interface ActiveHold {
  reason: string;
  held_at: string | null;
}

interface ExecutionView {
  batch: GxpBatch;
  steps: BatchStep[];
  blockers: ExecutionBlocker[];
  parameters_by_step_id: Record<string, StepParameter[]>;
  results_by_step_id: Record<string, StepResultRow[]>;
  step_detail_by_step_id: Record<string, StepDetail>;
  active_hold_by_step_id: Record<string, ActiveHold>;
}

// GET /products/v1/business-ids — one row per Product Master Business ID (its latest version).
interface ProductBusinessIdOption {
  product_business_id: string;
  name: string;
  version_no: number;
  lifecycle_state: string;
}
// GET /products/v1/{business_id}/versions — every version of one Business ID.
interface ProductVersionOption {
  product_version_id: string;
  product_business_id: string;
  version_no: number;
  name: string;
  lifecycle_state: string;
}
// GET /recipes/v2/families — one row per Recipe Family, already scoped to its own product_business_id.
interface RecipeFamilyOption {
  recipe_family_id: string;
  recipe_code: string;
  product_business_id: string;
  has_released: boolean;
}
// GET /recipes/v2/{recipe_family_id}/versions
interface RecipeVersionOption {
  recipe_version_id: string;
  recipe_family_id: string;
  version_no: number;
  product_version_id: string;
  lifecycle_state: string;
}

// Matches app/modules/batch_execution/models.py::BATCH_STATES exactly -- the frontend previously used
// "in_progress"/"complete", which the backend never emits ("in_execution" is the real running state, and
// no terminal "complete" state exists yet, BAT-FR-026, SG-048 #026), so every batch-running condition
// below (the "In progress" KPI, hold/abort/per-step-start availability) silently never matched once a
// batch actually started.
const BATCH_STATES = ["planned", "issued", "in_execution", "on_hold", "aborted", "production_complete"];

type Action = "issue" | "start" | "hold" | "resume" | "abort";

const ACTION_LABEL: Record<Action, string> = {
  issue: "Issue batch",
  start: "Start batch",
  hold: "Hold",
  resume: "Resume",
  abort: "Abort",
};

// Matches app/modules/batch_execution/models.py::ALLOWED_TRANSITIONS exactly.
const ALLOWED_FROM: Record<string, Action[]> = {
  planned: ["issue"],
  issued: ["start", "abort"],
  in_execution: ["hold", "abort"],
  on_hold: ["resume", "abort"],
  production_complete: ["hold"],
};

export default function BatchExecutionPage() {
  const { me } = useMe();
  const { siteId, loading: siteLoading } = useSiteId();
  const [state, setState] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const list = useApiResource<{ batches: GxpBatch[]; on_hold_count: number }>(
    siteId ? `/batches/v1?site_id=${siteId}${state ? `&state=${state}` : ""}&_=${reloadToken}` : null
  );

  const canCreate = holdsAnyRole(me, ["Admin", "Supervisor"]);
  const batches = list.data?.batches ?? [];
  const active = batches.filter((b) => b.state === "in_execution").length;

  // batch_execution's own `state` (draft/issued/in_execution/production_complete/…) and release_scope's
  // state (draft_evaluation/eligible/blocked/released/rejected/hold, a separate module/Document 15) are
  // two different state machines on the same batch — "Production complete" here says nothing about
  // whether /release has actually released it. Looked up per batch via the new GET
  // /release/v1/scopes/batch/{id} (added resolving the "how do I know it's released" / "no Release
  // button anywhere" confusion — that batch had no visible release status at all before this).
  const [releaseStatus, setReleaseStatus] = useState<Record<string, string | null>>({});
  useEffect(() => {
    let cancelled = false;
    Promise.all(
      batches.map((b) =>
        api
          .get<{ state: string } | null>(`/release/v1/scopes/batch/${b.batch_id}`)
          .then((scope) => [b.batch_id, scope?.state ?? null] as const)
          .catch(() => [b.batch_id, null] as const)
      )
    ).then((entries) => {
      if (cancelled) return;
      setReleaseStatus(Object.fromEntries(entries));
    });
    return () => {
      cancelled = true;
    };
    // batches is a new array identity each fetch; comparing its ids keeps this from refetching every
    // unrelated re-render while still refetching whenever the actual batch set changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batches.map((b) => b.batch_id).join(",")]);

  // DataTable does its own fetch on every page/sort/search/reloadToken change rather than reading
  // `list.data` above — `list` refetches asynchronously on the same reloadToken bump, and relying on
  // its (possibly still-stale) data here would risk the table missing a refresh that already landed
  // in the KPI tiles.
  const fetchBatches = clientPagedFetcher<GxpBatch>(
    async () => {
      if (!siteId) return [];
      const result = await api.get<{ batches: GxpBatch[] }>(
        `/batches/v1?site_id=${siteId}${state ? `&state=${state}` : ""}`
      );
      return result.batches;
    },
    { searchText: (b) => `${b.batch_number} ${b.product_name ?? ""} ${b.product_code ?? ""}` }
  );

  const batchColumns: DataTableColumn<GxpBatch>[] = [
    {
      key: "batch_number",
      header: "Batch",
      sortable: true,
      render: (b) => <span className="font-semibold tabular">{b.batch_number}</span>,
    },
    {
      key: "product_name",
      header: "Product",
      render: (b) => (
        <span className="fs-2">{b.product_name ? `${b.product_name} (${b.product_code})` : b.product_version_id}</span>
      ),
    },
    {
      key: "target_qty",
      header: "Target",
      render: (b) => (
        <span className="tabular fs-2">
          {b.target_qty} {b.target_uom}
        </span>
      ),
    },
    { key: "state", header: "State", sortable: true, render: (b) => <WorkflowStatePill state={b.state} /> },
    {
      key: "release_status",
      header: "Release",
      render: (b) => {
        const rs = releaseStatus[b.batch_id];
        return rs ? <WorkflowStatePill state={rs} /> : <span className="text-muted fs-2">Not evaluated</span>;
      },
    },
    {
      key: "issued_at",
      header: "Issued",
      sortable: true,
      render: (b) => <span className="tabular fs-2">{b.issued_at ? formatDateTime(b.issued_at) : "—"}</span>,
    },
    {
      key: "started_at",
      header: "Started",
      sortable: true,
      render: (b) => <span className="tabular fs-2">{b.started_at ? formatDateTime(b.started_at) : "—"}</span>,
    },
    {
      key: "actions",
      header: "",
      render: (b) => (
        <div className="flex justify-end">
          <Button size="sm" variant="secondary" onClick={() => setSelected(b.batch_id)}>
            Open
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHead
        title="Batch execution"
        subtitle="The released-recipe execution record: issue, start, hold, resume and step progress."
        action={
          canCreate ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> New batch
            </Button>
          ) : undefined
        }
      />

      <KpiRow>
        <KpiTile label="Batches" icon="flask" value={batches.length} />
        <KpiTile label="In progress" icon="play" value={active} tone="ok" />
        <KpiTile
          label="On hold"
          icon="lock"
          value={list.data?.on_hold_count ?? 0}
          delta={(list.data?.on_hold_count ?? 0) > 0 ? "Execution stopped" : "None held"}
          tone={(list.data?.on_hold_count ?? 0) > 0 ? "critical" : "ok"}
        />
      </KpiRow>

      {list.error && (
        <Banner tone="critical" title="Could not load batches">
          {list.error}
        </Banner>
      )}

      <Card>
        <CardHeader
          title="Batches"
          meta={
            <span className="flex items-center gap-2">
              State
              <Select
                value={state}
                onChange={(e) => {
                  setState(e.target.value);
                  setReloadToken((n) => n + 1);
                }}
              >
                <option value="">All</option>
                {BATCH_STATES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </span>
          }
        />
        {/* Holding the table until the site resolves avoids one request racing the initial `siteId`
            load (empty string / null on first render) - DataTable does not watch `siteId` itself, so
            that request would never correct on its own; see RecordListPage's identical guard. */}
        {siteLoading ? (
          <p className="table-loading-row" style={{ padding: "var(--space-4)" }}>
            Loading…
          </p>
        ) : (
          <DataTable
            columns={batchColumns}
            fetchPage={fetchBatches}
            rowKey={(b) => b.batch_id}
            searchPlaceholder="Search by batch number or product…"
            emptyIcon="flask"
            emptyMessage="No batches at this site."
            defaultSort={{ by: "issued_at", dir: "desc" }}
            reloadToken={reloadToken}
          />
        )}
      </Card>

      {createOpen && (
        <CreateBatchModal
          siteId={siteId}
          onClose={() => setCreateOpen(false)}
          onDone={() => {
            setCreateOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
      {selected && (
        <ExecutionModal
          batchId={selected}
          onClose={() => setSelected(null)}
          onChanged={() => setReloadToken((n) => n + 1)}
        />
      )}
    </div>
  );
}

function CreateBatchModal({
  siteId,
  onClose,
  onDone,
}: {
  siteId: string | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [batchNumber, setBatchNumber] = useState("");
  const [productBusinessId, setProductBusinessId] = useState("");
  const [productVersionId, setProductVersionId] = useState("");
  const [recipeFamilyId, setRecipeFamilyId] = useState("");
  const [recipeVersionId, setRecipeVersionId] = useState("");
  const [targetQty, setTargetQty] = useState("");
  const [targetUom, setTargetUom] = useState("kg");
  const [orderRef, setOrderRef] = useState("");

  const { data: businessIds, loading: businessIdsLoading, error: businessIdsError } =
    useApiResource<ProductBusinessIdOption[]>("/products/v1/business-ids");
  const { data: productVersions, loading: productVersionsLoading } = useApiResource<ProductVersionOption[]>(
    productBusinessId ? `/products/v1/${encodeURIComponent(productBusinessId)}/versions` : null
  );
  const { data: recipeFamilies, loading: recipeFamiliesLoading } =
    useApiResource<RecipeFamilyOption[]>("/recipes/v2/families");
  const { data: recipeVersions, loading: recipeVersionsLoading } = useApiResource<RecipeVersionOption[]>(
    recipeFamilyId ? `/recipes/v2/${recipeFamilyId}/versions` : null
  );

  const releasedProductVersions = (productVersions ?? []).filter((v) => v.lifecycle_state === "released");
  // A recipe family carries its own product_business_id (Document 10) — only show families authored
  // against the product picked above; a released version of one still has to match the exact
  // product_version_id picked (create_batch() checks recipe_version.product_version_id == product_version_id).
  const familiesForProduct = (recipeFamilies ?? []).filter((f) => f.product_business_id === productBusinessId);
  const releasedRecipeVersions = (recipeVersions ?? []).filter(
    (v) => v.lifecycle_state === "released" && v.product_version_id === productVersionId
  );

  return (
    <Modal open onClose={onClose} title="New batch" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!siteId) return;
          run(() =>
            api.post("/batches/v1", {
              idempotency_key: newIdempotencyKey(),
              site_id: siteId,
              batch_number: batchNumber,
              product_version_id: productVersionId,
              recipe_version_id: recipeVersionId,
              target_qty: targetQty,
              target_uom: targetUom,
              production_order_ref: orderRef || null,
            })
          );
        }}
      >
        <p className="hint mb-3">
          Both versions must be released - the backend refuses to create a batch against a draft product
          or recipe version. This creates the <code>gxp_batch</code> record every module - DDCP, QC,
          Packaging, Yield Reconciliation, QA Review, Release - now reads.
        </p>
        <Field label="Batch number" required>
          <Input value={batchNumber} onChange={(e) => setBatchNumber(e.target.value)} required autoFocus />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Product" required>
            <Select
              value={productBusinessId}
              onChange={(e) => {
                setProductBusinessId(e.target.value);
                setProductVersionId("");
                setRecipeFamilyId("");
                setRecipeVersionId("");
              }}
              disabled={businessIdsLoading}
              required
            >
              <option value="">
                {businessIdsError ? "Could not load products" : businessIdsLoading ? "Loading…" : "Select a product…"}
              </option>
              {(businessIds ?? []).map((b) => (
                <option key={b.product_business_id} value={b.product_business_id}>
                  {b.product_business_id} - {b.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Product version" required hint="Released versions only.">
            <Select
              value={productVersionId}
              onChange={(e) => {
                setProductVersionId(e.target.value);
                setRecipeVersionId("");
              }}
              disabled={!productBusinessId || productVersionsLoading}
              required
            >
              <option value="">
                {!productBusinessId
                  ? "—"
                  : productVersionsLoading
                    ? "Loading…"
                    : releasedProductVersions.length
                      ? "Select a released version…"
                      : "No released versions"}
              </option>
              {releasedProductVersions.map((v) => (
                <option key={v.product_version_id} value={v.product_version_id}>
                  v{v.version_no} - {v.name}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Recipe" required>
            <Select
              value={recipeFamilyId}
              onChange={(e) => {
                setRecipeFamilyId(e.target.value);
                setRecipeVersionId("");
              }}
              disabled={!productBusinessId || recipeFamiliesLoading}
              required
            >
              <option value="">
                {!productBusinessId
                  ? "—"
                  : recipeFamiliesLoading
                    ? "Loading…"
                    : familiesForProduct.length
                      ? "Select a recipe…"
                      : "No recipe families for this product"}
              </option>
              {familiesForProduct.map((f) => (
                <option key={f.recipe_family_id} value={f.recipe_family_id}>
                  {f.recipe_code}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Recipe version" required hint="Released versions matching the product version above.">
            <Select
              value={recipeVersionId}
              onChange={(e) => setRecipeVersionId(e.target.value)}
              disabled={!recipeFamilyId || !productVersionId || recipeVersionsLoading}
              required
            >
              <option value="">
                {!recipeFamilyId || !productVersionId
                  ? "—"
                  : recipeVersionsLoading
                    ? "Loading…"
                    : releasedRecipeVersions.length
                      ? "Select a released version…"
                      : "No matching released version"}
              </option>
              {releasedRecipeVersions.map((v) => (
                <option key={v.recipe_version_id} value={v.recipe_version_id}>
                  v{v.version_no}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Target quantity" required>
            <Input type="number" step="any" value={targetQty} onChange={(e) => setTargetQty(e.target.value)} required />
          </Field>
          <Field label="UOM" required>
            <Input value={targetUom} onChange={(e) => setTargetUom(e.target.value)} required />
          </Field>
          <Field label="Production order ref">
            <Input value={orderRef} onChange={(e) => setOrderRef(e.target.value)} />
          </Field>
        </div>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={busy || !batchNumber.trim() || !siteId || !productVersionId || !recipeVersionId}
          >
            {busy ? "Creating…" : "Create batch"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ExecutionModal({
  batchId,
  onClose,
  onChanged,
}: {
  batchId: string;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { me } = useMe();
  const view = useApiResource<ExecutionView>(`/batches/v1/${batchId}/execution-view`);
  const [action, setAction] = useState<Action | null>(null);
  const [startingStep, setStartingStep] = useState<BatchStep | null>(null);
  const [resultsStep, setResultsStep] = useState<BatchStep | null>(null);
  const [completingStep, setCompletingStep] = useState<BatchStep | null>(null);
  const [detailStep, setDetailStep] = useState<BatchStep | null>(null);
  const [holdingStep, setHoldingStep] = useState<BatchStep | null>(null);
  const [resumingStep, setResumingStep] = useState<BatchStep | null>(null);
  const [linkingEvidenceStep, setLinkingEvidenceStep] = useState<BatchStep | null>(null);
  const [handingOverStep, setHandingOverStep] = useState<BatchStep | null>(null);
  const [completingProduction, setCompletingProduction] = useState(false);

  const v = view.data;
  if (!v) {
    return (
      <Modal open onClose={onClose} title="Batch execution">
        {view.error ? <p className="error-text">{view.error}</p> : <p>Loading…</p>}
      </Modal>
    );
  }

  const b = v.batch;
  const allowed = ALLOWED_FROM[b.state] ?? [];
  const canExecute = holdsAnyRole(me, ["Admin", "Operator", "Supervisor"]);
  const canIssue = holdsAnyRole(me, ["Admin", "Supervisor"]);
  const hasBlockers = v.blockers.length > 0;

  function offered(a: Action): boolean {
    if (!allowed.includes(a)) return false;
    return a === "issue" ? canIssue : canExecute;
  }

  return (
    <Modal open onClose={onClose} title={`Batch ${b.batch_number}`} large>
      {b.state === "on_hold" && (
        <Banner tone="critical" title="Batch is on hold" icon="lock">
          Execution is stopped. No step can be started until the batch is resumed.
        </Banner>
      )}
      {hasBlockers && (
        <Banner tone="warn" title="Execution blockers">
          <div className="mt-1">
            {v.blockers.map((blocker) => (
              <div key={blocker.step_id} className="flex gap-2" style={{ padding: "3px 0" }}>
                <Icon name="alert-triangle" />
                <span>
                  <span className="font-semibold tabular">{blocker.recipe_step_code}</span> -{" "}
                  {blocker.reason}
                </span>
              </div>
            ))}
          </div>
        </Banner>
      )}

      <FactGrid>
        <Fact label="State">
          <WorkflowStatePill state={b.state} />
        </Fact>
        <Fact label="Target">
          <span className="tabular">
            {b.target_qty} {b.target_uom}
          </span>
        </Fact>
        <Fact label="Steps">
          {v.steps.filter((s) => s.state === "complete" || s.state === "completed").length} of {v.steps.length}{" "}
          complete
        </Fact>
        <Fact label="Issued">{b.issued_at ? formatDateTime(b.issued_at) : "—"}</Fact>
        <Fact label="Started">{b.started_at ? formatDateTime(b.started_at) : "—"}</Fact>
        <Fact label="Production order">{b.production_order_ref ?? "—"}</Fact>
        <Fact label="Record version">{b.version}</Fact>
        <IdFact label="Batch ID" value={b.batch_id} />
        <Fact label="Product">{b.product_name ? `${b.product_name} (${b.product_code})` : b.product_version_id}</Fact>
        <Fact label="Recipe">{b.recipe_code ? `${b.recipe_code} v${b.recipe_version_no}` : b.recipe_version_id}</Fact>
        <IdFact label="Recipe vault object" value={b.recipe_vault_object_id} />
        <IdFact label="Execution snapshot" value={b.execution_snapshot_id} />
      </FactGrid>

      <p className="fact-k mb-2 mt-4">Steps</p>
      {v.steps.length === 0 ? (
        <p className="hint">
          No step instances yet - they are created when the batch is issued.
        </p>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Step</th>
              <th>Required role</th>
              <th>State</th>
              <th>Assigned</th>
              <th>Started</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {v.steps.map((s) => (
              <tr key={s.step_id}>
                <td className="font-semibold tabular">{s.recipe_step_code}</td>
                <td className="fs-2">{s.required_role_code ?? <span className="text-muted">any</span>}</td>
                <td>
                  <WorkflowStatePill state={s.state} />
                  {s.state === "on_hold" && v.active_hold_by_step_id[s.step_id] && (
                    <p className="hint" style={{ marginTop: 2 }}>
                      {v.active_hold_by_step_id[s.step_id].reason}
                    </p>
                  )}
                </td>
                <td className="fs-2" style={{ wordBreak: "break-word" }}>
                  {s.assigned_full_name ? `${s.assigned_full_name} (${s.assigned_username})` : s.assigned_subject_id ?? "—"}
                </td>
                <td className="tabular fs-2">{s.started_at ? formatDateTime(s.started_at) : "—"}</td>
                <td style={{ textAlign: "right" }}>
                  <div className="flex justify-end gap-2 flex-wrap">
                    <Button size="sm" variant="secondary" onClick={() => setDetailStep(s)}>
                      <Icon name="info" /> Detail
                    </Button>
                    {canExecute && b.state === "in_execution" && s.state === "ready" && (
                      <Button size="sm" variant="secondary" onClick={() => setStartingStep(s)}>
                        <Icon name="play" /> Start
                      </Button>
                    )}
                    {canExecute && b.state === "in_execution" && s.state === "in_progress" && (
                      <>
                        {(v.parameters_by_step_id[s.step_id]?.length ?? 0) > 0 && (
                          <Button size="sm" variant="secondary" onClick={() => setResultsStep(s)}>
                            <Icon name="clipboard" /> Record results
                          </Button>
                        )}
                        <Button size="sm" variant="secondary" onClick={() => setLinkingEvidenceStep(s)}>
                          <Icon name="file-plus-2" /> Link evidence
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => setHandingOverStep(s)}>
                          <Icon name="arrow-right" /> Hand over
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => setHoldingStep(s)}>
                          <Icon name="lock" /> Hold
                        </Button>
                        <Button size="sm" variant="primary" onClick={() => setCompletingStep(s)}>
                          <Icon name="check-circle" /> Complete
                        </Button>
                      </>
                    )}
                    {canExecute && b.state === "in_execution" && s.state === "on_hold" && (
                      <Button size="sm" variant="primary" onClick={() => setResumingStep(s)}>
                        <Icon name="play" /> Resume
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <div className="flex justify-between gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        <div className="flex gap-2 flex-wrap">
          {(Object.keys(ACTION_LABEL) as Action[]).filter(offered).map((a) => (
            <Button
              key={a}
              size="sm"
              variant={a === "abort" ? "danger" : a === "hold" ? "secondary" : "primary"}
              onClick={() => setAction(a)}
            >
              {ACTION_LABEL[a]}
            </Button>
          ))}
          {canExecute && b.state === "in_execution" && v.steps.length > 0 && v.steps.every((s) => s.state === "complete") && (
            <Button size="sm" variant="success" onClick={() => setCompletingProduction(true)}>
              <Icon name="check-circle" /> Production complete
            </Button>
          )}
        </div>
      </div>

      {action && (
        <BatchActionModal
          batch={b}
          action={action}
          onClose={() => setAction(null)}
          onDone={() => {
            setAction(null);
            view.reload();
            onChanged();
          }}
        />
      )}
      {startingStep && (
        <StartStepModal
          batch={b}
          step={startingStep}
          onClose={() => setStartingStep(null)}
          onDone={() => {
            setStartingStep(null);
            view.reload();
            onChanged();
          }}
        />
      )}
      {resultsStep && (
        <RecordResultsModal
          batch={b}
          step={resultsStep}
          parameters={v.parameters_by_step_id[resultsStep.step_id] ?? []}
          existing={v.results_by_step_id[resultsStep.step_id] ?? []}
          onClose={() => setResultsStep(null)}
          onDone={() => {
            setResultsStep(null);
            view.reload();
            onChanged();
          }}
        />
      )}
      {completingStep && (
        <CompleteStepModal
          batch={b}
          step={completingStep}
          parameters={v.parameters_by_step_id[completingStep.step_id] ?? []}
          existing={v.results_by_step_id[completingStep.step_id] ?? []}
          onClose={() => setCompletingStep(null)}
          onDone={() => {
            setCompletingStep(null);
            view.reload();
            onChanged();
          }}
        />
      )}
      {detailStep && (
        <StepDetailModal
          step={detailStep}
          detail={v.step_detail_by_step_id[detailStep.step_id]}
          parameters={v.parameters_by_step_id[detailStep.step_id] ?? []}
          results={v.results_by_step_id[detailStep.step_id] ?? []}
          onClose={() => setDetailStep(null)}
        />
      )}
      {holdingStep && (
        <HoldStepModal
          batch={b}
          step={holdingStep}
          onClose={() => setHoldingStep(null)}
          onDone={() => {
            setHoldingStep(null);
            view.reload();
            onChanged();
          }}
        />
      )}
      {resumingStep && (
        <ResumeStepModal
          batch={b}
          step={resumingStep}
          activeHold={v.active_hold_by_step_id[resumingStep.step_id]}
          onClose={() => setResumingStep(null)}
          onDone={() => {
            setResumingStep(null);
            view.reload();
            onChanged();
          }}
        />
      )}
      {linkingEvidenceStep && (
        <LinkEvidenceModal
          batch={b}
          step={linkingEvidenceStep}
          onClose={() => setLinkingEvidenceStep(null)}
          onDone={() => {
            setLinkingEvidenceStep(null);
            view.reload();
            onChanged();
          }}
        />
      )}
      {handingOverStep && (
        <HandoverStepModal
          batch={b}
          step={handingOverStep}
          onClose={() => setHandingOverStep(null)}
          onDone={() => {
            setHandingOverStep(null);
            view.reload();
            onChanged();
          }}
        />
      )}
      {completingProduction && (
        <ProductionCompleteModal
          batch={b}
          onClose={() => setCompletingProduction(false)}
          onDone={() => {
            setCompletingProduction(false);
            view.reload();
            onChanged();
          }}
        />
      )}
    </Modal>
  );
}

// BAT-FR-020, step scope (SG-047 further partial resolution, 2026-09-09). Signed (Document 106 row 14's
// shape, the nearest analogous batch-level action -- no step-scoped row exists in Document 106 itself).
function HoldStepModal({
  batch,
  step,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  onClose: () => void;
  onDone: () => void;
}) {
  const [reason, setReason] = useState("");

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/batches/v1/${batch.batch_id}/steps/${step.step_id}/signature-challenges`}
      action="hold"
      title={
        <span className="flex items-center gap-2">
          <Icon name="lock" /> Hold step - {step.recipe_step_code}
        </span>
      }
 summary="Holding this step is a signed act and stops only this step - the rest of the batch keeps running."
      submitLabel="Sign & hold"
      reason="none"
      disabled={!reason.trim()}
      extraFields={
        <Field label="Hold reason" required>
          <textarea className="input" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
      }
      onSign={(payload) =>
        api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/hold`, {
          idempotency_key: payload.idempotency_key,
          batch_id: batch.batch_id,
          step_id: step.step_id,
          expected_version: step.version,
          reason: reason.trim(),
          challenge_id: payload.challenge_id,
          reauth_password: payload.reauth_password,
        })
      }
    />
  );
}

// BAT-FR-020 resume — Document 106 row 17's shape ("Approved", the meaning a QA authority attests when
// lifting a hold, distinct from the "Performed" the hold itself used).
function ResumeStepModal({
  batch,
  step,
  activeHold,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  activeHold: ActiveHold | undefined;
  onClose: () => void;
  onDone: () => void;
}) {
  const [reason, setReason] = useState("");

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/batches/v1/${batch.batch_id}/steps/${step.step_id}/signature-challenges`}
      action="resume"
      title={
        <span className="flex items-center gap-2">
          <Icon name="play" /> Resume step - {step.recipe_step_code}
        </span>
      }
      summary={
        activeHold
          ? `Held for: ${activeHold.reason}`
 :"Resuming this step is a signed act."
      }
      submitLabel="Sign & resume"
      reason="none"
      extraFields={
        <Field label="Resume note" hint="Optional - recorded in the audit trail.">
          <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
      }
      onSign={(payload) =>
        api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/resume`, {
          idempotency_key: payload.idempotency_key,
          batch_id: batch.batch_id,
          step_id: step.step_id,
          expected_version: step.version,
          reason: reason.trim() || null,
          challenge_id: payload.challenge_id,
          reauth_password: payload.reauth_password,
        })
      }
    />
  );
}

// BAT-FR-026, steps-completeness sub-clause only (SG-048 #026 partial resolution, 2026-09-09). Document
// 106 row 16's shape ("Performed", qualified performer, no independence).
function ProductionCompleteModal({
  batch,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  onClose: () => void;
  onDone: () => void;
}) {
  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/batches/v1/${batch.batch_id}/signature-challenges`}
      action="production_complete"
      title={
        <span className="flex items-center gap-2">
          <Icon name="check-circle" /> Mark production complete - {batch.batch_number}
        </span>
      }
 summary="Every recipe step is Complete. This is a signed act marking the batch's production phase done. Yield/reconciliation and other production blockers are not checked by this action yet."
      submitLabel="Sign & mark complete"
      reason="none"
      onSign={(payload) =>
        api.post(`/batches/v1/${batch.batch_id}/production-complete`, {
          idempotency_key: payload.idempotency_key,
          batch_id: batch.batch_id,
          expected_version: batch.version,
          challenge_id: payload.challenge_id,
          reauth_password: payload.reauth_password,
        })
      }
    />
  );
}

// "Step detail" — read-only, BAT-FR-005/§9's execution-UI field list (instruction, section, dependencies,
// evidence requirements, target/limits) plus current progress (2026-09-09, client-requested).
function StepDetailModal({
  step,
  detail,
  parameters,
  results,
  onClose,
}: {
  step: BatchStep;
  detail: StepDetail | undefined;
  parameters: StepParameter[];
  results: StepResultRow[];
  onClose: () => void;
}) {
  const latestByCode = new Map<string, StepResultRow>();
  for (const r of results) latestByCode.set(r.parameter_code, r);

  return (
    <Modal open onClose={onClose} title={`Step detail - ${step.recipe_step_code}`} large>
      <FactGrid>
        <Fact label="State">
          <WorkflowStatePill state={step.state} />
        </Fact>
        <Fact label="Step type">{detail?.step_type ?? "—"}</Fact>
        <Fact label="Section">{detail?.section_name ? `${detail.section_name} (${detail.section_code})` : "—"}</Fact>
        <Fact label="Critical">{detail?.is_critical ? "Yes" : "No"}</Fact>
        <Fact label="Required role">{step.required_role_code ?? <span className="text-muted">any</span>}</Fact>
        <Fact label="Assigned">
          {step.assigned_full_name ? `${step.assigned_full_name} (${step.assigned_username})` : step.assigned_subject_id ?? "—"}
        </Fact>
        <Fact label="Started">{step.started_at ? formatDateTime(step.started_at) : "—"}</Fact>
        <Fact label="Completed">{step.completed_at ? formatDateTime(step.completed_at) : "—"}</Fact>
      </FactGrid>

      <div className="mt-4">
        <p className="fact-k mb-1">Instruction</p>
        {detail?.instruction_text ? (
          <p className="fs-3" style={{ whiteSpace: "pre-wrap" }}>
            {detail.instruction_text}
          </p>
        ) : (
          <p className="hint">This step&apos;s recipe has no instruction text recorded.</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 mt-4">
        <div>
          <p className="fact-k mb-1">Predecessors (must be Complete first)</p>
          {!detail || detail.predecessor_codes.length === 0 ? (
            <p className="hint">None - this step is a root step.</p>
          ) : (
            <p className="tabular fs-2">{detail.predecessor_codes.join(", ")}</p>
          )}
        </div>
        <div>
          <p className="fact-k mb-1">Unblocks next</p>
          {!detail || detail.successor_codes.length === 0 ? (
            <p className="hint">None - this is a terminal step.</p>
          ) : (
            <p className="tabular fs-2">{detail.successor_codes.join(", ")}</p>
          )}
        </div>
      </div>

      <div className="mt-4">
        <p className="fact-k mb-2">Parameters &amp; recorded results</p>
        {parameters.length === 0 ? (
          <p className="hint">This step has no parameters.</p>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Parameter</th>
                <th>Type</th>
                <th>Target / range</th>
                <th>Recorded value</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {parameters.map((p) => {
                const r = latestByCode.get(p.parameter_code);
                const recorded = r
                  ? r.value_bool !== null
                    ? r.value_bool
                      ? "true"
                      : "false"
                    : (r.value_numeric ?? r.value_text ?? "—")
                  : null;
                return (
                  <tr key={p.parameter_code}>
                    <td className="font-semibold tabular">
                      {p.parameter_code}
                      {p.required && <span className="error-text"> *</span>}
                    </td>
                    <td className="fs-2">
                      {p.data_type}
                      {p.uom ? ` (${p.uom})` : ""}
                    </td>
                    <td className="tabular fs-2">
                      {p.target_value ? `target ${p.target_value}` : p.min_value || p.max_value ? `${p.min_value ?? "—"}–${p.max_value ?? "—"}` : "—"}
                    </td>
                    <td className="tabular fs-2">{recorded ?? <span className="text-muted">not recorded</span>}</td>
                    <td className="tabular fs-2">{r?.received_at ? formatDateTime(r.received_at) : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </div>

      <div className="mt-4">
        <p className="fact-k mb-2">Evidence requirements</p>
        {!detail || detail.evidence_requirements.length === 0 ? (
          <p className="hint">This step has no declared evidence requirement.</p>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Evidence type</th>
                <th>Count required</th>
                <th>Allowed file types</th>
              </tr>
            </thead>
            <tbody>
              {detail.evidence_requirements.map((e, i) => (
                <tr key={`${e.evidence_type}-${i}`}>
                  <td className="fs-2">{e.evidence_type}</td>
                  <td className="tabular fs-2">{e.required_count}</td>
                  <td className="fs-2">{e.allowed_mime_types ?? <span className="text-muted">any</span>}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
        <p className="hint mt-2">
          Stage and finalize the evidence object itself under Platform ops → Evidence operations, then use
 this step&apos;s &quot;Link evidence&quot; action to attach it here.
        </p>
      </div>

      <div className="flex justify-end mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </div>
    </Modal>
  );
}

function BatchActionModal({
  batch,
  action,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  action: Action;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [reason, setReason] = useState("");

  const PATH: Record<Action, string> = {
    issue: "issue",
    start: "start",
    hold: "hold",
    resume: "resume",
    abort: "abort",
  };

  return (
    <Modal open onClose={onClose} title={`${ACTION_LABEL[action]} - ${batch.batch_number}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/batches/v1/${batch.batch_id}/${PATH[action]}`, {
              idempotency_key: newIdempotencyKey(),
              batch_id: batch.batch_id,
              expected_version: batch.version,
              // The issue command takes no reason; the transition commands all accept one.
              ...(action === "issue" ? {} : { reason: reason || null }),
            })
          );
        }}
      >
        {action === "issue" && (
          <p className="fs-3 mb-3">
            Issuing freezes the recipe into an execution snapshot and creates this batch&apos;s step
            instances. The snapshot, not the live recipe, governs execution from here.
          </p>
        )}
        {action === "abort" && (
          <Banner tone="critical" title="Aborting is final">
            An aborted batch cannot be resumed. Material already consumed stays consumed and must be
            reconciled.
          </Banner>
        )}

        {action !== "issue" && (
          <Field
            label="Reason"
            required={action === "hold" || action === "abort"}
            hint="Part of the permanent batch record."
          >
            <textarea
              className="input"
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required={action === "hold" || action === "abort"}
            />
          </Field>
        )}

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant={action === "abort" ? "danger" : "primary"} disabled={busy}>
            {busy ? "Saving…" : ACTION_LABEL[action]}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function StartStepModal({
  batch,
  step,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [overrideReason, setOverrideReason] = useState("");
  const roleMismatch = error?.startsWith("STEP_ROLE_MISMATCH");

  return (
    <Modal open onClose={onClose} title={`Start step ${step.recipe_step_code}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/start`, {
              idempotency_key: newIdempotencyKey(),
              batch_id: batch.batch_id,
              step_id: step.step_id,
              expected_version: step.version,
              override_reason: overrideReason.trim() || undefined,
            })
          );
        }}
      >
        <p className="fs-3 mb-3">
          Starting a step claims it for you and records the start time. Your qualification and role for
          this step are checked by the backend.
        </p>
        <FactGrid>
          <Fact label="Step">{step.recipe_step_code}</Fact>
          <Fact label="Required role">{step.required_role_code ?? "any"}</Fact>
          <Fact label="Current state">
            <WorkflowStatePill state={step.state} />
          </Fact>
        </FactGrid>
        {step.required_role_code && (
          <div className="mt-3">
            <label className="hint" style={{ display: "block", marginBottom: 4 }}>
              Override reason{" "}
              <span className="text-muted">
 (only needed if you do not hold the {step.required_role_code} role recorded on the audit
                event; requires a Supervisor/Admin)
              </span>
            </label>
            <textarea
              className="input"
              rows={2}
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="e.g. cross-trained lead covering an absent operator, per shift log…"
            />
          </div>
        )}
        {error && (
          <p className="error-text mt-3 mb-2">
            {roleMismatch
              ? "This step is reserved for another role. Enter an override reason above and retry (Supervisor/Admin only)."
              : error}
          </p>
        )}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            <Icon name="play" /> {busy ? "Starting…" : "Start step"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

const EVIDENCE_LINK_SUBFIELDS: RepeatSubField[] = [
  { name: "evidence_id", label: "Evidence object ID", required: true, placeholder: "From Platform ops → Evidence operations" },
  { name: "evidence_sha256", label: "Evidence SHA-256", required: true },
  { name: "media_type", label: "Media type" },
  { name: "requirement_code", label: "Requirement code", placeholder: "Matches a declared evidence requirement" },
];

/** SG-047 (`gxp_step_evidence_link` half) — unsigned by design (attaching evidence is a capture, not a
 * release/disposition decision). Links already-staged/finalized evidence objects (stage + finalize an
 * upload via Platform ops → Evidence operations first, then paste the resulting id/hash here) rather than
 * re-implementing file upload inline — the evidence object lifecycle is owned by `app/modules/evidence`,
 * not this module. */
function LinkEvidenceModal({
  batch,
  step,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [links, setLinks] = useState<RepeatRow[]>([]);

  return (
    <Modal open onClose={onClose} title={`Link evidence - ${step.recipe_step_code}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/evidence-links`, {
              idempotency_key: newIdempotencyKey(),
              batch_id: batch.batch_id,
              step_id: step.step_id,
              expected_version: step.version,
              links: buildRepeatArray(EVIDENCE_LINK_SUBFIELDS, links),
            })
          );
        }}
      >
        <p className="fs-3 mb-3">
          Stage and finalize the evidence object first (Platform ops → Evidence operations), then link its
          id and content hash to this step.
        </p>
        <RepeatableRows
          label="Evidence links"
          required
          itemLabel="Evidence link"
          subFields={EVIDENCE_LINK_SUBFIELDS}
          value={links}
          onChange={setLinks}
        />
        {error && <p className="error-text mt-3 mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || links.length === 0}>
            {busy ? "Linking…" : "Link evidence"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function HandoverStepModal({
  batch,
  step,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const entities = useEntityOptions();
  const [toUserId, setToUserId] = useState("");
  const [reason, setReason] = useState("");

  return (
    <Modal open onClose={onClose} title={`Hand over step - ${step.recipe_step_code}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/handover`, {
              idempotency_key: newIdempotencyKey(),
              batch_id: batch.batch_id,
              step_id: step.step_id,
              expected_version: step.version,
              to_user_id: toUserId,
              reason: reason.trim() || null,
            })
          );
        }}
      >
        <p className="fs-3 mb-3">Reassigns this in-progress step to another qualified operator.</p>
        <EntityPickerField
          label="Hand over to"
          required
          value={toUserId}
          onChange={setToUserId}
          options={entities.users}
          status={entities.usersStatus}
          kind="user"
        />
        <Field label="Reason" hint="Optional. Recorded in the audit trail.">
          <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
        {error && <p className="error-text mt-3 mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !toUserId.trim()}>
            {busy ? "Handing over…" : "Hand over"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// BAT-FR-009/010, Document 106 row 21 (batch_step/results) — SG-047 partial resolution. Each recorded
// value's data_type comes from the recipe's own RecipeParameter (parameters prop), not asserted by this
// form -- the widget below is chosen by matching that declared type, purely a rendering decision.
function RecordResultsModal({
  batch,
  step,
  parameters,
  existing,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  parameters: StepParameter[];
  existing: StepResultRow[];
  onClose: () => void;
  onDone: () => void;
}) {
  // `existing` is received_at-ascending (service.get_step_results) -- last write per code wins as the
  // pre-filled starting value, a convenience for correcting a mis-keyed reading before completion.
  const latestByCode = new Map<string, StepResultRow>();
  for (const r of existing) latestByCode.set(r.parameter_code, r);

  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const p of parameters) {
      const prior = latestByCode.get(p.parameter_code);
      if (!prior) continue;
      if (isBooleanParameter(p.data_type)) init[p.parameter_code] = prior.value_bool ? "true" : "false";
      else if (isNumericParameter(p.data_type)) init[p.parameter_code] = prior.value_numeric ?? "";
      else init[p.parameter_code] = prior.value_text ?? "";
    }
    return init;
  });

  const filled = parameters.filter((p) => (values[p.parameter_code] ?? "").trim() !== "");

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/batches/v1/${batch.batch_id}/steps/${step.step_id}/signature-challenges`}
      action="results"
      title={
        <span className="flex items-center gap-2">
          <Icon name="clipboard" /> Record results - {step.recipe_step_code}
        </span>
      }
 summary="Recording a parameter result against this step is a signed act."
      submitLabel="Sign & record"
      reason="none"
      disabled={filled.length === 0}
      extraFields={
        <div className="mb-3">
          {parameters.length === 0 && <p className="hint">This step has no parameters to record.</p>}
          {parameters.map((p) => (
            <Field
              key={p.parameter_code}
              label={`${p.parameter_code}${p.required ? " *" : ""}`}
              hint={
                [
                  p.uom,
                  p.target_value ? `target ${p.target_value}` : null,
                  p.min_value || p.max_value ? `range ${p.min_value ?? "—"}–${p.max_value ?? "—"}` : null,
                ]
                  .filter(Boolean)
                  .join(" · ") || undefined
              }
            >
              {isBooleanParameter(p.data_type) ? (
                <Select
                  value={values[p.parameter_code] ?? ""}
                  onChange={(e) => setValues((v) => ({ ...v, [p.parameter_code]: e.target.value }))}
                >
                  <option value="">—</option>
                  <option value="true">Pass / Yes</option>
                  <option value="false">Fail / No</option>
                </Select>
              ) : (
                <Input
                  type={isNumericParameter(p.data_type) ? "number" : "text"}
                  step="any"
                  value={values[p.parameter_code] ?? ""}
                  onChange={(e) => setValues((v) => ({ ...v, [p.parameter_code]: e.target.value }))}
                />
              )}
            </Field>
          ))}
        </div>
      }
      onSign={(payload) =>
        api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/results`, {
          idempotency_key: payload.idempotency_key,
          batch_id: batch.batch_id,
          step_id: step.step_id,
          expected_version: step.version,
          challenge_id: payload.challenge_id,
          reauth_password: payload.reauth_password,
          results: filled.map((p) => {
            const raw = values[p.parameter_code];
            if (isBooleanParameter(p.data_type)) return { parameter_code: p.parameter_code, value_bool: raw === "true" };
            if (isNumericParameter(p.data_type)) return { parameter_code: p.parameter_code, value_numeric: raw };
            return { parameter_code: p.parameter_code, value_text: raw };
          }),
        })
      }
    />
  );
}

// BAT-FR-006 (runtime)/015/016, Document 106 row 19 (batch_step/complete) — SG-047 partial resolution.
// Blocked client-side (mirrors the server's own PARAMETER_REQUIRED check) whenever a required parameter
// has no recorded result yet.
function CompleteStepModal({
  batch,
  step,
  parameters,
  existing,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  parameters: StepParameter[];
  existing: StepResultRow[];
  onClose: () => void;
  onDone: () => void;
}) {
  const recordedCodes = new Set(existing.map((r) => r.parameter_code));
  const missingRequired = parameters.filter((p) => p.required && !recordedCodes.has(p.parameter_code));
  const [overrideReason, setOverrideReason] = useState("");

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/batches/v1/${batch.batch_id}/steps/${step.step_id}/signature-challenges`}
      action="complete"
      title={
        <span className="flex items-center gap-2">
          <Icon name="check-circle" /> Complete step - {step.recipe_step_code}
        </span>
      }
      summary={
        missingRequired.length > 0 ? (
          <>Missing a recorded result for: {missingRequired.map((p) => p.parameter_code).join(", ")}. Record results first.</>
        ) : (
"Completing this step is a signed act and unblocks the next step once every one of its predecessors is complete."
        )
      }
      submitLabel="Sign & complete"
      reason="none"
      disabled={missingRequired.length > 0}
      extraFields={
        step.required_role_code ? (
          <div className="mb-3">
            <label className="hint" style={{ display: "block", marginBottom: 4 }}>
              Override reason{" "}
              <span className="text-muted">
                (only if you do not hold the {step.required_role_code} role recorded on the audit event;
                requires Supervisor/Admin)
              </span>
            </label>
            <textarea
              className="input"
              rows={2}
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
            />
          </div>
        ) : undefined
      }
      onSign={(payload) =>
        api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/complete`, {
          idempotency_key: payload.idempotency_key,
          batch_id: batch.batch_id,
          step_id: step.step_id,
          expected_version: step.version,
          override_reason: overrideReason.trim() || undefined,
          challenge_id: payload.challenge_id,
          reauth_password: payload.reauth_password,
        })
      }
    />
  );
}
