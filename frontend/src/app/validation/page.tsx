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
import { FormConsole, type FormField } from "@/components/shared/FormConsole";
import { SignedJsonForm, type SignedJsonOp } from "@/components/shared/SignedJsonForm";

// Parameterised GET reads — {p} placeholders filled from the single "reference" input.
const READS = [
  { label: "Release gate (master plan id)", path: "releases/{p}/gate" },
  { label: "Validation package (scope)", path: "packages/{p}" },
  { label: "Validation package export (scope)", path: "packages/{p}/export" },
  { label: "Function assurance (function ref)", path: "functions/{p}/assurance" },
  { label: "Traceability (baseline id)", path: "traceability?baseline_id={p}" },
  { label: "Traceability gaps (baseline id)", path: "traceability/gaps?baseline_id={p}" },
  { label: "OQ coverage (execution id)", path: "oq/{p}/coverage" },
  { label: "Security qualification gate (suite id)", path: "security/{p}/gate" },
  { label: "Performance sizing (scenario id)", path: "performance/sizing?scenario_id={p}" },
  { label: "Exception gate (release ref)", path: "releases/{p}/exception-gate" },
  { label: "Migration legacy trace (plan id)", path: "migrations/{p}/legacy-trace" },
  { label: "Go-live readiness (VSR id)", path: "releases/{p}/go-live-readiness" },
];

