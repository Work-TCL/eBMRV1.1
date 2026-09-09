"use client";

import { useEffect, useState } from "react";
import {
  api,
  ApiError,
  canAuthorProduct,
  canReleaseProduct,
  clientPagedFetcher,
  holdsAnyRole,
  newIdempotencyKey,
} from "@/lib/api";
import { useApiResource, useMe, useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Modal } from "@/components/ui/Modal";
import { Field, RowButtonSlot } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { summarizeJson } from "@/components/ui/JsonPanel";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";

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
  pmoa_reference: string | null;
  part4_profile_code: string | null;
  sterile_profile_id: string | null;
  finished_tracking_strategy: string | null;
  udi_applicable: boolean | null;
  strength_value: string | null;
  strength_uom: string | null;
  device_model_code: string | null;
  effective_from: string | null;
  effective_to: string | null;
  released_vault_object_id: string | null;
  version_hash: string | null;
  version: number;
  site_id: string;
  constituents?: Constituent[];
}

// Matches app/modules/product_master/router.py::get_sterile_profiles — the real sterile-profile
// registry (Document 40 `equipment.aseptic_profile_versions`, RELEASED rows at the product's own site
// only). Replaces the free-text UUID field: sterile_profile_id is now chosen from an actual record, and
// the backend rejects anything else (PRD-FR-010, product_master/commands.py::_validate_sterile_profile).
interface SterileProfile {
  id: string;
  profile_number: string;
  version_no: number;
  state: string;
  required_area_classification: string | null;
}

function sterileProfileLabel(p: SterileProfile): string {
  return `${p.profile_number} v${p.version_no}${p.required_area_classification ? ` — ${p.required_area_classification}` : ""}`;
}

// Matches app/modules/product_master/router.py::get_business_ids — one row per distinct
// product_business_id (its highest version_no), used to populate the Constituent editor's Business ID
// field as a real picker instead of free-text (SG-081 read-side precedent: a plain read-only GET listing
// doesn't conflict with any future write/CRUD contract).
interface BusinessIdOption {
  product_version_id: string;
  product_business_id: string;
  name: string;
  version_no: number;
  lifecycle_state: string;
}

function businessIdOptionLabel(o: BusinessIdOption): string {
  return `${o.product_business_id} — ${o.name} (latest v${o.version_no}, ${o.lifecycle_state})`;
}

const MANUFACTURING_PROFILES = ["pharma", "device", "injectable_ddcp", "inhalation_ddcp", "drug_eluting_device"];
// STERILE_REQUIRED_PROFILES (services/gxp-api/app/modules/product_master/models.py) — matches the
// PRD-FR-010 completeness check exactly, so the UI can hint before Release ever blocks on it.
const STERILE_REQUIRED_PROFILES = ["injectable_ddcp", "inhalation_ddcp"];
// ddcp/models.py CONSTITUENT_TYPES — reused here for UI consistency only; product_master's own
// constituent_type column carries no matching DB/backend enum constraint (free text).
const CONSTITUENT_TYPES = ["DRUG", "BIOLOGIC", "DEVICE", "PACKAGING", "LABEL"];

// A constituent row being edited client-side, before/without a persisted `id` (matches
// commands.py::ConstituentInput — the command that (re)writes the whole constituent list).
interface ConstituentDraft {
  constituent_type: string;
  role_code: string;
  constituent_business_id: string;
  constituent_version_id: string;
  constituent_label: string; // display only — "<name> v<version_no> (<lifecycle_state>)"
  source_site_id: string;
  tracking_strategy: string;
  sequence_no: string;
}

function toConstituentDrafts(constituents: Constituent[] | undefined): ConstituentDraft[] {
  return (constituents ?? []).map((c) => ({
    constituent_type: c.constituent_type,
    role_code: c.role_code ?? "",
    constituent_business_id: c.constituent_business_id,
    constituent_version_id: c.constituent_version_id,
    constituent_label: c.constituent_business_id,
    source_site_id: c.source_site_id ?? "",
    tracking_strategy: c.tracking_strategy ?? "",
    sequence_no: c.sequence_no != null ? String(c.sequence_no) : "",
  }));
}

