"use client";

import { useEffect, useState } from "react";
import {
  api,
  ApiError,
  formatDateTime,
  listAll,
  newIdempotencyKey,
  type ListQuery,
  type Material,
  type MaterialContainer,
  type MaterialLot,
  type MutationReceipt,
  type Paged,
} from "@/lib/api";
import { useEntityOptions } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { MaterialLotStatePill } from "@/components/ui/StatePill";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { EntityPickerField } from "@/components/shared/EntityPicker";

const STATUS_OPTIONS = ["", "quarantine", "released", "rejected", "consumed", "expired"];

export default function MaterialLotsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  const [receiveOpen, setReceiveOpen] = useState(false);
  const [dispositionLot, setDispositionLot] = useState<MaterialLot | null>(null);
  const [samplingLot, setSamplingLot] = useState<MaterialLot | null>(null);
  const [collectingOrder, setCollectingOrder] = useState<{ id: string; version: number } | null>(null);
  const [qualityStatusLot, setQualityStatusLot] = useState<MaterialLot | null>(null);
  const [retestingLot, setRetestingLot] = useState<MaterialLot | null>(null);

  function fetchLots(query: ListQuery): Promise<Paged<MaterialLot>> {
    const search = new URLSearchParams({
      page: String(query.page),
      page_size: String(query.page_size),
      sort_dir: query.sort_dir,
    });
    if (query.q) search.set("q", query.q);
    if (query.sort_by) search.set("sort_by", query.sort_by);
    if (statusFilter) search.set("status", statusFilter);
    return api.get<Paged<MaterialLot>>(`/material-lots?${search.toString()}`);
  }

  const columns: DataTableColumn<MaterialLot>[] = [
    {
      key: "internal_lot",
      header: "Lot",
      sortable: true,
      render: (l) => <span className="font-semibold tabular">{l.internal_lot}</span>,
    },
    {
      key: "material_code",
      header: "Material",
      sortable: true,
      render: (l) => (
        <span>
          {l.material_name} <span className="text-muted tabular">({l.material_code})</span>
        </span>
      ),
    },
    {
      key: "available_quantity",
      header: "Available",
      sortable: false,
      align: "right",
      render: (l) => (
        <span className="tabular">
          {l.available_quantity} / {l.received_quantity} {l.uom}
        </span>
      ),
    },
    { key: "received_at", header: "Received", sortable: true, render: (l) => formatDateTime(l.received_at) },
    { key: "released_at", header: "Released", sortable: true, render: (l) => formatDateTime(l.released_at) },
    { key: "expiry_date", header: "Expiry", sortable: true, render: (l) => l.expiry_date ?? "—" },
    { key: "status", header: "Status", sortable: true, render: (l) => <MaterialLotStatePill status={l.status} /> },
    {
      key: "actions",
      header: "",
      render: (l) => (
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="ghost" onClick={() => setQualityStatusLot(l)}>
            <Icon name="info" /> Quality status
          </Button>
          {(l.status === "quarantine" || l.status === "sampling") && (
            <Button size="sm" variant="secondary" onClick={() => setSamplingLot(l)}>
              <Icon name="flask" /> Sample
            </Button>
          )}
          {l.status === "quarantine" && (
            <Button size="sm" variant="secondary" onClick={() => setRetestingLot(l)}>
              <Icon name="refresh" /> Retest
            </Button>
          )}
          {l.status === "quarantine" && (
            <Button size="sm" variant="secondary" onClick={() => setDispositionLot(l)}>
              <Icon name="badge-check" /> Disposition
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHead
        title="Material lots"
        subtitle="Every received lot, its QC disposition status, and remaining quantity."
        action={
          <Button variant="primary" onClick={() => setReceiveOpen(true)}>
            <Icon name="plus" /> Receive lot
          </Button>
        }
      />

      <div className="flex items-center gap-3 mb-4">
        <span className="fs-3 text-muted">Filter by status</span>
        <Select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
          }}
          style={{ maxWidth: 200 }}
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s ? s[0].toUpperCase() + s.slice(1) : "All statuses"}
            </option>
          ))}
        </Select>
      </div>

      <Card>
        <CardHeader title="Material lots" />
        <DataTable
          key={statusFilter}
          columns={columns}
          fetchPage={fetchLots}
          rowKey={(l) => l.id}
          searchPlaceholder="Search by lot number or material…"
          emptyIcon="list-checks"
          emptyMessage="No material lots yet - receive one to get started."
          defaultSort={{ by: "received_at", dir: "desc" }}
          reloadToken={reloadToken}
        />
      </Card>

      {receiveOpen && (
        <ReceiveLotModal
          onClose={() => setReceiveOpen(false)}
          onDone={() => {
            setReceiveOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}

      {dispositionLot && (
        <DispositionModal
          lot={dispositionLot}
          onClose={() => setDispositionLot(null)}
          onDone={() => {
            setDispositionLot(null);
            setReloadToken((n) => n + 1);
          }}
        />
      )}

      {samplingLot && (
        <NewSamplingOrderModal
          lot={samplingLot}
          onClose={() => setSamplingLot(null)}
          onCreated={(order) => {
            setSamplingLot(null);
            setCollectingOrder(order);
            setReloadToken((n) => n + 1);
          }}
        />
      )}

      {collectingOrder && (
        <CollectSampleModal
          order={collectingOrder}
          onClose={() => setCollectingOrder(null)}
          onDone={() => {
            setCollectingOrder(null);
            setReloadToken((n) => n + 1);
          }}
        />
      )}

      {qualityStatusLot && <QualityStatusModal lot={qualityStatusLot} onClose={() => setQualityStatusLot(null)} />}

      {retestingLot && (
        <RetestModal
          lot={retestingLot}
          onClose={() => setRetestingLot(null)}
          onDone={() => {
            setRetestingLot(null);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
    </div>
  );
}

function ReceiveLotModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [materialId, setMaterialId] = useState("");
  const [internalLot, setInternalLot] = useState("");
  const [supplierLot, setSupplierLot] = useState("");
  const [quantity, setQuantity] = useState("");
  const [uom, setUom] = useState("");
  const [uomTouched, setUomTouched] = useState(false);
  const [expiryDate, setExpiryDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listAll<Material>("/materials").then((ms) => {
      setMaterials(ms);
      if (ms.length) {
        setMaterialId(ms[0].id);
        setUom(ms[0].uom);
      }
    });
  }, []);

  // Switching material re-seeds the unit with that material's standard unit — but only while the
  // operator hasn't overridden it, so picking "Liter" for this receipt survives a later material change.
  function selectMaterial(id: string) {
    setMaterialId(id);
    if (!uomTouched) {
      const material = materials.find((m) => m.id === id);
      if (material) setUom(material.uom);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!materialId) return;
    setBusy(true);
    setError(null);
    try {
      const material = materials.find((m) => m.id === materialId)!;
      await api.post<MutationReceipt>(`/materials/${materialId}/lots`, {
        idempotency_key: newIdempotencyKey(),
        material_id: materialId,
        site_id: material.site_id,
        internal_lot: internalLot,
        supplier_lot: supplierLot || null,
        received_quantity: quantity,
        uom: uom.trim() || material.uom,
        expiry_date: expiryDate || null,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to receive lot");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Receive material lot">
      <form onSubmit={onSubmit}>
        <Field label="Material" required>
          <Select value={materialId} onChange={(e) => selectMaterial(e.target.value)} required>
            {materials.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.code})
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Internal lot number" required hint="Must be unique across all materials.">
          <Input value={internalLot} onChange={(e) => setInternalLot(e.target.value)} required autoFocus />
        </Field>
        <Field label="Supplier lot">
          <Input value={supplierLot} onChange={(e) => setSupplierLot(e.target.value)} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Received quantity" required>
            <Input value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
          </Field>
          <Field label="Unit of measure" required hint="Defaults to the material's standard unit - change it if this lot was received in a different unit, e.g. L instead of mL.">
            <Input
              value={uom}
              onChange={(e) => {
                setUomTouched(true);
                setUom(e.target.value);
              }}
              required
            />
          </Field>
        </div>
        <Field label="Expiry date" hint="Optional.">
          <Input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
        </Field>
        {error && <p className="error-text mb-3">{error}</p>}
        <p className="hint mb-3">Received lots enter Quarantine automatically and cannot be issued until QC dispositions them.</p>
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !materialId}>
            {busy ? "Receiving…" : "Receive lot"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function DispositionModal({
  lot,
  onClose,
  onDone,
}: {
  lot: MaterialLot;
  onClose: () => void;
  onDone: () => void;
}) {
  const [decision, setDecision] = useState<"released" | "rejected">("released");
  const [reason, setReason] = useState("");

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/material-lots/${lot.id}/signature-challenges`}
      action="disposition"
      title={`QC disposition - lot ${lot.internal_lot}`}
      summary={
        <>
          {lot.material_name} ({lot.material_code}) - {lot.received_quantity} {lot.uom} received{" "}
          {lot.received_at ? formatDateTime(lot.received_at) : ""}
          {lot.expiry_date ? `, expires ${lot.expiry_date}` : ""}.
        </>
      }
      submitVariant={decision === "rejected" ? "danger" : "success"}
      reason="none"
      extraFields={
        <>
          <Field label="Decision" required>
            <Select value={decision} onChange={(e) => setDecision(e.target.value as "released" | "rejected")}>
              <option value="released">Release</option>
              <option value="rejected">Reject</option>
            </Select>
          </Field>
          <Field label="Reason" hint="Required for a reject decision in a real deployment; optional here.">
            <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
        </>
      }
      onSign={(p) =>
        api.post<MutationReceipt>(`/material-lots/${lot.id}/disposition`, {
          idempotency_key: p.idempotency_key,
          lot_id: lot.id,
          expected_version: lot.version,
          decision,
          reason: reason || null,
          challenge_id: p.challenge_id,
          reauth_password: p.reauth_password,
        })
      }
    />
  );
}

/** Document 20 (SPEC-MAT-004?) sampling orders — `app/modules/material/router.py`: `POST
 * /materials/v1/lots/{lot_id}/sampling-orders` (create) and `POST /sampling-orders/{id}/collect` (a
 * different router prefix entirely — not under /materials/v1). Only "quarantine" or "sampling" lots are
 * eligible (server-enforced). No GET exists for a sampling order (verified against router.py), so this
 * modal captures the id/version from the create receipt and hands it straight to `CollectSampleModal`
 * rather than making the operator note it down and paste it back in later. */
function NewSamplingOrderModal({
  lot,
  onClose,
  onCreated,
}: {
  lot: MaterialLot;
  onClose: () => void;
  onCreated: (order: { id: string; version: number }) => void;
}) {
  const entities = useEntityOptions();
  const [containers, setContainers] = useState<MaterialContainer[] | null>(null);
  const [selectedContainerIds, setSelectedContainerIds] = useState<string[]>([]);
  const [samplingPlanRef, setSamplingPlanRef] = useState("");
  const [assignedSamplerId, setAssignedSamplerId] = useState("");
  const [asepticEvidenceRef, setAsepticEvidenceRef] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .get<{ items: MaterialContainer[] }>(`/material-lots/${lot.id}/containers`)
      .then((r) => {
        if (!cancelled) setContainers(r.items);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not load containers");
      });
    return () => {
      cancelled = true;
    };
  }, [lot.id]);

  function toggleContainer(id: string) {
    setSelectedContainerIds((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c, id]));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const receipt = await api.post<MutationReceipt>(`/materials/v1/lots/${lot.id}/sampling-orders`, {
        idempotency_key: newIdempotencyKey(),
        lot_id: lot.id,
        expected_version: lot.version,
        sampling_plan_ref: samplingPlanRef.trim() || null,
        selected_container_ids: selectedContainerIds,
        assigned_sampler_user_id: assignedSamplerId,
        aseptic_evidence_ref: asepticEvidenceRef.trim() || null,
      });
      onCreated({ id: receipt.aggregate_id, version: receipt.resulting_version });
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not create sampling order");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={`Order sampling - lot ${lot.internal_lot}`}>
      <form onSubmit={submit}>
        <EntityPickerField
          label="Assigned sampler"
          required
          value={assignedSamplerId}
          onChange={setAssignedSamplerId}
          options={entities.users}
          status={entities.usersStatus}
          kind="user"
        />
        <Field label="Sampling plan reference" hint="Optional.">
          <Input value={samplingPlanRef} onChange={(e) => setSamplingPlanRef(e.target.value)} />
        </Field>
        <Field label="Aseptic evidence reference" hint="Optional - for a sterile-product sample draw.">
          <Input value={asepticEvidenceRef} onChange={(e) => setAsepticEvidenceRef(e.target.value)} />
        </Field>

        <Field label="Containers to sample from" required hint="At least one container must be selected.">
          {loadError ? (
            <p className="error-text">{loadError}</p>
          ) : containers === null ? (
            <p className="hint">Loading containers…</p>
          ) : containers.length === 0 ? (
            <p className="hint">This lot has no containers recorded.</p>
          ) : (
            <div className="sig-block">
              {containers.map((c) => (
                <label key={c.id} className="flex items-center gap-2 fs-2 mb-1">
                  <input
                    type="checkbox"
                    checked={selectedContainerIds.includes(c.id)}
                    onChange={() => toggleContainer(c.id)}
                  />
                  {c.container_code} - {c.current_quantity} {c.uom} ({c.container_status})
                </label>
              ))}
            </div>
          )}
        </Field>

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !assignedSamplerId.trim() || selectedContainerIds.length === 0}>
            {busy ? "Creating…" : "Create sampling order"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function CollectSampleModal({
  order,
  onClose,
  onDone,
}: {
  order: { id: string; version: number };
  onClose: () => void;
  onDone: () => void;
}) {
  const [orderId, setOrderId] = useState(order.id);
  const [expectedVersion, setExpectedVersion] = useState(String(order.version));
  const [sampleQuantity, setSampleQuantity] = useState("");
  const [sampleUom, setSampleUom] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post<MutationReceipt>(`/sampling-orders/${orderId.trim()}/collect`, {
        idempotency_key: newIdempotencyKey(),
        sampling_order_id: orderId.trim(),
        expected_version: Number(expectedVersion),
        sample_quantity: sampleQuantity.trim(),
        sample_uom: sampleUom.trim(),
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not record collection");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Record sample collection">
      <form onSubmit={submit}>
        <p className="fs-2 text-muted mb-3">
        No lookup exists for a sampling order -
          the id and version below come from the order you just created, or can be entered directly if
          already known.
        </p>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Sampling order ID" required>
            <Input value={orderId} onChange={(e) => setOrderId(e.target.value)} required />
          </Field>
          <Field label="Expected version" required>
            <Input type="number" value={expectedVersion} onChange={(e) => setExpectedVersion(e.target.value)} required />
          </Field>
          <Field label="Sample quantity" required>
            <Input value={sampleQuantity} onChange={(e) => setSampleQuantity(e.target.value)} required />
          </Field>
          <Field label="Sample UOM" required>
            <Input value={sampleUom} onChange={(e) => setSampleUom(e.target.value)} required />
          </Field>
        </div>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Not yet - collect later
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={busy || !orderId.trim() || !expectedVersion.trim() || !sampleQuantity.trim() || !sampleUom.trim()}
          >
            {busy ? "Recording…" : "Record collection"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function QualityStatusModal({ lot, onClose }: { lot: MaterialLot; onClose: () => void }) {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<Record<string, unknown>>(`/materials/v1/lots/${lot.id}/quality-status`)
      .then((s) => {
        if (!cancelled) setStatus(s);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not load quality status");
      });
    return () => {
      cancelled = true;
    };
  }, [lot.id]);

  return (
    <Modal open onClose={onClose} title={`Quality status - lot ${lot.internal_lot}`}>
      {error && <p className="error-text">{error}</p>}
      {!error && !status && <p className="hint">Loading…</p>}
      {status && <JsonPanel title="Quality status" value={status} />}
      <div className="flex justify-end mt-3">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </div>
    </Modal>
  );
}

function RetestModal({
  lot,
  onClose,
  onDone,
}: {
  lot: MaterialLot;
  onClose: () => void;
  onDone: () => void;
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post<MutationReceipt>(`/materials/v1/lots/${lot.id}/retest`, {
        idempotency_key: newIdempotencyKey(),
        lot_id: lot.id,
        expected_version: lot.version,
        reason: reason.trim(),
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not place lot on retest");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={`Send for retest - lot ${lot.internal_lot}`}>
      <form onSubmit={submit}>
        <p className="fs-3 mb-3">
          Distinct from Disposition (release/reject) - sends this lot back for retesting instead of a
          final release/reject decision.
        </p>
        <Field label="Reason" required>
          <textarea className="input" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} required autoFocus />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !reason.trim()}>
            {busy ? "Saving…" : "Send for retest"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
