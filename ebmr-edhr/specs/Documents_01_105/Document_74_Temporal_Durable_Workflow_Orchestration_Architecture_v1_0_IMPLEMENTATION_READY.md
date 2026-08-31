# US eBMR / eDHR Regulated Manufacturing Platform
## Document 74 — Temporal Durable Workflow Orchestration Architecture — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DATA-006  
**Parent Documents:** Documents 01–68  
**Primary Dependencies:** Documents 02–03, 11, 26–37, 48–60, 69–73  
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

Define how Temporal coordinates long-running batch/QMS/regulatory/integration workflows without becoming the regulatory system of record, including deterministic workflow code, idempotent Activities, timers, compensation and upgrade/replay behavior.

# 2. Actors / Components

- Temporal Service
- Workflow Worker
- Activity Worker
- GxP API
- QMS/Regulatory Modules
- Operations/SRE
- Developer/CI

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
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


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| startBusinessWorkflow() | Domain service after authoritative creation | workflow_type; business_id; initial refs; correlation | Domain record exists; workflow profile effective | Starts workflow with deterministic ID; duplicate start returns existing run/defined policy | WorkflowRef | WorkflowStarted/WORKFLOW_ALREADY_EXISTS |
| executeGxPActivity() | Temporal Activity | operationId; command DTO; idempotency key; expected version | Worker authorized; domain dependency available | Calls GxP API; stores only activity result/history in Temporal | GxPActionReceipt | ActivityCompleted/GXP_API_FAILURE |
| scheduleRegulatoryTimer() | Workflow logic | domain obligation ID; due_at; escalation offsets | Due date already authoritative | Creates durable timers; no due-date ownership transfer | TimerPlan | RegulatoryTimerScheduled |
| receiveDomainSignal() | Domain event bridge | workflow ID; signal type; authoritative record/version | Source event authenticated/current | Signals workflow with ref/version; workflow validates duplicate/stale signal | SignalReceipt | WorkflowSignaled |
| compensateBusinessStep() | Workflow Activity | source action ref; authorized compensation command | Compensation allowed by domain rules | Calls domain API to create new correction/reversal/disposition transaction | CompensationReceipt | CompensationExecuted |
| continueLongWorkflow() | Workflow | carry-forward state refs/version | History threshold/profile met | Continues-as-new preserving business workflow ID/correlation | NewRunRef | WorkflowContinuedAsNew |
| queryWorkflowOperations() | Ops UI | workflow ID | Ops authorization | Returns operational status/activity failures/timers only | WorkflowOperationalView | none |
| replayWorkflowTest() | CI | historical workflow history fixture; new worker code | Fixture/version known | Replays deterministically and detects nondeterminism | ReplayTestResult | TEMPORAL_NONDETERMINISM |


# 5. State / Runtime / Ownership Model

```text
DOMAIN RECORD CREATED IN GxP
         ↓ event
START TEMPORAL WORKFLOW
         ↓
DETERMINISTIC WORKFLOW LOGIC
   ├ timer/wait
   ├ signal
   └ Activity → GxP/Integration API
                    ↓
             authoritative mutation
                    ↓
              domain event/signal
                    ↓
              workflow continues

Temporal lost → orchestration pauses
GxP truth remains authoritative

```

# 6. Data / Configuration Model

## Workflow metadata in GxP

```text
business_process_type
business_record_id
temporal_workflow_id
current_run_id (operational)
correlation_id
```

## Workflow payload rules

Carry IDs, versions, decision refs and small deterministic data. Evidence files and large records remain in GxP/Object Store.

## Initial workflow families

- batch lifecycle orchestration;
- QA review/release coordination;
- CAPA/effectiveness timers;
- deviation due/escalation;
- ERP/LIMS long-running integration where useful;
- postmarket/regulatory deadline/task orchestration.


# 7. APIs / Internal Interfaces

- `Temporal client internal interfaces`
- `Worker task queues`
- `Operations visibility adapter`

# 8. UI / Operations Screens

1. Workflow Operations
2. Stuck/Failed Activities
3. Timer/Deadline Operations
4. Worker Version/Task Queues
5. Replay Compatibility

# 9. Events / Operational Signals

- `WorkflowStarted`
- `WorkflowStuckDetected`
- `TemporalWorkerVersionChanged`
- `WorkflowCompensationExecuted`
- `TemporalNamespaceUnavailable`

# 10. Failure / Recovery Rules

- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

# 11. Repository Structure

```text
infrastructure/temporal-durable-workflow-orchestration-architecture/
services/platform/temporal-durable-workflow-orchestration-architecture/
packages/data-contracts/
validation/infrastructure/temporal-durable-workflow-orchestration-architecture/
tests/infrastructure/temporal-durable-workflow-orchestration-architecture/
docs/runbooks/temporal-durable-workflow-orchestration-architecture/
```

# 12. Mandatory Test Catalogue

- activity retry after timeout
- business validation not retried
- workflow code replay after upgrade
- duplicate start
- signal duplicate/out-of-order
- Temporal outage/recovery
- GxP outage
- continue-as-new

# 13. Acceptance Criteria

A multi-week CAPA or regulatory workflow can survive worker/service restarts and code deployment while all official decisions remain reproducible from authoritative domain records.

# 14. Claude Code / Codex Prohibitions

- Never store final regulated decision only in Temporal workflow state.
- Never perform external API/DB side effect directly in workflow code.
- Never use compensation to erase immutable GxP history.
- Never assume Temporal retry makes non-idempotent activity safe.


