# Claude Code prompt — WP-00 / Document 100: Database Migration Standard

TASK:
Implement the Database Migration Standard module (SPEC-ENG-004) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_100_Database_Migration_Standard_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: MIG-FR-001..032 (32)
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

- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `tooling` and its tests
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
tooling/src/            # domain services, command handlers, repositories
tooling/migrations/     # owned entities only
tooling/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-eng-004.yaml
contracts/events/spec-eng-004/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-eng-004/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
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

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createMigrationPlan() | Developer/Claude Code | schema diff; data transform; owner; affected release | MigrationPlan | MigrationPlanCreated |
| analyzeMigrationRisk() | CI/DB tooling | migration SQL/ORM patch; representative schema stats | MigrationRiskReport | UnsafeMigrationDetected |
| executeMigrationDryRun() | CI/Staging | migration package; restored representative DB | MigrationDryRunResult | MigrationDryRunCompleted |
| runChunkedBackfill() | Migration worker | migration ID; query scope; chunk size; transform version | BackfillResult | MigrationBackfillProgressed |
| verifyMigrationReconciliation() | Migration/Validation | before metrics; after state; reconciliation rules | MigrationReconciliation | MigrationReconciliationVerified |
| markMigrationApplied() | Migration runner | migration ID; checksum; commit; result | AppliedMigration | MigrationApplied |
| detectMigrationDrift() | Startup/CI | expected migration manifest; DB applied list/checksums | MigrationDriftReport | MigrationDriftDetected |
| generateUpgradePath() | Release tooling | from version; to version; migration graph | UpgradePath | UpgradePathGenerated |

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

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- none declared

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
Fail closed on any compliance-critical dependency outage; no degraded-mode commit.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- drop regulated column blocked
- large NOT NULL migration expand-contract
- chunked backfill resume
- migration checksum drift
- rolling old/new app compatibility
- MariaDB projection rebuild
- failed concurrent index
- PITR readiness check
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-00/Document_100_SPEC-ENG-004_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-ENG-004/<test_case_id>/`.
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
