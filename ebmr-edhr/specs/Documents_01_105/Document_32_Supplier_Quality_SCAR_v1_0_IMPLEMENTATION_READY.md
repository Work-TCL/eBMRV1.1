# US eBMR / eDHR Regulated Manufacturing Platform
## Document 32 — Supplier Quality / SCAR — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QMS-007  
**Parent Documents:** Documents 01–29  
**Primary Dependencies:** Supplier Qualification/ASL, NCR, Deviation, CAPA, Materials  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products (DDCP)  
**Future Profiles:** Medical Devices, Pharmaceuticals  
**Date:** 2026-08-20

---

# Implementation Standard

This document is implementation-grade. Codex/Claude Code shall not invent regulated behavior that is absent from this specification.

# Shared Quality Event Kernel

QMS modules use a common kernel for identity, site, source, severity, ownership, due dates, evidence, related records, audit and versioning. Module-specific states and approvals remain explicit.

# Regulatory Engineering Basis

Current 21 CFR Part 820 is the QMSR, effective February 2, 2026, and incorporates ISO 13485:2016 by reference. For drug profiles, Part 211 requires controlled procedures, production/laboratory records, Quality review and investigations. This specification summarizes engineering controls and does not reproduce copyrighted ISO text.

Official references:
- https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211

# 1. Objective

Define supplier corrective-action and supplier-quality case management integrated with approved-source status and incoming-material control.

# 2. Actors

- Supplier Quality Engineer
- Buyer
- QA
- Warehouse/QC
- Supplier Contact
- CAPA Owner
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| SCAR-FR-001 | Supplier quality case | Create from incoming reject, deviation, complaint, audit, trend or manufacturing defect. | Source linked. |
| SCAR-FR-002 | Affected source | Identify supplier/manufacturer site, material/spec and affected lots/products. | Scope exact. |
| SCAR-FR-003 | Containment | Hold lot/source/new receipts/use if risk requires; link ASL status. | Immediate control. |
| SCAR-FR-004 | SCAR issue | Formal request with problem/evidence, required response and due dates. | Supplier action. |
| SCAR-FR-005 | Acknowledgment | Track supplier acknowledgment/contact. | Communication. |
| SCAR-FR-006 | Supplier root cause | Capture supplier-provided root cause/evidence as supplier statement, not automatically accepted fact. | Review. |
| SCAR-FR-007 | Supplier actions | Track supplier corrections/corrective actions and implementation evidence. | Action. |
| SCAR-FR-008 | Internal review | Supplier Quality/QA accepts/rejects response with rationale/signature. | Authority. |
| SCAR-FR-009 | Effectiveness | Verify incoming/performance data after implementation. | True closure. |
| SCAR-FR-010 | Requalification | Significant issue may trigger audit/requalification. | ASL. |
| SCAR-FR-011 | Source suspension | Supplier-material approval can be suspended pending resolution. | Procurement gate. |
| SCAR-FR-012 | Alternate source | Emergency alternative source links deviation/change. | Controlled. |
| SCAR-FR-013 | Internal CAPA | Internal CAPA may also be required. | Ownership. |
| SCAR-FR-014 | Repeat issue | Detect recurrence by supplier/material/defect. | Trend. |
| SCAR-FR-015 | Escalation | Overdue response escalates. | Timeliness. |
| SCAR-FR-016 | Closure | Close only after accepted response/effectiveness/source decision. | Complete. |
| SCAR-FR-017 | Performance impact | SCAR contributes to supplier scorecard/risk. | Data driven. |
| SCAR-FR-018 | Export | Correspondence/evidence/history exportable. | Inspection-ready. |

# 4. State / Workflow Model

```text
OPEN → CONTAINMENT → SCAR_ISSUED → SUPPLIER_RESPONSE
     → INTERNAL_REVIEW → IMPLEMENTATION → EFFECTIVENESS
     → SOURCE_STATUS_DECISION → CLOSED
```

# 5. Data Model

## `supplier_quality_case`
- quality event ID
- supplier/manufacturer site
- material/spec
- affected lots
- severity/state
- ASL impact
- internal owner

## `scar_record`
- case ID
- SCAR number
- issued/due dates
- supplier response
- supplier root cause/action
- internal review
- effectiveness
- closure signature


# 6. APIs

- `POST /qms/v1/supplier-cases`
- `POST /qms/v1/supplier-cases/{id}/scar`
- `POST /qms/v1/scars/{id}/response`
- `POST /qms/v1/scars/{id}/review`
- `POST /qms/v1/scars/{id}/effectiveness`
- `POST /qms/v1/scars/{id}/close`

All regulated mutations pass through the GxP Mutation Gateway.

# 7. UI Screens

1. Supplier Quality Dashboard
2. Supplier Case
3. Containment/ASL Impact
4. SCAR
5. Supplier Response
6. Internal Review
7. Effectiveness
8. Supplier Status
9. History

# 8. Events

- `SupplierQualityCaseOpened`
- `SCARIssued`
- `SCARResponseReceived`
- `SupplierSourceSuspended`
- `SCAREffectivenessPassed`
- `SCARClosed`

# 9. Authorization / Signature / Audit

- Server-side Policy Service controls actions.
- Required approvals use regulated signatures.
- Released versions are immutable.
- Corrections preserve originals and audit.
- Admin privileges do not imply Quality authority.

# 10. Failure / Recovery

- DB unavailable: no regulated state transition.
- Signature/Policy unavailable: fail closed where required.
- Notification/outbox failures retry.
- Stale version rejects.
- Scheduled due/expiry jobs resume from persisted records.

# 11. Repository Structure

```text
services/gxp-api/src/modules/qms/supplier-quality---scar/
apps/ebmr_frappe/ebmr/qms/supplier-quality---scar/
contracts/events/qms/supplier-quality---scar/
validation/requirements/qms/supplier-quality---scar/
```

# 12. Implementation Sequence

1. Core record/state.
2. Master/configuration.
3. Policy/signature/audit.
4. Cross-module integrations.
5. UI/dashboards.
6. Events/notifications.
7. Export/history.
8. Negative/failure tests.
9. Validation traceability.

# 13. Test Catalogue

- incoming reject
- repeat supplier lot issue
- SCAR overdue
- supplier response rejected
- source suspended
- requalification
- failed effectiveness
- CAPA link

# 14. Acceptance Criteria

Supplier quality issue can prevent source eligibility immediately and cannot close solely because supplier submitted a response.

# 15. Codex / Claude Code Rules

- Never let supplier self-close SCAR.
- Never auto-accept supplier root cause/action.
- Never change ASL status outside controlled Quality authority.

# 16. Stable Error Codes
`SCAR_SOURCE_REQUIRED`, `SUPPLIER_RESPONSE_INCOMPLETE`, `SCAR_REVIEW_REJECTED`, `EFFECTIVENESS_REQUIRED`, `SUPPLIER_SOURCE_SUSPENDED`.
