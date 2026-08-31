# US eBMR / eDHR Regulated Manufacturing Platform
## Document 100 — Database Migration Standard — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-ENG-004  
**Parent Documents:** Documents 01–96  
**Primary Dependencies:** Documents 06, 69–76, 87, 94–99, 103  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This specification is itself a control source for Claude Code/Codex. Engineering agents shall not treat it as optional style advice when the requirement is marked mandatory.

For every engineering-control function defined below preserve:

- caller/trigger;
- input type, source and requiredness;
- preconditions;
- authorization/ownership where applicable;
- repository/database/artifact reads;
- repository/database/artifact writes;
- transaction/atomicity boundary;
- output/return type;
- events/evidence;
- stable error codes;
- CI enforcement mechanism;
- positive and negative tests.

If a requirement cannot be implemented because of a conflict with another numbered specification, create a `SPEC_GAP` and stop the conflicting change rather than silently choosing a new architecture.

# Engineering Non-Negotiables

- Never modify or fork Frappe/ERPNext core.
- GxP-authoritative mutations enter through the proprietary Mutation Gateway/domain APIs.
- Frappe/MariaDB projections are not authoritative GxP records.
- No generic CRUD over released/regulated records.
- No direct SQL repair of regulated records outside controlled repair/migration mechanisms.
- No bypass of authorization, SoD, qualification or Part 11 signature requirements.
- No deletion/rewriting of immutable audit/version/evidence history.
- No external side effect inside a database transaction unless a specification explicitly establishes a safe protocol.
- Transactional outbox and idempotency are mandatory where specified.
- Temporal orchestrates; it does not own regulatory truth.
- Redis/search/NATS projections or caches are not GxP truth.
- Regulated calculations use exact decimal/UOM/rounding rules.
- All public contracts, DB migrations and release artifacts are versioned and traceable to requirement IDs.
- Production deployment must match a validated release authorization.
- AI is advisory by default; autonomous regulated decisions are prohibited unless a future separately approved specification explicitly changes that rule.

# 1. Objective

Define safe schema and data evolution for PostgreSQL GxP databases and Frappe/MariaDB, including compatibility, backfills, locking, reconciliation, recovery and validation evidence.

# 2. Actors / Components

- Developer
- DBA
- Migration Runner
- Claude Code/Codex
- Release Engineer
- Validation
- SRE

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| MIG-FR-001 | Migration ownership | Only owning service/app migration package changes its authoritative schema. | Data ownership. |
| MIG-FR-002 | Version order | Migrations have deterministic unique ordered IDs and are immutable after production release. | Reproducibility. |
| MIG-FR-003 | Forward-first strategy | Production migrations designed forward-compatible; rollback usually app rollback/forward fix rather than destructive schema reversal. | Safety. |
| MIG-FR-004 | Expand-contract | Breaking schema evolution uses expand → dual compatibility/backfill → switch → contract after safe window. | Zero/low downtime. |
| MIG-FR-005 | No destructive history loss | Drop/truncate/delete of regulated/history data requires retention/migration approval and archival evidence. | Data integrity. |
| MIG-FR-006 | Backup precondition | Risk-relevant migration checks current backup/PITR and rollback/recovery readiness. | Recoverability. |
| MIG-FR-007 | Representative test | Migration tested against representative volume/cardinality/schema state. | Production realism. |
| MIG-FR-008 | Idempotency | Migration runner can detect applied state; rerun behavior explicit and safe. | Operational reliability. |
| MIG-FR-009 | Transactional DDL | Use transaction where supported/safe; nontransactional steps explicitly staged/recoverable. | Atomicity. |
| MIG-FR-010 | Lock analysis | Estimate table locks/rewrite duration/IO/WAL impact for large table changes. | Availability. |
| MIG-FR-011 | Online index | Use concurrent/online patterns when available and justified; failures leave recoverable state. | Availability. |
| MIG-FR-012 | Backfill | Large data backfills chunked/checkpointed/rate-limited with deterministic transform version. | Scale. |
| MIG-FR-013 | Backfill audit | Migration-generated regulated changes marked as migration provenance, not user actions. | Traceability. |
| MIG-FR-014 | Checksums/reconciliation | Data migration/backfill records counts/hashes/control totals before/after where material. | Accuracy. |
| MIG-FR-015 | Constraints | New NOT NULL/FK/check constraints introduced safely after data compatibility/backfill. | Integrity. |
| MIG-FR-016 | Default changes | Avoid table-rewrite defaults or hidden semantics; assess existing row behavior explicitly. | Safety. |
| MIG-FR-017 | Enum/state evolution | State/enum changes preserve historical readability and old worker compatibility during rollout. | Compatibility. |
| MIG-FR-018 | App compatibility | Document minimum/maximum app versions compatible with schema during rolling deploy. | Release safety. |
| MIG-FR-019 | MariaDB/Frappe migrations | Frappe patches/migrations follow same version/evidence discipline; projection tables may rebuild rather than complex migrate where safer. | Framework. |
| MIG-FR-020 | PostgreSQL migrations | GxP migrations executed by dedicated migration role; runtime service role has no DDL. | Security. |
| MIG-FR-021 | Object metadata | Object/evidence metadata schema migrations cannot orphan stored evidence. | Evidence. |
| MIG-FR-022 | Event schema coordination | Migration requiring event/API contract change coordinates deployment order and compatibility. | Distributed systems. |
| MIG-FR-023 | Temporal compatibility | Workflow code/schema changes account for in-flight histories/activity payloads. | Orchestration. |
| MIG-FR-024 | Migration dry run | Major migration supports staging/restore-copy rehearsal with timing/evidence. | Confidence. |
| MIG-FR-025 | Failure recovery | Runbook states partial-step detection, resume/repair/restore criteria. | Recovery. |
| MIG-FR-026 | No manual prod SQL | Manual DDL/DML in production prohibited except controlled emergency repair captured into subsequent migration/change record. | Control. |
| MIG-FR-027 | Reconciliation gate | Service not healthy after migration until mandatory schema/data checks pass. | Fail closed. |
| MIG-FR-028 | Migration evidence | Store source commit, migration IDs, start/end, runner, environment, result, counts/checks, failures. | Validation. |
| MIG-FR-029 | Retention-aware contract | Dropped old columns/tables only after retention/consumer/deployment compatibility analysis. | Governance. |
| MIG-FR-030 | Customer upgrade path | Every supported version has documented upgrade path or explicit intermediate hop. | Commercial support. |
| MIG-FR-031 | Downgrade semantics | Downgrade support explicitly stated; never imply app image rollback makes DB downgrade safe. | Honesty. |
| MIG-FR-032 | Validation impact | GxP schema/data migrations link change impact/revalidation requirements. | Validated state. |

