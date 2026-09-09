"use client";

import { useState } from "react";
import {
  api,
  ApiError,
  canRaiseQualityEvent,
  formatDate,
  isOverdue,
  newIdempotencyKey,
  type Deviation,
} from "@/lib/api";
import { useEntityOptions, useMe, useSiteId, type EntityOption, type EntityOptionsStatus } from "@/lib/hooks";
import { QmsListPage } from "@/components/qms/QmsListPage";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import type { DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { BoolPill, SeverityPill, WorkflowStatePill } from "@/components/ui/StatePill";

// Document 26 §4's own state notation, matching app/modules/qms/models.py::DEVIATION_STATES.
const DEVIATION_STATES = [
  "OPEN",
  "TRIAGE",
  "CONTAINMENT",
  "INVESTIGATION",
  "IMPACT_ASSESSMENT",
  "DISPOSITION",
  "CLOSED",
  "REOPENED",
];
const SOURCE_TYPES = ["batch", "qc", "material", "equipment", "environment", "supplier", "document", "system"];
const SEVERITIES = ["critical", "major", "minor"];

// Not every source_type has a browsable list behind it yet (document/environment/system have no bulk-list
// endpoint — Document 26 doesn't require one, and building one is out of scope for this picker). Where a
// list does exist, `kind` names it for EntityPickerField's copy; where it doesn't, `manualHint` explains
// what the free-text ID should be instead of silently reusing the "couldn't load the list" error copy.
const SOURCE_PICKER_KIND: Partial<Record<string, string>> = {
  batch: "batch",
  qc: "QC sample",
  material: "material lot",
  equipment: "equipment asset",
  supplier: "supplier",
};
const SOURCE_MANUAL_HINT: Partial<Record<string, string>> = {
  environment: "The EM sample or task ID this deviation traces to.",
  document: "The document version ID this deviation traces to.",
  system: "No record picker for this source type — enter the relevant reference ID.",
};

export default function DeviationsPage() {
  const { me } = useMe();
  const [createOpen, setCreateOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const columns: DataTableColumn<Deviation>[] = [
    {
      key: "deviation_number",
      header: "Number",
      sortable: true,
      render: (d) => <span className="font-semibold tabular">{d.deviation_number}</span>,
    },
    { key: "deviation_type", header: "Type", render: (d) => <span className="fs-2">{d.deviation_type}</span> },
    { key: "source_type", header: "Source", render: (d) => <span className="fs-2">{d.source_type}</span> },
    { key: "severity", header: "Severity", sortable: true, render: (d) => <SeverityPill severity={d.severity} /> },
    { key: "state", header: "State", sortable: true, render: (d) => <WorkflowStatePill state={d.state} /> },
    {
      key: "capa_required",
      header: "CAPA",
      render: (d) => <BoolPill value={d.capa_required} trueLabel="Required" falseLabel="Not required" />,
    },
    {
      key: "due_date",
      header: "Due",
      sortable: true,
      render: (d) =>
        d.due_date ? (
          <span className={isOverdue(d.due_date) && d.state !== "CLOSED" ? "error-text tabular fs-2" : "tabular fs-2"}>
            {isOverdue(d.due_date) && d.state !== "CLOSED" && <Icon name="alert-triangle" />} {formatDate(d.due_date)}
          </span>
        ) : (
          <span className="text-muted">—</span>
        ),
    },
  ];

  return (
    <>
      <QmsListPage<Deviation>
        title="Deviations"
        subtitle="Quality events from raise through triage, containment, investigation, impact and disposition."
        path="/qms/v1/deviations"
        columns={columns}
        states={DEVIATION_STATES}
        emptyIcon="alert-triangle"
        emptyMessage="No deviations recorded for this site."
        rowHref={(d) => `/deviations/${d.id}`}
        reloadToken={reloadToken}
        action={
          canRaiseQualityEvent(me) ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> Raise deviation
            </Button>
          ) : undefined
        }
      />
      {createOpen && (
        <RaiseDeviationModal
          onClose={() => setCreateOpen(false)}
          onDone={() => {
            setCreateOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
    </>
  );
}

function RaiseDeviationModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { siteId } = useSiteId();
  const { me } = useMe();
  const entities = useEntityOptions();
  const [deviationNumber, setDeviationNumber] = useState("");
  const [deviationType, setDeviationType] = useState("process");
  const [sourceType, setSourceType] = useState(SOURCE_TYPES[0]);
  const [sourceId, setSourceId] = useState("");

  // Reset the picked/typed record whenever the source type changes — an id chosen against one entity
  // list (e.g. a batch) is never valid once the type switches to a different one (e.g. equipment).
  function changeSourceType(value: string) {
    setSourceType(value);
    setSourceId("");
  }

  // Which of useEntityOptions()'s lists backs this source_type's picker, if any.
  const sourcePicker: { options: EntityOption[]; status: EntityOptionsStatus } | null = (() => {
    switch (sourceType) {
      case "batch":
        return { options: entities.batches, status: entities.batchesStatus };
      case "qc":
        return { options: entities.qcSamples, status: entities.qcSamplesStatus };
      case "material":
        return { options: entities.materialLots, status: entities.materialLotsStatus };
      case "equipment":
        return { options: entities.equipment, status: entities.equipmentStatus };
      case "supplier":
        return { options: entities.suppliers, status: entities.suppliersStatus };
      default:
        return null;
    }
  })();
  const [severity, setSeverity] = useState("major");
  const [planned, setPlanned] = useState(false);
  const [scope, setScope] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId || !me) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/qms/v1/deviations", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        deviation_number: deviationNumber,
        deviation_type: deviationType,
        source_type: sourceType,
        source_id: sourceId,
        severity,
        owner_subject_id: me.user_id,
        planned,
        // DEV-FR-016: a planned deviation must declare a bounded scope and end date, or it becomes a
        // permanent alternative process. The backend enforces all three keys being present.
        planned_scope: planned ? { scope, start_date: startDate, end_date: endDate } : null,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to raise deviation");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Raise a deviation" large>
      <form onSubmit={submit}>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Deviation number" required>
            <Input
              value={deviationNumber}
              onChange={(e) => setDeviationNumber(e.target.value)}
              placeholder="DEV-0002"
              required
              autoFocus
            />
          </Field>
          <Field label="Type" required>
            <Input value={deviationType} onChange={(e) => setDeviationType(e.target.value)} required />
          </Field>
          <Field label="Severity" required>
            <Select value={severity} onChange={(e) => setSeverity(e.target.value)}>
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Source type" required>
            <Select value={sourceType} onChange={(e) => changeSourceType(e.target.value)}>
              {SOURCE_TYPES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </Field>
          {sourcePicker ? (
            <EntityPickerField
              label="Source record"
              required
              value={sourceId}
              onChange={setSourceId}
              options={sourcePicker.options}
              status={sourcePicker.status}
              kind={SOURCE_PICKER_KIND[sourceType]!}
            />
          ) : (
            <Field label="Source record ID" required hint={SOURCE_MANUAL_HINT[sourceType]}>
              <Input value={sourceId} onChange={(e) => setSourceId(e.target.value)} required />
            </Field>
          )}
        </div>

        <label className="flex items-center gap-2 fs-2 mb-3">
          <input type="checkbox" checked={planned} onChange={(e) => setPlanned(e.target.checked)} />
          Planned deviation
        </label>

        {planned && (
          <>
            <Field label="Planned scope" required hint="What the alternative process covers.">
              <Input value={scope} onChange={(e) => setScope(e.target.value)} required />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Start date" required>
                <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
              </Field>
              <Field
                label="End date"
                required
                hint="Hard stop — the record cannot advance past this date."
              >
                <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
              </Field>
            </div>
          </>
        )}

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={busy || !deviationNumber.trim() || !sourceId.trim() || !siteId}
          >
            {busy ? "Raising…" : "Raise deviation"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
