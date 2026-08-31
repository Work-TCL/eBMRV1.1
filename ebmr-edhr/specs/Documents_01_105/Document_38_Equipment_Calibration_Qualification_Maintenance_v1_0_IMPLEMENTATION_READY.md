# US eBMR / eDHR Regulated Manufacturing Platform
## Document 38 — Equipment, Calibration, Qualification & Maintenance — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EQP-001  
**Parent Documents:** Documents 01–37  
**Primary Dependencies:** Recipe, Batch Execution, Training, Change, Edge, Cleaning  
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

Define regulated equipment lifecycle, qualification, calibration, maintenance, use history and execution eligibility for manufacturing, laboratory and packaging equipment.

# 2. Actors

- Equipment Administrator
- Engineering Manager
- Maintenance Technician
- Calibration Technician
- Production Operator
- QA
- Validation
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| EQP-FR-001 | Equipment master | Unique asset ID, type/class, manufacturer/model/serial, site/area/location, ownership and lifecycle status. | Canonical equipment identity. |
| EQP-FR-002 | Equipment class | Reusable equipment class defines capability, process use, calibration/maintenance/cleaning requirements and allowed recipe roles. | Recipe compatibility. |
| EQP-FR-003 | Lifecycle | Planned, Installed, Qualification Pending, Qualified/Available, Maintenance, Calibration Due, Out of Service, Suspended, Retired. | Explicit state. |
| EQP-FR-004 | Qualification status | Track IQ/OQ/PQ or equivalent qualification references, approved scope, effective/expiry/requalification triggers. | Use only qualified assets. |
| EQP-FR-005 | Calibration plan | Define calibration points, tolerances, procedure/version, frequency, standard requirements and due rules. | Controlled calibration. |
| EQP-FR-006 | Calibration execution | Capture pre-calibration/as-found, adjustments, post-calibration/as-left, standard/equipment, performer, date and result. | Complete evidence. |
| EQP-FR-007 | Out-of-tolerance calibration | OOT calibration automatically generates equipment hold/impact assessment and may trigger deviation/CAPA. | Product impact controlled. |
| EQP-FR-008 | Calibration standards | Reference standard/tool ID, calibration status, traceability/evidence and expiry. | Reliable calibration. |
| EQP-FR-009 | Preventive maintenance plan | Frequency, tasks, parts, procedure, owner, expected downtime and due dates. | Routine upkeep. |
| EQP-FR-010 | Maintenance work order | Create planned/corrective work order with fault, work, parts, technician, timestamps and verification. | Service history. |
| EQP-FR-011 | Post-maintenance verification | Equipment remains unavailable until required inspection/calibration/requalification/cleaning complete. | Safe return. |
| EQP-FR-012 | Breakdown | Unexpected failure marks equipment unavailable and evaluates affected in-process/recent batches. | Impact. |
| EQP-FR-013 | Equipment use log | Record date/time, batch/product/operation, operator/source, cleaning/maintenance context in chronological history. | 211.182 support. |
| EQP-FR-014 | Dedicated equipment | Support dedicated-equipment profile with use/cleaning evidence in batch when appropriate. | Flexible compliance. |
| EQP-FR-015 | Pre-use eligibility | Batch step checks current qualification, calibration, maintenance, cleaning and hold status. | No invalid equipment. |
| EQP-FR-016 | Reservation | Reserve equipment for batch/time window; reservation never overrides quality eligibility. | Scheduling. |
| EQP-FR-017 | Meter/runtime counters | Capture hours/cycles/counts from Edge/manual source for condition/frequency-based maintenance. | Predictive scheduling. |
| EQP-FR-018 | Instrument/device identity | Register PLC, balance, tester, sensor, controller or machine endpoints and credentials/certificates separately from asset master. | Secure integration. |
| EQP-FR-019 | Edge mapping | Versioned mapping between equipment tag/channel and GxP parameter. | Source traceability. |
| EQP-FR-020 | Status from maintenance system | External CMMS can provide work-order/reference status, but final GxP availability uses controlled product policy. | Boundary. |
| EQP-FR-021 | Spare parts | Record critical replaced component/part/serial where product/process impact exists. | Maintenance evidence. |
| EQP-FR-022 | Change control | Critical equipment modification links Change Control and validation impact. | Validated state. |
| EQP-FR-023 | Software/firmware | Track firmware/software/config version for automated equipment where relevant. | Reproducibility. |
| EQP-FR-024 | Alarm/events | Equipment alarms linked to batch/step and deviation when released rules require. | Process impact. |
| EQP-FR-025 | Cleaning dependency | Eligibility references current cleaning/sanitization/sterilization state from Document 39/42. | Integrated. |
| EQP-FR-026 | Location transfer | Moving equipment to another area/site can trigger requalification/change/cleaning requirements. | Controlled relocation. |
| EQP-FR-027 | Retirement | Retire with final status, data retention, outstanding batch/maintenance impact and approval. | Lifecycle closure. |
| EQP-FR-028 | Dashboard | Due calibration/maintenance, out-of-service, utilization, recurring failures and impact events. | Operational visibility. |
| EQP-FR-029 | Audit/export | Complete qualification/calibration/maintenance/use history exportable. | Inspection-ready. |
| EQP-FR-030 | No status bypass | Admin/operator cannot manually set 'Qualified/Available' without controlled evidence/authority. | Integrity. |


