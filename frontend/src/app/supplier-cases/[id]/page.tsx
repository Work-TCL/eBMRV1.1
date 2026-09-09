"use client";

import { use, useState } from "react";
import {
  api,
  canApproveQms,
  canInvestigateQms,
  formatDate,
  formatDateTime,
  isOverdue,
  newIdempotencyKey,
  type Scar,
  type SupplierCase,
} from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
import { QmsDetailShell, useCommand } from "@/components/qms/QmsDetailShell";
import { Fact, IdFact } from "@/components/ui/FactGrid";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { BoolPill, SeverityPill, WorkflowStatePill } from "@/components/ui/StatePill";

interface CaseDetail extends SupplierCase {
  material_spec_ref: Record<string, unknown> | null;
  containment: Record<string, unknown> | null;
  asl_impact: Record<string, unknown> | null;
  alternate_source_ref: Record<string, unknown> | null;
  scars: Scar[];
}

interface ScarDetail extends Scar {
  evidence: Record<string, unknown> | null;
  acknowledgment: Record<string, unknown> | null;
  supplier_root_cause: Record<string, unknown> | null;
  supplier_actions: Record<string, unknown> | null;
  internal_review: Record<string, unknown> | null;
  review_history: unknown[];
  effectiveness: Record<string, unknown> | null;
  effectiveness_history: unknown[];
  requalification_rationale: string | null;
  capa_rationale: string | null;
  related_case_ids: string[] | null;
  closure_history: unknown[];
}

type Action = "issue_scar" | "response" | "review" | "effectiveness" | "close";

// SG-138: no Document 106 policy rows for scar_record review/close.
const SIGNATURE_GATED: Action[] = ["review", "close"];
const SOURCE_STATUS_DECISIONS = ["no_change", "requalify", "suspend", "reinstate"];

