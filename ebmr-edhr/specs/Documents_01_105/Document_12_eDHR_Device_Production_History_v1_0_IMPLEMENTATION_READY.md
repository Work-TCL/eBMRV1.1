# US eBMR / eDHR Regulated Manufacturing Platform
## Document 12 — eDHR / Device Production History Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EBMR-003  
**Parent Documents:** Document 01 v1.1; Document 02 v1.0  
**Primary Dependencies:** Documents 03–11; Genealogy; Equipment; Packaging/UDI; QMS  
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

Define the electronic device production-history capability used for the device constituent of DDCP V1 and future standalone medical-device manufacturing.

The product may use “eDHR” as a customer-facing familiar term, but technical/regulatory mapping must use the current QMSR framework and incorporated ISO 13485 requirements, plus current UDI/labeling requirements where applicable.

# 2. Core Model

```text
Device Lot / Batch
    ├── Shared process evidence
    ├── Unit/Serial 001
    │   ├ components
    │   ├ assembly
    │   ├ tests
    │   ├ inspections
    │   └ label/UDI
    ├── Unit/Serial 002
    └── ...
```

For DDCP:

```text
Drug Batch / Fill Group
        ↓
Device Unit / Serial
        ↓
Final Combination Product
```

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| DHR-FR-001 | Device production record | Create complete lot/unit/serial production history derived from released product/recipe snapshot. | Device history reproducible. |
| DHR-FR-002 | Scope level | Support lot-level, serial-level, subassembly-level and inherited batch-level evidence. | High-volume execution configurable. |
| DHR-FR-003 | Serial generation/import | Generate or accept controlled serials with uniqueness, source and reservation rules. | No duplicate device identity. |
| DHR-FR-004 | UDI record | Store applicable DI/PI/UDI components, packaging level and source; link to unit/lot/batch history. | Current QMSR/UDI record support. |
| DHR-FR-005 | Component genealogy | Record exact device component lots/serials/subassemblies assembled into final device. | Backward/forward traceability. |
| DHR-FR-006 | Drug constituent linkage | For DDCP, link exact drug batch/lot/container/fill group to device unit/lot/combination product. | Integrated history. |
| DHR-FR-007 | Assembly step | Capture assembly station/equipment, operator/device source, time, parameters and component relationships. | Assembly evidence attributable. |
| DHR-FR-008 | Test result | Capture functional/electrical/mechanical/dose-delivery/visual or other structured test result with test specification/version. | Acceptance evidence exact. |
| DHR-FR-009 | Automated tester | Accept instrument result through Edge with source identity, mapping version, raw evidence reference and pass/fail rule. | Machine result attributable. |
| DHR-FR-010 | Manual inspection | Capture inspector, method, criteria, result, defect code and optional image/evidence. | Manual acceptance controlled. |
| DHR-FR-011 | Nonconformance | Failed component/unit/test creates linked NCR/exception and controls disposition. | Failure not overwritten. |
| DHR-FR-012 | Rework | Rework uses approved route and maintains original + reworked history, reason and approvals. | Rework traceable. |
| DHR-FR-013 | Scrap | Unit/component scrap records quantity/identity, reason, authority and genealogy impact. | Scrapped unit cannot release. |
| DHR-FR-014 | Acceptance status | Unit/lot status progresses through controlled states: In Process, Hold, Rework, Accepted, Rejected/Scrapped, Released. | Status rule driven. |
| DHR-FR-015 | Label/packaging link | Record exact label/UDI/packaging configuration used for device/lot/unit. | Packaging evidence linked. |
| DHR-FR-016 | Sterilization link | Where applicable link unit/lot to sterilization load/cycle and release status. | Sterilization eligibility visible. |
| DHR-FR-017 | Environmental/area link | Where required retain relevant production area/environmental evidence references. | Critical conditions linked. |
| DHR-FR-018 | Process validation reference | Step/equipment/process may reference applicable validated process version/status. | Production history supports validation linkage. |
| DHR-FR-019 | Calibration/test-equipment eligibility | Tester/equipment must be eligible when used; actual equipment ID stored. | Invalid tester blocks. |
| DHR-FR-020 | Production specification snapshot | Device history binds exact released specification/instructions/configuration. | No current-master drift. |
| DHR-FR-021 | Device record completeness | Before acceptance/release, evaluate required steps, components, tests, labels, signatures and unresolved NCRs. | Incomplete unit cannot release. |
| DHR-FR-022 | Bulk inheritance | Evidence common to many units may be inherited from batch/lot with immutable reference to avoid duplication. | Scale without semantic loss. |
| DHR-FR-023 | Override | Any unit-specific override/manual replacement requires released policy, reason, authorization and audit. | No hidden exception. |
| DHR-FR-024 | Unit split/merge | Support controlled subassembly transformation relationships; final unit genealogy remains acyclic/traceable. | Assembly graph consistent. |
| DHR-FR-025 | Repair during manufacturing | Distinguish manufacturing rework/repair from postmarket service; apply appropriate controlled route. | Semantics clear. |
| DHR-FR-026 | Device release package | Generate unit/lot history package with identifiers, components, process, tests, signatures, exceptions, labels and genealogy. | Inspection/customer evidence ready. |
| DHR-FR-027 | Search | Lookup by serial, UDI, lot, batch, component lot, drug batch, tester, defect code. | Fast investigation. |
| DHR-FR-028 | High-volume serial execution | Support bulk creation/result ingestion with controlled grouping while preserving unit exceptions. | Scales to many serials. |
| DHR-FR-029 | Record correction | Corrections use Vault/audit model and never rewrite original device history. | History preserved. |
| DHR-FR-030 | QMSR terminology | Product may expose customer-facing alias 'eDHR', but compliance mapping is maintained against current QMSR/ISO 13485 record/production controls rather than relying on obsolete clause numbering. | Current regulatory framing. |

