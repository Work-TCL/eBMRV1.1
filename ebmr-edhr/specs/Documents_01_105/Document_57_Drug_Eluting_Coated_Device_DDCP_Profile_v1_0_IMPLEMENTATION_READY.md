# US eBMR / eDHR Regulated Manufacturing Platform
## Document 57 — Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DDCP-004  
**Parent Documents:** Documents 01–53  
**Primary Dependencies:** Documents 13, 23–25, 28–29, 38–42, 47; Genealogy; Release  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profile:** Drug–Device Combination Products (DDCP)  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This document is intended to be consumed directly by Claude Code, Codex, or a human engineering team.

Before implementation, the coding agent shall extract this profile into:

- profile module/submodule map;
- profile requirement registry;
- stage/state-machine catalogue;
- function/service catalogue;
- function input/output schemas;
- recipe/profile configuration schema;
- constituent/material/equipment requirements;
- DB ownership and transaction map;
- API/event contracts;
- genealogy handoff map;
- UI action map;
- release-blocker catalogue;
- negative/failure/concurrency tests;
- requirement traceability.

For every public/domain function specified below, implementation must preserve:

1. caller/trigger;
2. typed inputs and source;
3. authorization/qualification/signature prerequisites;
4. business validation;
5. database reads;
6. database writes;
7. transaction boundary;
8. output/result;
9. events;
10. downstream consumers;
11. stable errors;
12. idempotency/concurrency;
13. GxP audit evidence;
14. test obligations.

If a missing decision changes regulated behavior, create a `SPEC_GAP` rather than inventing a rule.

# DDCP Platform Rule

These documents define **product-family profile behavior**, not separate duplicated applications.

The common platform remains:

```text
Product / Constituent / Regulatory Profile
        ↓
Master Recipe / MMR
        ↓
Batch Execution
        ↓
Materials / QC / Equipment / Sterile / Edge
        ↓
Genealogy / eDHR
        ↓
Review-by-Exception
        ↓
Constituent Release(s)
        ↓
Final Combination Product Release
```

Profile documents configure and extend the common engines. They shall not fork core GxP services.

# Regulatory Engineering Basis

Current FDA sources support these implementation assumptions:

- FDA combination-product definitions/types explicitly include prefilled syringes, autoinjectors, insulin injector pens, metered-dose inhalers, dry-powder inhalers and drug-coated/drug-eluting devices as common combination-product examples/types.
- 21 CFR Part 4 and FDA's final Combination Product CGMP guidance define the combination-product CGMP framework and constituent-part concepts.
- FDA's final 2013 guidance on pen, jet and related injectors is relevant to injector device-performance/manufacturing design.
- FDA's June 2024 draft Essential Drug Delivery Outputs guidance is a useful design input for delivery-performance outputs, but is draft and must not be treated as a binding implementation requirement.
- FDA's April 2018 MDI/DPI quality guidance remains draft; this document treats it as product-development design input rather than binding law.
- FDA's August 2026 Container Closure Systems guidance is draft and specifically notes CCSs that are device constituent parts of combination products; it is tracked as a future-facing design input, not a binding baseline.
- Current QMSR became effective February 2, 2026; device-constituent QMS controls must be mapped through the common profile/requirements engine.

Official references:
- https://www.fda.gov/combination-products/about-combination-products/combination-product-definition-combination-product-types
- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/current-good-manufacturing-practice-requirements-combination-products
- https://www.fda.gov/combination-products/guidance-regulatory-information/combination-products-guidance-documents
- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/essential-drug-delivery-outputs-devices-intended-deliver-drugs-and-biological-products
- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/metered-dose-inhaler-mdi-and-dry-powder-inhaler-dpi-drug-products-quality-considerations
- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/container-closure-systems-human-drugs-and-biological-products
- https://www.fda.gov/combination-products/device-product-codes-procodes-device-constituent-parts-andandabla-combination-products

# 1. Objective

Define the product-family profile for devices coated, impregnated or otherwise combined with a drug (and extensibly biologic), with explicit substrate/drug constituent handoffs, coating process evidence, dual material/unit reconciliation, sterilization interaction, product testing, genealogy and final DDCP release.

