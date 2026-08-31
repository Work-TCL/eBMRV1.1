# US eBMR / eDHR Regulated Manufacturing Platform
## Document 113 — Contract Completion Standard: Schemas, Error Codes, Idempotency & Exposure Boundaries — v1.0 APPROVED

**Specification ID:** SPEC-ENG-009
**Status:** APPROVED v1.0 (construction baseline) — approvers of record: Platform Architect and Contract Owner
**Closes:** SG-012, SG-013, SG-014, SG-018
**Approval:** Approved by the Project Owner during construction review on 2026-08-21. A formal Part 11 signature record must be captured in the QMS against this version before validated release; the approval block below is the record of the construction decision.

**Primary Dependencies:** Document 101 (API/event contract standard), Document 03 (MUT-FR-005/010/021/025/030), Document 102 (testing), Document 73 (outbox/bus)

---

# 0. Why this document exists

The baseline declares 497 API operations and 484 event types by name and path, but field-level request/response and payload schemas exist for only a handful. 69 of 103 module specifications declare no stable error codes. Ten specifications expose mutation APIs without stating idempotency behaviour. Fourteen declare neither an API nor an event surface, leaving their exposure boundary unstated — exactly where an implementation agent invents an endpoint or a direct database write.

# 1. Contract-first rule

```text
No implementation of an operation or event may be merged before:
  1. its schema exists in contracts/ (OpenAPI 3.1 / AsyncAPI / JSON Schema),
  2. its error codes exist in the registry,
  3. its idempotency and expected-version behaviour are declared,
  4. its consumers are listed,
  5. a contract test exists for the happy path and each declared error.
```

Schemas are authored **per work package**, immediately before implementing that package — not all 981 contracts up front, and never generated from finished code.

# 2. Canonical envelopes

## Command request (state-changing)
```json
{
  "command_id": "uuid",
  "command_type": "CompleteBatchStep",
  "schema_version": "1.0",
  "tenant_id": "uuid",
  "site_id": "uuid",
  "aggregate_type": "Batch",
  "aggregate_id": "uuid",
  "expected_version": 44,
  "idempotency_key": "uuid-or-source-key",
  "requested_at": "2026-08-20T10:00:00Z",
  "reason": null,
  "payload": {}
}
```

## Mutation receipt (response)
```json
{
  "command_id": "uuid", "aggregate_id": "uuid", "previous_version": 44, "resulting_version": 45,
  "decision": "COMMITTED", "audit_event_id": "uuid", "signature_ids": ["uuid"],
  "record_hash": {"algorithm": "SHA-256", "digest": "..."},
  "correlation_id": "uuid", "committed_at_utc": "...", "projection_status": "PENDING"
}
```

## Error response
```json
{
  "error_code": "STALE_VERSION",
  "message": "human readable, localizable, never parsed by clients",
  "correlation_id": "uuid",
  "details": {"expected_version": 44, "current_version": 46}
}
```

## Event envelope
```json
{
  "event_id": "uuid", "event_type": "BatchStepCompleted", "schema_version": "1.0",
  "tenant_id": "uuid", "site_id": "uuid", "aggregate_type": "Batch", "aggregate_id": "uuid",
  "aggregate_version": 45, "occurred_at_utc": "...", "correlation_id": "uuid",
  "causation_id": "uuid", "payload": {}
}
```

# 3. Field derivation rules (closes SG-013)

| Rule | Requirement |
|---|---|
| F1 | Every payload field maps to a field in the owning entity schema or to a declared computed value. No orphan fields. |
| F2 | Regulated numeric values are transported as decimal **strings** with an explicit UOM field (Document 110). |
| F3 | Timestamps are RFC 3339 UTC with `Z`; local time is never transported as authoritative. |
| F4 | Identifiers are UUID or the entity's declared business identifier type; never integers derived from row order. |
| F5 | Actor identity is never accepted from a payload (MUT-FR-002). |
| F6 | `additionalProperties: false` on every command payload schema (MUT-FR-005). |
| F7 | Enumerations are closed and versioned; adding a value is a minor version, removing one is breaking. |
| F8 | Event payloads carry references and the minimum necessary data; never PII beyond policy (Document 67). |
| F9 | Every schema declares `x-requirement-ids` linking to source requirements for traceability. |
| F10 | Compatibility: additive optional fields are minor; required-field, type, semantic or enum-removal changes require a new `schema_version`. |

