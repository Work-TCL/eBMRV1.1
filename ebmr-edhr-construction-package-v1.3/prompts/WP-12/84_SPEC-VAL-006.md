# Claude Code prompt — WP-12 / Document 84: Operational Qualification (OQ) & Functional Control Verification

TASK:
Implement the Operational Qualification (OQ) & Functional Control Verification module (SPEC-VAL-006) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_84_Operational_Qualification_OQ_Functional_Verification_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: OQ-FR-001..018 (18)
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
- `validation` and its tests
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
validation/src/            # domain services, command handlers, repositories
validation/migrations/     # owned entities only
validation/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-val-006.yaml
contracts/events/spec-val-006/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-val-006/
```

REQUIREMENTS TO IMPLEMENT (18):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| OQ-FR-001 | Functional scope | Verify system functions/controls against approved requirements/risk in IQ environment. | Functional assurance. |
| OQ-FR-002 | Core GxP controls | Mutation, authorization, signature, audit, Vault, rules and release explicitly tested. | Core GxP. |
| OQ-FR-003 | Boundary conditions | Test invalid states, limits, stale versions, missing inputs and unauthorized actions. | Robustness. |
| OQ-FR-004 | State machines | Verify allowed/forbidden transitions. | Operational checks. |
| OQ-FR-005 | Calculations | Verify decimal/UOM/rounding/rule vectors. | Accuracy. |
| OQ-FR-006 | Batch/QMS/material/QC | Representative regulated module flows covered by risk. | Business controls. |
| OQ-FR-007 | Equipment/sterile | Representative equipment/cleaning/EM/sterile controls for DDCP profile. | Production. |
| OQ-FR-008 | Error handling | Verify stable errors/fail-closed behavior. | Safety. |
| OQ-FR-009 | Concurrency | Verify optimistic lock/idempotency/duplicate requests. | Distributed correctness. |
| OQ-FR-010 | Restart/recovery | Test worker/app restart during critical flows. | Reliability. |
| OQ-FR-011 | Roles/SoD | Representative positive/negative authority matrix. | Authorization. |
| OQ-FR-012 | Configuration | Test exact released configuration/rules/templates. | Configured state. |
| OQ-FR-013 | Automated reuse | CI integration/API tests may satisfy OQ when environment/config equivalence established. | CSA. |
| OQ-FR-014 | End-user fit | Operational user fit belongs PQ/UAT rather than forcing all into OQ. | Separation. |
| OQ-FR-015 | Defect closure | Failures map defect/deviation/retest. | No hidden failure. |
| OQ-FR-016 | Coverage | Higher-risk requirements receive objective OQ or justified equivalent evidence. | Risk coverage. |
| OQ-FR-017 | Independent review | Critical evidence reviewed per VMP. | Assurance. |
| OQ-FR-018 | Approval | OQ approval prerequisite to PQ/go-live as configured. | Gate. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| deriveOQSuite() | Validation service | requirement baseline; risks; IQ | OQSuite | OQSuiteDerived |
| executeOQSuite() | Validation/CI | OQ suite; environment/config fingerprint | OQExecution | OQExecutionCompleted |
| evaluateOQCoverage() | Validation | OQ execution; risk/requirements | OQCoverageReport | OQCoverageEvaluated |
| approveOQ() | Validation/QA | execution; coverage; deviations; signature | ApprovedOQ | OQApproved |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `oq_suite` | 4 | PostgreSQL (GxP Core, authoritative) |
| `oq_execution` | 5 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (4):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /validation/v1/oq:suites` | yes | — |
| `POST /validation/v1/oq/executions` | yes | — |
| `GET /validation/v1/oq/{id}/coverage` | no | — |
| `POST /validation/v1/oq/{id}/approve` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (4):
| Event type | Producer | Dedupe key |
|---|---|---|
| `OQSuiteDerived` | SPEC-VAL-006 | event_id |
| `OQExecutionCompleted` | SPEC-VAL-006 | event_id |
| `OQCoverageEvaluated` | SPEC-VAL-006 | event_id |
| `OQApproved` | SPEC-VAL-006 | event_id |

UI SURFACES:
- OQ Scope
- OQ Execution
- Critical Coverage
- Failures
- OQ Approval

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- stale mutation denied
- signature wrong meaning
- audit old/new
- rounding vectors
- duplicate command
- worker restart
- unauthorized release
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-12/Document_84_SPEC-VAL-006_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-VAL-006/<test_case_id>/`.
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
