# US eBMR / eDHR Regulated Manufacturing Platform
## Document 79 — Validation Master Plan & Computer Software Assurance Strategy — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-001  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 01–78; Quality/Change/Release  
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

Define the master validation/CSA strategy, deliverables, responsibilities, assurance rigor, release gates and lifecycle required to validate the eBMR/eDHR platform for intended regulated use.

# 2. Actors / Components

- Validation Lead
- QA
- System Owner
- Engineering
- Security
- Infrastructure
- Customer Validation
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| VAL-FR-001 | Validation policy | Define product validation policy for DDCP/device/pharma deployment profiles. | Single strategy. |
| VAL-FR-002 | CSA applicability | Medical-device production/QMS functions use FDA 2026 CSA risk-based assurance principles. | Current FDA approach. |
| VAL-FR-003 | Drug validation basis | Drug constituent functions map Part 11/predicate rules/211.68 independently of device CSA guidance. | Correct scope. |
| VAL-FR-004 | Intended-use hierarchy | System → module → function → deployment intended use documented before assurance decision. | Risk context. |
| VAL-FR-005 | Validation plan version | Validation Master Plan versioned/released and linked to release family. | Controlled plan. |
| VAL-FR-006 | Deliverables | Define required artifacts by risk, deployment and customer responsibility. | Predictable evidence. |
| VAL-FR-007 | Responsibility matrix | Define vendor vs customer validation duties for platform, config, interfaces, SOPs, training and PQ/UAT. | Shared responsibility. |
| VAL-FR-008 | Risk-based rigor | Test method, independence and evidence depth increase with GxP/process risk. | Proportionate assurance. |
| VAL-FR-009 | Automated evidence | Controlled CI/unit/integration/system automation may provide objective validation evidence. | CSA efficiency. |
| VAL-FR-010 | Exploratory evidence | Exploratory testing permitted when risk allows and charter, actions, findings and conclusion are retained. | Flexible assurance. |
| VAL-FR-011 | Scripted evidence | Higher-risk or complex functions use detailed expected-results testing where needed. | Higher assurance. |
| VAL-FR-012 | Supplier evidence reuse | Code review, automated tests, SBOM, scans and design reviews can contribute when traceable. | Avoid duplication. |
| VAL-FR-013 | Representative environment | Qualification environment represents production configuration; differences documented/assessed. | Representative testing. |
| VAL-FR-014 | Configuration validation | Customer GxP configuration/rules/workflows/interfaces require validation beyond platform baseline. | Configured product. |
| VAL-FR-015 | Interface validation | ERP/LIMS/Edge/device interfaces separately scoped by intended use/risk. | Boundary assurance. |
| VAL-FR-016 | Migration validation | Data migration/conversion has dedicated plan/reconciliation/evidence. | Data integrity. |
| VAL-FR-017 | Part 11 validation | Electronic records/signatures/audit/copies/retention/access controls explicitly verified. | Part 11. |
| VAL-FR-018 | Infrastructure qualification | Cloud/on-prem infrastructure, backup, security and time prerequisites qualified. | Environment confidence. |
| VAL-FR-019 | Performance/security | Risk-relevant performance/security evidence required before regulated pilot. | Operational suitability. |
| VAL-FR-020 | Deviation handling | Validation deviations/defects/failures controlled; unresolved critical blockers prevent release. | No paper pass. |
| VAL-FR-021 | Traceability | Requirements ↔ risk ↔ functions ↔ tests ↔ evidence ↔ defects ↔ release. | Inspection-ready. |
| VAL-FR-022 | Approval roles | Validation author/reviewer/approver/QA release roles separated by policy. | SoD. |
| VAL-FR-023 | Customer package | Generate vendor baseline plus customer/site qualification package. | Commercial usability. |
| VAL-FR-024 | Release gate | Go-live requires approved VSR and exact validated artifact/configuration. | Controlled go-live. |
| VAL-FR-025 | Ongoing state | Periodic review/change impact/revalidation maintain validated state. | Lifecycle. |
| VAL-FR-026 | Evidence retention | Validation evidence retained according to applicable system/customer/regulatory policy. | Evidence. |
| VAL-FR-027 | Electronic validation records | Validation approvals/evidence use controlled electronic records/signatures when relied upon electronically. | Self-consistency. |
| VAL-FR-028 | No document-count metric | Assurance judged by risk coverage and evidence, not number of scripts/pages. | CSA intent. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createValidationMasterPlan() | Validation Lead | system_version; deployment_profile; regulatory_scopes; responsibility_model | Architecture baseline exists | Creates draft VMP and deliverable/risk/test/release strategy | ValidationMasterPlan | ValidationMasterPlanCreated |
| releaseValidationMasterPlan() | QA/Validation approver | vmp_id; version; signatures | Mandatory sections/reviews complete | Vault-releases VMP | ReleasedVMP | ValidationMasterPlanReleased |
| deriveValidationDeliverables() | Validation service | risk inventory; deployment profile; VMP version | Risk assessments available | Derives required artifacts/tests/qualification items | ValidationDeliverablePlan | ValidationDeliverablesDerived |
| assignValidationResponsibility() | Validation Admin | artifact/control; vendor/customer/shared owner; rationale | VMP effective | Stores responsibility assignment | ResponsibilityAssignment | ValidationResponsibilityAssigned |
| evaluateValidationReleaseGate() | Release workflow | release candidate; trace status; deviations; evidence | VMP effective | Returns blockers/readiness; never auto-approves | ValidationGateResult | ValidationReleaseGateEvaluated |
| generateValidationPackageIndex() | Validation service | release/customer/site scope | Approved artifacts available | Builds immutable validation evidence index | ValidationPackageIndex | ValidationPackageGenerated |


# 5. Validation State / Control Model

```text
DRAFT VMP → REVIEW → RELEASED → INTENDED USE/RISK → VALIDATION EXECUTION → VSR → GO-LIVE → PERIODIC REVIEW
```

# 6. Data / Evidence Model

`validation_master_plan`: scope, regulatory profiles, methodology, deliverable rules, responsibilities, approval/version.
`validation_deliverable_requirement`: artifact type, risk condition, owner, review/signature, evidence type, release-blocker flag.
`validation_release_gate`: release/config/environment scope, required artefacts, blockers, decision refs.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/master-plans`
- `POST /validation/v1/master-plans/{id}/release`
- `GET /validation/v1/releases/{id}/gate`
- `GET /validation/v1/packages/{scope}`

# 8. UI / Validation Workspace

1. Validation Master Plan
2. Responsibility Matrix
3. Deliverables
4. Release Gate
5. Validation Package

# 9. Events

- `ValidationMasterPlanReleased`
- `ValidationDeliverablesDerived`
- `ValidationReleaseGateEvaluated`
- `ValidationPackageGenerated`

# 10. Mandatory Test / Evidence Catalogue

- high-risk scripted/automated evidence
- low-risk exploratory evidence
- missing customer config PQ
- open critical validation deviation
- Part 11 evidence missing

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

A release/customer deployment has an approved strategy explaining why each function receives its assurance level and exactly what evidence is needed before regulated use.

# 13. Claude Code / Codex Prohibitions

- Never classify all functions the same risk for convenience.
- Never treat CSA guidance as eliminating predicate-rule/Part 11 obligations.
- Never approve release based on document count.
- Never let engineering alone approve validation release.


