"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  api,
  ApiError,
  newIdempotencyKey,
  type BatchDetail,
  type BatchStepDetail,
  type MaterialIssueRecord,
  type MaterialLot,
  type MutationReceipt,
} from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Banner } from "@/components/ui/Banner";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { BatchStatePill } from "@/components/ui/StatePill";
import { Stepper, StepItem, type StepMarkerState } from "@/components/ui/Stepper";
import { ContextBar } from "@/components/layout/ContextBar";

type PendingAction =
  | { kind: "complete_step"; step: BatchStepDetail }
  | { kind: "review" }
  | { kind: "release" };

const STEP_MARKER_STATE: Record<string, StepMarkerState> = {
  pending: "pending",
  ready: "available",
  in_progress: "current",
  completed: "completed",
  skipped: "blocked",
};

export default function BatchDetailPage() {
  const params = useParams<{ id: string }>();
  const batchId = params.id;
  const { me } = useMe();

  const [batch, setBatch] = useState<BatchDetail | null>(null);
  const [materialIssues, setMaterialIssues] = useState<MaterialIssueRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [issueMaterialOpen, setIssueMaterialOpen] = useState(false);

  const refresh = useCallback(() => {
    api.get<BatchDetail>(`/batches/${batchId}`).then(setBatch);
    api.get<MaterialIssueRecord[]>(`/batches/${batchId}/material-issues`).then(setMaterialIssues);
  }, [batchId]);

  useEffect(refresh, [refresh]);

  const myRoles = me?.roles_by_site?.[batch?.site_id ?? ""] ?? [];

  async function run<T>(action: () => Promise<T>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  if (!batch) return <p className="fs-3 text-muted">Loading…</p>;

  const canIssue = batch.status === "planned";
  const canSubmitForReview = batch.status === "production_complete";
  const canReview = batch.status === "qa_review";
  const canRelease = batch.status === "qa_review";

  return (
    <div>
      <ContextBar
        items={[
          { k: "Batch", v: batch.batch_number },
          { k: "Quantity", v: `${batch.target_quantity} ${batch.uom}` },
          { k: "Signed in", v: me?.username ?? "…" },
        ]}
      />

      <PageHead
        title={`Batch ${batch.batch_number}`}
        subtitle={
          <span className="flex items-center gap-3 mt-1">
            <BatchStatePill status={batch.status} />
            <span className="fs-2 text-muted">version {batch.version}</span>
          </span>
        }
      />

      {error && (
        <Banner tone="critical" title="Action refused">
          {error}
        </Banner>
      )}

      <div className="flex gap-3 mt-4 mb-5">
        {canIssue && (
          <Button
            variant="primary"
            disabled={busy}
            onClick={() =>
              run(() =>
                api.post<MutationReceipt>(`/batches/${batch.id}/issue`, {
                  idempotency_key: newIdempotencyKey(),
                  batch_id: batch.id,
                  expected_version: batch.version,
                })
              )
            }
          >
            <Icon name="play" /> Issue batch
          </Button>
        )}
        {canSubmitForReview && (
          <Button
            variant="primary"
            disabled={busy}
            onClick={() =>
              run(() =>
                api.post<MutationReceipt>(`/batches/${batch.id}/submit-for-review`, {
                  idempotency_key: newIdempotencyKey(),
                  batch_id: batch.id,
                  expected_version: batch.version,
                })
              )
            }
          >
            <Icon name="inbox" /> Submit for QA review
          </Button>
        )}
        {canReview && (!me || myRoles.includes("QA Reviewer")) && (
          <Button variant="secondary" disabled={busy} onClick={() => setPending({ kind: "review" })}>
            <Icon name="badge-check" /> Review batch
          </Button>
        )}
        {canRelease && (!me || myRoles.includes("QA Releaser")) && (
          <Button variant="success" disabled={busy} onClick={() => setPending({ kind: "release" })}>
            <Icon name="shield-check" /> Release batch
          </Button>
        )}
        {(batch.status === "issued" || batch.status === "in_execution") && (
          <Button variant="secondary" disabled={busy} onClick={() => setIssueMaterialOpen(true)}>
            <Icon name="scale" /> Issue material
          </Button>
        )}
      </div>

      <Card>
        <CardHeader title="Batch steps" meta={`${batch.steps.length} step${batch.steps.length === 1 ? "" : "s"}`} />
        <div style={{ padding: "var(--space-2) var(--space-5)" }}>
          <Stepper>
            {batch.steps.map((step) => (
              <StepItem
                key={step.batch_step_id}
                number={step.step_number}
                state={STEP_MARKER_STATE[step.status] ?? "pending"}
                title={step.name}
                meta={
                  step.requires_signature ? (
                    <span className="flex items-center gap-1">
                      <Icon name="pen" /> Requires signature — {step.signature_meaning}
                    </span>
                  ) : (
                    step.status
                  )
                }
                action={
                  <span>
                    {step.status === "ready" && (
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={busy}
                        onClick={() =>
                          run(() =>
                            api.post<MutationReceipt>(`/batches/${batch.id}/steps/${step.batch_step_id}/start`, {
                              idempotency_key: newIdempotencyKey(),
                              batch_id: batch.id,
                              expected_version: batch.version,
                              batch_step_id: step.batch_step_id,
                            })
                          )
                        }
                      >
                        Start
                      </Button>
                    )}
                    {step.status === "in_progress" &&
                      (step.requires_signature ? (
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={busy}
                          onClick={() => setPending({ kind: "complete_step", step })}
                        >
                          <Icon name="pen" /> Complete &amp; sign
                        </Button>
                      ) : (
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={busy}
                          onClick={() =>
                            run(() =>
                              api.post<MutationReceipt>(`/batches/${batch.id}/steps/${step.batch_step_id}/complete`, {
                                idempotency_key: newIdempotencyKey(),
                                batch_id: batch.id,
                                expected_version: batch.version,
                                batch_step_id: step.batch_step_id,
                                data: {},
                              })
                            )
                          }
                        >
                          Complete
                        </Button>
                      ))}
                  </span>
                }
              />
            ))}
          </Stepper>
        </div>
      </Card>

      <Card className="mt-5">
        <CardHeader
          title="Materials issued"
          meta={`${materialIssues.length} issue${materialIssues.length === 1 ? "" : "s"}`}
        />
        {materialIssues.length === 0 ? (
          <EmptyState icon="scale">No materials issued to this batch yet.</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Lot</th>
                <th>Material</th>
                <th style={{ textAlign: "right" }}>Quantity</th>
                <th>Issued</th>
              </tr>
            </thead>
            <tbody>
              {materialIssues.map((issue) => (
                <tr key={issue.id}>
                  <td className="font-semibold tabular">{issue.internal_lot}</td>
                  <td>
                    {issue.material_name} <span className="text-muted tabular">({issue.material_code})</span>
                  </td>
                  <td className="tabular" style={{ textAlign: "right" }}>
                    {issue.quantity} {issue.uom}
                  </td>
                  <td className="text-muted fs-3">{new Date(issue.issued_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {pending && (
        <SignatureModal
          batch={batch}
          pending={pending}
          onClose={() => setPending(null)}
          onDone={() => {
            setPending(null);
            refresh();
          }}
        />
      )}

      {issueMaterialOpen && (
        <IssueMaterialModal
          batch={batch}
          onClose={() => setIssueMaterialOpen(false)}
          onDone={() => {
            setIssueMaterialOpen(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}

function IssueMaterialModal({
  batch,
  onClose,
  onDone,
}: {
  batch: BatchDetail;
  onClose: () => void;
  onDone: () => void;
}) {
  const [lots, setLots] = useState<MaterialLot[]>([]);
  const [lotId, setLotId] = useState("");
  const [batchStepId, setBatchStepId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get<{ items: MaterialLot[] }>("/material-lots?status=released&page_size=100")
      .then((result) => {
        setLots(result.items);
        if (result.items.length) setLotId(result.items[0].id);
      });
  }, []);

  const selectedLot = lots.find((l) => l.id === lotId);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedLot) return;
    setBusy(true);
    setError(null);
    try {
      await api.post<MutationReceipt>(`/batches/${batch.id}/material-issues`, {
        idempotency_key: newIdempotencyKey(),
        lot_id: selectedLot.id,
        expected_version: selectedLot.version,
        batch_id: batch.id,
        batch_step_id: batchStepId || null,
        quantity,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to issue material");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Issue material to batch">
      <form onSubmit={onSubmit}>
        {lots.length === 0 ? (
          <Banner tone="warn" title="No released lots available">
            Receive a lot and have QC release it before it can be issued here.
          </Banner>
        ) : (
          <>
            <Field label="Material lot" required>
              <Select value={lotId} onChange={(e) => setLotId(e.target.value)} required>
                {lots.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.material_name} ({l.material_code}) — lot {l.internal_lot} — {l.available_quantity} {l.uom}{" "}
                    available
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Batch step" hint="Optional — link this issue to a specific step.">
              <Select value={batchStepId} onChange={(e) => setBatchStepId(e.target.value)}>
                <option value="">Not linked to a step</option>
                {batch.steps.map((s) => (
                  <option key={s.batch_step_id} value={s.batch_step_id}>
                    Step {s.step_number} — {s.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Quantity" required>
              <Input value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
            </Field>
          </>
        )}
        {error && <p className="error-text mb-3">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !selectedLot}>
            {busy ? "Issuing…" : "Issue material"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function SignatureModal({
  batch,
  pending,
  onClose,
  onDone,
}: {
  batch: BatchDetail;
  pending: PendingAction;
  onClose: () => void;
  onDone: () => void;
}) {
  const [password, setPassword] = useState("");
  const [reason, setReason] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [meaning, setMeaning] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const body =
      pending.kind === "complete_step"
        ? { action: "complete_step", batch_step_id: pending.step.batch_step_id }
        : { action: pending.kind };
    api
      .post<{ challenge_id: string; meaning: string }>(`/batches/${batch.id}/signature-challenges`, body)
      .then((c) => {
        setChallengeId(c.challenge_id);
        setMeaning(c.meaning);
      })
      .catch(() => setError("Could not request signature challenge"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function confirm() {
    if (!challengeId) return;
    setBusy(true);
    setError(null);
    try {
      if (pending.kind === "complete_step") {
        await api.post<MutationReceipt>(
          `/batches/${batch.id}/steps/${pending.step.batch_step_id}/complete`,
          {
            idempotency_key: newIdempotencyKey(),
            batch_id: batch.id,
            expected_version: batch.version,
            batch_step_id: pending.step.batch_step_id,
            data: {},
            challenge_id: challengeId,
            reauth_password: password,
          }
        );
      } else if (pending.kind === "review") {
        await api.post<MutationReceipt>(`/batches/${batch.id}/review`, {
          idempotency_key: newIdempotencyKey(),
          batch_id: batch.id,
          expected_version: batch.version,
          decision: "approved",
          reason: reason || null,
          challenge_id: challengeId,
          reauth_password: password,
        });
      } else {
        await api.post<MutationReceipt>(`/batches/${batch.id}/release`, {
          idempotency_key: newIdempotencyKey(),
          batch_id: batch.id,
          expected_version: batch.version,
          decision: "released",
          challenge_id: challengeId,
          reauth_password: password,
        });
      }
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Signature failed");
    } finally {
      setBusy(false);
    }
  }

  const title =
    pending.kind === "complete_step"
      ? `Sign step: ${pending.step.name}`
      : pending.kind === "review"
        ? "Sign QA review"
        : "Sign batch release";

  return (
    <Modal
      open
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          <Icon name="pen" /> {title}
        </span>
      }
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" disabled={busy || !challengeId || !password} onClick={confirm}>
            <Icon name="badge-check" /> {busy ? "Signing…" : "Sign"}
          </Button>
        </>
      }
    >
      {meaning && (
        <p className="fs-3 mb-3">
          Meaning: <span className="font-semibold">{meaning}</span>
        </p>
      )}
      <div className="sig-hint mb-4">
        Fresh authentication required — re-enter your password to sign (Part 11 step-up).
      </div>
      {pending.kind === "review" && (
        <Field label="Review comment" hint="Optional. Part of the permanent record.">
          <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
      )}
      <Field label="Password" required error={error}>
        <Input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
        />
      </Field>
    </Modal>
  );
}
