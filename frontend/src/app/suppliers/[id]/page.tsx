"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  ApiError,
  canApproveSupplier,
  canCreateSupplier,
  canDeleteSupplier,
  canUpdateSupplier,
  canOperateEvidence,
  downloadEvidence,
  formatDate,
  formatDateTime,
  isOverdue,
  newIdempotencyKey,
  type Me,
  type MutationReceipt,
  type Supplier,
} from "@/lib/api";
import { useApiResource, useEntityOptions, useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button, LinkButton } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { JsonPanel, summarizeJson } from "@/components/ui/JsonPanel";
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { Tabs } from "@/components/ui/Tabs";
import { useCommand } from "@/components/qms/QmsDetailShell";
import { KeyValueRows, buildKvObject, type KvRow } from "@/components/shared/RepeatableFields";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { DocumentPreviewModal } from "@/components/shared/DocumentPreviewModal";
import { ROLE_TYPES } from "../page";

interface SupplierSite {
  id: string;
  site_name: string;
  city: string | null;
  country: string | null;
  manufacturer_flag: boolean;
  certification_refs: Record<string, unknown> | null;
  status: string;
  version: number;
}

interface ScopeItem {
  material_id: string;
  code: string;
  name: string;
}

interface Qualification {
  id: string;
  supplier_site_id: string;
  scope: Record<string, unknown> | null;
  scope_items: ScopeItem[];
  risk_class: string | null;
  status: string;
  justification: string | null;
  effective_from: string | null;
  expires_at: string | null;
  quality_agreement_vault_id: string | null;
  approval_signatures: Record<string, unknown> | null;
  version: number;
}

interface SupplierDetail extends Supplier {
  external_mappings: Record<string, unknown> | null;
  sites: SupplierSite[];
  qualifications: Qualification[];
}

