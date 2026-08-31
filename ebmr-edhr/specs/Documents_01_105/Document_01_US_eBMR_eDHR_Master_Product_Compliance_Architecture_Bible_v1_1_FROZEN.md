# US eBMR / eDHR Regulated Manufacturing Platform
## Document 01 — Master Product, Compliance & Architecture Bible — v1.1 (FROZEN INPUT BASELINE)

**Initial Market:** Drug–Device Combination Products  
**Expansion 1:** Medical Device Manufacturing  
**Expansion 2:** Pharmaceutical Manufacturing  
**Target Market:** United States  
**Recommended Foundation:** Frappe Framework + Proprietary GxP Core  
**Architecture Goal:** Enterprise-grade, acquisition-ready regulated manufacturing platform  
**Document Status:** FROZEN BASELINE for Document 02 architecture work  
**Frozen Date:** 2026-08-20  
**V1 Primary Vertical:** Drug–Device Combination Products (DDCP)  
**V1 Reference Product Families:** Prefilled syringe, autoinjector, insulin pen, cartridge + injector, inhalation delivery systems, and drug-eluting/coated devices  
**Future Vertical Profiles:** Medical Devices, then Pharmaceuticals  
**Expected Customer Scale:** Up to 4 plants/customer initially; architecture sized with enterprise headroom

---

# 1. PURPOSE OF THIS DOCUMENT

This document defines the master functional, regulatory, data-integrity, security, technical and architectural requirements for a configurable electronic Batch Manufacturing Record / electronic Device History Record platform intended for regulated US manufacturing.

The product is deliberately designed in three vertical layers:

1. Drug–device combination products
2. Medical devices
3. Pharmaceuticals

The system should **not** become three different products.

It should become one regulated manufacturing platform with:

- a common GxP core,
- industry-specific modules,
- product-specific configuration,
- independent ERP/LIMS/equipment connectors,
- and a hardened electronic-record and electronic-signature subsystem.

This Bible should eventually become the parent document from which the following controlled specifications are generated:

- Product Requirements Specification
- User Requirements Specification — URS
- Functional Requirements Specification — FRS
- Software Design Specification — SDS
- Data Model Specification
- Security Specification
- Part 11 Assessment
- Risk Assessment
- Validation/CSA Plan
- Requirements Traceability Matrix
- Test Specifications
- Deployment Qualification Package


## 1.1 FUNCTIONAL DECOMPOSITION RULE — MANDATORY

No functionality in this product may remain only as a high-level feature name when implementation, compliance, security, testing, validation or architecture requires lower-level capabilities.

Every major requirement shall be decomposed using the following hierarchy:

```text
Module
  ↓
Functionality
  ↓
Sub-functionality
  ↓
Detailed behavior
  ↓
Compliance / business reason
  ↓
Frappe responsibility
  ↓
Proprietary eBMR/GxP responsibility
  ↓
Validation / test requirement
```

Where a module becomes too large for this Master Bible, this document shall still:

1. retain the parent requirement and sub-functionality inventory;
2. assign stable requirement IDs;
3. identify the dedicated downstream specification required;
4. cross-reference the dedicated specification from Document 02 and later documents.

This rule applies to all:

- eBMR functions,
- eDHR functions,
- drug-device combination functions,
- medical-device functions,
- pharmaceutical functions,
- QMS,
- QC/LIMS,
- material/procurement,
- equipment,
- security,
- Part 11,
- data integrity,
- audit,
- electronic signatures,
- validation,
- infrastructure,
- integrations,
- AI.

## 1.2 DOCUMENT 01 FROZEN PRODUCT DECISIONS

The following user/product inputs are frozen for the baseline architecture:

| Decision Area | Frozen Decision |
|---|---|
| V1 product strategy | One configurable DDCP platform, not one hardcoded manufacturing flow |
| Reference manufacturing profiles | Injectable drug-delivery systems; inhalation delivery systems; drug-eluting/coated devices |
| Customer documents unavailable | Build representative industry reference BMR/eDHR/document packs and later map customer-specific deltas |
| V1 functional boundary | eBMR + eDHR + compliance + manufacturing QMS required for execution/review/release |
| QMS V1 | Deviation, CAPA, OOS, OOT, NCR, Change Control, Document Control, Training, Supplier Quality, Risk, Complaint, Recall/Field Action, effectiveness controls |
| QC/LIMS | Native basic QC plus generic LIMS adapter |
| Equipment connectivity | Generic Edge Gateway first |
| E-signature | Keycloak-compatible identity abstraction, customer SSO, mandatory step-up authentication for regulated Part 11 signatures |
| Deployment | Dedicated SaaS + private cloud/on-premise from same controlled codebase |
| Cloud | Cloud-neutral container/Kubernetes architecture; AWS and Azure reference deployments first |
| Offline | Local/plant resilience and Edge buffering; no fully disconnected browser/tablet Part 11 execution in V1 |
| Expected scale | Up to 4 plants/customer, 10–15 concurrent users/plant, ~10 batches/day/plant; enterprise headroom required |
| Retention | Configurable by regulated record type; no normal physical deletion of regulated records |
| Architecture style | Modular Frappe application + separately bounded proprietary GxP Core; avoid unnecessary microservice explosion |
| IP | All custom eBMR/GxP code remains proprietary/acquisition-ready; permissive dependencies preferred; SBOM/license register mandatory |
| Validation | Validation-ready DDCP product package in V1; expandable by controlled delta for Device and Pharma profiles |
| AI | Advisory initially; never autonomous authority for regulated release/signature/record alteration |
| Material responsibility | Native regulated procurement/material lifecycle required, while external ERP remains pluggable system-of-record for commercial/financial responsibilities |

---

# 2. FIRST DECISION — IS THERE A BETTER MIT/APACHE BASE THAN FRAPPE?

## 2.1 Candidate comparison

These scores are an architectural assessment for **this specific eBMR/eDHR product**, rather than claims made by the upstream projects.

| Platform | License | Application Platform | Manufacturing | Workflow | Audit/Data history | GxP/Part 11 starting point | Overall fit as eBMR base |
|---|---|---:|---:|---:|---:|---:|---:|
| **Frappe Framework** | MIT | 9.5 | 4 | 9 | 5 | 3 | **8.8/10** |
| Apache OFBiz | Apache-2.0 | 7 | 9 | 6 | 4 | 2 | 7.1/10 |
| Corteza | Apache-2.0 | 8.5 | 2 | 8.5 | 5 | 2 | 7.2/10 |
| openBIS | Apache-2.0 | 6 | 2 | 5 | 8.5 | 5 | 6.5/10 |
| Medplum | Apache-2.0 | 8 | 1 | 7 | 8 | 6 | 6.8/10 |
| Temporal | MIT | Not full app | — | 10 | 9 workflow-history | 4 | Component only |

## Decision

**No permissively licensed single platform identified provides a better overall foundation than Frappe for this product.**

Therefore:

> **Frappe remains the primary application framework.**

But:

> **Frappe must not be treated as the GxP compliance engine.**

---

# 3. REGULATORY BASELINE

For electronic records used to satisfy FDA-regulated record requirements, Part 11 applies alongside the underlying predicate rules.

As of February 2, 2026, medical-device manufacturers operate under FDA's **Quality Management System Regulation (QMSR)**, which incorporates ISO 13485:2016 by reference.

Combination products are particularly important because 21 CFR Part 4 applies drug CGMP requirements when a drug constituent is present and device/QMSR requirements when a device constituent is present.

## 3.1 Regulatory matrix

| Regulation / standard | Combination | Device | Pharma | System relevance |
|---|---:|---:|---:|---|
| **21 CFR Part 11** | ✓ | ✓ | ✓ | Electronic records/signatures |
| **21 CFR Parts 210/211** | ✓ drug constituent | — | ✓ | Drug CGMP |
| **21 CFR Part 820 / QMSR** | ✓ device constituent | ✓ | — | Device QMS |
| **ISO 13485:2016 via QMSR** | ✓ | ✓ | — | Medical-device QMS |
| **21 CFR Part 4** | **✓ core** | — | — | Combination-product CGMP |
| 21 CFR Part 803 | Where applicable | ✓ | — | Device adverse-event reporting |
| 21 CFR Part 806 | Where applicable | ✓ | — | Corrections/removals |
| 21 CFR Part 830 | Where applicable | ✓ | — | UDI |
| 21 CFR Part 821 | Where applicable | Where applicable | — | Device tracking |
| Parts 600–680 | If biologic constituent | — | Biologics | Biological products |
| Part 1271 | If HCT/P constituent | — | Where applicable | Human cells/tissue products |
| FDA Data Integrity principles | ✓ | Relevant | ✓ | Trustworthy electronic data |
| FDA Computer Software Assurance | ✓ device side | ✓ | Useful risk-based practice | Production/QMS software assurance |

---

# 4. PRODUCT ARCHITECTURE PRINCIPLE

The product shall be divided into four major layers.

```text
┌──────────────────────────────────────────────────────┐
│                 EXPERIENCE LAYER                     │
│                                                      │
│ Production | QA | QC | Engineering | Warehouse      │
│ QMS | Management | Auditors                          │
└────────────────────────┬─────────────────────────────┘
                         │
                ┌────────▼────────┐
                │ FRAPPE PLATFORM │
                │      MIT        │
                │                 │
                │ UI / DocTypes   │
                │ Dashboards      │
                │ Reports         │
                │ Workspaces      │
                │ Generic RBAC    │
                │ Notifications   │
                │ APIs            │
                └────────┬────────┘
                         │
             ┌───────────▼────────────┐
             │ PROPRIETARY eBMR CORE  │
             │                        │
             │ Recipe Engine          │
             │ Batch Execution        │
             │ eDHR                   │
             │ Dispensing             │
             │ Equipment              │
             │ Genealogy              │
             │ QA/QC                  │
             │ Review by Exception    │
             │ QMS                    │
             └───────────┬────────────┘
                         │
           ┌─────────────▼───────────────┐
           │   PROPRIETARY GxP CORE     │
           │                             │
           │ E-Signature                 │
           │ Immutable Audit Ledger      │
           │ Record Version Vault        │
           │ Policy Enforcement          │
           │ Regulatory Record Locking   │
           │ Change Reasons              │
           │ Data Integrity              │
           │ Compliance Events           │
           └──────────────┬──────────────┘
                          │
       ┌──────────────────┼──────────────────┐
       ↓                  ↓                  ↓
 Enterprise IAM      ERP / LIMS        Factory Gateway
 Keycloak/IdP        Connectors        PLC/SCADA/Lab
```


## 4.1 V1 DDCP MANUFACTURING PROFILE ARCHITECTURE

The products included in the V1 roadmap do **not** share one identical manufacturing process. The system shall therefore use a common regulated execution core with configurable manufacturing profiles rather than one hardcoded BMR workflow.