# 2. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| COAT-FR-001 | Coated device profile | Support drug-eluting/coated/impregnated devices with device substrate + drug/biologic coating constituent + finished combined product. | Type 4/5 architecture. |
| COAT-FR-002 | Substrate identity | Track base device lot/serial/subassembly and released device specification/version. | Device constituent. |
| COAT-FR-003 | Drug/coating constituent | Track coating solution/formulation/bulk lot, concentration/potency, prepared amount and hold time. | Drug constituent. |
| COAT-FR-004 | Surface preparation | Capture cleaning/activation/priming/pre-treatment steps and evidence. | Coating readiness. |
| COAT-FR-005 | Coating recipe | Versioned coating process route: dip/spray/inkjet/deposition/impregnation/other approved method. | Extensible. |
| COAT-FR-006 | Coating parameters | Speed/time/flow/pressure/distance/temperature/humidity/cycle/pass and other mapped process parameters. | Process evidence. |
| COAT-FR-007 | Equipment/program | Coater/equipment and recipe/program version eligible and bound to batch. | Validated state. |
| COAT-FR-008 | Environment | Required room/temperature/humidity/particle/environment status gate. | Process control. |
| COAT-FR-009 | Drug usage ledger | Track drug/coating solution issued, applied, residual, sampled, rejected, recovered/disposed and reconcile. | Drug mass balance. |
| COAT-FR-010 | Unit/lot association | Map device lot/serial/substrate unit to coating run and drug/coating constituent lot. | Combination genealogy. |
| COAT-FR-011 | Coating weight/loading | Record direct/indirect drug loading/coating weight measurement according to approved method. | Dose/loading evidence. |
| COAT-FR-012 | Uniformity | Support coating thickness/loading/uniformity spatial or sampled result structures. | Quality. |
| COAT-FR-013 | Coating integrity | Inspection for delamination/cracks/defects/adhesion or product-specific attributes. | Device/drug interaction. |
| COAT-FR-014 | Drug content/assay | Link QC assay/content/impurity/degradation results for finished coated device where required. | Drug quality. |
| COAT-FR-015 | Release/elution profile | Support in-vitro release/elution test result sets when product specification requires. | Therapeutic performance. |
| COAT-FR-016 | Dimensional/device function | Ensure coating process does not invalidate required device dimensional/mechanical/functional tests. | Combined performance. |
| COAT-FR-017 | Drying/curing | Capture curing/drying conditions and hold times after coating. | Process. |
| COAT-FR-018 | Sterilization interaction | Profile specifies pre/post coating sterilization route and recognizes potential impact of sterilization on drug/coating/device. | Critical DDCP interaction. |
| COAT-FR-019 | Sterilization evidence | Link sterilization cycle/contract process to exact coated device lot/serial. | Genealogy. |
| COAT-FR-020 | Post-sterilization testing | Profile can require drug assay/degradation/release/device tests after sterilization. | Interaction verification. |
| COAT-FR-021 | Packaging | Barrier/package materials, protection, labeling and packaged lot genealogy. | Finished product. |
| COAT-FR-022 | Unit serialization | Support serial/unit-level coated device trace when device profile requires. | Device postmarket. |
| COAT-FR-023 | Process sampling | Sampling plan can select devices/locations/timepoints across coating run. | Representativeness. |
| COAT-FR-024 | OOS/NCR | Coating/drug/device failures create OOS/NCR/deviation and affected unit/lot scope. | QMS. |
| COAT-FR-025 | Rework | Recoating/stripping/reprocessing default prohibited unless released validated route explicitly permits and drug/device impact assessed. | Safe default. |
| COAT-FR-026 | Yield/reconciliation | Reconcile device units and drug/coating material separately and combined. | Full balance. |
| COAT-FR-027 | Constituent checkpoints | Device substrate and drug constituent may have separate release inputs; finished coated device has independent final release. | Part 4. |
| COAT-FR-028 | Final blockers | Coating parameter excursion, drug reconciliation gap, sterilization issue, assay/release/device failure, genealogy gap or QMS issue blocks release. | No bypass. |
| COAT-FR-029 | Change impact | Substrate material, coating formulation, drug source, coating equipment/program, environment, sterilization, packaging and test-method changes require Change/Risk/Validation assessment. | Lifecycle. |
| COAT-FR-030 | Complaint/field trace | Complaint serial/lot can trace backward to coating run/drug lot and forward to affected distributed units. | Postmarket. |

# 3. Claude Code Function Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createCoatedDeviceProfileVersion() | Product/Quality Engineer | product_version; substrate requirement; drug/coating requirement; coating route; tests; sterilization route | Product draft; referenced masters valid | Creates draft coated-device DDCP profile | CoatedDeviceProfileDraft | CoatedDeviceProfileDraftCreated |
| evaluateCoatingRunReadiness() | Batch/run start | device substrate lots/units; coating solution lot; equipment; environment; program | Inputs released; hold times valid; equipment/environment eligible | Returns blockers and freezes run sources | CoatingReadiness | CoatingRunReadinessEvaluated |
| startCoatingRun() | Operator/Supervisor | batch_id; coater_id; program_version; constituent quantities; context | Readiness PASS | Creates coating operation context, drug-usage ledger and device scope | CoatingRunContext | CoatingRunStarted |
| recordCoatingProcessEvidence() | Edge/Operator | run_id; parameter_code; value/uom; time; source mapping | Expected mapping/profile; context active | Stores process evidence/historian reference and evaluates limits | CoatingProcessResult | CoatingEvidenceRecorded; COATING_PARAMETER_EXCURSION |
| recordDrugLoadingResult() | QC/Inline measurement | unit/sample/lot; method; raw inputs; calculation rule | Expected sample/test; rule effective | Calculates/stores drug loading/coating result | DrugLoadingResult | DrugLoadingRecorded; DRUG_LOADING_OOS |
| bindDeviceToCoatingConstituent() | Genealogy service | device lot/serial scope; coating solution/drug lot; run_id | Identities valid and within run scope | Creates constituent genealogy edges | GenealogyBinding | CoatedDeviceGenealogyBound |
| completeCoatingRun() | Supervisor | run_id; counts; coating solution usage; losses; sample/reject refs | All process stages/results and dual reconciliation complete | Closes run, freezes evidence manifest | CoatingRunCompletion | CoatingRunCompleted; COATING_RECONCILIATION_FAILED |
| recordPostSterilizationTest() | QC/Device Test | finished coated lot/unit; sterilization ref; test profile/results | Required sterilization complete; sample valid | Stores post-sterilization drug/device result | PostSterilizationResult | PostSterilizationTestRecorded |
| evaluateCoatedDeviceReleaseReadiness() | QA Release | finished lot/serial scope | Required drug/device/sterilization/QC/QMS evidence complete | Returns deterministic blockers/ready status | ReleaseReadiness | CoatedDeviceReleaseReadinessEvaluated |
| traceCoatedDeviceComplaint() | Complaint/Recall | finished serial/lot | Identity valid | Returns substrate, coating run/drug lot, sterilization, package and distribution graph | ComplaintTraceGraph | none |

