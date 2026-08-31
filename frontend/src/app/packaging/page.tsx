"use client";

import { useState } from "react";
import {
  api,
  canExecutePackaging,
  formatDateTime,
  newIdempotencyKey,
  pagedFetcher,
  type PackagingRun,
} from "@/lib/api";
import { useApiResource, useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Table } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";

interface LabelIssue {
  id: string;
  label_version_id: string | null;
  quantity_issued: number;
  serial_range: Record<string, unknown> | null;
  issued_by: string;
  issued_at: string;
  state: string;
}

interface LabelReconciliation {
  id: string;
  issued: number;
  applied: number;
  returned: number;
  destroyed: number;
  rejected: number;
  samples: number;
  calculated_variance: number;
  tolerance_rule: string | null;
  result: string;
  investigation_link: string | null;
  created_at: string;
}

interface PackageNode {
  id: string;
  package_level: string;
  business_ref: string | null;
  parent_package_id: string | null;
  state: string;
}

interface RunDetail extends PackagingRun {
  label_issues: LabelIssue[];
  label_reconciliations: LabelReconciliation[];
  package_nodes: PackageNode[];
}

type Action = "line_clearance" | "issue_labels" | "reconcile_labels" | "reconcile_packaging" | "complete";

const ACTION_LABEL: Record<Action, string> = {
  line_clearance: "Line clearance",
  issue_labels: "Issue labels",
  reconcile_labels: "Reconcile labels",
  reconcile_packaging: "Reconcile packaging",
  complete: "Complete run",
};

