"use client";

import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Table } from "@/components/ui/Table";
import { StatePill } from "@/components/ui/StatePill";

// Mirrors app/modules/ai_governance/commands.py (13 functions) + models.py (11 registers).
// The module is fully implemented at the service layer but has no HTTP router yet, so this page is a
// governance reference, not an operable console.

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
];

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

export default function AiGovernancePage() {
  return (
    <div>
      <PageHead
        title="AI governance"
        subtitle="Document 105 (SPEC-AI-001) — the advisory-only AI boundary and its governance registers."
      />

      <Banner tone="info" title="AI is advisory only (AG-14 / AI-FR-003)">
        No AI capability may sign, release, disposition, approve, close a quality record or submit a
        report. AI proposes; a qualified human executes through the normal authorization / signature /
        mutation path. AI unavailability never blocks a regulated workflow (AI-FR-040).
      </Banner>

      <Banner tone="warn" title="No HTTP surface in this build">
        The <code>ai_governance</code> module is implemented at the service layer (13 functions, 11
        registers) but is not yet exposed as REST endpoints, so this page is a governance reference
        rather than an operable console. It will gain interactive views when the backend adds an
        <code> ai_governance</code> router.
      </Banner>

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
