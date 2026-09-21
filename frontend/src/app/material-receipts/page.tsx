"use client";

import { useState } from "react";
import {
  api,
  formatDateTime,
  hasPermission,
  newIdempotencyKey,
  type ListQuery,
  type Me,
  type MutationReceipt,
  type Paged,
} from "@/lib/api";
import { useEntityOptions, useMe, useSiteId } from "@/lib/hooks";
import { useCommand } from "@/components/shared/RecordDetailShell";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { UomSelect } from "@/components/ui/UomSelect";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid } from "@/components/ui/FactGrid";
import { Banner } from "@/components/ui/Banner";
import { WorkflowStatePill } from "@/components/ui/StatePill";

// app/modules/material/commands.py CreateMaterialReceiptCommand / ExamineReceiptCommand,
// app/modules/material/router.py _receipt_dict()/list_material_receipts(). Document 19 (SPEC-MAT-002A)
// receiving workflow — the step before a lot exists at all: a receipt records what arrived (incl.
// which supplier/manufacturer), then examining it either creates the Material lot in quarantine or
// holds the receipt as a discrepancy (damage, seal, contamination, identity mismatch, or an unapproved
// supplier — RCV-FR-005). Unsigned, RBAC-gated only — no Document 106 signature row for either step.
interface MaterialReceipt {
  id: string;
  site_id: string;
  receipt_number: string;
  po_reference: string | null;
  material_id: string;
  material_code: string;
  material_name: string;
  supplier_id: string | null;
  supplier_code: string | null;
  supplier_name: string | null;
  manufacturer_id: string | null;
  manufacturer_code: string | null;
  manufacturer_name: string | null;
  supplier_lot: string | null;
  manufacturer_lot: string | null;
  carrier_reference: string | null;
  received_gross_quantity: string;
  received_net_quantity: string | null;
  accepted_quantity: string | null;
  uom: string;
  manufacture_date: string | null;
  expiry_date: string | null;
  retest_date: string | null;
  shipment_condition_status: string | null;
  coa_document_hash: string | null;
  state: string;
  discrepancy_type: string | null;
  discrepancy_reason: string | null;
  received_at: string | null;
  version: number;
}

// material_receipt.create/.examine share one grant (Admin/Operator/Supervisor).
const canReceive = (me: Me | null) => hasPermission(me, "material_receipt.create");

function fetchReceipts(query: ListQuery): Promise<Paged<MaterialReceipt>> {
  const search = new URLSearchParams({
    page: String(query.page),
    page_size: String(query.page_size),
    sort_dir: query.sort_dir,
  });
  if (query.q) search.set("q", query.q);
  if (query.sort_by) search.set("sort_by", query.sort_by);
  return api.get<Paged<MaterialReceipt>>(`/materials/v1/receipts?${search.toString()}`);
}

