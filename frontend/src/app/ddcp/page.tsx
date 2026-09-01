"use client";

import { useState } from "react";
import { api, ApiError, holdsAnyRole, newIdempotencyKey, type MutationReceipt } from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";

interface DdcpType {
  key: string;
  label: string;
  /** router prefix, e.g. /ddcp/v1/prefilled-syringe */
  prefix: string;
  subtypeHint: string;
  hasProfileGet: boolean;
  hasGenealogy: boolean;
  hasReviewSummary: boolean;
  /** POST operations under the prefix, for the free-form execution/results form. */
  writeOps: string[];
}

const TYPES: DdcpType[] = [
  {
    key: "pfs",
    label: "Prefilled syringe / injectable (Doc 54)",
    prefix: "/ddcp/v1/prefilled-syringe",
    subtypeHint: "e.g. staked-needle, luer-lock",
    hasProfileGet: true,
    hasGenealogy: true,
    hasReviewSummary: true,
    writeOps: [
      "constituent-handoffs",
      "fill-operations",
      "production-counts",
      "device-assembly",
      "functional-tests",
      "stability-retain-samples",
    ],
  },
  {
    key: "auto",
    label: "Autoinjector (Doc 55)",
    prefix: "/ddcp/v1/autoinjector",
    subtypeHint: "e.g. single-use, reusable",
    hasProfileGet: false,
    hasGenealogy: false,
    hasReviewSummary: false,
    writeOps: [
      "assembly-operations",
      "drug-container-bindings",
      "functional-tests",
      "dose-delivery-results",
      "unit-dispositions",
      "reusable-device-pairings",
    ],
  },
  {
    key: "inh",
    label: "Inhalation — MDI / DPI (Doc 56)",
    prefix: "/ddcp/v1/inhalation",
    subtypeHint: "MDI | DPI",
    hasProfileGet: false,
    hasGenealogy: true,
    hasReviewSummary: false,
    writeOps: [
      "fill-runs",
      "closure-results",
      "dose-tests",
      "dose-counter-tests",
      "dose-unit-bindings",
    ],
  },
  {
    key: "coat",
    label: "Coated / combination device (Doc 57)",
    prefix: "/ddcp/v1/coated-device",
    subtypeHint: "e.g. drug-eluting stent",
    hasProfileGet: false,
    hasGenealogy: false,
    hasReviewSummary: false,
    writeOps: [
      "coating-runs",
      "drug-coating-usage",
      "device-coating-bindings",
      "drug-loading-results",
      "post-sterilization-tests",
      "functional-tests",
      "unit-dispositions",
    ],
  },
];

export default function DdcpPage() {
  const { me } = useMe();
  const [typeKey, setTypeKey] = useState(TYPES[0].key);
  const type = TYPES.find((t) => t.key === typeKey)!;
  const canAuthor = holdsAnyRole(me, ["Admin", "QA Reviewer", "Supervisor"]);

  return (
    <div>
      <PageHead
        title="DDCP product profiles"
        subtitle="Documents 54–57 — drug/device combination-product profiles: design, batch readiness, execution and release."
      />

      <Card pad className="mb-4">
        <Field label="Product family">
          <Select value={typeKey} onChange={(e) => setTypeKey(e.target.value)} style={{ minWidth: 360 }}>
            {TYPES.map((t) => (
              <option key={t.key} value={t.key}>
                {t.label}
              </option>
            ))}
          </Select>
        </Field>
      </Card>

      {!canAuthor && (
        <Banner tone="info" title="Read-only">
          Authoring and releasing profiles needs the QA Reviewer or Supervisor role.
        </Banner>
      )}

      {canAuthor && <ProfileCard type={type} />}
      <BatchCard type={type} canAuthor={canAuthor} />
      {canAuthor && <ExecutionCard type={type} />}
    </div>
  );
}

