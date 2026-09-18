"use client";

import { useState } from "react";
import {
  api,
  ApiError,
  canAuthorDocument,
  canReleaseDocument,
  formatDate,
  newIdempotencyKey,
} from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
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

// app/modules/qms/document_models.py DOCUMENT_TYPES.
const DOCUMENT_TYPES = ["sop", "policy", "specification", "work_instruction", "form", "external", "other"];

type Action = "submit" | "release" | "make_effective" | "obsolete" | "controlled_copy";

// Document 106 row for controlled_document_version/release (resolved, seed.py) — "Released" by an
// independent QA Releaser. Backend challenge endpoint: POST /documents/v1/drafts/{id}/signature-challenges
// (document_router.py, DOCUMENT_VERSION_SIGNATURE_ACTIONS = ("release",)).
const SIGNATURE_GATED: Action[] = ["release"];

export default function DocumentsPage() {
  const { me } = useMe();
  const [documentCode, setDocumentCode] = useState("");
  const [versions, setVersions] = useState<DocumentVersion[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftOpen, setDraftOpen] = useState(false);
  const [pending, setPending] = useState<{ version: DocumentVersion; action: Action } | null>(null);

  async function lookup(code = documentCode) {
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setVersions(await api.get<DocumentVersion[]>(`/documents/v1/${encodeURIComponent(code.trim())}/versions`));
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
      setVersions(null);
    } finally {
      setLoading(false);
    }
  }

  function actionsFor(v: DocumentVersion): Action[] {
    switch (v.state) {
      case "DRAFT":
        return canAuthorDocument(me) ? ["submit"] : [];
      case "REVIEW":
        return canReleaseDocument(me) ? ["release"] : [];
      case "RELEASED":
        return canReleaseDocument(me) ? ["make_effective"] : [];
      case "EFFECTIVE":
        return canReleaseDocument(me) ? ["controlled_copy", "obsolete"] : [];
      default:
        return [];
    }
  }

  return (
    <div>
      <PageHead
        title="Controlled documents"
        subtitle="Document versions from draft through review, release, effectivity and obsolescence."
        action={
          canAuthorDocument(me) ? (
            <Button variant="primary" onClick={() => setDraftOpen(true)}>
              <Icon name="plus" /> New draft
            </Button>
          ) : undefined
        }
      />

      <p className="hint mb-4">
        Document versions are looked up one at a time by document code, rather than browsed as a site-wide
        list.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          lookup();
        }}
        className="flex flex-wrap items-end gap-4 mb-4"
      >
        <Field label="Document code">
          <Input
            value={documentCode}
            onChange={(e) => setDocumentCode(e.target.value)}
            placeholder="e.g. SOP-QA-001"
            style={{ minWidth: 200, maxWidth: 260, width: "100%" }}
          />
        </Field>
        <Button type="submit" variant="secondary" disabled={loading || !documentCode.trim()}>
          <Icon name="search" /> {loading ? "Looking up…" : "Look up versions"}
        </Button>
      </form>

      {error && (
        <Banner tone="critical" title="Lookup failed">
          {error}
        </Banner>
      )}

      {versions && !error && (
        <Card>
          <CardHeader title={documentCode} meta={`${versions.length} version(s)`} />
          {versions.length === 0 ? (
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
            <IdFact label="Owner" value={v.owner_subject_id} />
          </FactGrid>
          <div className="mt-3">
            <JsonPanel title="Training impact" value={v.training_impact} />
          </div>
        </Card>
      ))}

      {draftOpen && (
        <DraftModal
          onClose={() => setDraftOpen(false)}
          onDone={(code) => {
            setDraftOpen(false);
            setDocumentCode(code);
            lookup(code);
          }}
        />
      )}

      {pending && (
        <ActionModal
          version={pending.version}
          action={pending.action}
          onClose={() => setPending(null)}
          onDone={() => {
            setPending(null);
            lookup();
          }}
        />
      )}
    </div>
  );
}

const ACTION_LABEL: Record<Action, string> = {
  submit: "Submit for review",
  release: "Release",
  make_effective: "Make effective",
  obsolete: "Obsolete",
  controlled_copy: "Issue copy",
};

function DraftModal({ onClose, onDone }: { onClose: () => void; onDone: (code: string) => void }) {
  const { siteId } = useSiteId();
  const { me } = useMe();
  const [documentCode, setDocumentCode] = useState("");
  // Declared after documentCode: the success callback closes over it to re-run the caller's lookup.
  const { busy, error, run } = useCommand(() => onDone(documentCode));
  const [documentType, setDocumentType] = useState(DOCUMENT_TYPES[0]);
  const [versionLabel, setVersionLabel] = useState("1.0");
  const [contentHash, setContentHash] = useState("");
  const [isExternal, setIsExternal] = useState(false);
  const [externalSource, setExternalSource] = useState("");

  return (
    <Modal open onClose={onClose} title="New document draft" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!siteId || !me) return;
          run(() =>
            api.post("/documents/v1/drafts", {
              idempotency_key: newIdempotencyKey(),
              site_id: siteId,
              document_code: documentCode,
              document_type: documentType,
              owner_subject_id: me.user_id,
              version_label: versionLabel,
              content_hash: contentHash,
              is_external: isExternal,
              external_source: isExternal ? externalSource : null,
            })
          );
        }}
      >
        <div className="grid grid-cols-3 gap-4">
          <Field label="Document code" required>
            <Input value={documentCode} onChange={(e) => setDocumentCode(e.target.value)} placeholder="SOP-QA-001" required autoFocus />
          </Field>
          <Field label="Type" required>
            <Select value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
              {DOCUMENT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Version label" required>
            <Input value={versionLabel} onChange={(e) => setVersionLabel(e.target.value)} required />
          </Field>
        </div>
        <Field
          label="Content hash"
          required
          hint="Digest of the authored content. It is what the released version is bound to - the document body itself lives in the Vault."
        >
          <Input value={contentHash} onChange={(e) => setContentHash(e.target.value)} required />
        </Field>
        <label className="flex items-center gap-2 fs-2 mb-3">
          <input type="checkbox" checked={isExternal} onChange={(e) => setIsExternal(e.target.checked)} />
          Externally authored document
        </label>
        {isExternal && (
          <Field label="External source" required>
            <Input value={externalSource} onChange={(e) => setExternalSource(e.target.value)} required />
          </Field>
        )}
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !documentCode.trim() || !siteId}>
            {busy ? "Creating…" : "Create draft"}
          </Button>
        </div>
      </form>
    </Modal>
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
          <Field label="Reviewer (user ID)" required hint="SOD-005: the author should not approve their own document.">
            <Input value={reviewer} onChange={(e) => setReviewer(e.target.value)} required autoFocus />
          </Field>
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
