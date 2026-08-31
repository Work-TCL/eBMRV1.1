# US eBMR / eDHR Regulated Manufacturing Platform
## Document 56 — Inhalation DDCP Manufacturing Profile — MDI / DPI — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DDCP-003  
**Parent Documents:** Documents 01–53  
**Primary Dependencies:** Documents 09–17, 23–25, 38–47; Packaging; Genealogy  
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

Define a configurable inhalation combination-product manufacturing profile for metered-dose inhalers and dry-powder inhalers, covering drug formulation/blend, container/device components, filling/assembly, closure integrity, inhalation performance testing, packaging, genealogy and final release.

# 2. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| INH-FR-001 | Inhalation profile | Support MDI, DPI and configured inhalation-device presentations through subtype-specific profile. | Family abstraction. |
| INH-FR-002 | Drug formulation constituent | Model formulation/blend/suspension/solution constituent with released batch/spec/hold time. | Drug input. |
| INH-FR-003 | Device/container constituents | MDI valve/canister/actuator or DPI device/capsule/blister/reservoir components tracked as device/container constituents. | Device trace. |
| INH-FR-004 | Propellant/excipient components | For MDI, propellant/excipient/material lots and dispensing controls configurable. | Formulation trace. |
| INH-FR-005 | Powder blend | For DPI, blend/bulk powder properties/hold status and sampling/test links configurable. | DPI process. |
| INH-FR-006 | Component prep | Cleaning/handling/release of valves/canisters/actuators/blisters/capsules/device parts. | Readiness. |
| INH-FR-007 | Filling route | Configure pressure fill, cold fill, liquid fill, powder dose fill, blister/capsule fill or other released route. | Product-specific. |
| INH-FR-008 | Fill/dose controls | Target fill/dose, IPC sampling and weight/mass/reconciliation rules. | Dose quantity. |
| INH-FR-009 | Valve/crimp assembly | For MDI, capture valve placement, crimp dimensions/settings and leak/closure results. | Container closure. |
| INH-FR-010 | Device assembly | Actuator/device assembly with exact component lots and assembly program. | Device constituent. |
| INH-FR-011 | DPI dose unit loading | Track powder dose/blister/capsule lot and device association according to unit/lot architecture. | Genealogy. |
| INH-FR-012 | Leak/pressure test | Capture product-specific leak/pressure/closure integrity tests. | System integrity. |
| INH-FR-013 | Delivered dose | Support delivered-dose/uniformity test data and method/version where included in released spec. | Performance. |
| INH-FR-014 | Aerodynamic performance | Support cascade impaction/aerodynamic particle size distribution or other performance test result structures as product-specific QC methods. | Inhalation performance. |
| INH-FR-015 | Spray/plume pattern hooks | Support spray pattern/plume geometry or device-specific output tests when defined by control strategy. | Extensible. |
| INH-FR-016 | Priming/repriming | Device test profile can capture priming/repriming actuation requirements and results. | Use performance. |
| INH-FR-017 | Actuation count | MDI/DPI unit/device may track labeled actuations/doses and counter mechanism test where applicable. | Dose counter. |
| INH-FR-018 | Moisture/environment | DPI process can enforce humidity/environment readiness and excursion linkage. | Powder sensitivity. |
| INH-FR-019 | Blend/fill hold time | Track formulation/blend-to-filling and intermediate hold limits. | Validated timing. |
| INH-FR-020 | Cleaning/changeover | Product-contact line/device assembly area cleaning and line clearance required. | Cross-contamination. |
| INH-FR-021 | Sampling | Structured beginning/middle/end or configured location/time sampling plans. | Representativeness. |
| INH-FR-022 | Unit/lot inspection | Visual/device/pack integrity results and defects. | Finished quality. |
| INH-FR-023 | Packaging | Canister/device/capsule/blister + actuator/accessory/IFU/label/carton reconciliation. | Configuration. |
| INH-FR-024 | Genealogy | Drug formulation/blend + primary container/device lots → finished inhaler lot/unit. | Trace. |
| INH-FR-025 | OOS/OOT | Delivered dose/aerodynamic/device functional failures enter common OOS/OOT workflow and block release as configured. | Lab integrity. |
| INH-FR-026 | Constituent release | Drug/device constituent checkpoints remain separate from final inhaler release. | DDCP. |
| INH-FR-027 | Release blockers | Unresolved fill/closure/device/dose/aerodynamic/QMS/reconciliation issue blocks final release per profile. | No bypass. |
| INH-FR-028 | Stability linkage | Profile supports orientation/storage/stability sample references where product program requires. | Lifecycle. |
| INH-FR-029 | Change impact | Valve/canister/actuator/device material, formulation, propellant, fill/crimp/device program and test-method changes invoke Change/Risk/Validation. | Lifecycle. |
| INH-FR-030 | Draft guidance status | FDA 2018 MDI/DPI guidance is treated as nonbinding product-design input; customer released spec/control strategy governs executable requirements. | Correct regulatory handling. |

