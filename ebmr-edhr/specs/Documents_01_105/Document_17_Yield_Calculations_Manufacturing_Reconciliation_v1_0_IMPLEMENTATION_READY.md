# US eBMR / eDHR Regulated Manufacturing Platform
## Document 17 — Yield, Calculations & Manufacturing Reconciliation Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EBMR-008  
**Parent Documents:** Document 01 v1.1; Document 02 v1.0  
**Primary Dependencies:** Documents 03–16; Rules Engine; Materials; Packaging; QC; Release  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products (DDCP)  
**Future Profiles:** Medical Devices, Pharmaceuticals  
**Date:** 2026-08-20

---


# Implementation Standard Applied to This Document

This specification is intended to be sufficient for Codex, Claude Code, or a human development team to implement the module with minimal interpretation.

Where applicable, the document therefore defines:

- objective and scope;
- non-goals/exclusions;
- actors/roles;
- functionality and sub-functionality;
- workflows and state machines;
- business rules;
- authorization and segregation of duties;
- electronic-signature behavior;
- audit behavior;
- entities, fields, relationships and ownership;
- PostgreSQL/Frappe storage boundaries;
- suggested tables, indexes and constraints;
- APIs and stable error codes;
- events/outbox contracts;
- UI screens/actions;
- integrations;
- calculations/validations;
- concurrency/idempotency;
- failure/recovery behavior;
- configuration;
- observability;
- retention/archival;
- migrations;
- performance/scaling;
- repository/module structure;
- implementation sequence;
- test cases;
- acceptance criteria;
- requirement traceability;
- explicit coding-agent rules.

If a future implementation decision changes regulated behavior and is not defined here, the coding agent shall raise a specification gap rather than inventing behavior.


# 1. Objective

Define manufacturing yield, potency/quantity calculations and material/packaging/label/component reconciliation used throughout eBMR/eDHR and DDCP final review/release.

Document 08 owns the generic rules/calculation engine. Document 17 defines the manufacturing semantics, source quantities, workflows and evidence around those calculations.

# 2. Functional Requirements

