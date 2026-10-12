"use client";

import { use, useState } from "react";
import {
  api,
  hasPermission,
  formatDate,
  formatDateTime,
  newIdempotencyKey,
  type Nonconformance,
} from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { QmsDetailShell, useCommand } from "@/components/qms/QmsDetailShell";
import { Fact, IdFact, UserFact } from "@/components/ui/FactGrid";
import { Tabs } from "@/components/ui/Tabs";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { StatePill, BoolPill, SeverityPill } from "@/components/ui/StatePill";
import { humanizeLabel } from "@/lib/format";

interface Disposition {
  id: string;
  affected_scope: unknown[];
  quantity: number | null;
  serials: string[] | null;
  disposition_type: string;
  justification: string;
  rework_route: Record<string, unknown> | null;
  follow_up_test_requirements: Record<string, unknown> | null;
  use_as_is_authorized_by: string | null;
  use_as_is_authorized_by_full_name?: string | null;
  use_as_is_authorized_by_username?: string | null;
  signature_id: string | null;
  created_at: string;
}

interface NcrDetail extends Nonconformance {
  owner_full_name?: string | null;
  owner_username?: string | null;
  scope_records: unknown[];
  requirement_ref: Record<string, unknown> | null;
  segregation: Record<string, unknown> | null;
  evaluation: Record<string, unknown> | null;
  supplier_link: Record<string, unknown> | null;
  capa_rationale: string | null;
  verification: Record<string, unknown> | null;
  verification_history: unknown[];
  closure_history: unknown[];
  reopen_history: unknown[];
  dispositions: Disposition[];
}

/** Resolves an actor to the best available display text -- full name, then username, then the raw id
 * as a last resort (e.g. a user resolved against a different site, or deleted) -- never silently blank. */
type Transition = "segregate" | "evaluate" | "disposition" | "verify" | "close" | "reopen";

const ALLOWED_FROM: Record<string, Transition[]> = {
  OPEN: ["segregate"],
  SEGREGATED: ["segregate", "evaluate"],
  EVALUATION: ["evaluate", "disposition"],
  // A disposition moves the record into its disposition state; every disposition type then needs
  // verification before close -- close_ncr() only accepts from VERIFICATION/REOPENED, never directly
  // from a disposition state (2026-10-09 real bug fixed: RETURN/SCRAP/USE_AS_IS used to map to
  // ["close"] here, which would always 409 INVALID_TRANSITION since close_ncr() never accepts those
  // three states directly -- verify_ncr() does, via the `confirmation` field for non-rework outcomes).
  REWORK: ["verify"],
  REPAIR: ["verify"],
  RETURN: ["verify"],
  SCRAP: ["verify"],
  USE_AS_IS: ["verify"],
  VERIFICATION: ["verify", "close"],
  // NCR-FR-016/SG-069 resolved 2026-10-09: CLOSED is no longer a terminal dead end.
  CLOSED: ["reopen"],
  // Mirrors Document 26's own REOPENED breadth -- any substantive forward step can resume from here.
  REOPENED: ["evaluate", "disposition", "verify", "close"],
};

// SG-138 resolved 2026-09-10 (seed.py SIGNATURE_POLICY_FLOOR rows 83-85): disposition/close are QA
// Releaser-signed, independent of the record owner; verify is a qualified independent verifier. Go
// through the shared Part 11 ceremony (challenge -> password re-entry -> signed mutation) below.
// reopen is deliberately NOT here -- same as qms_deviation/capa reopen, it's unsigned (RBAC-gated only).
const SIGNATURE_GATED: Transition[] = ["disposition", "verify", "close"];

const LABEL: Record<Transition, string> = {
  segregate: "Record segregation",
  evaluate: "Evaluate",
  disposition: "Disposition",
  verify: "Verify",
  close: "Close",
  reopen: "Reopen",
};

// The exact permission code app/modules/qms/ncr_router.py checks for each transition. Note ncr.verify
// is held by QA Reviewer/QC Reviewer, NOT QA Releaser (unlike disposition/close) -- the old shared
// "SIGNATURE_GATED -> approver role" split lumped verify in with disposition/close and would have hidden
// this button from the QA Reviewer/QC Reviewer users who actually hold it (audit finding 2026-09-18).
const PERMISSION_FOR_TRANSITION: Record<Transition, string> = {
  segregate: "ncr.segregate",
  evaluate: "ncr.evaluate",
  disposition: "ncr.disposition",
  verify: "ncr.verify",
  close: "ncr.close",
  reopen: "ncr.reopen",
};

