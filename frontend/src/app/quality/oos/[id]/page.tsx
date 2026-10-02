"use client";

import { use, useState } from "react";
import {
  api,
  canInvestigateOos,
  canExtendOos,
  canDispositionOos,
  formatDateTime,
  newIdempotencyKey,
  type MutationReceipt,
} from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
import { RecordDetailShell } from "@/components/shared/RecordDetailShell";
import { WorkflowActionButton } from "@/components/shared/WorkflowActionButton";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { Fact, IdFact } from "@/components/ui/FactGrid";
import { Tabs } from "@/components/ui/Tabs";
import { Table } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill, SeverityPill } from "@/components/ui/StatePill";

interface OosActivity {
  id: string;
  phase: string;
  activity_type: string;
  checklist_item: string | null;
  response_text: string | null;
  evidence_refs: string[];
  investigator_user_id: string;
  occurred_at: string | null;
  version: number;
}
interface OosRetestPlan {
  id: string;
  justification: string;
  number_of_retests: number;
  method_ref: string | null;
  analyst_criteria: string | null;
  instrument_criteria: string | null;
  interpretation_rule: string | null;
  status: string;
  version: number;
  created_at: string | null;
}
interface OosResamplePlan {
  id: string;
  scientific_rationale: string;
  sampling_plan_ref: string | null;
  sampling_plan_version: string | null;
  source_ref: string | null;
  approver_user_id: string | null;
  resulting_sample_ids: string[] | null;
  status: string;
  version: number;
  created_at: string | null;
}

// GET /quality/oos/v1/{id} — app/modules/qc/router.py::get_oos_record
interface OosDetail {
  id: string;
  site_id: string | null;
  oos_number: string;
  source_result_id: string;
  sample_id: string | null;
  test_order_id: string | null;
  batch_id: string | null;
  material_lot_id: string | null;
  state: string;
  severity: string | null;
  hold_status: string | null;
  final_classification: string | null;
  root_cause_code: string | null;
  version: number;
  opened_at: string | null;
  closed_at: string | null;
  activities: OosActivity[];
  retest_plans: OosRetestPlan[];
  resample_plans: OosResamplePlan[];
}

type UnsignedAction = "lab_investigation" | "classify_lab_cause" | "retest_plan" | "resample_plan" | "impact";
type SignedAction = "extended_investigation" | "disposition" | "close";

// Mirrors each command's own state guard in app/modules/qc/commands.py exactly (record_lab_investigation/
// classify_lab_cause/start_extended_investigation/authorize_retest_plan/authorize_resample_plan/
// record_impact_assessment/approve_disposition/close_oos).
const UNSIGNED_ALLOWED_FROM: Record<string, UnsignedAction[]> = {
  open: ["lab_investigation", "classify_lab_cause"],
  lab_investigation: ["lab_investigation", "classify_lab_cause"],
  qa_review: ["impact"],
  extended_investigation: ["retest_plan", "resample_plan", "impact"],
};
const SIGNED_ALLOWED_FROM: Record<string, SignedAction[]> = {
  no_assignable_lab_cause: ["extended_investigation"],
  final_disposition: ["disposition"],
  qa_approval: ["close"],
};
// "closed" is terminal — OOS has no reopen in this build (SG-074's own register entry: oos_record's
// DDL-frozen schema has no reopen_history column, unlike OOT's flat open/closed model).

const SIGNED_LABEL: Record<SignedAction, string> = {
  extended_investigation: "Start extended investigation",
  disposition: "Approve disposition",
  close: "Close OOS",
};

