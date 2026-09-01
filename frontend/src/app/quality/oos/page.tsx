"use client";

import { useState } from "react";
import {
  api,
  ApiError,
  canDispositionOos,
  canExtendOos,
  canInvestigateOos,
  newIdempotencyKey,
  type MutationReceipt,
} from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { WorkflowStatePill, SeverityPill } from "@/components/ui/StatePill";
import { WorkflowActionButton } from "@/components/shared/WorkflowActionButton";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";

// GET /quality/oos/v1/{oos_id} — app/modules/qc/router.py::get_oos_record
interface OosRecord {
  id: string;
  oos_number: string;
  state: string;
  severity: string | null;
  hold_status: string | null;
  final_classification: string | null;
  root_cause_code: string | null;
  version: number;
  source_result_id: string;
  activities: { id: string; phase: string; activity_type: string }[];
  retest_plans: { id: string; status: string }[];
  resample_plans: { id: string; status: string }[];
}

export default function OosPage() {
  const { me } = useMe();
  const [oosId, setOosId] = useState("");
  const [oos, setOos] = useState<OosRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sig, setSig] = useState<"extended_investigation" | "disposition" | "close" | null>(null);
  const [dispositionClass, setDispositionClass] = useState("CONFIRMED_OOS");
  const [extNotes, setExtNotes] = useState("");

  async function load(id = oosId) {
    if (!id.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setOos(await api.get<OosRecord>(`/quality/oos/v1/${id.trim()}`));
      setOosId(id.trim());
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
      setOos(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHead
        title="OOS / OOT"
        subtitle="Document 25 — out-of-specification investigation: lab phase, assignable-cause decision, extended investigation, disposition and closure."
      />

      <div className="grid grid-cols-2 gap-4 mb-4">
        <OpenFromResultCard onOpened={(id) => load(id)} />
        <Card pad>
          <CardHeader title="Look up OOS record" />
          <form
            onSubmit={(e) => {
              e.preventDefault();
              load();
            }}
            className="flex items-end gap-3 mt-3"
          >
            <Field label="OOS record ID">
              <Input value={oosId} onChange={(e) => setOosId(e.target.value)} style={{ minWidth: 260 }} />
            </Field>
            <Button type="submit" variant="secondary" disabled={loading || !oosId.trim()}>
              <Icon name="search" /> {loading ? "Loading…" : "Open"}
            </Button>
          </form>
          {error && <p className="error-text mt-3">{error}</p>}
        </Card>
      </div>

      {oos && (
        <>
          <Card pad className="mb-4">
            <div className="flex justify-between items-center mb-3">
              <span className="font-semibold flex items-center gap-3">
                {oos.oos_number} <WorkflowStatePill state={oos.state} />
              </span>
            </div>
            <FactGrid>
              <Fact label="Severity">
                <SeverityPill severity={oos.severity} />
              </Fact>
              <Fact label="Hold status">{oos.hold_status ?? "—"}</Fact>
              <Fact label="Final classification">{oos.final_classification ?? "—"}</Fact>
              <Fact label="Root cause code">{oos.root_cause_code ?? "—"}</Fact>
              <Fact label="Record version">{oos.version}</Fact>
              <IdFact label="Source result" value={oos.source_result_id} />
            </FactGrid>
          </Card>

          <div className="grid grid-cols-3 gap-4 mb-4">
            <Card pad>
              <CardHeader title={`Investigation activities (${oos.activities.length})`} />
              {oos.activities.length === 0 ? (
                <p className="hint mt-2">None recorded.</p>
              ) : (
                <Table>
                  <thead>
                    <tr>
                      <th>Phase</th>
                      <th>Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {oos.activities.map((a) => (
                      <tr key={a.id}>
                        <td>{a.phase}</td>
                        <td>{a.activity_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card>
            <Card pad>
              <CardHeader title={`Retest plans (${oos.retest_plans.length})`} />
              {oos.retest_plans.length === 0 ? (
                <p className="hint mt-2">None authorized.</p>
              ) : (
                <ul className="fs-2 mt-2" style={{ paddingLeft: "1.2em" }}>
                  {oos.retest_plans.map((p) => (
                    <li key={p.id}>{p.status}</li>
                  ))}
                </ul>
              )}
            </Card>
            <Card pad>
              <CardHeader title={`Resample plans (${oos.resample_plans.length})`} />
              {oos.resample_plans.length === 0 ? (
                <p className="hint mt-2">None authorized.</p>
              ) : (
                <ul className="fs-2 mt-2" style={{ paddingLeft: "1.2em" }}>
                  {oos.resample_plans.map((p) => (
                    <li key={p.id}>{p.status}</li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <Card pad>
            <CardHeader title="Actions" />
            <div className="flex flex-wrap gap-2 mt-3">
              {canInvestigateOos(me) && (
                <>
                  <LabInvestigationButton oos={oos} onDone={() => load()} />
                  <ClassifyLabCauseButton oos={oos} onDone={() => load()} />
                  <RetestPlanButton oos={oos} onDone={() => load()} />
                  <ResamplePlanButton oos={oos} onDone={() => load()} />
                  <ImpactButton oos={oos} onDone={() => load()} />
                </>
              )}
              {canExtendOos(me) && (
                <Button variant="secondary" onClick={() => setSig("extended_investigation")}>
                  Start extended investigation
                </Button>
              )}
              {canDispositionOos(me) && (
                <>
                  <Button variant="primary" onClick={() => setSig("disposition")}>
                    Approve disposition
                  </Button>
                  <Button variant="success" onClick={() => setSig("close")}>
                    Close OOS
                  </Button>
                </>
              )}
            </div>
          </Card>
        </>
      )}

      {oos && sig === "extended_investigation" && (
        <SignatureCeremony
          open
          onClose={() => setSig(null)}
          onDone={() => {
            setSig(null);
            load();
          }}
          challengePath={`/quality/oos/v1/${oos.id}/signature-challenges`}
          action="extended_investigation"
          title={`Start extended investigation — ${oos.oos_number}`}
          summary="Escalates the OOS to a full manufacturing / extended investigation. Requires your signature."
          extraFields={
            <Field label="Investigation notes">
              <textarea className="input" rows={3} value={extNotes} onChange={(e) => setExtNotes(e.target.value)} />
            </Field>
          }
          onSign={(p) =>
            api.post<MutationReceipt>(`/quality/oos/v1/${oos.id}/extended-investigation`, {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              oos_record_id: oos.id,
              expected_version: oos.version,
              investigation_notes: extNotes.trim() || null,
            })
          }
        />
      )}

      {oos && sig === "disposition" && (
        <SignatureCeremony
          open
          onClose={() => setSig(null)}
          onDone={() => {
            setSig(null);
            load();
          }}
          challengePath={`/quality/oos/v1/${oos.id}/signature-challenges`}
          action="disposition"
          title={`Approve disposition — ${oos.oos_number}`}
          summary="Records the final classification of this OOS result. This is a released quality decision."
          submitLabel="Sign & approve"
          extraFields={
            <Field label="Final classification" required>
              <Input value={dispositionClass} onChange={(e) => setDispositionClass(e.target.value)} />
            </Field>
          }
          disabled={!dispositionClass.trim()}
          onSign={(p) =>
            api.post<MutationReceipt>(`/quality/oos/v1/${oos.id}/disposition`, {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              oos_record_id: oos.id,
              expected_version: oos.version,
              final_classification: dispositionClass.trim(),
            })
          }
        />
      )}

      {oos && sig === "close" && (
        <SignatureCeremony
          open
          onClose={() => setSig(null)}
          onDone={() => {
            setSig(null);
            load();
          }}
          challengePath={`/quality/oos/v1/${oos.id}/signature-challenges`}
          action="close"
          title={`Close OOS — ${oos.oos_number}`}
          summary="Closes the investigation. All required phases and the disposition must already be complete."
          submitLabel="Sign & close"
          submitVariant="success"
          onSign={(p) =>
            api.post<MutationReceipt>(`/quality/oos/v1/${oos.id}/close`, {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              oos_record_id: oos.id,
              expected_version: oos.version,
            })
          }
        />
      )}
    </div>
  );
}

function OpenFromResultCard({ onOpened }: { onOpened: (oosId: string) => void }) {
  const [resultId, setResultId] = useState("");
  const [oosNumber, setOosNumber] = useState("");
  const [severity, setSeverity] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const receipt = await api.post<MutationReceipt>(
        `/quality/oos/v1/from-result/${encodeURIComponent(resultId.trim())}`,
        {
          idempotency_key: newIdempotencyKey(),
          source_result_id: resultId.trim(),
          oos_number: oosNumber.trim(),
          severity: severity.trim() || null,
        }
      );
      onOpened(receipt.aggregate_id);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not open OOS");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad>
      <CardHeader title="Open OOS from a result" />
      <form onSubmit={submit} className="mt-3">
        <Field label="Source QC result ID" required>
          <Input value={resultId} onChange={(e) => setResultId(e.target.value)} required />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="OOS number" required>
            <Input value={oosNumber} onChange={(e) => setOosNumber(e.target.value)} required />
          </Field>
          <Field label="Severity" hint="Optional.">
            <Input value={severity} onChange={(e) => setSeverity(e.target.value)} placeholder="e.g. major" />
          </Field>
        </div>
        {error && <p className="error-text mt-2">{error}</p>}
        <Button type="submit" variant="primary" disabled={busy || !resultId.trim() || !oosNumber.trim()} className="mt-2">
          {busy ? "Opening…" : "Open OOS"}
        </Button>
      </form>
    </Card>
  );
}

function LabInvestigationButton({ oos, onDone }: { oos: OosRecord; onDone: () => void }) {
  const [activityType, setActivityType] = useState("checklist_review");
  const [checklistItem, setChecklistItem] = useState("");
  const [responseText, setResponseText] = useState("");
  return (
    <WorkflowActionButton
      label="Record lab investigation"
      title={`Lab investigation — ${oos.oos_number}`}
      summary="Records one Phase 1a laboratory-investigation activity against this OOS."
      confirmLabel="Record"
      onDone={onDone}
      extraFields={
        <>
          <Field label="Activity type" required>
            <Input value={activityType} onChange={(e) => setActivityType(e.target.value)} />
          </Field>
          <Field label="Checklist item">
            <Input value={checklistItem} onChange={(e) => setChecklistItem(e.target.value)} />
          </Field>
          <Field label="Response">
            <textarea className="input" rows={2} value={responseText} onChange={(e) => setResponseText(e.target.value)} />
          </Field>
        </>
      }
      onConfirm={() =>
        api.post(`/quality/oos/v1/${oos.id}/lab-investigation`, {
          idempotency_key: newIdempotencyKey(),
          oos_record_id: oos.id,
          expected_version: oos.version,
          activity_type: activityType.trim(),
          checklist_item: checklistItem.trim() || null,
          response_text: responseText.trim() || null,
        })
      }
    />
  );
}

function ClassifyLabCauseButton({ oos, onDone }: { oos: OosRecord; onDone: () => void }) {
  const [assignable, setAssignable] = useState("no");
  const [rootCauseCode, setRootCauseCode] = useState("");
  return (
    <WorkflowActionButton
      label="Classify lab cause"
      title={`Assignable-cause decision — ${oos.oos_number}`}
      summary="Records whether the lab investigation found an assignable cause. If assignable, the original result can be invalidated."
      confirmLabel="Record decision"
      onDone={onDone}
      extraFields={
        <>
          <Field label="Assignable cause found?" required>
            <select className="input" value={assignable} onChange={(e) => setAssignable(e.target.value)}>
              <option value="no">No</option>
              <option value="yes">Yes</option>
            </select>
          </Field>
          <Field label="Root cause code" hint="Required when assignable.">
            <Input value={rootCauseCode} onChange={(e) => setRootCauseCode(e.target.value)} />
          </Field>
        </>
      }
      onConfirm={() =>
        api.post(`/quality/oos/v1/${oos.id}/classify-lab-cause`, {
          idempotency_key: newIdempotencyKey(),
          oos_record_id: oos.id,
          expected_version: oos.version,
          assignable: assignable === "yes",
          root_cause_code: rootCauseCode.trim() || null,
        })
      }
    />
  );
}

function RetestPlanButton({ oos, onDone }: { oos: OosRecord; onDone: () => void }) {
  const [justification, setJustification] = useState("");
  const [numberOfRetests, setNumberOfRetests] = useState("1");
  const [methodRef, setMethodRef] = useState("");
  return (
    <WorkflowActionButton
      label="Authorize retest plan"
      title={`Retest plan — ${oos.oos_number}`}
      summary="Authorizes a pre-defined retest scheme. The number of retests and interpretation rule are fixed before any retest is run."
      confirmLabel="Authorize"
      onDone={onDone}
      extraFields={
        <>
          <Field label="Justification" required>
            <textarea className="input" rows={2} value={justification} onChange={(e) => setJustification(e.target.value)} />
          </Field>
          <Field label="Number of retests" required>
            <Input type="number" min={1} value={numberOfRetests} onChange={(e) => setNumberOfRetests(e.target.value)} />
          </Field>
          <Field label="Method reference">
            <Input value={methodRef} onChange={(e) => setMethodRef(e.target.value)} />
          </Field>
        </>
      }
      onConfirm={() =>
        api.post(`/quality/oos/v1/${oos.id}/retest-plans`, {
          idempotency_key: newIdempotencyKey(),
          oos_record_id: oos.id,
          justification: justification.trim(),
          number_of_retests: Number(numberOfRetests),
          method_ref: methodRef.trim() || null,
        })
      }
    />
  );
}

function ResamplePlanButton({ oos, onDone }: { oos: OosRecord; onDone: () => void }) {
  const [rationale, setRationale] = useState("");
  const [samplingPlanRef, setSamplingPlanRef] = useState("");
  return (
    <WorkflowActionButton
      label="Authorize resample plan"
      title={`Resample plan — ${oos.oos_number}`}
      summary="Authorizes drawing a fresh sample. Requires a documented scientific rationale (resampling is not a retest)."
      confirmLabel="Authorize"
      onDone={onDone}
      extraFields={
        <>
          <Field label="Scientific rationale" required>
            <textarea className="input" rows={2} value={rationale} onChange={(e) => setRationale(e.target.value)} />
          </Field>
          <Field label="Sampling plan reference">
            <Input value={samplingPlanRef} onChange={(e) => setSamplingPlanRef(e.target.value)} />
          </Field>
        </>
      }
      onConfirm={() =>
        api.post(`/quality/oos/v1/${oos.id}/resample-plans`, {
          idempotency_key: newIdempotencyKey(),
          oos_record_id: oos.id,
          scientific_rationale: rationale.trim(),
          sampling_plan_ref: samplingPlanRef.trim() || null,
        })
      }
    />
  );
}

function ImpactButton({ oos, onDone }: { oos: OosRecord; onDone: () => void }) {
  const [impactText, setImpactText] = useState("");
  const [holdStatus, setHoldStatus] = useState("");
  return (
    <WorkflowActionButton
      label="Record impact assessment"
      title={`Impact assessment — ${oos.oos_number}`}
      summary="Records the assessed impact on other batches, lots and released product, and the resulting hold status."
      confirmLabel="Record"
      onDone={onDone}
      extraFields={
        <>
          <Field label="Impact assessment" required>
            <textarea className="input" rows={3} value={impactText} onChange={(e) => setImpactText(e.target.value)} />
          </Field>
          <Field label="Hold status">
            <Input value={holdStatus} onChange={(e) => setHoldStatus(e.target.value)} placeholder="e.g. batch_on_hold" />
          </Field>
        </>
      }
      onConfirm={() =>
        api.post(`/quality/oos/v1/${oos.id}/impact`, {
          idempotency_key: newIdempotencyKey(),
          oos_record_id: oos.id,
          expected_version: oos.version,
          impact_text: impactText.trim(),
          hold_status: holdStatus.trim() || null,
        })
      }
    />
  );
}
