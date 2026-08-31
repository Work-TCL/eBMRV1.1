# US eBMR / eDHR Regulated Manufacturing Platform
## Document 80 — Intended Use, GxP Criticality & Software Function Risk Classification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-002  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 01, 07, 29, 54–60, 79  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This specification is intended for direct ingestion by Claude Code, Codex, Validation/Quality, and engineering teams.

Before implementation, the coding agent shall extract:
1. requirement IDs and compliance/risk linkage;
2. validation artifact types;
3. validation lifecycle/state machines;
4. function/service contract catalogue;
5. typed input/output schemas;
6. authorization/qualification/SoD/signature requirements;
7. database reads/writes and transaction boundaries;
8. evidence/object-storage contracts;
9. test execution/result schemas;
10. traceability relationships;
11. deviation/defect linkage;
12. release/periodic-review gates;
13. automated/manual test obligations;
14. validation evidence retention.

For every public/domain validation function defined below, preserve caller/trigger, typed inputs, auth/signature prerequisites, validations, DB/evidence reads/writes, transaction boundary, output, events, stable errors, idempotency/concurrency, audit evidence, and test obligations.

If a missing decision can alter intended use, GxP risk, acceptance criteria, validation evidence, release eligibility, or revalidation scope, create a `SPEC_GAP` rather than guessing.

# Current U.S. Validation / CSA Regulatory Baseline

- FDA issued the final **Computer Software Assurance for Production and Quality Management System Software** guidance in February 2026. It recommends a risk-based approach for medical-device production/QMS software and supersedes the September 24, 2025 final guidance.
- The QMSR became effective February 2, 2026 and incorporates ISO 13485:2016 by reference. Maintain a licensed compliance mapping; do not reproduce copyrighted ISO clauses.
- 21 CFR §11.10 includes validation to ensure accuracy, reliability, consistent intended performance and the ability to discern invalid or altered records, plus copies, retention, access, audit, operational, authority, device, training and documentation controls.
- FDA's Part 11 Scope and Application guidance states Part 11 remains in effect while FDA exercises enforcement discretion for certain provisions as described there; predicate-rule obligations remain.
- 21 CFR §211.68 requires appropriate controls over computer/related systems used in drug manufacturing and addresses authorized changes, input/output checks, backups and appropriate validation data.
- IQ/OQ/PQ and GAMP-style lifecycle classifications are useful validation/industry methods, not universal FDA-mandated document names.

Primary references:
- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/computer-software-assurance-production-and-quality-management-system-software
- https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr
- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application
- https://www.law.cornell.edu/cfr/text/21/11.10
- https://www.law.cornell.edu/cfr/text/21/211.68

# Validation Architecture Principles

- Validation is intended-use and risk based.
- The validated state belongs to a released system configuration/version + environment + controlled procedures, not source code alone.
- Every critical requirement must trace to design/implementation and objective evidence.
- Automated tests are encouraged where deterministic, reliable and reviewable.
- Exploratory testing may be appropriate for lower-risk functions when objective evidence is retained.
- Higher-risk GxP functions require greater assurance rigor.
- Failed tests remain immutable; rerun never erases failure.
- Production release requires software release evidence and validation release evidence.
# 1. Objective

Define function-level intended use and risk classification that drives validation scope and assurance rigor under FDA's 2026 CSA approach while independently preserving Part 11 and drug CGMP controls.

# 2. Actors / Components

