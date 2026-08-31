# US eBMR / eDHR Regulated Manufacturing Platform
## Document 13 — Genealogy & Traceability Engine Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EBMR-004  
**Parent Documents:** Document 01 v1.1; Document 02 v1.0  
**Primary Dependencies:** Documents 03–12; Materials; ERP/WMS; Packaging; Complaint/Recall  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products (DDCP)  
**Future Profiles:** Medical Devices, Pharmaceuticals  
**Date:** 2026-08-20

---


# Implementation Standard Applied to This Document

This specification is intended to be sufficient for Codex, Claude Code, or a human development team to implement the module with minimal interpretation.

Where applicable, the document therefore defines:

- objective and scope;
- non-goals/exclusions;
- actors/roles;
- functionality and sub-functionality;
- workflows and state machines;
- business rules;
- authorization and segregation of duties;
- electronic-signature behavior;
- audit behavior;
- entities, fields, relationships and ownership;
- PostgreSQL/Frappe storage boundaries;
- suggested tables, indexes and constraints;
- APIs and stable error codes;
- events/outbox contracts;
- UI screens/actions;
- integrations;
- calculations/validations;
- concurrency/idempotency;
- failure/recovery behavior;
- configuration;
- observability;
- retention/archival;
- migrations;
- performance/scaling;
- repository/module structure;
- implementation sequence;
- test cases;
- acceptance criteria;
- requirement traceability;
- explicit coding-agent rules.

If a future implementation decision changes regulated behavior and is not defined here, the coding agent shall raise a specification gap rather than inventing behavior.


# 1. Objective

Provide one proprietary cross-domain genealogy engine for drug, device and combination-product manufacturing.

This is a major differentiating IP component because it joins materials, drug batches, device components, device serials, combination products, packaging and distribution references into one traceable graph.

# 2. Graph Model

```text
Supplier Lot
    ↓
Internal Material Lot / Container
    ↓
Drug Batch / Intermediate
    ↓
Fill Group / Cartridge / Syringe
    ↓
Device Component / Subassembly
    ↓
Device Serial
    ↓
Combination Product Lot/Serial
    ↓
Packaging Hierarchy
    ↓
Distribution Reference
```

# 3. Functional Requirements