export default function OosDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const { data, loading, error, reload } = useApiResource<OosDetail>(`/quality/oos/v1/${id}`);
  const [sig, setSig] = useState<SignedAction | null>(null);
  const [dispositionClass, setDispositionClass] = useState("");
  const [extNotes, setExtNotes] = useState("");

  const unsignedAllowed = data ? UNSIGNED_ALLOWED_FROM[data.state] ?? [] : [];
  const signedAllowed = data ? SIGNED_ALLOWED_FROM[data.state] ?? [] : [];
  const investigate = canInvestigateOos(me);
  const extend = canExtendOos(me);
  const disposition = canDispositionOos(me);

  return (
    <RecordDetailShell
      recordNumber={data?.oos_number ?? ""}
      state={data?.state}
      subtitle={data ? `Source result ${data.source_result_id.slice(0, 8)}…` : undefined}
      backHref="/quality/oos"
      backLabel="OOS / OOT"
      loading={loading}
      error={error}
      actions={
        data && (
          <>
            {investigate && unsignedAllowed.includes("lab_investigation") && (
              <LabInvestigationButton oos={data} onDone={reload} />
            )}
            {investigate && unsignedAllowed.includes("classify_lab_cause") && (
              <ClassifyLabCauseButton oos={data} onDone={reload} />
            )}
            {investigate && unsignedAllowed.includes("retest_plan") && <RetestPlanButton oos={data} onDone={reload} />}
            {investigate && unsignedAllowed.includes("resample_plan") && (
              <ResamplePlanButton oos={data} onDone={reload} />
            )}
            {investigate && unsignedAllowed.includes("impact") && <ImpactButton oos={data} onDone={reload} />}
            {extend && signedAllowed.includes("extended_investigation") && (
              <Button variant="secondary" onClick={() => setSig("extended_investigation")}>
                <Icon name="pen" /> {SIGNED_LABEL.extended_investigation}
              </Button>
            )}
            {disposition && signedAllowed.includes("disposition") && (
              <Button variant="primary" onClick={() => setSig("disposition")}>
                <Icon name="pen" /> {SIGNED_LABEL.disposition}
              </Button>
            )}
            {disposition && signedAllowed.includes("close") && (
              <Button variant="success" onClick={() => setSig("close")}>
                <Icon name="pen" /> {SIGNED_LABEL.close}
              </Button>
            )}
          </>
        )
      }
      facts={
        data && (
          <>
            <Fact label="Severity">
              <SeverityPill severity={data.severity} />
            </Fact>
            <Fact label="Hold status">{data.hold_status ?? "—"}</Fact>
            <Fact label="Final classification">{data.final_classification ?? "—"}</Fact>
            <Fact label="Root cause code">{data.root_cause_code ?? "—"}</Fact>
            <Fact label="Opened">{data.opened_at ? formatDateTime(data.opened_at) : "—"}</Fact>
            <Fact label="Closed">{data.closed_at ? formatDateTime(data.closed_at) : "—"}</Fact>
            <Fact label="Record version">{data.version}</Fact>
            <IdFact label="Source result" value={data.source_result_id} />
            {data.batch_id && <IdFact label="Batch" value={data.batch_id} />}
            {data.material_lot_id && <IdFact label="Material lot" value={data.material_lot_id} />}
          </>
        )
      }
    >
      {data && (
        <Tabs
          tabs={[
            {
              id: "activities",
              label: "Investigation activities",
              badge: data.activities.length || undefined,
              content: <ActivitiesTab activities={data.activities} />,
            },
            {
              id: "retest",
              label: "Retest plans",
              badge: data.retest_plans.length || undefined,
              content: <RetestTab plans={data.retest_plans} />,
            },
            {
              id: "resample",
              label: "Resample plans",
              badge: data.resample_plans.length || undefined,
              content: <ResampleTab plans={data.resample_plans} />,
            },
          ]}
        />
      )}

      {data && sig === "extended_investigation" && (
        <SignatureCeremony
          open
          onClose={() => setSig(null)}
          onDone={() => {
            setSig(null);
            reload();
          }}
          challengePath={`/quality/oos/v1/${data.id}/signature-challenges`}
          action="extended_investigation"
          title={`Start extended investigation - ${data.oos_number}`}
          summary="Escalates the OOS to a full manufacturing / extended investigation. Signer must be independent of the lab investigator (SoD)."
          extraFields={
            <Field label="Investigation notes">
              <textarea className="input" rows={3} value={extNotes} onChange={(e) => setExtNotes(e.target.value)} />
            </Field>
          }
          onSign={(p) =>
            api.post<MutationReceipt>(`/quality/oos/v1/${data.id}/extended-investigation`, {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              oos_record_id: data.id,
              expected_version: data.version,
              investigation_notes: extNotes.trim() || null,
            })
          }
        />
      )}

      {data && sig === "disposition" && (
        <SignatureCeremony
          open
          onClose={() => setSig(null)}
          onDone={() => {
            setSig(null);
            reload();
          }}
          challengePath={`/quality/oos/v1/${data.id}/signature-challenges`}
          action="disposition"
          title={`Approve disposition - ${data.oos_number}`}
          summary="Records the final classification of this OOS result. This is a released quality decision."
          submitLabel="Sign & approve"
          extraFields={
            <Field label="Final classification" required>
              <Input
                value={dispositionClass}
                onChange={(e) => setDispositionClass(e.target.value)}
                placeholder="e.g. laboratory_error"
              />
            </Field>
          }
          disabled={!dispositionClass.trim()}
          onSign={(p) =>
            api.post<MutationReceipt>(`/quality/oos/v1/${data.id}/disposition`, {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              oos_record_id: data.id,
              expected_version: data.version,
              final_classification: dispositionClass.trim(),
            })
          }
        />
      )}

      {data && sig === "close" && (
        <SignatureCeremony
          open
          onClose={() => setSig(null)}
          onDone={() => {
            setSig(null);
            reload();
          }}
          challengePath={`/quality/oos/v1/${data.id}/signature-challenges`}
          action="close"
          title={`Close OOS - ${data.oos_number}`}
          summary="Closes the investigation. Signer must be independent of whoever approved the disposition (SoD)."
          submitLabel="Sign & close"
          submitVariant="success"
          onSign={(p) =>
            api.post<MutationReceipt>(`/quality/oos/v1/${data.id}/close`, {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              oos_record_id: data.id,
              expected_version: data.version,
            })
          }
        />
      )}
    </RecordDetailShell>
  );
}

