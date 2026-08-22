# AI governance

**Purpose:** AI governance for the eBMR/eDHR platform.
**Applicable paths/modules:** see `docs/generated/17_REPOSITORY_STRUCTURE.md`; this rule applies to every
service, the Frappe app, edge and integration code unless a narrower scope is stated below.
**Source documents:** Document 105 (SPEC-AI-001)
**Source requirement IDs:** AI-FR-001..056 (56)

---

## Required implementation pattern

AI is advisory. It may summarise, extract, search, cluster and draft. Every AI use case is registered in
`docs/generated/41_AI_GOVERNANCE_REGISTER.md` with model/prompt/tool versions, retrieval sources,
evaluation set, acceptance thresholds, security tests and fallback behaviour. Retrieval is restricted to
authoritative sources filtered by the caller's own access rights.

## Forbidden patterns

- AI signing, releasing, dispositioning, approving, closing a quality record or submitting a report
- AI writing regulated state directly (any write goes through human authorization + the Mutation Gateway)
- AI output presented as authoritative without a source reference
- unpinned model or prompt version
- AI unavailability blocking a regulated workflow

## Required tests

prompt injection; data exfiltration; authorization bypass through retrieval; tool misuse; authority-boundary
negative tests; evaluation set against acceptance thresholds; fallback path with AI disabled.


## Source requirements (extract)

| ID | Requirement | Required behaviour |
|---|---|---|
| AI-FR-001 | AI use-case registry | Every AI capability—product or engineering—registered with purpose, users, data, model, tools and decision impact. |
| AI-FR-002 | Use-case class | Classify DEVELOPMENT_ASSISTANT, DOCUMENT_ASSISTANT, SEARCH_SUMMARY, ANALYTICS_ADVISORY, OPERATOR_ADVISORY, QUALITY_ADVISORY, REGULATORY_ADVISORY or future approved class. |
| AI-FR-003 | Regulated decision boundary | AI cannot autonomously release/disposition product, sign, approve deviation/CAPA, change specification, accept OOS, alter audit, determine legal reportability or issue regulatory submission. |
| AI-FR-004 | No hidden GxP write | AI tools cannot write GxP state directly; any proposed action goes through normal UI/API/authorization/signature and human review. |
| AI-FR-005 | Human review | AI output used in regulated workflow clearly marked advisory and requires authorized human verification before reliance/action. |
| AI-FR-006 | No signature delegation | AI/service identity cannot apply a human electronic signature or respond to signature challenge. |
| AI-FR-007 | Model registry | Track provider/model/version/deployment/endpoint/hash where applicable, context window, capability and effective dates. |
| AI-FR-008 | Prompt/template version | System prompts, retrieval instructions, tool policies and output schemas versioned/released. |
| AI-FR-009 | Tool registry | AI tool/function calls explicitly allowlisted with read/write risk class and scopes. |
| AI-FR-010 | Write tools disabled by default | Production AI receives read-only tools by default; any non-GxP write needs explicit low-risk approval and normal authorization. |
| AI-FR-011 | Data classification | Inputs/retrieval sources classified GxP, PII, confidential, security, public; provider use permitted only by policy. |
| AI-FR-012 | Provider data terms | Record whether provider may retain/train on data, region, subprocessors, enterprise privacy controls and contract. |
| AI-FR-013 | On-prem/private AI profile | Support local/private model path for customers that prohibit external API data transfer. |
| AI-FR-014 | Prompt injection defense | Retrieved documents, complaints, emails, web/API data and user text are untrusted content and cannot redefine system/tool policy. |
| AI-FR-015 | Retrieval provenance | Advisory answer cites/references retrieved source documents/record versions where factual support matters. |
| AI-FR-016 | Source authority | AI must distinguish authoritative GxP record from projections, draft docs, external web and user narrative. |
| AI-FR-017 | Freshness | AI response displays/records source cutoff/version when stale data could matter. |
| AI-FR-018 | Hallucination handling | When evidence insufficient/contradictory, output uncertainty or 'insufficient evidence' rather than fabricate regulated fact. |
| AI-FR-019 | Structured outputs | High-risk advisory extraction/classification uses validated JSON/schema output and server validation. |
| AI-FR-020 | Determinism settings | Temperature/randomness/tool settings versioned by use case; regulated advisory favors constrained reproducibility where useful. |
| AI-FR-021 | Model change control | Model/provider/version/prompt/retrieval/tool change receives risk/change/validation impact before production. |
| AI-FR-022 | Evaluation set | Each regulated-advisory use case has versioned representative evaluation dataset/scenarios. |
| AI-FR-023 | Evaluation dimensions | Evaluate factuality/grounding, extraction accuracy, refusal/uncertainty, tool safety, prompt injection, bias where relevant, latency/cost and robustness. |
| AI-FR-024 | Acceptance thresholds | Thresholds/risk tolerances defined per use case; overall average cannot hide critical failure class. |
| AI-FR-025 | Adversarial tests | Test prompt injection, data exfiltration, unsafe tool calls, cross-tenant retrieval, malformed context and jailbreak attempts. |
| AI-FR-026 | Human factors | Evaluate over-reliance/automation bias and ensure UI wording does not imply AI approval/authority. |
| AI-FR-027 | Output labeling | UI clearly identifies AI-generated/advisory content and relevant source/evidence links. |
| AI-FR-028 | AI audit log | Record use-case ID, model/version, prompt/template version, retrieval refs, tool calls, output hash, user, timestamp and human disposition as appropriate. |
| AI-FR-029 | Prompt privacy | Do not log secrets/full sensitive prompts unnecessarily; store protected/redacted evidence according to risk. |
| AI-FR-030 | Token/data minimization | Send minimum necessary data to model; avoid full batch/complaint/personnel record when narrower context suffices. |
| AI-FR-031 | Tenant isolation | Retrieval/tool execution bound tenant/site/role before model context assembly. |
| AI-FR-032 | No security secret reasoning | AI does not receive private keys/passwords/tokens or raw secrets as context. |
| AI-FR-033 | Incident handling | Material AI unsafe output/data leak/tool misuse creates security/quality incident as applicable. |
| AI-FR-034 | User feedback | Incorrect AI suggestion can be flagged and linked evaluation/improvement without rewriting historical output. |
| AI-FR-035 | Monitoring | Track model errors, groundedness proxies, refusal rates, tool denials, latency, cost, drift and user override/acceptance rates where meaningful. |
| AI-FR-036 | No online self-learning | Production AI does not autonomously retrain/update policy from user interactions in regulated use. |
| AI-FR-037 | Training data governance | If custom model/fine-tune is introduced, dataset provenance, rights, deidentification, splits, leakage and versioning mandatory. |
| AI-FR-038 | Bias/applicability | Where AI affects people/safety prioritization, evaluate representativeness/bias/applicability relevant to use case. |
| AI-FR-039 | Explainability | Provide source/rationale features appropriate to advisory use; do not fabricate chain-of-thought. |
| AI-FR-040 | AI availability | AI outage must not block core regulated manufacturing unless a separately validated process explicitly depends on it; manual/non-AI path exists. |

## SPEC_GAP triggers

Raise a SPEC_GAP rather than deciding, if you encounter: a missing signature/authorization/retention/
precision value, a conflict between two source documents, an entity without an owner, an event without a
producer, or any requirement that would need a regulated behaviour you cannot trace to
Document 105 or Documents 106–115.
