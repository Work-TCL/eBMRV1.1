# Claude Code prompt — WP-08 / Document 57: Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile

TASK:
Implement the Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile module (SPEC-DDCP-004) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_57_Drug_Eluting_Coated_Device_DDCP_Profile_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: COAT-FR-001..030 (30)
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
contracts/openapi/spec-ddcp-004.yaml
contracts/events/spec-ddcp-004/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-ddcp-004/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| COAT-FR-001 | Coated device profile | Support drug-eluting/coated/impregnated devices with device substrate + drug/biologic coating constituent + finished combined product. | Type 4/5 architecture. |
| COAT-FR-002 | Substrate identity | Track base device lot/serial/subassembly and released device specification/version. | Device constituent. |
| COAT-FR-003 | Drug/coating constituent | Track coating solution/formulation/bulk lot, concentration/potency, prepared amount and hold time. | Drug constituent. |
| COAT-FR-004 | Surface preparation | Capture cleaning/activation/priming/pre-treatment steps and evidence. | Coating readiness. |
| COAT-FR-005 | Coating recipe | Versioned coating process route: dip/spray/inkjet/deposition/impregnation/other approved method. | Extensible. |
| COAT-FR-006 | Coating parameters | Speed/time/flow/pressure/distance/temperature/humidity/cycle/pass and other mapped process parameters. | Process evidence. |
| COAT-FR-007 | Equipment/program | Coater/equipment and recipe/program version eligible and bound to batch. | Validated state. |
| COAT-FR-008 | Environment | Required room/temperature/humidity/particle/environment status gate. | Process control. |
| COAT-FR-009 | Drug usage ledger | Track drug/coating solution issued, applied, residual, sampled, rejected, recovered/disposed and reconcile. | Drug mass balance. |
| COAT-FR-010 | Unit/lot association | Map device lot/serial/substrate unit to coating run and drug/coating constituent lot. | Combination genealogy. |
| COAT-FR-011 | Coating weight/loading | Record direct/indirect drug loading/coating weight measurement according to approved method. | Dose/loading evidence. |
| COAT-FR-012 | Uniformity | Support coating thickness/loading/uniformity spatial or sampled result structures. | Quality. |
| COAT-FR-013 | Coating integrity | Inspection for delamination/cracks/defects/adhesion or product-specific attributes. | Device/drug interaction. |
| COAT-FR-014 | Drug content/assay | Link QC assay/content/impurity/degradation results for finished coated device where required. | Drug quality. |
| COAT-FR-015 | Release/elution profile | Support in-vitro release/elution test result sets when product specification requires. | Therapeutic performance. |
| COAT-FR-016 | Dimensional/device function | Ensure coating process does not invalidate required device dimensional/mechanical/functional tests. | Combined performance. |
| COAT-FR-017 | Drying/curing | Capture curing/drying conditions and hold times after coating. | Process. |
| COAT-FR-018 | Sterilization interaction | Profile specifies pre/post coating sterilization route and recognizes potential impact of sterilization on drug/coating/device. | Critical DDCP interaction. |
| COAT-FR-019 | Sterilization evidence | Link sterilization cycle/contract process to exact coated device lot/serial. | Genealogy. |
| COAT-FR-020 | Post-sterilization testing | Profile can require drug assay/degradation/release/device tests after sterilization. | Interaction verification. |
| COAT-FR-021 | Packaging | Barrier/package materials, protection, labeling and packaged lot genealogy. | Finished product. |
| COAT-FR-022 | Unit serialization | Support serial/unit-level coated device trace when device profile requires. | Device postmarket. |
| COAT-FR-023 | Process sampling | Sampling plan can select devices/locations/timepoints across coating run. | Representativeness. |
| COAT-FR-024 | OOS/NCR | Coating/drug/device failures create OOS/NCR/deviation and affected unit/lot scope. | QMS. |
| COAT-FR-025 | Rework | Recoating/stripping/reprocessing default prohibited unless released validated route explicitly permits and drug/device impact assessed. | Safe default. |
| COAT-FR-026 | Yield/reconciliation | Reconcile device units and drug/coating material separately and combined. | Full balance. |
| COAT-FR-027 | Constituent checkpoints | Device substrate and drug constituent may have separate release inputs; finished coated device has independent final release. | Part 4. |
| COAT-FR-028 | Final blockers | Coating parameter excursion, drug reconciliation gap, sterilization issue, assay/release/device failure, genealogy gap or QMS issue blocks release. | No bypass. |
| COAT-FR-029 | Change impact | Substrate material, coating formulation, drug source, coating equipment/program, environment, sterilization, packaging and test-method changes require Change/Risk/Validation assessment. | Lifecycle. |
| COAT-FR-030 | Complaint/field trace | Complaint serial/lot can trace backward to coating run/drug lot and forward to affected distributed units. | Postmarket. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createCoatedDeviceProfileVersion() | Product/Quality Engineer | product_version; substrate requirement; drug/coating requirement; coating route; tests; sterilization route | CoatedDeviceProfileDraft | CoatedDeviceProfileDraftCreated |
| evaluateCoatingRunReadiness() | Batch/run start | device substrate lots/units; coating solution lot; equipment; environment; program | CoatingReadiness | CoatingRunReadinessEvaluated |
| startCoatingRun() | Operator/Supervisor | batch_id; coater_id; program_version; constituent quantities; context | CoatingRunContext | CoatingRunStarted |
| recordCoatingProcessEvidence() | Edge/Operator | run_id; parameter_code; value/uom; time; source mapping | CoatingProcessResult | CoatingEvidenceRecorded; COATING_PARAMETER_EXCURSION |
| recordDrugLoadingResult() | QC/Inline measurement | unit/sample/lot; method; raw inputs; calculation rule | DrugLoadingResult | DrugLoadingRecorded; DRUG_LOADING_OOS |
| bindDeviceToCoatingConstituent() | Genealogy service | device lot/serial scope; coating solution/drug lot; run_id | GenealogyBinding | CoatedDeviceGenealogyBound |
| completeCoatingRun() | Supervisor | run_id; counts; coating solution usage; losses; sample/reject refs | CoatingRunCompletion | CoatingRunCompleted; COATING_RECONCILIATION_FAILED |
| recordPostSterilizationTest() | QC/Device Test | finished coated lot/unit; sterilization ref; test profile/results | PostSterilizationResult | PostSterilizationTestRecorded |
| evaluateCoatedDeviceReleaseReadiness() | QA Release | finished lot/serial scope | ReleaseReadiness | CoatedDeviceReleaseReadinessEvaluated |
| traceCoatedDeviceComplaint() | Complaint/Recall | finished serial/lot | ComplaintTraceGraph | none |

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
- Coated Device Profile
- Constituent Handoff
- Coating Readiness
- Coating Run
- Process Parameter Timeline
- Drug Loading / QC
- Coating Inspection
- Sterilization Link
- Post-Sterilization Test
- Dual Reconciliation
- Genealogy
- QA Release

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
- wrong drug lot
- substrate on hold
- coating solution hold expired
- humidity excursion
- program version mismatch
- drug loading OOS
- coating integrity defect partial unit scope
- failed sterilization
- post-sterilization assay failure
- unapproved recoating attempt
- dual reconciliation mismatch
- complaint trace to drug lot
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-08/Document_57_SPEC-DDCP-004_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DDCP-004/<test_case_id>/`.
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
