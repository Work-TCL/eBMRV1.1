"use client";

import { useState } from "react";
import { api, holdsAnyRole } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { FormConsole, type FormOp } from "@/components/shared/FormConsole";
import { SignedJsonForm, type SignedJsonOp } from "@/components/shared/SignedJsonForm";

// commands_vsr.py IssueValidatedReleaseAuthorizationCommand.decision / ApproveValidationSummaryCommand.decision
const RELEASE_DECISIONS = ["APPROVED", "CONDITIONAL", "REJECTED"].map((v) => ({ value: v, label: v }));
// commands_vsr.py GenerateValidationSummaryReportCommand.recommendation
const VSR_RECOMMENDATIONS = ["RECOMMENDED", "RECOMMENDED_WITH_CONDITIONS", "NOT_RECOMMENDED"].map((v) => ({ value: v, label: v }));
// commands_pq.py CreatePqScenarioCommand.process_area / product_profile
const PQ_PROCESS_AREAS = [
  "material_flow", "qc_flow", "deviation_flow", "signature_flow", "edge_device_flow",
  "erp_lims_flow", "shift_handoff", "business_process", "exception_recovery",
].map((v) => ({ value: v, label: v }));
const PQ_PRODUCT_PROFILES = ["prefilled_syringe", "injector", "inhalation", "coated_device"].map((v) => ({ value: v, label: v }));

// ---- FormConsole operations (unsigned; structured fields mirror each command's Pydantic model in
// commands_pq.py / commands_migration.py / commands_vsr.py so a non-technical operator fills labelled
// rows instead of typing a raw JSON body). ----------------------------------------------------------

const PQ_OPS: FormOp[] = [
  {
    path: "pq/scenarios",
    label: "Create a PQ scenario",
    fields: [
      { name: "scenario_number", label: "Scenario number", required: true },
      { name: "process_area", label: "Process area", type: "select", required: true, options: PQ_PROCESS_AREAS },
      { name: "product_profile", label: "Product profile", type: "select", options: PQ_PRODUCT_PROFILES, hint: "Only when this scenario is profile-specific." },
      { name: "intended_workflow", label: "Intended workflow", type: "textarea", required: true },
      { name: "acceptance_criteria", label: "Acceptance criteria", type: "textarea", required: true },
      { name: "representative_roles", label: "Representative roles", type: "stringList", itemLabel: "Role" },
      {
        name: "steps", label: "Steps", type: "repeat", itemLabel: "Step",
        subFields: [{ name: "step", label: "Step", required: true }, { name: "expected_result", label: "Expected result" }],
      },
      {
        name: "prerequisites", label: "Prerequisites", type: "repeat", itemLabel: "Prerequisite",
        subFields: [{ name: "prerequisite", label: "Prerequisite", required: true }, { name: "met", label: "Met", type: "bool" }],
      },
      { name: "is_uat", label: "Is UAT", type: "bool" },
      { name: "vmp_equivalence_ref", label: "VMP equivalence reference", hint: "Required when Is UAT is yes." },
      { name: "is_template", label: "Is template", type: "bool" },
      { name: "retention_class", label: "Retention class" },
    ],
  },
  {
    path: "pq/scenarios/{scenario_id}/participants",
    label: "Add PQ participants / training",
    fields: [
      { name: "scenario_id", label: "Scenario ID", required: true },
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      {
        name: "participants", label: "Participants", type: "repeat", required: true, itemLabel: "Participant",
        subFields: [
          { name: "user_id", label: "User ID", required: true },
          { name: "role", label: "Role", required: true },
          { name: "trained", label: "Trained", type: "bool" },
        ],
      },
    ],
  },
  {
    path: "pq/executions",
    label: "Record a PQ execution",
    fields: [
      { name: "scenario_id", label: "Scenario ID", required: true },
      { name: "environment", label: "Environment", required: true },
      { name: "config_ref", label: "Config reference", required: true },
      { name: "participant_identities", label: "Participant identities", type: "stringList", required: true, itemLabel: "Participant" },
      { name: "dataset_ref", label: "Dataset reference" },
      { name: "result", label: "Result", type: "select", required: true, options: [{ value: "COMPLETED", label: "Completed" }, { value: "FAILED", label: "Failed" }, { value: "INTERRUPTED", label: "Interrupted" }] },
      { name: "prior_execution_id", label: "Prior execution ID", hint: "Set when this re-runs an earlier execution." },
      {
        name: "step_results", label: "Step results", type: "repeat", itemLabel: "Step result",
        subFields: [
          { name: "step", label: "Step", required: true },
          { name: "outcome", label: "Outcome", type: "select", options: [{ value: "PASS", label: "Pass" }, { value: "FAIL", label: "Fail" }] },
          { name: "notes", label: "Notes" },
        ],
      },
      {
        name: "observations", label: "Usability observations", type: "repeat", itemLabel: "Observation",
        subFields: [
          { name: "observation", label: "Observation", required: true },
          { name: "severity", label: "Severity" },
          { name: "impact", label: "Impact" },
          { name: "change_candidate", label: "Change candidate", type: "bool" },
        ],
      },
      {
        name: "deviations", label: "Deviations", type: "repeat", itemLabel: "Deviation",
        subFields: [
          { name: "ref", label: "Reference" },
          { name: "severity", label: "Severity" },
          { name: "critical", label: "Critical", type: "bool" },
          { name: "resolved", label: "Resolved", type: "bool" },
        ],
      },
      {
        name: "evidence_manifest", label: "Evidence", type: "repeat", itemLabel: "Evidence item",
        subFields: [{ name: "evidence_id", label: "Evidence object ID" }],
      },
    ],
  },
];

