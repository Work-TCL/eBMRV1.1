# Data ownership and database rules

**Purpose:** Data ownership and database rules for the eBMR/eDHR platform.
**Applicable paths/modules:** see `docs/generated/17_REPOSITORY_STRUCTURE.md`; this rule applies to every
service, the Frappe app, edge and integration code unless a narrower scope is stated below.
**Source documents:** Document 69 (SPEC-DATA-001), Document 70 (SPEC-DATA-002), Document 71 (SPEC-DATA-003), Document 100 (SPEC-ENG-004), Document 75 (SPEC-DATA-007)
**Source requirement IDs:** DATA-FR-001..030 (30); PG-FR-001..034 (34); MDB-FR-001..028 (28); MIG-FR-001..032 (32); READ-FR-001..030 (30)

---

## Required implementation pattern

One authoritative owner and store per entity (`docs/generated/05_DATABASE_OWNERSHIP_MATRIX.md`).
Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`, a retention
class and row-level tenant scoping. Projections into Frappe/MariaDB carry `authoritative_source_id`,
`authoritative_source_version`, `projected_at`, `projection_status` and are read-only in the UI.

## Forbidden patterns

- cross-service schema access
- a second writable copy of a regulated entity
- a regulated decision read from a projection, cache, search index or report
- `float`/`double precision`/`real` for a regulated quantity
- missing tenant scope on a regulated query

## Required tests

ownership lint; cross-tenant access denial; projection staleness flag; rebuild from authoritative source;
decimal-only numeric path; optimistic concurrency on every mutable aggregate.


## Source requirements (extract)

| ID | Requirement | Required behaviour |
|---|---|---|
| DATA-FR-001 | Authoritative-store registry | Every entity/data class has declared authoritative store/service owner and permitted projections. |
| DATA-FR-002 | PostgreSQL authority | Regulated GxP commands, record versions, signatures, audit, release/disposition, genealogy and other proprietary GxP state use PostgreSQL ownership. |
| DATA-FR-003 | MariaDB scope | Frappe/MariaDB owns UI/application metadata, Frappe users/config as applicable, DocTypes/projections and non-authoritative workflow conveniences. |
| DATA-FR-004 | Projection marking | Every Frappe/read/search projection declares source entity/version and rebuild mechanism. |
| DATA-FR-005 | No cross-DB transaction assumption | No business invariant depends on atomic commit across PostgreSQL and MariaDB. |
| DATA-FR-006 | Postgres-first regulated mutation | Authoritative GxP state commits in PostgreSQL with audit/outbox; Frappe projection follows asynchronously or through explicit read-through. |
| DATA-FR-007 | Read path | UI may query Frappe projection for lists but must fetch authoritative detail/version for regulated action/signature where needed. |
| DATA-FR-008 | Staleness metadata | Projection exposes source version, projected_at and stale/degraded status. |
| DATA-FR-009 | Object-store ownership | Binary/raw evidence uses object storage; relational DB stores metadata/hash/links, not arbitrary large blobs by default. |
| DATA-FR-010 | Historian ownership | High-frequency telemetry belongs in historian/time-series/Edge storage; GxP stores relevant evidence/result refs. |
| DATA-FR-011 | Search ownership | Search index is rebuildable projection and cannot determine official regulated value/state. |
| DATA-FR-012 | Cache ownership | Cache is disposable and never sole source of permissions, signature target, release decision or regulated state. |
| DATA-FR-013 | Temporal ownership | Temporal owns workflow execution history/coordination only; domain state belongs to GxP services. |
| DATA-FR-014 | NATS ownership | NATS/JetStream owns transport state only; business event source is PostgreSQL outbox/event record. |
| DATA-FR-015 | External systems | ERP/LIMS/IdP/SCADA authority follows integration ownership matrix; external IDs remain references. |
| DATA-FR-016 | Entity identity | Internal immutable UUID/ID persists independently of external IDs/names. |
| DATA-FR-017 | Version semantics | Regulated mutable records use optimistic aggregate version; released versions immutable. |
| DATA-FR-018 | Timestamps | Server UTC authoritative receipt/transaction times; source times retained separately. |
| DATA-FR-019 | Decimal values | Regulated numeric values/calculations use exact decimal representation and explicit UOM/rounding. |
| DATA-FR-020 | Tenant/site key | Authoritative records carry tenant and site scope where applicable and are indexed/authorized consistently. |
| DATA-FR-021 | Sensitive classification | PII/security/GxP/config data classes map to encryption/access/retention policies. |
| DATA-FR-022 | Retention metadata | Every data class has retention trigger, duration/profile, legal-hold behavior and archive/delete owner. |
| DATA-FR-023 | Deletion | Regulated/history records are not hard-deleted through generic CRUD; purge uses controlled retention service. |
| DATA-FR-024 | Migration provenance | Imported/migrated data stores source system/file, transformation version, checksum and migration batch. |
| DATA-FR-025 | Schema ownership | Only owning service migration package may alter its authoritative tables. |
| DATA-FR-026 | Reporting | Analytics/reporting uses read replicas/read models/warehouse exports where possible; operational database is not unrestricted BI endpoint. |
| DATA-FR-027 | Data dictionary | Machine-readable entity/field/owner/classification/retention dictionary generated and maintained. |
| DATA-FR-028 | Cross-store consistency | Projection/integration consistency is monitored and repairable from authoritative source. |
| DATA-FR-029 | Data lineage | Critical result can identify source record/version, transformation/rule and destination evidence. |
| DATA-FR-030 | Architecture enforcement | CI/lint/tests prevent forbidden repository/service direct access to another service's authoritative schema where feasible. |
| PG-FR-001 | Supported version pin | Deployment pins a supported PostgreSQL major/minor validated for product release; no automatic major upgrade. |
| PG-FR-002 | Cluster topology | Reference supports managed PostgreSQL or self-hosted HA profile with primary + replica(s) according to availability requirements. |
| PG-FR-003 | Database separation | GxP PostgreSQL cluster/database separated from Frappe MariaDB and optionally from non-GxP analytics. |
| PG-FR-004 | Schema ownership | Schemas grouped by bounded context/service; owning service DB role owns migrations/tables. |
| PG-FR-005 | Runtime roles | Runtime role gets minimum SELECT/INSERT/UPDATE/EXECUTE needed; DDL denied. |
| PG-FR-006 | Migration role | Migration role separate from runtime role and used only during controlled deployment. |
| PG-FR-007 | UUID identity | UUIDv7/UUID or approved stable ID scheme used for distributed identities; DB sequences may supplement internal ordering. |
| PG-FR-008 | Optimistic version | Aggregate tables include bigint version and conditional UPDATE semantics. |
| PG-FR-009 | Foreign keys | Use FKs within bounded context where lifecycle permits; cross-service references may be logical IDs/events to avoid forbidden coupling. |
| PG-FR-010 | Check constraints | Encode stable structural invariants such as valid ranges/states where appropriate; business configuration remains rules service. |

## SPEC_GAP triggers

Raise a SPEC_GAP rather than deciding, if you encounter: a missing signature/authorization/retention/
precision value, a conflict between two source documents, an entity without an owner, an event without a
producer, or any requirement that would need a regulated behaviour you cannot trace to
Document 69, Document 70, Document 71, Document 100, Document 75 or Documents 106–115.
