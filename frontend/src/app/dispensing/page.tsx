"use client";

import { useEffect, useState } from "react";
import {
  api,
  hasPermission,
  listAll,
  listBatchesForSite,
  newIdempotencyKey,
  pagedFetcher,
  type BatchSummary,
  type Material,
} from "@/lib/api";
import { useApiResource, useEntityOptions, useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { FormConsole } from "@/components/shared/FormConsole";
import { SignedJsonForm } from "@/components/shared/SignedJsonForm";

interface DispensingOrder {
  id: string;
  site_id: string;
  batch_id: string;
  batch_step_id: string | null;
  material_id: string;
  target_qty: string;
  target_uom: string;
  tolerance_low: string;
  tolerance_high: string;
  // SG-094 (Topic 5): target/tolerance are now derived from the batch's recipe at creation time --
  // target_from_recipe is false only after a Supervisor/Admin `override-target` call.
  target_from_recipe: boolean;
  override_reason: string | null;
  overridden_by_user_id: string | null;
  overridden_at: string | null;
  state: string;
  version: number;
}

// Every step past creation is a signed act (Document 21 / Document 106) — the challenge action name
// matches the backend's _DISPENSING_CHALLENGE_MEANINGS keys.
type Step = "select_source" | "start" | "readings" | "manual_reading" | "verify" | "complete" | "cancel";

const STEP_LABEL: Record<Step, string> = {
  select_source: "Select source",
  start: "Start weighing",
  readings: "Record reading",
  manual_reading: "Record manual reading",
  verify: "Independent verify",
  complete: "Complete",
  cancel: "Cancel order",
};

// Which steps the order's state admits, mirroring the command guards in app/modules/material/commands.py.
// Two real bugs fixed here: (1) the backend only ever sets state to "started" after Start
// (select_dispensing_source/start_dispensing/record_manual_reading/verify_dispensing/complete_dispensing
// all grep-verified) -- "weighing"/"weighed" never occur, so ALLOWED_FROM[o.state] silently returned []
// for every order past "source_selected", hiding every action (readings/manual reading/verify/complete)
// from the UI entirely. (2) DSP-FR-017 multi-lot dispensing lets select_source be called again while
// "source_selected" (a container short of the full target quantity is expected, not an error) --
// select_dispensing_source's own docstring says so, but the UI only ever offered it from "created".
const ALLOWED_FROM: Record<string, Step[]> = {
  created: ["select_source", "cancel"],
  source_selected: ["select_source", "start", "cancel"],
  started: ["readings", "manual_reading", "verify", "complete", "cancel"],
  verified: ["complete", "cancel"],
};

export default function DispensingPage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [reloadToken, setReloadToken] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const canDispense = hasPermission(me, "dispensing_order.create");

  const columns: DataTableColumn<DispensingOrder>[] = [
    {
      key: "batch_id",
      header: "Batch",
      render: (o) => (
        <span className="tabular fs-2" style={{ wordBreak: "break-all" }}>
          {o.batch_id}
        </span>
      ),
    },
    {
      key: "target_qty",
      header: "Target",
      align: "right",
      render: (o) => (
        <span className="tabular">
          {o.target_qty} {o.target_uom}
        </span>
      ),
    },
    {
      key: "tolerance",
      header: "Tolerance",
      render: (o) => (
        <span className="tabular fs-2">
          {o.tolerance_low}–{o.tolerance_high}
        </span>
      ),
    },
    { key: "state", header: "State", sortable: true, render: (o) => <WorkflowStatePill state={o.state} /> },
  ];

  return (
    <div>
      <PageHead
        title="Dispensing"
        subtitle="The weighing queue, source selection, readings, independent verification and completion."
        action={
          canDispense ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> New dispensing order
            </Button>
          ) : undefined
        }
      />

      <p className="hint mb-4">
        Every step after creation is a signed act - each opens a signature ceremony bound to the order&apos;s
        current version.
      </p>

      <Card>
        <CardHeader title="Open queue" meta="Completed and cancelled orders are not listed" />
        <DataTable
          columns={columns}
          fetchPage={pagedFetcher<DispensingOrder>("/dispensing/v1/queue")}
          rowKey={(o) => o.id}
          searchPlaceholder="Search…"
          emptyIcon="droplet"
          emptyMessage="Nothing in the dispensing queue."
          defaultSort={{ by: "created_at", dir: "asc" }}
          reloadToken={reloadToken}
          onRowClick={(o) => setSelected(o.id)}
        />
      </Card>

      <FormConsole
      title="Material transaction operations"
        subtitle="What happens to a dispensed quantity afterward - consumed, returned, lost, or requested for destruction."
        root="/materials/v1"
        ops={[
          {
            path: "consumptions",
            label: "Record a consumption",
            fields: [
              { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
              { name: "step_id", label: "Step ID", hint: "Optional - the batch step this consumption belongs to." },
              { name: "dispensed_container_id", label: "Dispensed container ID", type: "dispensedContainerSelect", required: true },
              { name: "material_lot_id", label: "Material lot ID", hint: "Optional, if not derivable from the container." },
              { name: "quantity", label: "Quantity", required: true },
              { name: "uom", label: "Unit of measure", type: "uomSelect", required: true },
              { name: "source_type", label: "Source type", default: "manual", placeholder: "e.g. manual, machine" },
              { name: "source_id", label: "Source ID", hint: "Optional - e.g. a machine evidence reference." },
            ],
          },
          {
            path: "returns",
            label: "Record a return",
            fields: [
              { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
              { name: "dispensed_container_id", label: "Dispensed container ID", type: "dispensedContainerSelect", required: true },
              { name: "material_lot_id", label: "Material lot ID", hint: "Optional, if not derivable from the container." },
              { name: "quantity", label: "Quantity", required: true },
              { name: "uom", label: "Unit of measure", type: "uomSelect", required: true },
              { name: "container_condition", label: "Container condition", required: true },
              { name: "condition_acceptable", label: "Condition acceptable", type: "bool", required: true },
              { name: "storage_exposure_evidence", label: "Storage exposure evidence", type: "kv" },
              { name: "target_location_id", label: "Target location ID", required: true },
            ],
          },
          {
            path: "losses",
            label: "Record a loss / spill / sample",
            about: "One command covers sample, reject, spill and approved-loss transaction types.",
            fields: [
              { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
              { name: "dispensed_container_id", label: "Dispensed container ID", type: "dispensedContainerSelect", required: true },
              { name: "loss_type", label: "Loss type", required: true, placeholder: "e.g. SAMPLE, REJECT, SPILL, APPROVED_LOSS" },
              { name: "quantity", label: "Quantity", required: true },
              { name: "uom", label: "Unit of measure", type: "uomSelect", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
              { name: "location_id", label: "Location ID", hint: "Optional." },
              { name: "evidence", label: "Evidence", type: "kv" },
            ],
          },
          {
            path: "destructions",
            label: "Request a destruction",
            about: "Set exactly one of material lot, container, or dispensed container as the destruction's scope.",
            fields: [
              { name: "material_lot_id", label: "Material lot ID", hint: "One of the three scope fields." },
              { name: "container_id", label: "Container ID", hint: "One of the three scope fields." },
              { name: "dispensed_container_id", label: "Dispensed container ID", hint: "One of the three scope fields." },
              { name: "quantity", label: "Quantity", required: true },
              { name: "uom", label: "Unit of measure", type: "uomSelect", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
              { name: "method", label: "Method", hint: "Optional - e.g. incineration, chemical treatment." },
              { name: "vendor_name", label: "Vendor name", hint: "Optional - for third-party destruction." },
              { name: "manifest_reference", label: "Manifest reference", hint: "Optional." },
              { name: "certificate_vault_object_id", label: "Certificate vault object ID", hint: "Optional - a certificate of destruction already in the vault." },
              { name: "witnesses", label: "Witnesses", type: "kv" },
            ],
          },
        ]}
      />

      <SignedJsonForm
        title="Execute a destruction - signed"
        subtitle="Only a requested destruction can be executed."
        root="/materials/v1"
        ops={[
          {
            postPath: "destructions/{destruction_id}/execute",
            challengePath: "destructions/{destruction_id}/signature-challenges",
            action: "execute",
            label: "Execute a destruction",
            fields: [
              { name: "destruction_id", label: "Destruction record ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
            ],
          },
        ]}
      />

      {createOpen && (
        <CreateOrderModal
          siteId={siteId}
          onClose={() => setCreateOpen(false)}
          onDone={() => {
            setCreateOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
      {selected && (
        <OrderModal
          orderId={selected}
          onClose={() => setSelected(null)}
          onChanged={() => setReloadToken((n) => n + 1)}
        />
      )}
    </div>
  );
}

function CreateOrderModal({
  siteId,
  onClose,
  onDone,
}: {
  siteId: string | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [batchId, setBatchId] = useState("");
  const [materialId, setMaterialId] = useState("");
  const [batchStepId, setBatchStepId] = useState("");

  // SG-094 (Topic 5, project-owner-directed): target/tolerance are no longer entered here -- they are
  // derived server-side from the chosen batch step's recipe-declared RecipeMaterialRequirement. The
  // operator picks the batch and the step within it; a Supervisor/Admin can still override the derived
  // values afterward (see the order detail's "Override target" action), but only while the order is
  // still in "created" state.
  const { data: executionView, loading: stepsLoading } = useApiResource<{
    steps: { id: string; recipe_step_code: string }[];
    step_detail_by_step_id: Record<string, { instruction_text: string | null } | undefined>;
  }>(batchId ? `/batches/v1/${batchId}/execution-view` : null);
  const steps = executionView?.steps ?? [];
  // Defaults to the first step once the batch's steps load, without a setState-in-effect round trip --
  // batchStepId only tracks an explicit user pick (or is reset to "" when the batch itself changes).
  const effectiveBatchStepId = steps.some((s) => s.id === batchStepId) ? batchStepId : steps[0]?.id ?? "";

  useEffect(() => {
    let cancelled = false;
    listAll<Material>("/materials")
      .then((rows) => {
        if (cancelled) return;
        setMaterials(rows);
        setMaterialId((current) => current || rows[0]?.id || "");
      })
      .catch(() => undefined);
    if (siteId) {
      listBatchesForSite(siteId)
        .then((rows) => {
          if (cancelled) return;
          setBatches(rows);
          setBatchId((current) => current || rows[0]?.id || "");
        })
        .catch(() => undefined);
    }
    return () => {
      cancelled = true;
    };
  }, [siteId]);

  return (
    <Modal open onClose={onClose} title="New dispensing order" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!siteId) return;
          run(() =>
            api.post("/dispensing/v1/orders", {
              idempotency_key: newIdempotencyKey(),
              site_id: siteId,
              batch_id: batchId,
              batch_step_id: effectiveBatchStepId,
              material_id: materialId,
            })
          );
        }}
      >
        <Field label="Batch" required hint={batches.length === 0 ? "No batches available yet." : undefined}>
          {batches.length > 0 ? (
            <Select
              value={batchId}
              onChange={(e) => {
                setBatchId(e.target.value);
                setBatchStepId("");
              }}
              required
              autoFocus
            >
              <option value="">Select a batch</option>
              {batches.map((b) => (
                <option key={b.id} value={b.id}>
                    {b.batch_number} - {b.product_name} ({b.product_code})
                </option>
              ))}
            </Select>
          ) : (
            <Input value={batchId} onChange={(e) => setBatchId(e.target.value)} placeholder="Batch ID" required autoFocus />
          )}
        </Field>
        <Field
          label="Batch step"
          required
          hint={
            !batchId
              ? "Pick a batch first."
              : stepsLoading
              ? "Loading steps…"
              : steps.length === 0
              ? "This batch's recipe declares no steps."
              : "The recipe's declared material requirement for this step sets the target/tolerance."
          }
        >
          <Select value={effectiveBatchStepId} onChange={(e) => setBatchStepId(e.target.value)} required disabled={!batchId || steps.length === 0}>
            <option value="">Select a step…</option>
            {steps.map((s) => (
              <option key={s.id} value={s.id}>
                {s.recipe_step_code}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Material" required>
          <Select value={materialId} onChange={(e) => setMaterialId(e.target.value)} required>
            <option value="">Select a material…</option>
            {materials.map((m) => (
              <option key={m.id} value={m.id}>
                {m.code} - {m.name}
              </option>
            ))}
          </Select>
        </Field>
        <p className="hint mb-3">
          Target quantity, UOM and tolerance are not entered here - they come from this step&apos;s released
          recipe material requirement. If the recipe declares no requirement for this material at this
          step, creation is rejected rather than guessing a target.
        </p>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={busy || !batchId.trim() || !effectiveBatchStepId || !materialId || !siteId}
          >
            {busy ? "Creating…" : "Create order"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function OrderModal({
  orderId,
  onClose,
  onChanged,
}: {
  orderId: string;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { me } = useMe();
  const detail = useApiResource<DispensingOrder>(`/dispensing/v1/orders/${orderId}`);
  const [step, setStep] = useState<Step | null>(null);

  const [overriding, setOverriding] = useState(false);

  const o = detail.data;
  if (!o) {
    return (
      <Modal open onClose={onClose} title="Dispensing order">
        {detail.error ? <p className="error-text">{detail.error}</p> : <p>Loading…</p>}
      </Modal>
    );
  }

  const allowed = ALLOWED_FROM[o.state] ?? [];
  // Document 21 / SOD-011: verification must be performed by someone other than the weigher. The backend
  // enforces the actual independence rule; this only picks who is offered the button.
  const canVerify = hasPermission(me, "dispensing_order.verify");
  // select_source/start/readings/manual_reading/complete share one grant (Admin/Operator/Supervisor).
  const canWeigh = hasPermission(me, "dispensing_order.select_source");
  const canCancel = hasPermission(me, "dispensing_order.cancel");
  // SG-094 (Topic 5): Supervisor/Admin-only, and only reachable before dispensing starts.
  const canOverrideTarget = o.state === "created" && hasPermission(me, "dispensing_order.override_target");

  function offered(s: Step): boolean {
    if (!allowed.includes(s)) return false;
    if (s === "verify") return canVerify;
    if (s === "cancel") return canCancel;
    return canWeigh;
  }

  return (
    <Modal open onClose={onClose} title="Dispensing order" large>
      <FactGrid>
        <Fact label="State">
          <WorkflowStatePill state={o.state} />
        </Fact>
        <Fact label="Target">
          <span className="tabular">
            {o.target_qty} {o.target_uom}
          </span>
        </Fact>
        <Fact label="Tolerance">
          <span className="tabular">
            {o.tolerance_low}–{o.tolerance_high}
          </span>
        </Fact>
        <Fact label="Target source">
          {o.target_from_recipe ? (
            <StatePill state="accepted" icon="check-circle">
              From recipe
            </StatePill>
          ) : (
            <StatePill state="conflict" icon="alert-triangle">
              Manually overridden
            </StatePill>
          )}
        </Fact>
        {!o.target_from_recipe && o.override_reason && (
          <Fact label="Override reason">
            <span className="fs-2">{o.override_reason}</span>
          </Fact>
        )}
        <Fact label="Record version">{o.version}</Fact>
        <IdFact label="Order ID" value={o.id} />
        <IdFact label="Batch" value={o.batch_id} />
        <IdFact label="Material" value={o.material_id} />
      </FactGrid>

      <div className="flex justify-between gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        <div className="flex gap-2 flex-wrap">
          {canOverrideTarget && (
            <Button size="sm" variant="secondary" onClick={() => setOverriding(true)}>
              <Icon name="pen" /> Override target
            </Button>
          )}
          {(Object.keys(STEP_LABEL) as Step[]).filter(offered).map((s) => (
            <Button
              key={s}
              size="sm"
              variant={s === "cancel" ? "danger" : s === "complete" ? "primary" : "secondary"}
              onClick={() => setStep(s)}
            >
              <Icon name="pen" /> {STEP_LABEL[s]}
            </Button>
          ))}
        </div>
      </div>

      {step && (
        <StepModal
          order={o}
          step={step}
          onClose={() => setStep(null)}
          onDone={() => {
            setStep(null);
            detail.reload();
            onChanged();
          }}
        />
      )}

      {overriding && (
        <OverrideTargetModal
          order={o}
          onClose={() => setOverriding(false)}
          onDone={() => {
            setOverriding(false);
            detail.reload();
            onChanged();
          }}
        />
      )}
    </Modal>
  );
}

function StepModal({
  order,
  step,
  onClose,
  onDone,
}: {
  order: DispensingOrder;
  step: Step;
  onClose: () => void;
  onDone: () => void;
}) {
  const entities = useEntityOptions();
  const [lotId, setLotId] = useState("");
  const [containerId, setContainerId] = useState("");
  // GET /material-lots/{lot_id}/containers -- same lot-scoped container list Inventory's own Transfer
  // modal already reads; "Container ID" here was a raw text field with nothing to pick from.
  const { data: lotContainers, loading: lotContainersLoading } = useApiResource<{
    items: { id: string; container_code: string; current_quantity: string; uom: string }[];
  }>(lotId ? `/material-lots/${encodeURIComponent(lotId)}/containers` : null);
  const lotContainerOptions = lotContainers?.items ?? [];
  const [quantity, setQuantity] = useState("");
  const [tareValue, setTareValue] = useState("");
  const [readingValue, setReadingValue] = useState("");
  const [stable, setStable] = useState(true);
  const [deviceId, setDeviceId] = useState("");
  const [manualReason, setManualReason] = useState("");
  const [containerCode, setContainerCode] = useState("");
  const [takenQuantities, setTakenQuantities] = useState<Record<string, string>>({});
  const [reason, setReason] = useState("");

  // SG-223: complete_dispensing needs a positive actual_taken_quantities entry for every DispensingSource
  // this order has (DSP-FR-017 multi-lot dispensing can mean more than one) -- fetch them by their real
  // ids rather than asking the operator to type a source UUID with nothing to copy it from.
  const { data: orderDetail } = useApiResource<{
    sources: { id: string; internal_lot: string; container_code: string | null; reserved_quantity: string }[];
  }>(step === "complete" ? `/dispensing/v1/orders/${order.id}` : null);
  const orderSources = orderDetail?.sources ?? [];

  const missingRequired =
    (step === "select_source" && !quantity) ||
    (step === "readings" && !readingValue) ||
    (step === "manual_reading" && (!readingValue || !manualReason)) ||
    (step === "complete" &&
      (!containerCode ||
        orderSources.length === 0 ||
        orderSources.some((s) => !(Number(takenQuantities[s.id] ?? "") > 0)))) ||
    (step === "cancel" && !reason);

  // tolerance_low/tolerance_high are the absolute acceptable min/max total weight (see the CreateOrderModal
  // note above), not a delta from target_qty -- matches complete_dispensing's own
  // `tolerance_low <= total_taken <= tolerance_high` check exactly.
  const withinTolerance =
    readingValue &&
    Number(readingValue) >= Number(order.tolerance_low) &&
    Number(readingValue) <= Number(order.tolerance_high);

  const extraFields = (
    <>
      {step === "select_source" && (
        <>
          <div className="grid grid-cols-2 gap-4">
            <EntityPickerField
              label="Material lot ID"
              value={lotId}
              onChange={(v) => {
                setLotId(v);
                setContainerId("");
              }}
              options={entities.materialLots}
              status={entities.materialLotsStatus}
              kind="material lot"
            />
            <Field label="Container" hint={!lotId ? "Pick a material lot first." : undefined}>
              <Select value={containerId} onChange={(e) => setContainerId(e.target.value)} disabled={!lotId || lotContainersLoading}>
                <option value="">
                  {!lotId ? "—" : lotContainersLoading ? "Loading containers…" : lotContainerOptions.length ? "Select a container…" : "No containers for this lot"}
                </option>
                {lotContainerOptions.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.container_code} - {c.current_quantity} {c.uom}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <Field label="Quantity to take" required>
            <Input type="number" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
          </Field>
        </>
      )}

      {step === "start" && (
        <Field label="Tare value" hint="Leave blank if the balance tares itself.">
          <Input type="number" step="any" value={tareValue} onChange={(e) => setTareValue(e.target.value)} />
        </Field>
      )}

      {step === "readings" && (
        <>
          <Field
            label={`Reading (${order.target_uom})`}
            required
            hint={`Target ${order.target_qty} - acceptable range ${order.tolerance_low} to ${order.tolerance_high}`}
          >
            <Input type="number" step="any" value={readingValue} onChange={(e) => setReadingValue(e.target.value)} required autoFocus />
          </Field>
          {readingValue && (
            <p className="mb-3">
              {withinTolerance ? (
                <StatePill state="accepted" icon="check-circle">
                  Within tolerance
                </StatePill>
              ) : (
                <StatePill state="failed" icon="alert-triangle">
                  Out of tolerance
                </StatePill>
              )}
            </p>
          )}
          <label className="flex items-center gap-2 fs-2 mb-3">
            <input type="checkbox" checked={stable} onChange={(e) => setStable(e.target.checked)} />
            Balance reading was stable
          </label>
          <EntityPickerField
            label="Device ID"
            hint="Optional - which connected balance/device reported this reading."
            value={deviceId}
            onChange={setDeviceId}
            options={entities.equipment}
            status={entities.equipmentStatus}
            kind="equipment asset"
          />
        </>
      )}

      {step === "manual_reading" && (
        <>
          <Banner tone="warn" title="Manual reading">
            A manual reading bypasses the connected balance, so it needs a stated reason and is recorded
            as manual in the batch record.
          </Banner>
          <Field
            label={`Reading (${order.target_uom})`}
            required
            hint={`Target ${order.target_qty} - acceptable range ${order.tolerance_low} to ${order.tolerance_high}`}
          >
            <Input
              type="number"
              step="any"
              value={readingValue}
              onChange={(e) => setReadingValue(e.target.value)}
              required
              autoFocus
            />
          </Field>
          {readingValue && (
            <p className="mb-3">
              {withinTolerance ? (
                <StatePill state="accepted" icon="check-circle">
                  Within tolerance
                </StatePill>
              ) : (
                <StatePill state="failed" icon="alert-triangle">
                  Out of tolerance
                </StatePill>
              )}
            </p>
          )}
          <label className="flex items-center gap-2 fs-2 mb-3">
            <input type="checkbox" checked={stable} onChange={(e) => setStable(e.target.checked)} />
            Balance reading was stable
          </label>
          <Field label="Reason for manual entry" required>
            <textarea
              className="input"
              rows={2}
              value={manualReason}
              onChange={(e) => setManualReason(e.target.value)}
              required
            />
          </Field>
        </>
      )}

      {step === "verify" && (
        <p className="fs-3 mb-3">
          Independent verification confirms the dispensed quantity and identity. It must not be performed
          by the person who weighed (SOD-011) - the backend enforces this.
        </p>
      )}

      {step === "complete" && (
        <>
          <p className="fs-2 text-muted mb-2">
            Quantity actually taken from each source selected for this order (DSP-FR-017 - multiple sources
            when one container didn&rsquo;t cover the full target).
          </p>
          {orderSources.length === 0 ? (
            <p className="hint mb-2">Loading sources…</p>
          ) : (
            orderSources.map((s) => (
              <div key={s.id} className="grid grid-cols-2 gap-4 mb-2">
                <Field label={s.container_code ? `${s.internal_lot} - ${s.container_code}` : s.internal_lot} hint={`Selected: ${s.reserved_quantity}`}>
                  <span className="fs-2 text-muted">source id: {s.id}</span>
                </Field>
                <Field label="Quantity actually taken" required>
                  <Input
                    type="number"
                    step="any"
                    value={takenQuantities[s.id] ?? ""}
                    onChange={(e) => setTakenQuantities((c) => ({ ...c, [s.id]: e.target.value }))}
                    required
                    autoFocus
                  />
                </Field>
              </div>
            ))
          )}
          <Field label="Dispensed container code" required hint="The label applied to the dispensed container - free text you choose, not a reference to an existing record.">
            <Input value={containerCode} onChange={(e) => setContainerCode(e.target.value)} required />
          </Field>
        </>
      )}

      {step === "cancel" && (
        <Field label="Reason" required>
          <textarea className="input" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} required />
        </Field>
      )}
    </>
  );

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/dispensing/v1/orders/${order.id}/signature-challenges`}
      action={step}
      title={
        <span className="flex items-center gap-2">
          <Icon name="pen" /> {STEP_LABEL[step]}
        </span>
      }
      summary={`Fresh authentication is required to sign this step - ${STEP_LABEL[step].toLowerCase()}.`}
      submitLabel={STEP_LABEL[step]}
      submitVariant={step === "cancel" ? "danger" : "primary"}
      reason="none"
      extraFields={extraFields}
      disabled={missingRequired}
      onSign={(p) => {
        const base = {
          idempotency_key: p.idempotency_key,
          expected_version: order.version,
          challenge_id: p.challenge_id,
          reauth_password: p.reauth_password,
        };
        const path = `/dispensing/v1/orders/${order.id}`;
        switch (step) {
          case "select_source":
            return api.post(`${path}/select-source`, {
              ...base,
              material_lot_id: lotId || null,
              container_id: containerId || null,
              quantity,
            });
          case "start":
            return api.post(`${path}/start`, {
              ...base,
              tare_method: tareValue ? "manual" : null,
              tare_value: tareValue || null,
            });
          case "readings":
            return api.post(`${path}/readings`, {
              ...base,
              reading_value: readingValue,
              uom: order.target_uom,
              stable,
              device_id: deviceId || null,
            });
          case "manual_reading":
            return api.post(`${path}/manual-reading`, {
              ...base,
              reading_value: readingValue,
              uom: order.target_uom,
              stable,
              manual_reason: manualReason,
            });
          case "verify":
            return api.post(`${path}/verify`, base);
          case "complete":
            return api.post(`${path}/complete`, {
              ...base,
              actual_taken_quantities: Object.fromEntries(orderSources.map((s) => [s.id, takenQuantities[s.id]])),
              container_code: containerCode,
            });
          case "cancel":
            return api.post(`${path}/cancel`, { ...base, reason });
        }
      }}
    />
  );
}

// SG-094 (Topic 5) override path: RBAC-only (Supervisor/Admin via dispensing_order.override_target),
// mandatory reason, no signature -- mirrors the batch_step role-override shape rather than a signature
// ceremony for a record whose dispensing hasn't started yet. Only reachable while state == "created"
// (enforced server-side; OrderModal also only offers the button then).
function OverrideTargetModal({
  order,
  onClose,
  onDone,
}: {
  order: DispensingOrder;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [targetQty, setTargetQty] = useState(order.target_qty);
  const [targetUom, setTargetUom] = useState(order.target_uom);
  const [toleranceLow, setToleranceLow] = useState(order.tolerance_low);
  const [toleranceHigh, setToleranceHigh] = useState(order.tolerance_high);
  const [overrideReason, setOverrideReason] = useState("");

  return (
    <Modal open onClose={onClose} title="Override dispensing target">
      <Banner tone="warn" title="Manual override">
        This replaces the recipe-derived target/tolerance for this order only. A documented reason is
        required and is kept on the order&apos;s audit trail.
      </Banner>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/dispensing/v1/orders/${order.id}/override-target`, {
              idempotency_key: newIdempotencyKey(),
              expected_version: order.version,
              target_qty: targetQty,
              target_uom: targetUom,
              tolerance_low: toleranceLow,
              tolerance_high: toleranceHigh,
              override_reason: overrideReason,
            })
          );
        }}
      >
        <div className="grid grid-cols-4 gap-4 mt-3">
          <Field label="Target quantity" required>
            <Input type="number" step="any" value={targetQty} onChange={(e) => setTargetQty(e.target.value)} required />
          </Field>
          <Field label="UOM" required>
            <Input value={targetUom} onChange={(e) => setTargetUom(e.target.value)} required />
          </Field>
          <Field label="Tolerance low" required>
            <Input type="number" step="any" value={toleranceLow} onChange={(e) => setToleranceLow(e.target.value)} required />
          </Field>
          <Field label="Tolerance high" required>
            <Input type="number" step="any" value={toleranceHigh} onChange={(e) => setToleranceHigh(e.target.value)} required />
          </Field>
        </div>
        <Field label="Override reason" required>
          <textarea
            className="input"
            rows={3}
            value={overrideReason}
            onChange={(e) => setOverrideReason(e.target.value)}
            required
          />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={busy || !targetQty.trim() || !targetUom.trim() || !toleranceLow.trim() || !toleranceHigh.trim() || !overrideReason.trim()}
          >
            {busy ? "Saving…" : "Override target"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
