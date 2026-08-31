# US eBMR / eDHR Regulated Manufacturing Platform
## Document 29 — Change Control — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QMS-004
**Parent Documents:** Documents 01–25
**Primary Dependencies:** Product/Recipe/Document/Training/Validation/Software Release
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze
**Target Market:** United States
**V1 Vertical:** Drug–Device Combination Products (DDCP)
**Future Profiles:** Medical Devices, Pharmaceuticals
**Date:** 2026-08-20

---

# Implementation Standard

This document is implementation-grade. Codex/Claude Code shall not invent regulated behavior that is absent from this specification.

Every module must implement, where applicable: state machine, roles/SoD, e-signatures, audit, data model, DB constraints, APIs, stable errors, events, UI, failure handling, observability, retention, migrations, tests and requirement traceability.

# Shared Quality Event Kernel

All QMS records share:

```text
quality_event_id
event_type
tenant_id
site_id
source_type/source_id/source_version
severity/risk
state
owner/investigator
due_date
product/batch/material/device/equipment/supplier/document links
related_quality_event_ids[]
evidence_refs[]
created_at/closed_at
version
```

The common kernel does not force identical workflows.

# Regulatory Engineering Basis

Current verified anchors:
- 21 CFR §211.192 requires Quality review before release and thorough investigation of unexplained discrepancies/specification failures, extending to other associated batches/products where appropriate, with written conclusions and follow-up.
- Current 21 CFR Part 820 is the QMSR, effective February 2, 2026, and incorporates ISO 13485:2016 by reference for device quality-system requirements.
- This specification summarizes engineering controls and does not reproduce copyrighted ISO text.

Official references:
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-J/section-211.192
- https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr

# 1. Objective

Define controlled evaluation, approval, implementation, validation, effective dating and closure of regulated product/process/system changes.

# 2. Actors

- Change Requester
- Process Owner
- QA
- Regulatory
- Validation
- Engineering/IT
- Document Controller
- Training Coordinator
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| CHG-FR-001 | Change request | Create change for product/process/recipe/spec/material/source/equipment/facility/software/document/method/label/supplier. | Broad control. |
| CHG-FR-002 | Classification | Temporary/permanent and risk class using approved methodology. | Routing. |
| CHG-FR-003 | Current/proposed state | Document current state, proposed state and reason/business need. | Clear intent. |
| CHG-FR-004 | Affected objects | Link exact object versions potentially affected. | Impact graph. |
| CHG-FR-005 | Regulatory impact | Qualified Regulatory/Quality assesses filing/notification/approval/reportability implications. | Human authority. |
| CHG-FR-006 | Quality impact | Assess product quality/safety/performance. | Quality. |
| CHG-FR-007 | Validation impact | Assess process/equipment/software validation/requalification. | Validated state. |
| CHG-FR-008 | Risk assessment | Create/link risk assessment when required. | Risk based. |
| CHG-FR-009 | Training impact | Identify documents/roles/users needing training before effective date. | Readiness. |
| CHG-FR-010 | Open-batch/inventory impact | Assess open batches, released stock, materials, labels and transition plan. | Cutover safe. |
| CHG-FR-011 | Data/migration impact | Assess schema/master-data/migration/backfill/data-integrity requirements. | System safe. |
| CHG-FR-012 | Implementation plan | Tasks, owners, dependencies, evidence, target/effective date, rollback. | Executable. |
| CHG-FR-013 | Pre-approval | Quality/technical/regulatory approvals before implementation except controlled emergency path. | Controlled. |
| CHG-FR-014 | Emergency change | Time-bounded emergency path with reason/risk and mandatory retrospective review. | No loophole. |
| CHG-FR-015 | Execution evidence | Tasks link PR/build/release/equipment/document evidence. | Trace. |
| CHG-FR-016 | Verification/validation | Verify implemented state and required test/qualification before use. | Qualified. |
| CHG-FR-017 | Effective date | New state usable only after prerequisites/training/approval complete. | Controlled activation. |
| CHG-FR-018 | Post-implementation review | Verify intended result/no adverse effect when required. | Effectiveness. |
| CHG-FR-019 | Rollback | Controlled action preserving both versions/evidence. | History. |
| CHG-FR-020 | Closure | Close after implementation, verification, training/validation and follow-up. | Complete. |
| CHG-FR-021 | Cancellation | Retain reason/approval/history. | Integrity. |
| CHG-FR-022 | Software traceability | Software changes link requirement, code PR, tests, SBOM, validation impact, deployment. | CSA/CSV. |
| CHG-FR-023 | Master linkage | New product/recipe/spec/doc version can reference governing Change Control. | Trace. |
| CHG-FR-024 | Export | Before/after, impacts, approvals and evidence exportable. | Inspection-ready. |

