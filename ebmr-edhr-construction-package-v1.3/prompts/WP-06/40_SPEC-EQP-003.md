# Claude Code prompt — WP-06 / Document 40: Sterile / Aseptic Manufacturing Operations

TASK:
Implement the Sterile / Aseptic Manufacturing Operations module (SPEC-EQP-003) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_40_Sterile_Aseptic_Manufacturing_Operations_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: ASP-FR-001..028 (28)
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
contracts/openapi/spec-eqp-003.yaml
contracts/events/spec-eqp-003/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-eqp-003/
```

REQUIREMENTS TO IMPLEMENT (28):
| ID | Requirement | Required behaviour | Acceptance intent |
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

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (4 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `aseptic_profile_version` | 7 | PostgreSQL (GxP Core, authoritative) |
| `aseptic_operation` | 9 | PostgreSQL (GxP Core, authoritative) |
| `aseptic_intervention` | 9 | PostgreSQL (GxP Core, authoritative) |
| `aseptic_event_timeline` | 5 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (7):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /aseptic/v1/operations` | yes | — |
| `POST /aseptic/v1/operations/{id}/start` | yes | — |
| `POST /aseptic/v1/operations/{id}/interventions` | yes | — |
| `POST /aseptic/v1/operations/{id}/events` | yes | — |
| `POST /aseptic/v1/operations/{id}/complete` | yes | — |
| `GET /aseptic/v1/operations/{id}/readiness` | no | — |
| `GET /aseptic/v1/operations/{id}/review-summary` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (7):
| Event type | Producer | Dedupe key |
|---|---|---|
| `AsepticOperationStarted` | SPEC-EQP-003 | event_id |
| `AsepticInterventionRecorded` | SPEC-EQP-003 | event_id |
| `UnplannedInterventionDetected` | SPEC-EQP-003 | event_id |
| `AsepticHoldTimeExceeded` | SPEC-EQP-003 | event_id |
| `AsepticEnvironmentExcursionDetected` | SPEC-EQP-003 | event_id |
| `AsepticOperationHeld` | SPEC-EQP-003 | event_id |
| `AsepticOperationCompleted` | SPEC-EQP-003 | event_id |

UI SURFACES:
- Aseptic Readiness
- Area/Personnel Status
- Sterile Inputs
- Aseptic Setup
- Live Operation
- Interventions
- Hold-Time Timeline
- Environment/Alarms
- Completion
- QA Summary

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
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-06/Document_40_SPEC-EQP-003_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EQP-003/<test_case_id>/`.
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
