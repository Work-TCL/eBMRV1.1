# US eBMR / eDHR Regulated Manufacturing Platform
## Document 70 — PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DATA-002  
**Parent Documents:** Documents 01–68  
**Primary Dependencies:** Documents 03–08, 69; all GxP services; Backup/DR  
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

Define the authoritative PostgreSQL construction standard for schema ownership, transactions, concurrency, audit/outbox atomicity, partitioning, indexes, performance, integrity and controlled migrations.

# 2. Actors / Components

- GxP Service
- Database Architect
- DBA
- Migration Runner
- SRE
- Validation
- Reporting Service

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| PG-FR-001 | Supported version pin | Deployment pins a supported PostgreSQL major/minor validated for product release; no automatic major upgrade. | Controlled platform. |
| PG-FR-002 | Cluster topology | Reference supports managed PostgreSQL or self-hosted HA profile with primary + replica(s) according to availability requirements. | Portable. |
| PG-FR-003 | Database separation | GxP PostgreSQL cluster/database separated from Frappe MariaDB and optionally from non-GxP analytics. | Clear boundary. |
| PG-FR-004 | Schema ownership | Schemas grouped by bounded context/service; owning service DB role owns migrations/tables. | Least privilege. |
| PG-FR-005 | Runtime roles | Runtime role gets minimum SELECT/INSERT/UPDATE/EXECUTE needed; DDL denied. | Security. |
| PG-FR-006 | Migration role | Migration role separate from runtime role and used only during controlled deployment. | Change control. |
| PG-FR-007 | UUID identity | UUIDv7/UUID or approved stable ID scheme used for distributed identities; DB sequences may supplement internal ordering. | Scalable identity. |
| PG-FR-008 | Optimistic version | Aggregate tables include bigint version and conditional UPDATE semantics. | Concurrency. |
| PG-FR-009 | Foreign keys | Use FKs within bounded context where lifecycle permits; cross-service references may be logical IDs/events to avoid forbidden coupling. | Integrity/boundary. |
| PG-FR-010 | Check constraints | Encode stable structural invariants such as valid ranges/states where appropriate; business configuration remains rules service. | Defense in depth. |
| PG-FR-011 | Unique constraints | Idempotency, external mapping, command receipt and semantic uniqueness enforced at DB level where possible. | Duplicate prevention. |
| PG-FR-012 | Transaction isolation | Default transaction isolation chosen deliberately; high-contention operations may use row locks/advisory locks/serializable only when specified. | Correctness. |
| PG-FR-013 | No long transactions | User think-time, signature challenge and external API calls never hold DB transaction open. | Availability. |
| PG-FR-014 | Outbox atomicity | Domain mutation + audit + version + outbox commit in same PostgreSQL transaction. | Reliable events. |
| PG-FR-015 | Append-only tables | Audit/event/version evidence tables use restricted roles and no normal UPDATE/DELETE path. | Integrity. |
| PG-FR-016 | Partitioning candidates | Very large audit/event/security/integration tables support declarative time partitioning with tested query/index strategy. | Scale. |
| PG-FR-017 | Partition key design | Partition key aligns retention/query pattern and uniqueness constraints; avoid tenant partitions explosion. | Operability. |
| PG-FR-018 | Indexes | Indexes derived from documented query patterns; avoid blanket indexing JSON/low-selectivity columns. | Performance. |
| PG-FR-019 | JSONB use | JSONB permitted for versioned payload/evidence/config snapshots while frequently queried relational keys remain columns/indexed. | Balanced modeling. |
| PG-FR-020 | Decimal/UOM | Use NUMERIC/decimal for regulated quantities/calculations, not float unless measurement representation specifically requires and raw semantics retained. | Precision. |
| PG-FR-021 | Timestamps | Use timestamptz UTC; source/local timezone metadata stored explicitly if needed. | Time. |
| PG-FR-022 | Database timezone | Server/session database timezone set/treated consistently as UTC for persisted regulatory timestamps. | Consistency. |
| PG-FR-023 | Data checksums | Deployment profile assesses/enables PostgreSQL data checksums or equivalent managed-service integrity controls. | Corruption detection. |
| PG-FR-024 | WAL | WAL/replication/archiving configuration supports crash recovery and chosen RPO/PITR profile. | Durability. |
| PG-FR-025 | Connection pooling | Use bounded connection pool/proxy; service pool sizes derived from DB max connections and workload. | Stability. |
| PG-FR-026 | Statement timeout | Per workload query/statement/lock timeouts configured to avoid runaway operations. | Resource control. |
| PG-FR-027 | Vacuum/analyze | Autovacuum/statistics monitored/tuned for high-write partitioned tables; manual maintenance runbooks controlled. | Performance. |
| PG-FR-028 | Slow query monitoring | pg_stat_statements/managed equivalent and slow-query tracing available without logging sensitive parameters indiscriminately. | Diagnostics. |
| PG-FR-029 | DDL safety | Online/low-lock migration patterns used for large tables; destructive schema changes staged and reversible where feasible. | Availability. |
| PG-FR-030 | Partition lifecycle | Future partitions created ahead of time; missing partition fails visibly; detach/archive/drop only via retention workflow. | Lifecycle. |
| PG-FR-031 | Replica reads | Reporting/read-only workloads may use replicas only where acceptable staleness is explicit; regulated command/signature reads use primary/authoritative consistency. | Correct reads. |
| PG-FR-032 | Integrity verification | Periodic DB/index checks and backup/restore verification monitored. | Assurance. |
| PG-FR-033 | Extensions | PostgreSQL extensions require allowlist/security/license/managed-service compatibility approval. | Controlled dependency. |
| PG-FR-034 | No direct repair | Emergency repair uses service-admin command/migration with evidence; ad-hoc SQL UPDATE is prohibited for regulated records. | Integrity. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| executeGxPTransaction() | Mutation Gateway/domain service | aggregate id/version; command payload; actor/context | Expected version valid; auth/rules/signature complete | BEGIN; lock/check version; domain writes; version/audit/outbox; COMMIT | MutationReceipt | GxPTransactionCommitted; STALE_VERSION/DB_TX_FAILED |
| applyOptimisticUpdate() | Repository | table/key; expected_version; changes | Expected version supplied | UPDATE ... WHERE id=? AND version=?; increment version; rowcount must equal 1 | UpdatedVersion | STALE_VERSION |
| appendOutboxEvent() | Domain transaction | event envelope | Inside active authoritative transaction | INSERT unique event/idempotency fields; no separate commit | OutboxRef | OUTBOX_DUPLICATE |
| createTimePartition() | Partition maintenance job | table; start/end; storage/index profile | Partition template approved; bounds non-overlap | Creates/attaches partition and indexes under migration/maintenance transaction | PartitionRef | PARTITION_CREATE_FAILED |
| verifyPartitionCoverage() | Preflight/monitor | table; future horizon | Partitioned table exists | Checks current/future time has target partitions; alerts before gap | CoverageReport | PARTITION_GAP_DETECTED |
| runDatabaseIntegrityCheck() | DBA automation | database/schema/table scope; check profile | Read-safe maintenance window/policy | Runs checksums/amcheck/managed integrity checks and captures evidence | IntegrityCheckReport | DB_INTEGRITY_FAILURE |
| getPrimaryConsistencyRead() | Regulated action service | entity/id; expected version | Primary available | Reads authoritative current version with required lock/consistency semantics | AuthoritativeRecord | PRIMARY_UNAVAILABLE |
| runReadReplicaQuery() | Reporting | report/query definition; max_staleness | Replica healthy and lag <= allowed threshold | Runs bounded read-only query | ReportDataset | REPLICA_TOO_STALE |


