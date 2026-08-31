# Claude Code prompt — WP-07 / Document 51: Oracle Fusion, Dynamics 365 & Custom ERP Adapter Contracts

TASK:
Implement the Oracle Fusion, Dynamics 365 & Custom ERP Adapter Contracts module (SPEC-ERP-004) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_51_Oracle_Dynamics_Custom_ERP_Adapter_Contracts_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: MULTI-FR-001..024 (24)
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
contracts/openapi/spec-erp-004.yaml
contracts/events/spec-erp-004/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-erp-004/
```

REQUIREMENTS TO IMPLEMENT (24):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| MULTI-FR-001 | Adapter families | Provide Oracle Fusion SCM, Dynamics 365 Finance/Supply Chain and Generic Custom ERP implementations behind ERPProvider. | Vendor choice. |
| MULTI-FR-002 | Oracle REST profile | Use Oracle SCM REST resources for inventory/receiving/shipping/product references as configured. | Supported integration. |
| MULTI-FR-003 | Oracle inventory transaction | Map GxP inventory movement to Oracle inventory transaction resource/profile. | Inventory. |
| MULTI-FR-004 | Oracle receipt | Map receipt to supported Oracle receiving transaction/advice/confirmation pattern. | Receipt. |
| MULTI-FR-005 | Oracle lot/serial | Preserve Oracle lot/serial references while GxP genealogy remains authoritative. | Trace. |
| MULTI-FR-006 | Oracle privileges | Service account/API privileges minimized to exact resource operations. | Security. |
| MULTI-FR-007 | Oracle API release | Adapter configuration stores Oracle REST release/profile such as current 26x documentation rather than hardcoding one forever. | Compatibility. |
| MULTI-FR-008 | Dynamics integration pattern | Choose OData/data entities for synchronous CRUD-sized integration, data-management package REST for bulk/asynchronous, or custom services where justified. | Correct pattern. |
| MULTI-FR-009 | Dynamics product entity | Use supported product/item data entities/OData profile when synchronizing commercial item master. | Master mapping. |
| MULTI-FR-010 | Dynamics inventory | Use customer-supported data entities/services for warehouse/inventory transactions and references. | Inventory. |
| MULTI-FR-011 | Dynamics company/legal entity | Every request/mapping carries correct company/legal-entity context. | Tenant semantics. |
| MULTI-FR-012 | Dynamics entity versioning | Entity/custom-service names/fields isolated in adapter profile. | Maintainability. |
| MULTI-FR-013 | Custom REST adapter | Support OpenAPI-described REST endpoints with canonical mapping, auth, timeout, idempotency and reconciliation. | Generic integration. |
| MULTI-FR-014 | Custom SOAP adapter | Optional SOAP/WSDL adapter through isolated connector when legacy ERP requires it. | Legacy. |
| MULTI-FR-015 | Custom file adapter | SFTP/CSV/XML/EDI batch exchange allowed only with manifest, checksum, file identity, acknowledgement and replay rules. | Legacy/batch. |
| MULTI-FR-016 | Custom DB integration | Direct external ERP database read may be supported only read-only under customer-approved adapter; writes to vendor DB prohibited unless vendor-supported integration says otherwise. | Safety. |
| MULTI-FR-017 | Canonical DTO mapping | Vendor/custom fields map to canonical ERP DTOs; no business domain depends on raw vendor names. | Abstraction. |
| MULTI-FR-018 | Capabilities | Each adapter declares exact supported operations and limitations. | No false assumptions. |
| MULTI-FR-019 | External business error | Vendor rejection classified as nonretryable until input/mapping corrected. | Correct retry. |
| MULTI-FR-020 | Transport failure | Network/5xx/timeout/throttle classified retryable based on provider profile. | Resilience. |
| MULTI-FR-021 | Idempotency | Use vendor-provided idempotency/correlation if available plus local command ledger. | No duplicates. |
| MULTI-FR-022 | Reconciliation | Every write-capable custom adapter must implement a read/lookup/reconciliation path; otherwise production write capability is not approved. | Recoverability. |
| MULTI-FR-023 | Contract tests | Adapter certification requires simulator/sandbox contract suite. | Quality. |
| MULTI-FR-024 | No unverified connector | Customer custom adapter cannot be enabled for GxP posting without validation/acceptance profile. | Validated state. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| postOracleInventoryTransaction() | Integration worker | InventoryCommand; oracle_instance | ExternalTransactionRef | ORACLE_INVENTORY_TX_FAILED |
| postOracleReceipt() | Material Receipt integration | GoodsReceiptCommand | ExternalTransactionRef | ORACLE_RECEIPT_FAILED |
| getOracleInventory() | Reconciliation | org/item/subinventory/lot query | ERPInventoryBalance[] | ORACLE_QUERY_FAILED |
| queryDynamicsEntity() | Master/reconciliation | entity_name; company; filter; select | Canonical DTO[] | D365_ENTITY_QUERY_FAILED |
| postDynamicsEntity() | Integration worker | entity_name; company; canonical command | ExternalTransactionRef | D365_POST_FAILED |
| submitDynamicsDataPackage() | Bulk sync worker | package_manifest; file/evidence ref | ExternalJobRef | D365_PACKAGE_FAILED |
| callCustomREST() | Generic adapter | operation_id; canonical request | Canonical/ExternalTransactionRef | CUSTOM_ERP_HTTP_FAILED |
| exchangeCustomFile() | Batch scheduler | file_contract_id; canonical records | ExternalBatchRef | CUSTOM_ERP_FILE_FAILED |
| reconcileCustomWrite() | Reconciliation | command_id; provider-specific lookup keys | ReconciliationResult | CUSTOM_ERP_RECONCILIATION_UNSUPPORTED/MISMATCH |

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
- Oracle privilege missing
- Oracle transaction accepted with partial failed records
- Dynamics wrong company context
- Dynamics OData throttling
- Dynamics data-management job fails after upload
- custom REST timeout after external commit
- custom file duplicate pickup
- custom adapter lacks reconciliation path
- external schema changes
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-07/Document_51_SPEC-ERP-004_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-ERP-004/<test_case_id>/`.
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
