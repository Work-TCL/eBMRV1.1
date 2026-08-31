# US eBMR / eDHR Regulated Manufacturing Platform
## Document 40 — Sterile / Aseptic Manufacturing Operations — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EQP-003  
**Parent Documents:** Documents 01–37  
**Primary Dependencies:** Equipment, Cleaning, EM, Sterilization, Batch, QC, QA Review/Release  
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

Define aseptic-manufacturing execution controls for sterile/DDCP profiles, including classified-area readiness, personnel qualification, sterile component/equipment status, interventions, process hold times and batch-impact review.

# 2. Actors

- Aseptic Operator
- Aseptic Supervisor
- QA
- QC/Microbiology
- Environmental Monitoring Technician
- Engineering
- Validation
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| ASP-FR-001 | Sterile product profile | Product/recipe references released sterile/aseptic profile defining applicable controls. | Profile driven. |
| ASP-FR-002 | Classified area | Define cleanroom/zone/critical area and approved operation types. | Area eligibility. |
| ASP-FR-003 | Personnel qualification | Gowning/aseptic technique/media-fill or process qualification required by role/operation. | Qualified personnel. |
| ASP-FR-004 | Area qualification | Room/zone qualification/status required before aseptic operation. | Facility state. |
| ASP-FR-005 | Environmental readiness | Current EM/HVAC/pressure/temp/humidity status evaluated before start. | Controlled environment. |
| ASP-FR-006 | Line/room clearance | Required cleaning/disinfection/line-clearance complete before setup. | Readiness. |
| ASP-FR-007 | Sterile component status | Components, containers/closures, tools and product-contact parts must have valid sterile/clean status. | No contaminated input. |
| ASP-FR-008 | Equipment sterilization status | Applicable equipment/SIP/autoclave/filter status verified before use. | Sterility assurance. |
| ASP-FR-009 | Aseptic setup | Record assembly/setup steps, operators, sterile connections, equipment and timestamps. | Setup trace. |
| ASP-FR-010 | Intervention catalogue | Versioned catalogue: inherent/routine/corrective/non-routine interventions with permitted method and risk. | Structured interventions. |
| ASP-FR-011 | Intervention execution | Record exact time, operator, location, reason, duration, impacted units/time window and evidence. | Batch impact. |
| ASP-FR-012 | Unplanned intervention | Creates deviation/quality assessment based on rule. | No hidden intervention. |
| ASP-FR-013 | Open exposure time | Track exposure/hold time of sterile components/product when procedure defines limit. | Time control. |
| ASP-FR-014 | Aseptic process hold times | Bulk/filter/filling/stoppering/sealing hold times monitored and enforced. | Validated limits. |
| ASP-FR-015 | Filling operation | Capture line/filler, speed, fill parameters, batch/fill group, operators and machine data. | Complete process. |
| ASP-FR-016 | Container closure operation | Capture stoppering/sealing/capping status and inspection evidence. | Closure control. |
| ASP-FR-017 | Reject management | Aseptic/filling rejects tracked with reason, counts, serial/container range where applicable. | Reconciliation. |
| ASP-FR-018 | Media-fill qualification reference | Associate line/personnel/process qualification evidence and current status; full media-fill execution may be child spec. | Process assurance. |
| ASP-FR-019 | Sterility/bioburden tests | Link relevant QC test orders/results and release blockers. | Lab integration. |
| ASP-FR-020 | Filter integrity | Reference pre/post-use filter integrity requirement/result where configured. | Filtration assurance. |
| ASP-FR-021 | Environmental excursion | EM/HVAC/pressure excursion during operation creates impact window and Quality event. | Batch impact. |
| ASP-FR-022 | Operator excursion | Loss of qualification/gown breach/critical intervention creates hold/assessment. | Personnel risk. |
| ASP-FR-023 | RABS/isolator profile | Support barrier system identity, decontamination cycle status, glove integrity and intervention mapping when used. | Modern aseptic operations. |
| ASP-FR-024 | Gowning entry | Optional access/gowning qualification confirmation at area entry for regulated execution. | Access control. |
| ASP-FR-025 | Batch impact timeline | Overlay interventions, EM excursions, alarms and process events on manufacturing timeline. | Review-by-exception. |
| ASP-FR-026 | Aseptic completion | Operation cannot complete until sterile inputs, interventions, counts, EM and required process evidence resolved/current. | Completeness. |
| ASP-FR-027 | QA review | Aseptic summary feeds Review-by-Exception and Release Engine. | Release control. |
| ASP-FR-028 | Audit/export | Full aseptic execution package exportable with interventions, environment, sterile status and signatures. | Inspection-ready. |


