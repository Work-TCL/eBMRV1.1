# US eBMR / eDHR Regulated Manufacturing Platform
## Document 55 — Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DDCP-002  
**Parent Documents:** Documents 01–53  
**Primary Dependencies:** Documents 13, 16, 23, 28, 38, 46, 54; Device Testing; Genealogy  
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

Define injector-device assembly and performance evidence for autoinjectors, injector pens and cartridge/PFS-based delivery systems, including unit-level drug-container pairing, device assembly, delivery-performance testing, genealogy and final DDCP release.

# 2. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| INJ-FR-001 | Injector family profile | Support autoinjector, pen injector, reusable pen + cartridge, single-use injector and configured related injector architectures. | Reusable family model. |
| INJ-FR-002 | Drug container relation | Model PFS/cartridge/vial/reservoir as drug-container subassembly and separate injector device constituents. | Exact architecture. |
| INJ-FR-003 | Device BOM | Track housing, spring/drive, needle system, activation components, dose mechanism, cap, shield, electronics if applicable and packaging. | Device genealogy. |
| INJ-FR-004 | Subassembly handoff | Released drug-container subassembly enters injector assembly with exact lot/unit range and status. | Constituent handoff. |
| INJ-FR-005 | Device component release | Only released device component lots/subassemblies can be assembled. | QMS gate. |
| INJ-FR-006 | Assembly line readiness | Equipment program, tooling, calibration, cleaning/clearance, operator qualification and material verification before run. | Manufacturing gate. |
| INJ-FR-007 | Assembly recipe | Versioned assembly sequence includes component scans, orientation/presence checks, torque/force/position parameters and verification. | Deterministic assembly. |
| INJ-FR-008 | Unit serialization | Support unit-level internal serial/UDI/device identifier relationship when profile requires. | Device traceability. |
| INJ-FR-009 | Drug-container insertion | Track exact PFS/cartridge lot/unit into injector unit/lot; prevent duplicate/cross-use. | Genealogy. |
| INJ-FR-010 | Needle activation system | Capture assembly/test of needle insertion/retraction/shield function where applicable. | Safety/performance. |
| INJ-FR-011 | Dose setting mechanism | For pens, capture dose mechanism version/calibration/test route and configured dosing range. | Pen performance. |
| INJ-FR-012 | Delivery performance outputs | Profile defines essential delivery outputs such as delivered volume/dose, delivery time, activation force, needle depth or other product-specific outputs. | Performance control. |
| INJ-FR-013 | Function test plan | Sampling or 100% test plan, fixture/program version and acceptance criteria. | Device test evidence. |
| INJ-FR-014 | Force/torque tests | Support activation/cap removal/needle shield/drive/torque forces and dimensional/functional results. | Mechanical outputs. |
| INJ-FR-015 | Dose accuracy | Link dose-delivery/gravimetric/volumetric tests and calculations. | Drug delivery. |
| INJ-FR-016 | Incomplete dose detection | Test/result taxonomy includes under-delivery, partial delivery, premature stop and other profile defects. | Failure modes. |
| INJ-FR-017 | Audible/visual indicators | Test completion/window/click/indicator functions where included. | User feedback. |
| INJ-FR-018 | Reusable device pairing | For reusable injector + cartridge, model compatibility/approved pairing and cartridge lot genealogy without assuming permanent single unit relationship. | Cross-labeled architecture. |
| INJ-FR-019 | Software/electronics | If connected/electronic injector exists, firmware/config/software evidence hooks are available but require separately approved profile. | Future-ready. |
| INJ-FR-020 | Human factors linkage | Profile can reference design/risk/human-factors critical tasks but manufacturing eBMR does not itself determine usability acceptability. | Lifecycle link. |
| INJ-FR-021 | Device rejects | Unit reject reason, disassembly/scrap/rework authorization and constituent impact preserved. | Nonconformance. |
| INJ-FR-022 | Rework | Device rework only through released route; drug-container constituent cannot be casually reused unless procedure explicitly permits and quality status reevaluated. | Controlled. |
| INJ-FR-023 | Packaging | Device + drug constituent + accessories/IFU/labels/cap/tray/carton reconciliation. | Finished configuration. |
| INJ-FR-024 | Final device/combination test | Support finished-unit or lot-level tests after assembly/packaging. | Final evidence. |
| INJ-FR-025 | Genealogy | Component lots + drug-container lot/unit → injector serial/lot → packaged saleable unit. | End-to-end. |
| INJ-FR-026 | Constituent release | Separate container/drug/device checkpoints feed final combined release. | DDCP. |
| INJ-FR-027 | Release blockers | Failed dose/function test, unresolved device NCR, wrong component pairing, genealogy gap or incomplete container/drug evidence block final release. | No bypass. |
| INJ-FR-028 | Change impact | Drive system, spring, needle, cartridge/PFS, lubricant, assembly program, test fixture/program and labeling changes trigger controlled assessment. | Lifecycle. |
| INJ-FR-029 | Product family inheritance | Common injector profile can inherit product-family functions while exact test outputs/limits are product-version controlled. | Configurability. |
| INJ-FR-030 | Evidence export | Unit/lot-level combined package supports investigation of one complaint serial back to exact drug and device constituents. | Postmarket readiness. |

