# Claude Code prompt — WP-04 / Document 22: Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification

TASK:
Implement the Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification module (SPEC-MAT-002D) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_22_Material_Consumption_Return_Adjustment_Destruction_Reconciliation_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: CON-FR-001..032 (32)
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
- `services/gxp-api/src/modules/materials` and its tests
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
services/gxp-api/src/modules/materials/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/materials/migrations/     # owned entities only
services/gxp-api/src/modules/materials/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-mat-002d.yaml
contracts/events/spec-mat-002d/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-mat-002d/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| CON-FR-001 | Issue to production | Move dispensed/material container to production staging/use with exact batch/step reference and status. | Custody trace. |
| CON-FR-002 | Consumption | Record actual material quantity consumed in step, source dispensed container/lot and time. | Actual use evidence. |
| CON-FR-003 | Automatic consumption | Where machine/process provides authoritative quantity, accept via validated integration/rule; otherwise controlled manual capture. | Flexible source. |
| CON-FR-004 | Partial consumption | Track remaining quantity in dispensed container and resulting status/location. | No assumed full use. |
| CON-FR-005 | Return to warehouse | Return unused eligible material with quantity, seal/container condition, storage condition and status reevaluation. | Safe return. |
| CON-FR-006 | Return rejection | If return condition unsuitable, route to quarantine/reject/destruction workflow rather than normal stock. | No bad return. |
| CON-FR-007 | Material re-status after return | Product/profile may require QC/QA evaluation after exposure/opening/temperature excursion before reuse. | Risk controlled. |
| CON-FR-008 | Excess material | Record excess generated/remaining from dispensing/process and controlled disposition. | Balance complete. |
| CON-FR-009 | Process loss | Record allowed loss category/quantity/source and approval/rule. | Variance explained. |
| CON-FR-010 | Spill | Record spill quantity/estimate, quality/deviation link and cleanup evidence where required. | Incident trace. |
| CON-FR-011 | Sample withdrawal | Account for QC/in-process/reserve sample quantity and sample ID. | Balance. |
| CON-FR-012 | Reject/scrap material | Record rejected process material quantity, reason, location and disposition. | No ghost stock. |
| CON-FR-013 | Inventory adjustment | Exceptional positive/negative adjustment requires controlled reason, evidence, authorization and audit; cannot be routine correction for software defects. | Controlled discrepancy. |
| CON-FR-014 | Adjustment SoD | High-risk adjustment can require independent approval; user cannot approve own adjustment if configured. | Fraud/error control. |
| CON-FR-015 | Destruction request | Create destruction disposition for rejected/expired/excess/material/product with exact lot/container/quantity. | Scope exact. |
| CON-FR-016 | Destruction authorization | Require QA/authorized approval and witness where policy requires. | Controlled disposition. |
| CON-FR-017 | Destruction execution | Record method, date/time, performers/witnesses, quantity, evidence and destination/vendor where applicable. | Evidence. |
| CON-FR-018 | Third-party destruction | Track approved vendor/manifest/certificate and chain of custody. | External disposition trace. |
| CON-FR-019 | Reconciliation scope | Calculate material balance by batch/material requirement/lot/container/stage according to released rules. | Configurable scope. |
| CON-FR-020 | Source categories | Reconciliation includes dispensed/issued, consumed, returned, samples, rejected, destroyed, approved loss and unexplained variance. | Complete mass balance. |
| CON-FR-021 | Tolerance | Use Document 08/17 released tolerance/rounding/UOM rules. | Deterministic. |
| CON-FR-022 | Variance blocker | Out-of-tolerance/unexplained variance creates deviation/investigation and blocks production completion/release as configured. | No silent loss. |
| CON-FR-023 | Correction recalculation | Any corrected transaction creates superseding transaction/event and automatically recalculates affected reconciliation; original remains. | History. |
| CON-FR-024 | No transaction deletion | Consumption/return/adjustment/destruction records are immutable transactions; correction is reversal/supersession pattern. | Ledger integrity. |
| CON-FR-025 | ERP posting | Post consumption/return/scrap/destruction quantity/reference after GxP commit; retries idempotent. | Commercial sync. |
| CON-FR-026 | ERP discrepancy | Compare external postings and create reconciliation issue; ERP never overwrites GxP transaction ledger. | Boundary. |
| CON-FR-027 | Genealogy impact | Consumption creates genealogy; return/destruction preserves source/material identity and affected batch links. | Trace. |
| CON-FR-028 | Batch completion gate | All required material transactions/reconciliation must be current/acceptable before Production Complete. | eBMR complete. |
| CON-FR-029 | QA review | Review-by-exception shows adjustments, spills, losses, destruction and failed reconciliation. | Quality visibility. |
| CON-FR-030 | Audit/export | Batch/material history export includes all source/quantity/disposition/reconciliation records and signatures. | Inspection-ready. |
| CON-FR-031 | Cross-batch prohibition | A dispensed container assigned to Batch A cannot be consumed in Batch B unless a controlled return/reissue process creates new authorization. | No cross-use. |
| CON-FR-032 | Performance | Batch reconciliation may aggregate large device/packaging/component transaction sets asynchronously but current status is versioned. | Scale safe. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (5 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `material_consumption` | 11 | PostgreSQL (GxP Core, authoritative) |
| `material_return` | 7 | PostgreSQL (GxP Core, authoritative) |
| `inventory_adjustment_request` | 8 | PostgreSQL (GxP Core, authoritative) |
| `destruction_record` | 9 | PostgreSQL (GxP Core, authoritative) |
| `material_reconciliation` | 7 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (8):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /materials/v1/consumptions` | yes | — |
| `POST /materials/v1/returns` | yes | — |
| `POST /inventory/v1/adjustments` | yes | — |
| `POST /inventory/v1/adjustments/{id}/approve` | yes | policy lookup (Doc 106) |
| `POST /materials/v1/destructions` | yes | — |
| `POST /materials/v1/destructions/{id}/execute` | yes | — |
| `POST /reconciliation/v1/batches/{batchId}/materials/evaluate` | yes | — |
| `GET /reconciliation/v1/batches/{batchId}/materials` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (9):
| Event type | Producer | Dedupe key |
|---|---|---|
| `MaterialConsumed` | SPEC-MAT-002D | event_id |
| `MaterialReturned` | SPEC-MAT-002D | event_id |
| `MaterialSampled` | SPEC-MAT-002D | event_id |
| `MaterialLossRecorded` | SPEC-MAT-002D | event_id |
| `InventoryAdjustmentApproved` | SPEC-MAT-002D | event_id |
| `MaterialDestroyed` | SPEC-MAT-002D | event_id |
| `MaterialReconciliationCalculated` | SPEC-MAT-002D | event_id |
| `MaterialReconciliationFailed` | SPEC-MAT-002D | event_id |
| `ERPInventoryPostingFailed` | SPEC-MAT-002D | event_id |

UI SURFACES:
- Batch Material Usage
- Consume
- Return
- Loss/Spill/Sample
- Adjustment Request
- Destruction
- Reconciliation
- ERP Posting/Reconciliation
- Material History

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
- full consume
- partial consume
- cross-batch attempt
- return acceptable
- return needs quarantine
- spill
- sample withdrawal
- high-risk adjustment
- self-approval denied
- destruction with witness
- third-party destruction
- failed reconciliation
- correction/reversal
- ERP retry duplicate
- batch completion blocked
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-04/Document_22_SPEC-MAT-002D_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-MAT-002D/<test_case_id>/`.
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
