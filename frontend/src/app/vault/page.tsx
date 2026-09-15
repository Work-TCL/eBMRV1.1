"use client";

import { useEffect, useState } from "react";
import { api, ApiError, canCorrectVault, newIdempotencyKey } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { SignedJsonForm } from "@/components/shared/SignedJsonForm";

// Matches app/modules/vault/router.py::_object_dict.
interface VaultObject {
  object_id: string;
  site_id: string | null;
  object_type: string;
  business_id: string;
  internal_version: number;
  business_version_label: string | null;
  status: string;
  digest_algorithm: string;
  digest: string;
  canonical_payload: Record<string, unknown>;
  effective_from: string | null;
  effective_to: string | null;
  supersedes_object_id: string | null;
  corrected_from_object_id: string | null;
  retention_class: string | null;
  released_at: string;
  created_by_subject: string | null;
}

const OBJECT_TYPES = ["batch", "material_lot", "rule"];

export default function VaultPage() {
  const [objectType, setObjectType] = useState(OBJECT_TYPES[0]);
  const [businessId, setBusinessId] = useState("");
  const [versions, setVersions] = useState<VaultObject[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<VaultObject | null>(null);

  async function performLookup() {
    if (!businessId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<VaultObject[]>(
        `/vault/v1/business/${encodeURIComponent(objectType)}/${encodeURIComponent(businessId.trim())}/versions`
      );
      setVersions(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Lookup failed");
      setVersions(null);
    } finally {
      setLoading(false);
    }
  }

  function onSubmitLookup(e: React.FormEvent) {
    e.preventDefault();
    performLookup();
  }

  return (
    <div>
      <PageHead
        title="Vault"
        subtitle="Immutable release history - every batch release and material-lot disposition gets a hash-verified snapshot here."
      />

      <form onSubmit={onSubmitLookup} className="flex items-end gap-4 mb-4" style={{ flexWrap: "wrap" }}>
        <Field label="Record type">
          <Select value={objectType} onChange={(e) => setObjectType(e.target.value)} style={{ maxWidth: 180 }}>
            {OBJECT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Business ID" hint="Batch number, internal lot number, or rule ID.">
          <Input
            value={businessId}
            onChange={(e) => setBusinessId(e.target.value)}
            placeholder="e.g. B-2026-031"
            style={{ minWidth: 220 }}
          />
        </Field>
        <Button type="submit" variant="primary" disabled={loading || !businessId.trim()}>
          <Icon name="search" /> {loading ? "Looking up…" : "Look up"}
        </Button>
      </form>

      {error && (
        <Card>
          <p className="error-text" style={{ padding: "var(--space-4, 16px)" }}>
            {error}
          </p>
        </Card>
      )}

      {versions && !error && (
        <Card>
          <CardHeader title={`${objectType} / ${businessId}`} />
          {versions.length === 0 ? (
            <EmptyState icon="lock">No released version exists for this record yet.</EmptyState>
          ) : (
            <Table>
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Released at</th>
                  <th>Supersedes</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v) => (
                  <tr key={v.object_id}>
                    <td className="font-semibold tabular">v{v.internal_version}</td>
                    <td>{v.status}</td>
                    <td className="tabular fs-2">{new Date(v.released_at).toLocaleString()}</td>
                    <td className="tabular fs-1">{v.supersedes_object_id ? v.supersedes_object_id.slice(0, 8) : "—"}</td>
                    <td style={{ textAlign: "right" }}>
                      <Button size="sm" variant="secondary" onClick={() => setSelected(v)}>
                        View
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}

      {selected && (
        <ObjectDetailModal
          object={selected}
          onClose={() => setSelected(null)}
          onCorrected={() => {
            setSelected(null);
            performLookup();
          }}
        />
      )}

      <SignedJsonForm
        title="Release a master record to the vault - signed"
        subtitle="The generic release path - domain modules that already run their own release ceremony (batch release, material lot disposition) never reach this; use it only for a record type with no dedicated release flow of its own."
        root="/vault/v1"
        ops={[
          {
            postPath: "masters/{object_type}/{business_id}/release",
            challengePath: "masters/{object_type}/{business_id}/signature-challenges",
            action: "release",
            label: "Release a master record",
            mirrorBodyInChallenge: true,
            fields: [
              { name: "object_type", label: "Object type", required: true },
              { name: "business_id", label: "Business ID", required: true },
              { name: "canonical_payload", label: "Canonical payload", type: "kv", required: true, hint: "The exact record content being released, as key/value pairs." },
              { name: "business_version_label", label: "Business version label", hint: "Optional." },
              {
                name: "evidence", label: "Evidence", type: "repeat", itemLabel: "Evidence item",
                subFields: [
                  { name: "evidence_id", label: "Evidence object ID", required: true },
                  { name: "evidence_sha256", label: "SHA-256", required: true },
                  { name: "media_type", label: "Media type" },
                  { name: "sequence", label: "Sequence", type: "number" },
                ],
              },
            ],
          },
        ]}
      />
    </div>
  );
}

function ObjectDetailModal({
  object,
  onClose,
  onCorrected,
}: {
  object: VaultObject;
  onClose: () => void;
  onCorrected: () => void;
}) {
  const { me } = useMe();
  const [integrity, setIntegrity] = useState<{ digest_valid: boolean; link_valid: boolean } | null>(null);
  const [checking, setChecking] = useState(false);
  const [correctionOpen, setCorrectionOpen] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);

  async function checkIntegrity() {
    setChecking(true);
    try {
      const result = await api.get<{ digest_valid: boolean; link_valid: boolean }>(
        `/vault/v1/objects/${object.object_id}/integrity`
      );
      setIntegrity(result);
    } catch {
      setIntegrity(null);
    } finally {
      setChecking(false);
    }
  }


  return (
    <Modal open onClose={onClose} title={`${object.object_type} / ${object.business_id} - v${object.internal_version}`} large>
      <div className="mb-4">
        {(
          [
            ["Status", object.status],
            ["Digest", `${object.digest_algorithm}:${object.digest}`],
            ["Effective from", object.effective_from ? new Date(object.effective_from).toLocaleString() : "—"],
            ["Retention class", object.retention_class ?? "—"],
            ["Corrected from", object.corrected_from_object_id ?? "—"],
          ] as [string, string][]
        ).map(([label, value]) => (
          <div key={label} className="flex gap-3 fs-2" style={{ padding: "4px 0" }}>
            <span className="text-muted" style={{ minWidth: 130, flexShrink: 0 }}>
              {label}
            </span>
            <span className="tabular" style={{ wordBreak: "break-all" }}>
              {value}
            </span>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3 mb-3">
        <Button size="sm" variant="secondary" onClick={checkIntegrity} disabled={checking}>
          <Icon name="shield-check" /> {checking ? "Checking…" : "Verify integrity"}
        </Button>
        {integrity && (
          <span className={integrity.digest_valid && integrity.link_valid ? "text-muted" : "error-text"}>
            {integrity.digest_valid && integrity.link_valid
              ? "Digest and chain link both verify."
              : `Tampering detected - digest_valid=${integrity.digest_valid}, link_valid=${integrity.link_valid}`}
          </span>
        )}
      </div>

      {object.supersedes_object_id && (
        <div className="mb-2">
          <Button size="sm" variant="ghost" onClick={() => setCompareOpen(true)}>
            <Icon name="arrow-left" /> Compare with previous version
          </Button>
        </div>
      )}
      <JsonPanel title="Canonical payload" value={object.canonical_payload} />

      {compareOpen && object.supersedes_object_id && (
        <CompareModal
          current={object}
          previousObjectId={object.supersedes_object_id}
          onClose={() => setCompareOpen(false)}
        />
      )}

      {correctionOpen && (
        <RequestCorrectionModal
          object={object}
          onClose={() => setCorrectionOpen(false)}
          onDone={() => {
            setCorrectionOpen(false);
            onCorrected();
          }}
        />
      )}

      {canCorrectVault(me) && (
        <div className="mt-4">
          <Button variant="secondary" onClick={() => setCorrectionOpen(true)}>
            Request correction
          </Button>
        </div>
      )}
    </Modal>
  );
}

function RequestCorrectionModal({
  object,
  onClose,
  onDone,
}: {
  object: VaultObject;
  onClose: () => void;
  onDone: () => void;
}) {
  const [reasonCode, setReasonCode] = useState("DATA_ENTRY_ERROR");
  const [reasonText, setReasonText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post(`/vault/v1/objects/${object.object_id}/corrections`, {
        idempotency_key: newIdempotencyKey(),
        record_object_id: object.object_id,
        reason_code: reasonCode,
        reason_text: reasonText,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Request correction">
      <form onSubmit={onSubmit}>
        <Field label="Reason code" required>
          <Select value={reasonCode} onChange={(e) => setReasonCode(e.target.value)}>
            <option value="DATA_ENTRY_ERROR">Data entry error</option>
            <option value="MISSING_INFORMATION">Missing information</option>
            <option value="OTHER">Other</option>
          </Select>
        </Field>
        <Field label="Reason" required error={error}>
          <textarea className="input" rows={3} value={reasonText} onChange={(e) => setReasonText(e.target.value)} required />
        </Field>
        <p className="hint mb-3">
          This only records the request. Completing a correction requires a signature policy this deployment
          hasn&apos;t defined yet - it will correctly fail closed until one exists.
        </p>
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !reasonText.trim()}>
            {busy ? "Submitting…" : "Submit request"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function CompareModal({
  current,
  previousObjectId,
  onClose,
}: {
  current: VaultObject;
  previousObjectId: string;
  onClose: () => void;
}) {
  const [previous, setPrevious] = useState<VaultObject | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<VaultObject>(`/vault/v1/objects/${previousObjectId}`)
      .then((o) => {
        if (!cancelled) setPrevious(o);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not load previous version");
      });
    return () => {
      cancelled = true;
    };
  }, [previousObjectId]);

  const changedKeys = previous
    ? Array.from(
        new Set([...Object.keys(previous.canonical_payload), ...Object.keys(current.canonical_payload)])
      ).filter(
        (k) =>
          JSON.stringify(previous.canonical_payload[k]) !== JSON.stringify(current.canonical_payload[k])
      )
    : [];

  return (
    <Modal
      open
      onClose={onClose}
      large
      title={`Compare - ${current.object_type} / ${current.business_id}`}
    >
      {error && <p className="error-text mb-3">{error}</p>}
      {!previous && !error && <p className="text-muted">Loading previous version…</p>}
      {previous && (
        <>
          <p className="fs-2 mb-3">
            {changedKeys.length === 0 ? (
              "Canonical payloads are identical."
            ) : (
              <>
                Changed keys: <span className="tabular">{changedKeys.join(", ")}</span>
              </>
            )}
          </p>
          <div className="grid grid-cols-2 gap-4">
 <JsonPanel title={`Previous v${previous.internal_version}`} value={previous.canonical_payload} />
 <JsonPanel title={`Current v${current.internal_version}`} value={current.canonical_payload} />
          </div>
        </>
      )}
    </Modal>
  );
}
