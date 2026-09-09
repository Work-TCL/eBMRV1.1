"use client";

import { useEffect, useState } from "react";
import { api, ApiError, holdsAnyRole, newIdempotencyKey, pagedFetcher } from "@/lib/api";
import { useApiResource, useEntityOptions, useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Banner } from "@/components/ui/Banner";
import { Tabs } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { RepeatableRows, buildRepeatArray, type RepeatRow, type RepeatSubField } from "@/components/shared/RepeatableFields";

interface TestOrder {
  id: string;
  state: string;
  version: number;
  assigned_analyst_id: string | null;
  runs: string[];
  results: { id: string; outcome: string | null; result_version: number }[];
}

interface SampleRecord {
  id: string;
  sample_number: string;
  state: string;
  version: number;
  source_type: string;
  test_orders: TestOrder[];
}

interface ReleaseReadiness {
  sample_id: string;
  ready: boolean;
  blocking_test_orders: { id: string; state: string }[];
}

interface TestDefinition {
  id: string;
  test_code: string;
  test_name: string;
  result_data_type: string;
  uom: string | null;
}

interface Specification {
  id: string;
  spec_code: string;
  version_no: number;
  status: string;
  scope_type: string;
  scope_version_id: string;
  version: number;
  test_definitions: TestDefinition[];
}

const SAMPLE_TYPES = ["release", "stability", "in_process", "environmental", "raw_material", "retain"];
const SOURCE_TYPES = ["batch", "material_lot", "environment", "stability_study", "equipment"];
const SCOPE_TYPES = ["product", "in_process", "device"];

const TEST_DEFINITION_SUBFIELDS: RepeatSubField[] = [
  { name: "test_code", label: "Test code", required: true, placeholder: "e.g. FILL-WEIGHT" },
  { name: "test_name", label: "Test name", required: true, placeholder: "e.g. Fill weight" },
  { name: "result_data_type", label: "Result data type", required: true, placeholder: "numeric / text / pass_fail / json" },
  { name: "uom", label: "Unit of measure" },
  { name: "required", label: "Required", type: "bool", default: "true" },
  { name: "release_blocking", label: "Release blocking", type: "bool", default: "true" },
];

type OrderAction = "start" | "complete" | "review";