```text
                    DDCP COMMON CORE
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
      PROFILE A       PROFILE B      PROFILE C
      Injectable      Inhalation     Drug-Eluting/
      Drug Delivery   Delivery       Coated Device

      Prefilled       MDI/DPI        Drug-eluting
      Syringe         Nasal          stent/catheter/
      Autoinjector    Other          implant/coated
      Insulin Pen                    device
      Cartridge+
      Injector
```

### Common engine reused by every profile

- product/constituent master;
- material/component master;
- released specifications;
- master recipe/manufacturing instruction;
- batch/lot execution;
- eDHR-style device production history;
- equipment eligibility;
- personnel qualification;
- dispensing/material usage;
- process parameters;
- IPC/QC;
- genealogy;
- deviation;
- OOS/OOT;
- CAPA;
- nonconformance;
- electronic signatures;
- audit trail;
- record locking;
- QA review;
- disposition/release;
- inspection-ready export.

### Profile A — Injectable Drug-Delivery Systems

Required sub-functional coverage:

- formulation/bulk preparation where applicable;
- component preparation;
- sterile component readiness;
- filling;
- container closure;
- stoppering/plunger placement;
- syringe/cartridge assembly;
- device assembly;
- needle/shield/cap handling where applicable;
- visual inspection;
- leak/container-closure tests where applicable;
- functional testing;
- labeling;
- packaging;
- final combination-product genealogy;
- release.

### Profile B — Inhalation Delivery Systems

Required sub-functional coverage:

- formulation/blending/filling where applicable;
- canister/capsule/reservoir component control;
- metering-device assembly;
- actuator/device assembly;
- dose-delivery testing;
- leak testing where applicable;
- device functional tests;
- labeling/packaging;
- drug-batch-to-device-lot genealogy;
- release.

### Profile C — Drug-Eluting / Drug-Coated Devices

Required sub-functional coverage:

- device substrate/component genealogy;
- coating/formulation preparation;
- coating application;
- process parameter recording;
- drying/curing;
- coating weight/thickness where applicable;
- drug load/content verification;
- device inspection/testing;
- sterilization linkage where applicable;
- packaging;
- UDI/lot/serial linkage where applicable;
- final release.

### Profile validation principle

The common platform shall be validated as a reusable baseline. Each manufacturing profile shall then have its own profile-specific requirements, risks and test evidence. Customer-specific configurations shall be handled through controlled delta assessment/validation rather than modifying the core architecture.

**Dedicated future specifications required:**

- SPEC-DDCP-A — Injectable Drug-Delivery Manufacturing Profile
- SPEC-DDCP-B — Inhalation Delivery Manufacturing Profile
- SPEC-DDCP-C — Drug-Eluting / Coated Device Manufacturing Profile


---

# 5. COMMON FUNCTIONAL CORE

These capabilities are required across combination products, pharmaceuticals and medical devices.

## 5.1 Organization, facility and production structure

| ID | Functionality | What it does / Why required | Frappe / proprietary implementation |
|---|---|---|---|
| C-001 | Organization & Legal Entity | Represents the regulated manufacturer, business entity and operating organization responsible for records. It separates corporate ownership from manufacturing sites and forms the root of authorization, reporting and retention policies. | **Frappe DocTypes** will model Organization and Legal Entity. GxP records must additionally carry immutable organization/site identifiers so historical records do not change if master data is renamed. |
| C-002 | Manufacturing Site | Represents each FDA-regulated manufacturing facility. All batches, equipment, personnel, warehouses and quality events must belong to a defined site. | Frappe handles site master, relationships and permissions. Proprietary GxP records store a snapshot of the site identity at execution time. |
| C-003 | Building / Area / Room / Line | Creates the physical manufacturing hierarchy required to determine where each regulated operation took place. Supports contamination controls, equipment location and authorized-area rules. | Frappe hierarchical DocTypes. GxP execution engine validates whether the operation is permitted in the selected area. |
| C-004 | Department / Function | Defines Production, QA, QC, Warehouse, Engineering and other organizational functions. Required for responsibilities and segregation of duties. | Frappe Role and Department models plus proprietary policy mappings. |
| C-005 | Shift Management | Records production shifts and associates operators and activities with the active shift. Useful for investigations, operational reviews and traceability. | Frappe master + scheduling. Actual execution timestamps remain server-authoritative within GxP Core. |

---

# 6. IDENTITY, PEOPLE AND QUALIFICATION

| ID | Requirement | Description | Implementation |
|---|---|---|---|
| C-006 | Unique User Identity | Every human must use a unique identity. Shared Production, QA or Admin accounts must not be permitted for regulated actions. | Frappe users may represent identities, but **enterprise identity should preferably be delegated to Keycloak, Entra ID or customer IdP**. |
| C-007 | Role Based Access | Determines what operators, supervisors, QA, QC, engineering and administrators may see and perform. | Frappe has native user/role permission support. Proprietary GxP Core independently validates critical actions rather than trusting UI permissions alone. |
| C-008 | Segregation of Duties | Prevents conflicting activities, for example an operator independently approving their own exception or QA release where independent review is required. | Custom policy engine. Frappe roles provide inputs, but GxP Core performs final authorization. |
| C-009 | Employee Qualification | Associates users with qualifications such as dispensing operator, sterile-area operator, QA reviewer or specific equipment authorization. | Frappe DocTypes hold training/qualification information. Execution engine validates current qualification before allowing a step. |
| C-010 | Training Status | Links SOP/training requirements to users and their effectiveness or completion status. Expired/missing training can automatically block applicable activities. | Frappe document/workflow layer + proprietary execution gate. |
| C-011 | Temporary Authorization | Supports documented temporary qualification or emergency access with start/end date, justification and approval. | Custom Frappe workflow with mandatory GxP signature and audit event. |


## 6.1 STANDARD ROLE MODEL

The system shall ship with configurable reference roles rather than hardcoding customer-specific role names.

### Enterprise / IT

- Enterprise Administrator
- Site Administrator
- Application Administrator
- Security Administrator
- Integration Service Account
- Read-only Auditor / Inspector

### Production

- Production Manager
- Production Supervisor
- Operator
- Dispensing Operator
- Packaging Operator

### Quality Assurance

- Head of Quality
- QA Manager
- QA Reviewer
- QA Approver / Batch Release
- Deviation Investigator
- CAPA Owner

### Quality Control

- QC Manager
- QC Analyst
- Sampler

### Warehouse / Material

- Warehouse Manager
- Material Receiver
- Material Issuer
- Material Handler

### Procurement / Supplier Quality

- Procurement Manager
- Buyer
- Supplier Quality Manager / Engineer

### Engineering

- Engineering Manager
- Maintenance Technician
- Calibration Technician
- Equipment Administrator

### QMS Support

- Document Controller
- Training Coordinator
- Complaint Investigator
- Internal Auditor

## 6.2 SEGREGATION-OF-DUTIES SUB-FUNCTIONALITIES

The policy engine shall support:

- performer cannot verify the same controlled action where independent verification is required;
- verifier cannot be substituted silently after execution;
- production performer cannot perform independent QA release where prohibited by customer procedure;
- authors cannot approve their own released master record where configured;
- system administrators cannot create regulatory signatures on behalf of users;
- security administrators cannot alter released batch content;
- emergency access must be time-limited, reason-coded and independently reviewed;
- incompatible role combinations shall be configurable and reportable;
- every privilege elevation shall be audited;
- periodic access review reports shall be available.

**Dedicated future specification required:** Identity, Authorization, Qualification & Segregation-of-Duties Specification.

---

# 7. PRODUCT, MATERIAL AND SPECIFICATION MASTER

| ID | Functionality | Description | Implementation |
|---|---|---|---|
| C-012 | Product Master | Defines product identity, code, dosage/device configuration, manufacturing type, lifecycle status and associated regulatory configuration. | Frappe DocType. Released GxP master versions are separately frozen in GxP Core. |
| C-013 | Raw Material Master | Defines APIs, excipients, components, packaging materials and device components used during manufacturing. | Frappe DocType; ERP synchronization through adapters. |
| C-014 | Specification Master | Stores approved specifications including acceptable ranges, units, methods and effective periods. | Draft authoring in Frappe; released specification becomes an immutable version in the Record Vault. |
| C-015 | Unit of Measure | Defines controlled units and conversion rules. Prevents uncontrolled textual units and calculation ambiguity. | Frappe UOM capability/custom masters. Conversion algorithms belong to tested domain services. |
| C-016 | Supplier / Manufacturer | Identifies manufacturer/supplier sources for received materials and components. | Frappe or ERP adapter. GxP execution stores supplier/manufacturer snapshots where required. |
| C-017 | Material Quality Status | Supports quarantine, sampled, under-test, approved, rejected, expired and other controlled states. | Frappe fields/workflows display status; Quality Status Engine performs controlled transitions and prevents unauthorized consumption. |
| C-018 | Expiry / Retest | Tracks expiry/retest dates and automatically prevents use when material validity has elapsed. | Frappe stores dates; GxP Material Service performs enforcement at dispensing/consumption. |

---


# 7A. REGULATED PROCUREMENT & MATERIAL MANAGEMENT — V1

V1 shall include the material lifecycle required to support compliant eBMR execution. It shall **not** attempt to replace full financial ERP/accounting.

## 7A.1 Procurement lifecycle

```text
Supplier
   ↓
Supplier Qualification
   ↓
Approved Supplier List
   ↓
Purchase Requisition
   ↓
RFQ / Supplier Quote (optional by customer)
   ↓
Purchase Order
   ↓
Material Receipt / GRN
   ↓
Quarantine
   ↓
Sampling / QC
   ↓
Released / Rejected
   ↓
Warehouse
   ↓
Issue / Dispensing
   ↓
Consumption / Return
   ↓
Reconciliation
   ↓
Batch Genealogy
```

## 7A.2 Required procurement and material sub-functionalities

