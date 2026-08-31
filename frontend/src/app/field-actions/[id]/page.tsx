"use client";

import { use, useState } from "react";
import {
  api,
  canApproveQms,
  canInvestigateQms,
  formatDateTime,
  newIdempotencyKey,
  type FieldAction,
} from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
import { QmsDetailShell, useCommand } from "@/components/qms/QmsDetailShell";
import { Fact, IdFact } from "@/components/ui/FactGrid";
import { Tabs } from "@/components/ui/Tabs";
import { Card } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { KpiRow, KpiTile } from "@/components/ui/KpiTile";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { StatePill, BoolPill } from "@/components/ui/StatePill";

interface ScopeItem {
  id: string;
  product_ref: string | null;
  lot_batch_serial_refs: Record<string, unknown> | null;
  distribution_ref: Record<string, unknown> | null;
  distribution_hold: boolean;
  status: string;
  action_required: string | null;
  action_completed: boolean;
}

interface Communication {
  id: string;
  package_version: number;
  recipient: string;
  channel: string | null;
  message: string;
  sent_at: string | null;
  delivery_status: string;
  ack_status: string | null;
}

interface Reconciliation {
  affected_count: number;
  contacted_count: number;
  returned_count: number;
  corrected_count: number;
  destroyed_count: number;
  unavailable_count: number;
  outstanding_count: number;
  created_at: string;
}

interface FieldActionDetail extends FieldAction {
  trigger_ref: Record<string, unknown> | null;
  reportability_assessment: Record<string, unknown> | null;
  effectiveness_check: Record<string, unknown> | null;
  scope_items: ScopeItem[];
  communications: Communication[];
  reconciliation: Reconciliation | null;
}

type Transition = "scope" | "reportability" | "approve" | "communications" | "reconcile" | "effectiveness" | "close";

const ALLOWED_FROM: Record<string, Transition[]> = {
  ASSESSMENT: ["scope"],
  SCOPE_DEFINITION: ["scope", "reportability"],
  REGULATORY_DECISION: ["reportability", "approve"],
  APPROVAL: ["communications"],
  EXECUTION_NOTIFICATION: ["communications", "reconcile"],
  RECONCILIATION: ["reconcile", "effectiveness"],
  EFFECTIVENESS: ["effectiveness", "close"],
  CLOSED: [],
};

// SG-138: no Document 106 policy rows for field_action reportability/approve/close.
const SIGNATURE_GATED: Transition[] = ["reportability", "approve", "close"];

const LABEL: Record<Transition, string> = {
  scope: "Define scope",
  reportability: "Reportability",
  approve: "Approve",
  communications: "Record notification",
  reconcile: "Reconcile",
  effectiveness: "Effectiveness",
  close: "Close",
};

const REGIMES = ["FDA_21CFR806", "FDA_RECALL", "EU_MDR_FSCA", "HEALTH_CANADA", "NONE"];