# 3. Claude Code Function Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createInjectorProfileVersion() | Product/Device Engineer | product_version; injector_type; constituent architecture; assembly/test schemas | Product draft; referenced specs exist | Creates draft injector profile extending DDCP base | InjectorProfileDraft | InjectorProfileDraftCreated |
| evaluateInjectorAssemblyReadiness() | Batch/Work order start | batch_id; line_id; drug_container_lot/unit scope; device component lots | All constituent lots released; line/tools/programs eligible | Returns blockers/eligible sources and freezes handoff scope | AssemblyReadiness | InjectorAssemblyReadinessEvaluated |
| bindDrugContainerToInjectorUnit() | Assembly station/Edge | batch_id; drug_container_id; injector_unit_id; scanner evidence | Both identities valid, unused, expected family/status | Creates genealogy edge and assembly component record transactionally | BindingReceipt | DrugContainerBound; CONTAINER_ALREADY_USED/WRONG_PAIRING |
| recordAssemblyParameter() | PLC/Tester/Operator | unit/lot; parameter_code; value/uom; source/mapping version | Active assembly operation; expected parameter/source | Stores process evidence/result candidate via common engine | AssemblyParameterResult | InjectorAssemblyParameterRecorded |
| executeInjectorFunctionalTest() | Tester adapter/QC | unit/sample; test_profile; program_version; raw evidence | Tester/program/profile eligible | Runs/ingests structured device output results and evaluates acceptance | InjectorFunctionalTestResult | InjectorFunctionalTestCompleted; INJECTOR_TEST_FAILED |
| evaluateDoseDeliveryResult() | QC/Rules | raw measurements; calculation rule; acceptance profile | Method/rule released; measurements complete | Calculates delivered dose/volume/time/etc with decimal math; stores result/evidence | DoseDeliveryResult | DoseDeliveryEvaluated; DOSE_DELIVERY_FAILED |
| recordUnitDisposition() | QA/Production | unit_id; PASS/REJECT/REWORK; reason; NCR/rework ref | Functional/inspection results current | Creates unit disposition; updates availability projection; never deletes unit history | UnitDisposition | InjectorUnitDispositioned |
| completeInjectorAssemblyBatch() | Supervisor | batch_id; unit counts; rejects; tests; reconciliation | All units/categories resolved; genealogy and counts complete | Closes assembly stage and creates evidence manifest | AssemblyCompletion | InjectorAssemblyCompleted; UNIT_RECONCILIATION_FAILED |
| evaluateInjectorReleaseReadiness() | QA Release | batch_id/product lot | Constituent and test records current | Combines drug-container, injector-device and final packaging blockers | ReleaseReadiness | InjectorReleaseReadinessEvaluated |
| traceComplaintSerial() | Complaint/Genealogy | finished_serial | Serial exists | Returns finished unit → injector components → drug container → drug bulk and test evidence graph | ComplaintTraceGraph | none |