export default function SupplierCaseDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const [pending, setPending] = useState<{ action: Action; scar?: Scar } | null>(null);
  const { data, loading, error, reload } = useApiResource<CaseDetail>(`/qms/v1/supplier-cases/${id}`);

  const canIssue = data && data.scars.length === 0 && canInvestigateQms(me);

  return (
    <QmsDetailShell
      recordNumber={data?.case_number ?? ""}
      state={data?.state ?? ""}
      subtitle={data ? `${data.defect_code} · ${data.affected_lots.length} affected lot(s)` : undefined}
      backHref="/supplier-cases"
      backLabel="Supplier cases"
      loading={loading}
      error={error}
      actions={
        canIssue ? (
          <Button variant="primary" onClick={() => setPending({ action: "issue_scar" })}>
            <Icon name="plus" /> Issue SCAR
          </Button>
        ) : undefined
      }
      facts={
        data && (
          <>
            <Fact label="Severity">
              <SeverityPill severity={data.severity} />
            </Fact>
            <Fact label="Defect code">{data.defect_code}</Fact>
            <Fact label="Affected lots">{data.affected_lots.length}</Fact>
            <Fact label="SCARs issued">{data.scars.length}</Fact>
            <Fact label="Opened">{formatDateTime(data.created_at)}</Fact>
            <Fact label="Closed">{data.closed_at ? formatDateTime(data.closed_at) : "—"}</Fact>
            <Fact label="Record version">{data.version}</Fact>
            <IdFact label="Supplier" value={data.supplier_id} />
            <IdFact label="Supplier site" value={data.supplier_site_id} />
            <IdFact label="Material" value={data.material_id} />
            <IdFact label="Internal owner" value={data.internal_owner_subject_id} />
          </>
        )
      }
    >
      {data && (
        <>
          <Card pad className="mb-4">
            <JsonPanel title="Affected lots" value={data.affected_lots} />
            <JsonPanel title="Containment" value={data.containment} />
            <JsonPanel title="Material specification" value={data.material_spec_ref} />
            <JsonPanel title="Approved supplier list impact" value={data.asl_impact} />
            <JsonPanel title="Alternate source" value={data.alternate_source_ref} />
          </Card>

          {data.scars.length === 0 ? (
            <EmptyState icon="building">
              No SCAR issued against this case yet.
            </EmptyState>
          ) : (
            data.scars.map((scar) => (
              <ScarCard
                key={scar.id}
                scar={scar}
                onAction={(action) => setPending({ action, scar })}
                canWork={canInvestigateQms(me)}
                canApprove={canApproveQms(me)}
              />
            ))
          )}

          {pending && (
            <ActionModal
              supplierCase={data}
              action={pending.action}
              scar={pending.scar}
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

function ScarCard({
  scar,
  onAction,
  canWork,
  canApprove,
}: {
  scar: Scar;
  onAction: (action: Action) => void;
  canWork: boolean;
  canApprove: boolean;
}) {
  const detail = useApiResource<ScarDetail>(`/qms/v1/scars/${scar.id}`);
  const d = detail.data;
  const overdue = isOverdue(scar.due_date) && scar.state !== "CLOSED";

  return (
    <Card pad className="mb-4">
      <div className="flex justify-between items-center mb-3">
        <span className="font-semibold">
          {scar.scar_number} <WorkflowStatePill state={scar.state} />
        </span>
        <div className="flex gap-2">
          {scar.state === "SCAR_ISSUED" && canWork && (
            <Button size="sm" variant="secondary" onClick={() => onAction("response")}>
              Record supplier response
            </Button>
          )}
          {scar.state === "SUPPLIER_RESPONSE" && canApprove && (
            <Button size="sm" variant="secondary" onClick={() => onAction("review")}>
              <Icon name="pen" /> Review
            </Button>
          )}
          {scar.state === "IMPLEMENTATION" && canWork && (
            <Button size="sm" variant="secondary" onClick={() => onAction("effectiveness")}>
              Effectiveness
            </Button>
          )}
          {scar.state === "EFFECTIVENESS" && canApprove && (
            <Button size="sm" variant="primary" onClick={() => onAction("close")}>
              <Icon name="pen" /> Close
            </Button>
          )}
        </div>
      </div>

      <div className="fact-grid mb-3">
        <div className="fact">
          <span className="fact-k">Issued</span>
          <span className="fact-v">{formatDate(scar.issued_at)}</span>
        </div>
        <div className="fact">
          <span className="fact-k">Response due</span>
          <span className={overdue ? "fact-v error-text" : "fact-v"}>{formatDate(scar.due_date)}</span>
        </div>
        <div className="fact">
          <span className="fact-k">Repeat issue</span>
          <span className="fact-v">
            <BoolPill value={scar.is_repeat_issue} trueLabel="Repeat" falseLabel="First" />
          </span>
        </div>
        <div className="fact">
          <span className="fact-k">Requalification</span>
          <span className="fact-v">
            <BoolPill value={scar.requalification_required} trueLabel="Required" falseLabel="Not required" />
          </span>
        </div>
      </div>

      <p className="fs-3 mb-3">{scar.problem_statement}</p>

      {overdue && (
        <Banner tone="warn" title="Supplier response overdue">
          The SCAR response due date has passed.
        </Banner>
      )}

      {d && (
        <>
          <JsonPanel title="Evidence sent to supplier" value={d.evidence} />
          <JsonPanel title="Supplier acknowledgment" value={d.acknowledgment} />
          <JsonPanel title="Supplier root cause" value={d.supplier_root_cause} />
          <JsonPanel title="Supplier actions" value={d.supplier_actions} />
          <JsonPanel title="Internal review" value={d.internal_review} />
          <JsonPanel title="Effectiveness" value={d.effectiveness} />
          <JsonPanel title="Source status decision" value={d.source_status_decision} />
        </>
      )}
    </Card>
  );
}

function ActionModal({
  supplierCase,
  action,
  scar,
  onClose,
  onDone,
}: {
  supplierCase: CaseDetail;
  action: Action;
  scar?: Scar;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [scarNumber, setScarNumber] = useState("");
  const [problemStatement, setProblemStatement] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [rootCause, setRootCause] = useState("");
  const [supplierActions, setSupplierActions] = useState("");
  const [decision, setDecision] = useState("accepted");
  const [rationale, setRationale] = useState("");
  const [result, setResult] = useState("pass");
  const [evidence, setEvidence] = useState("");
  const [sourceStatus, setSourceStatus] = useState(SOURCE_STATUS_DECISIONS[0]);
  const [conclusion, setConclusion] = useState("");
  const [requalification, setRequalification] = useState(false);

  const LABEL: Record<Action, string> = {
    issue_scar: "Issue SCAR",
    response: "Record supplier response",
    review: "Review SCAR response",
    effectiveness: "Record effectiveness",
    close: "Close SCAR",
  };

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() => {
      if (action === "issue_scar") {
        return api.post(`/qms/v1/supplier-cases/${supplierCase.id}/scar`, {
          idempotency_key: newIdempotencyKey(),
          case_id: supplierCase.id,
          case_expected_version: supplierCase.version,
          scar_number: scarNumber,
          problem_statement: problemStatement,
          due_date: dueDate ? new Date(dueDate).toISOString() : null,
        });
      }
      if (!scar) return Promise.reject(new Error("No SCAR selected"));
      const base = { idempotency_key: newIdempotencyKey(), scar_id: scar.id, expected_version: scar.version };
      switch (action) {
        case "response":
          return api.post(`/qms/v1/scars/${scar.id}/response`, {
            ...base,
            supplier_root_cause: { description: rootCause },
            supplier_actions: { description: supplierActions },
          });
        case "review":
          return api.post(`/qms/v1/scars/${scar.id}/review`, { ...base, decision, rationale });
        case "effectiveness":
          return api.post(`/qms/v1/scars/${scar.id}/effectiveness`, {
            ...base,
            result,
            evidence: { description: evidence },
          });
        case "close":
          return api.post(`/qms/v1/scars/${scar.id}/close`, {
            ...base,
            source_status_decision: sourceStatus,
            conclusion,
            requalification_required: requalification,
            requalification_rationale: requalification ? rationale : null,
          });
      }
    });
  }

  return (
    <Modal open onClose={onClose} title={LABEL[action]}>
      <form onSubmit={submit}>
        {SIGNATURE_GATED.includes(action) && (
          <Banner tone="warn" title="This transition requires an electronic signature">
            This action needs a signature policy that hasn&apos;t been configured for this deployment yet, so it will be correctly refused rather than proceeding without one.
          </Banner>
        )}

        {action === "issue_scar" && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="SCAR number" required>
                <Input value={scarNumber} onChange={(e) => setScarNumber(e.target.value)} placeholder="SCAR-0001" required autoFocus />
              </Field>
              <Field label="Response due">
                <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              </Field>
            </div>
            <Field label="Problem statement" required hint="What the supplier is being asked to explain and correct.">
              <textarea
                className="input"
                rows={4}
                value={problemStatement}
                onChange={(e) => setProblemStatement(e.target.value)}
                required
              />
            </Field>
          </>
        )}

        {action === "response" && (
          <>
            <Field label="Supplier root cause" required>
              <textarea className="input" rows={3} value={rootCause} onChange={(e) => setRootCause(e.target.value)} required />
            </Field>
            <Field label="Supplier corrective actions" required>
              <textarea
                className="input"
                rows={3}
                value={supplierActions}
                onChange={(e) => setSupplierActions(e.target.value)}
                required
              />
            </Field>
          </>
        )}

        {action === "review" && (
          <>
            <Field label="Decision" required>
              <Select value={decision} onChange={(e) => setDecision(e.target.value)}>
                <option value="accepted">accepted</option>
                <option value="rejected">rejected — supplier must respond again</option>
              </Select>
            </Field>
            <Field label="Rationale" required>
              <textarea className="input" rows={3} value={rationale} onChange={(e) => setRationale(e.target.value)} required />
            </Field>
          </>
        )}

        {action === "effectiveness" && (
          <>
            <Field label="Result" required>
              <Select value={result} onChange={(e) => setResult(e.target.value)}>
                <option value="pass">pass</option>
                <option value="fail">fail</option>
              </Select>
            </Field>
            <Field label="Evidence" required>
              <textarea className="input" rows={3} value={evidence} onChange={(e) => setEvidence(e.target.value)} required />
            </Field>
          </>
        )}

        {action === "close" && (
          <>
            <Field label="Source status decision" required hint="What happens to this supplier's approved status.">
              <Select value={sourceStatus} onChange={(e) => setSourceStatus(e.target.value)}>
                {SOURCE_STATUS_DECISIONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Conclusion" required>
              <textarea className="input" rows={3} value={conclusion} onChange={(e) => setConclusion(e.target.value)} required />
            </Field>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input type="checkbox" checked={requalification} onChange={(e) => setRequalification(e.target.checked)} />
              Requalification required
            </label>
            {requalification && (
              <Field label="Requalification rationale" required>
                <textarea className="input" rows={2} value={rationale} onChange={(e) => setRationale(e.target.value)} required />
              </Field>
            )}
          </>
        )}

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Saving…" : LABEL[action]}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