| ID | Functionality | Required sub-functionalities | Primary implementation |
|---|---|---|---|
| MAT-001 | Supplier Master | supplier identity; manufacturer identity; addresses; status; approved materials; qualification links; regulatory certificates; effective status | Frappe master + QMS links |
| MAT-002 | Supplier Qualification | qualification request; questionnaire; audit; risk classification; approval; expiry/requalification; suspension; disqualification | QMS workflow + GxP signatures |
| MAT-003 | Approved Supplier List | material-to-approved-supplier relationship; site applicability; effective dates; exceptions; change history | Frappe configuration + GxP versioning |
| MAT-004 | Purchase Requisition | requester; material/specification version; required quantity/date; site; approval; ERP synchronization | Frappe/native procurement |
| MAT-005 | RFQ / Supplier Quote | RFQ issue; quote receipt; commercial comparison; supplier selection; attachment retention | Native module; non-GxP financial aspects may stay ERP |
| MAT-006 | Purchase Order | material/spec version; supplier/manufacturer; quantity; delivery terms; approval; ERP synchronization | Native regulated procurement or ERP adapter |
| MAT-007 | Material Receipt / GRN | PO match; received quantity; manufacturer lot; supplier lot; internal lot; container IDs; receipt date; damage inspection | Material service + warehouse UI |
| MAT-008 | COA Management | COA attachment; supplier test values; document authenticity metadata; version; review; discrepancy handling | Frappe documents + GxP audit |
| MAT-009 | Quarantine | automatic quarantine at receipt; location restriction; status labels; access control | Material Status Engine |
| MAT-010 | Sampling | sampling plan; sample quantity; sampler; sample IDs; container selection; chain of custody; LIMS transfer | QC/Sample module |
| MAT-011 | QC Disposition | pending; released; rejected; conditional/use-under-deviation if allowed; retest; expiry/retest | QC + Quality Status Engine |
| MAT-012 | Warehouse/Location | warehouse; zone; bin; environmental requirement; restricted area; status segregation | Frappe/ERP adapter |
| MAT-013 | FEFO / Eligibility | expiry/retest; released status; site; product applicability; reservation; blocked lot; deviation override | GxP Material Eligibility Engine |
| MAT-014 | Material Reservation | batch reservation; quantity; expiry; release; conflict handling | Inventory service |
| MAT-015 | Material Issue | issue to batch/area; scan verification; lot/container; quantity; operator | Inventory + genealogy |
| MAT-016 | Material Dispensing | target; tolerance; balance; actual quantity; verifier; potency adjustment; labels | Dispensing Engine |
| MAT-017 | Material Return | unused quantity; container state; return location; status reevaluation | Material service |
| MAT-018 | Inventory Adjustment | controlled adjustment; reason; independent approval where required; audit | GxP Mutation Gateway |
| MAT-019 | Destruction | destruction request; authorization; quantity; witness; method; evidence | QMS/material disposition |
| MAT-020 | Reconciliation | received/issued/dispensed/consumed/returned/destroyed variance; tolerance; exception | Reconciliation Engine |
| MAT-021 | Material Genealogy | supplier/manufacturer lot → internal lot → container → batch → finished product | Genealogy Service |
| MAT-022 | ERP Synchronization | master sync; PO sync; inventory quantity/value sync; consumption posting; retry/reconciliation | Adapter layer |

## 7A.3 System-of-record boundary

If the customer has SAP, Oracle, Dynamics, ERPNext or another ERP:

- ERP may remain authoritative for commercial PO, financial inventory valuation, accounts payable and accounting.
- eBMR remains authoritative for regulated receipt evidence, quality status, eligibility, dispensing, actual consumption evidence and manufacturing genealogy.
- Integration must support reconciliation and conflict handling.

If the customer has no suitable ERP, the native regulated procurement/material module may operate independently.

**Explicit V1 exclusions:** General Ledger, tax accounting, banking, accounts payable financial settlement and complete corporate accounting.

**Dedicated future specifications required:** Procurement & Supplier Quality Specification; Material Inventory & Dispensing Specification.

# 8. MASTER RECIPE / MANUFACTURING SPECIFICATION

| ID | Functionality | Description | Implementation |
|---|---|---|---|
| C-019 | Master Manufacturing Record | Defines the controlled manufacturing instructions from which executable batches are created. It includes materials, quantities, sequence, parameters, instructions, checks and signatures. | Authoring UI in Frappe. Once approved, GxP Core produces immutable Released Master Version. |
| C-020 | Recipe Version Control | Every released recipe is permanently identifiable. A new change creates a new version instead of altering the record used by previous batches. | Frappe manages draft workflow. GxP Version Vault stores immutable released snapshot/hash. |
| C-021 | Effective Dating | Defines when a recipe/specification may begin and cease being used. Prevents users from manually choosing obsolete versions. | Frappe configuration + GxP effective-date rules. |
| C-022 | Structured Steps | Every operation is represented as a structured executable step instead of uncontrolled free text. | Frappe child/linked DocTypes define steps. Proprietary Execution Engine interprets them. |
| C-023 | Step Dependencies | Defines which step must be completed before another begins and supports conditional/parallel branches. | **Proprietary execution graph.** Temporal may optionally provide durable orchestration. |
| C-024 | Parameter Definitions | Defines target, minimum, maximum, precision, unit, required evidence and source of each process parameter. | Frappe recipe authoring; GxP Rules Engine enforces execution. |
| C-025 | Calculation Definitions | Defines controlled calculations such as potency correction, yield, reconciliation and unit conversions. | Formula definition may be configured in Frappe, but executable calculation library must be version-controlled, tested and released as software. |
| C-026 | Instruction Versioning | Ensures the instruction displayed during manufacturing is exactly the approved instruction associated with that batch version. | Frozen recipe snapshot rendered by GxP service; no live reference to mutable master text. |

---

# 9. BATCH / LOT EXECUTION

| ID | Requirement | Description | Implementation |
|---|---|---|---|
| C-027 | Batch Creation | Creates the executable manufacturing instance using an approved product/recipe/version and target quantity. | Frappe initiation screen → GxP Batch Service. |
| C-028 | Unique Batch Number | Generates a unique controlled identifier and prevents duplicates or silent reuse. | Naming service; may integrate ERP numbering but GxP Core enforces uniqueness. |
| C-029 | Frozen Batch Snapshot | Once created, the batch captures the exact recipe/specification version used. Subsequent master-data changes cannot silently affect execution. | **Proprietary immutable snapshot mechanism.** |
| C-030 | Batch Lifecycle | Supports states such as Planned → Issued → In Execution → Production Complete → QA Review → Released/Rejected → Closed. | Frappe visual workflow; GxP state machine is authoritative. |
| C-031 | Step-by-Step Execution | Presents only valid executable steps and captures required results/evidence before completion. | Custom Frappe/React execution UI calling GxP Execution API. |
| C-032 | Sequence Enforcement | Prevents a user from bypassing required steps unless a specifically authorized exception path exists. | GxP Execution Engine. |
| C-033 | Pause / Resume | Allows controlled suspension caused by hold, equipment issue, shift change or investigation without losing state. | GxP state machine; Temporal is attractive for durable long-running execution. |
| C-034 | Parallel Operations | Allows valid simultaneous manufacturing activities while preserving dependencies. | Proprietary execution graph/Temporal workflow. |
| C-035 | Conditional Operations | Branches manufacturing based on results, product configuration or approved predefined conditions. | Rules Engine; conditions versioned with recipe. |
| C-036 | Automatic Exception | Out-of-limit or unexpected values automatically create/block/route exceptions instead of relying on operator judgment alone. | GxP Rules + Quality Event Service. |
| C-037 | Production Hold | Authorized personnel can place batch/step/material on hold with reason and signature. | Frappe display; GxP policy/state transition. |
| C-038 | Controlled Resume | Hold release requires defined disposition and authorized signature. | GxP E-Signature + execution state transition. |

---

# 10. MATERIAL DISPENSING AND CONSUMPTION

| ID | Requirement | Description | Implementation |
|---|---|---|---|
| C-039 | Material Requirement | Determines required component, target quantity and allowable alternatives from approved recipe. | GxP Recipe Service. ERP may provide inventory information. |
| C-040 | Lot Selection | Only eligible released lots may be selected. Expired, rejected, quarantined or wrong-material lots are blocked. | ERP inventory adapter + GxP Material Eligibility Engine. |
| C-041 | Barcode Scanning | Verifies material, lot/container and location to reduce manual identification errors. | Custom scanner UI; hardware/browser integration. |
| C-042 | Weighing Integration | Captures weight directly from validated balances where available instead of transcription. | Edge/Instrument Gateway, not Frappe itself. |
| C-043 | Manual Weight Entry | Permits controlled manual entry where necessary with source identification and optional independent verification. | Frappe execution UI + GxP validation/signature rules. |
| C-044 | Potency Adjustment | Applies approved calculation where active material quantity depends on potency/assay. | Validated calculation service. |
| C-045 | Material Consumption | Associates exact quantities and lots with specific batch steps. | GxP genealogy + ERP inventory transaction connector. |
| C-046 | Return / Excess | Records unused returned quantities and reconciles them to issued quantities. | GxP reconciliation plus ERP movement connector. |
| C-047 | Material Reconciliation | Ensures issued = consumed + returned + approved loss within defined tolerance. | Proprietary Reconciliation Engine. |

---

# 11. EQUIPMENT & FACILITY CONTROLS

| ID | Requirement | Description | Implementation |
|---|---|---|---|
| C-048 | Equipment Master | Identifies production, packaging and laboratory equipment. | Frappe master. |
| C-049 | Equipment Status | Available / in-use / cleaning / maintenance / calibration-due / out-of-service etc. | Frappe display + Equipment Eligibility Engine. |
| C-050 | Calibration Control | Prevents use of equipment when required calibration is overdue or invalid. | Calibration DocTypes + hard execution gate in GxP Core. |
| C-051 | Qualification | Stores IQ/OQ/PQ or applicable qualification status/evidence. | Frappe-controlled documentation + execution eligibility. |
| C-052 | Cleaning Status | Tracks cleaning state and relevant cleaning records. | Custom equipment lifecycle service. |
| C-053 | Line Clearance | Ensures previous product/material/documents are cleared before defined manufacturing/packaging operations. | eChecklist + signature/verification workflow. |
| C-054 | Maintenance | Tracks preventive/corrective maintenance affecting equipment availability. | Frappe or external CMMS integration. |
| C-055 | Equipment Usage Log | Automatically associates equipment with each batch/operation. | GxP Audit/Genealogy services. |
| C-056 | Electronic Equipment Data | Captures machine values such as speed, temperature, pressure or torque where applicable. | Edge Gateway/PLC/SCADA historian integration. |

---


# 11A. STERILE / ASEPTIC MANUFACTURING CAPABILITY — V1 ARCHITECTURAL REQUIREMENT

Sterile/aseptic capability shall be present in the architecture from V1 because injectable DDCP profiles may require it. It shall be enabled only for applicable customer/product profiles.

## 11A.1 Required sub-functionalities

