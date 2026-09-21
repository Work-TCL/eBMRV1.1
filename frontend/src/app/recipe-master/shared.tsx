"use client";

// Shared between the Recipe Master list page (page.tsx) and the full-page create screen
// (new/page.tsx) -- types, draft-editing state helpers, the graph editor UI, and the shared
// picker hooks/components both need. Split out 2026-09-16 when "New draft" moved from a modal
// to its own /recipe-master/new page, so both pages can build the same graph editor without
// duplicating ~800 lines of it.
import { useEffect, useMemo, useState } from "react";
import { api, listAll } from "@/lib/api";
import { useApiResource } from "@/lib/hooks";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

export const STEP_TYPE_OPTIONS = [
  "instruction", "data_entry", "scan", "weigh", "equipment_check", "calculation", "ipc_qc", "signature",
  "verification", "timer", "hold_point", "material_consume", "assembly", "test", "packaging", "custom_approved_type",
];

// Same closed set product_master exposes (services/gxp-api/app/modules/product_master/service.py
// SUPPORTED_MANUFACTURING_PROFILES). The recipe's profile is best kept equal to the product version's.
export const MANUFACTURING_PROFILES = ["pharma", "device", "injectable_ddcp", "inhalation_ddcp", "drug_eluting_device"];

// GET /products/v1/business-ids — one row per Product Master Business ID (its latest version).
export interface ProductBusinessIdOption {
  product_business_id: string;
  name: string;
  version_no: number;
  lifecycle_state: string;
}
// GET /products/v1/{business_id}/versions — every version of one Business ID.
export interface ProductVersionOption {
  product_version_id: string;
  product_business_id: string;
  version_no: number;
  name: string;
  lifecycle_state: string;
  manufacturing_profile_code: string;
  site_id: string;
}
// GET /rules/v1 — one row per rule with a currently-effective released version.
export interface ReleasedRuleOption {
  rule_id: string;
  rule_type: string;
  semantic_version: string;
}
// GET /material-specifications/v1/business-ids — one row per Material Specification Business ID (its latest version).
export interface MaterialSpecBusinessIdOption {
  material_spec_version_id: string;
  material_spec_business_id: string;
  name: string;
  version_no: number;
  lifecycle_state: string;
}
// GET /material-specifications/v1/{business_id}/versions — every version of one Business ID.
export interface MaterialSpecVersionOption {
  material_spec_version_id: string;
  material_spec_business_id: string;
  version_no: number;
  name: string;
  lifecycle_state: string;
}

// Matches app/modules/recipe_master/router.py::_version_dict + graph dicts.
export interface RecipeStep {
  id: string;
  stable_step_code: string;
  section_id: string;
  step_type: string;
  instruction_text: string | null;
  sequence_hint: number;
  required_role_code: string | null;
  required_qualification_code: string | null;
  is_critical: boolean;
  // SG-048 #018, visibility-only slice — optional; unset means no "overdue hold" flag is ever computed
  // for this step at execution time.
  expected_hold_duration_minutes: number | null;
}

export interface RecipeSection {
  id: string;
  stable_section_code: string;
  name: string;
  sequence: number;
  parallel_group: string | null;
  expected_duration_minutes: number | null;
}

export interface RecipeDependency {
  id: string;
  predecessor_step_id: string;
  successor_step_id: string;
  condition_rule_id: string | null;
  condition_rule_version: string | null;
}

export interface RecipeParameter {
  id: string;
  step_id: string;
  parameter_code: string;
  data_type: string;
  uom: string | null;
  source_type: string;
  target_value: string | null;
  min_value: string | null;
  max_value: string | null;
  precision_digits: number | null;
  required: boolean;
  rule_id: string | null;
  rule_version: string | null;
  manual_fallback_policy: string | null;
}

export interface RecipeEvidenceRequirement {
  id: string;
  step_id: string;
  evidence_type: string;
  required_count: number;
  allowed_mime_types: string | null;
  retention_class: string | null;
}

// Known-limitations fix (docs/testing/demo-gujarati/07 §7.9 item 4): matches
// recipe_master/router.py::get_equipment_classes / _equipment_class_dict.
export interface EquipmentClassOption {
  id: string;
  class_code: string;
  name: string;
  description: string | null;
  status: string;
}

export interface RecipeEquipmentRequirement {
  id: string;
  step_id: string;
  equipment_class: string;
  equipment_class_id: string | null;
  exact_equipment_optional: boolean;
  require_current_calibration: boolean;
  require_current_qualification: boolean;
  require_current_cleaning: boolean;
}

export interface RecipeMaterialRequirement {
  id: string;
  step_id: string;
  material_spec_version_id: string;
  target_value: string | null;
  min_value: string | null;
  max_value: string | null;
  uom: string | null;
  alternative_material_spec_version_id: string | null;
  substitution_allowed: boolean;
  consume_mode: string | null;
  genealogy_required: boolean;
}

export interface RecipeVersion {
  recipe_version_id: string;
  recipe_family_id: string;
  version_no: number;
  product_version_id: string;
  lifecycle_state: string;
  superseded_by_version_id: string | null;
  batch_size_value: string | null;
  batch_size_uom: string | null;
  released_vault_object_id: string | null;
  version_hash: string | null;
  version: number;
  sections?: RecipeSection[];
  steps?: RecipeStep[];
  dependencies?: RecipeDependency[];
  parameters?: RecipeParameter[];
  evidence_requirements?: RecipeEvidenceRequirement[];
  material_requirements?: RecipeMaterialRequirement[];
  equipment_requirements?: RecipeEquipmentRequirement[];
}

