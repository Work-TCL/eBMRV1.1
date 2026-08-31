# US eBMR / eDHR Regulated Manufacturing Platform
## Document 54 — Prefilled Syringe & Injectable DDCP Manufacturing Profile — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DDCP-001  
**Parent Documents:** Documents 01–53  
**Primary Dependencies:** Documents 09–17, 18–25, 38–42; Packaging; Genealogy; QA Release  
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

Define the executable product-family profile for prefilled syringe and closely related sterile injectable drug-delivery combination products, from released bulk constituent and primary components through aseptic filling, closure, inspection, device-functional evidence, packaging and final DDCP release.

# 2. Scope

Included V1 reference route: sterile liquid drug constituent filled into prefilled syringe with device constituent functions. Optional safety device and biologic flags are configurable. This is a profile layered on common Batch/QC/Equipment/QMS engines.

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| PFS-FR-001 | Profile master | Define injectable DDCP subtype, dosage form, presentation, fill volume, strength, device constituent and container-closure architecture. | Concrete product identity. |
| PFS-FR-002 | Constituent definition | Model drug/biologic constituent, syringe/barrel, stopper/plunger, needle/needle shield, tip cap, safety device and packaging as versioned constituents. | Full genealogy. |
| PFS-FR-003 | Bulk drug handoff | Receive released bulk drug/biologic batch reference with assay/potency, concentration, sterility/bioburden status and expiry/hold constraints. | Constituent handoff. |
| PFS-FR-004 | Primary components | Require released lots for barrel/syringe, stopper/plunger, needle/closure and other product-contact components. | No unapproved component. |
| PFS-FR-005 | Component preparation | Track washing/depyrogenation/sterilization/ready-to-use status according to configured component route. | Sterile readiness. |
| PFS-FR-006 | Line readiness | Filling line, cleanroom, cleaning, SIP/sterilization, environmental state, personnel and filter status all verified before batch stage start. | Aseptic gate. |
| PFS-FR-007 | Bulk hold time | Track bulk compounding-to-filtration/filling hold time and block when released limits exceeded. | Validated timing. |
| PFS-FR-008 | Sterile filtration | If process uses sterile filtration, bind filter lot/serial, pre/post integrity status, filtration parameters and evidence. | Filtration assurance. |
| PFS-FR-009 | Filling setup | Record filler, product-contact path, fill program/version, needle/nozzle setup, target fill and line configuration. | Setup evidence. |
| PFS-FR-010 | Fill execution | Capture batch/cycle group, fill start/end, machine counts, actual/IPC weights or volumes, alarms/interventions and rejects. | Complete filling record. |
| PFS-FR-011 | Fill-weight IPC | Perform configurable in-process fill weight/volume sampling with method, sample frequency and acceptance rule. | Dose quantity control. |
| PFS-FR-012 | Stoppering/plunging | Capture plunger/stopper insertion/position and relevant process settings/results. | Closure assembly. |
| PFS-FR-013 | Needle/closure assembly | Track needle installation/shield/tip cap/closure configuration where applicable. | Device constituent. |
| PFS-FR-014 | Container closure integrity | Link required CCI/leak/seal tests by lot/sample plan/method and release state. | System integrity. |
| PFS-FR-015 | Visual inspection | 100% or configured inspection records machine/manual inspection version, defect codes, rejects and sampling verification. | Finished presentation quality. |
| PFS-FR-016 | Silicone/tungsten/particulate profile | Support product-specific material/process attributes or QC references when defined in the product's released control strategy. | Product-specific extensibility. |
| PFS-FR-017 | Functional syringe tests | Support break-loose/glide force, needle shield/removal force, dose delivery, leakage or other device output tests when included in released specification. | Device performance. |
| PFS-FR-018 | Safety feature assembly | If needle-safety/guard device exists, track subassembly lot, assembly process and functional test. | Safety constituent. |
| PFS-FR-019 | Serialization/UDI hooks | Support device/combination-product identifier/UDI configuration where applicable; actual applicability is regulatory-profile controlled. | Future compliance. |
| PFS-FR-020 | Label/packaging | Link label/artwork version, carton/IFU, lot/expiry and packaging reconciliation. | Finished unit trace. |
| PFS-FR-021 | Unit/lot genealogy | Drug bulk → component lots → filled syringe lot/unit/sample → packaged lot/device ID relationships preserved. | End-to-end trace. |
| PFS-FR-022 | Yield reconciliation | Reconcile bulk issued, units filled, rejects, samples, line loss and finished packed quantity. | Mass/unit balance. |
| PFS-FR-023 | Constituent release | Drug and device-constituent evidence may have separate release checkpoints; final DDCP release remains independent. | Part 4 profile. |
| PFS-FR-024 | Final release blockers | Open deviations/OOS, failed filter integrity, EM excursion, CCI/functional failure, unresolved reconciliation or missing constituent evidence block release per profile. | No incomplete release. |
| PFS-FR-025 | Batch review package | Review shows critical aseptic timeline, filtration, fill IPC, interventions, defects, device tests, genealogy and deviations. | Review-by-exception. |
| PFS-FR-026 | Stability/retain refs | Create/reference stability/retain sample plans and finished lot samples where configured. | Lifecycle support. |
| PFS-FR-027 | Rework restriction | Filled primary container rework/reprocessing routes are profile-specific and default disallowed unless released procedure explicitly permits. | Safe default. |
| PFS-FR-028 | Biologic subtype | Biologic constituent can reuse profile, but biologic-specific requirements remain separately enabled/baselined; no implicit equivalency. | Future profile. |
| PFS-FR-029 | Change sensitivity | Changes to syringe/barrel/stopper/needle/silicone/closure/fill program/filter/control strategy link Change Control and risk/validation impact. | Lifecycle. |
| PFS-FR-030 | Inspection export | Produce one reproducible PFS/DDCP batch package including drug + device constituent + combined-product evidence. | Inspection-ready. |

