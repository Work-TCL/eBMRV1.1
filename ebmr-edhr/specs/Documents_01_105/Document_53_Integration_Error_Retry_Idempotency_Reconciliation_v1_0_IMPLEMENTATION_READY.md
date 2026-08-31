# US eBMR / eDHR Regulated Manufacturing Platform
## Document 53 — Integration Error Handling, Retry, Idempotency & Reconciliation — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-ERP-006  
**Parent Documents:** Documents 01–47  
**Primary Dependencies:** Documents 43–52; Integration Gateway; Observability/Security  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products (DDCP)  
**Future Profiles:** Medical Devices, Pharmaceuticals  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This specification is intended to be consumed directly by Claude Code, Codex, or a human engineering team.

Before coding this module, the coding agent shall extract:

- requirement IDs;
- module/submodule responsibilities;
- service/class/function catalogue;
- input/output schemas;
- authorization/signature/audit requirements;
- database reads/writes/transaction boundaries;
- API contracts;
- event contracts;
- state machines;
- integration dependencies;
- error codes;
- idempotency/concurrency strategy;
- positive/negative/failure tests;
- requirement-to-test traceability.

For every public/domain function, implementation must explicitly preserve:

1. caller/trigger;
2. input field names, types, requiredness and source;
3. preconditions;
4. authorization/qualification/SoD/signature rules;
5. business validation;
6. database reads;
7. database writes;
8. transaction boundary;
9. output/result;
10. emitted events;
11. consumed events;
12. downstream consumers;
13. stable errors;
14. idempotency/replay behavior;
15. concurrency/version behavior;
16. audit evidence;
17. observability;
18. test obligations.

If a decision would change regulated behavior and is not specified, create a `SPEC_GAP` rather than inventing a rule.

# ERP / GxP Ownership Principles

- ERP owns commercial/financial purchasing, costing, accounting, planning and warehouse/accounting postings according to deployment mode.
- GxP owns regulated material identity/status at use, batch/eDHR execution evidence, QC/QMS, genealogy, signatures, audit and final Quality release/disposition.
- An ERP inventory status is never automatically equivalent to GxP Quality release.
- An ERP production-order completion is never automatically equivalent to GxP batch completion or QA release.
- GxP transaction is committed first for regulated physical actions where GxP is authoritative; ERP posting follows through an idempotent integration command unless a specifically approved synchronous process requires otherwise.
- External ERP identifiers are mappings/references; they do not replace internal immutable GxP IDs.
- No ERP adapter may write directly to GxP PostgreSQL tables.
- All adapters use Integration Gateway contracts, idempotency, reconciliation and explicit source ownership.

# Current Vendor Integration Baseline

Current vendor documentation supports the architectural patterns used here:

- Frappe provides REST/RPC APIs, including resource APIs and whitelisted method calls; ERPNext integration shall use public/supported APIs rather than direct ERPNext database writes.
- SAP S/4HANA currently exposes Product Master APIs such as `API_PRODUCT_SRV` and Material Document APIs such as `API_MATERIAL_DOCUMENT` for inventory/material movements through supported OData/SOAP interfaces.
- Oracle Fusion Cloud SCM exposes REST APIs for inventory quantities, receipts, shipments and inventory transactions.
- Microsoft Dynamics 365 Finance/Supply Chain supports third-party integration through OData/data entities, data-management REST APIs and custom services according to use case/volume.

Official references:
- https://docs.frappe.io/framework/user/en/guides/integration/rest_api
- https://help.sap.com/docs/sap_s4hana_cloud/3c916ef10fc240c9afc594b346ffaf77/ccf66cce781c4a9a988d2553da64ffa5.html
- https://help.sap.com/docs/SAP_S4HANA_CLOUD/3f57e7df4a114edabffe8b2d581a59ed/d4c919581bc30a02e10000000a44147b.html
- https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/fasrp/index.html
- https://learn.microsoft.com/en-us/dynamics365/fin-ops-core/dev-itpro/data-entities/integration-overview

# 1. Objective

Define one consistent integration reliability model across ERP, LIMS, Edge and other enterprise adapters, with explicit error classification, retries, idempotency, uncertain-commit reconciliation, dead-letter handling and human-controlled recovery.

