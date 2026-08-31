# US eBMR / eDHR Regulated Manufacturing Platform
## Document 94 — Validation Defect, Deviation, Test Exception & Remediation Management — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-016  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 26–29, 79–93; Engineering issue tracker  
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

Define controlled lifecycle for validation failures, protocol/environment deviations, software defects, retest and risk disposition so failed evidence remains visible and release decisions are defensible.

# 2. Actors / Components

- Validator
- QA
- Engineering
- System Owner
- Change Control
- Issue Tracker Integration

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| VEX-FR-001 | Event types | Distinguish defect, test failure, protocol/environment deviation, evidence issue, requirement gap. | Clear workflow. |
| VEX-FR-002 | Automatic creation | Critical failed test can create validation exception automatically. | No loss. |
| VEX-FR-003 | Original evidence | Original failure/evidence immutable. | History. |
| VEX-FR-004 | Triage | Severity and GxP/release impact assessed. | Risk. |
| VEX-FR-005 | Engineering link | Issue/PR/commit linked to validation failure. | Trace. |
| VEX-FR-006 | QMS link | Validated-state impact can link/create Quality deviation. | QMS. |
| VEX-FR-007 | Protocol deviation | Departure from approved procedure records reason/impact/approval. | Controlled. |
| VEX-FR-008 | Environment deviation | Wrong environment/config may invalidate result. | Evidence validity. |
| VEX-FR-009 | Evidence issue | Missing/corrupt evidence cannot remain unexplained PASS. | Integrity. |
| VEX-FR-010 | Root cause | Critical/recurrent failure gets appropriate cause analysis. | Quality. |
| VEX-FR-011 | Fix link | Correction/change/version linked. | Remediation. |
| VEX-FR-012 | Retest scope | Direct/regression retest based on cause/change/risk. | Adequate verification. |
| VEX-FR-013 | Retest identity | New execution ID; prior failure remains. | History. |
| VEX-FR-014 | Disposition | OPEN/FIX/RETEST/ACCEPTED_WITH_RATIONALE/DEFERRED_BLOCKING/CLOSED. | Explicit. |
| VEX-FR-015 | Risk acceptance | Acceptance without fix needs residual-risk approval and cannot violate binding requirement. | Governance. |
| VEX-FR-016 | Release blocker | Critical/high unresolved/invalid evidence blocks release by policy. | Gate. |
| VEX-FR-017 | Known limitation | Approved limitation appears in VSR/release/customer package where material. | Transparency. |
| VEX-FR-018 | Trend | Track recurring failures/flaky tests/root causes. | Improvement. |
| VEX-FR-019 | Closure | Fix/retest/impact/approval needed. | Complete. |
| VEX-FR-020 | Reopen | New evidence can reopen with history. | Lifecycle. |
| VEX-FR-021 | Audit | Triage/disposition/closure/reopen audited/signed as policy. | Accountability. |
| VEX-FR-022 | VSR link | Open/accepted deviations automatically included in VSR. | Inspection. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createValidationException() | Test system/Validator | source execution; type; description; evidence; requirements | Source exists | Creates OPEN exception | ValidationException | ValidationExceptionCreated |
| triageValidationException() | Validation/QA/Engineering | exception; severity; GxP/release impact; rationale | Authorized | Stores triage/actions | ExceptionTriage | ValidationExceptionTriaged |
| linkEngineeringDefect() | Engineering integration | exception; issue/commit/PR | Refs valid | Creates trace/fix link | DefectLink | EngineeringDefectLinked |
| defineRetestScope() | Validation | exception; fix/change; affected trace graph | Cause/fix known | Selects direct/regression scope | RetestPlan | ValidationRetestScopeDefined |
| dispositionValidationException() | QA/Validation | exception; disposition; rationale; signature | Required actions complete | Updates controlled disposition | ExceptionDisposition | ValidationExceptionDispositioned |
| evaluateExceptionReleaseBlockers() | Release gate | release; open exceptions | Policy effective | Returns blockers/accepted limitations | ExceptionGateResult | ValidationExceptionGateEvaluated |


# 5. Validation State / Control Model

```text
FAILED/DEVIATED EVIDENCE → EXCEPTION → TRIAGE → FIX/RETEST OR RISK DISPOSITION/RELEASE BLOCK → CLOSE/REOPEN
```

# 6. Data / Evidence Model

`validation_exception`: type, source execution, affected requirements, severity/GxP/release impact, state/disposition, cause, issue/change refs, retest plan, version.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/exceptions`
- `POST /validation/v1/exceptions/{id}/triage`
- `POST /validation/v1/exceptions/{id}/retest-plan`
- `POST /validation/v1/exceptions/{id}/disposition`
- `GET /validation/v1/releases/{id}/exception-gate`

# 8. UI / Validation Workspace

1. Validation Exceptions
2. Triage
3. Defect Links
4. Retest Scope
5. Risk Acceptance
6. Release Blockers
7. Trend

# 9. Events

- `ValidationExceptionCreated`
- `ValidationExceptionTriaged`
- `ValidationRetestScopeDefined`
- `ValidationExceptionDispositioned`

# 10. Mandatory Test / Evidence Catalogue

- fail then fixed/retest
- wrong environment invalidates pass
- missing critical evidence
- accepted cosmetic issue
- critical defect blocks release

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

Every failed/deviated result remains traceable through cause, fix/risk disposition, retest and release impact without altering original evidence.

# 13. Claude Code / Codex Prohibitions

- Never edit failed test to pass.
- Never close because retest passed without cause/fix trace.
- Never accept violation of binding requirement as risk accepted.
- Never hide material limitation from VSR.


