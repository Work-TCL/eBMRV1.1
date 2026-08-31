# US eBMR / eDHR Regulated Manufacturing Platform
## Document 21 — Material Dispensing & Weighing Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-MAT-002C  
**Parent Documents:** Documents 01–17  
**Primary Dependencies:** Documents 03–20; Rules Engine; Batch Execution; Edge Gateway/Balance; Equipment  
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

Define controlled material picking, scanning, weighing, verification, labeling and issue to a batch.

# 2. Workflow

```text
Batch Material Requirement
  ↓
Reserve / Select Eligible Lot
  ↓
Scan Material + Lot + Container
  ↓
Verify Operator / Booth / Balance
  ↓
Calculate Target
  ↓
Tare
  ↓
Weigh / Stable Reading
  ↓
Tolerance Evaluation
  ↓
Verifier / E-Sign if required
  ↓
Create Dispensed Container + Label
  ↓
Inventory Transaction + Genealogy
  ↓
Complete
```

# 3. Functional Requirements

| ID | Functionality | Detailed behavior | Acceptance intent |
|---|---|---|---|
| DSP-FR-001 | Dispensing order | Create dispensing requirement from issued batch recipe snapshot with material spec, target quantity/formula, tolerance, stage and batch. | Exact demand. |
| DSP-FR-002 | Candidate selection | Suggest eligible released lots/containers using Inventory selection rules; operator cannot select excluded lot. | Wrong material prevented. |
| DSP-FR-003 | Material scan | Require material/lot/container barcode scan where configured and verify against requirement. | Identity check. |
| DSP-FR-004 | Location scan | Optionally verify warehouse/dispensing booth/location before operation. | Context. |
| DSP-FR-005 | Operator qualification | Require active dispensing qualification/training and site access. | Qualified personnel. |
| DSP-FR-006 | Balance eligibility | Verify balance/device registration, calibration, qualification, location and status before use. | Valid equipment. |
| DSP-FR-007 | Tare | Capture tare method/value/container and device source where applicable. | Net weight reproducible. |
| DSP-FR-008 | Target quantity | Target from recipe calculation, including potency adjustment where configured; exact rule version retained. | No manual target change. |
| DSP-FR-009 | Live balance capture | Read stable weight from Edge/Balance adapter with device identity, timestamp and quality. | Automated evidence. |
| DSP-FR-010 | Stability rule | Balance adapter/config defines stable-reading criteria and unit/precision. | No transient reading. |
| DSP-FR-011 | Manual weight fallback | Allowed only when recipe/device fallback policy permits; requires reason, manual source, possibly independent verification/signature. | Controlled fallback. |
| DSP-FR-012 | Tolerance | Evaluate actual against released tolerance rule; outside tolerance blocks completion/creates exception. | Correct quantity. |
| DSP-FR-013 | Multiple additions | Support incremental weigh additions while preserving readings and final accepted net. | Full history. |
| DSP-FR-014 | Overweight correction | If allowed, controlled removal/reweigh records all readings and material disposition; original overweight reading retained. | No overwrite. |
| DSP-FR-015 | Underweight correction | Additional material can be added from same/allowed lot according to policy; each addition traceable. | Accurate genealogy. |
| DSP-FR-016 | Potency adjustment | Use released assay/potency result and rule to determine active material target; verifier sees source and calculation. | Drug support. |
| DSP-FR-017 | Multi-lot dispensing | Use multiple approved lots only when recipe/profile permits; genealogy records each exact quantity. | No hidden pooling. |
| DSP-FR-018 | Independent verification | Support verifier scan/check of material/lot/target/actual/device and e-signature where required. | Second-person check. |
| DSP-FR-019 | Dispensed container | Create dispensed-material container/package identity with label and exact source lot/container quantities. | Shop-floor trace. |
| DSP-FR-020 | Dispensing label | Print controlled label including material, batch, dispensed qty/UOM, source lot(s), date/time, status, expiry/use-by if configured. | Identity maintained. |
| DSP-FR-021 | Label reprint | Controlled reprint with reason and count/history. | No uncontrolled duplicates. |
| DSP-FR-022 | Material issue | On accepted dispense, post inventory transaction/reservation consumption for exact source quantity. | Stock consistent. |
| DSP-FR-023 | Genealogy | Create source lot/container → dispensed container → batch relationship. | Trace. |
| DSP-FR-024 | Partial source container | Update remaining source-container quantity and open/reseal status. | Inventory correct. |
| DSP-FR-025 | Expiry/retest recheck | Revalidate source lot at dispense completion, not only initial selection, for long operations. | No stale eligibility. |
| DSP-FR-026 | Environmental/booth condition | Where required verify dispensing area/environment status before operation. | Controlled environment. |
| DSP-FR-027 | Line/booth clearance | Require applicable booth/area clearance status before dispensing. | Cross-contamination prevention. |
| DSP-FR-028 | Exception | Wrong scan, ineligible lot, balance failure, tolerance failure, qualification lapse or environment issue creates/block according to rule. | Fail safe. |
| DSP-FR-029 | Pause/resume | Preserve in-progress readings; resume revalidates material/balance/operator/status according to policy. | Interrupted work safe. |
| DSP-FR-030 | Cancel | Cancel before completion returns reservation and retains attempted evidence/reason; no consumption posted unless physically handled per policy. | No lost trace. |
| DSP-FR-031 | Bulk dispensing | Support batch/staged dispensing queue but each requirement has independent identity, eligibility, weight and genealogy. | Efficiency without ambiguity. |
| DSP-FR-032 | Audit/export | Dispensing record includes target/calculation, source lots, all relevant readings, actual, equipment, operators/verifier, signatures, labels and exceptions. | eBMR evidence complete. |

