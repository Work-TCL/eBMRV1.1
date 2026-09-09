/**
 * The DDCP product-family catalogue: for each of Documents 54–57, the profile-creation fields and the
 * execution/result operations available from Card 3, expressed as `DdcpField[]` so the page never shows
 * raw JSON. Field names match the backend commands in `services/gxp-api/app/modules/ddcp/*_commands.py`
 * exactly — this file only describes how to *present* those fields, it invents no new ones.
 *
 * `select` is used only where the backend actually enforces a closed vocabulary at the command layer
 * (grep-verified — see the module comment in `fields.ts` and the code review that produced this file);
 * everywhere the backend documents a vocabulary but leaves it open (`test_type`, `count_type`, …),
 * fields use `suggestions` (a datalist) instead of a hard `select`, so the UI never silently narrows
 * what the API accepts.
 */

import type { DdcpField, SelectOption } from "./fields";

// --- Shared vocabularies -------------------------------------------------------------------------

const CONSTITUENT_TYPE_OPTIONS: SelectOption[] = [
  { value: "DRUG", label: "Drug" },
  { value: "BIOLOGIC", label: "Biologic" },
  { value: "DEVICE", label: "Device" },
  { value: "PACKAGING", label: "Packaging" },
  { value: "LABEL", label: "Label" },
];

const REQUIRED_STATE_OPTIONS: SelectOption[] = [
  { value: "RELEASED", label: "Released" },
  { value: "READY_TO_USE", label: "Ready to use" },
  { value: "STERILIZED", label: "Sterilized" },
  { value: "DEPYROGENATED", label: "Depyrogenated" },
];

const TEST_RESULT_STATE_OPTIONS: SelectOption[] = [
  { value: "PENDING", label: "Pending" },
  { value: "PASS", label: "Pass" },
  { value: "FAIL", label: "Fail" },
  { value: "OOS", label: "Out of specification (OOS)" },
];

const TEST_RESULT_STATE_SUGGESTIONS = TEST_RESULT_STATE_OPTIONS;

const DEVICE_TEST_TYPE_SUGGESTIONS: SelectOption[] = [
  "CCI", "LEAK", "SEAL", "BREAK_LOOSE", "GLIDE_FORCE", "DOSE_DELIVERY", "SHIELD_REMOVAL",
  "ACTIVATION_FORCE", "DOSE_ACCURACY", "DOSE_COUNTER", "AUDIBLE_INDICATOR", "NEEDLE_ACTIVATION",
  "DOSE_MECHANISM_CALIBRATION", "FINAL_COMBINATION_TEST", "DELIVERED_DOSE", "AERODYNAMIC_PARTICLE_SIZE",
  "SPRAY_PATTERN", "PRIMING", "DRUG_CONTENT_ASSAY", "COATING_INTEGRITY", "RELEASE_ELUTION", "DIMENSIONAL_FUNCTION",
].map((v) => ({ value: v, label: v }));

const COUNT_TYPE_SUGGESTIONS: SelectOption[] = [
  "FILLED", "REJECTED_VISUAL", "REJECTED_IPC", "SAMPLED", "LINE_LOSS", "PACKED", "ASSEMBLED", "COATED",
].map((v) => ({ value: v, label: v }));

const COUNT_SOURCE_SUGGESTIONS: SelectOption[] = ["MACHINE", "MANUAL", "RECONCILIATION"].map((v) => ({ value: v, label: v }));

const ASSEMBLY_STEP_OPTIONS: SelectOption[] = [
  "NEEDLE_INSTALL", "SHIELD", "TIP_CAP", "SAFETY_DEVICE", "PLUNGER",
  "HOUSING_ASSEMBLY", "SPRING_DRIVE_INSTALL", "NEEDLE_SYSTEM_ASSEMBLY", "DOSE_MECHANISM_INSTALL",
  "CAP_ASSEMBLY", "ELECTRONICS_INSTALL", "VALVE_PLACEMENT", "CRIMP", "ACTUATOR_ASSEMBLY",
  "SURFACE_PREPARATION", "COATING_APPLICATION", "DRYING_CURING",
].map((v) => ({ value: v, label: v }));

const constituentRequirementsField: DdcpField = {
  name: "constituent_requirements",
  label: "Constituent requirements",
  type: "repeat",
  required: true,
  itemLabel: "Requirement",
  hint: "What this product is built from, and what state each part must be in before a batch can use it. At least one is required before the profile can be released.",
  subFields: [
    { name: "constituent_type", label: "Constituent type", type: "select", required: true, options: CONSTITUENT_TYPE_OPTIONS },
    { name: "component_role", label: "Component role", type: "text", required: true, placeholder: "e.g. bulk_drug, needle, primary_label" },
    { name: "required_state", label: "Required state", type: "select", options: REQUIRED_STATE_OPTIONS, default: "RELEASED" },
  ],
};

