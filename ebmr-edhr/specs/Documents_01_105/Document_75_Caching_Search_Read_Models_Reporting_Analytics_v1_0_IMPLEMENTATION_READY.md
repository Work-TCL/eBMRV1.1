# US eBMR / eDHR Regulated Manufacturing Platform
## Document 75 — Caching, Search, Read Models, Reporting Projections & Analytics Data Access — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DATA-007  
**Parent Documents:** Documents 01–68  
**Primary Dependencies:** Documents 15, 37, 58; 61–71; Frappe UI/reporting  
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

Define Redis/cache, search indexing, read models, materialized reporting projections and optional analytics exports as rebuildable performance layers with explicit freshness and authorization.

# 2. Actors / Components

- Application Service
- Redis/Cache
- Search Provider
- Projection Worker
- Reporting Service
- Analytics/BI
- User
- SRE

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| READ-FR-001 | Read-model purpose | Caches/search/read models improve UX/reporting but are non-authoritative projections. | Boundary. |
| READ-FR-002 | Redis usage | Redis may store sessions, rate limits, ephemeral locks, cache entries and queues only where architecture permits. | Controlled cache. |
| READ-FR-003 | No GxP truth in Redis | No regulated state/signature/audit/release result exists only in Redis. | Durability. |
| READ-FR-004 | Cache key scope | Tenant/site/user/entity/version included where necessary to prevent cross-scope leakage. | Isolation. |
| READ-FR-005 | TTL | Every cache class has TTL/invalidation strategy; infinite cache of mutable regulated data prohibited. | Freshness. |
| READ-FR-006 | Cache stampede | Use bounded locking/single-flight/jitter where high-cost queries need it. | Stability. |
| READ-FR-007 | Cache invalidation | Authoritative event/version invalidates/updates cache; regulated action can bypass cache. | Correctness. |
| READ-FR-008 | Search engine optional | OpenSearch/Elasticsearch-compatible or database search provider is pluggable; product not hard-dependent on one commercial engine. | Portability. |
| READ-FR-009 | Search index fields | Index only allowed searchable fields; sensitive/PII excluded or restricted. | Privacy. |
| READ-FR-010 | Search authorization | Search query applies tenant/site/role/resource filters; result ID then re-authorized on fetch. | No information leakage. |
| READ-FR-011 | No index authority | Search state/status never used as final release/signature target without authoritative fetch/version validation. | Consistency. |
| READ-FR-012 | Index version | Indexed document carries source entity ID/version/projected_at. | Trace. |
| READ-FR-013 | Stale results | UI can show stale/indexing status and authoritative detail refresh. | Transparency. |
| READ-FR-014 | Index rebuild | Full index can be dropped/recreated from authoritative source or projections. | Recoverability. |
| READ-FR-015 | Read model | Complex dashboards use dedicated read models/materialized views rather than deep cross-domain synchronous joins. | Performance. |
| READ-FR-016 | Materialized view refresh | Refresh mode/cadence/cutoff visible and not used for current regulated decision if stale. | Correctness. |
| READ-FR-017 | Report snapshots | Official reports/management packages freeze source cutoff/version independently of live dashboards. | Reproducibility. |
| READ-FR-018 | Analytics warehouse | Optional warehouse/lake export is one-way governed projection, not authoritative GxP write path. | Data architecture. |
| READ-FR-019 | ETL/ELT lineage | Exports include source IDs/versions/cutoff and transformation version. | Lineage. |
| READ-FR-020 | Read replica | PostgreSQL replicas can support bounded reporting where staleness accepted. | Scale. |
| READ-FR-021 | List pagination | Cursor/keyset pagination preferred for large operational lists; bounded page size. | Performance. |
| READ-FR-022 | Filter allowlist | Search/list filter/sort fields explicitly allowlisted/indexed to prevent abusive arbitrary queries. | Resource safety. |
| READ-FR-023 | Export limits | Large exports asynchronous with source snapshot/cutoff, authorization and expiration. | Scale/security. |
| READ-FR-024 | Session cache | Session revocation/authorization-critical state cannot be indefinitely cached past revocation policy. | Security. |
| READ-FR-025 | Rule/config cache | Released rule/master caches keyed by exact version and immutable content hash where possible. | Safe cache. |
| READ-FR-026 | Negative cache | Missing/denied resource caching scoped carefully and short-lived to avoid stale authorization/data visibility. | Correctness. |
| READ-FR-027 | Cache outage | Application degrades to authoritative reads or explicit unavailable; must not fabricate data. | Resilience. |
| READ-FR-028 | Search outage | Core regulated execution remains available where architecture allows; search/list UX may degrade. | Resilience. |
| READ-FR-029 | Observability | Hit ratio, latency, evictions, memory, index lag, rebuild progress and query performance monitored. | Operations. |
| READ-FR-030 | No sensitive logs | Search queries/cache keys/logs avoid leaking secrets/patient sensitive content. | Security. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| getVersionedCacheEntry() | Application service | cache class; tenant/site; entity id/version | Cache configured; auth already resolved as required | Gets exact-version cache; miss falls back to owner API | CacheResult | CACHE_MISS |
| invalidateEntityCache() | Event consumer | entity type/id/new version | Event valid/current | Deletes/marks older mutable-key caches; idempotent | InvalidationReceipt | CacheInvalidated |
| indexAuthoritativeProjection() | Search projector | entity projection; source version; allowed fields | Event/projection authorized; schema effective | Upserts search document if version newer | IndexReceipt | SearchDocumentIndexed |
| authorizeSearchQuery() | Search API | AuthContext; query/filter/sort | User authenticated; fields allowlisted | Builds tenant/site/resource security filter + bounded query | AuthorizedSearchPlan | SEARCH_FILTER_NOT_ALLOWED |
| fetchSearchResultDetail() | UI/API | result entity ID; source version | Result visible | Fetches authoritative owner API; re-authorizes and compares version | AuthoritativeDetail | SEARCH_RESULT_STALE |
| rebuildSearchIndex() | Admin/projector | index type; source cutoff | Authorized; source accessible | Creates new generation index, populates/checks, atomically switches alias | SearchRebuildResult | SearchIndexRebuilt |
| refreshReadModel() | Read-model worker | model; source cutoff/checkpoints | Sources available | Incrementally/materially rebuilds projection and records cutoff | ReadModelSnapshot | ReadModelRefreshed |
| generateAsyncExport() | Authorized user/report worker | report definition; filters; source cutoff | Export permission/limits | Builds frozen dataset/evidence file, stores expiry/access metadata | ExportJobResult | ExportGenerated |


