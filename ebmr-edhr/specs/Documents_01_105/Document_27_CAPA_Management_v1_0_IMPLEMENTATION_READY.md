# US eBMR / eDHR Regulated Manufacturing Platform
## Document 27 — CAPA Management — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QMS-002
**Parent Documents:** Documents 01–25
**Primary Dependencies:** Deviation, OOS/OOT, NCR, Complaint, Audit, Supplier, Change Control
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

Define corrective/preventive action management from verified problem/root cause through action implementation, objective effectiveness verification and Quality closure.

# 2. Actors

- CAPA Owner
- Investigator
- Action Owner
- QA Manager
- Process Owner
- Engineering/IT
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| CAPA-FR-001 | CAPA initiation | Create from deviation/OOS/OOT/NCR/complaint/audit/supplier/risk/trend/security/validation source. | Source explicit. |
| CAPA-FR-002 | Problem statement | Define verified problem and scope separately from solution. | Correct framing. |
| CAPA-FR-003 | Priority | Assign risk/priority and target date. | Risk based. |
| CAPA-FR-004 | Root-cause link | Reference investigation/root cause or proactive prevention rationale. | Evidence based. |
| CAPA-FR-005 | Corrective action | Define action addressing cause of detected issue. | Corrective. |
| CAPA-FR-006 | Preventive/systemic action | Support broader preventive/systemic action without forcing artificial categories. | Systemic improvement. |
| CAPA-FR-007 | Action owner/evidence | Every action has owner, due date, deliverable/evidence and state. | Accountability. |
| CAPA-FR-008 | Dependencies | Actions link Change, Training, Validation, Supplier, Software Release, Equipment etc. | Cross-module. |
| CAPA-FR-009 | Implementation verification | Reviewer verifies evidence and actual implementation. | Not checkbox-only. |
| CAPA-FR-010 | Effectiveness criteria | Define measurable criterion, data source, observation period and due date before check. | Objective. |
| CAPA-FR-011 | Effectiveness result | Pass/fail/inconclusive with evidence and reviewer. | True effectiveness. |
| CAPA-FR-012 | Failed effectiveness | Reopen CAPA/new investigation/action based on policy. | No cosmetic close. |
| CAPA-FR-013 | Extension | Reason/risk/approval; original due date retained. | Aging controlled. |
| CAPA-FR-014 | Escalation | Overdue/high-risk/repeat CAPA escalates. | Management visibility. |
| CAPA-FR-015 | Closure | All mandatory actions and effectiveness complete before QA closure. | Complete. |
| CAPA-FR-016 | Cancellation | Duplicate/not-required cancellation with Quality rationale. | History. |
| CAPA-FR-017 | Reopen | Recurrence/new evidence can reopen. | History. |
| CAPA-FR-018 | Recurrence analysis | Link new quality events to prior CAPA to assess recurrence. | Effectiveness signal. |
| CAPA-FR-019 | Multi-site scope | CAPA scope can be site/product/process/enterprise. | Scalable. |
| CAPA-FR-020 | Metrics | Aging, overdue, effectiveness failures, recurrence. | QMS dashboard. |
| CAPA-FR-021 | Signatures | Plan approval, extension, effectiveness and closure signed per policy. | Attributable. |
| CAPA-FR-022 | Export | Complete action/evidence/effectiveness history exportable. | Inspection-ready. |

# 4. State / Workflow Model

```text
OPEN → PROBLEM_CONFIRMED → PLAN → APPROVED
     → IMPLEMENTATION → IMPLEMENTATION_VERIFIED
     → EFFECTIVENESS_MONITORING → EFFECTIVENESS_REVIEW
     → QA_CLOSURE → CLOSED
EFFECTIVENESS_FAILED → REOPEN / NEW_ACTION
```

# 5. Data Model

## `capa_record`
```text
id uuid PK
quality_event_id uuid UNIQUE
capa_number varchar(120) UNIQUE
problem_statement text
risk_class varchar(40)
root_cause_ref jsonb
state varchar(50)
owner_subject_id uuid
target_date timestamptz
effectiveness_plan jsonb
version bigint
```

## `capa_action`
- action type
- owner
- due date
- dependency links
- implementation evidence
- verification status/signature

## `capa_effectiveness_check`
- criterion
- data source
- observation period
- result
- reviewer/signature


# 6. APIs

- `POST /qms/v1/capas`
- `POST /qms/v1/capas/{id}/plan`
- `POST /qms/v1/capas/{id}/actions`
- `POST /qms/v1/actions/{id}/complete`
- `POST /qms/v1/capas/{id}/effectiveness`
- `POST /qms/v1/capas/{id}/extend`
- `POST /qms/v1/capas/{id}/close`
- `POST /qms/v1/capas/{id}/reopen`

All mutation APIs use the GxP Mutation Gateway, optimistic concurrency and stable error codes.

# 7. UI Screens

1. CAPA Dashboard
2. Problem/Scope
3. Root Cause
4. Action Plan
5. Dependencies
6. Implementation Evidence
7. Effectiveness Plan
8. Effectiveness Review
9. QA Closure
10. Audit

# 8. Events

- `CAPAOpened`
- `CAPAPlanApproved`
- `CAPAActionAssigned`
- `CAPAActionCompleted`
- `CAPAEffectivenessStarted`
- `CAPAEffectivenessFailed`
- `CAPAClosed`
- `CAPAReopened`

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
services/gxp-api/src/modules/qms/capa-management/
apps/ebmr_frappe/ebmr/qms/capa-management/
contracts/events/qms/capa-management/
validation/requirements/qms/capa-management/
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

- CAPA from deviation
- multi-action dependency
- action without evidence denied
- change dependency
- failed effectiveness
- extension
- repeat deviation after CAPA
- cancel
- reopen
- SoD

# 14. Acceptance Criteria

CAPA cannot close until mandatory actions are verified and required effectiveness criteria are evaluated.

# 15. Codex / Claude Code Rules

- Never auto-generate/accept AI root cause as fact.
- Never mark action complete from owner checkbox alone.
- Never hide failed effectiveness.
- Never close before required effectiveness.

# 16. Stable Error Codes
`CAPA_SOURCE_REQUIRED`, `CAPA_ROOT_CAUSE_REQUIRED`, `ACTION_EVIDENCE_REQUIRED`, `ACTION_DEPENDENCY_OPEN`, `EFFECTIVENESS_PLAN_REQUIRED`, `CAPA_CLOSURE_BLOCKED`.
