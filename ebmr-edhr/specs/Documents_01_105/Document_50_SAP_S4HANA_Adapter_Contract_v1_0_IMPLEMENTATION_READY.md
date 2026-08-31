# US eBMR / eDHR Regulated Manufacturing Platform
## Document 50 — SAP S/4HANA Adapter Contract — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-ERP-003  
**Parent Documents:** Documents 01–47  
**Primary Dependencies:** Document 48; SAP S/4HANA APIs; Materials/Inventory/Procurement  
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

Define the SAP S/4HANA adapter boundary and canonical mappings for product/material references, inventory/material documents, production-order references and reconciliation without coupling GxP services to SAP semantics.

# 2. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| SAP-FR-001 | SAP instance profile | Support S/4HANA Cloud Public/Private/On-Prem profiles with configured API capabilities/version. | Deployment flexibility. |
| SAP-FR-002 | Auth | OAuth2/mTLS/basic only if approved deployment supports; secrets isolated. | Security. |
| SAP-FR-003 | Product master | Map canonical item/material through supported Product Master APIs such as API_PRODUCT_SRV where applicable. | Master mapping. |
| SAP-FR-004 | Material stock | Read inventory/stock through supported SAP inventory API/profile. | Reconciliation. |
| SAP-FR-005 | Material document | Create/retrieve material movement through supported Material Document API/profile. | Inventory posting. |
| SAP-FR-006 | Goods receipt | Map GxP receipt to correct SAP movement semantics and PO/order refs. | Receipt. |
| SAP-FR-007 | Goods issue | Map material consumption to approved movement code/type profile. | Consumption. |
| SAP-FR-008 | Transfer posting | Map GxP transfer when SAP ownership/profile requires. | Warehouse. |
| SAP-FR-009 | Reversal | Integration reversal is separate SAP transaction; never used to silently erase GxP physical record. | History. |
| SAP-FR-010 | Movement mapping | Movement codes/types stored as configuration, not hardcoded across customers. | Customer-specific. |
| SAP-FR-011 | Plant/storage location | Explicit site ↔ SAP plant/storage-location mapping. | Location integrity. |
| SAP-FR-012 | Material/UOM | Material number/base unit/alternate UOM mapping controlled. | Quantity integrity. |
| SAP-FR-013 | Batch/serial | SAP batch/serial refs mapped to internal IDs, not authoritative genealogy. | Trace. |
| SAP-FR-014 | Production order | Read SAP production/process order reference where customer uses SAP planning/manufacturing. | Planning. |
| SAP-FR-015 | Blocked/released stock | GxP quality release can project to SAP stock/status movement only through configured Quality-approved mapping. | No dual release. |
| SAP-FR-016 | Posting date | Posting/document dates derived per integration/business policy and retained with actual GxP physical occurrence time. | Chronology. |
| SAP-FR-017 | External transaction ref | Store SAP material document/year/item or equivalent transaction keys. | Reconciliation. |
| SAP-FR-018 | OData batch | Adapter may use OData `$batch` where supported but preserves per-command idempotency/response mapping. | Efficiency. |
| SAP-FR-019 | Error mapping | Map SAP HTTP/OData/business messages to stable integration errors while retaining raw diagnostic. | Support. |
| SAP-FR-020 | CSRF/session handling | Handle required SAP OData CSRF/session mechanics in client layer only. | Correct protocol. |
| SAP-FR-021 | Throttling/retry | Respect API limits and classify retryable vs business errors. | Resilience. |
| SAP-FR-022 | API version profile | Technical service/entity versions captured in adapter configuration. | Compatibility. |
| SAP-FR-023 | Custom BAPI/RFC | Custom/private BAPI/RFC integration allowed only through separate customer adapter profile; not assumed common baseline. | Controlled custom. |
| SAP-FR-024 | Reconciliation | Query material docs/stock by bounded date/object keys and compare expected commands. | Integrity. |
| SAP-FR-025 | No SAP regulatory authority | SAP material document success does not constitute eBMR step completion/QA release. | Boundary. |

