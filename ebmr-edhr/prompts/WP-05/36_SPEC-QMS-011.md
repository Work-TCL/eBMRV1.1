# Claude Code prompt — WP-05 / Document 36: Recall / Field Action Management

TASK:
Implement the Recall / Field Action Management module (SPEC-QMS-011) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_36_Recall_Field_Action_Management_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: FAR-FR-001..020 (20)
- Approved baselines: Document 106 (signature policy), 107 (SoD), 108 (retention), 109 (SLO/RPO),
  110 (precision/UOM), 111 (risk class), 112 (schemas/migrations), 113 (contracts), 114 (glossary)
- Phase-0 artefacts: `docs/generated/03_FUNCTION_CATALOGUE.csv`, `04_DATA_MODEL_CATALOGUE.md`,
  `05_DATABASE_OWNERSHIP_MATRIX.md`, `06_API_CATALOGUE.yaml`, `07_EVENT_CATALOGUE.yaml`,
  `14_ERROR_CODE_REGISTRY.md`, `28_INTENDED_USE_GXP_RISK_MATRIX.md`

RISK CLASS: **STANDARD-RISK** → hybrid testing with automated regression evidence

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
contracts/openapi/spec-qms-011.yaml
contracts/events/spec-qms-011/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-qms-011/
```

REQUIREMENTS TO IMPLEMENT (20):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| FAR-FR-001 | Assessment initiation | Create from complaint, deviation, CAPA, trend, regulatory request or management decision. | Trigger linked. |
| FAR-FR-002 | Action classification | Recall/correction/removal/field action/customer advisory/stock recovery or configured terminology. | Explicit. |
| FAR-FR-003 | Affected scope | Use Genealogy to identify products/lots/serials/packages/distribution references. | Accurate. |
| FAR-FR-004 | Constituent scope | DDCP action can target whole product or constituent/interface with final-product impact. | Combination aware. |
| FAR-FR-005 | Risk assessment | Link health/product risk assessment and rationale. | Evidence. |
| FAR-FR-006 | Reportability assessment | Authorized Regulatory determines applicable Part 806/drug/biologic/Part4 obligations/deadlines. | Human authority. |
| FAR-FR-007 | Distribution hold | Block undistributed inventory when required. | Containment. |
| FAR-FR-008 | Consignee snapshot | Resolve and freeze distribution/consignee scope from ERP/WMS/CRM. | Communication scope. |
| FAR-FR-009 | Communication package | Version/approve notification text/instructions/attachments. | Controlled. |
| FAR-FR-010 | Notification tracking | Recipient/date/channel/delivery/acknowledgment/follow-up. | Execution. |
| FAR-FR-011 | Return/correction plan | Return/inspect/correct/update/replace/destroy plan. | Disposition. |
| FAR-FR-012 | Unit reconciliation | Affected/contacted/returned/corrected/destroyed/unavailable/outstanding. | Effectiveness. |
| FAR-FR-013 | Effectiveness checks | Verify communication/action effectiveness under approved plan. | Control. |
| FAR-FR-014 | Submission evidence | Store regulatory report/submission IDs/dates/acknowledgments. | Evidence. |
| FAR-FR-015 | Corrections/removals record | Maintain applicable device correction/removal records even if reporting decision is no. | Part 806 support. |
| FAR-FR-016 | CAPA link | Underlying systemic action links CAPA. | Systemic. |
| FAR-FR-017 | Status updates | Track management/regulatory updates and milestones. | Governance. |
| FAR-FR-018 | Closure | Scope reconciliation, action, submissions, effectiveness and dependencies complete. | Complete. |
| FAR-FR-019 | Scope expansion | New affected product reopens/expands controlled version. | Dynamic. |
| FAR-FR-020 | Export | Decision/scope/communication/reconciliation/submission/closure package exportable. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (4 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `field_action` | 10 | PostgreSQL (GxP Core, authoritative) |
| `field_action_scope_item` | 3 | PostgreSQL (GxP Core, authoritative) |
| `field_action_communication` | 3 | PostgreSQL (GxP Core, authoritative) |
| `field_action_reconciliation` | 1 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (8):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /qms/v1/field-actions` | yes | — |
| `POST /qms/v1/field-actions/{id}/scope` | yes | — |
| `POST /qms/v1/field-actions/{id}/reportability` | yes | — |
| `POST /qms/v1/field-actions/{id}/approve` | yes | policy lookup (Doc 106) |
| `POST /qms/v1/field-actions/{id}/communications` | yes | — |
| `POST /qms/v1/field-actions/{id}/reconcile` | yes | — |
| `POST /qms/v1/field-actions/{id}/effectiveness` | yes | — |
| `POST /qms/v1/field-actions/{id}/close` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (9):
| Event type | Producer | Dedupe key |
|---|---|---|
| `FieldActionAssessmentOpened` | SPEC-QMS-011 | event_id |
| `FieldActionScopeFrozen` | SPEC-QMS-011 | event_id |
| `FieldActionApproved` | SPEC-QMS-011 | event_id |
| `FieldActionNotificationSent` | SPEC-QMS-011 | event_id |
| `FieldActionUnitReturned` | SPEC-QMS-011 | event_id |
| `FieldActionCorrectionCompleted` | SPEC-QMS-011 | event_id |
| `FieldActionEffectivenessCompleted` | SPEC-QMS-011 | event_id |
| `FieldActionClosed` | SPEC-QMS-011 | event_id |
| `FieldActionScopeExpanded` | SPEC-QMS-011 | event_id |

UI SURFACES:
- Field Action Dashboard
- Assessment/Risk
- Affected Product Scope
- Distribution/Consignees
- Reportability
- Communication Package
- Execution
- Returns/Corrections
- Reconciliation
- Effectiveness
- Closure

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- DB unavailable: no regulated transition.
- Signature/Policy unavailable: required action fails closed.
- Notification/integration failure: outbox retries; authoritative state remains.
- Stale version: reject.
- Scheduled due-date/metric jobs recover from persisted state.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- material-lot forward trace
- single serial complaint
- DDCP constituent issue
- distribution hold
- consignee snapshot
- return reconciliation
- device correction/removal record
- scope expansion
- CAPA dependency
- closure
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-05/Document_36_SPEC-QMS-011_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-QMS-011/<test_case_id>/`.
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
- state IQ/OQ/PQ impact; STANDARD-RISK functions need retained objective evidence
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
