"use client";

import { useEffect, useState } from "react";
import { api, ApiError, canCreateDevice, canExecuteDevice, newIdempotencyKey, pagedFetcher, type MutationReceipt } from "@/lib/api";
import { useEntityOptions, useMe, useSiteId, type EntityOption, type EntityOptionsStatus } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState, Table } from "@/components/ui/Table";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field, RowButtonSlot } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { ProductVersionPickerField } from "@/components/shared/ProductVersionPicker";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";

interface ReleaseReadiness {
  lot_id: string;
  lot_udi_di: string | null;
  unit_count: number;
  blocked_unit_ids: string[];
  blocked_units: { unit_id: string; serial_number: string | null }[];
  eligible: boolean;
  note: string;
}

interface DeviceUnit {
  unit_id: string;
  site_id: string;
  product_version_id: string;
  product_code: string | null;
  product_name: string | null;
  batch_id: string | null;
  batch_number: string | null;
  device_lot_id: string | null;
  device_lot_label: string | null;
  serial_number: string | null;
  udi_di: string | null;
  udi_pi: string | null;
  state: string;
  version: number;
  release_status: string | null;
}

/** Real reference data for the "Device lot" picker -- a lot has no separate master table of its own,
 * it's a `DeviceUnit` row with `serial_number IS NULL` (DHR-FR-001/002's own "lot-scope" shape) --
 * `GET /devices/v1/units?lots_only=true` is that exact subset. Local to this page only, same shape as
 * `usePackagingRuns`/`useEligibleSterileItems` elsewhere. */