# 4. Claude Code Function Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createInjectableProfileVersion() | Product/Quality Engineer | product_version_id; subtype; constituent_schema; process_route; control_strategy | Product draft; author authorized; referenced masters exist | Creates draft profile version and constituent/process-stage config | InjectableProfileDraft | InjectableProfileDraftCreated; PROFILE_SCHEMA_INVALID |
| releaseInjectableProfileVersion() | QA/Regulatory/Validation | profile_id; expected_version; signatures; change_ref | Requirements/risks/validation complete | Vault-releases immutable profile/effective date | ReleasedInjectableProfile | InjectableProfileReleased; PROFILE_RELEASE_BLOCKED |
| evaluateInjectableBatchReadiness() | Batch issue/start | batch_id; profile_version_id; line/equipment context | Issued recipe/profile; materials and equipment available | Reads bulk release, component release, sterile/clean status, training, EM, filter prerequisites | BatchReadinessResult | PFSBatchReadinessEvaluated; BULK_NOT_RELEASED/LINE_NOT_READY |
| startFillingStage() | Operator/Supervisor | batch_id; stage_id; line_id; fill_program_version; bulk_container_ids; e-sign if required | Readiness PASS; active context unique | Creates aseptic/filling operation context; binds source lots/equipment/program | FillingStageContext | PFSFillingStarted; FILL_PROGRAM_MISMATCH |
| recordFillIPCResult() | QC/IPC/Edge | batch_id; sample_id; actual_value; uom; method/source | Sampling point due; method/spec effective; source allowed | Stores IPC result/evidence via QC/Batch service; evaluates criterion | IPCResult | FillIPCRecorded; FILL_IPC_OOS |
| recordSyringeUnitOrCount() | Machine/Edge/Operator | batch_id; count_delta or unit IDs; category filled/reject/sample; source_event | Active filling context; source mapping valid | Updates immutable production count ledger/projection; genealogy if unit-level | UnitCountReceipt | SyringeCountRecorded; DUPLICATE_SOURCE_EVENT |
| recordAsepticInterventionForFill() | Aseptic module | operation_id; intervention_type; actor; start/end; impacted scope | Intervention profile effective | Links intervention to fill timeline and impacted unit/time range | InterventionImpactRef | PFSInterventionRecorded |
| completeFillingStage() | Supervisor | stage_id; counts; filter refs; IPC completion refs | All mandatory IPC/current filter/EM evidence available; counts reconciled | Closes fill operation and produces fill-stage evidence manifest | FillStageCompletion | PFSFillingCompleted; FILL_STAGE_INCOMPLETE |
| recordPFSFunctionalTest() | QC/Device Test adapter | sample/unit; test_code; method/program version; values/raw ref | Expected test; tester eligible | Creates QC/device test result linked to device constituent/finished product | PFSFunctionalTestResult | PFSFunctionalTestRecorded; DEVICE_TEST_FAILED |
| evaluatePFSReleaseReadiness() | QA Release Engine | batch_id; release_profile_version | All required stage evidence materialized | Evaluates drug/device/combined release blockers and returns deterministic list | ReleaseReadiness | PFSReleaseReadinessEvaluated; RELEASE_BLOCKERS_PRESENT |
| createPFSBatchEvidencePackage() | QA/Inspector export | batch_id; package_version | Batch state permits export | Builds evidence manifest/PDF refs with constituent, batch, QC, sterile, genealogy, audit/signatures | EvidencePackageRef | PFSBatchPackageGenerated |

