# AI Governance for Regulated Manufacturing

**Derived from:** Document 105 (SPEC-AI-001) — controlled source in `specs/`
**Purpose:** AI authority boundary and required controls.
**Requirements:** AI-FR-001..056 (56)

> This file is the working engineering standard. The controlled source is Document 105; where the two
> differ, the specification wins and this file is corrected.

## Requirements

| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| AI-FR-001 | AI use-case registry | Every AI capability—product or engineering—registered with purpose, users, data, model, tools and decision impact. | Inventory. |
| AI-FR-002 | Use-case class | Classify DEVELOPMENT_ASSISTANT, DOCUMENT_ASSISTANT, SEARCH_SUMMARY, ANALYTICS_ADVISORY, OPERATOR_ADVISORY, QUALITY_ADVISORY, REGULATORY_ADVISORY or future approved class. | Governance. |
| AI-FR-003 | Regulated decision boundary | AI cannot autonomously release/disposition product, sign, approve deviation/CAPA, change specification, accept OOS, alter audit, determine legal reportability or issue regulatory submission. | Human authority. |
| AI-FR-004 | No hidden GxP write | AI tools cannot write GxP state directly; any proposed action goes through normal UI/API/authorization/signature and human review. | Architecture. |
| AI-FR-005 | Human review | AI output used in regulated workflow clearly marked advisory and requires authorized human verification before reliance/action. | Oversight. |
| AI-FR-006 | No signature delegation | AI/service identity cannot apply a human electronic signature or respond to signature challenge. | Part 11. |
| AI-FR-007 | Model registry | Track provider/model/version/deployment/endpoint/hash where applicable, context window, capability and effective dates. | Reproducibility. |
| AI-FR-008 | Prompt/template version | System prompts, retrieval instructions, tool policies and output schemas versioned/released. | Behavior control. |
| AI-FR-009 | Tool registry | AI tool/function calls explicitly allowlisted with read/write risk class and scopes. | Agent safety. |
| AI-FR-010 | Write tools disabled by default | Production AI receives read-only tools by default; any non-GxP write needs explicit low-risk approval and normal authorization. | Least privilege. |
| AI-FR-011 | Data classification | Inputs/retrieval sources classified GxP, PII, confidential, security, public; provider use permitted only by policy. | Data protection. |
| AI-FR-012 | Provider data terms | Record whether provider may retain/train on data, region, subprocessors, enterprise privacy controls and contract. | Vendor governance. |
| AI-FR-013 | On-prem/private AI profile | Support local/private model path for customers that prohibit external API data transfer. | Deployment flexibility. |
| AI-FR-014 | Prompt injection defense | Retrieved documents, complaints, emails, web/API data and user text are untrusted content and cannot redefine system/tool policy. | Agent security. |
| AI-FR-015 | Retrieval provenance | Advisory answer cites/references retrieved source documents/record versions where factual support matters. | Grounding. |
| AI-FR-016 | Source authority | AI must distinguish authoritative GxP record from projections, draft docs, external web and user narrative. | Data integrity. |
| AI-FR-017 | Freshness | AI response displays/records source cutoff/version when stale data could matter. | Transparency. |
| AI-FR-018 | Hallucination handling | When evidence insufficient/contradictory, output uncertainty or 'insufficient evidence' rather than fabricate regulated fact. | Trustworthiness. |
| AI-FR-019 | Structured outputs | High-risk advisory extraction/classification uses validated JSON/schema output and server validation. | Reliability. |
| AI-FR-020 | Determinism settings | Temperature/randomness/tool settings versioned by use case; regulated advisory favors constrained reproducibility where useful. | Repeatability. |
| AI-FR-021 | Model change control | Model/provider/version/prompt/retrieval/tool change receives risk/change/validation impact before production. | Validated state. |
| AI-FR-022 | Evaluation set | Each regulated-advisory use case has versioned representative evaluation dataset/scenarios. | TEVV. |
| AI-FR-023 | Evaluation dimensions | Evaluate factuality/grounding, extraction accuracy, refusal/uncertainty, tool safety, prompt injection, bias where relevant, latency/cost and robustness. | Assurance. |
| AI-FR-024 | Acceptance thresholds | Thresholds/risk tolerances defined per use case; overall average cannot hide critical failure class. | Risk based. |
| AI-FR-025 | Adversarial tests | Test prompt injection, data exfiltration, unsafe tool calls, cross-tenant retrieval, malformed context and jailbreak attempts. | Security. |
| AI-FR-026 | Human factors | Evaluate over-reliance/automation bias and ensure UI wording does not imply AI approval/authority. | Usability. |
| AI-FR-027 | Output labeling | UI clearly identifies AI-generated/advisory content and relevant source/evidence links. | Transparency. |
| AI-FR-028 | AI audit log | Record use-case ID, model/version, prompt/template version, retrieval refs, tool calls, output hash, user, timestamp and human disposition as appropriate. | Traceability. |
| AI-FR-029 | Prompt privacy | Do not log secrets/full sensitive prompts unnecessarily; store protected/redacted evidence according to risk. | Privacy. |
| AI-FR-030 | Token/data minimization | Send minimum necessary data to model; avoid full batch/complaint/personnel record when narrower context suffices. | Data minimization. |
| AI-FR-031 | Tenant isolation | Retrieval/tool execution bound tenant/site/role before model context assembly. | Isolation. |
| AI-FR-032 | No security secret reasoning | AI does not receive private keys/passwords/tokens or raw secrets as context. | Security. |
| AI-FR-033 | Incident handling | Material AI unsafe output/data leak/tool misuse creates security/quality incident as applicable. | Response. |
| AI-FR-034 | User feedback | Incorrect AI suggestion can be flagged and linked evaluation/improvement without rewriting historical output. | Learning governance. |
| AI-FR-035 | Monitoring | Track model errors, groundedness proxies, refusal rates, tool denials, latency, cost, drift and user override/acceptance rates where meaningful. | Operations. |
| AI-FR-036 | No online self-learning | Production AI does not autonomously retrain/update policy from user interactions in regulated use. | Change control. |
| AI-FR-037 | Training data governance | If custom model/fine-tune is introduced, dataset provenance, rights, deidentification, splits, leakage and versioning mandatory. | Model governance. |
| AI-FR-038 | Bias/applicability | Where AI affects people/safety prioritization, evaluate representativeness/bias/applicability relevant to use case. | Trustworthiness. |
| AI-FR-039 | Explainability | Provide source/rationale features appropriate to advisory use; do not fabricate chain-of-thought. | Usable explanation. |
| AI-FR-040 | AI availability | AI outage must not block core regulated manufacturing unless a separately validated process explicitly depends on it; manual/non-AI path exists. | Business continuity. |
| AI-FR-041 | Fallback behavior | On timeout/model refusal/output schema failure, no guessed result is inserted; user receives explicit unavailable/needs-review state. | Fail closed. |
| AI-FR-042 | Development-agent governance | Claude Code/Codex governed by Document98 and cannot self-approve code/release/validation evidence. | Engineering AI. |
| AI-FR-043 | Generated code review | AI-generated code undergoes same code/security/license/test review as human code. | Equal standard. |
| AI-FR-044 | Copyright/IP review | AI-generated code/content evaluated under company IP policy; model/provider terms recorded. | Acquisition readiness. |
| AI-FR-045 | External AI API contract | Provider endpoints isolated behind AI Gateway abstraction so provider/model can change without domain rewrite. | Portability. |
| AI-FR-046 | AI Gateway | Central service enforces provider routing, data policy, model allowlist, prompts, tools, quotas, logging/redaction and evaluation hooks. | Control point. |
| AI-FR-047 | Model allowlist | Only approved model/provider/deployment versions usable in production; arbitrary user-selected model prohibited for regulated advisory. | Controlled behavior. |
| AI-FR-048 | Cost/resource limits | Per use-case token/tool/time limits prevent runaway agent behavior/DoS/cost. | Operational safety. |
| AI-FR-049 | FDA-specific future device AI | If future AI becomes an AI-enabled device software function, initiate separate regulatory/product-lifecycle assessment; generic advisory approval does not cover it. | Scope control. |
| AI-FR-050 | NIST mapping | Use NIST AI RMF 1.0/Generative AI Profile as voluntary governance mapping; track revisions without treating framework as law. | Current governance. |
| AI-FR-051 | Regulatory guidance status | Draft/final FDA AI guidance status stored with any future applicable regulatory mapping; draft recommendations not hardcoded as binding requirements. | Correct interpretation. |
| AI-FR-052 | Periodic review | AI use cases/models/prompts/tools/evaluations/incidents/vendor terms reviewed periodically and on material change. | Lifecycle. |
| AI-FR-053 | Retirement | AI model/use case can be disabled/retired with historical logs/evidence retained. | Lifecycle. |
| AI-FR-054 | Customer control | Customer can disable optional AI features and configure approved provider/private model profile without impacting core GxP execution. | Commercial fit. |
| AI-FR-055 | No AI compliance claims | Marketing/product UI cannot claim AI makes system FDA-compliant or replaces QA/regulatory judgement. | Truthfulness. |
| AI-FR-056 | Evidence honesty | AI may summarize validation/compliance evidence but cannot mark evidence/test as executed unless real execution record exists. | Validation integrity. |

## Enforcement

See `docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md`,
`docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md` and `.github/workflows/ci.yml`.

## Tests

- AI attempts QA release tool denied
- prompt injection in retrieved SOP cannot change policy
- cross-tenant RAG denied
- model version change requires evaluation
- invalid structured output
- AI hallucinated lot rejected by groundedness test
- provider outage core workflow remains
- human rejects advisory but original retained
- development agent cannot fabricate CI evidence
