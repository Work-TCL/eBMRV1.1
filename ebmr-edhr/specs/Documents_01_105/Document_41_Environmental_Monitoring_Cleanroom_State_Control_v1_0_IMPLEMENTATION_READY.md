# US eBMR / eDHR Regulated Manufacturing Platform
## Document 41 — Environmental Monitoring & Cleanroom State Control — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EQP-004  
**Parent Documents:** Documents 01–37  
**Primary Dependencies:** Aseptic Operations, Edge/Historian, QC/Microbiology, QMS  
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

Define environmental-monitoring program execution, continuous/frequent cleanroom condition monitoring, excursion handling, trending and batch/area state correlation.

# 2. Actors

- EM Technician
- Microbiology Analyst
- QC Reviewer
- QA
- Aseptic Supervisor
- Facilities/Engineering
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| EM-FR-001 | EM program | Released program by site/area defining locations, methods, frequencies, shifts/operations, limits and actions. | Written program. |
| EM-FR-002 | Location master | Unique monitoring point with room/zone, coordinates/description, sample type and criticality. | Exact location. |
| EM-FR-003 | Monitoring types | Viable air, surface/contact, settle plate, personnel, nonviable particles, temperature, humidity, differential pressure and other approved types. | Comprehensive. |
| EM-FR-004 | Schedule | Routine/static/dynamic/in-operation/post-operation schedules and event-triggered monitoring. | Coverage. |
| EM-FR-005 | Sample plan | Create EM sampling tasks with location/method/media/instrument/assigned qualified user. | Execution. |
| EM-FR-006 | Instrument eligibility | Particle counter/sensor/air sampler must be calibrated/qualified. | Valid source. |
| EM-FR-007 | Media/reagent | Microbiological media lot/status/growth-promotion/expiry where applicable. | Microbiology integrity. |
| EM-FR-008 | Sample execution | Capture collector, actual location/time, operation/batch context, instrument/media and conditions. | Trace. |
| EM-FR-009 | Incubation | Track media incubation conditions/times and readings for viable monitoring. | Complete microbiology. |
| EM-FR-010 | Result | Structured count/value/qualitative result and units; raw evidence retained. | Data. |
| EM-FR-011 | Alert/action limits | Versioned limits by location/type/state/operation; distinction between alert and action. | Controlled thresholds. |
| EM-FR-012 | Excursion trigger | Limit excursion creates EM event/deviation/investigation and relevant area/batch impact. | Fail safe. |
| EM-FR-013 | Organism identification | Support organism ID/species/genus/gram/morphology or lab reference where required. | Microbial investigation. |
| EM-FR-014 | Personnel monitoring | Link result to operator/gowning session/aseptic operation while respecting access/privacy. | Personnel impact. |
| EM-FR-015 | Continuous sensors | HVAC/BMS sensors integrate via Edge; retain source identity, timestamps, quality and evidence summaries. | Automation. |
| EM-FR-016 | Data gap | Missing/failed sensor/sample task creates data-gap event; no silent interpolation for GxP decision. | Integrity. |
| EM-FR-017 | Trend | Trend by location/type/organism/shift/product/season/time and detect deterioration before action limits. | State of control. |
| EM-FR-018 | Baseline | Trend baseline/version/cutoff retained. | Reproducible. |
| EM-FR-019 | Batch correlation | Associate dynamic/in-operation results and excursions to exact batch/stage/time window. | Impact assessment. |
| EM-FR-020 | Area status | Area readiness derives from current program/tasks/excursions/HVAC state, not manual green flag. | Execution gate. |
| EM-FR-021 | Investigation | Excursion links Deviation/CAPA and cleaning/disinfection corrective action. | QMS. |
| EM-FR-022 | Resampling | Resampling after excursion is controlled and does not erase original excursion. | No testing into compliance. |
| EM-FR-023 | Facility alarms | Pressure/temp/humidity/particle alarm events included in batch/QA timeline where relevant. | Review. |
| EM-FR-024 | Review | Microbiology/QA review results and trends; signatures according to procedure. | Authority. |
| EM-FR-025 | Retention/export | Raw result/evidence, trend and excursion history retained/exportable. | Inspection-ready. |
| EM-FR-026 | Performance | Continuous high-frequency raw telemetry stays historian/time-series; GxP store keeps relevant event/result/evidence refs. | Scale. |


