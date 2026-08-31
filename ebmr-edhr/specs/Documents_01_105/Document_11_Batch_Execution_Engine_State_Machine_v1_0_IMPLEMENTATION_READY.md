# US eBMR / eDHR Regulated Manufacturing Platform
## Document 11 — Batch Execution Engine & State Machine Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EBMR-002  
**Parent Documents:** Document 01 v1.1; Document 02 v1.0  
**Primary Dependencies:** Documents 03–10; Temporal; Material/QC/Equipment/QMS specs  
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

Define runtime manufacturing execution from batch creation through production completion and QA handoff.

The module is the central transactional engine for eBMR and is also reused for eDHR/unit-level device execution.

# 2. Architecture

```text
Operator / Device / Integration
         ↓
    Mutation Gateway
         ↓
Batch Domain Service  ←→ Temporal Orchestrator
         ↓
PostgreSQL authoritative state
├ Batch
├ Step Instances
├ Parameter Results
├ Material/Equipment Links
├ Exceptions
├ Audit
└ Outbox
```

Temporal manages orchestration; PostgreSQL controls authoritative batch state.

# 3. Batch State Machine

```text
PLANNED
  ↓ create
CREATED
  ↓ snapshot locked
ISSUED
  ↓ prerequisites ready
READY
  ↓ start
IN_EXECUTION
  ├─→ ON_HOLD
  ├─→ EXCEPTION_PENDING
  └─→ IN_EXECUTION
  ↓
PRODUCTION_COMPLETE
  ↓
QA_REVIEW
  ├─→ CONTROLLED_ACTION_REQUIRED
  └─→ RELEASE / REJECT / OTHER DISPOSITION
  ↓
CLOSED
```

# 4. Step State Machine

```text
NOT_READY
  ↓ dependencies satisfied
READY
  ↓ claim/start
IN_PROGRESS
  ├─→ PAUSED
  ├─→ EXCEPTION
  └─→ COMPLETED
        ↓ correction
      SUPERSEDED_BY_CORRECTION
```

Additional:
`NOT_APPLICABLE`, `VOIDED_CONTROLLED`.

