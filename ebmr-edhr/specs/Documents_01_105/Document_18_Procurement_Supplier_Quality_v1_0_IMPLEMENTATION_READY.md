# US eBMR / eDHR Regulated Manufacturing Platform
## Document 18 — Procurement & Supplier Quality Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-MAT-001  
**Parent Documents:** Documents 01–17  
**Primary Dependencies:** Documents 03–09, 17; QMS Supplier Quality/SCAR; ERP Integration  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products (DDCP)  
**Future Profiles:** Medical Devices, Pharmaceuticals  
**Date:** 2026-08-20

---


# Implementation Standard

This document is implementation-grade. Codex/Claude Code shall not invent regulated behavior that is absent from this specification.

Where applicable the specification defines:
- objective/scope/non-goals;
- actors and roles;
- functionalities and all required sub-functionalities;
- workflows/states;
- business rules;
- authorization/SoD;
- e-signature/audit behavior;
- entities/fields/relationships;
- database ownership/tables/indexes/constraints;
- APIs/errors/idempotency/concurrency;
- events/outbox contracts;
- UI/forms/actions;
- integrations;
- failure/recovery;
- security/configuration/observability;
- retention/migration/performance;
- repository structure;
- implementation sequence;
- positive/negative/failure/concurrency tests;
- acceptance criteria and coding-agent rules.

If an implementation decision would materially change regulatory behavior, the coding agent must raise a specification gap rather than guessing.

# Regulatory Engineering Basis

Relevant current U.S. requirements include, depending on product/profile/applicability:

- 21 CFR §211.80 — written procedures for receipt, identification, storage, handling, sampling, testing, and approval/rejection; lot/status identification;
- §211.82 — visual receipt examination and quarantine pending test/examination and release;
- §211.84 — representative sampling/testing, identity testing, supplier COA/reliability controls and QC release/rejection;
- §211.86 — controlled rotation of approved stock;
- §211.87 — retesting/reexamination when appropriate;
- §211.89 — rejected material quarantine/control;
- §211.94 — suitability and protection requirements for drug-product containers/closures;
- 21 CFR Part 4 for combination products;
- current QMSR under 21 CFR Part 820, effective February 2, 2026, incorporating ISO 13485:2016 and including supplier/purchasing controls through the incorporated quality-system framework.

This document summarizes engineering implications and does not reproduce copyrighted ISO text. Final applicability must be confirmed per customer/product intended use.

Reference URLs:
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-E/section-211.84
- https://www.law.cornell.edu/cfr/text/21/211.80
- https://www.law.cornell.edu/cfr/text/21/211.82
- https://www.law.cornell.edu/cfr/text/21/211.86
- https://www.law.cornell.edu/cfr/text/21/211.87
- https://www.law.cornell.edu/cfr/text/21/211.89
- https://www.law.cornell.edu/cfr/text/21/211.94
- https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr
- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/current-good-manufacturing-practice-requirements-combination-products

# 1. Objective

Define regulated supplier qualification and procurement controls while maintaining a clean boundary between commercial purchasing and GxP material eligibility.

# 2. System-of-Record Boundary

```text
Quality / eBMR
├ Supplier qualification
├ Approved Supplier List
├ Material/spec/source eligibility
├ Supplier quality status
├ COA/document requirement
└ Regulated procurement references

ERP or Native Procurement
├ PR
├ RFQ
├ PO
├ price/terms
└ financial references

GxP Material System
└ Receipt → Quarantine → QC → Release → Use
```

External ERP price, valuation or AP data never determines GxP material release.

# 3. Actors

- Requester
- Buyer
- Procurement Manager
- Supplier Quality Engineer/Manager
- QA Approver
- Warehouse Receiver
- QC
- Finance/ERP Integration Service
- Auditor