export default function ValidationPage() {
  const { me } = useMe();
  const canWork = holdsAnyRole(me, ["Admin", "QA Reviewer", "QA Releaser"]);

  return (
    <div>
      <PageHead
        title="Validation platform"
        subtitle="VMP, intended-use risk, traceability, test execution, IQ/OQ, Part 11, data integrity, interfaces, DR/security/performance qualification, exceptions and revalidation."
      />

      <ReadCard />

      {!canWork && (
        <Banner tone="info" title="Read-only">
          Authoring validation deliverables needs the QA Reviewer or QA Releaser role.
        </Banner>
      )}

      {canWork && (
        <>
          <FormConsole
            title="VMP · intended use · traceability (Docs 79–81)"
            root="/validation/v1"
            ops={[
              {
                path: "master-plans",
                label: "Create or update a validation master plan",
                about: "Leave Plan ID blank to create a new plan; set it (with its expected version) to update an existing draft.",
                fields: [
                  { name: "plan_id", label: "Plan ID", hint: "Leave blank to create a new plan." },
                  { name: "expected_version", label: "Expected version", type: "number", hint: "Required when updating an existing plan." },
                  { name: "plan_number", label: "Plan number", required: true },
                  { name: "scope", label: "Scope", required: true, type: "textarea" },
                  { name: "regulatory_profiles", label: "Regulatory profiles", type: "stringList", itemLabel: "Profile" },
                  { name: "methodology", label: "Methodology", required: true },
                  { name: "responsibilities", label: "Responsibilities", type: "kv" },
                  { name: "retention_class", label: "Retention class" },
                  {
                    name: "new_deliverables", label: "Deliverables", type: "repeat", itemLabel: "Deliverable",
                    subFields: [
                      { name: "artifact_type", label: "Artifact type", required: true },
                      { name: "risk_condition", label: "Risk condition", required: true },
                      { name: "owner", label: "Owner", required: true },
                      { name: "review_required", label: "Review required", type: "bool" },
                      { name: "signature_required", label: "Signature required", type: "bool" },
                      { name: "evidence_type", label: "Evidence type", required: true },
                      { name: "release_blocker", label: "Blocks release", type: "bool", default: "true" },
                    ],
                  },
                ],
              },
              {
                path: "intended-use",
                label: "Record intended use",
                fields: [
                  { name: "scope_ref", label: "Scope reference", required: true },
                  { name: "scope_version", label: "Scope version", required: true },
                  { name: "regulated_process", label: "Regulated process", required: true },
                  { name: "users", label: "Users", type: "stringList", itemLabel: "User / role" },
                  { name: "record_relevance", label: "Record relevance", type: "bool" },
                  { name: "signature_relevance", label: "Signature relevance", type: "bool" },
                ],
              },
              {
                path: "function-risks",
                label: "Add a function risk assessment",
                fields: [
                  { name: "function_ref", label: "Function reference", required: true },
                  { name: "function_version", label: "Function version", required: true },
                  { name: "failure_modes", label: "Failure modes", type: "stringList", itemLabel: "Failure mode" },
                  { name: "impacts", label: "Impacts", type: "kv" },
                  { name: "detectability", label: "Detectability", required: true },
                  { name: "automation_role", label: "Automation role", required: true },
                  { name: "has_release_or_disposition", label: "Has release/disposition role", type: "bool" },
                  { name: "has_signature_role", label: "Has signature role", type: "bool" },
                  { name: "has_audit_immutability_role", label: "Has audit/immutability role", type: "bool" },
                  { name: "has_enforcement_role", label: "Has enforcement role", type: "bool" },
                  { name: "controls", label: "Controls", type: "stringList", itemLabel: "Control" },
                ],
              },
              {
                path: "requirements:ingest",
                label: "Ingest requirements",
                fields: [
                  {
                    name: "requirements", label: "Requirements", type: "repeat", required: true, itemLabel: "Requirement",
                    subFields: [
                      { name: "requirement_code", label: "Requirement code", required: true },
                      { name: "source_document", label: "Source document", required: true },
                      { name: "source_section", label: "Source section", required: true },
                      { name: "text", label: "Text", required: true },
                      { name: "requirement_class", label: "Requirement class", required: true },
                      { name: "regulatory_source", label: "Regulatory source" },
                      { name: "binding_status", label: "Binding status", default: "BINDING" },
                    ],
                  },
                ],
              },
              {
                path: "trace-links",
                label: "Add a trace link",
                fields: [
                  { name: "source_type", label: "Source type", required: true },
                  { name: "source_id", label: "Source ID", required: true },
                  { name: "source_version", label: "Source version", required: true },
                  { name: "target_type", label: "Target type", required: true },
                  { name: "target_id", label: "Target ID", required: true },
                  { name: "target_version", label: "Target version", required: true },
                  { name: "relation_type", label: "Relation type", required: true, placeholder: "e.g. verifies, implements" },
                ],
              },
              {
                path: "baselines",
                label: "Freeze a requirement baseline",
                fields: [
                  { name: "release_scope", label: "Release scope", required: true },
                  { name: "customer_scope", label: "Customer scope" },
                  {
                    name: "requirement_refs", label: "Requirements in scope", type: "repeat", required: true, itemLabel: "Requirement",
                    subFields: [
                      { name: "code", label: "Requirement code", required: true },
                      { name: "version", label: "Version" },
                    ],
                  },
                  {
                    name: "exclusions", label: "Exclusions", type: "repeat", itemLabel: "Exclusion",
                    subFields: [
                      { name: "code", label: "Requirement code", required: true },
                      { name: "rationale", label: "Rationale" },
                    ],
                  },
                ],
              },
            ]}
          />
          <SignedJsonForm title="VMP · function risk — signed approvals" root="/validation/v1" ops={VMP_SIGNED_OPS} />

          <FormConsole
            title="Test library · IQ · OQ (Docs 82–84)"
            root="/validation/v1"
            ops={[
              {
                path: "tests",
                label: "Create a test",
                about: "Adds a test definition to the library (not yet approved for execution).",
                fields: [
                  { name: "test_code", label: "Test code", required: true, placeholder: "e.g. T-BATCH-001" },
                  { name: "method", label: "Method", type: "select", required: true, options: ["AUTOMATED", "SCRIPTED_MANUAL", "EXPLORATORY", "REVIEW_INSPECTION", "ANALYSIS", "SUPPLIER_EVIDENCE"].map((v) => ({ value: v, label: v })) },
                  { name: "procedure", label: "Procedure", type: "textarea", required: true },
                  { name: "expected_results", label: "Expected results", type: "textarea", required: true },
                  { name: "independent_review_required", label: "Independent review required", type: "bool" },
                  {
                    name: "requirement_refs", label: "Requirement references", type: "repeat", itemLabel: "Requirement",
                    hint: "The requirements this test verifies (optional).",
                    subFields: [
                      { name: "code", label: "Requirement code", required: true },
                      { name: "version", label: "Version" },
                    ],
                  },
                ],
              },
              {
                path: "executions",
                label: "Start a test execution",
                fields: [
                  { name: "test_definition_id", label: "Test definition ID", required: true },
                  { name: "environment_fingerprint", label: "Environment fingerprint", type: "kv" },
                  { name: "ci_run_ref", label: "CI run reference" },
                  { name: "performer_user_id", label: "Performer", type: "userSelect", hint: "Defaults to you if left blank." },
                ],
              },
              {
                path: "automated-evidence",
                label: "Attach automated evidence",
                fields: [
                  { name: "execution_id", label: "Execution ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "ci_run_ref", label: "CI run reference", required: true },
                  { name: "result", label: "Result", type: "select", required: true, options: [{ value: "PASS", label: "Pass" }, { value: "FAIL", label: "Fail" }] },
                  {
                    name: "evidence_manifest", label: "Evidence", type: "repeat", required: true, itemLabel: "Evidence item",
                    hint: "Each item referencing a finalized Evidence Store object.",
                    subFields: [{ name: "evidence_id", label: "Evidence object ID" }],
                  },
                ],
              },
              {
                path: "iq/protocols",
                label: "Create an IQ protocol",
                fields: [
                  { name: "environment", label: "Environment", required: true },
                  { name: "release_ref", label: "Release reference", required: true },
                  { name: "deployment_profile", label: "Deployment profile", required: true },
                  {
                    name: "expected_components", label: "Expected components", type: "repeat", itemLabel: "Component",
                    subFields: [{ name: "component", label: "Component" }, { name: "expected_version", label: "Expected version" }],
                  },
                  {
                    name: "checks", label: "Checks", type: "repeat", itemLabel: "Check",
                    subFields: [{ name: "check_code", label: "Check code" }, { name: "description", label: "Description" }],
                  },
                  { name: "acceptance_criteria", label: "Acceptance criteria", type: "textarea", required: true },
                ],
              },
              {
                path: "iq/executions",
                label: "Start an IQ execution",
                fields: [
                  { name: "protocol_id", label: "IQ protocol ID", required: true },
                  { name: "installed_inventory", label: "Installed inventory", type: "kv", required: true },
                  {
                    name: "check_results", label: "Check results", type: "repeat", itemLabel: "Result",
                    subFields: [{ name: "check_code", label: "Check code" }, { name: "outcome", label: "Outcome", type: "select", options: [{ value: "PASS", label: "Pass" }, { value: "FAIL", label: "Fail" }] }],
                  },
                  { name: "is_delta_iq", label: "Delta IQ", type: "bool" },
                  { name: "performer_user_id", label: "Performer", type: "userSelect", hint: "Defaults to you if left blank." },
                ],
              },
              {
                path: "oq:suites",
                label: "Create an OQ suite",
                fields: [
                  { name: "baseline_id", label: "Requirement baseline ID", required: true },
                  {
                    name: "selected_test_refs", label: "Selected tests", type: "repeat", required: true, itemLabel: "Test",
                    subFields: [{ name: "test_ref", label: "Test reference", required: true }],
                  },
                  {
                    name: "selected_evidence_refs", label: "Selected evidence", type: "repeat", itemLabel: "Evidence item",
                    subFields: [{ name: "evidence_id", label: "Evidence object ID" }],
                  },
                  {
                    name: "exclusions", label: "Exclusions", type: "repeat", itemLabel: "Exclusion",
                    subFields: [{ name: "test_ref", label: "Test reference" }, { name: "rationale", label: "Rationale" }],
                  },
                  { name: "environment_fingerprint", label: "Environment fingerprint", type: "kv" },
                ],
              },
              {
                path: "oq/executions",
                label: "Record an OQ execution",
                fields: [
                  { name: "suite_id", label: "OQ suite ID", required: true },
                  {
                    name: "executed_test_refs", label: "Executed tests", type: "repeat", required: true, itemLabel: "Test",
                    subFields: [
                      { name: "test_ref", label: "Test reference", required: true },
                      { name: "result", label: "Result", type: "select", options: [{ value: "PASS", label: "Pass" }, { value: "FAIL", label: "Fail" }] },
                    ],
                  },
                  {
                    name: "deviations", label: "Deviations", type: "repeat", itemLabel: "Deviation",
                    subFields: [{ name: "ref", label: "Reference" }, { name: "description", label: "Description" }],
                  },
                ],
              },
            ]}
          />
          <SignedJsonForm title="Test · IQ · OQ — signed completions & approvals" root="/validation/v1" ops={TEST_IQ_OQ_SIGNED_OPS} />

          <FormConsole
            title="Infrastructure · Part 11 · data integrity · interfaces (Docs 86, 88–90)"
            root="/validation/v1"
            ops={[
              {
                path: "infrastructure/profiles",
                label: "Create an infrastructure profile",
                fields: [
                  { name: "deployment_profile", label: "Deployment profile", required: true },
                  { name: "provider", label: "Provider", required: true },
                  {
                    name: "required_components", label: "Required components", type: "repeat", itemLabel: "Component",
                    subFields: [{ name: "component", label: "Component" }, { name: "version", label: "Version" }],
                  },
                  {
                    name: "control_tests", label: "Control tests", type: "repeat", itemLabel: "Test",
                    subFields: [{ name: "control_ref", label: "Control reference" }, { name: "description", label: "Description" }],
                  },
                  {
                    name: "supplier_evidence_refs", label: "Supplier evidence", type: "repeat", itemLabel: "Evidence item",
                    subFields: [{ name: "evidence_id", label: "Evidence object ID" }],
                  },
                  { name: "change_triggers", label: "Change triggers", type: "stringList", itemLabel: "Trigger" },
                ],
              },
              {
                path: "infrastructure/fingerprints",
                label: "Record an environment fingerprint",
                fields: [
                  { name: "profile_id", label: "Infrastructure profile ID", required: true },
                  { name: "captured_versions", label: "Captured versions", type: "kv", required: true },
                  { name: "config_hashes", label: "Config hashes", type: "kv" },
                  { name: "resource_sizing", label: "Resource sizing", type: "kv" },
                  { name: "network_security_refs", label: "Network security references", type: "kv" },
                  { name: "time_backup_refs", label: "Time/backup references", type: "kv" },
                ],
              },
              {
                path: "infrastructure/tests",
                label: "Record an infrastructure control test",
                fields: [
                  { name: "fingerprint_id", label: "Environment fingerprint ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                ],
              },
              {
                path: "part11/assessments",
                label: "Create a Part 11 assessment",
                fields: [
                  { name: "record_or_signature_type", label: "Record or signature type", required: true },
                  { name: "predicate_use", label: "Predicate use", required: true },
                  { name: "system_component", label: "System component", required: true },
                  { name: "context", label: "Context", type: "select", default: "CLOSED", options: [{ value: "CLOSED", label: "Closed" }, { value: "OPEN", label: "Open" }] },
                  { name: "applicable", label: "Applicable", type: "bool", default: "true" },
                  { name: "customer_responsibilities", label: "Customer responsibilities", type: "textarea" },
                ],
              },
              {
                path: "part11/{assessment_id}/test-suite",
                label: "Attach a Part 11 test suite",
                fields: [
                  { name: "assessment_id", label: "Part 11 assessment ID", required: true },
                  { name: "control_citations", label: "Control citations", type: "stringList", required: true, itemLabel: "Citation", placeholder: "e.g. 11.10(a), 11.10(e), 11.50" },
                ],
              },
              {
                path: "part11/control-results",
                label: "Record a Part 11 control result",
                fields: [
                  { name: "control_evidence_id", label: "Control evidence ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "result", label: "Result", type: "select", required: true, options: [{ value: "PASS", label: "Pass" }, { value: "FAIL", label: "Fail" }] },
                  { name: "test_ref", label: "Test reference" },
                  {
                    name: "evidence_manifest", label: "Evidence", type: "repeat", itemLabel: "Evidence item",
                    subFields: [{ name: "evidence_id", label: "Evidence object ID" }],
                  },
                  { name: "configuration_ref", label: "Configuration reference" },
                  { name: "procedure_ref", label: "Procedure reference" },
                  { name: "deviation_ref", label: "Deviation reference" },
                ],
              },
              {
                path: "data-integrity/suites",
                label: "Create a data-integrity suite",
                fields: [
                  { name: "data_class", label: "Data class", required: true },
                  { name: "lifecycle", label: "Lifecycle", required: true },
                  { name: "threats", label: "Threats", type: "stringList", itemLabel: "Threat" },
                  { name: "controls", label: "Controls", type: "stringList", itemLabel: "Control" },
                  { name: "tests", label: "Tests", type: "stringList", itemLabel: "Test" },
                ],
              },
              {
                path: "data-integrity/tamper-tests",
                label: "Record a tamper test",
                fields: [
                  { name: "profile_id", label: "Data-integrity profile ID", required: true },
                  { name: "isolated_snapshot_ref", label: "Isolated snapshot reference", required: true },
                  { name: "tamper_action", label: "Tamper action", required: true },
                  { name: "verifier_version", label: "Verifier version", required: true },
                  { name: "detected", label: "Detected", type: "bool" },
                  { name: "detection_evidence", label: "Detection evidence", type: "kv" },
                ],
              },
              {
                path: "interfaces/profiles",
                label: "Create an interface profile",
                fields: [
                  { name: "provider_or_device", label: "Provider or device", required: true },
                  { name: "contract_ref", label: "Contract reference", required: true },
                  { name: "contract_version", label: "Contract version", required: true },
                  { name: "intended_use", label: "Intended use", required: true },
                  { name: "risk_category", label: "Risk category", required: true },
                  { name: "auth_expectation", label: "Auth expectation", required: true },
                  { name: "source_time_quality_expectation", label: "Source time-quality expectation", type: "kv" },
                  { name: "failure_scenarios", label: "Failure scenarios", type: "stringList", itemLabel: "Scenario" },
                ],
              },
              {
                path: "interfaces/tests",
                label: "Record an interface contract test",
                fields: [
                  { name: "profile_id", label: "Interface profile ID", required: true },
                  { name: "scenario", label: "Scenario", required: true },
                  { name: "raw_inputs", label: "Raw inputs", type: "kv" },
                  { name: "canonical_outputs", label: "Canonical outputs", type: "kv" },
                  { name: "gxp_result", label: "GxP result", type: "kv" },
                  { name: "external_reconciliation", label: "External reconciliation", type: "kv" },
                  { name: "status", label: "Status", type: "select", default: "PASS", options: [{ value: "PASS", label: "Pass" }, { value: "FAIL", label: "Fail" }] },
                ],
              },
              {
                path: "interfaces/edge-outage-tests",
                label: "Record an edge-outage test",
                fields: [
                  { name: "profile_id", label: "Interface profile ID", required: true },
                  { name: "scenario", label: "Scenario", default: "edge_outage" },
                  { name: "raw_inputs", label: "Raw inputs", type: "kv" },
                  { name: "canonical_outputs", label: "Canonical outputs", type: "kv" },
                  { name: "gxp_result", label: "GxP result", type: "kv" },
                  { name: "external_reconciliation", label: "External reconciliation", type: "kv" },
                  { name: "status", label: "Status", type: "select", default: "PASS", options: [{ value: "PASS", label: "Pass" }, { value: "FAIL", label: "Fail" }] },
                ],
              },
            ]}
          />
          <SignedJsonForm title="Infrastructure · Part 11 · data integrity · interfaces — signed approvals" root="/validation/v1" ops={INFRA_SIGNED_OPS} />

          <FormConsole
            title="DR · security · performance qualification (Docs 91–93)"
            root="/validation/v1"
            ops={[
              {
                path: "dr/scenarios",
                label: "Create a DR scenario",
                fields: [
                  { name: "failure_type", label: "Failure type", required: true },
                  { name: "components", label: "Components", type: "stringList", required: true, itemLabel: "Component" },
                  { name: "recovery_method", label: "Recovery method", required: true },
                  { name: "target_rpo_seconds", label: "Target RPO (seconds)", type: "number" },
                  { name: "target_rto_seconds", label: "Target RTO (seconds)", type: "number", required: true },
                  { name: "restore_order", label: "Restore order", type: "stringList", itemLabel: "Component" },
                  { name: "acceptance_criteria", label: "Acceptance criteria", type: "textarea", required: true },
                ],
              },
              {
                path: "dr/executions",
                label: "Record a DR execution",
                fields: [
                  { name: "scenario_id", label: "DR scenario ID", required: true },
                  { name: "backup_set_ref", label: "Backup set reference", required: true },
                  { name: "restore_point", label: "Restore point", type: "datetime" },
                  { name: "started_at", label: "Started at", type: "datetime", required: true },
                  { name: "completed_at", label: "Completed at", type: "datetime", required: true },
                  { name: "integrity_checks", label: "Integrity checks", type: "kv", required: true, hint: 'Enter "true" or "false" as the value for each check.' },
                ],
              },
              {
                path: "dr/{execution_id}/measure",
                label: "Measure RPO/RTO for a DR execution",
                fields: [
                  { name: "execution_id", label: "DR execution ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "gxp_smoke_results", label: "GxP smoke test results", type: "kv" },
                  {
                    name: "deviations", label: "Deviations", type: "repeat", itemLabel: "Deviation",
                    subFields: [{ name: "ref", label: "Reference" }, { name: "description", label: "Description" }],
                  },
                ],
              },
              {
                path: "security/suites",
                label: "Create a security-qualification suite",
                fields: [
                  { name: "release_ref", label: "Release reference", required: true },
                  { name: "deployment_profile", label: "Deployment profile", required: true },
                  { name: "threat_control_baseline_ref", label: "Threat control baseline reference", required: true },
                  { name: "planned_tests", label: "Planned tests", type: "stringList", itemLabel: "Test" },
                ],
              },
              {
                path: "security/tests",
                label: "Record a security test",
                fields: [
                  { name: "suite_id", label: "Suite ID", required: true },
                  { name: "control_ref", label: "Control reference", required: true },
                  { name: "result", label: "Result", type: "select", required: true, options: [{ value: "PASS", label: "Pass" }, { value: "FAIL", label: "Fail" }] },
                  {
                    name: "severity_if_failed", label: "Severity if failed", type: "select", default: "MEDIUM",
                    options: ["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((v) => ({ value: v, label: v })),
                  },
                ],
              },
              {
                path: "security/findings",
                label: "Record a security finding",
                fields: [
                  { name: "suite_id", label: "Suite ID", required: true },
                  { name: "source", label: "Source", required: true, placeholder: "e.g. SAST, SCA, IAC, CONTAINER, PENTEST, MANUAL" },
                  { name: "control_ref", label: "Control reference", required: true },
                  { name: "severity", label: "Severity", required: true, placeholder: "e.g. LOW, MEDIUM, HIGH, CRITICAL" },
                  { name: "vulnerability_ref", label: "Vulnerability reference" },
                ],
              },
            ]}
          />
          <SignedJsonForm title="DR · security · performance — signed operations" root="/validation/v1" ops={DR_SEC_PERF_SIGNED_OPS} />

          <FormConsole
            title="Exceptions · revalidation (Docs 94, 96)"
            root="/validation/v1"
            ops={[
              {
                path: "change-impacts",
                label: "Record a change impact",
                fields: [
                  { name: "change_ref", label: "Change reference", required: true },
                  { name: "change_type", label: "Change type", required: true },
                  {
                    name: "affected_trace_artifacts", label: "Affected trace artifacts", type: "repeat", itemLabel: "Artifact",
                    subFields: [{ name: "type", label: "Type" }, { name: "ref", label: "Reference" }],
                  },
                  { name: "is_emergency", label: "Emergency change", type: "bool" },
                  { name: "revalidation_level", label: "Revalidation level", required: true },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                ],
              },
              {
                path: "revalidation-plans",
                label: "Approve a revalidation plan",
                about: "Attaches the revalidation plan reference to a change impact.",
                fields: [
                  { name: "change_impact_id", label: "Change impact ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "revalidation_ref", label: "Revalidation reference", required: true },
                ],
              },
              {
                path: "revalidations",
                label: "Record a revalidation",
                fields: [
                  { name: "change_impact_id", label: "Change impact ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "evidence_ref", label: "Evidence reference", required: true },
                ],
              },
              {
                path: "decommission",
                label: "Record a decommission decision",
                fields: [
                  { name: "baseline_id", label: "Baseline ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "decommission_evidence", label: "Decommission evidence", type: "kv", required: true },
                ],
              },
            ]}
          />
          <SignedJsonForm title="Exceptions · periodic review — signed operations" root="/validation/v1" ops={EXCEPTION_SIGNED_OPS} />
        </>
      )}
    </div>
  );
}

// ---- Signed operations (SG-172) -----------------------------------------------------------------
// Every op below calls a `POST {postPath}` command whose class requires `challenge_id`/`reauth_password`
// (see the relevant `commands_*.py`). The templates show the command's real field set (minus the
// transport fields `SignedJsonForm` adds) so a filled-in submission has a real chance of passing
// validation once Document 106 supplies the still-missing policy row (SG-172, blocking) — until then
// every one of these correctly returns SIGNATURE_POLICY_UNRESOLVED (409).

const VMP_SIGNED_OPS: SignedJsonOp[] = [
  {
    label: "Release a master plan",
    action: "release",
    postPath: "master-plans/{plan_id}/release",
    challengePath: "master-plans/{plan_id}/signature-challenges",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "reason", label: "Reason", type: "textarea", required: true },
    ],
  },
  {
    label: "Approve a function-risk assessment",
    action: "approve",
    postPath: "function-risks/{assessment_id}/approve",
    challengePath: "function-risks/{assessment_id}/signature-challenges",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "reason", label: "Reason", type: "textarea", required: true },
      { name: "residual_risk", label: "Residual risk" },
    ],
  },
];

const TEST_IQ_OQ_SIGNED_OPS: SignedJsonOp[] = [
  {
    label: "Approve a test definition",
    action: "approve",
    postPath: "tests/{test_id}/approve",
    challengePath: "tests/{test_id}/signature-challenges",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "reason", label: "Reason", type: "textarea", required: true },
    ],
  },
  {
    label: "Complete a test execution",
    action: "complete",
    postPath: "executions/{execution_id}/complete",
    challengePath: "executions/{execution_id}/signature-challenges",
    about: "Status is PASS | FAIL | BLOCKED | SKIPPED.",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "actual_result", label: "Actual result", type: "textarea", required: true },
      {
        name: "status", label: "Status", type: "select", required: true, default: "PASS",
        options: ["PASS", "FAIL", "BLOCKED", "SKIPPED"].map((v) => ({ value: v, label: v })),
      },
      { name: "observations", label: "Observations", type: "textarea" },
      { name: "blocked_reason", label: "Blocked reason", hint: "Set when status is BLOCKED." },
      {
        name: "evidence_manifest", label: "Evidence", type: "repeat", itemLabel: "Evidence item",
        subFields: [{ name: "evidence_id", label: "Evidence object ID" }],
      },
      { name: "reviewer_user_id", label: "Reviewer", type: "userSelect", hint: "Required when the test needs independent review." },
    ],
  },
  {
    label: "Complete an IQ execution",
    action: "complete",
    postPath: "iq/executions/{execution_id}/complete",
    challengePath: "iq/executions/{execution_id}/signature-challenges",
    about: "Result is PASS | FAIL.",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "result", label: "Result", type: "select", required: true, default: "PASS", options: [{ value: "PASS", label: "Pass" }, { value: "FAIL", label: "Fail" }] },
      {
        name: "evidence_manifest", label: "Evidence", type: "repeat", itemLabel: "Evidence item",
        subFields: [{ name: "evidence_id", label: "Evidence object ID" }],
      },
    ],
  },
  {
    label: "Approve an IQ execution",
    action: "approve",
    postPath: "iq/executions/{execution_id}/approve",
    challengePath: "iq/executions/{execution_id}/signature-challenges",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "reason", label: "Reason", type: "textarea", required: true },
    ],
  },
  {
    label: "Approve an OQ execution",
    action: "approve",
    postPath: "oq/{execution_id}/approve",
    challengePath: "oq/{execution_id}/signature-challenges",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "reason", label: "Reason", type: "textarea", required: true },
    ],
  },
];

