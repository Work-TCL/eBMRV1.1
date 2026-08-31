# US eBMR / eDHR Regulated Manufacturing Platform
## Document 14 — Review-by-Exception & QA Review Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EBMR-005  
**Parent Documents:** Document 01 v1.1; Document 02 v1.0  
**Primary Dependencies:** Documents 03–13; QMS; QC; Materials; Packaging; Release  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products (DDCP)  
**Future Profiles:** Medical Devices, Pharmaceuticals  
**Date:** 2026-08-20

---


# Implementation Standard Applied to This Document

This specification is intended to be sufficient for Codex, Claude Code, or a human development team to implement the module with minimal interpretation.

Where applicable, the document therefore defines:

- objective and scope;
- non-goals/exclusions;
- actors/roles;
- functionality and sub-functionality;
- workflows and state machines;
- business rules;
- authorization and segregation of duties;
- electronic-signature behavior;
- audit behavior;
- entities, fields, relationships and ownership;
- PostgreSQL/Frappe storage boundaries;
- suggested tables, indexes and constraints;
- APIs and stable error codes;
- events/outbox contracts;
- UI screens/actions;
- integrations;
- calculations/validations;
- concurrency/idempotency;
- failure/recovery behavior;
- configuration;
- observability;
- retention/archival;
- migrations;
- performance/scaling;
- repository/module structure;
- implementation sequence;
- test cases;
- acceptance criteria;
- requirement traceability;
- explicit coding-agent rules.

If a future implementation decision changes regulated behavior and is not defined here, the coding agent shall raise a specification gap rather than inventing behavior.


# 1. Objective

Define a QA review system that reduces review effort through exception prioritization while preserving full-record access and independent completeness checks.

Review-by-exception must never mean “QA only sees exceptions.”

# 2. Architecture

```text
Production Complete
      ↓
Review Snapshot / Package
      ├── Completeness Engine
      ├── Exception Index
      ├── Audit Review
      ├── QC Summary
      ├── Material/Genealogy
      ├── Equipment/Environment
      ├── Packaging/Label
      └── Yield/Reconciliation
      ↓
QA / Specialist Review
      ↓
Controlled Action Requests
      ↓
Review Complete + E-Sign
      ↓
Release Eligibility
```

# 3. Functional Requirements

