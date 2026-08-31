# US eBMR / eDHR Regulated Manufacturing Platform
## Document 78 — Performance, Capacity, Observability, SLOs & SRE Operations — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DATA-010  
**Parent Documents:** Documents 01–68  
**Primary Dependencies:** Documents 01–77; all services and deployment profiles  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This specification is intended for direct ingestion by Claude Code, Codex, and human engineering/operations teams.

Before implementation, the coding agent shall extract this document into:

1. requirement registry;
2. module/submodule and infrastructure-component map;
3. function/service contract catalogue;
4. typed input/output schemas;
5. database/storage ownership map;
6. data lifecycle and retention map;
7. API/event contracts;
8. transaction and concurrency model;
9. availability and failure-mode model;
10. backup/restore/DR controls;
11. observability/SLO/capacity controls;
12. configuration and deployment contracts;
13. positive/negative/failure/concurrency/restore tests;
14. requirement-to-test traceability.

For every public/domain/infrastructure function specified here, preserve:

- function name and purpose;
- caller/trigger;
- typed inputs and source;
- authorization/qualification/SoD/signature prerequisites where applicable;
- preconditions and validations;
- database/storage reads;
- database/storage writes;
- transaction boundary;
- output/result;
- emitted/consumed events;
- downstream consumers;
- stable errors;
- idempotency/concurrency;
- audit/operational evidence;
- observability;
- test obligations.

If a missing decision changes regulated behavior, data durability, recovery semantics, or infrastructure trust boundaries, create a `SPEC_GAP` rather than guessing.

# Data / Infrastructure Architectural Invariants

- PostgreSQL is the authoritative database for proprietary GxP Core regulated state.
- MariaDB is the Frappe operational/UI/configuration database and may contain projections, workflow/UI metadata, and non-authoritative application state.
- A regulated authoritative entity must not be dual-mastered between PostgreSQL and MariaDB.
- Immutable/released evidence and large binary artifacts are stored in object storage through Evidence/Vault services with content hashes and retention/WORM controls.
- NATS/JetStream is an asynchronous event-delivery layer. The authoritative event/outbox record originates from the same PostgreSQL transaction as the GxP state change.
- Temporal coordinates long-running processes and retries but is not the regulatory system of record.
- Redis/cache/search indexes are disposable/rebuildable accelerators or projections; they are never the only copy of regulated truth.
- Kubernetes, VM disks, PVCs and replicas are runtime infrastructure; none of them substitute for tested backups.
- Every persistent component must have explicit backup, restore, retention, encryption, monitoring, ownership and recovery behavior.
- Data retention/deletion is controlled by regulatory/product/customer/legal-hold policy and cannot be inferred from storage cost alone.

# Current Technical Reference Baseline

- PostgreSQL current official documentation is on major version 18. PostgreSQL WAL, replication, backup and declarative partitioning are used as reference capabilities, but deployment shall pin a validated supported version rather than follow `latest`.
- PostgreSQL WAL and archived WAL support crash recovery and point-in-time recovery architectures when correctly configured.
- NATS/JetStream provides durable streams/consumers and messaging primitives; application-level outbox/idempotency remains mandatory.
- Temporal provides durable workflow execution/recovery; workflow code must remain deterministic and activities must isolate external side effects.
- Kubernetes StatefulSets can provide stable identity/storage mechanics for stateful workloads, but production database/object-store deployment may also use managed services or dedicated operators/VMs depending on deployment profile.

Primary references:
- https://www.postgresql.org/docs/current/
- https://www.postgresql.org/docs/current/wal.html
- https://www.postgresql.org/docs/current/ddl-partitioning.html
- https://docs.nats.io/
- https://docs.temporal.io/
- https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
- https://kubernetes.io/docs/concepts/services-networking/network-policies/

# 1. Objective

Define measurable scale, performance, capacity, observability, graceful degradation and operational reliability targets so the platform can support enterprise plants without discovering architecture limits during customer deployment.

# 2. Actors / Components

