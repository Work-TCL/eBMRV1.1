"use client";

import { useEffect, useState } from "react";
import { api, ApiError, canAuthorProduct, newIdempotencyKey } from "@/lib/api";
import { useMe, useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

// Matches app/modules/product_master/router.py::_version_dict / _constituent_dict.
interface Constituent {
  id: string;
  constituent_type: string;
  role_code: string | null;
  constituent_business_id: string;
  constituent_version_id: string;
  source_site_id: string | null;
  tracking_strategy: string | null;
  sequence_no: number | null;
}

interface ProductVersion {
  product_version_id: string;
  product_business_id: string;
  version_no: number;
  product_code: string;
  name: string;
  product_family_id: string | null;
  lifecycle_state: string;
  manufacturing_profile_code: string;
  combination_product_type: string | null;
  sterile_profile_id: string | null;
  udi_applicable: boolean | null;
  device_model_code: string | null;
  effective_from: string | null;
  effective_to: string | null;
  released_vault_object_id: string | null;
  version_hash: string | null;
  version: number;
  site_id: string;
  constituents?: Constituent[];
}

const MANUFACTURING_PROFILES = ["pharma", "device", "injectable_ddcp", "inhalation_ddcp", "drug_eluting_device"];

export default function ProductMasterPage() {
  const { me } = useMe();
  const [businessId, setBusinessId] = useState("");
  const [versions, setVersions] = useState<ProductVersion[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftOpen, setDraftOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  async function performLookup() {
    if (!businessId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<ProductVersion[]>(`/products/v1/${encodeURIComponent(businessId.trim())}/versions`);
      setVersions(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Lookup failed");
      setVersions(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHead
        title="Product Master"
        subtitle="Document 09 — Product, Constituent & Regulatory Profile Master. Draft, author constituents, and release."
        action={
          canAuthorProduct(me) ? (
            <Button variant="primary" onClick={() => setDraftOpen(true)}>
              <Icon name="plus" /> New draft
            </Button>
          ) : undefined
        }
      />

      <p className="hint mb-4">
        This is the real Document 09 master — separate from the legacy <code>Products</code> page, which
        still feeds batch creation until Document 10/11 wire the two together.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          performLookup();
        }}
        className="flex items-end gap-4 mb-4"
      >
        <Field label="Product business ID">
          <Input value={businessId} onChange={(e) => setBusinessId(e.target.value)} placeholder="e.g. PRD-1" style={{ minWidth: 240 }} />
        </Field>
        <Button type="submit" variant="secondary" disabled={loading || !businessId.trim()}>
          <Icon name="search" /> {loading ? "Looking up…" : "Look up versions"}
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
          <CardHeader title={businessId} />
          {versions.length === 0 ? (
            <EmptyState icon="package">No versions exist for this product yet.</EmptyState>
          ) : (
            <Table>
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Name</th>
                  <th>State</th>
                  <th>Profile</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v) => (
                  <tr key={v.product_version_id}>
                    <td className="font-semibold tabular">{v.version_no}</td>
                    <td>{v.name}</td>
                    <td>{v.lifecycle_state}</td>
                    <td className="fs-2">{v.manufacturing_profile_code}</td>
                    <td style={{ textAlign: "right" }}>
                      <Button size="sm" variant="secondary" onClick={() => setSelectedId(v.product_version_id)}>
                        Open
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}

      {draftOpen && (
        <DraftModal
          onClose={() => setDraftOpen(false)}
          onDone={(newBusinessId) => {
            setDraftOpen(false);
            setBusinessId(newBusinessId);
            performLookup();
          }}
        />
      )}

      {selectedId && (
        <VersionDetailModal
          productVersionId={selectedId}
          onClose={() => setSelectedId(null)}
          onChanged={() => {
            setSelectedId(null);
            performLookup();
          }}
        />
      )}
    </div>
  );
}

function DraftModal({ onClose, onDone }: { onClose: () => void; onDone: (businessId: string) => void }) {
  const { sites } = useSites();
  const [businessId, setBusinessId] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [versionNo, setVersionNo] = useState("1");
  const [siteId, setSiteId] = useState("");
  const [profile, setProfile] = useState(MANUFACTURING_PROFILES[0]);
  const [udiApplicable, setUdiApplicable] = useState(false);
  const [deviceModelCode, setDeviceModelCode] = useState("");
  const [sterileProfileId, setSterileProfileId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/products/v1/drafts", {
        idempotency_key: newIdempotencyKey(),
        product_business_id: businessId,
        product_code: code || businessId,
        name,
        version_no: Number(versionNo),
        site_id: siteId,
        manufacturing_profile_code: profile,
        udi_applicable: udiApplicable,
        device_model_code: deviceModelCode || null,
        sterile_profile_id: sterileProfileId || null,
      });
      onDone(businessId);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to create draft");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="New product draft" large>
      <form onSubmit={onSubmit}>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Business ID" required>
            <Input value={businessId} onChange={(e) => setBusinessId(e.target.value)} required autoFocus />
          </Field>
          <Field label="Product code" hint="Defaults to business ID">
            <Input value={code} onChange={(e) => setCode(e.target.value)} />
          </Field>
          <Field label="Version no." required>
            <Input type="number" min={1} value={versionNo} onChange={(e) => setVersionNo(e.target.value)} required />
          </Field>
        </div>
        <Field label="Name" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Site" required>
            <Select value={siteId} onChange={(e) => setSiteId(e.target.value)} required>
              <option value="">Select a site…</option>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Manufacturing profile" required>
            <Select value={profile} onChange={(e) => setProfile(e.target.value)}>
              {MANUFACTURING_PROFILES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Sterile process profile ID" hint="Required if profile is injectable/inhalation DDCP (PRD-FR-010)">
            <Input value={sterileProfileId} onChange={(e) => setSterileProfileId(e.target.value)} />
          </Field>
          <Field label="Device model code" hint="Required if UDI applicable (PRD-FR-012)">
            <Input value={deviceModelCode} onChange={(e) => setDeviceModelCode(e.target.value)} />
          </Field>
        </div>
        <label className="flex items-center gap-2 fs-2 mb-3">
          <input type="checkbox" checked={udiApplicable} onChange={(e) => setUdiApplicable(e.target.checked)} />
          UDI applicable
        </label>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !businessId.trim() || !name.trim() || !siteId}>
            {busy ? "Creating…" : "Create draft"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

interface CompatibilityRow {
  id: string;
  compatibility_code: string;
  version_no: number;
  drug_constituent_version_id: string;
  device_constituent_version_id: string;
  interface_constraints: Record<string, unknown> | null;
  status: string;
  effective_from: string | null;
  effective_to: string | null;
}

function VersionDetailModal({
  productVersionId,
  onClose,
  onChanged,
}: {
  productVersionId: string;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { me } = useMe();
  const [version, setVersion] = useState<ProductVersion | null>(null);
  const [eligibility, setEligibility] = useState<{ eligible: boolean; checks: Record<string, unknown> } | null>(null);
  const [compatibility, setCompatibility] = useState<CompatibilityRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productVersionId]);

  async function refresh() {
    const [v, e, c] = await Promise.all([
      api.get<ProductVersion>(`/products/v1/${productVersionId}`),
      api.get<{ eligible: boolean; checks: Record<string, unknown> }>(`/products/v1/${productVersionId}/issue-eligibility`),
      api.get<CompatibilityRow[]>(`/products/v1/${productVersionId}/compatibility`).catch(() => [] as CompatibilityRow[]),
    ]);
    setVersion(v);
    setEligibility(e);
    setCompatibility(c);
  }

  async function runAction(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await refresh();
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const submit = () =>
    runAction(() =>
      api.post(`/products/v1/drafts/${productVersionId}/submit`, {
        idempotency_key: newIdempotencyKey(),
        product_version_id: productVersionId,
        expected_version: version!.version,
      })
    );

  const validateCompleteness = () =>
    runAction(() =>
      api.post(`/products/v1/${productVersionId}/validate-completeness`, {
        idempotency_key: newIdempotencyKey(),
        product_version_id: productVersionId,
      })
    );

  const release = () =>
    runAction(() =>
      api.post(`/products/v1/drafts/${productVersionId}/release`, {
        idempotency_key: newIdempotencyKey(),
        product_version_id: productVersionId,
        expected_version: version!.version,
      })
    );

  const suspend = () =>
    runAction(() =>
      api.post(`/products/v1/${productVersionId}/suspend`, {
        idempotency_key: newIdempotencyKey(),
        product_version_id: productVersionId,
        expected_version: version!.version,
        reason: "Suspended from Product Master UI",
      })
    );

  const reinstate = () =>
    runAction(() =>
      api.post(`/products/v1/${productVersionId}/reinstate`, {
        idempotency_key: newIdempotencyKey(),
        product_version_id: productVersionId,
        expected_version: version!.version,
        reason: "Reinstated from Product Master UI",
      })
    );

  if (!version) {
    return (
      <Modal open onClose={onClose} title="Loading…">
        {error ? <p className="error-text">{error}</p> : <p>Loading…</p>}
      </Modal>
    );
  }

  const findings = (eligibility?.checks.completeness_findings as string[] | undefined) ?? [];

  return (
    <Modal open onClose={onClose} title={`${version.name} — v${version.version_no}`} large>
      <div className="mb-4">
        {(
          [
            ["Business ID", version.product_business_id],
            ["Lifecycle state", version.lifecycle_state],
            ["Manufacturing profile", version.manufacturing_profile_code],
            ["Released vault object", version.released_vault_object_id ?? "—"],
            ["Version hash", version.version_hash ?? "—"],
          ] as [string, string][]
        ).map(([label, value]) => (
          <div key={label} className="flex gap-3 fs-2" style={{ padding: "4px 0" }}>
            <span className="text-muted" style={{ minWidth: 170, flexShrink: 0 }}>
              {label}
            </span>
            <span className="tabular" style={{ wordBreak: "break-all" }}>
              {value}
            </span>
          </div>
        ))}
      </div>

      <p className="fs-1 text-muted mb-1">Constituents</p>
      {!version.constituents || version.constituents.length === 0 ? (
        <p className="hint mb-3">No constituents declared on this version.</p>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Role</th>
              <th>Business ID</th>
            </tr>
          </thead>
          <tbody>
            {version.constituents.map((c) => (
              <tr key={c.id}>
                <td>{c.constituent_type}</td>
                <td>{c.role_code ?? "—"}</td>
                <td className="fs-2">{c.constituent_business_id}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <div className="mt-4">
        <p className="fs-1 text-muted mb-1">DDCP constituent compatibility</p>
        {compatibility.length === 0 ? (
          <p className="hint mb-3">
            No cross-constituent compatibility record references this version.
          </p>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Ver</th>
                <th>Status</th>
                <th>Effective</th>
                <th>Interface constraints</th>
              </tr>
            </thead>
            <tbody>
              {compatibility.map((c) => (
                <tr key={c.id}>
                  <td className="tabular">{c.compatibility_code}</td>
                  <td className="tabular">v{c.version_no}</td>
                  <td>{c.status}</td>
                  <td className="fs-2 tabular">
                    {c.effective_from ? new Date(c.effective_from).toLocaleDateString() : "—"}
                    {c.effective_to ? ` → ${new Date(c.effective_to).toLocaleDateString()}` : ""}
                  </td>
                  <td className="fs-1 tabular" style={{ wordBreak: "break-word" }}>
                    {c.interface_constraints ? JSON.stringify(c.interface_constraints) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      {eligibility && (
        <div className="mt-4">
          <p className="fs-1 text-muted mb-1">Issue eligibility</p>
          <p className={eligibility.eligible ? "fs-2" : "error-text fs-2"}>
            {eligibility.eligible ? "Eligible to issue" : "Not eligible"}
            {" — site admission: not yet implemented (SG-043)"}
          </p>
          {findings.length > 0 && (
            <ul className="fs-2" style={{ paddingLeft: "1.2em" }}>
              {findings.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {error && <p className="error-text mt-3">{error}</p>}

      <div className="flex justify-between gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        <div className="flex gap-2">
          {canAuthorProduct(me) && version.lifecycle_state === "draft" && (
            <>
              <Button variant="secondary" onClick={validateCompleteness} disabled={busy}>
                Check completeness
              </Button>
              <Button variant="primary" onClick={submit} disabled={busy}>
                Submit for review
              </Button>
            </>
          )}
          {canAuthorProduct(me) && version.lifecycle_state === "under_review" && (
            <Button variant="success" onClick={release} disabled={busy}>
              {busy ? "Releasing…" : "Release"}
            </Button>
          )}
          {canAuthorProduct(me) && version.lifecycle_state === "released" && (
            <Button variant="danger" onClick={suspend} disabled={busy}>
              Suspend
            </Button>
          )}
          {canAuthorProduct(me) && version.lifecycle_state === "suspended" && (
            <Button variant="primary" onClick={reinstate} disabled={busy}>
              Reinstate
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