// Matches app/modules/recipe_master/router.py::get_families / service.list_recipe_families.
export interface RecipeFamilyRow {
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

export interface DependencyDraft {
  key: string;
  predecessor_step_code: string;
  condition_rule_id: string;
  condition_rule_version: string;
}
export interface ParameterDraft {
  key: string;
  parameter_code: string;
  data_type: string;
  uom: string;
  source_type: string;
  target_value: string;
  min_value: string;
  max_value: string;
  precision_digits: string;
  required: boolean;
  rule_id: string;
  rule_version: string;
  manual_fallback_policy: string;
}
export interface MaterialRequirementDraft {
  key: string;
  material_spec_version_id: string;
  target_value: string;
  min_value: string;
  max_value: string;
  uom: string;
  alternative_material_spec_version_id: string;
  substitution_allowed: boolean;
  consume_mode: string;
  genealogy_required: boolean;
}
export interface EvidenceRequirementDraft {
  key: string;
  evidence_type: string;
  required_count: string;
  allowed_mime_types: string;
  retention_class: string;
}
export interface EquipmentRequirementDraft {
  key: string;
  equipment_class: string;
  equipment_class_id: string;
  exact_equipment_optional: boolean;
  require_current_calibration: boolean;
  require_current_qualification: boolean;
  require_current_cleaning: boolean;
}
export interface StepDraft {
  key: string;
  stable_step_code: string;
  step_type: string;
  instruction_text: string;
  is_critical: boolean;
  required_role_code: string;
  required_qualification_code: string;
  expected_hold_duration_minutes: string;
  depends_on: DependencyDraft[];
  parameters: ParameterDraft[];
  material_requirements: MaterialRequirementDraft[];
  evidence_requirements: EvidenceRequirementDraft[];
  equipment_requirements: EquipmentRequirementDraft[];
}
export interface SectionDraft {
  key: string;
  stable_section_code: string;
  name: string;
  parallel_group: string;
  expected_duration_minutes: string;
  steps: StepDraft[];
}

let localKeySeq = 0;
export function newKey(): string {
  localKeySeq += 1;
  return `k${localKeySeq}`;
}
export function emptyDependency(): DependencyDraft {
  return { key: newKey(), predecessor_step_code: "", condition_rule_id: "", condition_rule_version: "" };
}
export function emptyParameter(): ParameterDraft {
  return {
    key: newKey(),
    parameter_code: "",
    data_type: "",
    uom: "",
    source_type: "",
    target_value: "",
    min_value: "",
    max_value: "",
    precision_digits: "",
    required: true,
    rule_id: "",
    rule_version: "",
    manual_fallback_policy: "",
  };
}
export function emptyMaterialRequirement(): MaterialRequirementDraft {
  return {
    key: newKey(),
    material_spec_version_id: "",
    target_value: "",
    min_value: "",
    max_value: "",
    uom: "",
    alternative_material_spec_version_id: "",
    substitution_allowed: false,
    consume_mode: "",
    genealogy_required: true,
  };
}
export function emptyEvidenceRequirement(): EvidenceRequirementDraft {
  return { key: newKey(), evidence_type: "", required_count: "1", allowed_mime_types: "", retention_class: "" };
}
export function emptyEquipmentRequirement(): EquipmentRequirementDraft {
  return {
    key: newKey(),
    equipment_class: "",
    equipment_class_id: "",
    exact_equipment_optional: true,
    require_current_calibration: false,
    require_current_qualification: false,
    require_current_cleaning: false,
  };
}
export function emptyStep(): StepDraft {
  return {
    key: newKey(),
    stable_step_code: "",
    step_type: STEP_TYPE_OPTIONS[0],
    instruction_text: "",
    is_critical: false,
    required_role_code: "",
    required_qualification_code: "",
    expected_hold_duration_minutes: "",
    depends_on: [],
    parameters: [],
    material_requirements: [],
    evidence_requirements: [],
    equipment_requirements: [],
  };
}
export function emptySection(): SectionDraft {
  return { key: newKey(), stable_section_code: "", name: "", parallel_group: "", expected_duration_minutes: "", steps: [] };
}

/** Reconstructs the nested editor shape from a loaded version's flat graph — used to seed the "Edit"
 * modal with the recipe's current content instead of starting from a blank block. */
export function sectionsFromVersion(version: RecipeVersion): SectionDraft[] {
  const steps = version.steps ?? [];
  const sections = version.sections ?? [];
  const deps = version.dependencies ?? [];
  const params = version.parameters ?? [];
  const materialReqs = version.material_requirements ?? [];
  const evidenceReqs = version.evidence_requirements ?? [];
  const equipmentReqs = version.equipment_requirements ?? [];
  const stepById = new Map(steps.map((s) => [s.id, s]));
  return [...sections]
    .sort((a, b) => a.sequence - b.sequence)
    .map((sec) => ({
      key: newKey(),
      stable_section_code: sec.stable_section_code,
      name: sec.name,
      parallel_group: sec.parallel_group ?? "",
      expected_duration_minutes: sec.expected_duration_minutes != null ? String(sec.expected_duration_minutes) : "",
      steps: steps
        .filter((s) => s.section_id === sec.id)
        .sort((a, b) => a.sequence_hint - b.sequence_hint)
        .map((s) => ({
          key: newKey(),
          stable_step_code: s.stable_step_code,
          step_type: s.step_type,
          instruction_text: s.instruction_text ?? "",
          is_critical: s.is_critical,
          required_role_code: s.required_role_code ?? "",
          required_qualification_code: s.required_qualification_code ?? "",
          expected_hold_duration_minutes: s.expected_hold_duration_minutes != null ? String(s.expected_hold_duration_minutes) : "",
          depends_on: deps
            .filter((d) => d.successor_step_id === s.id)
            .map((d) => ({
              key: newKey(),
              predecessor_step_code: stepById.get(d.predecessor_step_id)?.stable_step_code ?? "",
              condition_rule_id: d.condition_rule_id ?? "",
              condition_rule_version: d.condition_rule_version ?? "",
            })),
          parameters: params
            .filter((p) => p.step_id === s.id)
            .map((p) => ({
              key: newKey(),
              parameter_code: p.parameter_code,
              data_type: p.data_type,
              uom: p.uom ?? "",
              source_type: p.source_type,
              target_value: p.target_value ?? "",
              min_value: p.min_value ?? "",
              max_value: p.max_value ?? "",
              precision_digits: p.precision_digits != null ? String(p.precision_digits) : "",
              required: p.required,
              rule_id: p.rule_id ?? "",
              rule_version: p.rule_version ?? "",
              manual_fallback_policy: p.manual_fallback_policy ?? "",
            })),
          material_requirements: materialReqs
            .filter((m) => m.step_id === s.id)
            .map((m) => ({
              key: newKey(),
              material_spec_version_id: m.material_spec_version_id,
              target_value: m.target_value ?? "",
              min_value: m.min_value ?? "",
              max_value: m.max_value ?? "",
              uom: m.uom ?? "",
              alternative_material_spec_version_id: m.alternative_material_spec_version_id ?? "",
              substitution_allowed: m.substitution_allowed,
              consume_mode: m.consume_mode ?? "",
              genealogy_required: m.genealogy_required,
            })),
          evidence_requirements: evidenceReqs
            .filter((e) => e.step_id === s.id)
            .map((e) => ({
              key: newKey(),
              evidence_type: e.evidence_type,
              required_count: String(e.required_count),
              allowed_mime_types: e.allowed_mime_types ?? "",
              retention_class: e.retention_class ?? "",
            })),
          equipment_requirements: equipmentReqs
            .filter((e) => e.step_id === s.id)
            .map((e) => ({
              key: newKey(),
              equipment_class: e.equipment_class,
              equipment_class_id: e.equipment_class_id ?? "",
              exact_equipment_optional: e.exact_equipment_optional,
              require_current_calibration: e.require_current_calibration,
              require_current_qualification: e.require_current_qualification,
              require_current_cleaning: e.require_current_cleaning,
            })),
        })),
    }));
}

/** The inverse — flattens the nested editor block back into the 3 arrays `CreateRecipeDraftCommand` /
 * `UpdateRecipeDraftCommand` expect. `sequence`/`sequence_hint` are derived from list order, so
 * reordering a section or step (the up/down buttons) is exactly how you change them — no separate
 * numeric field to keep in sync by hand. */
export function buildGraphPayload(sections: SectionDraft[]) {
  const sectionsOut = sections.map((s, i) => ({
    stable_section_code: s.stable_section_code,
    name: s.name,
    sequence: i + 1,
    ...(s.parallel_group ? { parallel_group: s.parallel_group } : {}),
    ...(s.expected_duration_minutes ? { expected_duration_minutes: Number(s.expected_duration_minutes) } : {}),
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
        ...(st.instruction_text ? { instruction_text: st.instruction_text } : {}),
        ...(st.required_role_code ? { required_role_code: st.required_role_code } : {}),
        ...(st.required_qualification_code ? { required_qualification_code: st.required_qualification_code } : {}),
        ...(st.expected_hold_duration_minutes ? { expected_hold_duration_minutes: Number(st.expected_hold_duration_minutes) } : {}),
        parameters: st.parameters
          .filter((p) => p.parameter_code.trim())
          .map((p) => ({
            parameter_code: p.parameter_code,
            data_type: p.data_type,
            source_type: p.source_type,
            required: p.required,
            ...(p.uom ? { uom: p.uom } : {}),
            ...(p.target_value ? { target_value: p.target_value } : {}),
            ...(p.min_value ? { min_value: p.min_value } : {}),
            ...(p.max_value ? { max_value: p.max_value } : {}),
            ...(p.precision_digits ? { precision_digits: Number(p.precision_digits) } : {}),
            ...(p.rule_id ? { rule_id: p.rule_id } : {}),
            ...(p.rule_id && p.rule_version ? { rule_version: p.rule_version } : {}),
            ...(p.manual_fallback_policy ? { manual_fallback_policy: p.manual_fallback_policy } : {}),
          })),
        material_requirements: st.material_requirements
          .filter((m) => m.material_spec_version_id.trim())
          .map((m) => ({
            material_spec_version_id: m.material_spec_version_id,
            substitution_allowed: m.substitution_allowed,
            genealogy_required: m.genealogy_required,
            ...(m.target_value ? { target_value: m.target_value } : {}),
            ...(m.min_value ? { min_value: m.min_value } : {}),
            ...(m.max_value ? { max_value: m.max_value } : {}),
            ...(m.uom ? { uom: m.uom } : {}),
            ...(m.alternative_material_spec_version_id
              ? { alternative_material_spec_version_id: m.alternative_material_spec_version_id }
              : {}),
            ...(m.consume_mode ? { consume_mode: m.consume_mode } : {}),
          })),
        evidence_requirements: st.evidence_requirements
          .filter((e) => e.evidence_type.trim())
          .map((e) => ({
            evidence_type: e.evidence_type,
            required_count: e.required_count ? Number(e.required_count) : 1,
            ...(e.allowed_mime_types ? { allowed_mime_types: e.allowed_mime_types } : {}),
            ...(e.retention_class ? { retention_class: e.retention_class } : {}),
          })),
        equipment_requirements: st.equipment_requirements
          .filter((e) => e.equipment_class.trim())
          .map((e) => ({
            equipment_class: e.equipment_class,
            ...(e.equipment_class_id ? { equipment_class_id: e.equipment_class_id } : {}),
            exact_equipment_optional: e.exact_equipment_optional,
            require_current_calibration: e.require_current_calibration,
            require_current_qualification: e.require_current_qualification,
            require_current_cleaning: e.require_current_cleaning,
          })),
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

export function totalStepCount(sections: SectionDraft[]): number {
  return sections.reduce((n, s) => n + s.steps.length, 0);
}
export function allStepCodes(sections: SectionDraft[]): string[] {
  return sections.flatMap((s) => s.steps.map((st) => st.stable_step_code.trim())).filter(Boolean);
}

/** Shared by DraftModal (create) and EditGraphModal (edit) — both fetch the same picker data. */
export function useRoleAndRuleOptions() {
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
    () => (releasedRules ?? []).map((r) => ({ value: r.rule_id, label: `${r.rule_id} - ${r.rule_type} v${r.semantic_version}` })),
    [releasedRules]
  );
  const { data: materialSpecOptions } = useApiResource<MaterialSpecBusinessIdOption[]>("/material-specifications/v1/business-ids");
  // SG-086: no qualification-code catalog table exists (iam.qualifications and qms.qualification_record
  // are two competing, non-authoritative grant stores for the same concept). Project-owner-directed
  // (asked directly, chose qms.qualification_record): suggest codes that have actually been granted,
  // via a <datalist> so a code not yet granted to anyone can still be typed (same pattern as DDCP's
  // free-text-with-suggestions fields, DdcpFieldControl.tsx).
  const { data: qualificationCodeOptions } = useApiResource<string[]>("/training/v1/qualification-codes");
  // §9.6's own honest note: parameter/material/batch-size UOM fields were free-text despite `gxp_uom`
  // already existing as released reference data -- suggest via <datalist> rather than a hard-validated
  // select, same reasoning as qualificationCodeOptions above: legacy/free-typed values that predate a
  // code's release must stay typeable, not silently blocked.
  const { data: releasedUoms } = useApiResource<{ code: string }[]>("/rules/v1/uom");
  const uomOptions = useMemo(() => (releasedUoms ?? []).map((u) => u.code), [releasedUoms]);
  // Known-limitations fix (docs/testing/demo-gujarati/07 §7.9 item 4): matches
  // recipe_master/router.py::get_equipment_classes / _equipment_class_dict.
  const { data: equipmentClassOptions } = useApiResource<EquipmentClassOption[]>("/recipes/v2/equipment-classes");
  return {
    roleOptions, ruleOptions, materialSpecOptions: materialSpecOptions ?? [],
    qualificationCodeOptions: qualificationCodeOptions ?? [], uomOptions,
    equipmentClassOptions: equipmentClassOptions ?? [],
  };
}

/** Two linked selects (Business ID -> version) for any field that references one Material Specification
 * version, e.g. a step's material_requirements. Resolves an existing `value` back to its business ID and
 * version list on mount (`GET /material-specifications/v1/{id}` then `.../{business_id}/versions`) so
 * editing an existing draft pre-fills both selects instead of showing a bare UUID. */
export function MaterialSpecVersionPicker({
  value,
  onChange,
  businessIdOptions,
  placeholder,
}: {
  value: string;
  onChange: (versionId: string) => void;
  businessIdOptions: MaterialSpecBusinessIdOption[];
  placeholder?: string;
}) {
  const [businessId, setBusinessId] = useState("");
  const [versions, setVersions] = useState<MaterialSpecVersionOption[]>([]);
  const [resolving, setResolving] = useState(false);

  useEffect(() => {
    // A blank value is a normal, valid intermediate state (business picked, no version yet - or
    // nothing picked at all) rather than something to resolve, so leave `businessId`/`versions`
    // alone here; clearing them belongs to the user-driven `onPickBusinessId` handler below,
    // otherwise this would race and clobber a business-id selection still in flight.
    if (!value || versions.some((v) => v.material_spec_version_id === value)) return;
    let cancelled = false;
    const resolve = async () => {
      setResolving(true);
      try {
        const v = await api.get<MaterialSpecVersionOption>(`/material-specifications/v1/${encodeURIComponent(value)}`);
        if (cancelled) return;
        setBusinessId(v.material_spec_business_id);
        const rows = await api.get<MaterialSpecVersionOption[]>(
          `/material-specifications/v1/${encodeURIComponent(v.material_spec_business_id)}/versions`
        );
        if (!cancelled) setVersions(rows);
      } catch {
        /* unknown/stale id - selects stay empty, the raw id is still carried in the draft either way */
      } finally {
        if (!cancelled) setResolving(false);
      }
    };
    resolve();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  async function onPickBusinessId(bid: string) {
    setBusinessId(bid);
    setVersions([]);
    onChange("");
    if (!bid) return;
    const rows = await api.get<MaterialSpecVersionOption[]>(`/material-specifications/v1/${encodeURIComponent(bid)}/versions`);
    rows.sort(
      (a, b) =>
        (a.lifecycle_state === "released" ? 0 : 1) - (b.lifecycle_state === "released" ? 0 : 1) || b.version_no - a.version_no
    );
    setVersions(rows);
  }

  return (
    <div className="flex gap-2">
      <Select value={businessId} onChange={(e) => onPickBusinessId(e.target.value)} style={{ minWidth: 170 }}>
        <option value="">{placeholder ?? "Material spec"} - select…</option>
        {businessIdOptions.map((o) => (
          <option key={o.material_spec_business_id} value={o.material_spec_business_id}>
            {o.material_spec_business_id} - {o.name}
          </option>
        ))}
      </Select>
      <Select value={value} onChange={(e) => onChange(e.target.value)} style={{ minWidth: 130 }} disabled={!businessId}>
        <option value="">{resolving ? "Loading…" : businessId ? "Version…" : "—"}</option>
        {versions.map((v) => (
          <option key={v.material_spec_version_id} value={v.material_spec_version_id}>
            v{v.version_no} ({v.lifecycle_state})
          </option>
        ))}
      </Select>
    </div>
  );
}


// ---------------------------------------------------------------------------
// RecipeGraphEditor — one repeated block: Section -> its Steps -> each step's "Depends on" list.
// Replaces the old 3 disconnected Sections/Steps/Dependencies RepeatableRows blocks. Sections and
// steps are true repeatable blocks (add/remove/reorder); a step's dependencies are edited right where
// the step itself is, instead of a separate flat list keyed by typing step codes twice.
// ---------------------------------------------------------------------------

export function RecipeGraphEditor({
  sections,
  onChange,
  roleOptions,
  ruleOptions,
  materialSpecOptions,
  qualificationCodeOptions,
  uomOptions,
  equipmentClassOptions,
}: {
  sections: SectionDraft[];
  onChange: (next: SectionDraft[]) => void;
  roleOptions: { value: string; label: string }[];
  ruleOptions: { value: string; label: string }[];
  materialSpecOptions: MaterialSpecBusinessIdOption[];
  qualificationCodeOptions: string[];
  uomOptions: string[];
  equipmentClassOptions: EquipmentClassOption[];
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
  function updateStepParams(sectionKey: string, stepKey: string, fn: (params: ParameterDraft[]) => ParameterDraft[]) {
    onChange(
      sections.map((s) =>
        s.key !== sectionKey
          ? s
          : { ...s, steps: s.steps.map((st) => (st.key !== stepKey ? st : { ...st, parameters: fn(st.parameters) })) }
      )
    );
  }
  function updateStepMaterialReqs(
    sectionKey: string,
    stepKey: string,
    fn: (reqs: MaterialRequirementDraft[]) => MaterialRequirementDraft[]
  ) {
    onChange(
      sections.map((s) =>
        s.key !== sectionKey
          ? s
          : {
              ...s,
              steps: s.steps.map((st) => (st.key !== stepKey ? st : { ...st, material_requirements: fn(st.material_requirements) })),
            }
      )
    );
  }
  function updateStepEvidenceReqs(
    sectionKey: string,
    stepKey: string,
    fn: (reqs: EvidenceRequirementDraft[]) => EvidenceRequirementDraft[]
  ) {
    onChange(
      sections.map((s) =>
        s.key !== sectionKey
          ? s
          : {
              ...s,
              steps: s.steps.map((st) => (st.key !== stepKey ? st : { ...st, evidence_requirements: fn(st.evidence_requirements) })),
            }
      )
    );
  }
  function updateStepEquipmentReqs(
    sectionKey: string,
    stepKey: string,
    fn: (reqs: EquipmentRequirementDraft[]) => EquipmentRequirementDraft[]
  ) {
    onChange(
      sections.map((s) =>
        s.key !== sectionKey
          ? s
          : {
              ...s,
              steps: s.steps.map((st) => (st.key !== stepKey ? st : { ...st, equipment_requirements: fn(st.equipment_requirements) })),
            }
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
        wait on another, add it under that step&apos;s &quot;Depends on&quot; list - no separate list to keep in
        sync by step code.
      </p>

      {sections.length === 0 && <p className="hint mb-2">No sections yet - add the first one below.</p>}

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
                <div className="flex flex-wrap items-center gap-3 mb-2">
                  <Input
                    placeholder="Parallel group (optional)"
                    value={section.parallel_group}
                    onChange={(e) => updateSection(section.key, { parallel_group: e.target.value })}
                    style={{ maxWidth: 220 }}
                  />
                  <Input
                    type="number"
                    min={0}
                    placeholder="Expected duration (minutes, optional)"
                    value={section.expected_duration_minutes}
                    onChange={(e) => updateSection(section.key, { expected_duration_minutes: e.target.value })}
                    style={{ maxWidth: 240 }}
                  />
                </div>
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
                    materialSpecOptions={materialSpecOptions}
                    qualificationCodeOptions={qualificationCodeOptions}
                    uomOptions={uomOptions}
                    equipmentClassOptions={equipmentClassOptions}
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
                    onAddParameter={() => updateStepParams(section.key, step.key, (params) => [...params, emptyParameter()])}
                    onRemoveParameter={(paramKey) =>
                      updateStepParams(section.key, step.key, (params) => params.filter((p) => p.key !== paramKey))
                    }
                    onUpdateParameter={(paramKey, patch) =>
                      updateStepParams(section.key, step.key, (params) =>
                        params.map((p) => (p.key === paramKey ? { ...p, ...patch } : p))
                      )
                    }
                    onAddMaterialRequirement={() =>
                      updateStepMaterialReqs(section.key, step.key, (reqs) => [...reqs, emptyMaterialRequirement()])
                    }
                    onRemoveMaterialRequirement={(reqKey) =>
                      updateStepMaterialReqs(section.key, step.key, (reqs) => reqs.filter((r) => r.key !== reqKey))
                    }
                    onUpdateMaterialRequirement={(reqKey, patch) =>
                      updateStepMaterialReqs(section.key, step.key, (reqs) =>
                        reqs.map((r) => (r.key === reqKey ? { ...r, ...patch } : r))
                      )
                    }
                    onAddEvidenceRequirement={() =>
                      updateStepEvidenceReqs(section.key, step.key, (reqs) => [...reqs, emptyEvidenceRequirement()])
                    }
                    onRemoveEvidenceRequirement={(reqKey) =>
                      updateStepEvidenceReqs(section.key, step.key, (reqs) => reqs.filter((r) => r.key !== reqKey))
                    }
                    onUpdateEvidenceRequirement={(reqKey, patch) =>
                      updateStepEvidenceReqs(section.key, step.key, (reqs) =>
                        reqs.map((r) => (r.key === reqKey ? { ...r, ...patch } : r))
                      )
                    }
                    onAddEquipmentRequirement={() =>
                      updateStepEquipmentReqs(section.key, step.key, (reqs) => [...reqs, emptyEquipmentRequirement()])
                    }
                    onRemoveEquipmentRequirement={(reqKey) =>
                      updateStepEquipmentReqs(section.key, step.key, (reqs) => reqs.filter((r) => r.key !== reqKey))
                    }
                    onUpdateEquipmentRequirement={(reqKey, patch) =>
                      updateStepEquipmentReqs(section.key, step.key, (reqs) =>
                        reqs.map((r) => (r.key === reqKey ? { ...r, ...patch } : r))
                      )
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

export function StepBlock({
  step,
  stepIndex,
  stepCount,
  allStepCodes: allCodes,
  roleOptions,
  ruleOptions,
  materialSpecOptions,
  qualificationCodeOptions,
  uomOptions,
  equipmentClassOptions,
  onChange,
  onRemove,
  onMove,
  onAddDependency,
  onRemoveDependency,
  onUpdateDependency,
  onAddParameter,
  onRemoveParameter,
  onUpdateParameter,
  onAddMaterialRequirement,
  onRemoveMaterialRequirement,
  onUpdateMaterialRequirement,
  onAddEvidenceRequirement,
  onRemoveEvidenceRequirement,
  onUpdateEvidenceRequirement,
  onAddEquipmentRequirement,
  onRemoveEquipmentRequirement,
  onUpdateEquipmentRequirement,
}: {
  step: StepDraft;
  stepIndex: number;
  stepCount: number;
  allStepCodes: string[];
  roleOptions: { value: string; label: string }[];
  ruleOptions: { value: string; label: string }[];
  materialSpecOptions: MaterialSpecBusinessIdOption[];
  qualificationCodeOptions: string[];
  uomOptions: string[];
  equipmentClassOptions: EquipmentClassOption[];
  onChange: (patch: Partial<StepDraft>) => void;
  onRemove: () => void;
  onMove: (dir: -1 | 1) => void;
  onAddDependency: () => void;
  onRemoveDependency: (depKey: string) => void;
  onUpdateDependency: (depKey: string, patch: Partial<DependencyDraft>) => void;
  onAddParameter: () => void;
  onRemoveParameter: (paramKey: string) => void;
  onUpdateParameter: (paramKey: string, patch: Partial<ParameterDraft>) => void;
  onAddMaterialRequirement: () => void;
  onRemoveMaterialRequirement: (reqKey: string) => void;
  onUpdateMaterialRequirement: (reqKey: string, patch: Partial<MaterialRequirementDraft>) => void;
  onAddEvidenceRequirement: () => void;
  onRemoveEvidenceRequirement: (reqKey: string) => void;
  onUpdateEvidenceRequirement: (reqKey: string, patch: Partial<EvidenceRequirementDraft>) => void;
  onAddEquipmentRequirement: () => void;
  onRemoveEquipmentRequirement: (reqKey: string) => void;
  onUpdateEquipmentRequirement: (reqKey: string, patch: Partial<EquipmentRequirementDraft>) => void;
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
      <textarea
        className="input mb-2"
        rows={2}
        placeholder="Instruction text - what the operator reads and does at this step"
        value={step.instruction_text}
        onChange={(e) => onChange({ instruction_text: e.target.value })}
      />

      <div className="grid grid-cols-2 gap-3 mb-2">
        <Select value={step.required_role_code} onChange={(e) => onChange({ required_role_code: e.target.value })}>
          <option value="">Required role - any</option>
          {roleOptions.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </Select>
        <div>
          <Input
            placeholder="Required qualification code (optional)"
            list={`dl-qual-${step.key}`}
            value={step.required_qualification_code}
            onChange={(e) => onChange({ required_qualification_code: e.target.value })}
          />
          <datalist id={`dl-qual-${step.key}`}>
            {qualificationCodeOptions.map((code) => (
              <option key={code} value={code} />
            ))}
          </datalist>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 mb-2">
        <div>
          <Input
            type="number"
            placeholder="Expected hold duration, minutes (optional)"
            value={step.expected_hold_duration_minutes}
            onChange={(e) => onChange({ expected_hold_duration_minutes: e.target.value })}
          />
          <p className="hint mt-1">
            If a hold on this step is left open longer than this, execution shows an &quot;overdue&quot;
            flag. Leave blank for no flag — nothing is enforced either way.
          </p>
        </div>
      </div>
      <div className="mb-2">
        <label className="flex items-center gap-2 fs-2">
          <input type="checkbox" checked={step.is_critical} onChange={(e) => onChange({ is_critical: e.target.checked })} />
          Critical step
        </label>
      </div>

      <div className="mb-2">
        <p className="hint mb-1">Depends on (must complete first)</p>
        {step.depends_on.length === 0 && <p className="hint mb-1">No dependency - this step is ready as soon as its section allows.</p>}
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
              <option value="">Condition rule - none (always required)</option>
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

      <div className="mb-2">
        <p className="hint mb-1">Parameters (what gets recorded at this step, and its acceptance limits)</p>
        {step.parameters.length === 0 && <p className="hint mb-1">No parameters - this step records nothing beyond its status.</p>}
        {step.parameters.map((param) => (
          <div key={param.key} className="sig-block mb-2" style={{ background: "var(--surface-sunken, #f6f6f6)" }}>
            <div className="grid grid-cols-3 gap-3 mb-2">
              <Input
                placeholder="Parameter code (e.g. mixing_temp_c)"
                value={param.parameter_code}
                onChange={(e) => onUpdateParameter(param.key, { parameter_code: e.target.value })}
                required
              />
              <Input
                placeholder="Data type (decimal / integer / text / boolean)"
                value={param.data_type}
                onChange={(e) => onUpdateParameter(param.key, { data_type: e.target.value })}
                required
              />
              <Input
                placeholder="Source (manual_entry / equipment_reading / calculated / scan)"
                value={param.source_type}
                onChange={(e) => onUpdateParameter(param.key, { source_type: e.target.value })}
                required
              />
            </div>
            <div className="grid grid-cols-4 gap-3 mb-2">
              <Select
                value={param.uom ?? ""}
                onChange={(e) => onUpdateParameter(param.key, { uom: e.target.value })}
              >
                <option value="">UOM (optional)</option>
                {uomOptions.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
                {param.uom && !uomOptions.includes(param.uom) && <option value={param.uom}>{param.uom}</option>}
              </Select>
              <Input
                placeholder="Target"
                value={param.target_value}
                onChange={(e) => onUpdateParameter(param.key, { target_value: e.target.value })}
              />
              <Input
                placeholder="Min"
                value={param.min_value}
                onChange={(e) => onUpdateParameter(param.key, { min_value: e.target.value })}
              />
              <Input
                placeholder="Max"
                value={param.max_value}
                onChange={(e) => onUpdateParameter(param.key, { max_value: e.target.value })}
              />
            </div>
            <div className="flex flex-wrap items-center gap-3 mb-2">
              <Input
                placeholder="Precision (decimal digits, optional)"
                type="number"
                min={0}
                value={param.precision_digits}
                onChange={(e) => onUpdateParameter(param.key, { precision_digits: e.target.value })}
                style={{ maxWidth: 200 }}
              />
              <Select
                value={param.rule_id}
                onChange={(e) => onUpdateParameter(param.key, { rule_id: e.target.value, rule_version: "" })}
                style={{ minWidth: 200 }}
              >
                <option value="">Validation rule - none</option>
                {ruleOptions.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </Select>
              {param.rule_id && (
                <Input
                  placeholder="Rule version pin (optional)"
                  value={param.rule_version}
                  onChange={(e) => onUpdateParameter(param.key, { rule_version: e.target.value })}
                  style={{ maxWidth: 160 }}
                />
              )}
              {param.rule_id && (
                <Input
                  placeholder="Manual fallback policy (if the rule can't run)"
                  value={param.manual_fallback_policy}
                  onChange={(e) => onUpdateParameter(param.key, { manual_fallback_policy: e.target.value })}
                  style={{ maxWidth: 220 }}
                />
              )}
              <label className="flex items-center gap-2 fs-2">
                <input
                  type="checkbox"
                  checked={param.required}
                  onChange={(e) => onUpdateParameter(param.key, { required: e.target.checked })}
                />
                Required
              </label>
              <Button type="button" size="sm" variant="ghost" onClick={() => onRemoveParameter(param.key)} style={{ marginLeft: "auto" }}>
                <Icon name="x" /> Remove
              </Button>
            </div>
          </div>
        ))}
        <Button type="button" size="sm" variant="ghost" onClick={onAddParameter}>
          <Icon name="plus" /> Add parameter
        </Button>
      </div>

      <div className="mb-2">
        <p className="hint mb-1">Materials consumed at this step</p>
        {step.material_requirements.length === 0 && <p className="hint mb-1">No materials required at this step.</p>}
        {step.material_requirements.map((req) => (
          <div key={req.key} className="sig-block mb-2" style={{ background: "var(--surface-sunken, #f6f6f6)" }}>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <MaterialSpecVersionPicker
                value={req.material_spec_version_id}
                onChange={(id) => onUpdateMaterialRequirement(req.key, { material_spec_version_id: id })}
                businessIdOptions={materialSpecOptions}
                placeholder="Material"
              />
            </div>
            <div className="grid grid-cols-4 gap-3 mb-2">
              <Input
                placeholder="Target qty"
                value={req.target_value}
                onChange={(e) => onUpdateMaterialRequirement(req.key, { target_value: e.target.value })}
              />
              <Input
                placeholder="Min qty"
                value={req.min_value}
                onChange={(e) => onUpdateMaterialRequirement(req.key, { min_value: e.target.value })}
              />
              <Input
                placeholder="Max qty"
                value={req.max_value}
                onChange={(e) => onUpdateMaterialRequirement(req.key, { max_value: e.target.value })}
              />
              <Select
                value={req.uom ?? ""}
                onChange={(e) => onUpdateMaterialRequirement(req.key, { uom: e.target.value })}
              >
                <option value="">UOM</option>
                {uomOptions.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
                {req.uom && !uomOptions.includes(req.uom) && <option value={req.uom}>{req.uom}</option>}
              </Select>
            </div>
            <div className="flex flex-wrap items-center gap-3 mb-2">
              <label className="flex items-center gap-2 fs-2">
                <input
                  type="checkbox"
                  checked={req.substitution_allowed}
                  onChange={(e) => onUpdateMaterialRequirement(req.key, { substitution_allowed: e.target.checked })}
                />
                Substitution allowed
              </label>
              {req.substitution_allowed && (
                <MaterialSpecVersionPicker
                  value={req.alternative_material_spec_version_id}
                  onChange={(id) => onUpdateMaterialRequirement(req.key, { alternative_material_spec_version_id: id })}
                  businessIdOptions={materialSpecOptions}
                  placeholder="Alternative material"
                />
              )}
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Input
                placeholder="Consume mode (optional)"
                value={req.consume_mode}
                onChange={(e) => onUpdateMaterialRequirement(req.key, { consume_mode: e.target.value })}
                style={{ maxWidth: 220 }}
              />
              <label className="flex items-center gap-2 fs-2">
                <input
                  type="checkbox"
                  checked={req.genealogy_required}
                  onChange={(e) => onUpdateMaterialRequirement(req.key, { genealogy_required: e.target.checked })}
                />
                Genealogy required
              </label>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => onRemoveMaterialRequirement(req.key)}
                style={{ marginLeft: "auto" }}
              >
                <Icon name="x" /> Remove
              </Button>
            </div>
          </div>
        ))}
        <Button type="button" size="sm" variant="ghost" onClick={onAddMaterialRequirement}>
          <Icon name="plus" /> Add material requirement
        </Button>
      </div>

      <div className="mb-2">
        <p className="hint mb-1">Equipment required at this step</p>
        {step.equipment_requirements.length === 0 && <p className="hint mb-1">No equipment requirement declared.</p>}
        {step.equipment_requirements.map((req) => (
          <div key={req.key} className="sig-block mb-2" style={{ background: "var(--surface-sunken, #f6f6f6)" }}>
            <div className="flex flex-wrap items-center gap-3 mb-2">
              {/* Known-limitations fix (docs/testing/demo-gujarati/07 §7.9 item 4): equipment_class_id is
               * the controlled reference batch-step-start enforcement matches against; equipment_class
               * stays a free-text label (kept for legacy rows / anything not yet in the class list). */}
              <Select
                value={req.equipment_class_id}
                onChange={(e) => {
                  const id = e.target.value;
                  const klass = equipmentClassOptions.find((k) => k.id === id);
                  onUpdateEquipmentRequirement(req.key, {
                    equipment_class_id: id,
                    ...(klass && !req.equipment_class ? { equipment_class: klass.class_code } : {}),
                  });
                }}
                style={{ minWidth: 200 }}
              >
                <option value="">No controlled class…</option>
                {equipmentClassOptions.map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.class_code} - {k.name}
                  </option>
                ))}
              </Select>
              <Input
                placeholder="Equipment class label (e.g. FILLING_LINE)"
                value={req.equipment_class}
                onChange={(e) => onUpdateEquipmentRequirement(req.key, { equipment_class: e.target.value })}
                style={{ minWidth: 220 }}
                required
              />
              <label className="flex items-center gap-2 fs-2">
                <input
                  type="checkbox"
                  checked={req.exact_equipment_optional}
                  onChange={(e) => onUpdateEquipmentRequirement(req.key, { exact_equipment_optional: e.target.checked })}
                />
                Any unit of this class is fine
              </label>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 fs-2">
                <input
                  type="checkbox"
                  checked={req.require_current_calibration}
                  onChange={(e) => onUpdateEquipmentRequirement(req.key, { require_current_calibration: e.target.checked })}
                />
                Requires current calibration
              </label>
              <label className="flex items-center gap-2 fs-2">
                <input
                  type="checkbox"
                  checked={req.require_current_qualification}
                  onChange={(e) => onUpdateEquipmentRequirement(req.key, { require_current_qualification: e.target.checked })}
                />
                Requires current qualification
              </label>
              <label className="flex items-center gap-2 fs-2">
                <input
                  type="checkbox"
                  checked={req.require_current_cleaning}
                  onChange={(e) => onUpdateEquipmentRequirement(req.key, { require_current_cleaning: e.target.checked })}
                />
                Requires current cleaning
              </label>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => onRemoveEquipmentRequirement(req.key)}
                style={{ marginLeft: "auto" }}
              >
                <Icon name="x" /> Remove
              </Button>
            </div>
          </div>
        ))}
        <Button type="button" size="sm" variant="ghost" onClick={onAddEquipmentRequirement}>
          <Icon name="plus" /> Add equipment requirement
        </Button>
      </div>

      <div className="mb-2">
        <p className="hint mb-1">Evidence required at this step</p>
        {step.evidence_requirements.length === 0 && <p className="hint mb-1">No evidence requirement declared.</p>}
        {step.evidence_requirements.map((req) => (
          <div key={req.key} className="sig-block mb-2" style={{ background: "var(--surface-sunken, #f6f6f6)" }}>
            <div className="grid grid-cols-4 gap-3 mb-2">
              <Input
                placeholder="Evidence type (e.g. photo, scan, printout)"
                value={req.evidence_type}
                onChange={(e) => onUpdateEvidenceRequirement(req.key, { evidence_type: e.target.value })}
                required
              />
              <Input
                type="number"
                min={1}
                placeholder="Required count"
                value={req.required_count}
                onChange={(e) => onUpdateEvidenceRequirement(req.key, { required_count: e.target.value })}
              />
              <Input
                placeholder="Allowed MIME types (optional)"
                value={req.allowed_mime_types}
                onChange={(e) => onUpdateEvidenceRequirement(req.key, { allowed_mime_types: e.target.value })}
              />
              <Input
                placeholder="Retention class (optional)"
                value={req.retention_class}
                onChange={(e) => onUpdateEvidenceRequirement(req.key, { retention_class: e.target.value })}
              />
            </div>
            <div className="flex justify-end">
              <Button type="button" size="sm" variant="ghost" onClick={() => onRemoveEvidenceRequirement(req.key)}>
                <Icon name="x" /> Remove
              </Button>
            </div>
          </div>
        ))}
        <Button type="button" size="sm" variant="ghost" onClick={onAddEvidenceRequirement}>
          <Icon name="plus" /> Add evidence requirement
        </Button>
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