# 4. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| SUP-FR-001 | Supplier master | Maintain supplier legal identity, business name, addresses, sites, contacts, manufacturer-vs-distributor role, external IDs and lifecycle status. | One controlled supplier identity. |
| SUP-FR-002 | Manufacturer master | Separate actual manufacturer identity from commercial supplier/distributor where different. | Manufacturer genealogy exact. |
| SUP-FR-003 | Supplier qualification request | Initiate qualification for supplier/site/material category with scope, risk, requested evidence and owner. | Qualification controlled. |
| SUP-FR-004 | Supplier risk classification | Classify supplier/material criticality using released risk methodology and product/profile applicability. | Controls proportional. |
| SUP-FR-005 | Qualification evidence | Store questionnaire, certifications, licenses, audits, capability evidence, quality agreements, test history and attachments as versioned evidence. | Review basis retained. |
| SUP-FR-006 | Supplier audit | Plan/record audit scope, date, auditors, findings, response, CAPA/SCAR links and approval. | Supplier audit inspectable. |
| SUP-FR-007 | Supplier approval | Approve supplier for specific manufacturer site/material/specification/category/site/customer scope, not blanket global approval by default. | ASL granular. |
| SUP-FR-008 | Approved Supplier List | Maintain effective-dated supplier-material/site approval matrix with status Approved, Conditional, Suspended, Disqualified, Expired. | Procurement eligibility deterministic. |
| SUP-FR-009 | Requalification | Define expiry/review frequency/risk trigger; generate due alerts and block new procurement if policy requires. | Approval current. |
| SUP-FR-010 | Suspension | Quality can suspend supplier/material relationship with reason/signature; open PO/receipt impact assessed separately. | No silent continued use. |
| SUP-FR-011 | Disqualification | Permanent/controlled disqualification retains history and affected material/product impact. | Historical evidence preserved. |
| SUP-FR-012 | Conditional approval | Support temporary/conditional supplier use under defined scope, expiry, justification, enhanced inspection/testing and approval. | Exception bounded. |
| SUP-FR-013 | Quality agreement | Reference controlled quality agreement version, effective dates and obligations; renewal/expiry alerts. | Contract expectations linked. |
| SUP-FR-014 | Supplier change notification | Record supplier/manufacturer/process/material/site change notices and link to Change Control/impact assessment. | Supplier changes assessed. |
| SUP-FR-015 | Supplier performance | Track incoming acceptance, rejects, SCARs, complaints, deviations, delivery performance and quality metrics. | Requalification data driven. |
| SUP-FR-016 | SCAR initiation | Create supplier corrective-action request from incoming defect, deviation, audit or trend and track response/effectiveness. | QMS integration. |
| SUP-FR-017 | Material-source approval | Specific material/specification can have allowed supplier + manufacturer combinations and alternates. | Wrong source blocked. |
| SUP-FR-018 | Procurement item mapping | Map regulated material/spec version to purchasing description/code and ERP/native item without losing regulated identity. | Commercial/GxP identities separated. |
| SUP-FR-019 | Purchase requisition | Create PR with requesting site, material/spec version, quantity/UOM, need date, approved source requirements and project/batch reference if applicable. | Requirements exact. |
| SUP-FR-020 | PR approval | Configurable approval by amount/site/category plus quality gate for critical/unapproved source. | No buyer override. |
| SUP-FR-021 | RFQ | Optional RFQ to approved candidate suppliers, capturing commercial quote separately from qualification status. | Commercial comparison. |
| SUP-FR-022 | Supplier selection | Buyer may select only eligible supplier/manufacturer relationship unless controlled exception is approved. | ASL enforced. |
| SUP-FR-023 | Purchase order | PO includes exact regulated material/spec reference, supplier/manufacturer, quantity/UOM, delivery site and quality/document requirements. | Receipt expectations exact. |
| SUP-FR-024 | PO revision | Commercial changes versioned; regulated source/spec changes require revalidation/quality approval and may require new PO revision. | No silent source substitution. |
| SUP-FR-025 | COA/document requirement | PO may define required COA/CoC/test certificate/sterility certificate/document set. | Receipt completeness known. |
| SUP-FR-026 | Lot/document terms | PO can require supplier lot, manufacturer lot, manufacture/expiry/retest data and container identity information. | Traceability prepared. |
| SUP-FR-027 | ERP mode | If external ERP owns PR/RFQ/PO, eBMR receives validated references and enforces ASL/spec/source eligibility; ERP remains financial/commercial SoR. | Adapter boundary. |
| SUP-FR-028 | Native mode | If no ERP, native procurement supports PR/RFQ/PO and status without implementing GL/AP/tax settlement. | SME-ready. |
| SUP-FR-029 | Duplicate supplier detection | Detect likely duplicate legal/manufacturer identities before creation; merge prohibited without controlled data-management procedure. | Master quality. |
| SUP-FR-030 | Supplier document expiry | Alert certificates/agreements/audits nearing expiry and evaluate whether they affect eligibility. | No stale qualification. |
| SUP-FR-031 | Procurement audit | Audit source selection, approval, PO regulated-field changes, exceptions and external synchronization. | Traceable purchasing. |
| SUP-FR-032 | Inspection export | Provide supplier qualification/ASL/SCAR/audit/performance history for authorized review. | Inspection-ready. |

# 5. Supplier State Model

