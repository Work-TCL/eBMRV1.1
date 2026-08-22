# Claude Code prompt — WP-05 / Document 34: Internal Audit Management

TASK:
Implement the Internal Audit Management module (SPEC-QMS-009) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_34_Internal_Audit_Management_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: AUDIT-FR-001..017 (17)
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
contracts/openapi/spec-qms-009.yaml
contracts/events/spec-qms-009/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-qms-009/
```

REQUIREMENTS TO IMPLEMENT (17):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| AUDIT-FR-001 | Audit program | Define annual/multi-period audit program by site/process/system/supplier where applicable. | Planned oversight. |
| AUDIT-FR-002 | Audit plan | Scope, objectives, criteria, references, auditors, schedule, auditees. | Clear plan. |
| AUDIT-FR-003 | Auditor independence | Policy prevents auditor from auditing own direct work/function where required. | Objectivity. |
| AUDIT-FR-004 | Checklist | Versioned checklist/template supports sampling prompts but never limits auditor findings. | Consistent. |
| AUDIT-FR-005 | Evidence | Capture interview/record/sample/evidence references with access controls. | Evidence. |
| AUDIT-FR-006 | Finding | Requirement/observation/evidence/severity/classification. | Objective finding. |
| AUDIT-FR-007 | Finding response | Assign owner, correction, root-cause/action and due dates. | Accountability. |
| AUDIT-FR-008 | CAPA link | Significant/systemic finding can create CAPA. | Integration. |
| AUDIT-FR-009 | Verification | Auditor/QA verifies action/effectiveness. | Closure quality. |
| AUDIT-FR-010 | Audit report | Generate controlled report from approved record. | Formal output. |
| AUDIT-FR-011 | Closure | Close only after findings dispositioned per policy. | Complete. |
| AUDIT-FR-012 | Schedule change | Reschedule/cancel with reason/approval; old schedule retained. | Transparency. |
| AUDIT-FR-013 | Confidentiality | Role/site access restrictions. | Security. |
| AUDIT-FR-014 | Repeat findings | Detect recurrence by process/requirement/root cause. | Trend. |
| AUDIT-FR-015 | Metrics | Completion, overdue findings, recurrence, CAPA links. | Management. |
| AUDIT-FR-016 | External audit tracking | Track external audits/inspection commitments separately where configured. | Broader QMS. |
| AUDIT-FR-017 | Export | Plan/evidence/findings/responses/closure exportable. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `internal_audit` | 13 | PostgreSQL (GxP Core, authoritative) |
| `audit_finding` | 8 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (6):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /qms/v1/audits` | yes | — |
| `POST /qms/v1/audits/{id}/start` | yes | — |
| `POST /qms/v1/audits/{id}/findings` | yes | — |
| `POST /qms/v1/findings/{id}/response` | yes | — |
| `POST /qms/v1/findings/{id}/verify` | yes | policy lookup (Doc 106) |
| `POST /qms/v1/audits/{id}/close` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `InternalAuditScheduled` | SPEC-QMS-009 | event_id |
| `InternalAuditStarted` | SPEC-QMS-009 | event_id |
| `AuditFindingOpened` | SPEC-QMS-009 | event_id |
| `AuditReportApproved` | SPEC-QMS-009 | event_id |
| `AuditFindingClosed` | SPEC-QMS-009 | event_id |
| `InternalAuditClosed` | SPEC-QMS-009 | event_id |

UI SURFACES:
- Audit Program
- Audit Plan
- Checklist
- Evidence/Notes
- Findings
- Report
- Responses/CAPA
- Follow-Up
- Metrics

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
- auditor independence
- finding CAPA
- late response
- repeat finding
- reschedule
- report approval
- restricted evidence
- closure incomplete
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-05/Document_34_SPEC-QMS-009_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-QMS-009/<test_case_id>/`.
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
