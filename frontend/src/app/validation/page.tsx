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
import { FormConsole } from "@/components/shared/FormConsole";
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
        subtitle="Documents 79–96 — VMP, intended-use risk, traceability, test execution, IQ/OQ, Part 11, data integrity, interfaces, DR/security/performance qualification, exceptions and revalidation."
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
              { path: "master-plans", label: "Create a validation master plan" },
              { path: "intended-use", label: "Record intended use" },
              { path: "function-risks", label: "Add a function risk assessment" },
              { path: "requirements:ingest", label: "Ingest requirements" },
              { path: "trace-links", label: "Add trace links" },
              { path: "baselines", label: "Freeze a baseline" },
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
                  { name: "requirement_refs", label: "Requirement refs (JSON array)", type: "json" },
                ],
              },
              { path: "executions", label: "Record a test execution (JSON)" },
              { path: "automated-evidence", label: "Attach automated evidence (JSON)" },
              { path: "iq/protocols", label: "Create an IQ protocol" },
              { path: "iq/executions", label: "Record an IQ execution" },
              { path: "oq:suites", label: "Create an OQ suite" },
              { path: "oq/executions", label: "Record an OQ execution" },
            ]}
          />
          <SignedJsonForm title="Test · IQ · OQ — signed completions & approvals" root="/validation/v1" ops={TEST_IQ_OQ_SIGNED_OPS} />

          <FormConsole
            title="Infrastructure · Part 11 · data integrity · interfaces (Docs 86, 88–90)"
            root="/validation/v1"
            ops={[
              { path: "infrastructure/profiles", label: "Create an infrastructure profile" },
              { path: "infrastructure/fingerprints", label: "Record an environment fingerprint" },
              { path: "infrastructure/tests", label: "Record an infrastructure control test" },
              { path: "part11/assessments", label: "Create a Part 11 assessment" },
              { path: "part11/{assessment_id}/test-suite", label: "Attach a Part 11 test suite" },
              { path: "part11/control-results", label: "Record Part 11 control results" },
              { path: "data-integrity/suites", label: "Create a data-integrity suite" },
              { path: "data-integrity/tamper-tests", label: "Record a tamper test" },
              { path: "interfaces/profiles", label: "Create an interface profile" },
              { path: "interfaces/tests", label: "Record an interface contract test" },
              { path: "interfaces/edge-outage-tests", label: "Record an edge-outage test" },
            ]}
          />
          <SignedJsonForm title="Infrastructure · Part 11 · data integrity · interfaces — signed approvals" root="/validation/v1" ops={INFRA_SIGNED_OPS} />

          <FormConsole
            title="DR · security · performance qualification (Docs 91–93)"
            root="/validation/v1"
            ops={[
              { path: "dr/scenarios", label: "Create a DR scenario" },
              { path: "dr/executions", label: "Record a DR execution" },
              { path: "dr/{execution_id}/measure", label: "Measure RPO/RTO for a DR execution" },
              { path: "security/suites", label: "Create a security-qualification suite" },
              { path: "security/tests", label: "Record a security test" },
              { path: "security/findings", label: "Record a security finding" },
            ]}
          />
          <SignedJsonForm title="DR · security · performance — signed operations" root="/validation/v1" ops={DR_SEC_PERF_SIGNED_OPS} />

          <FormConsole
            title="Exceptions · revalidation (Docs 94, 96)"
            root="/validation/v1"
            ops={[
              { path: "change-impacts", label: "Record a change impact (JSON)" },
              { path: "revalidation-plans", label: "Create a revalidation plan" },
              { path: "revalidations", label: "Record a revalidation" },
              { path: "decommission", label: "Record a decommission decision" },
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
    template: '{\n  "expected_version": 1,\n  "reason": ""\n}',
  },
  {
    label: "Approve a function-risk assessment",
    action: "approve",
    postPath: "function-risks/{assessment_id}/approve",
    challengePath: "function-risks/{assessment_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "reason": "",\n  "residual_risk": null\n}',
  },
];

const TEST_IQ_OQ_SIGNED_OPS: SignedJsonOp[] = [
  {
    label: "Approve a test definition",
    action: "approve",
    postPath: "tests/{test_id}/approve",
    challengePath: "tests/{test_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "reason": ""\n}',
  },
  {
    label: "Complete a test execution",
    action: "complete",
    postPath: "executions/{execution_id}/complete",
    challengePath: "executions/{execution_id}/signature-challenges",
    template:
      '{\n  "expected_version": 1,\n  "actual_result": "",\n  "status": "PASS",\n  "observations": null,\n  "blocked_reason": null,\n  "evidence_manifest": [],\n  "reviewer_user_id": null\n}',
    about: "status is PASS | FAIL | BLOCKED | SKIPPED.",
  },
  {
    label: "Complete an IQ execution",
    action: "complete",
    postPath: "iq/executions/{execution_id}/complete",
    challengePath: "iq/executions/{execution_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "result": "PASS",\n  "evidence_manifest": []\n}',
    about: "result is PASS | FAIL.",
  },
  {
    label: "Approve an IQ execution",
    action: "approve",
    postPath: "iq/executions/{execution_id}/approve",
    challengePath: "iq/executions/{execution_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "reason": ""\n}',
  },
  {
    label: "Approve an OQ execution",
    action: "approve",
    postPath: "oq/{execution_id}/approve",
    challengePath: "oq/{execution_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "reason": ""\n}',
  },
];

