# US eBMR / eDHR Regulated Manufacturing Platform
## Document 73 — NATS / JetStream Event Bus, Transactional Outbox & Async Contracts — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DATA-005  
**Parent Documents:** Documents 01–68  
**Primary Dependencies:** Documents 03, 43–53, 69–70; all async projections/integrations  
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

Define event contracts and reliable asynchronous delivery using PostgreSQL transactional outbox plus NATS/JetStream, including idempotent consumers, schema governance, replay, DLQ and broker-failure behavior.

# 2. Actors / Components

- Domain Service
- Outbox Publisher
- NATS/JetStream
- Projection Consumer
- Integration Consumer
- Security/Platform Admin
- Schema Registry/CI

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| EVT-FR-001 | Canonical event envelope | Every event has event_id, type, schema version, aggregate id/version, tenant/site, correlation/causation, occurred_at and payload. | Stable contract. |
| EVT-FR-002 | Transactional outbox | Authoritative GxP event inserted in same PostgreSQL transaction as domain state/audit. | Atomic source. |
| EVT-FR-003 | Outbox publisher | Publisher reads committed pending events and publishes to NATS/JetStream idempotently. | Reliable delivery. |
| EVT-FR-004 | Publish acknowledgement | Outbox marked published only after broker acknowledgement according to configured durable stream semantics. | No lost publish. |
| EVT-FR-005 | At-least-once consumers | Consumers assume duplicate delivery and must be idempotent. | Correct distributed model. |
| EVT-FR-006 | Consumer inbox/dedupe | Critical consumer maintains processed event IDs/result/version to prevent duplicate business effect. | Replay safe. |
| EVT-FR-007 | Subject naming | Versioned subject namespace includes environment/domain/event but avoids leaking sensitive data in subject names. | Operable. |
| EVT-FR-008 | Stream configuration | Durable streams define retention, storage, replicas, max age/size and permissions per event class. | Controlled messaging. |
| EVT-FR-009 | Consumer durability | Durable named consumers with explicit ack/retry/backoff for critical projections/integrations. | Recovery. |
| EVT-FR-010 | Dead letter strategy | Poison events moved/recorded for manual review after bounded attempts without deleting original event. | No loss. |
| EVT-FR-011 | Schema registry | JSON Schema/AsyncAPI event definitions versioned and CI compatibility-tested. | Contract governance. |
| EVT-FR-012 | Backward compatibility | Compatible additive changes preferred; breaking change uses new schema/event version and migration plan. | Safe evolution. |
| EVT-FR-013 | No sensitive payload excess | Event payload minimizes PII/secrets; sensitive content uses reference when possible. | Security. |
| EVT-FR-014 | Ordering | Per aggregate version ordering validated; consumers handle late/out-of-order events and reject stale projections. | Consistency. |
| EVT-FR-015 | No global ordering assumption | Architecture never assumes total order across all aggregates/services. | Scale. |
| EVT-FR-016 | Replay | Authorized stream/outbox replay uses event identity/version and does not re-execute non-idempotent business effect incorrectly. | Recovery. |
| EVT-FR-017 | Backfill tag | Bulk/projector rebuild may use source snapshot/events with explicit replay/backfill context. | Semantics. |
| EVT-FR-018 | Broker outage | Domain transaction still commits with outbox; publisher catches up after broker recovery. | Resilience. |
| EVT-FR-019 | Database outage | Publisher/consumer does not fabricate state; broker retention alone cannot commit GxP truth. | Boundary. |
| EVT-FR-020 | NATS auth | Service identities have publish/subscribe ACLs limited to required subjects. | Security. |
| EVT-FR-021 | TLS | NATS connections TLS/mTLS according to deployment profile. | Transport security. |
| EVT-FR-022 | Multi-tenant subjects | Dedicated deployment baseline still carries tenant/site in envelope; ACL/subject design prevents accidental cross-scope. | Isolation. |
| EVT-FR-023 | Large payload | Large files stay object store; event contains evidence ref/hash, not multi-MB blobs. | Scale. |
| EVT-FR-024 | Event retention | Broker retention chosen for operational replay, not regulatory long-term archive; authoritative event/audit/evidence retention remains elsewhere. | Boundary. |
| EVT-FR-025 | Observability | Outbox age, publish lag, stream lag, consumer ack pending, redelivery and DLQ monitored. | Operations. |
| EVT-FR-026 | Consumer failure policy | Business validation failure differs from transient dependency failure; poison event does not retry forever. | Stability. |
| EVT-FR-027 | Projection consumers | Projection worker stores source aggregate/event version and ignores duplicate/stale event safely. | Correct projection. |
| EVT-FR-028 | Integration consumers | ERP/LIMS/Edge integration commands derive from source event and own idempotency/reconciliation. | Integration safety. |
| EVT-FR-029 | Schema ownership | Event producer owns schema; consumers cannot reinterpret fields inconsistently. | Governance. |
| EVT-FR-030 | No event-sourcing assumption | The platform uses events/outbox for integration; not every domain aggregate is rebuilt solely from broker events unless explicitly specified. | Architecture clarity. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| appendDomainOutboxEvent() | Domain transaction | canonical event envelope | Active authoritative DB tx; event ID unique | Inserts gxp_outbox row transactionally | OutboxRef | OUTBOX_EVENT_APPENDED |
| claimOutboxBatch() | Outbox publisher | batch size; lease duration; now | Publisher DB role; pending records | Claims ordered rows using safe skip-locked/lease pattern | OutboxBatch | none |
| publishOutboxEvent() | Publisher | outbox event; subject mapping | NATS connection/auth; schema valid | Publishes to JetStream with event/message ID; waits broker ack | PublishReceipt | EVENT_PUBLISHED/BROKER_UNAVAILABLE |
| markOutboxPublished() | Publisher | outbox_id; publish receipt | Receipt matches event | Updates operational publish state/attempt; authoritative event immutable | void | OUTBOX_PUBLISH_STATE_CONFLICT |
| consumeEventIdempotently() | Consumer wrapper | event envelope; handler ID | Schema/auth scope valid | Checks inbox; invokes handler in transaction; records event processed/result | ConsumerReceipt | EVENT_ALREADY_PROCESSED/HANDLER_FAILED |
| handlePoisonEvent() | Consumer supervisor | event; failure history; policy | Retry threshold reached/nonretryable | Records DLQ/manual-review item and alert; retains event refs | DeadLetterRef | EventDeadLettered |
| replayConsumerEvents() | Integration Admin | consumer; event range/filter; reason | Authorized; handler idempotent/replay tested | Resets/requeues/reprocesses with replay context and evidence | ReplayJob | EventReplayStarted |
| verifyEventSchemaCompatibility() | CI | old/new JSON schema/AsyncAPI | Schema registry available | Checks compatibility rules and breaking changes | CompatibilityReport | EVENT_SCHEMA_BREAKING_CHANGE |


