# Claude Code prompt — WP-04 / Document 25: OOS / OOT Management Specification

TASK:
Implement the OOS / OOT Management Specification module (SPEC-QC-003) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_25_OOS_OOT_Management_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: OOS-FR-001..030 (30); OOT-FR-001..010 (10)
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
- `services/gxp-api/src/modules/qc` and its tests
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
services/gxp-api/src/modules/qc/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/qc/migrations/     # owned entities only
services/gxp-api/src/modules/qc/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-qc-003.yaml
contracts/events/spec-qc-003/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-qc-003/
```

REQUIREMENTS TO IMPLEMENT (40):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| OOS-FR-001 | Automatic OOS creation | Applicable result outside released specification/acceptance criterion creates OOS record automatically and links original result/sample/test/batch/material. | OOS cannot be suppressed. |
| OOS-FR-002 | Original result preservation | Original result, raw data, calculations, method, analyst, instrument, timestamps and audit remain immutable/retrievable regardless of later investigation/retest. | No result substitution. |
| OOS-FR-003 | Immediate notification | Notify QC/QA and affected batch/material workflow according to severity/profile; place release/continuation hold where configured. | Risk contained. |
| OOS-FR-004 | OOS state model | Open → Laboratory Investigation → Extended/Manufacturing Investigation if required → Impact/Disposition → QA Approval → Closed. | Controlled progression. |
| OOS-FR-005 | Phase I laboratory review | Capture analyst interview/check, method/procedure adherence, calculations, instrument status, standards/reagents, sample preparation, system suitability, raw data and obvious assignable cause evidence. | Scientific initial investigation. |
| OOS-FR-006 | Assignable cause | Only invalidate original test as analytically invalid when documented evidence supports specific assignable laboratory cause under procedure. | No speculative invalidation. |
| OOS-FR-007 | No assignable cause | If no conclusive laboratory error, proceed to broader investigation rather than declaring test invalid. | Comprehensive investigation. |
| OOS-FR-008 | Manufacturing investigation | Link batch records, process parameters, materials, equipment, environment, deviations, other batches/lots and historical trends as required. | Root cause beyond lab. |
| OOS-FR-009 | Batch/material hold | OOS can place affected batch/material/related lots on controlled hold pending investigation. | No release. |
| OOS-FR-010 | Retest plan | Retesting requires predefined/procedurally justified number of retests, method, analyst/instrument strategy and interpretation rule approved before executing retest. | No testing into compliance. |
| OOS-FR-011 | Retest authorization | Authorized QC/QA approval required before retest; original test remains. | Controlled action. |
| OOS-FR-012 | Retest result | Each retest is independent test instance linked to OOS, with complete raw data/result/review. | Full evidence. |
| OOS-FR-013 | Retest interpretation | System does not automatically average away/replace initial OOS; outcome follows released OOS procedure/rule and QA disposition. | No cherry-picking. |
| OOS-FR-014 | Resample plan | Resampling requires scientific rationale that original sample may not represent batch/material, authorization and defined sampling plan. | Controlled resampling. |
| OOS-FR-015 | Resample lineage | New sample explicitly links to original sample/OOS and captures source/location/container/quantity/time. | Trace. |
| OOS-FR-016 | Invalid test classification | Invalid result/test remains visible with reason/evidence and state; does not become deleted/hidden. | Data integrity. |
| OOS-FR-017 | Root cause | Capture root cause category/method/evidence; “unknown/no assignable cause” allowed when justified, not forced fake cause. | Scientific integrity. |
| OOS-FR-018 | Impact assessment | Assess affected batch/material/product, related lots, prior/subsequent batches, stability/complaints/other results as procedure requires. | Scope determined. |
| OOS-FR-019 | Disposition | Possible outcomes include Confirmed OOS/Reject, Laboratory Error/Invalid Test, Manufacturing Cause, No Assignable Cause with QA decision, Reprocess/Rework path where allowed. | Explicit conclusion. |
| OOS-FR-020 | CAPA link | Create/link CAPA when investigation identifies systemic/corrective/preventive action need. | QMS integration. |
| OOS-FR-021 | Change control link | Method/process/spec/system changes resulting from OOS require controlled Change Control. | No informal fix. |
| OOS-FR-022 | Closure | OOS closes only after required investigation, impact, retest/resample dispositions, linked actions and QA approval/signature complete. | No premature closure. |
| OOS-FR-023 | Reopen | New material information/evidence can reopen closed OOS through controlled workflow preserving prior closure decision. | History. |
| OOT-FR-001 | OOT rule | Define versioned trend rule by test/product/material/site using statistical/historical/business methodology approved by customer Quality. | Configurable. |
| OOT-FR-002 | OOT trigger | Result can trigger OOT while still within specification; raw result remains PASS against specification plus separate OOT flag/investigation status. | Do not mislabel as OOS. |
| OOT-FR-003 | OOT baseline | Trend rule references approved historical window/population, expected range/control logic and exclusions. | Method reproducible. |
| OOT-FR-004 | OOT state model | Open → Trend Review → Investigation/Impact → Action/Disposition → QA Approval → Closed. | Controlled. |
| OOT-FR-005 | Historical comparison | Display current result versus prior lots/batches/timepoints and relevant statistics/limits without changing official result. | Context. |
| OOT-FR-006 | OOT impact | Determine potential effect on batch/material/stability/process and whether release hold is required by profile. | Risk based. |
| OOT-FR-007 | Repeat OOT escalation | Repeated OOT signals can escalate severity/CAPA/change review according to trend rules. | Systemic detection. |
| OOT-FR-008 | Spec vs trend separation | Specification acceptance and OOT trending are separate dimensions; one does not silently modify the other. | Semantics clear. |
| OOT-FR-009 | External trend source | External LIMS/statistical tool OOT flag may be imported with source/method/version; GxP retains accepted flag/investigation linkage. | Integration. |
| OOT-FR-010 | Trend recalculation | When baseline/rule changes, historical official results remain; new trend analyses are versioned rather than rewriting past OOT decisions. | History. |
| OOS-FR-024 | Role/SoD | Analyst, investigator, QC reviewer and QA approver permissions configurable; analyst cannot unilaterally invalidate own failing result. | Independent authority. |
| OOS-FR-025 | E-signature | Key investigation/authorization/closure/disposition actions use regulated signatures per policy. | Attributable decisions. |
| OOS-FR-026 | Audit | Every investigation statement, classification, retest/resample authorization, result, conclusion, impact and closure is auditable/versioned. | Inspection-ready. |
| OOS-FR-027 | Review-by-exception | Open/closed OOS/OOT, retests, invalidated tests and impact status appear in QA Review package. | Release aware. |
| OOS-FR-028 | Release engine | Open/unresolved/confirmed OOS/OOT impacts feed explicit release blockers/warnings based on profile. | No bypass. |
| OOS-FR-029 | Metrics/trending | Dashboard OOS rate, recurring test/method/instrument/product/analyst patterns and closure aging; metrics never substitute investigation. | Quality intelligence. |
| OOS-FR-030 | Export | Generate complete investigation package with original and all subsequent data/results, approvals, impacts, audit and linked CAPA/change. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (5 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `oos_record` | 17 | PostgreSQL (GxP Core, authoritative) |
| `oos_investigation_activity` | 7 | PostgreSQL (GxP Core, authoritative) |
| `oos_retest_plan` | 7 | PostgreSQL (GxP Core, authoritative) |
| `oos_resample_plan` | 5 | PostgreSQL (GxP Core, authoritative) |
| `oot_record` | 7 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (12):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /quality/oos/v1/from-result/{resultId}` | yes | — |
| `GET /quality/oos/v1/{id}` | no | — |
| `POST /quality/oos/v1/{id}/lab-investigation` | yes | — |
| `POST /quality/oos/v1/{id}/classify-lab-cause` | yes | — |
| `POST /quality/oos/v1/{id}/extended-investigation` | yes | — |
| `POST /quality/oos/v1/{id}/retest-plans` | yes | — |
| `POST /quality/oos/v1/{id}/resample-plans` | yes | — |
| `POST /quality/oos/v1/{id}/impact` | yes | — |
| `POST /quality/oos/v1/{id}/disposition` | yes | policy lookup (Doc 106) |
| `POST /quality/oos/v1/{id}/close` | yes | policy lookup (Doc 106) |
| `POST /quality/oot/v1/evaluate` | yes | — |
| `POST /quality/oot/v1/{id}/close` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (13):
| Event type | Producer | Dedupe key |
|---|---|---|
| `OOSOpened` | SPEC-QC-003 | event_id |
| `OOSLabInvestigationStarted` | SPEC-QC-003 | event_id |
| `OOSAssignableCauseDetermined` | SPEC-QC-003 | event_id |
| `OOSExtendedInvestigationStarted` | SPEC-QC-003 | event_id |
| `OOSRetestAuthorized` | SPEC-QC-003 | event_id |
| `OOSRetestCompleted` | SPEC-QC-003 | event_id |
| `OOSResampleAuthorized` | SPEC-QC-003 | event_id |
| `OOSImpactAssessed` | SPEC-QC-003 | event_id |
| `OOSDispositionApproved` | SPEC-QC-003 | event_id |
| `OOSClosed` | SPEC-QC-003 | event_id |
| `OOTDetected` | SPEC-QC-003 | event_id |
| `OOTInvestigationStarted` | SPEC-QC-003 | event_id |
| `OOTClosed` | SPEC-QC-003 | event_id |

UI SURFACES:
- OOS Header / Original Result
- Raw Data / Method
- Laboratory Investigation
- Assignable Cause Decision
- Manufacturing/Extended Investigation
- Retest Plan/Results
- Resample Plan/Results
- Impact Assessment
- CAPA/Change Links
- Final Disposition
- QA Closure
- Full Audit
- OOT Signal
- Trend Chart / Historical Context
- Investigation
- Impact/Action

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
- justification
- number of retests
- method
- analyst/instrument criteria
- interpretation rule
- approver signature
- status
- unlimited “try again” button
- deleting failing injections/readings
- replacing initial result field
- selecting only favorable results without method/procedure basis
- undocumented retesting
- automatic OOS
- attempt to suppress OOS
- proven calculation error
- unproven lab error
- retest without authorization
- configured retest count exceeded
- passing retest does not replace original
- resample without rationale
- result correction vs retest distinction
- OOS holds batch
- CAPA link
- confirmed OOS reject
- OOT within spec
- repeated OOT escalation
- LIMS-managed OOS status sync
- closed OOS reopened
- reviewer/analyst SoD
- audit/export
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-04/Document_25_SPEC-QC-003_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-QC-003/<test_case_id>/`.
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
