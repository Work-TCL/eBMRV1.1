"use client";

import { useEffect, useState } from "react";
import {
  api,
  holdsAnyRole,
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
  material_id: string;
  target_qty: string;
  target_uom: string;
  tolerance_low: string;
  tolerance_high: string;
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
const ALLOWED_FROM: Record<string, Step[]> = {
  created: ["select_source", "cancel"],
  source_selected: ["start", "cancel"],
  weighing: ["readings", "manual_reading", "verify", "cancel"],
  weighed: ["verify", "complete", "cancel"],
  verified: ["complete", "cancel"],
};

export default function DispensingPage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [reloadToken, setReloadToken] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const canDispense = holdsAnyRole(me, ["Admin", "Operator", "Supervisor"]);

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
          −{o.tolerance_low} / +{o.tolerance_high}
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
              { name: "dispensed_container_id", label: "Dispensed container ID", required: true },
              { name: "material_lot_id", label: "Material lot ID", hint: "Optional, if not derivable from the container." },
              { name: "quantity", label: "Quantity", required: true },
              { name: "uom", label: "Unit of measure", required: true },
              { name: "source_type", label: "Source type", default: "manual", placeholder: "e.g. manual, machine" },
              { name: "source_id", label: "Source ID", hint: "Optional - e.g. a machine evidence reference." },
            ],
          },
          {
            path: "returns",
            label: "Record a return",
            fields: [
              { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
              { name: "dispensed_container_id", label: "Dispensed container ID", required: true },
              { name: "material_lot_id", label: "Material lot ID", hint: "Optional, if not derivable from the container." },
              { name: "quantity", label: "Quantity", required: true },
              { name: "uom", label: "Unit of measure", required: true },
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
              { name: "dispensed_container_id", label: "Dispensed container ID", required: true },
              { name: "loss_type", label: "Loss type", required: true, placeholder: "e.g. SAMPLE, REJECT, SPILL, APPROVED_LOSS" },
              { name: "quantity", label: "Quantity", required: true },
              { name: "uom", label: "Unit of measure", required: true },
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
              { name: "uom", label: "Unit of measure", required: true },
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
  const [targetQty, setTargetQty] = useState("");
  const [targetUom, setTargetUom] = useState("kg");
  const [toleranceLow, setToleranceLow] = useState("0.01");
  const [toleranceHigh, setToleranceHigh] = useState("0.01");

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
              material_id: materialId,
              target_qty: targetQty,
              target_uom: targetUom,
              tolerance_low: toleranceLow,
              tolerance_high: toleranceHigh,
            })
          );
        }}
      >
        <Field label="Batch" required hint={batches.length === 0 ? "No batches available yet." : undefined}>
          {batches.length > 0 ? (
            <Select value={batchId} onChange={(e) => setBatchId(e.target.value)} required autoFocus>
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
        <div className="grid grid-cols-4 gap-4">
          <Field label="Target quantity" required>
            <Input type="number" step="any" value={targetQty} onChange={(e) => setTargetQty(e.target.value)} required />
          </Field>
          <Field label="UOM" required>
            <Input value={targetUom} onChange={(e) => setTargetUom(e.target.value)} required />
          </Field>
          <Field label="Tolerance −" required>
            <Input type="number" step="any" value={toleranceLow} onChange={(e) => setToleranceLow(e.target.value)} required />
          </Field>
          <Field label="Tolerance +" required>
            <Input type="number" step="any" value={toleranceHigh} onChange={(e) => setToleranceHigh(e.target.value)} required />
          </Field>
        </div>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !batchId.trim() || !materialId || !siteId}>
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
  const canVerify = holdsAnyRole(me, ["Admin", "QC Reviewer"]);
  const canWeigh = holdsAnyRole(me, ["Admin", "Operator", "Supervisor"]);
  const canCancel = holdsAnyRole(me, ["Admin", "QA Releaser"]);

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
            −{o.tolerance_low} / +{o.tolerance_high}
          </span>
        </Fact>
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
  const [quantity, setQuantity] = useState("");
  const [tareValue, setTareValue] = useState("");
  const [readingValue, setReadingValue] = useState("");
  const [stable, setStable] = useState(true);
  const [deviceId, setDeviceId] = useState("");
  const [manualReason, setManualReason] = useState("");
  const [containerCode, setContainerCode] = useState("");
  const [takenQuantity, setTakenQuantity] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [reason, setReason] = useState("");

  const missingRequired =
    (step === "select_source" && !quantity) ||
    (step === "readings" && !readingValue) ||
    (step === "manual_reading" && (!readingValue || !manualReason)) ||
    (step === "complete" && (!sourceId || !takenQuantity || !containerCode)) ||
    (step === "cancel" && !reason);

  const withinTolerance =
    readingValue &&
    Number(readingValue) >= Number(order.target_qty) - Number(order.tolerance_low) &&
    Number(readingValue) <= Number(order.target_qty) + Number(order.tolerance_high);

  const extraFields = (
    <>
      {step === "select_source" && (
        <>
          <div className="grid grid-cols-2 gap-4">
            <EntityPickerField
              label="Material lot ID"
              value={lotId}
              onChange={setLotId}
              options={entities.materialLots}
              status={entities.materialLotsStatus}
              kind="material lot"
            />
            <Field label="Container ID">
              <Input value={containerId} onChange={(e) => setContainerId(e.target.value)} autoFocus />
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
            hint={`Target ${order.target_qty} −${order.tolerance_low} / +${order.tolerance_high}`}
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
            hint={`Target ${order.target_qty} −${order.tolerance_low} / +${order.tolerance_high}`}
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
          <Field label="Dispensing source ID" required hint="The source selected earlier for this order.">
            <Input value={sourceId} onChange={(e) => setSourceId(e.target.value)} required autoFocus />
          </Field>
          <Field label="Quantity actually taken" required>
            <Input
              type="number"
              step="any"
              value={takenQuantity}
              onChange={(e) => setTakenQuantity(e.target.value)}
              required
            />
          </Field>
          <Field label="Dispensed container code" required hint="The label applied to the dispensed container.">
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
              actual_taken_quantities: { [sourceId]: takenQuantity },
              container_code: containerCode,
            });
          case "cancel":
            return api.post(`${path}/cancel`, { ...base, reason });
        }
      }}
    />
  );
}