const APPROVAL_FIELDS: FormField[] = [
  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
  { name: "reason", label: "Reason", type: "textarea", required: true },
];

const INFRA_SIGNED_OPS: SignedJsonOp[] = [
  {
    label: "Approve an infrastructure fingerprint",
    action: "approve",
    postPath: "infrastructure/{fingerprint_id}/approve",
    challengePath: "infrastructure/{fingerprint_id}/signature-challenges",
    fields: APPROVAL_FIELDS,
  },
  {
    label: "Approve a Part 11 assessment",
    action: "approve",
    postPath: "part11/{assessment_id}/approve",
    challengePath: "part11/{assessment_id}/signature-challenges",
    fields: APPROVAL_FIELDS,
  },
  {
    label: "Approve a data-integrity profile",
    action: "approve",
    postPath: "data-integrity/{profile_id}/approve",
    challengePath: "data-integrity/{profile_id}/signature-challenges",
    fields: APPROVAL_FIELDS,
  },
  {
    label: "Approve an interface profile",
    action: "approve",
    postPath: "interfaces/{profile_id}/approve",
    challengePath: "interfaces/{profile_id}/signature-challenges",
    fields: APPROVAL_FIELDS,
  },
];

const DR_SEC_PERF_SIGNED_OPS: SignedJsonOp[] = [
  {
    label: "Approve a DR execution",
    action: "approve",
    postPath: "dr/{execution_id}/approve",
    challengePath: "dr/{execution_id}/signature-challenges",
    fields: APPROVAL_FIELDS,
  },
  {
    label: "Approve a security-qualification suite",
    action: "approve",
    postPath: "security/{suite_id}/approve",
    challengePath: "security/{suite_id}/signature-challenges",
    fields: APPROVAL_FIELDS,
  },
  {
    label: "Create a performance scenario",
    action: "create",
    postPath: "performance/scenarios",
    challengePath: "performance/scenarios/signature-challenges",
    mergeChallengeField: "new_record_id",
    about: "The challenge pre-generates the scenario id before you submit.",
    fields: [
      { name: "release_ref", label: "Release reference", required: true },
      { name: "environment", label: "Environment", required: true },
      { name: "load_model", label: "Load model", type: "kv" },
      { name: "planned_duration_seconds", label: "Planned duration (seconds)", type: "number", default: "3600" },
      { name: "thresholds", label: "Thresholds", type: "kv", required: true, hint: "Must not be empty — at least one setting is required." },
    ],
  },
  {
    label: "Record a performance run",
    action: "create",
    postPath: "performance/runs",
    challengePath: "performance/runs/signature-challenges",
    mergeChallengeField: "new_record_id",
    about: "The challenge pre-generates the run id before you submit.",
    fields: [
      { name: "scenario_id", label: "Performance scenario ID", required: true },
      { name: "build_ref", label: "Build reference", required: true },
      { name: "harness_ref", label: "Harness reference", required: true },
      { name: "started_at", label: "Started at", type: "datetime", required: true },
      { name: "completed_at", label: "Completed at", type: "datetime", required: true },
      { name: "metrics", label: "Metrics", type: "kv" },
    ],
  },
  {
    label: "Evaluate a performance run",
    action: "evaluate",
    postPath: "performance/{run_id}/evaluate",
    challengePath: "performance/{run_id}/signature-challenges",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "headroom_basis_points", label: "Headroom (basis points)", type: "number" },
      { name: "bottleneck", label: "Bottleneck" },
    ],
  },
];