# 5. State / Runtime / Ownership Model

```text
GxP TRANSACTION
    ├ domain state
    ├ audit/version
    └ OUTBOX(PENDING)
          ↓ publisher
      NATS/JETSTREAM
          ↓ durable consumers
   ┌──────┼──────────┐
Projection Integration Notifications
   ↓          ↓
INBOX/DEDUPE + idempotent handler

Broker down → outbox grows → catch up after recovery

```

# 6. Data / Configuration Model

## `gxp_outbox`
```text
event_id uuid PK
aggregate_type/id/version
event_type/schema_version
tenant_id/site_id
payload jsonb
correlation_id/causation_id
occurred_at
publish_state
attempt_count
next_attempt_at
published_at
```

## `consumer_inbox`
```text
consumer_name
event_id
payload_hash
processed_at
result_ref
PRIMARY KEY (consumer_name,event_id)
```

## Event envelope

```json
{
  "event_id":"uuid",
  "event_type":"BatchStepCompleted",
  "schema_version":"1.0",
  "aggregate":{"type":"Batch","id":"...","version":42},
  "tenant_id":"...",
  "site_id":"...",
  "correlation_id":"...",
  "causation_id":"...",
  "occurred_at":"...",
  "payload":{}
}
```


# 7. APIs / Internal Interfaces

- `Internal outbox publisher`
- `NATS subjects/streams`
- `AsyncAPI catalogue`
- `Admin replay/DLQ interfaces`

# 8. UI / Operations Screens

1. Event Stream Health
2. Outbox Lag
3. Consumer Lag
4. Dead Letters
5. Schema Registry
6. Replay Jobs

# 9. Events / Operational Signals

- `EventPublished`
- `EventDeadLettered`
- `EventReplayStarted`
- `EventSchemaBreakingChangeDetected`
- `ConsumerLagExceeded`
- `OutboxLagExceeded`

# 10. Failure / Recovery Rules

- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

# 11. Repository Structure

```text
infrastructure/nats-jetstream-event-bus-transactional-outbox-async-contracts/
services/platform/nats-jetstream-event-bus-transactional-outbox-async-contracts/
packages/data-contracts/
validation/infrastructure/nats-jetstream-event-bus-transactional-outbox-async-contracts/
tests/infrastructure/nats-jetstream-event-bus-transactional-outbox-async-contracts/
docs/runbooks/nats-jetstream-event-bus-transactional-outbox-async-contracts/
```

# 12. Mandatory Test Catalogue

- DB commit while NATS down
- publish ack lost then duplicate retry
- consumer crash after side effect before ack
- out-of-order aggregate version
- poison event
- schema additive change
- breaking schema blocked
- large evidence ref

# 13. Acceptance Criteria

A committed GxP transaction cannot lose its required downstream event because of a broker outage, and redelivery cannot create duplicate regulated business effects.

# 14. Claude Code / Codex Prohibitions

- Never publish event before authoritative DB commit.
- Never delete outbox because broker is unavailable.
- Never assume NATS exactly-once semantics remove need for application idempotency.
- Never place large evidence files or secrets in event payloads.


