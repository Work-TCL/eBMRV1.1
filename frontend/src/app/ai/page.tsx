"use client";

import { useState } from "react";
import { pagedFetcher } from "@/lib/api";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Modal } from "@/components/ui/Modal";
import { Fact, FactGrid } from "@/components/ui/FactGrid";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { FormConsole } from "@/components/shared/FormConsole";
import { SignedJsonForm, type SignedJsonOp } from "@/components/shared/SignedJsonForm";

// Matches app/modules/ai_governance/router.py::_use_case_dict.
interface AiUseCase {
  use_case_id: string;
  name: string;
  use_case_class: string;
  purpose: string;
  decision_impact: string;
  users: string[];
  data_classes: string[];
  state: string;
  retirement_reason: string | null;
  version: number;
}

// Matches app/modules/ai_governance/router.py::_model_deployment_dict.
interface AiModelDeployment {
  model_deployment_id: string;
  use_case_id: string | null;
  provider: string;
  model: string;
  model_version: string;
  deployment_type: string;
  endpoint: string | null;
  context_window: number | null;
  state: string;
  version: number;
}

// Matches app/modules/ai_governance/router.py::_advisory_dict.
interface AiAdvisory {
  advisory_id: string;
  use_case_id: string;
  model_deployment_id: string | null;
  status: string;
  output_hash: string | null;
  output_json: Record<string, unknown> | null;
  created_at: string | null;
}

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

type AiBlockKey = "lifecycle" | "operations" | "signed";