// Both kv fields below are genuinely free-form JSONB at the backend — no schema, nothing validated
// against a fixed key list (see each command's own docstring, e.g. commands.py's module comment on
// DdcpProfileVersion). The one exception each family has is already pulled out into its own typed
// field above (subtype, fill_route, environment_profile_id, coating_route_id, …) and merged into this
// object server-side, so there's no hidden key the operator needs to know to type by hand here — the
// example in the hint is illustrative, not a catalogue to memorise.
const FREE_FORM_NOTE = " Free-form the backend stores whatever you enter here as-is; nothing is validated against a fixed list.";

function architectureField(hint: string): DdcpField {
  return { name: "constituent_architecture", label: "Product architecture settings", type: "kv", hint: hint + FREE_FORM_NOTE };
}

function controlsField(extraHint?: string): DdcpField {
  return {
    name: "required_controls",
    label: "Required controls",
    type: "kv",
    hint:
      'Controls this product needs before release, e.g. "visualInspectionProfile" → "VI-001".' +
      FREE_FORM_NOTE +
      (extraHint ? ` ${extraHint}` : ""),
  };
}

const attributesField: DdcpField = {
  name: "attributes",
  label: "Additional attributes",
  type: "kv",
  hint: "Any extra properties to record with this handoff (optional)." + FREE_FORM_NOTE,
};

// --- Op / family shapes ---------------------------------------------------------------------------

export interface DdcpOp {
  /** Path segment(s) after the family prefix — may contain `{param}` placeholders filled from a
   * same-named field instead of being sent in the body. */
  path: string;
  label: string;
  about?: string;
  /** Presentation grouping only (Card 3's "what are you recording?" step) — buckets this family's ops
   * so the picker reads as a handful of labelled clusters instead of one long flat list. Purely a UI
   * arrangement, not a backend concept: it invents no sequencing or dependency the API doesn't already
   * enforce on its own (e.g. a handoff must exist before it can be decided regardless of how the picker
   * groups the two). Ops keep the group's first-appearance order from this array. */
  group: string;
  fields: DdcpField[];
  /** When submitting this op succeeds, the new record's id is offered to every later field in this
   * family whose own `recordKind` matches this string (see fields.ts's `DdcpField.recordKind`) — e.g.
   * "Record a constituent handoff" produces `"pfs_handoff"`, and "Accept or reject a constituent
   * handoff"'s Handoff ID field consumes it, so the id shows up there as a dropdown instead of asking
   * the operator to copy it from the previous op's result banner. Session-local only (ExecutionCard
   * state) — there is no backend list endpoint for these sub-resources to source it from instead. */
  producesRecordKind?: string;
}

export interface DdcpFamily {
  key: string;
  label: string;
  prefix: string;
  subtypeHint: string;
  hasProfileGet: boolean;
  hasGenealogy: boolean;
  hasReviewSummary: boolean;
  /** Readiness GET accepts these optional query fields beyond the always-required profile_version_id
   * (only Document 54's endpoint does — see `services/gxp-api/app/modules/ddcp/router.py`). */
  readinessExtraFields: DdcpField[];
  profileFields: DdcpField[];
  ops: DdcpOp[];
}

// --- Document 54 — Prefilled syringe / injectable ---------------------------------------------------

