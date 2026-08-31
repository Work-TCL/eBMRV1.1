# US eBMR / eDHR Regulated Manufacturing Platform
## Document 30 — Document Control — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QMS-005  
**Parent Documents:** Documents 01–29  
**Primary Dependencies:** Vault, E-Signature, Change Control, Training  
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

Define lifecycle and distribution control of SOPs, policies, specifications, work instructions, forms and other regulated documents.

# 2. Actors

- Author
- Technical Reviewer
- QA Approver
- Document Controller
- Training Coordinator
- User/Reader
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| DOC-FR-001 | Document master | Controlled document has immutable business identity, type, owner, department/site/profile and lifecycle. | Canonical identity. |
| DOC-FR-002 | Versioning | Each revision is separate version; released content immutable. | History. |
| DOC-FR-003 | Content storage | Store authoritative content/file in Vault/Evidence with hash and version. | Integrity. |
| DOC-FR-004 | Source/rendition | Differentiate editable source from released rendition/PDF where applicable. | Meaning preserved. |
| DOC-FR-005 | Review workflow | Technical/Quality/Regulatory reviewers based on document type. | Appropriate review. |
| DOC-FR-006 | Approval/e-signature | Controlled release requires policy-defined signatures. | Attributable. |
| DOC-FR-007 | Effective date | Version becomes usable only at approved effective date after prerequisites. | Controlled use. |
| DOC-FR-008 | Supersession | New effective version supersedes future use; historical records retain exact old version. | No drift. |
| DOC-FR-009 | Obsolete | Obsolete versions removed from normal current-use view but historically retrievable. | Prevent unintended use. |
| DOC-FR-010 | Controlled copy | Optional numbered controlled-copy issue/recipient/location/status. | Distribution control. |
| DOC-FR-011 | Uncontrolled copy marking | Print/download may be watermarked/marked uncontrolled per policy. | User awareness. |
| DOC-FR-012 | Periodic review | Review interval/due date with reminders/escalation. | Lifecycle. |
| DOC-FR-013 | Training impact | Release determines training assignment to roles/sites/users. | Training integrated. |
| DOC-FR-014 | Acknowledgment | Read-and-understand training is separate from approval signature. | Semantics. |
| DOC-FR-015 | Change link | Major revision may require Change Control. | Trace. |
| DOC-FR-016 | Relationships | Parent/child/reference links by exact version or explicit current-reference semantics. | Dependency clarity. |
| DOC-FR-017 | Forms/templates | Controlled forms and executable templates are versioned/released. | No uncontrolled forms. |
| DOC-FR-018 | External documents | Track external standards/guidance/customer specs with source/revision/applicability without unauthorized copying. | External control. |
| DOC-FR-019 | Access | Document-class/site/role access server-side. | Confidentiality. |
| DOC-FR-020 | Distribution audit | Audit controlled-copy generation/distribution where policy requires. | Evidence. |
| DOC-FR-021 | Retirement | Retire with reason/effective date/impact. | History. |
| DOC-FR-022 | Migration | Imported historical docs retain source/provenance; no fabricated approvals. | Integrity. |
| DOC-FR-023 | Search | Current/obsolete search by code/title/type/owner/site/effective date. | Usability. |
| DOC-FR-024 | Export | Revision/approval/effective/distribution history exportable. | Inspection-ready. |

# 4. State / Workflow Model

```text
DRAFT → REVIEW → APPROVED/RELEASED → EFFECTIVE
     → SUPERSEDED → OBSOLETE/ARCHIVED
DRAFT/REVIEW → CANCELLED
```

# 5. Data Model

## `controlled_document`
```text
id uuid PK
tenant_id uuid
document_code varchar(120) UNIQUE
document_type varchar(60)
owner_subject_id uuid
department_id uuid
site_scope jsonb
status varchar(40)
```

## `controlled_document_version`
```text
id uuid PK
document_id uuid
version_label varchar(60)
vault_object_id uuid
content_hash char(64)
state varchar(40)
effective_from timestamptz
effective_to timestamptz
change_control_id uuid
periodic_review_due timestamptz
version bigint
```

## `controlled_copy`
- document version
- copy number
- recipient/location
- issued/returned/destroyed status


# 6. APIs

- `POST /documents/v1/drafts`
- `POST /documents/v1/drafts/{id}/submit`
- `POST /documents/v1/drafts/{id}/release`
- `POST /documents/v1/versions/{id}/make-effective`
- `POST /documents/v1/versions/{id}/obsolete`
- `POST /documents/v1/versions/{id}/controlled-copies`
- `GET /documents/v1/{code}/versions`

All regulated mutations pass through the GxP Mutation Gateway.

# 7. UI Screens

1. Document Library
2. Document Editor/Upload
3. Review/Approval
4. Version Compare
5. Effective/Obsolete
6. Controlled Copies
7. Periodic Review
8. Training Impact
9. Audit

# 8. Events

- `DocumentVersionReleased`
- `DocumentVersionEffective`
- `DocumentVersionSuperseded`
- `DocumentObsoleted`
- `ControlledCopyIssued`
- `DocumentPeriodicReviewDue`

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
services/gxp-api/src/modules/qms/document-control/
apps/ebmr_frappe/ebmr/qms/document-control/
contracts/events/qms/document-control/
validation/requirements/qms/document-control/
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

- new SOP release
- future effective date
- obsolete old version
- historical batch opens old version
- controlled copy
- periodic review overdue
- training assignment
- unauthorized access
- migration

# 14. Acceptance Criteria

A regulated execution record can always resolve the exact document version in force/snapshot at execution time.

# 15. Codex / Claude Code Rules

- Never overwrite released document file.
- Never automatically replace historical SOP link with current version.
- Never confuse training acknowledgment with approval.
- Never embed copyrighted external standard text without rights.

# 16. Stable Error Codes
`DOCUMENT_REVIEW_INCOMPLETE`, `DOCUMENT_SIGNATURE_REQUIRED`, `EFFECTIVE_PREREQUISITES_INCOMPLETE`, `DOCUMENT_VERSION_OBSOLETE`, `CONTROLLED_COPY_CONFLICT`.
