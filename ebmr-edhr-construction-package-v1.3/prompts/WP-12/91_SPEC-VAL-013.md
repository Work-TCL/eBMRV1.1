# Claude Code prompt — WP-12 / Document 91: Backup, Restore, PITR & Disaster Recovery Qualification

TASK:
Implement the Backup, Restore, PITR & Disaster Recovery Qualification module (SPEC-VAL-013) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_91_Backup_Restore_PITR_DR_Qualification_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: DRV-FR-001..022 (22)
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
- `validation` and its tests
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
validation/src/            # domain services, command handlers, repositories
validation/migrations/     # owned entities only
validation/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-val-013.yaml
contracts/events/spec-val-013/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-val-013/
```

REQUIREMENTS TO IMPLEMENT (22):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| DRV-FR-001 | Scope | Map all persistent/critical components to RPO/RTO profile. | Complete. |
| DRV-FR-002 | Backup evidence | Verify backup/manifest/WAL/object/config evidence. | Protection. |
| DRV-FR-003 | Actual restore | Restore real data into isolated environment. | Objective recovery. |
| DRV-FR-004 | PITR | Recover PostgreSQL to selected timestamp/LSN. | PITR. |
| DRV-FR-005 | RPO | Measure latest recovered data vs expected source marker. | Objective. |
| DRV-FR-006 | RTO | Measure recovery declaration/start to validated service-ready. | Objective. |
| DRV-FR-007 | Audit continuity | Verify audit/version/outbox relationships. | GxP. |
| DRV-FR-008 | Evidence | Verify metadata→object hash/availability. | Evidence. |
| DRV-FR-009 | MariaDB | Restore/rebuild/reconcile Frappe projections. | UI recovery. |
| DRV-FR-010 | NATS | Recover/config and verify outbox catch-up. | Messaging. |
| DRV-FR-011 | Temporal | Resume orchestration without false domain state. | Orchestration. |
| DRV-FR-012 | Secrets/keys | Recovered data remains decryptable; missing/rotated key behavior tested. | Crypto. |
| DRV-FR-013 | Failover | Standby promotion/split-brain prevention where HA. | Availability. |
| DRV-FR-014 | Failback | Controlled rejoin/failback where applicable. | Operations. |
| DRV-FR-015 | Regional/site DR | Secondary region/site activation where required. | Enterprise. |
| DRV-FR-016 | Network/DNS/cert | Recovery endpoints/routing/trust validated. | Accessibility. |
| DRV-FR-017 | Security | Recovery preserves auth/network/least privilege. | Secure recovery. |
| DRV-FR-018 | GxP smoke | Representative create/read/sign/audit/evidence operation after recovery. | Business verification. |
| DRV-FR-019 | Data-loss detection | Missing interval detection/assessment works if RPO exceeded. | Transparency. |
| DRV-FR-020 | Runbook | Current operators can execute runbook; deviations update procedure. | Human readiness. |
| DRV-FR-021 | Cadence | Restore/DR qualification repeated per risk/profile. | Ongoing. |
| DRV-FR-022 | Approval | Qualification approved with achieved RPO/RTO. | Gate. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createDRQualificationScenario() | SRE/Validation | failure scenario; scope; target RPO/RTO; restore point | DRScenario | DRQualificationScenarioCreated |
| executeRestoreQualification() | DR operator | scenario; backup set; isolated target | DRExecution | DRRestoreExecuted |
| measureRecoveryObjectives() | Validation | execution; source marker; ready time | RecoveryObjectiveResult | RecoveryObjectivesMeasured |
| runRecoveredGxPSmoke() | Validation | recovered environment; smoke profile | RecoverySmokeResult | RecoveredGxPSmokeCompleted |
| approveDRQualification() | QA/Validation | results/deviations | DRQualification | DRQualificationApproved |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `dr_qualification_scenario` | 6 | PostgreSQL (GxP Core, authoritative) |
| `dr_qualification_execution` | 5 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (4):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /validation/v1/dr/scenarios` | yes | — |
| `POST /validation/v1/dr/executions` | yes | — |
| `POST /validation/v1/dr/{id}/measure` | yes | — |
| `POST /validation/v1/dr/{id}/approve` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (4):
| Event type | Producer | Dedupe key |
|---|---|---|
| `DRRestoreExecuted` | SPEC-VAL-013 | event_id |
| `RecoveryObjectivesMeasured` | SPEC-VAL-013 | event_id |
| `RecoveredGxPSmokeCompleted` | SPEC-VAL-013 | event_id |
| `DRQualificationApproved` | SPEC-VAL-013 | event_id |

UI SURFACES:
- DR Scenarios
- Restore Timeline
- RPO/RTO
- Integrity/Smoke
- DR Qualification

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
**Specification ID:** SPEC-VAL-013  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 65, 72–77, 82–90  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- PITR
- standby failover
- object mismatch
- outbox recovery
- Temporal resume
- MariaDB rebuild
- key unavailable
- RPO exceeded
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-12/Document_91_SPEC-VAL-013_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-VAL-013/<test_case_id>/`.
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
