# Claude Code prompt — WP-08 / Document 54: Prefilled Syringe & Injectable DDCP Manufacturing Profile

TASK:
Implement the Prefilled Syringe & Injectable DDCP Manufacturing Profile module (SPEC-DDCP-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_54_Prefilled_Syringe_Injectable_DDCP_Profile_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: PFS-FR-001..030 (30)
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
contracts/openapi/spec-ddcp-001.yaml
contracts/events/spec-ddcp-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-ddcp-001/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| PFS-FR-001 | Profile master | Define injectable DDCP subtype, dosage form, presentation, fill volume, strength, device constituent and container-closure architecture. | Concrete product identity. |
| PFS-FR-002 | Constituent definition | Model drug/biologic constituent, syringe/barrel, stopper/plunger, needle/needle shield, tip cap, safety device and packaging as versioned constituents. | Full genealogy. |
| PFS-FR-003 | Bulk drug handoff | Receive released bulk drug/biologic batch reference with assay/potency, concentration, sterility/bioburden status and expiry/hold constraints. | Constituent handoff. |
| PFS-FR-004 | Primary components | Require released lots for barrel/syringe, stopper/plunger, needle/closure and other product-contact components. | No unapproved component. |
| PFS-FR-005 | Component preparation | Track washing/depyrogenation/sterilization/ready-to-use status according to configured component route. | Sterile readiness. |
| PFS-FR-006 | Line readiness | Filling line, cleanroom, cleaning, SIP/sterilization, environmental state, personnel and filter status all verified before batch stage start. | Aseptic gate. |
| PFS-FR-007 | Bulk hold time | Track bulk compounding-to-filtration/filling hold time and block when released limits exceeded. | Validated timing. |
| PFS-FR-008 | Sterile filtration | If process uses sterile filtration, bind filter lot/serial, pre/post integrity status, filtration parameters and evidence. | Filtration assurance. |
| PFS-FR-009 | Filling setup | Record filler, product-contact path, fill program/version, needle/nozzle setup, target fill and line configuration. | Setup evidence. |
| PFS-FR-010 | Fill execution | Capture batch/cycle group, fill start/end, machine counts, actual/IPC weights or volumes, alarms/interventions and rejects. | Complete filling record. |
| PFS-FR-011 | Fill-weight IPC | Perform configurable in-process fill weight/volume sampling with method, sample frequency and acceptance rule. | Dose quantity control. |
| PFS-FR-012 | Stoppering/plunging | Capture plunger/stopper insertion/position and relevant process settings/results. | Closure assembly. |
| PFS-FR-013 | Needle/closure assembly | Track needle installation/shield/tip cap/closure configuration where applicable. | Device constituent. |
| PFS-FR-014 | Container closure integrity | Link required CCI/leak/seal tests by lot/sample plan/method and release state. | System integrity. |
| PFS-FR-015 | Visual inspection | 100% or configured inspection records machine/manual inspection version, defect codes, rejects and sampling verification. | Finished presentation quality. |
| PFS-FR-016 | Silicone/tungsten/particulate profile | Support product-specific material/process attributes or QC references when defined in the product's released control strategy. | Product-specific extensibility. |
| PFS-FR-017 | Functional syringe tests | Support break-loose/glide force, needle shield/removal force, dose delivery, leakage or other device output tests when included in released specification. | Device performance. |
| PFS-FR-018 | Safety feature assembly | If needle-safety/guard device exists, track subassembly lot, assembly process and functional test. | Safety constituent. |
| PFS-FR-019 | Serialization/UDI hooks | Support device/combination-product identifier/UDI configuration where applicable; actual applicability is regulatory-profile controlled. | Future compliance. |
| PFS-FR-020 | Label/packaging | Link label/artwork version, carton/IFU, lot/expiry and packaging reconciliation. | Finished unit trace. |
| PFS-FR-021 | Unit/lot genealogy | Drug bulk → component lots → filled syringe lot/unit/sample → packaged lot/device ID relationships preserved. | End-to-end trace. |
| PFS-FR-022 | Yield reconciliation | Reconcile bulk issued, units filled, rejects, samples, line loss and finished packed quantity. | Mass/unit balance. |
| PFS-FR-023 | Constituent release | Drug and device-constituent evidence may have separate release checkpoints; final DDCP release remains independent. | Part 4 profile. |
| PFS-FR-024 | Final release blockers | Open deviations/OOS, failed filter integrity, EM excursion, CCI/functional failure, unresolved reconciliation or missing constituent evidence block release per profile. | No incomplete release. |
| PFS-FR-025 | Batch review package | Review shows critical aseptic timeline, filtration, fill IPC, interventions, defects, device tests, genealogy and deviations. | Review-by-exception. |
| PFS-FR-026 | Stability/retain refs | Create/reference stability/retain sample plans and finished lot samples where configured. | Lifecycle support. |
| PFS-FR-027 | Rework restriction | Filled primary container rework/reprocessing routes are profile-specific and default disallowed unless released procedure explicitly permits. | Safe default. |
| PFS-FR-028 | Biologic subtype | Biologic constituent can reuse profile, but biologic-specific requirements remain separately enabled/baselined; no implicit equivalency. | Future profile. |
| PFS-FR-029 | Change sensitivity | Changes to syringe/barrel/stopper/needle/silicone/closure/fill program/filter/control strategy link Change Control and risk/validation impact. | Lifecycle. |
| PFS-FR-030 | Inspection export | Produce one reproducible PFS/DDCP batch package including drug + device constituent + combined-product evidence. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createInjectableProfileVersion() | Product/Quality Engineer | product_version_id; subtype; constituent_schema; process_route; control_strategy | InjectableProfileDraft | InjectableProfileDraftCreated; PROFILE_SCHEMA_INVALID |
| releaseInjectableProfileVersion() | QA/Regulatory/Validation | profile_id; expected_version; signatures; change_ref | ReleasedInjectableProfile | InjectableProfileReleased; PROFILE_RELEASE_BLOCKED |
| evaluateInjectableBatchReadiness() | Batch issue/start | batch_id; profile_version_id; line/equipment context | BatchReadinessResult | PFSBatchReadinessEvaluated; BULK_NOT_RELEASED/LINE_NOT_READY |
| startFillingStage() | Operator/Supervisor | batch_id; stage_id; line_id; fill_program_version; bulk_container_ids; e-sign if required | FillingStageContext | PFSFillingStarted; FILL_PROGRAM_MISMATCH |
| recordFillIPCResult() | QC/IPC/Edge | batch_id; sample_id; actual_value; uom; method/source | IPCResult | FillIPCRecorded; FILL_IPC_OOS |
| recordSyringeUnitOrCount() | Machine/Edge/Operator | batch_id; count_delta or unit IDs; category filled/reject/sample; source_event | UnitCountReceipt | SyringeCountRecorded; DUPLICATE_SOURCE_EVENT |
| recordAsepticInterventionForFill() | Aseptic module | operation_id; intervention_type; actor; start/end; impacted scope | InterventionImpactRef | PFSInterventionRecorded |
| completeFillingStage() | Supervisor | stage_id; counts; filter refs; IPC completion refs | FillStageCompletion | PFSFillingCompleted; FILL_STAGE_INCOMPLETE |
| recordPFSFunctionalTest() | QC/Device Test adapter | sample/unit; test_code; method/program version; values/raw ref | PFSFunctionalTestResult | PFSFunctionalTestRecorded; DEVICE_TEST_FAILED |
| evaluatePFSReleaseReadiness() | QA Release Engine | batch_id; release_profile_version | ReleaseReadiness | PFSReleaseReadinessEvaluated; RELEASE_BLOCKERS_PRESENT |
| createPFSBatchEvidencePackage() | QA/Inspector export | batch_id; package_version | EvidencePackageRef | PFSBatchPackageGenerated |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (9 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `ddcp_profile_version` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `constituent_requirement` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `constituent_handoff` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `fill_operation` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `production_count_ledger` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `device_assembly_record` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `device_functional_test_link` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `ddcp_release_checkpoint` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `batch_evidence_manifest` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (0):
_none declared in the source specifications_

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- Injectable Profile Designer
- Constituent Requirements
- Batch Readiness
- Filling Setup
- Aseptic Fill Execution
- Fill IPC
- Closure/Assembly
- Inspection
- Device Functional Results
- Reconciliation
- DDCP Review
- Final Release Summary

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
- unreleased bulk blocked
- wrong stopper/syringe lot blocked
- clean hold expired
- filter post-use integrity failed
- fill IPC OOS
- unplanned aseptic intervention
- count source retry duplicate
- visual reject reconciliation
- CCI sample failure
- device functional test fail
- component change after batch issue does not alter snapshot
- final release with device constituent incomplete denied
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-08/Document_54_SPEC-DDCP-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DDCP-001/<test_case_id>/`.
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
