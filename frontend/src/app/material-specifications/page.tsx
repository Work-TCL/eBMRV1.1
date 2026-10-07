"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, canAuthorMaterialSpec, canReleaseMaterialSpec, clientPagedFetcher, newIdempotencyKey, type MutationReceipt } from "@/lib/api";
import { useEntityOptions, useMe, useRequirePermission, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { Modal } from "@/components/ui/Modal";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { RepeatableRows, type RepeatRow, type RepeatSubField } from "@/components/shared/RepeatableFields";

interface MaterialSpecCriterion {
  id: string;
  sequence: number;
  test_name: string;
  specification_text: string;
  acceptance_criteria_text: string;
  fulfillment_path: string | null;
  version: number;
}

interface MaterialSpecVersion {
  material_spec_version_id: string;
  material_spec_business_id: string;
  version_no: number;
  material_id: string;
  name: string;
  lifecycle_state: string;
  version: number;
  // Only populated by GET /{material_spec_version_id} (the single-record detail fetch) -- the
  // list-of-versions-for-a-business-id endpoint doesn't include it.
  criteria?: MaterialSpecCriterion[] | null;
}

// Matches app/modules/material_specification/router.py::get_business_ids — one row per distinct
// material_spec_business_id (its highest version_no), same SG-081 read-side precedent as
// product_master's/recipe_master's own business-ids pickers.
interface SpecBusinessIdOption {
  material_spec_version_id: string;
  material_spec_business_id: string;
  name: string;
  version_no: number;
  lifecycle_state: string;
}

export default function MaterialSpecificationsPage() {
  const { me } = useRequirePermission("material_spec.view");
  const [newDraftOpen, setNewDraftOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  return (
    <div>
      <PageHead
        title="Material specification master"
        subtitle="Draft and release material specification versions (distinct from material lots / inventory - see /materials for that)."
        action={
          canAuthorMaterialSpec(me) && (
            <Button variant="primary" onClick={() => setNewDraftOpen(true)}>
              <Icon name="plus" /> New specification draft
            </Button>
          )
        }
      />

      <SpecificationsCard reloadToken={reloadToken} bumpReload={() => setReloadToken((n) => n + 1)} />

      {newDraftOpen && (
        <NewDraftModal
          onClose={() => setNewDraftOpen(false)}
          onDone={() => {
            setNewDraftOpen(false);
            setReloadToken((n) => n + 1);
          }}
        />
      )}
    </div>
  );
}

function SpecificationsCard({ reloadToken, bumpReload }: { reloadToken: number; bumpReload: () => void }) {
  const { me } = useMe();
  const router = useRouter();
  const [historyBusinessId, setHistoryBusinessId] = useState<string | null>(null);
  const [historyVersions, setHistoryVersions] = useState<MaterialSpecVersion[] | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [releasing, setReleasing] = useState<MaterialSpecVersion | null>(null);
  const [releaseLookupError, setReleaseLookupError] = useState<string | null>(null);
  const [viewingVersionId, setViewingVersionId] = useState<string | null>(null);

  // Deep link from the workflow-notifications bell, and now also the "back to source" link on a QC test
  // specification created off a release (`?material_spec_version_id=<id>`). Still drops a draft straight
  // into the release signature ceremony, but a non-draft version (the QC-spec case, always released by
  // definition -- see material_specification.commands.release_material_spec_version's QC-FR-001 bridge)
  // opens the read-only detail view instead: the release endpoint would just reject a second release.
  // Reads window.location directly rather than next/navigation's useSearchParams(), which needs a
  // Suspense boundary this page has no other reason to opt into.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const versionId = params.get("material_spec_version_id");
    if (!versionId) return;
    let cancelled = false;
    api
      .get<MaterialSpecVersion>(`/material-specifications/v1/${versionId}`)
      .then((version) => {
        if (cancelled) return;
        if (version.lifecycle_state === "draft") setReleasing(version);
        else setViewingVersionId(version.material_spec_version_id);
      })
      .catch((err) => {
        if (!cancelled) setReleaseLookupError(err instanceof ApiError ? err.message : "Could not load specification version");
      });
    router.replace("/material-specifications");
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // GET /material-specifications/v1/business-ids returns a plain array, not the server-side Paged<T>
  // envelope (Phase 1, small row counts — same ceiling product_master's/recipe_master's equivalent
  // lists document) — DataTable's search/sort/paging runs client-side over that array here.
  const fetchSpecs = clientPagedFetcher<SpecBusinessIdOption>(
    () => api.get<SpecBusinessIdOption[]>("/material-specifications/v1/business-ids"),
    { searchText: (s) => `${s.material_spec_business_id} ${s.name}` }
  );

  async function showHistory(businessId: string) {
    setHistoryBusinessId(businessId);
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      setHistoryVersions(
        await api.get<MaterialSpecVersion[]>(`/material-specifications/v1/${encodeURIComponent(businessId)}/versions`)
      );
    } catch (err) {
      setHistoryError(err instanceof ApiError ? err.message : "Could not load specification versions");
      setHistoryVersions(null);
    } finally {
      setHistoryLoading(false);
    }
  }

  // The list row only carries the latest version's id/state, not its record `version` (the release
  // command's optimistic-lock field) — fetch the full version detail before opening the signature
  // ceremony.
  async function releaseFromList(row: SpecBusinessIdOption) {
    setReleaseLookupError(null);
    try {
      setReleasing(await api.get<MaterialSpecVersion>(`/material-specifications/v1/${row.material_spec_version_id}`));
    } catch (err) {
      setReleaseLookupError(err instanceof ApiError ? err.message : "Could not load specification version");
    }
  }

  const columns: DataTableColumn<SpecBusinessIdOption>[] = [
    {
      key: "material_spec_business_id",
      header: "Business ID",
      sortable: true,
      render: (s) => <span className="font-semibold tabular">{s.material_spec_business_id}</span>,
    },
    { key: "name", header: "Name", sortable: true },
    {
      key: "version_no",
      header: "Latest version",
      sortable: true,
      render: (s) => <span className="tabular fs-2">v{s.version_no}</span>,
    },
    { key: "lifecycle_state", header: "State", sortable: true, render: (s) => <WorkflowStatePill state={s.lifecycle_state} /> },
    {
      key: "actions",
      header: "",
      render: (s) => (
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="ghost" onClick={() => setViewingVersionId(s.material_spec_version_id)}>
            <Icon name="eye" /> Open
          </Button>
          <Button size="sm" variant="ghost" onClick={() => showHistory(s.material_spec_business_id)}>
            Versions
          </Button>
          {s.lifecycle_state === "draft" && canReleaseMaterialSpec(me) && (
            <Button size="sm" variant="success" onClick={() => releaseFromList(s)}>
              <Icon name="pen" /> Release
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <Card className="mb-4">
      <CardHeader
        title="Material specifications"
        meta="One row per Business ID, its latest version - click Versions for the full history."
      />
      {releaseLookupError && (
        <p className="error-text mb-2" style={{ padding: "0 var(--space-4, 16px)" }}>
          {releaseLookupError}
        </p>
      )}
      <DataTable
        columns={columns}
        fetchPage={fetchSpecs}
        rowKey={(s) => s.material_spec_business_id}
        searchPlaceholder="Search by business ID or name…"
        emptyIcon="flask"
        emptyMessage={<>No material specifications drafted yet - use &quot;New specification draft&quot; above to create one.</>}
        defaultSort={{ by: "material_spec_business_id", dir: "asc" }}
        reloadToken={reloadToken}
      />

      {historyBusinessId && (
        <Card className="mt-4">
          <CardHeader
            title={`Versions - ${historyBusinessId}`}
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
                {historyVersions.map((v) => (
                  <tr key={v.material_spec_version_id}>
                    <td className="tabular">v{v.version_no}</td>
                    <td className="fs-2">{v.name}</td>
                    <td className="tabular fs-2" style={{ wordBreak: "break-all" }}>{v.material_id}</td>
                    <td>
                      <WorkflowStatePill state={v.lifecycle_state} />
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <div className="flex gap-2 justify-end">
                        <Button size="sm" variant="ghost" onClick={() => setViewingVersionId(v.material_spec_version_id)}>
                          <Icon name="eye" /> Open
                        </Button>
                        {v.lifecycle_state === "draft" && canReleaseMaterialSpec(me) && (
                          <Button size="sm" variant="success" onClick={() => setReleasing(v)}>
                            <Icon name="pen" /> Release
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
      )}

      {releasing && (
        <ReleaseModal
          version={releasing}
          onClose={() => setReleasing(null)}
          onDone={() => {
            setReleasing(null);
            bumpReload();
            if (historyBusinessId) void showHistory(historyBusinessId);
          }}
        />
      )}

      {viewingVersionId && <DetailModal versionId={viewingVersionId} onClose={() => setViewingVersionId(null)} />}
    </Card>
  );
}

// Client gap-analysis Phase 5: "open 1 detail modal per row" request -- a read-only view of a single
// specification version (its own metadata plus its full test-criteria list), fetched fresh every open so
// it always reflects the latest draft edits/release, same reasoning as ReleaseModal's own unconditional
// re-fetch above.
function DetailModal({ versionId, onClose }: { versionId: string; onClose: () => void }) {
  const [version, setVersion] = useState<MaterialSpecVersion | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<MaterialSpecVersion>(`/material-specifications/v1/${versionId}`)
      .then((v) => {
        if (!cancelled) setVersion(v);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load specification version");
      });
    return () => {
      cancelled = true;
    };
  }, [versionId]);

  return (
    <Modal
      open
      onClose={onClose}
      large
      title={version ? `${version.material_spec_business_id} v${version.version_no}` : "Specification detail"}
    >
      {error && <p className="error-text mb-2">{error}</p>}
      {!version && !error && <p className="hint">Loading…</p>}
      {version && (
        <>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <p className="fs-1 text-muted mb-1">Name</p>
              <p className="fs-3 font-semibold">{version.name}</p>
            </div>
            <div>
              <p className="fs-1 text-muted mb-1">State</p>
              <WorkflowStatePill state={version.lifecycle_state} />
            </div>
          </div>
          <p className="fs-2 font-semibold text-muted mb-2">Test criteria</p>
          {version.criteria && version.criteria.length > 0 ? (
            <CriteriaCards criteria={version.criteria} />
          ) : (
            <p className="hint">No test criteria were added to this version.</p>
          )}
        </>
      )}
    </Modal>
  );
}

// Client gap-analysis Phase 5 (2026-10-05): the client repeatedly described this exact three-column
// shape (matches a typical Certificate of Analysis table) as what a material specification should
// actually contain, instead of the free-text/no-UI-at-all state this form was in before.
const CRITERION_FULFILLMENT_OPTIONS = [
  { value: "in_house", label: "In-house test" },
  { value: "external_lab", label: "External lab" },
  { value: "supplier_coa", label: "Rely on supplier COA" },
];
const CRITERION_FULFILLMENT_LABELS: Record<string, string> = Object.fromEntries(
  CRITERION_FULFILLMENT_OPTIONS.map((o) => [o.value, o.label])
);

// Client gap-analysis Phase 5: replaces the old <Table> rendering of criteria (fine for a full-width
// page but forced to horizontally scroll once squeezed into a modal, since `.data-table` carries its own
// 640px min-width) with a stacked card per test -- reads top-to-bottom at any modal width instead of
// side-to-side, and is reused by both the release ceremony's "what you're about to approve" preview and
// the per-row "Open" detail view.
function CriteriaCards({ criteria }: { criteria: MaterialSpecCriterion[] }) {
  return (
    <div className="flex flex-col gap-3">
      {criteria.map((c, i) => (
        <div
          key={c.id}
          style={{
            border: "1px solid var(--border-hairline)",
            borderRadius: "var(--radius-md)",
            background: "var(--surface-sunken)",
            padding: "var(--space-4)",
          }}
        >
          <div className="flex items-center justify-between mb-2 gap-2">
            <span className="fs-3 font-semibold">
              {i + 1}. {c.test_name}
            </span>
            {c.fulfillment_path && (
              <span
                className="fs-1 text-muted"
                style={{ textTransform: "uppercase", letterSpacing: ".04em", whiteSpace: "nowrap" }}
              >
                {CRITERION_FULFILLMENT_LABELS[c.fulfillment_path] ?? c.fulfillment_path}
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="fs-1 text-muted mb-1">Specification</p>
              <p className="fs-2" style={{ margin: 0 }}>
                {c.specification_text || "—"}
              </p>
            </div>
            <div>
              <p className="fs-1 text-muted mb-1">Acceptance criteria</p>
              <p className="fs-2" style={{ margin: 0 }}>
                {c.acceptance_criteria_text || "—"}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function NewDraftModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { siteId } = useSiteId();
  const entities = useEntityOptions();
  const [materialId, setMaterialId] = useState("");
  const [name, setName] = useState("");
  const [criteriaRows, setCriteriaRows] = useState<RepeatRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const criterionSubFields: RepeatSubField[] = [
    { name: "test_name", label: "Test name", type: "text", required: true, placeholder: "e.g. Assay" },
    { name: "specification_text", label: "Specification", type: "text", required: true, placeholder: "e.g. White crystalline powder" },
    { name: "acceptance_criteria_text", label: "Acceptance criteria", type: "text", required: true, placeholder: "e.g. 98.0 to 102.0%" },
    { name: "fulfillment_path", label: "How it's tested", type: "select", options: CRITERION_FULFILLMENT_OPTIONS },
  ];
  const requiredCriterionFields = criterionSubFields.filter((sf) => sf.required);

  // The `*` on test_name/specification_text/acceptance_criteria_text above was purely cosmetic -- nothing
  // stopped submit from posting a row with, say, a test_name but a blank acceptance_criteria_text (the
  // backend's AddSpecificationCriterionCommand accepts empty strings). A row left entirely untouched is
  // still fine to submit (it's just dropped below, same as before); it's a row with *some* data but a
  // missing required field that has to block submission.
  const incompleteCriterionRows = criteriaRows
    .map((row, i) => ({ row, i }))
    .filter(({ row }) => Object.values(row).some((v) => (v ?? "").trim() !== ""))
    .filter(({ row }) => requiredCriterionFields.some((sf) => !(row[sf.name] ?? "").trim()))
    .map(({ i }) => i + 1);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId || incompleteCriterionRows.length > 0) return;
    setBusy(true);
    setError(null);
    try {
      // Client gap-analysis Phase 5: material_spec_business_id/version_no are no longer asked for here
      // (auto-derived/auto-incremented server-side) -- Material + Name + its test rows are the whole form
      // now, created and populated as one continuous action instead of two separately-navigated screens.
      const draft = await api.post<MutationReceipt>("/material-specifications/v1/drafts", {
        idempotency_key: newIdempotencyKey(),
        material_id: materialId.trim(),
        name: name.trim(),
        site_id: siteId,
      });
      // Submitted one at a time (not Promise.all) -- the backend computes each row's sequence as
      // max(existing)+1 without its own row lock, so concurrent inserts could race; a human filling one
      // form is not a true concurrency case, sequential awaits sidestep it entirely.
      for (const row of criteriaRows) {
        const anyFilled = Object.values(row).some((v) => (v ?? "").trim() !== "");
        if (!anyFilled) continue;
        await api.post("/material-specifications/v1/criteria", {
          idempotency_key: newIdempotencyKey(),
          material_spec_version_id: draft.aggregate_id,
          test_name: row.test_name.trim(),
          specification_text: row.specification_text.trim(),
          acceptance_criteria_text: row.acceptance_criteria_text.trim(),
          fulfillment_path: row.fulfillment_path || null,
        });
      }
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
        <EntityPickerField
          label="Material"
          required
          value={materialId}
          onChange={setMaterialId}
          options={entities.materials}
          status={entities.materialsStatus}
          kind="material"
        />
        <Field label="Name" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
        </Field>
        <RepeatableRows
          label="Test criteria"
          itemLabel="Test"
          hint="Add one row per test (matches a Certificate of Analysis table) — add as many as needed. You can keep adding/editing/removing rows after creating the draft, right up until it's released."
          subFields={criterionSubFields}
          value={criteriaRows}
          onChange={setCriteriaRows}
        />
        {incompleteCriterionRows.length > 0 && (
          <p className="error-text mb-2">
            <Icon name="alert-circle" /> Fill in all required fields (Test name, Specification, Acceptance criteria) for{" "}
            {incompleteCriterionRows.length === 1 ? `test ${incompleteCriterionRows[0]}` : `tests ${incompleteCriterionRows.join(", ")}`}
            , or remove the row.
          </p>
        )}
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={busy || !materialId.trim() || !name.trim() || !siteId || incompleteCriterionRows.length > 0}
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
  // Whichever entry point opened this (the list's "Release" button vs. the version-history table's own)
  // may or may not have already fetched criteria -- re-fetch detail here unconditionally so the releaser
  // can always actually see what they're approving before signing, same "approver must see the evidence
  // in the same window" requirement the client raised for supplier qualification documents.
  const [criteria, setCriteria] = useState<MaterialSpecCriterion[] | null>(version.criteria ?? null);
  useEffect(() => {
    let cancelled = false;
    api
      .get<MaterialSpecVersion>(`/material-specifications/v1/${version.material_spec_version_id}`)
      .then((v) => {
        if (!cancelled) setCriteria(v.criteria ?? []);
      })
      .catch(() => {
        // Non-fatal -- the signature ceremony itself still works without the criteria preview.
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version.material_spec_version_id]);

  return (
    <>
      <SignatureCeremony
        open
        onClose={onClose}
        onDone={onDone}
        large
        challengePath={`/material-specifications/v1/${version.material_spec_version_id}/signature-challenges`}
        action="release"
        title={`Release - ${version.material_spec_business_id} v${version.version_no}`}
        summary={
          <>
            <p className="mb-2">
              You are about to release <strong>{version.material_spec_business_id} v{version.version_no}</strong>.
            </p>
            {criteria && criteria.length > 0 ? (
              <CriteriaCards criteria={criteria} />
            ) : criteria && criteria.length === 0 ? (
              <p className="hint">No test criteria were added to this draft.</p>
            ) : null}
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
