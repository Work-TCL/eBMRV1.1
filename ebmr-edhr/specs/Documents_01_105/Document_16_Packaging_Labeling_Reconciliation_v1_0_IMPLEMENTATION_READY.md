# US eBMR / eDHR Regulated Manufacturing Platform
## Document 16 — Packaging, Labeling & Reconciliation Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EBMR-007  
**Parent Documents:** Document 01 v1.1; Document 02 v1.0  
**Primary Dependencies:** Documents 03–15; Materials; Edge; ERP/WMS; UDI/Product profile  
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

Define packaging and labeling controls that prevent mix-ups, preserve exact label/artwork/UDI history, reconcile controlled label quantities, and integrate packaging evidence into the batch/eDHR and final release.

# 2. Functional Requirements

| ID | Functionality | Detailed behavior | Acceptance intent |
|---|---|---|---|
| PKG-FR-001 | Packaging configuration | Use released packaging configuration tied to product/version and packaging level. | Correct materials/process. |
| PKG-FR-002 | Packaging material eligibility | Verify packaging components/material lots are released, correct, unexpired and approved for product. | Wrong packaging blocked. |
| PKG-FR-003 | Label master/version | Reference exact released label/artwork/template version and approved variable-data schema. | No latest-label ambiguity. |
| PKG-FR-004 | Label issuance | Issue controlled quantity/range/job with product/batch/lot/serial scope, label version, operator/system source and time. | Strict issuance trace. |
| PKG-FR-005 | Label examination | Before use/release, verify identity/conformity and required fields; device profiles include applicable UDI, expiration/storage/handling instructions. | Pre-use correctness. |
| PKG-FR-006 | Print integration | Integrate label printer/label management system through adapter; each print job has immutable ID, template version, variable data hash and printer source. | Printed label reproducible. |
| PKG-FR-007 | Reprint | Reprint requires reason, authorization and controlled reprint counter/status; original/reprint history retained. | No uncontrolled duplicate labels. |
| PKG-FR-008 | Serialization | Where required allocate/consume serials/UDI PI values and prevent duplicate assignment. | Unique units. |
| PKG-FR-009 | Line clearance | Require packaging line clearance before start/changeover and capture prior-product/material/label clearance checklist. | Mix-up prevention. |
| PKG-FR-010 | Packaging execution | Record packaging line/equipment, start/end, operators, materials, quantities, inspections and interruptions. | Complete packaging history. |
| PKG-FR-011 | Label application verification | Verify applied label matches product/batch/serial/package; barcode/vision scan preferred where available. | Wrong label detected. |
| PKG-FR-012 | Packaging inspection | Capture visual/automated inspection results and defect/reject code. | Acceptance evidence. |
| PKG-FR-013 | Label reconciliation | Reconcile issued, used, returned, destroyed, rejected and unused label quantities according to released policy. | Discrepancies surfaced. |
| PKG-FR-014 | Reconciliation waiver/profile | Only apply allowed reconciliation exceptions/waivers when specifically configured under applicable rule/profile and alternate examination evidence exists. | No broad waiver. |
| PKG-FR-015 | Excess controlled label destruction | Record destruction of excess lot/control-number labels with quantity, reason and witness/authority where required. | No uncontrolled surplus. |
| PKG-FR-016 | Returned label control | Returned labels maintain identity/status/location to prevent mix-ups. | Reusable stock controlled. |
| PKG-FR-017 | Packaging reconciliation | Reconcile packaging component quantities and finished pack counts, rejects, samples and destruction. | Material balance. |
| PKG-FR-018 | Package hierarchy | Create unit→carton→shipper/pallet hierarchy and genealogy where applicable. | Distribution trace. |
| PKG-FR-019 | Aggregation correction | Wrong aggregation relationship corrected through controlled event preserving original. | Serialization history. |
| PKG-FR-020 | Tamper-evident profile | Where applicable support tamper-evident packaging checks/evidence through product profile. | Profile-specific compliance. |
| PKG-FR-021 | Expiration | Print/capture expiration from released rule/product data; operator cannot free-type controlled expiry unless allowed workflow. | Dating controlled. |
| PKG-FR-022 | UDI | Device/DDCP label execution supports exact DI/PI construction/source and records UDI by device/lot as applicable. | Current device requirement support. |
| PKG-FR-023 | Artwork/spec evidence | Packaging record references approved artwork/specification/version and sample/specimen or image/evidence where configured. | Historical label evidence. |
| PKG-FR-024 | Packaging hold | Line or batch packaging can be held for label/material/equipment/quality issue. | Stop mix-up. |
| PKG-FR-025 | Changeover | Controlled end/start between product/batch/label versions includes clearance and reconciliation closure. | Safe transition. |
| PKG-FR-026 | Rejected packages | Track rejected units/packages, defect reason, rework/scrap disposition and serial status. | No ghost product. |
| PKG-FR-027 | Samples | Account for retained/QC/inspection samples in packaging reconciliation where applicable. | Quantity balance. |
| PKG-FR-028 | Final packaging completion | Cannot complete packaging stage until required inspections, line clearance closure and reconciliations are acceptable/resolved. | Release blocker. |
| PKG-FR-029 | ERP/WMS posting | Post packaged finished quantity/status/reference after GxP commit using adapter and idempotency. | Financial/warehouse sync. |
| PKG-FR-030 | Audit/export | Packaging/label history appears in batch/device record export, including issuance, reprints, reconciliation and inspections. | Inspection-ready. |
| PKG-FR-031 | Electronic record correction | Incorrect captured label/packaging data uses controlled correction, never direct edit. | Data integrity. |
| PKG-FR-032 | Printer/device identity | Printer, scanner, vision system and applicator sources are registered/attributable where automated evidence is used. | Source trusted. |