// app/modules/qms/ncr_models.py NCR_DISPOSITION_TYPES.
const DISPOSITION_TYPES = ["REWORK", "REPAIR", "RETURN", "SCRAP", "USE_AS_IS"];

export default function NcrDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const [pending, setPending] = useState<Transition | null>(null);
  const { data, loading, error, reload } = useApiResource<NcrDetail>(`/qms/v1/nonconformances/${id}`);

  const allowed = data ? (ALLOWED_FROM[data.state] ?? []) : [];
  const canDo = (t: Transition) => allowed.includes(t) && hasPermission(me, PERMISSION_FOR_TRANSITION[t]);

  return (
    <QmsDetailShell
      recordNumber={data?.ncr_number ?? ""}
      state={data?.state ?? ""}
      subtitle={data ? `${data.defect_code} · ${data.scope_type} scope` : undefined}
      backHref="/nonconformances"
      backLabel="Nonconformances"
      loading={loading}
      error={error}
      actions={(Object.keys(LABEL) as Transition[]).filter(canDo).map((t) => (
        <Button key={t} variant={t === "close" ? "primary" : "secondary"} onClick={() => setPending(t)}>
          {SIGNATURE_GATED.includes(t) && <Icon name="pen" />} {LABEL[t]}
        </Button>
      ))}
      facts={
        data && (
          <>
            <Fact label="Severity">
              <SeverityPill severity={data.severity} />
            </Fact>
            <Fact label="Defect code">{data.defect_code}</Fact>
            <Fact label="Release blocker">
              {data.release_blocker_active ? (
                <StatePill state="blocked" icon="lock">
                  Active
                </StatePill>
              ) : (
                <StatePill state="na" icon="slash-circle">
                  Cleared
                </StatePill>
              )}
            </Fact>
            <Fact label="CAPA required">
              <BoolPill value={data.capa_required} trueLabel="Required" falseLabel="Not required" />
            </Fact>
            <Fact label="Dispositions">{data.dispositions.length}</Fact>
            <Fact label="Raised">{formatDateTime(data.created_at)}</Fact>
            <Fact label="Closed">{data.closed_at ? formatDateTime(data.closed_at) : "—"}</Fact>
            <Fact label="Record version">{data.version}</Fact>
            <UserFact label="Owner" fullName={data.owner_full_name} username={data.owner_username} id={data.owner_subject_id} />
            <IdFact label="Source record" value={data.source_label ?? data.source_id} />
            <IdFact label="Quality event" value={data.quality_event_id} />
          </>
        )
      }
    >
      {data && (
        <>
          {data.release_blocker_active && (
            <Banner tone="critical" title="Release blocker active" icon="lock">
              Affected product cannot be released while this nonconformance is open.
            </Banner>
          )}

          <Tabs
            tabs={[
              {
                id: "evaluation",
                label: "Evaluation",
                content: (
                  <Card pad>
                    <JsonPanel title="Requirement reference" value={data.requirement_ref} />
                    <JsonPanel title="Affected records" value={data.scope_records} />
                    <JsonPanel title="Segregation" value={data.segregation} />
                    <JsonPanel title="Evaluation" value={data.evaluation} />
                    <JsonPanel title="Supplier link" value={data.supplier_link} />
                  </Card>
                ),
              },
              {
                id: "dispositions",
                label: "Dispositions",
                badge: data.dispositions.length || undefined,
                content: <DispositionsTab dispositions={data.dispositions} />,
              },
              {
                id: "verification",
                label: "Verification",
                content: (
                  <Card pad>
                    <VerificationRoundsPanel history={data.verification_history} latest={data.verification} />
                    <JsonPanel title="CAPA rationale" value={data.capa_rationale} />
                    <ClosuresPanel entries={data.closure_history} />
                    <ReopeningsPanel entries={data.reopen_history} />
                    {!data.verification && data.closure_history.length === 0 && data.reopen_history.length === 0 && (
                      <EmptyState icon="help-circle">Nothing verified or closed yet.</EmptyState>
                    )}
                  </Card>
                ),
              },
            ]}
          />

          {pending && (
            <TransitionModal
              ncr={data}
              transition={pending}
              onClose={() => setPending(null)}
              onDone={() => {
                setPending(null);
                reload();
              }}
            />
          )}
        </>
      )}
    </QmsDetailShell>
  );
}

