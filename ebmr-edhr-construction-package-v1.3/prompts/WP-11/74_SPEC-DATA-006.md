# Claude Code prompt — WP-11 / Document 74: Temporal Durable Workflow Orchestration Architecture

TASK:
Implement the Temporal Durable Workflow Orchestration Architecture module (SPEC-DATA-006) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_74_Temporal_Durable_Workflow_Orchestration_Architecture_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: TMP-FR-001..030 (30)
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
- `infrastructure` and its tests
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
infrastructure/src/            # domain services, command handlers, repositories
infrastructure/migrations/     # owned entities only
infrastructure/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-data-006.yaml
contracts/events/spec-data-006/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-data-006/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| TMP-FR-001 | Temporal role | Temporal coordinates long-running workflows/retries/timers/human waits; domain state remains GxP authoritative. | Boundary. |
| TMP-FR-002 | Workflow identity | Workflow ID derived from stable business process identity to prevent accidental duplicate orchestration. | Idempotency. |
| TMP-FR-003 | Deterministic workflow | Workflow code must be deterministic/replay-safe; external calls/DB writes occur only in Activities. | Temporal correctness. |
| TMP-FR-004 | Activity idempotency | Activities performing side effects use GxP/integration idempotency keys. | Retry safe. |
| TMP-FR-005 | Workflow versioning | Code changes use Temporal-supported versioning/deployment strategy; in-flight workflows remain compatible. | Upgrade safety. |
| TMP-FR-006 | No regulatory truth | Temporal search attributes/history are not official batch/QMS/release records. | Clear authority. |
| TMP-FR-007 | Domain command | Workflow Activity calls GxP API/Mutation Gateway and waits for receipt/result. | Correct mutation. |
| TMP-FR-008 | Signals | Human/external decisions enter workflow through authenticated service that first persists authoritative domain decision where appropriate. | No hidden decision. |
| TMP-FR-009 | Queries | Workflow queries are operational view only; regulated UI fetches domain authoritative state. | Freshness. |
| TMP-FR-010 | Timers | Due dates/escalations/timed waits can use durable Temporal timers while due-date source remains domain/regulatory record. | Scheduling. |
| TMP-FR-011 | Retry policy | Activity retry/backoff explicitly defined by error class; business validation/signature denial not retried blindly. | Correct recovery. |
| TMP-FR-012 | Timeouts | Start-to-close/schedule-to-close/heartbeat timeouts configured by activity. | Bounded. |
| TMP-FR-013 | Heartbeats | Long-running activities heartbeat progress/cancellation as applicable. | Recovery. |
| TMP-FR-014 | Cancellation | Workflow cancellation maps to authorized domain cancellation/compensation rules; never silently abandons regulated process. | Controlled. |
| TMP-FR-015 | Compensation | Saga compensation is new domain transaction, not rollback of immutable GxP history. | History. |
| TMP-FR-016 | Human tasks | Temporal may wait for QA/action completion but task authority/status exists in domain/QMS record. | No workflow-only task. |
| TMP-FR-017 | Child workflows | Use child workflows for bounded subprocesses where ownership/lifecycle warrants; avoid monolithic eternal workflow. | Maintainability. |
| TMP-FR-018 | Continue-as-new | Long histories use continue-as-new with business identity/correlation preserved. | Scale. |
| TMP-FR-019 | Namespace | Separate environment/customer deployment namespace/profile; production isolated from non-prod. | Isolation. |
| TMP-FR-020 | Worker identity | Workers use service identities with only required GxP/integration scopes. | Security. |
| TMP-FR-021 | Task queues | Queues partitioned by domain/workload/priority; worker deployment/version controlled. | Operations. |
| TMP-FR-022 | Temporal HA | Self-hosted/managed deployment profile meets availability/backup requirements for orchestration state. | Reliability. |
| TMP-FR-023 | Temporal outage | Existing GxP records remain valid; new/continuing orchestration pauses/degrades explicitly and resumes after recovery. | Resilience. |
| TMP-FR-024 | GxP DB outage | Activities fail/retry; workflows never invent successful domain transition. | Truth. |
| TMP-FR-025 | Visibility | Workflow ID/run/status/activity failures/correlation visible in operations UI, not as regulated source. | Support. |
| TMP-FR-026 | Audit linkage | Domain records store workflow/correlation IDs for troubleshooting; GxP Audit logs actual regulated action. | Cross-reference. |
| TMP-FR-027 | Security | Temporal Web/admin protected; workers TLS/auth; no unrestricted public access. | Security. |
| TMP-FR-028 | Data minimization | Workflow payloads avoid large evidence/PII; use IDs/references. | Efficiency/privacy. |
| TMP-FR-029 | Backup/restore | Temporal persistence backed up per deployment; restore tested for orchestration continuity, not GxP data recovery. | DR. |
| TMP-FR-030 | Testing | Workflow replay tests, time-skipping tests, activity failure/retry and version compatibility mandatory. | Assurance. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| startBusinessWorkflow() | Domain service after authoritative creation | workflow_type; business_id; initial refs; correlation | WorkflowRef | WorkflowStarted/WORKFLOW_ALREADY_EXISTS |
| executeGxPActivity() | Temporal Activity | operationId; command DTO; idempotency key; expected version | GxPActionReceipt | ActivityCompleted/GXP_API_FAILURE |
| scheduleRegulatoryTimer() | Workflow logic | domain obligation ID; due_at; escalation offsets | TimerPlan | RegulatoryTimerScheduled |
| receiveDomainSignal() | Domain event bridge | workflow ID; signal type; authoritative record/version | SignalReceipt | WorkflowSignaled |
| compensateBusinessStep() | Workflow Activity | source action ref; authorized compensation command | CompensationReceipt | CompensationExecuted |
| continueLongWorkflow() | Workflow | carry-forward state refs/version | NewRunRef | WorkflowContinuedAsNew |
| queryWorkflowOperations() | Ops UI | workflow ID | WorkflowOperationalView | none |
| replayWorkflowTest() | CI | historical workflow history fixture; new worker code | ReplayTestResult | TEMPORAL_NONDETERMINISM |

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

EVENTS (5):
| Event type | Producer | Dedupe key |
|---|---|---|
| `WorkflowStarted` | SPEC-DATA-006 | event_id |
| `WorkflowStuckDetected` | SPEC-DATA-006 | event_id |
| `TemporalWorkerVersionChanged` | SPEC-DATA-006 | event_id |
| `WorkflowCompensationExecuted` | SPEC-DATA-006 | event_id |
| `TemporalNamespaceUnavailable` | SPEC-DATA-006 | event_id |

UI SURFACES:
- Workflow Operations
- Stuck/Failed Activities
- Timer/Deadline Operations
- Worker Version/Task Queues
- Replay Compatibility

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- activity retry after timeout
- business validation not retried
- workflow code replay after upgrade
- duplicate start
- signal duplicate/out-of-order
- Temporal outage/recovery
- GxP outage
- continue-as-new
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-11/Document_74_SPEC-DATA-006_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DATA-006/<test_case_id>/`.
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
