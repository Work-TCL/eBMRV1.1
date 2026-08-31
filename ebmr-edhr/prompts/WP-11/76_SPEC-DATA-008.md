# Claude Code prompt — WP-11 / Document 76: Backup, Restore, Point-in-Time Recovery & Disaster Recovery

TASK:
Implement the Backup, Restore, Point-in-Time Recovery & Disaster Recovery module (SPEC-DATA-008) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_76_Backup_Restore_PITR_Disaster_Recovery_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: DR-FR-001..032 (32)
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
contracts/openapi/spec-data-008.yaml
contracts/events/spec-data-008/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-data-008/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| DR-FR-001 | Recovery objectives | Define RPO/RTO per component and business capability, approved by customer/product profile. | Measurable recovery. |
| DR-FR-002 | Tier classification | Classify GxP PostgreSQL, MariaDB, object evidence, NATS, Temporal, search/cache, observability, config/secrets by criticality. | Prioritized. |
| DR-FR-003 | PostgreSQL backup | Use base/full/incremental/managed backups plus WAL/PITR according to deployment profile. | Recoverability. |
| DR-FR-004 | WAL archive | WAL archiving protected, monitored and retained to meet PITR/RPO window. | PITR. |
| DR-FR-005 | Backup manifest | Backup includes manifest/checksum/metadata and is immutable/protected from production compromise. | Integrity. |
| DR-FR-006 | MariaDB backup | Frappe/MariaDB backups scheduled and encrypted; projection freshness expected after restore. | Operational recovery. |
| DR-FR-007 | Object storage protection | Object versioning/immutability/replication plus independent backup/export strategy as deployment requires. | Evidence recovery. |
| DR-FR-008 | NATS backup | Stream configuration/state backup/recovery documented, but domain recovery must not depend solely on NATS history. | Messaging recovery. |
| DR-FR-009 | Temporal backup | Temporal persistence backup/managed DR configured for orchestration; GxP records recover independently. | Orchestration recovery. |
| DR-FR-010 | Secrets/KMS backup | Key/secret recovery strategy prevents encrypted backups becoming unrecoverable. | Crypto recovery. |
| DR-FR-011 | Infrastructure config | IaC, manifests, config versions, certificates/trust metadata and deployment parameters backed by source/control plane. | Rebuildability. |
| DR-FR-012 | Offsite/isolation | Backups logically/physically isolated from normal production credentials/ransomware path. | Resilience. |
| DR-FR-013 | Encryption | Backups encrypted in transit/at rest; key access separate. | Security. |
| DR-FR-014 | Retention generations | Daily/weekly/monthly or equivalent retention derived from RPO/history/regulatory needs, not one hardcoded schedule. | Flexible. |
| DR-FR-015 | Backup monitoring | Backup start/completion/size/age/checksum/WAL gap/replication failures alert. | Reliability. |
| DR-FR-016 | Restore testing | Automated regular restore test into isolated environment; application-level integrity checks mandatory. | Evidence. |
| DR-FR-017 | PITR test | Demonstrate recovery to selected timestamp/LSN within objective and validate audit/event continuity. | Point-in-time confidence. |
| DR-FR-018 | Application consistency | Restore runbook defines recovery order/checkpoints across PostgreSQL/object/MariaDB/Temporal/NATS. | Cross-system consistency. |
| DR-FR-019 | Object reconciliation | After restore verify evidence metadata→object references/hashes. | Evidence integrity. |
| DR-FR-020 | Projection rebuild | Frappe/search/cache/read models can rebuild from recovered authoritative data. | Recovery simplification. |
| DR-FR-021 | DR site/region | Enterprise profile can use secondary region/site with documented replication/failover mode. | Availability. |
| DR-FR-022 | Failover authority | Primary DB promotion/failover uses controlled operator/automation with split-brain prevention. | Data integrity. |
| DR-FR-023 | Failback | Failback/rejoin procedure tests data divergence and does not simply overwrite new primary. | Recovery. |
| DR-FR-024 | Disaster declaration | DR activation has incident/change record, owner, time and affected services. | Governance. |
| DR-FR-025 | Validation before reopen | Recovered environment passes defined smoke/integrity/security/GxP checks before accepting regulated work. | Safe restart. |
| DR-FR-026 | Data-loss assessment | If recovery loses data beyond expected RPO, system identifies missing range/events and creates incident/GxP assessment. | Transparency. |
| DR-FR-027 | Offline customer | On-prem customer backup destination/runbook supports customer-operated storage without weakening integrity evidence. | Deployment. |
| DR-FR-028 | Backup deletion | Backup expiry/destruction follows controlled lifecycle and legal/security policies. | Governance. |
| DR-FR-029 | Restore access | Only privileged recovery role may perform restore; all operations audited. | Security. |
| DR-FR-030 | DR evidence | Each test records backup set, restore target, timings, checks, RPO/RTO achieved, failures and remediation. | Validation. |
| DR-FR-031 | Capacity | Backup target has growth forecast and alerts before exhaustion. | Operations. |
| DR-FR-032 | No replica-as-backup | Replication/standby alone is not considered backup. | Correct resilience. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createRecoveryObjectiveProfile() | Platform/Customer Admin | component/capability; RPO; RTO; durability/region profile | RecoveryObjectiveProfile | RecoveryObjectiveConfigured |
| verifyBackupFreshness() | Scheduled monitor | component; objective profile; backup/WAL metadata | BackupHealth | BackupRPOAtRisk |
| executePostgresRestoreTest() | DR automation | backup set; PITR target; isolated target profile | RestoreTestReport | PostgresRestoreTestCompleted |
| reconcileEvidenceAfterRestore() | DR validation | restored GxP metadata; object provider/snapshot | EvidenceRecoveryReport | EvidenceRestoreMismatch |
| rebuildDerivedStoresAfterRestore() | Recovery orchestration | projection/search/cache scopes; authoritative cutoff | DerivedRecoveryResult | DerivedStoresRebuilt |
| promoteStandby() | DR operator/automation | cluster; target replica; incident/change ID | FailoverReceipt | DatabaseFailoverCompleted |
| validateRecoveredPlatform() | DR validation gate | recovery environment; component reports; smoke/test profile | RecoveryValidationDecision | PlatformRecoveryValidated/RECOVERY_VALIDATION_FAILED |
| recordDataLossAssessment() | Security/QA/DR | restore point; expected latest; missing interval/events | DataLossAssessment | RecoveryDataLossDetected |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `recovery_objective_profile` | 4 | PostgreSQL (GxP Core, authoritative) |
| `backup_inventory` | 8 | PostgreSQL (GxP Core, authoritative) |
| `restore_test` | 5 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (3):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /platform/v1/recovery-objectives` | yes | — |
| `GET /platform/v1/backups/health` | no | — |
| `POST /platform/v1/restore-tests` | yes | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `BackupRPOAtRisk` | SPEC-DATA-008 | event_id |
| `RestoreTestFailed` | SPEC-DATA-008 | event_id |
| `DatabaseFailoverCompleted` | SPEC-DATA-008 | event_id |
| `EvidenceRestoreMismatch` | SPEC-DATA-008 | event_id |
| `PlatformRecoveryValidated` | SPEC-DATA-008 | event_id |
| `RecoveryDataLossDetected` | SPEC-DATA-008 | event_id |

UI SURFACES:
- Backup Health
- WAL/PITR Coverage
- Restore Tests
- DR Objectives
- Failover/Incident
- Recovery Validation

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
**Specification ID:** SPEC-DATA-008  
**Parent Documents:** Documents 01–68  
**Primary Dependencies:** Documents 05–06, 65, 69–75; Security Incident Response  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- backup set
- target
- PITR target
- elapsed time
- integrity checks
- RPO/RTO achieved
- evidence/report
- backup success flag but corrupt restore
- WAL gap
- PITR to 10 minutes before incident
- object evidence missing
- MariaDB older than GxP then projection rebuild
- standby promotion
- split brain prevention
- lost encryption key drill
- RPO exceeded
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-11/Document_76_SPEC-DATA-008_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DATA-008/<test_case_id>/`.
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
