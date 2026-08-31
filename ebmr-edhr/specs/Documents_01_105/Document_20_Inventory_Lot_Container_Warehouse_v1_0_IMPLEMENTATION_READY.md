# US eBMR / eDHR Regulated Manufacturing Platform
## Document 20 — Inventory, Lot/Container & Warehouse Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-MAT-002B  
**Parent Documents:** Documents 01–17  
**Primary Dependencies:** Documents 03–19; Genealogy; ERP/WMS; Edge/Barcode  
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

Define regulated inventory control for released/quarantined/rejected materials and components across lots, containers, warehouses and sites.

# 2. Core Principle

Never store only a mutable “current stock” quantity.

```text
Immutable Inventory Transactions
          ↓
Balance Projection
          ↓
Eligibility / Reservation
          ↓
Dispensing / Consumption
```

# 3. Functional Requirements

| ID | Functionality | Detailed behavior | Acceptance intent |
|---|---|---|---|
| INV-FR-001 | Warehouse master | Define site warehouse, zones, rooms, bins/locations, environmental class and permitted status/material categories. | Location controlled. |
| INV-FR-002 | Status segregation | Locations can be designated quarantine, released, rejected, return, destruction, controlled-temperature, sterile/component or other configured zones. | Physical/digital status aligned. |
| INV-FR-003 | Lot inventory | Maintain on-hand/reserved/available quantity by material lot and container. | Exact stock. |
| INV-FR-004 | Container inventory | Track individual container quantity/status/location where material handling requires it. | Dispensing source exact. |
| INV-FR-005 | Unit-of-measure | Canonical UOM and validated conversion used for stock transactions. | No unit ambiguity. |
| INV-FR-006 | Inventory transaction ledger | Every receipt, transfer, reserve, issue, dispense, consume, return, adjust, reject/destruct creates immutable transaction. | No editable balance. |
| INV-FR-007 | Derived balance | Current quantity derives from transaction ledger/projection and is reconciliation-tested. | History authoritative. |
| INV-FR-008 | Location transfer | Move lot/container between permitted locations with scanner/manual verification and status compatibility. | Wrong zone blocked. |
| INV-FR-009 | Inter-site transfer | Controlled shipment/receipt relationship preserving lot/container identity and quality state rules. | Multi-plant trace. |
| INV-FR-010 | Reservation | Reserve quantity/containers for batch/order without consuming; prevent over-reservation. | Planning safe. |
| INV-FR-011 | Reservation expiry/release | Reservation has status/expiry/cancel rules and can be released when batch changes. | No stranded stock. |
| INV-FR-012 | FEFO/FIFO policy | Selection engine prioritizes approved stock by product/profile rule; drug-side baseline supports oldest-approved stock rotation and deviation path. | Stock rotation compliant. |
| INV-FR-013 | Expiry | Expired material automatically becomes ineligible and may trigger status/hold workflow. | No expired use. |
| INV-FR-014 | Retest due | Retest-due material becomes ineligible/quarantine according to profile until reapproved. | 211.87 support. |
| INV-FR-015 | Quality hold | Quality can place lot/container hold independent of warehouse location. | Immediate block. |
| INV-FR-016 | Recall/blocked source | Supplier/material/quality event can block affected lots/containers through impact command. | Quality integrated. |
| INV-FR-017 | Product eligibility | Material lot may be released generally but only eligible for products/sites/spec versions defined by rules. | Correct product use. |
| INV-FR-018 | Alternative material | Selection of approved alternative material requires recipe/rule compatibility and possibly change/deviation approval. | No ad hoc substitution. |
| INV-FR-019 | Barcode | Generate/accept controlled barcode for material/lot/container/location; scan verifies expected identity. | Shop-floor reliability. |
| INV-FR-020 | Cycle count | Perform controlled inventory counts, discrepancies and adjustment approval without altering GxP transaction history. | Inventory accuracy. |
| INV-FR-021 | Physical count freeze | Optional location/item count lock prevents conflicting warehouse movements during count. | Concurrency safe. |
| INV-FR-022 | Negative inventory | GxP inventory cannot go negative through normal transaction. | Constraint. |
| INV-FR-023 | Container split | Split container creates child container identities with quantity conservation and parent relationship. | Traceability. |
| INV-FR-024 | Container merge | Merge only when material/spec/lot/status compatibility rules permit; preserve source relationships. | No identity loss. |
| INV-FR-025 | Partial container | Track remaining quantity after sampling/dispensing/return and reseal/open status where relevant. | Usability. |
| INV-FR-026 | Storage condition | Associate material/location storage requirements and environmental evidence/reference; excursion creates hold/impact when configured. | Quality protection. |
| INV-FR-027 | Label status | Container status labels reprinted only through controlled reprint with current quality status/version. | Physical status current. |
| INV-FR-028 | Inventory reconciliation with ERP | Compare GxP quantity to ERP/WMS quantity/reference; mismatches flagged, never auto-resolved by overwriting GxP ledger. | Boundary. |
| INV-FR-029 | Search | Search stock by material/spec/lot/container/status/location/expiry/retest/supplier/manufacturer. | Operational. |
| INV-FR-030 | Genealogy | Inventory transactions create/maintain lot/container provenance used by Document 13. | Traceable. |
| INV-FR-031 | Retention | Transaction history retained according to associated regulated record/material policy. | Evidence enduring. |
| INV-FR-032 | Performance | Support thousands/millions of inventory transactions with indexed ledger and balance projection. | Enterprise scale. |

