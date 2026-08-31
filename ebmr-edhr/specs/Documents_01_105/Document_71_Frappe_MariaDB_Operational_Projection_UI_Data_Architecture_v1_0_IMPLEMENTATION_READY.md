# US eBMR / eDHR Regulated Manufacturing Platform
## Document 71 — Frappe / MariaDB Operational Database, Projection & UI Data Architecture — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-DATA-003  
**Parent Documents:** Documents 01–68  
**Primary Dependencies:** Documents 01–07, 69–70; Frappe app; optional ERPNext  
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

Define MariaDB's exact role as the Frappe operational/UI/configuration and projection database, including read-only source-derived DocTypes, projection rebuilds and explicit prohibition on using Frappe persistence as the sole GxP authority.

# 2. Actors / Components

- Frappe App
- Projection Worker
- Frontend
- GxP API
- Frappe Admin
- DBA
- ERPNext Adapter

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| MDB-FR-001 | Frappe DB boundary | MariaDB contains Frappe framework state/DocTypes/config/projections only according to ownership registry. | Boundary. |
| MDB-FR-002 | No GxP authority | Released batch/QC/release/signature/audit truth is never authoritative solely in MariaDB. | Core integrity. |
| MDB-FR-003 | Projection DocTypes | Projection DocTypes include authoritative_source_id/version/projected_at/status. | Trace. |
| MDB-FR-004 | Projection update | Updates originate from events/API projection worker, not manual operator edits. | Consistency. |
| MDB-FR-005 | Projection immutability | Fields sourced from GxP are read-only in Frappe forms and server hooks reject direct writes. | No UI bypass. |
| MDB-FR-006 | Frappe configuration | Non-regulated UI/config may use normal DocTypes; regulated configuration uses Vault/GxP release workflow where required. | Config classification. |
| MDB-FR-007 | User identity mapping | Frappe user/session mapping is projection/integration of identity, not independent authority for GxP permission. | IAM boundary. |
| MDB-FR-008 | Workflow | Frappe workflow may drive UX but server GxP state machine/policy remains authoritative. | No duplicate workflow truth. |
| MDB-FR-009 | Attachments | Regulated evidence attachment bytes routed to Evidence Store; Frappe stores controlled reference where possible. | Storage boundary. |
| MDB-FR-010 | Background jobs | Frappe jobs that mutate regulated state call GxP APIs; no direct PostgreSQL connection. | Service boundary. |
| MDB-FR-011 | Custom scripts | Client/server scripts cannot bypass APIs or evaluate arbitrary regulated business rules. | Security. |
| MDB-FR-012 | ERPNext optionality | ERPNext DocTypes only present/useful when adapter deployment includes ERPNext; GxP app remains functional without ERPNext. | Decoupling. |
| MDB-FR-013 | Indexes | Projection/list indexes optimized for UI filters/search; migration controlled via Frappe app. | Performance. |
| MDB-FR-014 | Large tables | Do not mirror millions of audit/telemetry rows into MariaDB; expose API/read model summary. | Scale. |
| MDB-FR-015 | Projection rebuild | Projection tables can be truncated/rebuilt in maintenance mode from authoritative source. | Recoverability. |
| MDB-FR-016 | Projection correction | Do not manually edit source-derived projection; repair source mapping/projector and replay. | Consistency. |
| MDB-FR-017 | Backup | MariaDB backed up because it contains operational/UI/config state even if regulated truth is elsewhere. | Continuity. |
| MDB-FR-018 | Restore order | After MariaDB restore, projection freshness/rebuild reconciles against current GxP source before service healthy. | Consistency. |
| MDB-FR-019 | Frappe migrations | Bench/app schema migrations versioned and run through controlled release. | SDLC. |
| MDB-FR-020 | Site config secrets | Secrets excluded from Frappe DB/site config where possible and referenced from secret manager. | Security. |
| MDB-FR-021 | Tenant deployment | Dedicated customer deployment may use one Frappe site/database or documented site topology; cross-customer DB mixing not assumed. | Isolation. |
| MDB-FR-022 | Audit supplement | Frappe Version/activity may support UX/support but is explicitly non-authoritative vs GxP Audit Ledger. | Clear semantics. |
| MDB-FR-023 | Projection lag | UI indicates syncing/stale state rather than showing stale value as current without context. | Transparency. |
| MDB-FR-024 | Transaction hooks | Frappe after_commit/event trigger does not create false distributed atomicity; projector is replay/idempotent. | Reliability. |
| MDB-FR-025 | Permissions | Frappe permissions supplement UI visibility, but Policy Service is mandatory for regulated API action. | Authorization. |
| MDB-FR-026 | Read-only database role | Reporting/support direct MariaDB roles restricted and not used to alter projection/source-derived fields. | Security. |
| MDB-FR-027 | Database health | Monitor replication/backup/storage/slow queries/job queues as deployment requires. | Operations. |
| MDB-FR-028 | No cross-engine joins | Application code does not rely on SQL joins between MariaDB and PostgreSQL. | Portability. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| applyGxPProjection() | Projection worker | source event/entity/version; projection DTO | Event authenticated/idempotent; version >= current | Upserts read-only projection if newer; records source version/checkpoint | ProjectionApplyResult | FrappeProjectionApplied; PROJECTION_VERSION_CONFLICT |
| rejectDirectProjectionMutation() | Frappe server hook/API | doctype/document changes; user context | DocType/source field marked projection | Rejects source-derived field mutation; no save | Denied | PROJECTION_FIELD_READ_ONLY |
| rebuildFrappeProjection() | Admin/projector | projection type; scope; source cutoff | Maintenance authorization; authoritative APIs available | Clears/recreates selected projection idempotently; updates checkpoint | ProjectionRebuildResult | FrappeProjectionRebuilt |
| getProjectionStatus() | Frappe UI | entity/source ID | Projection exists | Returns source version/projected time/staleness | ProjectionStatus | PROJECTION_STALE |
| invokeGxPAction() | Frappe controller | operationId; DTO; AuthContext; idempotency/expected version | User authenticated; route allowed | Calls GxP API; never writes GxP DB; handles receipt/errors and projection eventual update | GxPActionReceipt | GXP_API_UNAVAILABLE |
| verifyMariaDBAfterRestore() | Recovery runbook | restore timestamp; projection checkpoints | MariaDB restored and isolated from writes | Validates framework/config and reconciles projection source versions | MariaDBRecoveryReport | MARIADB_RECONCILIATION_REQUIRED |