function useDeviceLots(siteId: string | null): { options: EntityOption[]; status: EntityOptionsStatus } {
  const [options, setOptions] = useState<EntityOption[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("loading");

  useEffect(() => {
    if (!siteId) return;
    let cancelled = false;
    api
      .get<{ items: DeviceUnit[] }>(`/devices/v1/units?site_id=${siteId}&lots_only=true&page_size=100`)
      .then((res) => {
        if (cancelled) return;
        setOptions(
          res.items.map((u) => ({
            value: u.unit_id,
            label: [u.udi_di, u.batch_number, u.product_code].filter(Boolean).join(" - ") || u.unit_id.slice(0, 8) + "…",
          }))
        );
        setStatus(res.items.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [siteId]);

  return { options, status };
}

function unitColumns(onOpen: (unit: DeviceUnit) => void): DataTableColumn<DeviceUnit>[] {
  return [
    {
      key: "serial_number",
      header: "Serial",
      sortable: true,
      render: (u) =>
        u.serial_number ? (
          <span className="fs-2 font-semibold tabular">{u.serial_number}</span>
        ) : (
          <StatePill state="unknown" icon="package">Lot</StatePill>
        ),
    },
    {
      key: "product",
      header: "Product",
      render: (u) => <span className="fs-2">{u.product_code ? `${u.product_name} (${u.product_code})` : u.product_version_id}</span>,
    },
    { key: "batch_number", header: "Batch", render: (u) => <span className="fs-2">{u.batch_number ?? "—"}</span> },
    { key: "device_lot_label", header: "Device lot", render: (u) => <span className="fs-2">{u.device_lot_label ?? (u.device_lot_id ? u.device_lot_id.slice(0, 8) + "…" : "—")}</span> },
    { key: "state", header: "State", sortable: true, render: (u) => <WorkflowStatePill state={u.state} /> },
    {
      key: "open",
      header: "",
      align: "right",
      render: (u) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={(e) => {
            e.stopPropagation();
            onOpen(u);
          }}
        >
          Open
        </Button>
      ),
    },
  ];
}

export default function DevicesPage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [unit, setUnit] = useState<DeviceUnit | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [holdOpen, setHoldOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const [lotId, setLotId] = useState("");
  const [readiness, setReadiness] = useState<ReleaseReadiness | null>(null);
  const [readinessError, setReadinessError] = useState<string | null>(null);
  const [readinessLoading, setReadinessLoading] = useState(false);
  const deviceLots = useDeviceLots(siteId);

  const fetchUnits = pagedFetcher<DeviceUnit>("/devices/v1/units", () => ({ site_id: siteId ?? "" }));

  async function openUnit(row: DeviceUnit) {
    setError(null);
    try {
      setUnit(await api.get<DeviceUnit>(`/devices/v1/units/${row.unit_id}/history`));
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
    }
  }

  async function checkReadiness(e: React.FormEvent) {
    e.preventDefault();
    setReadinessError(null);
    setReadiness(null);
    setReadinessLoading(true);
    try {
      setReadiness(await api.get<ReleaseReadiness>(`/devices/v1/lots/${lotId.trim()}/release-readiness`));
    } catch (err) {
      setReadinessError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
    } finally {
      setReadinessLoading(false);
    }
  }

  return (
    <div>
      <PageHead
        title="Devices"
        subtitle="Device units and lots, their UDI and release status, and lot release readiness."
      />

      {canCreateDevice(me) && <CreateLotCard siteId={siteId} onCreated={() => setReloadToken((n) => n + 1)} />}

      <Card pad className="mb-4">
        <CardHeader title="Device units & lots" meta="" />
        {siteId ? (
          <DataTable
            columns={unitColumns(openUnit)}
            fetchPage={fetchUnits}
            rowKey={(u) => u.unit_id}
            searchPlaceholder="Search serial number…"
            emptyMessage={<>No device units yet - use &quot;Device lot &amp; unit assembly&quot; above to add one.</>}
            defaultSort={{ by: "created_at", dir: "desc" }}
            onRowClick={openUnit}
            reloadToken={reloadToken}
          />
        ) : (
          <p className="hint mt-2">Loading…</p>
        )}
      </Card>

      {error && (
        <Banner tone="critical" title="Lookup failed">
          {error}
        </Banner>
      )}

      {unit && (
        <Modal
          open
          onClose={() => setUnit(null)}
          large
          title={
            <span className="flex items-center gap-3">
              {unit.serial_number ?? "Device lot"} <WorkflowStatePill state={unit.state} />
            </span>
          }
        >
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
            {unit.batch_number ? <Fact label="Batch">{unit.batch_number}</Fact> : <IdFact label="Batch" value={unit.batch_id} />}
            {unit.device_lot_id && (
              <Fact label="Device lot">{unit.device_lot_label ?? unit.device_lot_id}</Fact>
            )}
            {unit.product_code ? (
              <Fact label="Product">{`${unit.product_name} (${unit.product_code})`}</Fact>
            ) : (
              <IdFact label="Product version" value={unit.product_version_id} />
            )}
          </FactGrid>
          {canExecuteDevice(me) && unit.state !== "HELD" && (
            <div className="mt-3">
              <Button variant="danger" onClick={() => setHoldOpen(true)}>
                <Icon name="lock" /> Hold unit
              </Button>
            </div>
          )}
        </Modal>
      )}

      <Card pad>
        <CardHeader title="Lot release readiness" />
        {/* items-start, not items-end: EntityPickerField can carry its own hint text (loading/empty/
           error states), which would make that Field taller than a bare Button next to it — items-end
           would then bottom-align the row to the hint instead of the input itself, dragging the button
           down below where it visually belongs. RowButtonSlot keeps the button level with the input
           either way (same fix already applied elsewhere, e.g. genealogy/page.tsx, sterilization/
           page.tsx). */}
        <form onSubmit={checkReadiness} className="flex flex-wrap items-start gap-4 mt-3">
          <EntityPickerField
            label="Device lot"
            value={lotId}
            onChange={setLotId}
            options={deviceLots.options}
            status={deviceLots.status}
            kind="device lot"
          />
          <RowButtonSlot>
            <Button type="submit" variant="secondary" disabled={readinessLoading || !lotId.trim()}>
              <Icon name="search" /> {readinessLoading ? "Checking…" : "Check readiness"}
            </Button>
          </RowButtonSlot>
        </form>
        {readinessError && <p className="error-text mt-3">{readinessError}</p>}
        {readiness && (
          <div className="mt-3">
            <Banner
              tone={readiness.eligible ? "ok" : "critical"}
              title={readiness.eligible ? "Eligible for release" : "Not eligible for release"}
            >
              {readiness.note}
            </Banner>
            <FactGrid>
              <Fact label="Lot">{readiness.lot_udi_di ?? readiness.lot_id.slice(0, 8) + "…"}</Fact>
              <Fact label="Unit count">{readiness.unit_count}</Fact>
              <Fact label="Eligible">
                {readiness.eligible ? (
                  <StatePill state="accepted" icon="check-circle">Yes</StatePill>
                ) : (
                  <StatePill state="blocked" icon="lock">No</StatePill>
                )}
              </Fact>
            </FactGrid>
            {readiness.blocked_units.length > 0 && (
              <div className="mt-3">
                <h4 className="fs-2 font-semibold mb-2">Blocked units ({readiness.blocked_units.length})</h4>
                <Table>
                  <thead>
                    <tr>
                      <th>Unit</th>
                      <th>State</th>
                    </tr>
                  </thead>
                  <tbody>
                    {readiness.blocked_units.map((b) => (
                      <tr key={b.unit_id}>
                        <td className="fs-2 tabular">{b.serial_number ?? "(lot)"}</td>
                        <td>
                          <StatePill state="blocked" icon="lock">HELD</StatePill>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            )}
          </div>
        )}
        {!readiness && !readinessError && (
          <EmptyState icon="package">Pick a device lot to check whether it can be released.</EmptyState>
        )}
      </Card>

      {holdOpen && unit && (
        <HoldModal
          unit={unit}
          onClose={() => setHoldOpen(false)}
          onDone={() => {
            setHoldOpen(false);
            setReloadToken((n) => n + 1);
            // Re-read the unit so the detail card shows the committed state, not an assumed one.
            api
              .get<DeviceUnit>(`/devices/v1/units/${unit.unit_id}/history`)
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
    <Modal open onClose={onClose} title={`Hold device unit ${unit.serial_number ?? unit.unit_id.slice(0, 8) + "…"}`}>
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

function CreateLotCard({ siteId, onCreated }: { siteId: string | null; onCreated: () => void }) {
  const [productVersionId, setProductVersionId] = useState("");
  const [batchId, setBatchId] = useState("");
  const [udiDi, setUdiDi] = useState("");
  const [lotId, setLotId] = useState<string | null>(null);
  const [serials, setSerials] = useState("");
  const [unitCount, setUnitCount] = useState<number | null>(null);
  const { busy, error, run } = useCommand(() => undefined);
  const entities = useEntityOptions();

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
      onCreated();
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
      onCreated();
    });
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Device lot & unit assembly" />
      <form onSubmit={createLot} className="grid grid-cols-3 gap-4 mt-3">
        <ProductVersionPickerField
          label="Product version ID"
          required
          value={productVersionId}
          onChange={setProductVersionId}
        />
        <EntityPickerField
          label="Batch ID"
          hint="Optional link to the producing batch."
          value={batchId}
          onChange={setBatchId}
          options={entities.batches}
          status={entities.batchesStatus}
          kind="batch"
        />
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
