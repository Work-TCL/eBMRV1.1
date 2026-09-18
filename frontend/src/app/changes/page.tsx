"use client";

import { useState } from "react";
import { api, ApiError, hasPermission, formatDate, newIdempotencyKey, type ChangeControl } from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { QmsListPage } from "@/components/qms/QmsListPage";
import type { DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";

// app/modules/qms/change_models.py CHANGE_STATES / CHANGE_CLASSIFICATIONS / CHANGE_TYPES.
const CHANGE_STATES = [
  "DRAFT",
  "IMPACT_ASSESSMENT",
  "APPROVAL",
  "IMPLEMENTATION",
  "VERIFICATION",
  "EFFECTIVE",
  "CLOSED",
  "CANCELLED",
];
const CLASSIFICATIONS = ["temporary", "permanent"];
const CHANGE_TYPES = [
  "product", "process", "recipe", "spec", "material", "source", "equipment", "facility", "software",
  "document", "method", "label", "supplier",
];

export default function ChangesPage() {
  const { me } = useMe();
  const [createOpen, setCreateOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const columns: DataTableColumn<ChangeControl>[] = [
    {
      key: "change_number",
      header: "Number",
      sortable: true,
      render: (c) => (
        <span className="font-semibold tabular">
          {c.change_number}
          {c.emergency && (
            <span className="ml-auto">
              {" "}
              <StatePill state="conflict" icon="alert-triangle">
                Emergency
              </StatePill>
            </span>
          )}
        </span>
      ),
    },
    { key: "change_type", header: "Type", render: (c) => <span className="fs-2">{c.change_type}</span> },
    {
      key: "classification",
      header: "Classification",
      sortable: true,
      render: (c) => <span className="fs-2">{c.classification}</span>,
    },
    { key: "state", header: "State", sortable: true, render: (c) => <WorkflowStatePill state={c.state} /> },
    {
      key: "effective_at",
      header: "Effective",
      render: (c) => <span className="tabular fs-2">{formatDate(c.effective_at)}</span>,
    },
  ];

  return (
    <>
      <QmsListPage<ChangeControl>
        title="Change control"
        subtitle="Proposed changes through impact assessment, approval, implementation and verification."
        path="/qms/v1/changes"
        columns={columns}
        states={CHANGE_STATES}
        emptyIcon="refresh"
        emptyMessage="No change controls raised for this site."
        rowHref={(c) => `/changes/${c.id}`}
        reloadToken={reloadToken}
        action={
          hasPermission(me, "change.create") ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> Raise change
            </Button>
          ) : undefined
        }
      />
      {createOpen && (
        <RaiseChangeModal
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

function RaiseChangeModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { siteId } = useSiteId();
  const { me } = useMe();
  const [changeNumber, setChangeNumber] = useState("");
  const [changeType, setChangeType] = useState(CHANGE_TYPES[0]);
  const [classification, setClassification] = useState("permanent");
  const [currentState, setCurrentState] = useState("");
  const [proposedState, setProposedState] = useState("");
  const [reason, setReason] = useState("");
  const [emergency, setEmergency] = useState(false);
  const [emergencyReason, setEmergencyReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId || !me) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/qms/v1/changes", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        change_number: changeNumber,
        change_type: changeType,
        classification,
        current_state: { description: currentState },
        proposed_state: { description: proposedState },
        reason,
        owner_subject_id: me.user_id,
        emergency,
        emergency_reason: emergency ? emergencyReason : null,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to raise change control");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Raise a change control" large>
      <form onSubmit={submit}>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Change number" required>
            <Input value={changeNumber} onChange={(e) => setChangeNumber(e.target.value)} placeholder="CHG-0001" required autoFocus />
          </Field>
          <Field label="Type" required>
            <Select value={changeType} onChange={(e) => setChangeType(e.target.value)}>
              {CHANGE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Classification" required>
            <Select value={classification} onChange={(e) => setClassification(e.target.value)}>
              {CLASSIFICATIONS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <Field label="Current state" required hint="What exists today, in enough detail to be verifiable.">
          <textarea className="input" rows={2} value={currentState} onChange={(e) => setCurrentState(e.target.value)} required />
        </Field>
        <Field label="Proposed state" required>
          <textarea className="input" rows={2} value={proposedState} onChange={(e) => setProposedState(e.target.value)} required />
        </Field>
        <Field label="Reason for change" required>
          <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} required />
        </Field>
        <label className="flex items-center gap-2 fs-2 mb-3">
          <input type="checkbox" checked={emergency} onChange={(e) => setEmergency(e.target.checked)} />
          Emergency change
        </label>
        {emergency && (
          <Field
            label="Emergency justification"
            required
            hint="An emergency change requires a retrospective review before it can close."
          >
            <textarea className="input" rows={2} value={emergencyReason} onChange={(e) => setEmergencyReason(e.target.value)} required />
          </Field>
        )}
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !changeNumber.trim() || !siteId}>
            {busy ? "Raising…" : "Raise change"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