| ID | Functionality | Detailed behavior | Acceptance intent |
|---|---|---|---|
| YLD-FR-001 | Theoretical yield definition | Recipe/product defines theoretical yield or measure at appropriate manufacturing phases using released calculation/rule versions. | Expected output controlled. |
| YLD-FR-002 | Actual yield source | Actual yield derives from authoritative measured/recorded output quantities and source/equipment/manual evidence. | No untraceable number. |
| YLD-FR-003 | Yield percentage | Calculate percentage of theoretical yield using validated decimal formula and explicit rounding. | Reproducible result. |
| YLD-FR-004 | Independent verification | Where required, calculated yield is independently verified or verified per automated-equipment rule/profile. | Support applicable 211.103 workflow. |
| YLD-FR-005 | Phase yield | Support multiple phase/stage calculations, not only final yield. | Process loss visible. |
| YLD-FR-006 | Yield limits | Released recipe defines min/max percentage or other acceptance rule and investigation trigger. | Out-of-limit automatic. |
| YLD-FR-007 | Automated calculation | Automated calculation records input references, rule version, engine version and result; verifier sees inputs/result. | Transparent automation. |
| YLD-FR-008 | Manual calculation fallback | If calculation manually entered/externally calculated, require source, reason/policy and verification; default prefer engine calculation. | Fallback controlled. |
| YLD-FR-009 | Material mass balance | Reconcile received/issued/dispensed/consumed/returned/rejected/destroyed/loss quantities for defined scope. | Material accountability. |
| YLD-FR-010 | Dispensing reconciliation | For each material requirement reconcile dispensed vs consumed/returned/approved loss. | Per-material closure. |
| YLD-FR-011 | Packaging material balance | Reconcile packaging components issued/used/rejected/returned/destroyed/samples. | Packaging accountability. |
| YLD-FR-012 | Label reconciliation | Consume Document 16 label counts and applicable waiver/profile rule. | Unified release blocker. |
| YLD-FR-013 | Device component reconciliation | For serialized/critical components reconcile issued/assembled/rejected/scrapped/returned where configured. | Component accountability. |
| YLD-FR-014 | Unit count reconciliation | Reconcile produced/accepted/rejected/reworked/sampled/scrapped packaged unit counts. | Finished quantity consistent. |
| YLD-FR-015 | Potency correction | Calculate required active material amount from released potency/assay result and formula/version. | Drug dispensing support. |
| YLD-FR-016 | Overage/excess | Recipe may define justified component excess/overage as released parameter; system distinguishes planned excess from variance. | No hidden overage. |
| YLD-FR-017 | Unit conversion | All calculations use controlled UOM service and explicit dimensional conversion. | No mixed-unit error. |
| YLD-FR-018 | Precision/rounding | Each calculation has explicit decimal precision, rounding mode and stage. | No developer default. |
| YLD-FR-019 | Tolerance | Reconciliation defines absolute/percentage tolerance and inclusive/exclusive semantics. | Boundary deterministic. |
| YLD-FR-020 | Variance | Outside-tolerance result creates blocker and linked deviation/investigation according to profile. | No silent acceptance. |
| YLD-FR-021 | Approved loss | Document controlled reasons/categories for process loss, sample, spill, reject, destruction; approval may be required. | Variance explained. |
| YLD-FR-022 | Correction | Input/result correction preserves original and automatically re-evaluates affected downstream yields/reconciliations/review. | Consistency maintained. |
| YLD-FR-023 | Snapshot rule version | Batch uses exact calculation/reconciliation rules included in issue snapshot. | Historical reproducibility. |
| YLD-FR-024 | Rework/reprocess accounting | Original and rework material/output remain linked; no double-counting. | True balance. |
| YLD-FR-025 | Partial batch/sub-lot | Where supported, calculate and reconcile by defined scope and aggregate to parent. | Partial release support. |
| YLD-FR-026 | Serial/device scope | Unit count/component usage may aggregate serial-level data without losing exception visibility. | High-volume support. |
| YLD-FR-027 | External inventory reconciliation | ERP/WMS quantity may be compared after GxP calculation; discrepancy flagged but ERP never overwrites GxP evidence automatically. | Boundary clear. |
| YLD-FR-028 | Review display | QA sees source quantities, formulas, calculation versions, results, tolerances, variances and investigations. | Reviewable. |
| YLD-FR-029 | Release blocker | Required unresolved yield/reconciliation failures block release. | Quality gate. |
| YLD-FR-030 | Export | Final batch record includes yield and reconciliation results plus verification/signature and variance disposition. | 211.188-style evidence support. |
| YLD-FR-031 | Calculation trace | For every result retain input IDs/versions/values, calculation rule, engine version, time and verifier/signature if required. | Reproducible. |
| YLD-FR-032 | Performance | Large serial/component reconciliations may run asynchronously but final state is versioned and release waits for current result. | Scale safe. |

# 3. Core Calculation Objects

## Yield

Conceptually:

```text
yield_percent = actual_yield / theoretical_yield × 100
```

Implementation must call released calculation rule and Decimal/UOM services; do not embed formula in UI.

## Material Reconciliation

Conceptually:

```text
issued/dispensed =
consumed
+ returned
+ samples
+ rejected
+ destroyed
+ approved loss
+ unexplained variance
```

Exact categories and tolerances are profile/configuration controlled.

# 4. Data Model

## `manufacturing_calculation`

```text
id uuid PK
tenant_id uuid
batch_id uuid
scope_type varchar(40)
scope_id uuid
calculation_type varchar(60)
phase_code varchar(80)
rule_object_id uuid
input_refs jsonb
input_hash char(64)
result jsonb
outcome varchar(40)
version bigint
evaluated_at timestamptz
verified_signature_id uuid
supersedes_id uuid
```

## `reconciliation_record`
- batch/scope
- reconciliation type
- item/material/label/component ID
- source quantity categories
- UOM
- tolerance rule
- variance
- outcome
- linked quality event
- version/status

# 5. Calculation States

`PENDING_INPUT → READY → CALCULATED → VERIFICATION_REQUIRED → VERIFIED`

Alternate:
`FAILED`, `OUT_OF_LIMIT`, `SUPERSEDED`.

# 6. APIs

- `POST /manufacturing-calculations/v1/yield/evaluate`
- `POST /manufacturing-calculations/v1/potency/evaluate`
- `POST /reconciliation/v1/material/evaluate`
- `POST /reconciliation/v1/packaging/evaluate`
- `POST /reconciliation/v1/labels/evaluate`
- `POST /reconciliation/v1/components/evaluate`
- `POST /reconciliation/v1/{id}/verify`
- `GET /reconciliation/v1/batches/{batchId}/summary`

