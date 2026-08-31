# Claude Code prompt — WP-11 / Document 78: Performance, Capacity, Observability, SLOs & SRE Operations

TASK:
Implement the Performance, Capacity, Observability, SLOs & SRE Operations module (SPEC-DATA-010) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_78_Performance_Capacity_Observability_SLO_SRE_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: SRE-FR-001..036 (36)
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
contracts/openapi/spec-data-010.yaml
contracts/events/spec-data-010/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-data-010/
```

REQUIREMENTS TO IMPLEMENT (36):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| SRE-FR-001 | Service objectives | Define availability/latency/durability/freshness SLOs per critical capability, not one generic uptime number. | Meaningful reliability. |
| SRE-FR-002 | SLI | Measure API availability/latency, DB commit latency, queue lag, projection freshness, Edge delivery lag, evidence availability and restore readiness. | Observable. |
| SRE-FR-003 | Scale baseline | Design target includes 10+ plants/customer, 250+ concurrent/customer, 50+ batches/day/plant, thousands steps/batch and millions audit events/day without redesign. | Capacity. |
| SRE-FR-004 | Load model | Synthetic workload models users, batch steps, signatures, audit writes, events, equipment data, QC/QMS and reports. | Realistic testing. |
| SRE-FR-005 | Capacity unit | Define plant/customer capacity units and growth factors for DB, CPU, memory, storage, events and object evidence. | Forecast. |
| SRE-FR-006 | Headroom | Production capacity keeps configurable headroom for bursts/failover/maintenance. | Resilience. |
| SRE-FR-007 | API budgets | Critical interactive API p50/p95/p99 targets defined by operation class and tested. | UX. |
| SRE-FR-008 | Signature latency | Signature challenge/verify/commit measured independently. | Critical workflow. |
| SRE-FR-009 | Mutation throughput | Benchmark GxP mutation path including audit/outbox and concurrency. | Core performance. |
| SRE-FR-010 | Audit throughput | Audit partition/index/WAL capacity load tested at projected millions/day and burst rates. | Scale. |
| SRE-FR-011 | Event lag | Outbox/NATS/consumer lag SLOs and alerts. | Async health. |
| SRE-FR-012 | Projection freshness | Frappe/search/read model lag measured and surfaced. | UI correctness. |
| SRE-FR-013 | DB capacity | Monitor CPU, IOPS, WAL rate, storage growth, bloat, locks, connections, cache hit, replica lag. | DB operations. |
| SRE-FR-014 | Object capacity | Monitor object count/bytes, upload/download latency, archive tier, integrity failures, growth. | Evidence. |
| SRE-FR-015 | Temporal capacity | Monitor workflow starts, task-queue backlog, activity latency/failures, history size. | Orchestration. |
| SRE-FR-016 | Edge capacity | Per gateway connector/read rate, buffer depth, disk horizon and uplink bandwidth model. | Plant. |
| SRE-FR-017 | Report isolation | Heavy reports/exports use replicas/read models/async jobs and bounded resources. | Protect core. |
| SRE-FR-018 | Resource limits | CPU/memory limits avoid noisy-neighbor/OOM while not causing artificial throttling; based on measured load. | Runtime. |
| SRE-FR-019 | Autoscaling | Scale stateless services using safe metrics such as CPU, latency, queue depth, not DB connection count alone. | Elasticity. |
| SRE-FR-020 | Backpressure | Queues/workers apply bounded concurrency and backpressure instead of accepting infinite work. | Stability. |
| SRE-FR-021 | Rate limits | Protect expensive APIs/exports/integrations while preserving critical plant execution capacity. | Resilience. |
| SRE-FR-022 | Graceful degradation | Search/analytics/notifications may degrade independently; critical GxP execution dependency matrix defines what must stop. | Availability. |
| SRE-FR-023 | Health semantics | Liveness, readiness, startup and dependency health differentiated. | Correct orchestration. |
| SRE-FR-024 | Structured metrics | Prometheus/OpenTelemetry-compatible metrics with stable names/labels and cardinality controls. | Observability. |
| SRE-FR-025 | Distributed tracing | Trace critical request across Frappe/API/Mutation/DB/outbox/integration without leaking sensitive payloads. | Diagnostics. |
| SRE-FR-026 | Logs | Structured correlation IDs and redaction; no uncontrolled full request bodies. | Support/security. |
| SRE-FR-027 | Dashboards | Role-specific service, DB, batch-execution, integration, Edge, security and DR dashboards. | Operations. |
| SRE-FR-028 | Alert policy | Alerts linked to user/business impact with severity, runbook and dedupe; avoid noisy metric-only alerts. | Actionable. |
| SRE-FR-029 | Runbooks | Every critical alert/dependency has runbook including verification, containment and escalation. | Operational readiness. |
| SRE-FR-030 | Error budget | SLO error budget informs reliability work/release risk where organization adopts SRE practice. | Governance. |
| SRE-FR-031 | Soak test | Long-duration tests detect leaks, partition/outbox growth, worker drift and cache problems. | Stability. |
| SRE-FR-032 | Failure injection | Test DB failover, broker outage, Temporal outage, object-store latency, Edge reconnect and dependency throttling safely. | Resilience. |
| SRE-FR-033 | Capacity review | Quarterly/customer growth or threshold-triggered capacity review with forecast horizon. | Planning. |
| SRE-FR-034 | Storage forecast | Forecast relational, WAL, backup, object evidence, historian and logs separately. | Cost/reliability. |
| SRE-FR-035 | Performance regression | CI/release performance baseline detects critical regressions before production. | Quality. |
| SRE-FR-036 | No hidden optimization | Performance changes that alter regulated semantics, precision, retention or durability require explicit review. | Integrity. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| recordServiceLevelObjective() | SRE/Product | capability; SLI; target; window; deployment profile | SLODefinition | ServiceLevelObjectiveDefined |
| calculateCapacityForecast() | Capacity job | current metrics; growth assumptions; retention; horizon | CapacityForecast | CapacityForecastGenerated |
| runSyntheticLoadScenario() | Performance environment | scenario version; target scale; duration | LoadTestReport | LoadTestCompleted |
| evaluateReleasePerformanceGate() | CI/release | baseline report; candidate report; allowed regressions | PerformanceGateDecision | PerformanceRegressionDetected |
| emitPlatformMetric() | Any component | metric name/value/labels | MetricReceipt | none |
| startTraceSpan() | Request/service middleware | trace context; operation; safe attributes | TraceSpan | none |
| evaluateOperationalAlert() | Monitoring | metrics/logs/events; alert rule version | OperationalAlert | OperationalAlertRaised |
| executeCapacityScalingPlan() | SRE/automation | service/component; approved scaling action | ScalingReceipt | CapacityScaled |
| verifyGracefulDegradation() | Resilience test | failed dependency; expected capability matrix | DegradationTestReport | GracefulDegradationVerified |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `slo_definition` | 5 | PostgreSQL (GxP Core, authoritative) |
| `capacity_forecast` | 7 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (0):
_none declared in the source specifications_

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (7):
| Event type | Producer | Dedupe key |
|---|---|---|
| `OperationalAlertRaised` | SPEC-DATA-010 | event_id |
| `PerformanceRegressionDetected` | SPEC-DATA-010 | event_id |
| `CapacityThresholdForecasted` | SPEC-DATA-010 | event_id |
| `ProjectionLagExceeded` | SPEC-DATA-010 | event_id |
| `OutboxLagExceeded` | SPEC-DATA-010 | event_id |
| `DatabaseSaturationDetected` | SPEC-DATA-010 | event_id |
| `GracefulDegradationVerified` | SPEC-DATA-010 | event_id |

UI SURFACES:
- Executive Reliability
- GxP API
- Database
- NATS/Outbox
- Temporal
- Edge Fleet
- Object Evidence
- Projection Freshness
- Capacity Forecast
- Backup/DR

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
- 250 concurrent synthetic users
- 50 batches/day/plant
- million audit/day load
- DB failover under load
- NATS outage catch-up
- Temporal outage
- search outage critical execution continues
- object store slow upload
- 72h Edge backlog catch-up
- soak memory leak
- performance regression gate
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-11/Document_78_SPEC-DATA-010_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DATA-010/<test_case_id>/`.
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