# 4. Error code taxonomy (closes SG-012)

Platform-wide classes, all modules derive from them:

| Class | Prefix pattern | Examples |
|---|---|---|
| Authentication | `AUTHENTICATION_*`, `TOKEN_*` | `AUTHENTICATION_REQUIRED`, `TOKEN_INVALID` |
| Authorization/scope | `*_SCOPE_DENIED`, `ACTION_NOT_AUTHORIZED`, `SOD_*`, `QUALIFICATION_*` | `TENANT_SCOPE_DENIED`, `SOD_CONFLICT` |
| Schema/validation | `SCHEMA_*`, `COMMAND_*`, `*_REQUIRED`, `*_INVALID` | `SCHEMA_INVALID`, `REASON_REQUIRED` |
| State/domain | `STATE_TRANSITION_INVALID`, `*_INELIGIBLE`, `*_INCOMPLETE`, `*_EXPIRED` | `RESOURCE_INELIGIBLE` |
| Concurrency/idempotency | `STALE_VERSION`, `EXPECTED_VERSION_REQUIRED`, `IDEMPOTENCY_CONFLICT`, `REPLAY_DETECTED` | — |
| Signature | `SIGNATURE_*` | `SIGNATURE_REQUIRED`, `SIGNATURE_STALE` |
| Rules/calculation | `RULE_FAILED`, `PRECISION_*`, `UOM_*`, `DIVISION_UNDEFINED` | — |
| Dependency/system | `DEPENDENCY_UNAVAILABLE`, `SYSTEM_ERROR`, `SOURCE_NOT_REGISTERED` | — |

**Module derivation rule.** Each module defines codes only for conditions its domain owns, in the form `<DOMAIN_NOUN>_<CONDITION>` (e.g. `CONTAINMENT_REQUIRED`, `DISPOSITION_REQUIRED`). Reusing a platform code with different semantics is prohibited. Documents currently without codes (05, 06, 08, 09, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22, 23, 43, 45, 46 …) inherit the platform classes and must publish their domain codes in the same PR as their first endpoint.

# 5. Idempotency and replay (closes SG-014)

| Rule | Requirement |
|---|---|
| I1 | Every state-changing operation accepts `idempotency_key`; retries return the original receipt without a second regulated event (MUT-FR-010). |
| I2 | Key derivation: client-generated UUID for UI actions; `source_system + source_event_id` for integration and edge callers. |
| I3 | Idempotency records persist key, actor/source, command hash, resulting command id and version. |
| I4 | Same key + different payload hash → `IDEMPOTENCY_CONFLICT`, never a silent second write. |
| I5 | Retention of idempotency records is at least the longest retry/reconciliation window of any consumer, minimum 30 days. |
| I6 | Event consumers are idempotent by `event_id` and tolerate out-of-order delivery within an aggregate. |
| I7 | Documents 26, 28, 29, 30, 31, 32, 33, 34, 36, 37 adopt I1–I5 for all their mutation endpoints; their `POST` operations are duplicate-capable by nature (double click, retried integration callback). |

# 6. Exposure boundaries (closes SG-018)