# 4. Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB or repo effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createMigrationPlan() | Developer/Claude Code | schema diff; data transform; owner; affected release | Ownership registry current | Produces ordered steps, compatibility, lock/backfill, recovery and validation plan | MigrationPlan | MigrationPlanCreated |
| analyzeMigrationRisk() | CI/DB tooling | migration SQL/ORM patch; representative schema stats | Staging stats available | Detects destructive ops, locks, table rewrites, long transactions, unbounded backfills | MigrationRiskReport | UnsafeMigrationDetected |
| executeMigrationDryRun() | CI/Staging | migration package; restored representative DB | Backup copy ready | Runs migration, timing, locks, reconciliation and app compatibility tests | MigrationDryRunResult | MigrationDryRunCompleted |
| runChunkedBackfill() | Migration worker | migration ID; query scope; chunk size; transform version | Schema expanded; checkpoint table ready | Processes deterministic chunks with checkpoint/metrics | BackfillResult | MigrationBackfillProgressed |
| verifyMigrationReconciliation() | Migration/Validation | before metrics; after state; reconciliation rules | Migration finished | Compares counts/hashes/totals/orphans/constraints | MigrationReconciliation | MigrationReconciliationVerified |
| markMigrationApplied() | Migration runner | migration ID; checksum; commit; result | Exact migration succeeded/reconciled | Records immutable applied migration metadata | AppliedMigration | MigrationApplied |
| detectMigrationDrift() | Startup/CI | expected migration manifest; DB applied list/checksums | DB reachable | Blocks unknown/modified/missing migration state | MigrationDriftReport | MigrationDriftDetected |
| generateUpgradePath() | Release tooling | from version; to version; migration graph | Supported versions known | Returns required sequential migration/app compatibility steps | UpgradePath | UpgradePathGenerated |

# 5. Migration File Contract

Each migration defines:
```yaml
id:
owner_service:
source_requirement_ids: []
schema_before:
schema_after:
forward_steps: []
data_backfill:
compatibility_window:
lock_risk:
backup_requirement:
reconciliation:
failure_recovery:
validation_tests:
```
The production-applied file/checksum is immutable.

# 6. Expand / Migrate / Contract Pattern

Example:
1. add nullable new column/table;
2. deploy code writing old+new or new with compatibility;
3. chunked backfill;
4. verify counts/values;
5. deploy readers to new representation;
6. observe compatibility window;
7. remove old representation only after support/retention approval.

# 7. Migration Health Gate

Service readiness after schema migration may require:
- expected migration manifest;
- constraints/indexes present;
- no failed backfill;
- no orphan evidence refs;
- reconciliation PASS;
- compatible app version;
- migration deviation resolved/accepted.

# 8. Mandatory Test / Enforcement Catalogue

- drop regulated column blocked
- large NOT NULL migration expand-contract
- chunked backfill resume
- migration checksum drift
- rolling old/new app compatibility
- MariaDB projection rebuild
- failed concurrent index
- PITR readiness check

# 9. Acceptance Criteria

A database upgrade can be rehearsed, measured, reconciled and recovered without destructive loss of regulated history or assuming application rollback reverses schema state.

# 10. Claude Code / Codex Prohibitions

- Never edit an already released migration file.
- Never run unbounded one-shot data backfill on production critical table.
- Never use destructive rollback as default recovery.
- Never execute undocumented manual production DDL/DML.
