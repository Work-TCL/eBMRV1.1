# US eBMR / eDHR Regulated Manufacturing Platform
## Document 28 — Nonconformance Management — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QMS-003
**Parent Documents:** Documents 01–25
**Primary Dependencies:** Materials, Device History, QC, Supplier Quality, CAPA
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

Define identification, segregation, evaluation, controlled disposition and verification of nonconforming material, components, device units and finished product.

# 2. Actors

- Operator/Inspector
- QC
- QA
- Engineering
- Warehouse
- Supplier Quality
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| NCR-FR-001 | NCR initiation | Create nonconformance for material/component/subassembly/device/packaging/finished output. | Scope exact. |
| NCR-FR-002 | Automatic source | Failed QC/test/inspection can create NCR candidate. | Immediate. |
| NCR-FR-003 | Segregation | Hold/segregate exact lots/serials/quantities electronically and physically. | Prevent use. |
| NCR-FR-004 | Requirement violated | Reference exact specification/test/requirement and objective evidence. | Clear. |
| NCR-FR-005 | Evaluation | Assess severity, usability, quality/safety/performance and investigation need. | Risk. |
| NCR-FR-006 | Disposition | Rework, repair where allowed, return, scrap/destroy, concession/use-as-is only if policy permits. | Controlled. |
| NCR-FR-007 | Use-as-is restriction | Default restricted; technical/Quality justification and authority required. | Bounded. |
| NCR-FR-008 | Rework route | Use approved route/work instruction; original failure preserved. | Trace. |
| NCR-FR-009 | Reinspection/retest | Required after rework according to approved criteria; prior failure remains. | Evidence. |
| NCR-FR-010 | Supplier link | Link source supplier/material and SCAR if needed. | Supplier quality. |
| NCR-FR-011 | Batch/release impact | Affected scope creates release blocker/hold. | No bypass. |
| NCR-FR-012 | CAPA trigger | Significant/repeat NCR can require CAPA. | Systemic. |
| NCR-FR-013 | Partial scope | Disposition exact units/serials/quantity without changing unaffected product. | Device scale. |
| NCR-FR-014 | Scrap/destruction | Integrate inventory/destruction transaction. | Quantity closure. |
| NCR-FR-015 | Approval | Quality/engineering approval by disposition/profile. | Independent. |
| NCR-FR-016 | Reopen | New evidence can reopen. | History. |
| NCR-FR-017 | Trend | Defect codes trend by process/product/supplier. | Metrics. |
| NCR-FR-018 | Export | Complete evidence/disposition/rework/retest export. | Inspection-ready. |

# 4. State / Workflow Model

```text
OPEN → SEGREGATED → EVALUATION → DISPOSITION_PENDING
     → REWORK / RETURN / SCRAP / CONDITIONAL_DISPOSITION
     → VERIFICATION → QA_CLOSURE → CLOSED
```

# 5. Data Model

## `nonconformance_record`
```text
id uuid PK
quality_event_id uuid UNIQUE
ncr_number varchar(120) UNIQUE
scope_type varchar(50)
scope_records jsonb
requirement_ref jsonb
defect_code varchar(100)
severity varchar(40)
state varchar(50)
version bigint
```

## `ncr_disposition`
- affected scope subset
- quantity/serials
- disposition
- justification
- approver signatures
- rework route
- follow-up test requirements


# 6. APIs

- `POST /qms/v1/nonconformances`
- `POST /qms/v1/nonconformances/{id}/segregate`
- `POST /qms/v1/nonconformances/{id}/evaluate`
- `POST /qms/v1/nonconformances/{id}/disposition`
- `POST /qms/v1/nonconformances/{id}/verify`
- `POST /qms/v1/nonconformances/{id}/close`

All mutation APIs use the GxP Mutation Gateway, optimistic concurrency and stable error codes.

# 7. UI Screens

1. NCR Dashboard
2. Initiation
3. Affected Scope
4. Segregation
5. Evaluation
6. Disposition
7. Rework/Retest
8. Supplier/CAPA Links
9. Closure
10. Audit

# 8. Events

- `NonconformanceOpened`
- `NonconformingProductSegregated`
- `NCRDispositionApproved`
- `NCRReworkStarted`
- `NCRReinspectionCompleted`
- `NCRClosed`

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
services/gxp-api/src/modules/qms/nonconformance-management/
apps/ebmr_frappe/ebmr/qms/nonconformance-management/
contracts/events/qms/nonconformance-management/
validation/requirements/qms/nonconformance-management/
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

- failed device test
- material NCR
- partial serial disposition
- use-as-is denied/approved
- rework/retest
- scrap
- supplier return
- CAPA trigger
- release block

# 14. Acceptance Criteria

Nonconforming product cannot return to usable/released status without approved disposition and required verification.

# 15. Codex / Claude Code Rules

- Never make use-as-is a generic convenience button.
- Never overwrite failed test after rework.
- Never remove affected serial from NCR without controlled correction.

# 16. Stable Error Codes
`NCR_SCOPE_REQUIRED`, `SEGREGATION_REQUIRED`, `DISPOSITION_NOT_ALLOWED`, `USE_AS_IS_NOT_AUTHORIZED`, `REWORK_ROUTE_REQUIRED`, `REINSPECTION_REQUIRED`, `NCR_CLOSURE_BLOCKED`.
