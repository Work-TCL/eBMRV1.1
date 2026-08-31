# US eBMR / eDHR Regulated Manufacturing Platform
## Document 39 — Cleaning, Sanitization & Line Clearance — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EQP-002  
**Parent Documents:** Documents 01–37  
**Primary Dependencies:** Equipment, Batch, Packaging, QC, Sterile/Aseptic  
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

Define controlled equipment/area cleaning, sanitization, cleanliness verification, clean/dirty hold times and manufacturing/packaging line clearance.

# 2. Actors

- Production Operator
- Sanitation/Cleaning Operator
- Supervisor
- QA
- QC Sampler/Analyst
- Engineering
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| CLN-FR-001 | Cleaning procedure | Released procedure by equipment/area/product family defining method, agent, concentration, contact time, tools, disassembly/reassembly and acceptance. | Controlled method. |
| CLN-FR-002 | Cleaning type | Routine, product-changeover, campaign-end, deep clean, sanitization, manual, COP/CIP reference. | Clear semantics. |
| CLN-FR-003 | Schedule | Time/use/campaign/batch-count triggered cleaning due rules. | Appropriate intervals. |
| CLN-FR-004 | Responsibility | Procedure defines performer/verifier roles and qualifications. | 211.67 support. |
| CLN-FR-005 | Previous batch identity removal | Checklist/evidence confirms removal/obliteration of prior product/batch labels/materials/documents. | Mix-up prevention. |
| CLN-FR-006 | Pre-clean status | Equipment/area placed Dirty/To Clean and unavailable for use. | Execution gate. |
| CLN-FR-007 | Cleaning execution | Capture procedure version, agents/lots, concentration, times, steps, performer/source and evidence. | Complete record. |
| CLN-FR-008 | Disassembly/reassembly | Required components/parts tracked and verification before release. | Proper cleaning. |
| CLN-FR-009 | Inspection | Immediate pre-use cleanliness inspection where applicable, separate from cleaning completion. | 211.67 support. |
| CLN-FR-010 | Swab/rinse sampling | Where validation/routine verification requires, create QC sample/test with location/limit/spec. | Analytical verification. |
| CLN-FR-011 | Visual acceptance | Structured inspection criteria/results; visual-only permitted only where approved procedure allows. | Controlled. |
| CLN-FR-012 | Dirty hold time | Track maximum allowed time from use to cleaning start and generate deviation if exceeded. | Validated limits. |
| CLN-FR-013 | Clean hold time | Track clean state expiry; expired equipment requires re-clean/reinspection per procedure. | Protected clean state. |
| CLN-FR-014 | Protection after cleaning | Record cover/closure/storage state to protect clean equipment before use. | 211.67 support. |
| CLN-FR-015 | Cleaning verification failure | Failed swab/rinse/visual check creates deviation/NCR and equipment remains unavailable. | Fail safe. |
| CLN-FR-016 | Line clearance plan | Released checklist by line/area/process/packaging step. | Consistent clearance. |
| CLN-FR-017 | Line clearance execution | Verify removal of prior materials/components/labels/documents/product and readiness of area/equipment. | Mix-up prevention. |
| CLN-FR-018 | Material/label clearance | Scan/count leftover material/labels and reconcile/return/destroy as applicable. | Packaging integration. |
| CLN-FR-019 | Equipment status clearance | Confirm correct cleaned/calibrated/qualified equipment installed. | Readiness. |
| CLN-FR-020 | Area status | Confirm room/line cleanliness/environmental readiness and no incompatible concurrent operation. | Contamination control. |
| CLN-FR-021 | Independent verification | Second-person/automated verification where procedure requires. | Authority. |
| CLN-FR-022 | Batch linkage | Line clearance and cleaning evidence linked to exact batch/stage/packaging run. | eBMR evidence. |
| CLN-FR-023 | Changeover | End-of-batch clearance and next-product startup clearance remain distinct records. | No ambiguous state. |
| CLN-FR-024 | Campaign rules | Campaign manufacturing allows defined cleaning frequency but records each use and campaign boundary. | Configurable. |
| CLN-FR-025 | Automated cleaning | CIP/SIP cycle may satisfy parts of cleaning record only through validated interface and verification. | Automation safe. |
| CLN-FR-026 | Cleaning validation reference | Procedure references current approved validation study/matrix and product/equipment family applicability. | Validated basis. |
| CLN-FR-027 | Cleaning status | Equipment/area states: DIRTY, CLEANING, CLEAN, CLEAN_EXPIRED, HOLD, READY_FOR_USE. | Explicit. |
| CLN-FR-028 | Audit/export | Chronological cleaning/use/inspection/line-clearance history exportable. | Inspection-ready. |


