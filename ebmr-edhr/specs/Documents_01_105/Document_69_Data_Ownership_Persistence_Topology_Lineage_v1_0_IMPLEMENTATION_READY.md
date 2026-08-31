# US eBMR / eDHR Regulated Manufacturing Platform
## Document 69 — Enterprise Data Ownership, Persistence Topology & Data Lineage — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DATA-001  
**Parent Documents:** Documents 01–68  
**Primary Dependencies:** Documents 02–08, 43–53, 61–68; all domain modules  
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

Define the authoritative ownership of every data class and the rules for PostgreSQL, Frappe/MariaDB, object storage, historian, cache, search, messaging and orchestration so Claude Code never creates dual-master regulated data.

# 2. Actors / Components

- System Architect
- Domain Service
- Data Engineer
- DBA
- Frappe Developer
- Integration Service
- Validation
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| DATA-FR-001 | Authoritative-store registry | Every entity/data class has declared authoritative store/service owner and permitted projections. | No dual master. |
| DATA-FR-002 | PostgreSQL authority | Regulated GxP commands, record versions, signatures, audit, release/disposition, genealogy and other proprietary GxP state use PostgreSQL ownership. | Clear GxP truth. |
| DATA-FR-003 | MariaDB scope | Frappe/MariaDB owns UI/application metadata, Frappe users/config as applicable, DocTypes/projections and non-authoritative workflow conveniences. | Framework boundary. |
| DATA-FR-004 | Projection marking | Every Frappe/read/search projection declares source entity/version and rebuild mechanism. | No mistaken authority. |
| DATA-FR-005 | No cross-DB transaction assumption | No business invariant depends on atomic commit across PostgreSQL and MariaDB. | Distributed safety. |
| DATA-FR-006 | Postgres-first regulated mutation | Authoritative GxP state commits in PostgreSQL with audit/outbox; Frappe projection follows asynchronously or through explicit read-through. | Correct order. |
| DATA-FR-007 | Read path | UI may query Frappe projection for lists but must fetch authoritative detail/version for regulated action/signature where needed. | Freshness. |
| DATA-FR-008 | Staleness metadata | Projection exposes source version, projected_at and stale/degraded status. | Transparency. |
| DATA-FR-009 | Object-store ownership | Binary/raw evidence uses object storage; relational DB stores metadata/hash/links, not arbitrary large blobs by default. | Scale. |
| DATA-FR-010 | Historian ownership | High-frequency telemetry belongs in historian/time-series/Edge storage; GxP stores relevant evidence/result refs. | Tiering. |
| DATA-FR-011 | Search ownership | Search index is rebuildable projection and cannot determine official regulated value/state. | Search boundary. |
| DATA-FR-012 | Cache ownership | Cache is disposable and never sole source of permissions, signature target, release decision or regulated state. | Safe cache. |
| DATA-FR-013 | Temporal ownership | Temporal owns workflow execution history/coordination only; domain state belongs to GxP services. | Orchestration boundary. |
| DATA-FR-014 | NATS ownership | NATS/JetStream owns transport state only; business event source is PostgreSQL outbox/event record. | Messaging boundary. |
| DATA-FR-015 | External systems | ERP/LIMS/IdP/SCADA authority follows integration ownership matrix; external IDs remain references. | Integration clarity. |
| DATA-FR-016 | Entity identity | Internal immutable UUID/ID persists independently of external IDs/names. | Stable identity. |
| DATA-FR-017 | Version semantics | Regulated mutable records use optimistic aggregate version; released versions immutable. | Concurrency. |
| DATA-FR-018 | Timestamps | Server UTC authoritative receipt/transaction times; source times retained separately. | Chronology. |
| DATA-FR-019 | Decimal values | Regulated numeric values/calculations use exact decimal representation and explicit UOM/rounding. | No float drift. |
| DATA-FR-020 | Tenant/site key | Authoritative records carry tenant and site scope where applicable and are indexed/authorized consistently. | Isolation. |
| DATA-FR-021 | Sensitive classification | PII/security/GxP/config data classes map to encryption/access/retention policies. | Data protection. |
| DATA-FR-022 | Retention metadata | Every data class has retention trigger, duration/profile, legal-hold behavior and archive/delete owner. | Lifecycle. |
| DATA-FR-023 | Deletion | Regulated/history records are not hard-deleted through generic CRUD; purge uses controlled retention service. | Integrity. |
| DATA-FR-024 | Migration provenance | Imported/migrated data stores source system/file, transformation version, checksum and migration batch. | Traceability. |
| DATA-FR-025 | Schema ownership | Only owning service migration package may alter its authoritative tables. | Service boundary. |
| DATA-FR-026 | Reporting | Analytics/reporting uses read replicas/read models/warehouse exports where possible; operational database is not unrestricted BI endpoint. | Performance/security. |
| DATA-FR-027 | Data dictionary | Machine-readable entity/field/owner/classification/retention dictionary generated and maintained. | Claude Code clarity. |
| DATA-FR-028 | Cross-store consistency | Projection/integration consistency is monitored and repairable from authoritative source. | Recoverability. |
| DATA-FR-029 | Data lineage | Critical result can identify source record/version, transformation/rule and destination evidence. | Traceability. |
| DATA-FR-030 | Architecture enforcement | CI/lint/tests prevent forbidden repository/service direct access to another service's authoritative schema where feasible. | Guardrails. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| resolveDataOwner() | Any service/design tooling | entity_type; field/path? | Data ownership registry loaded | Returns authoritative service/store and permitted projections | DataOwnerDecision | DATA_OWNER_UNKNOWN |
| assertAuthoritativeWriteAllowed() | Repository/mutation layer | service_identity; entity_type; operation | Owner registry effective | Checks service is authoritative owner; rejects foreign schema write | WriteOwnershipDecision | FORBIDDEN_DATA_OWNER_WRITE |
| publishProjectionChange() | Authoritative service after commit | source_event_id; entity_type/id/version; projection payload/ref | Authoritative tx committed | Outbox event drives Frappe/search/read projection; no cross-DB transaction | ProjectionEvent | ProjectionUpdateRequested |
| getProjectionFreshness() | UI/read service | projection_type; entity_id | Projection exists | Compares projected source version/time to authoritative/current policy | ProjectionFreshness | PROJECTION_STALE |
| rebuildProjection() | Projection worker/admin | projection_type; scope; source cutoff | Authorized/rebuildable projection | Reads authoritative APIs/events and rebuilds target projection idempotently | ProjectionRebuildResult | ProjectionRebuilt |
| registerDataClass() | Data governance | entity/field; classification; retention; encryption profile | Governance authority | Creates versioned data dictionary entry | DataClassEntry | DataClassRegistered |
| recordMigrationProvenance() | Migration service | migration_batch; source; checksums; transformation version; destination refs | Migration approved | Stores provenance/evidence manifest and reconciliation counts | MigrationProvenance | MigrationProvenanceRecorded |
| verifyCrossStoreConsistency() | Scheduled/admin | projection/integration scope; source cutoff | Authoritative source available | Compares source version/count/hash to projection; produces differences | ConsistencyReport | CrossStoreMismatchDetected |