// models.py FINDING_SEVERITIES — shared by every exception/finding severity field in this module.
const FINDING_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((v) => ({ value: v, label: v }));

const EXCEPTION_SIGNED_OPS: SignedJsonOp[] = [
  {
    label: "Raise a validation exception",
    action: "create",
    postPath: "exceptions",
    challengePath: "exceptions/signature-challenges",
    mergeChallengeField: "new_record_id",
    about: "The signer must be independent of the person who requested this exception.",
    fields: [
      { name: "release_ref", label: "Release reference" },
      { name: "exception_type", label: "Exception type", type: "select", required: true, default: "TEST_FAILURE", options: ["DEFECT", "TEST_FAILURE", "PROTOCOL_DEVIATION", "ENVIRONMENT_DEVIATION", "EVIDENCE_ISSUE", "REQUIREMENT_GAP"].map((v) => ({ value: v, label: v })) },
      { name: "source_execution_type", label: "Source execution type", required: true },
      { name: "source_execution_id", label: "Source execution ID", required: true },
      { name: "original_evidence", label: "Original evidence", type: "kv", required: true, hint: "Must not be empty — at least one setting is required." },
      { name: "affected_requirement_refs", label: "Affected requirements", type: "stringList", itemLabel: "Requirement code" },
      { name: "severity", label: "Severity", type: "select", required: true, default: "HIGH", options: FINDING_SEVERITIES },
      { name: "gxp_impact", label: "GxP impact", type: "bool", default: "false" },
      { name: "release_impact", label: "Release impact", default: "BLOCKING" },
      { name: "requested_by_user_id", label: "Requested by", type: "userSelect", required: true },
    ],
  },
  {
    label: "Triage an exception",
    action: "triage",
    postPath: "exceptions/{exception_id}/triage",
    challengePath: "exceptions/{exception_id}/signature-challenges",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "severity", label: "Severity", type: "select", required: true, default: "HIGH", options: FINDING_SEVERITIES },
      { name: "gxp_impact", label: "GxP impact", type: "bool", required: true },
      { name: "release_impact", label: "Release impact", required: true },
      { name: "root_cause", label: "Root cause", type: "textarea" },
    ],
  },
  {
    label: "Attach a retest plan",
    action: "retest_plan",
    postPath: "exceptions/{exception_id}/retest-plan",
    challengePath: "exceptions/{exception_id}/signature-challenges",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      { name: "retest_plan", label: "Retest plan", type: "kv", required: true, hint: "Must not be empty — at least one setting is required." },
      { name: "fix_ref", label: "Fix reference" },
    ],
  },
  {
    label: "Disposition an exception",
    action: "disposition",
    postPath: "exceptions/{exception_id}/disposition",
    challengePath: "exceptions/{exception_id}/signature-challenges",
    about: "residual_risk_rationale is required when disposition is ACCEPTED_WITH_RATIONALE.",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      {
        name: "disposition", label: "Disposition", type: "select", required: true,
        options: ["OPEN", "FIX", "RETEST", "ACCEPTED_WITH_RATIONALE", "DEFERRED_BLOCKING", "CLOSED"].map((v) => ({ value: v, label: v })),
      },
      { name: "residual_risk_rationale", label: "Residual risk rationale", type: "textarea" },
      { name: "reason", label: "Reason", type: "textarea", required: true },
    ],
  },
  {
    label: "Create a periodic review",
    action: "create",
    postPath: "periodic-reviews",
    challengePath: "periodic-reviews/signature-challenges",
    mergeChallengeField: "new_record_id",
    about: "The challenge pre-generates the review id before you submit.",
    fields: [
      { name: "release_ref", label: "Release reference", required: true },
      { name: "period_start", label: "Period start", type: "datetime", required: true },
      { name: "period_end", label: "Period end", type: "datetime", required: true },
      { name: "inputs_considered", label: "Inputs considered", type: "kv", required: true, hint: "Must not be empty — at least one setting is required." },
    ],
  },
  {
    label: "Record a periodic-review decision",
    action: "decision",
    postPath: "periodic-reviews/{review_id}/decision",
    challengePath: "periodic-reviews/{review_id}/signature-challenges",
    fields: [
      { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
      {
        name: "decision", label: "Decision", type: "select", required: true,
        options: ["VALIDATED_CONFIRMED", "ACTION_REQUIRED", "REVALIDATION_REQUIRED", "SUSPENDED"].map((v) => ({ value: v, label: v })),
      },
    ],
  },
];

function ReadCard() {
  const [which, setWhich] = useState(0);
  const [ref, setRef] = useState("");
  const [data, setData] = useState<unknown>(undefined);
  const [busy, setBusy] = useState(false);

  const needsRef = READS[which].path.includes("{p}");

  async function load() {
    setBusy(true);
    setData(undefined);
    const path = READS[which].path.replace("{p}", encodeURIComponent(ref.trim()));
    try {
      setData(await api.get<unknown>(`/validation/v1/${path}`));
    } catch (err) {
      setData({ error: err instanceof Error ? err.message : String(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Validation reads" />
      <div className="flex items-end gap-3 mt-3" style={{ flexWrap: "wrap" }}>
        <Field label="Report">
          <Select value={which} onChange={(e) => setWhich(Number(e.target.value))} style={{ minWidth: 320 }}>
            {READS.map((r, i) => (
              <option key={r.path} value={i}>
                {r.label}
              </option>
            ))}
          </Select>
        </Field>
        {needsRef && (
          <Field label="Reference / ID">
            <Input value={ref} onChange={(e) => setRef(e.target.value)} style={{ minWidth: 260 }} />
          </Field>
        )}
        <Button variant="secondary" onClick={load} disabled={busy || (needsRef && !ref.trim())}>
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
