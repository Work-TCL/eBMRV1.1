"use client";

import { use, useState } from "react";
import {
  api,
  canApproveQms,
  canInvestigateQms,
  formatDate,
  formatDateTime,
  newIdempotencyKey,
  type Nonconformance,
} from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
import { QmsDetailShell, useCommand } from "@/components/qms/QmsDetailShell";
import { Fact, IdFact } from "@/components/ui/FactGrid";
import { Tabs } from "@/components/ui/Tabs";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { HistoryPanel, JsonPanel } from "@/components/ui/JsonPanel";
import { StatePill, BoolPill, SeverityPill } from "@/components/ui/StatePill";

interface Disposition {
  id: string;
  affected_scope: unknown[];
  quantity: number | null;
  serials: string[] | null;
  disposition_type: string;
  justification: string;
  rework_route: Record<string, unknown> | null;
  follow_up_test_requirements: Record<string, unknown> | null;
  use_as_is_authorized_by: string | null;
  signature_id: string | null;
  created_at: string;
}

interface NcrDetail extends Nonconformance {
  scope_records: unknown[];
  requirement_ref: Record<string, unknown> | null;
  segregation: Record<string, unknown> | null;
  evaluation: Record<string, unknown> | null;
  supplier_link: Record<string, unknown> | null;
  capa_rationale: string | null;
  verification: Record<string, unknown> | null;
  closure_history: unknown[];
  dispositions: Disposition[];
}

type Transition = "segregate" | "evaluate" | "disposition" | "verify" | "close";

const ALLOWED_FROM: Record<string, Transition[]> = {
  OPEN: ["segregate"],
  SEGREGATED: ["segregate", "evaluate"],
  EVALUATION: ["evaluate", "disposition"],
  // A disposition moves the record into its disposition state; rework-like ones then need verification.
  REWORK: ["verify"],
  REPAIR: ["verify"],
  RETURN: ["close"],
  SCRAP: ["close"],
  USE_AS_IS: ["close"],
  VERIFICATION: ["verify", "close"],
  CLOSED: [],
};

// SG-138: no Document 106 policy rows for nonconformance_record disposition/verify/close.
const SIGNATURE_GATED: Transition[] = ["disposition", "verify", "close"];

const LABEL: Record<Transition, string> = {
  segregate: "Record segregation",
  evaluate: "Evaluate",
  disposition: "Disposition",
  verify: "Verify",
  close: "Close",
};

// app/modules/qms/ncr_models.py NCR_DISPOSITION_TYPES.
const DISPOSITION_TYPES = ["REWORK", "REPAIR", "RETURN", "SCRAP", "USE_AS_IS"];

