# US eBMR / eDHR Regulated Manufacturing Platform
## Document 52 — Master Data Synchronization, Mapping & Reconciliation — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-ERP-005  
**Parent Documents:** Documents 01–47  
**Primary Dependencies:** Documents 09, 18–20, 48–51; Data Governance  
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

Define controlled master-data synchronization and mapping between eBMR/GxP and external ERP systems, with explicit field ownership, staging, conflict handling, approval and historical mapping versioning.

# 2. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| MDS-FR-001 | Master-data catalogue | Define synchronized object types: commercial item, regulated product mapping, material item, supplier, site/plant, warehouse/location, UOM, reason/movement code, cost center/project refs as applicable. | Controlled scope. |
| MDS-FR-002 | Field ownership | Every synchronized field explicitly owned by GxP or ERP; BIDIRECTIONAL ownership disallowed for same semantic field unless conflict policy approved. | No conflict. |
| MDS-FR-003 | Mapping status | UNMAPPED, PROPOSED, ACTIVE, CONFLICT, SUSPENDED, RETIRED. | Explicit. |
| MDS-FR-004 | Initial sync | Bulk initial import uses staging, validation and reconciliation before activation. | Safe onboarding. |
| MDS-FR-005 | Incremental sync | Timestamp/change-token/event/poll strategy vendor-specific but canonical processing identical. | Ongoing sync. |
| MDS-FR-006 | External change detection | ERP-owned field changes update projection; GxP-owned field changes from ERP create conflict, not overwrite. | Ownership. |
| MDS-FR-007 | GxP change propagation | Approved GxP-owned projection can be sent outward only if provider profile supports it. | Controlled. |
| MDS-FR-008 | Identity matching | Prefer explicit external IDs; name/fuzzy match only proposes mapping for human review. | No wrong master link. |
| MDS-FR-009 | Duplicate detection | Detect duplicate external/internal mappings and block activation. | Integrity. |
| MDS-FR-010 | UOM mapping | UOM equivalency/conversion approved/versioned; unknown UOM quarantines record. | Quantity safety. |
| MDS-FR-011 | Plant/site mapping | ERP plant/org/company/location context maps exactly to tenant/site. | Isolation. |
| MDS-FR-012 | Warehouse mapping | Warehouse/bin/subinventory location mapping explicit and effective-dated. | Logistics. |
| MDS-FR-013 | Supplier mapping | Commercial supplier identity mapping distinct from GxP manufacturer/approved source status. | Quality. |
| MDS-FR-014 | Product/material mapping | External item maps to exact internal business identity/version policy, never “latest regulated version” dynamically during historical execution. | History. |
| MDS-FR-015 | Reference-data mapping | Movement type/reason code/status reference values versioned by ERP instance. | Adapter semantics. |
| MDS-FR-016 | Effective dates | Mappings can be future-effective and historical mappings remain for old transactions. | Reproducibility. |
| MDS-FR-017 | Suspension | Suspend mapping on discovered mismatch without deleting history. | Containment. |
| MDS-FR-018 | Conflict queue | Structured differences with owner/source/current/proposed values and resolution action. | Governance. |
| MDS-FR-019 | Approval | Critical identity/UOM/site mappings require integration/data-owner approval; quality-critical mappings may require QA/validation. | Controlled. |
| MDS-FR-020 | Bulk approval restriction | High-risk mappings cannot be blanket-approved without review profile. | Safety. |
| MDS-FR-021 | Mapping hash/version | Every integration transaction records mapping version/hash used. | Investigation. |
| MDS-FR-022 | Sync checkpoint | Persist external change cursor/watermark per entity/instance. | Restart safe. |
| MDS-FR-023 | Replay | Reprocess same inbound master event idempotently. | Replay safe. |
| MDS-FR-024 | Delete semantics | External deletion/deactivation maps to inactive/suspended projection; never physically deletes GxP-linked master history. | History. |
| MDS-FR-025 | Reconciliation | Scheduled object counts/key fields/active mapping differences. | Detect drift. |
| MDS-FR-026 | Data quality metrics | Unmapped, conflict, stale, failed sync and duplicate rates visible. | Operability. |
| MDS-FR-027 | Audit | Mapping create/change/approve/suspend/merge and conflict resolution audited. | Trace. |
| MDS-FR-028 | Migration | Customer onboarding mapping/import package retained with source checksum and approval. | Provenance. |