| ID | Functionality | Detailed behavior | Acceptance intent |
|---|---|---|---|
| RBE-FR-001 | Review package | At Production Complete create versioned QA review package referencing stable batch record version and current exception index. | QA reviews defined scope. |
| RBE-FR-002 | Full-record access | Review-by-exception is an aid, not a substitute for access to complete record/evidence. | No hidden record. |
| RBE-FR-003 | Exception index | Aggregate deviations, OOS/OOT, NCRs, parameter excursions, manual overrides, corrections, missing evidence, failed integrations, late steps, equipment/material/environment issues, reconciliation/yield variance and signature issues. | Critical issues visible. |
| RBE-FR-004 | Severity | Assign severity/risk/category using released rule/QMS classification; QA may reclassify only through controlled reason/authority. | Prioritization controlled. |
| RBE-FR-005 | Completeness engine | Independently verify all applicable steps, required values, evidence, signatures, QC, materials, genealogy and calculations are present. | Missing data cannot be hidden because no exception was generated. |
| RBE-FR-006 | Changed-value review | List every controlled correction/superseded value with old/new, reason, actor, signature and impact. | Corrections obvious. |
| RBE-FR-007 | Manual override review | List automated-to-manual fallback, overrides, waived checks and exceptional authorizations. | Non-routine activity visible. |
| RBE-FR-008 | Audit-trail review | Provide filtered audit view for critical records/fields and allow QA to document review status separately. | Part 11/data-integrity support. |
| RBE-FR-009 | Signature review | Check required signatures exist, are valid, bound to current versions and satisfy SoD. | No invalid signature chain. |
| RBE-FR-010 | QC review | Summarize required tests, accepted results, superseded results, OOS/OOT and pending items. | QC status clear. |
| RBE-FR-011 | Material review | Summarize material lots, quality status at use, deviations, substitutions, reconciliation and expired/retest issues. | Material impact visible. |
| RBE-FR-012 | Equipment review | Show equipment used, eligibility at operation time, calibration/qualification/cleaning exceptions. | Equipment evidence. |
| RBE-FR-013 | Environment/sterile review | Where applicable show EM excursions, interventions, sterilization/filter/hold-time blockers. | Sterile DDCP review. |
| RBE-FR-014 | Genealogy completeness | Confirm required constituent/material/component/serial relationships exist and no unresolved gaps. | Release trace complete. |
| RBE-FR-015 | Packaging/label review | Show line clearance, label version, issuance/reconciliation, UDI, packaging inspection and discrepancies. | Packaging release evidence. |
| RBE-FR-016 | Yield/reconciliation | Show theoretical/actual yield, phase calculations and material/label/packaging reconciliation with variance status. | Numerical blockers visible. |
| RBE-FR-017 | Reviewer comment | QA can add structured comment/question linked to exact record/exception/evidence; comment is audited. | Review dialogue attributable. |
| RBE-FR-018 | Return for controlled action | QA can request correction/investigation/additional evidence through defined action, not edit production data directly. | Separation maintained. |
| RBE-FR-019 | Review checklist | Product/profile-specific checklist is versioned and snapshot-bound to review package. | Review expectations stable. |
| RBE-FR-020 | Review completion | Reviewer cannot complete until required checklist items and assigned exceptions are dispositioned or explicitly accepted according to policy. | No incomplete closure. |
| RBE-FR-021 | Multi-reviewer | Support specialist review sections (QC, Device Quality, Drug Quality, Sterile, Packaging) and final QA consolidation where required. | DDCP cross-functional review. |
| RBE-FR-022 | Review SoD | Review/release roles and prior execution participation evaluated through Document 07. | Independent review. |
| RBE-FR-023 | Review signature | Review completion uses regulated e-signature when in Part 11 scope; binds review package version/hash. | Exact review signed. |
| RBE-FR-024 | Review re-open | New evidence/correction after review completion invalidates/reopens affected review and requires re-evaluation/signature. | No stale review. |
| RBE-FR-025 | Risk-based routing | Rules may route high-risk exceptions to additional reviewers but cannot reduce mandatory customer/regulatory review requirements. | Escalation safe. |
| RBE-FR-026 | Search/trending | QA dashboard can filter batches by exception class, review age, product/site and blockers. | Operational quality management. |
| RBE-FR-027 | Export | Review package included in final batch export with checklist, reviewer comments, signatures and exception disposition. | Inspection-ready. |
| RBE-FR-028 | Performance | Exception index generated asynchronously but review cannot falsely show 'complete' until index/completeness status is current. | No stale green status. |
| RBE-FR-029 | Integrity health | Audit/evidence integrity failures appear as review blockers. | Tamper signal impacts release. |
| RBE-FR-030 | Review record retention | Review comments/checklists/signatures retained with batch record. | Long-term evidence. |

# 4. Data Model

## `qa_review_package`

```text
id uuid PK
tenant_id uuid
batch_id uuid
batch_version bigint
record_hash char(64)
checklist_version_id uuid
exception_index_version bigint
completeness_status varchar(40)
state varchar(40)
version bigint
created_at timestamptz
completed_at timestamptz
```

## `qa_review_item`
- package ID
- category
- source record/event
- severity
- status
- assigned reviewer
- disposition
- comment
- evidence refs
- completed signature

## `qa_review_comment`
- exact source object/version
- author
- type: QUESTION / COMMENT / REQUEST_ACTION / RESPONSE
- text
- timestamp
- status

# 5. Review States

`CREATED → INDEXING → READY_FOR_REVIEW → IN_REVIEW → ACTION_REQUIRED → IN_REVIEW → REVIEW_COMPLETE`

If source record changes:
`REVIEW_COMPLETE → INVALIDATED/REOPENED`.

# 6. Exception Sources

- QMS quality events;
- Rules Engine failures/warnings;
- Audit correction/override events;
- QC result status;
- missing expected evidence;
- equipment/material eligibility exceptions;
- temporal/time-limit breach;
- label reconciliation;
- yield/reconciliation;
- integration failures;
- integrity verification failures.

# 7. APIs

