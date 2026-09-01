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
              { path: "master-plans/{plan_id}/release", label: "Release a master plan" },
              { path: "intended-use", label: "Record intended use" },
              { path: "function-risks", label: "Add a function risk assessment" },
              { path: "function-risks/{assessment_id}/approve", label: "Approve a function-risk assessment" },
              { path: "requirements:ingest", label: "Ingest requirements" },
              { path: "trace-links", label: "Add trace links" },
              { path: "baselines", label: "Freeze a baseline" },
            ]}
          />

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
              { path: "tests/{test_id}/approve", label: "Approve a test — needs a signature (JSON)" },
              { path: "executions/{execution_id}/complete", label: "Complete an execution — needs a signature (JSON)" },
              { path: "automated-evidence", label: "Attach automated evidence (JSON)" },
              { path: "iq/protocols", label: "Create an IQ protocol" },
              { path: "iq/executions", label: "Record an IQ execution" },
              { path: "iq/executions/{execution_id}/complete", label: "Complete an IQ execution" },
              { path: "iq/executions/{execution_id}/approve", label: "Approve an IQ execution" },
              { path: "oq:suites", label: "Create an OQ suite" },
              { path: "oq/executions", label: "Record an OQ execution" },
              { path: "oq/{execution_id}/approve", label: "Approve an OQ execution" },
            ]}
          />

          <FormConsole
            title="Infrastructure · Part 11 · data integrity · interfaces (Docs 86, 88–90)"
            root="/validation/v1"
            ops={[
              { path: "infrastructure/profiles", label: "Create an infrastructure profile" },
              { path: "infrastructure/fingerprints", label: "Record an environment fingerprint" },
              { path: "infrastructure/tests", label: "Record an infrastructure control test" },
              { path: "infrastructure/{fingerprint_id}/approve", label: "Approve an infrastructure fingerprint" },
              { path: "part11/assessments", label: "Create a Part 11 assessment" },
              { path: "part11/{assessment_id}/test-suite", label: "Attach a Part 11 test suite" },
              { path: "part11/control-results", label: "Record Part 11 control results" },
              { path: "part11/{assessment_id}/approve", label: "Approve a Part 11 assessment" },
              { path: "data-integrity/suites", label: "Create a data-integrity suite" },
              { path: "data-integrity/tamper-tests", label: "Record a tamper test" },
              { path: "data-integrity/{profile_id}/approve", label: "Approve a data-integrity profile" },
              { path: "interfaces/profiles", label: "Create an interface profile" },
              { path: "interfaces/tests", label: "Record an interface contract test" },
              { path: "interfaces/edge-outage-tests", label: "Record an edge-outage test" },
              { path: "interfaces/{profile_id}/approve", label: "Approve an interface profile" },
            ]}
          />

          <FormConsole
            title="DR · security · performance qualification (Docs 91–93)"
            root="/validation/v1"
            ops={[
              { path: "dr/scenarios", label: "Create a DR scenario" },
              { path: "dr/executions", label: "Record a DR execution" },
              { path: "dr/{execution_id}/measure", label: "Measure RPO/RTO for a DR execution" },
              { path: "dr/{execution_id}/approve", label: "Approve a DR execution" },
              { path: "security/suites", label: "Create a security-qualification suite" },
              { path: "security/tests", label: "Record a security test" },
              { path: "security/findings", label: "Record a security finding" },
              { path: "security/{suite_id}/approve", label: "Approve a security suite" },
              { path: "performance/scenarios", label: "Create a performance scenario" },
              { path: "performance/runs", label: "Record a performance run" },
              { path: "performance/{run_id}/evaluate", label: "Evaluate a performance run vs SLO" },
            ]}
          />

          <FormConsole
            title="Exceptions · revalidation (Docs 94, 96)"
            root="/validation/v1"
            ops={[
              { path: "exceptions", label: "Raise a validation exception — needs a signature (JSON)" },
              { path: "exceptions/{exception_id}/triage", label: "Triage an exception — needs a signature (JSON)" },
              { path: "exceptions/{exception_id}/retest-plan", label: "Attach a retest plan (JSON)" },
              { path: "exceptions/{exception_id}/disposition", label: "Disposition an exception — needs a signature (JSON)" },
              { path: "change-impacts", label: "Record a change impact (JSON)" },
              { path: "revalidation-plans", label: "Create a revalidation plan" },
              { path: "revalidations", label: "Record a revalidation" },
              { path: "periodic-reviews", label: "Create a periodic review" },
              { path: "periodic-reviews/{review_id}/decision", label: "Record a periodic-review decision" },
              { path: "decommission", label: "Record a decommission decision" },
            ]}
          />
        </>
      )}
    </div>
  );
}

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
