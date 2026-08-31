# Claude Code prompt — WP-07 / Document 49: ERPNext Adapter Detailed Contract

TASK:
Implement the ERPNext Adapter Detailed Contract module (SPEC-ERP-002) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_49_ERPNext_Adapter_Detailed_Contract_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: ENXT-FR-001..024 (24)
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
- `services/integration-gateway` and its tests
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
services/integration-gateway/src/            # domain services, command handlers, repositories
services/integration-gateway/migrations/     # owned entities only
services/integration-gateway/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-erp-002.yaml
contracts/events/spec-erp-002/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-erp-002/
```

REQUIREMENTS TO IMPLEMENT (24):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| ENXT-FR-001 | Supported API | Use supported Frappe/ERPNext REST/RPC APIs; direct ERPNext MariaDB access prohibited. | Upgrade-safe boundary. |
| ENXT-FR-002 | Authentication | Token/API-key or approved OAuth/session/service identity profile; credentials per instance. | Secure. |
| ENXT-FR-003 | Item mapping | Map GxP product/material/component IDs to ERPNext Item codes and UOM. | Identity. |
| ENXT-FR-004 | Supplier mapping | Map supplier but never infer Approved Supplier status from ERPNext Supplier enabled state. | Quality boundary. |
| ENXT-FR-005 | Warehouse mapping | Map GxP site/warehouse/location to ERPNext Warehouse where integration mode requires. | Inventory sync. |
| ENXT-FR-006 | Purchase Order | Read/create/update PO through canonical provider when native procurement/ERP mode configured. | Procurement. |
| ENXT-FR-007 | Purchase Receipt | Post goods receipt after GxP receipt transaction, preserving PO/item/lot refs. | Receipt sync. |
| ENXT-FR-008 | Stock Entry issue | Post material issue/consumption through Stock Entry or supported ERPNext transaction abstraction. | Inventory posting. |
| ENXT-FR-009 | Stock return | Post material return/reversal using supported ERPNext transaction path. | Return sync. |
| ENXT-FR-010 | Batch/serial | Map ERPNext Batch/Serial references without replacing GxP lot/serial identity. | Trace. |
| ENXT-FR-011 | Finished goods | Post finished quantity/reference according to configured manufacturing/accounting model. | Output sync. |
| ENXT-FR-012 | Quality status projection | If ERPNext warehouse/status convention represents quarantine/released stock, mapping is one-way from GxP disposition. | No dual master. |
| ENXT-FR-013 | Production order reference | Read Work Order/Production Plan reference if customer uses ERPNext planning. | Planning source. |
| ENXT-FR-014 | External doc names | Store ERPNext doctype/name/document version/status as external reference. | Traceability. |
| ENXT-FR-015 | Submit/cancel semantics | Adapter understands ERPNext draft/submitted/cancelled document lifecycle and maps external result explicitly. | Correct status. |
| ENXT-FR-016 | Duplicate prevention | GxP command ID persisted in ERPNext integration reference/custom integration field only through controlled integration design, or maintained connector-side if ERP customization avoided. | Idempotency. |
| ENXT-FR-017 | Customization minimization | Prefer connector-side mappings and public APIs; do not require modifying ERPNext core. | Maintainability. |
| ENXT-FR-018 | Custom field policy | If external reference custom fields are required in ERPNext, they are installed by versioned connector migration and documented. | Controlled extension. |
| ENXT-FR-019 | Rate limiting | Bound requests/retries and handle Frappe validation/session errors. | Resilience. |
| ENXT-FR-020 | Attachment refs | Do not copy regulated evidence into ERPNext unless customer explicitly requires; store references where sufficient. | Boundary. |
| ENXT-FR-021 | Reconciliation | Compare purchase receipts/stock entries/work orders with integration ledger. | Integrity. |
| ENXT-FR-022 | Health | Validate API login, required DocTypes/fields, permissions and connector version. | Support. |
| ENXT-FR-023 | Permission scope | ERPNext integration user has least privileges for exact operations. | Security. |
| ENXT-FR-024 | No compliance delegation | ERPNext Workflow/DocStatus cannot substitute for GxP signatures/audit/release. | GxP integrity. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| authenticateERPNext() | Adapter startup | base_url; credential_ref | ERPNextSessionInfo | ERPNEXT_AUTH_FAILED |
| getItem() | Provider caller | external item code | ERPItem | ERPNEXT_ITEM_NOT_FOUND |
| getPurchaseOrder() | Procurement sync | PO name | ERPPurchaseOrder | ERPNEXT_PO_NOT_FOUND |
| createPurchaseOrder() | Procurement service | canonical PurchaseOrderCommand | ExternalTransactionRef | ERPNEXT_VALIDATION_FAILED |
| postGoodsReceipt() | Material Receipt service | GoodsReceiptCommand | ExternalTransactionRef | ERPNEXT_RECEIPT_FAILED |
| postInventoryIssue() | Consumption service | InventoryIssueCommand | ExternalTransactionRef | ERPNEXT_STOCK_ENTRY_FAILED |
| postInventoryReturn() | Material Return service | InventoryReturnCommand | ExternalTransactionRef | ERPNEXT_RETURN_FAILED |
| getInventoryBalance() | Reconciliation | item/warehouse/batch query | ERPInventoryBalance[] | ERPNEXT_BALANCE_QUERY_FAILED |
| getWorkOrder() | Batch planning/import | work_order_name | ERPProductionOrder | ERPNEXT_WORK_ORDER_NOT_FOUND |
| healthCheck() | Scheduler/admin | instance_id | ERPHealth | ERPNEXT_HEALTH_FAILED |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (0 entities owned by this module):
_none declared in the source specifications_

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (0):
_none declared in the source specifications_

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- none declared

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
- API token invalid
- item mapping missing
- supplier not quality-approved even though ERPNext supplier active
- Purchase Receipt timeout after submit
- duplicate retry
- Stock Entry validation error
- warehouse mapping wrong
- Work Order imported
- custom field absent
- ERPNext upgrade changes response field
- connector user overprivileged warning
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-07/Document_49_SPEC-ERP-002_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-ERP-002/<test_case_id>/`.
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