export default function AiGovernancePage() {
  const [openBlock, setOpenBlock] = useState<AiBlockKey | null>(null);
  const [useCasesReload, setUseCasesReload] = useState(0);
  const [deploymentsReload, setDeploymentsReload] = useState(0);
  const [advisoriesReload, setAdvisoriesReload] = useState(0);
  const [viewUseCase, setViewUseCase] = useState<AiUseCase | null>(null);
  const [viewDeployment, setViewDeployment] = useState<AiModelDeployment | null>(null);
  const [viewAdvisory, setViewAdvisory] = useState<AiAdvisory | null>(null);

  // Any of the 3 form blocks can create/change a use case, deployment or advisory - bump every list's
  // reload token on close rather than tracking which op ran, same "refresh on close" compromise used
  // elsewhere this pass for FormConsole/SignedJsonForm (neither exposes a per-op success callback).
  function closeBlock() {
    setOpenBlock(null);
    setUseCasesReload((n) => n + 1);
    setDeploymentsReload((n) => n + 1);
    setAdvisoriesReload((n) => n + 1);
  }

  return (
    <div>
      <PageHead
        title="AI governance"
        subtitle="The advisory-only AI boundary and its operations console."
        action={
          <>
            <Button variant="secondary" size="sm" onClick={() => setOpenBlock("lifecycle")}>
              Use case lifecycle
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setOpenBlock("operations")}>
              Context, advisory &amp; evaluation operations
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setOpenBlock("signed")}>
              <Icon name="pen-line" /> Signed AI governance operations
            </Button>
          </>
        }
      />

        <Banner tone="info" title="AI is advisory only">
        No AI capability may sign, release, disposition, approve, close a quality record or submit a
        report. AI proposes; a qualified human executes through the normal authorization / signature /
        mutation path. AI unavailability never blocks a regulated workflow.
      </Banner>

      <Banner tone="warn" title="5 actions below need a signature policy that hasn't been configured yet">
        Approving an AI model deployment, authorizing an AI tool call, recording a human disposition of AI
        output, evaluating the AI release gate, and switching the AI provider profile all require an
        electronic signature. None of them have a signature policy configured in this deployment yet, so
        each will be correctly refused until Head of Quality and Regulatory Affairs define one - this is
        the same fail-closed behavior every signed action in this system uses when its policy is missing,
        not a defect. Running an AI advisory request or an AI evaluation suite will also fail, because no
        live AI model provider or evaluation harness is connected in this environment.
      </Banner>

      <UseCasesListCard reloadToken={useCasesReload} onOpen={setViewUseCase} />
      <ModelDeploymentsListCard reloadToken={deploymentsReload} onOpen={setViewDeployment} />
      <AdvisoriesListCard reloadToken={advisoriesReload} onOpen={setViewAdvisory} />

      {viewUseCase && (
        <Modal open onClose={() => setViewUseCase(null)} large title={`${viewUseCase.name} - ${viewUseCase.state}`}>
          <FactGrid>
            <Fact label="State"><WorkflowStatePill state={viewUseCase.state} /></Fact>
            <Fact label="Use case class">{viewUseCase.use_case_class}</Fact>
            <Fact label="Users">{viewUseCase.users.join(", ") || "—"}</Fact>
            <Fact label="Data classes">{viewUseCase.data_classes.join(", ") || "—"}</Fact>
            <Fact label="Retirement reason">{viewUseCase.retirement_reason ?? "—"}</Fact>
            <Fact label="Record version">{viewUseCase.version}</Fact>
          </FactGrid>
          <JsonPanel title="Purpose" value={viewUseCase.purpose} />
          <JsonPanel title="Decision impact" value={viewUseCase.decision_impact} />
          <p className="hint mt-3">
            Use &quot;Use case lifecycle&quot; (header) to assess risk, retire or generate a governance
            package against use case ID <span className="tabular">{viewUseCase.use_case_id}</span>.
          </p>
        </Modal>
      )}

      {viewDeployment && (
        <Modal
          open
          onClose={() => setViewDeployment(null)}
          large
          title={`${viewDeployment.provider} / ${viewDeployment.model} - ${viewDeployment.state}`}
        >
          <FactGrid>
            <Fact label="State"><WorkflowStatePill state={viewDeployment.state} /></Fact>
            <Fact label="Model version">{viewDeployment.model_version}</Fact>
            <Fact label="Deployment type">{viewDeployment.deployment_type}</Fact>
            <Fact label="Endpoint">{viewDeployment.endpoint ?? "—"}</Fact>
            <Fact label="Context window">{viewDeployment.context_window ?? "—"}</Fact>
            <Fact label="Record version">{viewDeployment.version}</Fact>
          </FactGrid>
          <p className="hint mt-3">
            Use &quot;Signed AI governance operations&quot; (header) to switch the provider profile
            against model deployment ID <span className="tabular">{viewDeployment.model_deployment_id}</span>.
          </p>
        </Modal>
      )}

      {viewAdvisory && (
        <Modal open onClose={() => setViewAdvisory(null)} large title={`AI advisory - ${viewAdvisory.status}`}>
          <FactGrid>
            <Fact label="Status"><WorkflowStatePill state={viewAdvisory.status} /></Fact>
            <Fact label="Output hash">{viewAdvisory.output_hash ?? "—"}</Fact>
            <Fact label="Created at">{viewAdvisory.created_at ? new Date(viewAdvisory.created_at).toLocaleString() : "—"}</Fact>
          </FactGrid>
          <JsonPanel title="Output" value={viewAdvisory.output_json} />
          <p className="hint mt-3">
            Use &quot;Signed AI governance operations&quot; (header) to record a human disposition
            against advisory ID <span className="tabular">{viewAdvisory.advisory_id}</span>.
          </p>
        </Modal>
      )}

      {openBlock === "lifecycle" && (
        <Modal open onClose={closeBlock} title="Use case lifecycle" large>
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
        </Modal>
      )}

      {openBlock === "operations" && (
        <Modal open onClose={closeBlock} title="Context, advisory & evaluation operations" large>
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
            about: "Will fail closed (no result inserted) - no live AI model provider is configured in this environment.",
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
            about: "Will fail (no live evaluation harness configured) - see module docstring.",
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
        </Modal>
      )}

      {openBlock === "signed" && (
        <Modal open onClose={closeBlock} title="Signed AI governance operations" large>
          <SignedJsonForm
        title="Signed AI governance operations"
        subtitle="Requires a signature not yet configured in this deployment, so each will correctly fail closed until it is."
        root="/ai-governance/v1"
        ops={AI_SIGNED_OPS}
          />
        </Modal>
      )}
    </div>
  );
}

// ---- List cards ----------------------------------------------------------------------------------

function useCaseColumns(onOpen: (uc: AiUseCase) => void): DataTableColumn<AiUseCase>[] {
  return [
    { key: "name", header: "Name", sortable: true, render: (uc) => <span className="fs-2 font-semibold">{uc.name}</span> },
    { key: "use_case_class", header: "Class", render: (uc) => <span className="fs-2">{uc.use_case_class}</span> },
    { key: "state", header: "State", sortable: true, render: (uc) => <WorkflowStatePill state={uc.state} /> },
    {
      key: "open",
      header: "",
      align: "right",
      render: (uc) => (
        <Button size="sm" variant="secondary" onClick={(e) => { e.stopPropagation(); onOpen(uc); }}>
          View
        </Button>
      ),
    },
  ];
}