# 2. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| INT-FR-001 | Canonical integration message | All inbound/outbound exchanges have message/command/event ID, source, target, schema, correlation, causation and payload hash. | Trace. |
| INT-FR-002 | Error taxonomy | AUTH, CONFIG, VALIDATION, BUSINESS_REJECT, CONFLICT, RATE_LIMIT, TRANSIENT_NETWORK, SERVER_ERROR, TIMEOUT_UNCERTAIN, SCHEMA, SECURITY, MANUAL_REVIEW. | Consistent handling. |
| INT-FR-003 | Retry classification | Only retryable categories retry automatically; business/validation/config errors require correction/review. | No retry storms. |
| INT-FR-004 | Exponential backoff | Configurable capped backoff + jitter; vendor Retry-After honored where applicable. | Resilience. |
| INT-FR-005 | Maximum attempts | Retry count/time window configurable; exhausted commands enter manual-review/dead-letter. | Bounded. |
| INT-FR-006 | Idempotency key | Every write command has stable idempotency key derived from immutable source event/operation semantics. | No duplicates. |
| INT-FR-007 | Payload hash | Same idempotency key with different payload hash is conflict/integrity incident. | Tamper/drift detection. |
| INT-FR-008 | Uncertain timeout | Timeout after external request may represent committed external transaction; reconcile before replaying create where duplicate risk exists. | Exactly-once effect strategy. |
| INT-FR-009 | External correlation | Store vendor request/job/doc/reference IDs on every successful/uncertain attempt. | Investigability. |
| INT-FR-010 | Inbound dedupe | Unique external event/message ID + source instance and payload hash. | Replay safe. |
| INT-FR-011 | Out-of-order events | Process version/sequence-aware; stale events cannot overwrite newer projection. | Ordering. |
| INT-FR-012 | Dead letter | Retain failed original payload hash/reference, attempts/errors and required next action. | No loss. |
| INT-FR-013 | Manual replay | Authorized replay uses exact original payload unless a new corrected command is explicitly created. | Integrity. |
| INT-FR-014 | Corrected command | Business correction creates new command ID linked to original; never mutate original command payload. | History. |
| INT-FR-015 | Cancellation | Pending command may be cancelled/superseded only before confirmed external commit and with reason. | State clarity. |
| INT-FR-016 | Compensation | External reversal/compensation is a new integration command tied to authorized GxP correction/disposition. | No hidden rollback. |
| INT-FR-017 | Reconciliation types | MISSING_EXTERNAL, EXTRA_EXTERNAL, VALUE_MISMATCH, STATUS_MISMATCH, REFERENCE_MISMATCH, DUPLICATE_EXTERNAL, STALE_MAPPING. | Structured drift. |
| INT-FR-018 | Reconciliation snapshot | Report records source cutoff, query keys, external response refs and mapping versions. | Reproducible. |
| INT-FR-019 | Auto-resolve | Only benign known differences/duplicates may auto-resolve under released rule; quantity/status mismatches require review. | Safe. |
| INT-FR-020 | Integration hold | Critical unresolved integration mismatch can create operational/QA review flag according to module policy. | Risk. |
| INT-FR-021 | SLA/aging | Track oldest pending, retry age, dead-letter age and reconciliation age. | Operations. |
| INT-FR-022 | Circuit breaker | Per-instance breaker protects repeated transient vendor failures without losing queued commands. | Stability. |
| INT-FR-023 | Bulk jobs | Bulk import/export job tracks record-level successes/failures and supports idempotent resume. | Scale. |
| INT-FR-024 | Rate limiting | Per provider/operation quotas configured. | Vendor-safe. |
| INT-FR-025 | Security event | Unexpected payload hash/idempotency conflict/source identity mismatch raises security/data-integrity event. | Detection. |
| INT-FR-026 | Observability | Metrics/logs/traces include correlation IDs but redact sensitive credentials/content. | Support. |
| INT-FR-027 | Audit | Manual retry/remap/cancel/reconcile resolution audited. | Accountability. |
| INT-FR-028 | Retention | Integration ledgers retained long enough to support regulated-record investigation and external reconciliation. | Evidence. |
| INT-FR-029 | Chaos testing | Simulate network partitions, lost responses, duplicates, throttling, partial bulk failure and provider outage. | Reliability. |
| INT-FR-030 | No silent success | UI never displays external posting successful until Integration Gateway has confirmed/reconciled it. | Truth. |

# 3. Claude Code Reliability Function Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| classifyIntegrationError() | Adapter/client | provider response/exception; operation profile | Raw diagnostic captured | Maps to canonical category/code/retryable/uncertain_commit flags | CanonicalIntegrationError | none |
| computeRetryDecision() | Worker | command; canonical error; retry policy; attempt history | Error classified | Returns retry/no-retry, next_attempt_at, reconciliation-first flag | RetryDecision | none |
| scheduleRetry() | Worker | command_id; RetryDecision | Retry allowed and attempts remain | Updates state RETRY_WAIT, next attempt; appends attempt history | RetrySchedule | IntegrationRetryScheduled |
| markDeadLetter() | Worker | command_id; terminal error | No safe automatic retry | Marks MANUAL_REVIEW/DEAD_LETTER; emits alert | DeadLetterReceipt | IntegrationDeadLettered |
| ensureIdempotency() | Outbound handler | idempotency_key; payload_hash; source_event | Key format valid | Checks existing command/external result; same hash returns existing, different hash raises conflict | IdempotencyDecision | IDEMPOTENCY_PAYLOAD_CONFLICT |
| dedupeInboundEvent() | Inbound handler | erp_instance_id; external_event_id; payload_hash | Authenticated source | Unique constraint check; same hash duplicate accepted, different hash security incident | InboundDedupeDecision | INBOUND_EVENT_CONFLICT |
| reconcileUncertainCommit() | Worker | command_id; provider lookup strategy | Command in TIMEOUT_UNCERTAIN or equivalent | Queries external provider for expected effect before deciding retry | UncertainCommitResolution | ExternalCommitFound/NotFound |
| createReconciliationRun() | Scheduler/Admin | instance; reconciliation_type/scope; cutoff | Provider available | Stores run metadata; enumerates expected/internal and external state | ReconciliationRun | ReconciliationStarted |
| recordReconciliationDifference() | Reconciliation processor | run_id; difference type; internal/external evidence | Difference material | Stores structured difference and severity/owner | ReconciliationDifference | ReconciliationMismatchDetected |
| resolveReconciliationDifference() | Integration/Data Owner | difference_id; resolution; reason; correction refs | Authorized; versions current | Marks resolved and optionally queues new correction/sync command | ResolutionReceipt | ReconciliationResolved |
| tripCircuitBreaker() | Worker policy | instance/operation; failure window | Threshold exceeded | Sets breaker OPEN with retry-at; commands stay queued | CircuitBreakerState | ERPIntegrationCircuitOpened |
| closeCircuitBreaker() | Health probe | instance/operation | Successful probes/half-open policy | Sets CLOSED | CircuitBreakerState | ERPIntegrationCircuitClosed |

