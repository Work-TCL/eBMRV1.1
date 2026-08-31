# WP-11 — Scope & Requirements

**In scope:** Documents 69, 70, 71, 72, 73, 74, 75, 76, 77, 78

## Document 69 — Enterprise Data Ownership, Persistence Topology & Data Lineage (SPEC-DATA-001)

- Code location: `infrastructure`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: DATA-FR-001..030 (30)

## Document 70 — PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency (SPEC-DATA-002)

- Code location: `infrastructure`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: PG-FR-001..034 (34)

## Document 71 — Frappe / MariaDB Operational Database, Projection & UI Data Architecture (SPEC-DATA-003)

- Code location: `infrastructure`
- Authoritative store: MariaDB (Frappe operational/projection — NON-AUTHORITATIVE for GxP)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: MDB-FR-001..028 (28)

## Document 72 — Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle (SPEC-DATA-004)

- Code location: `infrastructure`
- Authoritative store: Object store (WORM evidence) + PostgreSQL metadata
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: OBJ-FR-001..030 (30)

## Document 73 — NATS / JetStream Event Bus, Transactional Outbox & Async Contracts (SPEC-DATA-005)

- Code location: `infrastructure`
- Authoritative store: PostgreSQL transactional outbox (authoritative) / NATS JetStream (transport)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: EVT-FR-001..030 (30)

## Document 74 — Temporal Durable Workflow Orchestration Architecture (SPEC-DATA-006)

- Code location: `infrastructure`
- Authoritative store: Temporal (orchestration only — NOT regulatory truth)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: TMP-FR-001..030 (30)

## Document 75 — Caching, Search, Read Models, Reporting Projections & Analytics Data Access (SPEC-DATA-007)

- Code location: `infrastructure`
- Authoritative store: Redis / search / read models (rebuildable, NON-AUTHORITATIVE)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: READ-FR-001..030 (30)

## Document 76 — Backup, Restore, Point-in-Time Recovery & Disaster Recovery (SPEC-DATA-008)

- Code location: `infrastructure`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: DR-FR-001..032 (32)

## Document 77 — Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture (SPEC-DATA-009)

- Code location: `infrastructure`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: DEP-FR-001..035 (35)

## Document 78 — Performance, Capacity, Observability, SLOs & SRE Operations (SPEC-DATA-010)

- Code location: `infrastructure`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: SRE-FR-001..036 (36)

## All requirements

