# US eBMR / eDHR Regulated Manufacturing Platform
## Document 42 — Sterilization, CIP/SIP & Sterile Filtration Management — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EQP-005  
**Parent Documents:** Documents 01–37  
**Primary Dependencies:** Equipment, Cleaning, Aseptic, Edge, QC, Genealogy, Release  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products (DDCP)  
**Future Profiles:** Medical Devices, Pharmaceuticals  
**Date:** 2026-08-20

---

# Implementation Standard

This specification is implementation-grade and is intended to be sufficient for Codex, Claude Code, or a human development team to implement the module with minimal interpretation.

Each module defines, where applicable:
- objective, scope and exclusions;
- actors/roles;
- complete functionality and sub-functionality;
- workflows/state machines;
- business rules;
- authorization/SoD;
- e-signature/audit behavior;
- entities/fields/relationships;
- database ownership/tables/indexes/constraints;
- APIs/error codes/idempotency/concurrency;
- events/outbox contracts;
- UI screens/actions;
- Edge/equipment integrations;
- failure/recovery;
- security/configuration/observability;
- retention/migration/performance;
- repository structure;
- implementation sequence;
- positive/negative/failure/concurrency tests;
- acceptance criteria;
- explicit coding-agent rules.

If a missing decision changes regulated behavior, the coding agent must raise a specification gap rather than guess.

# Regulatory Engineering Basis

Current verified U.S. anchors include:

- 21 CFR §211.42: aseptic processing areas require, as appropriate, cleanable surfaces, temperature/humidity controls, HEPA-filtered positive-pressure air, environmental monitoring, cleaning/disinfection and maintenance of equipment controlling aseptic conditions.
- §211.67: equipment/utensils must be cleaned, maintained and, where appropriate, sanitized/sterilized at suitable intervals; written procedures must define responsibilities, schedules, methods, removal of previous batch identity, protection of clean equipment and pre-use inspection.
- §211.68: automatic/mechanical/electronic equipment used in manufacturing must be routinely calibrated, inspected or checked under a written program, with records retained.
- §211.113(b): procedures for sterile products must include validation of aseptic and sterilization processes.
- §211.182: major equipment use/cleaning/maintenance records must be maintained chronologically with required batch/product/person attribution.
- FDA's aseptic-processing guidance remains an important current technical reference for environmental monitoring, aseptic interventions, sterilization, filtration and contamination control.
- Current QMSR became effective February 2, 2026 and incorporates ISO 13485:2016 for device QMS requirements; this specification does not reproduce copyrighted ISO clauses.

Official references:
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-C/section-211.42
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-D/section-211.67
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-D/section-211.68
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-F/section-211.113
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-J/section-211.182
- https://www.fda.gov/files/drugs/published/Sterile-Drug-Products-Produced-by-Aseptic-Processing-%E2%80%94-Current-Good-Manufacturing-Practice.pdf
- https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr

# 1. Objective

Define validated sterilization and automated cleaning/sterilization cycles plus sterile-filtration identity, integrity testing, process evidence and downstream sterile-status issuance.

# 2. Actors

