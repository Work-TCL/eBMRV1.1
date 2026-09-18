"use client";

import { useEffect, useState } from "react";
import {
  api,
  ApiError,
  formatDateTime,
  hasPermission,
  listAll,
  listBatchesForSite,
  newIdempotencyKey,
  pagedFetcher,
  type BatchSummary,
  type Material,
  type MaterialContainer,
  type MaterialLot,
  type MutationReceipt,
  type WarehouseLocation,
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
import { Field, RowButtonSlot } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { StatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { StringListRows, buildStringList } from "@/components/shared/RepeatableFields";

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
  container_code: string | null;
  transaction_type: string;
  quantity: string;
  uom: string;
  from_location_id: string | null;
  from_location_code: string | null;
  to_location_id?: string | null;
  to_location_code?: string | null;
  occurred_at?: string;
}

// GET /inventory/v1/adjustments — services/gxp-api/app/modules/material/router.py::list_adjustment_requests
interface AdjustmentRequestRow {
  id: string;
  internal_lot: string;
  material_code: string;
  container_id: string | null;
  location_code: string;
  expected_quantity: string;
  observed_quantity: string;
  variance: string;
  reason: string;
  status: string;
  requested_by: string;
  created_at: string | null;
  version: number;
}

const ADJUSTMENT_STATUS: Record<string, { state: "missing" | "accepted" | "failed"; label: string }> = {
 requested: { state: "missing", label: "Requested pending approval" },
  approved: { state: "accepted", label: "Approved" },
  // Until this pass, reject_inventory_adjustment_request didn't exist at all — a wrong/unwanted request
  // just sat in "requested" forever with no way out (DDCP_Client_Demo_Guide_Gujarati.md §19 #7).
  rejected: { state: "failed", label: "Rejected" },
};

// CON-FR-014: the approver/rejecter must be independent of the requester — enforced server-side
// (approve/reject_inventory_adjustment_request both refuse a self-decision), mirrored here so the buttons
// are disabled with an explanation rather than letting the user submit into a guaranteed rejection.
function adjustmentColumns(
  canApprove: boolean,
  myUsername: string | null,
  onApprove: (row: AdjustmentRequestRow) => void,
  onReject: (row: AdjustmentRequestRow) => void
): DataTableColumn<AdjustmentRequestRow>[] {
  return [
    {
      key: "internal_lot",
      header: "Lot",
      sortable: true,
      render: (r) => (
        <span className="tabular fs-2">
        {r.internal_lot} - <span className="text-muted">{r.material_code}</span>
        </span>
      ),
    },
    { key: "location_code", header: "Location", render: (r) => <span className="fs-2">{r.location_code}</span> },
    {
      key: "expected_quantity",
      header: "Expected",
      align: "right",
      render: (r) => <span className="tabular">{r.expected_quantity}</span>,
    },
    {
      key: "observed_quantity",
      header: "Observed",
      align: "right",
      render: (r) => <span className="tabular">{r.observed_quantity}</span>,
    },
    {
      key: "variance",
      header: "Variance",
      align: "right",
      render: (r) => (
        <span
          className="tabular font-semibold"
          style={Number(r.variance) < 0 ? { color: "var(--status-critical-text)" } : undefined}
        >
          {r.variance}
        </span>
      ),
    },
    {
      key: "reason",
      header: "Reason",
      render: (r) => (
        <span className="fs-2" style={{ display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {r.reason}
        </span>
      ),
    },
    { key: "requested_by", header: "Requested by", render: (r) => <span className="fs-2">{r.requested_by}</span> },
    {
      key: "created_at",
      header: "Requested",
      sortable: true,
      render: (r) => <span className="tabular fs-2">{r.created_at ? formatDateTime(r.created_at) : "—"}</span>,
    },
    {
      key: "status",
      header: "Status",
      render: (r) => {
        const s = ADJUSTMENT_STATUS[r.status] ?? { state: "missing" as const, label: r.status };
        const icon = r.status === "approved" ? "check-circle" : r.status === "rejected" ? "alert-triangle" : "clock";
        return (
          <StatePill state={s.state} icon={icon}>
            {s.label}
          </StatePill>
        );
      },
    },
    {
      key: "actions",
      header: "",
      render: (r) => {
        if (r.status !== "requested") return null;
        if (!canApprove) return null;
        const isSelf = myUsername != null && r.requested_by === myUsername;
        const title = isSelf ? "You requested this - an independent QA Releaser must approve or reject it" : undefined;
        return (
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="secondary" disabled={isSelf} onClick={() => onReject(r)} title={title}>
              Reject
            </Button>
            <Button size="sm" variant="primary" disabled={isSelf} onClick={() => onApprove(r)} title={title}>
              Approve
            </Button>
          </div>
        );
      },
    },
  ];
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
  const [materialLots, setMaterialLots] = useState<MaterialLot[]>([]);
  const [materialId, setMaterialId] = useState("");
  const [availability, setAvailability] = useState<AvailabilityRow[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState<Action | null>(null);
  const [ledgerLotId, setLedgerLotId] = useState("");
  const [activeLedgerLot, setActiveLedgerLot] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [approvingAdjustment, setApprovingAdjustment] = useState<AdjustmentRequestRow | null>(null);
  const [rejectingAdjustment, setRejectingAdjustment] = useState<AdjustmentRequestRow | null>(null);
  const [locations, setLocations] = useState<WarehouseLocation[]>([]);
  const [newLocationOpen, setNewLocationOpen] = useState(false);
  const [splittingContainer, setSplittingContainer] = useState<AvailabilityRow | null>(null);
  const [mergeSelection, setMergeSelection] = useState<Set<string>>(new Set());
  const [mergeOpen, setMergeOpen] = useState(false);

  // transfer/split/merge/cycle-count/consumption/return/loss/destruction share one grant.
  const canMove = hasPermission(me, "inventory_transaction.transfer");
  const canApprove = hasPermission(me, "inventory_adjustment_request.approve");
  const canManageLocations = hasPermission(me, "warehouse_location.create");
  // inventory_adjustment_request.create is its OWN, broader grant (also QA Releaser, unlike the
  // Operator/Supervisor-only canMove bundle above) -- audit finding 2026-09-18: "Request adjustment" was
  // gated on canMove and hid the button from QA Releaser despite holding this exact permission.
  const canRequestAdjustment = hasPermission(me, "inventory_adjustment_request.create");

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

  // Same cap/pattern as materials above — shared with the Lot ledger picker below and passed down to
  // ActionModal so Transfer/Cycle count/Adjustment don't each fetch their own copy.
  useEffect(() => {
    let cancelled = false;
    listAll<MaterialLot>("/material-lots")
      .then((rows) => {
        if (!cancelled) setMaterialLots(rows);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  // Lifted to the parent (rather than fetched inside ActionModal) so a newly-created location
  // (below) is immediately available to Transfer/Cycle count/Adjustment without reopening anything.
  useEffect(() => {
    if (!siteId) return;
    let cancelled = false;
    listAll<WarehouseLocation>("/inventory/v1/warehouse-locations", { site_id: siteId })
      .then((rows) => {
        if (!cancelled) setLocations(rows);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [siteId, reloadToken]);

  function loadAvailability(e: React.FormEvent) {
    e.preventDefault();
    void refreshAvailability();
  }

  async function refreshAvailability() {
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
      render: (t) => <span className="fs-2">{t.container_code ?? "—"}</span>,
    },
    {
      key: "from_location_id",
      header: "Location",
      render: (t) => (
        <span className="fs-2">
          {t.from_location_code ?? "—"} → {t.to_location_code ?? "—"}
        </span>
      ),
    },
  ];

  return (
    <div>
      <PageHead
        title="Inventory"
        subtitle="Availability, reservations, movements, cycle counts and the lot ledger."
        action={
          canMove || canManageLocations ? (
            <div className="flex gap-2">
              {canManageLocations && (
                <Button variant="secondary" onClick={() => setNewLocationOpen(true)}>
                  <Icon name="plus" /> New location
                </Button>
              )}
              {canMove && (
                <>
                  <Button variant="secondary" onClick={() => setAction("transfer")}>
                    Transfer
                  </Button>
                  <Button variant="secondary" onClick={() => setAction("cycle_count")}>
                    Cycle count
                  </Button>
                  <Button variant="primary" onClick={() => setAction("reserve")}>
                    <Icon name="plus" /> Reserve
                  </Button>
                </>
              )}
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
                {/* items-start, not items-end: the Material field carries a hint line below its select,
                 * which items-end would bottom-align the row to instead of the select itself — dragging
                 * the button down below the input it belongs beside. RowButtonSlot gives the button a
                 * same-height invisible label so it still lines up with the select. */}
                <form onSubmit={loadAvailability} className="flex flex-wrap items-start gap-4 mb-4">
                  <Field label="Material" hint="Lots are ordered FEFO - earliest expiry first.">
                    <Select value={materialId} onChange={(e) => setMaterialId(e.target.value)} style={{ minWidth: 200, maxWidth: 320, width: "100%" }}>
                      <option value="">Select a material…</option>
                      {materials.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.code} - {m.name}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <RowButtonSlot>
                    <Button type="submit" variant="secondary" disabled={loading || !materialId || !siteId}>
                      <Icon name="search" /> {loading ? "Loading…" : "Show availability"}
                    </Button>
                  </RowButtonSlot>
                </form>

                {error && (
                  <Banner tone="critical" title="Could not load availability">
                    {error}
                  </Banner>
                )}

                {availability && (
                  <Card>
                    <CardHeader
                      title="Available stock"
                      meta={`${availability.length} container(s)`}
                    />
                    {availability.length === 0 ? (
                      <EmptyState icon="inbox">
                        No eligible stock - every container is expired, quarantined, reserved or empty.
                      </EmptyState>
                    ) : (
                      <>
                        <Table>
                          <thead>
                            <tr>
                              <th></th>
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
                                <td>
                                  {canMove && (
                                    <input
                                      type="checkbox"
                                      checked={mergeSelection.has(row.container_id)}
                                      onChange={(e) =>
                                        setMergeSelection((cur) => {
                                          const next = new Set(cur);
                                          if (e.target.checked) next.add(row.container_id);
                                          else next.delete(row.container_id);
                                          return next;
                                        })
                                      }
                                    />
                                  )}
                                </td>
                                <td className="font-semibold tabular">{row.internal_lot}</td>
                                <td className="fs-2">{row.location_code}</td>
                                <td className="tabular" style={{ textAlign: "right" }}>
                                  {row.available} {row.uom}
                                </td>
                                <td className="tabular fs-2">{row.expiry_date ?? "—"}</td>
                                <td style={{ textAlign: "right" }}>
                                  <div className="flex gap-2 justify-end">
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
                                    {canMove && (
                                      <Button size="sm" variant="secondary" onClick={() => setSplittingContainer(row)}>
                                        Split
                                      </Button>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </Table>
                        {canMove && (
                          <div className="flex items-center gap-3 mt-3" style={{ padding: "0 var(--space-4) var(--space-3)" }}>
                            <Button
                              size="sm"
                              variant="secondary"
                              disabled={mergeSelection.size < 2}
                              onClick={() => setMergeOpen(true)}
                            >
                              Merge selected ({mergeSelection.size})
                            </Button>
                            <p className="hint">Select at least two containers of the same lot to merge.</p>
                          </div>
                        )}
                      </>
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
 {/* items-start, not items-end: see the Availability form above the hint below the
                 * input would otherwise pull the button down past the input it belongs beside. */}
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    setActiveLedgerLot(ledgerLotId.trim() || null);
                  }}
                  className="flex flex-wrap items-start gap-4 mb-4"
                >
                  <Field label="Material lot" hint="Every movement affecting this lot, in order.">
                    <Select
                      value={ledgerLotId}
                      onChange={(e) => setLedgerLotId(e.target.value)}
                      style={{ minWidth: 240, maxWidth: 380, width: "100%" }}
                    >
                      <option value="">Select a lot…</option>
                      {materialLots.map((l) => (
                        <option key={l.id} value={l.id}>
                  {l.internal_lot} - {l.material_code} ({l.status})
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <RowButtonSlot>
                    <Button type="submit" variant="secondary" disabled={!ledgerLotId}>
                      <Icon name="history" /> Show ledger
                    </Button>
                  </RowButtonSlot>
                </form>

                {activeLedgerLot ? (
                  <Card>
                    <CardHeader
                      title="Inventory ledger"
                      meta={materialLots.find((l) => l.id === activeLedgerLot)?.internal_lot}
                    />
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
                  <EmptyState icon="history">Select a material lot to see its movement history.</EmptyState>
                )}
              </div>
            ),
          },
          {
            id: "adjustments",
            label: "Adjustments",
            content: (
              <div>
                <Card pad className="mb-4">
                  <p className="fact-k mb-2">Exceptional inventory adjustment</p>
                  <p className="hint mb-3">
                  An adjustment is an exception, not a correction path - it needs a stated reason and an
                  independent approver. Cycle counts are the routine mechanism.
                  </p>
                  <div className="flex gap-2">
                    {canRequestAdjustment && (
                      <Button variant="secondary" onClick={() => setAction("adjustment")}>
                        <Icon name="plus" /> Request adjustment
                      </Button>
                    )}
                    {!canApprove && (
                      <p className="hint">
                      Approving an adjustment requires QA Releaser - you can raise one but not approve it.
                      </p>
                    )}
                  </div>
                </Card>

                <Card>
                  <CardHeader title="Adjustment requests" />
                  <DataTable
                    columns={adjustmentColumns(canApprove, me?.username ?? null, setApprovingAdjustment, setRejectingAdjustment)}
                    fetchPage={pagedFetcher<AdjustmentRequestRow>("/inventory/v1/adjustments")}
                    rowKey={(r) => r.id}
                    searchPlaceholder="Search by lot or material…"
                    emptyIcon="scale"
                    emptyMessage="No adjustment requests yet."
                    defaultSort={{ by: "created_at", dir: "desc" }}
                    reloadToken={reloadToken}
                  />
                </Card>
              </div>
            ),
          },
        ]}
      />

      {action && (
        <ActionModal
          action={action}
          materials={materials}
          materialLots={materialLots}
          locations={locations}
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

      {approvingAdjustment && (
        <SignatureCeremony
          open
          onClose={() => setApprovingAdjustment(null)}
          onDone={() => {
            setApprovingAdjustment(null);
            setReloadToken((n) => n + 1);
          }}
          challengePath={`/inventory/v1/adjustments/${approvingAdjustment.id}/signature-challenges`}
          action="approve"
 title={`Approve adjustment ${approvingAdjustment.internal_lot}`}
          summary={
            <>
              Approving this changes the recorded stock at <strong>{approvingAdjustment.location_code}</strong> from{" "}
              <strong>{approvingAdjustment.expected_quantity}</strong> to{" "}
              <strong>{approvingAdjustment.observed_quantity}</strong> (variance{" "}
 <strong>{approvingAdjustment.variance}</strong>) requested by{" "}
              <strong>{approvingAdjustment.requested_by}</strong>: “{approvingAdjustment.reason}”. This cannot be
              undone by re-approving; a further correction needs its own new adjustment request.
            </>
          }
          reason="required"
          onSign={(p) =>
            api.post<MutationReceipt>(`/inventory/v1/adjustments/${approvingAdjustment.id}/approve`, {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              expected_version: approvingAdjustment.version,
              reason: p.reason,
            })
          }
        />
      )}

      {rejectingAdjustment && (
        <SignatureCeremony
          open
          onClose={() => setRejectingAdjustment(null)}
          onDone={() => {
            setRejectingAdjustment(null);
            setReloadToken((n) => n + 1);
          }}
          challengePath={`/inventory/v1/adjustments/${rejectingAdjustment.id}/signature-challenges`}
          action="reject"
          title={`Reject adjustment ${rejectingAdjustment.internal_lot}`}
          summary={
            <>
              Rejecting this leaves the recorded stock at <strong>{rejectingAdjustment.location_code}</strong>{" "}
              unchanged — no inventory transaction is created. Requested by{" "}
              <strong>{rejectingAdjustment.requested_by}</strong>: “{rejectingAdjustment.reason}”. A wrong
              adjustment can still be re-requested from scratch afterward.
            </>
          }
          reason="required"
          onSign={(p) =>
            api.post<MutationReceipt>(`/inventory/v1/adjustments/${rejectingAdjustment.id}/reject`, {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              expected_version: rejectingAdjustment.version,
              reason: p.reason,
            })
          }
        />
      )}

      {newLocationOpen && (
        <NewLocationModal
          siteId={siteId}
          onClose={() => setNewLocationOpen(false)}
          onDone={() => {
            setNewLocationOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}

      {splittingContainer && (
        <SplitContainerModal
          container={splittingContainer}
          onClose={() => setSplittingContainer(null)}
          onDone={() => {
            setSplittingContainer(null);
            refreshAvailability();
          }}
        />
      )}

      {mergeOpen && (
        <MergeContainersModal
          containerIds={Array.from(mergeSelection)}
          onClose={() => setMergeOpen(false)}
          onDone={() => {
            setMergeOpen(false);
            setMergeSelection(new Set());
            refreshAvailability();
          }}
        />
      )}
    </div>
  );
}

function ActionModal({
  action,
  materials,
  materialLots,
  locations,
  siteId,
  onClose,
  onDone,
}: {
  action: Action;
  materials: Material[];
  materialLots: MaterialLot[];
  locations: WarehouseLocation[];
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

  // Transfer/Cycle count/Adjustment all reference an existing material lot, container and warehouse
  // location by UUID — none of those UUIDs are printed anywhere in the UI, so every one of these three
  // actions is backed by a dropdown fetched from a real listing endpoint instead of asking the user to
  // type one in by hand.
  // Reserve references an existing Batch by UUID too (§11) — same fix, real /batches/v1 listing.
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  useEffect(() => {
    if (action !== "reserve" || !siteId) return;
    let cancelled = false;
    listBatchesForSite(siteId)
      .then((rows) => {
        if (!cancelled) setBatches(rows);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [action, siteId]);

  // Containers only exist for a lot received through Material Receipts → Examine (§6.2) — a lot created
  // via the "Receive lot" quick shortcut has none, so this list can legitimately come back empty.
  // `containersLotId` tracks which lot `containers` was actually fetched for, so a stale list from a
  // previously-selected lot is never shown while the new lot's fetch is still in flight (render-time
  // derivation instead of clearing state imperatively inside the effect).
  const [containers, setContainers] = useState<MaterialContainer[]>([]);
  const [containersLotId, setContainersLotId] = useState<string | null>(null);
  useEffect(() => {
    if (!lotId) return;
    let cancelled = false;
    api
      .get<{ items: MaterialContainer[] }>(`/material-lots/${lotId}/containers`)
      .then((r) => {
        if (cancelled) return;
        setContainers(r.items);
        setContainersLotId(lotId);
      })
      .catch(() => {
        // Fetch failed -- treat as "no containers found" rather than leaving the picker stuck on
        // "Loading…" forever (containersLoading is derived below from containersLotId, not a flag set
        // directly in this effect).
        if (!cancelled) {
          setContainers([]);
          setContainersLotId(lotId);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [lotId]);
  const currentContainers = containersLotId === lotId ? containers : [];
  const containersLoading = !!lotId && containersLotId !== lotId;
  // React-recommended "adjusting state when a prop changes" pattern (render-time, not an effect) --
  // clears the picked container as soon as the lot selection itself changes.
  const [containerResetForLotId, setContainerResetForLotId] = useState(lotId);
  if (lotId !== containerResetForLotId) {
    setContainerResetForLotId(lotId);
    setContainerId("");
  }

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
 Reservation selects source lots server-side by FEFO - you name the material
              and quantity, not the lot.
            </p>
            <Field label="Batch" required>
              <Select value={batchId} onChange={(e) => setBatchId(e.target.value)} required autoFocus>
                <option value="">Select a batch…</option>
                {batches.map((b) => (
                  <option key={b.id} value={b.id}>
                  {b.batch_number} - {b.product_code} ({b.status})
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Material" required>
              <Select value={materialId} onChange={(e) => setMaterialId(e.target.value)} required>
                {materials.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.code} - {m.name}
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
              <Field label="Material lot" required>
                <Select value={lotId} onChange={(e) => setLotId(e.target.value)} required autoFocus>
                  <option value="">Select a lot…</option>
                  {materialLots.map((l) => (
                    <option key={l.id} value={l.id}>
                  {l.internal_lot} - {l.material_code} ({l.status})
                    </option>
                  ))}
                </Select>
              </Field>
              <Field
                label="Container"
                required
                hint={
                  lotId && !containersLoading && currentContainers.length === 0
                    ? "No containers exist for this lot - it was created via the 'Receive lot' quick shortcut, which doesn't create one. Transfer needs a lot received via Material Receipts → Examine."
                    : undefined
                }
              >
                <Select
                  value={containerId}
                  onChange={(e) => setContainerId(e.target.value)}
                  required
                  disabled={!lotId || currentContainers.length === 0}
                >
                  <option value="">{containersLoading ? "Loading…" : "Select a container…"}</option>
                  {currentContainers.map((c) => (
                    <option key={c.id} value={c.id}>
                    {c.container_code} - {c.current_quantity} {c.uom}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <Field label="From location" hint="Blank = first put-away for this container.">
                <Select value={fromLocation} onChange={(e) => setFromLocation(e.target.value)}>
 <option value="">(none put-away)</option>
                  {locations.map((loc) => (
                    <option key={loc.id} value={loc.id}>
                      {loc.location_code} ({loc.zone_type})
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="To location" required>
                <Select value={toLocation} onChange={(e) => setToLocation(e.target.value)} required>
                  <option value="">Select a location…</option>
                  {locations.map((loc) => (
                    <option key={loc.id} value={loc.id}>
                      {loc.location_code} ({loc.zone_type})
                    </option>
                  ))}
                </Select>
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
              <Field label="Material lot" required>
                <Select value={lotId} onChange={(e) => setLotId(e.target.value)} required autoFocus>
                  <option value="">Select a lot…</option>
                  {materialLots.map((l) => (
                    <option key={l.id} value={l.id}>
                  {l.internal_lot} - {l.material_code} ({l.status})
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Container" hint="Optional - leave blank to count the lot's un-containerized balance at this location.">
                <Select value={containerId} onChange={(e) => setContainerId(e.target.value)} disabled={!lotId}>
                  <option value="">{containersLoading ? "Loading…" : "(none)"}</option>
                  {currentContainers.map((c) => (
                    <option key={c.id} value={c.id}>
                    {c.container_code} - {c.current_quantity} {c.uom}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Location" required>
                <Select value={toLocation} onChange={(e) => setToLocation(e.target.value)} required>
                  <option value="">Select a location…</option>
                  {locations.map((loc) => (
                    <option key={loc.id} value={loc.id}>
                      {loc.location_code} ({loc.zone_type})
                    </option>
                  ))}
                </Select>
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
              <Field label="Material lot" required>
                <Select value={lotId} onChange={(e) => setLotId(e.target.value)} required autoFocus>
                  <option value="">Select a lot…</option>
                  {materialLots.map((l) => (
                    <option key={l.id} value={l.id}>
                  {l.internal_lot} - {l.material_code} ({l.status})
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Container" hint="Optional - leave blank to adjust the lot's un-containerized balance at this location.">
                <Select value={containerId} onChange={(e) => setContainerId(e.target.value)} disabled={!lotId}>
                  <option value="">{containersLoading ? "Loading…" : "(none)"}</option>
                  {currentContainers.map((c) => (
                    <option key={c.id} value={c.id}>
                    {c.container_code} - {c.current_quantity} {c.uom}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Location" required>
                <Select value={toLocation} onChange={(e) => setToLocation(e.target.value)} required>
                  <option value="">Select a location…</option>
                  {locations.map((loc) => (
                    <option key={loc.id} value={loc.id}>
                      {loc.location_code} ({loc.zone_type})
                    </option>
                  ))}
                </Select>
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

// zone_type is a free-text column (no DB check constraint — code comment on _ZONE_STATUS_COMPAT in
// material/commands.py), but these are the values the app's own zone-compatibility rule actually reads;
// anything else is accepted but carries no automatic behavior (destruction/return/etc.).
const ZONE_TYPES = [
  "quarantine",
  "released",
  "rejected",
  "sampling",
  "testing",
  "qc_disposition_pending",
  "retest_due",
  "controlled_temperature",
  "sterile_component",
  "return",
  "destruction",
  "other",
];

function NewLocationModal({
  siteId,
  onClose,
  onDone,
}: {
  siteId: string | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [warehouseCode, setWarehouseCode] = useState("");
  const [locationCode, setLocationCode] = useState("");
  const [zoneType, setZoneType] = useState("quarantine");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    run(() =>
      api.post<MutationReceipt>("/inventory/v1/warehouse-locations", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        warehouse_code: warehouseCode,
        location_code: locationCode,
        zone_type: zoneType,
      })
    );
  }

  return (
    <Modal open onClose={onClose} title="New warehouse location">
      <form onSubmit={submit}>
        <p className="hint mb-3">
 Master data - no signature, but permanent once created (no delete/rename UI
          exists yet). Used as the From/To location on Transfer, Cycle count and Adjustment.
        </p>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Warehouse code" required hint="Groups locations, e.g. one per physical building.">
            <Input value={warehouseCode} onChange={(e) => setWarehouseCode(e.target.value)} required autoFocus placeholder="WH1" />
          </Field>
          <Field label="Location code" required hint="Unique within the warehouse code above.">
            <Input value={locationCode} onChange={(e) => setLocationCode(e.target.value)} required placeholder="QUARANTINE-02" />
          </Field>
        </div>
        <Field
          label="Zone type"
          required
          hint="released/quarantine/rejected drive the Transfer zone-compatibility check - pick the one matching what this location is actually for."
        >
          <Select value={zoneType} onChange={(e) => setZoneType(e.target.value)} required>
            {ZONE_TYPES.map((z) => (
              <option key={z} value={z}>
                {z}
              </option>
            ))}
          </Select>
        </Field>

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !siteId}>
            {busy ? "Saving…" : "Create location"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** No container-detail-by-id GET exists anywhere (verified against `material/router.py` — availability
 * and the lot-containers list both omit `version`), so `expected_version` has to be entered by hand
 * here rather than looked up — same honest "no read exists" shape as OOT/sampling-orders earlier this
 * session. */
function SplitContainerModal({
  container,
  onClose,
  onDone,
}: {
  container: AvailabilityRow;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [expectedVersion, setExpectedVersion] = useState("1");
  const [splitQuantities, setSplitQuantities] = useState<string[]>([]);

  const quantities = buildStringList(splitQuantities);

  return (
    <Modal open onClose={onClose} title={`Split container - ${container.internal_lot}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/inventory/v1/containers/${container.container_id}/split`, {
              idempotency_key: newIdempotencyKey(),
              container_id: container.container_id,
              expected_version: Number(expectedVersion),
              split_quantities: quantities,
            })
          );
        }}
      >
        <p className="fs-3 mb-3">
          Splits {container.available} {container.uom} across the child quantities below - at least two
          required, and they should sum to the container&apos;s current quantity.
        </p>
        <Field label="Expected version" required hint="No lookup exists for this - check the audit ledger if unsure.">
          <Input type="number" value={expectedVersion} onChange={(e) => setExpectedVersion(e.target.value)} required />
        </Field>
        <StringListRows
          label="Split quantities"
          required
          itemLabel="Quantity"
          placeholder={`e.g. half of ${container.available}`}
          value={splitQuantities}
          onChange={setSplitQuantities}
        />
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || quantities.length < 2}>
            {busy ? "Splitting…" : "Split container"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function MergeContainersModal({
  containerIds,
  onClose,
  onDone,
}: {
  containerIds: string[];
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [newContainerCode, setNewContainerCode] = useState("");

  return (
    <Modal open onClose={onClose} title="Merge containers">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post("/inventory/v1/containers/merge", {
              idempotency_key: newIdempotencyKey(),
              source_container_ids: containerIds,
              new_container_code: newContainerCode.trim(),
            })
          );
        }}
      >
        <p className="fs-3 mb-3">Merging {containerIds.length} selected containers into one new container.</p>
        <Field label="New container code" required>
          <Input value={newContainerCode} onChange={(e) => setNewContainerCode(e.target.value)} required autoFocus />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !newContainerCode.trim()}>
            {busy ? "Merging…" : "Merge"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