# 4. State Model

Unit:
`CREATED → IN_PROCESS → TEST_PENDING → ACCEPTANCE_PENDING → ACCEPTED → RELEASED`

Alternate:
`HOLD`, `NONCONFORMING`, `REWORK`, `REJECTED`, `SCRAPPED`.

Only controlled transitions are permitted.

# 5. Data Model

## `device_unit`

```text
id uuid PK
tenant_id uuid
site_id uuid
product_version_id uuid
batch_id uuid
device_lot_id uuid
serial_number varchar(200)
udi_di varchar(120)
udi_pi jsonb
state varchar(40)
version bigint
release_status varchar(40)
created_at timestamptz
```

Unique:
- `(tenant_id, serial_number)` within configured product namespace;
- UDI uniqueness constraints according to configured representation.

## `device_component_usage`
- parent_unit/subassembly ID
- component type
- component material lot
- component serial
- quantity
- assembly step
- timestamp

## `device_test_result`
- unit/lot scope
- test specification version
- test code
- tester equipment ID
- result values
- pass/fail
- raw evidence reference
- rule evaluation
- result version/supersession

## `device_defect`
- defect code
- severity/classification
- location
- inspection/test source
- NCR link

## `device_evidence_inheritance`
- child unit
- shared source record
- evidence type
- immutable source version/hash

# 6. High-Volume Strategy

Avoid copying identical batch-level evidence into each serial row.

Use:
- immutable inherited references;
- bulk result commands where one validated machine produces results for a known serial range;
- exception rows only when unit differs;
- indexed serial lookup.

# 7. APIs

- `POST /devices/v1/lots`
- `POST /devices/v1/units/bulk-create`
- `POST /devices/v1/units/{id}/components`
- `POST /devices/v1/units/{id}/tests`
- `POST /devices/v1/units/{id}/inspection`
- `POST /devices/v1/units/{id}/hold`
- `POST /devices/v1/units/{id}/rework`
- `POST /devices/v1/units/{id}/accept`
- `GET /devices/v1/units/by-serial/{serial}`
- `GET /devices/v1/units/{id}/history`
- `GET /devices/v1/lots/{id}/release-readiness`

# 8. Events

- DeviceUnitCreated
- ComponentAssembled
- DeviceTestRecorded
- DeviceInspectionRecorded
- DeviceNonconformanceRaised
- DeviceReworkStarted
- DeviceAccepted
- DeviceScrapped
- DeviceReleased

# 9. UI

1. Device Lot Dashboard
2. Serial/Unit Search
3. Assembly Execution
4. Test Station View
5. Inspection View
6. NCR/Rework
7. Unit History
8. UDI/Label
9. Release Readiness
10. Device History Export

# 10. Integration

- Edge/tester;
- barcode scanners;
- vision inspection;
- label system;
- ERP/WMS;
- sterilization system;
- LIMS if device test routed externally.

# 11. Audit / Signature

Record:
- component installation/removal;
- tests/retests;
- acceptance;
- rework;
- scrap;
- release;
- corrections;
- label/UDI assignment.

Required signatures derive from product/recipe policy.

# 12. Repository Structure

```text
services/gxp-api/src/modules/device-history/
apps/ebmr_frappe/ebmr/device/
contracts/events/device/
validation/requirements/device-history/
```

# 13. Tests

- unit creation;
- duplicate serial;
- component lot trace;
- wrong component;
- tester calibration invalid;
- failed test → NCR;
- retest retains original;
- rework;
- scrap;
- shared evidence inheritance;
- UDI recording;
- batch-to-unit drug linkage;
- high-volume bulk results;
- unit correction;
- device export.

# 14. Acceptance

Representative autoinjector/pen flow must support:
drug constituent link → device components → assembly → functional test → visual inspection → label/UDI → acceptance → combination-product genealogy.

# 15. Codex / Claude Rules

Never treat retest as overwrite.
Never duplicate shared evidence merely to make serial query easy; use immutable references.
Never release serial with unresolved required test/NCR.
Never use historical “DHR” clause assumptions as current QMSR mapping without verified mapping.

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
