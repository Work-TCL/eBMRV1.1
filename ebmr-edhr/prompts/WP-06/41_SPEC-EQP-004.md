# Claude Code prompt — WP-06 / Document 41: Environmental Monitoring & Cleanroom State Control

TASK:
Implement the Environmental Monitoring & Cleanroom State Control module (SPEC-EQP-004) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_41_Environmental_Monitoring_Cleanroom_State_Control_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: EM-FR-001..026 (26)
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
- `services/gxp-api/src/modules/equipment` and its tests
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
services/gxp-api/src/modules/equipment/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/equipment/migrations/     # owned entities only
services/gxp-api/src/modules/equipment/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-eqp-004.yaml
contracts/events/spec-eqp-004/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-eqp-004/
```

REQUIREMENTS TO IMPLEMENT (26):
| ID | Requirement | Required behaviour | Acceptance intent |
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

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (4 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `em_program_version` | 9 | PostgreSQL (GxP Core, authoritative) |
| `em_location` | 5 | PostgreSQL (GxP Core, authoritative) |
| `em_sample_or_reading` | 11 | PostgreSQL (GxP Core, authoritative) |
| `em_excursion` | 4 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (8):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /em/v1/programs` | yes | — |
| `POST /em/v1/tasks` | yes | — |
| `POST /em/v1/tasks/{id}/collect` | yes | — |
| `POST /em/v1/results` | yes | — |
| `POST /em/v1/results/{id}/review` | yes | — |
| `POST /em/v1/excursions/{id}/impact` | yes | — |
| `GET /em/v1/areas/{id}/readiness` | no | — |
| `GET /em/v1/trends` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (8):
| Event type | Producer | Dedupe key |
|---|---|---|
| `EMTaskScheduled` | SPEC-EQP-004 | event_id |
| `EMSampleCollected` | SPEC-EQP-004 | event_id |
| `EMResultRecorded` | SPEC-EQP-004 | event_id |
| `EMAlertTriggered` | SPEC-EQP-004 | event_id |
| `EMActionLimitExceeded` | SPEC-EQP-004 | event_id |
| `EMDataGapDetected` | SPEC-EQP-004 | event_id |
| `EMAreaHeld` | SPEC-EQP-004 | event_id |
| `EMExcursionClosed` | SPEC-EQP-004 | event_id |

UI SURFACES:
- EM Program
- Monitoring Locations
- Sampling Schedule
- EM Collection
- Continuous Monitoring
- Result Review
- Excursions
- Organism Identification
- Area Readiness
- Trend Dashboard
- Batch Correlation

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- PostgreSQL unavailable: no regulated state transition.
- Edge/device unavailable: behavior follows released fallback policy; no fabricated reading/result.
- Calibration/qualification status cannot be assumed when source unavailable.
- Worker restart resumes scheduled maintenance/calibration/EM/sterilization jobs from persisted state.
- Event-bus outage uses outbox retry.
- Stale versions are rejected.
- Failed critical integrity checks generate Quality/Security event and relevant equipment/process hold.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
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
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-06/Document_41_SPEC-EQP-004_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EQP-004/<test_case_id>/`.
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