# 3. Data Model

## `packaging_run`
- batch ID
- product/package configuration version
- line/equipment
- state/version
- start/end
- line-clearance record
- reconciliation state

## `label_issue`

```text
id uuid PK
tenant_id uuid
packaging_run_id uuid
label_version_id uuid
quantity_issued bigint
serial_range/reference jsonb
print_job_id uuid
issued_by/source
issued_at timestamptz
state varchar(40)
```

## `label_reconciliation`
- issued
- applied/used
- returned
- destroyed
- rejected
- samples
- calculated variance
- tolerance rule
- result
- investigation link

## `package_node`
- package level
- serial/SSCC/custom ID
- product/batch
- parent package
- state

# 4. Packaging State

`NOT_READY → LINE_CLEARANCE → READY → IN_PROGRESS → RECONCILIATION_PENDING → COMPLETE`

Alternate:
`HOLD`, `EXCEPTION`, `ABORTED`.

# 5. Label Job Contract

A print job contains:
- exact label template/artwork version ID/hash;
- product version;
- batch/lot;
- serial/UDI variable data;
- quantity/range;
- printer identity;
- requested by;
- idempotency key;
- generated output/evidence hash where supported.

# 6. APIs

- `POST /packaging/v1/runs`
- `POST /packaging/v1/runs/{id}/line-clearance`
- `POST /packaging/v1/runs/{id}/labels/issue`
- `POST /packaging/v1/print-jobs`
- `POST /packaging/v1/labels/{id}/reprint`
- `POST /packaging/v1/runs/{id}/label-application`
- `POST /packaging/v1/runs/{id}/inspection`
- `POST /packaging/v1/runs/{id}/reconcile-labels`
- `POST /packaging/v1/runs/{id}/reconcile-packaging`
- `POST /packaging/v1/runs/{id}/complete`

# 7. Errors

`LINE_CLEARANCE_REQUIRED`, `LABEL_VERSION_INCORRECT`, `LABEL_QUANTITY_EXCEEDED`, `SERIAL_DUPLICATE`, `UDI_INVALID`, `REPRINT_REASON_REQUIRED`, `LABEL_RECONCILIATION_FAILED`, `PACKAGING_MATERIAL_INELIGIBLE`, `WRONG_PRODUCT_LABEL`, `PACKAGE_AGGREGATION_CONFLICT`.

# 8. UI

1. Packaging Run
2. Line Clearance
3. Packaging Materials
4. Label Issuance
5. Print/Reprint
6. Application Verification
7. Inspection
8. Label Reconciliation
9. Packaging Reconciliation
10. Serialization/Aggregation
11. Completion

# 9. Scanner/Vision Integration

Preferred application verification:
- scan printed/applied barcode;
- parse expected identifiers;
- compare product/batch/serial/expiry/UDI;
- record device identity and raw parsed value;
- reject mismatch.

# 10. Reconciliation Formula

Detailed formulas are implemented via Document 08/17.

Packaging module provides source quantities and consumes evaluation result.

# 11. Events

- PackagingRunStarted
- LineClearanceCompleted
- LabelIssued
- LabelPrinted
- LabelReprinted
- LabelApplied
- LabelMismatchDetected
- LabelReconciliationCompleted
- PackagingReconciliationCompleted
- PackageAggregated
- PackagingCompleted

# 12. Repository Structure

```text
services/gxp-api/src/modules/packaging/
apps/ebmr_frappe/ebmr/packaging/
connectors/label-printing/
contracts/events/packaging/
```

# 13. Tests

- correct label;
- wrong label scan;
- obsolete label;
- duplicate serial;
- controlled reprint;
- excessive labels;
- discrepancy outside limit;
- line clearance incomplete;
- label return;
- destruction;
- UDI;
- package aggregation;
- wrong aggregation correction;
- packaging material rejected;
- printer retry/idempotency;
- completion blocker.

# 14. Acceptance

Representative DDCP package flow must demonstrate:
line clearance → approved label version → controlled print/application → serial/UDI link → reconciliation → final package genealogy → release evidence.

# 15. Codex / Claude Rules

Never free-print arbitrary production label from Frappe template editor.
Never allow reprint without trace.
Never let reconciliation discrepancy be hidden by inventory adjustment.
Never use obsolete label version because it is still cached at printer.

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