# 4. State / Workflow Model

```text
PREPARATION → AREA_READY → ASEPTIC_SETUP → EXECUTION
     → INTERVENTION/EXCURSION (as needed)
     → ASEPTIC_COMPLETE → QA_REVIEW

ANY CRITICAL FAILURE → HOLD / DEVIATION / IMPACT_ASSESSMENT
```

# 5. Data Model

## `aseptic_profile_version`
- product/recipe scope
- required area class/profile
- personnel qualifications
- sterile input requirements
- intervention catalogue
- hold-time rules
- EM dependencies
- filter/sterilization requirements
- release blockers

## `aseptic_operation`
```text
id uuid PK
batch_id uuid
recipe_stage_id uuid
area_id uuid
profile_version_id uuid
state varchar(40)
started_at/completed_at timestamptz
environment_snapshot_ref uuid
version bigint
```

## `aseptic_intervention`
- operation ID
- intervention type/version
- planned/unplanned
- operator
- start/end
- location
- reason
- impacted time/unit scope
- deviation/impact link

## `aseptic_event_timeline`
- event type
- source
- authoritative timestamp
- batch/operation scope
- severity


# 6. APIs

- `POST /aseptic/v1/operations`
- `POST /aseptic/v1/operations/{id}/start`
- `POST /aseptic/v1/operations/{id}/interventions`
- `POST /aseptic/v1/operations/{id}/events`
- `POST /aseptic/v1/operations/{id}/complete`
- `GET /aseptic/v1/operations/{id}/readiness`
- `GET /aseptic/v1/operations/{id}/review-summary`

All regulated mutation APIs pass through the GxP Mutation Gateway.

# 7. UI Screens

1. Aseptic Readiness
2. Area/Personnel Status
3. Sterile Inputs
4. Aseptic Setup
5. Live Operation
6. Interventions
7. Hold-Time Timeline
8. Environment/Alarms
9. Completion
10. QA Summary

# 8. Events

- `AsepticOperationStarted`
- `AsepticInterventionRecorded`
- `UnplannedInterventionDetected`
- `AsepticHoldTimeExceeded`
- `AsepticEnvironmentExcursionDetected`
- `AsepticOperationHeld`
- `AsepticOperationCompleted`

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
services/gxp-api/src/modules/sterile---aseptic-manufacturing-operations/
apps/ebmr_frappe/ebmr/sterile---aseptic-manufacturing-operations/
edge/gateway/plugins/sterile---aseptic-manufacturing-operations/
contracts/events/sterile---aseptic-manufacturing-operations/
validation/requirements/sterile---aseptic-manufacturing-operations/
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

- start with failed area readiness
- unqualified operator
- expired sterile component status
- routine intervention
- unplanned intervention
- hold time exceeded
- pressure excursion
- filter integrity failure
- RABS glove issue
- completion with unresolved event denied

# 14. Acceptance Criteria

Representative sterile injectable/DDCP operation can run from readiness through filling/closure with traceable interventions, environment, sterile inputs/equipment, hold times and QA impact evidence.

# 15. Codex / Claude Code Rules

- Never let operator create arbitrary intervention category during production.
- Never treat EM status as informational only when profile makes it release-critical.
- Never hide unplanned intervention.
- Never complete aseptic stage while critical sterile-status dependency is unresolved.

# 16. Stable Error Codes
`ASEPTIC_AREA_NOT_READY`, `ASEPTIC_OPERATOR_NOT_QUALIFIED`, `STERILE_COMPONENT_INELIGIBLE`, `STERILIZATION_STATUS_INVALID`, `ASEPTIC_HOLD_TIME_EXCEEDED`, `UNPLANNED_INTERVENTION_REVIEW_REQUIRED`, `ASEPTIC_ENVIRONMENT_EXCURSION`.