const pfs: DdcpFamily = {
  key: "pfs",
  label: "Prefilled syringe / injectable",
  prefix: "/ddcp/v1/prefilled-syringe",
  subtypeHint: "What kind of injectable presentation this is.",
  hasProfileGet: true,
  hasGenealogy: true,
  hasReviewSummary: true,
  readinessExtraFields: [
 { name: "line_id", label: "Equipment area / line", type: "areaSelect", hint: "Optional checks line clearance and EM status too." },
 { name: "filler_equipment_id", label: "Filler equipment", type: "equipmentSelect", hint: "Optional checks this equipment's eligibility too." },
  ],
  profileFields: [
 { name: "profile_code", label: "Profile code", type: "text", required: true, placeholder: "e.g. PFS-DEMO-001", hint: "A unique code for this product combined with the site and version to identify it." },
 { name: "product_version_id", label: "Product (Product Master)", type: "productVersionSelect", required: true, hint: "The RELEASED Product Master version this profile is the combination-product spec for (SG-175) — must have manufacturing profile \"injectable_ddcp\"." },
    { name: "subtype", label: "Subtype", type: "select", options: [
      { value: "PREFILLED_SYRINGE", label: "Prefilled syringe" },
      { value: "CARTRIDGE", label: "Cartridge" },
      { value: "VIAL_DEVICE_COPACK", label: "Vial / device co-pack" },
      { value: "OTHER_INJECTABLE", label: "Other injectable" },
    ] },
    { name: "dosage_form", label: "Dosage form", type: "text" },
    { name: "presentation", label: "Presentation", type: "text" },
    architectureField('Sterile-process and fill-control settings, e.g. "sterileProcess" → "true".'),
    controlsField(
      'One recognized key here: a "serialization" row set to "true" flags unit serialization as ' +
 'applicable for reporting (PFS-FR-019) this never blocks release. The backend actually reads ' +
      'it nested ({"serialization": {"required": true}}), which this flat editor can\'t produce; a ' +
      "top-level true is stored as entered but won't be picked up by that reporting check."
    ),
    constituentRequirementsField,
  ],
  ops: [
    {
      path: "constituent-handoffs",
      label: "Record a constituent handoff",
      about: "Hand off a drug, device, packaging or label constituent into this batch (starts as PENDING until decided).",
      group: "Constituent handoffs",
      producesRecordKind: "pfs_handoff",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "from_constituent", label: "Constituent type", type: "select", required: true, options: CONSTITUENT_TYPE_OPTIONS },
        { name: "to_constituent", label: "Component role", type: "text", required: true, placeholder: "e.g. bulk_drug", hint: "Should match a component_role declared in the product's profile requirements." },
        {
          name: "source_batch_reference", label: "Source", type: "ref", required: true,
          refKeys: [{ value: "batch_id", label: "Upstream batch ID" }, { value: "lot_id", label: "Material lot ID" }],
          refValuePlaceholder: "Paste the batch or lot ID",
        },
        attributesField,
      ],
    },
    {
      path: "constituent-handoffs/{handoff_id}/decide",
      label: "Accept or reject a constituent handoff",
 about: "Decide a pending handoff accepting checks the source is released and (optionally) meets the profile's requirement for this component.",
      group: "Constituent handoffs",
      fields: [
 { name: "handoff_id", label: "Handoff ID", type: "recordSelect", recordKind: "pfs_handoff", pickerKind: "handoff", required: true, hint: "Picked from handoffs recorded earlier this session or enter one manually." },
 { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1", hint: "The handoff's current version auto-filled when picked above from a record this session already knows about; prevents overwriting someone else's change." },
        { name: "decision", label: "Decision", type: "select", required: true, options: [{ value: "ACCEPTED", label: "Accept" }, { value: "REJECTED", label: "Reject" }] },
        { name: "rejection_reason", label: "Rejection reason", type: "text", hint: "Required when rejecting." },
        { name: "profile_version_id", label: "Profile (optional check)", type: "profileSelect", hint: "If supplied, also checks preparation status and declared attributes against this profile's requirement." },
        { name: "sterilization_use_id", label: "Sterilization/depyrogenation reference", type: "sterilizationSelect", hint: "Required when the profile requires a sterilized/depyrogenated/ready-to-use component." },
      ],
    },
    {
      path: "fill-operations",
      label: "Start a fill operation",
 about: "Begin filling the batch's constituent handoffs must already be accepted and ready.",
      group: "Fill operations",
      producesRecordKind: "pfs_fill_operation",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "profile_version_id", label: "Released profile", type: "profileSelect", required: true, hint: "The RELEASED profile version this fill run follows." },
        { name: "line_id", label: "Equipment area / line", type: "areaSelect", required: true },
        { name: "filler_equipment_id", label: "Filler equipment", type: "equipmentSelect", required: true },
        { name: "fill_program_id", label: "Fill program ID", type: "text", required: true },
        { name: "fill_program_version", label: "Fill program version", type: "text", required: true },
        { name: "product_contact_path", label: "Product contact path", type: "kv", hint: 'How the product reaches the fill point, e.g. "path" → "standard".' + FREE_FORM_NOTE },
        { name: "target_fill", label: "Target fill quantity", type: "decimal", required: true, placeholder: "1.000000" },
        { name: "target_fill_uom", label: "Fill unit of measure", type: "text", required: true, placeholder: "mL" },
        { name: "cycle_group", label: "Cycle group", type: "text" },
      ],
    },
    {
      path: "fill-operations/{fill_operation_id}/ipc-results",
      label: "Record a fill in-process check (IPC)",
      about: "Record an in-process fill-weight (or similar) check against a released acceptance rule. An out-of-spec result holds the fill run.",
      group: "Fill operations",
      fields: [
 { name: "fill_operation_id", label: "Fill operation ID", type: "recordSelect", recordKind: "pfs_fill_operation", pickerKind: "fill operation", required: true, hint: "Picked from fill operations started earlier this session or enter one manually." },
 { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1", hint: "Auto-filled when picked above from a record this session already knows about re-check it if an earlier action on this same record failed, or you entered the ID manually." },
        { name: "sample_id", label: "Sample ID", type: "text", required: true },
        { name: "actual_value", label: "Measured value", type: "decimal", required: true },
        { name: "uom", label: "Unit of measure", type: "text", required: true },
        { name: "method", label: "Method", type: "text" },
        { name: "source", label: "Source", type: "text", suggestions: COUNT_SOURCE_SUGGESTIONS, default: "MANUAL" },
        { name: "acceptance_rule_id", label: "Acceptance rule", type: "ruleSelect", required: true, hint: "The released rule this check is evaluated against." },
      ],
    },
    {
      path: "fill-operations/{fill_operation_id}/interventions",
      label: "Record an aseptic intervention",
      about: "Link an aseptic intervention (already recorded in the Aseptic module) to this fill run's timeline.",
      group: "Fill operations",
      fields: [
 { name: "fill_operation_id", label: "Fill operation ID", type: "recordSelect", recordKind: "pfs_fill_operation", pickerKind: "fill operation", required: true, hint: "Picked from fill operations started earlier this session or enter one manually." },
 { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1", hint: "Auto-filled when picked above from a record this session already knows about re-check it if an earlier action on this same record failed, or you entered the ID manually." },
        { name: "intervention_type", label: "Intervention type", type: "text", required: true },
        { name: "started_at", label: "Started at", type: "datetime" },
        { name: "ended_at", label: "Ended at", type: "datetime" },
        { name: "impacted_unit_scope", label: "Impacted unit scope", type: "kv", hint: 'Which units this intervention may have affected, e.g. "unitRange" → "1001-1050".' + FREE_FORM_NOTE },
        { name: "source_aseptic_intervention_id", label: "Aseptic intervention reference", type: "asepticInterventionSelect", hint: "The intervention record in the Aseptic module, if any." },
      ],
    },
    {
      path: "fill-operations/{fill_operation_id}/complete",
      label: "Complete a fill operation",
 about: "Finish filling at least one FILLED count must already be recorded and no hold left open.",
      group: "Fill operations",
      fields: [
 { name: "fill_operation_id", label: "Fill operation ID", type: "recordSelect", recordKind: "pfs_fill_operation", pickerKind: "fill operation", required: true, hint: "Picked from fill operations started earlier this session or enter one manually." },
 { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1", hint: "Auto-filled when picked above from a record this session already knows about re-check it if an earlier action on this same record failed, or you entered the ID manually." },
        { name: "machine_count_end", label: "Machine count (end)", type: "number" },
        { name: "filter_use_id", label: "Sterile filter use reference", type: "text" },
        { name: "reason", label: "Reason / note", type: "text" },
      ],
    },
    {
      path: "production-counts",
      label: "Record a production count",
      about: "Append a unit count (filled, rejected, sampled, …) to this batch's ledger.",
      group: "Counts & disposition",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "count_type", label: "Count type", type: "text", required: true, suggestions: COUNT_TYPE_SUGGESTIONS },
        { name: "source", label: "Source", type: "text", required: true, suggestions: COUNT_SOURCE_SUGGESTIONS, default: "MANUAL" },
        { name: "quantity", label: "Quantity", type: "number", required: true },
        { name: "uom", label: "Unit of measure", type: "text", default: "EA" },
        { name: "device_reference", label: "Device reference", type: "ref", refKeys: [{ value: "device_id", label: "Device/line ID" }] },
        { name: "reason_code", label: "Reason code", type: "text" },
        { name: "occurred_at", label: "Occurred at", type: "datetime" },
 { name: "source_event_id", label: "Source event ID", type: "text", hint: "From a machine/edge system resubmitting the same ID never double-counts." },
      ],
    },
    {
      path: "device-assembly",
      label: "Record a device assembly step",
      about: "Record one assembly step for a device unit.",
      group: "Assembly",
      producesRecordKind: "pfs_assembly_record",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "assembly_step", label: "Assembly step", type: "select", required: true, options: ASSEMBLY_STEP_OPTIONS },
        { name: "component_lot_reference", label: "Component lot", type: "ref", required: true, refKeys: [{ value: "lot_id", label: "Component lot ID" }] },
        { name: "unit_identifier", label: "Unit identifier", type: "text" },
        { name: "equipment_id", label: "Equipment", type: "equipmentSelect" },
        { name: "process_parameters", label: "Process parameters", type: "kv", hint: 'Equipment/process settings for this step, e.g. "torque" → "2.5".' + FREE_FORM_NOTE },
        { name: "result", label: "Result", type: "select", required: true, options: [{ value: "PASS", label: "Pass" }, { value: "FAIL", label: "Fail" }, { value: "REWORK", label: "Rework" }], default: "PASS" },
 { name: "rework_procedure_reference", label: "Rework procedure reference", type: "ref", refKeys: [{ value: "procedure_id", label: "Released procedure ID" }], hint: "Required when result is Rework (PFS-FR-027) rework is disallowed by default without it." },
        { name: "occurred_at", label: "Occurred at", type: "datetime" },
      ],
    },
    {
      path: "device-assembly/{record_id}/verify",
      label: "Independently verify an assembly step",
 about: "A second person confirms an assembly step the person who performed it cannot also verify it (IND-001).",
      group: "Assembly",
      fields: [
 { name: "record_id", label: "Assembly record ID", type: "recordSelect", recordKind: "pfs_assembly_record", pickerKind: "assembly record", required: true, hint: "Picked from assembly steps recorded earlier this session or enter one manually. Remember IND-001: pick a step someone else performed." },
 { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1", hint: "Auto-filled when picked above from a record this session already knows about re-check it if an earlier action on this same record failed, or you entered the ID manually." },
      ],
    },
    {
      path: "functional-tests",
      label: "Link a device functional test",
      about: "Link a QC result (owned by the QC module) to this batch as a device functional test.",
      group: "Tests & samples",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "test_type", label: "Test type", type: "text", required: true, suggestions: DEVICE_TEST_TYPE_SUGGESTIONS },
        { name: "qc_record_reference", label: "QC result", type: "ref", required: true, refKeys: [{ value: "record_id", label: "QC result ID" }] },
        { name: "result_state", label: "Result", type: "select", required: true, options: TEST_RESULT_STATE_OPTIONS, default: "PENDING" },
        { name: "sample_plan_reference", label: "Sample plan reference", type: "ref", refKeys: [{ value: "plan_id", label: "Sample plan ID" }] },
        { name: "method_reference", label: "Method reference", type: "ref", refKeys: [{ value: "method_id", label: "Method ID" }] },
        { name: "linked_at", label: "Linked at", type: "datetime" },
      ],
    },
    {
      path: "stability-retain-samples",
      label: "Record a stability / retain sample reference",
      group: "Tests & samples",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "plan_reference", label: "Stability/retain plan", type: "ref", required: true, refKeys: [{ value: "plan_id", label: "Plan reference ID" }] },
        { name: "quantity", label: "Quantity", type: "number", required: true },
        { name: "occurred_at", label: "Occurred at", type: "datetime" },
      ],
    },
  ],
};

