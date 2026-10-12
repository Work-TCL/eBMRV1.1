"use client";

import { useEffect, useState } from "react";
import { api, hasPermission, listAll, newIdempotencyKey, pagedFetcher, type Me, type MutationReceipt } from "@/lib/api";
import { useMe, useSiteId, type EntityOption, type EntityOptionsStatus } from "@/lib/hooks";
import { useCommand } from "@/components/shared/RecordDetailShell";
import { PageHead } from "@/components/ui/PageHead";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Field, RowButtonSlot } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Modal } from "@/components/ui/Modal";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { Table, EmptyState } from "@/components/ui/Table";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { KeyValueRows, buildKvObject, type KvRow } from "@/components/shared/RepeatableFields";
import { humanizeLabel } from "@/lib/format";

// em_models.py ALERT_ACTION_STATUSES
const ALERT_ACTION_STATUSES = ["normal", "alert", "action_excursion"];

// Matches app/modules/equipment/em_router.py::_sample_dict (list-row subset).
interface EmSample {
  id: string;
  site_id: string;
  program_version_id: string;
  program_number: string | null;
  program_version_no: number | null;
  location_id: string;
  location_code: string | null;
  monitoring_type: string;
  state: string;
  result: Record<string, unknown> | null;
  alert_action_status: string | null;
  requires_deviation: boolean;
  version: number;
}

// Matches app/modules/equipment/em_router.py::_program_dict.
interface EmProgram {
  id: string;
  program_number: string;
  version_no: number;
  method_version: string | null;
  state: string;
  version: number;
}

// Matches app/modules/equipment/em_router.py::_excursion_dict.
interface EmExcursion {
  id: string;
  sample_id: string;
  sample_monitoring_type: string | null;
  area_id: string;
  area_code: string | null;
  disposition: string | null;
  impact_assessed_at: string | null;
  requires_deviation: boolean;
  version: number;
}

// Matches app/modules/equipment/em_commands.py::get_trends.
interface EmTrendSample {
  id: string;
  monitoring_type: string;
  result: Record<string, unknown> | null;
  alert_action_status: string | null;
  created_at: string;
}

interface EmTrends {
  location_id: string;
  samples: EmTrendSample[];
}

