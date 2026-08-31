"use client";

import { useEffect, useState } from "react";
import {
  api,
  canApproveSupplier,
  formatDate,
  isOverdue,
  newIdempotencyKey,
  pagedFetcher,
  type Supplier,
} from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
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
import { StatePill, WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/qms/QmsDetailShell";

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

interface Qualification {
  id: string;
  supplier_site_id: string;
  scope: Record<string, unknown> | null;
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

const ROLE_TYPES = ["supplier", "manufacturer", "both"];

export default function SuppliersPage() {
  const { me } = useMe();
  const [reloadToken, setReloadToken] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const fetchSuppliers = pagedFetcher<Supplier>("/suppliers/v1");

  const columns: DataTableColumn<Supplier>[] = [
    {
      key: "supplier_code",
      header: "Code",
      sortable: true,
      render: (s) => <span className="font-semibold tabular">{s.supplier_code}</span>,
    },
    { key: "legal_name", header: "Legal name", sortable: true },
    { key: "role_type", header: "Role", render: (s) => <span className="fs-2">{s.role_type}</span> },
    { key: "country", header: "Country", render: (s) => <span className="fs-2">{s.country ?? "—"}</span> },
    { key: "status", header: "Status", sortable: true, render: (s) => <WorkflowStatePill state={s.status} /> },
  ];

  return (
    <div>
      <PageHead
        title="Suppliers"
        subtitle="Document 18 — the supplier register, its sites, and their qualification status."
        action={
          canApproveSupplier(me) ? (
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus" /> New supplier
            </Button>
          ) : undefined
        }
      />

      <Card>
        <CardHeader title="Supplier register" />
        <DataTable
          columns={columns}
          fetchPage={fetchSuppliers}
          rowKey={(s) => s.id}
          searchPlaceholder="Search by code or legal name…"
          emptyIcon="building"
          emptyMessage="No suppliers registered yet."
          defaultSort={{ by: "created_at", dir: "desc" }}
          reloadToken={reloadToken}
          onRowClick={(s) => setSelected(s.id)}
        />
      </Card>

      {createOpen && (
        <CreateSupplierModal
          onClose={() => setCreateOpen(false)}
          onDone={() => {
            setCreateOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
      {selected && (
        <SupplierModal
          supplierId={selected}
          onClose={() => setSelected(null)}
          onChanged={() => setReloadToken((n) => n + 1)}
        />
      )}
    </div>
  );
}

function CreateSupplierModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { busy, error, run } = useCommand(onDone);
  const [supplierCode, setSupplierCode] = useState("");
  const [legalName, setLegalName] = useState("");
  const [roleType, setRoleType] = useState(ROLE_TYPES[0]);
  const [country, setCountry] = useState("");
  const [siteName, setSiteName] = useState("");
  const [siteCity, setSiteCity] = useState("");
  const [manufacturerFlag, setManufacturerFlag] = useState(false);

  return (
    <Modal open onClose={onClose} title="Register a supplier" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post("/suppliers/v1", {
              idempotency_key: newIdempotencyKey(),
              supplier_code: supplierCode,
              legal_name: legalName,
              role_type: roleType,
              country: country || null,
              sites: siteName
                ? [
                    {
                      site_name: siteName,
                      city: siteCity || null,
                      country: country || null,
                      manufacturer_flag: manufacturerFlag,
                    },
                  ]
                : [],
            })
          );
        }}
      >
        <div className="grid grid-cols-3 gap-4">
          <Field label="Supplier code" required>
            <Input value={supplierCode} onChange={(e) => setSupplierCode(e.target.value)} required autoFocus />
          </Field>
          <Field label="Role type" required>
            <Select value={roleType} onChange={(e) => setRoleType(e.target.value)}>
              {ROLE_TYPES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Country">
            <Input value={country} onChange={(e) => setCountry(e.target.value)} />
          </Field>
        </div>
        <Field label="Legal name" required>
          <Input value={legalName} onChange={(e) => setLegalName(e.target.value)} required />
        </Field>
        <p className="fact-k mb-2 mt-4">First site (optional)</p>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Site name">
            <Input value={siteName} onChange={(e) => setSiteName(e.target.value)} />
          </Field>
          <Field label="City">
            <Input value={siteCity} onChange={(e) => setSiteCity(e.target.value)} />
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
          <Button type="submit" variant="primary" disabled={busy || !supplierCode.trim() || !legalName.trim()}>
            {busy ? "Registering…" : "Register supplier"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function SupplierModal({
  supplierId,
  onClose,
  onChanged,
}: {
  supplierId: string;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { me } = useMe();
  const detail = useApiResource<SupplierDetail>(`/suppliers/v1/${supplierId}`);
  const [qualifyOpen, setQualifyOpen] = useState(false);
  const [approving, setApproving] = useState<Qualification | null>(null);

  const s = detail.data;
  if (!s) {
    return (
      <Modal open onClose={onClose} title="Supplier">
        {detail.error ? <p className="error-text">{detail.error}</p> : <p>Loading…</p>}
      </Modal>
    );
  }

  const expired = s.qualifications.filter((q) => isOverdue(q.expires_at) && q.status === "approved");

  return (
    <Modal open onClose={onClose} title={`${s.supplier_code} — ${s.legal_name}`} large>
      {expired.length > 0 && (
        <Banner tone="critical" title="Expired qualification">
          {expired.length} approved qualification(s) have passed their expiry date.
        </Banner>
      )}

      <FactGrid>
        <Fact label="Role type">{s.role_type}</Fact>
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

      <p className="fact-k mb-2 mt-4">Sites</p>
      {s.sites.length === 0 ? (
        <p className="hint">No sites registered for this supplier.</p>
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

      <div className="flex justify-between items-center mt-4 mb-2">
        <p className="fact-k">Qualifications</p>
        {canApproveSupplier(me) && s.sites.length > 0 && (
          <Button size="sm" variant="secondary" onClick={() => setQualifyOpen(true)}>
            <Icon name="plus" /> Request qualification
          </Button>
        )}
      </div>
      {s.qualifications.length === 0 ? (
        <EmptyState icon="badge-check">No qualification requested for this supplier.</EmptyState>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Risk class</th>
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
                <td>
                  <WorkflowStatePill state={q.status} />
                </td>
                <td className="tabular fs-2">{formatDate(q.effective_from)}</td>
                <td className={isOverdue(q.expires_at) ? "error-text tabular fs-2" : "tabular fs-2"}>
                  {formatDate(q.expires_at)}
                </td>
                <td style={{ textAlign: "right" }}>
                  {canApproveSupplier(me) && q.status !== "approved" && q.status !== "rejected" && (
                    <Button size="sm" variant="secondary" onClick={() => setApproving(q)}>
                      <Icon name="pen" /> Approve
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <div className="flex justify-between gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </div>

      {qualifyOpen && (
        <QualificationModal
          supplier={s}
          onClose={() => setQualifyOpen(false)}
          onDone={() => {
            setQualifyOpen(false);
            detail.reload();
            onChanged();
          }}
        />
      )}
      {approving && (
        <ApproveModal
          qualification={approving}
          onClose={() => setApproving(null)}
          onDone={() => {
            setApproving(null);
            detail.reload();
            onChanged();
          }}
        />
      )}
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
  const [siteId, setSiteId] = useState(supplier.sites[0]?.id ?? "");
  const [riskClass, setRiskClass] = useState("medium");
  const [scope, setScope] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [expiresAt, setExpiresAt] = useState("");

  return (
    <Modal open onClose={onClose} title="Request supplier qualification">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/suppliers/${supplier.id}/qualifications`, {
              idempotency_key: newIdempotencyKey(),
              supplier_id: supplier.id,
              supplier_site_id: siteId,
              risk_class: riskClass,
              scope: scope ? { description: scope } : null,
              effective_from: effectiveFrom ? new Date(effectiveFrom).toISOString() : null,
              expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
            })
          );
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
            <option value="high">high</option>
            <option value="medium">medium</option>
            <option value="low">low</option>
          </Select>
        </Field>
        <Field label="Scope" hint="What this supplier is qualified to provide.">
          <textarea className="input" rows={2} value={scope} onChange={(e) => setScope(e.target.value)} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Effective from">
            <Input type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
          </Field>
          <Field label="Expires">
            <Input type="date" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
          </Field>
        </div>
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

function ApproveModal({
  qualification,
  onClose,
  onDone,
}: {
  qualification: Qualification;
  onClose: () => void;
  onDone: () => void;
}) {
  const { busy, error, setError, run } = useCommand(onDone);
  const [decision, setDecision] = useState("approved");
  const [justification, setJustification] = useState("");
  const [password, setPassword] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [meaning, setMeaning] = useState("");

  // Document 18 gates approval behind a signature ceremony and, unlike the QMS modules, does expose the
  // challenge endpoint — so the ceremony is performed properly here. The challenge binds to the record's
  // current version and hash, so it is requested per ceremony rather than reused.
  useEffect(() => {
    let cancelled = false;
    api
      .post<{ challenge_id: string; meaning: string }>(
        `/supplier-qualifications/${qualification.id}/signature-challenges`,
        {}
      )
      .then((c) => {
        if (cancelled) return;
        setChallengeId(c.challenge_id);
        setMeaning(c.meaning);
      })
      .catch(() => {
        if (!cancelled) setError("Could not request a signature challenge");
      });
    return () => {
      cancelled = true;
    };
  }, [qualification.id, setError]);

  return (
    <Modal
      open
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          <Icon name="pen" /> Approve supplier qualification
        </span>
      }
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post(`/supplier-qualifications/${qualification.id}/approve`, {
              idempotency_key: newIdempotencyKey(),
              qualification_id: qualification.id,
              expected_version: qualification.version,
              decision,
              justification: justification || null,
              challenge_id: challengeId,
              reauth_password: password,
            })
          );
        }}
      >
        {meaning && (
          <p className="fs-3 mb-3">
            Meaning: <span className="font-semibold">{meaning}</span>
          </p>
        )}
        <div className="sig-hint mb-3">
          Fresh authentication required — re-enter your password to sign (Part 11 step-up).
        </div>
        <Field label="Decision" required>
          <Select value={decision} onChange={(e) => setDecision(e.target.value)}>
            <option value="approved">approved</option>
            <option value="conditional">conditional</option>
            <option value="rejected">rejected</option>
          </Select>
        </Field>
        <Field label="Justification" hint="Required for a conditional or rejected decision.">
          <textarea
            className="input"
            rows={3}
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
          />
        </Field>
        <Field label="Password" required>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !challengeId || !password}>
            <Icon name="badge-check" /> {busy ? "Signing…" : "Sign decision"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