// --- Document 55 — Autoinjector ---------------------------------------------------------------------

const autoinjector: DdcpFamily = {
  key: "auto",
  label: "Autoinjector",
  prefix: "/ddcp/v1/autoinjector",
  subtypeHint: "What kind of injector this is.",
  hasProfileGet: false,
  hasGenealogy: false,
  hasReviewSummary: false,
  readinessExtraFields: [],
  profileFields: [
    { name: "profile_code", label: "Profile code", type: "text", required: true, placeholder: "e.g. AUTO-DEMO-001" },
 { name: "product_version_id", label: "Product (Product Master)", type: "productVersionSelect", required: true, hint: "The RELEASED Product Master version this profile is the combination-product spec for (SG-175). No manufacturing-profile value names \"autoinjector\" specifically, so only existence/released/site are checked, not a family match." },
    { name: "injector_type", label: "Injector type", type: "select", required: true, options: [
      { value: "AUTOINJECTOR", label: "Autoinjector" },
 { value: "PEN_SINGLE_USE", label: "Pen single use" },
 { value: "PEN_REUSABLE", label: "Pen reusable" },
      { value: "CARTRIDGE_SYSTEM", label: "Cartridge system" },
    ] },
    { name: "device_bom_version_id", label: "Device BOM version", type: "text" },
    { name: "unit_serialization", label: "Unit serialization required", type: "bool", default: "false" },
    architectureField("Additional device architecture settings, if any."),
    controlsField(),
    constituentRequirementsField,
  ],
  ops: [
    {
      path: "assembly-operations",
      label: "Start an assembly operation",
 about: "Begin injector assembly the batch's constituent handoffs must already be accepted.",
      group: "Assembly",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "profile_version_id", label: "Released profile", type: "profileSelect", required: true },
        { name: "line_id", label: "Equipment area / line", type: "areaSelect" },
        { name: "equipment_id", label: "Equipment", type: "equipmentSelect" },
        { name: "program_id", label: "Program ID", type: "text" },
        { name: "program_version", label: "Program version", type: "text" },
      ],
    },
    {
      path: "drug-container-bindings",
      label: "Bind a drug container to an injector unit",
      about: "Each drug container can only be bound to one injector unit.",
      group: "Assembly",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        {
          name: "drug_container_reference", label: "Drug container", type: "ref", required: true,
          refKeys: [{ value: "container_id", label: "Container ID" }, { value: "lot_id", label: "Material lot ID" }],
        },
        { name: "injector_unit_serial", label: "Injector unit serial", type: "text", required: true },
      ],
    },
    {
      path: "functional-tests",
      label: "Record an injector functional test",
      group: "Tests & samples",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "test_type", label: "Test type", type: "text", required: true, suggestions: DEVICE_TEST_TYPE_SUGGESTIONS },
        { name: "qc_record_reference", label: "QC result", type: "ref", required: true, refKeys: [{ value: "record_id", label: "QC result ID" }] },
        { name: "sample_plan_reference", label: "Sample plan reference", type: "ref", refKeys: [{ value: "plan_id", label: "Sample plan ID" }] },
        { name: "method_reference", label: "Method reference", type: "ref", refKeys: [{ value: "method_id", label: "Method ID" }] },
        { name: "result_state", label: "Result", type: "text", suggestions: TEST_RESULT_STATE_SUGGESTIONS, default: "PENDING" },
      ],
    },
    {
      path: "dose-delivery-results",
      label: "Evaluate a dose delivery result",
      about: "Evaluated against a released acceptance rule (no hard-coded tolerance).",
      group: "Tests & samples",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "sample_id", label: "Sample ID", type: "text", required: true },
        { name: "actual_value", label: "Measured value", type: "decimal", required: true },
        { name: "uom", label: "Unit of measure", type: "text", required: true },
        { name: "acceptance_rule_id", label: "Acceptance rule", type: "ruleSelect", required: true },
        { name: "qc_record_reference", label: "QC result reference", type: "ref", refKeys: [{ value: "record_id", label: "QC result ID" }] },
      ],
    },
    {
      path: "unit-dispositions",
      label: "Record a unit disposition",
      group: "Counts & disposition",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "unit_identifier", label: "Unit identifier", type: "text", required: true },
        { name: "result", label: "Result", type: "select", required: true, options: [{ value: "PASS", label: "Pass" }, { value: "REJECT", label: "Reject" }, { value: "REWORK", label: "Rework" }] },
        { name: "reason", label: "Reason", type: "text", hint: "Required for Reject or Rework." },
        { name: "ncr_reference", label: "NCR reference", type: "ref", refKeys: [{ value: "ncr_id", label: "NCR ID" }] },
 { name: "rework_procedure_reference", label: "Rework procedure reference", type: "ref", refKeys: [{ value: "procedure_id", label: "Released procedure ID" }], hint: "Required for Rework (INJ-FR-022) disallowed by default without it." },
      ],
    },
    {
      path: "reusable-device-pairings",
      label: "Record a reusable device pairing",
      about: "Records compatibility between a reusable injector and a cartridge lot (the pen itself isn't consumed by the batch).",
      group: "Assembly",
      fields: [
        { name: "reusable_device_reference", label: "Reusable device", type: "ref", required: true, refKeys: [{ value: "device_id", label: "Device ID" }, { value: "serial", label: "Serial number" }] },
        { name: "cartridge_lot_reference", label: "Cartridge lot", type: "ref", required: true, refKeys: [{ value: "lot_id", label: "Cartridge lot ID" }] },
        { name: "compatibility_status", label: "Compatibility", type: "select", options: [
          { value: "COMPATIBLE", label: "Compatible" }, { value: "INCOMPATIBLE", label: "Incompatible" }, { value: "PENDING_REVIEW", label: "Pending review" },
        ], default: "PENDING_REVIEW" },
        { name: "rationale", label: "Rationale", type: "text" },
 { name: "batch_id", label: "Batch", type: "batchSelect", required: true, hint: "Required this pass a batch-independent pairing flow isn't implemented yet." },
      ],
    },
  ],
};

