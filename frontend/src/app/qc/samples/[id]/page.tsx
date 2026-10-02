"use client";

import { use, useState } from "react";
import {
  api,
  hasPermission,
  newIdempotencyKey,
  type MutationReceipt,
} from "@/lib/api";
import { useApiResource, useEntityOptions, useMe } from "@/lib/hooks";
import { RecordDetailShell, useCommand } from "@/components/shared/RecordDetailShell";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { Fact, IdFact } from "@/components/ui/FactGrid";
import { Tabs } from "@/components/ui/Tabs";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button, LinkButton } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { UomSelect } from "@/components/ui/UomSelect";
import { Icon } from "@/components/ui/Icon";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";

interface QcResultRow {
  id: string;
  outcome: string | null;
  result_version: number;
}

interface TestOrder {
  id: string;
  state: string;
  version: number;
  assigned_analyst_id: string | null;
  runs: string[];
  results: QcResultRow[];
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

type OrderAction = "start" | "complete" | "review";

export default function SampleDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const [createOrderOpen, setCreateOrderOpen] = useState(false);
  const [acting, setActing] = useState<{ order: TestOrder; action: OrderAction } | null>(null);
  const [correctingResult, setCorrectingResult] = useState<QcResultRow | null>(null);
  const [recordingData, setRecordingData] = useState<TestOrder | null>(null);
  const [recordingResult, setRecordingResult] = useState<TestOrder | null>(null);

  const canAnalyse = hasPermission(me, "qc_test_order.start");
  const canReview = hasPermission(me, "qc_test_order.review");

  const sample = useApiResource<SampleRecord>(`/qc/v1/samples/${id}/record`);
  const readinessResource = useApiResource<ReleaseReadiness>(`/qc/v1/release-readiness?sample_id=${id}`);
  // Feeds "Add test order"'s definition picker — every released spec's definitions, not just one page
  // of the browsable table on /qc (same Phase-1 "cap at 100, no site scoping" precedent as every other
  // flat picker list in this app).
  const specsForPicker = useApiResource<{ items: Specification[] }>(`/qc/v1/specifications?page_size=100`);
  const allSpecs = specsForPicker.data?.items ?? [];

  const record = sample.data;
  // Readiness is a secondary view; a failure there should not blank out the sample record itself.
  const readiness = readinessResource.error ? null : readinessResource.data;

  function reload() {
    sample.reload();
    readinessResource.reload();
  }

