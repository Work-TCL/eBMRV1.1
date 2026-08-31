# Claude Code prompt — WP-08 / Document 55: Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile

TASK:
Implement the Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile module (SPEC-DDCP-002) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_55_Autoinjector_Pen_Cartridge_DDCP_Profile_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: INJ-FR-001..030 (30)
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
contracts/openapi/spec-ddcp-002.yaml
contracts/events/spec-ddcp-002/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-ddcp-002/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| INJ-FR-001 | Injector family profile | Support autoinjector, pen injector, reusable pen + cartridge, single-use injector and configured related injector architectures. | Reusable family model. |
| INJ-FR-002 | Drug container relation | Model PFS/cartridge/vial/reservoir as drug-container subassembly and separate injector device constituents. | Exact architecture. |
| INJ-FR-003 | Device BOM | Track housing, spring/drive, needle system, activation components, dose mechanism, cap, shield, electronics if applicable and packaging. | Device genealogy. |
| INJ-FR-004 | Subassembly handoff | Released drug-container subassembly enters injector assembly with exact lot/unit range and status. | Constituent handoff. |
| INJ-FR-005 | Device component release | Only released device component lots/subassemblies can be assembled. | QMS gate. |
| INJ-FR-006 | Assembly line readiness | Equipment program, tooling, calibration, cleaning/clearance, operator qualification and material verification before run. | Manufacturing gate. |
| INJ-FR-007 | Assembly recipe | Versioned assembly sequence includes component scans, orientation/presence checks, torque/force/position parameters and verification. | Deterministic assembly. |
| INJ-FR-008 | Unit serialization | Support unit-level internal serial/UDI/device identifier relationship when profile requires. | Device traceability. |
| INJ-FR-009 | Drug-container insertion | Track exact PFS/cartridge lot/unit into injector unit/lot; prevent duplicate/cross-use. | Genealogy. |
| INJ-FR-010 | Needle activation system | Capture assembly/test of needle insertion/retraction/shield function where applicable. | Safety/performance. |
| INJ-FR-011 | Dose setting mechanism | For pens, capture dose mechanism version/calibration/test route and configured dosing range. | Pen performance. |
| INJ-FR-012 | Delivery performance outputs | Profile defines essential delivery outputs such as delivered volume/dose, delivery time, activation force, needle depth or other product-specific outputs. | Performance control. |
| INJ-FR-013 | Function test plan | Sampling or 100% test plan, fixture/program version and acceptance criteria. | Device test evidence. |
| INJ-FR-014 | Force/torque tests | Support activation/cap removal/needle shield/drive/torque forces and dimensional/functional results. | Mechanical outputs. |
| INJ-FR-015 | Dose accuracy | Link dose-delivery/gravimetric/volumetric tests and calculations. | Drug delivery. |
| INJ-FR-016 | Incomplete dose detection | Test/result taxonomy includes under-delivery, partial delivery, premature stop and other profile defects. | Failure modes. |
| INJ-FR-017 | Audible/visual indicators | Test completion/window/click/indicator functions where included. | User feedback. |
| INJ-FR-018 | Reusable device pairing | For reusable injector + cartridge, model compatibility/approved pairing and cartridge lot genealogy without assuming permanent single unit relationship. | Cross-labeled architecture. |
| INJ-FR-019 | Software/electronics | If connected/electronic injector exists, firmware/config/software evidence hooks are available but require separately approved profile. | Future-ready. |
| INJ-FR-020 | Human factors linkage | Profile can reference design/risk/human-factors critical tasks but manufacturing eBMR does not itself determine usability acceptability. | Lifecycle link. |
| INJ-FR-021 | Device rejects | Unit reject reason, disassembly/scrap/rework authorization and constituent impact preserved. | Nonconformance. |
| INJ-FR-022 | Rework | Device rework only through released route; drug-container constituent cannot be casually reused unless procedure explicitly permits and quality status reevaluated. | Controlled. |
| INJ-FR-023 | Packaging | Device + drug constituent + accessories/IFU/labels/cap/tray/carton reconciliation. | Finished configuration. |
| INJ-FR-024 | Final device/combination test | Support finished-unit or lot-level tests after assembly/packaging. | Final evidence. |
| INJ-FR-025 | Genealogy | Component lots + drug-container lot/unit → injector serial/lot → packaged saleable unit. | End-to-end. |
| INJ-FR-026 | Constituent release | Separate container/drug/device checkpoints feed final combined release. | DDCP. |
| INJ-FR-027 | Release blockers | Failed dose/function test, unresolved device NCR, wrong component pairing, genealogy gap or incomplete container/drug evidence block final release. | No bypass. |
| INJ-FR-028 | Change impact | Drive system, spring, needle, cartridge/PFS, lubricant, assembly program, test fixture/program and labeling changes trigger controlled assessment. | Lifecycle. |
| INJ-FR-029 | Product family inheritance | Common injector profile can inherit product-family functions while exact test outputs/limits are product-version controlled. | Configurability. |
| INJ-FR-030 | Evidence export | Unit/lot-level combined package supports investigation of one complaint serial back to exact drug and device constituents. | Postmarket readiness. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createInjectorProfileVersion() | Product/Device Engineer | product_version; injector_type; constituent architecture; assembly/test schemas | InjectorProfileDraft | InjectorProfileDraftCreated |
| evaluateInjectorAssemblyReadiness() | Batch/Work order start | batch_id; line_id; drug_container_lot/unit scope; device component lots | AssemblyReadiness | InjectorAssemblyReadinessEvaluated |
| bindDrugContainerToInjectorUnit() | Assembly station/Edge | batch_id; drug_container_id; injector_unit_id; scanner evidence | BindingReceipt | DrugContainerBound; CONTAINER_ALREADY_USED/WRONG_PAIRING |
| recordAssemblyParameter() | PLC/Tester/Operator | unit/lot; parameter_code; value/uom; source/mapping version | AssemblyParameterResult | InjectorAssemblyParameterRecorded |
| executeInjectorFunctionalTest() | Tester adapter/QC | unit/sample; test_profile; program_version; raw evidence | InjectorFunctionalTestResult | InjectorFunctionalTestCompleted; INJECTOR_TEST_FAILED |
| evaluateDoseDeliveryResult() | QC/Rules | raw measurements; calculation rule; acceptance profile | DoseDeliveryResult | DoseDeliveryEvaluated; DOSE_DELIVERY_FAILED |
| recordUnitDisposition() | QA/Production | unit_id; PASS/REJECT/REWORK; reason; NCR/rework ref | UnitDisposition | InjectorUnitDispositioned |
| completeInjectorAssemblyBatch() | Supervisor | batch_id; unit counts; rejects; tests; reconciliation | AssemblyCompletion | InjectorAssemblyCompleted; UNIT_RECONCILIATION_FAILED |
| evaluateInjectorReleaseReadiness() | QA Release | batch_id/product lot | ReleaseReadiness | InjectorReleaseReadinessEvaluated |
| traceComplaintSerial() | Complaint/Genealogy | finished_serial | ComplaintTraceGraph | none |

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
- Injector Profile
- Assembly BOM/Route
- Assembly Readiness
- Unit Scan/Binding
- Assembly Execution
- Functional Test
- Reject/Rework
- Unit Genealogy
- Packaging
- Review/Release
- Complaint Serial Trace

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
- PFS already bound to another serial
- cartridge wrong family
- device component lot on hold
- tester calibration expired
- tester program version wrong
- activation force fail then passing retest preserves both
- under-delivery
- rejected unit disassembly/reuse attempt
- reusable pen cross-label compatibility
- complaint trace from serial to drug lot
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-08/Document_55_SPEC-DDCP-002_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DDCP-002/<test_case_id>/`.
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
