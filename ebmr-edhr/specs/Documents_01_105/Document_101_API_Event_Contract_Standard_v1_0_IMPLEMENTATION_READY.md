# US eBMR / eDHR Regulated Manufacturing Platform
## Document 101 — API & Event Contract Standard — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-ENG-005  
**Parent Documents:** Documents 01–96  
**Primary Dependencies:** Documents 03, 48–53, 69–75, 90, 97–100  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This specification is itself a control source for Claude Code/Codex. Engineering agents shall not treat it as optional style advice when the requirement is marked mandatory.

For every engineering-control function defined below preserve:

- caller/trigger;
- input type, source and requiredness;
- preconditions;
- authorization/ownership where applicable;
- repository/database/artifact reads;
- repository/database/artifact writes;
- transaction/atomicity boundary;
- output/return type;
- events/evidence;
- stable error codes;
- CI enforcement mechanism;
- positive and negative tests.

If a requirement cannot be implemented because of a conflict with another numbered specification, create a `SPEC_GAP` and stop the conflicting change rather than silently choosing a new architecture.

# Engineering Non-Negotiables

- Never modify or fork Frappe/ERPNext core.
- GxP-authoritative mutations enter through the proprietary Mutation Gateway/domain APIs.
- Frappe/MariaDB projections are not authoritative GxP records.
- No generic CRUD over released/regulated records.
- No direct SQL repair of regulated records outside controlled repair/migration mechanisms.
- No bypass of authorization, SoD, qualification or Part 11 signature requirements.
- No deletion/rewriting of immutable audit/version/evidence history.
- No external side effect inside a database transaction unless a specification explicitly establishes a safe protocol.
- Transactional outbox and idempotency are mandatory where specified.
- Temporal orchestrates; it does not own regulatory truth.
- Redis/search/NATS projections or caches are not GxP truth.
- Regulated calculations use exact decimal/UOM/rounding rules.
- All public contracts, DB migrations and release artifacts are versioned and traceable to requirement IDs.
- Production deployment must match a validated release authorization.
- AI is advisory by default; autonomous regulated decisions are prohibited unless a future separately approved specification explicitly changes that rule.

# 1. Objective

Define stable API/event design, schema/versioning, idempotency, concurrency, errors, compatibility, deprecation and consumer testing for internal and customer integrations.

# 2. Actors / Components

- API Owner
- Event Producer
- Consumer
- Integration Engineer
- Claude Code/Codex
- CI
- Release Manager

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
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

# 4. Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB or repo effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| validateOpenAPIContract() | CI | OpenAPI document; style/security rules | Contract parses | Validates operation IDs, schemas, errors, security, examples and requirement metadata | OpenAPIValidationReport | OpenAPIContractInvalid |
| validateAsyncAPIContract() | CI | AsyncAPI/events; schema registry | Contract parses | Checks event envelope, subjects, owners, consumers, versions, examples | AsyncAPIValidationReport | AsyncAPIContractInvalid |
| classifyContractChange() | CI/Release | old contract; new contract | Both versions available | Computes compatible/additive/breaking/deprecated changes | ContractChangeClassification | BreakingContractDetected |
| resolveContractConsumers() | Contract registry | operation/event ID | Registry current | Returns consumers, versions, criticality, owner | ConsumerInventory | UnknownContractConsumer |
| runConsumerContractTests() | CI | provider candidate; consumer test packs | Test packs registered | Runs provider/consumer compatibility suite | ConsumerContractResult | ConsumerContractFailed |
| validateIdempotencyContract() | CI/design check | mutation operation schema/docs | Operation mutating/retryable | Checks idempotency scope/conflict/status semantics present | IdempotencyContractCheck | IdempotencyContractMissing |
| registerDeprecation() | API Governance | contract/version; replacement; end date; consumers | Owner approved | Creates deprecation record and usage telemetry rule | DeprecationRecord | ContractDeprecated |
| generateContractCatalogue() | Release tooling | all OpenAPI/AsyncAPI/schema sources | Contracts valid | Builds machine/human catalogue with version/owner/requirements | ContractCatalogue | ContractCatalogueGenerated |

# 5. Canonical API Error

```json
{
  "error": {
    "code": "STALE_VERSION",
    "message": "The record has changed.",
    "correlation_id": "uuid",
    "retryable": false,
    "field_errors": []
  }
}
```

# 6. Canonical Event Envelope

```json
{
  "event_id": "uuid",
  "event_type": "BatchStepCompleted",
  "schema_version": "1.0",
  "aggregate": {"type":"Batch","id":"uuid","version":42},
  "tenant_id": "uuid",
  "site_id": "uuid",
  "correlation_id": "uuid",
  "causation_id": "uuid",
  "occurred_at": "2026-08-20T00:00:00Z",
  "payload": {}
}
```

# 7. Compatibility Rules

Usually compatible:
- optional response field addition;
- new endpoint/event type;
- optional request field with server default that does not alter existing behavior.

Usually breaking:
- required field added;
- field removed/renamed/type narrowed;
- semantic meaning changed;
- enum consumer cannot handle new value;
- error/status/retry behavior changed incompatibly;
- event ordering/identity semantics changed.

The compatibility tool flags; owner decides under documented policy.

# 8. Deprecation Lifecycle

```text
ACTIVE → DEPRECATED → END_OF_SUPPORT → DISABLED
```
Disabling an externally used contract requires usage/consumer review and customer release communication where applicable.

# 9. Mandatory Test / Enforcement Catalogue

- required request field breaking change
- optional response field compatible
- duplicate idempotency key same payload
- same key different payload conflict
- event replay duplicate
- enum evolution
- consumer test failure
- deprecated endpoint telemetry

# 10. Acceptance Criteria

Customer/internal integrations can upgrade safely because every contract has stable semantics, explicit compatibility rules, registered consumers and machine-tested schemas.

# 11. Claude Code / Codex Prohibitions

- Never change contract semantics without version/compatibility review.
- Never use ad-hoc JSON payload not represented by schema.
- Never assume exactly-once broker delivery.
- Never hand-edit generated client as long-term fix.