# 4. Data Model

## `warehouse_location`
```text
id uuid PK
tenant_id uuid
site_id uuid
warehouse_code varchar(100)
location_code varchar(120)
zone_type varchar(50)
status varchar(40)
environment_profile_id uuid
```

## `inventory_transaction`
```text
id uuid PK
tenant_id uuid
site_id uuid
material_lot_id uuid
container_id uuid
transaction_type varchar(50)
quantity numeric(24,8)
uom varchar(40)
from_location_id uuid
to_location_id uuid
reference_type varchar(60)
reference_id uuid
source_event_id uuid
occurred_at timestamptz
actor_type varchar(40)
actor_id varchar(255)
```

## `inventory_balance_projection`
- material lot/container/location
- on_hand
- reserved
- available
- projection version
- last transaction ID

## `inventory_reservation`
- batch/order
- material requirement
- lot/container
- quantity
- status
- expiry
- version

# 5. Transaction Types

`RECEIPT`, `TRANSFER`, `RESERVE`, `UNRESERVE`, `ISSUE`, `DISPENSE`, `CONSUME`, `RETURN`, `SAMPLE`, `REJECT`, `DESTROY`, `ADJUST_POSITIVE`, `ADJUST_NEGATIVE`, `INTERSITE_SHIP`, `INTERSITE_RECEIVE`.

Financial valuation is not stored as GxP transaction truth.

# 6. Selection Algorithm

Material selection returns ordered candidates after:
1. released/eligible status;
2. site/product/spec compatibility;
3. non-expired/non-retest-due;
4. no quality hold;
5. available quantity;
6. stock-rotation rule;
7. reservation priority.

Any deviation from default rotation requires controlled reason/approval according to profile.

# 7. APIs

- `GET /inventory/v1/availability`
- `POST /inventory/v1/reservations`
- `POST /inventory/v1/reservations/{id}/release`
- `POST /inventory/v1/transfers`
- `POST /inventory/v1/containers/{id}/split`
- `POST /inventory/v1/containers/merge`
- `POST /inventory/v1/cycle-counts`
- `GET /inventory/v1/lots/{id}/ledger`
- `GET /inventory/v1/reconciliation/erp`

# 8. Database Constraints

- no transaction UPDATE/DELETE;
- quantity > 0 for ordinary transaction rows;
- direction determined by type;
- balance/reservation cannot exceed available under transactional lock/version;
- duplicate source event unique;
- unique container code.

# 9. UI

1. Warehouse Overview
2. Material Availability
3. Lot/Container Search
4. Transfer
5. Reservation
6. Expiry/Retest
7. Quality Hold
8. Cycle Count
9. Container Split/Merge
10. Inventory Ledger
11. ERP Reconciliation

# 10. Concurrency

Reservation/dispensing uses transactional row/advisory locks around balance aggregate when needed to prevent two batches reserving same final quantity.

# 11. Events

- InventoryReceived
- InventoryTransferred
- InventoryReserved
- InventoryReservationReleased
- ContainerSplit
- ContainerMerged
- MaterialQualityHoldPlaced
- InventoryAdjusted
- InventoryERPDiscrepancyDetected

# 12. Repository Structure

```text
services/gxp-api/src/modules/inventory/
apps/ebmr_frappe/ebmr/warehouse/
contracts/events/inventory/
```

# 13. Tests

- released lot availability;
- quarantine excluded;
- expired/retest excluded;
- simultaneous reservations;
- container split conservation;
- incompatible merge;
- transfer to wrong status zone;
- negative inventory attempt;
- FIFO/FEFO deviation;
- cycle-count discrepancy;
- ERP mismatch;
- intersite transfer.

# 14. Acceptance

Inventory selection must be able to answer: “Which exact released lot/container can Batch X legally/operationally use now?” and return only eligible sources.

# 15. Codex / Claude Rules

Never derive GxP eligibility solely from warehouse bin.
Never update balance without immutable transaction.
Never auto-correct GxP quantity to match ERP.
Never allow negative inventory to hide race conditions.