# 3. Claude Code Function Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createInhalationProfileVersion() | Product/Quality Engineer | product_version; subtype MDI/DPI; formulation; device constituents; route; tests | Product draft and referenced masters valid | Creates draft subtype-specific profile | InhalationProfileDraft | InhalationProfileDraftCreated |
| evaluateInhalationReadiness() | Batch start | batch_id; formulation/blend lot; device/component lots; environment/equipment | All released/eligible; hold/environment limits valid | Returns blockers and freezes constituent inputs | InhalationReadiness | InhalationReadinessEvaluated |
| startInhalerFillRun() | Production | batch/stage; fill route; equipment/program; target rules | Readiness PASS; route matches profile | Creates active filling context and Edge mappings | FillRunContext | InhalerFillStarted |
| recordCrimpOrClosureResult() | Edge/QC/Operator | unit/sample/lot; crimp dimensions or closure test; source | Expected test/source; equipment eligible | Stores structured result/evidence and evaluates rule | ClosureResult | InhalerClosureRecorded; CLOSURE_TEST_FAILED |
| recordInhalerDoseTest() | QC/LIMS | sample IDs; test code; method; raw results/evidence | Released spec/method; sample chain valid | Stores delivered dose/uniformity/aerodynamic result set | QCResultSet | InhalerDoseTestRecorded; INHALER_QC_OOS |
| recordDoseCounterTest() | Device Tester | unit/sample; program/version; expected count behavior | Device profile requires test; tester eligible | Stores device functional result | DeviceTestResult | DoseCounterTestRecorded |
| completeInhalerManufacturingRun() | Supervisor | run_id; counts; losses; samples; rejects; mandatory test refs | Counts/IPC/reconciliation complete | Closes run and generates process evidence manifest | RunCompletion | InhalerManufacturingCompleted |
| evaluateInhalerReleaseReadiness() | QA Release | batch_id | All required drug/device/QC/package evidence current | Deterministic blocker list | ReleaseReadiness | InhalerReleaseReadinessEvaluated |
| traceInhalerLot() | Genealogy/Complaint | finished lot/unit | Identity exists | Returns formulation/blend + primary device/container lots + QC/test/package evidence graph | GenealogyGraph | none |

# 4. Subtype Routes

## MDI Reference

```text
Released Drug / Excipients / Propellant
        ↓
Formulation / Bulk
        ↓
Canister + Valve Components
        ↓
Fill / Valve Placement / Crimp
        ↓
Leak / Closure
        ↓
Actuator Assembly
        ↓
Delivered Dose / Performance Tests
        ↓
Label / Package
        ↓
Final DDCP Release
```

## DPI Reference

```text
Released Drug / Carrier
        ↓
Blend / Powder Preparation
        ↓
Dose Unit Fill (reservoir/blister/capsule)
        ↓
Device Assembly
        ↓
Functional / Delivered Dose / Aerodynamic Tests
        ↓
Package
        ↓
Final DDCP Release
```

# 5. Profile Schema

```ts
type InhalationDDCPProfile = {
  subtype: "MDI"|"DPI";
  formulationOrBlendRequirement: ConstituentRequirement;
  deviceArchitectureVersionId: string;
  fillRoute: string;
  environmentProfileId?: string;
  requiredClosureTests: string[];
  requiredDeliveryTests: string[];
  requiredDeviceTests: string[];
  samplingPlans: string[];
  packagingProfileId: string;
  releaseProfileId: string;
};
```

# 6. Structured Aerodynamic Result

Use flexible QC result schema:
- stage/cut values;
- recovered mass;
- calculated metrics;
- method/instrument metadata;
- raw evidence references;
- calculation version;
- acceptance result.

Do not hardcode one compendial/device methodology globally.

# 7. Environmental Dependencies

DPI profiles may declare:
```text
max RH
temperature range
maximum environmental excursion duration
blend exposure limit
filling exposure limit
```

These rules are product/validation-controlled, not generic constants.

# 8. UI

1. Inhalation Profile
2. Formulation/Blend Handoff
3. Device Components
4. Readiness
5. Filling/Assembly
6. Closure/Leak
7. Dose/Performance Tests
8. Packaging
9. Genealogy
10. Review/Release

# 9. Stable Errors

`INHALATION_PROFILE_NOT_EFFECTIVE`, `FORMULATION_NOT_RELEASED`, `INHALER_COMPONENT_NOT_RELEASED`, `ENVIRONMENT_NOT_READY`, `FILL_ROUTE_MISMATCH`, `CLOSURE_TEST_FAILED`, `INHALER_QC_OOS`, `DOSE_COUNTER_TEST_FAILED`, `INHALER_RECONCILIATION_FAILED`.

# 10. Tests

- MDI wrong valve lot;
- crimp result out of limit;
- DPI humidity excursion;
- blend hold time expired;
- delivered-dose OOS;
- later passing retest preserves initial OOS;
- aerodynamic data import missing raw evidence;
- device component changed after batch issue;
- final packaging wrong actuator/device family.

# 11. Acceptance

One MDI and one DPI synthetic reference batch can execute using the same common core while applying different constituents, routes, environment dependencies, tests and release blockers.

# 12. Claude Code Prohibitions

- Do not create separate MDI/DPI applications.
- Do not hardcode 2018 draft-guidance recommendations as statutory requirements.
- Do not flatten multidimensional performance test data into one free-text result.
- Do not let device assembly completion equal product release.
