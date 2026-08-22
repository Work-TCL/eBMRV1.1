# Claude Code prompt — WP-07 / Document 48: Enterprise ERP Integration Architecture & Provider Contract

TASK:
Implement the Enterprise ERP Integration Architecture & Provider Contract module (SPEC-ERP-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_48_Enterprise_ERP_Integration_Architecture_Provider_Contract_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: ERP-ARC-001..030 (30)
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
contracts/openapi/spec-erp-001.yaml
contracts/events/spec-erp-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-erp-001/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| ERP-ARC-001 | Provider abstraction | Expose ERPProvider contracts for master data, procurement, inventory, manufacturing references and distribution references without vendor types in GxP domain. | Vendor-neutral core. |
| ERP-ARC-002 | Instance registry | Register ERP instance, tenant/site scope, vendor/type, environment, auth method, endpoint/version and enabled capabilities. | Multi-customer deployment. |
| ERP-ARC-003 | Capability discovery | Adapter declares supported operations rather than GxP assuming all ERP functions exist. | Safe compatibility. |
| ERP-ARC-004 | Ownership matrix | Every shared business object/field has one authoritative owner and defined projection/mapping owner. | No dual-master ambiguity. |
| ERP-ARC-005 | External mappings | Maintain internal immutable ID ↔ external ERP ID mapping with mapping version/status/source. | Stable identity. |
| ERP-ARC-006 | Material/item sync | ERP item/material data may seed commercial projection; regulated material/spec identity remains GxP-controlled. | Correct ownership. |
| ERP-ARC-007 | Supplier sync | ERP supplier can map to GxP supplier identity but does not imply approved-supplier status. | Quality boundary. |
| ERP-ARC-008 | PO reference | GxP may create/read/revise regulated procurement reference through provider while pricing/terms remain ERP-owned where applicable. | Procurement integration. |
| ERP-ARC-009 | Goods receipt posting | GxP receipt may trigger ERP goods receipt after authoritative GxP receipt commit. | Physical/commercial alignment. |
| ERP-ARC-010 | Quality status posting | GxP material release/reject may map to ERP stock/status representation, but ERP cannot create GxP release. | One-way authority. |
| ERP-ARC-011 | Reservation posting | Batch reservation may create ERP reservation/reference if integration profile requires. | Planning sync. |
| ERP-ARC-012 | Consumption posting | Material consumption posts to ERP after GxP consumption commit with exact transaction reference/idempotency. | No duplicate issue. |
| ERP-ARC-013 | Return posting | Material return posts separately with source GxP transaction reference. | Trace. |
| ERP-ARC-014 | Scrap/destruction posting | Approved GxP scrap/destruction triggers ERP quantity posting without altering GxP disposition. | Boundary. |
| ERP-ARC-015 | Finished goods receipt | Final produced/packaged quantity can be posted to ERP as unreleased/blocked or released stock according to integration profile. | No premature availability. |
| ERP-ARC-016 | Release availability | Final QA release event may move ERP stock to available/released state through configured mapping. | Commercial availability. |
| ERP-ARC-017 | Production order reference | ERP production/manufacturing order may be imported as planning/source reference; eBMR recipe/batch snapshot remains GxP truth. | MES boundary. |
| ERP-ARC-018 | Warehouse/location mapping | Map sites/warehouses/bins/locations with explicit ownership and allowed direction. | No silent location mismatch. |
| ERP-ARC-019 | UOM mapping | Controlled internal UOM ↔ ERP UOM mapping; incompatible conversions rejected. | Quantity integrity. |
| ERP-ARC-020 | Lot/serial mapping | Preserve ERP lot/serial references while internal genealogy remains authoritative. | Traceability. |
| ERP-ARC-021 | Transaction command ledger | Every outbound ERP command stored with command ID, source GxP event/transaction, payload hash, state and external response/reference. | Reconciliation. |
| ERP-ARC-022 | Inbound event ledger | Every inbound webhook/poll/import event stored/idempotently processed before projections. | Replay safe. |
| ERP-ARC-023 | Async default | Use asynchronous outbox/worker pattern for most ERP writes; synchronous dependency reserved for explicitly required pre-action checks. | Resilience. |
| ERP-ARC-024 | No distributed 2PC | Do not use distributed two-phase commit across GxP and ERP. | Failure isolation. |
| ERP-ARC-025 | Reconciliation | Scheduled and on-demand reconciliation compares expected vs external state with explicit difference type. | Detect drift. |
| ERP-ARC-026 | Failure states | Integration failures never fabricate success; physical/GxP transaction remains separately visible with ERP posting pending/failed. | Truth. |
| ERP-ARC-027 | Manual recovery | Authorized integration admin may retry/remap/reconcile metadata but cannot change regulated transaction content. | Admin boundary. |
| ERP-ARC-028 | Security | Per-instance credentials, TLS, least privilege, secret manager, outbound restrictions and API throttling. | Secure integration. |
| ERP-ARC-029 | Observability | Latency, queue age, failures, duplicates, reconciliation mismatches, vendor throttling and auth-expiry visible. | Operable. |
| ERP-ARC-030 | Version compatibility | Adapter records vendor/API version and contract version used for each exchange when material to investigation. | Reproducible. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| registerERPInstance() | Platform Admin | tenant_id; site_scope; provider_type; endpoint; auth_ref; capabilities | ERPInstance | ERPInstanceRegistered; ERP_INSTANCE_INVALID |
| getCapabilities() | Integration Gateway startup | erp_instance_id | ERPCapabilities | ERPHealthChecked; ERP_UNAVAILABLE |
| resolveExternalMapping() | Any integration operation | internal_type; internal_id; external_system; mapping_context | ExternalMapping | ERP_MAPPING_NOT_FOUND/AMBIGUOUS |
| createExternalMapping() | Controlled sync/admin | internal_id; external_id; entity_type; mapping_source; evidence | ExternalMapping | ExternalMappingCreated; ERP_MAPPING_CONFLICT |
| queueERPCommand() | GxP domain after commit | command_type; source_event_id; source_record; canonical_payload | ERPCommandReceipt | ERPCommandQueued; ERP_CAPABILITY_UNSUPPORTED |
| dispatchERPCommand() | Integration worker | integration_command_id | ERPCommandOutcome | ERPCommandSucceeded/Failed; ERP_TIMEOUT/THROTTLED |
| ingestERPEvent() | Webhook/poller/import | instance_id; external_event_id; payload; source_version | ERPInboundEventReceipt | ERPInboundEventReceived; ERP_EVENT_SCHEMA_INVALID |
| reconcileERPObject() | Scheduled/admin | reconciliation_scope; internal_ref; external_ref | ERPReconciliationResult | ERPReconciliationMismatchDetected |
| retryERPCommand() | Integration Admin/worker | command_id; reason/manual flag | RetryReceipt | ERPCommandRetried |
| cancelPendingERPCommand() | Integration Admin/domain supersession | command_id; reason | CancelReceipt | ERPCommandCancelled |

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
- ERP Instance Registry
- Capability/Health
- Mapping Dashboard
- Command Queue
- Failed/Retry Queue
- Inbound Event Monitor
- Reconciliation Dashboard
- External Reference Drilldown
- Integration Audit

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
Example: GxP material consumption commits, SAP posting fails.

Result:
- GxP consumption remains valid;
- integration command becomes FAILED/RETRY_WAIT;
- batch review can display `ERP_POSTING_PENDING`;
- worker retries;
- reconciliation verifies eventual external reference;
- nobody edits the GxP consumption to “undo” the integration failure unless a true physical/GxP correction transaction is authorized.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- ERP unavailable after GxP commit
- timeout after ERP committed but before response
- duplicate command retry
- stale item mapping
- wrong UOM
- external transaction manually reversed
- adapter version upgrade
- wrong tenant/site mapping
- reconciliation catches missing posting
- integration admin cannot edit GxP transaction
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-07/Document_48_SPEC-ERP-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-ERP-001/<test_case_id>/`.
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
