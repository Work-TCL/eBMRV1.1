# US eBMR / eDHR Regulated Manufacturing Platform
## Document 19 — Material Receipt, Quarantine & Quality Status Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-MAT-002A  
**Parent Documents:** Documents 01–17  
**Primary Dependencies:** Documents 03–18; Native QC/LIMS; Warehouse; QMS Deviations  
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

Define controlled receipt, identification, quarantine, sampling/testing and quality disposition of incoming materials, components, drug-product containers and closures.

# 2. State Model

```text
EXPECTED
  ↓ receipt
RECEIVED
  ↓ initial examination
QUARANTINE
  ├─→ SAMPLING
  ├─→ TESTING
  ↓
QC_DISPOSITION_PENDING
  ├─→ RELEASED
  ├─→ REJECTED
  ├─→ RETEST_DUE
  └─→ CONDITIONAL (only configured controlled path)
```

Rejected/expired/retest-due stock cannot be selected for manufacturing.

# 3. Functional Requirements

| ID | Functionality | Detailed behavior | Acceptance intent |
|---|---|---|---|
| RCV-FR-001 | Expected receipt | Load PO/transfer expectation with exact material/spec/source/quantity/document requirements. | Receiver knows expected material. |
| RCV-FR-002 | Receipt transaction | Create immutable receipt ID, site, date/time, receiver, carrier/reference, PO/source and received quantity. | Receipt attributable. |
| RCV-FR-003 | Visual examination | Capture appropriate labeling, damage, broken seals, contamination and shipment-condition observations before acceptance into quarantine. | 211.82-style receipt check. |
| RCV-FR-004 | Material identity | Match received material code/name/spec to expected material; mismatch creates hold/deviation, not silent remapping. | Wrong material blocked. |
| RCV-FR-005 | Supplier/manufacturer identity | Capture supplier and actual manufacturer and validate against approved source matrix. | Source eligibility checked. |
| RCV-FR-006 | Supplier lot | Capture supplier lot/batch number exactly as received. | Traceability. |
| RCV-FR-007 | Manufacturer lot | Capture manufacturer lot where distinct. | Source traceability. |
| RCV-FR-008 | Internal lot | Generate unique internal lot code for each received lot/shipment grouping according to site policy. | Distinctive status code. |
| RCV-FR-009 | Container identity | Create individual/container-group IDs and optional barcodes/QR labels. | Sampling/dispensing exact. |
| RCV-FR-010 | Quantity | Capture received gross/net/accepted quantity and UOM with conversion rules. | Inventory accurate. |
| RCV-FR-011 | Manufacture/expiry/retest | Capture available manufacture, expiry and retest dates with source/evidence and validation. | Eligibility later. |
| RCV-FR-012 | COA/CoC | Capture required documents, file hash, source and document completeness. | Supplier evidence linked. |
| RCV-FR-013 | COA extraction | AI/OCR may assist data entry later, but extracted data is advisory until verified; original document remains evidence. | No autonomous release. |
| RCV-FR-014 | Shipment conditions | Capture temperature logger/transport condition evidence where required and generate excursion if outside rule. | Cold-chain support. |
| RCV-FR-015 | Automatic quarantine | All applicable incoming regulated materials/containers/closures enter QUARANTINE by default until required test/examination and QC disposition. | No direct released receipt. |
| RCV-FR-016 | Physical/location quarantine | Assign allowed quarantine location/zone; system prevents issue/dispense from quarantined stock. | Status enforced. |
| RCV-FR-017 | Status label | Generate container/lot status label containing internal lot/container ID, material, status and other configured fields. | Physical/digital alignment. |
| RCV-FR-018 | Sampling request | Create sampling order based on material/spec/supplier risk/lot/shipment and sampling plan. | QC workflow initiated. |
| RCV-FR-019 | Container selection | Sampling plan identifies container(s) selected and quantity; actual selected containers recorded. | Representative sample trace. |
| RCV-FR-020 | Sampling execution | Capture sampler, date/time, method/procedure reference, container, sample ID and reseal/marking evidence. | 211.84-style evidence. |
| RCV-FR-021 | Aseptic sampling | Where required enforce sterile equipment/aseptic sampling qualification/profile and environment evidence. | Sterile materials supported. |
| RCV-FR-022 | Sample chain of custody | Track sample container/location/transfer to QC/LIMS and status. | Sample integrity. |
| RCV-FR-023 | Identity test | For applicable drug components require identity testing rule and result before release; supplier COA alone cannot bypass required identity testing. | 211.84 support. |
| RCV-FR-024 | Supplier COA reliance | Where permitted by profile, accept supplier analysis only with approved supplier-reliability status and required manufacturer testing/identity controls. | Conditional reliance. |
| RCV-FR-025 | Incoming QC | Link required tests/specification, native QC or LIMS results and result versions. | Disposition evidence. |
| RCV-FR-026 | Release disposition | Authorized Quality transitions lot/container group to RELEASED only after required evidence/rules complete. | QC authority. |
| RCV-FR-027 | Reject disposition | Failed lot becomes REJECTED and is controlled under segregated status/location to prevent use. | 211.89 support. |
| RCV-FR-028 | Conditional/under-deviation use | Default disabled; if customer procedure permits exceptional use, require deviation, quality approval, bounded scope and explicit material eligibility rule. | Exception controlled. |
| RCV-FR-029 | Retest status | Material may transition to RETEST_DUE/QUARANTINE and requires reexamination/retest before continued use where required. | 211.87 support. |
| RCV-FR-030 | Partial lot disposition | Allow container-level partial release/reject only when sampling/spec/profile explicitly permits and genealogy remains exact. | No ambiguous status. |
| RCV-FR-031 | Receipt discrepancy | Over/short/damaged/wrong lot/document mismatch generates discrepancy workflow and ERP reconciliation. | Commercial/GxP synchronized. |
| RCV-FR-032 | Audit/export | Full receipt→quarantine→sample→QC→release/reject history is exportable. | Inspection-ready. |