# 4. State / Workflow Model

```text
PROGRAM/SCHEDULE → SAMPLE_TASK → COLLECTED/ACQUIRED → RESULT_PENDING
     → REVIEWED
     ├→ NORMAL
     ├→ ALERT
     └→ ACTION_EXCURSION → INVESTIGATION → DISPOSITION

AREA STATUS: READY / WARNING / HOLD / NOT_READY
```

# 5. Data Model

## `em_program_version`
- site/area scope
- monitoring types
- locations
- method/version
- frequency
- alert/action limits
- operation/shift coverage
- review/trend rules
- released Vault ID

## `em_location`
- area/room/zone
- location code
- criticality
- sample types
- active/effective status

## `em_sample_or_reading`
```text
id uuid PK
program_version_id uuid
location_id uuid
monitoring_type varchar(60)
batch_id/aseptic_operation_id uuid
instrument_or_media_ref jsonb
sampled_at/acquired_at timestamptz
result jsonb
alert_action_status varchar(40)
review_state varchar(40)
version bigint
```

## `em_excursion`
- source result/event
- affected area/time/batches
- organism/details
- deviation/CAPA link
- disposition


# 6. APIs

- `POST /em/v1/programs`
- `POST /em/v1/tasks`
- `POST /em/v1/tasks/{id}/collect`
- `POST /em/v1/results`
- `POST /em/v1/results/{id}/review`
- `POST /em/v1/excursions/{id}/impact`
- `GET /em/v1/areas/{id}/readiness`
- `GET /em/v1/trends`

All regulated mutation APIs pass through the GxP Mutation Gateway.

# 7. UI Screens

1. EM Program
2. Monitoring Locations
3. Sampling Schedule
4. EM Collection
5. Continuous Monitoring
6. Result Review
7. Excursions
8. Organism Identification
9. Area Readiness
10. Trend Dashboard
11. Batch Correlation

# 8. Events

- `EMTaskScheduled`
- `EMSampleCollected`
- `EMResultRecorded`
- `EMAlertTriggered`
- `EMActionLimitExceeded`
- `EMDataGapDetected`
- `EMAreaHeld`
- `EMExcursionClosed`

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
services/gxp-api/src/modules/environmental-monitoring-and-cleanroom-state-control/
apps/ebmr_frappe/ebmr/environmental-monitoring-and-cleanroom-state-control/
edge/gateway/plugins/environmental-monitoring-and-cleanroom-state-control/
contracts/events/environmental-monitoring-and-cleanroom-state-control/
validation/requirements/environmental-monitoring-and-cleanroom-state-control/
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

- normal viable sample
- action-limit excursion
- resample cannot hide excursion
- continuous pressure gap
- sensor quality bad
- unqualified instrument
- organism ID
- batch correlation
- area readiness blocked
- historian outage

# 14. Acceptance Criteria

QA can determine environmental state for the exact aseptic operation/batch window, including missing data, alerts/action excursions, organisms, investigations and final disposition.

# 15. Codex / Claude Code Rules

- Never interpolate missing GxP environmental evidence to create a pass.
- Never overwrite excursion with resample result.
- Never write high-frequency raw historian data directly into Frappe DocTypes.
- Never make area READY from a manual toggle alone.

# 16. Stable Error Codes
`EM_PROGRAM_NOT_EFFECTIVE`, `EM_LOCATION_INVALID`, `EM_INSTRUMENT_INELIGIBLE`, `EM_DATA_GAP`, `EM_ACTION_LIMIT_EXCEEDED`, `EM_AREA_NOT_READY`, `EM_REVIEW_REQUIRED`.