# 4. Product Architecture Examples

Supported profile structures:

```text
A. PFS → Autoinjector
Drug Bulk → PFS → Device Assembly → Autoinjector

B. Cartridge → Disposable Pen
Drug Bulk → Cartridge → Pen Assembly → Finished Pen

C. Cartridge + Reusable Pen
Cartridge Batch ↔ Approved Reusable Pen Family
(final pairing may occur at use/distribution rather than manufacturing)
```

The profile explicitly records which structure applies.

# 5. Injector Profile Schema

```ts
type InjectorDDCPProfile = {
  injectorType: "AUTOINJECTOR"|"PEN_SINGLE_USE"|"PEN_REUSABLE"|"CARTRIDGE_SYSTEM";
  drugContainerRequirement: ConstituentRequirement;
  deviceBOMVersionId: string;
  unitSerialization: boolean;
  assemblyRouteVersionId: string;
  requiredDeliveryOutputs: DeliveryOutputDefinition[];
  functionalTestPlanId: string;
  finalInspectionPlanId: string;
  packagingProfileId: string;
  releaseProfileId: string;
};
```

# 6. Delivery Output Definition

```ts
type DeliveryOutputDefinition = {
  code: string;
  methodVersionId: string;
  resultType: "NUMERIC"|"PASS_FAIL"|"CURVE"|"SEQUENCE";
  canonicalUom?: string;
  calculationRuleId?: string;
  acceptanceRuleId: string;
  samplingPlanId: string;
};
```

The 2024 FDA EDDO draft may inform customer/product definitions, but the released product control strategy remains the system authority.

# 7. Unit Genealogy

For unit-serialized products:

```text
drug_bulk_lot
   ↓
pfs_or_cartridge_lot/unit
   ↓
injector_unit_serial
   ├ device component lots
   ├ assembly equipment/program
   ├ functional test result
   └ package/label unit
```

# 8. UI

1. Injector Profile
2. Assembly BOM/Route
3. Assembly Readiness
4. Unit Scan/Binding
5. Assembly Execution
6. Functional Test
7. Reject/Rework
8. Unit Genealogy
9. Packaging
10. Review/Release
11. Complaint Serial Trace

# 9. Stable Errors

`INJECTOR_PROFILE_NOT_EFFECTIVE`, `DRUG_CONTAINER_NOT_RELEASED`, `DEVICE_COMPONENT_NOT_RELEASED`, `CONTAINER_ALREADY_USED`, `WRONG_CONTAINER_DEVICE_PAIRING`, `ASSEMBLY_PROGRAM_MISMATCH`, `INJECTOR_TEST_FAILED`, `DOSE_DELIVERY_FAILED`, `UNIT_GENEALOGY_INCOMPLETE`, `INJECTOR_RECONCILIATION_FAILED`.

# 10. Tests

- PFS already bound to another serial;
- cartridge wrong family;
- device component lot on hold;
- tester calibration expired;
- tester program version wrong;
- activation force fail then passing retest preserves both;
- under-delivery;
- rejected unit disassembly/reuse attempt;
- reusable pen cross-label compatibility;
- complaint trace from serial to drug lot.

# 11. Acceptance

One finished autoinjector serial can be reconstructed from exact drug container through all device component lots, assembly evidence, delivery-performance results, disposition and packaging.

# 12. Claude Code Prohibitions

- Do not store unit pairing only as free-text assembly note.
- Do not let device test PASS replace a prior failed test.
- Do not reuse drug container from rejected unit unless released rework procedure explicitly authorizes it.
- Do not assume all injector products require the same EDDOs/test outputs.
