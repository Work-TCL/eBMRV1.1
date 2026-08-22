# Claude Code prompt — WP-05 / Document 27: CAPA Management

TASK:
Implement the CAPA Management module (SPEC-QMS-002) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_27_CAPA_Management_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: CAPA-FR-001..022 (22)
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
contracts/openapi/spec-qms-002.yaml
contracts/events/spec-qms-002/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-qms-002/
```

REQUIREMENTS TO IMPLEMENT (22):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| CAPA-FR-001 | CAPA initiation | Create from deviation/OOS/OOT/NCR/complaint/audit/supplier/risk/trend/security/validation source. | Source explicit. |
| CAPA-FR-002 | Problem statement | Define verified problem and scope separately from solution. | Correct framing. |
| CAPA-FR-003 | Priority | Assign risk/priority and target date. | Risk based. |
| CAPA-FR-004 | Root-cause link | Reference investigation/root cause or proactive prevention rationale. | Evidence based. |
| CAPA-FR-005 | Corrective action | Define action addressing cause of detected issue. | Corrective. |
| CAPA-FR-006 | Preventive/systemic action | Support broader preventive/systemic action without forcing artificial categories. | Systemic improvement. |
| CAPA-FR-007 | Action owner/evidence | Every action has owner, due date, deliverable/evidence and state. | Accountability. |
| CAPA-FR-008 | Dependencies | Actions link Change, Training, Validation, Supplier, Software Release, Equipment etc. | Cross-module. |
| CAPA-FR-009 | Implementation verification | Reviewer verifies evidence and actual implementation. | Not checkbox-only. |
| CAPA-FR-010 | Effectiveness criteria | Define measurable criterion, data source, observation period and due date before check. | Objective. |
| CAPA-FR-011 | Effectiveness result | Pass/fail/inconclusive with evidence and reviewer. | True effectiveness. |
| CAPA-FR-012 | Failed effectiveness | Reopen CAPA/new investigation/action based on policy. | No cosmetic close. |
| CAPA-FR-013 | Extension | Reason/risk/approval; original due date retained. | Aging controlled. |
| CAPA-FR-014 | Escalation | Overdue/high-risk/repeat CAPA escalates. | Management visibility. |
| CAPA-FR-015 | Closure | All mandatory actions and effectiveness complete before QA closure. | Complete. |
| CAPA-FR-016 | Cancellation | Duplicate/not-required cancellation with Quality rationale. | History. |
| CAPA-FR-017 | Reopen | Recurrence/new evidence can reopen. | History. |
| CAPA-FR-018 | Recurrence analysis | Link new quality events to prior CAPA to assess recurrence. | Effectiveness signal. |
| CAPA-FR-019 | Multi-site scope | CAPA scope can be site/product/process/enterprise. | Scalable. |
| CAPA-FR-020 | Metrics | Aging, overdue, effectiveness failures, recurrence. | QMS dashboard. |
| CAPA-FR-021 | Signatures | Plan approval, extension, effectiveness and closure signed per policy. | Attributable. |
| CAPA-FR-022 | Export | Complete action/evidence/effectiveness history exportable. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `capa_record` | 11 | PostgreSQL (GxP Core, authoritative) |
| `capa_action` | 6 | PostgreSQL (GxP Core, authoritative) |
| `capa_effectiveness_check` | 5 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (8):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /qms/v1/capas` | yes | — |
| `POST /qms/v1/capas/{id}/plan` | yes | — |
| `POST /qms/v1/capas/{id}/actions` | yes | — |
| `POST /qms/v1/actions/{id}/complete` | yes | — |
| `POST /qms/v1/capas/{id}/effectiveness` | yes | — |
| `POST /qms/v1/capas/{id}/extend` | yes | — |
| `POST /qms/v1/capas/{id}/close` | yes | policy lookup (Doc 106) |
| `POST /qms/v1/capas/{id}/reopen` | yes | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (8):
| Event type | Producer | Dedupe key |
|---|---|---|
| `CAPAOpened` | SPEC-QMS-002 | event_id |
| `CAPAPlanApproved` | SPEC-QMS-002 | event_id |
| `CAPAActionAssigned` | SPEC-QMS-002 | event_id |
| `CAPAActionCompleted` | SPEC-QMS-002 | event_id |
| `CAPAEffectivenessStarted` | SPEC-QMS-002 | event_id |
| `CAPAEffectivenessFailed` | SPEC-QMS-002 | event_id |
| `CAPAClosed` | SPEC-QMS-002 | event_id |
| `CAPAReopened` | SPEC-QMS-002 | event_id |

UI SURFACES:
- CAPA Dashboard
- Problem/Scope
- Root Cause
- Action Plan
- Dependencies
- Implementation Evidence
- Effectiveness Plan
- Effectiveness Review
- QA Closure
- Audit

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
- CAPA from deviation
- multi-action dependency
- action without evidence denied
- change dependency
- failed effectiveness
- extension
- repeat deviation after CAPA
- cancel
- reopen
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-05/Document_27_SPEC-QMS-002_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-QMS-002/<test_case_id>/`.
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