const MIGRATION_OPS: FormOp[] = [
  {
    path: "migrations/plans",
    label: "Create a migration plan",
    fields: [
      { name: "plan_number", label: "Plan number", required: true },
      { name: "source_system", label: "Source system", required: true },
      { name: "target_system", label: "Target system", default: "eBMR/eDHR platform" },
      { name: "scope", label: "Scope", type: "textarea", required: true },
      { name: "cutoff_at", label: "Cutoff at", type: "datetime", required: true },
      { name: "source_snapshot_ref", label: "Source snapshot reference", required: true },
      { name: "source_snapshot_hash", label: "Source snapshot hash", required: true },
      { name: "source_timezone", label: "Source timezone" },
      { name: "mapping_version", label: "Mapping version", required: true },
      { name: "transform_version", label: "Transform version", required: true },
      { name: "acceptance_criteria", label: "Acceptance criteria", type: "textarea", required: true },
      { name: "regulated_history_strategy", label: "Regulated history strategy", required: true },
      { name: "rollback_strategy", label: "Rollback strategy", required: true },
      { name: "legacy_access_strategy", label: "Legacy access strategy", required: true },
      { name: "retention_class", label: "Retention class" },
      {
        name: "mappings", label: "Field mappings", type: "repeat", required: true, itemLabel: "Mapping",
        subFields: [
          { name: "source_field", label: "Source field", required: true },
          { name: "target_field", label: "Target field", required: true },
          { name: "transform", label: "Transform" },
        ],
      },
      {
        name: "reconciliation_rules", label: "Reconciliation rules", type: "repeat", required: true, itemLabel: "Rule",
        hint: "No default tolerance ships with the platform — every migrated data class needs an explicit rule (MIGV-FR-009/020).",
        subFields: [
          { name: "data_class", label: "Data class", required: true },
          { name: "count_tolerance", label: "Count tolerance", type: "number" },
          { name: "control_total_tolerance", label: "Control total tolerance", type: "number" },
          { name: "critical_fields", label: "Critical fields", placeholder: "comma-separated" },
        ],
      },
      { name: "source_profile", label: "Source profile (optional)", type: "kv", hint: "Row counts, duplicates, orphans, invalid values — leave blank if not yet profiled." },
    ],
  },
  {
    path: "migrations/runs",
    label: "Record a migration run / dry run",
    fields: [
      { name: "plan_id", label: "Migration plan ID", required: true },
      { name: "run_type", label: "Run type", type: "select", required: true, options: [{ value: "DRY_RUN", label: "Dry run" }, { value: "CUTOVER", label: "Cutover" }] },
      { name: "source_hash", label: "Source hash", required: true, hint: "Must match the plan's frozen source snapshot hash unless this is a delta run." },
      { name: "scripts_config", label: "Scripts config", type: "kv", required: true },
      { name: "counts", label: "Counts", type: "kv", hint: "Optional. e.g. \"read\" → 1000, \"loaded\" → 998." },
      { name: "control_totals", label: "Control totals", type: "kv" },
      { name: "identity_map", label: "Identity map", type: "kv", hint: "Optional. legacy id → new id." },
      {
        name: "rejected_records", label: "Rejected records", type: "repeat", itemLabel: "Rejected record",
        subFields: [
          { name: "legacy_id", label: "Legacy ID", required: true },
          { name: "reason", label: "Reason", required: true },
          { name: "disposition", label: "Disposition" },
        ],
      },
      { name: "attachments", label: "Attachments summary", type: "kv", hint: "e.g. \"expected_count\", \"loaded_count\", \"hash_matches\"." },
      { name: "legacy_audit", label: "Legacy audit reference", type: "kv" },
      { name: "target_refs", label: "Target references", type: "kv" },
      {
        name: "errors", label: "Errors", type: "repeat", itemLabel: "Error",
        subFields: [{ name: "message", label: "Message", required: true }, { name: "code", label: "Code" }],
      },
      { name: "is_delta", label: "Delta run (cutover reconciliation on top of the baseline)", type: "bool" },
      { name: "sandbox", label: "Sandbox", type: "bool", default: "true" },
      { name: "status", label: "Status", type: "select", default: "COMPLETED", options: [{ value: "COMPLETED", label: "Completed" }, { value: "FAILED", label: "Failed" }, { value: "INTERRUPTED", label: "Interrupted" }] },
      { name: "prior_run_id", label: "Prior run ID" },
    ],
  },
  {
    path: "migrations/{run_id}/reconcile",
    label: "Reconcile a migration run",
    fields: [
      { name: "run_id", label: "Migration run ID", required: true },
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "count_comparison", label: "Count comparison", type: "kv", required: true, hint: "e.g. \"source\" → 1000, \"target\" → 998." },
      { name: "control_total_comparison", label: "Control total comparison", type: "kv" },
      { name: "critical_field_comparison", label: "Critical field comparison", type: "kv", hint: "e.g. \"method\" → SAMPLING, \"sample_size\" → 50." },
      { name: "attachment_comparison", label: "Attachment comparison", type: "kv" },
      { name: "reference_integrity", label: "Reference integrity", type: "kv" },
      {
        name: "deviations", label: "Deviations", type: "repeat", itemLabel: "Deviation",
        subFields: [
          { name: "ref", label: "Reference" },
          { name: "data_class", label: "Data class" },
          { name: "disposition", label: "Disposition" },
        ],
      },
    ],
  },
];