// --- Document 56 — Inhalation (MDI/DPI) ---------------------------------------------------------------

const inhalation: DdcpFamily = {
  key: "inh",
 label: "Inhalation MDI / DPI",
  prefix: "/ddcp/v1/inhalation",
  subtypeHint: "MDI (metered-dose) or DPI (dry-powder).",
  hasProfileGet: false,
  hasGenealogy: true,
  hasReviewSummary: false,
  readinessExtraFields: [],
  profileFields: [
    { name: "profile_code", label: "Profile code", type: "text", required: true, placeholder: "e.g. INH-DEMO-001" },
 { name: "product_version_id", label: "Product (Product Master)", type: "productVersionSelect", required: true, hint: "The RELEASED Product Master version this profile is the combination-product spec for (SG-175) — must have manufacturing profile \"inhalation_ddcp\"." },
 { name: "subtype", label: "Subtype", type: "select", required: true, options: [{ value: "MDI", label: "MDI metered dose" }, { value: "DPI", label: "DPI dry powder" }] },
    { name: "fill_route", label: "Fill route", type: "text", hint: "Must match what fill runs declare when they start." },
    { name: "environment_profile_id", label: "Environment profile", type: "text", hint: "If set, fill runs must report a ready environment status." },
    architectureField("Additional formulation/device architecture settings, if any."),
    controlsField(),
    constituentRequirementsField,
  ],
  ops: [
    {
      path: "fill-runs",
      label: "Start an inhaler fill run",
      about: "Fill route must match the profile's declared route; a blend/fill hold-time rule can also be checked.",
      group: "Fill operations",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "profile_version_id", label: "Released profile", type: "profileSelect", required: true },
        { name: "fill_route", label: "Fill route", type: "text", required: true },
        { name: "line_id", label: "Equipment area / line", type: "areaSelect" },
        { name: "equipment_id", label: "Equipment", type: "equipmentSelect" },
        { name: "program_id", label: "Program ID", type: "text" },
        { name: "program_version", label: "Program version", type: "text" },
        {
          name: "environment_status", label: "Environment ready", type: "boolKv", kvKey: "ready",
 hint: "Only checked when the profile declares an environment profile a No here blocks with ENVIRONMENT_NOT_READY.",
        },
        { name: "blend_hold_limit_rule_id", label: "Blend/fill hold-time rule", type: "text" },
      ],
    },
    {
      path: "closure-results",
      label: "Record a crimp / closure result",
      group: "Fill operations",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "unit_or_sample_id", label: "Unit / sample ID", type: "text", required: true },
        { name: "measured_value", label: "Measured value", type: "decimal", required: true },
        { name: "uom", label: "Unit of measure", type: "text", required: true },
        { name: "acceptance_rule_id", label: "Acceptance rule", type: "ruleSelect", required: true },
        { name: "test_type", label: "Test type", type: "text", suggestions: DEVICE_TEST_TYPE_SUGGESTIONS, default: "SEAL" },
      ],
    },
    {
      path: "dose-tests",
      label: "Record an inhaler dose test",
      group: "Tests & samples",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "test_type", label: "Test type", type: "text", required: true, suggestions: DEVICE_TEST_TYPE_SUGGESTIONS, placeholder: "DELIVERED_DOSE, AERODYNAMIC_PARTICLE_SIZE, SPRAY_PATTERN, PRIMING, …" },
        { name: "qc_record_reference", label: "QC result", type: "ref", required: true, refKeys: [{ value: "record_id", label: "QC result ID" }] },
        { name: "method_reference", label: "Method reference", type: "ref", refKeys: [{ value: "method_id", label: "Method ID" }] },
        { name: "result_state", label: "Result", type: "text", suggestions: TEST_RESULT_STATE_SUGGESTIONS, default: "PENDING" },
      ],
    },
    {
      path: "dose-counter-tests",
      label: "Record a dose counter test",
      group: "Tests & samples",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "unit_or_sample_id", label: "Unit / sample ID", type: "text", required: true },
        { name: "program_version", label: "Program version", type: "text" },
        { name: "result_state", label: "Result", type: "text", suggestions: TEST_RESULT_STATE_SUGGESTIONS, default: "PENDING" },
      ],
    },
    {
      path: "dose-unit-bindings",
      label: "Bind a dose unit to a device",
      about: "Each dose unit (blister/capsule/reservoir) can only be bound to one device.",
      group: "Assembly",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        {
          name: "dose_unit_reference", label: "Dose unit", type: "ref", required: true,
          refKeys: [{ value: "blister_id", label: "Blister ID" }, { value: "capsule_id", label: "Capsule ID" }, { value: "reservoir_lot_id", label: "Reservoir lot ID" }],
        },
        { name: "device_reference", label: "Device", type: "ref", required: true, refKeys: [{ value: "device_id", label: "Device ID" }] },
      ],
    },
  ],
};

