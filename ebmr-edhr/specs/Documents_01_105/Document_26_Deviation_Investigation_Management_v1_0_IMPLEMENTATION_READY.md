# US eBMR / eDHR Regulated Manufacturing Platform
## Document 26 — Deviation & Investigation Management — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QMS-001
**Parent Documents:** Documents 01–25
**Primary Dependencies:** Batch, QC/OOS, CAPA, Change Control, Review/Release
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

Define controlled planned/unplanned deviation handling from detection through containment, investigation, impact, disposition, follow-up and Quality closure.

# 2. Actors

- Production/Quality Event Reporter
- Deviation Investigator
- QA Reviewer/Approver
- QC
- Engineering
- Supplier Quality
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| DEV-FR-001 | Deviation initiation | Create planned/unplanned deviation from batch, QC, material, equipment, environment, supplier, document or system source. | Every deviation attributable. |
| DEV-FR-002 | Automatic source | Rules/Batch/QC/Edge can create deviation candidate with exact source event/version. | No retyping required. |
| DEV-FR-003 | Triage | Classify planned/unplanned, severity, product impact and investigation priority using released methodology. | Consistent routing. |
| DEV-FR-004 | Immediate correction | Record immediate correction separately from root-cause/CAPA. | Containment not confused with systemic action. |
| DEV-FR-005 | Containment | Place batch/material/equipment/area on hold where required. | Risk bounded. |
| DEV-FR-006 | Investigator | Assign qualified investigator, owner and due date; reassignment audited. | Ownership clear. |
| DEV-FR-007 | Investigation plan | Define records, interviews, batches/products and technical evidence to review. | Structured investigation. |
| DEV-FR-008 | Cross-batch investigation | Extend investigation to associated batches/products when relevant. | Supports §211.192. |
| DEV-FR-009 | Evidence graph | Link batch, audit, QC, equipment, materials, environment, supplier and files. | Complete evidence. |
| DEV-FR-010 | Root cause | Support configurable root-cause methods and 'no assignable cause' when justified. | No forced fake cause. |
| DEV-FR-011 | Impact assessment | Assess quality, patient/user, released/distributed product, validation, data integrity and regulatory impact. | Complete impact. |
| DEV-FR-012 | Disposition | Continue/hold/reject/rework/reprocess/additional test/destroy/field-action assessment according to policy. | Controlled outcome. |
| DEV-FR-013 | CAPA need | Record CAPA required/not required with rationale. | Systemic action decision. |
| DEV-FR-014 | Change need | Link Change Control for permanent process/spec/system/document changes. | Controlled change. |
| DEV-FR-015 | Training need | Create retraining/qualification actions where appropriate. | Training integrated. |
| DEV-FR-016 | Planned deviation | Pre-approved, bounded by scope/date/batches; cannot become permanent alternative process. | Temporary exception. |
| DEV-FR-017 | Extension | Due-date extension requires reason, risk review and approval; old due date retained. | No silent aging. |
| DEV-FR-018 | Closure | Require investigation, impact, disposition and mandatory linked actions before QA closure. | No premature closure. |
| DEV-FR-019 | QA signature | Final conclusion/disposition/closure signed according to policy. | Independent Quality authority. |
| DEV-FR-020 | Reopen | New evidence reopens through controlled action preserving prior closure. | History. |
| DEV-FR-021 | Recurrence | Find similar prior deviations by code/product/process/equipment/root cause. | Trend. |
| DEV-FR-022 | Release integration | Open/critical deviations create review/release blockers based on rule. | No release bypass. |
| DEV-FR-023 | Escalation | Critical/overdue deviation notifications/escalation. | Timely handling. |
| DEV-FR-024 | Export | Written investigation with conclusions/follow-up and evidence exportable. | Inspection-ready. |

# 4. State / Workflow Model

```text
OPEN → TRIAGE → CONTAINMENT → INVESTIGATION
     → IMPACT_ASSESSMENT → DISPOSITION → QA_REVIEW → CLOSED
CLOSED → REOPENED (controlled)
PLANNED: DRAFT → PREAPPROVED → ACTIVE → EXPIRED/CLOSED
```

# 5. Data Model

## `deviation_record`
```text
id uuid PK
quality_event_id uuid UNIQUE
deviation_number varchar(120) UNIQUE
deviation_type varchar(40)
source_type/source_id/source_version
severity varchar(40)
state varchar(50)
owner_subject_id uuid
investigator_subject_id uuid
planned boolean
planned_scope jsonb
immediate_correction jsonb
containment jsonb
root_cause jsonb
impact_assessment jsonb
disposition_code varchar(80)
due_date timestamptz
version bigint
closed_at timestamptz
```
Indexes: `(tenant_id,state,due_date)`, `(site_id,severity,state)`.

## `deviation_impact_link`
- impacted record type/ID/version
- impact category
- hold/disposition reference


# 6. APIs

- `POST /qms/v1/deviations`
- `POST /qms/v1/deviations/{id}/triage`
- `POST /qms/v1/deviations/{id}/contain`
- `POST /qms/v1/deviations/{id}/investigation`
- `POST /qms/v1/deviations/{id}/impact`
- `POST /qms/v1/deviations/{id}/disposition`
- `POST /qms/v1/deviations/{id}/extend`
- `POST /qms/v1/deviations/{id}/close`
- `POST /qms/v1/deviations/{id}/reopen`

All mutation APIs use the GxP Mutation Gateway, optimistic concurrency and stable error codes.

# 7. UI Screens

1. Deviation Dashboard
2. Initiation/Triage
3. Containment
4. Investigation & Evidence
5. Root Cause
6. Impact Assessment
7. Disposition
8. Linked CAPA/Change
9. QA Closure
10. Audit/History

# 8. Events

- `DeviationOpened`
- `DeviationContained`
- `DeviationInvestigationStarted`
- `DeviationImpactAssessed`
- `DeviationCAPARequired`
- `DeviationDispositionApproved`
- `DeviationClosed`
- `DeviationReopened`

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
services/gxp-api/src/modules/qms/deviation-and-investigation-management/
apps/ebmr_frappe/ebmr/qms/deviation-and-investigation-management/
contracts/events/qms/deviation-and-investigation-management/
validation/requirements/qms/deviation-and-investigation-management/
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

- automatic batch deviation
- planned deviation expiry
- cross-batch investigation
- no assignable cause
- CAPA required
- change required
- extension
- close with missing impact denied
- reopen
- release blocker
- SoD
- export

# 14. Acceptance Criteria

Representative manufacturing discrepancy is traceable from exact source step/result through related-batch investigation, impact/disposition, CAPA/change links and QA-signed closure.

# 15. Codex / Claude Code Rules

- Never use deviation as free-text note only.
- Never allow planned deviation to become permanent process.
- Never close because due date expired.
- Never edit source evidence from deviation module.

# 16. Stable Error Codes
`DEVIATION_SOURCE_INVALID`, `CONTAINMENT_REQUIRED`, `INVESTIGATION_INCOMPLETE`, `IMPACT_REQUIRED`, `DISPOSITION_REQUIRED`, `PLANNED_DEVIATION_EXPIRED`, `QA_CLOSURE_REQUIRED`.
