# API and event contracts

**Purpose:** API and event contracts for the eBMR/eDHR platform.
**Applicable paths/modules:** see `docs/generated/17_REPOSITORY_STRUCTURE.md`; this rule applies to every
service, the Frappe app, edge and integration code unless a narrower scope is stated below.
**Source documents:** Document 101 (SPEC-ENG-005), Document 73 (SPEC-DATA-005), Document 53 (SPEC-ERP-006), Document 74 (SPEC-DATA-006)
**Source requirement IDs:** CTR-FR-001..036 (36); EVT-FR-001..030 (30); INT-FR-001..030 (30); TMP-FR-001..030 (30)

---

## Required implementation pattern

Contract-first: OpenAPI 3.1 / AsyncAPI / JSON Schema committed **before** implementation (Document 113).
Canonical command envelope, mutation receipt, error response and event envelope are mandatory.
`additionalProperties: false` on command payloads. Decimal quantities transported as strings with a UOM.
Every schema carries `x-requirement-ids`.

## Forbidden patterns

- endpoint without a committed schema
- error branching on message text
- state-changing endpoint without `idempotency_key` and `expected_version`
- two producers for one event type
- new public endpoint in a module listed in Document 113 §6
- breaking change without a `schema_version` bump

## Required tests

contract test per operation including every declared error; extra-field rejection; duplicate submission
(same key, and same key with different payload); stale version; consumer replay by `event_id`;
out-of-order delivery; additive change does not break existing consumers.


## Source requirements (extract)

| ID | Requirement | Required behaviour |
|---|---|---|
| CTR-FR-001 | Contract-first | Public/cross-service APIs/events defined in version-controlled OpenAPI/AsyncAPI/JSON Schema before or with implementation. |
| CTR-FR-002 | Operation IDs | Every API operation has stable unique operationId used in traceability/client generation. |
| CTR-FR-003 | Event names | Every event has stable semantic type and schema version; transport subject is not business identity. |
| CTR-FR-004 | Typed schemas | Request/response/event payloads explicitly typed with required/optional/null semantics. |
| CTR-FR-005 | Strict input | Unknown dangerous fields rejected according to endpoint schema policy. |
| CTR-FR-006 | Error envelope | Stable error code/status/retryability/correlation contract documented. |
| CTR-FR-007 | HTTP semantics | Use consistent status codes; business rejection distinguishable from transport/server failure. |
| CTR-FR-008 | Idempotency | Retryable mutations define idempotency key scope, reuse semantics and conflict behavior. |
| CTR-FR-009 | Optimistic concurrency | Commands updating versioned aggregates define expected version/precondition behavior. |
| CTR-FR-010 | Correlation | Correlation/causation/request IDs propagated across service/event/integration boundaries. |
| CTR-FR-011 | Tenant/site scope | Contract carries or derives trusted scope; untrusted caller tenant field cannot override authenticated scope. |
| CTR-FR-012 | Pagination | Large lists use bounded cursor/keyset pagination and stable ordering. |
| CTR-FR-013 | Filtering | Allowed filters/sorts documented and bounded. |
| CTR-FR-014 | Time | Contract timestamps RFC3339/ISO 8601 with timezone/UTC semantics. |
| CTR-FR-015 | Decimal | Regulated decimals serialized as canonical string/structured decimal where precision loss in JSON number is possible. |
| CTR-FR-016 | UOM | Quantity contracts carry value/UOM and optional precision/source. |
| CTR-FR-017 | Enums | Unknown/future enum behavior planned; breaking enum changes versioned. |
| CTR-FR-018 | PII/secrets | Contracts minimize sensitive fields; credentials never returned/logged. |
| CTR-FR-019 | Evidence refs | Large evidence transmitted by controlled reference/hash, not embedded base64 by default. |
| CTR-FR-020 | Compatibility | Additive compatible changes preferred; breaking changes require new major/version route/event schema. |
| CTR-FR-021 | Deprecation | Deprecated contract has announcement, telemetry, replacement, end date and customer impact plan. |
| CTR-FR-022 | Consumer inventory | Known internal/external consumers registered before breaking change. |
| CTR-FR-023 | Consumer contract tests | Critical consumers/providers have automated compatibility tests. |
| CTR-FR-024 | Generated clients | Generated clients originate from approved contract version and are not hand-forked. |
| CTR-FR-025 | Webhook contracts | Auth/signature/replay window/idempotency/retries/ack semantics explicit. |
| CTR-FR-026 | Async delivery | Event consumers assume at-least-once/duplicates and define ordering/replay handling. |
| CTR-FR-027 | Event envelope | Event ID/type/schema/aggregate/version/tenant/site/correlation/causation/timestamps mandatory. |
| CTR-FR-028 | No hidden side effects | API operation documents domain mutation/events/external downstream effects. |
| CTR-FR-029 | Timeout/retry guidance | Client contract documents safe retry behavior; non-idempotent ambiguity handled via status/reconciliation endpoint. |
| CTR-FR-030 | Long operations | Use asynchronous job/workflow resource rather than holding request indefinitely. |
| CTR-FR-031 | Contract ownership | Each API/event has owning service/team and change approver. |
| CTR-FR-032 | Requirement trace | Operation/event schema maps source requirement IDs. |
| CTR-FR-033 | Security scopes | Auth mechanism and required policy/action scopes documented in contract metadata. |
| CTR-FR-034 | Rate/resource limits | Contract documents quotas/size limits where consumer behavior depends on them. |
| CTR-FR-035 | Examples | Examples must conform to schema and use synthetic data; CI validates examples. |
| CTR-FR-036 | No undocumented endpoint | Production endpoints/events must appear in inventory/contract unless explicitly internal runtime health mechanism. |
| EVT-FR-001 | Canonical event envelope | Every event has event_id, type, schema version, aggregate id/version, tenant/site, correlation/causation, occurred_at and payload. |
| EVT-FR-002 | Transactional outbox | Authoritative GxP event inserted in same PostgreSQL transaction as domain state/audit. |
| EVT-FR-003 | Outbox publisher | Publisher reads committed pending events and publishes to NATS/JetStream idempotently. |
| EVT-FR-004 | Publish acknowledgement | Outbox marked published only after broker acknowledgement according to configured durable stream semantics. |

## SPEC_GAP triggers

Raise a SPEC_GAP rather than deciding, if you encounter: a missing signature/authorization/retention/
precision value, a conflict between two source documents, an entity without an owner, an event without a
producer, or any requirement that would need a regulated behaviour you cannot trace to
Document 101, Document 73, Document 53, Document 74 or Documents 106–115.
