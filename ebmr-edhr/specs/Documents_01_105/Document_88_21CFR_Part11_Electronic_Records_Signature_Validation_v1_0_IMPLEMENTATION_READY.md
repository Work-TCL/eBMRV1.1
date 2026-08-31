# US eBMR / eDHR Regulated Manufacturing Platform
## Document 88 — 21 CFR Part 11 Electronic Records & Electronic Signature Validation — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-010  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 03–07, 30, 62, 65, 79–87  
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

Define explicit validation of Part 11 electronic-record and electronic-signature controls, including scope, copies, retention, access, audit, sequencing, authority/device checks and signature manifestation/linking.

# 2. Actors / Components

- Validation
- QA
- Regulatory
- Identity Admin
- Records Manager
- System Owner
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| P11-FR-001 | Part 11 scope | Identify records/signatures relied upon electronically under predicate rules. | Scope. |
| P11-FR-002 | Accuracy/reliability | Verify intended functions create accurate/reliable records. | 11.10(a). |
| P11-FR-003 | Altered record discernment | Verify invalid/altered record detection. | 11.10(a). |
| P11-FR-004 | Human-readable copies | Verify accurate complete human-readable export. | 11.10(b). |
| P11-FR-005 | Electronic copies | Verify electronic export with required metadata. | 11.10(b). |
| P11-FR-006 | Retention/retrieval | Verify ready retrieval through retention/archive. | 11.10(c). |
| P11-FR-007 | Access | Verify authorized-only record/system access. | 11.10(d). |
| P11-FR-008 | Audit trail | Verify secure timestamped audit, prior values, retention/review. | 11.10(e). |
| P11-FR-009 | Operational checks | Verify sequencing prevents invalid workflow order. | 11.10(f). |
| P11-FR-010 | Authority checks | Verify role/qualification/SoD/signature authority. | 11.10(g). |
| P11-FR-011 | Device/source checks | Verify scanner/balance/Edge/device validity as applicable. | 11.10(h). |
| P11-FR-012 | Training | Verify relevant training/qualification controls. | 11.10(i). |
| P11-FR-013 | Signature accountability policy | Customer responsibility/evidence documented. | 11.10(j). |
| P11-FR-014 | Documentation controls | Verify controlled system documentation/access/change history. | 11.10(k). |
| P11-FR-015 | Signature manifestation | Verify signer printed name, time and meaning in display/export. | 11.50. |
| P11-FR-016 | Signature linking | Verify signature cannot be transferred to falsify another record by ordinary means. | 11.70. |
| P11-FR-017 | Unique identity | Verify unique signer mapping and identity verification responsibility. | 11.100. |
| P11-FR-018 | Signature components | Verify configured signing ceremony satisfies applicable controls. | 11.200. |
| P11-FR-019 | Version binding | Signature binds exact record/version/hash/action/meaning. | Platform control. |
| P11-FR-020 | Fresh step-up | V1 validates fresh step-up for every regulated signature per Document 04. | Stronger baseline. |
| P11-FR-021 | Failed signing | Expired challenge/stale version/replay/wrong signer fails. | Security. |
| P11-FR-022 | Correction | Signed/released correction creates new version, not edit. | Integrity. |
| P11-FR-023 | Clock | Signature/audit UTC consistency verified. | Chronology. |
| P11-FR-024 | Open systems | Additional controls assessed where deployment/use is open-system context. | Scope. |
| P11-FR-025 | Customer certification | §11.100 certification/support remains customer responsibility. | Responsibility. |
| P11-FR-026 | Control matrix | Every applicable control maps test/evidence/config/procedure. | Inspection. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createPart11Assessment() | Validation/Regulatory | record types; predicate rules; deployment/use | Intended use approved | Creates Part 11 scope/control matrix | Part11Assessment | Part11AssessmentCreated |
| derivePart11TestSuite() | Validation | assessment; platform/customer config | Assessment approved | Selects control tests | Part11TestSuite | Part11TestSuiteDerived |
| verifySignatureManifestation() | Automated/manual test | signed record/export | Signed record exists | Checks name/time/meaning | ControlTestResult | SignatureManifestationVerified |
| verifySignatureRecordLink() | Validation | signature ID; record versions | Evidence available | Tests reassociation/tamper resistance | ControlTestResult | SignatureRecordLinkVerified |
| verifyRecordCopyCompleteness() | Validation | record/version; export types | Record retained | Compares source content/metadata/signatures/audit to copy | CopyVerification | ElectronicRecordCopyVerified |
| approvePart11Qualification() | QA/Validation | assessment/tests/deviations; signature | Required controls passed | Freezes Part 11 package | Part11Qualification | Part11QualificationApproved |


# 5. Validation State / Control Model

```text
PART 11 SCOPE → CONTROL MATRIX → RECORD/SIGNATURE TESTS → CUSTOMER RESPONSIBILITY EVIDENCE → DEVIATIONS → QUALIFICATION
```

# 6. Data / Evidence Model

`part11_scope_assessment`: record/signature type, predicate use, system component, closed/open context, applicability, customer responsibilities.
`part11_control_evidence`: control/citation, test/result/evidence, config, procedure, deviation.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/part11/assessments`
- `GET /validation/v1/part11/{id}/test-suite`
- `POST /validation/v1/part11/{id}/approve`

# 8. UI / Validation Workspace

1. Part 11 Scope
2. Control Matrix
3. Record Copy Test
4. Signature Validation
5. Customer Responsibility
6. Part 11 Package

# 9. Events

- `Part11AssessmentCreated`
- `Part11TestSuiteDerived`
- `Part11QualificationApproved`

# 10. Mandatory Test / Evidence Catalogue

- unauthorized record access
- audit old/new
- wrong workflow order
- invalid scanner source
- signature manifestation
- signature reassociation denied
- expired challenge
- archive retrieval

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

Each electronically relied-upon record/signature type has objective evidence for applicable Part 11 controls and explicit customer procedural responsibilities.

# 13. Claude Code / Codex Prohibitions

- Never claim FDA certification or blanket compliance from software alone.
- Never treat SSO login as signature.
- Never validate only UI and ignore export/archive.
- Never omit customer policy/certification responsibilities.


