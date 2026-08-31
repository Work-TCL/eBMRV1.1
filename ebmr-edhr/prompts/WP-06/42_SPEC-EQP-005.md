# Claude Code prompt — WP-06 / Document 42: Sterilization, CIP/SIP & Sterile Filtration Management

TASK:
Implement the Sterilization, CIP/SIP & Sterile Filtration Management module (SPEC-EQP-005) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_42_Sterilization_CIP_SIP_Sterile_Filtration_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: STR-FR-001..030 (30)
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
contracts/openapi/spec-eqp-005.yaml
contracts/events/spec-eqp-005/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-eqp-005/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
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

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (4 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `process_cycle_profile_version` | 9 | PostgreSQL (GxP Core, authoritative) |
| `process_cycle` | 14 | PostgreSQL (GxP Core, authoritative) |
| `sterilization_load_item` | 4 | PostgreSQL (GxP Core, authoritative) |
| `sterile_filter_use` | 6 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (9):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /sterilization/v1/cycles` | yes | — |
| `POST /sterilization/v1/cycles/{id}/start` | yes | — |
| `POST /sterilization/v1/cycles/{id}/data` | yes | — |
| `POST /sterilization/v1/cycles/{id}/review` | yes | — |
| `POST /cip-sip/v1/cycles` | yes | — |
| `POST /filtration/v1/filters/install` | yes | — |
| `POST /filtration/v1/filters/{id}/integrity-tests` | yes | — |
| `POST /filtration/v1/uses/{id}/complete` | yes | — |
| `GET /sterilization/v1/items/{id}/status` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (10):
| Event type | Producer | Dedupe key |
|---|---|---|
| `SterilizationCycleStarted` | SPEC-EQP-005 | event_id |
| `SterilizationCycleCompleted` | SPEC-EQP-005 | event_id |
| `SterilizationCycleFailed` | SPEC-EQP-005 | event_id |
| `SterilizationCycleAccepted` | SPEC-EQP-005 | event_id |
| `SIPStatusIssued` | SPEC-EQP-005 | event_id |
| `CIPCompleted` | SPEC-EQP-005 | event_id |
| `FilterInstalled` | SPEC-EQP-005 | event_id |
| `FilterIntegrityPassed` | SPEC-EQP-005 | event_id |
| `FilterIntegrityFailed` | SPEC-EQP-005 | event_id |
| `SterileStatusExpired` | SPEC-EQP-005 | event_id |

UI SURFACES:
- Cycle Profiles
- Load Builder
- Cycle Execution/Monitor
- Cycle Review
- Indicators
- CIP/SIP
- Filter Inventory/Installation
- Integrity Testing
- Sterile Status
- Batch/Genealogy Summary

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
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-06/Document_42_SPEC-EQP-005_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EQP-005/<test_case_id>/`.
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
