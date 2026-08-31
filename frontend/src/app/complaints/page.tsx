"use client";

import { useState } from "react";
import { api, ApiError, canRaiseQualityEvent, formatDate, newIdempotencyKey, type Complaint } from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { QmsListPage } from "@/components/qms/QmsListPage";
import type { DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { StatePill, BoolPill, WorkflowStatePill } from "@/components/ui/StatePill";

// app/modules/qms/complaint_models.py COMPLAINT_STATES / SOURCE_CHANNELS.
const COMPLAINT_STATES = [
  "RECEIVED",
  "TRIAGE",
  "NO_INVESTIGATION_JUSTIFIED",
  "INVESTIGATION",
  "REPORTABILITY_ASSESSMENT",
  "RESPONSE",
  "CLOSED",
];
const SOURCE_CHANNELS = ["oral", "written", "electronic"];

export default function ComplaintsPage() {
  const { me } = useMe();
  const [createOpen, setCreateOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const columns: DataTableColumn<Complaint>[] = [
    {
      key: "complaint_number",
      header: "Number",
      sortable: true,
      render: (c) => (
        <span className="font-semibold tabular">
          {c.complaint_number}
          {c.is_potential_duplicate && (
            <span>
              {" "}
              <StatePill state="stale" icon="alert-triangle">
                Possible duplicate
              </StatePill>
            </span>
          )}
        </span>
      ),
    },
    { key: "nature_code", header: "Nature", render: (c) => <span className="fs-2">{c.nature_code}</span> },
    { key: "source_channel", header: "Channel", render: (c) => <span className="fs-2">{c.source_channel}</span> },
    {
      key: "received_at",
      header: "Received",
      sortable: true,
      render: (c) => <span className="tabular fs-2">{formatDate(c.received_at)}</span>,
    },
    { key: "state", header: "State", sortable: true, render: (c) => <WorkflowStatePill state={c.state} /> },
    {
      key: "investigation_required",
      header: "Investigation",
      render: (c) => <BoolPill value={c.investigation_required} trueLabel="Required" falseLabel="Justified none" />,
    },
  ];

  return (
    <>
      <QmsListPage<Complaint>
        title="Complaints"
        subtitle="Document 35 — customer complaints from intake through triage, investigation and regulatory reportability."
        path="/qms/v1/complaints"
        columns={columns}
        states={COMPLAINT_STATES}
        emptyIcon="bell"
        emptyMessage="No complaints logged for this site."
        rowHref={(c) => `/complaints/${c.id}`}
        reloadToken={reloadToken}
        defaultSort={{ by: "received_at", dir: "desc" }}
        action={
          canRaiseQualityEvent(me) ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> Log complaint
            </Button>
          ) : undefined
        }
      />
      {createOpen && (
        <LogComplaintModal
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

function LogComplaintModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { siteId } = useSiteId();
  const [complaintNumber, setComplaintNumber] = useState("");
  const [receivedAt, setReceivedAt] = useState(new Date().toISOString().slice(0, 10));
  const [sourceChannel, setSourceChannel] = useState(SOURCE_CHANNELS[0]);
  const [natureCode, setNatureCode] = useState("");
  const [description, setDescription] = useState("");
  const [productRef, setProductRef] = useState("");
  const [lotRef, setLotRef] = useState("");
  const [complainant, setComplainant] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/qms/v1/complaints", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        complaint_number: complaintNumber,
        received_at: new Date(receivedAt).toISOString(),
        source_channel: sourceChannel,
        nature_code: natureCode,
        description,
        product_ref: productRef || null,
        lot_batch_serial_refs: lotRef ? { reference: lotRef } : null,
        complainant_info: complainant ? { contact: complainant } : null,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to log complaint");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Log a complaint" large>
      <form onSubmit={submit}>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Complaint number" required>
            <Input value={complaintNumber} onChange={(e) => setComplaintNumber(e.target.value)} placeholder="CMP-0001" required autoFocus />
          </Field>
          <Field label="Received at" required hint="Starts the reportability clock.">
            <Input type="date" value={receivedAt} onChange={(e) => setReceivedAt(e.target.value)} required />
          </Field>
          <Field label="Source channel" required>
            <Select value={sourceChannel} onChange={(e) => setSourceChannel(e.target.value)}>
              {SOURCE_CHANNELS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <Field label="Nature code" required hint="The complaint category, e.g. packaging_defect, efficacy, injury.">
          <Input value={natureCode} onChange={(e) => setNatureCode(e.target.value)} required />
        </Field>
        <Field label="Description" required hint="The complainant's own account, recorded as reported.">
          <textarea className="input" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} required />
        </Field>
        <Field
          label="Product version ID"
          hint="A released product version ID from Product Master. The complaint cannot be triaged until this is resolved."
        >
          <Input value={productRef} onChange={(e) => setProductRef(e.target.value)} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Lot / batch / serial reference">
            <Input value={lotRef} onChange={(e) => setLotRef(e.target.value)} />
          </Field>
          <Field label="Complainant contact">
            <Input value={complainant} onChange={(e) => setComplainant(e.target.value)} />
          </Field>
        </div>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !complaintNumber.trim() || !siteId}>
            {busy ? "Logging…" : "Log complaint"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
