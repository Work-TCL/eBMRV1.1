# WP-13 — Function Contracts

Every function must specify typed inputs, validations, authorization/qualification/SoD, signature requirement, processing rules, DB reads/writes, transaction boundary, outputs, events, errors, idempotency and concurrency. Full rows: `docs/generated/03_FUNCTION_CATALOGUE.csv` filtered by module.

| Function | Doc | Caller | Inputs | Preconditions | Output |
|---|---|---|---|---|---|
| registerAIUseCase() | 105 | AI Governance Admin | name; class; purpose; users; data classes; decision impact; proposed tools/models | Owner/risk assessment initiated | AIUseCase |
| assessAIUseCaseRisk() | 105 | AI Governance/QA/Security | use_case_id; failure modes; GxP/people/data/security impact; human oversight | Use case defined | AIRiskAssessment |
| approveAIModelDeployment() | 105 | AI Governance/Security/QA as required | provider/model/version; terms; privacy; evaluation result; use-case scope | Model allowlist checks/evaluation pass | ApprovedModelDeployment |
| buildAIRequestContext() | 105 | AI Gateway | AuthContext; use_case; user query; requested record refs | User authorized; data/provider policy effective | AIContextPackage |
| executeAIAdvisory() | 105 | AI Gateway | use_case; context package; prompt version; approved model; tool policy | Model/use case effective | AIAdvisoryResult |
| authorizeAIToolCall() | 105 | AI Gateway tool middleware | use_case; model request; tool; args; AuthContext | Tool allowlisted; action permitted; tenant/site scope valid | AIToolDecision |
| recordHumanAIDisposition() | 105 | User/regulated workflow | advisory_id; ACCEPTED_AS_INPUT/REJECTED/EDITED/NOT_USED; comments; downstream record ref | User authorized; advisory exists | AIDisposition |
| runAIEvaluationSuite() | 105 | AI validation/CI | use_case; model/prompt/tool versions; evaluation dataset; scenario classes | Dataset/version approved | AIEvaluationReport |
| evaluateAIReleaseGate() | 105 | AI Governance/Validation | candidate model/prompt/tool/config; eval report; incidents; vendor/security status | Current risk assessment | AIReleaseGate |
| detectPromptInjection() | 105 | AI Gateway/security layer | retrieved/user content; use-case policy | Policy active | PromptInjectionDecision |
| switchAIProviderProfile() | 105 | AI Platform Admin | use_case; target approved model/provider/private deployment | Target approved and evaluation equivalent/current | AIProviderSwitch |
| retireAIUseCase() | 105 | AI Governance | use_case; reason; replacement; effective date | Owner/QA approval as risk requires | RetirementReceipt |
| generateAIGovernancePackage() | 105 | Audit/Customer | use_case/release scope | Records available | AIGovernancePackage |
