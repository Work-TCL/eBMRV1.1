"use client";

import { useState } from "react";
import { api, ApiError, holdsAnyRole, newIdempotencyKey, type Me, type MutationReceipt } from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { KeyValueRows, buildKvObject, type KvRow } from "@/components/shared/RepeatableFields";

// em_models.py ALERT_ACTION_STATUSES
const ALERT_ACTION_STATUSES = ["normal", "alert", "action_excursion"];

// GET /em/v1/results/{sample_id}
interface EmSample {
  id: string;
  site_id: string;
  program_version_id: string;
  location_id: string;
  monitoring_type: string;
  state: string;
  result: Record<string, unknown> | null;
  alert_action_status: string | null;
  requires_deviation: boolean;
  version: number;
}

const canCollect = (me: Me | null) =>
  holdsAnyRole(me, ["Admin", "EM Technician", "Microbiology Analyst", "Operator", "Supervisor"]);
const canReview = (me: Me | null) => holdsAnyRole(me, ["Admin", "QA Reviewer", "Microbiology Analyst"]);

export default function EmPage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [sampleId, setSampleId] = useState("");
  const [sample, setSample] = useState<EmSample | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);

  async function load(id = sampleId) {
    if (!id.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setSample(await api.get<EmSample>(`/em/v1/results/${id.trim()}`));
      setSampleId(id.trim());
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
      setSample(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHead
        title="Environmental monitoring"
        subtitle="EM samples and readings: collection, result, excursion review and area readiness."
      />

      <div className="grid grid-cols-2 gap-4 mb-4">
        {canCollect(me) && <CreateTaskCard siteId={siteId} onCreated={(id) => load(id)} />}
        {canCollect(me) && <RecordResultCard onDone={() => load()} />}
      </div>

      <Card pad className="mb-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
          className="flex flex-wrap items-end gap-3"
        >
          <Field label="EM sample / reading ID">
            <Input value={sampleId} onChange={(e) => setSampleId(e.target.value)} style={{ minWidth: 200, maxWidth: 320, width: "100%" }} />
          </Field>
          <Button type="submit" variant="secondary" disabled={loading || !sampleId.trim()}>
            <Icon name="search" /> {loading ? "Loading…" : "Open"}
          </Button>
        </form>
        {error && <p className="error-text mt-3">{error}</p>}
      </Card>

      {sample && (
        <>
          <Card pad className="mb-4">
            <div className="flex justify-between items-center mb-3">
              <span className="font-semibold flex items-center gap-3">
                EM {sample.id.slice(0, 8)}… <WorkflowStatePill state={sample.state} />
              </span>
            </div>
            <FactGrid>
              <Fact label="Monitoring type">{sample.monitoring_type}</Fact>
              <Fact label="Alert / action status">
                {sample.alert_action_status ? (
                  <StatePill
                    state={sample.alert_action_status === "normal" ? "accepted" : "failed"}
                    icon={sample.alert_action_status === "normal" ? "check-circle" : "alert-triangle"}
                  >
                    {sample.alert_action_status}
                  </StatePill>
                ) : (
                  "—"
                )}
              </Fact>
              <Fact label="Requires deviation">{sample.requires_deviation ? "Yes" : "No"}</Fact>
              <Fact label="Record version">{sample.version}</Fact>
              <IdFact label="Program version" value={sample.program_version_id} />
              <IdFact label="Location" value={sample.location_id} />
            </FactGrid>
            <JsonPanel title="Result" value={sample.result} />
          </Card>

          {canReview(me) && (
            <Card pad>
              <CardHeader title="Actions" />
              <div className="mt-3">
                <Button variant="success" onClick={() => setReviewOpen(true)}>
                  Review result (sign)
                </Button>
              </div>
            </Card>
          )}
        </>
      )}

      {sample && reviewOpen && (
        <SignatureCeremony
          open
          onClose={() => setReviewOpen(false)}
          onDone={() => {
            setReviewOpen(false);
            load();
          }}
          challengePath={`/em/v1/results/${sample.id}/signature-challenges`}
          action="review"
          title={`Review EM result — ${sample.id.slice(0, 8)}…`}
          summary="Independent microbiological review of this EM result, including any excursion assessment."
          submitLabel="Sign & review"
          submitVariant="success"
          reason="optional"
          onSign={(p) =>
            api.post<MutationReceipt>(`/em/v1/results/${sample.id}/review`, {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              sample_id: sample.id,
              expected_version: sample.version,
              reason: p.reason,
            })
          }
        />
      )}
    </div>
  );
}

function CreateTaskCard({ siteId, onCreated }: { siteId: string | null; onCreated: (id: string) => void }) {
  const [programVersionId, setProgramVersionId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [monitoringType, setMonitoringType] = useState("viable_air");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const receipt = await api.post<MutationReceipt>("/em/v1/tasks", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        program_version_id: programVersionId.trim(),
        location_id: locationId.trim(),
        monitoring_type: monitoringType.trim(),
      });
      onCreated(receipt.aggregate_id);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad>
      <CardHeader title="Schedule EM sampling task" />
      <form onSubmit={submit} className="mt-3">
        <Field label="Program version ID" required>
          <Input value={programVersionId} onChange={(e) => setProgramVersionId(e.target.value)} required />
        </Field>
        <Field label="Location ID" required>
          <Input value={locationId} onChange={(e) => setLocationId(e.target.value)} required />
        </Field>
        <Field label="Monitoring type" required>
          <Input value={monitoringType} onChange={(e) => setMonitoringType(e.target.value)} required />
        </Field>
        {error && <p className="error-text mt-2">{error}</p>}
        <Button type="submit" variant="primary" disabled={busy || !programVersionId.trim() || !locationId.trim()} className="mt-2">
          {busy ? "Creating…" : "Schedule task"}
        </Button>
      </form>
    </Card>
  );
}

function RecordResultCard({ onDone }: { onDone: () => void }) {
  const [sampleId, setSampleId] = useState("");
  const [expectedVersion, setExpectedVersion] = useState("");
  const [result, setResult] = useState<KvRow[]>([{ key: "count", value: "0" }]);
  const [alertActionStatus, setAlertActionStatus] = useState("normal");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      await api.post<MutationReceipt>("/em/v1/results", {
        idempotency_key: newIdempotencyKey(),
        sample_id: sampleId.trim(),
        expected_version: expectedVersion ? Number(expectedVersion) : null,
        result: buildKvObject(result),
        alert_action_status: alertActionStatus.trim(),
      });
      setDone(true);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Record failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad>
      <CardHeader title="Record EM result" />
      <form onSubmit={submit} className="mt-3">
        <Field label="Sample / reading ID" required>
          <Input value={sampleId} onChange={(e) => setSampleId(e.target.value)} required />
        </Field>
        <Field label="Expected version" hint="From the sample record.">
          <Input type="number" value={expectedVersion} onChange={(e) => setExpectedVersion(e.target.value)} />
        </Field>
        <KeyValueRows
          label="Result"
          hint='The reading, e.g. "count" → 12, "unit" → cfu.'
          value={result}
          onChange={setResult}
        />
        <Field label="Alert / action status" required>
          <Select value={alertActionStatus} onChange={(e) => setAlertActionStatus(e.target.value)}>
            {ALERT_ACTION_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
        </Field>
        {error && <p className="error-text mt-2">{error}</p>}
        {done && <p className="fs-2 mt-2">Result recorded.</p>}
        <Button type="submit" variant="primary" disabled={busy || !sampleId.trim()} className="mt-2">
          {busy ? "Recording…" : "Record result"}
        </Button>
      </form>
    </Card>
  );
}