# 5. State / Runtime / Ownership Model

```text
GxP PostgreSQL
    ↓ events/APIs
Projection Worker
    ↓
Frappe MariaDB
  ├ UI projections
  ├ Frappe config/meta
  ├ non-authoritative workflow UX
  └ optional ERPNext data
       ↓
Frappe UI

Regulated action: Frappe UI → GxP API → PostgreSQL → projection update

```

# 6. Data / Configuration Model

## Projection baseline fields

```text
name / frappe internal identity
gxp_source_type
gxp_source_id
gxp_source_version
gxp_projected_at
gxp_projection_status
tenant/site
display/search fields
```

Source-derived fields are marked read-only and protected in server code.

## Frappe configuration classes

- UI-only/non-GxP config: MariaDB authoritative where approved.
- GxP master/config: authoritative PostgreSQL/Vault, Frappe projection only.
- External ERPNext objects: ERPNext authority per Document 48, not GxP.


# 7. APIs / Internal Interfaces

- `Projection worker event handlers`
- `Frappe whitelisted controllers that call GxP APIs`
- `GET /api/method/... projection status/admin operations`

# 8. UI / Operations Screens

1. Projection Sync Status
2. Frappe DB Health
3. Projection Rebuild
4. Stale Projection Indicators
5. Frappe Migration History

# 9. Events / Operational Signals

- `FrappeProjectionApplied`
- `FrappeProjectionRebuilt`
- `ProjectionStaleDetected`
- `DirectProjectionMutationDenied`

# 10. Failure / Recovery Rules

- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

# 11. Repository Structure

```text
infrastructure/frappe-mariadb-operational-database-projection-ui-data-architecture/
services/platform/frappe-mariadb-operational-database-projection-ui-data-architecture/
packages/data-contracts/
validation/infrastructure/frappe-mariadb-operational-database-projection-ui-data-architecture/
tests/infrastructure/frappe-mariadb-operational-database-projection-ui-data-architecture/
docs/runbooks/frappe-mariadb-operational-database-projection-ui-data-architecture/
```

# 12. Mandatory Test Catalogue

- manual edit projected batch state denied
- out-of-order event ignored
- projection rebuild after DB loss
- GxP API unavailable
- MariaDB restored older than PostgreSQL
- ERPNext absent deployment still functions

# 13. Acceptance Criteria

Deleting and rebuilding all GxP-derived Frappe projections does not destroy or alter any authoritative regulated record.

# 14. Claude Code / Codex Prohibitions

- Never let Frappe DocStatus/workflow equal final GxP state by itself.
- Never connect Frappe ORM directly to PostgreSQL GxP tables.
- Never mirror full audit ledger/telemetry into MariaDB.
- Never repair projection by editing it manually.


