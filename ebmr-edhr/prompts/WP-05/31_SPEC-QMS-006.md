# Claude Code prompt — WP-05 / Document 31: Training & Personnel Qualification

TASK:
Implement the Training & Personnel Qualification module (SPEC-QMS-006) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_31_Training_Personnel_Qualification_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: TRN-FR-001..024 (24)
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
contracts/openapi/spec-qms-006.yaml
contracts/events/spec-qms-006/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-qms-006/
```

REQUIREMENTS TO IMPLEMENT (24):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| TRN-FR-001 | Curriculum | Define curriculum by role/site/department/product/process/equipment/area. | Targeted. |
| TRN-FR-002 | Requirement source | Training can originate from document, role, qualification, change, CAPA or manager assignment. | Trace. |
| TRN-FR-003 | Assignment | Assign user/group with due/effective date and completion type. | Actionable. |
| TRN-FR-004 | Training types | Read/understand, instructor-led, practical/OJT, exam, demonstration, qualification, recurring. | Flexible. |
| TRN-FR-005 | Exact content version | Document training references exact released version. | Correct content. |
| TRN-FR-006 | Completion evidence | Trainee/trainer/date/score/result/evidence/signature. | Evidence. |
| TRN-FR-007 | Assessment | Quiz/exam/pass score/attempt rules; question bank versioned if used. | Competency. |
| TRN-FR-008 | Practical qualification | Observed checklist/process/equipment scope and evaluator. | Skill. |
| TRN-FR-009 | Qualification issuance | Completion may issue qualification with effective/expiry dates. | IAM integration. |
| TRN-FR-010 | Expiry/renewal | Recurring training/qualification renewal and execution blocking at expiry. | Current competence. |
| TRN-FR-011 | Grace period | Explicit controlled policy only. | No hidden grace. |
| TRN-FR-012 | Retraining triggers | Document revision, change, CAPA, deviation, performance, periodic cycle. | Current knowledge. |
| TRN-FR-013 | Revision impact | Document release decides whether retraining required and for whom. | Risk based. |
| TRN-FR-014 | Equivalency | Prior training/experience credit requires evidence/approval. | Controlled. |
| TRN-FR-015 | Waiver | Reason/scope/approver/expiry if permitted. | Bounded. |
| TRN-FR-016 | Execution gate | Policy Service blocks operation when training/qualification inactive. | Real enforcement. |
| TRN-FR-017 | Trainer qualification | Trainer/evaluator qualification where required. | Qualified assessor. |
| TRN-FR-018 | Temporary auth | Uses Document 07 process; training module cannot bypass authority. | No loophole. |
| TRN-FR-019 | Overdue escalation | Critical overdue training escalates. | Timely. |
| TRN-FR-020 | Training matrix | Role-vs-required training/qualification/gaps/expiry. | Management. |
| TRN-FR-021 | External training | Record external course/certificate with evidence/approval. | Broader competence. |
| TRN-FR-022 | History | Role/department changes do not rewrite old training. | Integrity. |
| TRN-FR-023 | Transcript | Complete training/qualification export. | Inspection-ready. |
| TRN-FR-024 | Failed attempts | Failed/expired attempts retained. | Data integrity. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `training_requirement` | 5 | PostgreSQL (GxP Core, authoritative) |
| `training_assignment` | 10 | PostgreSQL (GxP Core, authoritative) |
| `qualification_record` | 6 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (8):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /training/v1/requirements` | yes | — |
| `POST /training/v1/assignments` | yes | policy lookup (Doc 106) |
| `POST /training/v1/assignments/{id}/complete` | yes | policy lookup (Doc 106) |
| `POST /training/v1/assignments/{id}/assess` | yes | policy lookup (Doc 106) |
| `POST /training/v1/qualifications` | yes | — |
| `POST /training/v1/waivers` | yes | — |
| `GET /training/v1/subjects/{id}/status` | no | — |
| `GET /training/v1/matrix` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (7):
| Event type | Producer | Dedupe key |
|---|---|---|
| `TrainingAssigned` | SPEC-QMS-006 | event_id |
| `TrainingCompleted` | SPEC-QMS-006 | event_id |
| `TrainingFailed` | SPEC-QMS-006 | event_id |
| `QualificationIssued` | SPEC-QMS-006 | event_id |
| `QualificationExpired` | SPEC-QMS-006 | event_id |
| `RetrainingRequired` | SPEC-QMS-006 | event_id |
| `TrainingWaiverApproved` | SPEC-QMS-006 | event_id |

UI SURFACES:
- Training Dashboard
- Curriculum/Requirement
- Assignments
- Learning/Acknowledgment
- Assessment
- Practical Evaluation
- Qualifications
- Expiry/Renewal
- Training Matrix
- Transcript

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- DB unavailable: no regulated state transition.
- Signature/Policy unavailable: fail closed where required.
- Notification/outbox failures retry.
- Stale version rejects.
- Scheduled due/expiry jobs resume from persisted records.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- document revision
- failed exam
- qualification expiry during batch
- trainer unqualified
- equivalency
- waiver
- temporary auth cannot bypass
- role transfer
- audit transcript
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-05/Document_31_SPEC-QMS-006_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-QMS-006/<test_case_id>/`.
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
