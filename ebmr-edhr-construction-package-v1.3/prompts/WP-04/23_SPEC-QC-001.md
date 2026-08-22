# Claude Code prompt — WP-04 / Document 23: Native Basic QC & Sampling Specification

TASK:
Implement the Native Basic QC & Sampling Specification module (SPEC-QC-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_23_Native_Basic_QC_Sampling_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: QC-FR-001..038 (38)
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
- `services/gxp-api/src/modules/qc` and its tests
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
services/gxp-api/src/modules/qc/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/qc/migrations/     # owned entities only
services/gxp-api/src/modules/qc/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-qc-001.yaml
contracts/events/spec-qc-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-qc-001/
```

REQUIREMENTS TO IMPLEMENT (38):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| QC-FR-001 | Test specification master | Create versioned test specification by material/product/in-process/device scope with test list, methods, acceptance criteria, sampling plan and release dependency. | QC requirement controlled. |
| QC-FR-002 | Specification lifecycle | Draft, review, released/effective, superseded, obsolete, suspended; released spec immutable and Vault-backed. | No live edit. |
| QC-FR-003 | Test method reference | Each test references approved method/version, compendial/internal/validated method type and suitability/validation evidence reference. | Method exact. |
| QC-FR-004 | Method modification | Modified method requires controlled version, reason, validation/suitability evidence and approval; original method remains. | 211.194(b)-style record support. |
| QC-FR-005 | Sampling plan | Define sample source, quantity, number of units/containers, selection rule, frequency, sample type and reserve/retain behavior. | Written sampling plan. |
| QC-FR-006 | Sample identity | Assign immutable sample ID linked to source lot/batch/container/unit/location, amount, date sampled and date received in lab. | 211.194 sample identity. |
| QC-FR-007 | Sample type | Support incoming, in-process, finished product, device test, environmental, stability, reserve/retain and investigation samples. | Common QC core. |
| QC-FR-008 | Sampling execution | Record sampler, procedure/version, source location/container, amount, timestamp, container/label and chain-of-custody start. | Sample attributable. |
| QC-FR-009 | Chain of custody | Track sample transfers, lab location, storage condition, aliquots, destruction/retain status and custodians. | Sample integrity. |
| QC-FR-010 | Test order | Create one or more test orders from sample/spec with required tests, priority, due date and release/blocking flags. | Work queue controlled. |
| QC-FR-011 | Analyst assignment | Assign qualified analyst/team; qualification/training and method authorization checked at execution. | Qualified lab personnel. |
| QC-FR-012 | Instrument eligibility | Verify instrument/test equipment ID, calibration/status/method compatibility before accepting instrument-generated result. | Unqualified instrument blocked. |
| QC-FR-013 | Reference standard/reagent | Capture reference standard, reagent/solution IDs, lot, expiry/standardization status where test requires them. | Laboratory records complete. |
| QC-FR-014 | Sample amount | Record weight/measure used for each test where applicable. | 211.194(a)(3) support. |
| QC-FR-015 | Raw data | Retain all required raw data or immutable evidence references, including graphs/charts/spectra/files where produced by instrument. | Complete data. |
| QC-FR-016 | Manual raw data | Structured manual observations/entries capture analyst/time/unit/method step and audit history. | No untraceable worksheet. |
| QC-FR-017 | Instrument raw data | Instrument integration stores source ID, original file/reference, sequence/run ID, acquisition time, hash and metadata. | Original data preserved. |
| QC-FR-018 | Calculations | Use released calculation rules for calculations, units, conversion/equivalency factors and rounding; persist inputs/results/version. | 211.194(a)(5) support. |
| QC-FR-019 | Result | Store structured result, unit, method/spec version, acceptance criterion and Pass/Fail/OOS/OOT/Pending status. | Result meaning explicit. |
| QC-FR-020 | Multiple determinations | Model replicates/injections/readings individually where method requires; final reported result derives via released method/rule. | No hidden averaging. |
| QC-FR-021 | System suitability | Where applicable record system-suitability checks separately and determine whether test run is valid under method. | Invalid test distinguished. |
| QC-FR-022 | Analyst completion | Analyst signs/completes test record after all required data/results/evidence present. | Performer attribution. |
| QC-FR-023 | Second-person review | Reviewer verifies original records for accuracy, completeness and specification compliance; controlled e-sign where Part 11 applies. | 211.194(a)(8) support. |
| QC-FR-024 | Result correction | Correction creates superseding result/version with reason; original remains visible and may trigger impact review. | No overwrite. |
| QC-FR-025 | OOS trigger | Any applicable result outside specification/acceptance criteria automatically creates OOS candidate/record; user cannot suppress trigger. | Failed result preserved. |
| QC-FR-026 | OOT trigger | Released trend rule may flag result as OOT even if within specification; create OOT record without changing raw result. | Trend signal. |
| QC-FR-027 | Invalid test | Test may be invalidated only through controlled investigation with assignable cause/evidence; invalidation does not delete raw data. | Scientific invalidation. |
| QC-FR-028 | Retest | Retest cannot be started merely by editing/re-running failed result; it requires OOS/investigation authorization and new test instance. | No testing into compliance. |
| QC-FR-029 | Resample | New sample after OOS requires controlled authorization and scientific rationale; linked to original sample/OOS. | Controlled resampling. |
| QC-FR-030 | Material/batch disposition | QC test-set completion updates quality/release readiness but does not directly perform final batch/material release unless authorized module command executes. | Authority separated. |
| QC-FR-031 | Partial test completion | Test order shows incomplete required tests and blocks dependent release/step. | No false completion. |
| QC-FR-032 | Microbiology result support | Support qualitative/count results, incubation periods, organism/reference metadata and delayed completion without forcing all tests into numeric schema. | Future pharma/sterile ready. |
| QC-FR-033 | Device test support | Support force, torque, dimensional, dose-delivery, leak, electrical/functional, visual or other structured device test result types. | DDCP/device ready. |
| QC-FR-034 | Attachment/evidence | Attach method worksheets, chromatograms, spectra, reports, images and certificates with hash/version/source metadata. | Evidence complete. |
| QC-FR-035 | Stability linkage | Architecture can tag stability sample/timepoint/study and retain results, while full Stability Management may be separate later spec. | Expandable. |
| QC-FR-036 | QC dashboard | Show samples/tests by status, overdue, OOS/OOT, analyst, instrument, product/material and release blockers. | Operational. |
| QC-FR-037 | Search/export | Authorized users can retrieve complete sample/test record including raw data refs, calculations, analyst/reviewer signatures and audit. | Inspection-ready. |
| QC-FR-038 | No deletion | Sample/test/result/raw-data metadata cannot be physically deleted by normal application workflow. | Data integrity. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (6 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `qc_test_specification` | 10 | PostgreSQL (GxP Core, authoritative) |
| `qc_test_definition` | 7 | PostgreSQL (GxP Core, authoritative) |
| `qc_sample` | 15 | PostgreSQL (GxP Core, authoritative) |
| `qc_test_order` | 6 | PostgreSQL (GxP Core, authoritative) |
| `qc_test_run` | 8 | PostgreSQL (GxP Core, authoritative) |
| `qc_result` | 15 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (13):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /qc/v1/specifications/drafts` | yes | — |
| `POST /qc/v1/specifications/{id}/release` | yes | policy lookup (Doc 106) |
| `POST /qc/v1/samples` | yes | — |
| `POST /qc/v1/samples/{id}/receive` | yes | — |
| `POST /qc/v1/test-orders` | yes | — |
| `POST /qc/v1/test-orders/{id}/start` | yes | — |
| `POST /qc/v1/test-orders/{id}/raw-data` | yes | — |
| `POST /qc/v1/test-orders/{id}/results` | yes | — |
| `POST /qc/v1/test-orders/{id}/complete` | yes | — |
| `POST /qc/v1/test-orders/{id}/review` | yes | — |
| `POST /qc/v1/results/{id}/correct` | yes | — |
| `GET /qc/v1/samples/{id}/record` | no | — |
| `GET /qc/v1/release-readiness?...` | no | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (10):
| Event type | Producer | Dedupe key |
|---|---|---|
| `QCSampleCreated` | SPEC-QC-001 | event_id |
| `QCSampleReceived` | SPEC-QC-001 | event_id |
| `QCTestStarted` | SPEC-QC-001 | event_id |
| `QCResultRecorded` | SPEC-QC-001 | event_id |
| `QCResultOOSDetected` | SPEC-QC-001 | event_id |
| `QCResultOOTDetected` | SPEC-QC-001 | event_id |
| `QCTestAnalystCompleted` | SPEC-QC-001 | event_id |
| `QCTestReviewed` | SPEC-QC-001 | event_id |
| `QCResultCorrected` | SPEC-QC-001 | event_id |
| `QCTestInvalidated` | SPEC-QC-001 | event_id |

UI SURFACES:
- sample/source;
- method;
- sample amount;
- raw data/evidence;
- calculations;
- result/criterion;
- prior/superseded results;
- system suitability;
- OOS/OOT;
- analyst;
- audit;
- review signature.

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
- specification
- test code/name
- method version
- result data type
- acceptance rule
- required flag
- release-blocking flag
- OOS/OOT policies
- review policy
- sample ID
- test definition/version
- assigned analyst
- state/version
- started/completed/reviewed times
- blocking status
- test order
- instrument/equipment ID
- analyst
- sample amount
- reference standards/reagents
- system suitability
- raw-data evidence IDs
- calculation version
- numeric single value
- numeric replicate series
- calculated numeric
- qualitative enum
- pass/fail
- text/observation
- count
- range
- multidimensional JSON schema for approved device tests
- numeric pass
- numeric OOS
- qualitative fail
- replicate calculation
- missing raw data
- wrong method version
- analyst qualification expired
- instrument calibration expired
- system suitability failed
- result correction
- second-person reviewer edits attempt
- OOS then retest
- OOT within specification
- late instrument file
- sample chain of custody
- duplicate test submission
- backup/restore evidence
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-04/Document_23_SPEC-QC-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-QC-001/<test_case_id>/`.
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
