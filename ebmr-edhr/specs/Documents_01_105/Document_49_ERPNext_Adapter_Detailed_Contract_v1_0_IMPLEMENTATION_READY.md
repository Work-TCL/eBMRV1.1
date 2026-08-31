# US eBMR / eDHR Regulated Manufacturing Platform
## Document 49 — ERPNext Adapter Detailed Contract — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-ERP-002  
**Parent Documents:** Documents 01–47  
**Primary Dependencies:** Document 48; Procurement/Materials/Inventory; Frappe/ERPNext  
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

Define the concrete ERPNext adapter while preserving the independent eBMR/GxP application architecture and avoiding ERPNext core modifications.

# 2. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| ENXT-FR-001 | Supported API | Use supported Frappe/ERPNext REST/RPC APIs; direct ERPNext MariaDB access prohibited. | Upgrade-safe boundary. |
| ENXT-FR-002 | Authentication | Token/API-key or approved OAuth/session/service identity profile; credentials per instance. | Secure. |
| ENXT-FR-003 | Item mapping | Map GxP product/material/component IDs to ERPNext Item codes and UOM. | Identity. |
| ENXT-FR-004 | Supplier mapping | Map supplier but never infer Approved Supplier status from ERPNext Supplier enabled state. | Quality boundary. |
| ENXT-FR-005 | Warehouse mapping | Map GxP site/warehouse/location to ERPNext Warehouse where integration mode requires. | Inventory sync. |
| ENXT-FR-006 | Purchase Order | Read/create/update PO through canonical provider when native procurement/ERP mode configured. | Procurement. |
| ENXT-FR-007 | Purchase Receipt | Post goods receipt after GxP receipt transaction, preserving PO/item/lot refs. | Receipt sync. |
| ENXT-FR-008 | Stock Entry issue | Post material issue/consumption through Stock Entry or supported ERPNext transaction abstraction. | Inventory posting. |
| ENXT-FR-009 | Stock return | Post material return/reversal using supported ERPNext transaction path. | Return sync. |
| ENXT-FR-010 | Batch/serial | Map ERPNext Batch/Serial references without replacing GxP lot/serial identity. | Trace. |
| ENXT-FR-011 | Finished goods | Post finished quantity/reference according to configured manufacturing/accounting model. | Output sync. |
| ENXT-FR-012 | Quality status projection | If ERPNext warehouse/status convention represents quarantine/released stock, mapping is one-way from GxP disposition. | No dual master. |
| ENXT-FR-013 | Production order reference | Read Work Order/Production Plan reference if customer uses ERPNext planning. | Planning source. |
| ENXT-FR-014 | External doc names | Store ERPNext doctype/name/document version/status as external reference. | Traceability. |
| ENXT-FR-015 | Submit/cancel semantics | Adapter understands ERPNext draft/submitted/cancelled document lifecycle and maps external result explicitly. | Correct status. |
| ENXT-FR-016 | Duplicate prevention | GxP command ID persisted in ERPNext integration reference/custom integration field only through controlled integration design, or maintained connector-side if ERP customization avoided. | Idempotency. |
| ENXT-FR-017 | Customization minimization | Prefer connector-side mappings and public APIs; do not require modifying ERPNext core. | Maintainability. |
| ENXT-FR-018 | Custom field policy | If external reference custom fields are required in ERPNext, they are installed by versioned connector migration and documented. | Controlled extension. |
| ENXT-FR-019 | Rate limiting | Bound requests/retries and handle Frappe validation/session errors. | Resilience. |
| ENXT-FR-020 | Attachment refs | Do not copy regulated evidence into ERPNext unless customer explicitly requires; store references where sufficient. | Boundary. |
| ENXT-FR-021 | Reconciliation | Compare purchase receipts/stock entries/work orders with integration ledger. | Integrity. |
| ENXT-FR-022 | Health | Validate API login, required DocTypes/fields, permissions and connector version. | Support. |
| ENXT-FR-023 | Permission scope | ERPNext integration user has least privileges for exact operations. | Security. |
| ENXT-FR-024 | No compliance delegation | ERPNext Workflow/DocStatus cannot substitute for GxP signatures/audit/release. | GxP integrity. |