# 3. Claude Code Master-Data Function Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| stageInboundMasterRecords() | ERP poll/webhook/bulk import | entity_type; raw records; source cursor; instance | Source authenticated/schema recognized | Stores immutable staging records/hash; no active mapping mutation | StagingBatchReceipt | MasterDataStaged; MASTER_SCHEMA_INVALID |
| normalizeMasterRecord() | Sync processor | staging_record; mapping_profile_version | Profile effective | Maps vendor fields to canonical external-master projection; validates types/UOM/context | NormalizedExternalMaster | MASTER_NORMALIZATION_FAILED |
| matchInternalEntity() | Sync processor/admin | normalized external master; entity type | Matching policy available | Uses explicit mapping first; deterministic keys next; fuzzy only creates proposal | MasterMatchResult | MASTER_MATCH_AMBIGUOUS |
| proposeMapping() | Sync processor/admin | external_ref; internal_ref; evidence; confidence | No active conflicting mapping | Creates PROPOSED mapping/version | MappingProposal | MasterMappingProposed |
| approveMapping() | Data Owner/QA if required | mapping_id; expected_version; signature if policy | Reviewer authorized; identity/UOM/site validations pass | Activates versioned mapping; stores approval/audit | ActiveMapping | MasterMappingActivated |
| applyERPProjectionUpdate() | Sync processor | normalized record; active mapping | Field ownership matrix loaded | Updates only ERP-owned projection fields; GxP-owned differences create conflict | ProjectionUpdateResult | ERPProjectionUpdated/MasterConflictRaised |
| raiseMasterConflict() | Sync processor | entity/mapping; field diffs; source versions | Conflict material | Creates conflict queue item and optionally suspends mapping based on severity | MasterConflict | MasterDataConflictDetected |
| resolveMasterConflict() | Data Owner | conflict_id; resolution; reason; approvals | Authorized; source/current versions unchanged | Applies permitted projection/mapping action; closes conflict | ConflictResolution | MasterConflictResolved |
| advanceSyncCheckpoint() | Sync worker | instance/entity; cursor/watermark; batch_id | All staging records durably stored | Updates checkpoint after durable staging, not before | SyncCheckpoint | SyncCheckpointAdvanced |
| reconcileMasterMappings() | Scheduled/admin | instance; entity_type; scope | Provider available | Compares active internal mappings to external existence/key fields/status | MasterReconciliationReport | MasterReconciliationMismatchDetected |

# 4. Mapping Entity

```text
master_mapping
id uuid PK
erp_instance_id uuid
entity_type varchar
internal_id uuid
external_id varchar
mapping_version bigint
state varchar
effective_from/to
mapping_profile_version varchar
mapping_hash char(64)
approved_by/signature_ref
created_at
```

Unique active mapping constraints are defined per entity type.

# 5. Field Ownership Example

| Canonical field | Owner |
|---|---|
| item commercial description | ERP |
| item external code | ERP |
| regulated material specification | GxP |
| supplier payment terms | ERP |
| supplier Quality approval | GxP |
| warehouse accounting code | ERP |
| GxP location eligibility | GxP |
| UOM mapping | Joint controlled reference mapping |

# 6. Staging Pattern

```text
ERP raw change
   ↓
master_sync_staging
   ↓ normalize
canonical external projection
   ↓ match
mapping / conflict
   ↓
active projection
```

Do not directly update active mappings from webhook payload.

# 7. Mapping Change Effect on Open Batches

Open/issued batches keep the mapping/reference versions included in their execution snapshot where required. A new master mapping must not silently change historical external references.

# 8. Tests

- initial 100k item import;
- duplicate external item;
- supplier same name different legal entity;
- GxP-owned field changed in ERP;
- unknown UOM;
- wrong plant/site;
- mapping future effective;
- external item deactivated;
- replay same import batch;
- conflict resolution stale version;
- sync cursor crash/restart.

# 9. Acceptance

A customer ERP can be synchronized without allowing external master updates to overwrite regulated product/material/supplier-quality truth, and every outbound transaction can identify the exact mapping version used.

# 10. Claude Code Prohibitions

- Never fuzzy-match and auto-activate critical material/supplier mappings.
- Never model same semantic field as both ERP- and GxP-authoritative without explicit conflict policy.
- Never delete mapping history after remap.
- Never advance sync cursor before source records are durably staged.
