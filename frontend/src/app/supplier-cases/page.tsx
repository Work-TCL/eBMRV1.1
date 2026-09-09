"use client";

import { useState } from "react";
import { api, ApiError, canInvestigateQms, formatDate, newIdempotencyKey, type SupplierCase } from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { QmsListPage } from "@/components/qms/QmsListPage";
import type { DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { SeverityPill, WorkflowStatePill } from "@/components/ui/StatePill";

// app/modules/qms/scar_models.py CASE_STATES (the SCAR itself has its own SCAR_STATES).
const CASE_STATES = ["OPEN", "CONTAINMENT", "SCAR_ISSUED", "CLOSED"];
const SEVERITIES = ["critical", "major", "minor"];

export default function SupplierCasesPage() {
  const { me } = useMe();
  const [createOpen, setCreateOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const columns: DataTableColumn<SupplierCase>[] = [
    {
      key: "case_number",
      header: "Number",
      sortable: true,
      render: (c) => <span className="font-semibold tabular">{c.case_number}</span>,
    },
    { key: "defect_code", header: "Defect", render: (c) => <span className="fs-2">{c.defect_code}</span> },
    { key: "severity", header: "Severity", sortable: true, render: (c) => <SeverityPill severity={c.severity} /> },
    {
      key: "affected_lots",
      header: "Affected lots",
      render: (c) => <span className="tabular fs-2">{c.affected_lots.length}</span>,
    },
    { key: "state", header: "State", sortable: true, render: (c) => <WorkflowStatePill state={c.state} /> },
    {
      key: "created_at",
      header: "Opened",
      sortable: true,
      render: (c) => <span className="tabular fs-2">{formatDate(c.created_at)}</span>,
    },
  ];

  return (
    <>
      <QmsListPage<SupplierCase>
        title="Supplier cases"
        subtitle="Supplier quality cases and the SCARs issued against them."
        path="/qms/v1/supplier-cases"
        columns={columns}
        states={CASE_STATES}
        emptyIcon="building"
        emptyMessage="No supplier quality cases opened for this site."
        rowHref={(c) => `/supplier-cases/${c.id}`}
        reloadToken={reloadToken}
        action={
          canInvestigateQms(me) ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> Open case
            </Button>
          ) : undefined
        }
      />
      {createOpen && (
        <OpenCaseModal
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

function OpenCaseModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { siteId } = useSiteId();
  const { me } = useMe();
  const [caseNumber, setCaseNumber] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [materialId, setMaterialId] = useState("");
  const [affectedLot, setAffectedLot] = useState("");
  const [defectCode, setDefectCode] = useState("");
  const [severity, setSeverity] = useState("major");
  const [containment, setContainment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId || !me) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/qms/v1/supplier-cases", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        case_number: caseNumber,
        supplier_id: supplierId,
        material_id: materialId || null,
        affected_lots: affectedLot ? [{ lot: affectedLot }] : [],
        defect_code: defectCode,
        severity,
        internal_owner_subject_id: me.user_id,
        containment: containment ? { description: containment } : null,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to open supplier case");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Open a supplier quality case" large>
      <form onSubmit={submit}>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Case number" required>
            <Input value={caseNumber} onChange={(e) => setCaseNumber(e.target.value)} placeholder="SQC-0001" required autoFocus />
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
          <Field label="Supplier ID" required hint="From the supplier register.">
            <Input value={supplierId} onChange={(e) => setSupplierId(e.target.value)} required />
          </Field>
          <Field label="Material ID">
            <Input value={materialId} onChange={(e) => setMaterialId(e.target.value)} />
          </Field>
        </div>
        <Field label="Affected lot" hint="The supplier lot this case concerns.">
          <Input value={affectedLot} onChange={(e) => setAffectedLot(e.target.value)} />
        </Field>
        <Field label="Containment" hint="What has been done to stop affected material being used.">
          <textarea className="input" rows={2} value={containment} onChange={(e) => setContainment(e.target.value)} />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !caseNumber.trim() || !supplierId.trim() || !siteId}>
            {busy ? "Opening…" : "Open case"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
