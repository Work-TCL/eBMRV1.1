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
  type MaterialLot,
  type MutationReceipt,
  type Paged,
} from "@/lib/api";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Banner } from "@/components/ui/Banner";
import { MaterialLotStatePill } from "@/components/ui/StatePill";

const STATUS_OPTIONS = ["", "quarantine", "released", "rejected", "consumed", "expired"];

export default function MaterialLotsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  const [receiveOpen, setReceiveOpen] = useState(false);
  const [dispositionLot, setDispositionLot] = useState<MaterialLot | null>(null);

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
      render: (l) =>
        l.status === "quarantine" ? (
          <Button size="sm" variant="secondary" onClick={() => setDispositionLot(l)}>
            <Icon name="badge-check" /> Disposition
          </Button>
        ) : null,
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
          emptyMessage="No material lots yet — receive one to get started."
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
          <Field label="Unit of measure" required hint="Defaults to the material's standard unit — change it if this lot was received in a different unit, e.g. L instead of mL.">
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
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [decision, setDecision] = useState<"released" | "rejected">("released");
  const [reason, setReason] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .post<{ challenge_id: string }>(`/material-lots/${lot.id}/signature-challenges`, { action: "disposition" })
      .then((c) => setChallengeId(c.challenge_id))
      .catch(() => setError("Could not request signature challenge"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function confirm() {
    if (!challengeId) return;
    setBusy(true);
    setError(null);
    try {
      await api.post<MutationReceipt>(`/material-lots/${lot.id}/disposition`, {
        idempotency_key: newIdempotencyKey(),
        lot_id: lot.id,
        expected_version: lot.version,
        decision,
        reason: reason || null,
        challenge_id: challengeId,
        reauth_password: password,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Disposition failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={`QC disposition — lot ${lot.internal_lot}`}>
      <Banner tone="info" title={`${lot.material_name} (${lot.material_code})`}>
        {lot.received_quantity} {lot.uom} received {lot.received_at ? formatDateTime(lot.received_at) : ""}
        {lot.expiry_date ? `, expires ${lot.expiry_date}` : ""}.
      </Banner>

      <Field label="Decision" required>
        <Select value={decision} onChange={(e) => setDecision(e.target.value as "released" | "rejected")}>
          <option value="released">Release</option>
          <option value="rejected">Reject</option>
        </Select>
      </Field>
      <Field label="Reason" hint="Required for a reject decision in a real deployment; optional here.">
        <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
      </Field>
      <p className="fs-2 text-muted mb-2">
        Fresh authentication required — re-enter your password to sign (Part 11 step-up).
      </p>
      <Field label="Password" required>
        <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoFocus />
      </Field>
      {error && <p className="error-text mb-3">{error}</p>}
      <div className="flex justify-between gap-3 mt-2">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button
          variant={decision === "rejected" ? "danger" : "success"}
          disabled={busy || !challengeId || !password}
          onClick={confirm}
        >
          {busy ? "Signing…" : "Sign & submit"}
        </Button>
      </div>
    </Modal>
  );
}
