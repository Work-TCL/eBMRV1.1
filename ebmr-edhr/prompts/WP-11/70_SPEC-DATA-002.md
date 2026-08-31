# Claude Code prompt — WP-11 / Document 70: PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency

TASK:
Implement the PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency module (SPEC-DATA-002) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_70_PostgreSQL_GxP_Database_Schema_Partitioning_Concurrency_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: PG-FR-001..034 (34)
- Approved baselines: Document 106 (signature policy), 107 (SoD), 108 (retention), 109 (SLO/RPO),
  110 (precision/UOM), 111 (risk class), 112 (schemas/migrations), 113 (contracts), 114 (glossary)
- Phase-0 artefacts: `docs/generated/03_FUNCTION_CATALOGUE.csv`, `04_DATA_MODEL_CATALOGUE.md`,
  `05_DATABASE_OWNERSHIP_MATRIX.md`, `06_API_CATALOGUE.yaml`, `07_EVENT_CATALOGUE.yaml`,
  `14_ERROR_CODE_REGISTRY.md`, `28_INTENDED_USE_GXP_RISK_MATRIX.md`

RISK CLASS: **HIGHER-PROCESS-RISK** → scripted tests, independent review, mandatory negative and failure evidence

ARCHITECTURE CONSTRAINTS:
- Frappe is UI/configuration only; no core fork or edit.
- PostgreSQL is authoritative for regulated state; MariaDB holds read-only projections.
- Every regulated write goes through the Mutation Gateway → one PostgreSQL transaction carrying
  domain state + record version + audit event + outbox event.
- Signatures follow Document 04 + the approved Document 106 policy; login/MFA is never a signature.
- Audit, vault and evidence history is append-only and superseding.
- Outbox is the authoritative event source; NATS is transport; Temporal is orchestration only.
- Caches, projections, search and reports are rebuildable and never a regulated decision source.
- Adapters and edge never write GxP tables; they submit integration commands.
- AI is advisory; it cannot sign, release, disposition, approve, alter audit or submit reports.

PRECONDITIONS:
- WP-00 foundations exist (contracts tooling, guardrails, CI gates).
- WP-01 GxP Core is available (mutation, policy, signature, audit, vault, rules).
- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `infrastructure` and its tests
- `contracts/` entries owned by this module
- migrations for entities owned by this module
- Frappe UI surfaces for this module in `apps/ebmr_frappe/`

DO NOT:
- Do not modify anything under `specs/`.
- Do not implement a signature requirement not present in the approved Document 106 policy set
  (emit a policy row and reference the gap instead).
- Do not create a second authoritative store for an entity owned elsewhere.
- Do not add an endpoint to a module whose exposure boundary is "no independent API" (Document 113 §6).
- Do not write a migration for an entity absent from `docs/generated/04_DATA_MODEL_CATALOGUE.md`.
- Do not use binary floating point for a regulated quantity.
- Do not fabricate a test run, scan result or qualification record.
- Do not start work in another work package.

FILES TO CREATE/MODIFY:
```text
infrastructure/src/            # domain services, command handlers, repositories
infrastructure/migrations/     # owned entities only
infrastructure/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-data-002.yaml
contracts/events/spec-data-002/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-data-002/
```

REQUIREMENTS TO IMPLEMENT (34):
| ID | Requirement | Required behaviour | Acceptance intent |
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

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| executeGxPTransaction() | Mutation Gateway/domain service | aggregate id/version; command payload; actor/context | MutationReceipt | GxPTransactionCommitted; STALE_VERSION/DB_TX_FAILED |
| applyOptimisticUpdate() | Repository | table/key; expected_version; changes | UpdatedVersion | STALE_VERSION |
| appendOutboxEvent() | Domain transaction | event envelope | OutboxRef | OUTBOX_DUPLICATE |
| createTimePartition() | Partition maintenance job | table; start/end; storage/index profile | PartitionRef | PARTITION_CREATE_FAILED |
| verifyPartitionCoverage() | Preflight/monitor | table; future horizon | CoverageReport | PARTITION_GAP_DETECTED |
| runDatabaseIntegrityCheck() | DBA automation | database/schema/table scope; check profile | IntegrityCheckReport | DB_INTEGRITY_FAILURE |
| getPrimaryConsistencyRead() | Regulated action service | entity/id; expected version | AuthoritativeRecord | PRIMARY_UNAVAILABLE |
| runReadReplicaQuery() | Reporting | report/query definition; max_staleness | ReportDataset | REPLICA_TOO_STALE |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (0 entities owned by this module):
_none declared in the source specifications_

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (0):
_none declared in the source specifications_

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `DatabaseIntegrityFailure` | SPEC-DATA-002 | event_id |
| `PartitionGapDetected` | SPEC-DATA-002 | event_id |
| `ReplicaLagExceeded` | SPEC-DATA-002 | event_id |
| `MigrationApplied` | SPEC-DATA-002 | event_id |
| `DeadlockDetected` | SPEC-DATA-002 | event_id |
| `ConnectionPoolExhausted` | SPEC-DATA-002 | event_id |

UI SURFACES:
- Database/Schema Inventory
- Partition Health
- Connection/Lock Dashboard
- Slow Query Dashboard
- Integrity Checks
- Migration History

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- two concurrent expected-version updates
- deadlock retry
- outbox atomic rollback
- missing future partition
- replica lag regulated action uses primary
- large-table migration lock test
- database checksum/index corruption drill
- connection pool saturation
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-11/Document_70_SPEC-DATA-002_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DATA-002/<test_case_id>/`.
- A failed case is evidence: never delete it, re-run over it, or edit the expected result to make it pass.
  Raise a defect, record the reference, re-execute as a new dated execution.

TRACEABILITY & STATUS (mandatory at the end of this prompt):
- Update `traceability/TRACEABILITY_MASTER.csv` for every requirement you touched: `build_stage`,
  `verification_state`, `test_case_ids`, `evidence_location`.
- Update `status/build-status.json`: set this module's `stage`, append to `stage_history`, set
  `requirements_state` per requirement, and set `test_pass` / `test_fail` / `test_blocked` from the
  actual recorded results.
- You may only set stages you can evidence, up to and including CODE_COMPLETE and the test states.
  `REVIEWED`, `OQ_EXECUTED`, `QUALIFIED` and `RELEASED` are set by humans, never by you.
- Run `python tooling/status/rollup.py` and include the printed summary in your completion report.

VALIDATION / TRACEABILITY:
- update `docs/generated/15_TEST_TRACEABILITY_MATRIX.csv` and `29_VALIDATION_TRACEABILITY_MASTER.csv`
- state IQ/OQ/PQ impact; HIGHER-PROCESS-RISK functions need retained objective evidence
- Part 11 impact where signatures are involved (Document 88)

ACCEPTANCE CRITERIA:
- every requirement above implemented, traced and tested
- all listed tests executed with real results
- no architecture guardrail violation
- contracts committed before implementation and compatible

SPEC_GAP RULE:
Do not guess regulated behaviour. Append unresolved decisions to `docs/generated/18_SPEC_GAPS.md`
with affected requirements, risk, options and blocking status, then continue only on unaffected work.

BEFORE COMPLETION:
Run lint, typecheck, unit, contract, integration and guardrail checks. Report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; **test cases executed with PASS/FAIL/BLOCKED counts and
the case ids of every failure**; validation impact; **traceability and status files updated (include the
rollup summary)**; unresolved SPEC_GAPs; known limitations.