export default function ProductMasterPage() {
  const { me } = useMe();
  const [draftOpen, setDraftOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [historyBusinessId, setHistoryBusinessId] = useState<string | null>(null);
  const [historyVersions, setHistoryVersions] = useState<ProductVersion[] | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  // GET /products/v1/business-ids returns a plain array, not the server-side Paged<T> envelope
  // (Phase 1, small row counts — same ceiling `listAll`/`clientPagedFetcher` document) — DataTable's
  // search/sort/paging is done client-side over that array here.
  const fetchProducts = clientPagedFetcher<BusinessIdOption>(
    () => api.get<BusinessIdOption[]>("/products/v1/business-ids"),
    { searchText: (p) => `${p.product_business_id} ${p.name}` }
  );

  const productColumns: DataTableColumn<BusinessIdOption>[] = [
    {
      key: "product_business_id",
      header: "Business ID",
      sortable: true,
      render: (p) => <span className="font-semibold tabular">{p.product_business_id}</span>,
    },
    { key: "name", header: "Name", sortable: true },
    { key: "version_no", header: "Latest version", sortable: true, render: (p) => <span className="tabular fs-2">v{p.version_no}</span> },
    { key: "lifecycle_state", header: "State", sortable: true, render: (p) => <WorkflowStatePill state={p.lifecycle_state} /> },
    {
      key: "actions",
      header: "",
      render: (p) => (
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="ghost" onClick={() => showHistory(p.product_business_id)}>
            Versions
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setSelectedId(p.product_version_id)}>
            Open
          </Button>
        </div>
      ),
    },
  ];

  // "Versions" on a row reveals every version for that Business ID below the list — the released v1
  // alongside an in-progress draft v2, for example — without needing the removed manual lookup box.
  async function showHistory(businessId: string) {
    setHistoryBusinessId(businessId);
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      setHistoryVersions(await api.get<ProductVersion[]>(`/products/v1/${encodeURIComponent(businessId)}/versions`));
    } catch (err) {
      setHistoryError(err instanceof ApiError ? err.message : "Lookup failed");
      setHistoryVersions(null);
    } finally {
      setHistoryLoading(false);
    }
  }

  return (
    <div>
      <PageHead
        title="Product Master"
        subtitle="Product, Constituent & Regulatory Profile Master. Draft, author constituents, and release."
        action={
          canAuthorProduct(me) ? (
            <Button variant="primary" onClick={() => setDraftOpen(true)}>
              <Icon name="plus" /> New draft
            </Button>
          ) : undefined
        }
      />

      <p className="hint mb-4">
        This is the current product master — separate from the legacy Products page, which still feeds
        batch creation until the two are unified.
      </p>

      <Card className="mb-4">
        <CardHeader title="Products" meta="One row per Business ID, its latest version — click Versions for the full history." />
        <DataTable
          columns={productColumns}
          fetchPage={fetchProducts}
          rowKey={(p) => p.product_business_id}
          searchPlaceholder="Search by business ID or name…"
          emptyIcon="package"
          emptyMessage={<>No products drafted yet — use &quot;New draft&quot; above to create one.</>}
          defaultSort={{ by: "product_business_id", dir: "asc" }}
          reloadToken={reloadToken}
        />
      </Card>

      {historyBusinessId && (
        <Card>
          <CardHeader
            title={`Versions — ${historyBusinessId}`}
            meta={
              <Button size="sm" variant="ghost" onClick={() => setHistoryBusinessId(null)}>
                Close
              </Button>
            }
          />
          {historyLoading ? (
            <p className="hint" style={{ padding: "var(--space-4, 16px)" }}>
              Loading…
            </p>
          ) : historyError ? (
            <p className="error-text" style={{ padding: "var(--space-4, 16px)" }}>
              {historyError}
            </p>
          ) : !historyVersions || historyVersions.length === 0 ? (
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
                {historyVersions.map((v) => (
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
            setReloadToken((n) => n + 1);
            showHistory(newBusinessId);
          }}
        />
      )}

      {selectedId && (
        <VersionDetailModal
          productVersionId={selectedId}
          onClose={() => setSelectedId(null)}
          onChanged={() => {
            setSelectedId(null);
            setReloadToken((n) => n + 1);
            if (historyBusinessId) showHistory(historyBusinessId);
          }}
        />
      )}
    </div>
  );
}

/** Shared by DraftModal (create) and EditDraftModal (edit) — both send the same
 * `constituents: ConstituentInput[]` shape (commands.py), full-replace semantics. A constituent
 * references *another* Product Master version by its own Business ID (PRD-FR-004/006 — "meal kit"
 * analogy: drug/device are themselves Product Master records, the combination product just references
 * them). Business ID selection is a real dropdown (`GET /products/v1/business-ids`, one row per existing
 * product), not free text — picking one auto-runs the same by-Business-ID versions lookup the page's own
 * top-level search uses (`GET /products/v1/{business_id}/versions`) so the specific version can still be
 * picked below. */
function ConstituentEditor({
  constituents,
  onChange,
  sites,
}: {
  constituents: ConstituentDraft[];
  onChange: (next: ConstituentDraft[]) => void;
  sites: { id: string; name: string }[];
}) {
  const [type, setType] = useState(CONSTITUENT_TYPES[0]);
  const [roleCode, setRoleCode] = useState("");
  const [businessIdOptions, setBusinessIdOptions] = useState<BusinessIdOption[]>([]);
  const [businessIdOptionsError, setBusinessIdOptionsError] = useState<string | null>(null);
  const [lookupId, setLookupId] = useState("");
  const [lookupResults, setLookupResults] = useState<ProductVersion[] | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [lookupBusy, setLookupBusy] = useState(false);
  const [picked, setPicked] = useState<ProductVersion | null>(null);
  const [sourceSiteId, setSourceSiteId] = useState("");
  const [trackingStrategy, setTrackingStrategy] = useState("");
  const [sequenceNo, setSequenceNo] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .get<BusinessIdOption[]>("/products/v1/business-ids")
      .then((result) => {
        if (!cancelled) setBusinessIdOptions(result);
      })
      .catch((err) => {
        if (!cancelled) setBusinessIdOptionsError(err instanceof ApiError ? err.message : "Could not load Business IDs");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function runLookup(idOverride?: string) {
    const id = (idOverride ?? lookupId).trim();
    if (!id) return;
    setLookupBusy(true);
    setLookupError(null);
    setPicked(null);
    try {
      const result = await api.get<ProductVersion[]>(`/products/v1/${encodeURIComponent(id)}/versions`);
      setLookupResults(result);
      if (result.length === 0) setLookupError("No versions exist for this Business ID yet.");
    } catch (err) {
      setLookupError(err instanceof ApiError ? err.message : "Lookup failed");
      setLookupResults(null);
    } finally {
      setLookupBusy(false);
    }
  }

  function addConstituent() {
    if (!picked) return;
    onChange([
      ...constituents,
      {
        constituent_type: type,
        role_code: roleCode,
        constituent_business_id: picked.product_business_id,
        constituent_version_id: picked.product_version_id,
 constituent_label: `${picked.name} v${picked.version_no} (${picked.lifecycle_state})`,
        source_site_id: sourceSiteId,
        tracking_strategy: trackingStrategy,
        sequence_no: sequenceNo,
      },
    ]);
    setRoleCode("");
    setLookupId("");
    setLookupResults(null);
    setPicked(null);
    setSourceSiteId("");
    setTrackingStrategy("");
    setSequenceNo("");
  }

  return (
    <div className="mb-3">
      <p className="fact-k mb-1">Constituents</p>
      <p className="hint mb-2">
        Each constituent references another Product Master record by its own Business ID — the drug
        substance and the device component are themselves Product Master versions.
      </p>

      {constituents.length > 0 && (
        <Table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Role</th>
              <th>Constituent</th>
              <th>Source site</th>
              <th>Seq</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {constituents.map((c, i) => (
              <tr key={i}>
                <td className="fs-2">{c.constituent_type}</td>
                <td className="fs-2">{c.role_code || "—"}</td>
                <td className="fs-2">
                  {c.constituent_label} <span className="text-muted">({c.constituent_business_id})</span>
                </td>
                <td className="fs-2">{sites.find((s) => s.id === c.source_site_id)?.name ?? "—"}</td>
                <td className="tabular fs-2">{c.sequence_no || "—"}</td>
                <td style={{ textAlign: "right" }}>
                  <Button size="sm" variant="ghost" type="button" onClick={() => onChange(constituents.filter((_, idx) => idx !== i))}>
                    Remove
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <div style={{ border: "1px dashed var(--border-strong, #ccc)", borderRadius: 8, padding: 12 }}>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Type">
            <Select value={type} onChange={(e) => setType(e.target.value)}>
              {CONSTITUENT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Role code" hint="Free text, e.g. primary_drug / device_component.">
            <Input value={roleCode} onChange={(e) => setRoleCode(e.target.value)} />
          </Field>
        </div>

        {/* items-start, not items-end: the Business ID field carries a hint line below its select, which
         * items-end would bottom-align the row to instead of the select itself — dragging the button down
         * below the input it belongs beside. RowButtonSlot gives the button a same-height invisible label
         * so it still lines up with the select (see Field.tsx). */}
        <div className="flex flex-wrap items-start gap-3 mb-2">
          <Field
            label="Constituent's Business ID"
            hint="Picked from existing Product Master records — the drug/device must already have its own draft."
          >
            <Select
              value={lookupId}
              onChange={(e) => {
                const id = e.target.value;
                setLookupId(id);
                setLookupResults(null);
                setPicked(null);
                if (id) runLookup(id);
              }}
              style={{ minWidth: 260 }}
            >
              <option value="">Select a Business ID…</option>
              {businessIdOptions.map((o) => (
                <option key={o.product_business_id} value={o.product_business_id}>
                  {businessIdOptionLabel(o)}
                </option>
              ))}
            </Select>
          </Field>
          <RowButtonSlot>
            <Button type="button" variant="secondary" size="sm" disabled={lookupBusy || !lookupId.trim()} onClick={() => runLookup()}>
              {lookupBusy ? "Looking up…" : "Find versions"}
            </Button>
          </RowButtonSlot>
        </div>
        {businessIdOptionsError && <p className="error-text mb-2">{businessIdOptionsError}</p>}
        {lookupError && <p className="error-text mb-2">{lookupError}</p>}
        {lookupResults && lookupResults.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {lookupResults.map((v) => (
              <Button
                key={v.product_version_id}
                type="button"
                size="sm"
                variant={picked?.product_version_id === v.product_version_id ? "primary" : "secondary"}
                onClick={() => setPicked(v)}
              >
                  v{v.version_no} — {v.name} ({v.lifecycle_state})
              </Button>
            ))}
          </div>
        )}
        {picked && (
          <p className="hint mb-2">
            Selected: <strong>{picked.name}</strong> v{picked.version_no} ({picked.lifecycle_state})
          </p>
        )}

        <div className="grid grid-cols-3 gap-4">
          <Field label="Source site" hint="Optional.">
            <Select value={sourceSiteId} onChange={(e) => setSourceSiteId(e.target.value)}>
                <option value="">—</option>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Tracking strategy" hint="Optional, free text.">
            <Input value={trackingStrategy} onChange={(e) => setTrackingStrategy(e.target.value)} />
          </Field>
          <Field label="Sequence no." hint="Optional.">
            <Input type="number" value={sequenceNo} onChange={(e) => setSequenceNo(e.target.value)} />
          </Field>
        </div>
        <Button type="button" variant="secondary" size="sm" disabled={!picked} onClick={addConstituent}>
          <Icon name="plus" /> Add constituent
        </Button>
      </div>
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
  const [combinationProductType, setCombinationProductType] = useState("");
  const [strengthValue, setStrengthValue] = useState("");
  const [strengthUom, setStrengthUom] = useState("");
  const [pmoaReference, setPmoaReference] = useState("");
  const [part4ProfileCode, setPart4ProfileCode] = useState("");
  const [finishedTrackingStrategy, setFinishedTrackingStrategy] = useState("");
  const [constituents, setConstituents] = useState<ConstituentDraft[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const { data: sterileProfiles } = useApiResource<SterileProfile[]>(
    siteId ? `/products/v1/sterile-profiles?site_id=${siteId}` : null
  );
  useEffect(() => {
    // A site change invalidates any profile picked for the previous site (the registry is site-scoped).
    // This is a legitimate "reconcile local selection against freshly-fetched options" reset, not a
    // derived-state loop — the guard makes it converge in one pass.
    if (sterileProfileId && !(sterileProfiles ?? []).some((p) => p.id === sterileProfileId)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSterileProfileId("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId, sterileProfiles]);

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
        combination_product_type: combinationProductType || null,
        strength_value: strengthValue || null,
        strength_uom: strengthUom || null,
        pmoa_reference: pmoaReference || null,
        part4_profile_code: part4ProfileCode || null,
        finished_tracking_strategy: finishedTrackingStrategy || null,
        constituents: constituents.map((c) => ({
          constituent_type: c.constituent_type,
          role_code: c.role_code || null,
          constituent_business_id: c.constituent_business_id,
          constituent_version_id: c.constituent_version_id,
          source_site_id: c.source_site_id || null,
          tracking_strategy: c.tracking_strategy || null,
          sequence_no: c.sequence_no ? Number(c.sequence_no) : null,
        })),
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
          <Field
            label="Sterile process profile"
            hint={
              !siteId
                ? "Select a site first."
                : STERILE_REQUIRED_PROFILES.includes(profile)
                ? "Required at Release for this profile (PRD-FR-010) — picked from the site's released sterile process profiles."
                  : "Not required for this profile."
            }
          >
            <Select value={sterileProfileId} onChange={(e) => setSterileProfileId(e.target.value)} disabled={!siteId}>
            <option value="">—</option>
              {(sterileProfiles ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {sterileProfileLabel(p)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Device model code" hint="Required at Release if UDI applicable is checked (PRD-FR-012)">
            <Input value={deviceModelCode} onChange={(e) => setDeviceModelCode(e.target.value)} />
          </Field>
        </div>
        <label className="flex items-center gap-2 fs-2 mb-3">
          <input type="checkbox" checked={udiApplicable} onChange={(e) => setUdiApplicable(e.target.checked)} />
          UDI applicable
        </label>

        <p className="fact-k mb-2">Combination product (optional)</p>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Combination product type" hint="Free text, e.g. drug-device-combination.">
            <Input value={combinationProductType} onChange={(e) => setCombinationProductType(e.target.value)} />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Strength value">
              <Input type="number" step="any" value={strengthValue} onChange={(e) => setStrengthValue(e.target.value)} />
            </Field>
            <Field label="Strength UOM">
              <Input value={strengthUom} onChange={(e) => setStrengthUom(e.target.value)} placeholder="mg" />
            </Field>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Field label="PMOA reference" hint="Optional.">
            <Input value={pmoaReference} onChange={(e) => setPmoaReference(e.target.value)} />
          </Field>
          <Field label="Part 4 profile code" hint="Optional.">
            <Input value={part4ProfileCode} onChange={(e) => setPart4ProfileCode(e.target.value)} />
          </Field>
          <Field label="Finished tracking strategy" hint="Optional, free text.">
            <Input value={finishedTrackingStrategy} onChange={(e) => setFinishedTrackingStrategy(e.target.value)} />
          </Field>
        </div>
        {combinationProductType && constituents.length === 0 && (
          <p className="hint mb-2">
            A combination product needs at least one constituent, or Release will block (PRD-FR-004/006).
          </p>
        )}

        <ConstituentEditor constituents={constituents} onChange={setConstituents} sites={sites} />

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

/** Edit an existing draft — wires `PUT /products/v1/drafts/{id}` (services/gxp-api/app/modules/
 * product_master/commands.py::update_draft), which existed in the backend from the start but had no
 * frontend caller until now. Only reachable while `lifecycle_state === "draft"` (server-enforced too —
 * `update_draft()` rejects any other state). Identity fields (Business ID, Product code, Version no,
 * Site) are not part of UpdateProductDraftCommand and so aren't editable here — shown as read-only
 * context instead. `constituents` is a full replace, same as create. */
function EditDraftModal({
  version,
  onClose,
  onDone,
}: {
  version: ProductVersion;
  onClose: () => void;
  onDone: () => void;
}) {
  const { sites } = useSites();
  const [name, setName] = useState(version.name);
  const [profile, setProfile] = useState(version.manufacturing_profile_code);
  const [udiApplicable, setUdiApplicable] = useState(!!version.udi_applicable);
  const [deviceModelCode, setDeviceModelCode] = useState(version.device_model_code ?? "");
  const [sterileProfileId, setSterileProfileId] = useState(version.sterile_profile_id ?? "");
  const [combinationProductType, setCombinationProductType] = useState(version.combination_product_type ?? "");
  const [strengthValue, setStrengthValue] = useState(version.strength_value ?? "");
  const [strengthUom, setStrengthUom] = useState(version.strength_uom ?? "");
  const [pmoaReference, setPmoaReference] = useState(version.pmoa_reference ?? "");
  const [part4ProfileCode, setPart4ProfileCode] = useState(version.part4_profile_code ?? "");
  const [finishedTrackingStrategy, setFinishedTrackingStrategy] = useState(version.finished_tracking_strategy ?? "");
  const [constituents, setConstituents] = useState<ConstituentDraft[]>(toConstituentDrafts(version.constituents));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const { data: sterileProfiles } = useApiResource<SterileProfile[]>(
    `/products/v1/sterile-profiles?site_id=${version.site_id}`
  );

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.put(`/products/v1/drafts/${version.product_version_id}`, {
        idempotency_key: newIdempotencyKey(),
        product_version_id: version.product_version_id,
        expected_version: version.version,
        name,
        manufacturing_profile_code: profile,
        udi_applicable: udiApplicable,
        device_model_code: deviceModelCode || null,
        sterile_profile_id: sterileProfileId || null,
        combination_product_type: combinationProductType || null,
        strength_value: strengthValue || null,
        strength_uom: strengthUom || null,
        pmoa_reference: pmoaReference || null,
        part4_profile_code: part4ProfileCode || null,
        finished_tracking_strategy: finishedTrackingStrategy || null,
        constituents: constituents.map((c) => ({
          constituent_type: c.constituent_type,
          role_code: c.role_code || null,
          constituent_business_id: c.constituent_business_id,
          constituent_version_id: c.constituent_version_id,
          source_site_id: c.source_site_id || null,
          tracking_strategy: c.tracking_strategy || null,
          sequence_no: c.sequence_no ? Number(c.sequence_no) : null,
        })),
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to save changes");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={`Edit draft — ${version.product_business_id} v${version.version_no}`} large>
      <form onSubmit={onSubmit}>
        <p className="hint mb-3">
        Business ID, Product code, Version no. and Site are fixed once a draft exists — everything else
          can change while the record is still in draft state.
        </p>
        <Field label="Name" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Manufacturing profile" required>
            <Select value={profile} onChange={(e) => setProfile(e.target.value)}>
              {MANUFACTURING_PROFILES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            label="Sterile process profile"
            hint={
              STERILE_REQUIRED_PROFILES.includes(profile)
              ? "Required at Release for this profile (PRD-FR-010) — picked from the site's released sterile process profiles."
                : "Not required for this profile."
            }
          >
            <Select value={sterileProfileId} onChange={(e) => setSterileProfileId(e.target.value)}>
            <option value="">—</option>
              {(sterileProfiles ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {sterileProfileLabel(p)}
                </option>
              ))}
              {sterileProfileId && !(sterileProfiles ?? []).some((p) => p.id === sterileProfileId) && (
                <option value={sterileProfileId}>{sterileProfileId} (not a valid sterile process profile — reselect)</option>
              )}
            </Select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Device model code" hint="Required at Release if UDI applicable is checked (PRD-FR-012)">
            <Input value={deviceModelCode} onChange={(e) => setDeviceModelCode(e.target.value)} />
          </Field>
          <label className="flex items-center gap-2 fs-2" style={{ marginTop: 28 }}>
            <input type="checkbox" checked={udiApplicable} onChange={(e) => setUdiApplicable(e.target.checked)} />
            UDI applicable
          </label>
        </div>

        <p className="fact-k mb-2">Combination product (optional)</p>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Combination product type" hint="Free text, e.g. drug-device-combination.">
            <Input value={combinationProductType} onChange={(e) => setCombinationProductType(e.target.value)} />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Strength value">
              <Input type="number" step="any" value={strengthValue} onChange={(e) => setStrengthValue(e.target.value)} />
            </Field>
            <Field label="Strength UOM">
              <Input value={strengthUom} onChange={(e) => setStrengthUom(e.target.value)} placeholder="mg" />
            </Field>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Field label="PMOA reference" hint="Optional.">
            <Input value={pmoaReference} onChange={(e) => setPmoaReference(e.target.value)} />
          </Field>
          <Field label="Part 4 profile code" hint="Optional.">
            <Input value={part4ProfileCode} onChange={(e) => setPart4ProfileCode(e.target.value)} />
          </Field>
          <Field label="Finished tracking strategy" hint="Optional, free text.">
            <Input value={finishedTrackingStrategy} onChange={(e) => setFinishedTrackingStrategy(e.target.value)} />
          </Field>
        </div>
        {combinationProductType && constituents.length === 0 && (
          <p className="hint mb-2">
            A combination product needs at least one constituent, or Release will block (PRD-FR-004/006).
          </p>
        )}

        <ConstituentEditor constituents={constituents} onChange={setConstituents} sites={sites} />

        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !name.trim()}>
            {busy ? "Saving…" : "Save changes"}
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
  const [editOpen, setEditOpen] = useState(false);
  const [releaseSigOpen, setReleaseSigOpen] = useState(false);

  const { data: sterileProfiles } = useApiResource<SterileProfile[]>(
    version ? `/products/v1/sterile-profiles?site_id=${version.site_id}` : null
  );
  const sterileProfile = sterileProfiles?.find((p) => p.id === version?.sterile_profile_id);

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
            ...(version.sterile_profile_id
              ? ([
                  [
                    "Sterile process profile",
                    sterileProfile ? `${sterileProfileLabel(sterileProfile)} (${version.sterile_profile_id})` : version.sterile_profile_id,
                  ],
                ] as [string, string][])
              : []),
            ...(version.device_model_code ? ([["Device model code", version.device_model_code]] as [string, string][]) : []),
            ...(version.combination_product_type ? ([["Combination product type", version.combination_product_type]] as [string, string][]) : []),
            ...(version.strength_value
              ? ([["Strength", `${version.strength_value} ${version.strength_uom ?? ""}`.trim()]] as [string, string][])
              : []),
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
                  <td><WorkflowStatePill state={c.status} /></td>
                  <td className="fs-2 tabular">
                    {c.effective_from ? new Date(c.effective_from).toLocaleDateString() : "—"}
                    {c.effective_to ? ` → ${new Date(c.effective_to).toLocaleDateString()}` : ""}
                  </td>
                  <td className="fs-1" style={{ wordBreak: "break-word" }}>
                    {summarizeJson(c.interface_constraints)}
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
          </p>
          {!eligibility.eligible && (
            <ul className="fs-2" style={{ paddingLeft: "1.2em" }}>
              {!(eligibility.checks.lifecycle_ok as boolean) && (
                <li>
                  Lifecycle state is &quot;{eligibility.checks.lifecycle_state as string}&quot; — must be
                  &quot;released&quot; to issue.
                </li>
              )}
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
              <Button variant="secondary" onClick={() => setEditOpen(true)} disabled={busy}>
                Edit
              </Button>
              {findings.length > 0 ? (
                <Button variant="secondary" onClick={validateCompleteness} disabled={busy}>
                  Check completeness
                </Button>
              ) : (
                // The Issue eligibility panel above already re-computes completeness live on every
                // load/refresh (GET .../issue-eligibility) — findings.length === 0 means it's already
                // clean, so there's nothing left to check. Re-appears the moment an edit reintroduces a
                // finding.
                <span className="fs-2 text-muted flex items-center gap-1" style={{ padding: "0 8px" }}>
                  <Icon name="check-circle" /> Complete
                </span>
              )}
              <Button variant="primary" onClick={submit} disabled={busy}>
                Submit for review
              </Button>
            </>
          )}
          {canReleaseProduct(me) && version.lifecycle_state === "under_review" && (
            <Button variant="success" onClick={() => setReleaseSigOpen(true)} disabled={busy}>
              Release
            </Button>
          )}
          {holdsAnyRole(me, ["Admin"]) && version.lifecycle_state === "released" && (
            <Button variant="danger" onClick={suspend} disabled={busy}>
              Suspend
            </Button>
          )}
          {holdsAnyRole(me, ["Admin"]) && version.lifecycle_state === "suspended" && (
            <Button variant="primary" onClick={reinstate} disabled={busy}>
              Reinstate
            </Button>
          )}
        </div>
      </div>

      {editOpen && (
        <EditDraftModal
          version={version}
          onClose={() => setEditOpen(false)}
          onDone={() => {
            setEditOpen(false);
            refresh().catch((err) => setError(err instanceof ApiError ? err.message : "Failed to reload"));
            onChanged();
          }}
        />
      )}

      {releaseSigOpen && (
        <SignatureCeremony
          open
          onClose={() => setReleaseSigOpen(false)}
          onDone={() => {
            setReleaseSigOpen(false);
            refresh().catch((err) => setError(err instanceof ApiError ? err.message : "Failed to reload"));
            onChanged();
          }}
          challengePath={`/products/v1/${productVersionId}/signature-challenges`}
          action="release"
 title={`Release ${version.name} v${version.version_no}`}
          submitLabel="Sign & release"
          submitVariant="success"
          summary={
            <>
            This releases <strong>{version.product_business_id}</strong> v{version.version_no} — once released its content is locked; a further change needs a new version. Signed by a QA
              once released its content is locked; a further change needs a new version. Signed by a QA
              Releaser who is <strong>not</strong> the version&apos;s author (author ≠ releaser).
            </>
          }
          onSign={(p) =>
            api.post(`/products/v1/drafts/${productVersionId}/release`, {
              idempotency_key: p.idempotency_key,
              product_version_id: productVersionId,
              expected_version: version.version,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
            })
          }
        />
      )}
    </Modal>
  );
}
