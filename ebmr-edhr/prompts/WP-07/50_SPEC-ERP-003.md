# Claude Code prompt — WP-07 / Document 50: SAP S/4HANA Adapter Contract

TASK:
Implement the SAP S/4HANA Adapter Contract module (SPEC-ERP-003) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_50_SAP_S4HANA_Adapter_Contract_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: SAP-FR-001..025 (25)
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
contracts/openapi/spec-erp-003.yaml
contracts/events/spec-erp-003/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-erp-003/
```

REQUIREMENTS TO IMPLEMENT (25):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| SAP-FR-001 | SAP instance profile | Support S/4HANA Cloud Public/Private/On-Prem profiles with configured API capabilities/version. | Deployment flexibility. |
| SAP-FR-002 | Auth | OAuth2/mTLS/basic only if approved deployment supports; secrets isolated. | Security. |
| SAP-FR-003 | Product master | Map canonical item/material through supported Product Master APIs such as API_PRODUCT_SRV where applicable. | Master mapping. |
| SAP-FR-004 | Material stock | Read inventory/stock through supported SAP inventory API/profile. | Reconciliation. |
| SAP-FR-005 | Material document | Create/retrieve material movement through supported Material Document API/profile. | Inventory posting. |
| SAP-FR-006 | Goods receipt | Map GxP receipt to correct SAP movement semantics and PO/order refs. | Receipt. |
| SAP-FR-007 | Goods issue | Map material consumption to approved movement code/type profile. | Consumption. |
| SAP-FR-008 | Transfer posting | Map GxP transfer when SAP ownership/profile requires. | Warehouse. |
| SAP-FR-009 | Reversal | Integration reversal is separate SAP transaction; never used to silently erase GxP physical record. | History. |
| SAP-FR-010 | Movement mapping | Movement codes/types stored as configuration, not hardcoded across customers. | Customer-specific. |
| SAP-FR-011 | Plant/storage location | Explicit site ↔ SAP plant/storage-location mapping. | Location integrity. |
| SAP-FR-012 | Material/UOM | Material number/base unit/alternate UOM mapping controlled. | Quantity integrity. |
| SAP-FR-013 | Batch/serial | SAP batch/serial refs mapped to internal IDs, not authoritative genealogy. | Trace. |
| SAP-FR-014 | Production order | Read SAP production/process order reference where customer uses SAP planning/manufacturing. | Planning. |
| SAP-FR-015 | Blocked/released stock | GxP quality release can project to SAP stock/status movement only through configured Quality-approved mapping. | No dual release. |
| SAP-FR-016 | Posting date | Posting/document dates derived per integration/business policy and retained with actual GxP physical occurrence time. | Chronology. |
| SAP-FR-017 | External transaction ref | Store SAP material document/year/item or equivalent transaction keys. | Reconciliation. |
| SAP-FR-018 | OData batch | Adapter may use OData $batch where supported but preserves per-command idempotency/response mapping. | Efficiency. |
| SAP-FR-019 | Error mapping | Map SAP HTTP/OData/business messages to stable integration errors while retaining raw diagnostic. | Support. |
| SAP-FR-020 | CSRF/session handling | Handle required SAP OData CSRF/session mechanics in client layer only. | Correct protocol. |
| SAP-FR-021 | Throttling/retry | Respect API limits and classify retryable vs business errors. | Resilience. |
| SAP-FR-022 | API version profile | Technical service/entity versions captured in adapter configuration. | Compatibility. |
| SAP-FR-023 | Custom BAPI/RFC | Custom/private BAPI/RFC integration allowed only through separate customer adapter profile; not assumed common baseline. | Controlled custom. |
| SAP-FR-024 | Reconciliation | Query material docs/stock by bounded date/object keys and compare expected commands. | Integrity. |
| SAP-FR-025 | No SAP regulatory authority | SAP material document success does not constitute eBMR step completion/QA release. | Boundary. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| getSAPProduct() | Master sync | sap_material_id | ERPItem | SAP_PRODUCT_NOT_FOUND |
| getSAPInventoryBalance() | Reconciliation | plant; storage_location; material; batch? | ERPInventoryBalance[] | SAP_STOCK_QUERY_FAILED |
| postSAPMaterialDocument() | Outbound inventory worker | canonical material movement command | ExternalTransactionRef | SAP_MATERIAL_DOCUMENT_FAILED |
| reverseSAPMaterialDocument() | Authorized correction integration | original external ref; reversal reason; source GxP correction/ref | ExternalTransactionRef | SAP_REVERSAL_FAILED |
| getSAPProductionOrder() | Batch import/planning | production_order_id | ERPProductionOrder | SAP_PRODUCTION_ORDER_NOT_FOUND |
| fetchCSRFSecurityContext() | SAP client | service endpoint | SAPSecurityContext | SAP_CSRF_FAILED |
| mapSAPBusinessError() | SAP client | HTTP status; OData/business message payload | IntegrationError | none |
| reconcileSAPMaterialDocument() | Reconciliation job | command_id; external material doc ref | ReconciliationResult | SAP_RECONCILIATION_MISMATCH |

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
- wrong SAP plant mapping
- wrong movement code configuration
- CSRF failure
- OAuth expiry
- material document POST succeeds then client timeout
- duplicate retry
- business validation error
- reversal after GxP correction
- stock differs from GxP projection
- API service version upgrade
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-07/Document_50_SPEC-ERP-003_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-ERP-003/<test_case_id>/`.
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
