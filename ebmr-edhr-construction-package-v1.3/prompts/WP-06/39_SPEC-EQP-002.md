# Claude Code prompt — WP-06 / Document 39: Cleaning, Sanitization & Line Clearance

TASK:
Implement the Cleaning, Sanitization & Line Clearance module (SPEC-EQP-002) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_39_Cleaning_Sanitization_Line_Clearance_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: CLN-FR-001..028 (28)
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
contracts/openapi/spec-eqp-002.yaml
contracts/events/spec-eqp-002/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-eqp-002/
```

REQUIREMENTS TO IMPLEMENT (28):
| ID | Requirement | Required behaviour | Acceptance intent |
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

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `cleaning_procedure_version` | 9 | PostgreSQL (GxP Core, authoritative) |
| `cleaning_execution` | 11 | PostgreSQL (GxP Core, authoritative) |
| `line_clearance` | 7 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (7):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /cleaning/v1/executions` | yes | — |
| `POST /cleaning/v1/executions/{id}/steps` | yes | — |
| `POST /cleaning/v1/executions/{id}/complete` | yes | — |
| `POST /cleaning/v1/executions/{id}/verify` | yes | policy lookup (Doc 106) |
| `POST /line-clearance/v1` | yes | — |
| `POST /line-clearance/v1/{id}/complete` | yes | — |
| `GET /cleaning/v1/equipment/{id}/status` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (8):
| Event type | Producer | Dedupe key |
|---|---|---|
| `CleaningStarted` | SPEC-EQP-002 | event_id |
| `CleaningCompleted` | SPEC-EQP-002 | event_id |
| `CleaningVerificationFailed` | SPEC-EQP-002 | event_id |
| `EquipmentMarkedClean` | SPEC-EQP-002 | event_id |
| `CleanHoldExpired` | SPEC-EQP-002 | event_id |
| `LineClearanceStarted` | SPEC-EQP-002 | event_id |
| `LineClearanceCompleted` | SPEC-EQP-002 | event_id |
| `LineClearanceFailed` | SPEC-EQP-002 | event_id |

UI SURFACES:
- Cleaning Queue
- Cleaning Execution
- Agents/Materials
- Inspection/Sampling
- Clean Hold Status
- Line Clearance
- Changeover
- Cleaning History

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
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-06/Document_39_SPEC-EQP-002_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EQP-002/<test_case_id>/`.
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
