"use client";

import { useEffect, useState } from "react";
import { api, ApiError, holdsAnyRole, newIdempotencyKey } from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
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

const SAMPLE_TYPES = ["release", "stability", "in_process", "environmental", "raw_material", "retain"];
const SOURCE_TYPES = ["batch", "material_lot", "environment", "stability_study", "equipment"];

type OrderAction = "start" | "complete" | "review";

export default function QcPage() {
  const { me } = useMe();
  const [sampleId, setSampleId] = useState("");
  const [activeSample, setActiveSample] = useState<string | null>(null);
  const [createSampleOpen, setCreateSampleOpen] = useState(false);
  const [createOrderOpen, setCreateOrderOpen] = useState(false);
  const [acting, setActing] = useState<{ order: TestOrder; action: OrderAction } | null>(null);
  const [oosFrom, setOosFrom] = useState<string | null>(null);

  const canAnalyse = holdsAnyRole(me, ["Admin", "Operator", "Supervisor", "QC Reviewer"]);
  const canReview = holdsAnyRole(me, ["Admin", "QA Reviewer", "QC Reviewer"]);

  const sample = useApiResource<SampleRecord>(
    activeSample ? `/qc/v1/samples/${activeSample}/record` : null
  );
  const readinessResource = useApiResource<ReleaseReadiness>(
    activeSample ? `/qc/v1/release-readiness?sample_id=${activeSample}` : null
  );

  const record = sample.data;
  // Readiness is a secondary view; a failure there should not blank out the sample record itself.
  const readiness = readinessResource.error ? null : readinessResource.data;
  const loading = sample.loading;
  const error = sample.error;

  function reload() {
    sample.reload();
    readinessResource.reload();
  }

  return (
    <div>
      <PageHead
        title="QC testing"
        subtitle="Document 23/25 — samples, test orders, results, second-person review and OOS investigation."
        action={
          canAnalyse ? (
            <Button variant="primary" onClick={() => setCreateSampleOpen(true)}>
              <Icon name="plus" /> New sample
            </Button>
          ) : undefined
        }
      />

      <p className="hint mb-4">
        Document 23 exposes the QC record per sample rather than as a site-wide worklist, so this page
        opens one sample at a time.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setActiveSample(sampleId.trim() || null);
        }}
        className="flex items-end gap-4 mb-4"
      >
        <Field label="Sample ID">
          <Input value={sampleId} onChange={(e) => setSampleId(e.target.value)} style={{ minWidth: 340 }} />
        </Field>
        <Button type="submit" variant="secondary" disabled={loading || !sampleId.trim()}>
          <Icon name="flask" /> {loading ? "Loading…" : "Open sample"}
        </Button>
      </form>

      {error && (
        <Banner tone="critical" title="Could not load the sample">
          {error}
        </Banner>
      )}

      {record && (
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
            <div className="flex justify-between items-center mb-3">
              <span className="font-semibold">
                {record.sample_number} <WorkflowStatePill state={record.state} />
              </span>
              <div className="flex gap-2">
                {canAnalyse && record.state === "received" && (
                  <Button size="sm" variant="secondary" onClick={() => setCreateOrderOpen(true)}>
                    <Icon name="plus" /> Add test order
                  </Button>
                )}
                {canAnalyse && record.state === "created" && (
                  <ReceiveButton sample={record} onDone={reload} />
                )}
              </div>
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
                                  {canAnalyse && o.state === "in_testing" && (
                                    <Button size="sm" variant="secondary" onClick={() => setActing({ order: o, action: "start" })}>
                                      Start
                                    </Button>
                                  )}
                                  {canAnalyse && o.state === "in_progress" && (
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

      {createSampleOpen && (
        <CreateSampleModal
          onClose={() => setCreateSampleOpen(false)}
          onDone={(id) => {
            setCreateSampleOpen(false);
            setSampleId(id);
            setActiveSample(id);
          }}
        />
      )}
      {createOrderOpen && record && (
        <CreateOrderModal
          sample={record}
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
            <Select value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
              {SOURCE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <Field label="Source record ID">
          <Input value={sourceId} onChange={(e) => setSourceId(e.target.value)} />
        </Field>
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
  onClose,
  onDone,
}: {
  sample: SampleRecord;
  onClose: () => void;
  onDone: () => void;
}) {
  const { me } = useMe();
  const { busy, error, run } = useCommand(onDone);
  const [testDefinitionId, setTestDefinitionId] = useState("");
  const [analystId, setAnalystId] = useState(me?.user_id ?? "");

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
        <Field
          label="Test definition ID"
          required
          hint="From the released test specification governing this sample's scope."
        >
          <Input value={testDefinitionId} onChange={(e) => setTestDefinitionId(e.target.value)} required autoFocus />
        </Field>
        <Field label="Assigned analyst (user ID)">
          <Input value={analystId} onChange={(e) => setAnalystId(e.target.value)} />
        </Field>
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
