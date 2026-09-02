"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Table } from "@/components/ui/Table";
import { StatePill } from "@/components/ui/StatePill";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { FormConsole } from "@/components/shared/FormConsole";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";

// Mirrors app/modules/ai_governance/commands.py (13 functions) + router.py (24 routes, added 2026-09-01
// -- SG-171). The module has a real HTTP surface now; this page is an operable console, not just a
// reference. The 5 SIGNATURE POLICY LOOKUP REQUIRED functions below will 409 SIGNATURE_POLICY_UNRESOLVED
// on every attempt until Document 106 supplies a SPEC-AI-001 row (SG-167, blocking) -- that is the
// correct, evidenced fail-closed behaviour, not a bug in this page.

const REGISTERS = [
  ["ai_use_case", "AI-FR-001/002 — every AI capability with purpose, users, data, decision impact"],
  ["ai_risk_assessment", "AI-FR-003 — prohibited decisions, failure modes, assurance level"],
  ["ai_model_deployment", "AI-FR-007/021 — provider / model / version / endpoint / context window"],
  ["ai_prompt_version", "AI-FR-008 — system prompts, retrieval instructions, output schemas, versioned"],
  ["ai_tool_registry", "AI-FR-009/010 — allowlisted tools with risk class and scopes; write tools off by default"],
  ["ai_advisory_log", "AI-FR-005/028 — every advisory, its sources, model/prompt version, output hash"],
  ["ai_tool_decision", "AI-FR-009 — each tool-call authorization decision"],
  ["ai_disposition", "AI-FR-005 — the human disposition of each advisory (never auto-applied)"],
  ["ai_evaluation_report", "AI-FR-022/024 — evaluation-set results against acceptance thresholds"],
  ["ai_release_gate", "AI-FR-021 — the model/prompt/tool change gate before production"],
  ["ai_prompt_injection_event", "AI-FR-014/025 — detected prompt-injection / exfiltration attempts"],
] as const;

const FUNCTIONS = [
  ["registerAIUseCase", false],
  ["assessAIUseCaseRisk", false],
  ["approveAIModelDeployment", true],
  ["buildAIRequestContext", false],
  ["executeAIAdvisory", false],
  ["authorizeAIToolCall", true],
  ["recordHumanAIDisposition", true],
  ["runAIEvaluationSuite", false],
  ["evaluateAIReleaseGate", true],
  ["detectPromptInjection", false],
  ["switchAIProviderProfile", true],
  ["retireAIUseCase", false],
  ["generateAIGovernancePackage", false],
] as const;

const USE_CASE_CLASSES = [
  "DEVELOPMENT_ASSISTANT", "DOCUMENT_ASSISTANT", "SEARCH_SUMMARY", "ANALYTICS_ADVISORY",
  "OPERATOR_ADVISORY", "QUALITY_ADVISORY", "REGULATORY_ADVISORY",
];
const DEPLOYMENT_TYPES = ["CLOUD_API", "PRIVATE", "ON_PREM"];
const DISPOSITIONS = ["ACCEPTED_AS_INPUT", "REJECTED", "EDITED", "NOT_USED"];

