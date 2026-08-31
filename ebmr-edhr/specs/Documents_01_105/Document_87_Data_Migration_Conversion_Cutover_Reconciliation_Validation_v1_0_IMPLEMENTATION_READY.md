# US eBMR / eDHR Regulated Manufacturing Platform
## Document 87 — Data Migration, Conversion, Cutover & Reconciliation Validation — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-009  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 06, 30, 69–72, 76; customer legacy systems  
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

Define validated migration of legacy GxP/master/record/evidence data with source snapshots, controlled transformations, identity/provenance preservation, reconciliation and cutover.

# 2. Actors / Components

- Migration Engineer
- Data Owner
- Validation
- QA
- System Owner
- Legacy System Owner
- Records Manager

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| MIGV-FR-001 | Migration plan | Define source, scope, cutoff, transformations, owners and acceptance. | Controlled conversion. |
| MIGV-FR-002 | Source snapshot | Identify/freeze exact source export/cutoff/hash. | Reproducibility. |
| MIGV-FR-003 | Profiling | Assess completeness, duplicates, orphans, invalid values. | Risk awareness. |
| MIGV-FR-004 | Mapping | Source→target entity/field/UOM/status mapping versioned/approved. | Clarity. |
| MIGV-FR-005 | Transformation code | Scripts/version reviewed and testable. | Controlled logic. |
| MIGV-FR-006 | Regulated history | Preserve needed history/provenance or controlled legacy archive. | Continuity. |
| MIGV-FR-007 | Identity mapping | Legacy ID→new ID mapping retained. | Trace. |
| MIGV-FR-008 | Reference integrity | Relationships reconciled after import. | Integrity. |
| MIGV-FR-009 | Counts/totals | Counts, hashes, quantities/control totals by data class. | Completeness. |
| MIGV-FR-010 | Sampling/full compare | Use full automated compare for critical fields where feasible, otherwise risk-based sampling. | Evidence. |
| MIGV-FR-011 | Attachments | Evidence object counts/hashes/links reconciled. | Evidence. |
| MIGV-FR-012 | Legacy signatures | Preserve/migrate signature evidence without recreating historic signature as new signing. | Integrity. |
| MIGV-FR-013 | Legacy audit | Import provenance-marked audit/history or retain accessible legacy archive. | History. |
| MIGV-FR-014 | Timezones | Source timezone/precision semantics explicitly handled. | Chronology. |
| MIGV-FR-015 | Decimal/UOM | Conversion precision and UOM rules tested. | Accuracy. |
| MIGV-FR-016 | Dry runs | Material migration uses rehearsal(s) based on risk/scale. | Cutover confidence. |
| MIGV-FR-017 | Cutover delta | Final delta/change-freeze strategy reconciles late changes. | Completeness. |
| MIGV-FR-018 | Errors | Rejected records retained with reason/disposition. | No silent loss. |
| MIGV-FR-019 | Rollback | Fallback strategy avoids losing post-cutover transactions. | Operational safety. |
| MIGV-FR-020 | Approval | Final migration accepted only after reconciliation/deviation disposition. | Gate. |
| MIGV-FR-021 | Legacy access | Post-cutover legacy read-only retrieval strategy documented. | Inspection. |
| MIGV-FR-022 | Evidence retention | Scripts/config/logs/source hashes/reconciliations retained. | Audit. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createMigrationValidationPlan() | Data/Validation | source; target; scope; cutoff; mappings; reconciliation rules | Migration approved | Creates versioned migration plan | MigrationValidationPlan | MigrationValidationPlanCreated |
| profileMigrationSource() | Migration tool | source snapshot/ref | Authorized read-only | Produces data-quality/count/orphan profile | SourceProfile | MigrationSourceProfiled |
| executeMigrationDryRun() | Migration service | plan/version; snapshot; sandbox | Plan approved; target isolated | Runs transformation/import and record outcomes | MigrationRun | MigrationDryRunCompleted |
| reconcileMigrationRun() | Validation/Data | migration run; reconciliation profile | Run complete | Compares counts/hashes/totals/critical fields/files | MigrationReconciliation | MigrationReconciled |
| approveMigrationCutover() | System Owner/QA | final run; reconciliation; deviations; signature | Thresholds met | Approves production cutover evidence | MigrationAcceptance | MigrationAccepted |
| verifyLegacyRecordTrace() | Inspection test | legacy_id | Mapping/archive available | Returns new/archive refs and provenance | LegacyTraceResult | LEGACY_TRACE_MISSING |


# 5. Validation State / Control Model

```text
SOURCE SNAPSHOT/PROFILE → MAPPING/TRANSFORM → DRY RUN → RECONCILE → FINAL CUTOVER/DELTA → RECONCILE → ACCEPT/ROLLBACK
```

# 6. Data / Evidence Model

`migration_validation_plan`: source/target, scope, cutoff, mappings, transform version, reconciliation rules, acceptance.
`migration_run`: source hash, scripts/config, counts, errors, target refs.
`migration_reconciliation`: counts/hashes/totals/critical-field comparisons/files/deviations.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/migrations/plans`
- `POST /validation/v1/migrations/runs`
- `POST /validation/v1/migrations/{id}/reconcile`
- `POST /validation/v1/migrations/{id}/approve`

# 8. UI / Validation Workspace

1. Migration Plan
2. Source Profile
3. Dry Runs
4. Reconciliation
5. Cutover
6. Legacy Trace

# 9. Events

- `MigrationSourceProfiled`
- `MigrationDryRunCompleted`
- `MigrationReconciled`
- `MigrationAccepted`

# 10. Mandatory Test / Evidence Catalogue

- duplicate legacy ID
- timezone conversion
- historic signature
- missing attachment
- quantity mismatch
- rejected record
- final delta

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

Every migrated regulated record/evidence can be reconciled to a controlled legacy source snapshot and transformation provenance.

# 13. Claude Code / Codex Prohibitions

- Never recreate legacy signature as a new platform signature.
- Never silently drop failed conversion record.
- Never validate migration by count alone.
- Never mutate source during extraction.


