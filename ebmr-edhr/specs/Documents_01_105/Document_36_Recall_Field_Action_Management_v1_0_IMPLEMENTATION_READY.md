# US eBMR / eDHR Regulated Manufacturing Platform
## Document 36 — Recall / Field Action Management — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QMS-011  
**Parent Documents:** Documents 01–33  
**Primary Dependencies:** Genealogy, Complaint, CAPA, ERP/WMS, DDCP PMSR  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products (DDCP)  
**Future Profiles:** Medical Devices, Pharmaceuticals  
**Date:** 2026-08-20

---

# Implementation Standard

This document is implementation-grade. Codex/Claude Code shall not invent regulated behavior that is absent from this specification.

# Shared Quality Event Kernel

All QMS records share stable quality-event identity, tenant/site, source, severity, owner, due dates, product/batch/material/device/equipment/supplier links, evidence, relationships, audit and versioning.

# Regulatory Engineering Basis

Current verified anchors:
- 21 CFR §211.198 requires written procedures/records for drug-product complaints, Quality review, investigation determination, findings/follow-up where investigated, and documented reason/responsible person where no investigation is performed.
- Current QMSR is effective February 2, 2026 and incorporates ISO 13485:2016 by reference.
- 21 CFR Part 806 covers certain medical-device corrections/removals.
- 21 CFR Part 4 Subpart B and FDA's combination-product PMSR guidance address postmarketing safety reporting for combination products and distinct constituent/application reporting regimes.

The software supports controlled assessment, evidence, deadlines and submission references. It does not make unsupported autonomous legal/reportability decisions.

Official references:
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-J/section-211.198
- https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-806
- https://www.fda.gov/combination-products/guidance-regulatory-information/postmarketing-safety-reporting-combination-products

# 1. Objective

Define affected-product analysis, regulatory assessment, communication, correction/removal execution, reconciliation, effectiveness and closure for recalls and field actions.

# 2. Actors

- QA
- Regulatory Affairs
- Recall Coordinator
- Distribution/Warehouse
- Customer Service
- CAPA Owner
- Management
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| FAR-FR-001 | Assessment initiation | Create from complaint, deviation, CAPA, trend, regulatory request or management decision. | Trigger linked. |
| FAR-FR-002 | Action classification | Recall/correction/removal/field action/customer advisory/stock recovery or configured terminology. | Explicit. |
| FAR-FR-003 | Affected scope | Use Genealogy to identify products/lots/serials/packages/distribution references. | Accurate. |
| FAR-FR-004 | Constituent scope | DDCP action can target whole product or constituent/interface with final-product impact. | Combination aware. |
| FAR-FR-005 | Risk assessment | Link health/product risk assessment and rationale. | Evidence. |
| FAR-FR-006 | Reportability assessment | Authorized Regulatory determines applicable Part 806/drug/biologic/Part4 obligations/deadlines. | Human authority. |
| FAR-FR-007 | Distribution hold | Block undistributed inventory when required. | Containment. |
| FAR-FR-008 | Consignee snapshot | Resolve and freeze distribution/consignee scope from ERP/WMS/CRM. | Communication scope. |
| FAR-FR-009 | Communication package | Version/approve notification text/instructions/attachments. | Controlled. |
| FAR-FR-010 | Notification tracking | Recipient/date/channel/delivery/acknowledgment/follow-up. | Execution. |
| FAR-FR-011 | Return/correction plan | Return/inspect/correct/update/replace/destroy plan. | Disposition. |
| FAR-FR-012 | Unit reconciliation | Affected/contacted/returned/corrected/destroyed/unavailable/outstanding. | Effectiveness. |
| FAR-FR-013 | Effectiveness checks | Verify communication/action effectiveness under approved plan. | Control. |
| FAR-FR-014 | Submission evidence | Store regulatory report/submission IDs/dates/acknowledgments. | Evidence. |
| FAR-FR-015 | Corrections/removals record | Maintain applicable device correction/removal records even if reporting decision is no. | Part 806 support. |
| FAR-FR-016 | CAPA link | Underlying systemic action links CAPA. | Systemic. |
| FAR-FR-017 | Status updates | Track management/regulatory updates and milestones. | Governance. |
| FAR-FR-018 | Closure | Scope reconciliation, action, submissions, effectiveness and dependencies complete. | Complete. |
| FAR-FR-019 | Scope expansion | New affected product reopens/expands controlled version. | Dynamic. |
| FAR-FR-020 | Export | Decision/scope/communication/reconciliation/submission/closure package exportable. | Inspection-ready. |

