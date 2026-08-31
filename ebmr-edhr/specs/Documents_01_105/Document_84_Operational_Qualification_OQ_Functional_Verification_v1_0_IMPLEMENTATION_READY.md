# US eBMR / eDHR Regulated Manufacturing Platform
## Document 84 — Operational Qualification (OQ) & Functional Control Verification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-006  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 03–60, 80–83  
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

Define functional qualification of the configured platform in an IQ-approved environment, emphasizing higher-risk GxP controls, negative paths, calculations and concurrency.

# 2. Actors / Components

- Validation
- QA
- Engineering
- CI
- Process SME
- Security

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| OQ-FR-001 | Functional scope | Verify system functions/controls against approved requirements/risk in IQ environment. | Functional assurance. |
| OQ-FR-002 | Core GxP controls | Mutation, authorization, signature, audit, Vault, rules and release explicitly tested. | Core GxP. |
| OQ-FR-003 | Boundary conditions | Test invalid states, limits, stale versions, missing inputs and unauthorized actions. | Robustness. |
| OQ-FR-004 | State machines | Verify allowed/forbidden transitions. | Operational checks. |
| OQ-FR-005 | Calculations | Verify decimal/UOM/rounding/rule vectors. | Accuracy. |
| OQ-FR-006 | Batch/QMS/material/QC | Representative regulated module flows covered by risk. | Business controls. |
| OQ-FR-007 | Equipment/sterile | Representative equipment/cleaning/EM/sterile controls for DDCP profile. | Production. |
| OQ-FR-008 | Error handling | Verify stable errors/fail-closed behavior. | Safety. |
| OQ-FR-009 | Concurrency | Verify optimistic lock/idempotency/duplicate requests. | Distributed correctness. |
| OQ-FR-010 | Restart/recovery | Test worker/app restart during critical flows. | Reliability. |
| OQ-FR-011 | Roles/SoD | Representative positive/negative authority matrix. | Authorization. |
| OQ-FR-012 | Configuration | Test exact released configuration/rules/templates. | Configured state. |
| OQ-FR-013 | Automated reuse | CI integration/API tests may satisfy OQ when environment/config equivalence established. | CSA. |
| OQ-FR-014 | End-user fit | Operational user fit belongs PQ/UAT rather than forcing all into OQ. | Separation. |
| OQ-FR-015 | Defect closure | Failures map defect/deviation/retest. | No hidden failure. |
| OQ-FR-016 | Coverage | Higher-risk requirements receive objective OQ or justified equivalent evidence. | Risk coverage. |
| OQ-FR-017 | Independent review | Critical evidence reviewed per VMP. | Assurance. |
| OQ-FR-018 | Approval | OQ approval prerequisite to PQ/go-live as configured. | Gate. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| deriveOQSuite() | Validation service | requirement baseline; risks; IQ | IQ approved | Selects required functional/negative/concurrency tests | OQSuite | OQSuiteDerived |
| executeOQSuite() | Validation/CI | OQ suite; environment/config fingerprint | IQ valid | Executes/imports tests and evidence | OQExecution | OQExecutionCompleted |
| evaluateOQCoverage() | Validation | OQ execution; risk/requirements | Execution closed | Calculates critical coverage/gaps/failures | OQCoverageReport | OQCoverageEvaluated |
| approveOQ() | Validation/QA | execution; coverage; deviations; signature | Critical blockers resolved | Freezes OQ result | ApprovedOQ | OQApproved |


# 5. Validation State / Control Model

```text
IQ APPROVED → RISK-BASED OQ SUITE → FUNCTIONAL/NEGATIVE/CONCURRENCY/RECOVERY TEST → DEFECT/RETEST → OQ APPROVAL
```

# 6. Data / Evidence Model

`oq_suite`: baseline, selected tests/evidence, exclusions/rationale, environment fingerprint.
`oq_execution`: suite version, test refs, coverage, deviations, approval.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/oq:suites`
- `POST /validation/v1/oq/executions`
- `GET /validation/v1/oq/{id}/coverage`
- `POST /validation/v1/oq/{id}/approve`

# 8. UI / Validation Workspace

1. OQ Scope
2. OQ Execution
3. Critical Coverage
4. Failures
5. OQ Approval

# 9. Events

- `OQSuiteDerived`
- `OQExecutionCompleted`
- `OQCoverageEvaluated`
- `OQApproved`

# 10. Mandatory Test / Evidence Catalogue

- stale mutation denied
- signature wrong meaning
- audit old/new
- rounding vectors
- duplicate command
- worker restart
- unauthorized release

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

Higher-risk controls and representative regulated functions operate consistently as intended in the qualified environment.

# 13. Claude Code / Codex Prohibitions

- Never equate unit-test pass with OQ without trace/environment equivalence.
- Never omit negative tests for authority/state/signature.
- Never approve unresolved critical failure.
- Never test only happy paths.


