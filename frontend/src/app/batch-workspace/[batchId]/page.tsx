"use client";

import { use } from "react";
import { formatDate, formatDateTime } from "@/lib/api";
import { useApiResource } from "@/lib/hooks";
import { RecordDetailShell } from "@/components/shared/RecordDetailShell";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { LinkButton } from "@/components/ui/Button";
import { Fact, IdFact } from "@/components/ui/FactGrid";
import { Icon } from "@/components/ui/Icon";
import { BoolPill, StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { Stepper, StepItem, type StepMarkerState } from "@/components/ui/Stepper";

// Batch Workspace -- one read-only contextual dashboard over a batch's production flow, Materials/Lots,
// QC, Equipment, Sterile/Aseptic, Deviations/CAPA, and Release status, reading the single aggregation
// endpoint GET /batches/{id}/workspace (app/modules/batch_execution/record_service.py::get_batch_workspace).
// Every section here is read-only -- the real action for anything shown lives on the linked page ("no new
// business authority, no duplicated actions" scope this was built to); the step wizard below is a richer
// read-only view of the same step data batch-execution's own page already shows, not a new mutation path.

interface WorkspaceStep {
  step_id: string;
  recipe_step_code: string;
  state: string;
  required_role_code: string | null;
  started_at: string | null;
  completed_at: string | null;
  predecessor_codes: string[];
  successor_codes: string[];
}

interface WorkspaceMaterial {
  material_consumption_id: string;
  material_lot_id: string | null;
  internal_lot: string | null;
  quantity: string;
  uom: string;
  issued_at: string;
}

interface WorkspaceEquipmentUse {
  id: string;
  equipment_asset_id: string;
  equipment_code: string | null;
  log_type: string;
  occurred_at: string;
}

interface WorkspaceQcResult {
  sample_id: string;
  sample_number: string;
  test_code: string;
  order_state: string;
  outcome: string | null;
  value: string | null;
}

interface WorkspaceDeviation {
  id: string;
  deviation_number: string;
  deviation_type: string;
  state: string;
}

interface WorkspaceCapa {
  id: string;
  capa_number: string;
  state: string;
  risk_class: string;
}

interface WorkspaceAsepticOperation {
  id: string;
  state: string;
  area_id: string;
  area_code: string | null;
  created_at: string;
}

interface WorkspaceSterilizationCycle {
  id: string;
  state: string;
  process_type: string;
  equipment_id: string;
  equipment_code: string | null;
  created_at: string;
}

interface Workspace {
  batch: {
    id: string;
    batch_number: string;
    state: string;
    site_code: string | null;
    site_name: string | null;
    product_name: string | null;
    product_code: string | null;
    recipe_code: string | null;
    recipe_version_no: number | null;
    target_qty: string;
    target_uom: string;
    issued_at: string | null;
    started_at: string | null;
    production_completed_at: string | null;
    closed_at: string | null;
  };
  steps: WorkspaceStep[];
  materials_consumed: WorkspaceMaterial[];
  equipment_used: WorkspaceEquipmentUse[];
  qc_results: WorkspaceQcResult[];
  deviations: WorkspaceDeviation[];
  capas: WorkspaceCapa[];
  aseptic_operations: WorkspaceAsepticOperation[];
  sterilization_cycles: WorkspaceSterilizationCycle[];
  qa_review_package: { package_id: string; state: string; completeness_status: string } | null;
  release: { scope_id: string | null; eligible: boolean | null; blockers: string[]; warnings: string[] };
}

// Maps the batch step's real state (app/modules/batch_execution/models.py) onto the Stepper's 5-value
// marker vocabulary. "pending" here means "blocked on a predecessor", which the Stepper's own "pending"
// marker (grey, unstyled) already reads correctly as "not reachable yet".
function stepMarkerState(step: WorkspaceStep): StepMarkerState {
  if (step.state === "complete" || step.state === "completed") return "completed";
  if (step.state === "in_progress") return "current";
  if (step.state === "on_hold") return "blocked";
  if (step.state === "ready") return "available";
  return "pending";
}

function stepMeta(step: WorkspaceStep): string {
  const parts: string[] = [];
  if (step.state === "pending" && step.predecessor_codes.length > 0) {
    parts.push(`Waiting on ${step.predecessor_codes.join(", ")}`);
  }
  if (step.required_role_code) parts.push(`Required role: ${step.required_role_code}`);
  if (step.completed_at) parts.push(`Completed ${formatDate(step.completed_at)}`);
  else if (step.started_at) parts.push(`Started ${formatDate(step.started_at)}`);
  return parts.join(" · ") || "Not started";
}

export default function BatchWorkspacePage({ params }: { params: Promise<{ batchId: string }> }) {
  const { batchId } = use(params);
  const { data, loading, error } = useApiResource<Workspace>(`/batches/v1/${batchId}/workspace`);

  return (
    <RecordDetailShell
      recordNumber={data?.batch.batch_number ?? ""}
      state={data?.batch.state}
      subtitle="Read-only summary of this batch's production flow, quality signals and release status."
      backHref="/batch-execution"
      backLabel="Batch execution"
      loading={loading}
      error={error}
      actions={
        data && (
          <>
            <LinkButton href="/release" size="sm" variant="secondary">
              Release <Icon name="arrow-right" />
            </LinkButton>
            <LinkButton href="/qa-review" size="sm" variant="secondary">
              QA review <Icon name="arrow-right" />
            </LinkButton>
            <LinkButton href={`/batch-execution/${data.batch.id}`} variant="primary">
              Open batch <Icon name="arrow-right" />
            </LinkButton>
          </>
        )
      }
      facts={
        data && (
          <>
            <Fact label="Product">
              {data.batch.product_code ?? "—"}
              {data.batch.product_name ? ` — ${data.batch.product_name}` : ""}
            </Fact>
            <Fact label="Recipe">
              {data.batch.recipe_code ?? "—"}
              {data.batch.recipe_version_no ? ` v${data.batch.recipe_version_no}` : ""}
            </Fact>
            <Fact label="Site">
              {data.batch.site_code ?? "—"}
              {data.batch.site_name ? ` — ${data.batch.site_name}` : ""}
            </Fact>
            <Fact label="Target quantity">
              {data.batch.target_qty} {data.batch.target_uom}
            </Fact>
            <Fact label="Release">
              {data.release.scope_id ? (
                <BoolPill
                  value={data.release.eligible === true}
                  trueLabel="Eligible"
                  falseLabel={data.release.eligible === false ? "Blocked" : "Pending"}
                />
              ) : (
                <span className="fs-2 text-muted">Not yet evaluated</span>
              )}
            </Fact>
            <Fact label="QA review">
              {data.qa_review_package ? (
                <WorkflowStatePill state={data.qa_review_package.state} />
              ) : (
                <span className="fs-2 text-muted">Not started</span>
              )}
            </Fact>
            <Fact label="Issued">{data.batch.issued_at ? formatDateTime(data.batch.issued_at) : "—"}</Fact>
            <Fact label="Started">{data.batch.started_at ? formatDateTime(data.batch.started_at) : "—"}</Fact>
            <Fact label="Production complete">
              {data.batch.production_completed_at ? formatDateTime(data.batch.production_completed_at) : "—"}
            </Fact>
            <IdFact label="Batch ID" value={data.batch.id} />
          </>
        )
      }
    >
      {data && (
        <>
          {data.release.blockers.length > 0 && (
            <div className="mb-4">
              <Banner tone="critical" title={`${data.release.blockers.length} release blocker(s)`}>
                {data.release.blockers.join(" · ")}
              </Banner>
            </div>
          )}
          {data.release.warnings.length > 0 && (
            <div className="mb-4">
              <Banner tone="warn" title={`${data.release.warnings.length} release warning(s)`}>
                {data.release.warnings.join(" · ")}
              </Banner>
            </div>
          )}

          <Card pad className="mb-4">
            <CardHeader title="Production flow" meta={`${data.steps.filter((s) => stepMarkerState(s) === "completed").length} of ${data.steps.length} steps complete`} />
            {data.steps.length === 0 ? (
              <EmptyState icon="list">No step instances yet — created when the batch is issued.</EmptyState>
            ) : (
              <Stepper>
                {data.steps.map((s, i) => (
                  <StepItem key={s.step_id} number={i + 1} state={stepMarkerState(s)} title={s.recipe_step_code} meta={stepMeta(s)} />
                ))}
              </Stepper>
            )}
          </Card>

          <div className="grid grid-cols-2 gap-4">
            <Card pad>
              <CardHeader title="Materials & lots" meta={`${data.materials_consumed.length} consumption record(s)`} />
              {data.materials_consumed.length === 0 ? (
                <EmptyState icon="package">No material consumption recorded yet.</EmptyState>
              ) : (
                <Table>
                  <thead>
                    <tr>
                      <th>Lot</th>
                      <th>Quantity</th>
                      <th>Issued</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.materials_consumed.map((m) => (
                      <tr key={m.material_consumption_id}>
                        <td className="fs-2 tabular">{m.internal_lot ?? "—"}</td>
                        <td className="fs-2 tabular">
                          {m.quantity} {m.uom}
                        </td>
                        <td className="fs-2 tabular">{formatDate(m.issued_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
              <div className="mt-3">
                <LinkButton href="/material-lots" size="sm" variant="secondary">
                  Material lots <Icon name="arrow-right" />
                </LinkButton>
              </div>
            </Card>

            <Card pad>
              <CardHeader title="QC" meta={`${data.qc_results.length} result(s)`} />
              {data.qc_results.length === 0 ? (
                <EmptyState icon="flask">No QC results recorded yet.</EmptyState>
              ) : (
                <Table>
                  <thead>
                    <tr>
                      <th>Test</th>
                      <th>State</th>
                      <th>Outcome</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.qc_results.map((r) => (
                      <tr key={`${r.sample_id}-${r.test_code}`}>
                        <td className="fs-2">{r.test_code}</td>
                        <td>
                          <WorkflowStatePill state={r.order_state} />
                        </td>
                        <td>
                          {r.outcome ? (
                            <StatePill
                              state={r.outcome === "pass" ? "accepted" : r.outcome === "fail" || r.outcome === "oos" ? "failed" : "unknown"}
                              icon={r.outcome === "pass" ? "check-circle" : "alert-triangle"}
                            >
                              {r.outcome}
                            </StatePill>
                          ) : (
                            <span className="text-muted">pending</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
              <div className="mt-3">
                <LinkButton href="/qc" size="sm" variant="secondary">
                  QC testing <Icon name="arrow-right" />
                </LinkButton>
              </div>
            </Card>

            <Card pad>
              <CardHeader title="Equipment" meta={`${data.equipment_used.length} use log entries`} />
              {data.equipment_used.length === 0 ? (
                <EmptyState icon="tool">No equipment usage recorded yet.</EmptyState>
              ) : (
                <Table>
                  <thead>
                    <tr>
                      <th>Asset</th>
                      <th>Type</th>
                      <th>When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.equipment_used.map((u) => (
                      <tr key={u.id}>
                        <td className="fs-2 tabular" style={{ wordBreak: "break-all" }}>
                          {u.equipment_code ?? u.equipment_asset_id}
                        </td>
                        <td className="fs-2">{u.log_type}</td>
                        <td className="fs-2 tabular">{formatDate(u.occurred_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
              <div className="mt-3">
                <LinkButton href="/equipment" size="sm" variant="secondary">
                  Equipment <Icon name="arrow-right" />
                </LinkButton>
              </div>
            </Card>

            <Card pad>
              <CardHeader
                title="Sterile / aseptic"
                meta={`${data.aseptic_operations.length} aseptic op(s) · ${data.sterilization_cycles.length} cycle(s)`}
              />
              {data.aseptic_operations.length === 0 && data.sterilization_cycles.length === 0 ? (
                <EmptyState icon="shield">No aseptic or sterilization activity tied to this batch.</EmptyState>
              ) : (
                <Table>
                  <thead>
                    <tr>
                      <th>Kind</th>
                      <th>Location</th>
                      <th>State</th>
                      <th>When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.aseptic_operations.map((o) => (
                      <tr key={o.id}>
                        <td className="fs-2">Aseptic operation</td>
                        <td className="fs-2 tabular">{o.area_code ?? o.area_id}</td>
                        <td>
                          <WorkflowStatePill state={o.state} />
                        </td>
                        <td className="fs-2 tabular">{formatDate(o.created_at)}</td>
                      </tr>
                    ))}
                    {data.sterilization_cycles.map((c) => (
                      <tr key={c.id}>
                        <td className="fs-2">Sterilization ({c.process_type})</td>
                        <td className="fs-2 tabular">{c.equipment_code ?? c.equipment_id}</td>
                        <td>
                          <WorkflowStatePill state={c.state} />
                        </td>
                        <td className="fs-2 tabular">{formatDate(c.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
              <div className="mt-3 flex gap-2">
                <LinkButton href="/aseptic" size="sm" variant="secondary">
                  Aseptic
                </LinkButton>
                <LinkButton href="/sterilization" size="sm" variant="secondary">
                  Sterilization
                </LinkButton>
              </div>
            </Card>

            <Card pad>
              <CardHeader title="Deviations & CAPA" meta={`${data.deviations.length} deviation(s) · ${data.capas.length} CAPA(s)`} />
              {data.deviations.length === 0 && data.capas.length === 0 ? (
                <EmptyState icon="alert-triangle">No deviations or CAPAs raised against this batch.</EmptyState>
              ) : (
                <ul className="record-list">
                  {data.deviations.map((d) => (
                    <li key={d.id}>
                      <span className="record-list-label tabular">{d.deviation_number}</span>
                      <WorkflowStatePill state={d.state} />
                    </li>
                  ))}
                  {data.capas.map((c) => (
                    <li key={c.id}>
                      <span className="record-list-label tabular">{c.capa_number}</span>
                      <WorkflowStatePill state={c.state} />
                    </li>
                  ))}
                </ul>
              )}
              <div className="mt-3 flex gap-2">
                <LinkButton href="/deviations" size="sm" variant="secondary">
                  Deviations
                </LinkButton>
                <LinkButton href="/capa" size="sm" variant="secondary">
                  CAPA
                </LinkButton>
              </div>
            </Card>
          </div>
        </>
      )}
    </RecordDetailShell>
  );
}
