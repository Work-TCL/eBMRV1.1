# Database migration rules

**Purpose:** Database migration rules for the eBMR/eDHR platform.
**Applicable paths/modules:** see `docs/generated/17_REPOSITORY_STRUCTURE.md`; this rule applies to every
service, the Frappe app, edge and integration code unless a narrower scope is stated below.
**Source documents:** Document 100 (SPEC-ENG-004), Document 70 (SPEC-DATA-002), Document 87 (SPEC-VAL-009)
**Source requirement IDs:** MIG-FR-001..032 (32); PG-FR-001..034 (34); MIGV-FR-001..022 (22)

---

## Required implementation pattern

Expand → migrate → contract, with at least two releases between expand and contract. Backfills are
batched, resumable and idempotent with reconciliation counts. Every migration has a tested rollback or a
documented forward-fix rationale, and an entry in `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`.

## Forbidden patterns

- migration for an entity that is not in the data model catalogue
- destructive change in a single release
- rewriting regulated rows without an approved change record
- long ACCESS EXCLUSIVE locks on high-volume regulated tables
- one service migrating another service's schema

## Required tests

forward and rollback on a restored copy; lock-duration measurement; backfill resumability; row counts and
checksums before/after; application compatibility across the window.


## Source requirements (extract)

| ID | Requirement | Required behaviour |
|---|---|---|
| MIG-FR-001 | Migration ownership | Only owning service/app migration package changes its authoritative schema. |
| MIG-FR-002 | Version order | Migrations have deterministic unique ordered IDs and are immutable after production release. |
| MIG-FR-003 | Forward-first strategy | Production migrations designed forward-compatible; rollback usually app rollback/forward fix rather than destructive schema reversal. |
| MIG-FR-004 | Expand-contract | Breaking schema evolution uses expand → dual compatibility/backfill → switch → contract after safe window. |
| MIG-FR-005 | No destructive history loss | Drop/truncate/delete of regulated/history data requires retention/migration approval and archival evidence. |
| MIG-FR-006 | Backup precondition | Risk-relevant migration checks current backup/PITR and rollback/recovery readiness. |
| MIG-FR-007 | Representative test | Migration tested against representative volume/cardinality/schema state. |
| MIG-FR-008 | Idempotency | Migration runner can detect applied state; rerun behavior explicit and safe. |
| MIG-FR-009 | Transactional DDL | Use transaction where supported/safe; nontransactional steps explicitly staged/recoverable. |
| MIG-FR-010 | Lock analysis | Estimate table locks/rewrite duration/IO/WAL impact for large table changes. |
| MIG-FR-011 | Online index | Use concurrent/online patterns when available and justified; failures leave recoverable state. |
| MIG-FR-012 | Backfill | Large data backfills chunked/checkpointed/rate-limited with deterministic transform version. |
| MIG-FR-013 | Backfill audit | Migration-generated regulated changes marked as migration provenance, not user actions. |
| MIG-FR-014 | Checksums/reconciliation | Data migration/backfill records counts/hashes/control totals before/after where material. |
| MIG-FR-015 | Constraints | New NOT NULL/FK/check constraints introduced safely after data compatibility/backfill. |
| MIG-FR-016 | Default changes | Avoid table-rewrite defaults or hidden semantics; assess existing row behavior explicitly. |
| MIG-FR-017 | Enum/state evolution | State/enum changes preserve historical readability and old worker compatibility during rollout. |
| MIG-FR-018 | App compatibility | Document minimum/maximum app versions compatible with schema during rolling deploy. |
| MIG-FR-019 | MariaDB/Frappe migrations | Frappe patches/migrations follow same version/evidence discipline; projection tables may rebuild rather than complex migrate where safer. |
| MIG-FR-020 | PostgreSQL migrations | GxP migrations executed by dedicated migration role; runtime service role has no DDL. |
| MIG-FR-021 | Object metadata | Object/evidence metadata schema migrations cannot orphan stored evidence. |
| MIG-FR-022 | Event schema coordination | Migration requiring event/API contract change coordinates deployment order and compatibility. |
| MIG-FR-023 | Temporal compatibility | Workflow code/schema changes account for in-flight histories/activity payloads. |
| MIG-FR-024 | Migration dry run | Major migration supports staging/restore-copy rehearsal with timing/evidence. |
| MIG-FR-025 | Failure recovery | Runbook states partial-step detection, resume/repair/restore criteria. |
| MIG-FR-026 | No manual prod SQL | Manual DDL/DML in production prohibited except controlled emergency repair captured into subsequent migration/change record. |
| MIG-FR-027 | Reconciliation gate | Service not healthy after migration until mandatory schema/data checks pass. |
| MIG-FR-028 | Migration evidence | Store source commit, migration IDs, start/end, runner, environment, result, counts/checks, failures. |
| MIG-FR-029 | Retention-aware contract | Dropped old columns/tables only after retention/consumer/deployment compatibility analysis. |
| MIG-FR-030 | Customer upgrade path | Every supported version has documented upgrade path or explicit intermediate hop. |
| MIG-FR-031 | Downgrade semantics | Downgrade support explicitly stated; never imply app image rollback makes DB downgrade safe. |
| MIG-FR-032 | Validation impact | GxP schema/data migrations link change impact/revalidation requirements. |
| PG-FR-001 | Supported version pin | Deployment pins a supported PostgreSQL major/minor validated for product release; no automatic major upgrade. |
| PG-FR-002 | Cluster topology | Reference supports managed PostgreSQL or self-hosted HA profile with primary + replica(s) according to availability requirements. |
| PG-FR-003 | Database separation | GxP PostgreSQL cluster/database separated from Frappe MariaDB and optionally from non-GxP analytics. |
| PG-FR-004 | Schema ownership | Schemas grouped by bounded context/service; owning service DB role owns migrations/tables. |
| PG-FR-005 | Runtime roles | Runtime role gets minimum SELECT/INSERT/UPDATE/EXECUTE needed; DDL denied. |
| PG-FR-006 | Migration role | Migration role separate from runtime role and used only during controlled deployment. |
| PG-FR-007 | UUID identity | UUIDv7/UUID or approved stable ID scheme used for distributed identities; DB sequences may supplement internal ordering. |
| PG-FR-008 | Optimistic version | Aggregate tables include bigint version and conditional UPDATE semantics. |

## SPEC_GAP triggers

Raise a SPEC_GAP rather than deciding, if you encounter: a missing signature/authorization/retention/
precision value, a conflict between two source documents, an entity without an owner, an event without a
producer, or any requirement that would need a regulated behaviour you cannot trace to
Document 100, Document 70, Document 87 or Documents 106–115.
