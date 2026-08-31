# US eBMR / eDHR Regulated Manufacturing Platform
## Document 33 — Risk Management — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QMS-008  
**Parent Documents:** Documents 01–29  
**Primary Dependencies:** All QMS modules, Change Control, Product/Process specifications  
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

Define a configurable, versioned quality-risk system connecting hazards/failures to controls, residual risk, mitigations and authorized acceptance.

# 2. Actors

- Risk Owner
- QA
- Process/Engineering SME
- Regulatory
- Security/Validation
- Management
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| RSK-FR-001 | Risk register | Create controlled product/process/system/supplier/equipment/software risk. | Common register. |
| RSK-FR-002 | Methodology | Select approved risk methodology; formula/version controlled. | Consistent. |
| RSK-FR-003 | Hazard/problem | Define hazard/failure/problem, context and potential effect/harm. | Clear. |
| RSK-FR-004 | Initial assessment | Capture pre-control risk inputs/score/class. | Baseline. |
| RSK-FR-005 | Controls | Link preventive/detective controls and evidence. | Trace. |
| RSK-FR-006 | Residual assessment | Reassess after controls. | Decision. |
| RSK-FR-007 | Acceptance | Role/authority/rationale based on risk level. | Governance. |
| RSK-FR-008 | Mitigation actions | Link CAPA/change/tasks. | Action. |
| RSK-FR-009 | Quality-event link | Deviation/OOS/Complaint/Audit can trigger risk review. | Living risk. |
| RSK-FR-010 | Change link | Change Control can require reassessment before approval. | Integrated. |
| RSK-FR-011 | Object mapping | Link product/version, recipe/step, equipment, supplier, software component. | Specific. |
| RSK-FR-012 | Versioning | Historical assessments/scores preserved. | History. |
| RSK-FR-013 | Periodic review | Review cycle and escalation. | Current. |
| RSK-FR-014 | Signal review | Trend/complaint/incident can trigger unscheduled review. | Responsive. |
| RSK-FR-015 | Matrix configuration | Risk matrix/method controlled; no universal hardcoded FMEA. | Flexible. |
| RSK-FR-016 | Human acceptance | AI may suggest evidence but cannot accept risk. | Authority. |
| RSK-FR-017 | Dashboard | Heatmap/trends/overdue mitigations. | Visibility. |
| RSK-FR-018 | Export | Assessment/control/acceptance history exportable. | Inspection-ready. |

# 4. State / Workflow Model

```text
DRAFT → INITIAL_ASSESSMENT → CONTROLS/MITIGATION
     → RESIDUAL_ASSESSMENT → ACCEPTANCE_REVIEW → ACCEPTED
ACCEPTED → PERIODIC_REVIEW / TRIGGERED_REVIEW → NEW_VERSION
```

# 5. Data Model

## `risk_record`
```text
id uuid PK
quality_event_id uuid
risk_number varchar(120) UNIQUE
risk_type varchar(50)
methodology_id uuid
context jsonb
hazard_problem text
potential_effect text
state varchar(40)
owner_subject_id uuid
version bigint
```

## `risk_assessment_version`
- scoring inputs
- initial score/class
- controls
- residual inputs/score
- acceptance criteria
- approver/signature


# 6. APIs

- `POST /qms/v1/risks`
- `POST /qms/v1/risks/{id}/assessments`
- `POST /qms/v1/risks/{id}/controls`
- `POST /qms/v1/risks/{id}/accept`
- `POST /qms/v1/risks/{id}/review`
- `GET /qms/v1/risks/dashboard`

All regulated mutations pass through the GxP Mutation Gateway.

# 7. UI Screens

1. Risk Register
2. Risk Assessment
3. Controls/Mitigations
4. Residual Risk
5. Acceptance
6. Related Events/Changes
7. Review Calendar
8. Dashboard

# 8. Events

- `RiskCreated`
- `RiskAssessmentCompleted`
- `RiskMitigationRequired`
- `RiskAccepted`
- `RiskReviewTriggered`
- `RiskReassessed`

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
services/gxp-api/src/modules/qms/risk-management/
apps/ebmr_frappe/ebmr/qms/risk-management/
contracts/events/qms/risk-management/
validation/requirements/qms/risk-management/
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

- different methodologies
- high risk higher approval
- change triggers review
- complaint signal
- failed mitigation
- version history
- AI cannot accept

# 14. Acceptance Criteria

Historical risk values remain reproducible under the exact methodology/version used at the time, and acceptance authority is testable.

# 15. Codex / Claude Code Rules

- Never hardcode one FMEA matrix as universal truth.
- Never let AI accept residual risk.
- Never overwrite prior risk score when methodology changes.

# 16. Stable Error Codes
`RISK_METHOD_NOT_RELEASED`, `RISK_INPUT_INCOMPLETE`, `RESIDUAL_RISK_REVIEW_REQUIRED`, `RISK_ACCEPTANCE_NOT_AUTHORIZED`, `RISK_REVIEW_OVERDUE`.
