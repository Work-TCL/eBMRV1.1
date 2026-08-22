# Claude Code prompt — WP-01 / Document 08: Regulatory Rules & Calculation Engine

TASK:
Implement the Regulatory Rules & Calculation Engine module (SPEC-GXP-006) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_08_Regulatory_Rules_and_Calculation_Engine_Specification_v1_1_IMPLEMENTATION_READY.md`
- Requirement IDs: RUL-FR-001..032 (32)
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

- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `services/gxp-api/src/modules/rules` and its tests
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
services/gxp-api/src/modules/rules/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/rules/migrations/     # owned entities only
services/gxp-api/src/modules/rules/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-gxp-006.yaml
contracts/events/spec-gxp-006/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-gxp-006/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| RUL-FR-001 | Controlled rule object | Every GxP-critical rule/formula has stable ID, type, semantic version, status, scope and owner. | Rule identifiable in historical decision. |
| RUL-FR-002 | Rule lifecycle | Draft → Review → Approved/Released → Effective → Superseded/Retired. Released version immutable. | No in-place formula edit. |
| RUL-FR-003 | Effective dating | Rule version has effective-from/to and profile/site/product applicability; execution snapshots exact eligible version. | Future/obsolete rule not selected. |
| RUL-FR-004 | Deterministic evaluation | Same inputs + same released rule version produce same result, independent of UI/server instance. | Golden tests deterministic. |
| RUL-FR-005 | Safe expression language | GxP formulas/rules use constrained DSL/AST/function catalogue; arbitrary Python/JavaScript/SQL/network/file execution prohibited. | Expression cannot execute arbitrary code. |
| RUL-FR-006 | Typed inputs | Inputs define data type, unit, required/optional, precision, acceptable null behavior and source. | Wrong unit/type rejected. |
| RUL-FR-007 | Typed outputs | Outputs define result type, unit, precision, status/reason codes and downstream action. | Consumers contract stable. |
| RUL-FR-008 | Unit management | Use canonical UOM IDs and validated conversions; dimensional incompatibility rejected. | kg cannot be silently compared to L. |
| RUL-FR-009 | Decimal arithmetic | Use deterministic decimal arithmetic for regulated calculations; avoid binary floating-point where it could alter results. | Precision tests pass. |
| RUL-FR-010 | Rounding rules | Formula defines rounding mode, stage and decimal places/significant figures. | Rounding is explicit/versioned. |
| RUL-FR-011 | Limit rules | Support inclusive/exclusive min/max, target/tolerance, enumerations, ranges and conditional limits. | Boundary tests included. |
| RUL-FR-012 | Eligibility rules | Material, equipment, operator, area, recipe and constituent eligibility rules evaluate before relevant action. | Ineligible resource blocks. |
| RUL-FR-013 | Sequence/progression rules | Define prerequisite steps, parallel joins, conditional branches, hold points and permitted progression. | Out-of-sequence command denied. |
| RUL-FR-014 | Signature rules | Determine required signature meaning, signer role/qualification, independence and count/order. | Signature policy version captured. |
| RUL-FR-015 | Deviation/exception triggers | Out-of-limit, expired status, manual override, timing breach, environment excursion or missing evidence can generate configured exception/hold. | Trigger result deterministic. |
| RUL-FR-016 | Release rules | Aggregate required completion/QC/QMS/reconciliation/signature/equipment/environment evidence into release eligibility result with blockers. | Release reason codes explainable. |
| RUL-FR-017 | Yield calculation | Support theoretical/actual/stage yield and percentage according to released formula, input sources, verification policy and rounding. | §211.103-type scenarios testable where applicable. |
| RUL-FR-018 | Potency/assay adjustment | Support controlled potency correction with exact assay source/version, formula, units and precision. | Material quantity traceable. |
| RUL-FR-019 | Reconciliation calculation | Issued/dispensed/consumed/returned/rejected/destroyed quantities reconcile according to released rule/tolerance. | Variance creates blocker/event. |
| RUL-FR-020 | Time-window rules | Support process hold times, expiry/retest, calibration due, training expiry, timer limits and environmental windows using authoritative time. | Boundary/timezone tests pass. |
| RUL-FR-021 | Decision explanation | Every evaluation returns rule ID/version, inputs/reference IDs, outcome, reason codes and relevant calculated values. | QA can explain decision. |
| RUL-FR-022 | Evaluation persistence | Persist critical evaluation result/reference with regulated mutation/audit; avoid relying on recomputation under a newer rule. | Historical result reproducible. |
| RUL-FR-023 | Simulation/test mode | Authorized users can simulate draft rules against test/historical sanitized data without affecting regulated state. | Simulation clearly non-production. |
| RUL-FR-024 | Rule test cases | Each released critical rule includes approved positive, boundary, negative and error test vectors. | No release without tests. |
| RUL-FR-025 | Independent verification | Critical formulas can require independent reviewer approval/test evidence before release. | Formula author cannot self-approve if policy says no. |
| RUL-FR-026 | Change impact | Changing rule/formula triggers impact assessment for products, recipes, batches, tests, validation and customer configuration. | Affected scope report generated. |
| RUL-FR-027 | Snapshot binding | Batch/record snapshots reference exact rule/calculation versions required for execution. | Mid-batch rule change does not alter history. |
| RUL-FR-028 | External result rules | LIMS/ERP/Edge values are validated against source mapping, unit, schema and quality before rule evaluation. | Bad source data fails/quarantines. |
| RUL-FR-029 | Missing/invalid inputs | Rule defines explicit behavior: fail, hold, not-applicable or exception; never silently substitute default for critical missing data unless released rule permits. | Missing critical input cannot pass. |
| RUL-FR-030 | Overflow/domain errors | Divide-by-zero, invalid logarithm/range, overflow, unit mismatch or invalid enum produce controlled failure with no fabricated result. | Calculation errors observable. |
| RUL-FR-031 | Rule engine versioning | Record engine/runtime version separately from business rule version; engine upgrade requires regression. | Same rule under new engine validated. |
| RUL-FR-032 | Performance/cache safety | Caching compiled rules is allowed only if cache key includes immutable rule version and tenant/profile; cache cannot alter deterministic outcome. | No stale rule execution. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `gxp_rule_definition` | 19 | PostgreSQL (GxP Core, authoritative) |
| `gxp_rule_evaluation` | 13 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (6):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /rules/v1/drafts` | yes | — |
| `POST /rules/v1/{ruleId}/validate` | yes | — |
| `POST /rules/v1/{ruleId}/simulate` | yes | — |
| `POST /rules/v1/{ruleId}/release` | yes | policy lookup (Doc 106) |
| `GET /rules/v1/{ruleId}/versions` | no | — |
| `POST /rules/v1/evaluate` | yes | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- Rule Catalogue
- Rule Draft Editor
- Input/Output Contract
- Units/Precision/Rounding
- Test Vectors
- Simulation
- Review/Approval
- Released Versions
- Impact Analysis

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- missing critical input → fail/hold per released rule;
- invalid unit → reject;
- divide by zero/domain error → controlled calculation failure;
- unreleased rule → cannot execute production;
- rule engine unavailable → dependent regulated action fails closed;
- rule version not found for historical snapshot → integrity incident; no substitution with latest.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- deterministic repeat
- decimal precision
- every rounding mode used
- min/max boundary
- unit conversion
- invalid unit
- missing input
- null behavior
- effective dates
- superseded rule snapshot
- yield
- potency
- reconciliation
- time-window
- signature policy
- release blocker aggregation
- cache stale-rule test
- engine upgrade replay/golden tests
- happy path
- authorization denial
- validation failure
- stale/concurrent write
- duplicate/replay where applicable
- dependency outage
- restart/recovery
- data integrity
- audit verification
- signature verification where applicable
- nominal
- lower boundary
- upper boundary
- just below/above boundary
- invalid type
- null/missing
- arithmetic error where relevant
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-01/Document_08_SPEC-GXP-006_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-GXP-006/<test_case_id>/`.
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
- constrained DSL/AST decision
- decimal/UOM libraries selected and license-reviewed
- canonical calculation test-vector format
- initial V1 DDCP rule catalogue
- Release Engine interface
- change-control/validation workflow
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