| ID | Functionality | Required sub-functionalities | Implementation |
|---|---|---|---|
| ST-001 | Classified Area Master | cleanroom classification; room/zone; allowed operations; qualification status; effective dates | Frappe master + GxP eligibility |
| ST-002 | Environmental Monitoring Linkage | viable monitoring; non-viable particles; temperature; humidity; differential pressure; alert/action limits; excursion linkage | Edge/LIMS/EM adapter + GxP evidence |
| ST-003 | Personnel Gowning Qualification | qualification type; training; expiry; area eligibility; suspension | Training/Qualification Engine |
| ST-004 | Aseptic Operator Qualification | media-fill/aseptic qualification reference; validity; operation eligibility | Qualification Engine |
| ST-005 | Cleaning & Sanitization | procedure/version; agent; concentration; performed by; verified by; time; status | Equipment/area lifecycle |
| ST-006 | Sterilization Status | equipment/component sterilization cycle; load; parameters; cycle result; release status | Equipment/sterilization service |
| ST-007 | CIP/SIP Linkage | recipe/cycle; parameters; equipment path; cycle result; exception | Edge/Equipment integration |
| ST-008 | Filter Management | filter ID; type; batch/lot; installation; pre-use check; integrity test; post-use result; disposition | Specialized process module |
| ST-009 | Sterile Component Readiness | sterilization status; expiry/hold time; packaging integrity; release | Material Eligibility Engine |
| ST-010 | Bioburden Linkage | sample; method; result; limit; LIMS evidence; batch impact | QC/LIMS |
| ST-011 | Sterility Test Linkage | sample; test; result; status; investigation link | LIMS/QC |
| ST-012 | Media Fill Reference | line/process qualification; date; result; validity; applicable personnel/equipment | Validation/Qualification module |
| ST-013 | Intervention Recording | planned/unplanned intervention; time; operator; location; reason; impact | Batch Execution + Audit |
| ST-014 | Aseptic Hold Time | start; maximum allowed duration; timer; alert; excursion | Rules/Execution Engine |
| ST-015 | Bulk Hold Time | material/bulk start/end; temperature/storage condition; limit; exception | Rules Engine |
| ST-016 | Filling Parameters | target fill; actuals; speed; line settings; rejects; in-process checks | Execution + Edge |
| ST-017 | Stoppering/Sealing | component verification; parameter capture; inspection; reject reason | Execution Engine |
| ST-018 | Container Closure Integrity | test reference; sample/result; acceptance; batch impact | QC/LIMS |
| ST-019 | Environmental Excursion | automatic quality event; affected time window; affected batch/units; investigation | Quality Event Engine |
| ST-020 | Sterile Batch Impact Assessment | evidence aggregation; unresolved excursion; qualification status; release blocking | Release Engine |

**Dedicated future specification required:** Sterile & Aseptic Manufacturing Specification.

# 12. IN-PROCESS CONTROL AND QUALITY

| ID | Requirement | Description | Implementation |
|---|---|---|---|
| C-057 | In-Process Check | Defines samples/tests/checks required during production. | Frappe definitions; GxP execution. |
| C-058 | Acceptance Limits | Automatically determines pass/fail/exception against approved specification. | Rules Engine. |
| C-059 | Sample Identification | Creates traceable sample IDs connected to product/batch/step/material/equipment. | QC service + optional LIMS connector. |
| C-060 | QC Results | Captures or receives laboratory results. | Lightweight Frappe QC or external LIMS integration. |
| C-061 | OOS | Manages out-of-specification investigation without deleting the original result. | Proprietary QMS module. |
| C-062 | OOT | Supports out-of-trend investigation where configured. | Proprietary QMS analytics/workflow. |
| C-063 | Result Supersession | Original values are never silently overwritten. Corrections create new controlled values linked to the original and reason. | GxP Record/Audit Core. |
| C-064 | Batch Impact Assessment | Determines whether quality events block continued production or final release. | Quality Event + Release Engine. |

---

# 13. YIELD AND RECONCILIATION

| ID | Requirement | Description | Implementation |
|---|---|---|---|
| C-065 | Theoretical Yield | Calculates expected output using released recipe parameters. | Validated calculation engine. |
| C-066 | Actual Yield | Calculates output from recorded manufacturing results. | GxP calculation engine. |
| C-067 | Yield Percentage | Compares actual and theoretical quantities according to controlled formula. | GxP calculation engine. |
| C-068 | Yield Limits | Automatically creates exception if yield falls outside approved tolerance. | Rules + Quality Event Engine. |
| C-069 | Packaging Reconciliation | Reconciles issued, used, returned, destroyed and rejected packaging/labels. | Proprietary reconciliation module. |

---

# 14. ELECTRONIC SIGNATURE — CRITICAL PROPRIETARY COMPONENT

For regulated electronic signatures, the architecture shall support:

| Requirement | Implementation |
|---|---|
| Unique signer | Identity permanently tied to individual user. |
| Identity verification | Customer organization verifies user identity before electronic-signature assignment. |
| Signature meaning | Review, Perform, Verify, Approve, Release, Reject, Author, etc. |
| Date/time | Server-generated controlled timestamp. |
| Record linkage | Signature includes immutable record ID + version + hash. |
| Step-up authentication | Critical signature invokes authentication challenge rather than relying simply on existing browser session. |
| Authentication control | Designed consistent with applicable Part 11 identification-component requirements. |
| Signature manifestation | Printed name, timestamp and meaning appear on screen and human-readable exported record. |
| Signature non-transferability | Signature cannot simply be copied to another version/document. |
| Revocation | User can be disabled; existing historical signatures remain valid historical records. |

### Recommended implementation

Enterprise identity may be supplied by **Keycloak**, Microsoft Entra ID, Okta or the customer's identity provider.

However:

> Identity infrastructure authenticates the signer.  
> **Your GxP Signature Service creates the regulated signature record.**

Signature record example:

```text
Signature ID
User immutable ID
Printed signer name
Record ID
Record version
Record hash
Action/meaning
Date/time UTC
Authentication assurance/method
Session/challenge ID
Reason/comment where applicable
Signature-service version
```

---

# 15. IMMUTABLE AUDIT TRAIL — CRITICAL PROPRIETARY COMPONENT

Frappe's standard versioning/audit functions are useful operational capabilities but shall not be treated as the regulated GxP audit ledger.

## Audit event should include

```text
event_id
tenant/site
sequence
record_type
record_id
record_version
action
actor_id
actor_name
role
timestamp_utc
source
old_value
new_value
change_reason
signature_id
device/session
correlation_id
previous_event_hash
current_event_hash
```

## Rules

- Append only.
- No UPDATE of audit event.
- No DELETE through application.
- Privileged DBA actions independently monitored.
- Audit records retained for the required period.
- Old/new information preserved.
- Corrections do not destroy previous data.
- Reason for regulated changes required.
- Audit records available to QA/auditors.
- Audit trail exportable with record.

## Architecture

```text
Frappe / Device / API
        │
        ▼
 GxP Mutation Gateway
        │
        ├── Validate
        ├── Authorize
        ├── Business rule
        └── Record reason
        │
        ▼
 Transaction / Outbox
        │
        ├── Business Record
        │
        └── Audit Event
                │
                ▼
          Append-Only Ledger
```

For additional tamper evidence, audit events may be hash chained.

Cryptographic hash chaining is an architectural hardening control, **not itself an FDA requirement and not a substitute for Part 11 controls, validation or procedural governance.**

---

# 16. RECORD LOCKING AND VERSION VAULT

| Function | Requirement |
|---|---|
| Draft | Editable under permissions. |
| Executing | Only execution-authorized fields/actions may change. |
| Completed | Production inputs locked except controlled correction path. |
| QA Review | QA annotations/actions permitted; production result values protected. |
| Released | Regulatory record permanently frozen. |
| Corrected | Original remains; controlled correction/superseding record created. |
| Cancelled/Voided | Historical object retained with reason/status. |

Final regulatory locking shall be enforced by the GxP Core, not simply by Frappe UI state or DocStatus.

---

# 17. REVIEW BY EXCEPTION

Instead of asking QA to manually read every field of a large batch record, the system shall automatically identify:

- deviations,
- OOS/OOT,
- missing values,
- late steps,
- manual overrides,
- parameter excursions,
- failed signatures,
- changed values,
- equipment status exceptions,
- material exceptions,
- missing attachments,
- unresolved comments,
- reconciliation failures,
- abnormal process data,
- integration failures.

QA receives:

```text
Batch Summary
     ↓
Exceptions
     ↓
Critical Evidence
     ↓
Audit Trail
     ↓
QA Decision
```

This becomes a major commercial differentiator.

Implementation is primarily proprietary analytics/business logic; Frappe supplies dashboards, list/report interfaces and review screens.

---

# 18. DOCUMENT CONTROL

| Requirement | Implementation |
|---|---|
| SOP Master | Frappe authoring metadata + controlled file repository |
| Version number | GxP version model |
| Effective date | Document lifecycle |
| Approval | E-sign service |
| Obsolete state | Version vault retains history |
| Training impact | Training assignments automatically generated |
| Controlled copy | Watermarked/export-controlled generated file |
| Retrieval | Searchable by authorized users |
| Change history | Audit ledger |
| Review interval | Scheduled workflow |

Production document editing should **not** be performed through uncontrolled Frappe customization.

---

# 19. QMS MODULES COMMON TO THE PLATFORM — V1

V1 includes the manufacturing-quality functions required to execute, investigate, review and release DDCP production. It is not limited to only deviation/CAPA/OOS.

| ID | Module | Required sub-functionalities | Implementation boundary |
|---|---|---|---|
| QMS-001 | Deviation | planned/unplanned; initiation; source; classification; severity; immediate correction; containment; investigation; root cause; batch/material/equipment impact; disposition; approvals; extension; closure; trending | Frappe UI/workflow + GxP state/signature/audit |
| QMS-002 | CAPA | initiation; source linkage; problem statement; root cause; corrective action; preventive action; owners; due dates; implementation evidence; effectiveness criteria; effectiveness result; extension/escalation; closure | QMS service + GxP Core |
| QMS-003 | OOS | original result retention; Phase I laboratory review; investigation; retest authorization; resampling authorization; manufacturing investigation; root cause; batch impact; disposition; closure | QC/QMS + immutable result history |
| QMS-004 | OOT | trend rule; detection; historical comparison; investigation; root cause; impact; action; closure | Analytics + QMS |
| QMS-005 | Nonconformance | source; component/material/device/product; segregation; evaluation; disposition; rework/scrap/use-as-is if procedurally permitted; approval; closure | NCR module + Material/Device status |
| QMS-006 | Change Control | change request; reason; affected objects; regulatory impact; validation impact; risk; implementation plan; approval; effective date; training impact; post-implementation verification; closure | Change Control + Version Vault |
| QMS-007 | Document Control | authoring metadata; review; approval; version; effective date; supersession; controlled copy; periodic review; archival; training impact | Frappe docs + Version Vault + E-sign |
| QMS-008 | Training & Qualification | curriculum; role requirement; SOP assignment; completion; quiz/effectiveness; qualification; expiry; retraining; suspension; execution blocking | Frappe + Qualification Engine |
| QMS-009 | Supplier Quality | qualification; risk rating; approved supplier list; audit; performance; quality agreement reference; SCAR; requalification; suspension | Supplier Quality module |
| QMS-010 | SCAR | supplier issue; evidence; containment; supplier response; root cause; corrective action; effectiveness; closure | QMS workflow |
| QMS-011 | Risk Management | hazard/risk item; probability/severity or customer methodology; control; residual risk; linked change/deviation/CAPA/product/process; review | Risk module |
| QMS-012 | Internal Audit | audit plan; scope; checklist; auditor; findings; classification; response; CAPA link; follow-up; closure | Audit module |
| QMS-013 | Complaint | intake; product/lot/serial identification; complainant; event details; seriousness; constituent classification; investigation; reportability assessment; CAPA; closure | Complaint module |
| QMS-014 | Recall / Field Action | initiation; affected product determination; genealogy query; distribution scope; action classification; customer communication evidence; reconciliation; closure | Genealogy + Regulatory Action module |
| QMS-015 | Effectiveness Check | measurable criterion; due date; evidence; result; extension; failure escalation; CAPA re-open/new CAPA | QMS shared function |
| QMS-016 | Quality Metrics & Trending | deviation trends; OOS/OOT trends; CAPA aging; repeat issues; complaint trends; supplier quality; batch release cycle; configurable dashboards | Analytics/reporting |
| QMS-017 | Quality Event Linking | many-to-many links among deviation/CAPA/OOS/OOT/NCR/complaint/change/batch/material/equipment/personnel/document | Quality Event graph |
| QMS-018 | Quality Event Escalation | severity-based notification; overdue; repeat event; critical event; management escalation | Rules/Notification Engine |

