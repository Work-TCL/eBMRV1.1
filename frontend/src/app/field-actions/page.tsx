"use client";

import { useState } from "react";
import { api, ApiError, canApproveQms, canInvestigateQms, formatDate, newIdempotencyKey, type FieldAction } from "@/lib/api";
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
import { StatePill, BoolPill, WorkflowStatePill } from "@/components/ui/StatePill";

// app/modules/qms/field_action_models.py, verbatim from Document 36.
const FIELD_ACTION_STATES = [
  "ASSESSMENT",
  "SCOPE_DEFINITION",
  "REGULATORY_DECISION",
  "APPROVAL",
  "EXECUTION_NOTIFICATION",
  "RECONCILIATION",
  "EFFECTIVENESS",
  "CLOSED",
];
const ACTION_TYPES = ["recall", "correction", "removal", "field_action", "customer_advisory", "stock_recovery"];
const TRIGGER_TYPES = ["complaint", "deviation", "capa", "trend", "regulatory_request", "management_decision"];

// complaint/deviation/capa are real browsable QMS record types (`entities.complaints`/`.deviations`/
// `.capas`); trend/regulatory_request/management_decision are category labels, not a record type with
// its own list. Same honest split as `deviations/page.tsx`'s SOURCE_PICKER_KIND/SOURCE_MANUAL_HINT.
const TRIGGER_PICKER_KIND: Partial<Record<string, string>> = {
  complaint: "complaint",
  deviation: "deviation",
  capa: "CAPA",
};
const TRIGGER_MANUAL_HINT: Partial<Record<string, string>> = {
  trend: "No single record for a trend trigger — describe/reference the trend analysis that triggered this action.",
  regulatory_request: "No single record for a regulatory-request trigger — the relevant correspondence/reference ID.",
  management_decision: "No single record for a management-decision trigger — the relevant meeting/decision reference.",
};

export default function FieldActionsPage() {
  const { me } = useMe();
  const [createOpen, setCreateOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const columns: DataTableColumn<FieldAction>[] = [
    {
      key: "action_number",
      header: "Number",
      sortable: true,
      render: (f) => <span className="font-semibold tabular">{f.action_number}</span>,
    },
    {
      key: "action_type",
      header: "Type",
      sortable: true,
      render: (f) => (
        <StatePill state={f.action_type === "recall" ? "failed" : "conflict"} icon="flag">
          {f.action_type}
        </StatePill>
      ),
    },
    { key: "state", header: "State", sortable: true, render: (f) => <WorkflowStatePill state={f.state} /> },
    { key: "revision", header: "Revision", render: (f) => <span className="tabular fs-2">{f.revision}</span> },
    {
      key: "capa_required",
      header: "CAPA",
      render: (f) => <BoolPill value={f.capa_required} trueLabel="Required" falseLabel="Not required" />,
    },
    {
      key: "created_at",
      header: "Raised",
      sortable: true,
      render: (f) => <span className="tabular fs-2">{formatDate(f.created_at)}</span>,
    },
  ];

  return (
    <>
      <QmsListPage<FieldAction>
        title="Field actions"
        subtitle="Recalls, corrections and removals from scope definition through reconciliation and effectiveness."
        path="/qms/v1/field-actions"
        columns={columns}
        states={FIELD_ACTION_STATES}
        emptyIcon="flag"
        emptyMessage="No field actions raised for this site."
        rowHref={(f) => `/field-actions/${f.id}`}
        reloadToken={reloadToken}
        action={
          canInvestigateQms(me) || canApproveQms(me) ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> Raise field action
            </Button>
          ) : undefined
        }
      />
      {createOpen && (
        <RaiseFieldActionModal
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

function RaiseFieldActionModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { siteId } = useSiteId();
  const entities = useEntityOptions();
  const [actionNumber, setActionNumber] = useState("");
  const [actionType, setActionType] = useState(ACTION_TYPES[0]);
  const [triggerType, setTriggerType] = useState(TRIGGER_TYPES[0]);
  const [triggerId, setTriggerId] = useState("");

  function changeTriggerType(value: string) {
    setTriggerType(value);
    setTriggerId("");
  }

  const triggerPicker: { options: EntityOption[]; status: EntityOptionsStatus } | null = (() => {
    switch (triggerType) {
      case "complaint":
        return { options: entities.complaints, status: entities.complaintsStatus };
      case "deviation":
        return { options: entities.deviations, status: entities.deviationsStatus };
      case "capa":
        return { options: entities.capas, status: entities.capasStatus };
      default:
        return null;
    }
  })();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/qms/v1/field-actions", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        action_number: actionNumber,
        action_type: actionType,
        // FAR-FR-001: a field action always traces to what triggered it; the backend validates
        // trigger_ref.source_type against its own list.
        trigger_ref: { source_type: triggerType, source_id: triggerId },
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to raise field action");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Raise a field action">
      <form onSubmit={submit}>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Action number" required>
            <Input value={actionNumber} onChange={(e) => setActionNumber(e.target.value)} placeholder="FA-0001" required autoFocus />
          </Field>
          <Field label="Action type" required>
            <Select value={actionType} onChange={(e) => setActionType(e.target.value)}>
              {ACTION_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Trigger type" required>
            <Select value={triggerType} onChange={(e) => changeTriggerType(e.target.value)}>
              {TRIGGER_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
          {triggerPicker ? (
            <EntityPickerField
              label="Trigger record"
              required
              value={triggerId}
              onChange={setTriggerId}
              options={triggerPicker.options}
              status={triggerPicker.status}
              kind={TRIGGER_PICKER_KIND[triggerType]!}
            />
          ) : (
            <Field label="Trigger record ID" required hint={TRIGGER_MANUAL_HINT[triggerType]}>
              <Input value={triggerId} onChange={(e) => setTriggerId(e.target.value)} required />
            </Field>
          )}
        </div>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !actionNumber.trim() || !siteId}>
            {busy ? "Raising…" : "Raise field action"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