function DispositionsTab({ dispositions }: { dispositions: Disposition[] }) {
  if (dispositions.length === 0) {
    return <EmptyState icon="help-circle">No disposition recorded yet.</EmptyState>;
  }
  return (
    <div>
      {dispositions.map((d) => (
        <Card key={d.id} pad className="mb-3">
          <div className="flex justify-between items-center mb-2">
            <span className="font-semibold">{d.disposition_type}</span>
            <span className="fs-2 text-muted">{formatDate(d.created_at)}</span>
          </div>
          <p className="fs-2 mb-3">{d.justification}</p>
          {d.quantity !== null && (
            <p className="fs-2">
              <span className="text-muted">Quantity: </span>
              <span className="tabular">{d.quantity}</span>
            </p>
          )}
          <JsonPanel title="Affected scope" value={d.affected_scope} />
          <JsonPanel title="Serials" value={d.serials} />
          <JsonPanel title="Rework route" value={d.rework_route} />
          <JsonPanel title="Follow-up tests" value={d.follow_up_test_requirements} />
          {d.disposition_type === "USE_AS_IS" && (
            <p className="fs-2 text-muted">
              Use-as-is authorised by:{" "}
              {d.use_as_is_authorized_by_full_name || d.use_as_is_authorized_by_username || d.use_as_is_authorized_by || "—"}
            </p>
          )}
        </Card>
      ))}
    </div>
  );
}

interface VerificationRound {
  reinspection_evidence?: { result?: string } | null;
  confirmation?: { note?: string } | null;
  verified_by?: string;
  verified_by_full_name?: string | null;
  verified_by_username?: string | null;
  verified_at?: string;
  prior_disposition_state?: string;
  signature_id?: string | null;
}

/** Each round (`verify()` call) has nested `reinspection_evidence`/`confirmation` objects, so the
 * generic HistoryPanel/JsonPanel fallback renders it as a raw JSON dump -- this gives it the same
 * designed-card treatment as DispositionsTab above. `history` is empty for an NCR verified before
 * migration 0142 added it (no round ever appended retroactively, nothing fabricated); `latest` still
 * carries that one legacy round, synthesized as "Round 1" so it isn't lost from the view. */
function VerificationRoundsPanel({
  history,
  latest,
}: {
  history: unknown[];
  latest: Record<string, unknown> | null;
}) {
  const rounds: VerificationRound[] =
    Array.isArray(history) && history.length > 0
      ? (history as VerificationRound[])
      : latest
        ? [latest as VerificationRound]
        : [];

  if (rounds.length === 0) return null;

  return (
    <div className="mb-4">
      <p className="fact-k mb-2">Verification rounds</p>
      {rounds.map((r, i) => {
        const isReinspection = Boolean(r.reinspection_evidence);
        const evidenceText = r.reinspection_evidence?.result ?? r.confirmation?.note ?? null;
        return (
          <Card key={i} pad className="mb-3">
            <div className="flex justify-between items-center mb-2">
              <span className="font-semibold">
                Round {i + 1}
                {r.prior_disposition_state && (
                  <span className="text-muted fs-2" style={{ fontWeight: 400 }}>
                    {" "}
                    — {humanizeLabel(r.prior_disposition_state)}
                  </span>
                )}
              </span>
              <span className="fs-2 text-muted">{formatDateTime(r.verified_at)}</span>
            </div>
            {evidenceText && (
              <p className="fs-2 mb-3">
                <span className="text-muted">{isReinspection ? "Reinspection result" : "Confirmation"}: </span>
                {evidenceText}
              </p>
            )}
            <div className="flex items-center justify-between">
              <UserFact label="Verified by" fullName={r.verified_by_full_name} username={r.verified_by_username} id={r.verified_by} />
              <BoolPill value={Boolean(r.signature_id)} trueLabel="Signed" falseLabel="Unsigned" />
            </div>
          </Card>
        );
      })}
    </div>
  );
}

interface ClosureEntry {
  conclusion?: string;
  closed_at?: string;
  closed_by?: string;
  closed_by_full_name?: string | null;
  closed_by_username?: string | null;
  signature_id?: string | null;
}

/** Same designed-card treatment as VerificationRoundsPanel -- `closed_by` was previously shown as a raw
 * UUID via the generic HistoryPanel/FlatFacts fallback. */
