# Claude Code prompt — WP-03 / Document 14: Review-by-Exception & QA Review Specification

TASK:
Implement the Review-by-Exception & QA Review Specification module (SPEC-EBMR-005) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_14_Review_by_Exception_QA_Review_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: RBE-FR-001..030 (30)
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
- `services/gxp-api/src/modules/ebmr` and its tests
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
services/gxp-api/src/modules/ebmr/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/ebmr/migrations/     # owned entities only
services/gxp-api/src/modules/ebmr/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-ebmr-005.yaml
contracts/events/spec-ebmr-005/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-ebmr-005/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| RBE-FR-001 | Review package | At Production Complete create versioned QA review package referencing stable batch record version and current exception index. | QA reviews defined scope. |
| RBE-FR-002 | Full-record access | Review-by-exception is an aid, not a substitute for access to complete record/evidence. | No hidden record. |
| RBE-FR-003 | Exception index | Aggregate deviations, OOS/OOT, NCRs, parameter excursions, manual overrides, corrections, missing evidence, failed integrations, late steps, equipment/material/environment issues, reconciliation/yield variance and signature issues. | Critical issues visible. |
| RBE-FR-004 | Severity | Assign severity/risk/category using released rule/QMS classification; QA may reclassify only through controlled reason/authority. | Prioritization controlled. |
| RBE-FR-005 | Completeness engine | Independently verify all applicable steps, required values, evidence, signatures, QC, materials, genealogy and calculations are present. | Missing data cannot be hidden because no exception was generated. |
| RBE-FR-006 | Changed-value review | List every controlled correction/superseded value with old/new, reason, actor, signature and impact. | Corrections obvious. |
| RBE-FR-007 | Manual override review | List automated-to-manual fallback, overrides, waived checks and exceptional authorizations. | Non-routine activity visible. |
| RBE-FR-008 | Audit-trail review | Provide filtered audit view for critical records/fields and allow QA to document review status separately. | Part 11/data-integrity support. |
| RBE-FR-009 | Signature review | Check required signatures exist, are valid, bound to current versions and satisfy SoD. | No invalid signature chain. |
| RBE-FR-010 | QC review | Summarize required tests, accepted results, superseded results, OOS/OOT and pending items. | QC status clear. |
| RBE-FR-011 | Material review | Summarize material lots, quality status at use, deviations, substitutions, reconciliation and expired/retest issues. | Material impact visible. |
| RBE-FR-012 | Equipment review | Show equipment used, eligibility at operation time, calibration/qualification/cleaning exceptions. | Equipment evidence. |
| RBE-FR-013 | Environment/sterile review | Where applicable show EM excursions, interventions, sterilization/filter/hold-time blockers. | Sterile DDCP review. |
| RBE-FR-014 | Genealogy completeness | Confirm required constituent/material/component/serial relationships exist and no unresolved gaps. | Release trace complete. |
| RBE-FR-015 | Packaging/label review | Show line clearance, label version, issuance/reconciliation, UDI, packaging inspection and discrepancies. | Packaging release evidence. |
| RBE-FR-016 | Yield/reconciliation | Show theoretical/actual yield, phase calculations and material/label/packaging reconciliation with variance status. | Numerical blockers visible. |
| RBE-FR-017 | Reviewer comment | QA can add structured comment/question linked to exact record/exception/evidence; comment is audited. | Review dialogue attributable. |
| RBE-FR-018 | Return for controlled action | QA can request correction/investigation/additional evidence through defined action, not edit production data directly. | Separation maintained. |
| RBE-FR-019 | Review checklist | Product/profile-specific checklist is versioned and snapshot-bound to review package. | Review expectations stable. |
| RBE-FR-020 | Review completion | Reviewer cannot complete until required checklist items and assigned exceptions are dispositioned or explicitly accepted according to policy. | No incomplete closure. |
| RBE-FR-021 | Multi-reviewer | Support specialist review sections (QC, Device Quality, Drug Quality, Sterile, Packaging) and final QA consolidation where required. | DDCP cross-functional review. |
| RBE-FR-022 | Review SoD | Review/release roles and prior execution participation evaluated through Document 07. | Independent review. |
| RBE-FR-023 | Review signature | Review completion uses regulated e-signature when in Part 11 scope; binds review package version/hash. | Exact review signed. |
| RBE-FR-024 | Review re-open | New evidence/correction after review completion invalidates/reopens affected review and requires re-evaluation/signature. | No stale review. |
| RBE-FR-025 | Risk-based routing | Rules may route high-risk exceptions to additional reviewers but cannot reduce mandatory customer/regulatory review requirements. | Escalation safe. |
| RBE-FR-026 | Search/trending | QA dashboard can filter batches by exception class, review age, product/site and blockers. | Operational quality management. |
| RBE-FR-027 | Export | Review package included in final batch export with checklist, reviewer comments, signatures and exception disposition. | Inspection-ready. |
| RBE-FR-028 | Performance | Exception index generated asynchronously but review cannot falsely show 'complete' until index/completeness status is current. | No stale green status. |
| RBE-FR-029 | Integrity health | Audit/evidence integrity failures appear as review blockers. | Tamper signal impacts release. |
| RBE-FR-030 | Review record retention | Review comments/checklists/signatures retained with batch record. | Long-term evidence. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `qa_review_package` | 12 | PostgreSQL (GxP Core, authoritative) |
| `qa_review_item` | 10 | PostgreSQL (GxP Core, authoritative) |
| `qa_review_comment` | 5 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (9):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /qa-review/v1/batches/{batchId}/packages` | yes | — |
| `GET /qa-review/v1/packages/{id}` | no | — |
| `GET /qa-review/v1/packages/{id}/exceptions` | no | — |
| `POST /qa-review/v1/packages/{id}/comments` | yes | — |
| `POST /qa-review/v1/items/{id}/request-action` | yes | — |
| `POST /qa-review/v1/items/{id}/disposition` | yes | policy lookup (Doc 106) |
| `POST /qa-review/v1/packages/{id}/complete` | yes | — |
| `POST /qa-review/v1/packages/{id}/reindex` | yes | — |
| `GET /qa-review/v1/dashboard` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `QAReviewPackageCreated` | SPEC-EBMR-005 | event_id |
| `QAExceptionIndexed` | SPEC-EBMR-005 | event_id |
| `QAReviewStarted` | SPEC-EBMR-005 | event_id |
| `QAActionRequested` | SPEC-EBMR-005 | event_id |
| `QAReviewReopened` | SPEC-EBMR-005 | event_id |
| `QAReviewCompleted` | SPEC-EBMR-005 | event_id |

UI SURFACES:
- Batch Header / Product / Recipe
- Release Blockers
- Exception Summary by severity/category
- Corrections & Overrides
- QC/OOS/OOT
- Materials
- Equipment/Environment
- Packaging/Labels
- Genealogy
- Yield/Reconciliation
- Signatures
- Audit Trail
- Full Record
- Review Checklist
- Reviewer Comments / Actions

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
- no exceptions normal batch
- hidden missing field caught by completeness
- correction visible
- manual override visible
- unresolved deviation
- calibration exception
- environmental excursion
- label mismatch
- failed reconciliation
- invalid signature
- source changes after review signature
- multi-reviewer
- integrity checkpoint failure
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-03/Document_14_SPEC-EBMR-005_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EBMR-005/<test_case_id>/`.
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
- proof of completeness
- all exceptions
- full record access
- audit/signature/evidence drilldown
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