# 5. State / Runtime / Ownership Model

```text
GxP SERVICE
   ↓ pooled authenticated connection
POSTGRES PRIMARY
   ├ bounded-context schemas
   ├ domain tables
   ├ immutable versions/audit
   ├ outbox
   └ partitioned high-volume tables
      ↓ WAL/replication
READ REPLICA(S) / PITR ARCHIVE

```

# 6. Data / Configuration Model

## Schema convention

```text
gxp_core
gxp_audit
gxp_vault_meta
gxp_iam
gxp_rules
gxp_batch
gxp_materials
gxp_qc
gxp_qms
gxp_equipment
gxp_postmarket
integration
platform
```

Exact schema boundaries may be consolidated by service architecture, but ownership must remain explicit.

## Aggregate table baseline

```sql
id uuid PRIMARY KEY,
tenant_id uuid NOT NULL,
site_id uuid,
state text NOT NULL,
version bigint NOT NULL,
created_at timestamptz NOT NULL,
updated_at timestamptz NOT NULL
```

## High-volume partition candidates

- `gxp_audit_event` — monthly or workload-tested time partitions;
- `gxp_outbox` / processed archive;
- integration inbound/attempt ledgers;
- security event references if retained in PostgreSQL;
- selected high-volume execution/evidence summaries.

Partitioning must be justified by measured volume/query/retention, not applied to every table.


# 7. APIs / Internal Interfaces

- `Database repository interfaces internal to owning services`
- `Migration CLI`
- `DB health/metrics endpoints`
- `Read-only reporting interfaces`

# 8. UI / Operations Screens

1. Database/Schema Inventory
2. Partition Health
3. Connection/Lock Dashboard
4. Slow Query Dashboard
5. Integrity Checks
6. Migration History

# 9. Events / Operational Signals

- `DatabaseIntegrityFailure`
- `PartitionGapDetected`
- `ReplicaLagExceeded`
- `MigrationApplied`
- `DeadlockDetected`
- `ConnectionPoolExhausted`

# 10. Failure / Recovery Rules

- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

# 11. Repository Structure

```text
infrastructure/postgresql-gxp-database-architecture-schema-partitioning-concurrency/
services/platform/postgresql-gxp-database-architecture-schema-partitioning-concurrency/
packages/data-contracts/
validation/infrastructure/postgresql-gxp-database-architecture-schema-partitioning-concurrency/
tests/infrastructure/postgresql-gxp-database-architecture-schema-partitioning-concurrency/
docs/runbooks/postgresql-gxp-database-architecture-schema-partitioning-concurrency/
```

# 12. Mandatory Test Catalogue

- two concurrent expected-version updates
- deadlock retry
- outbox atomic rollback
- missing future partition
- replica lag regulated action uses primary
- large-table migration lock test
- database checksum/index corruption drill
- connection pool saturation

# 13. Acceptance Criteria

Authoritative GxP transactions remain atomic and reproducible under concurrency, and high-volume tables can scale without sacrificing immutable history or controlled retention.

# 14. Claude Code / Codex Prohibitions

- Never call external ERP/LIMS while DB transaction is open.
- Never use replica for signature target/current release decision unless explicitly allowed.
- Never update audit/version history in place.
- Never create generic ORM repository with unrestricted access to all schemas.

# 15. PostgreSQL Version Policy

The product supports a validated allowlist of PostgreSQL versions rather than coding to a single cloud vendor. As of this document date, PostgreSQL 18 is the current official documentation line; production deployment pins a tested version and upgrades through Change/Validation.

