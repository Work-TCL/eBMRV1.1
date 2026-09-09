"use client";

import { useState } from "react";
import { api, ApiError, canCreateDevice, canViewDevices, newIdempotencyKey, type MutationReceipt } from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";

interface DeviceUnit {
  unit_id: string;
  site_id: string;
  product_version_id: string;
  batch_id: string | null;
  device_lot_id: string | null;
  serial_number: string;
  udi_di: string | null;
  udi_pi: string | null;
  state: string;
  version: number;
  release_status: string | null;
}

export default function DevicesPage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [serial, setSerial] = useState("");
  const [unit, setUnit] = useState<DeviceUnit | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [holdOpen, setHoldOpen] = useState(false);

  const [lotId, setLotId] = useState("");
  const [readiness, setReadiness] = useState<Record<string, unknown> | null>(null);
  const [readinessError, setReadinessError] = useState<string | null>(null);

  async function lookup(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    setLoading(true);
    setError(null);
    setUnit(null);
    try {
      setUnit(
        await api.get<DeviceUnit>(
          `/devices/v1/units/by-serial/${encodeURIComponent(serial.trim())}?site_id=${siteId}`
        )
      );
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
    } finally {
      setLoading(false);
    }
  }

  async function checkReadiness(e: React.FormEvent) {
    e.preventDefault();
    setReadinessError(null);
    setReadiness(null);
    try {
      setReadiness(await api.get<Record<string, unknown>>(`/devices/v1/lots/${lotId.trim()}/release-readiness`));
    } catch (err) {
      setReadinessError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
    }
  }

  return (
    <div>
      <PageHead
        title="Devices"
        subtitle="Device units by serial, their UDI and release status, and lot release readiness."
      />

      <p className="hint mb-4">
        Device units are looked up one at a time by serial number rather than browsed as a list. Component,
        assembly, test and inspection history is not available yet.
      </p>

      {canCreateDevice(me) && <CreateLotCard siteId={siteId} />}

      <Card pad className="mb-4">
        <form onSubmit={lookup} className="flex flex-wrap items-end gap-4">
          <Field label="Serial number">
            <Input
              value={serial}
              onChange={(e) => setSerial(e.target.value)}
              placeholder="e.g. SN-000123"
              style={{ minWidth: 200, maxWidth: 300, width: "100%" }}
            />
          </Field>
          <Button type="submit" variant="secondary" disabled={loading || !serial.trim() || !siteId}>
            <Icon name="scan" /> {loading ? "Looking up…" : "Find unit"}
          </Button>
        </form>
      </Card>

      {error && (
        <Banner tone="critical" title="Unit not found">
          {error}
        </Banner>
      )}

      {unit && (
        <Card pad className="mb-4">
          <div className="flex justify-between items-center mb-3">
            <span className="font-semibold">
              {unit.serial_number} <WorkflowStatePill state={unit.state} />
            </span>
            {canViewDevices(me) && unit.state !== "HELD" && (
              <Button variant="danger" onClick={() => setHoldOpen(true)}>
                <Icon name="lock" /> Hold unit
              </Button>
            )}
          </div>
          <FactGrid>
            <Fact label="State">
              <WorkflowStatePill state={unit.state} />
            </Fact>
            <Fact label="Release status">
              {unit.release_status ? (
                <StatePill
                  state={unit.release_status.toLowerCase() === "released" ? "accepted" : "stale"}
                  icon={unit.release_status.toLowerCase() === "released" ? "check-circle" : "clock"}
                >
                  {unit.release_status}
                </StatePill>
              ) : (
                "—"
              )}
            </Fact>
            <Fact label="UDI-DI">{unit.udi_di ?? "—"}</Fact>
            <Fact label="UDI-PI">{unit.udi_pi ?? "—"}</Fact>
            <Fact label="Record version">{unit.version}</Fact>
            <IdFact label="Unit ID" value={unit.unit_id} />
            <IdFact label="Batch" value={unit.batch_id} />
            <IdFact label="Device lot" value={unit.device_lot_id} />
            <IdFact label="Product version" value={unit.product_version_id} />
          </FactGrid>
        </Card>
      )}

      <Card pad>
        <CardHeader title="Lot release readiness" />
        <form onSubmit={checkReadiness} className="flex flex-wrap items-end gap-4 mt-3">
          <Field label="Device lot ID">
            <Input value={lotId} onChange={(e) => setLotId(e.target.value)} style={{ minWidth: 200, maxWidth: 320, width: "100%" }} />
          </Field>
          <Button type="submit" variant="secondary" disabled={!lotId.trim()}>
            <Icon name="search" /> Check readiness
          </Button>
        </form>
        {readinessError && <p className="error-text mt-3">{readinessError}</p>}
        {readiness && (
          <div className="mt-3">
            <JsonPanel title="Readiness" value={readiness} />
          </div>
        )}
        {!readiness && !readinessError && (
          <EmptyState icon="package">Enter a device lot ID to check whether it can be released.</EmptyState>
        )}
      </Card>

      {holdOpen && unit && (
        <HoldModal
          unit={unit}
          onClose={() => setHoldOpen(false)}
          onDone={() => {
            setHoldOpen(false);
            setSerial(unit.serial_number);
            // Re-read the unit so the page shows the committed state, not an assumed one.
            api
              .get<DeviceUnit>(
                `/devices/v1/units/by-serial/${encodeURIComponent(unit.serial_number)}?site_id=${siteId}`
              )
              .then(setUnit)
              .catch(() => undefined);
          }}
        />
      )}
    </div>
  );
}