| Doc | Module | Exposure boundary |
|---|---|---|
| 44 | SPEC-EDGE-002 | Exposed through the Document 43 Edge Gateway runtime API; drivers are plugins, not a contract surface. |
| 45 | SPEC-EDGE-003 | Exposed through the Document 43 gateway upload/telemetry API; buffering is internal runtime behaviour. |
| 46 | SPEC-EDGE-004 | Exposed through the Document 43 gateway peripheral API and Document 21/16 domain APIs. |
| 47 | SPEC-EDGE-005 | Exposed through the Document 43 gateway acquisition API; command boundary enforced by Document 03. |
| 48 | SPEC-ERP-001 | Architecture and ownership rules; realised through the Document 53 integration gateway contracts. |
| 49 | SPEC-ERP-002 | Adapter implementation behind the Document 48/53 provider contract. |
| 50 | SPEC-ERP-003 | Adapter implementation behind the Document 48/53 provider contract. |
| 51 | SPEC-ERP-004 | Adapter implementations behind the Document 48/53 provider contract. |
| 52 | SPEC-ERP-005 | Master-data sync jobs behind the Document 53 integration gateway; no independent public API. |
| 53 | SPEC-ERP-006 | Owns the integration gateway contract surface for Documents 48–52. |
| 54 | SPEC-DDCP-001 | Profile configuration consumed by Documents 10/11/12/15 APIs; no independent API. |
| 55 | SPEC-DDCP-002 | As Document 54. |
| 56 | SPEC-DDCP-003 | As Document 54. |
| 57 | SPEC-DDCP-004 | As Document 54. |

**Rule.** A module without its own contract surface may not create one during implementation. If a genuine need appears, it is a contract change owned by the hosting module, recorded in the compatibility registry — never an ad-hoc endpoint.

# 7. Functional requirements

| ID | Requirement | Detailed behaviour | Acceptance intent |
|---|---|---|---|
| CTRC-FR-001 | Contract before code | CI rejects an implementation of an operation without a committed schema. | Gate test. |
| CTRC-FR-002 | Envelope conformance | Every command/event uses the canonical envelope. | Contract test. |
| CTRC-FR-003 | Closed payloads | `additionalProperties: false` on command payloads. | Negative test with an extra field. |
| CTRC-FR-004 | Error registry completeness | Every declared error path has a registry code and a test. | Coverage check. |
| CTRC-FR-005 | Idempotency universal | Every state-changing endpoint honours idempotency keys. | Duplicate-submission test per endpoint. |
| CTRC-FR-006 | Expected version universal | Every mutation on a versioned aggregate requires `expected_version`. | Negative test. |
| CTRC-FR-007 | Compatibility registry | Every schema change updates `37_API_EVENT_COMPATIBILITY_REGISTRY.md` with impact and consumer list. | PR check. |
| CTRC-FR-008 | Single producer | Each event type has exactly one producing module. | Registry constraint (see Document 115). |
| CTRC-FR-009 | Traceability | Schemas carry `x-requirement-ids`. | Traceability export. |
| CTRC-FR-010 | No exposure creep | New endpoints in modules listed in §6 are rejected without a contract change record. | Review gate. |

# 8. Test catalogue

1. Contract test per operation: happy path plus every declared error code.
2. Extra-field rejection test per command payload.
3. Duplicate submission with same key → identical receipt, one event.
4. Duplicate submission with same key and different payload → `IDEMPOTENCY_CONFLICT`.
5. Missing `expected_version` → rejected.
6. Stale `expected_version` → `STALE_VERSION`.
7. Event consumer replay: duplicate `event_id` applied twice → single effect.
8. Out-of-order events within an aggregate handled deterministically.
9. Schema evolution: additive optional field does not break an existing consumer contract test.
10. Breaking change without a version bump fails CI.

# 9. Acceptance criteria

1. Every implemented operation and event has a committed schema and contract tests.
2. Error registry contains every code any module can return.
3. Every mutation endpoint proves idempotency and expected-version behaviour by test.
4. No module in §6 has created an independent contract surface.

# 10. Claude Code / Codex prohibitions

- Do not implement an endpoint before its schema exists.
- Do not invent an error code that duplicates a platform class with different meaning.
- Do not return free-text-only errors.
- Do not add a public endpoint to a module listed in §6.
- Do not generate schemas from implementation code.

# 11. Approval block

| Role | Name | Decision | Date | Signature reference |
|---|---|---|---|---|
| Platform Architect |  |  |  |  |
| Contract Owner |  |  |  |  |