export default function FieldActionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const [pending, setPending] = useState<Transition | null>(null);
  const { data, loading, error, reload } = useApiResource<FieldActionDetail>(`/qms/v1/field-actions/${id}`);

  const allowed = data ? (ALLOWED_FROM[data.state] ?? []) : [];
  const canDo = (t: Transition) =>
    allowed.includes(t) && (SIGNATURE_GATED.includes(t) ? canApproveQms(me) : canInvestigateQms(me));

  const rec = data?.reconciliation;

  return (
    <QmsDetailShell
      recordNumber={data?.action_number ?? ""}
      state={data?.state ?? ""}
      subtitle={data ? `${data.action_type} · revision ${data.revision}` : undefined}
      backHref="/field-actions"
      backLabel="Field actions"
      loading={loading}
      error={error}
      actions={(Object.keys(LABEL) as Transition[]).filter(canDo).map((t) => (
        <Button key={t} variant={t === "approve" ? "primary" : "secondary"} onClick={() => setPending(t)}>
          {SIGNATURE_GATED.includes(t) && <Icon name="pen" />} {LABEL[t]}
        </Button>
      ))}
      facts={
        data && (
          <>
            <Fact label="Action type">
              <StatePill state={data.action_type === "recall" ? "failed" : "conflict"} icon="flag">
                {data.action_type}
              </StatePill>
            </Fact>
            <Fact label="Revision">{data.revision}</Fact>
            <Fact label="Scope items">{data.scope_items.length}</Fact>
            <Fact label="Notifications">{data.communications.length}</Fact>
            <Fact label="CAPA required">
              <BoolPill value={data.capa_required} trueLabel="Required" falseLabel="Not required" />
            </Fact>
            <Fact label="Raised">{formatDateTime(data.created_at)}</Fact>
            <Fact label="Closed">{data.closed_at ? formatDateTime(data.closed_at) : "—"}</Fact>
            <Fact label="Record version">{data.version}</Fact>
            <IdFact label="Risk assessment" value={data.risk_assessment_ref} />
            <IdFact label="Quality event" value={data.quality_event_id} />
          </>
        )
      }
    >
      {data && (
        <>
          {rec && rec.outstanding_count > 0 && (
            <Banner tone="warn" title={`${rec.outstanding_count} unit(s) outstanding`}>
              Reconciliation is incomplete — product remains unaccounted for in the field.
            </Banner>
          )}

          {rec && (
            <KpiRow>
              <KpiTile label="Affected" icon="package" value={rec.affected_count} />
              <KpiTile label="Contacted" icon="bell" value={rec.contacted_count} />
              <KpiTile label="Returned" icon="arrow-left" value={rec.returned_count} />
              <KpiTile label="Corrected" icon="check-circle" value={rec.corrected_count} tone="ok" />
              <KpiTile label="Destroyed" icon="x" value={rec.destroyed_count} />
              <KpiTile
                label="Outstanding"
                icon="alert-triangle"
                value={rec.outstanding_count}
                tone={rec.outstanding_count > 0 ? "critical" : "ok"}
              />
            </KpiRow>
          )}

          <Tabs
            tabs={[
              {
                id: "scope",
                label: "Scope",
                badge: data.scope_items.length || undefined,
                content: <ScopeTab items={data.scope_items} />,
              },
              {
                id: "regulatory",
                label: "Regulatory",
                content: (
                  <Card pad>
                    <JsonPanel title="Trigger" value={data.trigger_ref} />
                    <JsonPanel title="Reportability assessment" value={data.reportability_assessment} />
                    <JsonPanel title="CAPA rationale" value={data.capa_rationale} />
                    {!data.reportability_assessment && (
                      <EmptyState icon="shield-check">No reportability assessment recorded yet.</EmptyState>
                    )}
                  </Card>
                ),
              },
              {
                id: "notifications",
                label: "Notifications",
                badge: data.communications.length || undefined,
                content: <CommunicationsTab communications={data.communications} />,
              },
              {
                id: "effectiveness",
                label: "Effectiveness",
                content: (
                  <Card pad>
                    <JsonPanel title="Effectiveness check" value={data.effectiveness_check} />
                    {!data.effectiveness_check && (
                      <EmptyState icon="gauge">No effectiveness check recorded yet.</EmptyState>
                    )}
                  </Card>
                ),
              },
            ]}
          />

          {pending && (
            <TransitionModal
              fieldAction={data}
              transition={pending}
              onClose={() => setPending(null)}
              onDone={() => {
                setPending(null);
                reload();
              }}
            />
          )}
        </>
      )}
    </QmsDetailShell>
  );
}

