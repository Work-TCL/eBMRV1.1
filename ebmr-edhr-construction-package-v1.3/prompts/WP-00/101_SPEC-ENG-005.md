# Claude Code prompt — WP-00 / Document 101: API & Event Contract Standard

TASK:
Implement the API & Event Contract Standard module (SPEC-ENG-005) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_101_API_Event_Contract_Standard_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: CTR-FR-001..036 (36)
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
- `tooling` and its tests
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
tooling/src/            # domain services, command handlers, repositories
tooling/migrations/     # owned entities only
tooling/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-eng-005.yaml
contracts/events/spec-eng-005/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-eng-005/
```

REQUIREMENTS TO IMPLEMENT (36):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| CTR-FR-001 | Contract-first | Public/cross-service APIs/events defined in version-controlled OpenAPI/AsyncAPI/JSON Schema before or with implementation. | Stable contract. |
| CTR-FR-002 | Operation IDs | Every API operation has stable unique operationId used in traceability/client generation. | Identity. |
| CTR-FR-003 | Event names | Every event has stable semantic type and schema version; transport subject is not business identity. | Clarity. |
| CTR-FR-004 | Typed schemas | Request/response/event payloads explicitly typed with required/optional/null semantics. | Interoperability. |
| CTR-FR-005 | Strict input | Unknown dangerous fields rejected according to endpoint schema policy. | Mass assignment defense. |
| CTR-FR-006 | Error envelope | Stable error code/status/retryability/correlation contract documented. | Consumer behavior. |
| CTR-FR-007 | HTTP semantics | Use consistent status codes; business rejection distinguishable from transport/server failure. | Predictability. |
| CTR-FR-008 | Idempotency | Retryable mutations define idempotency key scope, reuse semantics and conflict behavior. | Safe retries. |
| CTR-FR-009 | Optimistic concurrency | Commands updating versioned aggregates define expected version/precondition behavior. | No lost update. |
| CTR-FR-010 | Correlation | Correlation/causation/request IDs propagated across service/event/integration boundaries. | Traceability. |
| CTR-FR-011 | Tenant/site scope | Contract carries or derives trusted scope; untrusted caller tenant field cannot override authenticated scope. | Isolation. |
| CTR-FR-012 | Pagination | Large lists use bounded cursor/keyset pagination and stable ordering. | Performance. |
| CTR-FR-013 | Filtering | Allowed filters/sorts documented and bounded. | Abuse prevention. |
| CTR-FR-014 | Time | Contract timestamps RFC3339/ISO 8601 with timezone/UTC semantics. | Chronology. |
| CTR-FR-015 | Decimal | Regulated decimals serialized as canonical string/structured decimal where precision loss in JSON number is possible. | Accuracy. |
| CTR-FR-016 | UOM | Quantity contracts carry value/UOM and optional precision/source. | Semantics. |
| CTR-FR-017 | Enums | Unknown/future enum behavior planned; breaking enum changes versioned. | Compatibility. |
| CTR-FR-018 | PII/secrets | Contracts minimize sensitive fields; credentials never returned/logged. | Security. |
| CTR-FR-019 | Evidence refs | Large evidence transmitted by controlled reference/hash, not embedded base64 by default. | Scale. |
| CTR-FR-020 | Compatibility | Additive compatible changes preferred; breaking changes require new major/version route/event schema. | Consumer safety. |
| CTR-FR-021 | Deprecation | Deprecated contract has announcement, telemetry, replacement, end date and customer impact plan. | Lifecycle. |
| CTR-FR-022 | Consumer inventory | Known internal/external consumers registered before breaking change. | Risk control. |
| CTR-FR-023 | Consumer contract tests | Critical consumers/providers have automated compatibility tests. | Assurance. |
| CTR-FR-024 | Generated clients | Generated clients originate from approved contract version and are not hand-forked. | Consistency. |
| CTR-FR-025 | Webhook contracts | Auth/signature/replay window/idempotency/retries/ack semantics explicit. | Integration security. |
| CTR-FR-026 | Async delivery | Event consumers assume at-least-once/duplicates and define ordering/replay handling. | Correctness. |
| CTR-FR-027 | Event envelope | Event ID/type/schema/aggregate/version/tenant/site/correlation/causation/timestamps mandatory. | Stable messaging. |
| CTR-FR-028 | No hidden side effects | API operation documents domain mutation/events/external downstream effects. | Reviewability. |
| CTR-FR-029 | Timeout/retry guidance | Client contract documents safe retry behavior; non-idempotent ambiguity handled via status/reconciliation endpoint. | Reliability. |
| CTR-FR-030 | Long operations | Use asynchronous job/workflow resource rather than holding request indefinitely. | Scale. |
| CTR-FR-031 | Contract ownership | Each API/event has owning service/team and change approver. | Governance. |
| CTR-FR-032 | Requirement trace | Operation/event schema maps source requirement IDs. | Validation. |
| CTR-FR-033 | Security scopes | Auth mechanism and required policy/action scopes documented in contract metadata. | Security. |
| CTR-FR-034 | Rate/resource limits | Contract documents quotas/size limits where consumer behavior depends on them. | Operability. |
| CTR-FR-035 | Examples | Examples must conform to schema and use synthetic data; CI validates examples. | Documentation quality. |
| CTR-FR-036 | No undocumented endpoint | Production endpoints/events must appear in inventory/contract unless explicitly internal runtime health mechanism. | Attack surface. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| validateOpenAPIContract() | CI | OpenAPI document; style/security rules | OpenAPIValidationReport | OpenAPIContractInvalid |
| validateAsyncAPIContract() | CI | AsyncAPI/events; schema registry | AsyncAPIValidationReport | AsyncAPIContractInvalid |
| classifyContractChange() | CI/Release | old contract; new contract | ContractChangeClassification | BreakingContractDetected |
| resolveContractConsumers() | Contract registry | operation/event ID | ConsumerInventory | UnknownContractConsumer |
| runConsumerContractTests() | CI | provider candidate; consumer test packs | ConsumerContractResult | ConsumerContractFailed |
| validateIdempotencyContract() | CI/design check | mutation operation schema/docs | IdempotencyContractCheck | IdempotencyContractMissing |
| registerDeprecation() | API Governance | contract/version; replacement; end date; consumers | DeprecationRecord | ContractDeprecated |
| generateContractCatalogue() | Release tooling | all OpenAPI/AsyncAPI/schema sources | ContractCatalogue | ContractCatalogueGenerated |

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
- required request field breaking change
- optional response field compatible
- duplicate idempotency key same payload
- same key different payload conflict
- event replay duplicate
- enum evolution
- consumer test failure
- deprecated endpoint telemetry
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-00/Document_101_SPEC-ENG-005_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-ENG-005/<test_case_id>/`.
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