  return (
    <RecordDetailShell
      recordNumber={record?.sample_number ?? ""}
      state={record?.state}
      backHref="/qc"
      backLabel="QC testing"
      loading={sample.loading}
      error={sample.error}
      actions={
        record && (
          <>
            {canAnalyse && record.state === "received" && (
              <Button variant="secondary" onClick={() => setCreateOrderOpen(true)}>
                <Icon name="plus" /> Add test order
              </Button>
            )}
            {canAnalyse && (record.state === "planned" || record.state === "collected") && (
              <ReceiveButton sample={record} onDone={reload} />
            )}
          </>
        )
      }
      facts={
        record && (
          <>
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
          </>
        )
      }
    >
      {record && (
        <>
          {readiness && (
            <Banner tone={readiness.ready ? "ok" : "warn"} title={readiness.ready ? "Release ready" : "Not release ready"}>
              {readiness.ready
                ? "Every blocking test order has been reviewed."
                : readiness.blocking_test_orders.length === 0
                  ? "No blocking test orders exist on this sample, so release readiness cannot be asserted."
                  : `${readiness.blocking_test_orders.filter((o) => o.state !== "reviewed").length} blocking test order(s) not yet reviewed.`}
            </Banner>
          )}

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
                                  <div className="flex gap-1 flex-wrap items-center">
                                    {o.results.map((r) => (
                                      <span key={r.id} className="flex gap-1 items-center">
                                        <StatePill
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
                                        <Button size="sm" variant="ghost" title="Request a correction to this result" onClick={() => setCorrectingResult(r)}>
                                          <Icon name="pen" />
                                        </Button>
                                      </span>
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
                                    <LinkButton size="sm" variant="danger" href="/quality/oos">
                                      Open OOS
                                    </LinkButton>
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
                      <EmptyState icon="help-circle">No blocking test orders on this sample.</EmptyState>
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
      {correctingResult && (
        <RequestCorrectionModal
          result={correctingResult}
          onClose={() => setCorrectingResult(null)}
          onDone={() => {
            setCorrectingResult(null);
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
    </RecordDetailShell>
  );
}

function ReceiveButton({ sample, onDone }: { sample: SampleRecord; onDone: () => void }) {
  const { busy, run } = useCommand(onDone);
  return (
    <Button
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
    .flatMap((s) => s.test_definitions.map((d) => ({ value: d.id, label: `${s.spec_code} v${s.version_no} - ${d.test_code} (${d.test_name})` })));

  return (
    <Modal open onClose={onClose} title={`Add test order - ${sample.sample_number}`}>
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
            hint="No released test specification exists yet - create one on the QC testing page, or enter an id directly."
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
  const { busy, error, run } = useCommand(onDone);

  // Only second-person review is a signed act here (Document 106 row for qc_test_order.review).
  if (action === "review") {
    return (
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        challengePath={`/qc/v1/test-orders/${order.id}/signature-challenges`}
        action="review"
        title="Second-person review"
        summary="Second-person review must be performed by someone other than the analyst who produced the result - the backend enforces this."
        submitLabel="Sign & review"
        onSign={(p) =>
          api.post<MutationReceipt>(`/qc/v1/test-orders/${order.id}/review`, {
            idempotency_key: p.idempotency_key,
            test_order_id: order.id,
            expected_version: order.version,
            challenge_id: p.challenge_id,
            reauth_password: p.reauth_password,
          })
        }
      />
    );
  }

  const TITLE: Record<Exclude<OrderAction, "review">, string> = {
    start: "Start test order",
    complete: "Complete test order",
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
          run(() =>
            action === "start"
              ? api.post(`/qc/v1/test-orders/${order.id}/start`, { ...base, analyst_id: me?.user_id ?? null })
              : api.post(`/qc/v1/test-orders/${order.id}/complete`, base)
          );
        }}
      >
        <p className="fs-3 mb-3">
          {action === "start"
            ? "Starting the order records you as the analyst and opens it for raw data entry."
            : "Completing the order closes analyst entry and sends it for second-person review."}
        </p>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Saving…" : TITLE[action]}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** Starts a correction directly from the actual result row (`result.id` is already known — no more
 * hand-typing a QC result ID copied from somewhere else, same fix shape as the inventory Split
 * Container version lookup above). Approving the correction still happens separately, on
 * `/qc/page.tsx`'s signed form, since SoD requires an independent second signer who may not be the
 * person requesting it — this only carries the correction's own id forward via the mutation receipt so
 * the requester (or whoever they hand it to) doesn't have to go looking for it. */
function RequestCorrectionModal({
  result,
  onClose,
  onDone,
}: {
  result: QcResultRow;
  onClose: () => void;
  onDone: () => void;
}) {
  const [correctedDecimal, setCorrectedDecimal] = useState("");
  const [correctedText, setCorrectedText] = useState("");
  const [createdCorrectionId, setCreatedCorrectionId] = useState<string | null>(null);

  if (createdCorrectionId) {
    return (
      <Modal open onClose={onDone} title="Correction requested">
        <p className="fs-3 mb-3">
          Correction <span className="tabular font-semibold">{createdCorrectionId}</span> has been
          requested. An independent reviewer (not you) must approve it from the QC page&apos;s
          &quot;Approve a result correction&quot; form using this ID.
        </p>
        <div className="flex justify-end">
          <Button variant="primary" onClick={onDone}>
            Done
          </Button>
        </div>
      </Modal>
    );
  }

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      // Not `onDone` directly - a successful sign should show the resulting correction ID (below)
      // before this modal closes, not close immediately the way every other signed action here does.
      onDone={() => {}}
      challengePath={`/qc/v1/results/${result.id}/signature-challenges`}
      action="correct"
      title="Request a result correction"
      summary="Requesting and approving a correction are independent signatures - the approver must differ from whoever requests it (SoD)."
      submitLabel="Sign & request"
      reason="required"
      extraFields={
        <>
          <Field label="Corrected value (numeric)" hint="Fill this or the text field below, matching the result's data type.">
            <Input value={correctedDecimal} onChange={(e) => setCorrectedDecimal(e.target.value)} />
          </Field>
          <Field label="Corrected value (text)">
            <Input value={correctedText} onChange={(e) => setCorrectedText(e.target.value)} />
          </Field>
        </>
      }
      onSign={async (p) => {
        const receipt = await api.post<MutationReceipt>(`/qc/v1/results/${result.id}/correct`, {
          idempotency_key: p.idempotency_key,
          result_id: result.id,
          reason_text: p.reason,
          corrected_value_decimal: correctedDecimal || null,
          corrected_value_text: correctedText || null,
          challenge_id: p.challenge_id,
          reauth_password: p.reauth_password,
        });
        setCreatedCorrectionId(receipt.aggregate_id);
        return receipt;
      }}
    />
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
          <UomSelect value={uom} onChange={setUom} />
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
          Evaluated against the test definition&rsquo;s own acceptance rule, if one is released - otherwise the
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
