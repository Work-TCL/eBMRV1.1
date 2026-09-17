"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, canAuthorRecipe, canReleaseRecipe, clientPagedFetcher, newIdempotencyKey } from "@/lib/api";
import { useMe, useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import { Button, LinkButton } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import {
  type RecipeFamilyRow,
  type RecipeVersion,
  type SectionDraft,
  RecipeGraphEditor,
  buildGraphPayload,
  sectionsFromVersion,
  totalStepCount,
  useRoleAndRuleOptions,
} from "./shared";

export default function RecipeMasterPage() {
  const { me } = useMe();
  const { sites } = useSites();
  const router = useRouter();
  const [reloadToken, setReloadToken] = useState(0);

  const [selectedId, setSelectedId] = useState<string | null>(null);

  // "Versions" on a row reveals every version for that recipe family below the list — the released v1
  // alongside an in-progress draft v2, for example.
  const [openFamily, setOpenFamily] = useState<RecipeFamilyRow | null>(null);
  const [versions, setVersions] = useState<RecipeVersion[] | null>(null);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [versionsError, setVersionsError] = useState<string | null>(null);

  async function showVersions(family: RecipeFamilyRow) {
    setOpenFamily(family);
    setVersionsLoading(true);
    setVersionsError(null);
    try {
      setVersions(
        await api.get<RecipeVersion[]>(`/recipes/v2/${encodeURIComponent(family.recipe_family_id)}/versions`)
      );
    } catch (err) {
      setVersionsError(err instanceof ApiError ? err.message : "Lookup failed");
      setVersions(null);
    } finally {
      setVersionsLoading(false);
    }
  }

  // Deep link from /recipe-master/new after a successful create (`?openFamily=<id>`) — jump straight
  // to the new family's versions, same as the old DraftModal's onDone callback used to do inline. Reads
  // window.location directly rather than next/navigation's useSearchParams(), which needs a Suspense
  // boundary for static rendering this page has no other reason to opt into.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const familyId = params.get("openFamily");
    if (!familyId) return;
    let cancelled = false;
    api
      .get<RecipeFamilyRow[]>("/recipes/v2/families")
      .then((fresh) => {
        if (cancelled) return;
        const row = fresh.find((f) => f.recipe_family_id === familyId);
        if (row) showVersions(row);
      })
      .catch(() => {
        /* the families table still shows the new draft either way */
      });
    router.replace("/recipe-master");
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const siteName = (id: string) => sites.find((s) => s.id === id)?.name ?? id;

  // GET /recipes/v2/families returns a plain array, not the server-side Paged<T> envelope (Phase 1,
  // small row counts — same ceiling `listAll`/`clientPagedFetcher` document) — DataTable's
  // search/sort/paging is done client-side over that array here.
  const fetchFamilies = clientPagedFetcher<RecipeFamilyRow>(
    () => api.get<RecipeFamilyRow[]>("/recipes/v2/families"),
    { searchText: (f) => `${f.recipe_code} ${f.product_business_id}` }
  );

  const familyColumns: DataTableColumn<RecipeFamilyRow>[] = [
    {
      key: "recipe_code",
      header: "Recipe code",
      sortable: true,
      render: (f) => <span className="font-semibold tabular">{f.recipe_code}</span>,
    },
    {
      key: "product_business_id",
      header: "Product business ID",
      sortable: true,
      render: (f) => <span className="tabular fs-2">{f.product_business_id}</span>,
    },
    { key: "site_id", header: "Site", render: (f) => <span className="fs-2">{siteName(f.site_id)}</span> },
    { key: "manufacturing_profile_code", header: "Profile", render: (f) => <span className="fs-2">{f.manufacturing_profile_code}</span> },
    {
      key: "version_count",
      header: "Versions",
      sortable: true,
      render: (f) => <span className="tabular fs-2">{f.version_count}</span>,
    },
    {
      key: "latest_version_no",
      header: "Latest",
      render: (f) =>
        f.latest_version_no == null ? (
          <span className="text-muted fs-2">—</span>
        ) : (
          <span className="flex items-center gap-2">
            <span className="tabular fs-2">v{f.latest_version_no}</span>
            {f.latest_lifecycle_state && <WorkflowStatePill state={f.latest_lifecycle_state} />}
          </span>
        ),
    },
    {
      key: "actions",
      header: "",
      render: (f) => (
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="ghost" onClick={() => showVersions(f)}>
            Versions
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              showVersions(f);
              if (f.latest_recipe_version_id) setSelectedId(f.latest_recipe_version_id);
            }}
            disabled={!f.latest_recipe_version_id}
          >
            Open latest
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHead
        title="Recipe Master"
        subtitle="Master Recipe / Master Manufacturing Record. Author sections, steps and dependencies in one block, validate the graph, and release."
        action={
          canAuthorRecipe(me) ? (
            <LinkButton href="/recipe-master/new" variant="primary">
              <Icon name="plus" /> New draft
            </LinkButton>
          ) : undefined
        }
      />

      <Card className="mb-4">
        <CardHeader title="Recipes" meta="One row per recipe family, its latest version - click Versions for the full history." />
        <DataTable
          columns={familyColumns}
          fetchPage={fetchFamilies}
          rowKey={(f) => f.recipe_family_id}
          searchPlaceholder="Search by recipe code or product…"
          emptyIcon="database"
          emptyMessage={<>No recipes drafted yet - use &quot;New draft&quot; above to create one.</>}
          defaultSort={{ by: "recipe_code", dir: "asc" }}
          reloadToken={reloadToken}
        />
      </Card>

      {openFamily && (
        <Card>
          <CardHeader
            title={`Versions - ${openFamily.recipe_code}`}
            meta={
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setOpenFamily(null);
                  setVersions(null);
                }}
              >
                Close
              </Button>
            }
          />
          {versionsLoading ? (
            <p className="hint" style={{ padding: "var(--space-4, 16px)" }}>
              Loading…
            </p>
          ) : versionsError ? (
            <p className="error-text" style={{ padding: "var(--space-4, 16px)" }}>
              {versionsError}
            </p>
          ) : !versions || versions.length === 0 ? (
            <EmptyState icon="database">No versions exist for this recipe family yet.</EmptyState>
          ) : (
            <Table>
              <thead>
                <tr>
                  <th>Version</th>
                  <th>State</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v) => (
                  <tr key={v.recipe_version_id}>
                    <td className="font-semibold tabular">{v.version_no}</td>
                    <td>
                      <WorkflowStatePill state={v.lifecycle_state} />
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <Button size="sm" variant="secondary" onClick={() => setSelectedId(v.recipe_version_id)}>
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

      {selectedId && (
        <VersionDetailModal
          recipeVersionId={selectedId}
          allVersions={versions ?? []}
          onClose={() => setSelectedId(null)}
          onChanged={() => {
            setSelectedId(null);
            setReloadToken((n) => n + 1);
            if (openFamily) showVersions(openFamily);
          }}
        />
      )}
    </div>
  );
}

/** Edits an existing draft's whole graph via the same nested block used to create one
 * (`PUT /recipes/v2/drafts/{id}` — full replace, draft state only, code-verified
 * `recipe_master/commands.py::update_draft`). Pre-filled from the version's current sections/steps/
 * dependencies via `sectionsFromVersion`. */
function EditGraphModal({
  version,
  onClose,
  onDone,
}: {
  version: RecipeVersion;
  onClose: () => void;
  onDone: () => void;
}) {
  const [sections, setSections] = useState<SectionDraft[]>(() => sectionsFromVersion(version));
  const [batchSizeValue, setBatchSizeValue] = useState(version.batch_size_value ?? "");
  const [batchSizeUom, setBatchSizeUom] = useState(version.batch_size_uom ?? "");
  const { roleOptions, ruleOptions, materialSpecOptions, qualificationCodeOptions, uomOptions } = useRoleAndRuleOptions();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const graph = buildGraphPayload(sections);
      await api.put(`/recipes/v2/drafts/${version.recipe_version_id}`, {
        idempotency_key: newIdempotencyKey(),
        recipe_version_id: version.recipe_version_id,
        expected_version: version.version,
        ...(batchSizeValue ? { batch_size_value: batchSizeValue } : {}),
        ...(batchSizeUom ? { batch_size_uom: batchSizeUom } : {}),
        ...graph,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to save changes");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={`Edit draft - v${version.version_no}`} large>
      <form onSubmit={onSubmit}>
        <p className="hint mb-3">
          Product, recipe code, version and site are fixed once a draft exists - sections, steps and
          dependencies can still change while it stays a draft.
        </p>
        {error && <p className="error-text mb-2">{error}</p>}

        <div className="grid grid-cols-3 gap-4 mb-3">
          <Field label="Batch size (optional)">
            <Input value={batchSizeValue} onChange={(e) => setBatchSizeValue(e.target.value)} />
          </Field>
          <Field label="Batch size UOM (optional)">
            <Input list="dl-uom-batch-size" value={batchSizeUom} onChange={(e) => setBatchSizeUom(e.target.value)} />
            <datalist id="dl-uom-batch-size">
              {uomOptions.map((code) => (
                <option key={code} value={code} />
              ))}
            </datalist>
          </Field>
        </div>

        <RecipeGraphEditor sections={sections} onChange={setSections} roleOptions={roleOptions} ruleOptions={ruleOptions} materialSpecOptions={materialSpecOptions} qualificationCodeOptions={qualificationCodeOptions} uomOptions={uomOptions} />

        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || sections.length === 0 || totalStepCount(sections) === 0}>
            {busy ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

interface RecipeDiff {
  sections: { added: string[]; removed: string[]; changed: { code: string; changes: Record<string, { from: string; to: string }> }[] };
  steps: { added: string[]; removed: string[]; changed: { code: string; changes: Record<string, { from: string; to: string }> }[] };
}

/** Read-only tree: Section (collapsible) -> its Steps, each showing type/role/critical/dependencies
 * inline. Replaces the old flat "every step in one table, dependencies in a second disconnected table"
 * view, which stopped being legible once a recipe had more than a handful of steps. */
function RecipeGraphTree({ version }: { version: RecipeVersion }) {
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const sections = version.sections ?? [];
  const steps = version.steps ?? [];
  const dependencies = version.dependencies ?? [];
  const parameters = version.parameters ?? [];
  const materialReqs = version.material_requirements ?? [];
  const evidenceReqs = version.evidence_requirements ?? [];
  const equipmentReqs = version.equipment_requirements ?? [];

  function toggle(id: string) {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (sections.length === 0) {
    return <p className="hint mb-3">No sections declared.</p>;
  }

  return (
    <div className="mb-3">
      {[...sections]
        .sort((a, b) => a.sequence - b.sequence)
        .map((sec) => {
          const isOpen = !collapsedSections.has(sec.id);
          const stepsInSection = steps.filter((s) => s.section_id === sec.id).sort((a, b) => a.sequence_hint - b.sequence_hint);
          return (
            <div key={sec.id} style={{ border: "1px solid var(--border-hairline, #ddd)", borderRadius: 8, marginBottom: 8 }}>
              <button
                type="button"
                onClick={() => toggle(sec.id)}
                aria-label={isOpen ? "Collapse section" : "Expand section"}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  width: "100%",
                  background: "var(--surface-sunken, #f6f6f6)",
                  border: "none",
                  borderRadius: isOpen ? "8px 8px 0 0" : 8,
                  padding: "8px 10px",
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <Icon name={isOpen ? "chevron-down" : "chevron-right"} />
                <span className="tabular font-semibold">{sec.stable_section_code}</span>
                <span className="fs-2 text-muted">{sec.name}</span>
                {sec.parallel_group && <span className="fs-2 text-muted">parallel group: {sec.parallel_group}</span>}
                {sec.expected_duration_minutes != null && (
                  <span className="fs-2 text-muted">~{sec.expected_duration_minutes} min</span>
                )}
                <span className="fs-2 text-muted" style={{ marginLeft: "auto" }}>
                  {stepsInSection.length} step{stepsInSection.length === 1 ? "" : "s"}
                </span>
              </button>
              {isOpen && (
                <div style={{ padding: "4px 10px 8px" }}>
                  {stepsInSection.length === 0 ? (
                    <p className="hint" style={{ padding: "6px 0" }}>
                      No steps in this section.
                    </p>
                  ) : (
                    stepsInSection.map((s) => {
                      const preds = dependencies
                        .filter((d) => d.successor_step_id === s.id)
                        .map((d) => ({
                          code: steps.find((x) => x.id === d.predecessor_step_id)?.stable_step_code ?? d.predecessor_step_id.slice(0, 8),
                          rule: d.condition_rule_id,
                        }));
                      const stepParams = parameters.filter((p) => p.step_id === s.id);
                      const stepMaterials = materialReqs.filter((m) => m.step_id === s.id);
                      const stepEvidence = evidenceReqs.filter((e) => e.step_id === s.id);
                      const stepEquipment = equipmentReqs.filter((e) => e.step_id === s.id);
                      return (
                        <div key={s.id} style={{ padding: "6px 2px", borderTop: "1px solid var(--border-hairline, #eee)" }}>
                          <div className="flex flex-wrap items-center gap-3 fs-2">
                            <span className="tabular font-semibold" style={{ minWidth: 110 }}>
                              {s.stable_step_code}
                            </span>
                            <span style={{ minWidth: 110 }}>{s.step_type}</span>
                            <span style={{ minWidth: 140 }}>
                              {s.required_role_code ?? <span className="text-muted">any role</span>}
                            </span>
                            {s.required_qualification_code && <span>qual: {s.required_qualification_code}</span>}
                            {s.is_critical && <span className="error-text">Critical</span>}
                            {preds.length > 0 && (
                              <span className="text-muted">
                                Depends on: {preds.map((p) => (p.rule ? `${p.code} (if ${p.rule})` : p.code)).join(", ")}
                              </span>
                            )}
                          </div>
                          {s.instruction_text && (
                            <div className="fs-2" style={{ paddingLeft: 118, paddingTop: 2 }}>
                              {s.instruction_text}
                            </div>
                          )}
                          {stepParams.length > 0 && (
                            <div className="fs-2 text-muted" style={{ paddingLeft: 118, paddingTop: 2 }}>
                              Parameters:{" "}
                              {stepParams
                                .map((p) => {
                                  const range =
                                    p.target_value != null
                                      ? `target ${p.target_value}${p.uom ? ` ${p.uom}` : ""}`
                                      : p.min_value != null || p.max_value != null
                                        ? `${p.min_value ?? "—"}–${p.max_value ?? "—"}${p.uom ? ` ${p.uom}` : ""}`
                                        : null;
                                  return `${p.parameter_code} (${p.data_type}${range ? `, ${range}` : ""})`;
                                })
                                .join(", ")}
                            </div>
                          )}
                          {stepMaterials.length > 0 && (
                            <div className="fs-2 text-muted" style={{ paddingLeft: 118, paddingTop: 2 }}>
                              Materials:{" "}
                              {stepMaterials
                                .map((m) => {
                                  const range =
                                    m.target_value != null
                                      ? `target ${m.target_value}${m.uom ? ` ${m.uom}` : ""}`
                                      : m.min_value != null || m.max_value != null
                                        ? `${m.min_value ?? "—"}–${m.max_value ?? "—"}${m.uom ? ` ${m.uom}` : ""}`
                                        : null;
                                  return `${m.material_spec_version_id.slice(0, 8)}…${range ? ` (${range})` : ""}`;
                                })
                                .join(", ")}
                            </div>
                          )}
                          {stepEquipment.length > 0 && (
                            <div className="fs-2 text-muted" style={{ paddingLeft: 118, paddingTop: 2 }}>
                              Equipment: {stepEquipment.map((e) => e.equipment_class).join(", ")}
                            </div>
                          )}
                          {stepEvidence.length > 0 && (
                            <div className="fs-2 text-muted" style={{ paddingLeft: 118, paddingTop: 2 }}>
                              Evidence:{" "}
                              {stepEvidence.map((e) => `${e.evidence_type} (x${e.required_count})`).join(", ")}
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          );
        })}
    </div>
  );
}

function VersionDetailModal({
  recipeVersionId,
  allVersions,
  onClose,
  onChanged,
}: {
  recipeVersionId: string;
  allVersions: RecipeVersion[];
  onClose: () => void;
  onChanged: () => void;
}) {
  const { me } = useMe();
  const [version, setVersion] = useState<RecipeVersion | null>(null);
  const [eligibility, setEligibility] = useState<{ eligible: boolean; checks: Record<string, unknown> } | null>(null);
  const [simResult, setSimResult] = useState<{ complete: boolean; findings: string[] } | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [compareTo, setCompareTo] = useState("");
  const [diff, setDiff] = useState<RecipeDiff | null>(null);
  const [diffError, setDiffError] = useState<string | null>(null);
  const [releaseSigOpen, setReleaseSigOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);

  async function runCompare() {
    if (!compareTo) return;
    setDiffError(null);
    setDiff(null);
    try {
      setDiff(await api.get<RecipeDiff>(`/recipes/v2/versions/${recipeVersionId}/compare/${compareTo}`));
    } catch (err) {
      setDiffError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Compare failed");
    }
  }

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recipeVersionId]);

  async function refresh() {
    const [v, e] = await Promise.all([
      api.get<RecipeVersion>(`/recipes/v2/versions/${recipeVersionId}`),
      api.get<{ eligible: boolean; checks: Record<string, unknown> }>(`/recipes/v2/versions/${recipeVersionId}/issue-eligibility`),
    ]);
    setVersion(v);
    setEligibility(e);
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

  const simulate = async () => {
    setError(null);
    try {
      const result = await api.post<{ complete: boolean; findings: string[] }>(`/recipes/v2/drafts/${recipeVersionId}/simulate`);
      setSimResult(result);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Simulation failed");
    }
  };

  const validate = () =>
    runAction(() =>
      api.post(`/recipes/v2/drafts/${recipeVersionId}/validate`, {
        idempotency_key: newIdempotencyKey(),
        recipe_version_id: recipeVersionId,
      })
    );

  const submit = () =>
    runAction(() =>
      api.post(`/recipes/v2/drafts/${recipeVersionId}/submit`, {
        idempotency_key: newIdempotencyKey(),
        recipe_version_id: recipeVersionId,
        expected_version: version!.version,
      })
    );

  if (!version) {
    return (
      <Modal open onClose={onClose} title="Loading…">
        {error ? <p className="error-text">{error}</p> : <p>Loading…</p>}
      </Modal>
    );
  }

  return (
    <Modal open onClose={onClose} title={`${version.recipe_family_id.slice(0, 8)}… - v${version.version_no}`} large>
      <div className="mb-4">
        {(
          [
            ["Lifecycle state", version.lifecycle_state],
            [
              "Batch size",
              version.batch_size_value ? `${version.batch_size_value}${version.batch_size_uom ? ` ${version.batch_size_uom}` : ""}` : "—",
            ],
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

      <div className="flex items-center justify-between mb-1">
        <p className="fs-1 text-muted">
          Recipe graph ({version.sections?.length ?? 0} section{(version.sections?.length ?? 0) === 1 ? "" : "s"},{" "}
          {version.steps?.length ?? 0} step{(version.steps?.length ?? 0) === 1 ? "" : "s"})
        </p>
        {canAuthorRecipe(me) && version.lifecycle_state === "draft" && (
          <Button size="sm" variant="secondary" onClick={() => setEditOpen(true)} disabled={busy}>
            Edit
          </Button>
        )}
      </div>
      <RecipeGraphTree version={version} />

      {(version.lifecycle_state === "draft" || version.lifecycle_state === "under_review") && (
        <div className="mt-4">
          <Button size="sm" variant="secondary" onClick={simulate}>
            Simulate
          </Button>
          {simResult && (
            <p className="fs-2 mt-2">
              {simResult.complete ? (
                "Graph is complete - ready to submit/release."
              ) : (
                <>
                  Findings:
                  <ul style={{ paddingLeft: "1.2em" }}>
                    {simResult.findings.map((f) => (
                      <li key={f}>{f}</li>
                    ))}
                  </ul>
                </>
              )}
            </p>
          )}
        </div>
      )}

      {eligibility && (
        <div className="mt-4">
          <p className="fs-1 text-muted mb-1">Issue eligibility</p>
          <p className={eligibility.eligible ? "fs-2" : "error-text fs-2"}>
            {eligibility.eligible ? "Eligible to issue" : "Not eligible"}
          </p>
        </div>
      )}

      <div className="mt-4">
        <p className="fs-1 text-muted mb-1">Compare with another version</p>
        <div className="flex flex-wrap items-end gap-3">
          <Select value={compareTo} onChange={(e) => setCompareTo(e.target.value)} style={{ minWidth: 200, maxWidth: 220, width: "100%" }}>
            <option value="">- pick a version -</option>
            {allVersions
              .filter((v) => v.recipe_version_id !== recipeVersionId)
              .map((v) => (
                <option key={v.recipe_version_id} value={v.recipe_version_id}>
                  v{v.version_no} ({v.lifecycle_state})
                </option>
              ))}
          </Select>
          <Button size="sm" variant="secondary" onClick={runCompare} disabled={!compareTo}>
            Compare
          </Button>
        </div>
        {diffError && <p className="error-text fs-2 mt-2">{diffError}</p>}
        {diff && (
          <div className="mt-3">
            {(["sections", "steps"] as const).map((kind) => {
              const d = diff[kind];
              const empty = d.added.length === 0 && d.removed.length === 0 && d.changed.length === 0;
              return (
                <div key={kind} className="mb-3">
                  <p className="fs-2 font-semibold" style={{ textTransform: "capitalize" }}>
                    {kind}
                  </p>
                  {empty ? (
                    <p className="fs-2 text-muted">No differences.</p>
                  ) : (
                    <ul className="fs-2" style={{ paddingLeft: "1.2em" }}>
                      {d.added.map((c) => (
                        <li key={`a-${c}`}>
                          <span className="tabular">{c}</span> - added
                        </li>
                      ))}
                      {d.removed.map((c) => (
                        <li key={`r-${c}`}>
                          <span className="tabular">{c}</span> - removed
                        </li>
                      ))}
                      {d.changed.map((c) => (
                        <li key={`c-${c.code}`}>
                          <span className="tabular">{c.code}</span> -{" "}
                          {Object.entries(c.changes)
                            .map(([f, { from, to }]) => `${f}: ${from} → ${to}`)
                            .join("; ")}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {error && <p className="error-text mt-3">{error}</p>}

      <div className="flex justify-between gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        <div className="flex gap-2">
          {canAuthorRecipe(me) && version.lifecycle_state === "draft" && (
            <>
              <Button variant="secondary" onClick={validate} disabled={busy}>
                Validate
              </Button>
              <Button variant="primary" onClick={submit} disabled={busy}>
                Submit for review
              </Button>
            </>
          )}
          {canReleaseRecipe(me) && version.lifecycle_state === "under_review" && (
            <Button variant="success" onClick={() => setReleaseSigOpen(true)} disabled={busy}>
              Release
            </Button>
          )}
        </div>
      </div>

      {editOpen && (
        <EditGraphModal
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
          challengePath={`/recipes/v2/drafts/${recipeVersionId}/signature-challenges`}
          action="release"
          submitVariant="success"
          submitLabel="Sign & release"
          title={`Release recipe - v${version.version_no}`}
          summary={
            <>
              This releases recipe version <strong>v{version.version_no}</strong> - once released its
              graph is locked; a change needs a new version. Signed by a QA Releaser who is{" "}
              <strong>not</strong> the recipe&apos;s author (author ≠ releaser).
            </>
          }
          onSign={(p) =>
            api.post(`/recipes/v2/drafts/${recipeVersionId}/release`, {
              idempotency_key: p.idempotency_key,
              recipe_version_id: recipeVersionId,
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
