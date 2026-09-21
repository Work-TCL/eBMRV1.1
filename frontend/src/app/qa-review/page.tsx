"use client";

import { useState } from "react";
import {
  api,
  canExecuteQaReview,
  formatDateTime,
  newIdempotencyKey,
} from "@/lib/api";
import { useApiResource, useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { KpiRow, KpiTile } from "@/components/ui/KpiTile";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";

interface ReviewPackage {
  package_id: string;
  site_id: string;
  batch_id: string;
  batch_version: number;
  record_hash: string;
  exception_index_version: number;
  completeness_status: string;
  state: string;
  version: number;
  completed_at: string | null;
  stale?: boolean;
}

// GET /batches/v1 — same shape batch-execution's picker reads; only the fields the create-package
// dropdown needs are declared here.
interface BatchOption {
  batch_id: string;
  batch_number: string;
  product_name: string | null;
  product_code: string | null;
  state: string;
}

interface Exceptions {
  package_id: string;
  batch_id: string;
  corrections: unknown[];
  integrity_check: Record<string, unknown> | null;
  batch_on_hold: boolean;
  // 2026-09-19: QC/materials/environment (hard blockers) and QC/environment/packaging (non-blocking
  // warnings) - see app/modules/qa_review/service.py::_extra_signals. Plain strings, not the structured
  // {code,message_key,...} shape /release/v1 uses - qa_review's blocker list has always been list[str].
  blockers: string[];
  warnings: string[];
}

// qa_review/models.py::QA_REVIEW_STATES — the real state vocabulary. The previous OPEN/IN_REVIEW/COMPLETE
// list never matched a real package row, so the state filter always returned zero rows and the "COMPLETE"
// checks below always evaluated false (the actual bug behind the live INVALID_TRANSITION report: "Complete
// review" stayed visible and clickable on an already-REVIEW_COMPLETE package).
const PACKAGE_STATES = ["READY_FOR_REVIEW", "REVIEW_COMPLETE", "REOPENED"];

export default function QaReviewPage() {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [state, setState] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const dashboard = useApiResource<{ packages: ReviewPackage[] }>(
    siteId ? `/qa-review/v1/dashboard?site_id=${siteId}${state ? `&state=${state}` : ""}&_=${reloadToken}` : null
  );

  const packages = dashboard.data?.packages ?? [];
  const complete = packages.filter((p) => p.state === "REVIEW_COMPLETE").length;
  const incomplete = packages.filter((p) => p.completeness_status !== "complete").length;

  return (
    <div>
      <PageHead
        title="QA review"
        subtitle="Batch review packages, their exception index and completeness gate."
        action={
          canExecuteQaReview(me) ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> New review package
            </Button>
          ) : undefined
        }
      />

      <KpiRow>
        <KpiTile label="Packages" icon="clipboard" value={packages.length} />
        <KpiTile label="Complete" icon="check-circle" value={complete} tone="ok" />
        <KpiTile
          label="Incomplete record"
          icon="alert-triangle"
          value={incomplete}
          delta={incomplete > 0 ? "Cannot complete review until resolved" : "All records complete"}
          tone={incomplete > 0 ? "warn" : "ok"}
        />
      </KpiRow>

      <p className="hint mb-4">
        Exception-class and review-age filtering are not available yet. State filtering is the part
        available today.
      </p>

      {dashboard.error && (
        <Banner tone="critical" title="Could not load the review dashboard">
          {dashboard.error}
        </Banner>
      )}

      <Card>
        <CardHeader
          title="Review packages"
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
                {PACKAGE_STATES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </span>
          }
        />
        {packages.length === 0 ? (
          <EmptyState icon="clipboard">No review packages for this site.</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Batch</th>
                <th>State</th>
                <th>Completeness</th>
                <th>Index version</th>
                <th>Completed</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {packages.map((p) => (
                <tr key={p.package_id}>
                  <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>
                    {p.batch_id}
                  </td>
                  <td>
                    <WorkflowStatePill state={p.state} />
                  </td>
                  <td>
                    {p.completeness_status === "complete" ? (
                      <StatePill state="accepted" icon="check-circle">
                        Complete
                      </StatePill>
                    ) : (
                      <StatePill state="conflict" icon="alert-triangle">
                        {p.completeness_status}
                      </StatePill>
                    )}
                  </td>
                  <td className="tabular fs-2">v{p.exception_index_version}</td>
                  <td className="tabular fs-2">{p.completed_at ? formatDateTime(p.completed_at) : "—"}</td>
                  <td style={{ textAlign: "right" }}>
                    <Button size="sm" variant="secondary" onClick={() => setSelected(p.package_id)}>
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
        <CreatePackageModal
          siteId={siteId}
          onClose={() => setCreateOpen(false)}
          onDone={() => {
            setCreateOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
      {selected && (
        <PackageModal
          packageId={selected}
          onClose={() => setSelected(null)}
          onChanged={() => setReloadToken((n) => n + 1)}
        />
      )}
    </div>
  );
}

function CreatePackageModal({
  siteId,
  onClose,
  onDone,
}: {
  siteId: string | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [batchId, setBatchId] = useState("");

  const { data: batchList, loading: batchesLoading, error: batchesError } = useApiResource<{ batches: BatchOption[] }>(
    siteId ? `/batches/v1?site_id=${siteId}` : null
  );
  const batches = batchList?.batches ?? [];

  return (
    <Modal open onClose={onClose} title="Create a review package">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/qa-review/v1/batches/${batchId}/packages`, {
              idempotency_key: newIdempotencyKey(),
              batch_id: batchId,
            })
          );
        }}
      >
        <Field
          label="Batch"
          required
          hint="The package snapshots the batch at its current version; a later batch change marks it stale."
        >
          <Select value={batchId} onChange={(e) => setBatchId(e.target.value)} disabled={batchesLoading} required autoFocus>
            <option value="">
              {batchesError ? "Could not load batches" : batchesLoading ? "Loading…" : batches.length ? "Select a batch…" : "No batches at this site"}
            </option>
            {batches.map((b) => (
              <option key={b.batch_id} value={b.batch_id}>
                {b.batch_number} - {b.product_name ? `${b.product_name} (${b.product_code})` : b.batch_id} · {b.state}
              </option>
            ))}
          </Select>
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !batchId.trim()}>
            {busy ? "Creating…" : "Create package"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function PackageModal({
  packageId,
  onClose,
  onChanged,
}: {
  packageId: string;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { me } = useMe();
  const pkg = useApiResource<ReviewPackage>(`/qa-review/v1/packages/${packageId}`);
  const exceptions = useApiResource<Exceptions>(`/qa-review/v1/packages/${packageId}/exceptions`);
  const { busy, error, run } = useCommand(() => {
    pkg.reload();
    exceptions.reload();
    onChanged();
  });
  const [signing, setSigning] = useState(false);

  const p = pkg.data;
  const e = exceptions.data;

  if (!p) {
    return (
      <Modal open onClose={onClose} title="Review package">
        {pkg.error ? <p className="error-text">{pkg.error}</p> : <p>Loading…</p>}
      </Modal>
    );
  }

  const canAct = canExecuteQaReview(me);
  const integrityOk = e?.integrity_check
    ? (e.integrity_check as { valid?: boolean; ok?: boolean }).valid ??
      (e.integrity_check as { ok?: boolean }).ok ??
      null
    : null;

  return (
    <Modal open onClose={onClose} title="Review package" large>
      {p.stale && (
        <Banner tone="warn" title="Package is stale">
          The batch has changed since this package was indexed (batch version {p.batch_version}). Reindex
          before completing the review.
        </Banner>
      )}
      {e?.batch_on_hold && (
        <Banner tone="critical" title="Batch is on hold" icon="lock">
          A batch on hold cannot have its review completed.
        </Banner>
      )}
      {integrityOk === false && (
        <Banner tone="critical" title="Execution snapshot failed integrity verification">
          The Vault object backing this batch does not match its recorded hash.
        </Banner>
      )}
      {e && e.blockers.length > 0 && (
        <Banner tone="critical" title={`${e.blockers.length} blocker(s) prevent completing this review`}>
          {e.blockers.join(" · ")}
        </Banner>
      )}
      {e && e.warnings.length > 0 && (
        <Banner tone="warn" title={`${e.warnings.length} warning(s) - visible, does not block review`}>
          {e.warnings.join(" · ")}
        </Banner>
      )}

      <FactGrid>
        <Fact label="State">
          <WorkflowStatePill state={p.state} />
        </Fact>
        <Fact label="Completeness">{p.completeness_status}</Fact>
        <Fact label="Batch version">{p.batch_version}</Fact>
        <Fact label="Index version">v{p.exception_index_version}</Fact>
        <Fact label="Completed">{p.completed_at ? formatDateTime(p.completed_at) : "—"}</Fact>
        <Fact label="Record version">{p.version}</Fact>
        <IdFact label="Batch" value={p.batch_id} />
        <IdFact label="Record hash" value={p.record_hash} />
      </FactGrid>

      <div className="mt-4">
        <JsonPanel title="Integrity check" value={e?.integrity_check} />
        <p className="fact-k mb-2">Corrections in this batch</p>
        {!e || e.corrections.length === 0 ? (
          <p className="hint">No corrections recorded against this batch.</p>
        ) : (
          <JsonPanel title="" value={e.corrections} />
        )}
      </div>

      {error && <p className="error-text mt-3">{error}</p>}

      <div className="flex justify-between gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        <div className="flex gap-2">
          {/* reindex_review_package() works from any state (models.py QA_REVIEW_STATES: READY_FOR_REVIEW/
             REVIEW_COMPLETE/REOPENED - there is no "COMPLETE") - including REVIEW_COMPLETE, where a
             changed batch reopens it. Never state-gated on the backend, so not gated here. */}
          {canAct && (
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() =>
                run(() =>
                  api.post(`/qa-review/v1/packages/${p.package_id}/reindex`, {
                    idempotency_key: newIdempotencyKey(),
                    package_id: p.package_id,
                    expected_version: p.version,
                  })
                )
              }
            >
              <Icon name="refresh" /> Reindex
            </Button>
          )}
          {/* Only READY_FOR_REVIEW/REOPENED allow completing (ALLOWED_TRANSITIONS) - offering this once
             already REVIEW_COMPLETE is exactly what produced the live INVALID_TRANSITION report: the old
             `p.state !== "COMPLETE"` check compared against a state string this module never uses. */}
          {canAct && p.state !== "REVIEW_COMPLETE" && (
            <Button variant="primary" disabled={busy} onClick={() => setSigning(true)}>
              <Icon name="pen" /> Complete review
            </Button>
          )}
        </div>
      </div>

      {signing && (
        <SignatureCeremony
          open
          onClose={() => setSigning(false)}
          onDone={() => {
            setSigning(false);
            pkg.reload();
            exceptions.reload();
            onChanged();
          }}
          challengePath={`/qa-review/v1/packages/${p.package_id}/signature-challenges`}
          action="complete"
          title={`Complete review - batch ${p.batch_id}`}
          summary="Marks this batch's QA review package complete. Requires your signature."
          submitLabel="Sign & complete review"
          onSign={(sig) =>
            api.post(`/qa-review/v1/packages/${p.package_id}/complete`, {
              idempotency_key: sig.idempotency_key,
              package_id: p.package_id,
              expected_version: p.version,
              challenge_id: sig.challenge_id,
              reauth_password: sig.reauth_password,
            })
          }
        />
      )}
    </Modal>
  );
}
