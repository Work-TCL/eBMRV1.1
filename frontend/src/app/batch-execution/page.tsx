"use client";

import { useEffect, useState } from "react";
import { api, clientPagedFetcher, formatDateTime, hasPermission, newIdempotencyKey } from "@/lib/api";
import { useApiResource, useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Banner } from "@/components/ui/Banner";
import { KpiRow, KpiTile } from "@/components/ui/KpiTile";
import { Button, LinkButton } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { UomSelect } from "@/components/ui/UomSelect";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";

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

export default function BatchExecutionPage() {
  const { me } = useMe();
  const { siteId, loading: siteLoading } = useSiteId();
  const [state, setState] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);

  const list = useApiResource<{ batches: GxpBatch[]; on_hold_count: number }>(
    siteId ? `/batches/v1?site_id=${siteId}${state ? `&state=${state}` : ""}&_=${reloadToken}` : null
  );

  const canCreate = hasPermission(me, "batch_execution.create");
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
          <LinkButton href={`/batch-execution/${b.batch_id}`} variant="secondary" size="sm">
            Open
          </LinkButton>
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
          <UomSelect label="UOM" value={targetUom} onChange={setTargetUom} required />
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