function ProfileCard({ type }: { type: DdcpType }) {
  const { siteId } = useSiteId();
  const [profileCode, setProfileCode] = useState("");
  const [subtype, setSubtype] = useState("");
  const [architecture, setArchitecture] = useState("{}");
  const [controls, setControls] = useState("{}");
  const [requirements, setRequirements] = useState("[]");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newId, setNewId] = useState<string | null>(null);

  // release
  const [releaseId, setReleaseId] = useState("");
  const [expectedVersion, setExpectedVersion] = useState("1");
  const [changeRef, setChangeRef] = useState("");
  const [releaseBusy, setReleaseBusy] = useState(false);
  const [releaseMsg, setReleaseMsg] = useState<string | null>(null);

  // lookup
  const [lookupId, setLookupId] = useState("");
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNewId(null);
    try {
      const receipt = await api.post<MutationReceipt>(`${type.prefix}/profiles`, {
        idempotency_key: newIdempotencyKey(),
        ...(siteId ? { site_id: siteId } : {}),
        profile_code: profileCode.trim(),
        subtype: subtype.trim() || null,
        constituent_architecture: JSON.parse(architecture),
        required_controls: JSON.parse(controls),
        constituent_requirements: JSON.parse(requirements),
      });
      setNewId(receipt.aggregate_id);
      setReleaseId(receipt.aggregate_id);
    } catch (err) {
      if (err instanceof SyntaxError) setError(`Invalid JSON: ${err.message}`);
      else setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function release(e: React.FormEvent) {
    e.preventDefault();
    setReleaseBusy(true);
    setReleaseMsg(null);
    try {
      await api.post<MutationReceipt>(`${type.prefix}/profiles/${releaseId.trim()}/release`, {
        idempotency_key: newIdempotencyKey(),
        profile_id: releaseId.trim(),
        expected_version: Number(expectedVersion),
        change_ref: changeRef.trim() || null,
      });
      setReleaseMsg("Profile released.");
    } catch (err) {
      setReleaseMsg(err instanceof ApiError ? `${err.code}: ${err.message}` : "Release failed");
    } finally {
      setReleaseBusy(false);
    }
  }

  async function lookup(e: React.FormEvent) {
    e.preventDefault();
    setProfile(null);
    try {
      setProfile(await api.get<Record<string, unknown>>(`${type.prefix}/profiles/${lookupId.trim()}`));
    } catch (err) {
      setProfile({ error: err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed" });
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Profile designer" />
      <form onSubmit={create} className="grid grid-cols-2 gap-4 mt-3">
        <Field label="Profile code" required>
          <Input value={profileCode} onChange={(e) => setProfileCode(e.target.value)} required />
        </Field>
        <Field label="Subtype" hint={type.subtypeHint}>
          <Input value={subtype} onChange={(e) => setSubtype(e.target.value)} />
        </Field>
        <Field label="Constituent architecture (JSON)">
          <textarea className="input" rows={3} value={architecture} onChange={(e) => setArchitecture(e.target.value)} spellCheck={false} />
        </Field>
        <Field label="Required controls (JSON)">
          <textarea className="input" rows={3} value={controls} onChange={(e) => setControls(e.target.value)} spellCheck={false} />
        </Field>
        <Field label="Constituent requirements (JSON array)" hint="[{constituent_type, component_role, required_state}]">
          <textarea className="input" rows={3} value={requirements} onChange={(e) => setRequirements(e.target.value)} spellCheck={false} />
        </Field>
        <div style={{ gridColumn: "1 / -1" }}>
          {error && <p className="error-text mb-2">{error}</p>}
          {newId && (
            <Banner tone="ok" title="Profile version created (draft)">
              Profile ID <span className="tabular">{newId}</span>
            </Banner>
          )}
          <Button type="submit" variant="primary" disabled={busy || !profileCode.trim()}>
            {busy ? "Creating…" : "Create profile version"}
          </Button>
        </div>
      </form>

      <div className="mt-4" style={{ borderTop: "1px solid var(--border-hairline)", paddingTop: "var(--space-3)" }}>
        <p className="fs-1 text-muted mb-2">Release a profile version</p>
        <form onSubmit={release} className="flex items-end gap-3" style={{ flexWrap: "wrap" }}>
          <Field label="Profile ID">
            <Input value={releaseId} onChange={(e) => setReleaseId(e.target.value)} style={{ minWidth: 260 }} />
          </Field>
          <Field label="Expected version">
            <Input type="number" value={expectedVersion} onChange={(e) => setExpectedVersion(e.target.value)} style={{ maxWidth: 120 }} />
          </Field>
          <Field label="Change ref">
            <Input value={changeRef} onChange={(e) => setChangeRef(e.target.value)} />
          </Field>
          <Button type="submit" variant="success" disabled={releaseBusy || !releaseId.trim()}>
            {releaseBusy ? "Releasing…" : "Release"}
          </Button>
        </form>
        {releaseMsg && <p className={releaseMsg === "Profile released." ? "fs-2 mt-2" : "error-text mt-2"}>{releaseMsg}</p>}
      </div>

      {type.hasProfileGet && (
        <div className="mt-4" style={{ borderTop: "1px solid var(--border-hairline)", paddingTop: "var(--space-3)" }}>
          <p className="fs-1 text-muted mb-2">Look up a profile version</p>
          <form onSubmit={lookup} className="flex items-end gap-3">
            <Field label="Profile ID">
              <Input value={lookupId} onChange={(e) => setLookupId(e.target.value)} style={{ minWidth: 260 }} />
            </Field>
            <Button type="submit" variant="secondary" disabled={!lookupId.trim()}>
              <Icon name="search" /> Look up
            </Button>
          </form>
          {profile && <div className="mt-3"><JsonPanel title="Profile" value={profile} /></div>}
        </div>
      )}
    </Card>
  );
}

function BatchCard({ type, canAuthor }: { type: DdcpType; canAuthor: boolean }) {
  const [batchId, setBatchId] = useState("");
  const [readiness, setReadiness] = useState<Record<string, unknown> | null>(null);
  const [genealogy, setGenealogy] = useState<Record<string, unknown> | null>(null);
  const [reviewSummary, setReviewSummary] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  async function load(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setReadiness(null);
    setGenealogy(null);
    setReviewSummary(null);
    const id = batchId.trim();
    try {
      setReadiness(await api.get<Record<string, unknown>>(`${type.prefix}/batches/${id}/readiness`));
      if (type.hasGenealogy) setGenealogy(await api.get<Record<string, unknown>>(`${type.prefix}/batches/${id}/genealogy`).catch(() => null));
      if (type.hasReviewSummary)
        setReviewSummary(await api.get<Record<string, unknown>>(`${type.prefix}/batches/${id}/review-summary`).catch(() => null));
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
    }
  }

  async function runBatchAction(seg: string, label: string) {
    setActionMsg(null);
    try {
      await api.post<MutationReceipt>(`${type.prefix}/batches/${batchId.trim()}/${seg}`, {
        idempotency_key: newIdempotencyKey(),
        batch_id: batchId.trim(),
      });
      setActionMsg(`${label} done.`);
    } catch (err) {
      setActionMsg(err instanceof ApiError ? `${err.code}: ${err.message}` : `${label} failed`);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Batch readiness & release" />
      <form onSubmit={load} className="flex items-end gap-3 mt-3">
        <Field label="Batch ID">
          <Input value={batchId} onChange={(e) => setBatchId(e.target.value)} style={{ minWidth: 320 }} />
        </Field>
        <Button type="submit" variant="secondary" disabled={!batchId.trim()}>
          <Icon name="search" /> Load
        </Button>
      </form>
      {error && <p className="error-text mt-3">{error}</p>}

      {readiness && (
        <>
          <div className="mt-3"><JsonPanel title="Readiness" value={readiness} /></div>
          {genealogy && <div className="mt-3"><JsonPanel title="Genealogy" value={genealogy} /></div>}
          {reviewSummary && <div className="mt-3"><JsonPanel title="Review summary" value={reviewSummary} /></div>}
          {canAuthor && (
            <div className="flex gap-2 mt-3">
              <Button variant="primary" onClick={() => runBatchAction("release-readiness", "Release-readiness assessment")}>
                Assess release readiness
              </Button>
              <Button variant="secondary" onClick={() => runBatchAction("evidence-package", "Evidence package")}>
                Freeze evidence package
              </Button>
            </div>
          )}
          {actionMsg && <p className="fs-2 mt-2">{actionMsg}</p>}
        </>
      )}
    </Card>
  );
}

function ExecutionCard({ type }: { type: DdcpType }) {
  const [opRaw, setOp] = useState(type.writeOps[0]);
  const [payload, setPayload] = useState("{\n  \n}");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  // Derive the effective op so a family change can't leave a stale value selected.
  const op = type.writeOps.includes(opRaw) ? opRaw : type.writeOps[0];

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setResult(null);
    try {
      const body = JSON.parse(payload);
      const receipt = await api.post<MutationReceipt>(`${type.prefix}/${op}`, {
        idempotency_key: newIdempotencyKey(),
        ...body,
      });
      setResult(`OK — ${receipt.command_id ? "command " + receipt.command_id : "recorded"}`);
    } catch (err) {
      if (err instanceof SyntaxError) setResult(`Invalid JSON: ${err.message}`);
      else setResult(err instanceof ApiError ? `${err.code}: ${err.message}` : "Submit failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad>
      <CardHeader title="Execution & result records" />
      <p className="fs-2 text-muted mb-3">
        The execution, IPC and functional-test records for this family carry structured payloads — submit
        them here as JSON. <code>idempotency_key</code> is added automatically.
      </p>
      <form onSubmit={submit}>
        <Field label="Operation">
          <Select value={op} onChange={(e) => setOp(e.target.value)}>
            {type.writeOps.map((o) => (
              <option key={o} value={o}>
                POST {type.prefix}/{o}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Payload (JSON)">
          <textarea className="input" rows={10} value={payload} onChange={(e) => setPayload(e.target.value)} spellCheck={false} />
        </Field>
        {result && <p className={result.startsWith("OK") ? "fs-2 mt-2" : "error-text mt-2"}>{result}</p>}
        <Button type="submit" variant="primary" disabled={busy} className="mt-2">
          {busy ? "Submitting…" : "Submit"}
        </Button>
      </form>
    </Card>
  );
}