## 19.1 QMS architectural rule

Frappe may provide forms, lists, dashboards and non-authoritative workflow presentation.

The GxP Core shall control:

- critical state transitions,
- signature requirements,
- reason-for-change,
- immutable event history,
- released/closed record locking,
- cross-record impact relationships,
- batch-release blocking.

**Dedicated future specifications required:** Deviation & Investigation; CAPA; OOS/OOT; Change Control; Document Control; Training & Qualification; Supplier Quality; Complaint/Postmarket; Risk Management.


---

# 20. DRUG–DEVICE COMBINATION PRODUCT MODULE

This is **Version 1** and should drive the first production architecture.

## 20.1 Combination-specific functionality

| ID | Functionality | Why it is required | Implementation |
|---|---|---|---|
| CP-001 | Combination Product Master | Defines the finished combination product and links all constituent parts. | Frappe master + frozen GxP version. |
| CP-002 | Constituent Classification | Identifies drug, device, biologic, HCT/P or other applicable constituent. | Regulatory configuration schema. |
| CP-003 | Drug Constituent Version | Tracks exact formulation/batch/specification incorporated into combination product. | GxP genealogy. |
| CP-004 | Device Constituent Version | Tracks exact device configuration/component/lot/serial incorporated. | Device genealogy. |
| CP-005 | Cross-Constituent Genealogy | Allows finished product to be traced backwards through both drug and device supply chains. | **Proprietary Genealogy Engine.** |
| CP-006 | Combined Manufacturing Route | Controls filling, assembly, device integration, packaging and other cross-domain operations. | Execution graph. |
| CP-007 | Constituent Facility Tracking | Identifies where separately manufactured constituents were produced and when the combined system begins. | Site/genealogy model. |
| CP-008 | Interface Critical Parameters | Controls parameters related specifically to drug-device interface, e.g. fill volume, delivery mechanism or assembly characteristics. | Recipe/parameter engine. |
| CP-009 | Device UDI + Drug Batch Link | Links serialized/UDI-bearing device identity with drug batch/lot where applicable. | Genealogy/UDI service. |
| CP-010 | Combination Packaging | Controls packaging involving both regulated constituent identities. | Packaging module. |
| CP-011 | Combination Labeling | Builds controlled labeling information from released constituent/product data. | Controlled Label Service. |
| CP-012 | Unified Deviation | One event can affect drug constituent, device constituent and final combination product simultaneously. | Quality Event graph. |
| CP-013 | Cross-Constituent CAPA | Allows CAPA to reference affected constituent/process/product records. | QMS relationship model. |
| CP-014 | Unified Release | Final product cannot release until all constituent and final-product requirements are satisfied. | Release/Disposition Engine. |
| CP-015 | Cross-Functional Approval | Supports Production, Device Quality, Drug Quality and final QA decision where organizational procedure requires it. | E-signature + workflow. |
| CP-016 | Expiration Determination | Maintains final expiry information supported by applicable constituent/product requirements. | Rule-controlled released data. |
| CP-017 | Stability Linkage | Links applicable drug/combination stability information. | LIMS/QC integration. |
| CP-018 | Reserve Sample Linkage | Supports required drug-product reserve-sample records where applicable. | Sample/LIMS module. |
| CP-019 | Combination Complaint | Complaint can be classified as drug, device, combination/interface or unknown cause. | QMS complaint engine. |
| CP-020 | Recall Impact Analysis | One constituent lot can identify all affected finished combination-product lots/serials. | Genealogy graph query. |

## 20.2 Part 4 streamlined-path controls

For a device+drug combination using a QMSR-based operating system, additional drug-CGMP functions may include:

- component/container testing and approval/rejection,
- yield calculation,
- applicable tamper-evident packaging,
- expiration dating,
- testing and release,
- stability testing,
- special testing,
- reserve samples.

These functions must be represented explicitly in the Combination Product profile even if the first customer's existing QMS is device-centric.

---


# 20A. DDCP POSTMARKET QUALITY / SAFETY SUPPORT — V1

V1 shall support the manufacturing/QMS evidence needed for combination-product complaint and postmarket assessment. Direct electronic submission to FDA may be implemented as a later connector.

## Required sub-functionalities

| ID | Functionality | Required sub-functionalities |
|---|---|---|
| PM-001 | Complaint Intake | product; lot; serial/UDI; constituent; complainant; event date; narrative; attachments; source |
| PM-002 | Constituent Classification | drug-related; device-related; interface-related; combined; unknown |
| PM-003 | Seriousness / Criticality Assessment | configurable regulatory/quality assessment; immediate escalation; medical review link where required |
| PM-004 | Reportability Assessment | assessment workflow; rationale; reviewer; due-date tracking; evidence |
| PM-005 | Investigation | batch history; device history; manufacturing deviations; QC; equipment; complaints; genealogy evidence |
| PM-006 | Affected Product Search | lot/serial/UDI; constituent lot; material lot; supplier lot; distribution relationship |
| PM-007 | CAPA Link | complaint → CAPA; repeat issue detection; effectiveness |
| PM-008 | Field Action / Recall | affected scope; hold; notification evidence; reconciliation; closure |
| PM-009 | Postmarket Audit Trail | all assessment changes/signatures/reasons preserved |
| PM-010 | Regulatory Submission Adapter | future connector interface for FDA/customer reporting systems |

**Dedicated future specification required:** Combination Product Complaint, Postmarket Assessment & Field Action Specification.

# 21. MEDICAL DEVICE MANUFACTURING PROFILE

The second product release adds the full device-manufacturing profile.

| ID | Functionality | Description / Need | Implementation |
|---|---|---|---|
| MD-001 | Device Master | Defines device family/model/configuration and lifecycle status. | Frappe master + GxP release. |
| MD-002 | Production Specification | Defines released device manufacturing configuration. | Version Vault. |
| MD-003 | eDHR-Style Record | Electronic production history showing how the unit/lot was manufactured and accepted. | Reuse eBMR Execution Engine with device profile. |
| MD-004 | Serial Number | Unique serial-level production tracking. | Genealogy service. |
| MD-005 | Lot Number | Lot-level traceability where serialized tracking is not sufficient/applicable. | Genealogy service. |
| MD-006 | UDI | Stores/associates device identifiers and production identifiers where applicable. | Dedicated UDI service. |
| MD-007 | Component Traceability | Determines exact components/assemblies used in finished units. | Genealogy graph. |
| MD-008 | Supplier Control | Links qualified supplier status to incoming components. | Supplier Quality module. |
| MD-009 | Incoming Acceptance | Inspection/testing before component acceptance. | QC module. |
| MD-010 | Assembly Execution | Controlled sequential device assembly steps. | Common execution engine. |
| MD-011 | Test Equipment | Test station and instrument association. | Equipment Gateway. |
| MD-012 | Device Test Result | Captures pass/fail and raw/evidence values. | QC/test service. |
| MD-013 | Process Validation Link | Associates validated processes and applicable versions with production steps. | Validation Master. |
| MD-014 | Sterilization | Where applicable, records sterilization batch/cycle and relevant linkage. | Specialized execution/integration profile. |
| MD-015 | Environmental Conditions | Captures relevant manufacturing environmental conditions. | Monitoring integration. |
| MD-016 | Nonconforming Product | Identifies, segregates and disposes nonconforming material/product. | NCR module. |
| MD-017 | Rework | Executes only approved rework route while retaining original manufacturing history. | Controlled rework recipe. |
| MD-018 | Final Acceptance | Confirms defined manufacturing/test requirements are completed. | Release Engine. |
| MD-019 | Label/Packaging Control | Controls device labeling/packaging operations. | Label service + execution engine. |
| MD-020 | Complaint Record | Captures complaint evaluation/investigation information. | QMS Complaint module. |
| MD-021 | Servicing | Records service operations where applicable. | Device service module. |
| MD-022 | MDR Assessment | Determines whether a complaint/event should enter MDR reporting workflow. | Regulatory QMS module. |
| MD-023 | Corrections / Removals | Manages field corrections/removals where applicable. | Regulatory action module. |
| MD-024 | Device Tracking | Supports additional tracking requirements for applicable devices. | Genealogy/regulatory profile. |
| MD-025 | Device Risk Linkage | Links manufacturing nonconformities/deviations/process changes to controlled product/process risk objects. | Risk module. |

---

# 22. PHARMACEUTICAL MANUFACTURING PROFILE