Supplier:
`DRAFT → UNDER_QUALIFICATION → APPROVED → SUSPENDED → APPROVED / DISQUALIFIED`

Supplier-material approval:
`PROPOSED → REVIEW → APPROVED/CONDITIONAL → EXPIRED/SUSPENDED/DISQUALIFIED`.

# 6. Data Model

## `supplier`
```text
id uuid PK
tenant_id uuid
supplier_code varchar(120)
legal_name varchar(255)
role_type varchar(40)
status varchar(40)
country varchar(80)
external_mappings jsonb
version bigint
```

## `supplier_site`
- supplier ID
- site identity/address
- manufacturer flag
- regulatory/certification refs
- status

## `supplier_qualification`
```text
id uuid PK
supplier_site_id uuid
scope jsonb
risk_class varchar(40)
status varchar(40)
effective_from timestamptz
expires_at timestamptz
quality_agreement_vault_id uuid
approval_signatures jsonb
version bigint
```

## `approved_supplier_material`
- supplier site
- manufacturer site
- material specification version
- receiving site
- approval status
- conditional controls
- effective dates
- test/inspection profile override

## `purchase_requisition`
- material spec
- quantity/UOM
- site
- need date
- source requirements
- status/version

## `purchase_order_ref`
- native/external mode
- PO number
- supplier/manufacturer
- material spec
- quantity/UOM
- revision
- regulated requirement snapshot
- external system version/sync status

# 7. APIs

- `POST /suppliers/v1`
- `POST /suppliers/{id}/qualifications`
- `POST /supplier-qualifications/{id}/approve`
- `POST /supplier-material-approvals`
- `POST /supplier-material-approvals/{id}/suspend`
- `GET /materials/{specId}/eligible-suppliers?site=...`
- `POST /procurement/v1/requisitions`
- `POST /procurement/v1/purchase-orders`
- `POST /procurement/v1/purchase-orders/{id}/revise`
- `GET /procurement/v1/purchase-orders/{po}/receipt-expectation`

Errors:
`SUPPLIER_NOT_APPROVED`, `SUPPLIER_APPROVAL_EXPIRED`, `MATERIAL_SOURCE_NOT_APPROVED`, `MANUFACTURER_MISMATCH`, `QUALITY_AGREEMENT_EXPIRED`, `PO_REGULATED_CHANGE_REQUIRES_APPROVAL`.

# 8. UI

1. Supplier Catalogue
2. Supplier Qualification
3. Supplier Audit
4. Approved Supplier List
5. Material/Source Matrix
6. Supplier Performance
7. SCAR Links
8. PR
9. RFQ/Quote Comparison
10. PO
11. PO Regulated Requirements
12. Supplier Quality Dashboard

# 9. ERP Integration

Provider operations:
- get/create PR;
- get/create/revise PO;
- supplier/item mapping;
- PO status;
- expected receipt.

All external callbacks use source IDs and idempotency.

# 10. Audit / Signature

E-sign required according to policy for:
- supplier qualification approval;
- conditional approval;
- suspension/disqualification;
- regulated source exception;
- critical PO source/spec change.

# 11. Events

- SupplierQualificationApproved
- SupplierMaterialApproved
- SupplierSuspended
- SupplierDisqualified
- PurchaseRequisitionApproved
- PurchaseOrderIssued
- PurchaseOrderRegulatedFieldsChanged

# 12. Repository Structure

```text
services/gxp-api/src/modules/supplier-quality/
services/gxp-api/src/modules/procurement/
apps/ebmr_frappe/ebmr/supplier_quality/
apps/ebmr_frappe/ebmr/procurement/
connectors/erp/
```

# 13. Implementation Sequence

1. supplier/site;
2. qualification;
3. ASL/source matrix;
4. performance/expiry;
5. PR;
6. PO reference/native PO;
7. ERP adapter;
8. quality agreements;
9. suspension/change impact;
10. reports.

# 14. Tests

- approved supplier PO;
- unapproved source blocked;
- supplier approval expires;
- conditional source;
- distributor vs manufacturer mismatch;
- PO revision changes source;
- expired certificate;
- duplicate external callback;
- supplier suspended with open PO;
- ERP unavailable;
- native procurement mode;
- audit/export.

# 15. Acceptance

A buyer cannot procure a critical material from an unapproved supplier/manufacturer combination through normal workflow, regardless of whether the PO originates in native procurement or external ERP.

# 16. Codex / Claude Rules

Never treat ERP supplier master as automatically quality-approved.
Never combine supplier and manufacturer identity when they are different.
Never let price/availability override ASL eligibility.
Never implement full accounting in this module.