# 4. State / Workflow Model

```text
PLANNED → INSTALLED → QUALIFICATION_PENDING → QUALIFIED_AVAILABLE
QUALIFIED_AVAILABLE → CALIBRATION_DUE / MAINTENANCE_DUE / OUT_OF_SERVICE / SUSPENDED
CALIBRATION/MAINTENANCE → VERIFICATION → QUALIFIED_AVAILABLE
ANY ACTIVE → RETIRED
```

# 5. Data Model

## `equipment_asset`
```text
id uuid PK
tenant_id uuid
site_id uuid
equipment_code varchar(120) UNIQUE
equipment_class_id uuid
manufacturer varchar(255)
model varchar(160)
serial_no varchar(160)
location_id uuid
state varchar(50)
qualification_status varchar(40)
calibration_status varchar(40)
maintenance_status varchar(40)
cleanliness_status varchar(40)
firmware_version varchar(80)
version bigint
```

## `equipment_calibration`
- asset ID
- calibration plan/version
- due/performed dates
- as-found values
- adjustments
- as-left values
- standards used
- result/status
- impact assessment/deviation
- performer/reviewer signatures

## `maintenance_work_order`
- type planned/corrective
- fault/diagnosis
- work/parts
- technician
- post-maintenance requirements
- verification
- state/version

## `equipment_use_log`
- equipment
- batch/product/step
- start/end
- operator/source
- cleaning context
- event references


# 6. APIs

- `POST /equipment/v1/assets`
- `POST /equipment/v1/{id}/qualifications`
- `POST /equipment/v1/{id}/calibrations`
- `POST /equipment/v1/{id}/maintenance`
- `POST /equipment/v1/{id}/hold`
- `POST /equipment/v1/{id}/return-to-service`
- `GET /equipment/v1/{id}/eligibility`
- `GET /equipment/v1/{id}/history`
- `GET /equipment/v1/dashboard`

All regulated mutation APIs pass through the GxP Mutation Gateway.

# 7. UI Screens

1. Equipment Catalogue
2. Asset Detail
3. Qualification
4. Calibration Plan/Execution
5. Maintenance Work Orders
6. Use Log
7. Firmware/Configuration
8. Eligibility
9. Due Dashboard
10. History/Export

# 8. Events

- `EquipmentInstalled`
- `EquipmentQualified`
- `CalibrationDue`
- `EquipmentCalibrated`
- `CalibrationOutOfTolerance`
- `MaintenanceDue`
- `EquipmentOutOfService`
- `MaintenanceCompleted`
- `EquipmentReturnedToService`
- `EquipmentRetired`

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
services/gxp-api/src/modules/equipment-calibration-qualification-and-maintenance/
apps/ebmr_frappe/ebmr/equipment-calibration-qualification-and-maintenance/
edge/gateway/plugins/equipment-calibration-qualification-and-maintenance/
contracts/events/equipment-calibration-qualification-and-maintenance/
validation/requirements/equipment-calibration-qualification-and-maintenance/
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

- valid equipment use
- expired calibration blocks step
- as-found OOT impact
- maintenance then calibration required
- breakdown during batch
- wrong equipment class
- relocation
- firmware change
- CMMS outage
- concurrent reservation
- retirement

# 14. Acceptance Criteria

Batch execution cannot start a step requiring equipment unless the exact asset is currently eligible for that operation, with qualification, calibration, maintenance and cleaning status resolved.

# 15. Codex / Claude Code Rules

- Never let Frappe status field alone determine equipment eligibility.
- Never reset calibration due date without completed calibration record.
- Never return equipment to service while required post-maintenance verification is incomplete.
- Never overwrite as-found calibration results.

# 16. Stable Error Codes
`EQUIPMENT_NOT_QUALIFIED`, `CALIBRATION_EXPIRED`, `MAINTENANCE_DUE`, `EQUIPMENT_OUT_OF_SERVICE`, `POST_MAINTENANCE_VERIFICATION_REQUIRED`, `CALIBRATION_OOT_IMPACT_REQUIRED`, `EQUIPMENT_CLASS_MISMATCH`.