const SUMMARY_OPS: FormOp[] = [
  {
    path: "summary-reports",
    label: "Create a validation summary report",
    fields: [
      { name: "report_number", label: "Report number", required: true },
      { name: "release_ref", label: "Release reference", required: true },
      { name: "environment", label: "Environment", required: true },
      { name: "intended_use", label: "Intended use", type: "textarea", required: true },
      { name: "config_scope", label: "Config scope", type: "textarea", required: true },
      { name: "evidence_manifest_ref", label: "Evidence manifest reference", required: true },
      { name: "recommendation", label: "Recommendation", type: "select", required: true, options: VSR_RECOMMENDATIONS },
      { name: "customer", label: "Customer" },
      { name: "retention_class", label: "Retention class" },
      { name: "baselines", label: "Baselines", type: "kv" },
      { name: "execution_summary", label: "Execution summary", type: "kv" },
 { name: "traceability_status", label: "Traceability status", type: "kv", hint: "e.g. \"critical_gaps\", \"orphans\" as counts or notes." },
      {
        name: "deviations", label: "Deviations", type: "repeat", itemLabel: "Deviation",
        subFields: [
          { name: "ref", label: "Reference" },
          { name: "state", label: "State", type: "select", options: [{ value: "OPEN", label: "Open" }, { value: "CLOSED", label: "Closed" }, { value: "ACCEPTED", label: "Accepted" }] },
          { name: "critical", label: "Critical", type: "bool" },
          { name: "release_impact", label: "Release impact" },
        ],
      },
      { name: "security_summary", label: "Security summary", type: "kv", hint: "e.g. \"qualification\", \"critical_open\"." },
      { name: "performance_summary", label: "Performance summary", type: "kv" },
      { name: "dr_summary", label: "DR summary", type: "kv", hint: "e.g. \"restore_qualification\", \"achieved_rpo\", \"achieved_rto\", \"qualified\"." },
      { name: "migration_summary", label: "Migration summary", type: "kv" },
      { name: "part11_summary", label: "Part 11 summary", type: "kv" },
      {
        name: "customer_responsibilities", label: "Customer responsibilities", type: "repeat", itemLabel: "Responsibility",
        subFields: [{ name: "responsibility", label: "Responsibility", required: true }, { name: "owner", label: "Owner" }],
      },
      {
        name: "known_limitations", label: "Known limitations", type: "repeat", required: true, itemLabel: "Limitation",
        hint: 'Never omitted (VSR-FR-013) — add a single row with "none" if there truly are none.',
        subFields: [{ name: "limitation", label: "Limitation", required: true }, { name: "notes", label: "Notes" }],
      },
      {
        name: "evidence_manifest", label: "Evidence", type: "repeat", itemLabel: "Evidence item",
        subFields: [{ name: "evidence_id", label: "Evidence object ID" }],
      },
    ],
  },
  {
    path: "releases/{authorization_id}/post-go-live-verification",
    label: "Record post-go-live verification",
    fields: [
      { name: "authorization_id", label: "Release authorization ID", required: true },
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "outcome", label: "Outcome", type: "select", required: true, options: [{ value: "PASS", label: "Pass" }, { value: "FAIL", label: "Fail" }] },
      {
        name: "smoke_results", label: "Smoke test results", type: "repeat", itemLabel: "Result",
        subFields: [
          { name: "check", label: "Check", required: true },
          { name: "result", label: "Result", type: "select", options: [{ value: "PASS", label: "Pass" }, { value: "FAIL", label: "Fail" }] },
          { name: "notes", label: "Notes" },
        ],
      },
      {
        name: "monitoring_results", label: "Monitoring results", type: "repeat", itemLabel: "Result",
        subFields: [
          { name: "check", label: "Check", required: true },
          { name: "result", label: "Result", type: "select", options: [{ value: "PASS", label: "Pass" }, { value: "FAIL", label: "Fail" }] },
          { name: "notes", label: "Notes" },
        ],
      },
      { name: "rollback_ref", label: "Rollback reference", hint: "A FAIL outcome must reference a rollback, incident, or change (VSR-FR-024)." },
      { name: "incident_ref", label: "Incident reference" },
      { name: "change_ref", label: "Change reference" },
      { name: "notes", label: "Notes", type: "textarea" },
    ],
  },
];

