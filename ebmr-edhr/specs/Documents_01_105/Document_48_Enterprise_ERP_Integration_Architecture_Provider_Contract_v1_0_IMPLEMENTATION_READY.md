# US eBMR / eDHR Regulated Manufacturing Platform
## Document 48 — Enterprise ERP Integration Architecture & Provider Contract — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-ERP-001  
**Parent Documents:** Documents 01–47  
**Primary Dependencies:** Documents 18–22, 43–47; Integration Gateway; GxP Mutation Gateway  
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

Define the vendor-neutral ERP integration architecture, source-of-truth boundaries, provider interfaces, command/event ledgers and transaction/reconciliation behavior for ERPNext, SAP, Oracle, Dynamics and customer ERPs.

# 2. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
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

# 3. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| registerERPInstance() | Platform Admin | tenant_id; site_scope; provider_type; endpoint; auth_ref; capabilities | Admin authorized; secret reference valid; provider installed | Stores ERP instance config in integration config store; no GxP business mutation | ERPInstance | ERPInstanceRegistered; ERP_INSTANCE_INVALID |
| getCapabilities() | Integration Gateway startup | erp_instance_id | Instance active | Calls adapter capability descriptor/health; caches supported operations | ERPCapabilities | ERPHealthChecked; ERP_UNAVAILABLE |
| resolveExternalMapping() | Any integration operation | internal_type; internal_id; external_system; mapping_context | Mapping exists/effective or creation policy allows | Reads mapping table; no automatic guessing by name | ExternalMapping | ERP_MAPPING_NOT_FOUND/AMBIGUOUS |
| createExternalMapping() | Controlled sync/admin | internal_id; external_id; entity_type; mapping_source; evidence | Uniqueness and ownership rules satisfied | Inserts versioned mapping; audits source | ExternalMapping | ExternalMappingCreated; ERP_MAPPING_CONFLICT |
| queueERPCommand() | GxP domain after commit | command_type; source_event_id; source_record; canonical_payload | Source GxP transaction committed; capability supported | Creates integration_command + payload hash + idempotency key in Integration Gateway DB/outbox | ERPCommandReceipt | ERPCommandQueued; ERP_CAPABILITY_UNSUPPORTED |
| dispatchERPCommand() | Integration worker | integration_command_id | Command pending/retry-due; adapter healthy | Calls provider; stores attempt/response; never changes GxP source transaction | ERPCommandOutcome | ERPCommandSucceeded/Failed; ERP_TIMEOUT/THROTTLED |
| ingestERPEvent() | Webhook/poller/import | instance_id; external_event_id; payload; source_version | Authenticated source; schema known | Durably stores raw event/hash; validates; dispatches projection/reconciliation handler | ERPInboundEventReceipt | ERPInboundEventReceived; ERP_EVENT_SCHEMA_INVALID |
| reconcileERPObject() | Scheduled/admin | reconciliation_scope; internal_ref; external_ref | Mapping available | Fetches expected internal projection and external state; calculates structured differences | ERPReconciliationResult | ERPReconciliationMismatchDetected |
| retryERPCommand() | Integration Admin/worker | command_id; reason/manual flag | Command failed/retryable; payload unchanged | Creates new attempt only; preserves original command | RetryReceipt | ERPCommandRetried |
| cancelPendingERPCommand() | Integration Admin/domain supersession | command_id; reason | Command not externally committed; cancellation authorized | Marks integration command cancelled/superseded; does not reverse GxP event | CancelReceipt | ERPCommandCancelled |

# 4. Provider Interface

```ts
interface ERPProvider {
  capabilities(): Promise<ERPCapabilities>;
  healthCheck(): Promise<ERPHealth>;

  getItem(ref: ExternalRef): Promise<ERPItem>;
  getSupplier(ref: ExternalRef): Promise<ERPSupplier>;
  getPurchaseOrder(ref: ExternalRef): Promise<ERPPurchaseOrder>;
  createOrUpdatePurchaseOrder?(cmd: PurchaseOrderCommand): Promise<ExternalTransactionRef>;

  postGoodsReceipt?(cmd: GoodsReceiptCommand): Promise<ExternalTransactionRef>;
  postInventoryIssue?(cmd: InventoryIssueCommand): Promise<ExternalTransactionRef>;
  postInventoryReturn?(cmd: InventoryReturnCommand): Promise<ExternalTransactionRef>;
  postInventoryAdjustment?(cmd: InventoryAdjustmentCommand): Promise<ExternalTransactionRef>;
  postFinishedGoodsReceipt?(cmd: FinishedGoodsReceiptCommand): Promise<ExternalTransactionRef>;
  updateStockAvailabilityStatus?(cmd: StockStatusCommand): Promise<ExternalTransactionRef>;

  getInventoryBalance?(query: ERPInventoryQuery): Promise<ERPInventoryBalance[]>;
  getProductionOrder?(ref: ExternalRef): Promise<ERPProductionOrder>;
  getDistributionReferences?(query: DistributionQuery): Promise<ERPDistributionReference[]>;
}
```