# 4. State / Workflow Model

```text
DRAFT → IMPACT_ASSESSMENT → RISK_REVIEW → APPROVAL
     → IMPLEMENTATION → VERIFICATION/VALIDATION
     → EFFECTIVE → POST_IMPLEMENTATION_REVIEW → CLOSED
EMERGENCY → IMPLEMENT → RETROSPECTIVE_REVIEW
```

# 5. Data Model

## `change_control`
```text
id uuid PK
quality_event_id uuid UNIQUE
change_number varchar(120) UNIQUE
change_type varchar(50)
classification varchar(40)
current_state jsonb
proposed_state jsonb
state varchar(50)
risk_ref uuid
regulatory_impact jsonb
validation_impact jsonb
training_impact jsonb
effective_at timestamptz
version bigint
```

## `change_affected_object`
- object type/ID/version
- impact category
- action required

## `change_task`
- owner
- task/evidence
- dependency
- due date/status


# 6. APIs

- `POST /qms/v1/changes`
- `POST /qms/v1/changes/{id}/impact`
- `POST /qms/v1/changes/{id}/approve`
- `POST /qms/v1/changes/{id}/tasks`
- `POST /qms/v1/changes/{id}/implement`
- `POST /qms/v1/changes/{id}/verify`
- `POST /qms/v1/changes/{id}/make-effective`
- `POST /qms/v1/changes/{id}/close`

All mutation APIs use the GxP Mutation Gateway, optimistic concurrency and stable error codes.

# 7. UI Screens

1. Change Dashboard
2. Request
3. Affected Objects
4. Impact Assessments
5. Risk
6. Implementation Plan
7. Validation/Training
8. Approvals
9. Execution Evidence
10. Post-Implementation Review
11. Closure

# 8. Events

- `ChangeRequested`
- `ChangeImpactAssessed`
- `ChangeApproved`
- `ChangeImplementationStarted`
- `ChangeValidationCompleted`
- `ChangeMadeEffective`
- `ChangeClosed`
- `EmergencyChangeOpened`

# 9. Authorization / Signature / Audit

- Server-side Policy Service controls state transitions.
- High-risk approval/closure uses regulated e-signature when applicable.
- Corrections create new versions and preserve original values/evidence.
- Source batch/QC/material/equipment records are never edited from QMS screens.
- Extension, cancellation, reopen and disposition actions are audited.

# 10. Failure / Recovery

- DB unavailable: no regulated transition succeeds.
- Policy/signature unavailable: required action fails closed.
- Notification failure: authoritative state may commit; outbox retries notifications.
- Stale version: reject and refresh.
- Worker restart: due-date/escalation processing resumes from persisted state.

# 11. Repository Structure

```text
services/gxp-api/src/modules/qms/change-control/
apps/ebmr_frappe/ebmr/qms/change-control/
contracts/events/qms/change-control/
validation/requirements/qms/change-control/
```

# 12. Implementation Sequence

1. Core record and state machine.
2. Source/evidence linking.
3. Authorization and signature policies.
4. Investigation/action business rules.
5. Cross-module links and release blockers.
6. UI and dashboards.
7. Events/outbox and notifications.
8. Export and audit views.
9. Negative/failure/concurrency tests.
10. Validation traceability.

# 13. Test Catalogue

- recipe change
- software schema change
- supplier change
- label change
- open batch impact
- training prerequisite
- emergency change
- rollback
- cancel
- post-implementation failure

# 14. Acceptance Criteria

No GxP-relevant permanent master/system/process change becomes effective outside approved Change Control when policy defines it as change-controlled.

# 15. Codex / Claude Code Rules

- Never patch production GxP behavior outside Change Control.
- Never use emergency path to skip retrospective review.
- Never make new master effective before required validation/training.

# 16. Stable Error Codes
`CHANGE_IMPACT_INCOMPLETE`, `REGULATORY_REVIEW_REQUIRED`, `VALIDATION_INCOMPLETE`, `TRAINING_INCOMPLETE`, `CHANGE_NOT_APPROVED`, `EFFECTIVE_DATE_BLOCKED`.
