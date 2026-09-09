"use client";

import { useState } from "react";
import { api, ApiError, canInvestigateQms, formatDate, isOverdue, newIdempotencyKey, type RiskRecord } from "@/lib/api";
import { useApiResource, useMe, useSiteId } from "@/lib/hooks";
import { QmsListPage } from "@/components/qms/QmsListPage";
import type { DataTableColumn } from "@/components/ui/DataTable";
import { KpiRow, KpiTile } from "@/components/ui/KpiTile";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";

const RISK_STATES = [
  "DRAFT",
  "INITIAL_ASSESSMENT",
  "CONTROLS_MITIGATION",
  "RESIDUAL_ASSESSMENT",
  "ACCEPTED",
  "NEW_VERSION",
];
const RISK_TYPES = ["product", "process", "system", "supplier", "equipment", "software"];

interface RiskDashboard {
  site_id: string;
  risks: {
    id: string;
    risk_number: string;
    risk_type: string;
    state: string;
    next_review_due_at: string | null;
    is_overdue: boolean;
    initial_score: Record<string, unknown> | null;
    residual_score: Record<string, unknown> | null;
  }[];
  by_state: Record<string, number>;
  by_type: Record<string, number>;
  overdue_count: number;
}

export default function RisksPage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [createOpen, setCreateOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const { data: dashboard } = useApiResource<RiskDashboard>(
    siteId ? `/qms/v1/risks/dashboard?site_id=${siteId}` : null
  );

  const columns: DataTableColumn<RiskRecord>[] = [
    {
      key: "risk_number",
      header: "Number",
      sortable: true,
      render: (r) => <span className="font-semibold tabular">{r.risk_number}</span>,
    },
    { key: "risk_type", header: "Type", sortable: true, render: (r) => <span className="fs-2">{r.risk_type}</span> },
    {
      key: "hazard_problem",
      header: "Hazard",
      render: (r) => (
        <span className="fs-2" title={r.hazard_problem}>
          {r.hazard_problem.length > 60 ? `${r.hazard_problem.slice(0, 60)}…` : r.hazard_problem}
        </span>
      ),
    },
    { key: "state", header: "State", sortable: true, render: (r) => <WorkflowStatePill state={r.state} /> },
    {
      key: "next_review_due_at",
      header: "Review due",
      sortable: true,
      render: (r) => {
        const overdue = isOverdue(r.next_review_due_at) && r.state === "ACCEPTED";
        return (
          <span className={overdue ? "error-text tabular fs-2" : "tabular fs-2"}>
            {overdue && <Icon name="alert-triangle" />} {formatDate(r.next_review_due_at)}
          </span>
        );
      },
    },
  ];

  const total = dashboard?.risks.length ?? 0;
  const accepted = dashboard?.by_state.ACCEPTED ?? 0;

  return (
    <>
      <QmsListPage<RiskRecord>
        title="Risk register"
        subtitle="Hazards, assessments, controls and periodic review across product, process and system risk."
        path="/qms/v1/risks"
        columns={columns}
        states={RISK_STATES}
        emptyIcon="gauge"
        emptyMessage="No risks recorded for this site."
        rowHref={(r) => `/risks/${r.id}`}
        reloadToken={reloadToken}
        action={
          canInvestigateQms(me) ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> Raise risk
            </Button>
          ) : undefined
        }
      >
        {dashboard && (
          <KpiRow>
            <KpiTile label="Total risks" icon="gauge" value={total} />
            <KpiTile
              label="Accepted"
              icon="check-circle"
              value={accepted}
              delta={total > 0 ? `${Math.round((accepted / total) * 100)}% of register` : undefined}
              tone="ok"
            />
            <KpiTile
              label="Review overdue"
              icon="alert-triangle"
              value={dashboard.overdue_count}
              delta={dashboard.overdue_count > 0 ? "Accepted risks past review date" : "All reviews current"}
              tone={dashboard.overdue_count > 0 ? "critical" : "ok"}
            />
            <KpiTile
              label="Risk types"
              icon="layers"
              value={Object.keys(dashboard.by_type).length}
              delta={Object.entries(dashboard.by_type)
                .map(([type, count]) => `${type} ${count}`)
                .join(" · ")}
            />
          </KpiRow>
        )}
      </QmsListPage>
      {createOpen && (
        <RaiseRiskModal
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

function RaiseRiskModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { siteId } = useSiteId();
  const { me } = useMe();
  const [riskNumber, setRiskNumber] = useState("");
  const [riskType, setRiskType] = useState(RISK_TYPES[0]);
  const [hazard, setHazard] = useState("");
  const [effect, setEffect] = useState("");
  const [methodologyId, setMethodologyId] = useState("");
  const [context, setContext] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId || !me) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/qms/v1/risks", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        risk_number: riskNumber,
        risk_type: riskType,
        hazard_problem: hazard,
        potential_effect: effect,
        owner_subject_id: me.user_id,
        methodology_id: methodologyId || null,
        context: context ? { description: context } : null,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to raise risk");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Raise a risk" large>
      <form onSubmit={submit}>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Risk number" required>
            <Input value={riskNumber} onChange={(e) => setRiskNumber(e.target.value)} placeholder="RSK-0001" required autoFocus />
          </Field>
          <Field label="Risk type" required>
            <Select value={riskType} onChange={(e) => setRiskType(e.target.value)}>
              {RISK_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <Field label="Hazard or problem" required hint="The condition that could cause harm.">
          <textarea className="input" rows={2} value={hazard} onChange={(e) => setHazard(e.target.value)} required />
        </Field>
        <Field label="Potential effect" required hint="What happens if the hazard is realised.">
          <textarea className="input" rows={2} value={effect} onChange={(e) => setEffect(e.target.value)} required />
        </Field>
        <Field
          label="Methodology ID"
          hint="A released rule of type risk_methodology, authored on the Rules page. Required before the first assessment."
        >
          <Input value={methodologyId} onChange={(e) => setMethodologyId(e.target.value)} />
        </Field>
        <Field label="Context" hint="Scope, product or process this risk applies to.">
          <textarea className="input" rows={2} value={context} onChange={(e) => setContext(e.target.value)} />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !riskNumber.trim() || !siteId}>
            {busy ? "Raising…" : "Raise risk"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