export default function AiGovernancePage() {
  return (
    <div>
      <PageHead
        title="AI governance"
        subtitle="Document 105 (SPEC-AI-001) — the advisory-only AI boundary, its governance registers, and the operations console."
      />

      <Banner tone="info" title="AI is advisory only (AG-14 / AI-FR-003)">
        No AI capability may sign, release, disposition, approve, close a quality record or submit a
        report. AI proposes; a qualified human executes through the normal authorization / signature /
        mutation path. AI unavailability never blocks a regulated workflow (AI-FR-040).
      </Banner>

      <Banner tone="warn" title="5 signed operations are fail-closed (SG-167, blocking)">
        Document 106 has zero signature-policy rows for AI-governance actions, so
        <code> approveAIModelDeployment</code>, <code>authorizeAIToolCall</code>,
        <code> recordHumanAIDisposition</code>, <code>evaluateAIReleaseGate</code> and
        <code> switchAIProviderProfile</code> below will correctly return
        <code> SIGNATURE_POLICY_UNRESOLVED</code> until Head of Quality + Regulatory Affairs supply those
        rows — this is the same fail-closed behaviour every signed action in this system uses when its
        policy is missing, not a defect. <code>executeAIAdvisory</code> and
        <code> runAIEvaluationSuite</code> will also fail (503 / no result) because no live AI model
        provider or evaluation harness is configured in this environment.
      </Banner>

      <UseCasesCard />
      <ModelDeploymentsCard />
      <AdvisoriesCard />

      <FormConsole
        title="Use case lifecycle"
        root="/ai-governance/v1"
        ops={[
          {
            path: "use-cases",
            label: "Register a use case",
            fields: [
              { name: "name", label: "Name", required: true },
              { name: "use_case_class", label: "Use case class", type: "select", required: true, options: USE_CASE_CLASSES.map((v) => ({ value: v, label: v })) },
              { name: "purpose", label: "Purpose", type: "textarea", required: true },
              { name: "decision_impact", label: "Decision impact", type: "textarea", required: true },
              { name: "users", label: "Users (JSON list)", type: "json", hint: 'e.g. ["QA Reviewer"]' },
              { name: "data_classes", label: "Data classes (JSON list)", type: "json", hint: 'e.g. ["GxP"]' },
              { name: "proposed_tools", label: "Proposed tools (JSON list)", type: "json" },
              { name: "proposed_models", label: "Proposed models (JSON list)", type: "json" },
              { name: "site_id", label: "Site ID" },
              { name: "reason", label: "Reason", required: true },
            ],
          },
          {
            path: "use-cases/{use_case_id}/risk-assessments",
            label: "Assess use case risk",
            fields: [
              { name: "use_case_id", label: "Use case ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true },
              { name: "gxp_impact", label: "GxP impact", type: "textarea", required: true },
              { name: "human_oversight", label: "Human oversight", type: "textarea", required: true },
              { name: "people_impact", label: "People impact", type: "textarea" },
              { name: "data_impact", label: "Data impact", type: "textarea" },
              { name: "security_impact", label: "Security impact", type: "textarea" },
              { name: "failure_modes", label: "Failure modes (JSON list)", type: "json" },
              { name: "prohibited_decisions", label: "Prohibited decisions (JSON list)", type: "json" },
              { name: "evaluation_required", label: "Evaluation required", type: "bool", default: "true" },
              { name: "approval_required", label: "Approval required", type: "bool", default: "true" },
              { name: "reason", label: "Reason", required: true },
            ],
          },
          {
            path: "use-cases/{use_case_id}/retire",
            label: "Retire a use case",
            fields: [
              { name: "use_case_id", label: "Use case ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true },
              { name: "reason", label: "Reason", required: true },
              { name: "replacement", label: "Replacement" },
              { name: "effective_date", label: "Effective date", type: "date" },
            ],
          },
          {
            path: "use-cases/{use_case_id}/governance-package",
            label: "Generate a governance evidence package",
            fields: [
              { name: "use_case_id", label: "Use case ID", required: true },
              { name: "reason", label: "Reason", default: "governance package export" },
            ],
          },
        ]}
      />

      <FormConsole
        title="Context, advisory & evaluation operations"
        root="/ai-governance/v1"
        ops={[
          {
            path: "context-packages",
            label: "Build a request context",
            fields: [
              { name: "use_case_id", label: "Use case ID", required: true },
              { name: "user_query", label: "User query", type: "textarea", required: true },
              { name: "requested_record_refs", label: "Requested record refs (JSON list)", type: "json" },
              { name: "reason", label: "Reason", required: true },
            ],
          },
          {
            path: "advisories",
            label: "Execute an advisory",
            about: "Will fail closed (no result inserted) — no live AI model provider is configured in this environment.",
            fields: [
              { name: "use_case_id", label: "Use case ID", required: true },
              { name: "model_deployment_id", label: "Model deployment ID", required: true },
              { name: "prompt_version_id", label: "Prompt version ID" },
              { name: "context_ref", label: "Context ref (JSON)", type: "json" },
              { name: "output_schema", label: "Output schema (JSON)", type: "json" },
              { name: "reason", label: "Reason", required: true },
            ],
          },
          {
            path: "evaluation-reports",
            label: "Run an evaluation suite",
            about: "Will fail (no live evaluation harness configured) — see module docstring.",
            fields: [
              { name: "use_case_id", label: "Use case ID", required: true },
              { name: "dataset_ref", label: "Dataset ref", required: true },
              { name: "model_deployment_id", label: "Model deployment ID" },
              { name: "prompt_version_id", label: "Prompt version ID" },
              { name: "scenario_classes", label: "Scenario classes (JSON list)", type: "json" },
              { name: "critical_thresholds_bp", label: "Critical thresholds, basis points (JSON)", type: "json" },
              { name: "reason", label: "Reason", required: true },
            ],
          },
          {
            path: "injection-screens",
            label: "Screen content for prompt injection",
            fields: [
              { name: "use_case_id", label: "Use case ID", required: true },
              { name: "content", label: "Content", type: "textarea", required: true },
              { name: "block_on_detect", label: "Block on detect", type: "bool", default: "true" },
              { name: "reason", label: "Reason", default: "automated content screen" },
            ],
          },
        ]}
      />

      <SignedForm
        title="Approve an AI model deployment"
        subtitle="SIGNED (SG-167) — approveAIModelDeployment(), AI-FR-007/012/013/047."
        postPath="/ai-governance/v1/model-deployments"
        challengePath="/ai-governance/v1/model-deployments/signature-challenges"
        fields={[
          { name: "provider", label: "Provider", required: true },
          { name: "model", label: "Model", required: true },
          { name: "model_version", label: "Model version", required: true },
          { name: "deployment_type", label: "Deployment type", type: "select", required: true, options: DEPLOYMENT_TYPES },
          { name: "use_case_id", label: "Use case ID" },
          { name: "endpoint", label: "Endpoint" },
          { name: "context_window", label: "Context window", type: "number" },
          { name: "data_terms", label: "Data terms (JSON)", type: "json" },
          { name: "evaluation_report_id", label: "Evaluation report ID" },
          { name: "reason", label: "Reason", required: true },
        ]}
      />

      <SignedForm
        title="Authorize an AI tool call"
        subtitle="SIGNED (SG-167) — authorizeAIToolCall(), AI-FR-003/004/009/010."
        postPath="/ai-governance/v1/tool-decisions"
        challengePath="/ai-governance/v1/tool-decisions/signature-challenges"
        fields={[
          { name: "use_case_id", label: "Use case ID", required: true },
          { name: "tool_name", label: "Tool name", required: true },
          { name: "args", label: "Args (JSON)", type: "json" },
          { name: "advisory_id", label: "Advisory ID" },
          { name: "reason", label: "Reason", required: true },
        ]}
      />

      <SignedForm
        title="Record a human disposition of an AI advisory"
        subtitle="SIGNED (SG-167) — recordHumanAIDisposition(), AI-FR-005/034."
        postPath="/ai-governance/v1/dispositions"
        challengePath="/ai-governance/v1/dispositions/signature-challenges"
        fields={[
          { name: "advisory_id", label: "Advisory ID", required: true },
          { name: "disposition", label: "Disposition", type: "select", required: true, options: DISPOSITIONS },
          { name: "comments", label: "Comments", type: "textarea" },
          { name: "downstream_record_ref", label: "Downstream record ref" },
          { name: "reason", label: "Reason", required: true },
        ]}
      />

      <SignedForm
        title="Evaluate the AI release gate"
        subtitle="SIGNED (SG-167) — evaluateAIReleaseGate(), AI-FR-021/024."
        postPath="/ai-governance/v1/release-gates"
        challengePath="/ai-governance/v1/release-gates/signature-challenges"
        fields={[
          { name: "use_case_id", label: "Use case ID", required: true },
          { name: "evaluation_report_id", label: "Evaluation report ID", required: true },
          { name: "incidents_ref", label: "Incidents ref (JSON list)", type: "json" },
          { name: "vendor_security_status", label: "Vendor security status", type: "textarea" },
          { name: "reason", label: "Reason", required: true },
        ]}
      />

      <SignedForm
        title="Switch AI provider / model profile"
        subtitle="SIGNED (SG-167) — switchAIProviderProfile()."
        postPath="/ai-governance/v1/provider-switches"
        challengePath="/ai-governance/v1/provider-switches/signature-challenges"
        fields={[
          { name: "use_case_id", label: "Use case ID", required: true },
          { name: "to_model_deployment_id", label: "To model deployment ID", required: true },
          { name: "from_model_deployment_id", label: "From model deployment ID" },
          { name: "reason", label: "Reason", required: true },
        ]}
      />

      <Card className="mb-4">
        <CardHeader title="Governance registers" />
        <Table>
          <thead>
            <tr>
              <th>Register</th>
              <th>Purpose</th>
            </tr>
          </thead>
          <tbody>
            {REGISTERS.map(([name, purpose]) => (
              <tr key={name}>
                <td className="tabular font-semibold">{name}</td>
                <td className="fs-2">{purpose}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card>
        <CardHeader title="Governance functions" />
        <Table>
          <thead>
            <tr>
              <th>Function</th>
              <th>Signature</th>
            </tr>
          </thead>
          <tbody>
            {FUNCTIONS.map(([name, signed]) => (
              <tr key={name}>
                <td className="tabular">{name}</td>
                <td>
                  {signed ? (
                    <StatePill state="conflict" icon="pen-line">
                      Signature policy lookup (SG-167)
                    </StatePill>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  );
}

// ---- Read cards --------------------------------------------------------------------------------

function UseCasesCard() {
  const [id, setId] = useState("");
  const [state, setState] = useState("");
  const [result, setResult] = useState<unknown>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(path: string) {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.get<unknown>(path));
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Use cases" />
      <div className="grid grid-cols-3 gap-4 mb-3">
        <Field label="Use case ID (for lookup)">
          <Input value={id} onChange={(e) => setId(e.target.value)} placeholder="uuid" />
        </Field>
        <Field label="State filter (for list)" hint="DRAFT / RISK_ASSESSED / ACTIVE / RETIRED">
          <Input value={state} onChange={(e) => setState(e.target.value)} />
        </Field>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" disabled={busy} onClick={() => run(`/ai-governance/v1/use-cases${state ? `?state=${encodeURIComponent(state)}` : ""}`)}>
          <Icon name="list-checks" /> List use cases
        </Button>
        <Button variant="secondary" disabled={busy || !id.trim()} onClick={() => run(`/ai-governance/v1/use-cases/${encodeURIComponent(id.trim())}`)}>
          <Icon name="search" /> Look up by ID
        </Button>
      </div>
      {error && <p className="error-text mt-2">{error}</p>}
      {result !== undefined && (
        <div className="mt-3">
          <JsonPanel title="Result" value={result} />
        </div>
      )}
    </Card>
  );
}

function ModelDeploymentsCard() {
  const [id, setId] = useState("");
  const [useCaseId, setUseCaseId] = useState("");
  const [result, setResult] = useState<unknown>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(path: string) {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.get<unknown>(path));
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Model deployments" />
      <div className="grid grid-cols-3 gap-4 mb-3">
        <Field label="Model deployment ID (for lookup)">
          <Input value={id} onChange={(e) => setId(e.target.value)} placeholder="uuid" />
        </Field>
        <Field label="Use case ID filter (for list)">
          <Input value={useCaseId} onChange={(e) => setUseCaseId(e.target.value)} placeholder="uuid" />
        </Field>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" disabled={busy} onClick={() => run(`/ai-governance/v1/model-deployments${useCaseId ? `?use_case_id=${encodeURIComponent(useCaseId.trim())}` : ""}`)}>
          <Icon name="list-checks" /> List model deployments
        </Button>
        <Button variant="secondary" disabled={busy || !id.trim()} onClick={() => run(`/ai-governance/v1/model-deployments/${encodeURIComponent(id.trim())}`)}>
          <Icon name="search" /> Look up by ID
        </Button>
      </div>
      {error && <p className="error-text mt-2">{error}</p>}
      {result !== undefined && (
        <div className="mt-3">
          <JsonPanel title="Result" value={result} />
        </div>
      )}
    </Card>
  );
}

function AdvisoriesCard() {
  const [id, setId] = useState("");
  const [useCaseId, setUseCaseId] = useState("");
  const [result, setResult] = useState<unknown>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(path: string) {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.get<unknown>(path));
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Advisories" />
      <div className="grid grid-cols-3 gap-4 mb-3">
        <Field label="Advisory ID (for lookup)">
          <Input value={id} onChange={(e) => setId(e.target.value)} placeholder="uuid" />
        </Field>
        <Field label="Use case ID filter (for list)">
          <Input value={useCaseId} onChange={(e) => setUseCaseId(e.target.value)} placeholder="uuid" />
        </Field>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" disabled={busy} onClick={() => run(`/ai-governance/v1/advisories${useCaseId ? `?use_case_id=${encodeURIComponent(useCaseId.trim())}` : ""}`)}>
          <Icon name="list-checks" /> List advisories
        </Button>
        <Button variant="secondary" disabled={busy || !id.trim()} onClick={() => run(`/ai-governance/v1/advisories/${encodeURIComponent(id.trim())}`)}>
          <Icon name="search" /> Look up by ID
        </Button>
      </div>
      {error && <p className="error-text mt-2">{error}</p>}
      {result !== undefined && (
        <div className="mt-3">
          <JsonPanel title="Result" value={result} />
        </div>
      )}
    </Card>
  );
}

// ---- Signed operation form ---------------------------------------------------------------------

interface SignedField {
  name: string;
  label: string;
  type?: "text" | "number" | "textarea" | "json" | "select" | "bool";
  required?: boolean;
  hint?: string;
  options?: string[];
}

function coerceSigned(field: SignedField, raw: string): unknown {
  const v = raw.trim();
  if (v === "") return field.required ? "" : null;
  switch (field.type) {
    case "number":
      return Number(v);
    case "bool":
      return v === "true";
    case "json":
      return JSON.parse(v);
    default:
      return v;
  }
}

/** A signed-mutation form: fill typed fields, request a signature challenge bound to the exact field
 * values shown, sign, submit. `challengePath`'s endpoint expects the same field set the mutation body
 * does (minus the transport fields the ceremony adds) — see
 * `app/modules/ai_governance/router.py`'s `*ChallengeBody` models. */
function SignedForm({
  title,
  subtitle,
  postPath,
  challengePath,
  fields,
}: {
  title: string;
  subtitle?: string;
  postPath: string;
  challengePath: string;
  fields: SignedField[];
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [open, setOpen] = useState(false);
  const [buildError, setBuildError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(undefined);
  // Snapshotted at "Request signature" time so the modal (and its challengeBody, which the challenge
  // is content-hash-bound to) renders from a fixed value rather than re-reading `values` on every render.
  const [pendingBody, setPendingBody] = useState<Record<string, unknown> | null>(null);

  function buildBody(): Record<string, unknown> | null {
    try {
      const body: Record<string, unknown> = {};
      for (const f of fields) {
        const c = coerceSigned(f, values[f.name] ?? "");
        if (c !== null) body[f.name] = c;
      }
      setBuildError(null);
      return body;
    } catch (err) {
      setBuildError(err instanceof Error ? `Invalid input: ${err.message}` : "Invalid input");
      return null;
    }
  }

  const missingRequired = fields.some((f) => f.required && !(values[f.name] ?? "").trim());

  return (
    <Card pad className="mb-4">
      <CardHeader title={title} />
      {subtitle && <p className="fs-2 text-muted mb-3">{subtitle}</p>}
      <div className="grid grid-cols-2 gap-4">
        {fields.map((f) => (
          <Field key={f.name} label={f.label} required={f.required} hint={f.hint}>
            {f.type === "select" ? (
              <Select value={values[f.name] ?? ""} onChange={(e) => setValues((c) => ({ ...c, [f.name]: e.target.value }))}>
                <option value="">—</option>
                {(f.options ?? []).map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </Select>
            ) : f.type === "bool" ? (
              <Select value={values[f.name] ?? ""} onChange={(e) => setValues((c) => ({ ...c, [f.name]: e.target.value }))}>
                <option value="">—</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </Select>
            ) : f.type === "textarea" || f.type === "json" ? (
              <textarea
                className="input"
                rows={f.type === "json" ? 3 : 2}
                value={values[f.name] ?? ""}
                onChange={(e) => setValues((c) => ({ ...c, [f.name]: e.target.value }))}
                placeholder={f.type === "json" ? "{ } or [ ]" : undefined}
                spellCheck={false}
              />
            ) : (
              <Input
                type={f.type === "number" ? "number" : "text"}
                value={values[f.name] ?? ""}
                onChange={(e) => setValues((c) => ({ ...c, [f.name]: e.target.value }))}
              />
            )}
          </Field>
        ))}
      </div>
      {buildError && <p className="error-text mt-2">{buildError}</p>}
      <Button
        type="button"
        variant="primary"
        className="mt-3"
        disabled={missingRequired}
        onClick={() => {
          const built = buildBody();
          if (built) {
            setPendingBody(built);
            setOpen(true);
          }
        }}
      >
        <Icon name="pen-line" /> Request signature &amp; submit
      </Button>
      {result !== undefined && (
        <div className="mt-3">
          <JsonPanel title="Response" value={result} />
        </div>
      )}

      {open && pendingBody && (
        <SignatureCeremony
          open={open}
          onClose={() => setOpen(false)}
          onDone={() => setOpen(false)}
          challengePath={challengePath}
          action={title}
          challengeBody={pendingBody}
          title={title}
          summary={
            <>
              You are about to sign <strong>{title.toLowerCase()}</strong> with exactly the field values
              entered above. The challenge is bound to those values — changing a field after requesting the
              challenge invalidates it.
            </>
          }
          reason="none"
          onSign={async (payload) => {
            const receipt = await api.post<unknown>(postPath, {
              idempotency_key: payload.idempotency_key,
              ...pendingBody,
              challenge_id: payload.challenge_id,
              reauth_password: payload.reauth_password,
            });
            setResult(receipt);
            return receipt;
          }}
        />
      )}
    </Card>
  );
}
