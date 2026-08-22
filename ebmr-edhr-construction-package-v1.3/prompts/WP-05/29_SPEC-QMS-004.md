# Claude Code prompt — WP-05 / Document 29: Change Control

TASK:
Implement the Change Control module (SPEC-QMS-004) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_29_Change_Control_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: CHG-FR-001..024 (24)
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
- `services/gxp-api/src/modules/qms` and its tests
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
services/gxp-api/src/modules/qms/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/qms/migrations/     # owned entities only
services/gxp-api/src/modules/qms/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-qms-004.yaml
contracts/events/spec-qms-004/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-qms-004/
```

REQUIREMENTS TO IMPLEMENT (24):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| CHG-FR-001 | Change request | Create change for product/process/recipe/spec/material/source/equipment/facility/software/document/method/label/supplier. | Broad control. |
| CHG-FR-002 | Classification | Temporary/permanent and risk class using approved methodology. | Routing. |
| CHG-FR-003 | Current/proposed state | Document current state, proposed state and reason/business need. | Clear intent. |
| CHG-FR-004 | Affected objects | Link exact object versions potentially affected. | Impact graph. |
| CHG-FR-005 | Regulatory impact | Qualified Regulatory/Quality assesses filing/notification/approval/reportability implications. | Human authority. |
| CHG-FR-006 | Quality impact | Assess product quality/safety/performance. | Quality. |
| CHG-FR-007 | Validation impact | Assess process/equipment/software validation/requalification. | Validated state. |
| CHG-FR-008 | Risk assessment | Create/link risk assessment when required. | Risk based. |
| CHG-FR-009 | Training impact | Identify documents/roles/users needing training before effective date. | Readiness. |
| CHG-FR-010 | Open-batch/inventory impact | Assess open batches, released stock, materials, labels and transition plan. | Cutover safe. |
| CHG-FR-011 | Data/migration impact | Assess schema/master-data/migration/backfill/data-integrity requirements. | System safe. |
| CHG-FR-012 | Implementation plan | Tasks, owners, dependencies, evidence, target/effective date, rollback. | Executable. |
| CHG-FR-013 | Pre-approval | Quality/technical/regulatory approvals before implementation except controlled emergency path. | Controlled. |
| CHG-FR-014 | Emergency change | Time-bounded emergency path with reason/risk and mandatory retrospective review. | No loophole. |
| CHG-FR-015 | Execution evidence | Tasks link PR/build/release/equipment/document evidence. | Trace. |
| CHG-FR-016 | Verification/validation | Verify implemented state and required test/qualification before use. | Qualified. |
| CHG-FR-017 | Effective date | New state usable only after prerequisites/training/approval complete. | Controlled activation. |
| CHG-FR-018 | Post-implementation review | Verify intended result/no adverse effect when required. | Effectiveness. |
| CHG-FR-019 | Rollback | Controlled action preserving both versions/evidence. | History. |
| CHG-FR-020 | Closure | Close after implementation, verification, training/validation and follow-up. | Complete. |
| CHG-FR-021 | Cancellation | Retain reason/approval/history. | Integrity. |
| CHG-FR-022 | Software traceability | Software changes link requirement, code PR, tests, SBOM, validation impact, deployment. | CSA/CSV. |
| CHG-FR-023 | Master linkage | New product/recipe/spec/doc version can reference governing Change Control. | Trace. |
| CHG-FR-024 | Export | Before/after, impacts, approvals and evidence exportable. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `change_control` | 14 | PostgreSQL (GxP Core, authoritative) |
| `change_affected_object` | 3 | PostgreSQL (GxP Core, authoritative) |
| `change_task` | 4 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (8):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /qms/v1/changes` | yes | — |
| `POST /qms/v1/changes/{id}/impact` | yes | — |
| `POST /qms/v1/changes/{id}/approve` | yes | policy lookup (Doc 106) |
| `POST /qms/v1/changes/{id}/tasks` | yes | — |
| `POST /qms/v1/changes/{id}/implement` | yes | — |
| `POST /qms/v1/changes/{id}/verify` | yes | policy lookup (Doc 106) |
| `POST /qms/v1/changes/{id}/make-effective` | yes | — |
| `POST /qms/v1/changes/{id}/close` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (8):
| Event type | Producer | Dedupe key |
|---|---|---|
| `ChangeRequested` | SPEC-QMS-004 | event_id |
| `ChangeImpactAssessed` | SPEC-QMS-004 | event_id |
| `ChangeApproved` | SPEC-QMS-004 | event_id |
| `ChangeImplementationStarted` | SPEC-QMS-004 | event_id |
| `ChangeValidationCompleted` | SPEC-QMS-004 | event_id |
| `ChangeMadeEffective` | SPEC-QMS-004 | event_id |
| `ChangeClosed` | SPEC-QMS-004 | event_id |
| `EmergencyChangeOpened` | SPEC-QMS-004 | event_id |

UI SURFACES:
- Change Dashboard
- Request
- Affected Objects
- Impact Assessments
- Risk
- Implementation Plan
- Validation/Training
- Approvals
- Execution Evidence
- Post-Implementation Review
- Closure

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- DB unavailable: no regulated transition succeeds.
- Policy/signature unavailable: required action fails closed.
- Notification failure: authoritative state may commit; outbox retries notifications.
- Stale version: reject and refresh.
- Worker restart: due-date/escalation processing resumes from persisted state.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- recipe change
- software schema change
- supplier change
- label change
- open batch impact
- training prerequisite
- emergency change
- rollback
- cancel
- post-implementation failure
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-05/Document_29_SPEC-QMS-004_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-QMS-004/<test_case_id>/`.
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
