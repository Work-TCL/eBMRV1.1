# Claude Code prompt — WP-12 / Document 94: Validation Defect, Deviation, Test Exception & Remediation Management

TASK:
Implement the Validation Defect, Deviation, Test Exception & Remediation Management module (SPEC-VAL-016) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_94_Validation_Defect_Deviation_Exception_Remediation_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: VEX-FR-001..022 (22)
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
contracts/openapi/spec-val-016.yaml
contracts/events/spec-val-016/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-val-016/
```

REQUIREMENTS TO IMPLEMENT (22):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| VEX-FR-001 | Event types | Distinguish defect, test failure, protocol/environment deviation, evidence issue, requirement gap. | Clear workflow. |
| VEX-FR-002 | Automatic creation | Critical failed test can create validation exception automatically. | No loss. |
| VEX-FR-003 | Original evidence | Original failure/evidence immutable. | History. |
| VEX-FR-004 | Triage | Severity and GxP/release impact assessed. | Risk. |
| VEX-FR-005 | Engineering link | Issue/PR/commit linked to validation failure. | Trace. |
| VEX-FR-006 | QMS link | Validated-state impact can link/create Quality deviation. | QMS. |
| VEX-FR-007 | Protocol deviation | Departure from approved procedure records reason/impact/approval. | Controlled. |
| VEX-FR-008 | Environment deviation | Wrong environment/config may invalidate result. | Evidence validity. |
| VEX-FR-009 | Evidence issue | Missing/corrupt evidence cannot remain unexplained PASS. | Integrity. |
| VEX-FR-010 | Root cause | Critical/recurrent failure gets appropriate cause analysis. | Quality. |
| VEX-FR-011 | Fix link | Correction/change/version linked. | Remediation. |
| VEX-FR-012 | Retest scope | Direct/regression retest based on cause/change/risk. | Adequate verification. |
| VEX-FR-013 | Retest identity | New execution ID; prior failure remains. | History. |
| VEX-FR-014 | Disposition | OPEN/FIX/RETEST/ACCEPTED_WITH_RATIONALE/DEFERRED_BLOCKING/CLOSED. | Explicit. |
| VEX-FR-015 | Risk acceptance | Acceptance without fix needs residual-risk approval and cannot violate binding requirement. | Governance. |
| VEX-FR-016 | Release blocker | Critical/high unresolved/invalid evidence blocks release by policy. | Gate. |
| VEX-FR-017 | Known limitation | Approved limitation appears in VSR/release/customer package where material. | Transparency. |
| VEX-FR-018 | Trend | Track recurring failures/flaky tests/root causes. | Improvement. |
| VEX-FR-019 | Closure | Fix/retest/impact/approval needed. | Complete. |
| VEX-FR-020 | Reopen | New evidence can reopen with history. | Lifecycle. |
| VEX-FR-021 | Audit | Triage/disposition/closure/reopen audited/signed as policy. | Accountability. |
| VEX-FR-022 | VSR link | Open/accepted deviations automatically included in VSR. | Inspection. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createValidationException() | Test system/Validator | source execution; type; description; evidence; requirements | ValidationException | ValidationExceptionCreated |
| triageValidationException() | Validation/QA/Engineering | exception; severity; GxP/release impact; rationale | ExceptionTriage | ValidationExceptionTriaged |
| linkEngineeringDefect() | Engineering integration | exception; issue/commit/PR | DefectLink | EngineeringDefectLinked |
| defineRetestScope() | Validation | exception; fix/change; affected trace graph | RetestPlan | ValidationRetestScopeDefined |
| dispositionValidationException() | QA/Validation | exception; disposition; rationale; signature | ExceptionDisposition | ValidationExceptionDispositioned |
| evaluateExceptionReleaseBlockers() | Release gate | release; open exceptions | ExceptionGateResult | ValidationExceptionGateEvaluated |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (1 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `validation_exception` | 9 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (5):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /validation/v1/exceptions` | yes | — |
| `POST /validation/v1/exceptions/{id}/triage` | yes | — |
| `POST /validation/v1/exceptions/{id}/retest-plan` | yes | — |
| `POST /validation/v1/exceptions/{id}/disposition` | yes | policy lookup (Doc 106) |
| `GET /validation/v1/releases/{id}/exception-gate` | no | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (4):
| Event type | Producer | Dedupe key |
|---|---|---|
| `ValidationExceptionCreated` | SPEC-VAL-016 | event_id |
| `ValidationExceptionTriaged` | SPEC-VAL-016 | event_id |
| `ValidationRetestScopeDefined` | SPEC-VAL-016 | event_id |
| `ValidationExceptionDispositioned` | SPEC-VAL-016 | event_id |

UI SURFACES:
- Validation Exceptions
- Triage
- Defect Links
- Retest Scope
- Risk Acceptance
- Release Blockers
- Trend

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- fail then fixed/retest
- wrong environment invalidates pass
- missing critical evidence
- accepted cosmetic issue
- critical defect blocks release
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-12/Document_94_SPEC-VAL-016_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-VAL-016/<test_case_id>/`.
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