| ID | Functionality | Description / Need | Implementation |
|---|---|---|---|
| PH-001 | Master Production & Control Record | Controlled manufacturing formula/instruction record. | Recipe Engine + Version Vault |
| PH-002 | Batch Production Record | Complete execution history for each batch. | eBMR Execution Engine |
| PH-003 | Component Control | Approved/rejected/quarantine component lifecycle. | Material Quality Service |
| PH-004 | Component Testing | Supports receipt, sampling/testing and release decisions. | QC/LIMS |
| PH-005 | Container / Closure | Controls applicable containers/closures and their approved status. | Material/specification system |
| PH-006 | Material Identity | Prevents incorrect component use. | Barcode + eligibility engine |
| PH-007 | Component Weighing | Controlled dispensing/verification. | Dispensing Engine |
| PH-008 | Yield Calculation | Theoretical/actual yield at defined manufacturing phases. | Calculation Engine |
| PH-009 | Equipment Identification | Records significant equipment used. | Equipment genealogy |
| PH-010 | Production Sequence | Enforces written manufacturing procedure. | Execution Engine |
| PH-011 | In-Process Controls | Captures required process checks/testing. | IPC module |
| PH-012 | Time Limit Control | Enforces defined time windows between/process operations where applicable. | Rules/Temporal scheduler |
| PH-013 | Microbial Controls | Supports records/checks for applicable microbiological contamination controls. | Specialized recipe/QC profile |
| PH-014 | Reprocessing | Controlled QA-approved reprocessing procedure with full history. | Rework/Reprocess Engine |
| PH-015 | Packaging | Controlled packaging operations. | Packaging module |
| PH-016 | Label Issuance | Controlled label generation/issuance. | Label service |
| PH-017 | Label Reconciliation | Accounts for issued/used/returned/destroyed labels. | Reconciliation Engine |
| PH-018 | Tamper Evidence | Supports applicable tamper-evident packaging requirements. | Packaging profile |
| PH-019 | Warehousing | Controlled storage status/location/environment where applicable. | ERP/WMS integration |
| PH-020 | Distribution Traceability | Links distributed product to lot/batch. | ERP + genealogy |
| PH-021 | Laboratory Controls | Manages/references testing specifications, methods and results. | LIMS integration/QC |
| PH-022 | Release Testing | Ensures required testing/acceptance before release. | Release Engine |
| PH-023 | Stability | Links stability program/results. | LIMS/stability module |
| PH-024 | Special Testing | Supports special testing requirements based on product/process. | Configurable QC workflow |
| PH-025 | Reserve Samples | Tracks reserve samples and retention. | Sample module |
| PH-026 | Laboratory Record | Maintains complete test/result evidence. | LIMS + GxP audit |
| PH-027 | Batch QA Review | Supports review of production and control records. | Review-by-Exception |
| PH-028 | Complaint | Captures drug-product complaint and investigation. | QMS Complaint module |
| PH-029 | Returned Drug | Controls received returned drug and disposition. | Return workflow |
| PH-030 | Salvage / Destruction | Controlled decision and traceability for salvage/destruction. | Disposition Engine |

---

# 23. PART 11 COMPLIANCE REQUIREMENTS

| Control | Frappe native? | Final design |
|---|---:|---|
| Unique users | Strong | Frappe/Keycloak |
| RBAC | Strong | Frappe + GxP authorization |
| System validation | No framework can supply customer validation | CSA/validation program |
| Complete record copies | Partial | GxP Export Service |
| Retention | Configurable | Record Vault + retention policy |
| Time-stamped audit | Partial | **GxP Audit Ledger** |
| Old information preserved | Partial | **Immutable versions** |
| Operational sequencing | Custom | **Execution Engine** |
| Authority checks | Strong basis | GxP policy service |
| Device/input checks | Custom | Edge/Input Validation |
| Electronic signature | Insufficient natively | **E-Sign Service** |
| Signature manifestation | Custom | **E-Sign Service** |
| Signature/record linkage | Custom | Record hash/version binding |
| Reason for change | Custom | GxP mutation API |
| Training controls | Custom | Training/Qualification |
| Documentation change control | Development process | Git + SDLC/QMS |
| Inspection-ready export | Custom | Regulatory Export Service |

---

# 24. DATA INTEGRITY REQUIREMENTS

The architecture shall enforce:

| Principle | System control |
|---|---|
| Attributable | Identity on every regulated event |
| Legible | Human-readable record/export |
| Contemporaneous | Controlled server/device timestamps |
| Original | Original record retained |
| Accurate | Validations and controlled calculations |
| Complete | No selective deletion of adverse/failed data |
| Consistent | Sequenced events/time/order |
| Enduring | Long-term archival |
| Available | Timely retrieval |
| Traceable corrections | Audit trail and reason |
| Metadata preservation | Source, unit, device, user, timestamp |
| Failed result preservation | Supersede rather than erase |
| Unauthorized deletion prevention | Policy + immutable storage |

---

# 25. SECURITY MASTER REQUIREMENTS

## 25.1 Identity and authorization

| Security requirement | Implementation |
|---|---|
| Unique users | Mandatory |
| MFA | Mandatory for privileged users; recommended enterprise-wide |
| Step-up authentication | Mandatory for designated electronic signatures |
| SSO | OIDC/SAML |
| AD/LDAP | Through customer IdP/Keycloak |
| RBAC | Frappe roles |
| Fine-grained authorization | GxP policy layer; OPA may be evaluated |
| Separation of duties | Policy rules |
| Privileged account management | Dedicated roles/PAM |
| No shared regulated accounts | Hard policy |
| Service accounts | Non-human identity, minimum privileges |
| Periodic access review | Compliance report/workflow |

## 25.2 Application security

- Server-side authorization on every regulated mutation.
- Never rely on hidden buttons/disabled fields as security.
- Strict input validation.
- CSRF protection.
- XSS prevention.
- SQL-injection prevention.
- Secure file upload scanning.
- Malware scanning.
- API rate limiting.
- API scopes.
- Idempotency for critical integration calls.
- Replay protection.
- Signed integration messages where necessary.
- Security headers.
- Session timeout.
- Authentication-event monitoring.

Regulated mutation endpoints should be wrapped by the proprietary GxP gateway instead of exposing uncontrolled generic CRUD.

## 25.3 Infrastructure security

- TLS everywhere.
- Encryption at rest.
- Managed encryption keys.
- Key rotation.
- Secret vault.
- Network segmentation.
- Database inaccessible from public internet.
- Private service communication.
- WAF/API gateway.
- IDS/IPS where appropriate.
- Central logging.
- SIEM integration.
- EDR for applicable hosts.
- Hardened containers/VMs.
- Immutable infrastructure where practical.
- Backup encryption.
- Immutable/WORM backup copies.
- Multi-region/off-site backup.
- Restore testing.
- Defined RPO/RTO.
- Disaster-recovery exercises.

## 25.4 Development security

- Mandatory pull requests.
- Independent code review.
- Protected main/release branches.
- Signed/versioned releases.
- SAST.
- DAST.
- Software composition analysis.
- Dependency vulnerability scanning.
- Secret scanning.
- Container scanning.
- SBOM generation.
- Patch program.
- Security regression testing.
- Penetration testing.
- Vulnerability management and SLA.
- Change-control linkage.

---

# 26. CRITICAL RULE — NO UNCONTROLLED FRAPPE CUSTOMIZATION IN PRODUCTION

For a validated production environment:

```text
Production users must NOT be able to:

❌ Create regulated DocTypes
❌ Change regulated fields
❌ Modify workflow logic
❌ Add arbitrary Server Scripts
❌ Add arbitrary Client Scripts
❌ Change calculations
❌ Change approval rules
❌ Change GxP permissions
❌ Modify released print/export templates
```

Changes must follow:

```text
Change Request
      ↓
Impact Assessment
      ↓
Requirement
      ↓
Git Branch
      ↓
Code Review
      ↓
Automated Testing
      ↓
Validation Impact
      ↓
Approved Release
      ↓
Controlled Deployment
```

---

# 27. PROPRIETARY GxP CORE — YOUR MOST IMPORTANT IP

This is the 30–40% that should distinguish the product from a customized Frappe application.

## 27.1 GxP Mutation Gateway

All regulated create/change/approve/release operations pass through one controlled API.

It performs:

1. authentication,
2. authorization,
3. state validation,
4. business-rule validation,
5. required-reason validation,
6. e-signature challenge where required,
7. record version creation,
8. audit-event creation,
9. transaction/outbox,
10. immutable storage acknowledgement.

Frappe must never independently modify finalized GxP records.

## 27.2 Electronic Signature Service

Responsible for:

- signer verification,
- step-up authentication,
- signing meaning,
- signature timestamp,
- record/version/hash binding,
- signature manifestation,
- signature evidence,
- non-transferability.

## 27.3 Audit Ledger Service

Responsible for:

- append-only regulatory history,
- before/after values,
- reasons,
- actor identity,
- timestamps,
- signature association,
- correlation with machine/API actions,
- audit-trail search/export.

## 27.4 Record Version Vault

Responsible for permanently preserving:

- released recipes,
- specifications,
- batch snapshots,
- approved documents,
- released batch records,
- signed reports,
- original values,
- superseded versions.

## 27.5 Execution Orchestrator

Responsible for:

- step sequencing,
- dependencies,
- parallel operations,
- conditional logic,
- timers,
- holds,
- resumes,
- retries,
- equipment checks,
- qualification checks,
- material checks,
- exception generation.

Temporal is an optional component for workflow durability, but regulatory record truth must remain in the GxP Record/Audit services rather than using Temporal history itself as the regulatory batch record.

## 27.6 Genealogy Service

This should be a proprietary cross-domain graph:

```text
Supplier
  ↓
Material Lot
  ↓
Drug Batch
  ↓
Device Component
  ↓
Device Lot / Serial
  ↓
Combination Product
  ↓
Finished Lot
  ↓
Packaging
  ↓
Distribution
```

Queries must work both directions.

Examples:

> Which finished products contain raw-material lot RM-28372?

> For serial CP-009182, show every constituent lot, component and manufacturing operation.

## 27.7 Regulatory Rules Engine

Should answer:

```text
Can this action occur?

Is material allowed?

Is equipment valid?

Is operator qualified?

Is recipe effective?

Is verification required?

Does this value trigger deviation?

Can batch continue?

Can batch release?

What signatures are required?
```

Rules should be versioned and tested.

Do **not** allow arbitrary customer Python code to determine critical compliance behavior.

## 27.8 Release / Disposition Engine

One service determines whether product is eligible for:

- release,
- rejection,
- hold,
- rework,
- reprocessing,
- destruction,
- return,
- other controlled disposition.

It must evaluate unresolved exceptions, QC, materials, signatures, equipment, reconciliation and configured product requirements.

---

# 28. FACTORY / LAB INTEGRATION ARCHITECTURE

```text
PLC
SCADA
Historian
Balance
Barcode
Vision
Tester
Environmental Monitor
Laboratory Instrument
        │
        ▼
   EDGE GATEWAY
        │
        ├─ Source authentication
        ├─ Timestamp
        ├─ Buffering
        ├─ Validation
        ├─ Unit normalization
        ├─ Device identity
        └─ Data-quality status
        │
        ▼
 Integration Gateway
        │
        ▼
      GxP Core
```

Frappe should display this data.

Frappe should **not** be responsible for industrial-protocol acquisition.

---

# 29. ERP / LIMS INTEGRATION ARCHITECTURE

Never hard-code eBMR against ERPNext.

Use interfaces.

```text
InventoryProvider
MaterialProvider
PurchaseProvider
ManufacturingProvider
WarehouseProvider
QualityProvider
```

Adapters:

```text
ERPNextAdapter
SAPAdapter
OracleAdapter
DynamicsAdapter
CustomerERPAdapter
```

Likewise:

```text
LIMSProvider
    ├─ LabWare
    ├─ STARLIMS
    ├─ openBIS
    └─ Customer LIMS
```

---

# 30. MULTI-TENANCY / CUSTOMER ISOLATION

For serious US regulated customers, preferred deployment is:

```text
Customer A
 ├ Frappe Application
 ├ GxP Core
 ├ Operational Database
 ├ Audit Ledger
 └ Dedicated Storage

Customer B
 ├ Frappe Application
 ├ GxP Core
 ├ Operational Database
 ├ Audit Ledger
 └ Dedicated Storage
```