export default function SupplierDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { me } = useMe();
  const detail = useApiResource<SupplierDetail>(`/suppliers/v1/${id}`);
  const [qualifyOpen, setQualifyOpen] = useState(false);
  const [approving, setApproving] = useState<Qualification | null>(null);
  const [addSiteOpen, setAddSiteOpen] = useState(false);
  const [viewingDocuments, setViewingDocuments] = useState<Qualification | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  if (detail.error) {
    return (
      <div>
        <PageHead title="Supplier" />
        <Banner tone="critical" title="Could not load this supplier">
          {detail.error}
        </Banner>
        <LinkButton href="/suppliers" variant="secondary">
          <Icon name="arrow-left" /> Back to suppliers
        </LinkButton>
      </div>
    );
  }

  if (!detail.data) {
    return (
      <div>
        <PageHead title="Supplier" subtitle="Loading…" />
      </div>
    );
  }

  const s = detail.data;
  const expired = s.qualifications.filter((q) => isOverdue(q.expires_at) && q.status === "approved");
  const canEditOrDelete = s.status === "draft" && (canUpdateSupplier(me) || canDeleteSupplier(me));

  return (
    <div>
      <PageHead
        title={
          <span className="flex items-center gap-3">
            {s.supplier_code} - {s.legal_name} <WorkflowStatePill state={s.status} />
          </span>
        }
        subtitle={[s.role_type.replace(/_/g, " "), s.country].filter(Boolean).join(" · ")}
        action={
          <div className="flex gap-2">
            <LinkButton href="/suppliers" variant="secondary">
              <Icon name="arrow-left" /> Back
            </LinkButton>
            {/* Client follow-up (2026-10-06, project-owner-directed): edit/delete only while still draft --
                once a qualification exists the supplier has left draft, so this naturally disappears then. */}
            {s.status === "draft" && canUpdateSupplier(me) && (
              <Button variant="secondary" onClick={() => setEditOpen(true)}>
                <Icon name="pen-line" /> Edit
              </Button>
            )}
            {s.status === "draft" && canDeleteSupplier(me) && (
              <Button variant="danger" onClick={() => setDeleteConfirmOpen(true)}>
                <Icon name="x" /> Delete
              </Button>
            )}
          </div>
        }
      />

      {expired.length > 0 && (
        <Banner tone="critical" title="Expired qualification">
          {expired.length} approved qualification(s) have passed their expiry date.
        </Banner>
      )}

      {canEditOrDelete && deleteConfirmOpen && (
        <Banner tone="critical" title="Delete this draft supplier?">
          {`This permanently removes ${s.legal_name} and its ${s.sites.length} site(s). This cannot be undone. Only possible because nothing references it yet (no qualification, no material receipts, no equipment/QC provider links).`}
        </Banner>
      )}
      {deleteConfirmOpen && (
        <div className="mb-4">
          {deleteError && <p className="error-text mb-2">{deleteError}</p>}
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="danger"
              disabled={deleteBusy}
              onClick={async () => {
                setDeleteBusy(true);
                setDeleteError(null);
                try {
                  await api.del(`/suppliers/v1/${s.id}`, { idempotency_key: newIdempotencyKey(), supplier_id: s.id });
                  router.push("/suppliers");
                } catch (err) {
                  setDeleteError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to delete");
                  setDeleteBusy(false);
                }
              }}
            >
              {deleteBusy ? "Deleting…" : "Yes, delete it"}
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setDeleteConfirmOpen(false)} disabled={deleteBusy}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      <Card pad className="mb-4">
        <FactGrid>
          <Fact label="Role type">{s.role_type.replace(/_/g, " ")}</Fact>
          <Fact label="Status">
            <WorkflowStatePill state={s.status} />
          </Fact>
          <Fact label="Country">{s.country ?? "—"}</Fact>
          <Fact label="Sites">{s.sites.length}</Fact>
          <Fact label="Qualifications">{s.qualifications.length}</Fact>
          <Fact label="Record version">{s.version}</Fact>
          <IdFact label="Supplier ID" value={s.id} />
        </FactGrid>
        <div className="mt-4">
          <JsonPanel title="External system mappings" value={s.external_mappings} />
        </div>
      </Card>

      <Tabs
        tabs={[
          {
            id: "sites",
            label: "Sites",
            badge: s.sites.length,
            content: (
              <Card>
                <CardHeader
                  title="Sites"
                  meta={
                    canCreateSupplier(me) && (
                      <Button size="sm" variant="secondary" onClick={() => setAddSiteOpen(true)}>
                        <Icon name="plus" /> Add site
                      </Button>
                    )
                  }
                />
                {s.sites.length === 0 ? (
                  <EmptyState icon="building">No sites registered for this supplier.</EmptyState>
                ) : (
                  <Table>
                    <thead>
                      <tr>
                        <th>Site</th>
                        <th>Location</th>
                        <th>Manufacturer</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {s.sites.map((site) => (
                        <tr key={site.id}>
                          <td className="font-semibold">{site.site_name}</td>
                          <td className="fs-2">{[site.city, site.country].filter(Boolean).join(", ") || "—"}</td>
                          <td>
                            {site.manufacturer_flag ? (
                              <StatePill state="accepted" icon="check-circle">
                                Yes
                              </StatePill>
                            ) : (
                              <span className="text-muted">—</span>
                            )}
                          </td>
                          <td>
                            <WorkflowStatePill state={site.status} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                )}
              </Card>
            ),
          },
          {
            id: "qualifications",
            label: "Qualifications",
            badge: s.qualifications.length,
            content: (
              <Card>
                <CardHeader
                  title="Qualifications"
                  meta={
                    canCreateSupplier(me) &&
                    s.sites.length > 0 && (
                      <Button size="sm" variant="secondary" onClick={() => setQualifyOpen(true)}>
                        <Icon name="plus" /> Request qualification
                      </Button>
                    )
                  }
                />
                {s.qualifications.length === 0 ? (
                  <EmptyState icon="badge-check">No qualification requested for this supplier.</EmptyState>
                ) : (
                  <Table>
                    <thead>
                      <tr>
                        <th>Risk class</th>
                        <th>Scope</th>
                        <th>Status</th>
                        <th>Effective</th>
                        <th>Expires</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {s.qualifications.map((q) => (
                        <tr key={q.id}>
                          <td className="fs-2">{q.risk_class ?? "—"}</td>
                          <td className="fs-2">
                            {q.scope_items.length > 0 ? (
                              <span>{q.scope_items.map((item) => item.code).join(", ")}</span>
                            ) : (
                              <span className="text-muted">—</span>
                            )}
                            {q.scope && Object.keys(q.scope).length > 0 && (
                              <div className="text-muted">{summarizeJson(q.scope)}</div>
                            )}
                          </td>
                          <td>
                            <WorkflowStatePill state={q.status} />
                          </td>
                          <td className="tabular fs-2">{formatDate(q.effective_from)}</td>
                          <td className={isOverdue(q.expires_at) ? "error-text tabular fs-2" : "tabular fs-2"}>
                            {formatDate(q.expires_at)}
                          </td>
                          <td style={{ textAlign: "right" }}>
                            <div className="flex gap-2 justify-end">
                              <Button size="sm" variant="secondary" onClick={() => setViewingDocuments(q)}>
                                <Icon name="file-text" /> Documents
                              </Button>
                              {canApproveSupplier(me) && q.status !== "approved" && q.status !== "rejected" && (
                                <Button size="sm" variant="secondary" onClick={() => setApproving(q)}>
                                  <Icon name="pen" /> Approve
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                )}
              </Card>
            ),
          },
        ]}
      />

      {addSiteOpen && (
        <AddSiteModal
          supplierId={s.id}
          onClose={() => setAddSiteOpen(false)}
          onDone={() => {
            setAddSiteOpen(false);
            detail.reload();
          }}
        />
      )}
      {editOpen && (
        <EditSupplierModal
          supplier={s}
          onClose={() => setEditOpen(false)}
          onDone={() => {
            setEditOpen(false);
            detail.reload();
          }}
        />
      )}
      {qualifyOpen && (
        <QualificationModal
          supplier={s}
          onClose={() => setQualifyOpen(false)}
          onDone={() => {
            setQualifyOpen(false);
            detail.reload();
          }}
        />
      )}
      {viewingDocuments && (
        <QualificationDocumentsModal
          qualification={viewingDocuments}
          me={me}
          onClose={() => setViewingDocuments(null)}
        />
      )}
      {approving && (
        <ApproveModal
          qualification={approving}
          onClose={() => setApproving(null)}
          onDone={() => {
            setApproving(null);
            detail.reload();
          }}
        />
      )}
    </div>
  );
}

function EditSupplierModal({
  supplier,
  onClose,
  onDone,
}: {
  supplier: SupplierDetail;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [legalName, setLegalName] = useState(supplier.legal_name);
  const [roleType, setRoleType] = useState(supplier.role_type);
  const [country, setCountry] = useState(supplier.country ?? "");

  return (
    <Modal open onClose={onClose} title={`Edit - ${supplier.supplier_code}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.put(`/suppliers/v1/${supplier.id}`, {
              idempotency_key: newIdempotencyKey(),
              supplier_id: supplier.id,
              expected_version: supplier.version,
              legal_name: legalName,
              role_type: roleType,
              country: country || null,
              external_mappings: supplier.external_mappings,
            })
          );
        }}
      >
        <p className="hint mb-3">
          Supplier code ({supplier.supplier_code}) is fixed once registered — only possible while this
          supplier is still draft.
        </p>
        <Field label="Legal name" required>
          <Input value={legalName} onChange={(e) => setLegalName(e.target.value)} required autoFocus />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Role type" required>
            <Select value={roleType} onChange={(e) => setRoleType(e.target.value)}>
              {ROLE_TYPES.map((r) => (
                <option key={r} value={r}>
                  {r.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Country">
            <Input value={country} onChange={(e) => setCountry(e.target.value)} />
          </Field>
        </div>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !legalName.trim()}>
            {busy ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function AddSiteModal({
  supplierId,
  onClose,
  onDone,
}: {
  supplierId: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const [siteName, setSiteName] = useState("");
  const [city, setCity] = useState("");
  const [country, setCountry] = useState("");
  const [manufacturerFlag, setManufacturerFlag] = useState(false);

  return (
    <Modal open onClose={onClose} title="Add a site">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/suppliers/${supplierId}/sites`, {
              idempotency_key: newIdempotencyKey(),
              supplier_id: supplierId,
              site: {
                site_name: siteName,
                city: city || null,
                country: country || null,
                manufacturer_flag: manufacturerFlag,
              },
            })
          );
        }}
      >
        <Field label="Site name" required>
          <Input value={siteName} onChange={(e) => setSiteName(e.target.value)} required autoFocus />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="City">
            <Input value={city} onChange={(e) => setCity(e.target.value)} />
          </Field>
          <Field label="Country">
            <Input value={country} onChange={(e) => setCountry(e.target.value)} />
          </Field>
        </div>
        <label className="flex items-center gap-2 fs-2 mb-3">
          <input
            type="checkbox"
            checked={manufacturerFlag}
            onChange={(e) => setManufacturerFlag(e.target.checked)}
          />
          This site manufactures (rather than only distributing)
        </label>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !siteName.trim()}>
            {busy ? "Adding…" : "Add site"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function QualificationModal({
  supplier,
  onClose,
  onDone,
}: {
  supplier: SupplierDetail;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, run } = useCommand(onDone);
  const { materials, materialsStatus } = useEntityOptions();
  const [siteId, setSiteId] = useState(supplier.sites[0]?.id ?? "");
  const [riskClass, setRiskClass] = useState("medium");
  // Client gap-analysis Phase 3 (2026-10-05): scope is now a structured list of Material rows via
  // "Add Material" (scope_material_ids), not free text -- the free-text KeyValueRows stays available for
  // notes that don't map to a specific material (per project-owner direction, both are kept).
  const [scopeMaterialIds, setScopeMaterialIds] = useState<string[]>([]);
  const [materialToAdd, setMaterialToAdd] = useState("");
  const [scope, setScope] = useState<KvRow[]>([]);
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [expiresAt, setExpiresAt] = useState("");

  const addableMaterials = materials.filter((m) => !scopeMaterialIds.includes(m.value));

  return (
    <Modal open onClose={onClose} title="Request supplier qualification">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() => {
            const scopeObj = buildKvObject(scope);
            return api.post(`/suppliers/${supplier.id}/qualifications`, {
              idempotency_key: newIdempotencyKey(),
              supplier_id: supplier.id,
              supplier_site_id: siteId,
              risk_class: riskClass,
              scope: Object.keys(scopeObj).length ? scopeObj : null,
              scope_material_ids: scopeMaterialIds,
              effective_from: effectiveFrom ? new Date(effectiveFrom).toISOString() : null,
              expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
            });
          });
        }}
      >
        <Field label="Supplier site" required>
          <Select value={siteId} onChange={(e) => setSiteId(e.target.value)} required>
            {supplier.sites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.site_name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Risk class" required>
          <Select value={riskClass} onChange={(e) => setRiskClass(e.target.value)}>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </Select>
        </Field>
        <Field label="Scope" hint="What materials this supplier is qualified to provide.">
          <div className="flex gap-2 items-end">
            <div style={{ flex: 1 }}>
              <Select value={materialToAdd} onChange={(e) => setMaterialToAdd(e.target.value)} disabled={materialsStatus !== "ready" || addableMaterials.length === 0}>
                <option value="">
                  {materialsStatus === "loading" ? "Loading materials…" : "Select a material to add…"}
                </option>
                {addableMaterials.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </Select>
            </div>
            <Button
              type="button"
              variant="secondary"
              disabled={!materialToAdd}
              onClick={() => {
                if (!materialToAdd) return;
                setScopeMaterialIds((prev) => [...prev, materialToAdd]);
                setMaterialToAdd("");
              }}
            >
              <Icon name="plus" /> Add material
            </Button>
          </div>
        </Field>
        {scopeMaterialIds.length > 0 && (
          <div className="flex flex-col gap-2 mb-3">
            {scopeMaterialIds.map((id) => {
              const m = materials.find((opt) => opt.value === id);
              return (
                <div key={id} className="flex items-center justify-between gap-2 card" style={{ padding: "6px 10px" }}>
                  <span className="fs-2">{m?.label ?? id}</span>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => setScopeMaterialIds((prev) => prev.filter((x) => x !== id))}
                  >
                    Remove
                  </Button>
                </div>
              );
            })}
          </div>
        )}
        <KeyValueRows
          label="Scope notes (optional)"
          hint="Anything about scope that doesn't map to a specific material above, e.g. a general exclusion or condition."
          value={scope}
          onChange={setScope}
        />
        <div className="grid grid-cols-2 gap-4">
          <Field label="Effective from">
            <Input type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
          </Field>
          <Field label="Expires">
            <Input type="date" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
          </Field>
        </div>
        <p className="hint mb-3">
          The signed quality agreement and other supporting documents (audit reports, certificates, etc.)
          can be added from the qualification&apos;s “Documents” button after it&apos;s created.
        </p>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !siteId}>
            {busy ? "Requesting…" : "Request qualification"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Qualification documents -- client gap-analysis Phase 3 (2026-10-05): a real "Add Document" upload
// (name, category, effective/expiry dates), all visible/openable in the same popup an approver reviews
// the qualification from. Reuses the generic `evidence` module exactly the way equipment/[id]/page.tsx's
// "Documents" tab already does (owner_type/owner_id + provenance JSONB), not the heavier Vault release
// ceremony `SupplierQualificationEvidence` originally assumed -- that table/field are left untouched for
// backward compatibility, this is a second, additive path.
// Redesigned 2026-10-06 (project-owner-directed, "very bad UI" feedback): the plain table became a card
// grid with a per-document inline preview (image/PDF/text render in-browser via DocumentPreviewModal;
// anything else falls back to Download, same as before).
// ---------------------------------------------------------------------------

const EVIDENCE_CATEGORIES = [
  { value: "quality_agreement", label: "Quality agreement" },
  { value: "certificate", label: "Certificate" },
  { value: "audit_report", label: "Audit report" },
  { value: "license", label: "License" },
  { value: "questionnaire", label: "Questionnaire" },
  { value: "capability_evidence", label: "Capability evidence" },
  { value: "test_history", label: "Test history" },
  { value: "other", label: "Other" },
];

interface QualificationDocument {
  id: string;
  filename: string;
  mime_type: string;
  state: string;
  created_at: string;
  provenance: {
    document_name?: string;
    evidence_category?: string;
    effective_date?: string;
    expiry_date?: string;
  } | null;
}

function QualificationDocumentsModal({
  qualification,
  me,
  onClose,
}: {
  qualification: Qualification;
  me: Me | null;
  onClose: () => void;
}) {
  const { data, reload } = useApiResource<{ evidence_objects: QualificationDocument[] }>(
    `/evidence/v1/objects?owner_type=supplier_qualification&owner_id=${qualification.id}`
  );
  const [uploadOpen, setUploadOpen] = useState(false);
  const [previewing, setPreviewing] = useState<QualificationDocument | null>(null);
  const documents = data?.evidence_objects ?? [];

  return (
    <Modal open onClose={onClose} title="Qualification documents" large>
      <div className="flex justify-between items-center mb-3">
        <p className="hint">Supporting documents for this qualification, visible to any approver reviewing it.</p>
        {canOperateEvidence(me) && (
          <Button size="sm" variant="secondary" onClick={() => setUploadOpen(true)}>
            <Icon name="plus" /> Add document
          </Button>
        )}
      </div>
      {documents.length === 0 ? (
        <EmptyState icon="file-text">No documents uploaded for this qualification yet.</EmptyState>
      ) : (
        <div
          className="grid gap-3"
          style={{ gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))" }}
        >
          {documents.map((d) => {
            const category = EVIDENCE_CATEGORIES.find((c) => c.value === d.provenance?.evidence_category);
            const canPreview = d.mime_type.startsWith("image/") || d.mime_type === "application/pdf" || d.mime_type.startsWith("text/");
            return (
              <div key={d.id} className="card card-pad flex flex-col gap-2">
                <div className="flex items-start gap-2">
                  <Icon name="file-text" />
                  <span className="font-semibold fs-2" style={{ wordBreak: "break-word" }}>
                    {d.provenance?.document_name ?? d.filename}
                  </span>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="fs-1 text-muted">{category?.label ?? d.provenance?.evidence_category ?? "Other"}</span>
                  <WorkflowStatePill state={d.state} />
                </div>
                <div className="fs-1 text-muted">
                  {d.provenance?.effective_date && <div>Effective: {formatDate(d.provenance.effective_date)}</div>}
                  {d.provenance?.expiry_date && (
                    <div className={isOverdue(d.provenance.expiry_date) ? "error-text" : undefined}>
                      Expires: {formatDate(d.provenance.expiry_date)}
                    </div>
                  )}
                  <div>Uploaded {formatDateTime(d.created_at)}</div>
                </div>
                {d.state === "FINALIZED" && (
                  <div className="flex gap-2 mt-auto" style={{ paddingTop: 4 }}>
                    {canPreview && (
                      <Button size="sm" variant="secondary" onClick={() => setPreviewing(d)}>
                        <Icon name="eye" /> Preview
                      </Button>
                    )}
                    <Button size="sm" variant="secondary" onClick={() => downloadEvidence(d.id)}>
                      <Icon name="download" /> Download
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="flex justify-end gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </div>

      {uploadOpen && (
        <UploadQualificationDocumentModal
          qualificationId={qualification.id}
          onClose={() => setUploadOpen(false)}
          onDone={() => {
            setUploadOpen(false);
            reload();
          }}
        />
      )}
      {previewing && (
        <DocumentPreviewModal
          evidenceId={previewing.id}
          filename={previewing.provenance?.document_name ?? previewing.filename}
          mimeType={previewing.mime_type}
          onClose={() => setPreviewing(null)}
        />
      )}
    </Modal>
  );
}

function UploadQualificationDocumentModal({
  qualificationId,
  onClose,
  onDone,
}: {
  qualificationId: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const [documentName, setDocumentName] = useState("");
  const [evidenceCategory, setEvidenceCategory] = useState(EVIDENCE_CATEGORIES[0].value);
  const [effectiveDate, setEffectiveDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileBase64, setFileBase64] = useState("");
  const [mimeType, setMimeType] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFile(file: File | undefined) {
    if (!file) {
      setFileName(null);
      setFileBase64("");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      const base64 = result.includes(",") ? result.slice(result.indexOf(",") + 1) : result;
      setFileName(file.name);
      setMimeType(file.type || "application/octet-stream");
      setFileBase64(base64);
    };
    reader.readAsDataURL(file);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!fileName || !fileBase64) return;
    setBusy(true);
    setError(null);
    try {
      const provenance = {
        document_name: documentName || fileName,
        evidence_category: evidenceCategory,
        effective_date: effectiveDate || null,
        expiry_date: expiryDate || null,
      };
      const staged = await api.post<MutationReceipt>("/evidence/v1/uploads", {
        idempotency_key: newIdempotencyKey(),
        owner_type: "supplier_qualification",
        owner_id: qualificationId,
        filename: fileName,
        mime_type: mimeType,
        provenance,
        reason: `Supplier qualification document upload (${evidenceCategory})`,
      });
      await api.post<MutationReceipt>(`/evidence/v1/${staged.aggregate_id}:finalize`, {
        idempotency_key: newIdempotencyKey(),
        evidence_id: staged.aggregate_id,
        expected_version: staged.resulting_version,
        content_base64: fileBase64,
        reason: `Supplier qualification document upload (${evidenceCategory})`,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to upload document");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Add document">
      <form onSubmit={onSubmit}>
        <Field label="Document name" hint='E.g. "ISO 9001 Certificate". Defaults to the filename if left blank.'>
          <Input value={documentName} onChange={(e) => setDocumentName(e.target.value)} />
        </Field>
        <Field label="Category" required>
          <Select value={evidenceCategory} onChange={(e) => setEvidenceCategory(e.target.value)}>
            {EVIDENCE_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </Select>
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Effective date (optional)">
            <Input type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} />
          </Field>
          <Field label="Expiry date (optional)">
            <Input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
          </Field>
        </div>
        <Field label="File" required>
          <input type="file" className="input" onChange={(e) => handleFile(e.target.files?.[0])} />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !fileName}>
            {busy ? "Uploading…" : "Upload"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ApproveModal({
  qualification,
  onClose,
  onDone,
}: {
  qualification: Qualification;
  onClose: () => void;
  onDone: () => void;
}) {
  const [decision, setDecision] = useState("approved");
  const [justification, setJustification] = useState("");

  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/supplier-qualifications/${qualification.id}/signature-challenges`}
      action="approve"
      title={
        <span className="flex items-center gap-2">
          <Icon name="pen" /> Approve supplier qualification
        </span>
      }
      summary="Records the qualification decision for this supplier."
      submitLabel="Sign decision"
      reason="none"
      extraFields={
        <>
          <Field label="Decision" required>
            <Select value={decision} onChange={(e) => setDecision(e.target.value)}>
              <option value="approved">approved</option>
              <option value="conditional">conditional</option>
              <option value="rejected">rejected</option>
            </Select>
          </Field>
          {/* Client gap-analysis Phase 3: "Explanation" for a routine approval, "Justification" is
              reserved for an exception/deviation (conditional or rejected) decision, where it's also
              required -- the field and its backend semantics are unchanged, only the label differs. */}
          <Field
            label={decision === "approved" ? "Explanation" : "Justification"}
            hint={decision === "approved" ? "Optional." : "Required for a conditional or rejected decision."}
          >
            <textarea
              className="input"
              rows={3}
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
            />
          </Field>
        </>
      }
      onSign={(p) =>
        api.post(`/supplier-qualifications/${qualification.id}/approve`, {
          idempotency_key: p.idempotency_key,
          qualification_id: qualification.id,
          expected_version: qualification.version,
          decision,
          justification: justification || null,
          challenge_id: p.challenge_id,
          reauth_password: p.reauth_password,
        })
      }
    />
  );
}