# 5. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| BAT-FR-001 | Batch creation | Create batch from effective product + recipe version, site, target quantity and allowed production order/reference. | Batch source fully attributable. |
| BAT-FR-002 | Unique identity | Assign immutable batch ID plus controlled human batch number. Prevent duplicate/reused business numbers by tenant/site policy. | Unique batch traceability. |
| BAT-FR-003 | Issue snapshot | At issue, create immutable execution snapshot from exact released dependencies. | Open batch immune to later master changes. |
| BAT-FR-004 | Batch lifecycle | Authoritative states: Planned, Created/Snapshot Locked, Issued, Ready, In Execution, On Hold, Exception Pending, Production Complete, QA Review, Released/Rejected/Other Disposition, Closed. | State machine explicit. |
| BAT-FR-005 | Step instance creation | Instantiate executable step instances from snapshot with stable recipe step reference and batch-specific state. | Execution has immutable parent instruction. |
| BAT-FR-006 | Step readiness | Compute readiness from predecessors, conditions, material/equipment/personnel requirements, holds and quality blockers. | UI cannot force readiness. |
| BAT-FR-007 | Step claim/start | Authorized operator may claim/start ready step; record operator, area, equipment context and start time. | Who/where/when captured. |
| BAT-FR-008 | Concurrent execution | Support parallel independent steps with version/concurrency protection and explicit join conditions. | No cross-step overwrite. |
| BAT-FR-009 | Parameter capture | Capture typed value, UOM, source, source timestamp, receive time, actor/device, quality status and applicable rule result. | Complete evidence. |
| BAT-FR-010 | Manual entry | Manual result records actor, reason/source and verification policy; replacing unavailable automated input requires allowed fallback path. | Manual substitution visible. |
| BAT-FR-011 | Device/Edge result | Accept registered device data with source identity, sequence/idempotency, mapping version and data-quality status. | Machine evidence attributable. |
| BAT-FR-012 | Material consume | Step invokes Material Service eligibility/reservation/dispensing/consumption command; genealogy relationship committed. | Batch knows exact material lots/containers. |
| BAT-FR-013 | Equipment use | Verify equipment eligibility at start and relevant completion; capture actual equipment IDs. | Equipment history exact. |
| BAT-FR-014 | Qualification gate | Verify performer/verifier training/qualification at action time. | Unqualified action blocked. |
| BAT-FR-015 | Step validation | Before completion validate required parameters, evidence, calculations, QC requirements, materials and signatures. | Incomplete step cannot complete. |
| BAT-FR-016 | Step signature | When required, completion/verification consumes Document 04 signature bound to exact step/result version. | Signature exact. |
| BAT-FR-017 | Independent verification | Support second-person verification with SoD and exact values/evidence being verified. | Checker knows what was checked. |
| BAT-FR-018 | Timer | Start/stop/measure controlled durations; time-limit breach generates configured exception/hold. | Hold time enforced. |
| BAT-FR-019 | Pause/resume | Pause reason/status retained; resume revalidates relevant resources if policy requires. | Long interruptions safe. |
| BAT-FR-020 | Batch hold | Authorized command holds whole batch or scoped stage/step; reason/signature and source quality event captured. | No execution past hold. |
| BAT-FR-021 | Exception generation | Out-of-limit, missing/invalid evidence, timeout, material/equipment/qualification failure or manual override generates linked exception according to rule. | Deviation not optional. |
| BAT-FR-022 | Conditional branch | Evaluate released branch rule and activate exact downstream path; unselected path marked Not Applicable with reason/reference. | Record explains path. |
| BAT-FR-023 | Step correction | Completed step data correction uses controlled correction workflow preserving original, reason, impact and signatures. | No edit-in-place. |
| BAT-FR-024 | Rework/reprocess | Only released rework/reprocess route can be instantiated after authorized disposition; history links original and new route. | No improvised rework. |
| BAT-FR-025 | Shift handover | Support controlled operator handover without changing prior attribution; active step may require pause/checklist/signature. | Continuity maintained. |
| BAT-FR-026 | Production completion | Batch can become Production Complete only when all required applicable steps, yields/reconciliations and production blockers are resolved. | Completeness deterministic. |
| BAT-FR-027 | QA review handoff | Create review snapshot/index and lock production inputs except controlled correction/action path. | QA reviews stable evidence. |
| BAT-FR-028 | Temporal orchestration | Use Temporal for waits/timers/retries/parallel orchestration; authoritative state remains PostgreSQL. | Workflow engine not record truth. |
| BAT-FR-029 | Restart/recovery | Worker/application restart resumes from authoritative batch/Temporal state without duplicate regulated actions. | Resilient long-running batch. |
| BAT-FR-030 | Integration outage | ERP/LIMS/Edge outage follows profile rules: buffer/pending/hold; never fabricate completion/pass. | Fail safe. |
| BAT-FR-031 | Batch abort/cancel | Controlled abort/void retains all data, reason, status, material/equipment impact and disposition requirement. | No deletion. |
| BAT-FR-032 | Unit/serial scope | Steps may execute at batch/lot/unit/serial/subassembly scope depending on profile. | Device/DDCP reuse. |
| BAT-FR-033 | Late data | Late device/LIMS data is accepted only through defined rule with source timestamp and batch-state impact; cannot silently alter released decision. | Late evidence controlled. |
| BAT-FR-034 | Execution comments | Structured comments/notes may be added with author/time; corrections to comments preserve history if regulated. | Communication auditable. |
| BAT-FR-035 | Production dashboard | Show active batches, current step, holds, exceptions, timers and resource blockers without exposing unauthorized data. | Operational visibility. |
| BAT-FR-036 | Batch export readiness | At any time, system can produce current structured record; final inspection export after release comes from authoritative records. | No hidden spreadsheet reconstruction. |

# 6. Data Model

## `gxp_batch`

```text
id uuid PK
tenant_id uuid
site_id uuid
batch_number varchar(120)
product_version_id uuid
recipe_vault_object_id uuid
execution_snapshot_id uuid
target_qty numeric(24,8)
target_uom varchar(40)
state varchar(50)
version bigint NOT NULL
production_order_ref varchar(160)
created_at timestamptz
issued_at timestamptz
started_at timestamptz
production_completed_at timestamptz
qa_review_started_at timestamptz
closed_at timestamptz
```

Unique `(tenant_id, batch_number)` or site-scoped configurable sequence.

## `gxp_batch_step`

```text
id uuid PK
batch_id uuid
recipe_step_code varchar(120)
scope_type varchar(40)
scope_id uuid
state varchar(40)
version bigint
assigned_subject_id uuid
started_at timestamptz
completed_at timestamptz
branch_status varchar(40)
exception_state varchar(40)
temporal_workflow_ref varchar(255)
```

## `gxp_step_result`
- step_id
- parameter_code
- result_version
- value_decimal/text/bool/json
- uom
- source_type
- source_id
- source_timestamp
- received_at
- data_quality
- rule_evaluation_id
- created_by
- supersedes_result_id

## `gxp_step_evidence_link`
- step
- evidence ID/version/hash
- requirement code

## `gxp_batch_hold`
- scope
- reason
- quality event
- started/ended
- signatures

# 7. Commands / APIs