export default function QcPage() {
  const { me } = useMe();
  const [activeSample, setActiveSample] = useState<string | null>(null);
  const [createSampleOpen, setCreateSampleOpen] = useState(false);
  const [createOrderOpen, setCreateOrderOpen] = useState(false);
  const [acting, setActing] = useState<{ order: TestOrder; action: OrderAction } | null>(null);
  const [recordingData, setRecordingData] = useState<TestOrder | null>(null);
  const [recordingResult, setRecordingResult] = useState<TestOrder | null>(null);
  const [oosFrom, setOosFrom] = useState<string | null>(null);
  const [newSpecOpen, setNewSpecOpen] = useState(false);
  const [releasingSpec, setReleasingSpec] = useState<Specification | null>(null);
  const [specsReloadToken, setSpecsReloadToken] = useState(0);
  const [samplesReloadToken, setSamplesReloadToken] = useState(0);

  const canAnalyse = holdsAnyRole(me, ["Admin", "Operator", "Supervisor", "QC Reviewer"]);
  const canReview = holdsAnyRole(me, ["Admin", "QA Reviewer", "QC Reviewer"]);

  // Feeds "Add test order"'s definition picker — every released spec's definitions, not just one page
  // of the browsable table below (same Phase-1 "cap at 100, no site scoping" precedent as every other
  // flat picker list in this app).
  const specsForPicker = useApiResource<{ items: Specification[] }>(`/qc/v1/specifications?page_size=100`);
  const allSpecs = specsForPicker.data?.items ?? [];

  const sample = useApiResource<SampleRecord>(
    activeSample ? `/qc/v1/samples/${activeSample}/record` : null
  );
  const readinessResource = useApiResource<ReleaseReadiness>(
    activeSample ? `/qc/v1/release-readiness?sample_id=${activeSample}` : null
  );

  const record = sample.data;
  // Readiness is a secondary view; a failure there should not blank out the sample record itself.
  const readiness = readinessResource.error ? null : readinessResource.data;
  const error = sample.error;

  function reload() {
    sample.reload();
    readinessResource.reload();
  }

  return (
    <div>
      <PageHead
        title="QC testing"
        subtitle="Samples, test orders, results, second-person review and OOS investigation."
        action={
          <div className="flex gap-2">
            {canAnalyse && (
              <Button variant="secondary" onClick={() => setNewSpecOpen(true)}>
                <Icon name="plus" /> New test specification
              </Button>
            )}
            {canAnalyse && (
              <Button variant="primary" onClick={() => setCreateSampleOpen(true)}>
                <Icon name="plus" /> New sample
              </Button>
            )}
          </div>
        }
      />

      <SpecificationsCard
        canRelease={canReview}
        onRelease={setReleasingSpec}
        reloadToken={specsReloadToken}
      />

      <SamplesCard onOpen={setActiveSample} reloadToken={samplesReloadToken} />

      {activeSample && (
        <Modal
          open
          onClose={() => setActiveSample(null)}
          large
          title={
            record ? (
              <span className="flex items-center gap-3">
                {record.sample_number} <WorkflowStatePill state={record.state} />
              </span>
            ) : (
              "Loading…"
            )
          }
        >
          {error ? (
            <Banner tone="critical" title="Could not load the sample">
              {error}
            </Banner>
          ) : !record ? (
            <p className="hint">Loading…</p>
          ) : (
            <>
          {readiness && (
            <Banner
              tone={readiness.ready ? "ok" : "warn"}
              title={readiness.ready ? "Release ready" : "Not release ready"}
            >
              {readiness.ready
                ? "Every blocking test order has been reviewed."
                : readiness.blocking_test_orders.length === 0
                  ? "No blocking test orders exist on this sample, so release readiness cannot be asserted."
                  : `${readiness.blocking_test_orders.filter((o) => o.state !== "reviewed").length} blocking test order(s) not yet reviewed.`}
            </Banner>
          )}

          <Card pad className="mb-4">
            <div className="flex justify-end gap-2 mb-3">
              {canAnalyse && record.state === "received" && (
                <Button size="sm" variant="secondary" onClick={() => setCreateOrderOpen(true)}>
                  <Icon name="plus" /> Add test order
                </Button>
              )}
              {canAnalyse && (record.state === "planned" || record.state === "collected") && (
                <ReceiveButton sample={record} onDone={reload} />
              )}
            </div>
            <FactGrid>
              <Fact label="State">
                <WorkflowStatePill state={record.state} />
              </Fact>
              <Fact label="Source type">{record.source_type}</Fact>
              <Fact label="Test orders">{record.test_orders.length}</Fact>
              <Fact label="Release ready">
                {readiness ? (
                  readiness.ready ? (
                    <StatePill state="accepted" icon="check-circle">
                      Yes
                    </StatePill>
                  ) : (
                    <StatePill state="blocked" icon="lock">
                      No
                    </StatePill>
                  )
                ) : (
                  "—"
                )}
              </Fact>
              <IdFact label="Sample ID" value={record.id} />
            </FactGrid>
          </Card>

          <Tabs
            tabs={[
              {
                id: "orders",
                label: "Test orders",
                badge: record.test_orders.length || undefined,
                content:
                  record.test_orders.length === 0 ? (
                    <EmptyState icon="flask">No test orders on this sample.</EmptyState>
                  ) : (
                    <Card>
                      <CardHeader title="Test orders" />
                      <Table>
                        <thead>
                          <tr>
                            <th>Order</th>
                            <th>State</th>
                            <th>Analyst</th>
                            <th>Runs</th>
                            <th>Results</th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>
                          {record.test_orders.map((o) => (
                            <tr key={o.id}>
                              <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>
                                {o.id}
                              </td>
                              <td>
                                <WorkflowStatePill state={o.state} />
                              </td>
                              <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>
                                {o.assigned_analyst_id ?? "—"}
                              </td>
                              <td className="tabular">{o.runs.length}</td>
                              <td>
                                {o.results.length === 0 ? (
                                  <span className="text-muted">—</span>
                                ) : (
                                  <div className="flex gap-1 flex-wrap">
                                    {o.results.map((r) => (
                                      <StatePill
                                        key={r.id}
                                        state={
                                          r.outcome === "pass"
                                            ? "accepted"
                                            : r.outcome === "fail" || r.outcome === "oos"
                                              ? "failed"
                                              : "unknown"
                                        }
                                        icon={r.outcome === "pass" ? "check-circle" : "alert-triangle"}
                                      >
                                        {r.outcome ?? "recorded"}
                                      </StatePill>
                                    ))}
                                  </div>
                                )}
                              </td>
                              <td style={{ textAlign: "right" }}>
                                <div className="flex gap-2 justify-end">
                                  {canAnalyse && (o.state === "created" || o.state === "assigned") && (
                                    <Button size="sm" variant="secondary" onClick={() => setActing({ order: o, action: "start" })}>
                                      Start
                                    </Button>
                                  )}
                                  {canAnalyse && o.state === "in_progress" && (
                                    <Button size="sm" variant="secondary" onClick={() => setRecordingData(o)}>
                                      Record raw data
                                    </Button>
                                  )}
                                  {canAnalyse && o.state === "in_progress" && o.runs.length > 0 && (
                                    <Button size="sm" variant="secondary" onClick={() => setRecordingResult(o)}>
                                      Record result
                                    </Button>
                                  )}
                                  {canAnalyse && (o.state === "in_progress" || o.state === "oos_pending" || o.state === "oot_pending") && (
                                    <Button size="sm" variant="secondary" onClick={() => setActing({ order: o, action: "complete" })}>
                                      Complete
                                    </Button>
                                  )}
                                  {canReview && o.state === "analyst_complete" && (
                                    <Button size="sm" variant="secondary" onClick={() => setActing({ order: o, action: "review" })}>
                                      <Icon name="pen" /> Review
                                    </Button>
                                  )}
                                  {o.results.some((r) => r.outcome === "fail" || r.outcome === "oos") && (
                                    <Button
                                      size="sm"
                                      variant="danger"
                                      onClick={() =>
                                        setOosFrom(
                                          o.results.find((r) => r.outcome === "fail" || r.outcome === "oos")!.id
                                        )
                                      }
                                    >
                                      Open OOS
                                    </Button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    </Card>
                  ),
              },
              {
                id: "readiness",
                label: "Release readiness",
                content: (
                  <Card pad>
                    {!readiness ? (
                      <EmptyState icon="help-circle">Readiness not loaded.</EmptyState>
                    ) : readiness.blocking_test_orders.length === 0 ? (
                      <EmptyState icon="help-circle">
                        No blocking test orders on this sample.
                      </EmptyState>
                    ) : (
                      <Table>
                        <thead>
                          <tr>
                            <th>Blocking test order</th>
                            <th>State</th>
                          </tr>
                        </thead>
                        <tbody>
                          {readiness.blocking_test_orders.map((o) => (
                            <tr key={o.id}>
                              <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>
                                {o.id}
                              </td>
                              <td>
                                <WorkflowStatePill state={o.state} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    )}
                  </Card>
                ),
              },
            ]}
          />
            </>
          )}
        </Modal>
      )}

      {createSampleOpen && (
        <CreateSampleModal
          onClose={() => setCreateSampleOpen(false)}
          onDone={(id) => {
            setCreateSampleOpen(false);
            setActiveSample(id);
            setSamplesReloadToken((n) => n + 1);
          }}
        />
      )}
      {createOrderOpen && record && (
        <CreateOrderModal
          sample={record}
          specifications={allSpecs}
          onClose={() => setCreateOrderOpen(false)}
          onDone={() => {
            setCreateOrderOpen(false);
            reload();
          }}
        />
      )}
      {newSpecOpen && (
        <NewSpecificationModal
          onClose={() => setNewSpecOpen(false)}
          onDone={() => {
            setNewSpecOpen(false);
            setSpecsReloadToken((n) => n + 1);
            specsForPicker.reload();
          }}
        />
      )}
      {releasingSpec && (
        <ReleaseSpecificationModal
          specification={releasingSpec}
          onClose={() => setReleasingSpec(null)}
          onDone={() => {
            setReleasingSpec(null);
            setSpecsReloadToken((n) => n + 1);
            specsForPicker.reload();
          }}
        />
      )}
      {acting && (
        <OrderActionModal
          order={acting.order}
          action={acting.action}
          onClose={() => setActing(null)}
          onDone={() => {
            setActing(null);
            reload();
          }}
        />
      )}
      {recordingData && (
        <RecordRawDataModal
          order={recordingData}
          onClose={() => setRecordingData(null)}
          onDone={() => {
            setRecordingData(null);
            reload();
          }}
        />
      )}
      {recordingResult && (
        <RecordResultModal
          order={recordingResult}
          onClose={() => setRecordingResult(null)}
          onDone={() => {
            setRecordingResult(null);
            reload();
          }}
        />
      )}
      {oosFrom && (
        <OpenOosModal
          resultId={oosFrom}
          onClose={() => setOosFrom(null)}
          onDone={() => {
            setOosFrom(null);
            reload();
          }}
        />
      )}
    </div>
  );
}

function ReceiveButton({ sample, onDone }: { sample: SampleRecord; onDone: () => void }) {
  const { busy, run } = useCommand(onDone);
  return (
    <Button
      size="sm"
      variant="secondary"
      disabled={busy}
      onClick={() =>
        run(() =>
          api.post(`/qc/v1/samples/${sample.id}/receive`, {
            idempotency_key: newIdempotencyKey(),
            sample_id: sample.id,
            expected_version: sample.version,
          })
        )
      }
    >
      Receive sample
    </Button>
  );
}

function CreateSampleModal({ onClose, onDone }: { onClose: () => void; onDone: (id: string) => void }) {
  const [createdId, setCreatedId] = useState("");
  const { busy, error, run } = useCommand(() => onDone(createdId));
  const [sampleNumber, setSampleNumber] = useState("");
  const [sampleType, setSampleType] = useState(SAMPLE_TYPES[0]);
  const [sourceType, setSourceType] = useState(SOURCE_TYPES[0]);
  const [sourceId, setSourceId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [uom, setUom] = useState("g");
  const entities = useEntityOptions();

  return (
    <Modal open onClose={onClose} title="Create a QC sample" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(async () => {
            const receipt = await api.post<{ aggregate_id: string }>("/qc/v1/samples", {
              idempotency_key: newIdempotencyKey(),
              sample_number: sampleNumber,
              sample_type: sampleType,
              source_type: sourceType,
              source_id: sourceId || null,
              sample_quantity: quantity || null,
              sample_uom: uom || null,
            });
            setCreatedId(receipt.aggregate_id);
            return receipt;
          });
        }}
      >
        <div className="grid grid-cols-3 gap-4">
          <Field label="Sample number" required>
            <Input value={sampleNumber} onChange={(e) => setSampleNumber(e.target.value)} required autoFocus />
          </Field>
          <Field label="Sample type" required>
            <Select value={sampleType} onChange={(e) => setSampleType(e.target.value)}>
              {SAMPLE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Source type" required>
            <Select
              value={sourceType}
              // An id picked/typed for one source kind (a batch id, say) is meaningless once the kind
              // changes — clear it along with the switch rather than silently keep the stale value while
              // showing an unrelated picker (or the same generic text box, which is what made this look
              // like "nothing changed" before the picker branches below existed).
              onChange={(e) => {
                setSourceType(e.target.value);
                setSourceId("");
              }}
            >
              {SOURCE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        {sourceType === "batch" ? (
          <EntityPickerField
            label="Source record"
            hint="The batch this sample was drawn from."
            value={sourceId}
            onChange={setSourceId}
            options={entities.batches}
            status={entities.batchesStatus}
            kind="batch"
          />
        ) : sourceType === "material_lot" ? (
          <EntityPickerField
            label="Source record"
            hint="The material lot this sample was drawn from."
            value={sourceId}
            onChange={setSourceId}
            options={entities.materialLots}
            status={entities.materialLotsStatus}
            kind="material lot"
          />
        ) : sourceType === "equipment" ? (
          <EntityPickerField
            label="Source record"
            hint="The equipment asset this sample was drawn from."
            value={sourceId}
            onChange={setSourceId}
            options={entities.equipment}
            status={entities.equipmentStatus}
            kind="equipment asset"
          />
        ) : (
          <Field
            label="Source reference"
            hint="No record list exists for this source type yet (environment/stability study) — enter a free-text reference."
          >
            <Input value={sourceId} onChange={(e) => setSourceId(e.target.value)} />
          </Field>
        )}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Sample quantity">
            <Input type="number" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </Field>
          <Field label="UOM">
            <Input value={uom} onChange={(e) => setUom(e.target.value)} />
          </Field>
        </div>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !sampleNumber.trim()}>
            {busy ? "Creating…" : "Create sample"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function CreateOrderModal({
  sample,
  specifications,
  onClose,
  onDone,
}: {
  sample: SampleRecord;
  /** RELEASED specs only get filtered in below — create_test_order itself rejects a definition whose
   * specification isn't released (TestSpecNotEffectiveError), so an unreleased one is never a valid
   * choice here. */
  specifications: Specification[];
  onClose: () => void;
  onDone: () => void;
}) {
  const { me } = useMe();
  const { busy, error, run } = useCommand(onDone);
  const entities = useEntityOptions();
  const [testDefinitionId, setTestDefinitionId] = useState("");
  const [analystId, setAnalystId] = useState(me?.user_id ?? "");

  const definitionOptions = specifications
    .filter((s) => s.status === "released")
    .flatMap((s) => s.test_definitions.map((d) => ({ value: d.id, label: `${s.spec_code} v${s.version_no} — ${d.test_code} (${d.test_name})` })));

  return (
    <Modal open onClose={onClose} title={`Add test order — ${sample.sample_number}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post("/qc/v1/test-orders", {
              idempotency_key: newIdempotencyKey(),
              sample_id: sample.id,
              test_definition_id: testDefinitionId,
              assigned_analyst_id: analystId || null,
            })
          );
        }}
      >
        {definitionOptions.length > 0 ? (
          <EntityPickerField
            label="Test definition"
            required
            hint="From a released test specification governing this sample's scope."
            value={testDefinitionId}
            onChange={setTestDefinitionId}
            options={definitionOptions}
            status="ready"
            kind="test definition"
          />
        ) : (
          <Field
            label="Test definition ID"
            required
            hint="No released test specification exists yet — use “New test specification” above, or enter an id directly."
          >
            <Input value={testDefinitionId} onChange={(e) => setTestDefinitionId(e.target.value)} required autoFocus />
          </Field>
        )}
        <EntityPickerField
          label="Assigned analyst"
          value={analystId}
          onChange={setAnalystId}
          options={entities.users}
          status={entities.usersStatus}
          kind="user"
        />
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !testDefinitionId.trim()}>
            {busy ? "Creating…" : "Add test order"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function OrderActionModal({
  order,
  action,
  onClose,
  onDone,
}: {
  order: TestOrder;
  action: OrderAction;
  onClose: () => void;
  onDone: () => void;
}) {
  const { me } = useMe();
  const { busy, error, setError, run } = useCommand(onDone);
  const [password, setPassword] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [meaning, setMeaning] = useState("");

  // Only second-person review is a signed act here (Document 106 row for qc_test_order.review).
  const signed = action === "review";

  useEffect(() => {
    if (!signed) return;
    let cancelled = false;
    api
      .post<{ challenge_id: string; meaning: string }>(
        `/qc/v1/test-orders/${order.id}/signature-challenges`,
        { action: "review" }
      )
      .then((c) => {
        if (cancelled) return;
        setChallengeId(c.challenge_id);
        setMeaning(c.meaning);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not request a signature challenge");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [order.id, signed, setError]);

  const TITLE: Record<OrderAction, string> = {
    start: "Start test order",
    complete: "Complete test order",
    review: "Second-person review",
  };

  return (
    <Modal open onClose={onClose} title={TITLE[action]}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const base = {
            idempotency_key: newIdempotencyKey(),
            test_order_id: order.id,
            expected_version: order.version,
          };
          run(() => {
            if (action === "start") {
              return api.post(`/qc/v1/test-orders/${order.id}/start`, {
                ...base,
                analyst_id: me?.user_id ?? null,
              });
            }
            if (action === "complete") {
              return api.post(`/qc/v1/test-orders/${order.id}/complete`, base);
            }
            return api.post(`/qc/v1/test-orders/${order.id}/review`, {
              ...base,
              challenge_id: challengeId,
              reauth_password: password,
            });
          });
        }}
      >
        {signed && (
          <>
            {meaning && (
              <p className="fs-3 mb-2">
                Meaning: <span className="font-semibold">{meaning}</span>
              </p>
            )}
            <div className="sig-hint mb-3">
              Second-person review must be performed by someone other than the analyst who produced the
              result — the backend enforces this.
            </div>
            <Field label="Password" required>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </Field>
          </>
        )}
        {!signed && (
          <p className="fs-3 mb-3">
            {action === "start"
              ? "Starting the order records you as the analyst and opens it for raw data entry."
              : "Completing the order closes analyst entry and sends it for second-person review."}
          </p>
        )}
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || (signed && (!challengeId || !password))}>
            {busy ? "Saving…" : TITLE[action]}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** QC-FR-013..017: creates the `qc_test_run` a result must attach to — required, not optional, despite
 * "Record raw data" sounding like an add-on: `record_result` rejects without a real `test_run_id`, and
 * this is the only command that creates one. */
function RecordRawDataModal({
  order,
  onClose,
  onDone,
}: {
  order: TestOrder;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [methodVersion, setMethodVersion] = useState("");
  const [instrumentRef, setInstrumentRef] = useState("");
  const [sampleAmount, setSampleAmount] = useState("");

  return (
    <Modal open onClose={onClose} title="Record raw data">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/qc/v1/test-orders/${order.id}/raw-data`, {
              idempotency_key: newIdempotencyKey(),
              test_order_id: order.id,
              method_version: methodVersion || null,
              instrument_ref: instrumentRef || null,
              sample_amount: sampleAmount || null,
            })
          );
        }}
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Method version">
            <Input value={methodVersion} onChange={(e) => setMethodVersion(e.target.value)} placeholder="e.g. HPLC-METHOD-001 v2" autoFocus />
          </Field>
          <Field label="Instrument reference">
            <Input value={instrumentRef} onChange={(e) => setInstrumentRef(e.target.value)} placeholder="e.g. HPLC-04" />
          </Field>
        </div>
        <Field label="Sample amount">
          <Input type="number" step="any" value={sampleAmount} onChange={(e) => setSampleAmount(e.target.value)} />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Recording…" : "Record raw data"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** QC-FR-018..020/025/026/032/033: the actual `qc_result` INSERT — creates the row every DDCP
 * `qc_record_reference` picker (and every OOS/OOT investigation) ultimately resolves back to. Attaches
 * to whichever `test_run_id` "Record raw data" created (a Select if more than one run exists, otherwise
 * used directly — most orders have exactly one). */
function RecordResultModal({
  order,
  onClose,
  onDone,
}: {
  order: TestOrder;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [testRunId, setTestRunId] = useState(order.runs[0] ?? "");
  const [resultType, setResultType] = useState("numeric");
  const [valueDecimal, setValueDecimal] = useState("");
  const [valueText, setValueText] = useState("");
  const [uom, setUom] = useState("");

  return (
    <Modal open onClose={onClose} title="Record result">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/qc/v1/test-orders/${order.id}/results`, {
              idempotency_key: newIdempotencyKey(),
              test_order_id: order.id,
              test_run_id: testRunId,
              result_type: resultType,
              value_decimal: resultType === "numeric" ? valueDecimal || null : null,
              value_text: resultType !== "numeric" ? valueText || null : null,
              uom: uom || null,
            })
          );
        }}
      >
        {order.runs.length > 1 && (
          <Field label="Test run" required>
            <Select value={testRunId} onChange={(e) => setTestRunId(e.target.value)}>
              {order.runs.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </Select>
          </Field>
        )}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Result type" required>
            <Select value={resultType} onChange={(e) => setResultType(e.target.value)}>
              <option value="numeric">numeric</option>
              <option value="text">text</option>
              <option value="pass_fail">pass_fail</option>
            </Select>
          </Field>
          <Field label="UOM">
            <Input value={uom} onChange={(e) => setUom(e.target.value)} placeholder="e.g. mL" />
          </Field>
        </div>
        {resultType === "numeric" ? (
          <Field label="Value" required>
            <Input type="number" step="any" value={valueDecimal} onChange={(e) => setValueDecimal(e.target.value)} required autoFocus />
          </Field>
        ) : (
          <Field label="Value" required>
            <Input value={valueText} onChange={(e) => setValueText(e.target.value)} required autoFocus />
          </Field>
        )}
        <p className="hint mb-2">
          Evaluated against the test definition&rsquo;s own acceptance rule, if one is released — otherwise the
          result stays &ldquo;pending&rdquo;, a normal outcome, not an error.
        </p>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !testRunId || (resultType === "numeric" ? !valueDecimal.trim() : !valueText.trim())}>
            {busy ? "Recording…" : "Record result"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function OpenOosModal({
  resultId,
  onClose,
  onDone,
}: {
  resultId: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [oosNumber, setOosNumber] = useState("");
  const [severity, setSeverity] = useState("major");

  return (
    <Modal open onClose={onClose} title="Open an OOS investigation">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/oos/v1/from-result/${resultId}`, {
              idempotency_key: newIdempotencyKey(),
              source_result_id: resultId,
              oos_number: oosNumber,
              severity,
            })
          );
        }}
      >
        <Banner tone="warn" title="An OOS result cannot simply be retested">
          211.192 requires a documented investigation before any retest or resample decision.
        </Banner>
        <Field label="OOS number" required>
          <Input value={oosNumber} onChange={(e) => setOosNumber(e.target.value)} placeholder="OOS-0001" required autoFocus />
        </Field>
        <Field label="Severity" required>
          <Select value={severity} onChange={(e) => setSeverity(e.target.value)}>
            <option value="critical">critical</option>
            <option value="major">major</option>
            <option value="minor">minor</option>
          </Select>
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="danger" disabled={busy || !oosNumber.trim()}>
            {busy ? "Opening…" : "Open OOS"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** Browsable list for /qc's own "test specifications" section — previously no way to see what
 * specifications/definitions existed at all, only author one blind via a direct API call (no UI existed
 * to create or release one either). A released specification's definitions are what "Add test order"
 * above picks from, and what every DDCP "QC result" field ultimately resolves back through. */
function specificationColumns(canRelease: boolean, onRelease: (spec: Specification) => void): DataTableColumn<Specification>[] {
  return [
    {
      key: "spec_code",
      header: "Spec code",
      sortable: true,
      render: (s) => <span className="fs-2 font-semibold">{s.spec_code} v{s.version_no}</span>,
    },
    { key: "scope_type", header: "Scope", render: (s) => <span className="fs-2">{s.scope_type}</span> },
    { key: "status", header: "State", render: (s) => <WorkflowStatePill state={s.status} /> },
    { key: "definitions", header: "Definitions", render: (s) => <span className="tabular">{s.test_definitions.length}</span> },
    {
      key: "release",
      header: "",
      align: "right",
      render: (s) =>
        canRelease && s.status === "draft" ? (
          <Button
            size="sm"
            variant="success"
            onClick={(e) => {
              e.stopPropagation();
              onRelease(s);
            }}
          >
            <Icon name="pen" /> Release
          </Button>
        ) : null,
    },
  ];
}

/** Browsable list for /qc's own "Test specifications" section — previously no way to see what
 * specifications/definitions existed at all, only author one blind via a direct API call (no UI existed
 * to create or release one either). A released specification's definitions are what "Add test order"
 * above picks from, and what every DDCP "QC result" field ultimately resolves back through. */
function SpecificationsCard({
  canRelease,
  onRelease,
  reloadToken,
}: {
  canRelease: boolean;
  onRelease: (spec: Specification) => void;
  reloadToken: number;
}) {
  const fetchSpecs = pagedFetcher<Specification>("/qc/v1/specifications");
  return (
    <Card pad className="mb-4">
      <CardHeader title="Test specifications" meta="" />
      <DataTable
        columns={specificationColumns(canRelease, onRelease)}
        fetchPage={fetchSpecs}
        rowKey={(s) => s.id}
        searchPlaceholder="Search spec code…"
        emptyIcon="flask"
        emptyMessage='No test specifications yet — use "New test specification" above to add one.'
        defaultSort={{ by: "created_at", dir: "desc" }}
        reloadToken={reloadToken}
      />
    </Card>
  );
}

/** Browsable list for /qc's own "Samples" section — previously no way to see what samples existed at
 * all, only open one already-known by id (the removed "Sample ID" lookup box). */
function SamplesCard({
  onOpen,
  reloadToken,
}: {
  onOpen: (id: string) => void;
  reloadToken: number;
}) {
  const fetchSamples = pagedFetcher<{ id: string; sample_number: string; sample_type: string; source_type: string; state: string }>(
    "/qc/v1/samples",
  );
  const columns: DataTableColumn<{ id: string; sample_number: string; sample_type: string; source_type: string; state: string }>[] = [
    { key: "sample_number", header: "Sample number", sortable: true, render: (s) => <span className="fs-2 font-semibold">{s.sample_number}</span> },
    { key: "sample_type", header: "Sample type", render: (s) => <span className="fs-2">{s.sample_type}</span> },
    { key: "source_type", header: "Source type", render: (s) => <span className="fs-2">{s.source_type}</span> },
    { key: "state", header: "State", render: (s) => <WorkflowStatePill state={s.state} /> },
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
            onOpen(s.id);
          }}
        >
          Open
        </Button>
      ),
    },
  ];
  return (
    <Card pad className="mb-4">
      <CardHeader title="Samples" meta="" />
      <DataTable
        columns={columns}
        fetchPage={fetchSamples}
        rowKey={(s) => s.id}
        searchPlaceholder="Search sample number…"
        emptyIcon="flask"
        emptyMessage='No samples yet — use "New sample" above to add one.'
        defaultSort={{ by: "created_at", dir: "desc" }}
        onRowClick={(s) => onOpen(s.id)}
        reloadToken={reloadToken}
      />
    </Card>
  );
}

function NewSpecificationModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { busy, error, run } = useCommand(onDone);
  const [specCode, setSpecCode] = useState("");
  const [scopeType, setScopeType] = useState("product");
  const [scopeVersionId, setScopeVersionId] = useState("");
  const [definitions, setDefinitions] = useState<RepeatRow[]>([]);

  return (
    <Modal open onClose={onClose} title="New test specification" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post("/qc/v1/specifications/drafts", {
              idempotency_key: newIdempotencyKey(),
              spec_code: specCode,
              scope_type: scopeType,
              scope_version_id: scopeVersionId,
              test_definitions: buildRepeatArray(TEST_DEFINITION_SUBFIELDS, definitions),
            })
          );
        }}
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Spec code" required>
            <Input value={specCode} onChange={(e) => setSpecCode(e.target.value)} placeholder="e.g. QC-SPEC-PFS-001" required autoFocus />
          </Field>
          <Field label="Scope type" required>
            <Select value={scopeType} onChange={(e) => setScopeType(e.target.value)}>
              {SCOPE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <Field
          label="Scope version ID"
          required
          hint={
            scopeType === "product"
              ? "The product version this specification governs — find it on /product-master."
              : scopeType === "in_process"
                ? "The recipe version this specification governs — find it on /recipe-master."
                : "The device version this specification governs."
          }
        >
          <Input value={scopeVersionId} onChange={(e) => setScopeVersionId(e.target.value)} required />
        </Field>
        <RepeatableRows
          label="Test definitions"
          itemLabel="Test definition"
          hint="Every test this specification defines — at least one is required for a test order to ever be created against it."
          subFields={TEST_DEFINITION_SUBFIELDS}
          value={definitions}
          onChange={setDefinitions}
        />
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !specCode.trim() || !scopeVersionId.trim() || definitions.length === 0}>
            {busy ? "Creating…" : "Create draft"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ReleaseSpecificationModal({
  specification,
  onClose,
  onDone,
}: {
  specification: Specification;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, setError, run } = useCommand(onDone);
  const [password, setPassword] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [meaning, setMeaning] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .post<{ challenge_id: string; meaning: string }>(
        `/qc/v1/specifications/${specification.id}/signature-challenges`,
        { action: "release" }
      )
      .then((c) => {
        if (cancelled) return;
        setChallengeId(c.challenge_id);
        setMeaning(c.meaning);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not request a signature challenge");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [specification.id, setError]);

  return (
    <Modal open onClose={onClose} title={`Release — ${specification.spec_code} v${specification.version_no}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/qc/v1/specifications/${specification.id}/release`, {
              idempotency_key: newIdempotencyKey(),
              specification_id: specification.id,
              expected_version: specification.version,
              challenge_id: challengeId,
              reauth_password: password,
            })
          );
        }}
      >
        {meaning && (
          <p className="fs-3 mb-2">
            Meaning: <span className="font-semibold">{meaning}</span>
          </p>
        )}
        <p className="fs-3 mb-3">
          Releasing makes every test definition on this specification usable for a real test order — this
          cannot be undone by unreleasing it.
        </p>
        <Field label="Password" required>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="success" disabled={busy || !challengeId || !password}>
            {busy ? "Releasing…" : "Release"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
