"use client";

import { useEffect, useMemo, useState } from "react";
import {
  api,
  ApiError,
  canAuthorRecipe,
  canReleaseRecipe,
  clientPagedFetcher,
  listAll,
  newIdempotencyKey,
} from "@/lib/api";
import { useApiResource, useMe, useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";

const STEP_TYPE_OPTIONS = [
  "instruction", "data_entry", "scan", "weigh", "equipment_check", "calculation", "ipc_qc", "signature",
  "verification", "timer", "hold_point", "material_consume", "assembly", "test", "packaging", "custom_approved_type",
];

// Same closed set product_master exposes (services/gxp-api/app/modules/product_master/service.py
// SUPPORTED_MANUFACTURING_PROFILES). The recipe's profile is best kept equal to the product version's.
const MANUFACTURING_PROFILES = ["pharma", "device", "injectable_ddcp", "inhalation_ddcp", "drug_eluting_device"];

// GET /products/v1/business-ids — one row per Product Master Business ID (its latest version).
interface ProductBusinessIdOption {
  product_business_id: string;
  name: string;
  version_no: number;
  lifecycle_state: string;
}
// GET /products/v1/{business_id}/versions — every version of one Business ID.
interface ProductVersionOption {
  product_version_id: string;
  product_business_id: string;
  version_no: number;
  name: string;
  lifecycle_state: string;
  manufacturing_profile_code: string;
  site_id: string;
}
// GET /rules/v1 — one row per rule with a currently-effective released version.
interface ReleasedRuleOption {
  rule_id: string;
  rule_type: string;
  semantic_version: string;
}

// Matches app/modules/recipe_master/router.py::_version_dict + graph dicts.
interface RecipeStep {
  id: string;
  stable_step_code: string;
  section_id: string;
  step_type: string;
  instruction_text: string | null;
  sequence_hint: number;
  required_role_code: string | null;
  is_critical: boolean;
}

interface RecipeSection {
  id: string;
  stable_section_code: string;
  name: string;
  sequence: number;
}

interface RecipeDependency {
  id: string;
  predecessor_step_id: string;
  successor_step_id: string;
  condition_rule_id: string | null;
  condition_rule_version: string | null;
}

interface RecipeVersion {
  recipe_version_id: string;
  recipe_family_id: string;
  version_no: number;
  product_version_id: string;
  lifecycle_state: string;
  released_vault_object_id: string | null;
  version_hash: string | null;
  version: number;
  sections?: RecipeSection[];
  steps?: RecipeStep[];
  dependencies?: RecipeDependency[];
}

// Matches app/modules/recipe_master/router.py::get_families / service.list_recipe_families.
interface RecipeFamilyRow {
  recipe_family_id: string;
  recipe_code: string;
  product_business_id: string;
  site_id: string;
  manufacturing_profile_code: string;
  family_lifecycle_state: string;
  version_count: number;
  latest_recipe_version_id: string | null;
  latest_version_no: number | null;
  latest_lifecycle_state: string | null;
  has_released: boolean;
}

// ---------------------------------------------------------------------------
// Editable graph draft shapes — one nested block (sections -> steps -> depends-on) instead of 3
// disconnected flat lists. `key` is a local-only React list key, never sent to the backend; the real
// identity for cross-references while editing is the (still-blank-able) `stable_*_code` text the user
// types, exactly as the API itself keys sections/steps by their stable code.
// ---------------------------------------------------------------------------

interface DependencyDraft {
  key: string;
  predecessor_step_code: string;
  condition_rule_id: string;
  condition_rule_version: string;
}
interface StepDraft {
  key: string;
  stable_step_code: string;
  step_type: string;
  is_critical: boolean;
  required_role_code: string;
  depends_on: DependencyDraft[];
}
interface SectionDraft {
  key: string;
  stable_section_code: string;
  name: string;
  steps: StepDraft[];
}

let localKeySeq = 0;
function newKey(): string {
  localKeySeq += 1;
  return `k${localKeySeq}`;
}
function emptyDependency(): DependencyDraft {
  return { key: newKey(), predecessor_step_code: "", condition_rule_id: "", condition_rule_version: "" };
}
function emptyStep(): StepDraft {
  return { key: newKey(), stable_step_code: "", step_type: STEP_TYPE_OPTIONS[0], is_critical: false, required_role_code: "", depends_on: [] };
}
function emptySection(): SectionDraft {
  return { key: newKey(), stable_section_code: "", name: "", steps: [] };
}

/** Reconstructs the nested editor shape from a loaded version's flat graph — used to seed the "Edit"
 * modal with the recipe's current content instead of starting from a blank block. */
function sectionsFromVersion(version: RecipeVersion): SectionDraft[] {
  const steps = version.steps ?? [];
  const sections = version.sections ?? [];
  const deps = version.dependencies ?? [];
  const stepById = new Map(steps.map((s) => [s.id, s]));
  return [...sections]
    .sort((a, b) => a.sequence - b.sequence)
    .map((sec) => ({
      key: newKey(),
      stable_section_code: sec.stable_section_code,
      name: sec.name,
      steps: steps
        .filter((s) => s.section_id === sec.id)
        .sort((a, b) => a.sequence_hint - b.sequence_hint)
        .map((s) => ({
          key: newKey(),
          stable_step_code: s.stable_step_code,
          step_type: s.step_type,
          is_critical: s.is_critical,
          required_role_code: s.required_role_code ?? "",
          depends_on: deps
            .filter((d) => d.successor_step_id === s.id)
            .map((d) => ({
              key: newKey(),
              predecessor_step_code: stepById.get(d.predecessor_step_id)?.stable_step_code ?? "",
              condition_rule_id: d.condition_rule_id ?? "",
              condition_rule_version: d.condition_rule_version ?? "",
            })),
        })),
    }));
}

/** The inverse — flattens the nested editor block back into the 3 arrays `CreateRecipeDraftCommand` /
 * `UpdateRecipeDraftCommand` expect. `sequence`/`sequence_hint` are derived from list order, so
 * reordering a section or step (the up/down buttons) is exactly how you change them — no separate
 * numeric field to keep in sync by hand. */
function buildGraphPayload(sections: SectionDraft[]) {
  const sectionsOut = sections.map((s, i) => ({
    stable_section_code: s.stable_section_code,
    name: s.name,
    sequence: i + 1,
  }));
  const stepsOut: Record<string, unknown>[] = [];
  const dependenciesOut: Record<string, unknown>[] = [];
  sections.forEach((sec) => {
    sec.steps.forEach((st, i) => {
      stepsOut.push({
        stable_step_code: st.stable_step_code,
        section_code: sec.stable_section_code,
        step_type: st.step_type,
        sequence_hint: i + 1,
        is_critical: st.is_critical,
        ...(st.required_role_code ? { required_role_code: st.required_role_code } : {}),
      });
      st.depends_on.forEach((d) => {
        if (!d.predecessor_step_code) return;
        dependenciesOut.push({
          predecessor_step_code: d.predecessor_step_code,
          successor_step_code: st.stable_step_code,
          ...(d.condition_rule_id ? { condition_rule_id: d.condition_rule_id } : {}),
          ...(d.condition_rule_version ? { condition_rule_version: d.condition_rule_version } : {}),
        });
      });
    });
  });
  return { sections: sectionsOut, steps: stepsOut, dependencies: dependenciesOut };
}

function totalStepCount(sections: SectionDraft[]): number {
  return sections.reduce((n, s) => n + s.steps.length, 0);
}
function allStepCodes(sections: SectionDraft[]): string[] {
  return sections.flatMap((s) => s.steps.map((st) => st.stable_step_code.trim())).filter(Boolean);
}

/** Shared by DraftModal (create) and EditGraphModal (edit) — both fetch the same picker data. */
function useRoleAndRuleOptions() {
  const [roleOptions, setRoleOptions] = useState<{ value: string; label: string }[]>([]);
  useEffect(() => {
    let cancelled = false;
    listAll<{ id: string; name: string }>("/roles")
      .then((rows) => {
        if (!cancelled) setRoleOptions(rows.map((r) => ({ value: r.name, label: r.name })));
      })
      .catch(() => {
        /* the field just falls back to no options */
      });
    return () => {
      cancelled = true;
    };
  }, []);
  const { data: releasedRules } = useApiResource<ReleasedRuleOption[]>("/rules/v1");
  const ruleOptions = useMemo(
    () => (releasedRules ?? []).map((r) => ({ value: r.rule_id, label: `${r.rule_id} — ${r.rule_type} v${r.semantic_version}` })),
    [releasedRules]
  );
  return { roleOptions, ruleOptions };
}

export default function RecipeMasterPage() {
  const { me } = useMe();
  const { sites } = useSites();
  const [reloadToken, setReloadToken] = useState(0);

  const [draftOpen, setDraftOpen] = useState(false);
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
            <Button variant="primary" onClick={() => setDraftOpen(true)}>
              <Icon name="plus" /> New draft
            </Button>
          ) : undefined
        }
      />

      <Card className="mb-4">
        <CardHeader title="Recipes" meta="One row per recipe family, its latest version — click Versions for the full history." />
        <DataTable
          columns={familyColumns}
          fetchPage={fetchFamilies}
          rowKey={(f) => f.recipe_family_id}
          searchPlaceholder="Search by recipe code or product…"
          emptyIcon="database"
          emptyMessage={<>No recipes drafted yet — use &quot;New draft&quot; above to create one.</>}
          defaultSort={{ by: "recipe_code", dir: "asc" }}
          reloadToken={reloadToken}
        />
      </Card>

      {openFamily && (
        <Card>
          <CardHeader
            title={`Versions — ${openFamily.recipe_code}`}
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

      {draftOpen && (
        <DraftModal
          onClose={() => setDraftOpen(false)}
          onDone={async (familyId) => {
            setDraftOpen(false);
            setReloadToken((n) => n + 1);
            // Jump straight to the just-created family's versions. Re-fetch the family list here (the
            // hook's reload is fire-and-forget) so the opened panel carries the real row metadata.
            try {
              const fresh = await api.get<RecipeFamilyRow[]>("/recipes/v2/families");
              const row = fresh.find((f) => f.recipe_family_id === familyId);
              if (row) showVersions(row);
            } catch {
              /* the families table still refreshed; the new draft is visible there */
            }
          }}
        />
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

// ---------------------------------------------------------------------------
// RecipeGraphEditor — one repeated block: Section -> its Steps -> each step's "Depends on" list.
// Replaces the old 3 disconnected Sections/Steps/Dependencies RepeatableRows blocks. Sections and
// steps are true repeatable blocks (add/remove/reorder); a step's dependencies are edited right where
// the step itself is, instead of a separate flat list keyed by typing step codes twice.
// ---------------------------------------------------------------------------

function RecipeGraphEditor({
  sections,
  onChange,
  roleOptions,
  ruleOptions,
}: {
  sections: SectionDraft[];
  onChange: (next: SectionDraft[]) => void;
  roleOptions: { value: string; label: string }[];
  ruleOptions: { value: string; label: string }[];
}) {
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());

  function toggleSection(key: string) {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function updateSection(key: string, patch: Partial<SectionDraft>) {
    onChange(sections.map((s) => (s.key === key ? { ...s, ...patch } : s)));
  }
  function removeSection(key: string) {
    onChange(sections.filter((s) => s.key !== key));
  }
  function addSection() {
    onChange([...sections, emptySection()]);
  }
  function moveSection(key: string, dir: -1 | 1) {
    const i = sections.findIndex((s) => s.key === key);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= sections.length) return;
    const next = [...sections];
    [next[i], next[j]] = [next[j], next[i]];
    onChange(next);
  }

  function updateStepDeps(sectionKey: string, stepKey: string, fn: (deps: DependencyDraft[]) => DependencyDraft[]) {
    onChange(
      sections.map((s) =>
        s.key !== sectionKey
          ? s
          : { ...s, steps: s.steps.map((st) => (st.key !== stepKey ? st : { ...st, depends_on: fn(st.depends_on) })) }
      )
    );
  }
  function updateStep(sectionKey: string, stepKey: string, patch: Partial<StepDraft>) {
    onChange(
      sections.map((s) =>
        s.key !== sectionKey ? s : { ...s, steps: s.steps.map((st) => (st.key === stepKey ? { ...st, ...patch } : st)) }
      )
    );
  }
  function removeStep(sectionKey: string, stepKey: string) {
    onChange(sections.map((s) => (s.key !== sectionKey ? s : { ...s, steps: s.steps.filter((st) => st.key !== stepKey) })));
  }
  function addStep(sectionKey: string) {
    onChange(sections.map((s) => (s.key !== sectionKey ? s : { ...s, steps: [...s.steps, emptyStep()] })));
  }
  function moveStep(sectionKey: string, stepKey: string, dir: -1 | 1) {
    onChange(
      sections.map((s) => {
        if (s.key !== sectionKey) return s;
        const i = s.steps.findIndex((st) => st.key === stepKey);
        const j = i + dir;
        if (i < 0 || j < 0 || j >= s.steps.length) return s;
        const steps = [...s.steps];
        [steps[i], steps[j]] = [steps[j], steps[i]];
        return { ...s, steps };
      })
    );
  }

  const stepCount = totalStepCount(sections);

  return (
    <div className="mb-3">
      <div className="flex items-center justify-between mb-2">
        <p className="fact-k">Sections, steps &amp; dependencies</p>
        <span className="hint">
          {sections.length} section{sections.length === 1 ? "" : "s"}, {stepCount} step{stepCount === 1 ? "" : "s"}
        </span>
      </div>
      <p className="hint mb-2">
        Build the recipe as one block: add a section, add its steps underneath, and for any step that must
        wait on another, add it under that step&apos;s &quot;Depends on&quot; list — no separate list to keep in
        sync by step code.
      </p>

      {sections.length === 0 && <p className="hint mb-2">No sections yet — add the first one below.</p>}

      {sections.map((section, sIndex) => {
        const isCollapsed = collapsedSections.has(section.key);
        return (
          <div
            key={section.key}
            style={{ border: "1px solid var(--border-strong, #ccc)", borderRadius: 8, marginBottom: 10 }}
          >
            <div
              className="flex items-center gap-2"
              style={{ padding: "8px 10px", background: "var(--surface-sunken, #f6f6f6)", borderRadius: "8px 8px 0 0" }}
            >
              <button
                type="button"
                onClick={() => toggleSection(section.key)}
                aria-label={isCollapsed ? "Expand section" : "Collapse section"}
                style={{ background: "none", border: "none", cursor: "pointer", padding: 4, display: "flex", flexShrink: 0 }}
              >
                <Icon name={isCollapsed ? "chevron-right" : "chevron-down"} />
              </button>
              <Input
                placeholder="Section code (e.g. SEC-FILL)"
                value={section.stable_section_code}
                onChange={(e) => updateSection(section.key, { stable_section_code: e.target.value })}
                style={{ maxWidth: 190 }}
                required
              />
              <Input
                placeholder="Section name"
                value={section.name}
                onChange={(e) => updateSection(section.key, { name: e.target.value })}
                style={{ flex: 1, minWidth: 0 }}
                required
              />
              <span className="hint" style={{ whiteSpace: "nowrap" }}>
                {section.steps.length} step{section.steps.length === 1 ? "" : "s"}
              </span>
              <Button type="button" size="sm" variant="ghost" onClick={() => moveSection(section.key, -1)} disabled={sIndex === 0} aria-label="Move section up">
                ↑
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => moveSection(section.key, 1)}
                disabled={sIndex === sections.length - 1}
                aria-label="Move section down"
              >
                ↓
              </Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => removeSection(section.key)}>
                <Icon name="x" /> Remove
              </Button>
            </div>

            {!isCollapsed && (
              <div style={{ padding: 10 }}>
                {section.steps.length === 0 && <p className="hint mb-2">No steps in this section yet.</p>}
                {section.steps.map((step, stIndex) => (
                  <StepBlock
                    key={step.key}
                    step={step}
                    stepIndex={stIndex}
                    stepCount={section.steps.length}
                    allStepCodes={allStepCodes(sections)}
                    roleOptions={roleOptions}
                    ruleOptions={ruleOptions}
                    onChange={(patch) => updateStep(section.key, step.key, patch)}
                    onRemove={() => removeStep(section.key, step.key)}
                    onMove={(dir) => moveStep(section.key, step.key, dir)}
                    onAddDependency={() => updateStepDeps(section.key, step.key, (deps) => [...deps, emptyDependency()])}
                    onRemoveDependency={(depKey) =>
                      updateStepDeps(section.key, step.key, (deps) => deps.filter((d) => d.key !== depKey))
                    }
                    onUpdateDependency={(depKey, patch) =>
                      updateStepDeps(section.key, step.key, (deps) => deps.map((d) => (d.key === depKey ? { ...d, ...patch } : d)))
                    }
                  />
                ))}
                <Button type="button" variant="secondary" size="sm" onClick={() => addStep(section.key)}>
                  <Icon name="plus" /> Add step
                </Button>
              </div>
            )}
          </div>
        );
      })}

      <Button type="button" variant="secondary" size="sm" onClick={addSection}>
        <Icon name="plus" /> Add section
      </Button>
      {sections.length === 0 && <p className="error-text mt-2">Add at least one section with one step.</p>}
    </div>
  );
}

function StepBlock({
  step,
  stepIndex,
  stepCount,
  allStepCodes: allCodes,
  roleOptions,
  ruleOptions,
  onChange,
  onRemove,
  onMove,
  onAddDependency,
  onRemoveDependency,
  onUpdateDependency,
}: {
  step: StepDraft;
  stepIndex: number;
  stepCount: number;
  allStepCodes: string[];
  roleOptions: { value: string; label: string }[];
  ruleOptions: { value: string; label: string }[];
  onChange: (patch: Partial<StepDraft>) => void;
  onRemove: () => void;
  onMove: (dir: -1 | 1) => void;
  onAddDependency: () => void;
  onRemoveDependency: (depKey: string) => void;
  onUpdateDependency: (depKey: string, patch: Partial<DependencyDraft>) => void;
}) {
  const predecessorOptions = allCodes.filter((c) => c && c !== step.stable_step_code.trim());

  return (
    <div className="sig-block mb-2">
      <div className="grid grid-cols-2 gap-3 mb-2">
        <Input
          placeholder="Step code (e.g. FILL-01)"
          value={step.stable_step_code}
          onChange={(e) => onChange({ stable_step_code: e.target.value })}
          required
        />
        <Select value={step.step_type} onChange={(e) => onChange({ step_type: e.target.value })} required>
          {STEP_TYPE_OPTIONS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
      </div>
      <div className="grid grid-cols-2 gap-3 mb-2">
        <Select value={step.required_role_code} onChange={(e) => onChange({ required_role_code: e.target.value })}>
          <option value="">Required role — any</option>
          {roleOptions.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </Select>
        <label className="flex items-center gap-2 fs-2">
          <input type="checkbox" checked={step.is_critical} onChange={(e) => onChange({ is_critical: e.target.checked })} />
          Critical step
        </label>
      </div>

      <div className="mb-2">
        <p className="hint mb-1">Depends on (must complete first)</p>
        {step.depends_on.length === 0 && <p className="hint mb-1">No dependency — this step is ready as soon as its section allows.</p>}
        {step.depends_on.map((dep) => (
          <div key={dep.key} className="flex flex-wrap items-center gap-2 mb-2">
            <Select
              value={dep.predecessor_step_code}
              onChange={(e) => onUpdateDependency(dep.key, { predecessor_step_code: e.target.value })}
              style={{ minWidth: 160 }}
            >
              <option value="">Select a step…</option>
              {predecessorOptions.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
            <Select
              value={dep.condition_rule_id}
              onChange={(e) => onUpdateDependency(dep.key, { condition_rule_id: e.target.value })}
              style={{ minWidth: 200 }}
            >
              <option value="">Condition rule — none (always required)</option>
              {ruleOptions.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </Select>
            {dep.condition_rule_id && (
              <Input
                placeholder="Rule version pin (optional)"
                value={dep.condition_rule_version}
                onChange={(e) => onUpdateDependency(dep.key, { condition_rule_version: e.target.value })}
                style={{ maxWidth: 160 }}
              />
            )}
            <Button type="button" size="sm" variant="ghost" onClick={() => onRemoveDependency(dep.key)}>
              <Icon name="x" />
            </Button>
          </div>
        ))}
        <Button type="button" size="sm" variant="ghost" onClick={onAddDependency} disabled={predecessorOptions.length === 0}>
          <Icon name="plus" /> Add dependency
        </Button>
        {predecessorOptions.length === 0 && <span className="hint" style={{ marginLeft: 8 }}>Add another step first.</span>}
      </div>

      <div className="flex justify-between items-center">
        <span className="hint">Step {stepIndex + 1} of {stepCount}</span>
        <div className="flex gap-1">
          <Button type="button" size="sm" variant="ghost" onClick={() => onMove(-1)} disabled={stepIndex === 0} aria-label="Move step up">
            ↑
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => onMove(1)} disabled={stepIndex === stepCount - 1} aria-label="Move step down">
            ↓
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={onRemove}>
            <Icon name="x" /> Remove
          </Button>
        </div>
      </div>
    </div>
  );
}

function DraftModal({ onClose, onDone }: { onClose: () => void; onDone: (recipeFamilyId: string) => void }) {
  const { sites } = useSites();
  const [productBusinessId, setProductBusinessId] = useState("");
  const [recipeCode, setRecipeCode] = useState("");
  const [productVersionId, setProductVersionId] = useState("");
  const [versionNo, setVersionNo] = useState("1");
  const [siteId, setSiteId] = useState("");
  const [profile, setProfile] = useState("pharma");
  const [sections, setSections] = useState<SectionDraft[]>([]);
  const { roleOptions, ruleOptions } = useRoleAndRuleOptions();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Product Master pickers — real dropdowns (Process Engineer holds product.view).
  const { data: businessIdOptions } = useApiResource<ProductBusinessIdOption[]>("/products/v1/business-ids");
  const [productVersions, setProductVersions] = useState<ProductVersionOption[]>([]);
  const [pvError, setPvError] = useState<string | null>(null);
  const pickedVersion = productVersions.find((v) => v.product_version_id === productVersionId);

  async function onPickBusinessId(bid: string) {
    setProductBusinessId(bid);
    setProductVersionId("");
    setProductVersions([]);
    setPvError(null);
    if (!bid) return;
    try {
      const rows = await api.get<ProductVersionOption[]>(`/products/v1/${encodeURIComponent(bid)}/versions`);
      // Released versions first, then newest — a recipe should normally target a released product version.
      rows.sort(
        (a, b) =>
          (a.lifecycle_state === "released" ? 0 : 1) - (b.lifecycle_state === "released" ? 0 : 1) || b.version_no - a.version_no
      );
      setProductVersions(rows);
    } catch (err) {
      setPvError(err instanceof ApiError ? err.message : "Could not load versions for this Business ID");
    }
  }

  function onPickVersion(pvId: string) {
    setProductVersionId(pvId);
    const pv = productVersions.find((v) => v.product_version_id === pvId);
    if (pv) {
      if (pv.site_id) setSiteId(pv.site_id);
      if (pv.manufacturing_profile_code) setProfile(pv.manufacturing_profile_code);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const graph = buildGraphPayload(sections);
      const receipt = await api.post<{ aggregate_id: string }>("/recipes/v2/drafts", {
        idempotency_key: newIdempotencyKey(),
        product_business_id: productBusinessId,
        recipe_code: recipeCode,
        version_no: Number(versionNo),
        product_version_id: productVersionId,
        site_id: siteId,
        manufacturing_profile_code: profile,
        ...graph,
      });
      const detail = await api.get<RecipeVersion>(`/recipes/v2/versions/${receipt.aggregate_id}`);
      onDone(detail.recipe_family_id);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to create draft");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="New recipe draft" large>
      <form onSubmit={onSubmit}>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Product" required hint="From Product Master">
            <Select value={productBusinessId} onChange={(e) => onPickBusinessId(e.target.value)} required autoFocus>
              <option value="">Select a product…</option>
              {(businessIdOptions ?? []).map((o) => (
                <option key={o.product_business_id} value={o.product_business_id}>
                  {o.product_business_id} — {o.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Recipe code" required>
            <Input value={recipeCode} onChange={(e) => setRecipeCode(e.target.value)} required />
          </Field>
          <Field label="Version no." required>
            <Input type="number" min={1} value={versionNo} onChange={(e) => setVersionNo(e.target.value)} required />
          </Field>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Field
            label="Product version"
            required
            hint={
              !productBusinessId
                ? "Pick a product first"
                : pickedVersion && pickedVersion.lifecycle_state !== "released"
                  ? "⚠ not released — a batch can only be created from a released product version"
                  : "The released product spec this recipe is authored against"
            }
          >
            <Select value={productVersionId} onChange={(e) => onPickVersion(e.target.value)} required disabled={!productBusinessId}>
              <option value="">{productBusinessId ? "Select a version…" : "—"}</option>
              {productVersions.map((v) => (
                <option key={v.product_version_id} value={v.product_version_id}>
                  v{v.version_no} — {v.name} ({v.lifecycle_state})
                </option>
              ))}
            </Select>
          </Field>
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
          <Field label="Manufacturing profile" required hint="Defaults to the product version's profile">
            <Select value={profile} onChange={(e) => setProfile(e.target.value)} required>
              {MANUFACTURING_PROFILES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
              {profile && !MANUFACTURING_PROFILES.includes(profile) && <option value={profile}>{profile}</option>}
            </Select>
          </Field>
        </div>
        {pvError && <p className="error-text mt-2">{pvError}</p>}
        {error && <p className="error-text mt-2">{error}</p>}

        <RecipeGraphEditor sections={sections} onChange={setSections} roleOptions={roleOptions} ruleOptions={ruleOptions} />

        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={
              busy ||
              !productBusinessId.trim() ||
              !recipeCode.trim() ||
              !siteId ||
              !productVersionId.trim() ||
              sections.length === 0 ||
              totalStepCount(sections) === 0
            }
          >
            {busy ? "Creating…" : "Create draft"}
          </Button>
        </div>
      </form>
    </Modal>
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
  const { roleOptions, ruleOptions } = useRoleAndRuleOptions();
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
    <Modal open onClose={onClose} title={`Edit draft — v${version.version_no}`} large>
      <form onSubmit={onSubmit}>
        <p className="hint mb-3">
          Product, recipe code, version and site are fixed once a draft exists — sections, steps and
          dependencies can still change while it stays a draft.
        </p>
        {error && <p className="error-text mb-2">{error}</p>}

        <RecipeGraphEditor sections={sections} onChange={setSections} roleOptions={roleOptions} ruleOptions={ruleOptions} />

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
                      return (
                        <div
                          key={s.id}
                          className="flex flex-wrap items-center gap-3 fs-2"
                          style={{ padding: "6px 2px", borderTop: "1px solid var(--border-hairline, #eee)" }}
                        >
                          <span className="tabular font-semibold" style={{ minWidth: 110 }}>
                            {s.stable_step_code}
                          </span>
                          <span style={{ minWidth: 110 }}>{s.step_type}</span>
                          <span style={{ minWidth: 140 }}>
                            {s.required_role_code ?? <span className="text-muted">any role</span>}
                          </span>
                          {s.is_critical && <span className="error-text">Critical</span>}
                          {preds.length > 0 && (
                            <span className="text-muted">
                              Depends on: {preds.map((p) => (p.rule ? `${p.code} (if ${p.rule})` : p.code)).join(", ")}
                            </span>
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
    <Modal open onClose={onClose} title={`${version.recipe_family_id.slice(0, 8)}… — v${version.version_no}`} large>
      <div className="mb-4">
        {(
          [
            ["Lifecycle state", version.lifecycle_state],
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
                "Graph is complete — ready to submit/release."
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
            <option value="">— pick a version —</option>
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
                          <span className="tabular">{c}</span> — added
                        </li>
                      ))}
                      {d.removed.map((c) => (
                        <li key={`r-${c}`}>
                          <span className="tabular">{c}</span> — removed
                        </li>
                      ))}
                      {d.changed.map((c) => (
                        <li key={`c-${c.code}`}>
                          <span className="tabular">{c.code}</span> —{" "}
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
          title={`Release recipe — v${version.version_no}`}
          summary={
            <>
              This releases recipe version <strong>v{version.version_no}</strong> — once released its
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
