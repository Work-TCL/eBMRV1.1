"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { FormConsole } from "@/components/shared/FormConsole";
import { SignedJsonForm, type SignedJsonOp } from "@/components/shared/SignedJsonForm";

// Mirrors app/modules/ai_governance/commands.py (13 functions) + router.py (24 routes, added 2026-09-01
// -- SG-171). The module has a real HTTP surface now; this page is an operable console, not just a
// reference. The 5 SIGNATURE POLICY LOOKUP REQUIRED functions below will 409 SIGNATURE_POLICY_UNRESOLVED
// on every attempt until Document 106 supplies a SPEC-AI-001 row (SG-167, blocking) -- that is the
// correct, evidenced fail-closed behaviour, not a bug in this page.

const USE_CASE_CLASSES = [
  "DEVELOPMENT_ASSISTANT", "DOCUMENT_ASSISTANT", "SEARCH_SUMMARY", "ANALYTICS_ADVISORY",
  "OPERATOR_ADVISORY", "QUALITY_ADVISORY", "REGULATORY_ADVISORY",
];
const DEPLOYMENT_TYPES = ["CLOUD_API", "PRIVATE", "ON_PREM"];
const DISPOSITIONS = ["ACCEPTED_AS_INPUT", "REJECTED", "EDITED", "NOT_USED"];

// Each op's challenge endpoint mirrors the mutation body exactly (router.py's `*ChallengeBody` models,
// content-hash-bound per SG-167) rather than a bare `{ action }`, and the policy lookup's `action` string
// is hardcoded server-side per route — so `action` here is a label only, not read by these endpoints.
const AI_SIGNED_OPS: SignedJsonOp[] = [
  {
    label: "Approve an AI model deployment",
    action: "approve",
    postPath: "model-deployments",
    challengePath: "model-deployments/signature-challenges",
    mirrorBodyInChallenge: true,
    fields: [
      { name: "provider", label: "Provider", required: true },
      { name: "model", label: "Model", required: true },
      { name: "model_version", label: "Model version", required: true },
      { name: "deployment_type", label: "Deployment type", type: "select", required: true, options: DEPLOYMENT_TYPES.map((v) => ({ value: v, label: v })) },
      { name: "use_case_id", label: "Use case ID" },
      { name: "endpoint", label: "Endpoint" },
      { name: "context_window", label: "Context window", type: "number" },
      { name: "data_terms", label: "Data terms", type: "kv" },
      { name: "evaluation_report_id", label: "Evaluation report ID" },
      { name: "reason", label: "Reason", required: true },
    ],
  },
  {
    label: "Authorize an AI tool call",
    action: "authorize",
    postPath: "tool-decisions",
    challengePath: "tool-decisions/signature-challenges",
    mirrorBodyInChallenge: true,
    fields: [
      { name: "use_case_id", label: "Use case ID", required: true },
      { name: "tool_name", label: "Tool name", required: true },
      { name: "args", label: "Arguments", type: "kv" },
      { name: "advisory_id", label: "Advisory ID" },
      { name: "reason", label: "Reason", required: true },
    ],
  },
  {
    label: "Record a human disposition of an AI advisory",
    action: "record",
    postPath: "dispositions",
    challengePath: "dispositions/signature-challenges",
    mirrorBodyInChallenge: true,
    fields: [
      { name: "advisory_id", label: "Advisory ID", required: true },
      { name: "disposition", label: "Disposition", type: "select", required: true, options: DISPOSITIONS.map((v) => ({ value: v, label: v })) },
      { name: "comments", label: "Comments", type: "textarea" },
      { name: "downstream_record_ref", label: "Downstream record ref" },
      { name: "reason", label: "Reason", required: true },
    ],
  },
  {
    label: "Evaluate the AI release gate",
    action: "evaluate",
    postPath: "release-gates",
    challengePath: "release-gates/signature-challenges",
    mirrorBodyInChallenge: true,
    fields: [
      { name: "use_case_id", label: "Use case ID", required: true },
      { name: "evaluation_report_id", label: "Evaluation report ID", required: true },
      { name: "incidents_ref", label: "Incident references", type: "stringList", itemLabel: "Incident" },
      { name: "vendor_security_status", label: "Vendor security status", type: "textarea" },
      { name: "reason", label: "Reason", required: true },
    ],
  },
  {
    label: "Switch AI provider / model profile",
    action: "switch",
    postPath: "provider-switches",
    challengePath: "provider-switches/signature-challenges",
    mirrorBodyInChallenge: true,
    fields: [
      { name: "use_case_id", label: "Use case ID", required: true },
      { name: "to_model_deployment_id", label: "To model deployment ID", required: true },
      { name: "from_model_deployment_id", label: "From model deployment ID" },
      { name: "reason", label: "Reason", required: true },
    ],
  },
];

export default function AiGovernancePage() {
  return (
    <div>
      <PageHead
        title="AI governance"
        subtitle="The advisory-only AI boundary and its operations console."
      />

      <Banner tone="info" title="AI is advisory only (AG-14 / AI-FR-003)">
        No AI capability may sign, release, disposition, approve, close a quality record or submit a
        report. AI proposes; a qualified human executes through the normal authorization / signature /
        mutation path. AI unavailability never blocks a regulated workflow (AI-FR-040).
      </Banner>

      <Banner tone="warn" title="5 actions below need a signature policy that hasn't been configured yet">
        Approving an AI model deployment, authorizing an AI tool call, recording a human disposition of AI
        output, evaluating the AI release gate, and switching the AI provider profile all require an
        electronic signature. None of them have a signature policy configured in this deployment yet, so
        each will be correctly refused until Head of Quality and Regulatory Affairs define one — this is
        the same fail-closed behavior every signed action in this system uses when its policy is missing,
        not a defect. Running an AI advisory request or an AI evaluation suite will also fail, because no
        live AI model provider or evaluation harness is connected in this environment.
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
              { name: "users", label: "Users", type: "stringList", itemLabel: "User / role", placeholder: "e.g. QA Reviewer" },
              { name: "data_classes", label: "Data classes", type: "stringList", itemLabel: "Data class", placeholder: "e.g. GxP" },
              { name: "proposed_tools", label: "Proposed tools", type: "stringList", itemLabel: "Tool" },
              { name: "proposed_models", label: "Proposed models", type: "stringList", itemLabel: "Model" },
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
              { name: "failure_modes", label: "Failure modes", type: "stringList", itemLabel: "Failure mode" },
              { name: "prohibited_decisions", label: "Prohibited decisions", type: "stringList", itemLabel: "Decision" },
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
              { name: "requested_record_refs", label: "Requested record references", type: "stringList", itemLabel: "Reference" },
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
              { name: "context_ref", label: "Context reference", type: "kv" },
              { name: "output_schema", label: "Output schema", type: "kv" },
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
              { name: "scenario_classes", label: "Scenario classes", type: "stringList", itemLabel: "Class" },
              { name: "critical_thresholds_bp", label: "Critical thresholds (basis points)", type: "kv" },
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

      <SignedJsonForm
        title="Signed AI governance operations"
 subtitle="Requires a signature not yet configured in this deployment, so each will correctly fail closed until it is."
        root="/ai-governance/v1"
        ops={AI_SIGNED_OPS}
      />

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