- Sterilization Operator
- Production Operator
- Engineering
- Microbiology/QC
- QA Reviewer
- Validation
- External Sterilization Integration
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| STR-FR-001 | Process profile | Released sterilization/CIP/SIP/filter process profile by equipment/product/component/load type. | Validated recipe. |
| STR-FR-002 | Process types | Steam/autoclave, dry heat, depyrogenation, gas/radiation/external reference, SIP, CIP, sterile filtration and approved future types. | Extensible. |
| STR-FR-003 | Cycle recipe version | Exact cycle parameters, phases, limits, sensors and acceptance rules Vault-released. | No controller drift. |
| STR-FR-004 | Load definition | Record load items, equipment/parts/components, lot/container IDs, load configuration and pattern version. | Load trace. |
| STR-FR-005 | Equipment eligibility | Sterilizer/CIP/SIP system must be qualified/calibrated/maintained and correct recipe available. | Valid equipment. |
| STR-FR-006 | Cycle start authorization | Verify load, recipe, operator, equipment and prerequisites before start. | Prevention. |
| STR-FR-007 | Automated cycle acquisition | Capture controller/PLC cycle ID, parameters, alarms, phase data, source timestamps, quality and evidence file. | Raw process evidence. |
| STR-FR-008 | Critical parameter evaluation | Released rule checks temperature/pressure/time/F0/concentration/flow/conductivity or process-specific parameters. | Deterministic acceptance. |
| STR-FR-009 | Cycle deviation | Critical excursion/alarm automatically fails/holds cycle pending investigation; operator cannot manually mark pass. | Fail safe. |
| STR-FR-010 | Cycle review | Qualified reviewer assesses cycle/evidence/alarms and signs acceptance/rejection. | Independent. |
| STR-FR-011 | Biological/chemical indicators | Where used, record indicator IDs/locations/lots/results and QC links. | Validation/routine evidence. |
| STR-FR-012 | Sterile status issuance | Accepted sterilization cycle grants bounded sterile status to exact load items with expiry/hold rules. | Downstream eligibility. |
| STR-FR-013 | SIP status | Accepted SIP grants equipment/product-contact path sterile status for defined validity window. | Aseptic readiness. |
| STR-FR-014 | CIP execution | Record cleaning solution, concentration, temperature, flow, time, conductivity/rinse endpoints and alarms. | Automated cleaning. |
| STR-FR-015 | CIP verification | CIP completion may still require sampling/visual/chemical verification per procedure. | No automation shortcut. |
| STR-FR-016 | Filter master | Filter type/manufacturer/lot/serial/pore rating/application/install location/status. | Exact identity. |
| STR-FR-017 | Filter installation | Record filter lot/serial, housing, direction, operator, sterilization/status and product/batch use. | Genealogy. |
| STR-FR-018 | Pre-use integrity test | Where profile requires, perform/record approved integrity test before use. | Filter assurance. |
| STR-FR-019 | Post-use integrity test | Where required, perform/record after filtration and before release decision. | Process assurance. |
| STR-FR-020 | Integrity failure | Failure creates batch/equipment hold, deviation and impacted product assessment; original result retained. | No hidden failure. |
| STR-FR-021 | Filtration parameters | Record pressure/flow/differential pressure/time/volume/temp and filter train as required. | Complete process. |
| STR-FR-022 | Filter reuse | Default single-use unless released validated profile explicitly permits reuse with cycle/use tracking. | Safe default. |
| STR-FR-023 | Vent/gas filters | Support sterile gas/vent filter identity, sterilization and integrity where applicable. | Barrier control. |
| STR-FR-024 | Hold-time link | Sterilized item/filter/clean equipment validity ties to aseptic/clean hold limits. | Integrated. |
| STR-FR-025 | External sterilizer | Contract sterilization adapter can import cycle/load/certificate/evidence but Quality acceptance remains GxP-controlled. | Supplier boundary. |
| STR-FR-026 | Reprocessing after failure | Failed cycle cannot simply be rerun; approved investigation/reprocessing route required. | No test-until-pass. |
| STR-FR-027 | Qualification/validation reference | Cycle profile references approved validation/requalification evidence and load pattern. | Validated basis. |
| STR-FR-028 | Batch/device genealogy | Sterilization/filter/cycle relationships appear in genealogy/eDHR/eBMR. | Trace. |
| STR-FR-029 | QA/release integration | Unreviewed/failed required cycle or filter integrity blocks QA/release. | Release control. |
| STR-FR-030 | Audit/export | Cycle/load/filter/raw evidence/review/impact package exportable. | Inspection-ready. |


# 4. State / Workflow Model

```text
PROFILE/LOAD READY → CYCLE_STARTED → CYCLE_RUNNING
     → CYCLE_COMPLETE → REVIEW_PENDING
     ├→ ACCEPTED → STERILE/CLEAN STATUS ISSUED
     └→ FAILED/HOLD → INVESTIGATION

FILTER:
RECEIVED/ELIGIBLE → INSTALLED → PRE_USE_TEST (if required)
→ IN_USE → POST_USE_TEST → ACCEPTED / FAILED
```

# 5. Data Model

## `process_cycle_profile_version`
- process type
- equipment class
- load pattern
- controller recipe/version
- critical parameters/limits
- indicator requirements
- review policy
- validation reference
- released Vault ID

## `process_cycle`
```text
id uuid PK
process_type varchar(40)
equipment_id uuid
profile_version_id uuid
batch_id uuid
controller_cycle_id varchar(160)
load_id uuid
state varchar(40)
started_at/completed_at timestamptz
parameter_summary jsonb
alarm_summary jsonb
raw_evidence_ref uuid
review_signature_id uuid
version bigint
```

## `sterilization_load_item`
- cycle/load
- item/equipment/component/lot/container
- position/load pattern
- resulting sterile status/expiry