# 4. State / Workflow Model

```text
DIRTY → CLEANING → CLEANING_VERIFICATION → CLEAN
CLEAN → READY_FOR_USE
CLEAN → CLEAN_EXPIRED
ANY → HOLD

LINE CLEARANCE:
NOT_STARTED → IN_PROGRESS → VERIFICATION_PENDING → CLEARED
→ EXPIRED/USED
```

# 5. Data Model

## `cleaning_procedure_version`
- equipment/area scope
- cleaning type
- agents/concentrations
- steps/times
- disassembly
- sample/inspection requirements
- dirty/clean hold limits
- validation reference
- released Vault ID

## `cleaning_execution`
```text
id uuid PK
equipment_id/area_id uuid
procedure_version_id uuid
batch_context jsonb
state varchar(40)
started_at/completed_at timestamptz
dirty_since timestamptz
clean_until timestamptz
agents_used jsonb
performer/reviewer jsonb
version bigint
```

## `line_clearance`
- line/area
- previous batch/product
- next batch/product
- checklist version
- material/label/equipment items
- performer/verifier
- state/expiry


# 6. APIs

- `POST /cleaning/v1/executions`
- `POST /cleaning/v1/executions/{id}/steps`
- `POST /cleaning/v1/executions/{id}/complete`
- `POST /cleaning/v1/executions/{id}/verify`
- `POST /line-clearance/v1`
- `POST /line-clearance/v1/{id}/complete`
- `GET /cleaning/v1/equipment/{id}/status`

All regulated mutation APIs pass through the GxP Mutation Gateway.

# 7. UI Screens

1. Cleaning Queue
2. Cleaning Execution
3. Agents/Materials
4. Inspection/Sampling
5. Clean Hold Status
6. Line Clearance
7. Changeover
8. Cleaning History

# 8. Events

- `CleaningStarted`
- `CleaningCompleted`
- `CleaningVerificationFailed`
- `EquipmentMarkedClean`
- `CleanHoldExpired`
- `LineClearanceStarted`
- `LineClearanceCompleted`
- `LineClearanceFailed`

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
services/gxp-api/src/modules/cleaning-sanitization-and-line-clearance/
apps/ebmr_frappe/ebmr/cleaning-sanitization-and-line-clearance/
edge/gateway/plugins/cleaning-sanitization-and-line-clearance/
contracts/events/cleaning-sanitization-and-line-clearance/
validation/requirements/cleaning-sanitization-and-line-clearance/
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

- normal clean
- dirty hold exceeded
- clean hold expires
- swab failure
- wrong cleaning procedure
- previous label remains
- wrong equipment installed
- campaign cleaning
- CIP integration
- second-person verification

# 14. Acceptance Criteria

Equipment/line cannot become ready for regulated use until required cleaning and line-clearance evidence is complete and current for the exact next operation.

# 15. Codex / Claude Code Rules

- Never change equipment from DIRTY to CLEAN without execution record.
- Never treat line clearance as single unchecked checkbox.
- Never suppress failed cleaning verification after successful repeat.
- Never allow expired clean hold to remain eligible.

# 16. Stable Error Codes
`CLEANING_REQUIRED`, `DIRTY_HOLD_EXCEEDED`, `CLEAN_HOLD_EXPIRED`, `CLEANING_VERIFICATION_FAILED`, `LINE_CLEARANCE_REQUIRED`, `PREVIOUS_BATCH_IDENTITY_PRESENT`, `WRONG_EQUIPMENT_INSTALLED`.