// GET /em/v1/locations — real picker data for `location_id` (an `em_locations.id`, not an equipment
// area id — `EmSampleOrReading.location_id` FKs to `em_locations`, and `get_trends()` filters on the
// same column). The create-task form previously picked from `entities.areas` instead, which submits an
// equipment_areas.id where an em_locations.id is required — always a guaranteed `NotFoundError` from
// `create_em_task()`'s own `em_location` lookup, never a working task. Local to this page only, not
// promoted to `useEntityOptions()`, since no other page needs it yet (same precedent as aseptic's own
// `useEligibleSterileItems`).
function useEmLocationOptions(): { options: EntityOption[]; status: EntityOptionsStatus } {
  const [options, setOptions] = useState<EntityOption[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    listAll<{ id: string; location_code: string; criticality: string | null }>("/em/v1/locations")
      .then((rows) => {
        if (cancelled) return;
        setOptions(rows.map((r) => ({ value: r.id, label: [r.location_code, r.criticality].filter(Boolean).join(" - ") })));
        setStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { options, status };
}

// GET /em/v1/programs — real picker data for `program_version_id` (previously free-text, despite the
// "EM programs" list card right above the create-task form already showing every program that exists).
// No state filter (same as the backend's own unfiltered list) since `create_em_task()` doesn't require
// RELEASED either. Page-local for the same reason `useEmLocationOptions` is.
function useEmProgramOptions(): { options: EntityOption[]; status: EntityOptionsStatus } {
  const [options, setOptions] = useState<EntityOption[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    listAll<{ id: string; program_number: string; version_no: number; state: string }>("/em/v1/programs")
      .then((rows) => {
        if (cancelled) return;
        setOptions(rows.map((r) => ({ value: r.id, label: `${r.program_number} v${r.version_no} (${r.state})` })));
        setStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { options, status };
}

// GET /em/v1/samples — real picker data for a result-recording form's `sample_id` when opened from the
// page header (no sample already in context) — previously free-text despite the "EM samples/readings"
// list card showing every one. Page-local, same reasoning as the two hooks above.
function useEmSampleOptions(): { options: EntityOption[]; status: EntityOptionsStatus } {
  const [options, setOptions] = useState<EntityOption[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    listAll<{ id: string; monitoring_type: string; state: string }>("/em/v1/samples")
      .then((rows) => {
        if (cancelled) return;
        setOptions(rows.map((r) => ({ value: r.id, label: `EM ${r.id.slice(0, 8)}… - ${r.monitoring_type} (${r.state})` })));
        setStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { options, status };
}

// GET /em/v1/excursions — same reasoning as `useEmSampleOptions`, for an impact-recording form's
// `excursion_id` when opened from the page header.
function useEmExcursionOptions(): { options: EntityOption[]; status: EntityOptionsStatus } {
  const [options, setOptions] = useState<EntityOption[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    listAll<{ id: string; disposition: string | null; impact_assessed_at: string | null }>("/em/v1/excursions")
      .then((rows) => {
        if (cancelled) return;
        setOptions(
          rows.map((r) => ({
            value: r.id,
            label: `EM excursion ${r.id.slice(0, 8)}…${r.impact_assessed_at ? "" : " (impact pending)"}`,
          }))
        );
        setStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { options, status };
}

// em_program.create / em_sample.create (Document 41) — Admin + EM Technician only per scripts/seed.py.
// em_sample.record_result additionally includes Microbiology Analyst (the role that actually records lab
// results), so it gets its own, broader helper. Audit finding 2026-09-18: canCollect previously covered
// all three with one over-broad list (Operator/Supervisor hold none of these grants; Microbiology
// Analyst holds only record_result, not the two create actions).
const canCreateEm = (me: Me | null) => hasPermission(me, "em_program.create");
const canRecordEmResult = (me: Me | null) => hasPermission(me, "em_sample.record_result");
// em_sample.review (Document 41, Document 106 row 115) — Admin + QA Reviewer + QC Reviewer per
// scripts/seed.py. em_excursion.impact is narrower — Admin + QA Reviewer only — so it gets its own
// helper. Audit finding 2026-09-18: canReview previously granted both to Admin/QA Reviewer/Microbiology
// Analyst, which let Microbiology Analyst attempt em_sample.review (violates the documented SoD — the
// analyst who records a result must not also independently review it) while hiding em_sample.review from
// QC Reviewer, who actually holds it (SG-204 bug class), and wrongly including QC Reviewer on
// em_excursion.impact, which QC Reviewer does not hold.
const canReview = (me: Me | null) => hasPermission(me, "em_sample.review");
const canImpactExcursion = (me: Me | null) => hasPermission(me, "em_excursion.impact");

export default function EmPage() {
  const { me, loading: meLoading } = useMe();
  const { siteId } = useSiteId();

  const [programOpen, setProgramOpen] = useState(false);
  const [taskOpen, setTaskOpen] = useState(false);
  const [trendsOpen, setTrendsOpen] = useState(false);
  const [resultPrefill, setResultPrefill] = useState<{ sampleId: string; expectedVersion: string } | null>(null);
  const [excursionPrefill, setExcursionPrefill] = useState<{ excursionId: string; expectedVersion: string } | null>(null);

  const [viewProgram, setViewProgram] = useState<EmProgram | null>(null);
  const [viewSample, setViewSample] = useState<EmSample | null>(null);
  const [viewExcursion, setViewExcursion] = useState<EmExcursion | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);

  const [programReload, setProgramReload] = useState(0);
  const [sampleReload, setSampleReload] = useState(0);
  const [excursionReload, setExcursionReload] = useState(0);

  return (
    <div>
      <PageHead
        title="Environmental monitoring"
        subtitle="EM samples and readings: collection, result, excursion review and area readiness."
        action={
          meLoading ? (
            <div className="flex gap-2 flex-wrap">
              {[150, 210, 170, 190].map((w, i) => (
                <Skeleton key={i} width={w} height={36} radius="var(--radius-md)" />
              ))}
            </div>
          ) : (
          <>
            {canCreateEm(me) && (
              <Button variant="secondary" onClick={() => setProgramOpen(true)}>
                <Icon name="plus" /> New EM program
              </Button>
            )}
            {canCreateEm(me) && (
              <Button variant="secondary" onClick={() => setTaskOpen(true)}>
                <Icon name="plus" /> Schedule EM sampling task
              </Button>
            )}
            {canRecordEmResult(me) && (
              <Button variant="secondary" onClick={() => setResultPrefill({ sampleId: "", expectedVersion: "" })}>
                <Icon name="pen-line" /> Record EM result
              </Button>
            )}
            {canImpactExcursion(me) && (
              <Button variant="secondary" onClick={() => setExcursionPrefill({ excursionId: "", expectedVersion: "" })}>
                <Icon name="pen-line" /> Record excursion impact
              </Button>
            )}
            <Button variant="secondary" onClick={() => setTrendsOpen(true)}>
              <Icon name="gauge" /> EM trends
            </Button>
          </>
          )
        }
      />

      <EmProgramsListCard reloadToken={programReload} onOpen={setViewProgram} />
      <EmSamplesListCard reloadToken={sampleReload} onOpen={setViewSample} />
      <EmExcursionsListCard reloadToken={excursionReload} onOpen={setViewExcursion} />

      {programOpen && (
        <Modal open onClose={() => setProgramOpen(false)} title="Create an EM program" large>
          <CreateProgramForm
            siteId={siteId}
            onDone={() => {
              setProgramOpen(false);
              setProgramReload((n) => n + 1);
            }}
          />
        </Modal>
      )}

      {taskOpen && (
        <Modal open onClose={() => setTaskOpen(false)} title="Schedule EM sampling task" large>
          <CreateTaskForm
            siteId={siteId}
            onDone={() => {
              setTaskOpen(false);
              setSampleReload((n) => n + 1);
            }}
          />
        </Modal>
      )}

      {resultPrefill && (
        <Modal open onClose={() => setResultPrefill(null)} title="Record EM result" large>
          <RecordResultForm
            initialSampleId={resultPrefill.sampleId}
            initialExpectedVersion={resultPrefill.expectedVersion}
            onDone={() => {
              setResultPrefill(null);
              setViewSample(null);
              setSampleReload((n) => n + 1);
            }}
          />
        </Modal>
      )}

      {excursionPrefill && (
        <Modal open onClose={() => setExcursionPrefill(null)} title="Record excursion impact" large>
          <RecordExcursionImpactForm
            initialExcursionId={excursionPrefill.excursionId}
            initialExpectedVersion={excursionPrefill.expectedVersion}
            onDone={() => {
              setExcursionPrefill(null);
              setViewExcursion(null);
              setExcursionReload((n) => n + 1);
            }}
          />
        </Modal>
      )}

      {trendsOpen && (
        <Modal open onClose={() => setTrendsOpen(false)} title="EM trends" large>
          <TrendsForm />
        </Modal>
      )}

      {viewProgram && (
        <Modal open onClose={() => setViewProgram(null)} title={`EM program ${viewProgram.program_number} v${viewProgram.version_no}`}>
          <FactGrid>
            <Fact label="State">
              <StatePill
                state={viewProgram.state === "RELEASED" ? "accepted" : "unknown"}
                icon={viewProgram.state === "RELEASED" ? "check-circle" : "slash-circle"}
              >
                {viewProgram.state}
              </StatePill>
            </Fact>
            <Fact label="Method version">{viewProgram.method_version ?? "—"}</Fact>
            <Fact label="Record version">{viewProgram.version}</Fact>
          </FactGrid>
        </Modal>
      )}

      {viewSample && (
        <Modal
          open
          onClose={() => setViewSample(null)}
          large
          title={
            <span className="flex items-center gap-3">
              EM {viewSample.id.slice(0, 8)}… <WorkflowStatePill state={viewSample.state} />
            </span>
          }
        >
          <FactGrid>
            <Fact label="Monitoring type">{viewSample.monitoring_type}</Fact>
            <Fact label="Alert / action status">
              {viewSample.alert_action_status ? (
                <StatePill
                  state={viewSample.alert_action_status === "normal" ? "accepted" : "failed"}
                  icon={viewSample.alert_action_status === "normal" ? "check-circle" : "alert-triangle"}
                >
                  {viewSample.alert_action_status}
                </StatePill>
              ) : (
                "—"
              )}
            </Fact>
            <Fact label="Requires deviation">{viewSample.requires_deviation ? "Yes" : "No"}</Fact>
            <Fact label="Record version">{viewSample.version}</Fact>
            {viewSample.program_number ? (
              <Fact label="Program version">{`${viewSample.program_number} v${viewSample.program_version_no}`}</Fact>
            ) : (
              <IdFact label="Program version" value={viewSample.program_version_id} />
            )}
            {viewSample.location_code ? (
              <Fact label="Location">{viewSample.location_code}</Fact>
            ) : (
              <IdFact label="Location" value={viewSample.location_id} />
            )}
          </FactGrid>
          <JsonPanel title="Result" value={viewSample.result} />
          <div className="flex gap-2 mt-3">
            {canRecordEmResult(me) && (
              <Button
                variant="secondary"
                onClick={() =>
                  setResultPrefill({ sampleId: viewSample.id, expectedVersion: String(viewSample.version) })
                }
              >
                Record result
              </Button>
            )}
            {canReview(me) && (
              <Button variant="success" onClick={() => setReviewOpen(true)}>
                Review result (sign)
              </Button>
            )}
          </div>
        </Modal>
      )}

      {viewSample && reviewOpen && (
        <SignatureCeremony
          open
          onClose={() => setReviewOpen(false)}
          onDone={() => {
            setReviewOpen(false);
            setViewSample(null);
            setSampleReload((n) => n + 1);
          }}
          challengePath={`/em/v1/results/${viewSample.id}/signature-challenges`}
          action="review"
          title={`Review EM result - ${viewSample.id.slice(0, 8)}…`}
          summary="Independent microbiological review of this EM result, including any excursion assessment."
          submitLabel="Sign & review"
          submitVariant="success"
          reason="optional"
          onSign={(p) =>
            api.post<MutationReceipt>(`/em/v1/results/${viewSample.id}/review`, {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              sample_id: viewSample.id,
              expected_version: viewSample.version,
              reason: p.reason,
            })
          }
        />
      )}

      {viewExcursion && (
        <Modal open onClose={() => setViewExcursion(null)} title={`EM excursion ${viewExcursion.id.slice(0, 8)}…`}>
          <FactGrid>
            <Fact label="Disposition">{viewExcursion.disposition ?? "—"}</Fact>
            <Fact label="Requires deviation">{viewExcursion.requires_deviation ? "Yes" : "No"}</Fact>
            <Fact label="Impact assessed at">
              {viewExcursion.impact_assessed_at ? new Date(viewExcursion.impact_assessed_at).toLocaleString() : "—"}
            </Fact>
            {viewExcursion.sample_monitoring_type ? (
              <Fact label="Sample">{`EM ${viewExcursion.sample_id.slice(0, 8)}… - ${viewExcursion.sample_monitoring_type}`}</Fact>
            ) : (
              <IdFact label="Sample" value={viewExcursion.sample_id} />
            )}
            {viewExcursion.area_code ? (
              <Fact label="Area">{viewExcursion.area_code}</Fact>
            ) : (
              <IdFact label="Area" value={viewExcursion.area_id} />
            )}
            <Fact label="Record version">{viewExcursion.version}</Fact>
          </FactGrid>
          {canImpactExcursion(me) && !viewExcursion.impact_assessed_at && (
            <Button
              variant="secondary"
              className="mt-3"
              onClick={() =>
                setExcursionPrefill({ excursionId: viewExcursion.id, expectedVersion: String(viewExcursion.version) })
              }
            >
              Record impact
            </Button>
          )}
        </Modal>
      )}
    </div>
  );
}

function programColumns(onOpen: (p: EmProgram) => void): DataTableColumn<EmProgram>[] {
  return [
    {
      key: "program_number",
      header: "Program",
      sortable: true,
      render: (p) => (
        <span className="fs-2 font-semibold">
          {p.program_number} v{p.version_no}
        </span>
      ),
    },
    {
      key: "state",
      header: "State",
      render: (p) => (
        <StatePill state={p.state === "RELEASED" ? "accepted" : "unknown"} icon={p.state === "RELEASED" ? "check-circle" : "slash-circle"}>
          {p.state}
        </StatePill>
      ),
    },
    { key: "method_version", header: "Method version", render: (p) => <span className="fs-2">{p.method_version ?? "—"}</span> },
    {
      key: "open",
      header: "",
      align: "right",
      render: (p) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={(e) => {
            e.stopPropagation();
            onOpen(p);
          }}
        >
          View
        </Button>
      ),
    },
  ];
}

function EmProgramsListCard({ reloadToken, onOpen }: { reloadToken: number; onOpen: (p: EmProgram) => void }) {
  const fetchPrograms = pagedFetcher<EmProgram>("/em/v1/programs");
  return (
    <Card pad className="mb-4">
      <CardHeader title="EM programs" />
      <DataTable
        columns={programColumns(onOpen)}
        fetchPage={fetchPrograms}
        rowKey={(p) => p.id}
        searchPlaceholder="Search program number…"
        emptyMessage='No EM programs yet - use "New EM program" above to add one.'
        defaultSort={{ by: "created_at", dir: "desc" }}
        onRowClick={onOpen}
        reloadToken={reloadToken}
      />
    </Card>
  );
}

function sampleColumns(onOpen: (s: EmSample) => void): DataTableColumn<EmSample>[] {
  return [
    {
      key: "id",
      header: "EM sample / reading",
      render: (s) => <span className="fs-2 font-semibold">EM {s.id.slice(0, 8)}…</span>,
    },
    { key: "monitoring_type", header: "Monitoring type", render: (s) => <span className="fs-2">{s.monitoring_type}</span> },
    { key: "state", header: "State", sortable: true, render: (s) => <WorkflowStatePill state={s.state} /> },
    {
      key: "alert_action_status",
      header: "Alert / action",
      render: (s) =>
        s.alert_action_status ? (
          <StatePill
            state={s.alert_action_status === "normal" ? "accepted" : "failed"}
            icon={s.alert_action_status === "normal" ? "check-circle" : "alert-triangle"}
          >
            {s.alert_action_status}
          </StatePill>
        ) : (
          "—"
        ),
    },
    {
      key: "open",
      header: "",
      align: "right",
      render: (s) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={(e) => {
            e.stopPropagation();
            onOpen(s);
          }}
        >
          View
        </Button>
      ),
    },
  ];
}

function EmSamplesListCard({ reloadToken, onOpen }: { reloadToken: number; onOpen: (s: EmSample) => void }) {
  const fetchSamples = pagedFetcher<EmSample>("/em/v1/samples");
  return (
    <Card pad className="mb-4">
      <CardHeader title="EM samples / readings" />
      <DataTable
        columns={sampleColumns(onOpen)}
        fetchPage={fetchSamples}
        rowKey={(s) => s.id}
        searchPlaceholder="Search monitoring type…"
        emptyMessage='No EM samples/readings yet - use "Schedule EM sampling task" above to add one.'
        defaultSort={{ by: "created_at", dir: "desc" }}
        onRowClick={onOpen}
        reloadToken={reloadToken}
      />
    </Card>
  );
}

function excursionColumns(onOpen: (e: EmExcursion) => void): DataTableColumn<EmExcursion>[] {
  return [
    { key: "id", header: "EM excursion", render: (e) => <span className="fs-2 font-semibold">EM excursion {e.id.slice(0, 8)}…</span> },
    { key: "disposition", header: "Disposition", render: (e) => <span className="fs-2">{e.disposition ?? "—"}</span> },
    {
      key: "impact_assessed_at",
      header: "Impact assessed",
      render: (e) =>
        e.impact_assessed_at ? (
          <span className="tabular fs-2">{new Date(e.impact_assessed_at).toLocaleString()}</span>
        ) : (
          <StatePill state="failed" icon="alert-triangle">Pending</StatePill>
        ),
    },
    {
      key: "open",
      header: "",
      align: "right",
      render: (e) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={(ev) => {
            ev.stopPropagation();
            onOpen(e);
          }}
        >
          View
        </Button>
      ),
    },
  ];
}

function EmExcursionsListCard({ reloadToken, onOpen }: { reloadToken: number; onOpen: (e: EmExcursion) => void }) {
  const fetchExcursions = pagedFetcher<EmExcursion>("/em/v1/excursions");
  return (
    <Card pad className="mb-4">
      <CardHeader title="EM excursions" />
      <DataTable
        columns={excursionColumns(onOpen)}
        fetchPage={fetchExcursions}
        rowKey={(e) => e.id}
        searchPlaceholder="Search disposition…"
        emptyMessage="No EM excursions yet - these are created automatically when a result is recorded as an action excursion."
        defaultSort={{ by: "created_at", dir: "desc" }}
        onRowClick={onOpen}
        reloadToken={reloadToken}
      />
    </Card>
  );
}

function CreateTaskForm({ siteId, onDone }: { siteId: string | null; onDone: () => void }) {
  const { options: locationOptions, status: locationOptionsStatus } = useEmLocationOptions();
  const { options: programOptions, status: programOptionsStatus } = useEmProgramOptions();
  const { busy, error, run } = useCommand(onDone);
  const [programVersionId, setProgramVersionId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [monitoringType, setMonitoringType] = useState("viable_air");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() =>
      api.post<MutationReceipt>("/em/v1/tasks", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        program_version_id: programVersionId.trim(),
        location_id: locationId.trim(),
        monitoring_type: monitoringType.trim(),
      })
    );
  }

  return (
    <form onSubmit={submit}>
      <EntityPickerField
        label="Program version"
        required
        value={programVersionId}
        onChange={setProgramVersionId}
        options={programOptions}
        status={programOptionsStatus}
        kind="EM program"
      />
      <EntityPickerField
        label="Location"
        required
        value={locationId}
        onChange={setLocationId}
        options={locationOptions}
        status={locationOptionsStatus}
        kind="EM location"
      />
      <Field label="Monitoring type" required>
        <Input value={monitoringType} onChange={(e) => setMonitoringType(e.target.value)} required />
      </Field>
      {error && <p className="error-text mt-2">{error}</p>}
      <div className="flex justify-between gap-3 mt-3">
        <span />
        <Button type="submit" variant="primary" disabled={busy || !programVersionId.trim() || !locationId.trim()}>
          {busy ? "Scheduling…" : "Schedule task"}
        </Button>
      </div>
    </form>
  );
}

function CreateProgramForm({ siteId, onDone }: { siteId: string | null; onDone: () => void }) {
  const { busy, error, run } = useCommand(onDone);
  const [programNumber, setProgramNumber] = useState("");
  const [methodVersion, setMethodVersion] = useState("");
  const [monitoringTypes, setMonitoringTypes] = useState<KvRow[]>([]);
  const [alertLimits, setAlertLimits] = useState<KvRow[]>([]);
  const [actionLimits, setActionLimits] = useState<KvRow[]>([]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() =>
      api.post<MutationReceipt>("/em/v1/programs", {
        idempotency_key: newIdempotencyKey(),
        site_id: siteId,
        program_number: programNumber.trim(),
        method_version: methodVersion.trim() || null,
        monitoring_types: Object.keys(buildKvObject(monitoringTypes)).length ? buildKvObject(monitoringTypes) : null,
        alert_limits: Object.keys(buildKvObject(alertLimits)).length ? buildKvObject(alertLimits) : null,
        action_limits: Object.keys(buildKvObject(actionLimits)).length ? buildKvObject(actionLimits) : null,
      })
    );
  }

  return (
    <form onSubmit={submit}>
      <Field label="Program number" required>
        <Input value={programNumber} onChange={(e) => setProgramNumber(e.target.value)} required autoFocus />
      </Field>
      <Field label="Method version" hint="Optional.">
        <Input value={methodVersion} onChange={(e) => setMethodVersion(e.target.value)} />
      </Field>
      <KeyValueRows label="Monitoring types" hint='Optional, e.g. "viable_air" → "true".' value={monitoringTypes} onChange={setMonitoringTypes} />
      <KeyValueRows label="Alert limits" hint="Optional, per monitoring type." value={alertLimits} onChange={setAlertLimits} />
      <KeyValueRows label="Action limits" hint="Optional, per monitoring type." value={actionLimits} onChange={setActionLimits} />
      {error && <p className="error-text mt-2">{error}</p>}
      <div className="flex justify-between gap-3 mt-3">
        <span />
        <Button type="submit" variant="primary" disabled={busy || !programNumber.trim()}>
          {busy ? "Creating…" : "Create program"}
        </Button>
      </div>
    </form>
  );
}

function RecordExcursionImpactForm({
  initialExcursionId,
  initialExpectedVersion,
  onDone,
}: {
  initialExcursionId: string;
  initialExpectedVersion: string;
  onDone: () => void;
}) {
  const { options: excursionOptions, status: excursionOptionsStatus } = useEmExcursionOptions();
  const { busy, error, run } = useCommand(onDone);
  const [excursionId, setExcursionId] = useState(initialExcursionId);
  const [expectedVersion, setExpectedVersion] = useState(initialExpectedVersion);
  const [affectedTimeStart, setAffectedTimeStart] = useState("");
  const [affectedTimeEnd, setAffectedTimeEnd] = useState("");
  const [affectedBatchIds, setAffectedBatchIds] = useState<KvRow[]>([]);
  const [disposition, setDisposition] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() =>
      api.post<MutationReceipt>(`/em/v1/excursions/${excursionId.trim()}/impact`, {
        idempotency_key: newIdempotencyKey(),
        excursion_id: excursionId.trim(),
        expected_version: Number(expectedVersion),
        affected_time_start: affectedTimeStart ? new Date(affectedTimeStart).toISOString() : null,
        affected_time_end: affectedTimeEnd ? new Date(affectedTimeEnd).toISOString() : null,
        affected_batch_ids: Object.keys(buildKvObject(affectedBatchIds)).length ? buildKvObject(affectedBatchIds) : null,
        disposition: disposition.trim() || null,
      })
    );
  }

  return (
    <form onSubmit={submit}>
      <EntityPickerField
        label="Excursion"
        required
        hint={initialExcursionId ? "Pre-filled from the excursion you opened." : undefined}
        value={excursionId}
        onChange={setExcursionId}
        options={excursionOptions}
        status={excursionOptionsStatus}
        kind="EM excursion"
      />
      <Field label="Expected version" required>
        <Input type="number" value={expectedVersion} onChange={(e) => setExpectedVersion(e.target.value)} required />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Affected time start">
          <Input type="datetime-local" value={affectedTimeStart} onChange={(e) => setAffectedTimeStart(e.target.value)} />
        </Field>
        <Field label="Affected time end">
          <Input type="datetime-local" value={affectedTimeEnd} onChange={(e) => setAffectedTimeEnd(e.target.value)} />
        </Field>
      </div>
      <KeyValueRows
        label="Affected batches"
        hint='Optional, e.g. a batch ID → "true".'
        value={affectedBatchIds}
        onChange={setAffectedBatchIds}
      />
      <Field label="Disposition" hint="Optional.">
        <Input value={disposition} onChange={(e) => setDisposition(e.target.value)} />
      </Field>
      {error && <p className="error-text mt-2">{error}</p>}
      <div className="flex justify-between gap-3 mt-3">
        <span />
        <Button type="submit" variant="primary" disabled={busy || !excursionId.trim() || !expectedVersion.trim()}>
          {busy ? "Recording…" : "Record impact"}
        </Button>
      </div>
    </form>
  );
}

function formatResultValues(result: Record<string, unknown> | null): string {
  if (!result || Object.keys(result).length === 0) return "—";
  return Object.entries(result)
    .map(([k, v]) => `${k}: ${v}`)
    .join(", ");
}

function TrendsForm() {
  const { options: locationOptions, status: locationOptionsStatus } = useEmLocationOptions();
  const [locationId, setLocationId] = useState("");
  const [monitoringType, setMonitoringType] = useState("");
  const [trends, setTrends] = useState<EmTrends | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function lookup(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setTrends(null);
    try {
      const q = new URLSearchParams({ location_id: locationId.trim() });
      if (monitoringType.trim()) q.set("monitoring_type", monitoringType.trim());
      setTrends(await api.get<EmTrends>(`/em/v1/trends?${q.toString()}`));
    } catch {
      setError("Lookup failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {/* `items-start` (not `items-end`) because "Monitoring type"'s hint text makes that Field taller
          than "Location" — bottom-aligning would push Location's select down below Monitoring type's
          input instead of levelling the two controls. `RowButtonSlot` gives the bare Button the same
          invisible label height so it still lines up with both inputs, not their labels. */}
      <form onSubmit={lookup} className="flex flex-wrap items-start gap-3">
        <div style={{ minWidth: 220 }}>
          <EntityPickerField
            label="Location"
            required
            value={locationId}
            onChange={setLocationId}
            options={locationOptions}
            status={locationOptionsStatus}
            kind="EM location"
          />
        </div>
        <Field label="Monitoring type" hint="Optional.">
          <Input value={monitoringType} onChange={(e) => setMonitoringType(e.target.value)} />
        </Field>
        <RowButtonSlot>
          <Button type="submit" variant="secondary" disabled={busy || !locationId.trim()}>
            <Icon name="search" /> {busy ? "Loading…" : "Show trends"}
          </Button>
        </RowButtonSlot>
      </form>
      {error && <p className="error-text mt-3">{error}</p>}
      {trends && (
        <div className="mt-3">
          <div className="flex items-center justify-between mb-2">
            <span className="font-semibold fs-2">Readings</span>
            <span className="fs-2 text-muted">
              {trends.samples.length} reading{trends.samples.length === 1 ? "" : "s"}
            </span>
          </div>
          {trends.samples.length === 0 ? (
            <EmptyState icon="gauge">No readings recorded yet for this location.</EmptyState>
          ) : (
            <Table>
              <thead>
                <tr>
                  <th>Sampled at</th>
                  <th>Monitoring type</th>
                  <th>Result</th>
                  <th>Alert / action</th>
                </tr>
              </thead>
              <tbody>
                {trends.samples.map((s) => (
                  <tr key={s.id}>
                    <td className="tabular fs-2">{new Date(s.created_at).toLocaleString()}</td>
                    <td className="fs-2">{s.monitoring_type}</td>
                    <td className="fs-2">{formatResultValues(s.result)}</td>
                    <td>
                      {s.alert_action_status ? (
                        <StatePill
                          state={s.alert_action_status === "normal" ? "accepted" : "failed"}
                          icon={s.alert_action_status === "normal" ? "check-circle" : "alert-triangle"}
                        >
                          {s.alert_action_status}
                        </StatePill>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </div>
      )}
    </>
  );
}

function RecordResultForm({
  initialSampleId,
  initialExpectedVersion,
  onDone,
}: {
  initialSampleId: string;
  initialExpectedVersion: string;
  onDone: () => void;
}) {
  const { options: sampleOptions, status: sampleOptionsStatus } = useEmSampleOptions();
  const [sampleId, setSampleId] = useState(initialSampleId);
  const [expectedVersion, setExpectedVersion] = useState(initialExpectedVersion);
  const [result, setResult] = useState<KvRow[]>([{ key: "count", value: "0" }]);
  const [alertActionStatus, setAlertActionStatus] = useState("normal");
  // em_sample_or_reading/record_result requires a signature (Document 106 row 114, "Performed") -- this
  // form previously posted directly with no challenge_id/reauth_password at all, so "Record EM result"
  // always failed with MISSING_SIGNATURE (same bug class as the CAPA close/cancel fix: backend policy
  // already required a signature, only the frontend ceremony was never wired). Fixed by opening the same
  // `SignatureCeremony` this page's "Review (sign)" button already uses, closing over the fields
  // collected here rather than collecting them a second time inside the ceremony.
  const [signing, setSigning] = useState(false);

  const missingRequired = !sampleId.trim() || !expectedVersion.trim();

  return (
    <>
      <EntityPickerField
        label="Sample / reading"
        required
        hint={initialSampleId ? "Pre-filled from the sample you opened." : undefined}
        value={sampleId}
        onChange={setSampleId}
        options={sampleOptions}
        status={sampleOptionsStatus}
        kind="EM sample/reading"
      />
      <Field label="Expected version" required hint="From the sample record.">
        <Input type="number" value={expectedVersion} onChange={(e) => setExpectedVersion(e.target.value)} />
      </Field>
      <KeyValueRows label="Result" hint='The reading, e.g. "count" → 12, "unit" → cfu.' value={result} onChange={setResult} />
      <Field label="Alert / action status" required>
        <Select value={alertActionStatus} onChange={(e) => setAlertActionStatus(e.target.value)}>
          {ALERT_ACTION_STATUSES.map((s) => (
            <option key={s} value={s}>
              {humanizeLabel(s)}
            </option>
          ))}
        </Select>
      </Field>
      <div className="flex justify-between gap-3 mt-3">
        <span />
        <Button type="button" variant="primary" disabled={missingRequired} onClick={() => setSigning(true)}>
          Record result (sign)
        </Button>
      </div>
      {signing && (
        <SignatureCeremony
          open
          onClose={() => setSigning(false)}
          onDone={() => {
            setSigning(false);
            onDone();
          }}
          challengePath={`/em/v1/results/${sampleId}/signature-challenges`}
          action="record_result"
          title="Record EM result - sign"
          summary="Attests this result was recorded as read from the instrument/media."
          submitLabel="Sign & record"
          reason="none"
          onSign={(p) =>
            api.post<MutationReceipt>("/em/v1/results", {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              sample_id: sampleId.trim(),
              expected_version: Number(expectedVersion),
              result: buildKvObject(result),
              alert_action_status: alertActionStatus.trim(),
            })
          }
        />
      )}
    </>
  );
}