Provider contracts use canonical domain DTOs. Vendor SDK/OData types are confined to adapter packages.

# 5. Canonical Outbound Command

```ts
type ERPCommandEnvelope<T> = {
  commandId: string;
  schemaVersion: string;
  tenantId: string;
  siteId: string;
  erpInstanceId: string;
  commandType: string;
  sourceEventId: string;
  sourceRecord: { type: string; id: string; version: number; };
  idempotencyKey: string;
  occurredAt: string;
  payload: T;
};
```

# 6. Integration Command Ledger

`integration_command`:
```text
id uuid PK
erp_instance_id uuid
command_type varchar
source_event_id uuid
source_record_type/id/version
payload_json jsonb
payload_hash char(64)
idempotency_key varchar UNIQUE
state PENDING|IN_PROGRESS|SUCCEEDED|FAILED|RETRY_WAIT|CANCELLED
attempt_count int
next_attempt_at timestamptz
external_ref jsonb
last_error jsonb
created_at/updated_at
```

`integration_attempt`:
- command ID
- attempt number
- started/completed
- request metadata hash
- HTTP/vendor status
- external correlation/reference
- error category
- retryable flag

# 7. Ownership Matrix

| Object / Field | Authoritative owner | ERP usage |
|---|---|---|
| Product regulated version | GxP | mapped item/product reference |
| Material spec version | GxP | mapped item/material |
| Supplier quality approval | GxP | supplier reference only |
| Price/payment/tax | ERP | not GxP truth |
| GxP material quality status | GxP | projected stock/status if configured |
| Accounting inventory value | ERP | no GxP ownership |
| Physical regulated consumption | GxP | posted as ERP movement |
| Final QA release | GxP | projected ERP availability |
| Production order | ERP/Planning | source/reference only |
| Batch record | GxP | reference/status projection only |
| Distribution shipment | ERP/WMS | imported reference for genealogy/recall |

# 8. Transaction Pattern

```text
Physical / Regulated Action
        ↓
GxP PostgreSQL transaction
        ├ business record
        ├ audit
        └ outbox
             ↓
      Integration Command
             ↓
         ERP Adapter
             ↓
        ERP transaction
             ↓
 response/reference/reconciliation
```

No distributed 2PC.

# 9. Failure Semantics

Example: GxP material consumption commits, SAP posting fails.

Result:
- GxP consumption remains valid;
- integration command becomes FAILED/RETRY_WAIT;
- batch review can display `ERP_POSTING_PENDING`;
- worker retries;
- reconciliation verifies eventual external reference;
- nobody edits the GxP consumption to “undo” the integration failure unless a true physical/GxP correction transaction is authorized.

# 10. UI

- ERP Instance Registry
- Capability/Health
- Mapping Dashboard
- Command Queue
- Failed/Retry Queue
- Inbound Event Monitor
- Reconciliation Dashboard
- External Reference Drilldown
- Integration Audit

# 11. Stable Errors

`ERP_INSTANCE_INVALID`, `ERP_CAPABILITY_UNSUPPORTED`, `ERP_MAPPING_NOT_FOUND`, `ERP_MAPPING_CONFLICT`, `ERP_AUTH_FAILED`, `ERP_TIMEOUT`, `ERP_THROTTLED`, `ERP_VALIDATION_REJECTED`, `ERP_EXTERNAL_CONFLICT`, `ERP_RECONCILIATION_MISMATCH`.

# 12. Tests

- ERP unavailable after GxP commit;
- timeout after ERP committed but before response;
- duplicate command retry;
- stale item mapping;
- wrong UOM;
- external transaction manually reversed;
- adapter version upgrade;
- wrong tenant/site mapping;
- reconciliation catches missing posting;
- integration admin cannot edit GxP transaction.

# 13. Acceptance

The platform can swap ERP providers without changing Batch, Materials, QC, QMS or Release domain code and can prove every external posting back to one immutable GxP source event/transaction.

# 14. Claude Code Prohibitions

- Never import SAP/Oracle/Dynamics/ERPNext SDK types into GxP domain packages.
- Never directly update GxP PostgreSQL from ERP callbacks.
- Never treat ERP stock “unrestricted/available” as proof of GxP Quality release.
- Never roll back a committed GxP physical transaction because the ERP API is down.
