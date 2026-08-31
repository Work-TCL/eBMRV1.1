"use client";

import { useState } from "react";
import Link from "next/link";
import { api, formatDateTime, holdsAnyRole, newIdempotencyKey } from "@/lib/api";
import { useApiResource, useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { KpiRow, KpiTile } from "@/components/ui/KpiTile";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";

interface GxpBatch {
  batch_id: string;
  site_id: string;
  batch_number: string;
  product_version_id: string;
  recipe_version_id: string;
  recipe_vault_object_id: string | null;
  execution_snapshot_id: string | null;
  target_qty: string;
  target_uom: string;
  state: string;
  version: number;
  production_order_ref: string | null;
  issued_at: string | null;
  started_at: string | null;
}

interface BatchStep {
  step_id: string;
  batch_id: string;
  recipe_step_code: string;
  state: string;
  version: number;
  assigned_subject_id: string | null;
  started_at: string | null;
}

interface ExecutionView {
  batch: GxpBatch;
  steps: BatchStep[];
  blockers: unknown;
}

const BATCH_STATES = ["planned", "issued", "in_progress", "on_hold", "aborted", "complete"];

type Action = "issue" | "start" | "hold" | "resume" | "abort";

const ACTION_LABEL: Record<Action, string> = {
  issue: "Issue batch",
  start: "Start batch",
  hold: "Hold",
  resume: "Resume",
  abort: "Abort",
};

const ALLOWED_FROM: Record<string, Action[]> = {
  planned: ["issue"],
  issued: ["start", "abort"],
  in_progress: ["hold", "abort"],
  on_hold: ["resume", "abort"],
};

export default function BatchExecutionPage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [state, setState] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const list = useApiResource<{ batches: GxpBatch[]; on_hold_count: number }>(
    siteId ? `/batches/v1?site_id=${siteId}${state ? `&state=${state}` : ""}&_=${reloadToken}` : null
  );

  const canCreate = holdsAnyRole(me, ["Admin", "Supervisor"]);
  const batches = list.data?.batches ?? [];
  const active = batches.filter((b) => b.state === "in_progress").length;

  return (
    <div>
      <PageHead
        title="Batch execution"
        subtitle="Document 11 — the released-recipe execution record: issue, start, hold, resume and step progress."
        action={
          canCreate ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> New batch
            </Button>
          ) : undefined
        }
      />

      <p className="hint mb-4">
        This is the Document 11 execution record (<code>gxp_batch</code>), a separate aggregate from the
        legacy <Link href="/batches">Batches</Link> page — the two are not yet wired together. Bottleneck and
        operator-assignment analytics are not built; see SG-048.
      </p>

      <KpiRow>
        <KpiTile label="Batches" icon="flask" value={batches.length} />
        <KpiTile label="In progress" icon="play" value={active} tone="ok" />
        <KpiTile
          label="On hold"
          icon="lock"
          value={list.data?.on_hold_count ?? 0}
          delta={(list.data?.on_hold_count ?? 0) > 0 ? "Execution stopped" : "None held"}
          tone={(list.data?.on_hold_count ?? 0) > 0 ? "critical" : "ok"}
        />
      </KpiRow>

      {list.error && (
        <Banner tone="critical" title="Could not load batches">
          {list.error}
        </Banner>
      )}

      <Card>
        <CardHeader
          title="Batches"
          meta={
            <span className="flex items-center gap-2">
              State
              <Select
                value={state}
                onChange={(e) => {
                  setState(e.target.value);
                  setReloadToken((n) => n + 1);
                }}
              >
                <option value="">All</option>
                {BATCH_STATES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </span>
          }
        />
        {batches.length === 0 ? (
          <EmptyState icon="flask">No Document 11 batches at this site.</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Batch</th>
                <th>Target</th>
                <th>State</th>
                <th>Issued</th>
                <th>Started</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {batches.map((b) => (
                <tr key={b.batch_id}>
                  <td className="font-semibold tabular">{b.batch_number}</td>
                  <td className="tabular fs-2">
                    {b.target_qty} {b.target_uom}
                  </td>
                  <td>
                    <WorkflowStatePill state={b.state} />
                  </td>
                  <td className="tabular fs-2">{b.issued_at ? formatDateTime(b.issued_at) : "—"}</td>
                  <td className="tabular fs-2">{b.started_at ? formatDateTime(b.started_at) : "—"}</td>
                  <td style={{ textAlign: "right" }}>
                    <Button size="sm" variant="secondary" onClick={() => setSelected(b.batch_id)}>
                      Open
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {createOpen && (
        <CreateBatchModal
          siteId={siteId}
          onClose={() => setCreateOpen(false)}
          onDone={() => {
            setCreateOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
      {selected && (
        <ExecutionModal
          batchId={selected}
          onClose={() => setSelected(null)}
          onChanged={() => setReloadToken((n) => n + 1)}
        />
      )}
    </div>
  );
}

function CreateBatchModal({
  siteId,
  onClose,
  onDone,
}: {
  siteId: string | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [batchNumber, setBatchNumber] = useState("");
  const [productVersionId, setProductVersionId] = useState("");
  const [recipeVersionId, setRecipeVersionId] = useState("");
  const [targetQty, setTargetQty] = useState("");
  const [targetUom, setTargetUom] = useState("kg");
  const [orderRef, setOrderRef] = useState("");

  return (
    <Modal open onClose={onClose} title="New batch (Document 11)" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!siteId) return;
          run(() =>
            api.post("/batches/v1", {
              idempotency_key: newIdempotencyKey(),
              site_id: siteId,
              batch_number: batchNumber,
              product_version_id: productVersionId,
              recipe_version_id: recipeVersionId,
              target_qty: targetQty,
              target_uom: targetUom,
              production_order_ref: orderRef || null,
            })
          );
        }}
      >
        <p className="hint mb-3">
          Both versions must be released — the backend refuses to create a batch against a draft product
          or recipe version.
        </p>
        <Field label="Batch number" required>
          <Input value={batchNumber} onChange={(e) => setBatchNumber(e.target.value)} required autoFocus />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Product version ID" required>
            <Input value={productVersionId} onChange={(e) => setProductVersionId(e.target.value)} required />
          </Field>
          <Field label="Recipe version ID" required>
            <Input value={recipeVersionId} onChange={(e) => setRecipeVersionId(e.target.value)} required />
          </Field>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Target quantity" required>
            <Input type="number" step="any" value={targetQty} onChange={(e) => setTargetQty(e.target.value)} required />
          </Field>
          <Field label="UOM" required>
            <Input value={targetUom} onChange={(e) => setTargetUom(e.target.value)} required />
          </Field>
          <Field label="Production order ref">
            <Input value={orderRef} onChange={(e) => setOrderRef(e.target.value)} />
          </Field>
        </div>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !batchNumber.trim() || !siteId}>
            {busy ? "Creating…" : "Create batch"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ExecutionModal({
  batchId,
  onClose,
  onChanged,
}: {
  batchId: string;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { me } = useMe();
  const view = useApiResource<ExecutionView>(`/batches/v1/${batchId}/execution-view`);
  const [action, setAction] = useState<Action | null>(null);
  const [startingStep, setStartingStep] = useState<BatchStep | null>(null);

  const v = view.data;
  if (!v) {
    return (
      <Modal open onClose={onClose} title="Batch execution">
        {view.error ? <p className="error-text">{view.error}</p> : <p>Loading…</p>}
      </Modal>
    );
  }

  const b = v.batch;
  const allowed = ALLOWED_FROM[b.state] ?? [];
  const canExecute = holdsAnyRole(me, ["Admin", "Operator", "Supervisor"]);
  const canIssue = holdsAnyRole(me, ["Admin", "Supervisor"]);
  const hasBlockers =
    Array.isArray(v.blockers) ? v.blockers.length > 0 : !!v.blockers && Object.keys(v.blockers).length > 0;

  function offered(a: Action): boolean {
    if (!allowed.includes(a)) return false;
    return a === "issue" ? canIssue : canExecute;
  }

  return (
    <Modal open onClose={onClose} title={`Batch ${b.batch_number}`} large>
      {b.state === "on_hold" && (
        <Banner tone="critical" title="Batch is on hold" icon="lock">
          Execution is stopped. No step can be started until the batch is resumed.
        </Banner>
      )}
      {hasBlockers && (
        <Banner tone="warn" title="Execution blockers">
          Conditions below prevent this batch progressing.
        </Banner>
      )}

      <FactGrid>
        <Fact label="State">
          <WorkflowStatePill state={b.state} />
        </Fact>
        <Fact label="Target">
          <span className="tabular">
            {b.target_qty} {b.target_uom}
          </span>
        </Fact>
        <Fact label="Steps">
          {v.steps.filter((s) => s.state === "complete" || s.state === "completed").length} of {v.steps.length}{" "}
          complete
        </Fact>
        <Fact label="Issued">{b.issued_at ? formatDateTime(b.issued_at) : "—"}</Fact>
        <Fact label="Started">{b.started_at ? formatDateTime(b.started_at) : "—"}</Fact>
        <Fact label="Production order">{b.production_order_ref ?? "—"}</Fact>
        <Fact label="Record version">{b.version}</Fact>
        <IdFact label="Batch ID" value={b.batch_id} />
        <IdFact label="Product version" value={b.product_version_id} />
        <IdFact label="Recipe version" value={b.recipe_version_id} />
        <IdFact label="Recipe vault object" value={b.recipe_vault_object_id} />
        <IdFact label="Execution snapshot" value={b.execution_snapshot_id} />
      </FactGrid>

      <div className="mt-4">
        <JsonPanel title="Blockers" value={v.blockers} />
      </div>

      <p className="fact-k mb-2 mt-4">Steps</p>
      {v.steps.length === 0 ? (
        <p className="hint">
          No step instances yet — they are created when the batch is issued.
        </p>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Step</th>
              <th>State</th>
              <th>Assigned</th>
              <th>Started</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {v.steps.map((s) => (
              <tr key={s.step_id}>
                <td className="font-semibold tabular">{s.recipe_step_code}</td>
                <td>
                  <WorkflowStatePill state={s.state} />
                </td>
                <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>
                  {s.assigned_subject_id ?? "—"}
                </td>
                <td className="tabular fs-2">{s.started_at ? formatDateTime(s.started_at) : "—"}</td>
                <td style={{ textAlign: "right" }}>
                  {canExecute && b.state === "in_progress" && s.state !== "in_progress" && s.state !== "complete" && (
                    <Button size="sm" variant="secondary" onClick={() => setStartingStep(s)}>
                      <Icon name="play" /> Start
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <div className="flex justify-between gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        <div className="flex gap-2 flex-wrap">
          {(Object.keys(ACTION_LABEL) as Action[]).filter(offered).map((a) => (
            <Button
              key={a}
              size="sm"
              variant={a === "abort" ? "danger" : a === "hold" ? "secondary" : "primary"}
              onClick={() => setAction(a)}
            >
              {ACTION_LABEL[a]}
            </Button>
          ))}
        </div>
      </div>

      {action && (
        <BatchActionModal
          batch={b}
          action={action}
          onClose={() => setAction(null)}
          onDone={() => {
            setAction(null);
            view.reload();
            onChanged();
          }}
        />
      )}
      {startingStep && (
        <StartStepModal
          batch={b}
          step={startingStep}
          onClose={() => setStartingStep(null)}
          onDone={() => {
            setStartingStep(null);
            view.reload();
            onChanged();
          }}
        />
      )}
    </Modal>
  );
}

function BatchActionModal({
  batch,
  action,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  action: Action;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [reason, setReason] = useState("");

  const PATH: Record<Action, string> = {
    issue: "issue",
    start: "start",
    hold: "hold",
    resume: "resume",
    abort: "abort",
  };

  return (
    <Modal open onClose={onClose} title={`${ACTION_LABEL[action]} — ${batch.batch_number}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/batches/v1/${batch.batch_id}/${PATH[action]}`, {
              idempotency_key: newIdempotencyKey(),
              batch_id: batch.batch_id,
              expected_version: batch.version,
              // The issue command takes no reason; the transition commands all accept one.
              ...(action === "issue" ? {} : { reason: reason || null }),
            })
          );
        }}
      >
        {action === "issue" && (
          <p className="fs-3 mb-3">
            Issuing freezes the recipe into an execution snapshot and creates this batch&apos;s step
            instances. The snapshot, not the live recipe, governs execution from here.
          </p>
        )}
        {action === "abort" && (
          <Banner tone="critical" title="Aborting is final">
            An aborted batch cannot be resumed. Material already consumed stays consumed and must be
            reconciled.
          </Banner>
        )}

        {action !== "issue" && (
          <Field
            label="Reason"
            required={action === "hold" || action === "abort"}
            hint="Part of the permanent batch record."
          >
            <textarea
              className="input"
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required={action === "hold" || action === "abort"}
            />
          </Field>
        )}

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant={action === "abort" ? "danger" : "primary"} disabled={busy}>
            {busy ? "Saving…" : ACTION_LABEL[action]}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function StartStepModal({
  batch,
  step,
  onClose,
  onDone,
}: {
  batch: GxpBatch;
  step: BatchStep;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);

  return (
    <Modal open onClose={onClose} title={`Start step ${step.recipe_step_code}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/batches/v1/${batch.batch_id}/steps/${step.step_id}/start`, {
              idempotency_key: newIdempotencyKey(),
              batch_id: batch.batch_id,
              step_id: step.step_id,
              expected_version: step.version,
            })
          );
        }}
      >
        <p className="fs-3 mb-3">
          Starting a step claims it for you and records the start time. Your qualification for this step is
          checked by the backend.
        </p>
        <FactGrid>
          <Fact label="Step">{step.recipe_step_code}</Fact>
          <Fact label="Current state">
            <StatePill state="missing" icon="clock">
              {step.state}
            </StatePill>
          </Fact>
        </FactGrid>
        {error && <p className="error-text mt-3 mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            <Icon name="play" /> {busy ? "Starting…" : "Start step"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
