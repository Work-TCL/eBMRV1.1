"use client";

import { useEffect, useState } from "react";
import {
  api,
  ApiError,
  hasPermission,
  formatDate,
  isOverdue,
  newIdempotencyKey,
  type Capa,
} from "@/lib/api";
import { useEntityOptions, useMe, useRequirePermission, useSiteId, type EntityOption, type EntityOptionsStatus } from "@/lib/hooks";
import { QmsListPage } from "@/components/qms/QmsListPage";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import type { DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { SeverityPill, WorkflowStatePill } from "@/components/ui/StatePill";

// app/modules/qms/capa_commands.py state machine.
// app/modules/qms/capa_models.py CAPA_STATES / CAPA_SOURCE_TYPES.
const CAPA_STATES = [
  "OPEN",
  "PLAN",
  "IMPLEMENTATION",
  "IMPLEMENTATION_VERIFIED",
  "EFFECTIVENESS_MONITORING",
  "EFFECTIVENESS_REVIEW",
  "EFFECTIVENESS_FAILED",
  "CLOSED",
  "CANCELLED",
  "REOPENED",
];
const RISK_CLASSES = ["high", "medium", "low"];
const SOURCE_TYPES = [
  "deviation", "oos", "oot", "ncr", "complaint", "audit", "supplier", "risk", "trend", "security",
  "validation",
];

// Not every source_type has a browsable list behind it — same honest split `deviations/page.tsx`'s own
// SOURCE_PICKER_KIND/SOURCE_MANUAL_HINT pair already established. `oos`/`oot` gained real list endpoints
// (qc/router.py::list_oos_records/list_oot_records, 2026-09-26) so they get real pickers now too;
// `trend`/`security`/`validation` aren't real browsable record types in this system at all
// (proactive/category labels, not entities with a list) and stay free text.
const SOURCE_PICKER_KIND: Partial<Record<string, string>> = {
  deviation: "deviation",
  ncr: "nonconformance",
  complaint: "complaint",
  audit: "internal audit",
  supplier: "supplier",
  risk: "risk",
  oos: "OOS record",
  oot: "OOT record",
};
const SOURCE_MANUAL_HINT: Partial<Record<string, string>> = {
  trend: "No single record for a trend origin — describe/reference the trend analysis this CAPA answers.",
  security: "No single record for a security-incident origin yet — the relevant reference ID.",
  validation: "No single record for a validation-finding origin yet — the relevant reference ID.",
};

export default function CapaPage() {
  const { me } = useRequirePermission("capa.view");
  const [createOpen, setCreateOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const [prefillSource, setPrefillSource] = useState<{ sourceType: string; sourceId: string } | null>(null);

  // Deep link from a source record's own "Create linked CAPA" action (e.g. deviations/[id]/page.tsx,
  // `?source_type=deviation&source_id=<id>`) — opens the Raise CAPA modal pre-filled with that source
  // instead of making the user re-select it. Reads window.location directly rather than next/navigation's
  // useSearchParams(), to avoid opting this page into a Suspense boundary it has no other reason to need.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sourceType = params.get("source_type");
    const sourceId = params.get("source_id");
    if (sourceType && sourceId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPrefillSource({ sourceType, sourceId });
      setCreateOpen(true);
    }
  }, []);

  const columns: DataTableColumn<Capa>[] = [
    {
      key: "capa_number",
      header: "Number",
      sortable: true,
      render: (c) => <span className="font-semibold tabular">{c.capa_number}</span>,
    },
    {
      key: "problem_statement",
      header: "Problem",
      render: (c) => (
        <span className="fs-2" title={c.problem_statement}>
          {c.problem_statement.length > 70 ? `${c.problem_statement.slice(0, 70)}…` : c.problem_statement}
        </span>
      ),
    },
    { key: "source_type", header: "Source", render: (c) => <span className="fs-2">{c.source_type}</span> },
    {
      key: "risk_class",
      header: "Risk class",
      sortable: true,
      render: (c) => <SeverityPill severity={c.risk_class} />,
    },
    { key: "state", header: "State", sortable: true, render: (c) => <WorkflowStatePill state={c.state} /> },
    {
      key: "target_date",
      header: "Target",
      sortable: true,
      render: (c) => (
        <span
          className={
            isOverdue(c.target_date) && c.state !== "CLOSED" ? "error-text tabular fs-2" : "tabular fs-2"
          }
        >
          {isOverdue(c.target_date) && c.state !== "CLOSED" && <Icon name="alert-triangle" />}{" "}
          {formatDate(c.target_date)}
        </span>
      ),
    },
  ];

  return (
    <>
      <QmsListPage<Capa>
        title="CAPA"
        subtitle="Corrective and preventive actions from plan through implementation to effectiveness."
        path="/qms/v1/capas"
        columns={columns}
        states={CAPA_STATES}
        emptyIcon="shield-check"
        emptyMessage="No CAPAs raised for this site."
        rowHref={(c) => `/capa/${c.id}`}
        reloadToken={reloadToken}
        action={
          hasPermission(me, "capa.create") ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> Raise CAPA
            </Button>
          ) : undefined
        }
      />
      {createOpen && (
        <RaiseCapaModal
          initialSourceType={prefillSource?.sourceType}
          initialSourceId={prefillSource?.sourceId}
          onClose={() => {
            setCreateOpen(false);
            setPrefillSource(null);
          }}
          onDone={() => {
            setCreateOpen(false);
            setPrefillSource(null);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
    </>
  );
}

function RaiseCapaModal({
  initialSourceType,
  initialSourceId,
  onClose,
  onDone,
}: {
  /** Pre-fills the source when this modal was opened from a source record's own "Create linked CAPA"
   * action (see CapaPage's `?source_type=`/`?source_id=` deep link) — still editable, not locked, in
   * case the wrong record linked here. */
  initialSourceType?: string;
  initialSourceId?: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const { siteId } = useSiteId();
  const { me } = useMe();
  const entities = useEntityOptions();
  const [capaNumber, setCapaNumber] = useState("");
  const [sourceType, setSourceType] = useState(
    initialSourceType && SOURCE_TYPES.includes(initialSourceType) ? initialSourceType : SOURCE_TYPES[0]
  );
  const [sourceId, setSourceId] = useState(initialSourceId ?? "");

  // Reset the picked/typed record whenever the source type changes — an id chosen against one entity
  // list is never valid once the type switches to a different one (same rule deviations/page.tsx's
  // changeSourceType follows).
  function changeSourceType(value: string) {
    setSourceType(value);
    setSourceId("");
  }

  // Which of useEntityOptions()'s lists backs this source_type's picker, if any.
  const sourcePicker: { options: EntityOption[]; status: EntityOptionsStatus } | null = (() => {
    switch (sourceType) {
      case "deviation":
        return { options: entities.deviations, status: entities.deviationsStatus };
      case "ncr":
        return { options: entities.nonconformances, status: entities.nonconformancesStatus };
      case "complaint":
        return { options: entities.complaints, status: entities.complaintsStatus };
      case "audit":
        return { options: entities.internalAudits, status: entities.internalAuditsStatus };
      case "supplier":
        return { options: entities.suppliers, status: entities.suppliersStatus };
      case "risk":
        return { options: entities.risks, status: entities.risksStatus };
      case "oos":
        return { options: entities.oosRecords, status: entities.oosRecordsStatus };
      case "oot":
        return { options: entities.ootRecords, status: entities.ootRecordsStatus };
      default:
        return null;
    }
  })();
  const [problem, setProblem] = useState("");
  const [riskClass, setRiskClass] = useState("medium");
  const [targetDate, setTargetDate] = useState("");
  const [investigationRef, setInvestigationRef] = useState("");
  const [proactiveRationale, setProactiveRationale] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // CAPA-FR-004 accepts either an investigation reference or a proactive rationale; the source type
  // vocabulary has no "proactive" member, so "trend" and "risk" are the proactive-style origins.
  const proactive = sourceType === "trend" || sourceType === "risk";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId || !me) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/qms/v1/capas", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        capa_number: capaNumber,
        source_type: sourceType,
        source_id: sourceId,
        problem_statement: problem,
        risk_class: riskClass,
        owner_subject_id: me.user_id,
        target_date: new Date(targetDate).toISOString(),
        // CAPA-FR-004: a CAPA must trace to either a concluded investigation or a stated proactive
        // rationale — the backend rejects a root_cause_ref carrying neither.
        root_cause_ref: proactive
          ? { proactive_rationale: proactiveRationale }
          : { investigation_ref: investigationRef },
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to raise CAPA");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Raise a CAPA" large>
      <form onSubmit={submit}>
        <div className="grid grid-cols-3 gap-4">
          <Field label="CAPA number" required>
            <Input value={capaNumber} onChange={(e) => setCapaNumber(e.target.value)} placeholder="CAPA-0001" required autoFocus />
          </Field>
          <Field label="Risk class" required>
            <Select value={riskClass} onChange={(e) => setRiskClass(e.target.value)}>
              {RISK_CLASSES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Target date" required>
            <Input type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} required />
          </Field>
        </div>
        <Field label="Problem statement" required>
          <textarea className="input" rows={3} value={problem} onChange={(e) => setProblem(e.target.value)} required />
        </Field>
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
        {proactive ? (
          <Field label="Proactive rationale" required hint="Why this CAPA is raised without a triggering investigation.">
            <textarea
              className="input"
              rows={2}
              value={proactiveRationale}
              onChange={(e) => setProactiveRationale(e.target.value)}
              required
            />
          </Field>
        ) : (
          <Field label="Investigation reference" required hint="The concluded investigation this CAPA answers.">
            <Input value={investigationRef} onChange={(e) => setInvestigationRef(e.target.value)} required />
          </Field>
        )}
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !capaNumber.trim() || !targetDate || !siteId}>
            {busy ? "Raising…" : "Raise CAPA"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