# 4. Data Model

## `dispensing_order`
```text
id uuid PK
batch_id uuid
batch_step_id uuid
material_requirement_id uuid
material_spec_version_id uuid
target_rule_id uuid
target_qty numeric(24,8)
target_uom varchar(40)
tolerance_rule_id uuid
state varchar(40)
version bigint
```

## `dispensing_source`
- order ID
- material lot ID
- source container ID
- reserved quantity
- actual taken quantity
- source eligibility evaluation

## `weighing_session`
- order
- balance ID
- operator
- booth/location
- tare
- readings
- stable result
- source/manual flag
- rule version
- start/end

## `dispensed_container`
- new container ID
- batch
- material
- actual quantity
- UOM
- source list
- status
- label print job

# 5. Balance Adapter Contract

Operations:
- identify device;
- get current unit;
- tare/status;
- stable reading;
- device health;
- calibration/status metadata.

Return:
```json
{
  "device_id":"BAL-001",
  "reading":"12.345",
  "uom":"kg",
  "stable":true,
  "source_timestamp":"...",
  "sequence":"...",
  "quality":"GOOD"
}
```

# 6. APIs

- `POST /dispensing/v1/orders`
- `POST /dispensing/v1/orders/{id}/select-source`
- `POST /dispensing/v1/orders/{id}/start`
- `POST /dispensing/v1/orders/{id}/readings`
- `POST /dispensing/v1/orders/{id}/manual-reading`
- `POST /dispensing/v1/orders/{id}/verify`
- `POST /dispensing/v1/orders/{id}/complete`
- `POST /dispensing/v1/orders/{id}/cancel`
- `GET /dispensing/v1/queue`

Errors:
`WRONG_MATERIAL`, `LOT_INELIGIBLE`, `CONTAINER_INELIGIBLE`, `BALANCE_INELIGIBLE`, `READING_UNSTABLE`, `WEIGHT_OUT_OF_TOLERANCE`, `MANUAL_FALLBACK_NOT_ALLOWED`, `VERIFIER_REQUIRED`, `SOURCE_QUANTITY_INSUFFICIENT`.

# 7. UI

Large shop-floor workflow:
1. Dispensing Queue
2. Scan Batch/Requirement
3. Scan Source
4. Equipment/Booth Check
5. Target Calculation
6. Live Weight
7. Tolerance
8. Verification
9. Label
10. Completed Record

# 8. Concurrency

Completion transaction must:
- recheck source lot eligibility;
- lock/verify source available quantity;
- commit inventory transaction + genealogy + dispense result atomically or with authoritative same-DB boundaries.

# 9. Audit/Signature

Audit material scans, selected sources, target, readings, manual fallback, tolerance exceptions, verifier/signature and final inventory/genealogy link.

# 10. Events

- DispensingStarted
- DispensingSourceSelected
- WeighingReadingAccepted
- WeighingExceptionRaised
- DispensingVerified
- MaterialDispensed
- DispensingCancelled

# 11. Repository Structure

```text
services/gxp-api/src/modules/dispensing/
apps/ebmr_frappe/ebmr/dispensing/
edge/gateway/plugins/balance/
connectors/label-printing/
```

# 12. Tests

- normal balance dispense;
- wrong material scan;
- quarantine/expired source;
- two batches same final stock;
- balance calibration expired;
- unstable reading;
- overweight correction;
- multi-lot allowed/disallowed;
- potency-adjusted target;
- manual fallback allowed/disallowed;
- verifier SoD;
- pause then retest date passes;
- label reprint;
- cancel.

# 13. Acceptance

A representative drug/DDCP material must be dispensed with exact lot/container trace, validated target/tolerance, balance evidence and batch genealogy without manual database/inventory corrections.

# 14. Codex / Claude Rules

Never trust barcode text without server lookup.
Never accept device reading without registered device identity/quality.
Never modify target quantity in UI outside released calculation.
Never hide overweight/failed readings.