- `POST /qa-review/v1/batches/{batchId}/packages`
- `GET /qa-review/v1/packages/{id}`
- `GET /qa-review/v1/packages/{id}/exceptions`
- `POST /qa-review/v1/packages/{id}/comments`
- `POST /qa-review/v1/items/{id}/request-action`
- `POST /qa-review/v1/items/{id}/disposition`
- `POST /qa-review/v1/packages/{id}/complete`
- `POST /qa-review/v1/packages/{id}/reindex`
- `GET /qa-review/v1/dashboard`

# 8. UI

Main screen sections:
1. Batch Header / Product / Recipe
2. Release Blockers
3. Exception Summary by severity/category
4. Corrections & Overrides
5. QC/OOS/OOT
6. Materials
7. Equipment/Environment
8. Packaging/Labels
9. Genealogy
10. Yield/Reconciliation
11. Signatures
12. Audit Trail
13. Full Record
14. Review Checklist
15. Reviewer Comments / Actions

# 9. Review Completeness Algorithm

Review package cannot be `READY_FOR_REVIEW` until:
- exception indexing completed at current batch version;
- completeness engine completed;
- required integration states resolved enough to determine status;
- batch hash/version unchanged during index generation.

# 10. Controlled Action

QA cannot edit result.
QA requests:
- correction;
- deviation/investigation;
- additional evidence;
- repeat/retest request through QMS/QC policy;
- rework/reprocess assessment.

Source module performs action through Mutation Gateway; review package then reindexes.

# 11. Events

- QAReviewPackageCreated
- QAExceptionIndexed
- QAReviewStarted
- QAActionRequested
- QAReviewReopened
- QAReviewCompleted

# 12. Repository Structure

```text
services/gxp-api/src/modules/qa-review/
services/workers/src/qa-indexer/
apps/ebmr_frappe/ebmr/qa_review/
contracts/events/qa-review/
```

# 13. Tests

- no exceptions normal batch;
- hidden missing field caught by completeness;
- correction visible;
- manual override visible;
- unresolved deviation;
- OOS;
- calibration exception;
- environmental excursion;
- label mismatch;
- failed reconciliation;
- invalid signature;
- source changes after review signature;
- multi-reviewer;
- SoD;
- integrity checkpoint failure.

# 14. Acceptance

QA must be able to review representative 500–1000-step batch without manually visiting every field while still having:
- proof of completeness;
- all exceptions;
- full record access;
- audit/signature/evidence drilldown.

# 15. Codex / Claude Rules

Never equate zero indexed exceptions with complete/acceptable batch.
Never let reviewer directly edit production/QC data.
Never keep a completed review valid after underlying signed record changes.

# Regulatory Engineering Basis

This specification is an engineering baseline, not legal advice and not a declaration that the software or a customer configuration is automatically compliant.

Relevant current U.S. regulatory sources include:

- 21 CFR Part 4 — combination-product CGMP framework;
- 21 CFR Part 11 — electronic records/electronic signatures when applicable;
- 21 CFR Parts 210/211 — drug CGMP;
- 21 CFR §211.186 — Master production and control records;
- 21 CFR §211.188 — Batch production and control records;
- 21 CFR §211.103 — Calculation of yield;
- 21 CFR Part 211 Subpart G — Packaging and labeling control;
- 21 CFR Part 820 — QMSR, effective February 2, 2026;
- 21 CFR §820.10 — requirements for a quality management system;
- 21 CFR §820.35 — control of records, including UDI-related records;
- 21 CFR §820.45 — device labeling and packaging controls;
- applicable UDI requirements under 21 CFR Part 830.

The current QMSR incorporates ISO 13485:2016 by reference. This document summarizes engineering implications and does not reproduce copyrighted ISO text.

Reference URLs:
- https://www.law.cornell.edu/cfr/text/21/4.4
- https://www.law.cornell.edu/cfr/text/21/211.186
- https://www.law.cornell.edu/cfr/text/21/211.188
- https://www.law.cornell.edu/cfr/text/21/211.103
- https://www.law.cornell.edu/cfr/text/21/part-211/subpart-G
- https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr
- https://www.law.cornell.edu/cfr/text/21/820.10
- https://www.law.cornell.edu/cfr/text/21/820.35
- https://www.law.cornell.edu/cfr/text/21/820.45