function UseCasesListCard({ reloadToken, onOpen }: { reloadToken: number; onOpen: (uc: AiUseCase) => void }) {
  const fetchUseCases = pagedFetcher<AiUseCase>("/ai-governance/v1/use-cases");
  return (
    <Card pad className="mb-4">
      <CardHeader title="Use cases" />
      <DataTable
        columns={useCaseColumns(onOpen)}
        fetchPage={fetchUseCases}
        rowKey={(uc) => uc.use_case_id}
        searchPlaceholder="Search name…"
        emptyMessage='No AI use cases yet - use "Use case lifecycle" above to register one.'
        defaultSort={{ by: "created_at", dir: "desc" }}
        onRowClick={onOpen}
        reloadToken={reloadToken}
      />
    </Card>
  );
}

function modelDeploymentColumns(onOpen: (d: AiModelDeployment) => void): DataTableColumn<AiModelDeployment>[] {
  return [
    {
      key: "provider",
      header: "Provider / model",
      sortable: true,
      render: (d) => <span className="fs-2 font-semibold">{d.provider} / {d.model} ({d.model_version})</span>,
    },
    { key: "deployment_type", header: "Deployment type", render: (d) => <span className="fs-2">{d.deployment_type}</span> },
    { key: "state", header: "State", sortable: true, render: (d) => <WorkflowStatePill state={d.state} /> },
    {
      key: "open",
      header: "",
      align: "right",
      render: (d) => (
        <Button size="sm" variant="secondary" onClick={(e) => { e.stopPropagation(); onOpen(d); }}>
          View
        </Button>
      ),
    },
  ];
}

function ModelDeploymentsListCard({ reloadToken, onOpen }: { reloadToken: number; onOpen: (d: AiModelDeployment) => void }) {
  const fetchDeployments = pagedFetcher<AiModelDeployment>("/ai-governance/v1/model-deployments");
  return (
    <Card pad className="mb-4">
      <CardHeader title="Model deployments" />
      <DataTable
        columns={modelDeploymentColumns(onOpen)}
        fetchPage={fetchDeployments}
        rowKey={(d) => d.model_deployment_id}
        searchPlaceholder="Search provider…"
        emptyMessage='No AI model deployments yet - use "Signed AI governance operations" above to approve one.'
        defaultSort={{ by: "created_at", dir: "desc" }}
        onRowClick={onOpen}
        reloadToken={reloadToken}
      />
    </Card>
  );
}

function advisoryColumns(onOpen: (a: AiAdvisory) => void): DataTableColumn<AiAdvisory>[] {
  return [
    { key: "advisory_id", header: "Advisory", render: (a) => <span className="fs-2 font-semibold">AI advisory {a.advisory_id.slice(0, 8)}…</span> },
    { key: "status", header: "Status", sortable: true, render: (a) => <WorkflowStatePill state={a.status} /> },
    {
      key: "created_at",
      header: "Created at",
      sortable: true,
      render: (a) => <span className="tabular fs-2">{a.created_at ? new Date(a.created_at).toLocaleString() : "—"}</span>,
    },
    {
      key: "open",
      header: "",
      align: "right",
      render: (a) => (
        <Button size="sm" variant="secondary" onClick={(e) => { e.stopPropagation(); onOpen(a); }}>
          View
        </Button>
      ),
    },
  ];
}

function AdvisoriesListCard({ reloadToken, onOpen }: { reloadToken: number; onOpen: (a: AiAdvisory) => void }) {
  const fetchAdvisories = pagedFetcher<AiAdvisory>("/ai-governance/v1/advisories");
  return (
    <Card pad className="mb-4">
      <CardHeader title="Advisories" />
      <DataTable
        columns={advisoryColumns(onOpen)}
        fetchPage={fetchAdvisories}
        rowKey={(a) => a.advisory_id}
        searchPlaceholder="Search status…"
        emptyMessage='No AI advisories recorded yet - use "Context, advisory & evaluation operations" above to execute one.'
        defaultSort={{ by: "created_at", dir: "desc" }}
        onRowClick={onOpen}
        reloadToken={reloadToken}
      />
    </Card>
  );
}
