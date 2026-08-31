# Claude Code prompt — WP-03 / Document 17: Yield, Calculations & Manufacturing Reconciliation Specification

TASK:
Implement the Yield, Calculations & Manufacturing Reconciliation Specification module (SPEC-EBMR-008) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_17_Yield_Calculations_Manufacturing_Reconciliation_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: YLD-FR-001..032 (32)
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
contracts/openapi/spec-ebmr-008.yaml
contracts/events/spec-ebmr-008/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-ebmr-008/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| YLD-FR-001 | Theoretical yield definition | Recipe/product defines theoretical yield or measure at appropriate manufacturing phases using released calculation/rule versions. | Expected output controlled. |
| YLD-FR-002 | Actual yield source | Actual yield derives from authoritative measured/recorded output quantities and source/equipment/manual evidence. | No untraceable number. |
| YLD-FR-003 | Yield percentage | Calculate percentage of theoretical yield using validated decimal formula and explicit rounding. | Reproducible result. |
| YLD-FR-004 | Independent verification | Where required, calculated yield is independently verified or verified per automated-equipment rule/profile. | Support applicable 211.103 workflow. |
| YLD-FR-005 | Phase yield | Support multiple phase/stage calculations, not only final yield. | Process loss visible. |
| YLD-FR-006 | Yield limits | Released recipe defines min/max percentage or other acceptance rule and investigation trigger. | Out-of-limit automatic. |
| YLD-FR-007 | Automated calculation | Automated calculation records input references, rule version, engine version and result; verifier sees inputs/result. | Transparent automation. |
| YLD-FR-008 | Manual calculation fallback | If calculation manually entered/externally calculated, require source, reason/policy and verification; default prefer engine calculation. | Fallback controlled. |
| YLD-FR-009 | Material mass balance | Reconcile received/issued/dispensed/consumed/returned/rejected/destroyed/loss quantities for defined scope. | Material accountability. |
| YLD-FR-010 | Dispensing reconciliation | For each material requirement reconcile dispensed vs consumed/returned/approved loss. | Per-material closure. |
| YLD-FR-011 | Packaging material balance | Reconcile packaging components issued/used/rejected/returned/destroyed/samples. | Packaging accountability. |
| YLD-FR-012 | Label reconciliation | Consume Document 16 label counts and applicable waiver/profile rule. | Unified release blocker. |
| YLD-FR-013 | Device component reconciliation | For serialized/critical components reconcile issued/assembled/rejected/scrapped/returned where configured. | Component accountability. |
| YLD-FR-014 | Unit count reconciliation | Reconcile produced/accepted/rejected/reworked/sampled/scrapped packaged unit counts. | Finished quantity consistent. |
| YLD-FR-015 | Potency correction | Calculate required active material amount from released potency/assay result and formula/version. | Drug dispensing support. |
| YLD-FR-016 | Overage/excess | Recipe may define justified component excess/overage as released parameter; system distinguishes planned excess from variance. | No hidden overage. |
| YLD-FR-017 | Unit conversion | All calculations use controlled UOM service and explicit dimensional conversion. | No mixed-unit error. |
| YLD-FR-018 | Precision/rounding | Each calculation has explicit decimal precision, rounding mode and stage. | No developer default. |
| YLD-FR-019 | Tolerance | Reconciliation defines absolute/percentage tolerance and inclusive/exclusive semantics. | Boundary deterministic. |
| YLD-FR-020 | Variance | Outside-tolerance result creates blocker and linked deviation/investigation according to profile. | No silent acceptance. |
| YLD-FR-021 | Approved loss | Document controlled reasons/categories for process loss, sample, spill, reject, destruction; approval may be required. | Variance explained. |
| YLD-FR-022 | Correction | Input/result correction preserves original and automatically re-evaluates affected downstream yields/reconciliations/review. | Consistency maintained. |
| YLD-FR-023 | Snapshot rule version | Batch uses exact calculation/reconciliation rules included in issue snapshot. | Historical reproducibility. |
| YLD-FR-024 | Rework/reprocess accounting | Original and rework material/output remain linked; no double-counting. | True balance. |
| YLD-FR-025 | Partial batch/sub-lot | Where supported, calculate and reconcile by defined scope and aggregate to parent. | Partial release support. |
| YLD-FR-026 | Serial/device scope | Unit count/component usage may aggregate serial-level data without losing exception visibility. | High-volume support. |
| YLD-FR-027 | External inventory reconciliation | ERP/WMS quantity may be compared after GxP calculation; discrepancy flagged but ERP never overwrites GxP evidence automatically. | Boundary clear. |
| YLD-FR-028 | Review display | QA sees source quantities, formulas, calculation versions, results, tolerances, variances and investigations. | Reviewable. |
| YLD-FR-029 | Release blocker | Required unresolved yield/reconciliation failures block release. | Quality gate. |
| YLD-FR-030 | Export | Final batch record includes yield and reconciliation results plus verification/signature and variance disposition. | 211.188-style evidence support. |
| YLD-FR-031 | Calculation trace | For every result retain input IDs/versions/values, calculation rule, engine version, time and verifier/signature if required. | Reproducible. |
| YLD-FR-032 | Performance | Large serial/component reconciliations may run asynchronously but final state is versioned and release waits for current result. | Scale safe. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `manufacturing_calculation` | 16 | PostgreSQL (GxP Core, authoritative) |
| `reconciliation_record` | 9 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (8):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /manufacturing-calculations/v1/yield/evaluate` | yes | — |
| `POST /manufacturing-calculations/v1/potency/evaluate` | yes | — |
| `POST /reconciliation/v1/material/evaluate` | yes | — |
| `POST /reconciliation/v1/packaging/evaluate` | yes | — |
| `POST /reconciliation/v1/labels/evaluate` | yes | — |
| `POST /reconciliation/v1/components/evaluate` | yes | — |
| `POST /reconciliation/v1/{id}/verify` | yes | policy lookup (Doc 106) |
| `GET /reconciliation/v1/batches/{batchId}/summary` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (7):
| Event type | Producer | Dedupe key |
|---|---|---|
| `YieldCalculated` | SPEC-EBMR-008 | event_id |
| `YieldOutOfLimit` | SPEC-EBMR-008 | event_id |
| `YieldVerified` | SPEC-EBMR-008 | event_id |
| `MaterialReconciliationCalculated` | SPEC-EBMR-008 | event_id |
| `ReconciliationFailed` | SPEC-EBMR-008 | event_id |
| `ReconciliationVerified` | SPEC-EBMR-008 | event_id |
| `ReconciliationSuperseded` | SPEC-EBMR-008 | event_id |

UI SURFACES:
- phase;
- theoretical quantity;
- actual quantity;
- UOM;
- formula/version;
- calculated percentage;
- limits;
- outcome;
- input source drilldown;
- verifier/signature.

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
- normal yield
- zero theoretical quantity
- decimal precision
- UOM conversion
- min boundary
- max boundary
- below/above tolerance
- independent verification
- potency adjustment
- material return
- sample/destruction
- rework
- label discrepancy
- component scrap
- ERP discrepancy
- correction recalculation
- old rule snapshot
- large serial aggregation
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-03/Document_17_SPEC-EBMR-008_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EBMR-008/<test_case_id>/`.
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
- stage yield
- final yield
- active material/potency calculation where configured
- raw material reconciliation
- device component count reconciliation
- label reconciliation
- packaging reconciliation
- all results visible to QA and Release Engine
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
