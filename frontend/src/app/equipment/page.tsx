"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  ApiError,
  canCreateEquipment,
  formatDate,
  isOverdue,
  newIdempotencyKey,
  pagedFetcher,
  type EquipmentAsset,
  type MutationReceipt,
} from "@/lib/api";
import { useApiResource, useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { KpiRow, KpiTile } from "@/components/ui/KpiTile";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";

interface EquipmentDashboard {
  site_id: string;
  due_calibration_count: number;
  due_maintenance_count: number;
  out_of_service: { id: string; equipment_code: string; state: string }[];
}

// The asset lifecycle states app/modules/equipment/commands.py actually assigns.
const ASSET_STATES = [
  "INSTALLED",
  "QUALIFICATION_PENDING",
  "QUALIFIED_AVAILABLE",
  "CALIBRATION_DUE",
  "MAINTENANCE_DUE",
  "VERIFICATION",
  "OUT_OF_SERVICE",
  "SUSPENDED",
];

export default function EquipmentPage() {
  const router = useRouter();
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [reloadToken, setReloadToken] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedState, setSelectedState] = useState("");

  const { data: dashboard } = useApiResource<EquipmentDashboard>(
    siteId ? `/equipment/v1/dashboard?site_id=${siteId}` : null
  );

  // app/modules/equipment/router.py::list_assets takes `state` alongside the shared page params.
  // DataTable holds fetchPage in a ref rather than an effect dependency, so this inline closure can
  // read current state directly; changing the filter bumps reloadToken to force the refetch.
  const fetchAssets = pagedFetcher<EquipmentAsset>("/equipment/v1/assets", () => ({ state: selectedState }));

  const columns: DataTableColumn<EquipmentAsset>[] = [
    {
      key: "equipment_code",
      header: "Code",
      sortable: true,
      render: (a) => <span className="font-semibold tabular">{a.equipment_code}</span>,
    },
    {
      key: "model",
      header: "Manufacturer / model",
      render: (a) => (
        <span className="fs-2">
          {[a.manufacturer, a.model].filter(Boolean).join(" ") || <span className="text-muted">—</span>}
        </span>
      ),
    },
    { key: "state", header: "State", sortable: true, render: (a) => <WorkflowStatePill state={a.state} /> },
    {
      key: "qualification_status",
      header: "Qualification",
      render: (a) => <StatusCell value={a.qualification_status} />,
    },
    {
      key: "next_calibration_due_date",
      header: "Calibration due",
      render: (a) => <DueCell date={a.next_calibration_due_date} status={a.calibration_status} />,
    },
    {
      key: "hold_flag",
      header: "Hold",
      render: (a) =>
        a.hold_flag ? (
          <StatePill state="blocked" icon="lock">
            On hold
          </StatePill>
        ) : (
          <span className="text-muted">—</span>
        ),
    },
  ];

  return (
    <div>
      <PageHead
        title="Equipment"
        subtitle="Document 38 — asset register, qualification, calibration, maintenance and use eligibility."
        action={
          canCreateEquipment(me) ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> New asset
            </Button>
          ) : undefined
        }
      />

      {dashboard && (
        <KpiRow>
          <KpiTile
            label="Calibration due"
            icon="gauge"
            value={dashboard.due_calibration_count}
            delta={dashboard.due_calibration_count > 0 ? "Past or at due date" : "All current"}
            tone={dashboard.due_calibration_count > 0 ? "warn" : "ok"}
          />
          <KpiTile
            label="Maintenance open"
            icon="refresh"
            value={dashboard.due_maintenance_count}
            delta={dashboard.due_maintenance_count > 0 ? "In progress or pending verification" : "None open"}
            tone={dashboard.due_maintenance_count > 0 ? "warn" : "ok"}
          />
          <KpiTile
            label="Out of service"
            icon="alert-triangle"
            value={dashboard.out_of_service.length}
            delta={
              dashboard.out_of_service.length > 0
                ? dashboard.out_of_service.map((a) => a.equipment_code).join(", ")
                : "All assets available"
            }
            tone={dashboard.out_of_service.length > 0 ? "critical" : "ok"}
          />
        </KpiRow>
      )}

      <p className="hint mb-4">
        Utilization and recurring-failure analytics (the rest of EQP-FR-028) need a time-series engine
        this deployment does not have yet — the counts above are the implemented part.
      </p>

      <Card>
        <CardHeader
          title="Asset register"
          meta={
            <span className="flex items-center gap-2">
              State
              <Select
                value={selectedState}
                onChange={(e) => {
                  setSelectedState(e.target.value);
                  setReloadToken((n) => n + 1);
                }}
              >
                <option value="">All</option>
                {ASSET_STATES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </span>
          }
        />
        <DataTable
          columns={columns}
          fetchPage={fetchAssets}
          rowKey={(a) => a.id}
          searchPlaceholder="Search by equipment code…"
          emptyIcon="scan"
          emptyMessage="No equipment assets registered yet."
          defaultSort={{ by: "created_at", dir: "desc" }}
          reloadToken={reloadToken}
          onRowClick={(a) => router.push(`/equipment/${a.id}`)}
        />
      </Card>

      {createOpen && (
        <CreateAssetModal
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

function StatusCell({ value }: { value: string | null }) {
  if (!value) return <span className="text-muted">—</span>;
  const good = ["qualified", "valid", "current", "passed"].includes(value.toLowerCase());
  return (
    <StatePill state={good ? "accepted" : "stale"} icon={good ? "check-circle" : "clock"}>
      {value}
    </StatePill>
  );
}

/** Calibration due date carries the actual signal — a date in the past is the exception the register
 * exists to surface, so it is styled rather than just printed. */
function DueCell({ date, status }: { date: string | null; status: string | null }) {
  if (!date) return <span className="text-muted">{status ?? "—"}</span>;
  const overdue = isOverdue(date);
  return (
    <span className={overdue ? "error-text tabular fs-2" : "tabular fs-2"}>
      {overdue && <Icon name="alert-triangle" />} {formatDate(date)}
    </span>
  );
}

function CreateAssetModal({
  siteId,
  onClose,
  onDone,
}: {
  siteId: string | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const [equipmentCode, setEquipmentCode] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [model, setModel] = useState("");
  const [serialNo, setSerialNo] = useState("");
  const [firmwareVersion, setFirmwareVersion] = useState("");
  const [dedicated, setDedicated] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    setBusy(true);
    setError(null);
    try {
      await api.post<MutationReceipt>("/equipment/v1/assets", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        equipment_code: equipmentCode,
        manufacturer: manufacturer || null,
        model: model || null,
        serial_no: serialNo || null,
        firmware_version: firmwareVersion || null,
        dedicated,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to create asset");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="New equipment asset" large>
      <form onSubmit={onSubmit}>
        <Field label="Equipment code" required>
          <Input value={equipmentCode} onChange={(e) => setEquipmentCode(e.target.value)} required autoFocus />
        </Field>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Manufacturer">
            <Input value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} />
          </Field>
          <Field label="Model">
            <Input value={model} onChange={(e) => setModel(e.target.value)} />
          </Field>
          <Field label="Serial no.">
            <Input value={serialNo} onChange={(e) => setSerialNo(e.target.value)} />
          </Field>
        </div>
        <Field label="Firmware version" hint="Recorded so a firmware change can be tied to change control.">
          <Input value={firmwareVersion} onChange={(e) => setFirmwareVersion(e.target.value)} />
        </Field>
        <label className="flex items-center gap-2 fs-2 mb-3">
          <input type="checkbox" checked={dedicated} onChange={(e) => setDedicated(e.target.checked)} />
          Dedicated to a single product or process
        </label>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !equipmentCode.trim() || !siteId}>
            {busy ? "Creating…" : "Create asset"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