| ID | Functionality | Detailed behavior | Acceptance intent |
|---|---|---|---|
| GEN-FR-001 | Canonical genealogy entity | Represent supplier/material lot/container, drug batch, intermediate, device component lot/serial, device unit, combination lot/serial, package and distribution reference as typed genealogy nodes. | Common trace model. |
| GEN-FR-002 | Typed relationships | Use controlled edge types such as CONTAINS, DERIVED_FROM, CONSUMED_IN, ASSEMBLED_INTO, PACKAGED_AS, FILLED_INTO, TESTED_BY, STERILIZED_IN, DISTRIBUTED_AS. | Meaning explicit. |
| GEN-FR-003 | Forward trace | Given source material/component/drug batch, return all directly/indirectly affected intermediates/final lots/serials/packages. | Recall impact. |
| GEN-FR-004 | Backward trace | Given final lot/serial, return all source materials/components/drug/device lots, operations and equipment evidence. | Investigation. |
| GEN-FR-005 | Container-level trace | Track internal material container identity where dispensing/partial use matters. | Exact source. |
| GEN-FR-006 | Quantity on edge | Store consumed/produced quantity + UOM for material transformation relationships where applicable. | Mass/quantity genealogy. |
| GEN-FR-007 | Step provenance | Edge can reference batch step/operation that created relationship. | Process context. |
| GEN-FR-008 | Version/hash provenance | Node/edge references exact authoritative record/version and source event. | No mutable pointer. |
| GEN-FR-009 | Drug-device compatibility | Final DDCP genealogy records exact constituent compatibility version used. | Pairing evidence. |
| GEN-FR-010 | Serial relationship | Support component serial → device serial → combination-product serial. | Unit trace. |
| GEN-FR-011 | Lot-to-serial scale | Efficiently represent many serials consuming same lot without unbounded duplicated metadata. | Scale. |
| GEN-FR-012 | Package hierarchy | Represent unit → carton → shipper/pallet/package aggregation where required. | Distribution/recall. |
| GEN-FR-013 | Distribution reference | Link released product lot/serial/package to ERP/WMS shipment/distribution reference without making ERP record genealogy truth. | Downstream trace. |
| GEN-FR-014 | Rework relationship | Record REWORKED_FROM/SUPERSEDES relationships preserving original identity. | History. |
| GEN-FR-015 | Split/merge | Support one lot split into many, many materials into one batch, subassemblies merged into final unit. | Manufacturing transformations. |
| GEN-FR-016 | No arbitrary deletion | Genealogy nodes/edges from regulated execution are immutable facts; corrections append superseding/voiding relationship metadata. | Trace cannot disappear. |
| GEN-FR-017 | Correction | If erroneous link was recorded, correction marks original as invalid/superseded through controlled event and adds correct edge; original remains. | Audit. |
| GEN-FR-018 | Recall query | Query affected final products, inventory, released/distributed references and quality events from any source node. | Field action support. |
| GEN-FR-019 | Complaint query | Serial/lot complaint query retrieves full manufacturing/constituent history and related prior complaints/events. | Investigation. |
| GEN-FR-020 | Supplier impact | Supplier/manufacturer lot can identify internal lots and finished product impact. | Supplier quality. |
| GEN-FR-021 | Equipment correlation | Optionally associate operations with actual equipment, but do not model equipment as material ancestry unless semantically appropriate. | Process evidence. |
| GEN-FR-022 | Evidence links | Node/edge can reference COA, test report, assembly/test evidence, sterilization evidence. | Complete context. |
| GEN-FR-023 | Graph consistency | Prevent invalid edge classes, self-relationships, impossible product type transitions and duplicate exact edges. | Semantic integrity. |
| GEN-FR-024 | Cycle handling | Material/product ancestry should normally be acyclic; rework/correction relationships are separately typed to avoid misleading ancestry cycles. | Trace algorithm safe. |
| GEN-FR-025 | Traversal depth | Support bounded/unbounded authorized traversals with protection against runaway queries. | Performance/security. |
| GEN-FR-026 | Affected scope snapshot | Recall/impact assessment can save a versioned result set with query criteria, graph version/cutoff and reviewer signature. | Investigation reproducible. |
| GEN-FR-027 | External mapping | ERP/LIMS source IDs linked to nodes as provenance but internal genealogy IDs remain authoritative. | Vendor independence. |
| GEN-FR-028 | Import/migration | Migrated genealogy identifies source system/migration batch and preserves source checksum. | Historical provenance. |
| GEN-FR-029 | Performance | Target common single-serial backward trace under interactive latency and large-lot forward impact through indexed traversal/materialized helper tables. | Usable at scale. |
| GEN-FR-030 | Export | Generate structured genealogy JSON/CSV and human-readable trace report with node/edge evidence. | Inspection/recall ready. |

# 4. PostgreSQL Model

V1 uses PostgreSQL rather than a dedicated graph DB.

## `genealogy_node`

```text
id uuid PK
tenant_id uuid
node_type varchar(60)
business_ref varchar(200)
authoritative_record_type varchar(80)
authoritative_record_id uuid
authoritative_version bigint
record_hash char(64)
site_id uuid
created_at timestamptz
```

Indexes:
- `(tenant_id, node_type, business_ref)`
- `(tenant_id, authoritative_record_id)`

## `genealogy_edge`

```text
id uuid PK
tenant_id uuid
from_node_id uuid NOT NULL
to_node_id uuid NOT NULL
edge_type varchar(60) NOT NULL
quantity numeric(24,8)
uom varchar(40)
step_id uuid
source_event_id uuid
state varchar(30) default 'ACTIVE'
supersedes_edge_id uuid
created_at timestamptz
```

Indexes:
- `(tenant_id, from_node_id, edge_type)`
- `(tenant_id, to_node_id, edge_type)`
- `(tenant_id, step_id)`

Unique exact edge constraint based on semantic fields/source event where appropriate.

# 5. Edge Types

Controlled catalogue:
- `RECEIVED_AS`
- `SPLIT_FROM`
- `DERIVED_FROM`
- `CONSUMED_IN`
- `PRODUCED_AS`
- `FILLED_INTO`
- `ASSEMBLED_INTO`
- `PACKAGED_AS`
- `AGGREGATED_INTO`
- `STERILIZED_IN`
- `REWORKED_FROM`
- `SUPERSEDES`
- `DISTRIBUTED_AS`

# 6. Query APIs

