"use client";

import { useEffect, useState, type CSSProperties } from "react";
import {
  api,
  ApiError,
  canDispositionOos,
  canExtendOos,
  canInvestigateOos,
  newIdempotencyKey,
  type MutationReceipt,
} from "@/lib/api";
import { useEntityOptions, useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { WorkflowStatePill, SeverityPill } from "@/components/ui/StatePill";
import { WorkflowActionButton } from "@/components/shared/WorkflowActionButton";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";

// GET /qc/v1/results?batch_id=... — real picker data for a field referencing a `qc_result` row by id
// (qc/router.py::list_results_for_batch's own docstring names DDCP's `qc_record_reference` as the first
// caller this was built for; OOS/OOT's "Source QC result ID" is the same shape of gap). Scoped to a
// chosen batch, not a flat list — a QC result only makes sense in the context of which batch it came
// from, so this cascades on a batch picker exactly like `inventory/page.tsx`'s lot -> container picker
// cascades on a chosen lot (same "state lags behind the id it was fetched for" guard against a stale list
// flashing while a new batch's fetch is in flight).
interface QcResultOption {
  id: string;
  label: string;
}

const linkBtnStyle: CSSProperties = {
  background: "none",
  border: "none",
  padding: 0,
  color: "var(--brand-600)",
  fontSize: "var(--fs-1)",
  cursor: "pointer",
  textDecoration: "underline",
  marginTop: 4,
};

function useQcResultsForBatch(batchId: string): { options: QcResultOption[]; loading: boolean } {
  const [results, setResults] = useState<QcResultOption[]>([]);
  const [resultsBatchId, setResultsBatchId] = useState<string | null>(null);
  useEffect(() => {
    if (!batchId) return;
    let cancelled = false;
    api
      .get<QcResultOption[]>(`/qc/v1/results?batch_id=${encodeURIComponent(batchId)}`)
      .then((rows) => {
        if (cancelled) return;
        setResults(rows);
        setResultsBatchId(batchId);
      })
      .catch(() => {
        if (!cancelled) {
          setResults([]);
          setResultsBatchId(batchId);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [batchId]);
  const current = resultsBatchId === batchId ? results : [];
  return { options: current, loading: !!batchId && resultsBatchId !== batchId };
}

/** A batch picker plus a dependent QC-result picker scoped to whichever batch is chosen — replaces a
 * raw "Source QC result ID" text box across both `OotCard` and `OpenFromResultCard` below, which
 * previously asked the operator to already know a QC result's UUID (there is no "browse QC results"
 * page; this is the only place that id is discoverable without going to the database directly). */
function QcResultPickerField({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const entities = useEntityOptions();
  const [batchId, setBatchId] = useState("");
  const { options: results, loading: resultsLoading } = useQcResultsForBatch(batchId);
  const [manual, setManual] = useState(false);

  if (manual) {
    return (
      <Field label="Source QC result ID" required hint="Enter the QC result's ID directly.">
        <Input value={value} onChange={(e) => onChange(e.target.value)} style={{ minWidth: 260 }} required />
        <button type="button" style={linkBtnStyle} onClick={() => setManual(false)}>
          Choose from a batch&rsquo;s results instead
        </button>
      </Field>
    );
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <Field label="Batch" hint="Pick the batch the QC result belongs to.">
        <Select
          value={batchId}
          onChange={(e) => {
            setBatchId(e.target.value);
            onChange("");
          }}
          disabled={entities.batchesStatus === "loading"}
          style={{ minWidth: 220 }}
        >
          <option value="">{entities.batchesStatus === "loading" ? "Loading batches…" : "Select a batch…"}</option>
          {entities.batches.map((b) => (
            <option key={b.value} value={b.value}>
              {b.label}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Source QC result" required hint={!batchId ? "Pick a batch first." : undefined}>
        <Select value={value} onChange={(e) => onChange(e.target.value)} disabled={!batchId || resultsLoading}>
          <option value="">
            {!batchId ? "—" : resultsLoading ? "Loading results…" : results.length ? "Select a result…" : "No QC results for this batch"}
          </option>
          {results.map((r) => (
            <option key={r.id} value={r.id}>
              {r.label}
            </option>
          ))}
        </Select>
        <button type="button" style={linkBtnStyle} onClick={() => setManual(true)}>
          Can&rsquo;t find it? Enter ID manually
        </button>
      </Field>
    </div>
  );
}

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
        subtitle="Out-of-specification investigation: lab phase, assignable-cause decision, extended investigation, disposition and closure."
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
            className="flex flex-wrap items-end gap-3 mt-3"
          >
            <Field label="OOS record ID">
              <Input value={oosId} onChange={(e) => setOosId(e.target.value)} style={{ minWidth: 200, maxWidth: 260, width: "100%" }} />
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
                    <li key={p.id}><WorkflowStatePill state={p.status} /></li>
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
                    <li key={p.id}><WorkflowStatePill state={p.status} /></li>
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
          title={`Start extended investigation - ${oos.oos_number}`}
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
          title={`Approve disposition - ${oos.oos_number}`}
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
          title={`Close OOS - ${oos.oos_number}`}
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

      <OotCard />
    </div>
  );
}

/** Document 25 (SPEC-QC-003) OOT lifecycle — `app/modules/qc/router.py`'s `oos_router`, `/quality/oot/v1`.
 * No `GET /oot/v1/{oot_id}` exists (verified: only `evaluate`, `signature-challenges` and `close` are
 * declared) — evaluating captures the record's id/version straight from the mutation receipt, exactly
 * like `OpenFromResultCard` does for OOS above; closing a record from a prior session (its version not
 * held in this page's state) has no way to re-fetch that version, so the id/version fields are left
 * editable rather than silently wrong. Known limitation, not a SPEC_GAP (no requirement calls for OOT
 * browse/detail read, only evaluate/close). */
function OotCard() {
  const { me } = useMe();
  const [sourceResultId, setSourceResultId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ootRecordId, setOotRecordId] = useState("");
  const [expectedVersion, setExpectedVersion] = useState("");
  const [closing, setClosing] = useState(false);

  async function evaluate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const receipt = await api.post<MutationReceipt>("/quality/oot/v1/evaluate", {
        idempotency_key: newIdempotencyKey(),
        source_result_id: sourceResultId.trim(),
      });
      setOotRecordId(receipt.aggregate_id);
      setExpectedVersion(String(receipt.resulting_version));
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not evaluate OOT");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Out-of-trend (OOT)" />
      <p className="fs-2 text-muted mb-3">
        Evaluates a result against its test definition&apos;s trend rule and, if triggered, opens an OOT
        record. There is no OOT browse/detail read in this deployment - the id and version below come
        straight from the evaluate response, or can be entered directly if already known.
      </p>
      <form onSubmit={evaluate} className="flex flex-wrap items-end gap-3 mb-3">
        <QcResultPickerField value={sourceResultId} onChange={setSourceResultId} />
        <Button type="submit" variant="primary" disabled={busy || !sourceResultId.trim()}>
          {busy ? "Evaluating…" : "Evaluate for OOT"}
        </Button>
      </form>
      {error && <p className="error-text mb-3">{error}</p>}

      <div className="grid grid-cols-2 gap-4 items-end">
        <Field label="OOT record ID">
          <Input value={ootRecordId} onChange={(e) => setOotRecordId(e.target.value)} />
        </Field>
        <Field label="Expected version">
          <Input type="number" value={expectedVersion} onChange={(e) => setExpectedVersion(e.target.value)} />
        </Field>
      </div>
      {canDispositionOos(me) && (
        <Button variant="success" className="mt-3" disabled={!ootRecordId.trim() || !expectedVersion.trim()} onClick={() => setClosing(true)}>
          Close OOT
        </Button>
      )}

      {closing && (
        <SignatureCeremony
          open
          onClose={() => setClosing(false)}
          onDone={() => setClosing(false)}
          challengePath={`/quality/oot/v1/${ootRecordId.trim()}/signature-challenges`}
          action="close"
          title="Close OOT"
          summary="Closes the out-of-trend record. This cannot be undone."
          submitLabel="Sign & close"
          submitVariant="success"
          onSign={(p) =>
            api.post<MutationReceipt>(`/quality/oot/v1/${ootRecordId.trim()}/close`, {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              oot_record_id: ootRecordId.trim(),
              expected_version: Number(expectedVersion),
            })
          }
        />
      )}
    </Card>
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
        <QcResultPickerField value={resultId} onChange={setResultId} />
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

function ClassifyLabCauseButton({ oos, onDone }: { oos: OosRecord; onDone: () => void }) {
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

function RetestPlanButton({ oos, onDone }: { oos: OosRecord; onDone: () => void }) {
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

function ResamplePlanButton({ oos, onDone }: { oos: OosRecord; onDone: () => void }) {
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

function ImpactButton({ oos, onDone }: { oos: OosRecord; onDone: () => void }) {
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
