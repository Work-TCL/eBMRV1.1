# `dbops` — PostgreSQL GxP Database Architecture (Document 70 / SPEC-DATA-002)

Document 70 declares **0 owned entities, 0 HTTP APIs, 6 operational-signal events, no signatures**. It
is a *construction standard*: it fixes how every other module's PostgreSQL schema, transactions,
concurrency, partitioning and integrity are built, and adds a small helper library + health signals.
This file is the machine-checkable record of where each PG-FR is satisfied.

| PG-FR | Requirement | Where enforced / evidenced |
|---|---|---|
| PG-FR-001 | Supported version pin | Deployment pins a validated PostgreSQL major (18 is the current doc line); no auto major upgrade. `reference/env` records the pinned version; upgrade goes through Change/Validation. **Policy statement — no code artefact.** |
| PG-FR-002 | Cluster topology | Reference supports managed PG or self-hosted primary+replica(s). Phase 1 = single primary; `dbops/read_routing.py` is written so a future replica needs no caller changes. |
| PG-FR-003 | Database separation | GxP PostgreSQL (`ebmr_new_gxp`) is a distinct cluster/database from Frappe MariaDB (AG-03/AG-04). |
| PG-FR-004 | Schema ownership | One schema per bounded context (`ebmr`, `audit`, `vault`, `signature`, `mutation`, `iam`, `rules`, `materials`, `qms`, `equipment`, `erp`, `edge`, `machine_integration`, `security`, `dataops`, …). Only the owning service's migration package alters its tables (DATA-FR-025 / MIG-FR-001). |
| PG-FR-005 | Runtime roles | `ebmr_new_gxp_app` is granted only `SELECT/INSERT/UPDATE/TRUNCATE` (no `DELETE`, no DDL) on its tables; every migration ends `REVOKE CREATE ON SCHEMA ... FROM app`. |
| PG-FR-006 | Migration role | `ebmr_new_migrator` is a separate, higher-privileged role used only by Alembic (`GXP_MIGRATION_DATABASE_URL`); the runtime never has DDL. |
| PG-FR-007 | UUID identity | Every aggregate PK is `uuid` (`default=uuid.uuid4`); external IDs are separate reference columns. |
| PG-FR-008 | Optimistic version | Every mutable aggregate carries `version bigint`; `dbops/concurrency.py::apply_optimistic_update` is the canonical `UPDATE ... WHERE id=? AND version=?` helper (rowcount 1 or `STALE_VERSION`). |
| PG-FR-009 | Foreign keys | FKs used within a bounded context; cross-service references are logical IDs / events (no cross-schema FK coupling). |
| PG-FR-010 | Check constraints | Structural invariants (state enums, non-negative counts) encoded as `CHECK` / `NOT NULL` where stable; business config stays in the rules service. |
| PG-FR-011 | Unique constraints | `mutation.idempotency_keys` PK, `command_receipts` unique keys, external-mapping unique keys, per-module `UniqueConstraint`s (e.g. `dataops.data_ownership_registry(entity_type)`). |
| PG-FR-012 | Transaction isolation | Default `READ COMMITTED`; `dbops/concurrency.py::with_deadlock_retry` retries SQLSTATE `40P01`/`40001` a bounded number of times, else `DEADLOCK_DETECTED`. |
| PG-FR-013 | No long transactions | Signature challenge, policy lookup and any external I/O happen **outside** `db.transaction(...)` (see `.claude/rules/01`); the gateway transaction only does domain+version+audit+outbox. |
| PG-FR-014 | Outbox atomicity | `app/mutation/gateway.py`: `write_audit_event` + `write_outbox_event` + domain write + `record_command_receipt` in one `session.begin()`. Proven by `tests/test_dbops_pg_architecture.py::test_outbox_atomic_rollback`. |
| PG-FR-015 | Append-only tables | `audit.audit_events`, `mutation.outbox_events`, `signature.signatures`, `vault.*` — app role has no `UPDATE`/`DELETE` grant (privilege-level, not app-level). |
| PG-FR-016 | Partitioning candidates | `gxp_audit_event` / `gxp_outbox` are the approved RANGE-partition candidates (spec # 6). `dbops/partitioning.py` is the create/verify mechanism; wiring a parent to partitioning is a separate *measured* migration (not applied pre-emptively). |
| PG-FR-017 | Partition key design | Time (`occurred_at` month) partition key aligns retention + query pattern; no per-tenant partitioning (single-tenant per deployment, ADR-0006). |
| PG-FR-018 | Indexes | Indexes are added from documented query patterns per module (e.g. `ix_vulnerability_record_state`); JSONB columns are not blanket-indexed. |
| PG-FR-019 | JSONB use | JSONB for versioned payloads / evidence / config snapshots; frequently-queried keys are columns. |
| PG-FR-020 | Decimal/UOM | Regulated quantities use `NUMERIC`/`Decimal` (Document 110); `dbops` adds no float columns; guardrail forbids binary float for regulated quantities. |
| PG-FR-021/022 | Timestamps / DB timezone | All persisted regulatory timestamps are `timestamptz`; server/session time treated as UTC; source/local time stored separately where needed. |
| PG-FR-023 | Data checksums | `dbops/integrity.py::run_database_integrity_check` reads `pg_stat_database.checksum_failures`; deployment profile enables `data_checksums` / managed-service equivalent. |
| PG-FR-024 | WAL | WAL/archiving configuration is the Backup/DR profile (Document 76); `MigrationApplied` signal records each schema change. |
| PG-FR-025 | Connection pooling | SQLAlchemy async engine pool is bounded; `ConnectionPoolExhausted` signal on saturation. |
| PG-FR-026 | Statement timeout | Per-workload `statement_timeout` / `lock_timeout` set at the deployment/session level. |
| PG-FR-027 | Vacuum/analyze | Autovacuum monitored for high-write tables; manual maintenance is a controlled runbook. |
| PG-FR-028 | Slow query monitoring | `pg_stat_statements` / managed equivalent; parameters not logged indiscriminately. |
| PG-FR-029 | DDL safety | Migrations are expand-only / additive where possible; destructive changes staged + reversible (`downgrade()` tested); `.claude/rules/08`. |
| PG-FR-030 | Partition lifecycle | `dbops/partitioning.py::verify_partition_coverage` alerts before a gap; `PARTITION_GAP_DETECTED`; detach/archive/drop only via retention workflow (Document 76/108). |
| PG-FR-031 | Replica reads | `dbops/read_routing.py`: `get_primary_consistency_read` (regulated reads, fail closed `PRIMARY_UNAVAILABLE`) vs `run_read_replica_query` (reporting, `REPLICA_TOO_STALE` beyond `max_staleness`). |
| PG-FR-032 | Integrity verification | `run_database_integrity_check` (checksums + `amcheck` btree checks when the extension is present); periodic per the ops schedule. |
| PG-FR-033 | Extensions | Extensions require an allowlist / security / license / managed-service compatibility review; currently only stock contrib (`amcheck` optional). |
| PG-FR-034 | No direct repair | Emergency repair is a privileged admin command / migration with evidence (Document 63 `admin_command`); ad-hoc `UPDATE` on regulated rows is prohibited (guardrail + no app `DELETE` grant). |

## Known limitation

`gxp_audit_event` / `gxp_outbox` are **not yet declaratively partitioned** — PG-FR-016 says partitioning
is "justified by measured volume/query/retention, not applied to every table", and Phase 1 has no
production volume data. `dbops/partitioning.py` is the ready mechanism; converting a parent table to
RANGE partitioning is a future measured migration.
