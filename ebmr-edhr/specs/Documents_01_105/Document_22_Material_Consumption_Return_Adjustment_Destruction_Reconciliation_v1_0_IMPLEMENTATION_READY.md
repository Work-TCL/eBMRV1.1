# US eBMR / eDHR Regulated Manufacturing Platform
## Document 22 — Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-MAT-002D  
**Parent Documents:** Documents 01–17  
**Primary Dependencies:** Documents 03–21; Yield/Reconciliation; QMS Deviations; ERP/WMS; Genealogy  
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

Define the complete post-dispensing material lifecycle and ensure every regulated quantity is accounted for before batch completion/release.

# 2. Lifecycle

```text
DISPENSED
   ↓ issue/stage
IN_PRODUCTION
   ├─→ CONSUMED
   ├─→ RETURNED
   ├─→ SAMPLE
   ├─→ REJECTED
   ├─→ DESTROYED
   └─→ APPROVED_LOSS
          ↓
      RECONCILIATION
          ↓
   ACCEPTABLE / VARIANCE
```

# 3. Functional Requirements

| ID | Functionality | Detailed behavior | Acceptance intent |
|---|---|---|---|
| CON-FR-001 | Issue to production | Move dispensed/material container to production staging/use with exact batch/step reference and status. | Custody trace. |
| CON-FR-002 | Consumption | Record actual material quantity consumed in step, source dispensed container/lot and time. | Actual use evidence. |
| CON-FR-003 | Automatic consumption | Where machine/process provides authoritative quantity, accept via validated integration/rule; otherwise controlled manual capture. | Flexible source. |
| CON-FR-004 | Partial consumption | Track remaining quantity in dispensed container and resulting status/location. | No assumed full use. |
| CON-FR-005 | Return to warehouse | Return unused eligible material with quantity, seal/container condition, storage condition and status reevaluation. | Safe return. |
| CON-FR-006 | Return rejection | If return condition unsuitable, route to quarantine/reject/destruction workflow rather than normal stock. | No bad return. |
| CON-FR-007 | Material re-status after return | Product/profile may require QC/QA evaluation after exposure/opening/temperature excursion before reuse. | Risk controlled. |
| CON-FR-008 | Excess material | Record excess generated/remaining from dispensing/process and controlled disposition. | Balance complete. |
| CON-FR-009 | Process loss | Record allowed loss category/quantity/source and approval/rule. | Variance explained. |
| CON-FR-010 | Spill | Record spill quantity/estimate, quality/deviation link and cleanup evidence where required. | Incident trace. |
| CON-FR-011 | Sample withdrawal | Account for QC/in-process/reserve sample quantity and sample ID. | Balance. |
| CON-FR-012 | Reject/scrap material | Record rejected process material quantity, reason, location and disposition. | No ghost stock. |
| CON-FR-013 | Inventory adjustment | Exceptional positive/negative adjustment requires controlled reason, evidence, authorization and audit; cannot be routine correction for software defects. | Controlled discrepancy. |
| CON-FR-014 | Adjustment SoD | High-risk adjustment can require independent approval; user cannot approve own adjustment if configured. | Fraud/error control. |
| CON-FR-015 | Destruction request | Create destruction disposition for rejected/expired/excess/material/product with exact lot/container/quantity. | Scope exact. |
| CON-FR-016 | Destruction authorization | Require QA/authorized approval and witness where policy requires. | Controlled disposition. |
| CON-FR-017 | Destruction execution | Record method, date/time, performers/witnesses, quantity, evidence and destination/vendor where applicable. | Evidence. |
| CON-FR-018 | Third-party destruction | Track approved vendor/manifest/certificate and chain of custody. | External disposition trace. |
| CON-FR-019 | Reconciliation scope | Calculate material balance by batch/material requirement/lot/container/stage according to released rules. | Configurable scope. |
| CON-FR-020 | Source categories | Reconciliation includes dispensed/issued, consumed, returned, samples, rejected, destroyed, approved loss and unexplained variance. | Complete mass balance. |
| CON-FR-021 | Tolerance | Use Document 08/17 released tolerance/rounding/UOM rules. | Deterministic. |
| CON-FR-022 | Variance blocker | Out-of-tolerance/unexplained variance creates deviation/investigation and blocks production completion/release as configured. | No silent loss. |
| CON-FR-023 | Correction recalculation | Any corrected transaction creates superseding transaction/event and automatically recalculates affected reconciliation; original remains. | History. |
| CON-FR-024 | No transaction deletion | Consumption/return/adjustment/destruction records are immutable transactions; correction is reversal/supersession pattern. | Ledger integrity. |
| CON-FR-025 | ERP posting | Post consumption/return/scrap/destruction quantity/reference after GxP commit; retries idempotent. | Commercial sync. |
| CON-FR-026 | ERP discrepancy | Compare external postings and create reconciliation issue; ERP never overwrites GxP transaction ledger. | Boundary. |
| CON-FR-027 | Genealogy impact | Consumption creates genealogy; return/destruction preserves source/material identity and affected batch links. | Trace. |
| CON-FR-028 | Batch completion gate | All required material transactions/reconciliation must be current/acceptable before Production Complete. | eBMR complete. |
| CON-FR-029 | QA review | Review-by-exception shows adjustments, spills, losses, destruction and failed reconciliation. | Quality visibility. |
| CON-FR-030 | Audit/export | Batch/material history export includes all source/quantity/disposition/reconciliation records and signatures. | Inspection-ready. |
| CON-FR-031 | Cross-batch prohibition | A dispensed container assigned to Batch A cannot be consumed in Batch B unless a controlled return/reissue process creates new authorization. | No cross-use. |
| CON-FR-032 | Performance | Batch reconciliation may aggregate large device/packaging/component transaction sets asynchronously but current status is versioned. | Scale safe. |