# 5. Manufacturing Stage Template

```text
Released Bulk Drug/Biologic
        ↓
Primary Component Release / Preparation
        ↓
Line + Aseptic Readiness
        ↓
Sterile Filtration (if applicable)
        ↓
Filling
        ↓
Stoppering / Plunger / Closure
        ↓
Optional Needle / Safety Device Assembly
        ↓
Visual Inspection
        ↓
CCI / Device Functional Testing
        ↓
Label / Package
        ↓
Reconciliation
        ↓
Constituent Review(s)
        ↓
Final DDCP QA Release
```

Each stage is instantiated from a released recipe/profile snapshot.

# 6. Profile Configuration Schema

```ts
type InjectableDDCPProfile = {
  subtype: "PREFILLED_SYRINGE"|"CARTRIDGE"|"VIAL_DEVICE_COPACK"|"OTHER_INJECTABLE";
  drugConstituentVersionId: string;
  deviceConstituents: DeviceConstituentRequirement[];
  primaryContainerArchitecture: string;
  sterileProcess: {
    aseptic: boolean;
    terminalSterilization?: boolean;
    sterileFiltrationRequired?: boolean;
  };
  fillControl: {
    targetRuleId: string;
    ipcSamplingPlanId: string;
    acceptanceRuleId: string;
  };
  requiredDeviceTests: string[];
  requiredCCIProfileId?: string;
  requiredVisualInspectionProfileId: string;
  releaseProfileId: string;
};
```

# 7. Key Data Objects

- `ddcp_profile_version`
- `constituent_requirement`
- `constituent_handoff`
- `fill_operation`
- `production_count_ledger`
- `device_assembly_record`
- `device_functional_test_link`
- `ddcp_release_checkpoint`
- `batch_evidence_manifest`

Do not duplicate QC, Genealogy, Equipment or Audit tables.

# 8. Constituent Handoff Contract

`constituent_handoff`:
```text
handoff_id
constituent_type DRUG|BIOLOGIC|DEVICE
source_lot/version
source_release_decision
quantity/unit scope
receiving DDCP batch/stage
effective_at
status
evidence refs
```

Final DDCP release never derives solely from constituent release.

# 9. UI

1. Injectable Profile Designer
2. Constituent Requirements
3. Batch Readiness
4. Filling Setup
5. Aseptic Fill Execution
6. Fill IPC
7. Closure/Assembly
8. Inspection
9. Device Functional Results
10. Reconciliation
11. DDCP Review
12. Final Release Summary

# 10. Stable Errors

`PFS_PROFILE_NOT_EFFECTIVE`, `BULK_NOT_RELEASED`, `PRIMARY_COMPONENT_NOT_RELEASED`, `LINE_NOT_READY`, `STERILE_FILTRATION_REQUIRED`, `FILL_PROGRAM_MISMATCH`, `FILL_IPC_OOS`, `FILTER_INTEGRITY_FAILED`, `CCI_TEST_FAILED`, `DEVICE_TEST_FAILED`, `PFS_RECONCILIATION_FAILED`.

# 11. Module Connection

```text
Product Profile → Recipe Snapshot
Materials → Constituent Handoff
Equipment/Cleaning/Sterile/EM → Readiness
Edge → Filler/Inspector/Test Evidence
QC → IPC/CCI/Functional Results
Genealogy → Drug + Device + Unit/Lot Trace
QMS → Exceptions
Review → Combined Evidence
Release → Final DDCP Decision
```

# 12. Mandatory Tests

- unreleased bulk blocked;
- wrong stopper/syringe lot blocked;
- clean hold expired;
- filter post-use integrity failed;
- fill IPC OOS;
- unplanned aseptic intervention;
- count source retry duplicate;
- visual reject reconciliation;
- CCI sample failure;
- device functional test fail;
- component change after batch issue does not alter snapshot;
- final release with device constituent incomplete denied.

# 13. Acceptance

One representative PFS batch is fully executable from released drug and device components to final packaged DDCP, with exact genealogy, sterile/process/device evidence, exception handling and final QA release.

# 14. Claude Code Prohibitions

- Do not implement PFS as a hardcoded separate batch engine.
- Do not mark filled syringes released when drug constituent alone is released.
- Do not overwrite original failed inspection/device/CCI result after retest.
- Do not dynamically bind issued batch to newer component/profile version.
