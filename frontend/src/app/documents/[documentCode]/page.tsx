"use client";

import { use, useState } from "react";
import {
  api,
  canAuthorDocument,
  canReleaseDocument,
  formatDate,
  formatDateTime,
  hasPermission,
  newIdempotencyKey,
} from "@/lib/api";
import { useApiResource, useEntityOptions, useMe, useRequirePermission } from "@/lib/hooks";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { PageHead } from "@/components/ui/PageHead";
import { Card } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button, LinkButton } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact, UserFact } from "@/components/ui/FactGrid";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";

// Matches app/modules/qms/document_router.py's version dict.
interface DocumentVersion {
  id: string;
  site_id: string;
  document_code: string;
  document_type: string;
  version_label: string;
  state: string;
  owner_subject_id: string;
  owner_full_name: string | null;
  owner_username: string | null;
  content_hash: string;
  rendition_hash: string | null;
  effective_from: string | null;
  effective_to: string | null;
  periodic_review_due: string | null;
  acknowledgment_required: boolean;
  is_external: boolean;
  external_source: string | null;
  external_revision: string | null;
  training_impact: Record<string, unknown> | null;
  version: number;
  created_at: string;
}

type Action = "submit" | "release" | "make_effective" | "obsolete" | "controlled_copy" | "acknowledge";

// Document 106 row for controlled_document_version/release (resolved, seed.py) — "Released" by an
// independent QA Releaser. Backend challenge endpoint: POST /documents/v1/drafts/{id}/signature-challenges
// (document_router.py, DOCUMENT_VERSION_SIGNATURE_ACTIONS = ("release",)).
const SIGNATURE_GATED: Action[] = ["release"];

const ACTION_LABEL: Record<Action, string> = {
  submit: "Submit for review",
  release: "Release",
  make_effective: "Make effective",
  obsolete: "Obsolete",
  controlled_copy: "Issue copy",
  acknowledge: "Acknowledge",
};