- System Owner
- Process Owner
- Validation
- QA
- Engineering
- Regulatory
- Security

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| RISK-FR-001 | Intended use | Document intended use at system/module/function level and affected regulated process. | Risk basis. |
| RISK-FR-002 | GxP impact | Classify direct/indirect/no GxP impact with rationale. | Scoping. |
| RISK-FR-003 | Quality impact | Assess patient/product quality, safety, data integrity and release consequences. | CSA risk. |
| RISK-FR-004 | Failure mode | Identify process/business failure if function fails or produces wrong result. | Real risk. |
| RISK-FR-005 | Detectability | Assess likelihood failure is detected before harm/wrong decision. | Risk dimension. |
| RISK-FR-006 | Automation role | Classify informational/advisory/calculation/enforcement/control/automated decision. | Criticality. |
| RISK-FR-007 | Record role | Identify whether function creates/modifies/signs/audits/archives predicate-rule record. | Part 11 scope. |
| RISK-FR-008 | Signature role | Identify whether function performs/relies on legally binding e-signature. | Part 11. |
| RISK-FR-009 | Constituent scope | For DDCP identify drug/device/biologic/final-combination impact. | Part 4 context. |
| RISK-FR-010 | Risk category | Use controlled higher-process-risk/standard-risk plus internal criticality as configured. | CSA alignment. |
| RISK-FR-011 | Assurance method | Risk drives testing style, depth, independence and evidence. | Proportionate. |
| RISK-FR-012 | Configuration risk | Assess customer workflow/rule/form/interface configuration separately from platform code. | Configured state. |
| RISK-FR-013 | Supplier component risk | Assess third-party/OSS/service based on intended use and controls. | Supply-chain. |
| RISK-FR-014 | Infrastructure risk | Assess critical infrastructure failure/recovery effects. | Environment. |
| RISK-FR-015 | Interface risk | Assess external data/mapping/source/output failure and detection. | Integration. |
| RISK-FR-016 | AI risk | AI advisory functions separately classified; autonomous regulated decisions prohibited. | AI governance. |
| RISK-FR-017 | Risk version | Assessment tied to exact requirement/function/design/config version. | Traceability. |
| RISK-FR-018 | Change reassessment | Material change triggers risk impact reassessment. | Lifecycle. |
| RISK-FR-019 | Residual risk | Post-control risk documented and approved. | Governance. |
| RISK-FR-020 | Scoring method | Methodology versioned; numeric score never replaces rationale. | Quality. |
| RISK-FR-021 | Out-of-scope rationale | Validation exclusion documented/reviewed and change-sensitive. | Inspection. |
| RISK-FR-022 | Coverage | Every higher-risk function maps controls and objective evidence. | Completeness. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createIntendedUseStatement() | System/Process Owner | scope_type; scope_id; intended_use; process; users | Scope exists | Creates versioned intended-use statement | IntendedUse | IntendedUseCreated |
| assessFunctionRisk() | Validation/Process Owner | function_id; failure_modes; impacts; detectability; automation/record role | Function/spec version exists | Creates risk classification and control rationale | FunctionRiskAssessment | FunctionRiskAssessed |
| approveRiskAssessment() | QA/Validation | assessment_id; decision; signature | Assessment complete/current | Freezes risk/residual decision | ApprovedRiskAssessment | RiskAssessmentApproved |
| deriveAssuranceLevel() | Validation service | approved risk; function type; VMP rules | VMP effective | Returns required testing/evidence/review depth | AssuranceRequirement | AssuranceLevelDerived |
| reassessRiskForChange() | Change Control | change_id; affected function/config IDs | Impact identified | Creates new risk assessment delta/revalidation recommendation | RiskReassessment | ValidationRiskReassessmentRequired |


# 5. Validation State / Control Model

```text
FUNCTION → INTENDED USE → FAILURE MODE/IMPACT → RISK CATEGORY → ASSURANCE METHOD → RESIDUAL RISK APPROVAL → CHANGE REASSESSMENT
```

# 6. Data / Evidence Model

`intended_use`: scope/version, regulated process, users, record/signature relevance.
`function_risk_assessment`: function/version, failure modes, impacts, detectability, automation role, controls, category, assurance level, approval.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/intended-use`
- `POST /validation/v1/function-risks`
- `POST /validation/v1/function-risks/{id}/approve`
- `GET /validation/v1/functions/{id}/assurance`

# 8. UI / Validation Workspace

1. Intended Use
2. Function Risk Matrix
3. Failure Modes
4. Assurance Level
5. Risk Change Impact

# 9. Events

- `IntendedUseCreated`
- `FunctionRiskAssessed`
- `RiskAssessmentApproved`
- `AssuranceLevelDerived`
- `ValidationRiskReassessmentRequired`

# 10. Mandatory Test / Evidence Catalogue

- calculation high impact
- display-only low risk
- audit-disable high risk
- customer release-rule config
- external bad mapping
- AI advisory

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

Every assurance/test decision can be traced to approved intended use and failure-risk rationale.

# 13. Claude Code / Codex Prohibitions

- Never classify risk solely by module name.
- Never mark Part 11 record function out of scope without rationale.
- Never let numeric score replace failure analysis.
- Never reuse stale risk assessment after material change.


