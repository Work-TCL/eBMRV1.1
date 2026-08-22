# Claude Code prompt — WP-00 / Document 102: Testing Strategy

TASK:
Implement the Testing Strategy module (SPEC-ENG-006) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_102_Testing_Strategy_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: TEST-FR-001..036 (36)
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

- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `tooling` and its tests
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
tooling/src/            # domain services, command handlers, repositories
tooling/migrations/     # owned entities only
tooling/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-eng-006.yaml
contracts/events/spec-eng-006/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-eng-006/
```

REQUIREMENTS TO IMPLEMENT (36):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| TEST-FR-001 | Test pyramid/portfolio | Use multiple test layers selected by risk; no single coverage metric substitutes for assurance. | Balanced quality. |
| TEST-FR-002 | Unit tests | Deterministic domain functions, parsers, calculations and state/rule helpers receive fast isolated tests. | Fast feedback. |
| TEST-FR-003 | Property tests | Calculations, conversions, parsers, idempotency and invariants use property/fuzz testing where valuable. | Edge-case confidence. |
| TEST-FR-004 | Rule vectors | Regulated rules/calculations maintain approved table-driven golden vectors including boundary/rounding/UOM cases. | Accuracy. |
| TEST-FR-005 | Repository tests | Repository persistence tests verify constraints/versioning/transaction behavior against real database where needed. | Data correctness. |
| TEST-FR-006 | API tests | Each operation tests schema, auth, business success, validation errors, expected-version and idempotency. | Contract correctness. |
| TEST-FR-007 | Contract tests | Provider/consumer compatibility tests for internal/external APIs/events. | Integration stability. |
| TEST-FR-008 | Event tests | Outbox/event envelope, duplicate, replay, ordering and poison-event behavior verified. | Async correctness. |
| TEST-FR-009 | Integration tests | Real/test-container dependencies used for PostgreSQL, NATS, object storage, Temporal and adapters where fake would miss behavior. | System confidence. |
| TEST-FR-010 | Workflow replay tests | Temporal workflows tested with deterministic replay/version fixtures and time-skipping. | Upgrade safety. |
| TEST-FR-011 | Frappe tests | Projection read-only, permissions, server controller routing and UI action/API mapping tested. | Framework boundary. |
| TEST-FR-012 | UI component tests | High-risk UI controls verify state, required fields, read-only/source version and safe error display. | UX correctness. |
| TEST-FR-013 | End-to-end tests | Critical eBMR/QMS/material/QC/release flows tested across real service boundaries in controlled environment. | Business confidence. |
| TEST-FR-014 | Authorization tests | Positive/negative roles, tenant/site scope, SoD and qualification checks automated. | Security/GxP. |
| TEST-FR-015 | Signature tests | Fresh challenge, incorrect auth, expired nonce, stale record, meaning, manifestation/linking tested. | Part 11. |
| TEST-FR-016 | Audit/Vault tests | Old/new values, append-only, hash chain, canonicalization, corrections and archive retrieval tested. | Data integrity. |
| TEST-FR-017 | Concurrency tests | Race, stale version, duplicate request, lock/deadlock/retry conditions tested for contested aggregates. | No lost updates. |
| TEST-FR-018 | Failure injection | DB/NATS/Temporal/object/ERP/LIMS/Edge outages and timeout ambiguity tested. | Resilience. |
| TEST-FR-019 | Recovery tests | Restart/crash after each durable boundary verifies correct resume/idempotency. | Reliability. |
| TEST-FR-020 | Security tests | SAST/SCA plus BOLA/injection/SSRF/XSS/CSRF/file/rate/secret/PKI/network tests per Doc92. | Security. |
| TEST-FR-021 | Performance tests | Load/soak/capacity tests tied NFRs and qualified scale. | Performance. |
| TEST-FR-022 | Migration tests | Every migration runs on previous supported schema plus representative data and reconciliation. | Upgrade safety. |
| TEST-FR-023 | Backup/restore tests | Restore/PITR tests verify application-level integrity. | DR. |
| TEST-FR-024 | Mutation testing | Selected high-risk pure domain/rules packages may use mutation testing to identify weak tests. | Test quality. |
| TEST-FR-025 | Coverage metrics | Line/branch coverage reported by package but thresholds are risk-tiered; critical function trace coverage matters more. | Useful metrics. |
| TEST-FR-026 | Critical requirement coverage | Every higher-risk requirement has at least one objective verification link. | Validation. |
| TEST-FR-027 | No flaky tolerance | Flaky tests quarantined only with owner/issue/expiry; release-critical flakiness is blocker. | Reliable CI. |
| TEST-FR-028 | Test determinism | Tests control clock/ID/randomness/network and avoid order dependence. | Repeatability. |
| TEST-FR-029 | Synthetic data | Test fixtures synthetic/deidentified, stable and versioned; no production secrets/data in repo. | Privacy. |
| TEST-FR-030 | Test isolation | Parallel tests do not share mutable tenant/site/global state unless scenario explicitly exercises concurrency. | Stability. |
| TEST-FR-031 | Evidence output | Validation-eligible tests emit machine-readable result, environment/build/test IDs and artifacts. | CSA reuse. |
| TEST-FR-032 | Failure retention | CI/validation preserves failed result; rerun is separate evidence. | Integrity. |
| TEST-FR-033 | Test ownership | Each suite/package has CODEOWNER/maintainer; orphan tests treated as engineering debt. | Governance. |
| TEST-FR-034 | Test review | Critical tests reviewed when requirement/risk behavior changes, not blindly reused. | Validated state. |
| TEST-FR-035 | Test tagging | Tags classify unit/integration/contract/e2e/security/performance/validation and risk level. | Selective execution. |
| TEST-FR-036 | No mock-only critical proof | Mocks can isolate units but cannot be sole proof of DB/broker/crypto/integration semantics. | Real behavior. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| deriveRequiredTestSet() | CI/Change impact | changed requirements/functions/files; risk matrix | RequiredTestSet | RequiredTestsDerived |
| runUnitTestSuite() | CI | package; commit; test profile | TestRun | UnitTestsCompleted |
| runIntegrationTestEnvironment() | CI | suite; container/service versions; config | IntegrationTestRun | IntegrationTestsCompleted |
| runConcurrencyScenario() | CI/Performance | scenario; worker count; seed; target function | ConcurrencyResult | ConcurrencyScenarioCompleted |
| runFailureInjectionScenario() | Resilience test | dependency; failure mode; duration; expected behavior | FailureInjectionResult | FailureInjectionCompleted |
| importTestRunAsValidationEvidence() | Validation integration | CI run ID; test IDs; build/environment fingerprint | ValidationEvidenceImport | EngineeringEvidenceImported |
| detectFlakyTest() | CI analytics | test history; threshold/policy | FlakyTestFinding | FlakyTestDetected |
| evaluateTestReleaseGate() | Release CI | required test set; runs; exceptions | TestGateDecision | TestReleaseGateEvaluated |

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
- none declared

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
- unit/property rule vectors
- real PostgreSQL repository constraints
- API BOLA negative tests
- outbox duplicate consumer crash scenario
- Temporal replay compatibility
- migration previous-version matrix
- flaky critical test
- CI evidence imported into validation
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-00/Document_102_SPEC-ENG-006_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-ENG-006/<test_case_id>/`.
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