const READS = [
  { label: "Go-live readiness (VSR id)", path: "releases/{p}/go-live-readiness" },
  { label: "Migration legacy trace (plan id)", path: "migrations/{p}/legacy-trace" },
];

export default function GoLivePage() {
  const { me } = useMe();
  const canWork = holdsAnyRole(me, ["Admin", "QA Releaser", "QA Reviewer"]);

  return (
    <div>
      <PageHead
        title="Deployment · PQ · go-live"
        subtitle="Performance qualification, data migration, the validation summary report and the release authorization."
      />

      <ReadCard />

      {!canWork && (
        <Banner tone="info" title="Read-only">
          Driving PQ, migration and release authorization needs the QA Releaser or QA Reviewer role.
        </Banner>
      )}

      {canWork && (
        <>
          <FormConsole title="Performance qualification" root="/validation/v1" ops={PQ_OPS} />

          <FormConsole title="Data migration" root="/validation/v1" ops={MIGRATION_OPS} />

          <FormConsole title="Validation summary & release authorization" root="/validation/v1" ops={SUMMARY_OPS} />

 <SignedJsonForm title="PQ · migration · release signed operations" root="/validation/v1" ops={GO_LIVE_SIGNED_OPS} />
        </>
      )}
    </div>
  );
}

// ---- Signed operations (SG-172) -----------------------------------------------------------------