export default function DocumentDetailPage({ params }: { params: Promise<{ documentCode: string }> }) {
  const { documentCode: encodedCode } = use(params);
  const documentCode = decodeURIComponent(encodedCode);
  const { me } = useRequirePermission("document.view");
  const {
    data: versions,
    loading,
    error,
    reload,
  } = useApiResource<DocumentVersion[]>(`/documents/v1/${encodeURIComponent(documentCode)}/versions`);
  const [pending, setPending] = useState<{ version: DocumentVersion; action: Action } | null>(null);

  function actionsFor(v: DocumentVersion): Action[] {
    switch (v.state) {
      case "DRAFT":
        return canAuthorDocument(me) ? ["submit"] : [];
      case "REVIEW":
        return canReleaseDocument(me) ? ["release"] : [];
      case "RELEASED":
        return canReleaseDocument(me) ? ["make_effective"] : [];
      case "EFFECTIVE": {
        // SG-079 resolved 2026-10-09 (project-owner-directed, "Simple unsigned log"): acknowledgment is
        // the same audience as document.view (anyone who can see a document should be able to confirm
        // they read it) -- not gated by canReleaseDocument like the QA-authority actions below it.
        const actions: Action[] = hasPermission(me, "document.acknowledge") ? ["acknowledge"] : [];
        return canReleaseDocument(me) ? [...actions, "controlled_copy", "obsolete"] : actions;
      }
      default:
        return [];
    }
  }

  return (
    <div>
      <PageHead
        title={documentCode}
        subtitle="Document versions from draft through review, release, effectivity and obsolescence."
        action={
          <LinkButton href="/documents" variant="secondary">
            <Icon name="arrow-left" /> Back to documents
          </LinkButton>
        }
      />

      {error && (
        <Banner tone="critical" title="Could not load this document">
          {error}
        </Banner>
      )}

      {!error && (
        <Card>
          {loading ? (
            <EmptyState icon="file-text">Loading…</EmptyState>
          ) : !versions || versions.length === 0 ? (
            <EmptyState icon="file-text">No versions exist for this document code.</EmptyState>
          ) : (
            <Table>
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Type</th>
                  <th>State</th>
                  <th>Effective</th>
                  <th>Review due</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v) => (
                  <tr key={v.id}>
                    <td className="font-semibold tabular">{v.version_label}</td>
                    <td className="fs-2">{v.document_type}</td>
                    <td>
                      <WorkflowStatePill state={v.state} />
                    </td>
                    <td className="tabular fs-2">
                      {formatDate(v.effective_from)}
                      {v.effective_to && ` – ${formatDate(v.effective_to)}`}
                    </td>
                    <td className="tabular fs-2">{formatDate(v.periodic_review_due)}</td>
                    <td style={{ textAlign: "right" }}>
                      <div className="flex gap-2 justify-end">
                        {actionsFor(v).map((a) => (
                          <Button key={a} size="sm" variant="secondary" onClick={() => setPending({ version: v, action: a })}>
                            {SIGNATURE_GATED.includes(a) && <Icon name="pen" />} {ACTION_LABEL[a]}
                          </Button>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}

      {versions?.map((v) => (
        <Card key={v.id} pad className="mt-4">
          <div className="flex justify-between items-center mb-3">
            <span className="font-semibold">
              {v.document_code} {v.version_label}
            </span>
            <WorkflowStatePill state={v.state} />
          </div>
          <FactGrid>
            <Fact label="Type">{v.document_type}</Fact>
            <Fact label="External">{v.is_external ? v.external_source ?? "Yes" : "No"}</Fact>
            <Fact label="Acknowledgment">{v.acknowledgment_required ? "Required" : "Not required"}</Fact>
            <Fact label="Record version">{v.version}</Fact>
            <IdFact label="Content hash" value={v.content_hash} />
            <IdFact label="Rendition hash" value={v.rendition_hash} />
            <UserFact label="Owner" fullName={v.owner_full_name} username={v.owner_username} id={v.owner_subject_id} />
          </FactGrid>
          <div className="mt-3">
            <JsonPanel title="Training impact" value={v.training_impact} />
          </div>
          {v.state === "EFFECTIVE" && <AcknowledgmentsPanel version={v} />}
        </Card>
      ))}

      {pending && (
        <ActionModal
          version={pending.version}
          action={pending.action}
          onClose={() => setPending(null)}
          onDone={() => {
            setPending(null);
            reload();
          }}
        />
      )}
    </div>
  );
}

// DOC-FR-014/SG-079 resolved 2026-10-09 (project-owner-directed, "Simple unsigned log"): shows who has
// already confirmed reading this EFFECTIVE version -- the read side of the acknowledgment feature. Not
// a Part 11 signature (AG-07): the backend always returns signature_id: null for these rows.
interface Acknowledgment {
  id: string;
  user_id: string;
  user_full_name: string | null;
  user_username: string | null;
  statement: string | null;
  acknowledged_at: string;
}

function AcknowledgmentsPanel({ version }: { version: DocumentVersion }) {
  const { data } = useApiResource<Acknowledgment[]>(`/documents/v1/versions/${version.id}/acknowledgments`);

  return (
    <div className="mt-3">
      <p className="fact-k mb-2">Acknowledgments{data ? ` (${data.length})` : ""}</p>
      {!data || data.length === 0 ? (
        <p className="fs-2 text-muted">No one has acknowledged this version yet.</p>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>User</th>
              <th>Statement</th>
              <th>Acknowledged at</th>
            </tr>
          </thead>
          <tbody>
            {data.map((a) => (
              <tr key={a.id}>
                <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>
                  {a.user_full_name || a.user_username || a.user_id}
                </td>
                <td className="fs-2">{a.statement ?? "—"}</td>
                <td className="tabular fs-2">{formatDateTime(a.acknowledged_at)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}

function ActionModal({
  version,
  action,
  onClose,
  onDone,
}: {
  version: DocumentVersion;
  action: Action;
  onClose: () => void;
  onDone: () => void;
}) {
  const { me } = useMe();
  const entities = useEntityOptions();
  const { busy, error, run } = useCommand(onDone);
  const [reviewer, setReviewer] = useState(me?.user_id ?? "");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [periodicReview, setPeriodicReview] = useState("");
  const [trainingRequired, setTrainingRequired] = useState(false);
  const [acknowledgmentRequired, setAcknowledgmentRequired] = useState(false);
  const [trainingConfirmed, setTrainingConfirmed] = useState(false);
  const [retirementReason, setRetirementReason] = useState("");
  const [copyNumber, setCopyNumber] = useState("");
  const [recipient, setRecipient] = useState("");
  const [location, setLocation] = useState("");
  const [acknowledgmentStatement, setAcknowledgmentStatement] = useState("");

  const base = {
    idempotency_key: newIdempotencyKey(),
    document_version_id: version.id,
    expected_version: version.version,
  };

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() => {
      switch (action) {
        case "submit":
          return api.post(`/documents/v1/drafts/${version.id}/submit`, {
            ...base,
            reviewers: [{ subject_id: reviewer, role: "reviewer" }],
          });
        case "make_effective":
          return api.post(`/documents/v1/versions/${version.id}/make-effective`, {
            ...base,
            training_confirmed: trainingConfirmed,
          });
        case "obsolete":
          return api.post(`/documents/v1/versions/${version.id}/obsolete`, {
            ...base,
            retirement_reason: retirementReason,
          });
        case "controlled_copy":
          return api.post(`/documents/v1/versions/${version.id}/controlled-copies`, {
            ...base,
            copy_number: copyNumber,
            recipient,
            location: location || null,
          });
        case "acknowledge":
          // No expected_version -- this is an insert-only log, not a mutation of the version's own
          // aggregate state (AcknowledgeDocumentVersionCommand doesn't accept one, CommandEnvelope is
          // extra="forbid").
          return api.post(`/documents/v1/versions/${version.id}/acknowledgments`, {
            idempotency_key: newIdempotencyKey(),
            document_version_id: version.id,
            statement: acknowledgmentStatement || null,
          });
        default:
          // "release" is signature-gated and never reaches this form — see the early return below
          // that renders <SignatureCeremony> for it instead.
          throw new Error(`${action} does not submit through the plain form`);
      }
    });
  }

  // Document 106 row (controlled_document_version/release): "Released" by an independent QA Releaser,
  // via the shared Part 11 ceremony (challenge -> password re-entry -> signed mutation) — same pattern
  // as the deviations/CAPA detail pages' close.
  if (action === "release") {
    return (
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        challengePath={`/documents/v1/drafts/${version.id}/signature-challenges`}
        action="release"
        title={`Release - ${version.document_code} ${version.version_label}`}
        summary="Releases this document version. This is a released quality decision - signer must be independent of the record's author."
        submitLabel="Sign & release"
        submitVariant="success"
        extraFields={
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Effective from">
                <Input type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
              </Field>
              <Field label="Periodic review due">
                <Input type="date" value={periodicReview} onChange={(e) => setPeriodicReview(e.target.value)} />
              </Field>
            </div>
            <label className="flex items-center gap-2 fs-2 mb-2">
              <input type="checkbox" checked={trainingRequired} onChange={(e) => setTrainingRequired(e.target.checked)} />
              Training required before this version can be made effective
            </label>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input
                type="checkbox"
                checked={acknowledgmentRequired}
                onChange={(e) => setAcknowledgmentRequired(e.target.checked)}
              />
              Read-and-understood acknowledgment required
            </label>
          </>
        }
        onSign={(p) =>
          api.post(`/documents/v1/drafts/${version.id}/release`, {
            idempotency_key: p.idempotency_key,
            document_version_id: version.id,
            expected_version: version.version,
            challenge_id: p.challenge_id,
            reauth_password: p.reauth_password,
            review_completed: true,
            effective_from: effectiveFrom ? new Date(effectiveFrom).toISOString() : null,
            periodic_review_due: periodicReview ? new Date(periodicReview).toISOString() : null,
            training_impact: { required: trainingRequired },
            acknowledgment_required: acknowledgmentRequired,
          })
        }
      />
    );
  }

  return (
    <Modal open onClose={onClose} title={`${ACTION_LABEL[action]} - ${version.document_code} ${version.version_label}`}>
      <form onSubmit={submit}>
        {action === "submit" && (
          <EntityPickerField
            label="Reviewer"
            required
            hint="SOD-005: the author should not approve their own document."
            value={reviewer}
            onChange={setReviewer}
            options={entities.users}
            status={entities.usersStatus}
            kind="user"
          />
        )}

        {action === "make_effective" && (
          <>
            <p className="fs-3 mb-3">
              Making this version effective supersedes the currently effective version of{" "}
              {version.document_code}.
            </p>
            <label className="flex items-center gap-2 fs-2 mb-3">
              <input
                type="checkbox"
                checked={trainingConfirmed}
                onChange={(e) => setTrainingConfirmed(e.target.checked)}
              />
              Required training has been completed
            </label>
          </>
        )}

        {action === "obsolete" && (
          <Field label="Retirement reason" required>
            <textarea
              className="input"
              rows={3}
              value={retirementReason}
              onChange={(e) => setRetirementReason(e.target.value)}
              required
            />
          </Field>
        )}

        {action === "acknowledge" && (
          <>
            <p className="fs-3 mb-3">
              Confirm that you have read and understood {version.document_code} {version.version_label}.
              This is an unsigned log, not a Part 11 electronic signature.
            </p>
            <Field label="Statement" hint="Optional. E.g. &quot;I have read and understood this SOP and will follow it exactly as written.&quot;">
              <textarea
                className="input"
                rows={3}
                value={acknowledgmentStatement}
                onChange={(e) => setAcknowledgmentStatement(e.target.value)}
              />
            </Field>
          </>
        )}

        {action === "controlled_copy" && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Copy number" required>
                <Input value={copyNumber} onChange={(e) => setCopyNumber(e.target.value)} required autoFocus />
              </Field>
              <Field label="Recipient" required>
                <Input value={recipient} onChange={(e) => setRecipient(e.target.value)} required />
              </Field>
            </div>
            <Field label="Location" hint="Where the physical copy is posted, so it can be recalled on supersession.">
              <Input value={location} onChange={(e) => setLocation(e.target.value)} />
            </Field>
          </>
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