# 5. State / Runtime / Ownership Model

```text
AUTHORITATIVE GxP WRITE
      ↓
PostgreSQL transaction
  ├ domain state
  ├ audit/version
  └ outbox
      ↓
Async projections
  ├ Frappe/MariaDB
  ├ Search
  ├ Cache
  ├ Analytics
  └ Integrations

Object evidence ← metadata/hash in GxP
Historian/Edge ← raw telemetry; GxP holds intended-use evidence refs

```

# 6. Data / Configuration Model

## `data_ownership_registry`
```text
entity_type varchar PK
authoritative_service varchar
authoritative_store POSTGRES|MARIADB|OBJECT|EXTERNAL
projection_targets jsonb
tenant_scoped boolean
site_scoped boolean
classification varchar
retention_policy_id uuid
encryption_profile_id uuid
```

## `projection_checkpoint`
- projection type
- source stream/entity
- last source event/version
- projected_at
- state/error

## `migration_batch`
- source system/artifact
- source hash
- transform version
- start/end
- counts/hash reconciliation
- approver/evidence


# 7. APIs / Internal Interfaces

- `GET /platform/v1/data-ownership/{entityType}`
- `GET /platform/v1/projections/{type}/{id}/freshness`
- `POST /platform/v1/projections/{type}:rebuild`
- `GET /platform/v1/data-dictionary`

# 8. UI / Operations Screens

1. Data Ownership Matrix
2. Projection Health
3. Data Dictionary
4. Migration Provenance
5. Cross-Store Consistency

# 9. Events / Operational Signals

- `ProjectionUpdateRequested`
- `ProjectionRebuilt`
- `ProjectionStaleDetected`
- `CrossStoreMismatchDetected`
- `MigrationProvenanceRecorded`

# 10. Failure / Recovery Rules

- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

# 11. Repository Structure

```text
infrastructure/enterprise-data-ownership-persistence-topology-data-lineage/
services/platform/enterprise-data-ownership-persistence-topology-data-lineage/
packages/data-contracts/
validation/infrastructure/enterprise-data-ownership-persistence-topology-data-lineage/
tests/infrastructure/enterprise-data-ownership-persistence-topology-data-lineage/
docs/runbooks/enterprise-data-ownership-persistence-topology-data-lineage/
```

# 12. Mandatory Test Catalogue

- foreign service tries GxP write
- Frappe projection lags one version
- search rebuild
- cache loss
- external ID remap
- migration count/hash mismatch
- generic delete denied

# 13. Acceptance Criteria

Every entity used by Documents 01–68 resolves to exactly one authoritative owner/store, and all projections can be deleted/rebuilt without losing regulated truth.

# 14. Claude Code / Codex Prohibitions

- Never create the same authoritative regulated entity in PostgreSQL and MariaDB.
- Never make cache/search/Temporal/NATS the sole source of regulated state.
- Never update another service's authoritative table directly.
- Never hide projection staleness during regulated action.

# 15. Claude Code Required Artifact

Generate `25_DATA_OWNERSHIP_AND_LINEAGE_MATRIX.md` covering every entity and storage tier before schema implementation.