function ClosuresPanel({ entries }: { entries: unknown[] }) {
  if (!Array.isArray(entries) || entries.length === 0) return null;
  const rows = entries as ClosureEntry[];
  return (
    <div className="mb-4">
      <p className="fact-k mb-2">Closures</p>
      {rows.map((c, i) => (
        <Card key={i} pad className="mb-3">
          <div className="flex justify-between items-center mb-2">
            <span className="font-semibold">Closure {i + 1}</span>
            <span className="fs-2 text-muted">{formatDateTime(c.closed_at)}</span>
          </div>
          {c.conclusion && <p className="fs-2 mb-3">{c.conclusion}</p>}
          <div className="flex items-center justify-between">
            <UserFact label="Closed by" fullName={c.closed_by_full_name} username={c.closed_by_username} id={c.closed_by} />
            <BoolPill value={Boolean(c.signature_id)} trueLabel="Signed" falseLabel="Unsigned" />
          </div>
        </Card>
      ))}
    </div>
  );
}

interface ReopenEntry {
  reason?: string;
  new_evidence?: string;
  reopened_at?: string;
  reopened_by?: string;
  reopened_by_full_name?: string | null;
  reopened_by_username?: string | null;
}

/** Same designed-card treatment as ClosuresPanel/VerificationRoundsPanel -- reopen is unsigned (RBAC-
 * gated only, same as Deviation/CAPA), so there's no signed badge here. */
function ReopeningsPanel({ entries }: { entries: unknown[] }) {
  if (!Array.isArray(entries) || entries.length === 0) return null;
  const rows = entries as ReopenEntry[];
  return (
    <div className="mb-4">
      <p className="fact-k mb-2">Reopenings</p>
      {rows.map((r, i) => (
        <Card key={i} pad className="mb-3">
          <div className="flex justify-between items-center mb-2">
            <span className="font-semibold">Reopening {i + 1}</span>
            <span className="fs-2 text-muted">{formatDateTime(r.reopened_at)}</span>
          </div>
          {r.reason && (
            <p className="fs-2 mb-2">
              <span className="text-muted">Reason: </span>
              {r.reason}
            </p>
          )}
          {r.new_evidence && (
            <p className="fs-2 mb-3">
              <span className="text-muted">New evidence: </span>
              {r.new_evidence}
            </p>
          )}
          <UserFact label="Reopened by" fullName={r.reopened_by_full_name} username={r.reopened_by_username} id={r.reopened_by} />
        </Card>
      ))}
    </div>
  );
}