# 4. Reference Manufacturing Route

```text
Released Device Substrate
        +
Released Drug / Coating Constituent
        ↓
Surface Preparation
        ↓
Coating / Impregnation Process
        ↓
Dry / Cure
        ↓
Coating / Drug Loading / Integrity Tests
        ↓
Sterilization (route-dependent)
        ↓
Post-Sterilization Drug + Device Tests
        ↓
Package
        ↓
Dual Reconciliation
        ↓
Final DDCP Release
```

# 5. Profile Schema

```ts
type CoatedDeviceDDCPProfile = {
  substrateRequirement: ConstituentRequirement;
  coatingDrugRequirement: ConstituentRequirement;
  surfacePreparationRouteId: string;
  coatingRouteId: string;
  coatingEquipmentClass: string;
  environmentProfileId?: string;
  criticalProcessParameters: string[];
  drugLoadingTestProfileId: string;
  coatingIntegrityTestProfileId?: string;
  deviceFunctionalTestProfileId: string;
  sterilizationRouteId?: string;
  postSterilizationTests: string[];
  packagingProfileId: string;
  releaseProfileId: string;
};
```

# 6. Dual Reconciliation

Device-unit reconciliation:
```text
substrates issued
= coated accepted
+ rejected
+ sampled/destructive-test
+ destroyed
+ approved loss/other disposition
```

Drug/coating reconciliation:
```text
drug/coating issued
= applied/estimated on product
+ residual/returned
+ samples
+ destroyed/waste
+ approved process loss
+ variance
```

Exact formulas are profile/rule-version controlled.

# 7. Sterilization Interaction

The profile must state:
- whether coating occurs before/after sterilization;
- sterilization modality/profile;
- which drug/coating/device characteristics require post-sterilization verification;
- applicable hold/storage constraints.

No generic sterilization assumption is allowed.

# 8. Evidence Tiering

High-frequency coater signals remain historian/Edge evidence; GxP stores:
- run ID;
- mapping/profile version;
- critical parameter results;
- alarm/excursion events;
- raw evidence manifest/hash/window.

# 9. UI

1. Coated Device Profile
2. Constituent Handoff
3. Coating Readiness
4. Coating Run
5. Process Parameter Timeline
6. Drug Loading / QC
7. Coating Inspection
8. Sterilization Link
9. Post-Sterilization Test
10. Dual Reconciliation
11. Genealogy
12. QA Release

# 10. Stable Errors

`COATED_DEVICE_PROFILE_NOT_EFFECTIVE`, `SUBSTRATE_NOT_RELEASED`, `COATING_DRUG_NOT_RELEASED`, `COATING_HOLD_TIME_EXPIRED`, `COATING_ENVIRONMENT_NOT_READY`, `COATING_PROGRAM_MISMATCH`, `COATING_PARAMETER_EXCURSION`, `DRUG_LOADING_OOS`, `STERILIZATION_INTERACTION_REVIEW_REQUIRED`, `COATING_RECONCILIATION_FAILED`.

# 11. Tests

- wrong drug lot;
- substrate on hold;
- coating solution hold expired;
- humidity excursion;
- program version mismatch;
- drug loading OOS;
- coating integrity defect partial unit scope;
- failed sterilization;
- post-sterilization assay failure;
- unapproved recoating attempt;
- dual reconciliation mismatch;
- complaint trace to drug lot.

# 12. Acceptance

A finished coated-device lot/serial can be traced to the exact base device, coating drug lot, process run/evidence, sterilization and final drug/device tests, with independent combined-product QA release.

# 13. Claude Code Prohibitions

- Do not treat coated device as ordinary device BOM with a text field for drug.
- Do not merge drug-material and device-unit reconciliation into one ambiguous quantity.
- Do not allow failed coating run to be recoated/reprocessed without released route.
- Do not assume sterilization has no effect on drug/coating constituent.
