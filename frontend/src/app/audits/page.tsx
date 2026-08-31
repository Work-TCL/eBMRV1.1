"use client";

import { useState } from "react";
import { api, ApiError, canInvestigateQms, formatDate, newIdempotencyKey, type InternalAudit } from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { QmsListPage } from "@/components/qms/QmsListPage";
import type { DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";

// app/modules/qms/internal_audit_models.py INTERNAL_AUDIT_STATES.
const AUDIT_STATES = ["SCHEDULED", "IN_PROGRESS", "FINDINGS_OPEN", "CLOSED"];

export default function AuditsPage() {
  const { me } = useMe();
  const [createOpen, setCreateOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const columns: DataTableColumn<InternalAudit>[] = [
    {
      key: "audit_number",
      header: "Number",
      sortable: true,
      render: (a) => <span className="font-semibold tabular">{a.audit_number}</span>,
    },
    { key: "program_ref", header: "Programme", render: (a) => <span className="fs-2">{a.program_ref}</span> },
    {
      key: "scheduled_at",
      header: "Scheduled",
      sortable: true,
      render: (a) => <span className="tabular fs-2">{formatDate(a.scheduled_at)}</span>,
    },
    {
      key: "actual_start_at",
      header: "Conducted",
      render: (a) => (
        <span className="tabular fs-2">
          {a.actual_start_at ? `${formatDate(a.actual_start_at)}${a.actual_end_at ? ` – ${formatDate(a.actual_end_at)}` : ""}` : "—"}
        </span>
      ),
    },
    { key: "state", header: "State", sortable: true, render: (a) => <WorkflowStatePill state={a.state} /> },
  ];

  return (
    <>
      <QmsListPage<InternalAudit>
        title="Internal audits"
        subtitle="Document 34 — the audit programme, its findings, auditee responses and closure verification."
        path="/qms/v1/audits"
        columns={columns}
        states={AUDIT_STATES}
        emptyIcon="clipboard"
        emptyMessage="No internal audits scheduled for this site."
        rowHref={(a) => `/audits/${a.id}`}
        reloadToken={reloadToken}
        defaultSort={{ by: "scheduled_at", dir: "desc" }}
        action={
          canInvestigateQms(me) ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> Schedule audit
            </Button>
          ) : undefined
        }
      />
      {createOpen && (
        <ScheduleAuditModal
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

function ScheduleAuditModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { siteId } = useSiteId();
  const { me } = useMe();
  const [auditNumber, setAuditNumber] = useState("");
  const [programRef, setProgramRef] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [criteria, setCriteria] = useState("");
  const [processScope, setProcessScope] = useState("");
  const [leadAuditor, setLeadAuditor] = useState(me?.user_id ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/qms/v1/audits", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        audit_number: auditNumber,
        program_ref: programRef,
        criteria_refs: { standards: criteria.split(",").map((c) => c.trim()).filter(Boolean) },
        lead_auditor_id: leadAuditor,
        scheduled_at: new Date(scheduledAt).toISOString(),
        process_scope: processScope ? { processes: processScope.split(",").map((p) => p.trim()) } : null,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to schedule audit");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Schedule an internal audit" large>
      <form onSubmit={submit}>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Audit number" required>
            <Input value={auditNumber} onChange={(e) => setAuditNumber(e.target.value)} placeholder="IA-0001" required autoFocus />
          </Field>
          <Field label="Programme reference" required>
            <Input value={programRef} onChange={(e) => setProgramRef(e.target.value)} required />
          </Field>
          <Field label="Scheduled date" required>
            <Input type="date" value={scheduledAt} onChange={(e) => setScheduledAt(e.target.value)} required />
          </Field>
        </div>
        <Field label="Audit criteria" required hint="Comma-separated standards or procedures audited against.">
          <Input value={criteria} onChange={(e) => setCriteria(e.target.value)} placeholder="21 CFR 820, ISO 13485" required />
        </Field>
        <Field
          label="Process scope"
          required
          hint="Comma-separated processes in scope. An audit must declare a site or process scope."
        >
          <Input
            value={processScope}
            onChange={(e) => setProcessScope(e.target.value)}
            placeholder="CAPA, Complaint handling"
            required
          />
        </Field>
        <Field label="Lead auditor (user ID)" required hint="SOD-016: the auditor must be independent of the area audited.">
          <Input value={leadAuditor} onChange={(e) => setLeadAuditor(e.target.value)} required />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !auditNumber.trim() || !processScope.trim() || !siteId}>
            {busy ? "Scheduling…" : "Schedule audit"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