# 7. Source Quantity Rules

Sources must be authoritative references:
- Material Service transactions;
- Step results;
- Packaging/Label module;
- Device component usage;
- QC/sample withdrawals;
- approved destruction/returns.

User cannot manually type “consumed total” to bypass transaction evidence unless explicit fallback procedure exists.

# 8. Yield Verification UI

Display:
- phase;
- theoretical quantity;
- actual quantity;
- UOM;
- formula/version;
- calculated percentage;
- limits;
- outcome;
- input source drilldown;
- verifier/signature.

# 9. Variance Workflow

```text
Calculate
  ↓
Within tolerance → ACCEPTABLE
Outside tolerance
  ↓
Create/Link Deviation or Investigation
  ↓
Quality disposition
  ↓
Recalculate/Accept controlled resolution
  ↓
Release eligibility
```

A quality disposition does not erase original failed calculation.

# 10. Events

- YieldCalculated
- YieldOutOfLimit
- YieldVerified
- MaterialReconciliationCalculated
- ReconciliationFailed
- ReconciliationVerified
- ReconciliationSuperseded

# 11. Integration

ERP/WMS reconciliation:
- compare GxP transaction totals to external posted quantities;
- report discrepancy;
- allow controlled re-post/reconciliation;
- never let ERP overwrite GxP consumption.

# 12. Repository Structure

```text
services/gxp-api/src/modules/manufacturing-calculations/
services/gxp-api/src/modules/reconciliation/
apps/ebmr_frappe/ebmr/reconciliation/
contracts/events/reconciliation/
```

# 13. Test Catalogue

- normal yield;
- zero theoretical quantity;
- decimal precision;
- UOM conversion;
- min boundary;
- max boundary;
- below/above tolerance;
- independent verification;
- potency adjustment;
- material return;
- sample/destruction;
- rework;
- label discrepancy;
- component scrap;
- ERP discrepancy;
- correction recalculation;
- old rule snapshot;
- large serial aggregation.

# 14. Acceptance

Representative DDCP batch must prove:
- stage yield;
- final yield;
- active material/potency calculation where configured;
- raw material reconciliation;
- device component count reconciliation;
- label reconciliation;
- packaging reconciliation;
- all results visible to QA and Release Engine.

# 15. Codex / Claude Rules

Never use binary float for regulated calculation.
Never hard-code tolerance in UI.
Never silently round before the released rule says to.
Never overwrite failed calculation after correction/retest.
Never make ERP stock balance the authoritative GxP reconciliation result.

# Regulatory Engineering Basis

This specification is an engineering baseline, not legal advice and not a declaration that the software or a customer configuration is automatically compliant.

Relevant current U.S. regulatory sources include:

- 21 CFR Part 4 — combination-product CGMP framework;
- 21 CFR Part 11 — electronic records/electronic signatures when applicable;
- 21 CFR Parts 210/211 — drug CGMP;
- 21 CFR §211.186 — Master production and control records;
- 21 CFR §211.188 — Batch production and control records;
- 21 CFR §211.103 — Calculation of yield;
- 21 CFR Part 211 Subpart G — Packaging and labeling control;
- 21 CFR Part 820 — QMSR, effective February 2, 2026;
- 21 CFR §820.10 — requirements for a quality management system;
- 21 CFR §820.35 — control of records, including UDI-related records;
- 21 CFR §820.45 — device labeling and packaging controls;
- applicable UDI requirements under 21 CFR Part 830.

The current QMSR incorporates ISO 13485:2016 by reference. This document summarizes engineering implications and does not reproduce copyrighted ISO text.

Reference URLs:
- https://www.law.cornell.edu/cfr/text/21/4.4
- https://www.law.cornell.edu/cfr/text/21/211.186
- https://www.law.cornell.edu/cfr/text/21/211.188
- https://www.law.cornell.edu/cfr/text/21/211.103
- https://www.law.cornell.edu/cfr/text/21/part-211/subpart-G
- https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr
- https://www.law.cornell.edu/cfr/text/21/820.10
- https://www.law.cornell.edu/cfr/text/21/820.35
- https://www.law.cornell.edu/cfr/text/21/820.45
