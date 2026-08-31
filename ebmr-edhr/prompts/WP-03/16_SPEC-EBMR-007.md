# Claude Code prompt — WP-03 / Document 16: Packaging, Labeling & Reconciliation Specification

TASK:
Implement the Packaging, Labeling & Reconciliation Specification module (SPEC-EBMR-007) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_16_Packaging_Labeling_Reconciliation_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: PKG-FR-001..032 (32)
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
contracts/openapi/spec-ebmr-007.yaml
contracts/events/spec-ebmr-007/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-ebmr-007/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| PKG-FR-001 | Packaging configuration | Use released packaging configuration tied to product/version and packaging level. | Correct materials/process. |
| PKG-FR-002 | Packaging material eligibility | Verify packaging components/material lots are released, correct, unexpired and approved for product. | Wrong packaging blocked. |
| PKG-FR-003 | Label master/version | Reference exact released label/artwork/template version and approved variable-data schema. | No latest-label ambiguity. |
| PKG-FR-004 | Label issuance | Issue controlled quantity/range/job with product/batch/lot/serial scope, label version, operator/system source and time. | Strict issuance trace. |
| PKG-FR-005 | Label examination | Before use/release, verify identity/conformity and required fields; device profiles include applicable UDI, expiration/storage/handling instructions. | Pre-use correctness. |
| PKG-FR-006 | Print integration | Integrate label printer/label management system through adapter; each print job has immutable ID, template version, variable data hash and printer source. | Printed label reproducible. |
| PKG-FR-007 | Reprint | Reprint requires reason, authorization and controlled reprint counter/status; original/reprint history retained. | No uncontrolled duplicate labels. |
| PKG-FR-008 | Serialization | Where required allocate/consume serials/UDI PI values and prevent duplicate assignment. | Unique units. |
| PKG-FR-009 | Line clearance | Require packaging line clearance before start/changeover and capture prior-product/material/label clearance checklist. | Mix-up prevention. |
| PKG-FR-010 | Packaging execution | Record packaging line/equipment, start/end, operators, materials, quantities, inspections and interruptions. | Complete packaging history. |
| PKG-FR-011 | Label application verification | Verify applied label matches product/batch/serial/package; barcode/vision scan preferred where available. | Wrong label detected. |
| PKG-FR-012 | Packaging inspection | Capture visual/automated inspection results and defect/reject code. | Acceptance evidence. |
| PKG-FR-013 | Label reconciliation | Reconcile issued, used, returned, destroyed, rejected and unused label quantities according to released policy. | Discrepancies surfaced. |
| PKG-FR-014 | Reconciliation waiver/profile | Only apply allowed reconciliation exceptions/waivers when specifically configured under applicable rule/profile and alternate examination evidence exists. | No broad waiver. |
| PKG-FR-015 | Excess controlled label destruction | Record destruction of excess lot/control-number labels with quantity, reason and witness/authority where required. | No uncontrolled surplus. |
| PKG-FR-016 | Returned label control | Returned labels maintain identity/status/location to prevent mix-ups. | Reusable stock controlled. |
| PKG-FR-017 | Packaging reconciliation | Reconcile packaging component quantities and finished pack counts, rejects, samples and destruction. | Material balance. |
| PKG-FR-018 | Package hierarchy | Create unit→carton→shipper/pallet hierarchy and genealogy where applicable. | Distribution trace. |
| PKG-FR-019 | Aggregation correction | Wrong aggregation relationship corrected through controlled event preserving original. | Serialization history. |
| PKG-FR-020 | Tamper-evident profile | Where applicable support tamper-evident packaging checks/evidence through product profile. | Profile-specific compliance. |
| PKG-FR-021 | Expiration | Print/capture expiration from released rule/product data; operator cannot free-type controlled expiry unless allowed workflow. | Dating controlled. |
| PKG-FR-022 | UDI | Device/DDCP label execution supports exact DI/PI construction/source and records UDI by device/lot as applicable. | Current device requirement support. |
| PKG-FR-023 | Artwork/spec evidence | Packaging record references approved artwork/specification/version and sample/specimen or image/evidence where configured. | Historical label evidence. |
| PKG-FR-024 | Packaging hold | Line or batch packaging can be held for label/material/equipment/quality issue. | Stop mix-up. |
| PKG-FR-025 | Changeover | Controlled end/start between product/batch/label versions includes clearance and reconciliation closure. | Safe transition. |
| PKG-FR-026 | Rejected packages | Track rejected units/packages, defect reason, rework/scrap disposition and serial status. | No ghost product. |
| PKG-FR-027 | Samples | Account for retained/QC/inspection samples in packaging reconciliation where applicable. | Quantity balance. |
| PKG-FR-028 | Final packaging completion | Cannot complete packaging stage until required inspections, line clearance closure and reconciliations are acceptable/resolved. | Release blocker. |
| PKG-FR-029 | ERP/WMS posting | Post packaged finished quantity/status/reference after GxP commit using adapter and idempotency. | Financial/warehouse sync. |
| PKG-FR-030 | Audit/export | Packaging/label history appears in batch/device record export, including issuance, reprints, reconciliation and inspections. | Inspection-ready. |
| PKG-FR-031 | Electronic record correction | Incorrect captured label/packaging data uses controlled correction, never direct edit. | Data integrity. |
| PKG-FR-032 | Printer/device identity | Printer, scanner, vision system and applicator sources are registered/attributable where automated evidence is used. | Source trusted. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (4 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `packaging_run` | 6 | PostgreSQL (GxP Core, authoritative) |
| `label_issue` | 10 | PostgreSQL (GxP Core, authoritative) |
| `label_reconciliation` | 10 | PostgreSQL (GxP Core, authoritative) |
| `package_node` | 4 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (10):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /packaging/v1/runs` | yes | — |
| `POST /packaging/v1/runs/{id}/line-clearance` | yes | — |
| `POST /packaging/v1/runs/{id}/labels/issue` | yes | — |
| `POST /packaging/v1/print-jobs` | yes | — |
| `POST /packaging/v1/labels/{id}/reprint` | yes | — |
| `POST /packaging/v1/runs/{id}/label-application` | yes | — |
| `POST /packaging/v1/runs/{id}/inspection` | yes | — |
| `POST /packaging/v1/runs/{id}/reconcile-labels` | yes | — |
| `POST /packaging/v1/runs/{id}/reconcile-packaging` | yes | — |
| `POST /packaging/v1/runs/{id}/complete` | yes | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (11):
| Event type | Producer | Dedupe key |
|---|---|---|
| `PackagingRunStarted` | SPEC-EBMR-007 | event_id |
| `LineClearanceCompleted` | SPEC-EBMR-007 | event_id |
| `LabelIssued` | SPEC-EBMR-007 | event_id |
| `LabelPrinted` | SPEC-EBMR-007 | event_id |
| `LabelReprinted` | SPEC-EBMR-007 | event_id |
| `LabelApplied` | SPEC-EBMR-007 | event_id |
| `LabelMismatchDetected` | SPEC-EBMR-007 | event_id |
| `LabelReconciliationCompleted` | SPEC-EBMR-007 | event_id |
| `PackagingReconciliationCompleted` | SPEC-EBMR-007 | event_id |
| `PackageAggregated` | SPEC-EBMR-007 | event_id |
| `PackagingCompleted` | SPEC-EBMR-007 | event_id |

UI SURFACES:
- Packaging Run
- Line Clearance
- Packaging Materials
- Label Issuance
- Print/Reprint
- Application Verification
- Inspection
- Label Reconciliation
- Packaging Reconciliation
- Serialization/Aggregation
- Completion

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
- correct label
- wrong label scan
- obsolete label
- duplicate serial
- controlled reprint
- excessive labels
- discrepancy outside limit
- line clearance incomplete
- label return
- destruction
- package aggregation
- wrong aggregation correction
- packaging material rejected
- printer retry/idempotency
- completion blocker
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-03/Document_16_SPEC-EBMR-007_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EBMR-007/<test_case_id>/`.
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
