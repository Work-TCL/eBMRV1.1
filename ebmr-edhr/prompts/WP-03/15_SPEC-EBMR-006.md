# Claude Code prompt — WP-03 / Document 15: Release / Disposition Engine Specification

TASK:
Implement the Release / Disposition Engine Specification module (SPEC-EBMR-006) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_15_Release_Disposition_Engine_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: REL-FR-001..032 (32)
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
contracts/openapi/spec-ebmr-006.yaml
contracts/events/spec-ebmr-006/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-ebmr-006/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| REL-FR-001 | Release scope | Define release/disposition object for exact product/batch/device lot/serial/combination scope. | Decision target unambiguous. |
| REL-FR-002 | Separate DDCP final release | Drug/device constituent acceptance/release are prerequisites but never automatically equal final combination-product release. | Final DDCP authority separate. |
| REL-FR-003 | Eligibility evaluation | Evaluate released rule set against manufacturing completeness, QA review, QC, QMS, materials, equipment, environment, packaging, genealogy, yield/reconciliation and signatures. | No manual checklist-only release. |
| REL-FR-004 | Blocker model | Return machine-readable blockers with severity, source record and resolution action. | User knows exact reason. |
| REL-FR-005 | Warning model | Warnings may require acknowledgement/comment but cannot be used to downgrade mandatory blocker without controlled rule/change. | No ad hoc bypass. |
| REL-FR-006 | QA authority | Only authorized current QA Release signer(s) may execute final release/disposition. | Authority controlled. |
| REL-FR-007 | Step-up signature | Final release/reject/disposition uses Document 04 signature bound to exact release package/version/hash. | Exact decision signed. |
| REL-FR-008 | Re-evaluation before commit | Immediately before release commit, recheck batch version, eligibility rules, open blockers and signature validity. | No stale green status. |
| REL-FR-009 | Release snapshot | Commit immutable release package containing exact decision inputs, rule versions, review package, signatures, batch/record hash and genealogy completeness status. | Historical release reproducible. |
| REL-FR-010 | Release states | Draft Evaluation, Eligible, Blocked, Pending Signature, Released, Rejected, Hold, Rework, Reprocess, Destruction, Return/Other configured disposition. | Explicit disposition. |
| REL-FR-011 | Hold disposition | Quality can place release hold with reason and signature; release eligibility may continue updating but product cannot distribute. | Hold enforced. |
| REL-FR-012 | Reject | Reject decision records reason, affected scope, inventory status and downstream disposition requirement. | Rejected product controlled. |
| REL-FR-013 | Rework/reprocess | Disposition links to approved route; original release scope remains unreleased until new execution/review complete. | No shortcut. |
| REL-FR-014 | Destruction | Disposition can require destruction workflow/evidence/witness before closure. | Material/product accounted. |
| REL-FR-015 | Partial release | Only supported when product/profile explicitly allows defined sub-lot/serial scope with independent genealogy/QC/reconciliation; default disabled. | No accidental partial release. |
| REL-FR-016 | Serial release | Device units may inherit lot release only when profile/rules permit and all unit exceptions are resolved. | High-volume support. |
| REL-FR-017 | Expiry/retest/status | Evaluate expiration, stability/release test and relevant constituent status rules. | Expired/ineligible product cannot release. |
| REL-FR-018 | Open QMS events | Evaluate deviations/OOS/OOT/NCR/CAPA dependencies according to released profile; unresolved critical event blocks. | Quality integrated. |
| REL-FR-019 | Material status | All consumed critical material lots must have acceptable use status or approved deviation captured. | Traceable. |
| REL-FR-020 | Equipment status at use | Eligibility considers equipment status at operation time and unresolved equipment-impact events. | Historical correctness. |
| REL-FR-021 | Sterile/environment | Applicable sterile/environmental release evidence and excursion dispositions required. | Aseptic product support. |
| REL-FR-022 | Packaging/label | Packaging completion, label correctness and reconciliation required where applicable. | Final product correctly labeled. |
| REL-FR-023 | Genealogy | Required material/constituent/serial/package genealogy completeness required. | Recall-ready. |
| REL-FR-024 | Yield/reconciliation | Configured yield/material/label reconciliation within limits or resolved investigation required. | Numerical closure. |
| REL-FR-025 | Review package | QA review must be current/not invalidated and signed when required. | Review not stale. |
| REL-FR-026 | Release correction | Release decision itself cannot be edited; if later found erroneous, create controlled post-release quality/field-action path, not overwrite history. | Release history immutable. |
| REL-FR-027 | Distribution integration | After release, emit event to ERP/WMS; integration failure does not undo release but prevents/flags downstream availability according to interface policy. | System boundaries clear. |
| REL-FR-028 | Release certificate/export | Generate release summary/certificate if configured, with signer, time, product/batch, decision and source package hash. | Customer evidence. |
| REL-FR-029 | Release audit | Audit eligibility evaluation, blockers, acknowledgements, signature and final decision. | Inspection-ready. |
| REL-FR-030 | Bulk release | Batching multiple independent release scopes into one UI action may be allowed, but each scope gets independent eligibility/signature binding/decision record. | No one signature ambiguously covers unknown scope. |
| REL-FR-031 | Revoke availability | Post-release hold/recall is a new controlled status/action; released historical decision remains intact. | No history rewrite. |
| REL-FR-032 | Release SLA metrics | Track review/release cycle time and blocker aging without influencing regulatory decision. | Operational analytics. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `release_scope` | 13 | PostgreSQL (GxP Core, authoritative) |
| `release_evaluation` | 7 | PostgreSQL (GxP Core, authoritative) |
| `release_decision` | 7 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (9):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /release/v1/scopes/{type}/{id}/evaluate` | yes | policy lookup (Doc 106) |
| `GET /release/v1/scopes/{id}/eligibility` | no | policy lookup (Doc 106) |
| `POST /release/v1/scopes/{id}/release` | yes | policy lookup (Doc 106) |
| `POST /release/v1/scopes/{id}/hold` | yes | policy lookup (Doc 106) |
| `POST /release/v1/scopes/{id}/reject` | yes | policy lookup (Doc 106) |
| `POST /release/v1/scopes/{id}/rework` | yes | policy lookup (Doc 106) |
| `POST /release/v1/scopes/{id}/reprocess` | yes | policy lookup (Doc 106) |
| `POST /release/v1/scopes/{id}/destroy` | yes | policy lookup (Doc 106) |
| `GET /release/v1/scopes/{id}/package` | no | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (9):
| Event type | Producer | Dedupe key |
|---|---|---|
| `ReleaseEvaluationCompleted` | SPEC-EBMR-006 | event_id |
| `ReleaseEligibilityChanged` | SPEC-EBMR-006 | event_id |
| `ReleaseHoldPlaced` | SPEC-EBMR-006 | event_id |
| `ProductReleased` | SPEC-EBMR-006 | event_id |
| `ProductRejected` | SPEC-EBMR-006 | event_id |
| `ReworkDispositionApproved` | SPEC-EBMR-006 | event_id |
| `ReprocessDispositionApproved` | SPEC-EBMR-006 | event_id |
| `DestructionDispositionApproved` | SPEC-EBMR-006 | event_id |
| `PostReleaseHoldPlaced` | SPEC-EBMR-006 | event_id |

UI SURFACES:
- Release Dashboard
- Scope Header
- Eligibility Summary
- Blockers/Warnings
- QA Review Status
- QC/QMS
- Materials/Genealogy
- Packaging/Label
- Yield/Reconciliation
- Release Decision
- Signature Dialog
- Release Package

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
- fully eligible release
- open deviation
- missing QC
- stale QA review
- missing material genealogy
- equipment exception
- sterile excursion
- failed label reconciliation
- yield failure
- same user SoD conflict
- record changes during signature
- ERP outage after release
- reject
- rework
- partial release disabled
- DDCP constituent released but final not released
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-03/Document_15_SPEC-EBMR-006_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EBMR-006/<test_case_id>/`.
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
