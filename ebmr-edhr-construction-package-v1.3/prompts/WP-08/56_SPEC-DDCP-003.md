# Claude Code prompt — WP-08 / Document 56: Inhalation DDCP Manufacturing Profile — MDI / DPI

TASK:
Implement the Inhalation DDCP Manufacturing Profile — MDI / DPI module (SPEC-DDCP-003) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_56_Inhalation_MDI_DPI_DDCP_Profile_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: INH-FR-001..030 (30)
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
- `services/gxp-api/src/modules/ddcp` and its tests
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
services/gxp-api/src/modules/ddcp/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/ddcp/migrations/     # owned entities only
services/gxp-api/src/modules/ddcp/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-ddcp-003.yaml
contracts/events/spec-ddcp-003/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-ddcp-003/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| INH-FR-001 | Inhalation profile | Support MDI, DPI and configured inhalation-device presentations through subtype-specific profile. | Family abstraction. |
| INH-FR-002 | Drug formulation constituent | Model formulation/blend/suspension/solution constituent with released batch/spec/hold time. | Drug input. |
| INH-FR-003 | Device/container constituents | MDI valve/canister/actuator or DPI device/capsule/blister/reservoir components tracked as device/container constituents. | Device trace. |
| INH-FR-004 | Propellant/excipient components | For MDI, propellant/excipient/material lots and dispensing controls configurable. | Formulation trace. |
| INH-FR-005 | Powder blend | For DPI, blend/bulk powder properties/hold status and sampling/test links configurable. | DPI process. |
| INH-FR-006 | Component prep | Cleaning/handling/release of valves/canisters/actuators/blisters/capsules/device parts. | Readiness. |
| INH-FR-007 | Filling route | Configure pressure fill, cold fill, liquid fill, powder dose fill, blister/capsule fill or other released route. | Product-specific. |
| INH-FR-008 | Fill/dose controls | Target fill/dose, IPC sampling and weight/mass/reconciliation rules. | Dose quantity. |
| INH-FR-009 | Valve/crimp assembly | For MDI, capture valve placement, crimp dimensions/settings and leak/closure results. | Container closure. |
| INH-FR-010 | Device assembly | Actuator/device assembly with exact component lots and assembly program. | Device constituent. |
| INH-FR-011 | DPI dose unit loading | Track powder dose/blister/capsule lot and device association according to unit/lot architecture. | Genealogy. |
| INH-FR-012 | Leak/pressure test | Capture product-specific leak/pressure/closure integrity tests. | System integrity. |
| INH-FR-013 | Delivered dose | Support delivered-dose/uniformity test data and method/version where included in released spec. | Performance. |
| INH-FR-014 | Aerodynamic performance | Support cascade impaction/aerodynamic particle size distribution or other performance test result structures as product-specific QC methods. | Inhalation performance. |
| INH-FR-015 | Spray/plume pattern hooks | Support spray pattern/plume geometry or device-specific output tests when defined by control strategy. | Extensible. |
| INH-FR-016 | Priming/repriming | Device test profile can capture priming/repriming actuation requirements and results. | Use performance. |
| INH-FR-017 | Actuation count | MDI/DPI unit/device may track labeled actuations/doses and counter mechanism test where applicable. | Dose counter. |
| INH-FR-018 | Moisture/environment | DPI process can enforce humidity/environment readiness and excursion linkage. | Powder sensitivity. |
| INH-FR-019 | Blend/fill hold time | Track formulation/blend-to-filling and intermediate hold limits. | Validated timing. |
| INH-FR-020 | Cleaning/changeover | Product-contact line/device assembly area cleaning and line clearance required. | Cross-contamination. |
| INH-FR-021 | Sampling | Structured beginning/middle/end or configured location/time sampling plans. | Representativeness. |
| INH-FR-022 | Unit/lot inspection | Visual/device/pack integrity results and defects. | Finished quality. |
| INH-FR-023 | Packaging | Canister/device/capsule/blister + actuator/accessory/IFU/label/carton reconciliation. | Configuration. |
| INH-FR-024 | Genealogy | Drug formulation/blend + primary container/device lots → finished inhaler lot/unit. | Trace. |
| INH-FR-025 | OOS/OOT | Delivered dose/aerodynamic/device functional failures enter common OOS/OOT workflow and block release as configured. | Lab integrity. |
| INH-FR-026 | Constituent release | Drug/device constituent checkpoints remain separate from final inhaler release. | DDCP. |
| INH-FR-027 | Release blockers | Unresolved fill/closure/device/dose/aerodynamic/QMS/reconciliation issue blocks final release per profile. | No bypass. |
| INH-FR-028 | Stability linkage | Profile supports orientation/storage/stability sample references where product program requires. | Lifecycle. |
| INH-FR-029 | Change impact | Valve/canister/actuator/device material, formulation, propellant, fill/crimp/device program and test-method changes invoke Change/Risk/Validation. | Lifecycle. |
| INH-FR-030 | Draft guidance status | FDA 2018 MDI/DPI guidance is treated as nonbinding product-design input; customer released spec/control strategy governs executable requirements. | Correct regulatory handling. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createInhalationProfileVersion() | Product/Quality Engineer | product_version; subtype MDI/DPI; formulation; device constituents; route; tests | InhalationProfileDraft | InhalationProfileDraftCreated |
| evaluateInhalationReadiness() | Batch start | batch_id; formulation/blend lot; device/component lots; environment/equipment | InhalationReadiness | InhalationReadinessEvaluated |
| startInhalerFillRun() | Production | batch/stage; fill route; equipment/program; target rules | FillRunContext | InhalerFillStarted |
| recordCrimpOrClosureResult() | Edge/QC/Operator | unit/sample/lot; crimp dimensions or closure test; source | ClosureResult | InhalerClosureRecorded; CLOSURE_TEST_FAILED |
| recordInhalerDoseTest() | QC/LIMS | sample IDs; test code; method; raw results/evidence | QCResultSet | InhalerDoseTestRecorded; INHALER_QC_OOS |
| recordDoseCounterTest() | Device Tester | unit/sample; program/version; expected count behavior | DeviceTestResult | DoseCounterTestRecorded |
| completeInhalerManufacturingRun() | Supervisor | run_id; counts; losses; samples; rejects; mandatory test refs | RunCompletion | InhalerManufacturingCompleted |
| evaluateInhalerReleaseReadiness() | QA Release | batch_id | ReleaseReadiness | InhalerReleaseReadinessEvaluated |
| traceInhalerLot() | Genealogy/Complaint | finished lot/unit | GenealogyGraph | none |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (0 entities owned by this module):
_none declared in the source specifications_

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (0):
_none declared in the source specifications_

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- Inhalation Profile
- Formulation/Blend Handoff
- Device Components
- Readiness
- Filling/Assembly
- Closure/Leak
- Dose/Performance Tests
- Packaging
- Genealogy
- Review/Release

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
- MDI wrong valve lot
- crimp result out of limit
- DPI humidity excursion
- blend hold time expired
- delivered-dose OOS
- later passing retest preserves initial OOS
- aerodynamic data import missing raw evidence
- device component changed after batch issue
- final packaging wrong actuator/device family
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-08/Document_56_SPEC-DDCP-003_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DDCP-003/<test_case_id>/`.
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