# 3. Claude Code SAP Function Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| getSAPProduct() | Master sync | sap_material_id | SAP product API configured/authenticated | Calls Product Master API/profile; maps SAP fields to canonical ERPItem | ERPItem | SAP_PRODUCT_NOT_FOUND |
| getSAPInventoryBalance() | Reconciliation | plant; storage_location; material; batch? | Inventory API configured | Queries SAP stock/material API; maps quantities/UOM | ERPInventoryBalance[] | SAP_STOCK_QUERY_FAILED |
| postSAPMaterialDocument() | Outbound inventory worker | canonical material movement command | Movement mapping/plant/location/material/UOM valid; source GxP tx committed | Builds SAP API_MATERIAL_DOCUMENT request; POSTs; stores material document/year/item | ExternalTransactionRef | SAP_MATERIAL_DOCUMENT_FAILED |
| reverseSAPMaterialDocument() | Authorized correction integration | original external ref; reversal reason; source GxP correction/ref | GxP correction transaction exists; reversal mapping allowed | Calls supported cancellation/reversal API; stores new external ref | ExternalTransactionRef | SAP_REVERSAL_FAILED |
| getSAPProductionOrder() | Batch import/planning | production_order_id | API/profile supports query | Fetches order/reference and maps planning fields only | ERPProductionOrder | SAP_PRODUCTION_ORDER_NOT_FOUND |
| fetchCSRFSecurityContext() | SAP client | service endpoint | Auth valid | Fetches CSRF token/session cookie if required; caches securely short-term | SAPSecurityContext | SAP_CSRF_FAILED |
| mapSAPBusinessError() | SAP client | HTTP status; OData/business message payload | Raw response available | Classifies AUTH/VALIDATION/CONFLICT/THROTTLE/RETRYABLE and preserves raw diagnostic ref | IntegrationError | none |
| reconcileSAPMaterialDocument() | Reconciliation job | command_id; external material doc ref | External ref known or lookup window bounded | Reads SAP doc and compares material/qty/UOM/plant/location/posting | ReconciliationResult | SAP_RECONCILIATION_MISMATCH |

# 4. Current Reference APIs

Current SAP documentation identifies:
- Product Master A2X OData service `API_PRODUCT_SRV`;
- Material Documents - Read, Create service `API_MATERIAL_DOCUMENT`;
- supported material-document operations for read/create/cancel;
- material document header/item entities and movement-code semantics.

Adapter code shall use configured service metadata/version rather than assuming one immutable SAP release.

# 5. Material Movement Mapping

Customer-specific configuration:

```yaml
goods_receipt_po:
  sap_goods_movement_code: "01"
  gxp_source: MATERIAL_RECEIPT

goods_issue:
  sap_goods_movement_code: "03"
  gxp_source: MATERIAL_CONSUMPTION

transfer_posting:
  sap_goods_movement_code: "04"
  gxp_source: INVENTORY_TRANSFER

reversal:
  sap_goods_movement_code: "06"
  gxp_source: CONTROLLED_GXP_CORRECTION
```

This is an example profile, not a universal hardcoded mapping.

# 6. SAP Client Layer

```text
connectors/sap/
├── client/
│   ├── auth/
│   ├── csrf/
│   ├── odata/
│   └── soap_optional/
├── product/
├── inventory/
├── manufacturing/
├── mappings/
├── reconciliation/
└── tests/
```

# 7. Idempotency

Because external APIs may not provide a first-class universal idempotency header:
- persist local command ID and payload hash;
- lookup prior external ref before retrying a create after uncertain timeout;
- use SAP document/customer reference fields only if supported/configured;
- reconciliation must detect “posted externally but response lost.”

# 8. Tests

- wrong SAP plant mapping;
- wrong movement code configuration;
- CSRF failure;
- OAuth expiry;
- material document POST succeeds then client timeout;
- duplicate retry;
- business validation error;
- reversal after GxP correction;
- stock differs from GxP projection;
- API service version upgrade.

# 9. Acceptance

The adapter can post and later reconcile one GxP inventory movement to one SAP material-document effect while preserving the original GxP physical transaction independently.

# 10. Claude Code Prohibitions

- Never hardcode customer SAP movement types across all deployments.
- Never let SAP material document reverse/delete original GxP history.
- Never use SAP “unrestricted stock” as autonomous final QA release.
- Never place SAP OData entity models in GxP core domain.