// --- Document 57 — Coated / combination device ------------------------------------------------------

const coatedDevice: DdcpFamily = {
  key: "coat",
  label: "Coated / combination device",
  prefix: "/ddcp/v1/coated-device",
  subtypeHint: "e.g. drug-eluting stent.",
  hasProfileGet: false,
  hasGenealogy: false,
  hasReviewSummary: false,
  readinessExtraFields: [],
  profileFields: [
    { name: "profile_code", label: "Profile code", type: "text", required: true, placeholder: "e.g. COAT-DEMO-001" },
 { name: "product_version_id", label: "Product (Product Master)", type: "productVersionSelect", required: true, hint: "The RELEASED Product Master version this profile is the combination-product spec for (SG-175). No manufacturing-profile value names \"coated device\" specifically, so only existence/released/site are checked, not a family match." },
    { name: "coating_route_id", label: "Coating route", type: "text" },
    { name: "sterilization_route_id", label: "Sterilization route", type: "text" },
    { name: "environment_profile_id", label: "Environment profile", type: "text", hint: "If set, coating runs must report a ready environment status." },
    architectureField("Additional coating/device architecture settings, if any."),
    controlsField(),
    constituentRequirementsField,
  ],
  ops: [
    {
      path: "coating-runs",
      label: "Start a coating run",
      about: "An initial drug-solution quantity, if given, is recorded as ISSUED on the mass-balance ledger.",
      group: "Coating",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "profile_version_id", label: "Released profile", type: "profileSelect", required: true },
        { name: "line_id", label: "Equipment area / line", type: "areaSelect" },
        { name: "equipment_id", label: "Equipment", type: "equipmentSelect" },
        { name: "program_id", label: "Program ID", type: "text" },
        { name: "program_version", label: "Program version", type: "text" },
        {
          name: "environment_status", label: "Environment ready", type: "boolKv", kvKey: "ready",
 hint: "Only checked when the profile declares an environment profile a No here blocks with COATING_ENVIRONMENT_NOT_READY.",
        },
        { name: "initial_drug_solution_quantity", label: "Initial drug solution quantity", type: "decimal" },
        { name: "initial_drug_solution_uom", label: "Initial drug solution unit", type: "text", placeholder: "g" },
      ],
    },
    {
      path: "drug-coating-usage",
      label: "Record drug / coating usage",
 about: "Mass-balance entry how much drug/coating material was issued, applied, sampled, wasted, …",
      group: "Coating",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "usage_type", label: "Usage type", type: "select", required: true, options: [
          "ISSUED", "APPLIED", "RESIDUAL", "SAMPLED", "REJECTED", "RECOVERED", "DISPOSED",
        ].map((v) => ({ value: v, label: v })) },
        { name: "quantity", label: "Quantity", type: "decimal", required: true },
        { name: "uom", label: "Unit of measure", type: "text", required: true },
        { name: "reason_code", label: "Reason code", type: "text" },
        { name: "occurred_at", label: "Occurred at", type: "datetime" },
      ],
    },
    {
      path: "device-coating-bindings",
      label: "Bind a device unit to a coating constituent",
      group: "Assembly",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "device_unit_reference", label: "Device unit", type: "ref", required: true, refKeys: [{ value: "unit_id", label: "Unit ID" }, { value: "serial", label: "Serial number" }] },
        { name: "coating_solution_reference", label: "Coating solution / lot", type: "ref", required: true, refKeys: [{ value: "lot_id", label: "Coating solution lot ID" }] },
      ],
    },
    {
      path: "drug-loading-results",
      label: "Record a drug loading result",
      about: 'Evaluated against a released acceptance rule; a failing result is recorded as OOS, not FAIL.',
      group: "Tests & samples",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "unit_or_sample_id", label: "Unit / sample ID", type: "text", required: true },
        { name: "measured_value", label: "Measured value", type: "decimal", required: true },
        { name: "uom", label: "Unit of measure", type: "text", required: true },
        { name: "acceptance_rule_id", label: "Acceptance rule", type: "ruleSelect", required: true },
        { name: "test_type", label: "Test type", type: "text", suggestions: DEVICE_TEST_TYPE_SUGGESTIONS, default: "COATING_INTEGRITY" },
      ],
    },
    {
      path: "post-sterilization-tests",
      label: "Record a post-sterilization test",
      group: "Tests & samples",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "sterilization_reference", label: "Sterilization cycle", type: "ref", required: true, refKeys: [{ value: "cycle_id", label: "Sterilization cycle ID" }] },
        { name: "test_type", label: "Test type", type: "text", required: true, suggestions: DEVICE_TEST_TYPE_SUGGESTIONS },
        { name: "qc_record_reference", label: "QC result reference", type: "ref", refKeys: [{ value: "record_id", label: "QC result ID" }] },
        { name: "result_state", label: "Result", type: "text", suggestions: TEST_RESULT_STATE_SUGGESTIONS, default: "PENDING" },
      ],
    },
    {
      path: "functional-tests",
      label: "Record a device functional test",
      group: "Tests & samples",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "test_type", label: "Test type", type: "text", required: true, suggestions: DEVICE_TEST_TYPE_SUGGESTIONS },
        { name: "qc_record_reference", label: "QC result", type: "ref", required: true, refKeys: [{ value: "record_id", label: "QC result ID" }] },
        { name: "method_reference", label: "Method reference", type: "ref", refKeys: [{ value: "method_id", label: "Method ID" }] },
        { name: "result_state", label: "Result", type: "text", suggestions: TEST_RESULT_STATE_SUGGESTIONS, default: "PENDING" },
      ],
    },
    {
      path: "unit-dispositions",
      label: "Record a unit disposition",
      about: "Recoating/stripping/reprocessing is disallowed by default (COAT-FR-025).",
      group: "Counts & disposition",
      fields: [
        { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
        { name: "unit_identifier", label: "Unit identifier", type: "text", required: true },
        { name: "result", label: "Result", type: "select", required: true, options: [{ value: "PASS", label: "Pass" }, { value: "REJECT", label: "Reject" }, { value: "REWORK", label: "Rework" }] },
        { name: "reason", label: "Reason", type: "text", hint: "Required for Reject or Rework." },
        { name: "drug_device_impact_assessment", label: "Drug/device impact assessment", type: "kv", hint: "Required for Rework, alongside a procedure reference." + FREE_FORM_NOTE },
        { name: "rework_procedure_reference", label: "Rework procedure reference", type: "ref", refKeys: [{ value: "procedure_id", label: "Released procedure ID" }], hint: "Required for Rework, alongside an impact assessment." },
      ],
    },
  ],
};

export const DDCP_FAMILIES: DdcpFamily[] = [pfs, autoinjector, inhalation, coatedDevice];