# 4. Data Model

All quantity changes use `inventory_transaction` from Document 20.

Additional records:

## `material_consumption`
```text
id uuid PK
batch_id uuid
step_id uuid
dispensed_container_id uuid
material_lot_id uuid
quantity numeric(24,8)
uom varchar(40)
source_type varchar(40)
source_id varchar(255)
occurred_at timestamptz
transaction_id uuid
```

## `material_return`
- source batch/dispensed container
- quantity
- container condition
- storage/exposure evidence
- target location
- resulting quality status
- transaction ID

## `inventory_adjustment_request`
- scope
- expected quantity
- observed quantity
- variance
- reason
- evidence
- approval/signature
- resulting reversal/adjustment transactions

## `destruction_record`
- material/product scope
- lot/container
- quantity
- reason
- method
- vendor
- witnesses
- evidence
- transaction

## `material_reconciliation`
- batch/material requirement
- source quantities
- calculation rule/version
- outcome
- variance
- linked deviation
- version

# 5. Correction Pattern

Never edit transaction quantity.

Example:
```text
Original CONSUME 10.0 kg
      ↓ correction approved
REVERSAL 10.0 kg
      +
Correct CONSUME 9.5 kg
```

Both transactions link to correction record and audit.

# 6. APIs

- `POST /materials/v1/consumptions`
- `POST /materials/v1/returns`
- `POST /inventory/v1/adjustments`
- `POST /inventory/v1/adjustments/{id}/approve`
- `POST /materials/v1/destructions`
- `POST /materials/v1/destructions/{id}/execute`
- `POST /reconciliation/v1/batches/{batchId}/materials/evaluate`
- `GET /reconciliation/v1/batches/{batchId}/materials`

Errors:
`BATCH_MISMATCH`, `QUANTITY_EXCEEDS_AVAILABLE`, `RETURN_CONDITION_REVIEW_REQUIRED`, `ADJUSTMENT_APPROVAL_REQUIRED`, `DESTRUCTION_NOT_AUTHORIZED`, `RECONCILIATION_FAILED`, `ERP_POSTING_PENDING`.

# 7. UI

1. Batch Material Usage
2. Consume
3. Return
4. Loss/Spill/Sample
5. Adjustment Request
6. Destruction
7. Reconciliation
8. ERP Posting/Reconciliation
9. Material History

# 8. ERP Integration

After each committed GxP movement:
- enqueue external posting;
- map transaction type;
- idempotency key = GxP transaction ID;
- persist external document/reference;
- retry;
- compare posted quantity.

ERP failure appears as integration exception, not GxP transaction rollback unless process explicitly requires synchronous external confirmation before physical action.

# 9. Audit/Signature

Signatures may be required for:
- high-risk adjustment;
- destruction;
- exceptional return/re-status;
- reconciliation acceptance outside nominal rules (through deviation).

# 10. Events

- MaterialConsumed
- MaterialReturned
- MaterialSampled
- MaterialLossRecorded
- InventoryAdjustmentApproved
- MaterialDestroyed
- MaterialReconciliationCalculated
- MaterialReconciliationFailed
- ERPInventoryPostingFailed

# 11. Repository Structure

```text
services/gxp-api/src/modules/material-usage/
services/gxp-api/src/modules/destruction/
services/gxp-api/src/modules/material-reconciliation/
apps/ebmr_frappe/ebmr/material_usage/
```

# 12. Implementation Sequence

1. consumption;
2. partial/remaining;
3. return;
4. samples/losses;
5. adjustments/reversal pattern;
6. destruction;
7. reconciliation;
8. ERP posting;
9. batch-completion integration.

# 13. Tests

- full consume;
- partial consume;
- cross-batch attempt;
- return acceptable;
- return needs quarantine;
- spill;
- sample withdrawal;
- high-risk adjustment;
- self-approval denied;
- destruction with witness;
- third-party destruction;
- failed reconciliation;
- correction/reversal;
- ERP retry duplicate;
- batch completion blocked.

# 14. Acceptance

For every material requirement in a representative DDCP batch, the system must reconcile the full path from source lot/container through dispense, consume/return/sample/loss/destruction and produce zero/unresolved variance according to released rules before release.

# 15. Codex / Claude Rules

Never edit inventory ledger transaction.
Never use generic stock adjustment to hide failed reconciliation.
Never consume a container against a different batch without controlled return/reissue.
Never let ERP posting success define GxP consumption truth.
