"use client";

import { useState } from "react";
import { api, ApiError, newIdempotencyKey } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { Modal } from "@/components/ui/Modal";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";

interface MaterialSpecVersion {
  material_spec_version_id: string;
  material_spec_business_id: string;
  version_no: number;
  material_id: string;
  name: string;
  lifecycle_state: string;
  version: number;
}

export default function MaterialSpecificationsPage() {
  const { me } = useMe();
  const [newDraftOpen, setNewDraftOpen] = useState(false);

  return (
    <div>
      <PageHead
        title="Material specification master"
        subtitle="Draft and release material specification versions (distinct from material lots / inventory - see /materials for that)."
        action={
          me && (
            <Button variant="primary" onClick={() => setNewDraftOpen(true)}>
              <Icon name="plus" /> New specification draft
            </Button>
          )
        }
      />

      <VersionsCard />

      {newDraftOpen && (
        <NewDraftModal
          onClose={() => setNewDraftOpen(false)}
          onDone={() => setNewDraftOpen(false)}
        />
      )}
    </div>
  );
}

function VersionsCard() {
  const [businessId, setBusinessId] = useState("");
  const [versions, setVersions] = useState<MaterialSpecVersion[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [releasing, setReleasing] = useState<MaterialSpecVersion | null>(null);

  async function lookup() {
    if (!businessId.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setVersions(
        await api.get<MaterialSpecVersion[]>(`/material-specifications/v1/${encodeURIComponent(businessId.trim())}/versions`)
      );
    } catch (err) {
      setVersions(null);
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not load specification versions");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Specification versions" meta="" />
      <p className="fs-2 text-muted mb-3">No list-all-specifications endpoint exists - look up a specification by its business ID.</p>
      <div className="flex gap-2 items-end mb-3">
        <div style={{ flex: 1 }}>
          <Field label="Material spec business ID">
            <Input value={businessId} onChange={(e) => setBusinessId(e.target.value)} placeholder="e.g. MATSPEC-PFS-BODY-001" />
          </Field>
        </div>
        <Button variant="secondary" disabled={busy || !businessId.trim()} onClick={() => lookup()}>
          <Icon name="search" /> Look up
        </Button>
      </div>
      {error && <p className="error-text mb-2">{error}</p>}
      {versions &&
        (versions.length === 0 ? (
          <EmptyState icon="flask">No versions for this business ID.</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Version</th>
                <th>Name</th>
                <th>Material ID</th>
                <th>State</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.material_spec_version_id}>
                  <td className="tabular">v{v.version_no}</td>
                  <td className="fs-2">{v.name}</td>
                  <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>{v.material_id}</td>
                  <td>
                    <WorkflowStatePill state={v.lifecycle_state} />
                  </td>
                  <td style={{ textAlign: "right" }}>
                    {v.lifecycle_state === "draft" && (
                      <Button size="sm" variant="success" onClick={() => setReleasing(v)}>
                        <Icon name="pen" /> Release
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        ))}

      {releasing && (
        <ReleaseModal
          version={releasing}
          onClose={() => setReleasing(null)}
          onDone={() => {
            setReleasing(null);
            void lookup();
          }}
        />
      )}
    </Card>
  );
}

function NewDraftModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [businessId, setBusinessId] = useState("");
  const [versionNo, setVersionNo] = useState("1");
  const [materialId, setMaterialId] = useState("");
  const [name, setName] = useState("");
  const [siteId, setSiteId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/material-specifications/v1/drafts", {
        idempotency_key: newIdempotencyKey(),
        material_spec_business_id: businessId.trim(),
        version_no: Number(versionNo),
        material_id: materialId.trim(),
        name: name.trim(),
        site_id: siteId.trim(),
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not create draft");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="New material specification draft">
      <form onSubmit={submit}>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Business ID" required>
            <Input value={businessId} onChange={(e) => setBusinessId(e.target.value)} placeholder="e.g. MATSPEC-PFS-BODY-001" required autoFocus />
          </Field>
          <Field label="Version number" required>
            <Input type="number" min={1} value={versionNo} onChange={(e) => setVersionNo(e.target.value)} required />
          </Field>
          <Field label="Material ID" required hint="Find the material's ID on /materials.">
            <Input value={materialId} onChange={(e) => setMaterialId(e.target.value)} required />
          </Field>
          <Field label="Site ID" required>
            <Input value={siteId} onChange={(e) => setSiteId(e.target.value)} required />
          </Field>
        </div>
        <Field label="Name" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={busy || !businessId.trim() || !materialId.trim() || !name.trim() || !siteId.trim()}
          >
            {busy ? "Creating…" : "Create draft"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ReleaseModal({
  version,
  onClose,
  onDone,
}: {
  version: MaterialSpecVersion;
  onClose: () => void;
  onDone: () => void;
}) {
  return (
    <>
      <Banner tone="warn" title="Signature policy not yet configured">
        The challenge below is real, but no signature policy is configured for releasing a material
        specification version yet - the release itself will correctly fail closed until one is added.
      </Banner>
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        challengePath={`/material-specifications/v1/${version.material_spec_version_id}/signature-challenges`}
        action="release"
        title={`Release - ${version.material_spec_business_id} v${version.version_no}`}
        summary={
          <>
            You are about to release <strong>{version.material_spec_business_id} v{version.version_no}</strong>.
          </>
        }
        reason="none"
        onSign={async (payload) => {
          try {
            return await api.post(`/material-specifications/v1/drafts/${version.material_spec_version_id}/release`, {
              idempotency_key: payload.idempotency_key,
              material_spec_version_id: version.material_spec_version_id,
              expected_version: version.version,
              challenge_id: payload.challenge_id,
              reauth_password: payload.reauth_password,
            });
          } catch (err) {
            throw err instanceof ApiError ? err : new Error("Request failed");
          }
        }}
      />
    </>
  );
}
