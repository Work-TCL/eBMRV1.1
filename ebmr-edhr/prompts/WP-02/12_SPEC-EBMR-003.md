# Claude Code prompt — WP-02 / Document 12: eDHR / Device Production History Specification

TASK:
Implement the eDHR / Device Production History Specification module (SPEC-EBMR-003) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_12_eDHR_Device_Production_History_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: DHR-FR-001..030 (30)
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
contracts/openapi/spec-ebmr-003.yaml
contracts/events/spec-ebmr-003/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-ebmr-003/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| DHR-FR-001 | Device production record | Create complete lot/unit/serial production history derived from released product/recipe snapshot. | Device history reproducible. |
| DHR-FR-002 | Scope level | Support lot-level, serial-level, subassembly-level and inherited batch-level evidence. | High-volume execution configurable. |
| DHR-FR-003 | Serial generation/import | Generate or accept controlled serials with uniqueness, source and reservation rules. | No duplicate device identity. |
| DHR-FR-004 | UDI record | Store applicable DI/PI/UDI components, packaging level and source; link to unit/lot/batch history. | Current QMSR/UDI record support. |
| DHR-FR-005 | Component genealogy | Record exact device component lots/serials/subassemblies assembled into final device. | Backward/forward traceability. |
| DHR-FR-006 | Drug constituent linkage | For DDCP, link exact drug batch/lot/container/fill group to device unit/lot/combination product. | Integrated history. |
| DHR-FR-007 | Assembly step | Capture assembly station/equipment, operator/device source, time, parameters and component relationships. | Assembly evidence attributable. |
| DHR-FR-008 | Test result | Capture functional/electrical/mechanical/dose-delivery/visual or other structured test result with test specification/version. | Acceptance evidence exact. |
| DHR-FR-009 | Automated tester | Accept instrument result through Edge with source identity, mapping version, raw evidence reference and pass/fail rule. | Machine result attributable. |
| DHR-FR-010 | Manual inspection | Capture inspector, method, criteria, result, defect code and optional image/evidence. | Manual acceptance controlled. |
| DHR-FR-011 | Nonconformance | Failed component/unit/test creates linked NCR/exception and controls disposition. | Failure not overwritten. |
| DHR-FR-012 | Rework | Rework uses approved route and maintains original + reworked history, reason and approvals. | Rework traceable. |
| DHR-FR-013 | Scrap | Unit/component scrap records quantity/identity, reason, authority and genealogy impact. | Scrapped unit cannot release. |
| DHR-FR-014 | Acceptance status | Unit/lot status progresses through controlled states: In Process, Hold, Rework, Accepted, Rejected/Scrapped, Released. | Status rule driven. |
| DHR-FR-015 | Label/packaging link | Record exact label/UDI/packaging configuration used for device/lot/unit. | Packaging evidence linked. |
| DHR-FR-016 | Sterilization link | Where applicable link unit/lot to sterilization load/cycle and release status. | Sterilization eligibility visible. |
| DHR-FR-017 | Environmental/area link | Where required retain relevant production area/environmental evidence references. | Critical conditions linked. |
| DHR-FR-018 | Process validation reference | Step/equipment/process may reference applicable validated process version/status. | Production history supports validation linkage. |
| DHR-FR-019 | Calibration/test-equipment eligibility | Tester/equipment must be eligible when used; actual equipment ID stored. | Invalid tester blocks. |
| DHR-FR-020 | Production specification snapshot | Device history binds exact released specification/instructions/configuration. | No current-master drift. |
| DHR-FR-021 | Device record completeness | Before acceptance/release, evaluate required steps, components, tests, labels, signatures and unresolved NCRs. | Incomplete unit cannot release. |
| DHR-FR-022 | Bulk inheritance | Evidence common to many units may be inherited from batch/lot with immutable reference to avoid duplication. | Scale without semantic loss. |
| DHR-FR-023 | Override | Any unit-specific override/manual replacement requires released policy, reason, authorization and audit. | No hidden exception. |
| DHR-FR-024 | Unit split/merge | Support controlled subassembly transformation relationships; final unit genealogy remains acyclic/traceable. | Assembly graph consistent. |
| DHR-FR-025 | Repair during manufacturing | Distinguish manufacturing rework/repair from postmarket service; apply appropriate controlled route. | Semantics clear. |
| DHR-FR-026 | Device release package | Generate unit/lot history package with identifiers, components, process, tests, signatures, exceptions, labels and genealogy. | Inspection/customer evidence ready. |
| DHR-FR-027 | Search | Lookup by serial, UDI, lot, batch, component lot, drug batch, tester, defect code. | Fast investigation. |
| DHR-FR-028 | High-volume serial execution | Support bulk creation/result ingestion with controlled grouping while preserving unit exceptions. | Scales to many serials. |
| DHR-FR-029 | Record correction | Corrections use Vault/audit model and never rewrite original device history. | History preserved. |
| DHR-FR-030 | QMSR terminology | Product may expose customer-facing alias 'eDHR', but compliance mapping is maintained against current QMSR/ISO 13485 record/production controls rather than relying on obsolete clause numbering. | Current regulatory framing. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (5 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `device_unit` | 13 | PostgreSQL (GxP Core, authoritative) |
| `device_component_usage` | 7 | PostgreSQL (GxP Core, authoritative) |
| `device_test_result` | 9 | PostgreSQL (GxP Core, authoritative) |
| `device_defect` | 4 | PostgreSQL (GxP Core, authoritative) |
| `device_evidence_inheritance` | 4 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (11):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /devices/v1/lots` | yes | — |
| `POST /devices/v1/units/bulk-create` | yes | — |
| `POST /devices/v1/units/{id}/components` | yes | — |
| `POST /devices/v1/units/{id}/tests` | yes | — |
| `POST /devices/v1/units/{id}/inspection` | yes | — |
| `POST /devices/v1/units/{id}/hold` | yes | — |
| `POST /devices/v1/units/{id}/rework` | yes | — |
| `POST /devices/v1/units/{id}/accept` | yes | — |
| `GET /devices/v1/units/by-serial/{serial}` | no | — |
| `GET /devices/v1/units/{id}/history` | no | — |
| `GET /devices/v1/lots/{id}/release-readiness` | no | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (9):
| Event type | Producer | Dedupe key |
|---|---|---|
| `DeviceUnitCreated` | SPEC-EBMR-003 | event_id |
| `ComponentAssembled` | SPEC-EBMR-003 | event_id |
| `DeviceTestRecorded` | SPEC-EBMR-003 | event_id |
| `DeviceInspectionRecorded` | SPEC-EBMR-003 | event_id |
| `DeviceNonconformanceRaised` | SPEC-EBMR-003 | event_id |
| `DeviceReworkStarted` | SPEC-EBMR-003 | event_id |
| `DeviceAccepted` | SPEC-EBMR-003 | event_id |
| `DeviceScrapped` | SPEC-EBMR-003 | event_id |
| `DeviceReleased` | SPEC-EBMR-003 | event_id |

UI SURFACES:
- Device Lot Dashboard
- Serial/Unit Search
- Assembly Execution
- Test Station View
- Inspection View
- NCR/Rework
- Unit History
- UDI/Label
- Release Readiness
- Device History Export

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
Fail closed on any compliance-critical dependency outage; no degraded-mode commit.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- unit/lot scope
- test specification version
- test code
- tester equipment ID
- result values
- pass/fail
- raw evidence reference
- rule evaluation
- result version/supersession
- unit creation
- duplicate serial
- component lot trace
- wrong component
- tester calibration invalid
- failed test → NCR
- retest retains original
- rework
- scrap
- shared evidence inheritance
- UDI recording
- batch-to-unit drug linkage
- high-volume bulk results
- unit correction
- device export
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-02/Document_12_SPEC-EBMR-003_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EBMR-003/<test_case_id>/`.
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