- `GET /genealogy/v1/nodes/lookup?...`
- `GET /genealogy/v1/nodes/{id}/ancestors`
- `GET /genealogy/v1/nodes/{id}/descendants`
- `GET /genealogy/v1/serial/{serial}/full-trace`
- `GET /genealogy/v1/material-lot/{lot}/affected-products`
- `POST /genealogy/v1/impact-assessments`
- `GET /genealogy/v1/impact-assessments/{id}`
- `POST /genealogy/v1/exports`

# 7. Traversal Implementation

Use recursive CTEs initially.

Requirements:
- tenant predicate on every recursive step;
- max depth/query timeout;
- visited-node detection;
- edge-type filters;
- optional date/site/state filters.

For high-scale serial/package aggregation, add materialized ancestry/descendency helper tables only after benchmark evidence.

# 8. Write Path

Genealogy writes are not generic CRUD.

They are generated by domain events:
- MaterialConsumed
- DrugBatchProduced
- DeviceComponentAssembled
- FillLinkedToDevice
- PackagingCompleted
- DistributionLinked

Each edge creation is idempotent by source event ID.

# 9. UI

1. Genealogy Search
2. Interactive Trace Tree/Graph
3. Material Lot Impact
4. Serial History
5. DDCP Constituent View
6. Recall Impact Assessment
7. Saved/Approved Impact Snapshot
8. Export

# 10. Correction

Never delete wrong edge.

Use:
1. controlled correction request;
2. mark semantic state `SUPERSEDED/VOIDED` through authorized mutation;
3. link superseding edge;
4. audit original and correction.

# 11. Performance Targets

Design benchmark:
- serial backward trace: seconds, not minutes;
- material lot with tens/hundreds thousands affected serials: asynchronous if needed;
- saved impact assessment generated with progress/status;
- pagination/streaming for huge results.

# 12. Events

- GenealogyNodeCreated
- GenealogyEdgeCreated
- GenealogyEdgeCorrected
- ImpactAssessmentCreated
- ImpactAssessmentApproved

# 13. Repository Structure

```text
services/gxp-api/src/modules/genealogy/
packages/genealogy-model/
apps/ebmr_frappe/ebmr/genealogy/
contracts/events/genealogy/
```

# 14. Tests

- simple material→batch;
- drug batch→device serial;
- many component lots;
- split/merge;
- partial container;
- rework;
- wrong edge correction;
- cycle protection;
- tenant isolation;
- 100k serial affected query;
- saved recall impact;
- migration provenance;
- package hierarchy.

# 15. Acceptance

A single final autoinjector serial must be traceable backward to:
drug batch/lot, container/fill group, device component lots/serials, assembly/test operations, packaging/label and relevant equipment/evidence.

A source material/component lot must be traceable forward to all affected finished DDCP lots/serials.

# 16. Codex / Claude Rules

Never use mutable business name as genealogy key.
Never delete genealogy history.
Never create genealogy edge directly from UI.
Never introduce graph DB until benchmark justifies it.

# Regulatory Engineering Basis

This specification is an engineering baseline, not legal advice and not a declaration that the software or a customer configuration is automatically compliant.

Relevant current U.S. regulatory sources include:

- 21 CFR Part 4 — combination-product CGMP framework;
- 21 CFR Part 11 — electronic records/electronic signatures when applicable;
- 21 CFR Parts 210/211 — drug CGMP;
- 21 CFR §211.186 — Master production and control records;
- 21 CFR §211.188 — Batch production and control records;
- 21 CFR §211.103 — Calculation of yield;
- 21 CFR Part 211 Subpart G — Packaging and labeling control;
- 21 CFR Part 820 — QMSR, effective February 2, 2026;
- 21 CFR §820.10 — requirements for a quality management system;
- 21 CFR §820.35 — control of records, including UDI-related records;
- 21 CFR §820.45 — device labeling and packaging controls;
- applicable UDI requirements under 21 CFR Part 830.

The current QMSR incorporates ISO 13485:2016 by reference. This document summarizes engineering implications and does not reproduce copyrighted ISO text.

Reference URLs:
- https://www.law.cornell.edu/cfr/text/21/4.4
- https://www.law.cornell.edu/cfr/text/21/211.186
- https://www.law.cornell.edu/cfr/text/21/211.188
- https://www.law.cornell.edu/cfr/text/21/211.103
- https://www.law.cornell.edu/cfr/text/21/part-211/subpart-G
- https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr
- https://www.law.cornell.edu/cfr/text/21/820.10
- https://www.law.cornell.edu/cfr/text/21/820.35
- https://www.law.cornell.edu/cfr/text/21/820.45