- `POST /batches/v1`
- `POST /batches/{id}/issue`
- `POST /batches/{id}/start`
- `POST /batches/{id}/hold`
- `POST /batches/{id}/resume`
- `POST /batches/{id}/steps/{stepId}/start`
- `POST /batches/{id}/steps/{stepId}/results`
- `POST /batches/{id}/steps/{stepId}/complete`
- `POST /batches/{id}/steps/{stepId}/verify`
- `POST /batches/{id}/steps/{stepId}/correct`
- `POST /batches/{id}/production-complete`
- `POST /batches/{id}/abort`
- `GET /batches/{id}`
- `GET /batches/{id}/execution-view`
- `GET /batches/{id}/blockers`

All mutation operations use Document 03 command envelope.

Errors:
`BATCH_NOT_ISSUABLE`, `STEP_NOT_READY`, `STEP_ALREADY_COMPLETED`, `DEPENDENCY_INCOMPLETE`, `BATCH_ON_HOLD`, `PARAMETER_REQUIRED`, `VALUE_OUT_OF_RANGE`, `EQUIPMENT_INELIGIBLE`, `MATERIAL_INELIGIBLE`, `QUALIFICATION_REQUIRED`, `VERIFIER_SOD_CONFLICT`, `TIMER_LIMIT_EXCEEDED`, `PRODUCTION_NOT_COMPLETE`.

# 8. Temporal Workflows

Recommended:
- one workflow per batch;
- child workflows only for very large/unit-level scopes where justified;
- Activities call GxP APIs;
- timers handle hold times/escalations;
- workflow IDs include tenant/site/batch ID;
- workflow payload contains identifiers, not full sensitive record.

# 9. Execution UI

Operator UI:
- batch header;
- current section/step;
- instruction;
- required materials/equipment;
- input controls;
- scanner/balance/device status;
- target/limits;
- evidence;
- timer;
- verifier/signature;
- hold/exception;
- next permitted action.

Supervisor:
- all active batches;
- bottlenecks;
- holds;
- exceptions;
- overdue timers;
- operator assignments.

# 10. Concurrency

- batch/step version required for mutation;
- step start uses conditional update;
- duplicate scan/device events idempotent;
- material reservations managed externally but linked;
- two verifiers cannot consume same signature requirement twice;
- branch activation transactionally marks other path N/A.

# 11. Failure/Recovery

| Failure | Behavior |
|---|---|
| Browser closes | Authoritative step remains; reopen from server state |
| Frappe restart | Batch state persists |
| Temporal worker restart | Workflow replay/resume |
| PostgreSQL unavailable | Regulated mutation stops |
| Edge unavailable | Automated source pending; fallback only if released rule permits |
| LIMS unavailable | QC-dependent continuation/release blocks |
| ERP unavailable | Material/inventory behavior follows defined local-authority rules |
| Signature unavailable | Signed action cannot complete |

# 12. Events

- BatchCreated
- BatchIssued
- BatchStarted
- BatchHeld
- BatchResumed
- StepReady
- StepStarted
- StepResultRecorded
- StepCompleted
- StepVerified
- StepExceptionRaised
- StepCorrected
- BranchSelected
- ProductionCompleted
- BatchAborted
- QAReviewRequested

# 13. Audit

Every state/result change references:
- actor/source;
- version;
- old/new;
- reason;
- signature;
- rule evaluation;
- material/equipment/evidence references.

# 14. Repository Structure

```text
services/gxp-api/src/modules/batch/
services/gxp-api/src/modules/execution/
services/workers/src/workflows/batch/
apps/ebmr_frappe/ebmr/execution/
contracts/events/batch/
validation/requirements/execution/
```

# 15. Implementation Sequence

1. batch aggregate/state;
2. issue snapshot;
3. step instances/readiness;
4. result capture;
5. completion;
6. signature/verifier;
7. holds/exceptions;
8. branches/parallel;
9. timers/Temporal;
10. material/equipment/QC adapters;
11. correction/rework;
12. production completion.

# 16. Test Catalogue

At minimum:
- sequential normal batch;
- parallel steps;
- conditional branch;
- duplicate step start;
- simultaneous result edits;
- stale version;
- browser refresh;
- worker crash;
- event-bus outage;
- material failure;
- calibration expiration mid-batch;
- qualification expiration before next step;
- manual fallback;
- device duplicate/replay;
- hold/resume;
- timer breach;
- correction;
- rework route;
- abort;
- production completion blocker;
- unit/serial scope.

# 17. Acceptance

The engine is implementation-complete only if a representative injectable DDCP batch can run end-to-end with:
product/recipe snapshot, materials, device component genealogy, equipment, parameters, QC hold, exception, signature, production completion and QA handoff.

# 18. Codex / Claude Rules

Never store authoritative execution state only in Temporal.
Never let UI mark a step completed without server validation.
Never edit completed result in place.
Never hide a failed/out-of-limit value by replacing it with retest.
Never let retry create duplicate consumption or signatures.

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
