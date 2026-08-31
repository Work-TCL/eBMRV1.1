# US eBMR / eDHR Regulated Manufacturing Platform
## Document 82 — Validation Test Strategy, Test Methods & Objective Evidence Governance — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-004  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 79–81; CI/CD; Evidence Store  
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

Define risk-based automated, scripted and exploratory validation methods and the objective-evidence model needed for repeatable, reviewable assurance.

# 2. Actors / Components

- Validation Tester
- Developer
- Independent Reviewer
- CI System
- QA
- Evidence Service

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| TST-FR-001 | Test methods | Support automated, scripted manual, exploratory, review/inspection, analysis and supplier-evidence verification. | CSA flexibility. |
| TST-FR-002 | Method selection | Risk, complexity, determinism and control drive test method. | Risk based. |
| TST-FR-003 | Versioning | Approved/executed test definition immutable/versioned. | Evidence. |
| TST-FR-004 | Preconditions | Define environment/config/data/roles/dependencies. | Repeatability. |
| TST-FR-005 | Expected results | Scripted/automated tests have objective expected result/tolerance. | Clear pass. |
| TST-FR-006 | Exploratory charter | Retain charter, tester, actions, observations, conclusion and evidence. | Objective evidence. |
| TST-FR-007 | Test data | Synthetic/controlled data identified/versioned; production data avoided unless controlled. | Governance. |
| TST-FR-008 | Environment fingerprint | Capture app/build/config/DB/schema/browser/device/interface versions. | Reproducibility. |
| TST-FR-009 | Automated evidence | Capture test code commit, runner/image, logs/results/artifacts. | Trustworthy automation. |
| TST-FR-010 | Manual execution | Capture performer, timestamps, actual result, evidence, deviations. | Attribution. |
| TST-FR-011 | Review | Higher-risk evidence independently reviewed according to VMP. | Assurance. |
| TST-FR-012 | Approval signature | Validation approval uses controlled signature when relied upon electronically. | Controlled evidence. |
| TST-FR-013 | Failure retention | Failure remains; later pass is separate execution. | History. |
| TST-FR-014 | Blocked/skipped | Require reason and release impact. | No false coverage. |
| TST-FR-015 | Evidence hash | Logs/screenshots/files stored via Evidence Store with hash. | Integrity. |
| TST-FR-016 | Evidence efficiency | Screenshots supplement stronger machine evidence rather than replace it. | Efficient validation. |
| TST-FR-017 | Independence | Tester/reviewer independence risk-based; developer evidence may count when justified. | Balanced. |
| TST-FR-018 | Flaky tests | Flaky automated tests tracked and cannot be sole critical evidence. | Evidence quality. |
| TST-FR-019 | Regression | Risk-based regression suite derived from change impact. | Lifecycle. |
| TST-FR-020 | Negative tests | Higher-risk functions include invalid/unauthorized/failure-state tests. | Robustness. |
| TST-FR-021 | Concurrency | Critical idempotency/version/locking functions include race/retry tests. | Distributed correctness. |
| TST-FR-022 | Recovery | Critical flows include restart/dependency outage/recovery evidence. | Reliability. |
| TST-FR-023 | Protocol export | Human-readable protocol/result generated from authoritative records. | Inspection. |
| TST-FR-024 | No result editing | Executed result corrected by amendment/new execution, not in-place edit. | Integrity. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createValidationTestDefinition() | Validation/Engineer | test_type; requirements; risk; procedure/charter; expected results | Trace/risk exists | Creates draft test definition | TestDefinition | ValidationTestCreated |
| approveTestDefinition() | Reviewer | test/version; signature | Definition complete/current | Freezes executable test version | ApprovedTest | ValidationTestApproved |
| startTestExecution() | Tester/CI | test version; environment fingerprint; data/config refs | Eligible environment | Creates execution identity | TestExecution | ValidationTestExecutionStarted |
| recordTestObservation() | Tester/Automation | execution; step/check; actual; evidence; status | Execution active | Appends immutable observation/result | ObservationReceipt | ValidationObservationRecorded |
| completeTestExecution() | Tester/CI | execution; conclusion; summary | Mandatory evidence present | Closes PASS/FAIL/BLOCKED and triggers exception on failure | TestResult | ValidationTestCompleted |
| reviewTestExecution() | Reviewer | execution; conclusion; signature | Execution closed | Accepts/rejects evidence | TestReview | ValidationTestReviewed |
| importAutomatedTestEvidence() | CI | run ID; commit; report; artifact refs; fingerprint | Trusted CI source | Creates traceable automated validation evidence | ImportedTestEvidence | AutomatedEvidenceImported |


# 5. Validation State / Control Model

```text
TEST DRAFT → APPROVED → EXECUTION (AUTOMATED/SCRIPTED/EXPLORATORY) → PASS/FAIL/BLOCKED → REVIEW → TRACE/RELEASE
```

# 6. Data / Evidence Model

`validation_test_definition`: code/version, method, requirement/risk links, preconditions/data, procedure/charter, expected results, review rule.
`validation_test_execution`: exact test/environment, tester/CI, observations, final status, evidence manifest, defect/deviation links.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/tests`
- `POST /validation/v1/tests/{id}/approve`
- `POST /validation/v1/executions`
- `POST /validation/v1/executions/{id}/complete`
- `POST /validation/v1/automated-evidence`

# 8. UI / Validation Workspace

1. Test Library
2. Execution Workspace
3. Automated Evidence
4. Exploratory Charters
5. Failed/Blocked Tests
6. Evidence Review

# 9. Events

- `ValidationTestApproved`
- `ValidationTestExecutionStarted`
- `ValidationTestCompleted`
- `AutomatedEvidenceImported`
- `ValidationTestReviewed`

# 10. Mandatory Test / Evidence Catalogue

- automated pass import
- flaky automation
- failed manual step
- exploratory session
- retest preserves old fail
- stale environment fingerprint

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

Every PASS used for release is tied to a known test method, exact build/config/environment and objective retained evidence appropriate to risk.

# 13. Claude Code / Codex Prohibitions

- Never edit failed execution to PASS.
- Never require screenshots when machine evidence is stronger solely for tradition.
- Never count skipped test as PASS.
- Never use flaky test as sole critical evidence.