const INFRA_SIGNED_OPS: SignedJsonOp[] = [
  {
    label: "Approve an infrastructure fingerprint",
    action: "approve",
    postPath: "infrastructure/{fingerprint_id}/approve",
    challengePath: "infrastructure/{fingerprint_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "reason": ""\n}',
  },
  {
    label: "Approve a Part 11 assessment",
    action: "approve",
    postPath: "part11/{assessment_id}/approve",
    challengePath: "part11/{assessment_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "reason": ""\n}',
  },
  {
    label: "Approve a data-integrity profile",
    action: "approve",
    postPath: "data-integrity/{profile_id}/approve",
    challengePath: "data-integrity/{profile_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "reason": ""\n}',
  },
  {
    label: "Approve an interface profile",
    action: "approve",
    postPath: "interfaces/{profile_id}/approve",
    challengePath: "interfaces/{profile_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "reason": ""\n}',
  },
];

const DR_SEC_PERF_SIGNED_OPS: SignedJsonOp[] = [
  {
    label: "Approve a DR execution",
    action: "approve",
    postPath: "dr/{execution_id}/approve",
    challengePath: "dr/{execution_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "reason": ""\n}',
  },
  {
    label: "Approve a security-qualification suite",
    action: "approve",
    postPath: "security/{suite_id}/approve",
    challengePath: "security/{suite_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "reason": ""\n}',
  },
  {
    label: "Create a performance scenario",
    action: "create",
    postPath: "performance/scenarios",
    challengePath: "performance/scenarios/signature-challenges",
    mergeChallengeField: "new_record_id",
    template:
      '{\n  "release_ref": "",\n  "environment": "",\n  "load_model": {},\n  "planned_duration_seconds": 3600,\n  "thresholds": {}\n}',
    about: "Signed-CREATE (Document 106 rows 159–161) — the challenge pre-generates the scenario id.",
  },
  {
    label: "Record a performance run",
    action: "create",
    postPath: "performance/runs",
    challengePath: "performance/runs/signature-challenges",
    mergeChallengeField: "new_record_id",
    template:
      '{\n  "scenario_id": "",\n  "build_ref": "",\n  "harness_ref": "",\n  "started_at": "",\n  "completed_at": "",\n  "metrics": {}\n}',
    about: "Signed-CREATE (Document 106 row 159) — the challenge pre-generates the run id.",
  },
  {
    label: "Evaluate a performance run",
    action: "evaluate",
    postPath: "performance/{run_id}/evaluate",
    challengePath: "performance/{run_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "headroom_basis_points": null,\n  "bottleneck": null\n}',
  },
];

const EXCEPTION_SIGNED_OPS: SignedJsonOp[] = [
  {
    label: "Raise a validation exception",
    action: "create",
    postPath: "exceptions",
    challengePath: "exceptions/signature-challenges",
    mergeChallengeField: "new_record_id",
    template:
      '{\n  "release_ref": "",\n  "exception_type": "TEST_FAILURE",\n  "source_execution_type": "",\n  "source_execution_id": "",\n  "original_evidence": {},\n  "severity": "HIGH",\n  "requested_by_user_id": ""\n}',
    about: "Signed-CREATE (Document 106 row 162) — signer must be independent of requested_by_user_id.",
  },
  {
    label: "Triage an exception",
    action: "triage",
    postPath: "exceptions/{exception_id}/triage",
    challengePath: "exceptions/{exception_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "severity": "HIGH",\n  "gxp_impact": false,\n  "release_impact": ""\n}',
  },
  {
    label: "Attach a retest plan",
    action: "retest_plan",
    postPath: "exceptions/{exception_id}/retest-plan",
    challengePath: "exceptions/{exception_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "retest_plan": {},\n  "fix_ref": null\n}',
  },
  {
    label: "Disposition an exception",
    action: "disposition",
    postPath: "exceptions/{exception_id}/disposition",
    challengePath: "exceptions/{exception_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "disposition": "",\n  "residual_risk_rationale": null,\n  "reason": ""\n}',
  },
  {
    label: "Create a periodic review",
    action: "create",
    postPath: "periodic-reviews",
    challengePath: "periodic-reviews/signature-challenges",
    mergeChallengeField: "new_record_id",
    template:
      '{\n  "release_ref": "",\n  "period_start": "",\n  "period_end": "",\n  "inputs_considered": {}\n}',
    about: "Signed-CREATE (Document 106 row 170) — the challenge pre-generates the review id.",
  },
  {
    label: "Record a periodic-review decision",
    action: "decision",
    postPath: "periodic-reviews/{review_id}/decision",
    challengePath: "periodic-reviews/{review_id}/signature-challenges",
    template: '{\n  "expected_version": 1,\n  "decision": ""\n}',
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