# 4. Data Model

## `material_receipt`
```text
id uuid PK
tenant_id uuid
site_id uuid
receipt_number varchar(120)
po_reference varchar(160)
supplier_id uuid
manufacturer_id uuid
received_at timestamptz
receiver_subject_id uuid
state varchar(40)
version bigint
shipment_condition_status varchar(40)
```

## `material_lot`
```text
id uuid PK
material_spec_version_id uuid
internal_lot_no varchar(160)
supplier_lot_no varchar(200)
manufacturer_lot_no varchar(200)
receipt_id uuid
manufacture_date date
expiry_date date
retest_date date
quality_status varchar(40)
quality_status_version bigint
released_at timestamptz
release_signature_id uuid
```

## `material_container`
- lot ID
- container code/barcode
- received/current quantity
- UOM
- current warehouse/location
- quality status inheritance/override
- sampled flag
- seal/damage status

## `sampling_order`
- lot
- sampling plan/version
- selected containers
- sample quantities
- assigned sampler
- status

## `material_quality_disposition`
- lot/container scope
- evidence/test references
- decision
- signature
- effective time
- reason/deviation

# 5. APIs

- `POST /materials/v1/receipts`
- `POST /materials/v1/receipts/{id}/examine`
- `POST /materials/v1/lots/{id}/sampling-orders`
- `POST /sampling-orders/{id}/collect`
- `POST /materials/v1/lots/{id}/release`
- `POST /materials/v1/lots/{id}/reject`
- `POST /materials/v1/lots/{id}/retest`
- `GET /materials/v1/lots/{id}/quality-status`
- `GET /materials/v1/lots/{id}/release-readiness`

Errors:
`SOURCE_NOT_APPROVED`, `RECEIPT_LABEL_MISMATCH`, `CONTAINER_DAMAGED`, `COA_REQUIRED`, `SAMPLING_INCOMPLETE`, `IDENTITY_TEST_REQUIRED`, `QC_INCOMPLETE`, `QUALITY_RELEASE_NOT_AUTHORIZED`.

# 6. UI

1. Expected Receipts
2. Receiving
3. Visual Examination
4. Lot/Container Labeling
5. Quarantine Dashboard
6. Sampling
7. QC/LIMS Status
8. Quality Disposition
9. Retest/Expiry Dashboard
10. Receipt History

# 7. Quality Status Engine

Material eligibility queries must not simply read a mutable status text.
They evaluate:
- current approved disposition;
- expiry/retest;
- supplier/source status at relevant time;
- site;
- product/spec applicability;
- hold/deviation;
- container-specific restrictions.

# 8. ERP/WMS Sync

After GxP receipt:
- post/reference receipt to ERP;
- quarantine stock status mapping;
- after QA release/reject, send status event;
- external failure remains pending/reconciled;
- ERP status never independently releases GxP lot.

# 9. Audit/Signature

Signature required for Quality release/reject/conditional-use approval according to profile.
Receipt/sampling/COA/QC source and corrections audited.

# 10. Events

- MaterialReceived
- MaterialQuarantined
- SamplingOrdered
- SampleCollected
- MaterialQCCompleted
- MaterialReleased
- MaterialRejected
- MaterialRetestRequired
- ReceiptDiscrepancyRaised

# 11. Repository Structure

```text
services/gxp-api/src/modules/material-receipt/
services/gxp-api/src/modules/material-quality-status/
apps/ebmr_frappe/ebmr/receiving/
apps/ebmr_frappe/ebmr/sampling/
```

# 12. Implementation Sequence

1. receipt;
2. lot/container;
3. automatic quarantine;
4. labels;
5. sampling;
6. QC adapter;
7. release/reject;
8. retest;
9. ERP sync;
10. reports.

# 13. Tests

- correct receipt;
- wrong supplier;
- wrong manufacturer;
- damaged seal;
- missing COA;
- quarantine issue attempt;
- sampling selected containers;
- identity test missing;
- supplier COA permitted/not permitted;
- release;
- reject;
- retest due;
- partial container disposition;
- ERP outage;
- stale QA signature.

# 14. Acceptance

No received regulated material can become eligible for dispensing merely because goods receipt was posted. The exact Quality release path must complete.

# 15. Codex / Claude Rules

Never initialize received regulated stock as RELEASED.
Never let warehouse/ERP user directly change GxP quality status.
Never overwrite supplier/manufacturer lot identity after use without controlled correction/impact assessment.