## `sterile_filter_use`
- filter lot/serial
- batch/process
- installation
- pre/post integrity test refs
- process parameters
- state


# 6. APIs

- `POST /sterilization/v1/cycles`
- `POST /sterilization/v1/cycles/{id}/start`
- `POST /sterilization/v1/cycles/{id}/data`
- `POST /sterilization/v1/cycles/{id}/review`
- `POST /cip-sip/v1/cycles`
- `POST /filtration/v1/filters/install`
- `POST /filtration/v1/filters/{id}/integrity-tests`
- `POST /filtration/v1/uses/{id}/complete`
- `GET /sterilization/v1/items/{id}/status`

All regulated mutation APIs pass through the GxP Mutation Gateway.

# 7. UI Screens

1. Cycle Profiles
2. Load Builder
3. Cycle Execution/Monitor
4. Cycle Review
5. Indicators
6. CIP/SIP
7. Filter Inventory/Installation
8. Integrity Testing
9. Sterile Status
10. Batch/Genealogy Summary

# 8. Events

- `SterilizationCycleStarted`
- `SterilizationCycleCompleted`
- `SterilizationCycleFailed`
- `SterilizationCycleAccepted`
- `SIPStatusIssued`
- `CIPCompleted`
- `FilterInstalled`
- `FilterIntegrityPassed`
- `FilterIntegrityFailed`
- `SterileStatusExpired`

# 9. Authorization / Signature / Audit

- Server-side Policy Service controls execution and approvals.
- Quality/Engineering authority is separate from generic system administration.
- Required calibration, cleaning, maintenance, line-clearance and sterile-process approvals use policy-defined electronic signatures.
- Equipment state changes are audited with previous/new state, reason, actor/source and linked evidence.
- Automated equipment results retain source device identity, source timestamp, receive timestamp, mapping version and quality status.
- Direct Frappe/DB changes to authoritative equipment/sterile state are prohibited.

# 10. Failure / Recovery

- PostgreSQL unavailable: no regulated state transition.
- Edge/device unavailable: behavior follows released fallback policy; no fabricated reading/result.
- Calibration/qualification status cannot be assumed when source unavailable.
- Worker restart resumes scheduled maintenance/calibration/EM/sterilization jobs from persisted state.
- Event-bus outage uses outbox retry.
- Stale versions are rejected.
- Failed critical integrity checks generate Quality/Security event and relevant equipment/process hold.

# 11. Repository Structure

```text
services/gxp-api/src/modules/sterilization-cip-sip-and-sterile-filtration-management/
apps/ebmr_frappe/ebmr/sterilization-cip-sip-and-sterile-filtration-management/
edge/gateway/plugins/sterilization-cip-sip-and-sterile-filtration-management/
contracts/events/sterilization-cip-sip-and-sterile-filtration-management/
validation/requirements/sterilization-cip-sip-and-sterile-filtration-management/
```

# 12. Implementation Sequence

1. Core master/state model.
2. Schedule/eligibility engine.
3. Execution records and evidence.
4. GxP authorization/signature/audit.
5. Batch/Recipe/QA/Release integration.
6. Edge/device source integration.
7. Alerts/escalation.
8. UI/dashboard/export.
9. Failure/concurrency/negative tests.
10. Validation traceability.

# 13. Test Catalogue

- valid autoclave cycle
- wrong load pattern
- controller alarm
- cycle critical parameter fail
- rerun without investigation denied
- CIP rinse failure
- pre-use filter fail
- post-use filter fail
- external sterilizer evidence
- sterile status expiry
- release blocker

# 14. Acceptance Criteria

Representative sterile DDCP batch can prove exact sterilization/CIP/SIP/filter lineage and that all required cycles and integrity tests were valid, reviewed and current for the manufacturing window.

# 15. Codex / Claude Code Rules

- Never let PLC controller 'cycle complete' equal GxP accepted cycle automatically.
- Never rerun failed sterilization until pass without controlled investigation.
- Never overwrite failed integrity test.
- Never issue sterile status without exact accepted load/item relationship.

# 16. Stable Error Codes
`CYCLE_PROFILE_NOT_EFFECTIVE`, `STERILIZER_INELIGIBLE`, `LOAD_PATTERN_INVALID`, `CYCLE_PARAMETER_FAILED`, `CYCLE_REVIEW_REQUIRED`, `FILTER_INTEGRITY_FAILED`, `STERILE_STATUS_EXPIRED`, `REPROCESSING_AUTHORIZATION_REQUIRED`.