Maintain one codebase but support isolated environments.

Do not make shared-database multi-tenancy a mandatory architectural dependency for enterprise life-science customers.

---


# 30A. FROZEN DEPLOYMENT, DATABASE, OFFLINE & SCALE TARGETS

## 30A.1 Deployment model

The same controlled product codebase shall support:

1. dedicated SaaS deployment;
2. customer private-cloud deployment;
3. customer on-premise deployment.

Large regulated customers should normally receive isolated application/database/storage environments rather than shared regulated databases.

## 30A.2 Cloud model

Software shall remain cloud-neutral using containers/Kubernetes-compatible deployment patterns.

Reference deployments shall be developed first for:

- AWS;
- Microsoft Azure.

Cloud-specific managed services may be used behind abstraction/configuration boundaries and shall not become mandatory for core GxP behavior.

## 30A.3 Database split

Frozen baseline:

```text
Frappe Application Layer
        │
      MariaDB
        │
  Controlled APIs/events
        │
        ▼
Proprietary GxP Core
        │
    PostgreSQL
        │
  ┌─────┼─────────┐
  │     │         │
Audit  GxP       Genealogy/
Ledger Records   Evidence Index
```

The exact storage technology for immutable archival/WORM evidence is an infrastructure design decision for Document 02.

## 30A.4 Offline / resilience rule

### Supported in V1

- plant-local/private deployment can continue when internet/WAN connectivity fails;
- Edge Gateway buffers equipment/instrument data locally;
- buffered events retain source identity, timestamp, ordering and data-quality metadata;
- synchronization is controlled and audited after connectivity returns.

### Not supported in V1

Fully disconnected browser/tablet execution with later synchronization of Part 11 signatures is excluded from V1.

The architecture shall preserve extension points for future controlled offline execution if justified by customer need.

## 30A.5 Scale targets

| Dimension | Expected initial use | Architecture design target |
|---|---:|---:|
| Plants/customer | Up to 4 | 10+ |
| Concurrent users/plant | 10–15 | 50 |
| Concurrent users/customer | ~60 | 250+ |
| Batches/day/plant | ~10 | 50+ |
| Steps/batch | Customer-specific | 1,000 normal; several thousand technically supported |
| Equipment/data sources | Initially limited | Hundreds/site |
| Retention | Configurable | 10+ year-capable architecture, customer/regulation configurable |
| Audit volume | Moderate initially | Millions of events/day possible without redesign |
| Serialized device records | Product-specific | High-volume serial/lot genealogy supported |

High-frequency telemetry shall **not** be stored as individual Frappe DocType records. Relevant evidence/results are referenced from appropriate historian/time-series/object storage with source, timestamp, quality and integrity metadata.

# 31. CONFIGURATION MODEL

The same product should support all three markets using configuration profiles.

```text
CORE PLATFORM
│
├── COMMON GxP
│
├── COMBINATION PRODUCT PROFILE
│
├── DEVICE PROFILE
│
└── PHARMA PROFILE
```

No forking customer code unless absolutely necessary.

---

# 32. CUSTOMER-CONFIGURABLE VS CODE-CONTROLLED

## Customer configurable

- sites,
- departments,
- products,
- equipment,
- materials,
- users,
- roles within approved model,
- limits,
- recipes,
- SOPs,
- workflows within validated configuration boundaries,
- reports,
- notification recipients.

## Code-controlled

- e-signature algorithms,
- audit implementation,
- authorization engine,
- record locking,
- mutation gateway,
- genealogy algorithms,
- formula execution framework,
- released-document hashing,
- compliance-event generation,
- security controls,
- integration security,
- database migration logic.

---

# 33. COMPUTER SOFTWARE ASSURANCE / VALIDATION

A software supplier cannot simply declare a customer's implementation “FDA validated.”

Your company should provide a **validation-ready product package**.

Required development/validation evidence should include at minimum:

| Artifact | Product responsibility |
|---|---|
| Intended Use | Yes |
| Product Requirements | Yes |
| URS template | Yes |
| Functional Specification | Yes |
| Architecture Specification | Yes |
| Data Model | Yes |
| Risk Assessment | Yes |
| Security Risk Assessment | Yes |
| Part 11 Assessment | Yes |
| Requirements Traceability | Yes |
| Automated Test Evidence | Yes |
| Critical Functional Tests | Yes |
| Negative Tests | Yes |
| Security Tests | Yes |
| Installation/Deployment qualification support | Yes |
| Release Notes | Yes |
| Known Issues | Yes |
| Validation Summary | Yes |
| Change Impact Assessment | Every release |
| Regression Evidence | Every release |
| SBOM | Every release |
| Backup/Restore test evidence | Yes |
| Disaster Recovery test evidence | Yes |

Customer/site-specific validation remains dependent on configured intended use, procedures and environment.


## 33.1 DDCP V1 validation package

The V1 product shall provide a validation-ready baseline covering:

- Intended Use Statement;
- Product Requirements;
- User Requirements template;
- Functional Requirements;
- System Architecture;
- Detailed Design;
- Data Model;
- Part 11 Assessment;
- Part 4 Compliance Matrix;
- 21 CFR Parts 210/211 mapping applicable to the DDCP profile;
- QMSR / ISO 13485 mapping applicable to the device constituent;
- Data Integrity Assessment;
- Security Risk Assessment;
- GxP Functional Risk Assessment;
- Requirements Traceability Matrix;
- Test Specifications;
- automated test evidence;
- critical positive tests;
- negative/abuse tests;
- electronic-signature tests;
- audit-trail tests;
- record-locking/correction tests;
- backup/restore tests;
- disaster-recovery tests;
- installation/deployment qualification support;
- operational qualification support;
- customer performance/UAT templates;
- Validation Summary;
- release notes;
- known issues;
- change-impact assessment;
- regression evidence;
- SBOM;
- third-party license register.

## 33.2 Expansion validation strategy

Future Medical Device and Pharma profiles shall use controlled delta validation:

```text
Validated Common Core
      +
New Vertical Requirements
      +
New/Changed Risks
      +
New/Changed Tests
      =
Controlled Profile Validation Delta
```

The full common platform is not revalidated from zero without cause; impact assessment determines regression scope.


---

# 34. INSPECTION-READY RECORD EXPORT

A regulator/auditor must be able to retrieve a complete record without reconstructing it from dozens of database tables.

Export package should contain:

```text
Batch Cover
Product
Recipe Version
Material Lots
Dispensing
Equipment
Process Steps
Parameters
IPC
QC Results
Exceptions
Deviations
Reprocessing
Yield
Reconciliation
Packaging
Labels
Electronic Signatures
QA Review
Release
Audit Trail
Attachments
Machine Evidence
```

Generate:

- human-readable PDF,
- structured electronic export,
- manifest,
- attachment package,
- integrity checksums.


## 34.1 Reference DDCP Manufacturing Record Pack

Until a real customer document pack is supplied, product development shall use representative regulated records and forms including:

### Master / controlled documents

- Product Master
- Combination Product Master
- Constituent Product Master
- Master Manufacturing Record / Master Production & Control Record
- Device production specification / device master information
- Master Formula / Recipe
- Bill of Materials
- Material Specification
- Component Specification
- Packaging Specification
- Label Specification
- Equipment Specification
- Process Parameter Specification
- Sampling / QC Specification
- Cleaning / Sterilization Procedure reference

### Executed batch/device records

- Batch Manufacturing Record
- eDHR-style Device Production History
- Material Receipt / Quality Status evidence
- Dispensing Sheet
- Equipment Usage Record
- Cleaning / Line Clearance Record
- Sterilization/Aseptic evidence where applicable
- In-Process Control Sheet
- QC Result Set
- Environmental Monitoring evidence where applicable
- Yield Calculation
- Material Reconciliation
- Packaging Record
- Label Issuance/Reconciliation
- Device Functional/Test Record
- Deviation/OOS/OOT/NCR links
- CAPA links where applicable
- QA Review
- Batch/Device Release
- Electronic Signature Manifest
- Audit Trail
- Genealogy Report
- Attachments/Machine Evidence Manifest

Customer-specific documents shall later be mapped to this canonical model and treated as controlled configuration/delta requirements rather than forcing customer-specific forks.


---

# 35. AVAILABILITY AND DISASTER RECOVERY

The system should define per-customer:

- uptime objective,
- RPO,
- RTO,
- backup frequency,
- restore procedure,
- failover architecture,
- offline-production behavior,
- edge buffering,
- degraded-mode rules.

For production operations, loss of the SaaS connection must never silently cause loss of regulated machine data.

Where offline execution is allowed, define exactly:

- which operations can continue,
- how identity is established,
- how signatures work,
- how timestamps are protected,
- how events are synchronized,
- how conflicts are resolved.

---

# 36. AI POLICY

AI must initially be **advisory**, not the unreviewed authority for regulated manufacturing decisions.

Recommended first AI functions:

- batch review assistance,
- anomaly detection,
- deviation summarization,
- historical similarity search,
- root-cause evidence retrieval,
- SOP lookup,
- natural-language batch queries,
- manufacturing trend analysis.

AI should **not initially autonomously**:

- alter released recipe,
- release batch,
- sign record,
- erase data,
- disposition product,
- change specifications,
- close deviation,
- modify regulated audit history.

AI actions affecting regulated records must pass through the same GxP Mutation Gateway as human/API actions.

---

# 37. DEVELOPMENT REPOSITORY STRUCTURE

Recommended conceptual architecture:

```text
platform/
│
├── frappe/
│
├── ebmr_app/
│   ├── common/
│   ├── combination/
│   ├── device/
│   ├── pharma/
│   ├── qms/
│   ├── qc/
│   └── integrations/
│
├── gxp_core/
│   ├── audit/
│   ├── signature/
│   ├── record_vault/
│   ├── authorization/
│   ├── mutation_gateway/
│   ├── rules/
│   ├── execution/
│   ├── genealogy/
│   ├── release/
│   └── evidence/
│
├── edge_gateway/
│
├── connectors/
│   ├── erpnext/
│   ├── sap/
│   ├── oracle/
│   ├── dynamics/
│   ├── lims/
│   └── equipment/
│
├── validation/
│   ├── requirements/
│   ├── risks/
│   ├── traceability/
│   ├── tests/
│   └── releases/
│
└── infrastructure/
```

---

# 38. WHAT FRAPPE IS ALLOWED TO DO

Frappe should provide:

- application UI,
- standard forms,
- DocTypes,
- workspaces,
- dashboards,
- reports,
- non-critical workflow presentation,
- notification framework,
- user/role integration,
- CRUD for non-regulated configuration,
- attachment interface,
- APIs,
- admin screens,
- integration presentation.

---

# 39. WHAT FRAPPE MUST NOT BE SOLELY RESPONSIBLE FOR

Do not rely only on Frappe for:

- Part 11 electronic signatures,
- final authorization of critical GxP actions,
- immutable audit trail,
- regulatory record locking,
- released master-record integrity,
- change-reason enforcement,
- batch-execution durability,
- cross-product genealogy,
- WORM archival,
- industrial data acquisition,
- cybersecurity monitoring,
- customer validation,
- disaster recovery.

---

# 40. RECOMMENDED PERMISSIVE COMPONENT STACK

## Core

**Frappe Framework — MIT**

Use for application foundation.

## Identity

**Keycloak — Apache-2.0**

Use where appropriate for:

- OIDC,
- SAML,
- OAuth,
- MFA,
- WebAuthn,
- step-up authentication,
- enterprise federation.

## Durable Workflow

**Temporal — MIT**

Evaluate for:

- manufacturing workflows lasting hours/days,
- timers,
- waits,
- retries,
- crash recovery,
- orchestration.

## Policy

**Open Policy Agent — Apache-2.0 — optional**

Potential use:

```text
Can QA_USER_42
release
BATCH_19272
at SITE_3
given unresolvedDeviationCount=0?
```

## Scientific/LIMS integration reference

**openBIS — Apache-2.0**

Good optional integration/reference for scientific data, lab inventory and data provenance, but not the main application foundation.

---

# 41. IMPORTANT LICENSE WARNING

Do not automatically adopt a project simply because older material describes it as MIT or Apache licensed.

Licenses must be checked **at the exact version/commit selected for the product**.

Every dependency must have a maintained:

```text
Third-Party Software Register
├ Package
├ Version
├ Repository
├ License
├ Copyright
├ Modification status
├ Distribution obligations
└ Approval
```

This will matter significantly in future acquisition due diligence.

---

# 42. PRODUCT RELEASE STRATEGY

## V1 — Drug–Device Combination Product

V1 is a **Regulated DDCP Manufacturing Platform**, not only an electronic form replacement.

### V1 common platform

- Frappe application layer
- proprietary eBMR/eDHR domain core
- proprietary GxP Compliance Core
- identity/SSO integration
- Part 11 signature service
- immutable audit ledger
- record version vault
- controlled mutation gateway
- rules/policy engine
- execution orchestrator
- genealogy service
- release/disposition engine
- regulatory export service

### V1 manufacturing

- Combination Product Master
- constituent product management
- released recipe/version control
- eBMR execution
- eDHR-style device production history
- batch/lot/serial management
- material procurement
- supplier qualification
- receiving/quarantine
- inventory/status
- sampling/basic QC
- LIMS adapter
- dispensing/weighing architecture
- equipment/calibration/qualification
- line clearance
- cleaning
- sterile/aseptic-ready architecture
- IPC
- calculations/yield
- material and packaging reconciliation
- packaging
- labeling
- combination genealogy
- QA review
- release/disposition
- inspection-ready export

### V1 QMS

- deviation
- CAPA
- OOS
- OOT
- nonconformance
- change control
- document control
- training/qualification
- supplier quality / SCAR
- risk management
- internal audit
- complaint
- recall/field action
- effectiveness checks
- quality metrics/trending

### V1 integration/infrastructure

- generic Edge Gateway
- ERP adapter abstraction
- LIMS adapter abstraction
- AWS reference deployment
- Azure reference deployment
- private-cloud/on-prem deployment pattern
- edge buffering/local resilience
- security/monitoring integration boundaries
- validation-ready release package

### V1 reference manufacturing profiles

1. Injectable drug-delivery systems
2. Inhalation delivery systems
3. Drug-eluting/coated devices

**This release must establish the reusable architecture.**

It shall not be implemented as a temporary one-customer special case.

## V2 — Medical Device

Reuse:

```text
Common Platform
GxP Core
E-Signatures
Audit
Execution
Genealogy
QMS
Equipment
QA
Integration
```

Add:

- broader device configuration,
- eDHR,
- UDI,
- serial traceability,
- supplier quality,
- incoming acceptance,
- nonconformance,
- process validation,
- device labeling,
- service,
- complaint/MDR/correction-removal workflows as product scope requires.

## V3 — Pharmaceutical

Reuse common platform and add deeper:

- pharma recipe/formulation,
- potency calculations,
- dispensing,
- packaging,
- stability,
- reserve samples,
- laboratory controls,
- microbiological/sterile profiles,
- time-limit controls,
- reprocessing,
- returns/salvage,
- pharma-specific reporting.

---

# 43. COMMERCIAL PRODUCT POSITIONING

Do not position this simply as:

> eBMR Software

Long-term product category should be:

# Regulated Manufacturing Execution & Quality Platform

Modules:

```text
Platform
│
├── eBMR
├── eDHR
├── MES
├── QMS
├── QC/LIMS Integration
├── Equipment
├── Material Traceability
├── Genealogy
├── Document Control
├── Training
├── Electronic Signatures
├── Audit & Compliance
├── Validation
├── Analytics
└── AI
```

---


# 43A. REQUIRED DOWNSTREAM DEDICATED SPECIFICATIONS

The following modules are too large to be safely defined only in this Master Bible. Document 01 remains the parent requirement source, but dedicated specifications shall be created and cross-referenced.

| Spec ID | Dedicated specification |
|---|---|
| SPEC-GXP-001 | GxP Mutation Gateway |
| SPEC-GXP-002 | Part 11 Electronic Signature |
| SPEC-GXP-003 | Immutable Audit Ledger & Audit Review |
| SPEC-GXP-004 | Record Version Vault, Locking & Controlled Corrections |
| SPEC-EBMR-001 | Master Recipe / Manufacturing Instruction |
| SPEC-EBMR-002 | Batch Execution & State Machine |
| SPEC-EBMR-003 | Review by Exception & Batch Release |
| SPEC-EBMR-004 | Genealogy & Traceability |
| SPEC-MAT-001 | Procurement & Supplier Quality |
| SPEC-MAT-002 | Inventory, Dispensing & Reconciliation |
| SPEC-QC-001 | Basic QC, Sampling & LIMS Integration |
| SPEC-QMS-001 | Deviation & Investigation |
| SPEC-QMS-002 | CAPA |
| SPEC-QMS-003 | OOS / OOT |
| SPEC-QMS-004 | Change Control |
| SPEC-QMS-005 | Document Control |
| SPEC-QMS-006 | Training & Qualification |
| SPEC-QMS-007 | Complaint / Postmarket / Recall |
| SPEC-QMS-008 | Risk Management |
| SPEC-EQP-001 | Equipment, Calibration, Cleaning & Qualification |
| SPEC-ASEPTIC-001 | Sterile / Aseptic Manufacturing |
| SPEC-EDGE-001 | Edge Gateway & Equipment/Instrument Connectivity |
| SPEC-IAM-001 | Identity, Authorization & Segregation of Duties |
| SPEC-INT-001 | ERP Adapter Architecture |
| SPEC-INT-002 | LIMS Adapter Architecture |
| SPEC-SEC-001 | Security Architecture & Threat Model |
| SPEC-VAL-001 | CSA / Validation Package Architecture |
| SPEC-DDCP-A | Injectable Drug-Delivery Manufacturing Profile |
| SPEC-DDCP-B | Inhalation Delivery Manufacturing Profile |
| SPEC-DDCP-C | Drug-Eluting / Coated Device Manufacturing Profile |

Document 02 shall define the architecture boundaries and dependency map for all of these specifications.

# 44. FINAL PLATFORM DECISION

## Do not

- build the entire platform from zero;
- fork ERPNext;
- modify ERPNext core;
- rely on ERPNext as the regulatory system;
- put all compliance logic inside Frappe DocType hooks;
- rely on Frappe's normal Audit Trail as the Part 11 audit ledger;
- rely on normal login as the only electronic-signature control;
- permit uncontrolled production customization;
- hard-code the product to one ERP;
- build separate codebases for combination/device/pharma.

## Do

Build:

```text
FRAPPE
Application Platform
        +
PROPRIETARY eBMR/eDHR DOMAIN CORE
        +
PROPRIETARY GxP COMPLIANCE CORE
        +
KEYCLOAK / ENTERPRISE IdP
Identity & Step-up Authentication
        +
TEMPORAL
(optional but strongly worth evaluating)
Durable Manufacturing Orchestration
        +
ERP/LIMS/FACTORY ADAPTERS
```

---

# 45. ARCHITECTURAL VERDICT

### Frappe as ready-made FDA eBMR

**3/10**

### Frappe as application framework

**8.8/10**

### Frappe + ordinary custom app

**6–7/10**

### Frappe + proprietary GxP Core + hardened IAM + controlled SDLC

**9+/10 achievable**

### Frappe + GxP Core + eBMR/eDHR domain + combination-product genealogy + enterprise integrations + validation package

**This is the recommended product architecture.**

The defensible intellectual property is therefore **not Frappe**.

The acquisition-value IP should become:

1. GxP Compliance Core
2. Electronic Signature Engine
3. Immutable Audit Architecture
4. Batch Execution Engine
5. Recipe/Version Engine
6. Combination-Product Genealogy
7. Review-by-Exception
8. Regulatory Rules Engine
9. Release/Disposition Engine
10. Validation-ready product architecture
11. ERP/LIMS/factory abstraction layer
12. Regulated AI layer

---

# 46. MASTER PRINCIPLE

> **Frappe handles the application.**  
> **eBMR Core understands manufacturing.**  
> **GxP Core establishes trust.**  
> **Connectors communicate with the enterprise and factory.**

This separation should be treated as a non-negotiable architectural rule from the first production commit.

---


# 46A. DOCUMENT 01 FREEZE DECLARATION

The product inputs required to begin Document 02 are considered **frozen** at this revision.

Document 02 may make detailed technical selections within these boundaries, but it must not silently change:

- Frappe as the primary application framework;
- proprietary eBMR/eDHR domain logic;
- proprietary GxP trust/compliance core;
- configurable DDCP profile architecture;
- V1 manufacturing-QMS scope;
- regulated procurement/material capability;
- native basic QC + generic LIMS adapter;
- generic Edge Gateway;
- mandatory regulated-signature step-up authentication;
- isolated enterprise deployment capability;
- cloud-neutral software architecture;
- AWS/Azure reference deployments;
- no fully disconnected Part 11 browser execution in V1;
- configurable retention/no normal deletion of regulated records;
- proprietary IP strategy;
- validation-ready DDCP V1;
- advisory-only AI for regulated decisions.

Any later change to these frozen decisions shall require:

1. documented change request;
2. reason;
3. impact assessment;
4. affected requirements/specifications;
5. approval;
6. revision of Document 01 where the change is product-level.

# Regulatory Qualification

This Bible is a product-engineering baseline, not a legal opinion or a declaration that the eventual product or customer deployment is FDA compliant.

Actual obligations vary by intended use, constituent type, manufacturing process, customer QMS, product classification and configuration. Final implementation should be reviewed by qualified US regulatory/quality professionals, and each production deployment should undergo the customer's appropriate validation/CSA and procedural controls.
