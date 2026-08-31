# US eBMR / eDHR Regulated Manufacturing Platform
## Document 34 — Internal Audit Management — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QMS-009  
**Parent Documents:** Documents 01–33  
**Primary Dependencies:** CAPA, Risk, Document Control, Training  
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

Define internal quality audit planning, execution, findings, responses, CAPA linkage, verification and closure.

# 2. Actors

- Audit Program Manager
- Lead Auditor
- Auditor
- Auditee/Process Owner
- QA
- CAPA Owner
- Management

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| AUDIT-FR-001 | Audit program | Define annual/multi-period audit program by site/process/system/supplier where applicable. | Planned oversight. |
| AUDIT-FR-002 | Audit plan | Scope, objectives, criteria, references, auditors, schedule, auditees. | Clear plan. |
| AUDIT-FR-003 | Auditor independence | Policy prevents auditor from auditing own direct work/function where required. | Objectivity. |
| AUDIT-FR-004 | Checklist | Versioned checklist/template supports sampling prompts but never limits auditor findings. | Consistent. |
| AUDIT-FR-005 | Evidence | Capture interview/record/sample/evidence references with access controls. | Evidence. |
| AUDIT-FR-006 | Finding | Requirement/observation/evidence/severity/classification. | Objective finding. |
| AUDIT-FR-007 | Finding response | Assign owner, correction, root-cause/action and due dates. | Accountability. |
| AUDIT-FR-008 | CAPA link | Significant/systemic finding can create CAPA. | Integration. |
| AUDIT-FR-009 | Verification | Auditor/QA verifies action/effectiveness. | Closure quality. |
| AUDIT-FR-010 | Audit report | Generate controlled report from approved record. | Formal output. |
| AUDIT-FR-011 | Closure | Close only after findings dispositioned per policy. | Complete. |
| AUDIT-FR-012 | Schedule change | Reschedule/cancel with reason/approval; old schedule retained. | Transparency. |
| AUDIT-FR-013 | Confidentiality | Role/site access restrictions. | Security. |
| AUDIT-FR-014 | Repeat findings | Detect recurrence by process/requirement/root cause. | Trend. |
| AUDIT-FR-015 | Metrics | Completion, overdue findings, recurrence, CAPA links. | Management. |
| AUDIT-FR-016 | External audit tracking | Track external audits/inspection commitments separately where configured. | Broader QMS. |
| AUDIT-FR-017 | Export | Plan/evidence/findings/responses/closure exportable. | Inspection-ready. |

# 4. State / Workflow Model

```text
PLANNED → SCHEDULED → IN_PROGRESS → REPORT_DRAFT
     → REPORT_APPROVED → FINDINGS_OPEN
     → FOLLOW_UP → CLOSED
```

# 5. Data Model

## `internal_audit`
```text
id uuid PK
quality_event_id uuid
audit_number varchar(120) UNIQUE
program_ref varchar(120)
site_scope jsonb
process_scope jsonb
criteria_refs jsonb
lead_auditor_id uuid
team jsonb
scheduled_at timestamptz
actual_start/end timestamptz
state varchar(40)
version bigint
```

## `audit_finding`
- audit ID
- finding number
- requirement/reference
- evidence
- classification
- owner
- response
- CAPA link
- verification/closure


# 6. APIs

- `POST /qms/v1/audits`
- `POST /qms/v1/audits/{id}/start`
- `POST /qms/v1/audits/{id}/findings`
- `POST /qms/v1/findings/{id}/response`
- `POST /qms/v1/findings/{id}/verify`
- `POST /qms/v1/audits/{id}/close`

All regulated mutations pass through the GxP Mutation Gateway.

# 7. UI Screens

1. Audit Program
2. Audit Plan
3. Checklist
4. Evidence/Notes
5. Findings
6. Report
7. Responses/CAPA
8. Follow-Up
9. Metrics

# 8. Events

- `InternalAuditScheduled`
- `InternalAuditStarted`
- `AuditFindingOpened`
- `AuditReportApproved`
- `AuditFindingClosed`
- `InternalAuditClosed`

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
services/gxp-api/src/modules/qms/internal-audit-management/
apps/ebmr_frappe/ebmr/qms/internal-audit-management/
contracts/events/qms/internal-audit-management/
validation/requirements/qms/internal-audit-management/
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

- auditor independence
- finding CAPA
- late response
- repeat finding
- reschedule
- report approval
- restricted evidence
- closure incomplete

# 14. Acceptance Criteria

An audit can be planned, performed, reported and closed with every finding traced to response, CAPA where required and independent verification.

# 15. Codex / Claude Code Rules

- Never force checklist as only source of findings.
- Never let auditee self-close finding when independent verification required.
- Never delete finding because wording changes.

# 16. Stable Error Codes
`AUDITOR_SOD_CONFLICT`, `AUDIT_SCOPE_INCOMPLETE`, `FINDING_RESPONSE_REQUIRED`, `FINDING_VERIFICATION_REQUIRED`, `AUDIT_CLOSURE_BLOCKED`.
