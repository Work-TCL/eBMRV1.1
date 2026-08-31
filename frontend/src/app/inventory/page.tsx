"use client";

import { useEffect, useState } from "react";
import {
  api,
  ApiError,
  formatDateTime,
  holdsAnyRole,
  listAll,
  newIdempotencyKey,
  pagedFetcher,
  type Material,
} from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Tabs } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { useCommand } from "@/components/qms/QmsDetailShell";

interface AvailabilityRow {
  material_lot_id: string;
  internal_lot: string;
  container_id: string;
  location_id: string;
  location_code: string;
  available: string;
  uom: string;
  expiry_date: string | null;
}

interface LedgerRow {
  id: string;
  container_id: string | null;
  transaction_type: string;
  quantity: string;
  uom: string;
  from_location_id: string | null;
  to_location_id?: string | null;
  occurred_at?: string;
}

type Action = "reserve" | "transfer" | "cycle_count" | "adjustment";

const ACTION_LABEL: Record<Action, string> = {
  reserve: "Reserve material",
  transfer: "Transfer",
  cycle_count: "Cycle count",
  adjustment: "Request adjustment",
};

export default function InventoryPage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [materials, setMaterials] = useState<Material[]>([]);
  const [materialId, setMaterialId] = useState("");
  const [availability, setAvailability] = useState<AvailabilityRow[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState<Action | null>(null);
  const [ledgerLotId, setLedgerLotId] = useState("");
  const [activeLedgerLot, setActiveLedgerLot] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const canMove = holdsAnyRole(me, ["Admin", "Operator", "Supervisor"]);
  const canApprove = holdsAnyRole(me, ["Admin", "QA Releaser"]);

  // Populated once for the material picker; Phase 1 row counts sit well inside listAll's 100 cap.
  useEffect(() => {
    let cancelled = false;
    listAll<Material>("/materials")
      .then((rows) => {
        if (!cancelled) setMaterials(rows);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  async function loadAvailability(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId || !materialId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<{ items: AvailabilityRow[] }>(
        `/inventory/v1/availability?material_id=${materialId}&site_id=${siteId}`
      );
      setAvailability(result.items);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not load availability");
      setAvailability(null);
    } finally {
      setLoading(false);
    }
  }

  const ledgerColumns: DataTableColumn<LedgerRow>[] = [
    {
      key: "occurred_at",
      header: "When",
      sortable: true,
      render: (t) => <span className="tabular fs-2">{t.occurred_at ? formatDateTime(t.occurred_at) : "—"}</span>,
    },
    { key: "transaction_type", header: "Type", render: (t) => <span className="fs-2">{t.transaction_type}</span> },
    {
      key: "quantity",
      header: "Quantity",
      align: "right",
      render: (t) => (
        <span className="tabular">
          {t.quantity} {t.uom}
        </span>
      ),
    },
    {
      key: "container_id",
      header: "Container",
      render: (t) => (
        <span className="tabular fs-2" style={{ wordBreak: "break-all" }}>
          {t.container_id ?? "—"}
        </span>
      ),
    },
  ];

  return (
    <div>
      <PageHead
        title="Inventory"
        subtitle="Document 20/22 — availability, reservations, movements, cycle counts and the lot ledger."
        action={
          canMove ? (
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setAction("transfer")}>
                Transfer
              </Button>
              <Button variant="secondary" onClick={() => setAction("cycle_count")}>
                Cycle count
              </Button>
              <Button variant="primary" onClick={() => setAction("reserve")}>
                <Icon name="plus" /> Reserve
              </Button>
            </div>
          ) : undefined
        }
      />

      <Tabs
        tabs={[
          {
            id: "availability",
            label: "Availability",
            content: (
              <div>
                <form onSubmit={loadAvailability} className="flex items-end gap-4 mb-4">
                  <Field label="Material" hint="Lots are ordered FEFO — earliest expiry first.">
                    <Select value={materialId} onChange={(e) => setMaterialId(e.target.value)} style={{ minWidth: 320 }}>
                      <option value="">Select a material…</option>
                      {materials.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.code} — {m.name}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Button type="submit" variant="secondary" disabled={loading || !materialId || !siteId}>
                    <Icon name="search" /> {loading ? "Loading…" : "Show availability"}
                  </Button>
                </form>

                {error && (
                  <Banner tone="critical" title="Could not load availability">
                    {error}
                  </Banner>
                )}

                {availability && (
                  <Card>
                    <CardHeader title="Available stock" meta={`${availability.length} container(s)`} />
                    {availability.length === 0 ? (
                      <EmptyState icon="inbox">
                        No eligible stock — every container is expired, quarantined, reserved or empty.
                      </EmptyState>
                    ) : (
                      <Table>
                        <thead>
                          <tr>
                            <th>Lot</th>
                            <th>Location</th>
                            <th style={{ textAlign: "right" }}>Available</th>
                            <th>Expiry</th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>
                          {availability.map((row) => (
                            <tr key={row.container_id}>
                              <td className="font-semibold tabular">{row.internal_lot}</td>
                              <td className="fs-2">{row.location_code}</td>
                              <td className="tabular" style={{ textAlign: "right" }}>
                                {row.available} {row.uom}
                              </td>
                              <td className="tabular fs-2">{row.expiry_date ?? "—"}</td>
                              <td style={{ textAlign: "right" }}>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => {
                                    setLedgerLotId(row.material_lot_id);
                                    setActiveLedgerLot(row.material_lot_id);
                                  }}
                                >
                                  Ledger
                                </Button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    )}
                  </Card>
                )}
              </div>
            ),
          },
          {
            id: "ledger",
            label: "Lot ledger",
            content: (
              <div>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    setActiveLedgerLot(ledgerLotId.trim() || null);
                  }}
                  className="flex items-end gap-4 mb-4"
                >
                  <Field label="Material lot ID" hint="Every movement affecting this lot, in order.">
                    <Input value={ledgerLotId} onChange={(e) => setLedgerLotId(e.target.value)} style={{ minWidth: 340 }} />
                  </Field>
                  <Button type="submit" variant="secondary" disabled={!ledgerLotId.trim()}>
                    <Icon name="history" /> Show ledger
                  </Button>
                </form>

                {activeLedgerLot ? (
                  <Card>
                    <CardHeader title="Inventory ledger" />
                    <DataTable
                      columns={ledgerColumns}
                      fetchPage={pagedFetcher<LedgerRow>(`/inventory/v1/lots/${activeLedgerLot}/ledger`)}
                      rowKey={(t) => t.id}
                      searchPlaceholder="Search…"
                      emptyIcon="history"
                      emptyMessage="No inventory transactions for this lot."
                      defaultSort={{ by: "occurred_at", dir: "desc" }}
                      reloadToken={reloadToken}
                    />
                  </Card>
                ) : (
                  <EmptyState icon="history">Enter a material lot ID to see its movement history.</EmptyState>
                )}
              </div>
            ),
          },
          {
            id: "adjustments",
            label: "Adjustments",
            content: (
              <Card pad>
                <p className="fact-k mb-2">Exceptional inventory adjustment</p>
                <p className="hint mb-3">
                  An adjustment is an exception, not a correction path — it needs a stated reason and an
                  independent approver (Document 22). Cycle counts are the routine mechanism.
                </p>
                <div className="flex gap-2">
                  {canMove && (
                    <Button variant="secondary" onClick={() => setAction("adjustment")}>
                      <Icon name="plus" /> Request adjustment
                    </Button>
                  )}
                  {!canApprove && (
                    <p className="hint">
                      Approving an adjustment requires QA Releaser — you can raise one but not approve it.
                    </p>
                  )}
                </div>
              </Card>
            ),
          },
        ]}
      />

      {action && (
        <ActionModal
          action={action}
          materials={materials}
          siteId={siteId}
          onClose={() => setAction(null)}
          onDone={() => {
            setAction(null);
            setReloadToken((n) => n + 1);
            if (materialId && siteId) {
              api
                .get<{ items: AvailabilityRow[] }>(
                  `/inventory/v1/availability?material_id=${materialId}&site_id=${siteId}`
                )
                .then((r) => setAvailability(r.items))
                .catch(() => undefined);
            }
          }}
        />
      )}
    </div>
  );
}

function ActionModal({
  action,
  materials,
  siteId,
  onClose,
  onDone,
}: {
  action: Action;
  materials: Material[];
  siteId: string | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [batchId, setBatchId] = useState("");
  const [materialId, setMaterialId] = useState(materials[0]?.id ?? "");
  const [quantity, setQuantity] = useState("");
  const [uom, setUom] = useState("kg");
  const [lotId, setLotId] = useState("");
  const [containerId, setContainerId] = useState("");
  const [fromLocation, setFromLocation] = useState("");
  const [toLocation, setToLocation] = useState("");
  const [countedQuantity, setCountedQuantity] = useState("");
  const [expectedQuantity, setExpectedQuantity] = useState("");
  const [observedQuantity, setObservedQuantity] = useState("");
  const [reason, setReason] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const key = newIdempotencyKey();
    run(() => {
      switch (action) {
        case "reserve":
          return api.post("/inventory/v1/reservations", {
            idempotency_key: key,
            batch_id: batchId,
            material_id: materialId,
            site_id: siteId,
            quantity,
            uom,
          });
        case "transfer":
          return api.post("/inventory/v1/transfers", {
            idempotency_key: key,
            material_lot_id: lotId,
            container_id: containerId,
            from_location_id: fromLocation || null,
            to_location_id: toLocation,
            quantity,
          });
        case "cycle_count":
          return api.post("/inventory/v1/cycle-counts", {
            idempotency_key: key,
            material_lot_id: lotId,
            container_id: containerId || null,
            location_id: toLocation,
            counted_quantity: countedQuantity,
            reason: reason || null,
          });
        case "adjustment":
          return api.post("/inventory/v1/adjustments", {
            idempotency_key: key,
            material_lot_id: lotId,
            container_id: containerId || null,
            location_id: toLocation,
            expected_quantity: expectedQuantity,
            observed_quantity: observedQuantity,
            reason,
          });
      }
    });
  }

  return (
    <Modal open onClose={onClose} title={ACTION_LABEL[action]} large>
      <form onSubmit={submit}>
        {action === "reserve" && (
          <>
            <p className="hint mb-3">
              Reservation selects source lots server-side by FEFO (INV-FR-010/012) — you name the material
              and quantity, not the lot.
            </p>
            <Field label="Batch ID" required>
              <Input value={batchId} onChange={(e) => setBatchId(e.target.value)} required autoFocus />
            </Field>
            <Field label="Material" required>
              <Select value={materialId} onChange={(e) => setMaterialId(e.target.value)} required>
                {materials.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.code} — {m.name}
                  </option>
                ))}
              </Select>
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Quantity" required>
                <Input type="number" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
              </Field>
              <Field label="UOM" required>
                <Input value={uom} onChange={(e) => setUom(e.target.value)} required />
              </Field>
            </div>
          </>
        )}

        {action === "transfer" && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Material lot ID" required>
                <Input value={lotId} onChange={(e) => setLotId(e.target.value)} required autoFocus />
              </Field>
              <Field label="Container ID" required>
                <Input value={containerId} onChange={(e) => setContainerId(e.target.value)} required />
              </Field>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <Field label="From location ID">
                <Input value={fromLocation} onChange={(e) => setFromLocation(e.target.value)} />
              </Field>
              <Field label="To location ID" required>
                <Input value={toLocation} onChange={(e) => setToLocation(e.target.value)} required />
              </Field>
              <Field label="Quantity" required>
                <Input type="number" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
              </Field>
            </div>
          </>
        )}

        {action === "cycle_count" && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Material lot ID" required>
                <Input value={lotId} onChange={(e) => setLotId(e.target.value)} required autoFocus />
              </Field>
              <Field label="Container ID">
                <Input value={containerId} onChange={(e) => setContainerId(e.target.value)} />
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Location ID" required>
                <Input value={toLocation} onChange={(e) => setToLocation(e.target.value)} required />
              </Field>
              <Field label="Counted quantity" required hint="What was physically counted, not what was expected.">
                <Input
                  type="number"
                  step="any"
                  value={countedQuantity}
                  onChange={(e) => setCountedQuantity(e.target.value)}
                  required
                />
              </Field>
            </div>
            <Field label="Reason / notes">
              <Input value={reason} onChange={(e) => setReason(e.target.value)} />
            </Field>
          </>
        )}

        {action === "adjustment" && (
          <>
            <Banner tone="warn" title="Adjustments are exceptions">
              An adjustment changes recorded stock without a physical movement. It requires an independent
              approver before it takes effect.
            </Banner>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Material lot ID" required>
                <Input value={lotId} onChange={(e) => setLotId(e.target.value)} required autoFocus />
              </Field>
              <Field label="Container ID">
                <Input value={containerId} onChange={(e) => setContainerId(e.target.value)} />
              </Field>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Location ID" required>
                <Input value={toLocation} onChange={(e) => setToLocation(e.target.value)} required />
              </Field>
              <Field label="Expected quantity" required>
                <Input
                  type="number"
                  step="any"
                  value={expectedQuantity}
                  onChange={(e) => setExpectedQuantity(e.target.value)}
                  required
                />
              </Field>
              <Field label="Observed quantity" required>
                <Input
                  type="number"
                  step="any"
                  value={observedQuantity}
                  onChange={(e) => setObservedQuantity(e.target.value)}
                  required
                />
              </Field>
            </div>
            <Field label="Reason" required>
              <textarea className="input" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} required />
            </Field>
          </>
        )}

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Saving…" : ACTION_LABEL[action]}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