const GO_LIVE_SIGNED_OPS: SignedJsonOp[] = [
  {
    label: "Approve a PQ scenario (site acceptance)",
    action: "approve",
    postPath: "pq/{scenario_id}/approve",
    challengePath: "pq/{scenario_id}/signature-challenges",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "reason", label: "Reason", type: "textarea", required: true },
      { name: "decision", label: "Decision", type: "select", default: "ACCEPTED", options: [{ value: "ACCEPTED", label: "Accepted" }, { value: "REJECTED", label: "Rejected" }] },
    ],
  },
  {
    label: "Approve a migration run (cutover)",
    action: "approve",
    postPath: "migrations/{run_id}/approve",
    challengePath: "migrations/{run_id}/signature-challenges",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "reason", label: "Reason", type: "textarea", required: true },
    ],
  },
  {
    label: "Approve a validation summary report",
    action: "approve",
    postPath: "summary-reports/{report_id}/approve",
    challengePath: "summary-reports/{report_id}/signature-challenges",
    about: "Decision is APPROVED | CONDITIONAL | REJECTED.",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "reason", label: "Reason", type: "textarea", required: true },
      { name: "decision", label: "Decision", type: "select", required: true, options: RELEASE_DECISIONS },
      {
        name: "decision_conditions", label: "Decision conditions", type: "repeat", itemLabel: "Condition",
        hint: "Only meaningful when decision is CONDITIONAL.",
        subFields: [{ name: "condition", label: "Condition", required: true }, { name: "names_critical_control", label: "Names a critical control", type: "bool" }],
      },
    ],
  },
  {
    label: "Authorize the release / go-live",
    action: "authorize",
    postPath: "releases/{vsr_id}/authorize",
    challengePath: "releases/{vsr_id}/authorize/signature-challenges",
    mirrorBodyInChallenge: true,
    // release_identity is a nested object (image_digest / code_commit / sbom_ref / schema_version /
    // migration_head / config_version) — genuinely nested enough that a JSON body is the honest UI
    // (`FormField` has no "nested object" type), same rationale as FormConsole's own JSON fallback.
    template:
      '{\n  "authorization_number": "",\n  "environment": "",\n  "config_fingerprint": "",\n  "release_identity": {\n    "image_digest": "",\n    "code_commit": "",\n    "sbom_ref": "",\n    "schema_version": "",\n    "migration_head": "",\n    "config_version": ""\n  },\n  "artifact_digests": {},\n  "decision": "APPROVED",\n  "go_live_gates": {},\n  "reason": "",\n  "conditions": [],\n  "production_performer_user_ids": []\n}',
    about:
        "This signature is bound to the exact payload below — decision is APPROVED | CONDITIONAL | REJECTED. Do not edit the payload after requesting the challenge.",
  },
  {
    label: "Record a deployment check",
    action: "deployment_check",
    postPath: "releases/{authorization_id}/deployment-check",
    challengePath: "releases/{authorization_id}/deployment-check/signature-challenges",
    about: "The signer must not be one of the listed production performers.",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "submitted_config_fingerprint", label: "Submitted config fingerprint", required: true },
      { name: "submitted_artifact_digests", label: "Submitted artifact digests", type: "kv" },
      { name: "reason", label: "Reason", type: "textarea", required: true },
      {
        name: "production_performer_user_ids", label: "Production performers", type: "stringList", itemLabel: "User ID",
        hint: "User IDs of everyone who performed the production deployment steps. The signer must not be listed here.",
      },
    ],
  },
];

function ReadCard() {
  const [which, setWhich] = useState(0);
  const [ref, setRef] = useState("");
  const [data, setData] = useState<unknown>(undefined);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setData(undefined);
    try {
      setData(await api.get<unknown>(`/validation/v1/${READS[which].path.replace("{p}", encodeURIComponent(ref.trim()))}`));
    } catch (err) {
      setData({ error: err instanceof Error ? err.message : String(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Go-live reads" />
      <div className="flex flex-wrap items-end gap-3 mt-3">
        <Field label="Report">
          <Select value={which} onChange={(e) => setWhich(Number(e.target.value))} style={{ minWidth: 200, maxWidth: 300, width: "100%" }}>
            {READS.map((r, i) => (
              <option key={r.path} value={i}>
                {r.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Reference / ID">
          <Input value={ref} onChange={(e) => setRef(e.target.value)} style={{ minWidth: 200, maxWidth: 260, width: "100%" }} />
        </Field>
        <Button variant="secondary" onClick={load} disabled={busy || !ref.trim()}>
          {busy ? "Loading…" : "Load"}
        </Button>
      </div>
      {data !== undefined && (
        <div className="mt-3">
          <JsonPanel title={READS[which].label} value={data} />
        </div>
      )}
    </Card>
  );
}
