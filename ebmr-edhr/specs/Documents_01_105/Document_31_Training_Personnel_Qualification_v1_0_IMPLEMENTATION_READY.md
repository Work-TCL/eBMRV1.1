# US eBMR / eDHR Regulated Manufacturing Platform
## Document 31 — Training & Personnel Qualification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QMS-006  
**Parent Documents:** Documents 01–29  
**Primary Dependencies:** Document Control, IAM/SoD, Change/CAPA/Deviation, Equipment  
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

Define role-based training, competency assessment and qualification so untrained or unqualified personnel are actively prevented from regulated work.

# 2. Actors

- Training Coordinator
- Trainee
- Supervisor
- Trainer/Evaluator
- QA
- Document Controller
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| TRN-FR-001 | Curriculum | Define curriculum by role/site/department/product/process/equipment/area. | Targeted. |
| TRN-FR-002 | Requirement source | Training can originate from document, role, qualification, change, CAPA or manager assignment. | Trace. |
| TRN-FR-003 | Assignment | Assign user/group with due/effective date and completion type. | Actionable. |
| TRN-FR-004 | Training types | Read/understand, instructor-led, practical/OJT, exam, demonstration, qualification, recurring. | Flexible. |
| TRN-FR-005 | Exact content version | Document training references exact released version. | Correct content. |
| TRN-FR-006 | Completion evidence | Trainee/trainer/date/score/result/evidence/signature. | Evidence. |
| TRN-FR-007 | Assessment | Quiz/exam/pass score/attempt rules; question bank versioned if used. | Competency. |
| TRN-FR-008 | Practical qualification | Observed checklist/process/equipment scope and evaluator. | Skill. |
| TRN-FR-009 | Qualification issuance | Completion may issue qualification with effective/expiry dates. | IAM integration. |
| TRN-FR-010 | Expiry/renewal | Recurring training/qualification renewal and execution blocking at expiry. | Current competence. |
| TRN-FR-011 | Grace period | Explicit controlled policy only. | No hidden grace. |
| TRN-FR-012 | Retraining triggers | Document revision, change, CAPA, deviation, performance, periodic cycle. | Current knowledge. |
| TRN-FR-013 | Revision impact | Document release decides whether retraining required and for whom. | Risk based. |
| TRN-FR-014 | Equivalency | Prior training/experience credit requires evidence/approval. | Controlled. |
| TRN-FR-015 | Waiver | Reason/scope/approver/expiry if permitted. | Bounded. |
| TRN-FR-016 | Execution gate | Policy Service blocks operation when training/qualification inactive. | Real enforcement. |
| TRN-FR-017 | Trainer qualification | Trainer/evaluator qualification where required. | Qualified assessor. |
| TRN-FR-018 | Temporary auth | Uses Document 07 process; training module cannot bypass authority. | No loophole. |
| TRN-FR-019 | Overdue escalation | Critical overdue training escalates. | Timely. |
| TRN-FR-020 | Training matrix | Role-vs-required training/qualification/gaps/expiry. | Management. |
| TRN-FR-021 | External training | Record external course/certificate with evidence/approval. | Broader competence. |
| TRN-FR-022 | History | Role/department changes do not rewrite old training. | Integrity. |
| TRN-FR-023 | Transcript | Complete training/qualification export. | Inspection-ready. |
| TRN-FR-024 | Failed attempts | Failed/expired attempts retained. | Data integrity. |

# 4. State / Workflow Model

```text
ASSIGNED → IN_PROGRESS → ASSESSMENT_PENDING → COMPLETED
      └→ FAILED → RETRAIN/REASSESS
COMPLETED → QUALIFIED (where applicable)
QUALIFIED → EXPIRING → EXPIRED / RENEWED
```

# 5. Data Model

## `training_requirement`
- source type/version
- role/site/product/equipment scope
- training type
- recurrence/expiry
- assessment requirement

## `training_assignment`
```text
id uuid PK
subject_id uuid
requirement_id uuid
source_version_id uuid
state varchar(40)
assigned_at timestamptz
due_at timestamptz
completed_at timestamptz
result varchar(40)
version bigint
```

## `qualification_record`
- subject
- qualification code
- scope
- effective/expiry
- state
- evaluator/signature


# 6. APIs

- `POST /training/v1/requirements`
- `POST /training/v1/assignments`
- `POST /training/v1/assignments/{id}/complete`
- `POST /training/v1/assignments/{id}/assess`
- `POST /training/v1/qualifications`
- `POST /training/v1/waivers`
- `GET /training/v1/subjects/{id}/status`
- `GET /training/v1/matrix`

All regulated mutations pass through the GxP Mutation Gateway.

# 7. UI Screens

1. Training Dashboard
2. Curriculum/Requirement
3. Assignments
4. Learning/Acknowledgment
5. Assessment
6. Practical Evaluation
7. Qualifications
8. Expiry/Renewal
9. Training Matrix
10. Transcript

# 8. Events

- `TrainingAssigned`
- `TrainingCompleted`
- `TrainingFailed`
- `QualificationIssued`
- `QualificationExpired`
- `RetrainingRequired`
- `TrainingWaiverApproved`

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
services/gxp-api/src/modules/qms/training-and-personnel-qualification/
apps/ebmr_frappe/ebmr/qms/training-and-personnel-qualification/
contracts/events/qms/training-and-personnel-qualification/
validation/requirements/qms/training-and-personnel-qualification/
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

- document revision
- failed exam
- qualification expiry during batch
- trainer unqualified
- equivalency
- waiver
- temporary auth cannot bypass
- role transfer
- audit transcript

# 14. Acceptance Criteria

Authorization tests prove users missing/expired mandatory training or qualification cannot execute configured regulated action through UI or API.

# 15. Codex / Claude Code Rules

- Never treat role assignment as proof of training.
- Never delete failed training attempt.
- Never make UI visibility the only training gate.
- Never auto-credit revised SOP without approved rule.

# 16. Stable Error Codes
`TRAINING_REQUIRED`, `TRAINING_EXPIRED`, `ASSESSMENT_FAILED`, `QUALIFICATION_REQUIRED`, `QUALIFICATION_EXPIRED`, `TRAINER_NOT_QUALIFIED`, `WAIVER_NOT_AUTHORIZED`.
