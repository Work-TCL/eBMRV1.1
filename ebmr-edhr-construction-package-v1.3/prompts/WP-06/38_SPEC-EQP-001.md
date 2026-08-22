# Claude Code prompt — WP-06 / Document 38: Equipment, Calibration, Qualification & Maintenance

TASK:
Implement the Equipment, Calibration, Qualification & Maintenance module (SPEC-EQP-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_38_Equipment_Calibration_Qualification_Maintenance_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: EQP-FR-001..030 (30)
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
contracts/openapi/spec-eqp-001.yaml
contracts/events/spec-eqp-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-eqp-001/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
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

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (4 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `equipment_asset` | 16 | PostgreSQL (GxP Core, authoritative) |
| `equipment_calibration` | 8 | PostgreSQL (GxP Core, authoritative) |
| `maintenance_work_order` | 6 | PostgreSQL (GxP Core, authoritative) |
| `equipment_use_log` | 6 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (9):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /equipment/v1/assets` | yes | — |
| `POST /equipment/v1/{id}/qualifications` | yes | — |
| `POST /equipment/v1/{id}/calibrations` | yes | — |
| `POST /equipment/v1/{id}/maintenance` | yes | — |
| `POST /equipment/v1/{id}/hold` | yes | — |
| `POST /equipment/v1/{id}/return-to-service` | yes | — |
| `GET /equipment/v1/{id}/eligibility` | no | — |
| `GET /equipment/v1/{id}/history` | no | — |
| `GET /equipment/v1/dashboard` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (10):
| Event type | Producer | Dedupe key |
|---|---|---|
| `EquipmentInstalled` | SPEC-EQP-001 | event_id |
| `EquipmentQualified` | SPEC-EQP-001 | event_id |
| `CalibrationDue` | SPEC-EQP-001 | event_id |
| `EquipmentCalibrated` | SPEC-EQP-001 | event_id |
| `CalibrationOutOfTolerance` | SPEC-EQP-001 | event_id |
| `MaintenanceDue` | SPEC-EQP-001 | event_id |
| `EquipmentOutOfService` | SPEC-EQP-001 | event_id |
| `MaintenanceCompleted` | SPEC-EQP-001 | event_id |
| `EquipmentReturnedToService` | SPEC-EQP-001 | event_id |
| `EquipmentRetired` | SPEC-EQP-001 | event_id |

UI SURFACES:
- Equipment Catalogue
- Asset Detail
- Qualification
- Calibration Plan/Execution
- Maintenance Work Orders
- Use Log
- Firmware/Configuration
- Eligibility
- Due Dashboard
- History/Export

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
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-06/Document_38_SPEC-EQP-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EQP-001/<test_case_id>/`.
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
