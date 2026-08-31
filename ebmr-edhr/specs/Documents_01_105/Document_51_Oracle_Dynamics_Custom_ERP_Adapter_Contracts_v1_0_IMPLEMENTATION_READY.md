# US eBMR / eDHR Regulated Manufacturing Platform
## Document 51 — Oracle Fusion, Dynamics 365 & Custom ERP Adapter Contracts — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-ERP-004  
**Parent Documents:** Documents 01–47  
**Primary Dependencies:** Document 48; Oracle SCM REST; Dynamics integration patterns; customer ERP adapters  
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

Define implementation contracts for Oracle Fusion Cloud SCM, Microsoft Dynamics 365 Finance/Supply Chain, and generic customer ERP adapters while maintaining one canonical ERPProvider interface.

# 2. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| MULTI-FR-001 | Adapter families | Provide Oracle Fusion SCM, Dynamics 365 Finance/Supply Chain and Generic Custom ERP implementations behind ERPProvider. | Vendor choice. |
| MULTI-FR-002 | Oracle REST profile | Use Oracle SCM REST resources for inventory/receiving/shipping/product references as configured. | Supported integration. |
| MULTI-FR-003 | Oracle inventory transaction | Map GxP inventory movement to Oracle inventory transaction resource/profile. | Inventory. |
| MULTI-FR-004 | Oracle receipt | Map receipt to supported Oracle receiving transaction/advice/confirmation pattern. | Receipt. |
| MULTI-FR-005 | Oracle lot/serial | Preserve Oracle lot/serial references while GxP genealogy remains authoritative. | Trace. |
| MULTI-FR-006 | Oracle privileges | Service account/API privileges minimized to exact resource operations. | Security. |
| MULTI-FR-007 | Oracle API release | Adapter configuration stores Oracle REST release/profile such as current 26x documentation rather than hardcoding one forever. | Compatibility. |
| MULTI-FR-008 | Dynamics integration pattern | Choose OData/data entities for synchronous CRUD-sized integration, data-management package REST for bulk/asynchronous, or custom services where justified. | Correct pattern. |
| MULTI-FR-009 | Dynamics product entity | Use supported product/item data entities/OData profile when synchronizing commercial item master. | Master mapping. |
| MULTI-FR-010 | Dynamics inventory | Use customer-supported data entities/services for warehouse/inventory transactions and references. | Inventory. |
| MULTI-FR-011 | Dynamics company/legal entity | Every request/mapping carries correct company/legal-entity context. | Tenant semantics. |
| MULTI-FR-012 | Dynamics entity versioning | Entity/custom-service names/fields isolated in adapter profile. | Maintainability. |
| MULTI-FR-013 | Custom REST adapter | Support OpenAPI-described REST endpoints with canonical mapping, auth, timeout, idempotency and reconciliation. | Generic integration. |
| MULTI-FR-014 | Custom SOAP adapter | Optional SOAP/WSDL adapter through isolated connector when legacy ERP requires it. | Legacy. |
| MULTI-FR-015 | Custom file adapter | SFTP/CSV/XML/EDI batch exchange allowed only with manifest, checksum, file identity, acknowledgement and replay rules. | Legacy/batch. |
| MULTI-FR-016 | Custom DB integration | Direct external ERP database read may be supported only read-only under customer-approved adapter; writes to vendor DB prohibited unless vendor-supported integration says otherwise. | Safety. |
| MULTI-FR-017 | Canonical DTO mapping | Vendor/custom fields map to canonical ERP DTOs; no business domain depends on raw vendor names. | Abstraction. |
| MULTI-FR-018 | Capabilities | Each adapter declares exact supported operations and limitations. | No false assumptions. |
| MULTI-FR-019 | External business error | Vendor rejection classified as nonretryable until input/mapping corrected. | Correct retry. |
| MULTI-FR-020 | Transport failure | Network/5xx/timeout/throttle classified retryable based on provider profile. | Resilience. |
| MULTI-FR-021 | Idempotency | Use vendor-provided idempotency/correlation if available plus local command ledger. | No duplicates. |
| MULTI-FR-022 | Reconciliation | Every write-capable custom adapter must implement a read/lookup/reconciliation path; otherwise production write capability is not approved. | Recoverability. |
| MULTI-FR-023 | Contract tests | Adapter certification requires simulator/sandbox contract suite. | Quality. |
| MULTI-FR-024 | No unverified connector | Customer custom adapter cannot be enabled for GxP posting without validation/acceptance profile. | Validated state. |