# 4. State / Workflow Model

```text
ASSESSMENT → SCOPE_DEFINITION → REGULATORY_DECISION → APPROVAL
     → EXECUTION/NOTIFICATION → RECONCILIATION
     → EFFECTIVENESS → CLOSURE_REVIEW → CLOSED
CLOSED → EXPANDED/REOPENED (controlled)
```

# 5. Data Model

## `field_action`
```text
id uuid PK
quality_event_id uuid UNIQUE
action_number varchar(120) UNIQUE
action_type varchar(60)
trigger_ref jsonb
state varchar(50)
risk_assessment_ref uuid
reportability_assessment jsonb
scope_snapshot_id uuid
version bigint
```

## `field_action_scope_item`
- product/lot/serial/package
- distribution reference
- status/action required/completed

## `field_action_communication`
- communication version
- recipient
- sent/delivery/ack status

## `field_action_reconciliation`
- affected/contacted/returned/corrected/destroyed/outstanding


# 6. APIs

- `POST /qms/v1/field-actions`
- `POST /qms/v1/field-actions/{id}/scope`
- `POST /qms/v1/field-actions/{id}/reportability`
- `POST /qms/v1/field-actions/{id}/approve`
- `POST /qms/v1/field-actions/{id}/communications`
- `POST /qms/v1/field-actions/{id}/reconcile`
- `POST /qms/v1/field-actions/{id}/effectiveness`
- `POST /qms/v1/field-actions/{id}/close`

All regulated mutations pass through the GxP Mutation Gateway.

# 7. UI Screens

1. Field Action Dashboard
2. Assessment/Risk
3. Affected Product Scope
4. Distribution/Consignees
5. Reportability
6. Communication Package
7. Execution
8. Returns/Corrections
9. Reconciliation
10. Effectiveness
11. Closure

# 8. Events

- `FieldActionAssessmentOpened`
- `FieldActionScopeFrozen`
- `FieldActionApproved`
- `FieldActionNotificationSent`
- `FieldActionUnitReturned`
- `FieldActionCorrectionCompleted`
- `FieldActionEffectivenessCompleted`
- `FieldActionClosed`
- `FieldActionScopeExpanded`

# 9. Authorization / Signature / Audit

- Server-side authorization controls every state transition.
- High-risk decisions/closures use regulated signatures when applicable.
- Corrections preserve original values/evidence.
- Regulatory/reportability decisions require authorized human review.
- Admin/service identities cannot impersonate Quality/Regulatory signers.

# 10. Failure / Recovery

- DB unavailable: no regulated transition.
- Signature/Policy unavailable: required action fails closed.
- Notification/integration failure: outbox retries; authoritative state remains.
- Stale version: reject.
- Scheduled due-date/metric jobs recover from persisted state.

# 11. Repository Structure

```text
services/gxp-api/src/modules/qms/recall---field-action-management/
apps/ebmr_frappe/ebmr/qms/recall---field-action-management/
contracts/events/qms/recall---field-action-management/
validation/requirements/qms/recall---field-action-management/
```

# 12. Implementation Sequence

1. Core record/state.
2. Evidence/relationship model.
3. Authorization/signature/audit.
4. Cross-module integrations.
5. UI and dashboards.
6. Events/outbox/notifications.
7. Reports/exports.
8. Negative/failure tests.
9. Validation traceability.

# 13. Test Catalogue

- material-lot forward trace
- single serial complaint
- DDCP constituent issue
- distribution hold
- consignee snapshot
- return reconciliation
- device correction/removal record
- scope expansion
- CAPA dependency
- closure

# 14. Acceptance Criteria

From any affected material/component/product lot or serial, the system can freeze a controlled affected-product scope and reconcile identified distributed/non-distributed product through closure.

# 15. Codex / Claude Code Rules

- Never use live ERP shipment query as only preserved recall scope.
- Never auto-decide reportability.
- Never alter historical release decision to represent later field action.

# 16. Regulatory Design Note

Part 806 and Part 4 postmarket obligations are not reduced to one universal workflow. Product/profile configuration determines which assessment tasks and reporting records are applicable, while authorized Regulatory/Quality personnel make final reportability decisions.

# 17. Stable Error Codes

`FIELD_ACTION_SCOPE_REQUIRED`, `REPORTABILITY_ASSESSMENT_REQUIRED`, `COMMUNICATION_NOT_APPROVED`, `RECONCILIATION_INCOMPLETE`, `EFFECTIVENESS_REQUIRED`, `FIELD_ACTION_CLOSURE_BLOCKED`.

