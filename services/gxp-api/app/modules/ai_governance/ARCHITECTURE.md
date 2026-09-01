# `ai_governance` — AI Governance for Regulated Manufacturing (Document 105 / SPEC-AI-001)

## Two decisions that deviate from the WP-13 sub-prompt's literal text

**1. Location.** `work-packages/WP-13/CLAUDE_CODE_PROMPT.md` and `prompts/WP-13/105_SPEC-AI-001.md`
say `services/ai-gateway` (a standalone microservice). This module instead lives in
`services/gxp-api/app/modules/ai_governance/`, reusing the existing Mutation Gateway / audit / outbox /
signature kernel — same decision this project already made for every WP-11 module vs. their sub-prompts'
stale `infrastructure/`/`src/` paths. Reason, specific to Document 105:
`docs/generated/03_FUNCTION_CATALOGUE.csv` (FN-1005..FN-1017 — precedence tier 6, **above** the current
task per CLAUDE.md §1) states for every one of the 13 functions: *"single PostgreSQL transaction: domain
+ version + audit + outbox (MUT-FR-015)"*. MUT-FR-015's single-transaction requirement cannot span two
separate services/DB connections — a standalone `services/ai-gateway` calling back into `gxp-api` over
HTTP could never satisfy it. Not a SPEC_GAP: this is an implementation-location choice, not an invented
regulated behaviour.

**2. Data model.** The spec text and the sub-prompt both say "DATA MODEL (0 entities)" / "APIS (0)" /
"EVENTS (0)". Checked and confirmed: `04_DATA_MODEL_CATALOGUE.md`, `05_DATABASE_OWNERSHIP_MATRIX.md`,
`06_API_CATALOGUE.yaml` and `07_EVENT_CATALOGUE.yaml` have **zero** SPEC-AI-001 rows — an incomplete
Phase-0 artefact, not a deliberate architecture (contrast with Document 74/Temporal, which genuinely has
0 entities because no live cluster exists). `03_FUNCTION_CATALOGUE.csv` is unambiguous and more specific
(same resolution rule Document 76/78 used for their own internal spec inconsistencies in WP-11: the more
operationally-detailed source wins). 11 tables were derived directly from each function's stated
Inputs/Output in that catalogue — see `models.py` docstrings for the per-table mapping. No field beyond
what the catalogue already states was invented.

## Signature status — SG-167

5 of 13 functions carry "SIGNATURE POLICY LOOKUP REQUIRED (Doc 04 SIG-FR-004; baseline values -> SG-004)"
in the function catalogue: `approveAIModelDeployment`, `authorizeAIToolCall`,
`recordHumanAIDisposition`, `evaluateAIReleaseGate`, `switchAIProviderProfile`. Document 106 (SG-004's
resolution baseline) has **zero** SPEC-AI-001 rows. Each of these 5 calls
`signature_service.resolve_signature_requirement()`, which is fail-closed by design (Doc 106 SIGP-FR-004
— see `app/modules/signature/service.py`): a missing policy row raises `SignaturePolicyUnresolvedError`
on every real call. This mirrors WP-01's originally-unresolved signed commands and is the *correct*
MUT-FR-022 behaviour ("if ... the Signature Service for required signings ... is unavailable, mutation
does not succeed"), not a defect — the code is fully implemented (including the full
step-up/challenge/consume/sign path in `_apply_signature()`) and will start working the moment Document
106 gains these 5 rows, with no further code change. Raised as **SG-167** in
`docs/generated/18_SPEC_GAPS.md`, non-blocking for CODE_COMPLETE (same treatment as WP-01's SG-035/SG-029
precedent).

One open nuance flagged inside SG-167: `authorizeAIToolCall()`'s signature semantics (a live interactive
step-up ceremony on every single tool call, vs. a one-time signed approval that adds a tool to a
use-case's allowlist with fast RBAC-only checks per call afterward) is itself something only Document
106 can specify — not guessed here.

## AI-FR requirement -> enforcement map

