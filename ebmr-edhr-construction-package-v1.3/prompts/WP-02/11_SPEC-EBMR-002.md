# Claude Code prompt — WP-02 / Document 11: Batch Execution Engine & State Machine Specification

TASK:
Implement the Batch Execution Engine & State Machine Specification module (SPEC-EBMR-002) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_11_Batch_Execution_Engine_State_Machine_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: BAT-FR-001..036 (36)
- Approved baselines: Document 106 (signature policy), 107 (SoD), 108 (retention), 109 (SLO/RPO),
  110 (precision/UOM), 111 (risk class), 112 (schemas/migrations), 113 (contracts), 114 (glossary)
- Phase-0 artefacts: `docs/generated/03_FUNCTION_CATALOGUE.csv`, `04_DATA_MODEL_CATALOGUE.md`,
  `05_DATABASE_OWNERSHIP_MATRIX.md`, `06_API_CATALOGUE.yaml`, `07_EVENT_CATALOGUE.yaml`,
  `14_ERROR_CODE_REGISTRY.md`, `28_INTENDED_USE_GXP_RISK_MATRIX.md`

RISK CLASS: **HIGHER-PROCESS-RISK** → scripted tests, independent review, mandatory negative and failure evidence

ARCHITECTURE CONSTRAINTS:
- Frappe is UI/configuration only; no core fork or edit.
- PostgreSQL is authoritative for regulated state; MariaDB holds read-only projections.
- Every regulated write goes through the Mutation Gateway → one PostgreSQL transaction carrying
  domain state + record version + audit event + outbox event.
- Signatures follow Document 04 + the approved Document 106 policy; login/MFA is never a signature.
- Audit, vault and evidence history is append-only and superseding.
- Outbox is the authoritative event source; NATS is transport; Temporal is orchestration only.
- Caches, projections, search and reports are rebuildable and never a regulated decision source.
- Adapters and edge never write GxP tables; they submit integration commands.
- AI is advisory; it cannot sign, release, disposition, approve, alter audit or submit reports.

PRECONDITIONS:
- WP-00 foundations exist (contracts tooling, guardrails, CI gates).
- WP-01 GxP Core is available (mutation, policy, signature, audit, vault, rules).
- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `services/gxp-api/src/modules/ebmr` and its tests
- `contracts/` entries owned by this module
- migrations for entities owned by this module
- Frappe UI surfaces for this module in `apps/ebmr_frappe/`

DO NOT:
- Do not modify anything under `specs/`.
- Do not implement a signature requirement not present in the approved Document 106 policy set
  (emit a policy row and reference the gap instead).
- Do not create a second authoritative store for an entity owned elsewhere.
- Do not add an endpoint to a module whose exposure boundary is "no independent API" (Document 113 §6).
- Do not write a migration for an entity absent from `docs/generated/04_DATA_MODEL_CATALOGUE.md`.
- Do not use binary floating point for a regulated quantity.
- Do not fabricate a test run, scan result or qualification record.
- Do not start work in another work package.

FILES TO CREATE/MODIFY:
```text
services/gxp-api/src/modules/ebmr/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/ebmr/migrations/     # owned entities only
services/gxp-api/src/modules/ebmr/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-ebmr-002.yaml
contracts/events/spec-ebmr-002/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-ebmr-002/
```