# 3. Claude Code Multi-ERP Function Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| postOracleInventoryTransaction() | Integration worker | InventoryCommand; oracle_instance | Oracle API profile/privileges/mappings valid | Calls configured inventoryBalanceTransactions or approved endpoint; stores response IDs/errors | ExternalTransactionRef | ORACLE_INVENTORY_TX_FAILED |
| postOracleReceipt() | Material Receipt integration | GoodsReceiptCommand | Oracle receiving profile configured | Calls supported receiving transaction/advice flow; stores group/transaction refs | ExternalTransactionRef | ORACLE_RECEIPT_FAILED |
| getOracleInventory() | Reconciliation | org/item/subinventory/lot query | Read privilege | Calls Oracle inventory quantity/balance REST profile; maps canonical balance | ERPInventoryBalance[] | ORACLE_QUERY_FAILED |
| queryDynamicsEntity() | Master/reconciliation | entity_name; company; filter; select | Entity allowlisted; auth/company valid | Executes OData query and maps via configured entity mapper | Canonical DTO[] | D365_ENTITY_QUERY_FAILED |
| postDynamicsEntity() | Integration worker | entity_name; company; canonical command | Write-capable entity/service approved; mapping valid | Calls OData/custom service or queues data-management package according to profile | ExternalTransactionRef | D365_POST_FAILED |
| submitDynamicsDataPackage() | Bulk sync worker | package_manifest; file/evidence ref | Bulk pattern enabled; package schema released | Submits data-management REST job; stores job ID and status | ExternalJobRef | D365_PACKAGE_FAILED |
| callCustomREST() | Generic adapter | operation_id; canonical request | OpenAPI operation allowlisted; auth/mapping valid | Maps canonical → external request; calls endpoint; maps response | Canonical/ExternalTransactionRef | CUSTOM_ERP_HTTP_FAILED |
| exchangeCustomFile() | Batch scheduler | file_contract_id; canonical records | SFTP/file profile active; schema/version known | Writes signed/checksummed outbound file + manifest; waits/polls ack/import result | ExternalBatchRef | CUSTOM_ERP_FILE_FAILED |
| reconcileCustomWrite() | Reconciliation | command_id; provider-specific lookup keys | Adapter has required readback implementation | Fetches external state and compares canonical expected effect | ReconciliationResult | CUSTOM_ERP_RECONCILIATION_UNSUPPORTED/MISMATCH |

# 4. Oracle Reference

Current Oracle Fusion Cloud SCM REST documentation includes inventory-management use cases for:
- inventory quantities;
- receiving;
- inventory transactions;
- shipment transactions;
- lots and serials.

The adapter stores the Oracle API release/profile in configuration and contract tests against the target customer's actual release.

# 5. Dynamics Reference

Current Microsoft guidance supports several integration patterns:
- OData/data entities;
- Data management package REST API;
- custom services;
- asynchronous/batch integrations.

Selection criteria:
- synchronous small CRUD/reference → OData when supported;
- high-volume import/export → data management/batch;
- special domain action unavailable through entities → approved custom service.

# 6. Generic Custom ERP Contract

Every custom adapter package must contain:

```text
adapter-manifest.yaml
openapi-or-wsdl/
mapping/
auth/
client/
operations/
reconciliation/
simulator-or-fixtures/
contract-tests/
validation-package/
```

`adapter-manifest.yaml`:
```yaml
provider: CUSTOMER_X
version: 1.0.0
capabilities:
  getItem: true
  getSupplier: true
  postGoodsReceipt: true
  postInventoryIssue: true
  reconcileInventoryMovement: true
auth:
  type: oauth2 | mtls | api_key | basic_approved
```

# 7. File Integration Contract

Outbound file:
- immutable batch ID;
- schema version;
- record count;
- SHA-256 manifest;
- generated UTC time;
- source command IDs.

Inbound ack:
- same batch ID;
- accepted/rejected records;
- external refs;
- checksum;
- processing time.

No “drop CSV into folder and assume success.”

# 8. Tests

- Oracle privilege missing;
- Oracle transaction accepted with partial failed records;
- Dynamics wrong company context;
- Dynamics OData throttling;
- Dynamics data-management job fails after upload;
- custom REST timeout after external commit;
- custom file duplicate pickup;
- custom adapter lacks reconciliation path;
- external schema changes.

# 9. Acceptance

A new customer ERP can be added by implementing ERPProvider + mapping + reconciliation + contract tests without editing Materials/Batch/Release modules.

# 10. Claude Code Prohibitions

- Never implement a write-only ERP connector with no reconciliation/readback.
- Never expose arbitrary customer SQL write.
- Never leak Dynamics/Oracle raw fields into GxP domain models.
- Never enable a custom connector in production solely because a happy-path API call worked.