export default function MaterialReceiptsPage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [reloadToken, setReloadToken] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [viewing, setViewing] = useState<MaterialReceipt | null>(null);
  const [examining, setExamining] = useState<MaterialReceipt | null>(null);

  const columns: DataTableColumn<MaterialReceipt>[] = [
    {
      key: "receipt_number",
      header: "Receipt",
      sortable: true,
      render: (r) => <span className="font-semibold tabular">{r.receipt_number}</span>,
    },
    {
      key: "material_code",
      header: "Material",
      sortable: true,
      render: (r) => (
        <span>
          {r.material_name} <span className="text-muted tabular">({r.material_code})</span>
        </span>
      ),
    },
    {
      key: "received_gross_quantity",
      header: "Quantity",
      align: "right",
      render: (r) => (
        <span className="tabular">
          {r.received_gross_quantity} {r.uom}
        </span>
      ),
    },
    { key: "received_at", header: "Received", sortable: true, render: (r) => formatDateTime(r.received_at) },
    { key: "state", header: "Status", sortable: true, render: (r) => <WorkflowStatePill state={r.state} /> },
    {
      key: "note",
      header: "Note",
      render: (r) =>
        r.state === "discrepancy_hold" ? (
          <span className="error-text fs-2">{r.discrepancy_reason ?? r.discrepancy_type}</span>
        ) : (
 <span className="text-muted"></span>
        ),
    },
    {
      key: "actions",
      header: "",
      render: (r) =>
        r.state === "received" && canReceive(me) ? (
          <Button
            size="sm"
            variant="secondary"
            onClick={(e) => {
              e.stopPropagation();
              setExamining(r);
            }}
          >
            <Icon name="badge-check" /> Examine
          </Button>
        ) : null,
    },
  ];

  return (
    <div>
      <PageHead
        title="Material receipts"
 subtitle="What arrived, from whom, and its examination the step before a material lot exists."
        action={
          canReceive(me) ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> Log a receipt
            </Button>
          ) : undefined
        }
      />

      <Card>
        <CardHeader title="Material receipts" />
        <DataTable
          columns={columns}
          fetchPage={fetchReceipts}
          rowKey={(r) => r.id}
          searchPlaceholder="Search by receipt number or material…"
          emptyIcon="list-checks"
 emptyMessage="No material receipts yet log one to get started."
          defaultSort={{ by: "received_at", dir: "desc" }}
          reloadToken={reloadToken}
          onRowClick={(r) => setViewing(r)}
        />
      </Card>

      {viewing && (
        <ReceiptDetailModal
          receipt={viewing}
          me={me}
          onClose={() => setViewing(null)}
          onExamine={() => {
            setExamining(viewing);
            setViewing(null);
          }}
        />
      )}

      {createOpen && (
        <CreateReceiptModal
          siteId={siteId}
          onClose={() => setCreateOpen(false)}
          onDone={() => {
            setCreateOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}

      {examining && (
        <ExamineReceiptModal
          receipt={examining}
          onClose={() => setExamining(null)}
          onDone={() => {
            setExamining(null);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
    </div>
  );
}

function ReceiptDetailModal({
  receipt: r,
  me,
  onClose,
  onExamine,
}: {
  receipt: MaterialReceipt;
  me: Me | null;
  onClose: () => void;
  onExamine: () => void;
}) {
  return (
    <Modal
      open
      onClose={onClose}
      title={
        <span className="flex items-center gap-3">
          {r.receipt_number} <WorkflowStatePill state={r.state} />
        </span>
      }
      large
    >
      {r.state === "discrepancy_hold" && (
 <Banner tone="critical" title={`On hold ${r.discrepancy_type ?? "discrepancy"}`}>
          {r.discrepancy_reason ?? "Examination raised a discrepancy; this receipt did not produce a lot."}
        </Banner>
      )}
      {r.state === "examined" && (
 <Banner tone="ok" title="Examined lot created">
          This receipt passed examination. Find its lot under Material lots, filtered by this receipt&rsquo;s material.
        </Banner>
      )}

      <FactGrid>
        <Fact label="Material">
          {r.material_name} <span className="text-muted tabular">({r.material_code})</span>
        </Fact>
 <Fact label="PO reference">{r.po_reference ?? ""}</Fact>
 <Fact label="Carrier / shipment reference">{r.carrier_reference ?? ""}</Fact>
        <Fact label="Gross quantity">
          {r.received_gross_quantity} {r.uom}
        </Fact>
 <Fact label="Net quantity">{r.received_net_quantity ? `${r.received_net_quantity} ${r.uom}` : ""}</Fact>
 <Fact label="Accepted quantity">{r.accepted_quantity ? `${r.accepted_quantity} ${r.uom}` : ""}</Fact>
 <Fact label="Supplier's lot number">{r.supplier_lot ?? ""}</Fact>
 <Fact label="Manufacturer's lot number">{r.manufacturer_lot ?? ""}</Fact>
 <Fact label="Manufacture date">{r.manufacture_date ?? ""}</Fact>
 <Fact label="Expiry date">{r.expiry_date ?? ""}</Fact>
 <Fact label="Retest date">{r.retest_date ?? ""}</Fact>
 <Fact label="Shipment condition">{r.shipment_condition_status ?? ""}</Fact>
 <Fact label="CoA document hash">{r.coa_document_hash ?? ""}</Fact>
        <Fact label="Received">{formatDateTime(r.received_at)}</Fact>
        <Fact label="Record version">{r.version}</Fact>
        <Fact label="Supplier">
          {r.supplier_name ? (
            <>
              {r.supplier_name} <span className="text-muted tabular">({r.supplier_code})</span>
            </>
          ) : (
 ""
          )}
        </Fact>
        <Fact label="Manufacturer">
          {r.manufacturer_name ? (
            <>
              {r.manufacturer_name} <span className="text-muted tabular">({r.manufacturer_code})</span>
            </>
          ) : (
 ""
          )}
        </Fact>
      </FactGrid>

      <div className="flex justify-between gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        {r.state === "received" && canReceive(me) && (
          <Button variant="primary" onClick={onExamine}>
            <Icon name="badge-check" /> Examine receipt
          </Button>
        )}
      </div>
    </Modal>
  );
}

function CreateReceiptModal({
  siteId,
  onClose,
  onDone,
}: {
  siteId: string | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const entities = useEntityOptions();
  const [receiptNumber, setReceiptNumber] = useState("");
  const [materialId, setMaterialId] = useState("");
  const [poReference, setPoReference] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [manufacturerId, setManufacturerId] = useState("");
  const [supplierLot, setSupplierLot] = useState("");
  const [manufacturerLot, setManufacturerLot] = useState("");
  const [carrierReference, setCarrierReference] = useState("");
  const [grossQuantity, setGrossQuantity] = useState("");
  const [netQuantity, setNetQuantity] = useState("");
  const [acceptedQuantity, setAcceptedQuantity] = useState("");
  const [uom, setUom] = useState("");
  const [manufactureDate, setManufactureDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [retestDate, setRetestDate] = useState("");
  const [shipmentCondition, setShipmentCondition] = useState("");
  const [coaHash, setCoaHash] = useState("");

  return (
    <Modal open onClose={onClose} title="Log a material receipt" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post<MutationReceipt>("/materials/v1/receipts", {
              idempotency_key: newIdempotencyKey(),
              site_id: siteId,
              receipt_number: receiptNumber,
              material_id: materialId,
              po_reference: poReference || null,
              supplier_id: supplierId || null,
              manufacturer_id: manufacturerId || null,
              supplier_lot: supplierLot || null,
              manufacturer_lot: manufacturerLot || null,
              carrier_reference: carrierReference || null,
              received_gross_quantity: grossQuantity,
              received_net_quantity: netQuantity || null,
              accepted_quantity: acceptedQuantity || null,
              uom,
              manufacture_date: manufactureDate || null,
              expiry_date: expiryDate || null,
              retest_date: retestDate || null,
              shipment_condition_status: shipmentCondition || null,
              coa_document_hash: coaHash || null,
            })
          );
        }}
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Receipt number" required>
            <Input value={receiptNumber} onChange={(e) => setReceiptNumber(e.target.value)} required autoFocus />
          </Field>
          <EntityPickerField
            label="Material" required
            value={materialId} onChange={setMaterialId}
            options={entities.materials} status={entities.materialsStatus} kind="material"
          />
          <Field label="PO reference">
            <Input value={poReference} onChange={(e) => setPoReference(e.target.value)} />
          </Field>
          <Field label="Carrier / shipment reference">
            <Input value={carrierReference} onChange={(e) => setCarrierReference(e.target.value)} />
          </Field>
          <EntityPickerField
            label="Supplier"
            hint="Leave blank if received directly from the manufacturer with no separate supplier."
            value={supplierId} onChange={setSupplierId}
            options={entities.suppliers} status={entities.suppliersStatus} kind="supplier"
          />
          <EntityPickerField
            label="Manufacturer" hint="Only if different from the supplier."
            value={manufacturerId} onChange={setManufacturerId}
            options={entities.suppliers} status={entities.suppliersStatus} kind="supplier"
          />
          <Field label="Supplier's lot number" hint="From the supplier's label or certificate of analysis.">
            <Input value={supplierLot} onChange={(e) => setSupplierLot(e.target.value)} />
          </Field>
          <Field label="Manufacturer's lot number">
            <Input value={manufacturerLot} onChange={(e) => setManufacturerLot(e.target.value)} />
          </Field>
          <Field label="Received quantity (gross)" required hint="Kept as exact text.">
            <Input value={grossQuantity} onChange={(e) => setGrossQuantity(e.target.value)} required />
          </Field>
          <UomSelect value={uom} onChange={setUom} required />
 <Field label="Received quantity (net)" hint="Optional if different from gross.">
            <Input value={netQuantity} onChange={(e) => setNetQuantity(e.target.value)} />
          </Field>
          <Field label="Accepted quantity" hint="Defaults to the gross quantity if left blank.">
            <Input value={acceptedQuantity} onChange={(e) => setAcceptedQuantity(e.target.value)} />
          </Field>
          <Field label="Manufacture date">
            <Input type="date" value={manufactureDate} onChange={(e) => setManufactureDate(e.target.value)} />
          </Field>
          <Field label="Expiry date">
            <Input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
          </Field>
          <Field label="Retest date">
            <Input type="date" value={retestDate} onChange={(e) => setRetestDate(e.target.value)} />
          </Field>
          <Field label="Shipment condition">
            <Input value={shipmentCondition} onChange={(e) => setShipmentCondition(e.target.value)} placeholder="e.g. ambient, refrigerated" />
          </Field>
          <div style={{ gridColumn: "1 / -1" }}>
 <Field label="CoA document hash" hint="Optional SHA-256 hash of the Certificate of Analysis evidence, if available.">
              <Input value={coaHash} onChange={(e) => setCoaHash(e.target.value)} />
            </Field>
          </div>
        </div>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !materialId || !receiptNumber.trim() || !grossQuantity.trim() || !uom.trim()}>
            {busy ? "Logging…" : "Log receipt"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

const YES_NO = [
 { value: "", label: "Select" },
  { value: "true", label: "Yes" },
  { value: "false", label: "No" },
];

function YesNoField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <Field label={label} required>
      <Select value={value} onChange={(e) => onChange(e.target.value)}>
        {YES_NO.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>
    </Field>
  );
}

function ExamineReceiptModal({
  receipt,
  onClose,
  onDone,
}: {
  receipt: MaterialReceipt;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [identityConfirmed, setIdentityConfirmed] = useState("");
  const [labelingOk, setLabelingOk] = useState("");
  const [damageObserved, setDamageObserved] = useState("");
  const [sealBroken, setSealBroken] = useState("");
  const [contaminationObserved, setContaminationObserved] = useState("");
  const [internalLot, setInternalLot] = useState("");
  const [containerCount, setContainerCount] = useState("1");
  const [examinationNotes, setExaminationNotes] = useState("");
  const [discrepancyReason, setDiscrepancyReason] = useState("");

  // All five checks are required (no default) on the backend command — a real visual examination has
  // no "unanswered" state, so none of these silently default; the submit button itself stays disabled
  // until every one has an explicit Yes/No, rather than letting an unanswered check quietly become
  // "no problem observed".
  const allAnswered = [identityConfirmed, labelingOk, damageObserved, sealBroken, contaminationObserved].every(
    (v) => v === "true" || v === "false"
  );

  return (
 <Modal open onClose={onClose} title={`Examine receipt ${receipt.receipt_number}`} large>
      <p className="fs-2 text-muted mb-3">
        Visual examination and identity/supplier check. A clean result creates the material lot (in
        quarantine); damage, a broken seal, contamination, an identity mismatch, or an unapproved
        supplier holds the receipt as a discrepancy instead.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post<MutationReceipt>(`/materials/v1/receipts/${receipt.id}/examine`, {
              idempotency_key: newIdempotencyKey(),
              receipt_id: receipt.id,
              expected_version: receipt.version,
              identity_confirmed: identityConfirmed === "true",
              labeling_ok: labelingOk === "true",
              damage_observed: damageObserved === "true",
              seal_broken: sealBroken === "true",
              contamination_observed: contaminationObserved === "true",
              internal_lot: internalLot,
              container_count: containerCount ? Number(containerCount) : 1,
              examination_notes: examinationNotes || null,
              discrepancy_reason: discrepancyReason || null,
            })
          );
        }}
      >
        <div className="grid grid-cols-2 gap-4">
          <YesNoField label="Identity confirmed" value={identityConfirmed} onChange={setIdentityConfirmed} />
          <YesNoField label="Labeling correct" value={labelingOk} onChange={setLabelingOk} />
          <YesNoField label="Damage observed" value={damageObserved} onChange={setDamageObserved} />
          <YesNoField label="Seal broken" value={sealBroken} onChange={setSealBroken} />
          <YesNoField label="Contamination observed" value={contaminationObserved} onChange={setContaminationObserved} />
          <Field label="Container count" hint="Defaults to 1 if left blank.">
            <Input type="number" value={containerCount} onChange={(e) => setContainerCount(e.target.value)} />
          </Field>
        </div>
        <Field label="Internal lot number" required hint="Assigned to the material lot this examination creates (only used when the result is clean).">
          <Input value={internalLot} onChange={(e) => setInternalLot(e.target.value)} required autoFocus />
        </Field>
        <Field label="Examination notes">
          <textarea className="input" rows={2} value={examinationNotes} onChange={(e) => setExaminationNotes(e.target.value)} />
        </Field>
        <Field label="Discrepancy reason" hint="Required when identity is not confirmed; optional (auto-filled) for every other discrepancy type.">
          <textarea className="input" rows={2} value={discrepancyReason} onChange={(e) => setDiscrepancyReason(e.target.value)} />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !allAnswered || !internalLot.trim()}>
            {busy ? "Submitting…" : "Examine receipt"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