export default function NcrDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const [pending, setPending] = useState<Transition | null>(null);
  const { data, loading, error, reload } = useApiResource<NcrDetail>(`/qms/v1/nonconformances/${id}`);

  const allowed = data ? (ALLOWED_FROM[data.state] ?? []) : [];
  const canDo = (t: Transition) =>
    allowed.includes(t) && (SIGNATURE_GATED.includes(t) ? canApproveQms(me) : canInvestigateQms(me));

  return (
    <QmsDetailShell
      recordNumber={data?.ncr_number ?? ""}
      state={data?.state ?? ""}
      subtitle={data ? `${data.defect_code} · ${data.scope_type} scope` : undefined}
      backHref="/nonconformances"
      backLabel="Nonconformances"
      loading={loading}
      error={error}
      actions={(Object.keys(LABEL) as Transition[]).filter(canDo).map((t) => (
        <Button key={t} variant={t === "close" ? "primary" : "secondary"} onClick={() => setPending(t)}>
          {SIGNATURE_GATED.includes(t) && <Icon name="pen" />} {LABEL[t]}
        </Button>
      ))}
      facts={
        data && (
          <>
            <Fact label="Severity">
              <SeverityPill severity={data.severity} />
            </Fact>
            <Fact label="Defect code">{data.defect_code}</Fact>
            <Fact label="Release blocker">
              {data.release_blocker_active ? (
                <StatePill state="blocked" icon="lock">
                  Active
                </StatePill>
              ) : (
                <StatePill state="na" icon="slash-circle">
                  Cleared
                </StatePill>
              )}
            </Fact>
            <Fact label="CAPA required">
              <BoolPill value={data.capa_required} trueLabel="Required" falseLabel="Not required" />
            </Fact>
            <Fact label="Dispositions">{data.dispositions.length}</Fact>
            <Fact label="Raised">{formatDateTime(data.created_at)}</Fact>
            <Fact label="Closed">{data.closed_at ? formatDateTime(data.closed_at) : "—"}</Fact>
            <Fact label="Record version">{data.version}</Fact>
            <IdFact label="Owner" value={data.owner_subject_id} />
            <IdFact label="Source record" value={data.source_id} />
            <IdFact label="Quality event" value={data.quality_event_id} />
          </>
        )
      }
    >
      {data && (
        <>
          {data.release_blocker_active && (
            <Banner tone="critical" title="Release blocker active" icon="lock">
              Affected product cannot be released while this nonconformance is open.
            </Banner>
          )}

          <Tabs
            tabs={[
              {
                id: "evaluation",
                label: "Evaluation",
                content: (
                  <Card pad>
                    <JsonPanel title="Requirement reference" value={data.requirement_ref} />
                    <JsonPanel title="Affected records" value={data.scope_records} />
                    <JsonPanel title="Segregation" value={data.segregation} />
                    <JsonPanel title="Evaluation" value={data.evaluation} />
                    <JsonPanel title="Supplier link" value={data.supplier_link} />
                  </Card>
                ),
              },
              {
                id: "dispositions",
                label: "Dispositions",
                badge: data.dispositions.length || undefined,
                content: <DispositionsTab dispositions={data.dispositions} />,
              },
              {
                id: "verification",
                label: "Verification",
                content: (
                  <Card pad>
                    <JsonPanel title="Verification" value={data.verification} />
                    <JsonPanel title="CAPA rationale" value={data.capa_rationale} />
                    <HistoryPanel title="Closures" entries={data.closure_history} />
                    {!data.verification && data.closure_history.length === 0 && (
                      <EmptyState icon="help-circle">Nothing verified or closed yet.</EmptyState>
                    )}
                  </Card>
                ),
              },
            ]}
          />

          {pending && (
            <TransitionModal
              ncr={data}
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

function DispositionsTab({ dispositions }: { dispositions: Disposition[] }) {
  if (dispositions.length === 0) {
    return <EmptyState icon="help-circle">No disposition recorded yet.</EmptyState>;
  }
  return (
    <div>
      {dispositions.map((d) => (
        <Card key={d.id} pad className="mb-3">
          <div className="flex justify-between items-center mb-2">
            <span className="font-semibold">{d.disposition_type}</span>
            <span className="fs-2 text-muted">{formatDate(d.created_at)}</span>
          </div>
          <p className="fs-2 mb-3">{d.justification}</p>
          {d.quantity !== null && (
            <p className="fs-2">
              <span className="text-muted">Quantity: </span>
              <span className="tabular">{d.quantity}</span>
            </p>
          )}
          <JsonPanel title="Affected scope" value={d.affected_scope} />
          <JsonPanel title="Serials" value={d.serials} />
          <JsonPanel title="Rework route" value={d.rework_route} />
          <JsonPanel title="Follow-up tests" value={d.follow_up_test_requirements} />
          {d.disposition_type === "USE_AS_IS" && (
            <p className="fs-2 text-muted">
              Use-as-is authorised by: <span className="tabular">{d.use_as_is_authorized_by ?? "—"}</span>
            </p>
          )}
        </Card>
      ))}
    </div>
  );
}

function TransitionModal({
  ncr,
  transition,
  onClose,
  onDone,
}: {
  ncr: NcrDetail;
  transition: Transition;
  onClose: () => void;
  onDone: () => void;
}) {
  const { me } = useMe();
  const { busy, error, run } = useCommand(onDone);

  const [location, setLocation] = useState("");
  const [evaluation, setEvaluation] = useState("");
  const [dispositionType, setDispositionType] = useState(DISPOSITION_TYPES[0]);
  const [justification, setJustification] = useState("");
  const [quantity, setQuantity] = useState("");
  const [capaRequired, setCapaRequired] = useState(false);
  const [capaRationale, setCapaRationale] = useState("");
  const [reinspection, setReinspection] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [reason, setReason] = useState("");

  const base = { idempotency_key: newIdempotencyKey(), ncr_id: ncr.id, expected_version: ncr.version };
  const path = `/qms/v1/nonconformances/${ncr.id}`;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() => {
      switch (transition) {
        case "segregate":
          return api.post(`${path}/segregate`, {
            ...base,
            locations: [{ location, segregated_at: new Date().toISOString() }],
            reason: reason || null,
          });
        case "evaluate":
          return api.post(`${path}/evaluate`, {
            ...base,
            evaluation: { conclusion: evaluation },
            reason: reason || null,
          });
        case "disposition":
          return api.post(`${path}/disposition`, {
            ...base,
            disposition_type: dispositionType,
            affected_scope: ncr.scope_records,
            justification,
            quantity: quantity ? Number(quantity) : null,
            capa_required: capaRequired,
            capa_rationale: capaRationale || null,
            use_as_is_authorized_by: dispositionType === "USE_AS_IS" ? (me?.user_id ?? null) : null,
          });
        case "verify":
          return api.post(`${path}/verify`, {
            ...base,
            reinspection_evidence: { result: reinspection },
            reason: reason || null,
          });
        case "close":
          return api.post(`${path}/close`, { ...base, conclusion });
      }
    });
  }

  return (
    <Modal open onClose={onClose} title={`${LABEL[transition]} - ${ncr.ncr_number}`}>
      <form onSubmit={submit}>
        {SIGNATURE_GATED.includes(transition) && (
          <Banner tone="warn" title="This transition requires an electronic signature">
            This action needs a signature policy that hasn&apos;t been configured for this deployment yet, so it will be correctly refused rather than proceeding without one.
          </Banner>
        )}

        {transition === "segregate" && (
          <Field label="Segregation location" required hint="Where the nonconforming material is being held.">
            <Input value={location} onChange={(e) => setLocation(e.target.value)} required autoFocus />
          </Field>
        )}

        {transition === "evaluate" && (
          <Field label="Evaluation conclusion" required>
            <textarea className="input" rows={3} value={evaluation} onChange={(e) => setEvaluation(e.target.value)} required />
          </Field>
        )}

        {transition === "disposition" && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Disposition type" required>
                <Select value={dispositionType} onChange={(e) => setDispositionType(e.target.value)}>
                  {DISPOSITION_TYPES.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Quantity">
                <Input type="number" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
              </Field>
            </div>
            <Field label="Justification" required>
              <textarea className="input" rows={3} value={justification} onChange={(e) => setJustification(e.target.value)} required />
            </Field>
            {dispositionType === "USE_AS_IS" && (
              <Banner tone="warn" title="Use-as-is releases nonconforming product">
                You are recorded as the authorising party. This decision needs a justification an inspector
                would accept on its own terms.
              </Banner>
            )}
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input type="checkbox" checked={capaRequired} onChange={(e) => setCapaRequired(e.target.checked)} />
              CAPA required
            </label>
            {capaRequired && (
              <Field label="CAPA rationale" required>
                <textarea className="input" rows={2} value={capaRationale} onChange={(e) => setCapaRationale(e.target.value)} required />
              </Field>
            )}
          </>
        )}

        {transition === "verify" && (
          <Field label="Reinspection result" required hint="Evidence that the rework or repair achieved conformance.">
            <textarea className="input" rows={3} value={reinspection} onChange={(e) => setReinspection(e.target.value)} required />
          </Field>
        )}

        {transition === "close" && (
          <Field label="Conclusion" required>
            <textarea className="input" rows={3} value={conclusion} onChange={(e) => setConclusion(e.target.value)} required />
          </Field>
        )}

        {(transition === "segregate" || transition === "evaluate" || transition === "verify") && (
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