function TransitionModal({
  ncr,
  transition,
  onClose,
  onDone,
}: {
  ncr: NcrDetail;
  transition: Transition;
  onClose: () => void;
  onDone: () => void;
}) {
  const { me } = useMe();
  const { busy, error, run } = useCommand(onDone);

  const [location, setLocation] = useState("");
  const [evaluation, setEvaluation] = useState("");
  const [usability, setUsability] = useState("");
  const [qualityImpact, setQualityImpact] = useState("none");
  const [safetyImpact, setSafetyImpact] = useState("none");
  const [performanceImpact, setPerformanceImpact] = useState("none");
  const [investigationNeeded, setInvestigationNeeded] = useState(false);
  const [dispositionType, setDispositionType] = useState(DISPOSITION_TYPES[0]);
  const [justification, setJustification] = useState("");
  const [quantity, setQuantity] = useState("");
  const [capaRequired, setCapaRequired] = useState(false);
  const [capaRationale, setCapaRationale] = useState("");
  const [reinspection, setReinspection] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [reason, setReason] = useState("");
  const [newEvidence, setNewEvidence] = useState("");

  const base = { idempotency_key: newIdempotencyKey(), ncr_id: ncr.id, expected_version: ncr.version };
  const path = `/qms/v1/nonconformances/${ncr.id}`;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() => {
      switch (transition) {
        case "segregate":
          return api.post(`${path}/segregate`, {
            ...base,
            locations: [{ location, segregated_at: new Date().toISOString() }],
            reason: reason || null,
          });
        case "evaluate":
          return api.post(`${path}/evaluate`, {
            ...base,
            evaluation: {
              conclusion: evaluation,
              usability,
              quality_impact: qualityImpact,
              safety_impact: safetyImpact,
              performance_impact: performanceImpact,
              investigation_needed: investigationNeeded,
            },
            reason: reason || null,
          });
        case "reopen":
          return api.post(`${path}/reopen`, {
            ...base,
            reason,
            new_evidence: newEvidence,
          });
        default:
          // disposition/verify/close are signature-gated and never reach this form -- see the early
          // returns below that render <SignatureCeremony> for them instead.
          throw new Error(`${transition} does not submit through the plain form`);
      }
    });
  }

  // Document 106 section 9 rows 83-85 (SG-138, resolved): disposition/close are QA Releaser-signed,
  // independent of the record owner; verify is a qualified independent verifier.
  if (transition === "disposition") {
    return (
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        challengePath={`${path}/signature-challenges`}
        action="disposition"
        title={`Disposition - ${ncr.ncr_number}`}
        summary="Records the disposition of this nonconformance. This is a released quality decision - signer must be independent of the record's owner."
        submitLabel="Sign & record disposition"
        submitVariant="success"
        disabled={!justification.trim() || (capaRequired && !capaRationale.trim())}
        extraFields={
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Disposition type" required>
                <Select value={dispositionType} onChange={(e) => setDispositionType(e.target.value)}>
                  {DISPOSITION_TYPES.map((d) => (
                    <option key={d} value={d}>
                      {humanizeLabel(d)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Quantity">
                <Input type="number" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
              </Field>
            </div>
            <Field label="Justification" required>
              <textarea className="input" rows={3} value={justification} onChange={(e) => setJustification(e.target.value)} required />
            </Field>
            {dispositionType === "USE_AS_IS" && (
              <Banner tone="warn" title="Use-as-is releases nonconforming product">
                You are recorded as the authorising party. This decision needs a justification an inspector
                would accept on its own terms.
              </Banner>
            )}
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input type="checkbox" checked={capaRequired} onChange={(e) => setCapaRequired(e.target.checked)} />
              CAPA required
            </label>
            {capaRequired && (
              <Field label="CAPA rationale" required>
                <textarea className="input" rows={2} value={capaRationale} onChange={(e) => setCapaRationale(e.target.value)} required />
              </Field>
            )}
          </>
        }
        onSign={(p) =>
          api.post(`${path}/disposition`, {
            idempotency_key: p.idempotency_key,
            ncr_id: ncr.id,
            expected_version: ncr.version,
            challenge_id: p.challenge_id,
            reauth_password: p.reauth_password,
            disposition_type: dispositionType,
            affected_scope: ncr.scope_records,
            justification,
            quantity: quantity ? Number(quantity) : null,
            capa_required: capaRequired,
            capa_rationale: capaRationale || null,
            use_as_is_authorized_by: dispositionType === "USE_AS_IS" ? (me?.user_id ?? null) : null,
          })
        }
      />
    );
  }

  if (transition === "verify") {
    // app/modules/qms/ncr_models.py REWORK_LIKE_DISPOSITIONS: only REWORK/REPAIR need reinspection
    // evidence; RETURN/SCRAP/USE_AS_IS only need a confirmation the disposition was executed. The
    // record's own state names the disposition type directly (REWORK/REPAIR/RETURN/SCRAP/USE_AS_IS);
    // a re-verify from VERIFICATION falls back to the most recent recorded disposition.
    const latestDispositionType = ncr.dispositions.length
      ? ncr.dispositions[ncr.dispositions.length - 1].disposition_type
      : null;
    const effectiveDispositionType = ncr.state === "VERIFICATION" ? latestDispositionType : ncr.state;
    const isReworkLike = effectiveDispositionType === "REWORK" || effectiveDispositionType === "REPAIR";
    return (
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        challengePath={`${path}/signature-challenges`}
        action="verify"
        title={`Verify - ${ncr.ncr_number}`}
        summary="Records verification of the disposition. Signer must be a qualified independent verifier, not the performer."
        submitLabel="Sign & verify"
        submitVariant="success"
        disabled={!reinspection.trim()}
        extraFields={
          isReworkLike ? (
            <Field label="Reinspection result" required hint="Evidence that the rework or repair achieved conformance.">
              <textarea className="input" rows={3} value={reinspection} onChange={(e) => setReinspection(e.target.value)} required />
            </Field>
          ) : (
            <Field label="Confirmation" required hint="Confirm the disposition (return/scrap/use-as-is) was actually executed.">
              <textarea className="input" rows={3} value={reinspection} onChange={(e) => setReinspection(e.target.value)} required />
            </Field>
          )
        }
        onSign={(p) =>
          api.post(`${path}/verify`, {
            idempotency_key: p.idempotency_key,
            ncr_id: ncr.id,
            expected_version: ncr.version,
            challenge_id: p.challenge_id,
            reauth_password: p.reauth_password,
            ...(isReworkLike
              ? { reinspection_evidence: { result: reinspection } }
              : { confirmation: { note: reinspection } }),
          })
        }
      />
    );
  }

  if (transition === "close") {
    return (
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        challengePath={`${path}/signature-challenges`}
        action="close"
        title={`Close - ${ncr.ncr_number}`}
        summary="Closes the nonconformance record permanently. This is a released quality decision - signer must be independent of the record's owner."
        submitLabel="Sign & close"
        submitVariant="success"
        disabled={!conclusion.trim()}
        extraFields={
          <Field label="Conclusion" required>
            <textarea className="input" rows={3} value={conclusion} onChange={(e) => setConclusion(e.target.value)} required />
          </Field>
        }
        onSign={(p) =>
          api.post(`${path}/close`, {
            idempotency_key: p.idempotency_key,
            ncr_id: ncr.id,
            expected_version: ncr.version,
            challenge_id: p.challenge_id,
            reauth_password: p.reauth_password,
            conclusion,
          })
        }
      />
    );
  }

  return (
    <Modal open onClose={onClose} title={`${LABEL[transition]} - ${ncr.ncr_number}`}>
      <form onSubmit={submit}>
        {transition === "segregate" && (
          <Field label="Segregation location" required hint="Where the nonconforming material is being held.">
            <Input value={location} onChange={(e) => setLocation(e.target.value)} required autoFocus />
          </Field>
        )}

        {transition === "evaluate" && (
          <>
            <Field label="Evaluation conclusion" required>
              <textarea className="input" rows={3} value={evaluation} onChange={(e) => setEvaluation(e.target.value)} required />
            </Field>
            <Field label="Usability" required hint="Can the affected material/product still be used as-is, elsewhere, or not at all?">
              <Input value={usability} onChange={(e) => setUsability(e.target.value)} required />
            </Field>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Quality impact" required>
                <Select value={qualityImpact} onChange={(e) => setQualityImpact(e.target.value)}>
                  <option value="none">none</option>
                  <option value="minor">minor</option>
                  <option value="moderate">moderate</option>
                  <option value="major">major</option>
                </Select>
              </Field>
              <Field label="Safety impact" required>
                <Select value={safetyImpact} onChange={(e) => setSafetyImpact(e.target.value)}>
                  <option value="none">none</option>
                  <option value="minor">minor</option>
                  <option value="moderate">moderate</option>
                  <option value="major">major</option>
                </Select>
              </Field>
              <Field label="Performance impact" required>
                <Select value={performanceImpact} onChange={(e) => setPerformanceImpact(e.target.value)}>
                  <option value="none">none</option>
                  <option value="minor">minor</option>
                  <option value="moderate">moderate</option>
                  <option value="major">major</option>
                </Select>
              </Field>
            </div>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input type="checkbox" checked={investigationNeeded} onChange={(e) => setInvestigationNeeded(e.target.checked)} />
              Investigation needed
            </label>
          </>
        )}

        {(transition === "segregate" || transition === "evaluate") && (
          <Field label="Reason" hint="Optional. Recorded in the audit trail.">
            <Input value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
        )}

        {transition === "reopen" && (
          <>
            <Banner tone="warn" title="Reopening a closed nonconformance">
              This is an unsigned, RBAC-gated action (same as Deviation/CAPA reopen) -- the prior
              closure and its signature are preserved, never cleared.
            </Banner>
            <Field label="Reason" required hint="Why this closed NCR needs to be reopened.">
              <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} required />
            </Field>
            <Field label="New evidence" required hint="The new evidence that justifies reopening.">
              <textarea className="input" rows={3} value={newEvidence} onChange={(e) => setNewEvidence(e.target.value)} required />
            </Field>
          </>
        )}

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={
              busy ||
              (transition === "evaluate" && (!evaluation.trim() || !usability.trim())) ||
              (transition === "reopen" && (!reason.trim() || !newEvidence.trim()))
            }
          >
            {busy ? "Saving…" : LABEL[transition]}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
