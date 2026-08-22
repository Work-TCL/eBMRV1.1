# Claude Code prompt — WP-05 / Document 26: Deviation & Investigation Management

TASK:
Implement the Deviation & Investigation Management module (SPEC-QMS-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_26_Deviation_Investigation_Management_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: DEV-FR-001..024 (24)
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
contracts/openapi/spec-qms-001.yaml
contracts/events/spec-qms-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-qms-001/
```

REQUIREMENTS TO IMPLEMENT (24):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| DEV-FR-001 | Deviation initiation | Create planned/unplanned deviation from batch, QC, material, equipment, environment, supplier, document or system source. | Every deviation attributable. |
| DEV-FR-002 | Automatic source | Rules/Batch/QC/Edge can create deviation candidate with exact source event/version. | No retyping required. |
| DEV-FR-003 | Triage | Classify planned/unplanned, severity, product impact and investigation priority using released methodology. | Consistent routing. |
| DEV-FR-004 | Immediate correction | Record immediate correction separately from root-cause/CAPA. | Containment not confused with systemic action. |
| DEV-FR-005 | Containment | Place batch/material/equipment/area on hold where required. | Risk bounded. |
| DEV-FR-006 | Investigator | Assign qualified investigator, owner and due date; reassignment audited. | Ownership clear. |
| DEV-FR-007 | Investigation plan | Define records, interviews, batches/products and technical evidence to review. | Structured investigation. |
| DEV-FR-008 | Cross-batch investigation | Extend investigation to associated batches/products when relevant. | Supports §211.192. |
| DEV-FR-009 | Evidence graph | Link batch, audit, QC, equipment, materials, environment, supplier and files. | Complete evidence. |
| DEV-FR-010 | Root cause | Support configurable root-cause methods and 'no assignable cause' when justified. | No forced fake cause. |
| DEV-FR-011 | Impact assessment | Assess quality, patient/user, released/distributed product, validation, data integrity and regulatory impact. | Complete impact. |
| DEV-FR-012 | Disposition | Continue/hold/reject/rework/reprocess/additional test/destroy/field-action assessment according to policy. | Controlled outcome. |
| DEV-FR-013 | CAPA need | Record CAPA required/not required with rationale. | Systemic action decision. |
| DEV-FR-014 | Change need | Link Change Control for permanent process/spec/system/document changes. | Controlled change. |
| DEV-FR-015 | Training need | Create retraining/qualification actions where appropriate. | Training integrated. |
| DEV-FR-016 | Planned deviation | Pre-approved, bounded by scope/date/batches; cannot become permanent alternative process. | Temporary exception. |
| DEV-FR-017 | Extension | Due-date extension requires reason, risk review and approval; old due date retained. | No silent aging. |
| DEV-FR-018 | Closure | Require investigation, impact, disposition and mandatory linked actions before QA closure. | No premature closure. |
| DEV-FR-019 | QA signature | Final conclusion/disposition/closure signed according to policy. | Independent Quality authority. |
| DEV-FR-020 | Reopen | New evidence reopens through controlled action preserving prior closure. | History. |
| DEV-FR-021 | Recurrence | Find similar prior deviations by code/product/process/equipment/root cause. | Trend. |
| DEV-FR-022 | Release integration | Open/critical deviations create review/release blockers based on rule. | No release bypass. |
| DEV-FR-023 | Escalation | Critical/overdue deviation notifications/escalation. | Timely handling. |
| DEV-FR-024 | Export | Written investigation with conclusions/follow-up and evidence exportable. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `deviation_record` | 19 | PostgreSQL (GxP Core, authoritative) |
| `deviation_impact_link` | 3 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (9):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /qms/v1/deviations` | yes | — |
| `POST /qms/v1/deviations/{id}/triage` | yes | — |
| `POST /qms/v1/deviations/{id}/contain` | yes | — |
| `POST /qms/v1/deviations/{id}/investigation` | yes | — |
| `POST /qms/v1/deviations/{id}/impact` | yes | — |
| `POST /qms/v1/deviations/{id}/disposition` | yes | policy lookup (Doc 106) |
| `POST /qms/v1/deviations/{id}/extend` | yes | — |
| `POST /qms/v1/deviations/{id}/close` | yes | policy lookup (Doc 106) |
| `POST /qms/v1/deviations/{id}/reopen` | yes | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (8):
| Event type | Producer | Dedupe key |
|---|---|---|
| `DeviationOpened` | SPEC-QMS-001 | event_id |
| `DeviationContained` | SPEC-QMS-001 | event_id |
| `DeviationInvestigationStarted` | SPEC-QMS-001 | event_id |
| `DeviationImpactAssessed` | SPEC-QMS-001 | event_id |
| `DeviationCAPARequired` | SPEC-QMS-001 | event_id |
| `DeviationDispositionApproved` | SPEC-QMS-001 | event_id |
| `DeviationClosed` | SPEC-QMS-001 | event_id |
| `DeviationReopened` | SPEC-QMS-001 | event_id |

UI SURFACES:
- Deviation Dashboard
- Initiation/Triage
- Containment
- Investigation & Evidence
- Root Cause
- Impact Assessment
- Disposition
- Linked CAPA/Change
- QA Closure
- Audit/History

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
- automatic batch deviation
- planned deviation expiry
- cross-batch investigation
- no assignable cause
- CAPA required
- change required
- extension
- close with missing impact denied
- reopen
- release blocker
- export
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-05/Document_26_SPEC-QMS-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-QMS-001/<test_case_id>/`.
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