# 5. State / Runtime / Ownership Model

```text
AUTHORITATIVE SOURCES
     ↓ events/checkpoints
READ LAYERS
  ├ Redis cache
  ├ Frappe projections
  ├ Search index
  ├ Read models/materialized views
  └ Analytics warehouse export

REGULATED ACTION → authoritative fetch/version check

```

# 6. Data / Configuration Model

## `projection_document_metadata`
- source type/id/version
- tenant/site
- projected_at
- schema version
- index/read-model generation

## `read_model_checkpoint`
- model
- source stream/table
- last event/version/cutoff
- state/error

## Cache classes
- immutable released master by ID/version;
- short-lived entity/list;
- policy/rule exact version;
- session/rate limits;
- no authoritative regulated mutation state.


# 7. APIs / Internal Interfaces

- `GET /search/v1/...`
- `POST /search/v1/indexes/{type}:rebuild`
- `POST /reports/v1/exports`
- `GET /platform/v1/read-models/{name}/status`

# 8. UI / Operations Screens

1. Search
2. Index Health
3. Cache Health
4. Read Model Freshness
5. Async Exports
6. Analytics Cutoff

# 9. Events / Operational Signals

- `SearchDocumentIndexed`
- `SearchIndexRebuilt`
- `ReadModelRefreshed`
- `CacheInvalidated`
- `ProjectionLagExceeded`
- `ExportGenerated`

# 10. Failure / Recovery Rules

- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

# 11. Repository Structure

```text
infrastructure/caching-search-read-models-reporting-projections-analytics-data-access/
services/platform/caching-search-read-models-reporting-projections-analytics-data-access/
packages/data-contracts/
validation/infrastructure/caching-search-read-models-reporting-projections-analytics-data-access/
tests/infrastructure/caching-search-read-models-reporting-projections-analytics-data-access/
docs/runbooks/caching-search-read-models-reporting-projections-analytics-data-access/
```

# 12. Mandatory Test Catalogue

- cross-tenant search
- stale search result then authoritative fetch
- Redis loss
- search engine outage
- rebuild with zero downtime alias switch
- large export authorization
- rule exact-version cache

# 13. Acceptance Criteria

Loss of Redis and search indexes may degrade performance/UX but cannot lose, alter, or authorize regulated GxP data.

# 14. Claude Code / Codex Prohibitions

- Never make release/signature decision from search index alone.
- Never put sensitive authorization context in globally shared cache key.
- Never let BI/warehouse write back to GxP tables.
- Never expose arbitrary unbounded search/filter query.