REQUIREMENTS TO IMPLEMENT (36):
| ID | Requirement | Required behaviour | Acceptance intent |
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

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (5 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `gxp_batch` | 18 | PostgreSQL (GxP Core, authoritative) |
| `gxp_batch_step` | 13 | PostgreSQL (GxP Core, authoritative) |
| `gxp_step_result` | 13 | PostgreSQL (GxP Core, authoritative) |
| `gxp_step_evidence_link` | 3 | PostgreSQL (GxP Core, authoritative) |
| `gxp_batch_hold` | 5 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (15):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /batches/v1` | yes | — |
| `POST /batches/{id}/issue` | yes | — |
| `POST /batches/{id}/start` | yes | — |
| `POST /batches/{id}/hold` | yes | — |
| `POST /batches/{id}/resume` | yes | — |
| `POST /batches/{id}/steps/{stepId}/start` | yes | — |
| `POST /batches/{id}/steps/{stepId}/results` | yes | — |
| `POST /batches/{id}/steps/{stepId}/complete` | yes | — |
| `POST /batches/{id}/steps/{stepId}/verify` | yes | policy lookup (Doc 106) |
| `POST /batches/{id}/steps/{stepId}/correct` | yes | — |
| `POST /batches/{id}/production-complete` | yes | — |
| `POST /batches/{id}/abort` | yes | — |
| `GET /batches/{id}` | no | — |
| `GET /batches/{id}/execution-view` | no | — |
| `GET /batches/{id}/blockers` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (16):
| Event type | Producer | Dedupe key |
|---|---|---|
| `BatchCreated` | SPEC-EBMR-002 | event_id |
| `BatchIssued` | SPEC-EBMR-002 | event_id |
| `BatchStarted` | SPEC-EBMR-002 | event_id |
| `BatchHeld` | SPEC-EBMR-002 | event_id |
| `BatchResumed` | SPEC-EBMR-002 | event_id |
| `StepReady` | SPEC-EBMR-002 | event_id |
| `StepStarted` | SPEC-EBMR-002 | event_id |
| `StepResultRecorded` | SPEC-EBMR-002 | event_id |
| `StepCompleted` | SPEC-EBMR-002 | event_id |
| `StepVerified` | SPEC-EBMR-002 | event_id |
| `StepExceptionRaised` | SPEC-EBMR-002 | event_id |
| `StepCorrected` | SPEC-EBMR-002 | event_id |
| `BranchSelected` | SPEC-EBMR-002 | event_id |
| `ProductionCompleted` | SPEC-EBMR-002 | event_id |
| `BatchAborted` | SPEC-EBMR-002 | event_id |
| `QAReviewRequested` | SPEC-EBMR-002 | event_id |

UI SURFACES:
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
- all active batches;
- bottlenecks;
- holds;
- exceptions;
- overdue timers;
- operator assignments.

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
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

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- sequential normal batch
- parallel steps
- conditional branch
- duplicate step start
- simultaneous result edits
- stale version
- browser refresh
- worker crash
- event-bus outage
- material failure
- calibration expiration mid-batch
- qualification expiration before next step
- manual fallback
- device duplicate/replay
- hold/resume
- timer breach
- correction
- rework route
- abort
- production completion blocker
- unit/serial scope
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-02/Document_11_SPEC-EBMR-002_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EBMR-002/<test_case_id>/`.
- A failed case is evidence: never delete it, re-run over it, or edit the expected result to make it pass.
  Raise a defect, record the reference, re-execute as a new dated execution.

TRACEABILITY & STATUS (mandatory at the end of this prompt):
- Update `traceability/TRACEABILITY_MASTER.csv` for every requirement you touched: `build_stage`,
  `verification_state`, `test_case_ids`, `evidence_location`.
- Update `status/build-status.json`: set this module's `stage`, append to `stage_history`, set
  `requirements_state` per requirement, and set `test_pass` / `test_fail` / `test_blocked` from the
  actual recorded results.
- You may only set stages you can evidence, up to and including CODE_COMPLETE and the test states.
  `REVIEWED`, `OQ_EXECUTED`, `QUALIFIED` and `RELEASED` are set by humans, never by you.
- Run `python tooling/status/rollup.py` and include the printed summary in your completion report.

VALIDATION / TRACEABILITY:
- update `docs/generated/15_TEST_TRACEABILITY_MATRIX.csv` and `29_VALIDATION_TRACEABILITY_MASTER.csv`
- state IQ/OQ/PQ impact; HIGHER-PROCESS-RISK functions need retained objective evidence
- Part 11 impact where signatures are involved (Document 88)

ACCEPTANCE CRITERIA:
- every requirement above implemented, traced and tested
- all listed tests executed with real results
- no architecture guardrail violation
- contracts committed before implementation and compatible

SPEC_GAP RULE:
Do not guess regulated behaviour. Append unresolved decisions to `docs/generated/18_SPEC_GAPS.md`
with affected requirements, risk, options and blocking status, then continue only on unaffected work.

BEFORE COMPLETION:
Run lint, typecheck, unit, contract, integration and guardrail checks. Report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; **test cases executed with PASS/FAIL/BLOCKED counts and
the case ids of every failure**; validation impact; **traceability and status files updated (include the
rollup summary)**; unresolved SPEC_GAPs; known limitations.
