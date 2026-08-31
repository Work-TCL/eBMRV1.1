"use client";

import { useState } from "react";
import { api, ApiError, canRaiseQualityEvent, newIdempotencyKey, type Nonconformance } from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { QmsListPage } from "@/components/qms/QmsListPage";
import type { DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { StatePill, BoolPill, SeverityPill, WorkflowStatePill } from "@/components/ui/StatePill";

// app/modules/qms/ncr_models.py NCR_STATES / NCR_SCOPE_TYPES.
const NCR_STATES = [
  "OPEN", "SEGREGATED", "EVALUATION", "REWORK", "REPAIR", "RETURN", "SCRAP", "USE_AS_IS",
  "VERIFICATION", "CLOSED",
];
const SCOPE_TYPES = ["material", "component", "subassembly", "device", "packaging", "finished_output"];
const SEVERITIES = ["critical", "major", "minor"];

export default function NonconformancesPage() {
  const { me } = useMe();
  const [createOpen, setCreateOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const columns: DataTableColumn<Nonconformance>[] = [
    {
      key: "ncr_number",
      header: "Number",
      sortable: true,
      render: (n) => <span className="font-semibold tabular">{n.ncr_number}</span>,
    },
    { key: "defect_code", header: "Defect", render: (n) => <span className="fs-2">{n.defect_code}</span> },
    { key: "scope_type", header: "Scope", render: (n) => <span className="fs-2">{n.scope_type}</span> },
    { key: "severity", header: "Severity", sortable: true, render: (n) => <SeverityPill severity={n.severity} /> },
    { key: "state", header: "State", sortable: true, render: (n) => <WorkflowStatePill state={n.state} /> },
    {
      key: "release_blocker_active",
      header: "Release",
      render: (n) =>
        n.release_blocker_active ? (
          <StatePill state="blocked" icon="lock">
            Blocked
          </StatePill>
        ) : (
          <span className="text-muted">—</span>
        ),
    },
    {
      key: "capa_required",
      header: "CAPA",
      render: (n) => <BoolPill value={n.capa_required} trueLabel="Required" falseLabel="Not required" />,
    },
  ];

  return (
    <>
      <QmsListPage<Nonconformance>
        title="Nonconformances"
        subtitle="Document 28 — nonconforming product from segregation through evaluation and disposition to verification."
        path="/qms/v1/nonconformances"
        columns={columns}
        states={NCR_STATES}
        emptyIcon="cross-medical"
        emptyMessage="No nonconformances recorded for this site."
        rowHref={(n) => `/nonconformances/${n.id}`}
        reloadToken={reloadToken}
        action={
          canRaiseQualityEvent(me) ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> Raise NCR
            </Button>
          ) : undefined
        }
      />
      {createOpen && (
        <RaiseNcrModal
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

function RaiseNcrModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { siteId } = useSiteId();
  const { me } = useMe();
  const [ncrNumber, setNcrNumber] = useState("");
  const [scopeType, setScopeType] = useState(SCOPE_TYPES[0]);
  const [scopeRecordId, setScopeRecordId] = useState("");
  const [defectCode, setDefectCode] = useState("");
  const [severity, setSeverity] = useState("major");
  const [specRef, setSpecRef] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId || !me) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/qms/v1/nonconformances", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        ncr_number: ncrNumber,
        scope_type: scopeType,
        scope_records: [{ record_type: scopeType, record_id: scopeRecordId }],
        // NCR-FR-004: a nonconformance is nonconformance *to something* — the backend requires the
        // requirement reference to name either a specification or a test.
        requirement_ref: { spec_ref: specRef },
        defect_code: defectCode,
        severity,
        owner_subject_id: me.user_id,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to raise nonconformance");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Raise a nonconformance" large>
      <form onSubmit={submit}>
        <div className="grid grid-cols-3 gap-4">
          <Field label="NCR number" required>
            <Input value={ncrNumber} onChange={(e) => setNcrNumber(e.target.value)} placeholder="NCR-0001" required autoFocus />
          </Field>
          <Field label="Defect code" required>
            <Input value={defectCode} onChange={(e) => setDefectCode(e.target.value)} required />
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
          <Field label="Scope type" required>
            <Select value={scopeType} onChange={(e) => setScopeType(e.target.value)}>
              {SCOPE_TYPES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Affected record ID" required>
            <Input value={scopeRecordId} onChange={(e) => setScopeRecordId(e.target.value)} required />
          </Field>
        </div>
        <Field label="Specification reference" required hint="The requirement this product fails to meet.">
          <Input value={specRef} onChange={(e) => setSpecRef(e.target.value)} required />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !ncrNumber.trim() || !siteId}>
            {busy ? "Raising…" : "Raise nonconformance"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