function ScopeTab({ items }: { items: ScopeItem[] }) {
  if (items.length === 0) {
    return <EmptyState icon="layers">No scope items defined — the affected population is not yet bounded.</EmptyState>;
  }
  return (
    <Card>
      <Table>
        <thead>
          <tr>
            <th>Lot / serial</th>
            <th>Distribution</th>
            <th>Hold</th>
            <th>Status</th>
            <th>Action required</th>
            <th>Complete</th>
          </tr>
        </thead>
        <tbody>
          {items.map((i) => (
            <tr key={i.id}>
              <td className="fs-2">
                {i.lot_batch_serial_refs ? JSON.stringify(i.lot_batch_serial_refs) : "—"}
              </td>
              <td className="fs-2">{i.distribution_ref ? JSON.stringify(i.distribution_ref) : "—"}</td>
              <td>
                {i.distribution_hold ? (
                  <StatePill state="blocked" icon="lock">
                    Held
                  </StatePill>
                ) : (
                  <span className="text-muted">—</span>
                )}
              </td>
              <td className="fs-2">{i.status}</td>
              <td className="fs-2">{i.action_required ?? "—"}</td>
              <td>
                {i.action_completed ? (
                  <StatePill state="accepted" icon="check-circle">
                    Done
                  </StatePill>
                ) : (
                  <StatePill state="stale" icon="clock">
                    Open
                  </StatePill>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}

function CommunicationsTab({ communications }: { communications: Communication[] }) {
  if (communications.length === 0) {
    return <EmptyState icon="bell">No customer notifications recorded.</EmptyState>;
  }
  return (
    <Card>
      <Table>
        <thead>
          <tr>
            <th>Sent</th>
            <th>Recipient</th>
            <th>Channel</th>
            <th>Delivery</th>
            <th>Acknowledged</th>
            <th>Package</th>
          </tr>
        </thead>
        <tbody>
          {communications.map((c) => (
            <tr key={c.id}>
              <td className="tabular fs-2">{c.sent_at ? formatDateTime(c.sent_at) : "Not sent"}</td>
              <td>{c.recipient}</td>
              <td className="fs-2">{c.channel ?? "—"}</td>
              <td className="fs-2">{c.delivery_status}</td>
              <td className="fs-2">{c.ack_status ?? "—"}</td>
              <td className="tabular fs-2">v{c.package_version}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}

function TransitionModal({
  fieldAction,
  transition,
  onClose,
  onDone,
}: {
  fieldAction: FieldActionDetail;
  transition: Transition;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);

  const [lotRef, setLotRef] = useState("");
  const [actionRequired, setActionRequired] = useState("return");
  const [distributionHold, setDistributionHold] = useState(true);
  const [regimes, setRegimes] = useState<string[]>([]);
  const [decision, setDecision] = useState("reportable");
  const [rationale, setRationale] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [recipient, setRecipient] = useState("");
  const [message, setMessage] = useState("");
  const [channel, setChannel] = useState("email");
  const [counts, setCounts] = useState({
    affected_count: String(fieldAction.reconciliation?.affected_count ?? fieldAction.scope_items.length),
    contacted_count: "0",
    returned_count: "0",
    corrected_count: "0",
    destroyed_count: "0",
    unavailable_count: "0",
    outstanding_count: "0",
  });
  const [result, setResult] = useState("pass");
  const [reason, setReason] = useState("");

  const base = {
    idempotency_key: newIdempotencyKey(),
    field_action_id: fieldAction.id,
    expected_version: fieldAction.version,
  };
  const path = `/qms/v1/field-actions/${fieldAction.id}`;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() => {
      switch (transition) {
        case "scope":
          return api.post(`${path}/scope`, {
            ...base,
            items: [
              {
                lot_batch_serial_refs: { reference: lotRef },
                distribution_hold: distributionHold,
                action_required: actionRequired,
              },
            ],
            reason: reason || null,
          });
        case "reportability":
          return api.post(`${path}/reportability`, {
            ...base,
            applicable_regimes: regimes,
            rationale,
            decision,
            due_date: dueDate ? new Date(dueDate).toISOString() : null,
          });
        case "approve":
          return api.post(`${path}/approve`, { ...base, conclusion });
        case "communications":
          return api.post(`${path}/communications`, {
            ...base,
            recipient,
            message,
            channel,
            sent_at: new Date().toISOString(),
            delivery_status: "sent",
          });
        case "reconcile":
          return api.post(`${path}/reconcile`, {
            ...base,
            ...Object.fromEntries(Object.entries(counts).map(([k, v]) => [k, Number(v)])),
          });
        case "effectiveness":
          return api.post(`${path}/effectiveness`, { ...base, result, evidence: { note: conclusion } });
        case "close":
          return api.post(`${path}/close`, { ...base, conclusion });
      }
    });
  }

  return (
    <Modal
      open
      onClose={onClose}
      large={transition === "reconcile" || transition === "reportability"}
      title={`${LABEL[transition]} — ${fieldAction.action_number}`}
    >
      <form onSubmit={submit}>
        {SIGNATURE_GATED.includes(transition) && (
          <Banner tone="warn" title="This transition requires an electronic signature">
            No Document 106 policy row exists yet for this action (SG-138), so the backend fails it closed.
          </Banner>
        )}

        {transition === "scope" && (
          <>
            <Field label="Lot / batch / serial reference" required>
              <Input value={lotRef} onChange={(e) => setLotRef(e.target.value)} required autoFocus />
            </Field>
            <Field label="Action required" required>
              <Select value={actionRequired} onChange={(e) => setActionRequired(e.target.value)}>
                <option value="return">return</option>
                <option value="destroy">destroy</option>
                <option value="correct_in_place">correct in place</option>
                <option value="quarantine">quarantine</option>
              </Select>
            </Field>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input
                type="checkbox"
                checked={distributionHold}
                onChange={(e) => setDistributionHold(e.target.checked)}
              />
              Place a distribution hold on this scope
            </label>
          </>
        )}

        {transition === "reportability" && (
          <>
            <Field label="Applicable regimes" required>
              <div className="flex flex-wrap gap-3">
                {REGIMES.map((r) => (
                  <label key={r} className="flex items-center gap-2 fs-2">
                    <input
                      type="checkbox"
                      checked={regimes.includes(r)}
                      onChange={(e) =>
                        setRegimes((prev) => (e.target.checked ? [...prev, r] : prev.filter((x) => x !== r)))
                      }
                    />
                    {r}
                  </label>
                ))}
              </div>
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Decision" required>
                <Select value={decision} onChange={(e) => setDecision(e.target.value)}>
                  <option value="reportable">reportable</option>
                  <option value="not_reportable">not reportable</option>
                </Select>
              </Field>
              <Field label="Submission due">
                <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              </Field>
            </div>
            <Field label="Rationale" required>
              <textarea className="input" rows={3} value={rationale} onChange={(e) => setRationale(e.target.value)} required />
            </Field>
          </>
        )}

        {transition === "communications" && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Recipient" required>
                <Input value={recipient} onChange={(e) => setRecipient(e.target.value)} required />
              </Field>
              <Field label="Channel">
                <Select value={channel} onChange={(e) => setChannel(e.target.value)}>
                  <option value="email">email</option>
                  <option value="letter">letter</option>
                  <option value="phone">phone</option>
                  <option value="portal">portal</option>
                </Select>
              </Field>
            </div>
            <Field label="Message" required>
              <textarea className="input" rows={4} value={message} onChange={(e) => setMessage(e.target.value)} required />
            </Field>
          </>
        )}

        {transition === "reconcile" && (
          <>
            <p className="hint mb-3">
              Counts of the affected population. Outstanding is what remains unaccounted for in the field.
            </p>
            <div className="grid grid-cols-3 gap-4">
              {(
                [
                  ["affected_count", "Affected"],
                  ["contacted_count", "Contacted"],
                  ["returned_count", "Returned"],
                  ["corrected_count", "Corrected"],
                  ["destroyed_count", "Destroyed"],
                  ["unavailable_count", "Unavailable"],
                  ["outstanding_count", "Outstanding"],
                ] as const
              ).map(([key, label]) => (
                <Field key={key} label={label}>
                  <Input
                    type="number"
                    min={0}
                    value={counts[key]}
                    onChange={(e) => setCounts((prev) => ({ ...prev, [key]: e.target.value }))}
                  />
                </Field>
              ))}
            </div>
          </>
        )}

        {transition === "effectiveness" && (
          <>
            <Field label="Result" required>
              <Select value={result} onChange={(e) => setResult(e.target.value)}>
                <option value="pass">pass</option>
                <option value="fail">fail</option>
              </Select>
            </Field>
            <Field label="Evidence" required>
              <textarea className="input" rows={3} value={conclusion} onChange={(e) => setConclusion(e.target.value)} required />
            </Field>
          </>
        )}

        {(transition === "approve" || transition === "close") && (
          <Field label="Conclusion" required>
            <textarea className="input" rows={3} value={conclusion} onChange={(e) => setConclusion(e.target.value)} required />
          </Field>
        )}

        {transition === "scope" && (
          <Field label="Reason" hint="Optional. Recorded in the audit trail.">
            <Input value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
        )}

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Saving…" : LABEL[transition]}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
