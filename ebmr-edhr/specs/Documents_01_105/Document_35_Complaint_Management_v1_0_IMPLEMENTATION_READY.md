# US eBMR / eDHR Regulated Manufacturing Platform
## Document 35 — Complaint Management — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QMS-010  
**Parent Documents:** Documents 01–33  
**Primary Dependencies:** Genealogy, OOS/Deviation/CAPA, Postmarket/Reportability, Recall  
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

Define complaint intake, product/constituent identification, investigation, reportability-assessment workflow, CAPA/field-action linkage and closure for drug, device and DDCP products.

# 2. Actors

- Complaint Coordinator
- QA Investigator
- Regulatory/Safety
- Device Quality
- Drug Quality
- CAPA Owner
- Customer Service
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| CMP-FR-001 | Complaint intake | Capture oral/written/electronic complaint from customer, patient/user, distributor, service, sales or regulator. | All channels. |
| CMP-FR-002 | Known information | Product name/strength/configuration, lot/batch/serial/UDI, complainant, date, nature, country/event details and reply where known. | Complaint file. |
| CMP-FR-003 | Acknowledgment | Track complaint acknowledgment/communication. | Customer handling. |
| CMP-FR-004 | Product identification | Resolve product/lot/serial; unknown IDs go to reconciliation queue. | Trace. |
| CMP-FR-005 | Constituent classification | Drug/device/interface/combination/packaging/label/usability/unknown. | DDCP aware. |
| CMP-FR-006 | Triage | Quality/Regulatory seriousness/criticality assessment under approved procedure. | Safety. |
| CMP-FR-007 | Investigation decision | Quality determines investigation required/not required. | 211.198 support. |
| CMP-FR-008 | No-investigation rationale | If not investigated, reason and responsible approver recorded. | 211.198 support. |
| CMP-FR-009 | Investigation | Link batch/device history, QC, deviations, materials, equipment, complaints, service and returned product. | Complete. |
| CMP-FR-010 | Returned product | Track chain of custody, testing, preservation and disposition. | Evidence. |
| CMP-FR-011 | Genealogy | Serial/lot lookup identifies constituents/materials/related product. | DDCP. |
| CMP-FR-012 | Reportability assessment | Separate authorized assessment with rationale, regime, trigger/date and due date; software does not decide legal outcome alone. | Controlled. |
| CMP-FR-013 | Part 4 PMSR profile | Support multiple constituent/application reporting regimes and information-sharing hooks. | Combination support. |
| CMP-FR-014 | Device reporting hook | MDR/eMDR reference/workflow where applicable. | Postmarket. |
| CMP-FR-015 | Drug safety hook | FAERS/safety-system reference/escalation where applicable. | Postmarket. |
| CMP-FR-016 | Trend | Complaint codes/failure mode/product/lot/constituent trend. | Signal. |
| CMP-FR-017 | CAPA | Significant/repeat complaint can create CAPA. | Systemic. |
| CMP-FR-018 | Field action | Complaint can trigger recall/field-action assessment. | Containment. |
| CMP-FR-019 | Response | Track approved response to complainant. | Communication. |
| CMP-FR-020 | Closure | Investigation decision, reportability, CAPA/field action and response complete per policy. | Complete. |
| CMP-FR-021 | Retention | Apply product/profile/predicate retention policy. | Durable. |
| CMP-FR-022 | Privacy | Restrict/minimize personal/health data. | Confidentiality. |
| CMP-FR-023 | Duplicate detection | Link duplicate reports without deleting original intake. | Integrity. |
| CMP-FR-024 | Export | Known data, investigation/follow-up or no-investigation rationale, reportability and response exportable. | Inspection-ready. |

# 4. State / Workflow Model

```text
RECEIVED → TRIAGE → INVESTIGATION_DECISION
   ├→ NO_INVESTIGATION_JUSTIFIED
   └→ INVESTIGATION
       → REPORTABILITY_ASSESSMENT
       → CAPA/FIELD_ACTION if required
       → RESPONSE → QA_CLOSURE → CLOSED
```

# 5. Data Model

## `complaint_record`
```text
id uuid PK
quality_event_id uuid UNIQUE
complaint_number varchar(120) UNIQUE
received_at timestamptz
source_channel varchar(40)
product_ref uuid
lot_batch_serial_refs jsonb
complainant_ref/encrypted_fields jsonb
nature_code varchar(100)
description text
constituent_classification varchar(60)
state varchar(50)
investigation_required boolean
no_investigation_reason text
version bigint
```

## `complaint_reportability_assessment`
- applicable regime(s)
- assessment inputs/rationale
- due date
- reviewer/signature
- submission reference/status

## `complaint_communication`
- direction
- recipient/channel
- date
- approved message/reference


# 6. APIs

- `POST /qms/v1/complaints`
- `POST /qms/v1/complaints/{id}/triage`
- `POST /qms/v1/complaints/{id}/investigation-decision`
- `POST /qms/v1/complaints/{id}/investigation`
- `POST /qms/v1/complaints/{id}/reportability`
- `POST /qms/v1/complaints/{id}/response`
- `POST /qms/v1/complaints/{id}/close`

All regulated mutations pass through the GxP Mutation Gateway.

# 7. UI Screens

1. Complaint Intake
2. Product/Serial Lookup
3. Triage
4. Investigation Decision
5. Manufacturing/Genealogy Evidence
6. Returned Product
7. Reportability Assessment
8. CAPA/Field Action
9. Communications
10. Closure
11. Trend

# 8. Events

- `ComplaintReceived`
- `ComplaintInvestigationRequired`
- `ComplaintInvestigationWaivedWithRationale`
- `ComplaintReportabilityAssessmentCompleted`
- `ComplaintCAPAOpened`
- `ComplaintFieldActionAssessmentOpened`
- `ComplaintClosed`

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
services/gxp-api/src/modules/qms/complaint-management/
apps/ebmr_frappe/ebmr/qms/complaint-management/
contracts/events/qms/complaint-management/
validation/requirements/qms/complaint-management/
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

- oral complaint
- unknown serial
- autoinjector constituent issue
- no-investigation rationale
- prior similar complaints
- reportability due date
- CAPA
- field action trigger
- privacy restriction
- duplicate intake
- export

# 14. Acceptance Criteria

Complaint workflow can support current drug complaint-file requirements and DDCP constituent/reportability assessment without software making an unsupported legal determination.

# 15. Codex / Claude Code Rules

- Never auto-decide FDA reportability with AI/rules alone.
- Never close without investigation decision/rationale.
- Never delete duplicate complaint intake.
- Never expose complainant sensitive data broadly.

# 16. Regulatory Design Note

For drug complaints, the record supports the known complaint information, Quality investigation decision, investigation findings/follow-up where performed, and documented rationale/responsible person where not performed. Combination-product reporting is modeled as an explicit assessment because constituent/application regimes can differ.

# 17. Stable Error Codes

`COMPLAINT_PRODUCT_UNRESOLVED`, `INVESTIGATION_DECISION_REQUIRED`, `NO_INVESTIGATION_RATIONALE_REQUIRED`, `REPORTABILITY_ASSESSMENT_REQUIRED`, `COMPLAINT_CLOSURE_BLOCKED`.