| AI-FR | Requirement | Where enforced |
|---|---|---|
| 001 | Use-case registry | `ai_use_case` table; `register_ai_use_case()` |
| 002 | Use-case class | `USE_CASE_CLASSES` enum validated in `register_ai_use_case()` |
| 003 | Regulated decision boundary | `REGULATED_DECISION_SCOPES` — `authorize_ai_tool_call()` refuses unconditionally; `assess_ai_use_case_risk()` records `prohibited_decisions` |
| 004 | No hidden GxP write | Structural: no `ai_governance` function imports any GxP domain module/command |
| 005 | Human review | `ai_advisory_log.status`, `record_human_ai_disposition()` — every advisory is disposed by a human, never auto-applied |
| 006 | No signature delegation | No `ai_governance` code path calls `signature_service.sign()` with a non-human actor; `authorize_ai_tool_call`'s tool middleware never signs on the model's behalf |
| 007 | Model registry | `ai_model_deployment` (provider/model/version/endpoint/context_window/effective_from) |
| 008 | Prompt/template version | `ai_prompt_version` |
| 009 | Tool registry | `ai_tool_registry` (`risk_class`, `allowed_scopes`) |
| 010 | Write tools disabled by default | `AIToolRegistry.risk_class` default `READ`; `WRITE_LOW_RISK` requires an `ACTIVE` use case in `authorize_ai_tool_call()` |
| 011 | Data classification | `AIUseCase.data_classes`; enforced in `build_ai_request_context()` |
| 012 | Provider data terms | `AIModelDeployment.data_terms` JSONB |
| 013 | On-prem/private AI profile | `deployment_type=PRIVATE|ON_PREM` on `ai_model_deployment` |
| 014 | Prompt injection defense | `detect_prompt_injection()` — pattern match, never treated as policy |
| 015 | Retrieval provenance | `AIAdvisoryLog.context_ref` carries source refs; `build_ai_request_context()`'s `scoped_refs` |
| 016 | Source authority | `context_ref`/`scoped_refs` distinguish `record_type`; no projection/draft is silently promoted to authoritative |
| 017 | Freshness | `scoped_refs[].source_cutoff` / `source_version` |
| 018 | Hallucination handling | `execute_ai_advisory()` raises `AIOutputInvalidError` rather than inserting a guess |
| 019 | Structured outputs | `_validate_against_schema()` in `execute_ai_advisory()` |
| 020 | Determinism settings | `AIPromptVersion` per use case; caller-side model params are part of the versioned prompt/tool policy, not this module's concern |
| 021 | Model change control | `evaluate_ai_release_gate()` gates a model/prompt/tool change behind a passed evaluation |
| 022 | Evaluation set | `AIEvaluationReport.dataset_ref`/`scenario_classes` |
| 023 | Evaluation dimensions | `metrics` JSONB — caller-injected `evaluator()` computes per-dimension basis-point scores |
| 024 | Acceptance thresholds | `critical_thresholds_bp` — `critical_failures` list overrides the overall average |
| 025 | Adversarial tests | `test_ai_governance.py` — injection/exfiltration/unsafe-tool/cross-tenant/malformed/jailbreak cases |
| 026 | Human factors | `ai_advisory_log.status="GENERATED"` — a receipt, never a claim of correctness; UI wording is a Frappe-layer concern outside this pass |
| 027 | Output labeling | `output_json`/`status` are always distinguishable from authoritative GxP state at the API boundary |
| 028 | AI audit log | `ai_advisory_log` IS the mandated log row |
| 029 | Prompt privacy | `ai_advisory_log` never stores the raw prompt, only `prompt_version_id` + `output_hash`/`output_json` |
| 030 | Token/data minimization | `build_ai_request_context()` only returns `requested_record_refs`, never a full record dump |
| 031 | Tenant isolation | `build_ai_request_context(caller_site_id=...)` — bound before context assembly |
| 032 | No security secret reasoning | `build_ai_request_context()` unconditionally denies `credential`/`secret`/`SECRET` classification |
| 033 | Incident handling | `AIReleaseGate.incidents_ref` — open incidents force `REVIEW` |
| 034 | User feedback | `ai_disposition` — INSERT-only, never rewrites `ai_advisory_log` |
| 035 | Monitoring | Not built this pass — no metrics/tracing exporter in this environment (known limitation, matches every other WP-11 module) |
| 036 | No online self-learning | Structural: no `ai_governance` code path writes back to `ai_prompt_version`/`ai_model_deployment` from advisory output |
| 037 | Training data governance | Out of scope this pass — no fine-tuned/custom model exists to govern (known limitation) |
| 038 | Bias/applicability | `AIRiskAssessment.people_impact` field |
| 039 | Explainability | `context_ref` on every advisory log row |
| 040 | AI availability | Structural: no GxP domain module calls into `ai_governance`; a manual/non-AI path always exists because nothing here is on the regulated critical path |
| 041 | Fallback behavior | `execute_ai_advisory()`'s `except` branch — `UNAVAILABLE` status, `AIOutputInvalidError`, no guess |
| 042-044 | Development-agent governance / generated-code review / IP review | Out of scope — Document 98/SDLC process, not this module's runtime |
| 045 | External AI API contract | `model_client`/`evaluator` are injected callables — the only integration point |
| 046 | AI Gateway | This module's `commands.py` collectively IS the control point (routing, allowlist, quotas via caller-supplied limits, logging) |
| 047 | Model allowlist | `execute_ai_advisory()` requires `AIModelDeployment.state == APPROVED` |
| 048 | Cost/resource limits | Not built this pass — no numeric token/time/cost cap baseline exists in Documents 106-115 (SG-166-family gap, see SPEC_GAP) |
| 049 | FDA device-software scope | Out of scope — no AI-enabled device software function exists in this product yet |
| 050 | NIST mapping | Documentation-only; no code artefact |
| 051 | Regulatory guidance status | Documentation-only; no code artefact |
| 052 | Periodic review | `generate_ai_governance_package()` gives the reviewable evidence bundle; the review cadence itself is a process, not code |
| 053 | Retirement | `retire_ai_use_case()` — `state=RETIRED`, all prior rows retained |
| 054 | Customer control | `deployment_type` supports a fully private/on-prem profile per use case |
| 055 | No AI compliance claims | Documentation-only; no code artefact |
| 056 | Evidence honesty | Structural: this module never marks a `test-cases/TEST_CASE_LIBRARY.csv` row PASS without a real assertion (same discipline as every WP-11 document) |

## Known limitations

No live LLM provider is configured in this environment — `execute_ai_advisory()` and
`run_ai_evaluation_suite()` take caller-injected callables (`model_client`, `evaluator`); tests supply a
fake implementation and prove the gateway logic (allowlist, schema validation, fail-closed fallback,
critical-failure blocking) without fabricating a live model call. AI-FR-035 (monitoring),
AI-FR-037 (training data governance), AI-FR-042..044/049..051/055 (process/documentation-only
requirements) have no code artefact in this pass — they are organizational/process controls, not gaps in
this module's implementation.
