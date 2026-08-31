# API & Event Contract Standard

**Derived from:** Document 101 (SPEC-ENG-005) — controlled source in `specs/`
**Purpose:** Contract authoring, versioning and compatibility rules.
**Requirements:** CTR-FR-001..036 (36)

> This file is the working engineering standard. The controlled source is Document 101; where the two
> differ, the specification wins and this file is corrected.

## Requirements

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

## Enforcement

See `docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md`,
`docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md` and `.github/workflows/ci.yml`.

## Tests

- required request field breaking change
- optional response field compatible
- duplicate idempotency key same payload
- same key different payload conflict
- event replay duplicate
- enum evolution
- consumer test failure
- deprecated endpoint telemetry