export default function PackagingPage() {
  const { me } = useMe();
  const { siteId, loading: siteLoading } = useSiteId();
  const [reloadToken, setReloadToken] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const fetchRuns = pagedFetcher<PackagingRun>("/packaging/v1/runs", () => ({ site_id: siteId ?? "" }));

  const columns: DataTableColumn<PackagingRun>[] = [
    {
      key: "line_ref",
      header: "Line",
      render: (r) => <span className="font-semibold tabular">{r.line_ref ?? "—"}</span>,
    },
    {
      key: "batch_id",
      header: "Batch",
      render: (r) => (
        <span className="tabular fs-2" style={{ wordBreak: "break-all" }}>
          {r.batch_id}
        </span>
      ),
    },
    { key: "state", header: "State", sortable: true, render: (r) => <WorkflowStatePill state={r.state} /> },
    {
      key: "line_clearance_completed",
      header: "Line clearance",
      render: (r) =>
        r.line_clearance_completed ? (
          <StatePill state="accepted" icon="check-circle">
            Complete
          </StatePill>
        ) : (
          <StatePill state="blocked" icon="lock">
            Outstanding
          </StatePill>
        ),
    },
    {
      key: "reconciliation_state",
      header: "Reconciliation",
      sortable: true,
      render: (r) => <span className="fs-2">{r.reconciliation_state}</span>,
    },
    {
      key: "started_at",
      header: "Started",
      sortable: true,
      render: (r) => <span className="tabular fs-2">{r.started_at ? formatDateTime(r.started_at) : "—"}</span>,
    },
  ];

  return (
    <div>
      <PageHead
        title="Packaging"
        subtitle="Document 16 — packaging runs, line clearance, label issue and the reconciliation gate."
        action={
          canExecutePackaging(me) ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> New run
            </Button>
          ) : undefined
        }
      />

      <Card>
        <CardHeader title="Packaging runs" />
        {/* Held until the site resolves — DataTable does not watch siteId, so mounting early would
            issue one unscoped request and never correct itself. */}
        {siteLoading ? (
          <p className="table-loading-row" style={{ padding: "var(--space-4)" }}>
            Loading…
          </p>
        ) : (
          <DataTable
            columns={columns}
            fetchPage={fetchRuns}
            rowKey={(r) => r.id}
            searchPlaceholder="Search by line reference…"
            emptyIcon="package"
            emptyMessage="No packaging runs for this site."
            defaultSort={{ by: "created_at", dir: "desc" }}
            reloadToken={reloadToken}
            onRowClick={(r) => setSelected(r.id)}
          />
        )}
      </Card>

      {createOpen && (
        <CreateRunModal
          onClose={() => setCreateOpen(false)}
          onDone={() => {
            setCreateOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
      {selected && (
        <RunModal
          runId={selected}
          onClose={() => setSelected(null)}
          onChanged={() => setReloadToken((n) => n + 1)}
        />
      )}
    </div>
  );
}

function CreateRunModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { busy, error, run } = useCommand(onDone);
  const [batchId, setBatchId] = useState("");
  const [lineRef, setLineRef] = useState("");

  return (
    <Modal open onClose={onClose} title="New packaging run">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post("/packaging/v1/runs", {
              idempotency_key: newIdempotencyKey(),
              batch_id: batchId,
              line_ref: lineRef || null,
            })
          );
        }}
      >
        <Field label="Batch ID" required>
          <Input value={batchId} onChange={(e) => setBatchId(e.target.value)} required autoFocus />
        </Field>
        <Field label="Line reference" hint="The packaging line this run occupies.">
          <Input value={lineRef} onChange={(e) => setLineRef(e.target.value)} />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !batchId.trim()}>
            {busy ? "Creating…" : "Create run"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function RunModal({
  runId,
  onClose,
  onChanged,
}: {
  runId: string;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { me } = useMe();
  const detail = useApiResource<RunDetail>(`/packaging/v1/runs/${runId}`);
  const [action, setAction] = useState<Action | null>(null);

  const r = detail.data;
  if (!r) {
    return (
      <Modal open onClose={onClose} title="Packaging run">
        {detail.error ? <p className="error-text">{detail.error}</p> : <p>Loading…</p>}
      </Modal>
    );
  }

  const canAct = canExecutePackaging(me) && r.state !== "complete";
  const latestReconciliation = r.label_reconciliations.at(-1);
  const totalIssued = r.label_issues.reduce((sum, i) => sum + i.quantity_issued, 0);

  return (
    <Modal open onClose={onClose} title={`Packaging run — ${r.line_ref ?? "unassigned line"}`} large>
      {!r.line_clearance_completed && (
        <Banner tone="warn" title="Line clearance outstanding" icon="lock">
          Labels cannot be issued until line clearance is recorded.
        </Banner>
      )}
      {latestReconciliation && latestReconciliation.result !== "pass" && (
        <Banner tone="critical" title="Label reconciliation variance">
          Variance of {latestReconciliation.calculated_variance} label(s) — result{" "}
          {latestReconciliation.result}. A run cannot complete on a failed reconciliation.
        </Banner>
      )}

      <FactGrid>
        <Fact label="State">
          <WorkflowStatePill state={r.state} />
        </Fact>
        <Fact label="Line clearance">{r.line_clearance_completed ? "Complete" : "Outstanding"}</Fact>
        <Fact label="Reconciliation">{r.reconciliation_state}</Fact>
        <Fact label="Labels issued">{totalIssued}</Fact>
        <Fact label="Package nodes">{r.package_nodes.length}</Fact>
        <Fact label="Started">{r.started_at ? formatDateTime(r.started_at) : "—"}</Fact>
        <Fact label="Ended">{r.ended_at ? formatDateTime(r.ended_at) : "—"}</Fact>
        <Fact label="Record version">{r.version}</Fact>
        <IdFact label="Batch" value={r.batch_id} />
        <IdFact label="Product version" value={r.product_version_id} />
      </FactGrid>

      <p className="fact-k mb-2 mt-4">Label issues</p>
      {r.label_issues.length === 0 ? (
        <p className="hint">No labels issued on this run.</p>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Issued</th>
              <th style={{ textAlign: "right" }}>Quantity</th>
              <th>State</th>
            </tr>
          </thead>
          <tbody>
            {r.label_issues.map((i) => (
              <tr key={i.id}>
                <td className="tabular fs-2">{formatDateTime(i.issued_at)}</td>
                <td className="tabular" style={{ textAlign: "right" }}>
                  {i.quantity_issued}
                </td>
                <td className="fs-2">{i.state}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <p className="fact-k mb-2 mt-4">Label reconciliations</p>
      {r.label_reconciliations.length === 0 ? (
        <p className="hint">No label reconciliation recorded.</p>
      ) : (
        <Table>
          <thead>
            <tr>
              <th style={{ textAlign: "right" }}>Issued</th>
              <th style={{ textAlign: "right" }}>Applied</th>
              <th style={{ textAlign: "right" }}>Returned</th>
              <th style={{ textAlign: "right" }}>Destroyed</th>
              <th style={{ textAlign: "right" }}>Rejected</th>
              <th style={{ textAlign: "right" }}>Samples</th>
              <th style={{ textAlign: "right" }}>Variance</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {r.label_reconciliations.map((rec) => (
              <tr key={rec.id}>
                <td className="tabular" style={{ textAlign: "right" }}>{rec.issued}</td>
                <td className="tabular" style={{ textAlign: "right" }}>{rec.applied}</td>
                <td className="tabular" style={{ textAlign: "right" }}>{rec.returned}</td>
                <td className="tabular" style={{ textAlign: "right" }}>{rec.destroyed}</td>
                <td className="tabular" style={{ textAlign: "right" }}>{rec.rejected}</td>
                <td className="tabular" style={{ textAlign: "right" }}>{rec.samples}</td>
                <td
                  className={rec.calculated_variance !== 0 ? "error-text tabular" : "tabular"}
                  style={{ textAlign: "right" }}
                >
                  {rec.calculated_variance}
                </td>
                <td>
                  <StatePill state={rec.result === "pass" ? "accepted" : "failed"} icon={rec.result === "pass" ? "check-circle" : "x"}>
                    {rec.result}
                  </StatePill>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {r.package_nodes.length > 0 && (
        <>
          <p className="fact-k mb-2 mt-4">Package hierarchy</p>
          <Table>
            <thead>
              <tr>
                <th>Level</th>
                <th>Reference</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {r.package_nodes.map((n) => (
                <tr key={n.id}>
                  <td>{n.package_level}</td>
                  <td className="tabular fs-2">{n.business_ref ?? "—"}</td>
                  <td className="fs-2">{n.state}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </>
      )}

      <div className="flex justify-between gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        {canAct && (
          <div className="flex gap-2 flex-wrap">
            {!r.line_clearance_completed && (
              <Button size="sm" variant="secondary" onClick={() => setAction("line_clearance")}>
                Line clearance
              </Button>
            )}
            {r.line_clearance_completed && (
              <>
                <Button size="sm" variant="secondary" onClick={() => setAction("issue_labels")}>
                  Issue labels
                </Button>
                <Button size="sm" variant="secondary" onClick={() => setAction("reconcile_labels")}>
                  Reconcile labels
                </Button>
                <Button size="sm" variant="secondary" onClick={() => setAction("reconcile_packaging")}>
                  Reconcile packaging
                </Button>
                <Button size="sm" variant="primary" onClick={() => setAction("complete")}>
                  Complete run
                </Button>
              </>
            )}
          </div>
        )}
      </div>

      {action && (
        <ActionModal
          run={r}
          action={action}
          onClose={() => setAction(null)}
          onDone={() => {
            setAction(null);
            detail.reload();
            onChanged();
          }}
        />
      )}
    </Modal>
  );
}

function ActionModal({
  run: packagingRun,
  action,
  onClose,
  onDone,
}: {
  run: RunDetail;
  action: Action;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [quantity, setQuantity] = useState("");
  const [labelCounts, setLabelCounts] = useState({
    applied: "0",
    returned: "0",
    destroyed: "0",
    rejected: "0",
    samples: "0",
  });
  const [packCounts, setPackCounts] = useState({
    components_issued: "0",
    finished_packs: "0",
    rejects: "0",
    samples: "0",
    destroyed: "0",
  });
  const [reason, setReason] = useState("");

  const base = {
    idempotency_key: newIdempotencyKey(),
    run_id: packagingRun.id,
    expected_version: packagingRun.version,
  };
  const path = `/packaging/v1/runs/${packagingRun.id}`;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() => {
      switch (action) {
        case "line_clearance":
          return api.post(`${path}/line-clearance`, { ...base, reason: reason || null });
        case "issue_labels":
          return api.post(`${path}/labels/issue`, { ...base, quantity_issued: Number(quantity) });
        case "reconcile_labels":
          return api.post(`${path}/reconcile-labels`, {
            ...base,
            ...Object.fromEntries(Object.entries(labelCounts).map(([k, v]) => [k, Number(v)])),
          });
        case "reconcile_packaging":
          return api.post(`${path}/reconcile-packaging`, {
            ...base,
            ...Object.fromEntries(Object.entries(packCounts).map(([k, v]) => [k, Number(v)])),
          });
        case "complete":
          return api.post(`${path}/complete`, base);
      }
    });
  }

  return (
    <Modal open onClose={onClose} title={ACTION_LABEL[action]} large={action.startsWith("reconcile")}>
      <form onSubmit={submit}>
        {action === "line_clearance" && (
          <Field label="Reason / notes" hint="What was verified clear before this run starts.">
            <textarea className="input" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
        )}

        {action === "issue_labels" && (
          <Field label="Quantity issued" required>
            <Input
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              required
              autoFocus
            />
          </Field>
        )}

        {action === "reconcile_labels" && (
          <>
            <p className="hint mb-3">
              Issued is taken from the run&apos;s own label issue records; account for every one of them
              here.
            </p>
            <div className="grid grid-cols-3 gap-4">
              {(["applied", "returned", "destroyed", "rejected", "samples"] as const).map((k) => (
                <Field key={k} label={k.charAt(0).toUpperCase() + k.slice(1)}>
                  <Input
                    type="number"
                    min={0}
                    value={labelCounts[k]}
                    onChange={(e) => setLabelCounts((prev) => ({ ...prev, [k]: e.target.value }))}
                  />
                </Field>
              ))}
            </div>
          </>
        )}

        {action === "reconcile_packaging" && (
          <div className="grid grid-cols-3 gap-4">
            {(["components_issued", "finished_packs", "rejects", "samples", "destroyed"] as const).map((k) => (
              <Field key={k} label={k.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())}>
                <Input
                  type="number"
                  min={0}
                  value={packCounts[k]}
                  onChange={(e) => setPackCounts((prev) => ({ ...prev, [k]: e.target.value }))}
                />
              </Field>
            ))}
          </div>
        )}

        {action === "complete" && (
          <p className="fs-3 mb-3">
            Completing the run closes it to further label issue and reconciliation. Reconciliation must
            have passed first.
          </p>
        )}

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Saving…" : ACTION_LABEL[action]}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