| ID | Doc | Requirement | Behaviour | Acceptance |
|---|---|---|---|---|
| DATA-FR-001 | 69 | Authoritative-store registry | Every entity/data class has declared authoritative store/service owner and permitted projections. | No dual master. |
| DATA-FR-002 | 69 | PostgreSQL authority | Regulated GxP commands, record versions, signatures, audit, release/disposition, genealogy and other proprietary GxP state use PostgreSQL ownership. | Clear GxP truth. |
| DATA-FR-003 | 69 | MariaDB scope | Frappe/MariaDB owns UI/application metadata, Frappe users/config as applicable, DocTypes/projections and non-authoritative workflow conveniences. | Framework boundary. |
| DATA-FR-004 | 69 | Projection marking | Every Frappe/read/search projection declares source entity/version and rebuild mechanism. | No mistaken authority. |
| DATA-FR-005 | 69 | No cross-DB transaction assumption | No business invariant depends on atomic commit across PostgreSQL and MariaDB. | Distributed safety. |
| DATA-FR-006 | 69 | Postgres-first regulated mutation | Authoritative GxP state commits in PostgreSQL with audit/outbox; Frappe projection follows asynchronously or through explicit read-through. | Correct order. |
| DATA-FR-007 | 69 | Read path | UI may query Frappe projection for lists but must fetch authoritative detail/version for regulated action/signature where needed. | Freshness. |
| DATA-FR-008 | 69 | Staleness metadata | Projection exposes source version, projected_at and stale/degraded status. | Transparency. |
| DATA-FR-009 | 69 | Object-store ownership | Binary/raw evidence uses object storage; relational DB stores metadata/hash/links, not arbitrary large blobs by default. | Scale. |
| DATA-FR-010 | 69 | Historian ownership | High-frequency telemetry belongs in historian/time-series/Edge storage; GxP stores relevant evidence/result refs. | Tiering. |
| DATA-FR-011 | 69 | Search ownership | Search index is rebuildable projection and cannot determine official regulated value/state. | Search boundary. |
| DATA-FR-012 | 69 | Cache ownership | Cache is disposable and never sole source of permissions, signature target, release decision or regulated state. | Safe cache. |
| DATA-FR-013 | 69 | Temporal ownership | Temporal owns workflow execution history/coordination only; domain state belongs to GxP services. | Orchestration boundary. |
| DATA-FR-014 | 69 | NATS ownership | NATS/JetStream owns transport state only; business event source is PostgreSQL outbox/event record. | Messaging boundary. |
| DATA-FR-015 | 69 | External systems | ERP/LIMS/IdP/SCADA authority follows integration ownership matrix; external IDs remain references. | Integration clarity. |
| DATA-FR-016 | 69 | Entity identity | Internal immutable UUID/ID persists independently of external IDs/names. | Stable identity. |
| DATA-FR-017 | 69 | Version semantics | Regulated mutable records use optimistic aggregate version; released versions immutable. | Concurrency. |
| DATA-FR-018 | 69 | Timestamps | Server UTC authoritative receipt/transaction times; source times retained separately. | Chronology. |
| DATA-FR-019 | 69 | Decimal values | Regulated numeric values/calculations use exact decimal representation and explicit UOM/rounding. | No float drift. |
| DATA-FR-020 | 69 | Tenant/site key | Authoritative records carry tenant and site scope where applicable and are indexed/authorized consistently. | Isolation. |
| DATA-FR-021 | 69 | Sensitive classification | PII/security/GxP/config data classes map to encryption/access/retention policies. | Data protection. |
| DATA-FR-022 | 69 | Retention metadata | Every data class has retention trigger, duration/profile, legal-hold behavior and archive/delete owner. | Lifecycle. |
| DATA-FR-023 | 69 | Deletion | Regulated/history records are not hard-deleted through generic CRUD; purge uses controlled retention service. | Integrity. |
| DATA-FR-024 | 69 | Migration provenance | Imported/migrated data stores source system/file, transformation version, checksum and migration batch. | Traceability. |
| DATA-FR-025 | 69 | Schema ownership | Only owning service migration package may alter its authoritative tables. | Service boundary. |
| DATA-FR-026 | 69 | Reporting | Analytics/reporting uses read replicas/read models/warehouse exports where possible; operational database is not unrestricted BI endpoint. | Performance/security. |
| DATA-FR-027 | 69 | Data dictionary | Machine-readable entity/field/owner/classification/retention dictionary generated and maintained. | Claude Code clarity. |
| DATA-FR-028 | 69 | Cross-store consistency | Projection/integration consistency is monitored and repairable from authoritative source. | Recoverability. |
| DATA-FR-029 | 69 | Data lineage | Critical result can identify source record/version, transformation/rule and destination evidence. | Traceability. |
| DATA-FR-030 | 69 | Architecture enforcement | CI/lint/tests prevent forbidden repository/service direct access to another service's authoritative schema where feasible. | Guardrails. |
| PG-FR-001 | 70 | Supported version pin | Deployment pins a supported PostgreSQL major/minor validated for product release; no automatic major upgrade. | Controlled platform. |
| PG-FR-002 | 70 | Cluster topology | Reference supports managed PostgreSQL or self-hosted HA profile with primary + replica(s) according to availability requirements. | Portable. |
| PG-FR-003 | 70 | Database separation | GxP PostgreSQL cluster/database separated from Frappe MariaDB and optionally from non-GxP analytics. | Clear boundary. |
| PG-FR-004 | 70 | Schema ownership | Schemas grouped by bounded context/service; owning service DB role owns migrations/tables. | Least privilege. |
| PG-FR-005 | 70 | Runtime roles | Runtime role gets minimum SELECT/INSERT/UPDATE/EXECUTE needed; DDL denied. | Security. |
| PG-FR-006 | 70 | Migration role | Migration role separate from runtime role and used only during controlled deployment. | Change control. |
| PG-FR-007 | 70 | UUID identity | UUIDv7/UUID or approved stable ID scheme used for distributed identities; DB sequences may supplement internal ordering. | Scalable identity. |
| PG-FR-008 | 70 | Optimistic version | Aggregate tables include bigint version and conditional UPDATE semantics. | Concurrency. |
| PG-FR-009 | 70 | Foreign keys | Use FKs within bounded context where lifecycle permits; cross-service references may be logical IDs/events to avoid forbidden coupling. | Integrity/boundary. |
| PG-FR-010 | 70 | Check constraints | Encode stable structural invariants such as valid ranges/states where appropriate; business configuration remains rules service. | Defense in depth. |
| PG-FR-011 | 70 | Unique constraints | Idempotency, external mapping, command receipt and semantic uniqueness enforced at DB level where possible. | Duplicate prevention. |
| PG-FR-012 | 70 | Transaction isolation | Default transaction isolation chosen deliberately; high-contention operations may use row locks/advisory locks/serializable only when specified. | Correctness. |
| PG-FR-013 | 70 | No long transactions | User think-time, signature challenge and external API calls never hold DB transaction open. | Availability. |
| PG-FR-014 | 70 | Outbox atomicity | Domain mutation + audit + version + outbox commit in same PostgreSQL transaction. | Reliable events. |
| PG-FR-015 | 70 | Append-only tables | Audit/event/version evidence tables use restricted roles and no normal UPDATE/DELETE path. | Integrity. |
| PG-FR-016 | 70 | Partitioning candidates | Very large audit/event/security/integration tables support declarative time partitioning with tested query/index strategy. | Scale. |
| PG-FR-017 | 70 | Partition key design | Partition key aligns retention/query pattern and uniqueness constraints; avoid tenant partitions explosion. | Operability. |
| PG-FR-018 | 70 | Indexes | Indexes derived from documented query patterns; avoid blanket indexing JSON/low-selectivity columns. | Performance. |
| PG-FR-019 | 70 | JSONB use | JSONB permitted for versioned payload/evidence/config snapshots while frequently queried relational keys remain columns/indexed. | Balanced modeling. |
| PG-FR-020 | 70 | Decimal/UOM | Use NUMERIC/decimal for regulated quantities/calculations, not float unless measurement representation specifically requires and raw semantics retained. | Precision. |
| PG-FR-021 | 70 | Timestamps | Use timestamptz UTC; source/local timezone metadata stored explicitly if needed. | Time. |
| PG-FR-022 | 70 | Database timezone | Server/session database timezone set/treated consistently as UTC for persisted regulatory timestamps. | Consistency. |
| PG-FR-023 | 70 | Data checksums | Deployment profile assesses/enables PostgreSQL data checksums or equivalent managed-service integrity controls. | Corruption detection. |
| PG-FR-024 | 70 | WAL | WAL/replication/archiving configuration supports crash recovery and chosen RPO/PITR profile. | Durability. |
| PG-FR-025 | 70 | Connection pooling | Use bounded connection pool/proxy; service pool sizes derived from DB max connections and workload. | Stability. |
| PG-FR-026 | 70 | Statement timeout | Per workload query/statement/lock timeouts configured to avoid runaway operations. | Resource control. |
| PG-FR-027 | 70 | Vacuum/analyze | Autovacuum/statistics monitored/tuned for high-write partitioned tables; manual maintenance runbooks controlled. | Performance. |
| PG-FR-028 | 70 | Slow query monitoring | pg_stat_statements/managed equivalent and slow-query tracing available without logging sensitive parameters indiscriminately. | Diagnostics. |
| PG-FR-029 | 70 | DDL safety | Online/low-lock migration patterns used for large tables; destructive schema changes staged and reversible where feasible. | Availability. |
| PG-FR-030 | 70 | Partition lifecycle | Future partitions created ahead of time; missing partition fails visibly; detach/archive/drop only via retention workflow. | Lifecycle. |
| PG-FR-031 | 70 | Replica reads | Reporting/read-only workloads may use replicas only where acceptable staleness is explicit; regulated command/signature reads use primary/authoritative consistency. | Correct reads. |
| PG-FR-032 | 70 | Integrity verification | Periodic DB/index checks and backup/restore verification monitored. | Assurance. |
| PG-FR-033 | 70 | Extensions | PostgreSQL extensions require allowlist/security/license/managed-service compatibility approval. | Controlled dependency. |
| PG-FR-034 | 70 | No direct repair | Emergency repair uses service-admin command/migration with evidence; ad-hoc SQL UPDATE is prohibited for regulated records. | Integrity. |
| MDB-FR-001 | 71 | Frappe DB boundary | MariaDB contains Frappe framework state/DocTypes/config/projections only according to ownership registry. | Boundary. |
| MDB-FR-002 | 71 | No GxP authority | Released batch/QC/release/signature/audit truth is never authoritative solely in MariaDB. | Core integrity. |
| MDB-FR-003 | 71 | Projection DocTypes | Projection DocTypes include authoritative_source_id/version/projected_at/status. | Trace. |
| MDB-FR-004 | 71 | Projection update | Updates originate from events/API projection worker, not manual operator edits. | Consistency. |
| MDB-FR-005 | 71 | Projection immutability | Fields sourced from GxP are read-only in Frappe forms and server hooks reject direct writes. | No UI bypass. |
| MDB-FR-006 | 71 | Frappe configuration | Non-regulated UI/config may use normal DocTypes; regulated configuration uses Vault/GxP release workflow where required. | Config classification. |
| MDB-FR-007 | 71 | User identity mapping | Frappe user/session mapping is projection/integration of identity, not independent authority for GxP permission. | IAM boundary. |
| MDB-FR-008 | 71 | Workflow | Frappe workflow may drive UX but server GxP state machine/policy remains authoritative. | No duplicate workflow truth. |
| MDB-FR-009 | 71 | Attachments | Regulated evidence attachment bytes routed to Evidence Store; Frappe stores controlled reference where possible. | Storage boundary. |
| MDB-FR-010 | 71 | Background jobs | Frappe jobs that mutate regulated state call GxP APIs; no direct PostgreSQL connection. | Service boundary. |
| MDB-FR-011 | 71 | Custom scripts | Client/server scripts cannot bypass APIs or evaluate arbitrary regulated business rules. | Security. |
| MDB-FR-012 | 71 | ERPNext optionality | ERPNext DocTypes only present/useful when adapter deployment includes ERPNext; GxP app remains functional without ERPNext. | Decoupling. |
| MDB-FR-013 | 71 | Indexes | Projection/list indexes optimized for UI filters/search; migration controlled via Frappe app. | Performance. |
| MDB-FR-014 | 71 | Large tables | Do not mirror millions of audit/telemetry rows into MariaDB; expose API/read model summary. | Scale. |
| MDB-FR-015 | 71 | Projection rebuild | Projection tables can be truncated/rebuilt in maintenance mode from authoritative source. | Recoverability. |
| MDB-FR-016 | 71 | Projection correction | Do not manually edit source-derived projection; repair source mapping/projector and replay. | Consistency. |
| MDB-FR-017 | 71 | Backup | MariaDB backed up because it contains operational/UI/config state even if regulated truth is elsewhere. | Continuity. |
| MDB-FR-018 | 71 | Restore order | After MariaDB restore, projection freshness/rebuild reconciles against current GxP source before service healthy. | Consistency. |
| MDB-FR-019 | 71 | Frappe migrations | Bench/app schema migrations versioned and run through controlled release. | SDLC. |
| MDB-FR-020 | 71 | Site config secrets | Secrets excluded from Frappe DB/site config where possible and referenced from secret manager. | Security. |
| MDB-FR-021 | 71 | Tenant deployment | Dedicated customer deployment may use one Frappe site/database or documented site topology; cross-customer DB mixing not assumed. | Isolation. |
| MDB-FR-022 | 71 | Audit supplement | Frappe Version/activity may support UX/support but is explicitly non-authoritative vs GxP Audit Ledger. | Clear semantics. |
| MDB-FR-023 | 71 | Projection lag | UI indicates syncing/stale state rather than showing stale value as current without context. | Transparency. |
| MDB-FR-024 | 71 | Transaction hooks | Frappe after_commit/event trigger does not create false distributed atomicity; projector is replay/idempotent. | Reliability. |
| MDB-FR-025 | 71 | Permissions | Frappe permissions supplement UI visibility, but Policy Service is mandatory for regulated API action. | Authorization. |
| MDB-FR-026 | 71 | Read-only database role | Reporting/support direct MariaDB roles restricted and not used to alter projection/source-derived fields. | Security. |
| MDB-FR-027 | 71 | Database health | Monitor replication/backup/storage/slow queries/job queues as deployment requires. | Operations. |
| MDB-FR-028 | 71 | No cross-engine joins | Application code does not rely on SQL joins between MariaDB and PostgreSQL. | Portability. |
| OBJ-FR-001 | 72 | Evidence object abstraction | Support S3-compatible, Azure Blob and on-prem object storage through one EvidenceStore provider. | Cloud-neutral. |
| OBJ-FR-002 | 72 | Content addressing | Evidence object identified by generated immutable evidence ID plus SHA-256/approved digest; optional content-addressed path. | Integrity. |
| OBJ-FR-003 | 72 | Upload staging | Upload enters STAGED/QUARANTINE until checksum/type/security validation completes. | Safe ingestion. |
| OBJ-FR-004 | 72 | Immutable promotion | Validated evidence promoted/finalized into immutable object key/version; overwrite prohibited. | History. |
| OBJ-FR-005 | 72 | Metadata authority | PostgreSQL stores evidence metadata, ownership, hash, size, MIME, source, retention, legal hold and object version/reference. | Searchable control. |
| OBJ-FR-006 | 72 | WORM/immutability | Release/archive profile supports Object Lock/immutability policy or equivalent on-prem retention lock. | Tamper resistance. |
| OBJ-FR-007 | 72 | Retention mode | Governance/compliance/provider-specific retention mode selected by deployment and legal requirements; config protected. | Controlled storage. |
| OBJ-FR-008 | 72 | Evidence manifest | Regulated record/release package references immutable manifest of evidence IDs/hashes/versions. | Inspection. |
| OBJ-FR-009 | 72 | Large raw evidence | Machine files, images, PDFs, instrument exports, reports and cycle evidence stored without loading into DB blob columns. | Scale. |
| OBJ-FR-010 | 72 | Multipart upload | Large files use resumable/multipart upload with final whole-object integrity verification. | Reliability. |
| OBJ-FR-011 | 72 | Pre-signed URL | Temporary upload/download URLs can be issued only after authorization and short expiry; URL alone not permanent authority. | Secure transfer. |
| OBJ-FR-012 | 72 | Download authorization | Service validates subject/resource/evidence access before generating download token. | Confidentiality. |
| OBJ-FR-013 | 72 | Encryption | Provider at-rest encryption with customer/dedicated keys where profile requires; TLS in transit. | Security. |
| OBJ-FR-014 | 72 | Malware/quarantine | Externally uploaded files scanned/quarantined before ordinary access where applicable. | Security. |
| OBJ-FR-015 | 72 | Type validation | MIME/extension/content signature/size policies validated; filenames treated as metadata only. | Upload safety. |
| OBJ-FR-016 | 72 | Hash verification | Hash verified at ingest, copy/archive, restore and optionally periodic integrity scans. | Integrity. |
| OBJ-FR-017 | 72 | No in-place edit | Corrected document/file creates new evidence object/version and relationship; original retained. | History. |
| OBJ-FR-018 | 72 | Legal hold | Hold prevents normal expiry/delete regardless of retention schedule. | Governance. |
| OBJ-FR-019 | 72 | Retention expiration | Purge eligibility determined by Records service + holds + reference policy, not bucket lifecycle alone. | Controlled deletion. |
| OBJ-FR-020 | 72 | Lifecycle tiers | Archive/cold tiers allowed if retrieval SLA/validation/immutability requirements met. | Cost control. |
| OBJ-FR-021 | 72 | Cross-region/site replication | Optional replication configured per deployment/DR profile; replica integrity monitored. | DR. |
| OBJ-FR-022 | 72 | Backup distinction | Replication/versioning is not backup; backup/restore strategy explicitly tested. | Resilience. |
| OBJ-FR-023 | 72 | Missing object | Broken evidence metadata→object relation triggers critical integrity event and release/inspection blocker where relevant. | Fail safe. |
| OBJ-FR-024 | 72 | Orphan detection | Unreferenced objects/staged uploads detected and handled via controlled cleanup policies. | Hygiene. |
| OBJ-FR-025 | 72 | Evidence provenance | Store producer, source device/system, uploaded actor/service, timestamps and source hash where supplied. | Traceability. |
| OBJ-FR-026 | 72 | Rendering | Generated PDFs/renditions are separate evidence objects linked to canonical data/version and renderer version. | Reproducibility. |
| OBJ-FR-027 | 72 | Export package | Inspection export creates manifest, files, hashes and metadata without changing source evidence. | Portable evidence. |
| OBJ-FR-028 | 72 | Restore validation | Restored archive verifies object count/manifests/hashes and sampled retrieval before healthy. | DR assurance. |
| OBJ-FR-029 | 72 | Provider migration | Storage-provider migration uses manifest/hash copy verification and retains old location until acceptance. | Cloud portability. |
| OBJ-FR-030 | 72 | No bucket browsing | Users/apps do not receive broad bucket listing credentials; access is resource-scoped. | Least privilege. |
| EVT-FR-001 | 73 | Canonical event envelope | Every event has event_id, type, schema version, aggregate id/version, tenant/site, correlation/causation, occurred_at and payload. | Stable contract. |
| EVT-FR-002 | 73 | Transactional outbox | Authoritative GxP event inserted in same PostgreSQL transaction as domain state/audit. | Atomic source. |
| EVT-FR-003 | 73 | Outbox publisher | Publisher reads committed pending events and publishes to NATS/JetStream idempotently. | Reliable delivery. |
| EVT-FR-004 | 73 | Publish acknowledgement | Outbox marked published only after broker acknowledgement according to configured durable stream semantics. | No lost publish. |
| EVT-FR-005 | 73 | At-least-once consumers | Consumers assume duplicate delivery and must be idempotent. | Correct distributed model. |
| EVT-FR-006 | 73 | Consumer inbox/dedupe | Critical consumer maintains processed event IDs/result/version to prevent duplicate business effect. | Replay safe. |
| EVT-FR-007 | 73 | Subject naming | Versioned subject namespace includes environment/domain/event but avoids leaking sensitive data in subject names. | Operable. |
| EVT-FR-008 | 73 | Stream configuration | Durable streams define retention, storage, replicas, max age/size and permissions per event class. | Controlled messaging. |
| EVT-FR-009 | 73 | Consumer durability | Durable named consumers with explicit ack/retry/backoff for critical projections/integrations. | Recovery. |
| EVT-FR-010 | 73 | Dead letter strategy | Poison events moved/recorded for manual review after bounded attempts without deleting original event. | No loss. |
| EVT-FR-011 | 73 | Schema registry | JSON Schema/AsyncAPI event definitions versioned and CI compatibility-tested. | Contract governance. |
| EVT-FR-012 | 73 | Backward compatibility | Compatible additive changes preferred; breaking change uses new schema/event version and migration plan. | Safe evolution. |
| EVT-FR-013 | 73 | No sensitive payload excess | Event payload minimizes PII/secrets; sensitive content uses reference when possible. | Security. |
| EVT-FR-014 | 73 | Ordering | Per aggregate version ordering validated; consumers handle late/out-of-order events and reject stale projections. | Consistency. |
| EVT-FR-015 | 73 | No global ordering assumption | Architecture never assumes total order across all aggregates/services. | Scale. |
| EVT-FR-016 | 73 | Replay | Authorized stream/outbox replay uses event identity/version and does not re-execute non-idempotent business effect incorrectly. | Recovery. |
| EVT-FR-017 | 73 | Backfill tag | Bulk/projector rebuild may use source snapshot/events with explicit replay/backfill context. | Semantics. |
| EVT-FR-018 | 73 | Broker outage | Domain transaction still commits with outbox; publisher catches up after broker recovery. | Resilience. |
| EVT-FR-019 | 73 | Database outage | Publisher/consumer does not fabricate state; broker retention alone cannot commit GxP truth. | Boundary. |
| EVT-FR-020 | 73 | NATS auth | Service identities have publish/subscribe ACLs limited to required subjects. | Security. |
| EVT-FR-021 | 73 | TLS | NATS connections TLS/mTLS according to deployment profile. | Transport security. |
| EVT-FR-022 | 73 | Multi-tenant subjects | Dedicated deployment baseline still carries tenant/site in envelope; ACL/subject design prevents accidental cross-scope. | Isolation. |
| EVT-FR-023 | 73 | Large payload | Large files stay object store; event contains evidence ref/hash, not multi-MB blobs. | Scale. |
| EVT-FR-024 | 73 | Event retention | Broker retention chosen for operational replay, not regulatory long-term archive; authoritative event/audit/evidence retention remains elsewhere. | Boundary. |
| EVT-FR-025 | 73 | Observability | Outbox age, publish lag, stream lag, consumer ack pending, redelivery and DLQ monitored. | Operations. |
| EVT-FR-026 | 73 | Consumer failure policy | Business validation failure differs from transient dependency failure; poison event does not retry forever. | Stability. |
| EVT-FR-027 | 73 | Projection consumers | Projection worker stores source aggregate/event version and ignores duplicate/stale event safely. | Correct projection. |
| EVT-FR-028 | 73 | Integration consumers | ERP/LIMS/Edge integration commands derive from source event and own idempotency/reconciliation. | Integration safety. |
| EVT-FR-029 | 73 | Schema ownership | Event producer owns schema; consumers cannot reinterpret fields inconsistently. | Governance. |
| EVT-FR-030 | 73 | No event-sourcing assumption | The platform uses events/outbox for integration; not every domain aggregate is rebuilt solely from broker events unless explicitly specified. | Architecture clarity. |
| TMP-FR-001 | 74 | Temporal role | Temporal coordinates long-running workflows/retries/timers/human waits; domain state remains GxP authoritative. | Boundary. |
| TMP-FR-002 | 74 | Workflow identity | Workflow ID derived from stable business process identity to prevent accidental duplicate orchestration. | Idempotency. |
| TMP-FR-003 | 74 | Deterministic workflow | Workflow code must be deterministic/replay-safe; external calls/DB writes occur only in Activities. | Temporal correctness. |
| TMP-FR-004 | 74 | Activity idempotency | Activities performing side effects use GxP/integration idempotency keys. | Retry safe. |
| TMP-FR-005 | 74 | Workflow versioning | Code changes use Temporal-supported versioning/deployment strategy; in-flight workflows remain compatible. | Upgrade safety. |
| TMP-FR-006 | 74 | No regulatory truth | Temporal search attributes/history are not official batch/QMS/release records. | Clear authority. |
| TMP-FR-007 | 74 | Domain command | Workflow Activity calls GxP API/Mutation Gateway and waits for receipt/result. | Correct mutation. |
| TMP-FR-008 | 74 | Signals | Human/external decisions enter workflow through authenticated service that first persists authoritative domain decision where appropriate. | No hidden decision. |
| TMP-FR-009 | 74 | Queries | Workflow queries are operational view only; regulated UI fetches domain authoritative state. | Freshness. |
| TMP-FR-010 | 74 | Timers | Due dates/escalations/timed waits can use durable Temporal timers while due-date source remains domain/regulatory record. | Scheduling. |
| TMP-FR-011 | 74 | Retry policy | Activity retry/backoff explicitly defined by error class; business validation/signature denial not retried blindly. | Correct recovery. |
| TMP-FR-012 | 74 | Timeouts | Start-to-close/schedule-to-close/heartbeat timeouts configured by activity. | Bounded. |
| TMP-FR-013 | 74 | Heartbeats | Long-running activities heartbeat progress/cancellation as applicable. | Recovery. |
| TMP-FR-014 | 74 | Cancellation | Workflow cancellation maps to authorized domain cancellation/compensation rules; never silently abandons regulated process. | Controlled. |
| TMP-FR-015 | 74 | Compensation | Saga compensation is new domain transaction, not rollback of immutable GxP history. | History. |
| TMP-FR-016 | 74 | Human tasks | Temporal may wait for QA/action completion but task authority/status exists in domain/QMS record. | No workflow-only task. |
| TMP-FR-017 | 74 | Child workflows | Use child workflows for bounded subprocesses where ownership/lifecycle warrants; avoid monolithic eternal workflow. | Maintainability. |
| TMP-FR-018 | 74 | Continue-as-new | Long histories use continue-as-new with business identity/correlation preserved. | Scale. |
| TMP-FR-019 | 74 | Namespace | Separate environment/customer deployment namespace/profile; production isolated from non-prod. | Isolation. |
| TMP-FR-020 | 74 | Worker identity | Workers use service identities with only required GxP/integration scopes. | Security. |
| TMP-FR-021 | 74 | Task queues | Queues partitioned by domain/workload/priority; worker deployment/version controlled. | Operations. |
| TMP-FR-022 | 74 | Temporal HA | Self-hosted/managed deployment profile meets availability/backup requirements for orchestration state. | Reliability. |
| TMP-FR-023 | 74 | Temporal outage | Existing GxP records remain valid; new/continuing orchestration pauses/degrades explicitly and resumes after recovery. | Resilience. |
| TMP-FR-024 | 74 | GxP DB outage | Activities fail/retry; workflows never invent successful domain transition. | Truth. |
| TMP-FR-025 | 74 | Visibility | Workflow ID/run/status/activity failures/correlation visible in operations UI, not as regulated source. | Support. |
| TMP-FR-026 | 74 | Audit linkage | Domain records store workflow/correlation IDs for troubleshooting; GxP Audit logs actual regulated action. | Cross-reference. |
| TMP-FR-027 | 74 | Security | Temporal Web/admin protected; workers TLS/auth; no unrestricted public access. | Security. |
| TMP-FR-028 | 74 | Data minimization | Workflow payloads avoid large evidence/PII; use IDs/references. | Efficiency/privacy. |
| TMP-FR-029 | 74 | Backup/restore | Temporal persistence backed up per deployment; restore tested for orchestration continuity, not GxP data recovery. | DR. |
| TMP-FR-030 | 74 | Testing | Workflow replay tests, time-skipping tests, activity failure/retry and version compatibility mandatory. | Assurance. |
| READ-FR-001 | 75 | Read-model purpose | Caches/search/read models improve UX/reporting but are non-authoritative projections. | Boundary. |
| READ-FR-002 | 75 | Redis usage | Redis may store sessions, rate limits, ephemeral locks, cache entries and queues only where architecture permits. | Controlled cache. |
| READ-FR-003 | 75 | No GxP truth in Redis | No regulated state/signature/audit/release result exists only in Redis. | Durability. |
| READ-FR-004 | 75 | Cache key scope | Tenant/site/user/entity/version included where necessary to prevent cross-scope leakage. | Isolation. |
| READ-FR-005 | 75 | TTL | Every cache class has TTL/invalidation strategy; infinite cache of mutable regulated data prohibited. | Freshness. |
| READ-FR-006 | 75 | Cache stampede | Use bounded locking/single-flight/jitter where high-cost queries need it. | Stability. |
| READ-FR-007 | 75 | Cache invalidation | Authoritative event/version invalidates/updates cache; regulated action can bypass cache. | Correctness. |
| READ-FR-008 | 75 | Search engine optional | OpenSearch/Elasticsearch-compatible or database search provider is pluggable; product not hard-dependent on one commercial engine. | Portability. |
| READ-FR-009 | 75 | Search index fields | Index only allowed searchable fields; sensitive/PII excluded or restricted. | Privacy. |
| READ-FR-010 | 75 | Search authorization | Search query applies tenant/site/role/resource filters; result ID then re-authorized on fetch. | No information leakage. |
| READ-FR-011 | 75 | No index authority | Search state/status never used as final release/signature target without authoritative fetch/version validation. | Consistency. |
| READ-FR-012 | 75 | Index version | Indexed document carries source entity ID/version/projected_at. | Trace. |
| READ-FR-013 | 75 | Stale results | UI can show stale/indexing status and authoritative detail refresh. | Transparency. |
| READ-FR-014 | 75 | Index rebuild | Full index can be dropped/recreated from authoritative source or projections. | Recoverability. |
| READ-FR-015 | 75 | Read model | Complex dashboards use dedicated read models/materialized views rather than deep cross-domain synchronous joins. | Performance. |
| READ-FR-016 | 75 | Materialized view refresh | Refresh mode/cadence/cutoff visible and not used for current regulated decision if stale. | Correctness. |
| READ-FR-017 | 75 | Report snapshots | Official reports/management packages freeze source cutoff/version independently of live dashboards. | Reproducibility. |
| READ-FR-018 | 75 | Analytics warehouse | Optional warehouse/lake export is one-way governed projection, not authoritative GxP write path. | Data architecture. |
| READ-FR-019 | 75 | ETL/ELT lineage | Exports include source IDs/versions/cutoff and transformation version. | Lineage. |
| READ-FR-020 | 75 | Read replica | PostgreSQL replicas can support bounded reporting where staleness accepted. | Scale. |
| READ-FR-021 | 75 | List pagination | Cursor/keyset pagination preferred for large operational lists; bounded page size. | Performance. |
| READ-FR-022 | 75 | Filter allowlist | Search/list filter/sort fields explicitly allowlisted/indexed to prevent abusive arbitrary queries. | Resource safety. |
| READ-FR-023 | 75 | Export limits | Large exports asynchronous with source snapshot/cutoff, authorization and expiration. | Scale/security. |
| READ-FR-024 | 75 | Session cache | Session revocation/authorization-critical state cannot be indefinitely cached past revocation policy. | Security. |
| READ-FR-025 | 75 | Rule/config cache | Released rule/master caches keyed by exact version and immutable content hash where possible. | Safe cache. |
| READ-FR-026 | 75 | Negative cache | Missing/denied resource caching scoped carefully and short-lived to avoid stale authorization/data visibility. | Correctness. |
| READ-FR-027 | 75 | Cache outage | Application degrades to authoritative reads or explicit unavailable; must not fabricate data. | Resilience. |
| READ-FR-028 | 75 | Search outage | Core regulated execution remains available where architecture allows; search/list UX may degrade. | Resilience. |
| READ-FR-029 | 75 | Observability | Hit ratio, latency, evictions, memory, index lag, rebuild progress and query performance monitored. | Operations. |
| READ-FR-030 | 75 | No sensitive logs | Search queries/cache keys/logs avoid leaking secrets/patient sensitive content. | Security. |
| DR-FR-001 | 76 | Recovery objectives | Define RPO/RTO per component and business capability, approved by customer/product profile. | Measurable recovery. |
| DR-FR-002 | 76 | Tier classification | Classify GxP PostgreSQL, MariaDB, object evidence, NATS, Temporal, search/cache, observability, config/secrets by criticality. | Prioritized. |
| DR-FR-003 | 76 | PostgreSQL backup | Use base/full/incremental/managed backups plus WAL/PITR according to deployment profile. | Recoverability. |
| DR-FR-004 | 76 | WAL archive | WAL archiving protected, monitored and retained to meet PITR/RPO window. | PITR. |
| DR-FR-005 | 76 | Backup manifest | Backup includes manifest/checksum/metadata and is immutable/protected from production compromise. | Integrity. |
| DR-FR-006 | 76 | MariaDB backup | Frappe/MariaDB backups scheduled and encrypted; projection freshness expected after restore. | Operational recovery. |
| DR-FR-007 | 76 | Object storage protection | Object versioning/immutability/replication plus independent backup/export strategy as deployment requires. | Evidence recovery. |
| DR-FR-008 | 76 | NATS backup | Stream configuration/state backup/recovery documented, but domain recovery must not depend solely on NATS history. | Messaging recovery. |
| DR-FR-009 | 76 | Temporal backup | Temporal persistence backup/managed DR configured for orchestration; GxP records recover independently. | Orchestration recovery. |
| DR-FR-010 | 76 | Secrets/KMS backup | Key/secret recovery strategy prevents encrypted backups becoming unrecoverable. | Crypto recovery. |
| DR-FR-011 | 76 | Infrastructure config | IaC, manifests, config versions, certificates/trust metadata and deployment parameters backed by source/control plane. | Rebuildability. |
| DR-FR-012 | 76 | Offsite/isolation | Backups logically/physically isolated from normal production credentials/ransomware path. | Resilience. |
| DR-FR-013 | 76 | Encryption | Backups encrypted in transit/at rest; key access separate. | Security. |
| DR-FR-014 | 76 | Retention generations | Daily/weekly/monthly or equivalent retention derived from RPO/history/regulatory needs, not one hardcoded schedule. | Flexible. |
| DR-FR-015 | 76 | Backup monitoring | Backup start/completion/size/age/checksum/WAL gap/replication failures alert. | Reliability. |
| DR-FR-016 | 76 | Restore testing | Automated regular restore test into isolated environment; application-level integrity checks mandatory. | Evidence. |
| DR-FR-017 | 76 | PITR test | Demonstrate recovery to selected timestamp/LSN within objective and validate audit/event continuity. | Point-in-time confidence. |
| DR-FR-018 | 76 | Application consistency | Restore runbook defines recovery order/checkpoints across PostgreSQL/object/MariaDB/Temporal/NATS. | Cross-system consistency. |
| DR-FR-019 | 76 | Object reconciliation | After restore verify evidence metadata→object references/hashes. | Evidence integrity. |
| DR-FR-020 | 76 | Projection rebuild | Frappe/search/cache/read models can rebuild from recovered authoritative data. | Recovery simplification. |
| DR-FR-021 | 76 | DR site/region | Enterprise profile can use secondary region/site with documented replication/failover mode. | Availability. |
| DR-FR-022 | 76 | Failover authority | Primary DB promotion/failover uses controlled operator/automation with split-brain prevention. | Data integrity. |
| DR-FR-023 | 76 | Failback | Failback/rejoin procedure tests data divergence and does not simply overwrite new primary. | Recovery. |
| DR-FR-024 | 76 | Disaster declaration | DR activation has incident/change record, owner, time and affected services. | Governance. |
| DR-FR-025 | 76 | Validation before reopen | Recovered environment passes defined smoke/integrity/security/GxP checks before accepting regulated work. | Safe restart. |
| DR-FR-026 | 76 | Data-loss assessment | If recovery loses data beyond expected RPO, system identifies missing range/events and creates incident/GxP assessment. | Transparency. |
| DR-FR-027 | 76 | Offline customer | On-prem customer backup destination/runbook supports customer-operated storage without weakening integrity evidence. | Deployment. |
| DR-FR-028 | 76 | Backup deletion | Backup expiry/destruction follows controlled lifecycle and legal/security policies. | Governance. |
| DR-FR-029 | 76 | Restore access | Only privileged recovery role may perform restore; all operations audited. | Security. |
| DR-FR-030 | 76 | DR evidence | Each test records backup set, restore target, timings, checks, RPO/RTO achieved, failures and remediation. | Validation. |
| DR-FR-031 | 76 | Capacity | Backup target has growth forecast and alerts before exhaustion. | Operations. |
| DR-FR-032 | 76 | No replica-as-backup | Replication/standby alone is not considered backup. | Correct resilience. |
| DEP-FR-001 | 77 | Deployment profiles | Support AWS, Azure, private cloud/on-prem Kubernetes and controlled VM/container profile without vendor-specific domain code. | Cloud-neutral. |
| DEP-FR-002 | 77 | Dedicated customer deployment | Baseline production uses dedicated customer deployment/isolation; multi-tenant shared deployment requires separate architecture approval. | Enterprise. |
| DEP-FR-003 | 77 | Environment separation | dev/test/validation/staging/prod logically separated with distinct secrets/data/endpoints. | SDLC. |
| DEP-FR-004 | 77 | IaC | Infrastructure defined in version-controlled Terraform/OpenTofu/Helm/Kustomize or approved equivalents. | Reproducible. |
| DEP-FR-005 | 77 | Immutable images | Services deployed from signed immutable image digest/release. | Supply-chain. |
| DEP-FR-006 | 77 | Configuration | Environment config separated from code; GxP/security config version controlled and approved as required. | Change control. |
| DEP-FR-007 | 77 | Kubernetes namespaces | Separate platform/GxP/integration/observability or equivalent boundaries with service accounts/network policy. | Isolation. |
| DEP-FR-008 | 77 | Stateless services | Frappe/GxP APIs/workers run as stateless horizontally scalable deployments where architecture permits. | Scale. |
| DEP-FR-009 | 77 | Stateful services | Managed services preferred where suitable; self-hosted stateful components use operators/StatefulSets/VMs with tested persistence/backup. | Reliability. |
| DEP-FR-010 | 77 | Persistent volumes | PVC/storage class performance/durability/retention explicitly configured; PVC retention not backup. | Storage. |
| DEP-FR-011 | 77 | Ingress | TLS ingress/API gateway with WAF/rate limits as deployment requires; admin endpoints segregated. | Security. |
| DEP-FR-012 | 77 | Service discovery | Internal DNS/service names stable and environment-scoped. | Runtime. |
| DEP-FR-013 | 77 | Secrets | External secret manager/CSI/operator or controlled equivalent; no plaintext Kubernetes Secret manifests in repo. | Security. |
| DEP-FR-014 | 77 | PKI | Service/Edge certificates provisioned through documented CA/KMS workflow. | Identity. |
| DEP-FR-015 | 77 | Database endpoints | Managed/private endpoints or internal-only services; no public DB. | Security. |
| DEP-FR-016 | 77 | Object store | Provider abstraction maps S3/Azure/on-prem endpoints and WORM/immutability capabilities. | Portability. |
| DEP-FR-017 | 77 | NATS | NATS cluster/service profile pins version, storage, replicas, TLS/auth, monitoring and backup/config. | Messaging. |
| DEP-FR-018 | 77 | Temporal | Temporal Cloud/self-hosted profile with namespace/auth/persistence/worker config. | Orchestration. |
| DEP-FR-019 | 77 | Redis/search | Optional deployment with HA/persistence according to cache/search role; service can degrade if unavailable. | Read layer. |
| DEP-FR-020 | 77 | Resource requests/limits | Kubernetes workloads define requests/limits based on load tests; avoid arbitrary tiny defaults. | Scheduling. |
| DEP-FR-021 | 77 | Probes | Startup/readiness/liveness probes are service-semantic; readiness fails when dependency needed to serve safely is unavailable. | Correct routing. |
| DEP-FR-022 | 77 | Graceful shutdown | APIs/workers drain requests/jobs/outbox leases before termination within configured grace. | Safe rollout. |
| DEP-FR-023 | 77 | Pod disruption | PDB/topology spread/anti-affinity used where availability warrants. | Resilience. |
| DEP-FR-024 | 77 | Autoscaling | Stateless workers/API HPA/KEDA or equivalent uses safe metrics and max bounds; DB connections considered. | Scale. |
| DEP-FR-025 | 77 | Rolling deploy | Rolling/canary/blue-green strategy per service risk; DB migrations backward compatible across rollout window. | Availability. |
| DEP-FR-026 | 77 | Rollback | Application rollback does not blindly reverse incompatible DB migration; migration compatibility plan explicit. | Safe release. |
| DEP-FR-027 | 77 | On-prem install | Air-gapped/private registry/offline package mode supported for enterprise plants where required. | Deployment. |
| DEP-FR-028 | 77 | On-prem prerequisites | CPU/RAM/storage/network/NTP/DNS/PKI/backup prerequisites machine-checkable before install. | Successful setup. |
| DEP-FR-029 | 77 | Installation validation | Post-install automated health/security/data/queue/storage/auth checks produce evidence report. | Qualification aid. |
| DEP-FR-030 | 77 | Upgrade | Upgrade preflight, backup, migration, deployment, smoke tests, rollback decision and validation evidence. | Controlled change. |
| DEP-FR-031 | 77 | Infrastructure drift | Detect IaC/config drift in production and alert/require reconciliation. | Validated state. |
| DEP-FR-032 | 77 | Feature flags | Runtime flags versioned/scoped; GxP-affecting flag cannot silently change regulated behavior outside change/release controls. | Safe config. |
| DEP-FR-033 | 77 | Time sync | All hosts/nodes use approved UTC/NTP/PTP strategy and monitor offset. | Chronology. |
| DEP-FR-034 | 77 | Certificate/DNS expiry | Monitor certificates/domains/dependencies before expiry. | Availability. |
| DEP-FR-035 | 77 | No single-node assumption | Production reference can scale beyond one host; on-prem compact profile explicitly documents reduced HA. | Commercial scalability. |
| SRE-FR-001 | 78 | Service objectives | Define availability/latency/durability/freshness SLOs per critical capability, not one generic uptime number. | Meaningful reliability. |
| SRE-FR-002 | 78 | SLI | Measure API availability/latency, DB commit latency, queue lag, projection freshness, Edge delivery lag, evidence availability and restore readiness. | Observable. |
| SRE-FR-003 | 78 | Scale baseline | Design target includes 10+ plants/customer, 250+ concurrent/customer, 50+ batches/day/plant, thousands steps/batch and millions audit events/day without redesign. | Capacity. |
| SRE-FR-004 | 78 | Load model | Synthetic workload models users, batch steps, signatures, audit writes, events, equipment data, QC/QMS and reports. | Realistic testing. |
| SRE-FR-005 | 78 | Capacity unit | Define plant/customer capacity units and growth factors for DB, CPU, memory, storage, events and object evidence. | Forecast. |
| SRE-FR-006 | 78 | Headroom | Production capacity keeps configurable headroom for bursts/failover/maintenance. | Resilience. |
| SRE-FR-007 | 78 | API budgets | Critical interactive API p50/p95/p99 targets defined by operation class and tested. | UX. |
| SRE-FR-008 | 78 | Signature latency | Signature challenge/verify/commit measured independently. | Critical workflow. |
| SRE-FR-009 | 78 | Mutation throughput | Benchmark GxP mutation path including audit/outbox and concurrency. | Core performance. |
| SRE-FR-010 | 78 | Audit throughput | Audit partition/index/WAL capacity load tested at projected millions/day and burst rates. | Scale. |
| SRE-FR-011 | 78 | Event lag | Outbox/NATS/consumer lag SLOs and alerts. | Async health. |
| SRE-FR-012 | 78 | Projection freshness | Frappe/search/read model lag measured and surfaced. | UI correctness. |
| SRE-FR-013 | 78 | DB capacity | Monitor CPU, IOPS, WAL rate, storage growth, bloat, locks, connections, cache hit, replica lag. | DB operations. |
| SRE-FR-014 | 78 | Object capacity | Monitor object count/bytes, upload/download latency, archive tier, integrity failures, growth. | Evidence. |
| SRE-FR-015 | 78 | Temporal capacity | Monitor workflow starts, task-queue backlog, activity latency/failures, history size. | Orchestration. |
| SRE-FR-016 | 78 | Edge capacity | Per gateway connector/read rate, buffer depth, disk horizon and uplink bandwidth model. | Plant. |
| SRE-FR-017 | 78 | Report isolation | Heavy reports/exports use replicas/read models/async jobs and bounded resources. | Protect core. |
| SRE-FR-018 | 78 | Resource limits | CPU/memory limits avoid noisy-neighbor/OOM while not causing artificial throttling; based on measured load. | Runtime. |
| SRE-FR-019 | 78 | Autoscaling | Scale stateless services using safe metrics such as CPU, latency, queue depth, not DB connection count alone. | Elasticity. |
| SRE-FR-020 | 78 | Backpressure | Queues/workers apply bounded concurrency and backpressure instead of accepting infinite work. | Stability. |
| SRE-FR-021 | 78 | Rate limits | Protect expensive APIs/exports/integrations while preserving critical plant execution capacity. | Resilience. |
| SRE-FR-022 | 78 | Graceful degradation | Search/analytics/notifications may degrade independently; critical GxP execution dependency matrix defines what must stop. | Availability. |
| SRE-FR-023 | 78 | Health semantics | Liveness, readiness, startup and dependency health differentiated. | Correct orchestration. |
| SRE-FR-024 | 78 | Structured metrics | Prometheus/OpenTelemetry-compatible metrics with stable names/labels and cardinality controls. | Observability. |
| SRE-FR-025 | 78 | Distributed tracing | Trace critical request across Frappe/API/Mutation/DB/outbox/integration without leaking sensitive payloads. | Diagnostics. |
| SRE-FR-026 | 78 | Logs | Structured correlation IDs and redaction; no uncontrolled full request bodies. | Support/security. |
| SRE-FR-027 | 78 | Dashboards | Role-specific service, DB, batch-execution, integration, Edge, security and DR dashboards. | Operations. |
| SRE-FR-028 | 78 | Alert policy | Alerts linked to user/business impact with severity, runbook and dedupe; avoid noisy metric-only alerts. | Actionable. |
| SRE-FR-029 | 78 | Runbooks | Every critical alert/dependency has runbook including verification, containment and escalation. | Operational readiness. |
| SRE-FR-030 | 78 | Error budget | SLO error budget informs reliability work/release risk where organization adopts SRE practice. | Governance. |
| SRE-FR-031 | 78 | Soak test | Long-duration tests detect leaks, partition/outbox growth, worker drift and cache problems. | Stability. |
| SRE-FR-032 | 78 | Failure injection | Test DB failover, broker outage, Temporal outage, object-store latency, Edge reconnect and dependency throttling safely. | Resilience. |
| SRE-FR-033 | 78 | Capacity review | Quarterly/customer growth or threshold-triggered capacity review with forecast horizon. | Planning. |
| SRE-FR-034 | 78 | Storage forecast | Forecast relational, WAL, backup, object evidence, historian and logs separately. | Cost/reliability. |
| SRE-FR-035 | 78 | Performance regression | CI/release performance baseline detects critical regressions before production. | Quality. |
| SRE-FR-036 | 78 | No hidden optimization | Performance changes that alter regulated semantics, precision, retention or durability require explicit review. | Integrity. |