function ActivitiesTab({ activities }: { activities: OosActivity[] }) {
  if (activities.length === 0) {
    return <p className="hint">No investigation activities recorded yet.</p>;
  }
  return (
    <Table>
      <thead>
        <tr>
          <th>Phase</th>
          <th>Type</th>
          <th>Checklist item</th>
          <th>Response</th>
          <th>Occurred</th>
        </tr>
      </thead>
      <tbody>
        {activities.map((a) => (
          <tr key={a.id}>
            <td className="fs-2">{a.phase}</td>
            <td className="fs-2">{a.activity_type}</td>
            <td className="fs-2">{a.checklist_item ?? "—"}</td>
            <td className="fs-2">{a.response_text ?? "—"}</td>
            <td className="tabular fs-2">{a.occurred_at ? formatDateTime(a.occurred_at) : "—"}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function RetestTab({ plans }: { plans: OosRetestPlan[] }) {
  if (plans.length === 0) {
    return <p className="hint">No retest plans authorized yet.</p>;
  }
  return (
    <Table>
      <thead>
        <tr>
          <th>Status</th>
          <th>Justification</th>
          <th># Retests</th>
          <th>Method</th>
        </tr>
      </thead>
      <tbody>
        {plans.map((p) => (
          <tr key={p.id}>
            <td>
              <WorkflowStatePill state={p.status} />
            </td>
            <td className="fs-2">{p.justification}</td>
            <td className="tabular fs-2">{p.number_of_retests}</td>
            <td className="fs-2">{p.method_ref ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function ResampleTab({ plans }: { plans: OosResamplePlan[] }) {
  if (plans.length === 0) {
    return <p className="hint">No resample plans authorized yet.</p>;
  }
  return (
    <Table>
      <thead>
        <tr>
          <th>Status</th>
          <th>Scientific rationale</th>
          <th>Sampling plan ref</th>
        </tr>
      </thead>
      <tbody>
        {plans.map((p) => (
          <tr key={p.id}>
            <td>
              <WorkflowStatePill state={p.status} />
            </td>
            <td className="fs-2">{p.scientific_rationale}</td>
            <td className="fs-2">{p.sampling_plan_ref ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function LabInvestigationButton({ oos, onDone }: { oos: OosDetail; onDone: () => void }) {
  const [activityType, setActivityType] = useState("checklist_review");
  const [checklistItem, setChecklistItem] = useState("");
  const [responseText, setResponseText] = useState("");
  return (
    <WorkflowActionButton
      label="Record lab investigation"
      title={`Lab investigation - ${oos.oos_number}`}
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

function ClassifyLabCauseButton({ oos, onDone }: { oos: OosDetail; onDone: () => void }) {
  const [assignable, setAssignable] = useState("no");
  const [rootCauseCode, setRootCauseCode] = useState("");
  return (
    <WorkflowActionButton
      label="Classify lab cause"
      title={`Assignable-cause decision - ${oos.oos_number}`}
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

function RetestPlanButton({ oos, onDone }: { oos: OosDetail; onDone: () => void }) {
  const [justification, setJustification] = useState("");
  const [numberOfRetests, setNumberOfRetests] = useState("1");
  const [methodRef, setMethodRef] = useState("");
  return (
    <WorkflowActionButton
      label="Authorize retest plan"
      title={`Retest plan - ${oos.oos_number}`}
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

function ResamplePlanButton({ oos, onDone }: { oos: OosDetail; onDone: () => void }) {
  const [rationale, setRationale] = useState("");
  const [samplingPlanRef, setSamplingPlanRef] = useState("");
  return (
    <WorkflowActionButton
      label="Authorize resample plan"
      title={`Resample plan - ${oos.oos_number}`}
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

function ImpactButton({ oos, onDone }: { oos: OosDetail; onDone: () => void }) {
  const [impactText, setImpactText] = useState("");
  const [holdStatus, setHoldStatus] = useState("");
  return (
    <WorkflowActionButton
      label="Record impact assessment"
      title={`Impact assessment - ${oos.oos_number}`}
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
