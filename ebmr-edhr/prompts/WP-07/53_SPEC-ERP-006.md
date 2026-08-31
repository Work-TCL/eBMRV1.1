# Claude Code prompt — WP-07 / Document 53: Integration Error Handling, Retry, Idempotency & Reconciliation

TASK:
Implement the Integration Error Handling, Retry, Idempotency & Reconciliation module (SPEC-ERP-006) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_53_Integration_Error_Retry_Idempotency_Reconciliation_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: INT-FR-001..030 (30)
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
- `services/integration-gateway` and its tests
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
services/integration-gateway/src/            # domain services, command handlers, repositories
services/integration-gateway/migrations/     # owned entities only
services/integration-gateway/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-erp-006.yaml
contracts/events/spec-erp-006/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-erp-006/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| INT-FR-001 | Canonical integration message | All inbound/outbound exchanges have message/command/event ID, source, target, schema, correlation, causation and payload hash. | Trace. |
| INT-FR-002 | Error taxonomy | AUTH, CONFIG, VALIDATION, BUSINESS_REJECT, CONFLICT, RATE_LIMIT, TRANSIENT_NETWORK, SERVER_ERROR, TIMEOUT_UNCERTAIN, SCHEMA, SECURITY, MANUAL_REVIEW. | Consistent handling. |
| INT-FR-003 | Retry classification | Only retryable categories retry automatically; business/validation/config errors require correction/review. | No retry storms. |
| INT-FR-004 | Exponential backoff | Configurable capped backoff + jitter; vendor Retry-After honored where applicable. | Resilience. |
| INT-FR-005 | Maximum attempts | Retry count/time window configurable; exhausted commands enter manual-review/dead-letter. | Bounded. |
| INT-FR-006 | Idempotency key | Every write command has stable idempotency key derived from immutable source event/operation semantics. | No duplicates. |
| INT-FR-007 | Payload hash | Same idempotency key with different payload hash is conflict/integrity incident. | Tamper/drift detection. |
| INT-FR-008 | Uncertain timeout | Timeout after external request may represent committed external transaction; reconcile before replaying create where duplicate risk exists. | Exactly-once effect strategy. |
| INT-FR-009 | External correlation | Store vendor request/job/doc/reference IDs on every successful/uncertain attempt. | Investigability. |
| INT-FR-010 | Inbound dedupe | Unique external event/message ID + source instance and payload hash. | Replay safe. |
| INT-FR-011 | Out-of-order events | Process version/sequence-aware; stale events cannot overwrite newer projection. | Ordering. |
| INT-FR-012 | Dead letter | Retain failed original payload hash/reference, attempts/errors and required next action. | No loss. |
| INT-FR-013 | Manual replay | Authorized replay uses exact original payload unless a new corrected command is explicitly created. | Integrity. |
| INT-FR-014 | Corrected command | Business correction creates new command ID linked to original; never mutate original command payload. | History. |
| INT-FR-015 | Cancellation | Pending command may be cancelled/superseded only before confirmed external commit and with reason. | State clarity. |
| INT-FR-016 | Compensation | External reversal/compensation is a new integration command tied to authorized GxP correction/disposition. | No hidden rollback. |
| INT-FR-017 | Reconciliation types | MISSING_EXTERNAL, EXTRA_EXTERNAL, VALUE_MISMATCH, STATUS_MISMATCH, REFERENCE_MISMATCH, DUPLICATE_EXTERNAL, STALE_MAPPING. | Structured drift. |
| INT-FR-018 | Reconciliation snapshot | Report records source cutoff, query keys, external response refs and mapping versions. | Reproducible. |
| INT-FR-019 | Auto-resolve | Only benign known differences/duplicates may auto-resolve under released rule; quantity/status mismatches require review. | Safe. |
| INT-FR-020 | Integration hold | Critical unresolved integration mismatch can create operational/QA review flag according to module policy. | Risk. |
| INT-FR-021 | SLA/aging | Track oldest pending, retry age, dead-letter age and reconciliation age. | Operations. |
| INT-FR-022 | Circuit breaker | Per-instance breaker protects repeated transient vendor failures without losing queued commands. | Stability. |
| INT-FR-023 | Bulk jobs | Bulk import/export job tracks record-level successes/failures and supports idempotent resume. | Scale. |
| INT-FR-024 | Rate limiting | Per provider/operation quotas configured. | Vendor-safe. |
| INT-FR-025 | Security event | Unexpected payload hash/idempotency conflict/source identity mismatch raises security/data-integrity event. | Detection. |
| INT-FR-026 | Observability | Metrics/logs/traces include correlation IDs but redact sensitive credentials/content. | Support. |
| INT-FR-027 | Audit | Manual retry/remap/cancel/reconcile resolution audited. | Accountability. |
| INT-FR-028 | Retention | Integration ledgers retained long enough to support regulated-record investigation and external reconciliation. | Evidence. |
| INT-FR-029 | Chaos testing | Simulate network partitions, lost responses, duplicates, throttling, partial bulk failure and provider outage. | Reliability. |
| INT-FR-030 | No silent success | UI never displays external posting successful until Integration Gateway has confirmed/reconciled it. | Truth. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| classifyIntegrationError() | Adapter/client | provider response/exception; operation profile | CanonicalIntegrationError | none |
| computeRetryDecision() | Worker | command; canonical error; retry policy; attempt history | RetryDecision | none |
| scheduleRetry() | Worker | command_id; RetryDecision | RetrySchedule | IntegrationRetryScheduled |
| markDeadLetter() | Worker | command_id; terminal error | DeadLetterReceipt | IntegrationDeadLettered |
| ensureIdempotency() | Outbound handler | idempotency_key; payload_hash; source_event | IdempotencyDecision | IDEMPOTENCY_PAYLOAD_CONFLICT |
| dedupeInboundEvent() | Inbound handler | erp_instance_id; external_event_id; payload_hash | InboundDedupeDecision | INBOUND_EVENT_CONFLICT |
| reconcileUncertainCommit() | Worker | command_id; provider lookup strategy | UncertainCommitResolution | ExternalCommitFound/NotFound |
| createReconciliationRun() | Scheduler/Admin | instance; reconciliation_type/scope; cutoff | ReconciliationRun | ReconciliationStarted |
| recordReconciliationDifference() | Reconciliation processor | run_id; difference type; internal/external evidence | ReconciliationDifference | ReconciliationMismatchDetected |
| resolveReconciliationDifference() | Integration/Data Owner | difference_id; resolution; reason; correction refs | ResolutionReceipt | ReconciliationResolved |
| tripCircuitBreaker() | Worker policy | instance/operation; failure window | CircuitBreakerState | ERPIntegrationCircuitOpened |
| closeCircuitBreaker() | Health probe | instance/operation | CircuitBreakerState | ERPIntegrationCircuitClosed |

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
- 500 error retry
- 400 validation no retry
- 429 Retry-After
- timeout after vendor commit
- duplicate idempotency same hash
- duplicate idempotency different hash
- inbound duplicate event
- out-of-order inbound version
- dead-letter replay
- corrected new command
- circuit breaker
- bulk partial failure
- reconciliation missing external posting
- extra external transaction
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-07/Document_53_SPEC-ERP-006_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-ERP-006/<test_case_id>/`.
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
