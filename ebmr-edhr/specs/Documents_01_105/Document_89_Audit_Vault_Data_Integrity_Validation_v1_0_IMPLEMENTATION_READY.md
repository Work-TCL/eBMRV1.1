# US eBMR / eDHR Regulated Manufacturing Platform
## Document 89 — Audit Trail, Record Version Vault & Data Integrity Validation — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-011  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 05–06, 45, 69–76, 79–88  
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

Validate audit, immutable versions, evidence lineage, correction, hashes, archival and data-integrity controls—including deliberate tamper scenarios.

# 2. Actors / Components

- Validation
- QA
- DBA in isolated test role
- Records Manager
- Security
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| DIV-FR-001 | Audit append-only | Normal roles cannot update/delete audit events. | Tamper resistance. |
| DIV-FR-002 | Old/new values | Changed regulated fields preserve prior/new values and reason/signature links. | History. |
| DIV-FR-003 | Hash chain | Verify per-record hash-chain continuity/tamper detection. | Integrity. |
| DIV-FR-004 | Checkpoints | Verify signed integrity checkpoints and verification. | Tamper evidence. |
| DIV-FR-005 | Tamper simulation | Controlled isolated DBA tamper/removal/reorder test is detected. | Independent detection. |
| DIV-FR-006 | Vault immutability | Released versions immutable/retrievable. | History. |
| DIV-FR-007 | Canonicalization | Same payload produces stable digest under approved vectors. | Reproducibility. |
| DIV-FR-008 | Manifest | Record version manifest hashes exact evidence refs. | Completeness. |
| DIV-FR-009 | Correction/supersession | New version/relationship preserves original. | Data integrity. |
| DIV-FR-010 | Void | Void never erases content/history. | History. |
| DIV-FR-011 | Restore integrity | Restore preserves audit/hash/version/evidence relationships. | DR. |
| DIV-FR-012 | Migration provenance | Migrated data distinguished with source/transformation metadata. | Trace. |
| DIV-FR-013 | Failed result retention | Failed/OOS/rejected/test history retained after success/retest. | Completeness. |
| DIV-FR-014 | Timestamp provenance | Source vs receive/server time preserved. | Chronology. |
| DIV-FR-015 | Attribution | Human/service/device/source attribution verified. | Attributable. |
| DIV-FR-016 | Offline chronology | Edge/offline buffering preserves contemporaneous source chronology. | Contemporaneous. |
| DIV-FR-017 | Original evidence | Raw instrument/machine evidence linkage/hash retained as required. | Original. |
| DIV-FR-018 | Accuracy | Calculation/UOM/transformation versions and vectors verified. | Accurate. |
| DIV-FR-019 | Complete genealogy | Representative batch genealogy complete. | Complete. |
| DIV-FR-020 | Ordering | Late/duplicate/out-of-order data cannot corrupt official history. | Consistent. |
| DIV-FR-021 | Enduring | Archive/cold retrieval and hash verification. | Enduring. |
| DIV-FR-022 | Available | Retained records retrievable for inspection within accepted time. | Available. |
| DIV-FR-023 | Audit review | Review annotations do not mutate original events. | Review integrity. |
| DIV-FR-024 | Retention/hold | Legal hold/retention blocks premature destruction. | Governance. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| deriveDataIntegrityTestSuite() | Validation | data classes; risk; audit/Vault architecture | Baselines current | Selects integrity/tamper/version/archive tests | DataIntegritySuite | DataIntegritySuiteDerived |
| runAuditTamperDetectionTest() | Validation isolated env | audit scope; tamper scenario | Non-production copy | Applies simulated tamper and verifier | TamperTestResult | AuditTamperTestCompleted |
| verifyVaultCanonicalization() | Automated validation | test vectors; engine version | Vectors approved | Compares expected bytes/digest | CanonicalizationResult | VaultCanonicalizationVerified |
| verifyRecordCorrectionHistory() | Validation | record; correction scenario | Record released | Checks old unchanged/new linked/audited | IntegrityTestResult | RecordCorrectionHistoryVerified |
| verifyArchiveRetrievalIntegrity() | Validation/DR | archived record/evidence set | Archive available | Retrieves and compares hashes/manifests | ArchiveIntegrityResult | ArchiveRetrievalVerified |
| approveDataIntegrityQualification() | QA/Validation | suite/results/deviations | Critical tests complete | Freezes qualification | DataIntegrityQualification | DataIntegrityQualificationApproved |


# 5. Validation State / Control Model

```text
CREATE → MODIFY/CORRECT → SIGN/RELEASE → ARCHIVE → RETRIEVE; AT EACH STAGE AUDIT/VERSION/HASH/LINEAGE → TAMPER TEST → QUALIFICATION
```

# 6. Data / Evidence Model

`data_integrity_test_profile`: data class, lifecycle, threats, controls, tests.
`tamper_test_execution`: isolated snapshot, tamper action, verifier version, detection evidence.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/data-integrity/suites`
- `POST /validation/v1/data-integrity/tamper-tests`
- `POST /validation/v1/data-integrity/{id}/approve`

# 8. UI / Validation Workspace

1. Data Integrity Matrix
2. Audit Tamper
3. Vault Canonicalization
4. Corrections
5. Archive Retrieval
6. Qualification

# 9. Events

- `AuditTamperTestCompleted`
- `VaultCanonicalizationVerified`
- `ArchiveRetrievalVerified`
- `DataIntegrityQualificationApproved`

# 10. Mandatory Test / Evidence Catalogue

- audit row modified/deleted
- hash chain break
- evidence replaced
- failed result retained
- correction history
- cold archive
- late Edge chronology

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

A representative regulated record can be followed through its complete lifecycle and protected-history tampering is prevented or detected.

# 13. Claude Code / Codex Prohibitions

- Never validate data integrity only by UI review.
- Never tamper-test production data.
- Never remove original failure after retest.
- Never rely on backup alone as immutable-history proof.