- SRE
- Performance Engineer
- Platform Engineer
- DBA
- Edge Engineer
- Product Owner
- QA/Validation
- Customer Operations

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
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


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| recordServiceLevelObjective() | SRE/Product | capability; SLI; target; window; deployment profile | Owner/measurement defined | Stores versioned SLO and alert/error-budget metadata | SLODefinition | ServiceLevelObjectiveDefined |
| calculateCapacityForecast() | Capacity job | current metrics; growth assumptions; retention; horizon | Metrics sufficient; model version approved | Forecasts CPU/memory/DB/storage/event/object/Edge needs with headroom | CapacityForecast | CapacityForecastGenerated |
| runSyntheticLoadScenario() | Performance environment | scenario version; target scale; duration | Environment isolated/representative; synthetic data | Executes workload, captures latency/throughput/errors/resource metrics | LoadTestReport | LoadTestCompleted |
| evaluateReleasePerformanceGate() | CI/release | baseline report; candidate report; allowed regressions | Comparable test scenario | Returns pass/warn/block by critical operation thresholds | PerformanceGateDecision | PerformanceRegressionDetected |
| emitPlatformMetric() | Any component | metric name/value/labels | Metric registered; labels bounded | Exports metric to observability pipeline | MetricReceipt | none |
| startTraceSpan() | Request/service middleware | trace context; operation; safe attributes | Tracing enabled/sample policy | Creates span with correlation and redacted attributes | TraceSpan | none |
| evaluateOperationalAlert() | Monitoring | metrics/logs/events; alert rule version | Rule effective | Creates deduplicated alert if business-impact condition met | OperationalAlert | OperationalAlertRaised |
| executeCapacityScalingPlan() | SRE/automation | service/component; approved scaling action | Forecast/alert and permissions | Scales stateless component or raises stateful resize/change task | ScalingReceipt | CapacityScaled |
| verifyGracefulDegradation() | Resilience test | failed dependency; expected capability matrix | Test environment/safe injection | Confirms affected/unaffected operations behave as designed | DegradationTestReport | GracefulDegradationVerified |


# 5. State / Runtime / Ownership Model

```text
WORKLOAD / CUSTOMER GROWTH
       ↓
SLIs + CAPACITY METRICS
       ↓
SLO / FORECAST
   ├→ NORMAL
   ├→ SCALE
   ├→ TUNE
   └→ ARCHITECTURAL CAPACITY REVIEW

REQUEST → TRACE → SERVICE → DB/OUTBOX → EVENT/CONSUMER
          ↓ metrics/logs
      DASHBOARD/ALERT
          ↓
        RUNBOOK

```

# 6. Data / Configuration Model

## Initial capacity assumptions to validate

```text
10+ plants per customer
50+ batches/day/plant
~1000 normal steps/batch with several thousand supported
50 concurrent users/plant
250+ concurrent/customer
hundreds of equipment/data sources/site
millions of audit events/day possible
10+ year regulatory retention
```

These are design targets, not a promise without validated customer sizing.

## `slo_definition`
- capability
- SLI formula/data source
- target
- evaluation window
- deployment profile
- error budget/alert rules

## `capacity_forecast`
- component/resource
- current usage
- growth assumptions
- forecast horizon
- required headroom
- threshold/date
- recommended action


# 7. APIs / Internal Interfaces

- `Metrics/OTel endpoints`
- `SLO/capacity APIs internal`
- `Performance-test harness`
- `Alert/runbook integrations`

# 8. UI / Operations Screens

1. Executive Reliability
2. GxP API
3. Database
4. NATS/Outbox
5. Temporal
6. Edge Fleet
7. Object Evidence
8. Projection Freshness
9. Capacity Forecast
10. Backup/DR

# 9. Events / Operational Signals

- `OperationalAlertRaised`
- `PerformanceRegressionDetected`
- `CapacityThresholdForecasted`
- `ProjectionLagExceeded`
- `OutboxLagExceeded`
- `DatabaseSaturationDetected`
- `GracefulDegradationVerified`

# 10. Failure / Recovery Rules

- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

# 11. Repository Structure

```text
infrastructure/performance-capacity-observability-slos-sre-operations/
services/platform/performance-capacity-observability-slos-sre-operations/
packages/data-contracts/
validation/infrastructure/performance-capacity-observability-slos-sre-operations/
tests/infrastructure/performance-capacity-observability-slos-sre-operations/
docs/runbooks/performance-capacity-observability-slos-sre-operations/
```

# 12. Mandatory Test Catalogue

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

# 13. Acceptance Criteria

At target reference scale, the platform has documented load-test evidence, component capacity forecasts, operational SLOs and runbooks, and can identify the next bottleneck before capacity exhaustion.

# 14. Claude Code / Codex Prohibitions

- Never optimize by disabling fsync/WAL durability or audit evidence.
- Never declare capacity from CPU alone.
- Never allow observability labels to include unbounded batch/user IDs by default.
- Never run heavy arbitrary reports on primary GxP DB without workload controls.

# 15. Required Claude Code Artifact

Generate `27_CAPACITY_SLO_OBSERVABILITY_MODEL.md` mapping each critical capability to load assumptions, SLI/SLO, dashboards, alerts, runbooks and scaling bottlenecks.