# 4. Command State Machine

```text
PENDING
  ↓ dispatch
IN_PROGRESS
  ├→ SUCCEEDED
  ├→ RETRY_WAIT → IN_PROGRESS
  ├→ TIMEOUT_UNCERTAIN → RECONCILING
  │                         ├→ SUCCEEDED
  │                         └→ RETRY_WAIT / MANUAL_REVIEW
  ├→ BUSINESS_REJECTED → MANUAL_REVIEW
  └→ DEAD_LETTER

PENDING/RETRY_WAIT → CANCELLED (controlled, only when safe)
```

# 5. Error Contract

```ts
type CanonicalIntegrationError = {
  code: string;
  category:
    | "AUTH" | "CONFIG" | "VALIDATION" | "BUSINESS_REJECT"
    | "CONFLICT" | "RATE_LIMIT" | "TRANSIENT_NETWORK"
    | "SERVER_ERROR" | "TIMEOUT_UNCERTAIN" | "SCHEMA"
    | "SECURITY" | "MANUAL_REVIEW";
  retryable: boolean;
  uncertainCommit: boolean;
  providerCode?: string;
  messageKey: string;
  rawDiagnosticRef?: string;
};
```

# 6. Idempotency Key Rules

Examples:
```text
erp:goods-receipt:{gxp_receipt_id}:{receipt_version}
erp:consume:{inventory_transaction_id}
erp:return:{inventory_transaction_id}
erp:release-status:{release_scope_id}:{release_decision_version}
```

Never use timestamp/random UUID alone as idempotency semantic key for the same business command.

# 7. Uncertain Commit Algorithm

```text
request sent
   ↓
client timeout / connection reset
   ↓
DO NOT blindly resend create
   ↓
provider-specific lookup using external correlation/business keys
   ├→ found expected effect → mark SUCCEEDED
   ├→ definitely absent → retry
   └→ cannot determine → MANUAL_REVIEW / bounded retry policy
```

# 8. Reconciliation Data Model

`reconciliation_run`:
- instance
- object/transaction scope
- cutoff
- started/completed
- adapter version
- mapping versions
- state

`reconciliation_difference`:
- type
- internal reference/version
- external reference/version
- expected values
- observed values
- severity
- state
- owner
- resolution
- correction command refs

# 9. Dashboard

- Queue Overview
- Retry Wait
- Uncertain Commit
- Dead Letter
- Circuit Breakers
- Reconciliation Runs
- Differences
- Manual Resolution Audit
- Vendor Health/Throttle

# 10. Metrics

- commands_pending_total
- commands_failed_total
- command_age_seconds
- retry_attempts_total
- timeout_uncertain_total
- duplicate_prevented_total
- dead_letter_total
- reconciliation_mismatch_total
- circuit_breaker_state
- vendor_latency_seconds

# 11. Tests

- 500 error retry;
- 400 validation no retry;
- 429 Retry-After;
- timeout after vendor commit;
- duplicate idempotency same hash;
- duplicate idempotency different hash;
- inbound duplicate event;
- out-of-order inbound version;
- dead-letter replay;
- corrected new command;
- circuit breaker;
- bulk partial failure;
- reconciliation missing external posting;
- extra external transaction.

# 12. Acceptance

For every external write, the platform can distinguish “not attempted,” “failed safely,” “possibly committed,” “confirmed committed,” and “manual review required,” and can prevent duplicate business effects during retries.

# 13. Claude Code Prohibitions

- Never retry all errors blindly.
- Never mutate original failed command payload to make retry succeed.
- Never mark timeout as failed-with-no-side-effect unless provider reconciliation proves absence.
- Never hide dead-letter items from operational dashboards.