function HoldModal({
  unit,
  onClose,
  onDone,
}: {
  unit: DeviceUnit;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [reason, setReason] = useState("");

  return (
    <Modal open onClose={onClose} title={`Hold device unit ${unit.serial_number}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/devices/v1/units/${unit.unit_id}/hold`, {
              idempotency_key: newIdempotencyKey(),
              unit_id: unit.unit_id,
              expected_version: unit.version,
              reason,
            })
          );
        }}
      >
        <Field label="Reason" required hint="Part of the permanent device history record.">
          <textarea className="input" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} required />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="danger" disabled={busy || !reason.trim()}>
            {busy ? "Holding…" : "Hold unit"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function CreateLotCard({ siteId }: { siteId: string | null }) {
  const [productVersionId, setProductVersionId] = useState("");
  const [batchId, setBatchId] = useState("");
  const [udiDi, setUdiDi] = useState("");
  const [lotId, setLotId] = useState<string | null>(null);
  const [serials, setSerials] = useState("");
  const [unitCount, setUnitCount] = useState<number | null>(null);
  const { busy, error, run } = useCommand(() => undefined);

  function createLot(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    run(async () => {
      const receipt = await api.post<MutationReceipt>("/devices/v1/lots", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        product_version_id: productVersionId.trim(),
        batch_id: batchId.trim() || null,
        udi_di: udiDi.trim() || null,
      });
      setLotId(receipt.aggregate_id);
      setUnitCount(null);
    });
  }

  function createUnits(e: React.FormEvent) {
    e.preventDefault();
    if (!lotId) return;
    const units = serials
      .split(/[\n,]/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((serial_number) => ({ serial_number }));
    if (units.length === 0) return;
    run(async () => {
      const receipts = await api.post<MutationReceipt[]>("/devices/v1/units/bulk-create", {
        idempotency_key: newIdempotencyKey(),
        device_lot_id: lotId,
        units,
      });
      setUnitCount(receipts.length);
      setSerials("");
    });
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Device lot & unit assembly" />
      <form onSubmit={createLot} className="grid grid-cols-3 gap-4 mt-3">
        <Field label="Product version ID" required>
          <Input value={productVersionId} onChange={(e) => setProductVersionId(e.target.value)} required />
        </Field>
        <Field label="Batch ID" hint="Optional link to the producing batch.">
          <Input value={batchId} onChange={(e) => setBatchId(e.target.value)} />
        </Field>
        <Field label="UDI-DI" hint="Optional.">
          <Input value={udiDi} onChange={(e) => setUdiDi(e.target.value)} />
        </Field>
        <div style={{ gridColumn: "1 / -1" }}>
          <Button type="submit" variant="primary" disabled={busy || !productVersionId.trim() || !siteId}>
            {busy ? "Working…" : "Create device lot"}
          </Button>
        </div>
      </form>

      {lotId && (
        <div className="mt-4">
          <Banner tone="ok" title="Device lot created">
            Lot ID <span className="tabular">{lotId}</span>. Add serial units below.
          </Banner>
          <form onSubmit={createUnits} className="mt-3">
            <Field label="Serial numbers" hint="One per line (or comma-separated).">
              <textarea
                className="input"
                rows={4}
                value={serials}
                onChange={(e) => setSerials(e.target.value)}
                placeholder={"SN-000001\nSN-000002"}
              />
            </Field>
            <Button type="submit" variant="secondary" disabled={busy || !serials.trim()}>
              {busy ? "Working…" : "Bulk-create units"}
            </Button>
            {unitCount !== null && (
              <p className="fs-2 mt-2">Created {unitCount} unit{unitCount === 1 ? "" : "s"}.</p>
            )}
          </form>
        </div>
      )}

      {error && <p className="error-text mt-3">{error}</p>}
    </Card>
  );
}