# 3. Claude Code Adapter Function Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| authenticateERPNext() | Adapter startup | base_url; credential_ref | Credential secret resolves; TLS valid | Establishes API auth context/test request | ERPNextSessionInfo | ERPNEXT_AUTH_FAILED |
| getItem() | Provider caller | external item code | Authenticated; read permission | GET resource Item; maps to canonical ERPItem | ERPItem | ERPNEXT_ITEM_NOT_FOUND |
| getPurchaseOrder() | Procurement sync | PO name | Read permission | GET Purchase Order + required lines; maps canonical PO | ERPPurchaseOrder | ERPNEXT_PO_NOT_FOUND |
| createPurchaseOrder() | Procurement service | canonical PurchaseOrderCommand | Provider capability enabled; mappings/UOM/supplier valid | POST Purchase Order draft/submission per integration profile; stores external ref | ExternalTransactionRef | ERPNEXT_VALIDATION_FAILED |
| postGoodsReceipt() | Material Receipt service | GoodsReceiptCommand | GxP receipt committed; PO/item/warehouse mappings valid | Creates Purchase Receipt/appropriate doc; submits if profile requires | ExternalTransactionRef | ERPNEXT_RECEIPT_FAILED |
| postInventoryIssue() | Consumption service | InventoryIssueCommand | GxP consumption committed; stock-entry mapping valid | Creates Stock Entry or supported transaction with external ref/idempotency context | ExternalTransactionRef | ERPNEXT_STOCK_ENTRY_FAILED |
| postInventoryReturn() | Material Return service | InventoryReturnCommand | GxP return committed | Creates supported return/reversal transaction | ExternalTransactionRef | ERPNEXT_RETURN_FAILED |
| getInventoryBalance() | Reconciliation | item/warehouse/batch query | Read permission; mapping valid | Queries supported stock/resource/report endpoint per adapter profile | ERPInventoryBalance[] | ERPNEXT_BALANCE_QUERY_FAILED |
| getWorkOrder() | Batch planning/import | work_order_name | Read permission | Reads Work Order and maps source/planning fields only | ERPProductionOrder | ERPNEXT_WORK_ORDER_NOT_FOUND |
| healthCheck() | Scheduler/admin | instance_id | Credentials available | Checks Frappe version, required resources/permissions and optional connector custom fields | ERPHealth | ERPNEXT_HEALTH_FAILED |

# 4. Connector Package

```text
connectors/erpnext/
├── src/
│   ├── client/
│   ├── auth/
│   ├── mappings/
│   ├── purchase/
│   ├── inventory/
│   ├── manufacturing/
│   ├── reconciliation/
│   └── health/
├── contracts/
├── migrations/        # only connector-specific ERPNext custom fields if approved
├── fixtures/
└── tests/
```

# 5. API Usage

Reference patterns:
- resource REST APIs for standard DocTypes;
- whitelisted RPC only when a supported standard operation requires it;
- no SQL connection to ERPNext database;
- no editing ERPNext core Python files.

The exact API route is isolated in adapter code so ERPNext/Frappe version changes do not leak into GxP domain.

# 6. Mapping Examples

```text
GxP material_spec_version_id → ERPNext Item.item_code
GxP supplier_id              → ERPNext Supplier.name
GxP warehouse/location       → ERPNext Warehouse.name
GxP receipt_id               → ERPNext Purchase Receipt external ref
GxP consumption_tx_id        → ERPNext Stock Entry external ref
GxP batch_id                 → ERPNext Work Order reference (planning only)
```

# 7. Idempotency

Preferred:
- connector stores command ID ↔ ERPNext document reference;
- if customer permits connector custom field, include immutable external command/reference field on created documents;
- before retrying create, first lookup mapping/reference;
- do not create a second Purchase Receipt/Stock Entry because the first response timed out.

# 8. Submit / Cancel

ERPNext's document lifecycle is external semantics.

Adapter response:
```ts
type ERPNextDocumentRef = {
  doctype: string;
  name: string;
  docstatus: 0|1|2;
  modified?: string;
};
```

GxP never maps `docstatus=1` to QA release.

# 9. Tests

- API token invalid;
- item mapping missing;
- supplier not quality-approved even though ERPNext supplier active;
- Purchase Receipt timeout after submit;
- duplicate retry;
- Stock Entry validation error;
- warehouse mapping wrong;
- Work Order imported;
- custom field absent;
- ERPNext upgrade changes response field;
- connector user overprivileged warning.

# 10. Acceptance

A full material flow can synchronize PO → GxP receipt/quarantine → GxP release → dispense/consume → ERPNext stock posting while preserving GxP quality authority and exactly-once business effect through idempotent retries.

# 11. Claude Code Prohibitions

- Never modify ERPNext core.
- Never read/write ERPNext DB directly.
- Never implement GxP release using ERPNext Workflow or DocStatus.
- Never require custom ERPNext fields unless connector specification explicitly declares them.
