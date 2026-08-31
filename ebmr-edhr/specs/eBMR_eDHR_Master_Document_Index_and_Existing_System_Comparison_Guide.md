# eBMR / eDHR Master Document Index & Existing-System Comparison Guide

**Purpose:** Provide one master overview of every planned specification/document so the new platform can be compared systematically against an existing eBMR/eDHR/MES/QMS system before and during development.

**Use this document for:**
- existing-system gap analysis;
- build-vs-reuse decisions;
- migration planning;
- product due diligence;
- development planning;
- validation planning;
- deciding which detailed documents must be generated next.

---

# How to Compare an Existing System

For every document below, classify the existing system as:

| Status | Meaning |
|---|---|
| **FULL** | Function exists and meets the intended behavior/compliance need |
| **PARTIAL** | Function exists but misses sub-functions, compliance controls, integration, audit, security or scalability |
| **MISSING** | Function does not exist |
| **REPLACE** | Existing function exists but architecture/compliance risk makes replacement preferable |
| **REUSE** | Existing component can be retained with minimal change |
| **INTEGRATE** | Existing external system should remain and be connected through an adapter |

Recommended comparison sheet columns:

`Document ID | Module | Existing Status | Existing Module/Screen | Missing Sub-functions | Compliance Gap | Security Gap | Integration Gap | Reuse/Replace Decision | Estimated Effort | Notes`

---

# A. FOUNDATION & ARCHITECTURE

## Document 01 — Master Product, Compliance & Architecture Bible

**Objective:** Defines the full product scope, regulatory boundaries, V1 DDCP strategy, future Device/Pharma expansion, Frappe vs proprietary GxP ownership, and non-negotiable product rules.

**Main functionalities / scope:** Common GxP, DDCP/device/pharma modules, compliance baseline, security baseline, procurement/material scope, QMS scope, sterile readiness, validation strategy.

**Existing-system comparison focus:** Compare whether the existing system covers the same overall product scope, regulatory profiles, QMS depth, material lifecycle, sterile/aseptic readiness, and expansion capability.

**Primary category:** Foundation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 02 — System Architecture & GxP Core Technical Specification

**Objective:** Converts Document 01 into the technical architecture used by developers and architects.

**Main functionalities / scope:** Frappe layer, GxP Core, PostgreSQL/MariaDB split, Keycloak, Temporal, Mutation Gateway, Audit, Signature, Record Vault, event architecture, Edge, ERP/LIMS adapters, security, deployment.

**Existing-system comparison focus:** Compare actual architecture, system-of-record boundaries, databases, trust zones, integration design, offline behavior, scalability, and whether regulated truth is separated from UI/framework logic.

**Primary category:** Architecture

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# B. GxP CORE

## Document 03 — GxP Mutation Gateway Specification

**Objective:** Defines the controlled entry point for every regulated create/change/approve/release action.

**Main functionalities / scope:** Identity validation, authorization, state validation, expected-version checks, reason-for-change, signature enforcement, idempotency, transactions, outbox, error handling.

**Existing-system comparison focus:** Compare whether existing system has one authoritative mutation path or allows direct DB/API/UI writes that bypass compliance controls.

**Primary category:** GxP Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 04 — Part 11 Electronic Signature Specification

**Objective:** Defines how regulated electronic signatures are authenticated, recorded, bound to records, manifested, and protected.

**Main functionalities / scope:** Step-up authentication, signature challenge, record hash/version binding, signer identity, meaning, timestamps, replay prevention, failed attempts, revocation, export manifestation.

**Existing-system comparison focus:** Compare signature workflow, password/MFA handling, re-authentication, signature meaning, linkage to exact record version, and audit evidence.

**Primary category:** GxP Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 05 — Immutable Audit Ledger & Audit Review Specification

**Objective:** Defines the independent audit history for regulated actions and how QA/auditors review it.

**Main functionalities / scope:** Append-only events, old/new values, actor/source, reason, signature link, timestamps, hash chaining/checkpoints, search, filters, export, integrity verification, retention.

**Existing-system comparison focus:** Compare whether existing audit can be edited/deleted, whether old values and reasons are preserved, whether machine/API actions are attributable, and whether audit export is inspection-ready.

**Primary category:** GxP Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 06 — Record Version Vault, Locking, Amendment & Controlled Correction Specification

**Objective:** Defines immutable released records and controlled post-release correction behavior.

**Main functionalities / scope:** Canonicalization, hashing, version creation, locking states, amendment/correction, supersession, original preservation, archival, retrieval, integrity checks.

**Existing-system comparison focus:** Compare how released recipes/batches/documents are locked, amended, corrected, and whether historical versions remain fully retrievable.

**Primary category:** GxP Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 07 — Identity, Authorization, RBAC, Qualification & Segregation-of-Duties Specification

**Objective:** Defines who may perform which regulated actions under which site, role, qualification, and SoD conditions.

**Main functionalities / scope:** SSO, Keycloak/customer IdP, roles, site scope, qualification, training status, maker-checker rules, break-glass access, access review, service identities.

**Existing-system comparison focus:** Compare role granularity, site restrictions, training/qualification blocking, conflicting-role prevention, admin privilege separation, and access-review capability.

**Primary category:** GxP Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 08 — Regulatory Rules & Calculation Engine Specification

**Objective:** Defines how regulated business rules and validated calculations are authored, versioned, executed, tested, and released.

**Main functionalities / scope:** Eligibility rules, limits, formulas, units, precision, rounding, deviation triggers, release rules, signature rules, equipment/material/qualification checks, rule versioning.

**Existing-system comparison focus:** Compare whether calculations/rules are hardcoded, configurable, version-controlled, testable, auditable, and tied to the released recipe/version.

**Primary category:** GxP Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# C. eBMR / eDHR CORE

## Document 09 — Product, Constituent & Regulatory Profile Master

**Objective:** Defines the product/constituent model used for DDCP, medical device, and pharma profiles.

**Main functionalities / scope:** Product master, drug/device/biologic constituent types, regulatory profile, PMOA metadata, UDI applicability, sterile applicability, lot/serial strategy, profile activation.

**Existing-system comparison focus:** Compare how existing system models combination products, multiple constituents, product variants, regulatory applicability, and profile-specific rules.

**Primary category:** eBMR Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 10 — Master Recipe / Master Manufacturing Record Specification

**Objective:** Defines how approved manufacturing instructions are authored, structured, versioned, approved, and made effective.

**Main functionalities / scope:** Steps, materials, equipment, parameters, calculations, QC points, signatures, holds, conditional/parallel flow, effective dates, obsolescence, release.

**Existing-system comparison focus:** Compare recipe flexibility, version control, structured vs free-text instructions, conditional logic, approval, effective dating, and frozen batch snapshots.

**Primary category:** eBMR Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 11 — Batch Execution Engine & State Machine Specification

**Objective:** Defines the runtime behavior of an electronic batch from creation through execution, review, release, and closure.

**Main functionalities / scope:** Batch creation, snapshot lock, step states, sequence enforcement, parallel/conditional steps, pause/resume, holds, timers, shift handover, exceptions, corrections, rework/reprocess.

**Existing-system comparison focus:** Compare actual batch execution controls, bypass prevention, concurrency, offline/resume behavior, exception handling, and state integrity.

**Primary category:** eBMR Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 12 — eDHR / Device Production History Specification

**Objective:** Defines the electronic production history needed for device constituents and future medical-device manufacturing.

**Main functionalities / scope:** Lot/serial production history, component genealogy, assembly steps, test results, acceptance, UDI/serial linkage, rework, final release evidence.

**Existing-system comparison focus:** Compare whether existing system supports unit/serial-level traceability, component genealogy, device testing, acceptance evidence, and final eDHR export.

**Primary category:** eBMR Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 13 — Genealogy & Traceability Engine Specification

**Objective:** Defines forward/backward traceability across material, drug batch, device component, serial, combination product, packaging, and distribution.

**Main functionalities / scope:** Lot/container genealogy, serial genealogy, derived-from/assembled-into/consumed-in relations, affected-product search, recall tracing, complaint tracing.

**Existing-system comparison focus:** Compare trace depth, speed, lot-to-finished and finished-to-source queries, serial support, supplier-lot traceability, and recall impact analysis.

**Primary category:** eBMR Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 14 — Review-by-Exception & QA Review Specification

**Objective:** Defines how QA reviews large electronic records efficiently by focusing on deviations, changed values, missing evidence, and abnormal conditions.

**Main functionalities / scope:** Exception index, severity, manual overrides, missing signatures, parameter excursions, equipment/material exceptions, audit review, evidence review, reviewer comments, review status.

**Existing-system comparison focus:** Compare whether QA must manually read the full BMR or gets automated exception-centric review and blocker identification.

**Primary category:** eBMR Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 15 — Release / Disposition Engine Specification

**Objective:** Defines the final automated eligibility check and controlled QA disposition of a batch/device/lot.

**Main functionalities / scope:** Completion checks, QC status, deviations/OOS/OOT, reconciliation, signatures, equipment/personnel status, environmental evidence, release/hold/reject/rework/destruction.

**Existing-system comparison focus:** Compare whether release uses a configurable rule engine, whether blockers are automatically detected, and whether release is independently signed and auditable.

**Primary category:** eBMR Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 16 — Packaging, Labeling & Reconciliation Specification

**Objective:** Defines controlled packaging and labeling execution for pharma, device, and combination-product records.

**Main functionalities / scope:** Packaging materials, label issuance, line clearance, print/version control, barcode/UDI, label reconciliation, rejects, returns, destruction, packaging genealogy.

**Existing-system comparison focus:** Compare label version control, issuance, reconciliation, packaging evidence, UDI integration, and prevention of obsolete label use.

**Primary category:** eBMR Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 17 — Yield, Calculations & Manufacturing Reconciliation Specification

**Objective:** Defines validated yield calculations and quantity reconciliation throughout production.

**Main functionalities / scope:** Theoretical yield, actual yield, stage yield, tolerances, potency correction, quantity balance, packaging reconciliation, variance trigger, correction controls.

**Existing-system comparison focus:** Compare calculation validation, formula versioning, automatic variance/deviation generation, and reconciliation completeness.

**Primary category:** eBMR Core

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# D. PROCUREMENT, MATERIALS & WAREHOUSE

## Document 18 — Procurement & Supplier Quality Specification

**Objective:** Defines regulated procurement from approved suppliers and integration with external ERP procurement where present.

**Main functionalities / scope:** Supplier master, qualification, approved supplier list, PR, RFQ, PO, supplier/material approval, quality agreement references, requalification, suspension.

**Existing-system comparison focus:** Compare supplier qualification depth, ASL control, PO/spec linkage, supplier status blocking, and ERP integration.

**Primary category:** Materials

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 19 — Material Receipt, Quarantine & Quality Status Specification

**Objective:** Defines controlled receipt of incoming materials/components and their transition through quarantine, sampling, QC, release/rejection.

**Main functionalities / scope:** GRN, PO match, supplier/manufacturer lot, internal lot, container IDs, COA, damage check, quarantine, sample request, release/reject/conditional status.

**Existing-system comparison focus:** Compare receiving traceability, quarantine enforcement, COA handling, quality status controls, and unauthorized-use prevention.

**Primary category:** Materials

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 20 — Inventory, Lot/Container & Warehouse Specification

**Objective:** Defines regulated inventory identity, locations, status, reservation, expiry/retest, and movement.

**Main functionalities / scope:** Warehouse/zone/bin, lot/container identity, FEFO, expiry/retest, reservations, transfers, blocked stock, status segregation, stock reconciliation.

**Existing-system comparison focus:** Compare whether existing inventory understands regulatory status and container identity or only financial stock quantities.

**Primary category:** Materials

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 21 — Material Dispensing & Weighing Specification

**Objective:** Defines controlled material picking, scanning, weighing, verification, and issue to batch.

**Main functionalities / scope:** Barcode verification, lot eligibility, target/tolerance, balance integration, manual entry, double verification, potency adjustment, label printing, partial containers, exceptions.

**Existing-system comparison focus:** Compare weighing integration, wrong-material prevention, tolerance checks, second-person verification, and dispensing genealogy.

**Primary category:** Materials

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 22 — Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification

**Objective:** Defines what happens to material after issue and how all quantities are accounted for.

**Main functionalities / scope:** Actual consumption, returns, leftover container status, adjustments, destruction, witness, reconciliation, variance handling, ERP posting, audit trail.

**Existing-system comparison focus:** Compare full quantity lifecycle, reasons/approval for adjustments, destruction controls, and issued-vs-consumed-vs-returned reconciliation.

**Primary category:** Materials

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# E. QC / LABORATORY

## Document 23 — Native Basic QC & Sampling Specification

**Objective:** Defines the built-in QC capability for customers without a full LIMS.

**Main functionalities / scope:** Test specification, methods, sampling plan, sample IDs, chain of custody, analyst assignment, result entry, limits, review, pass/fail, release dependency.

**Existing-system comparison focus:** Compare whether existing product has enough native QC to operate independently and whether QC results are tightly linked to material/batch release.

**Primary category:** QC

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 24 — LIMS Integration Architecture & Generic Adapter Contract

**Objective:** Defines vendor-neutral integration with customer LIMS systems.

**Main functionalities / scope:** Sample creation, status polling, result receive/revision, COA/evidence, acknowledgement, mapping, idempotency, retry, schema validation, source authentication.

**Existing-system comparison focus:** Compare LIMS integration flexibility, vendor coupling, result versioning, error handling, and whether external results can bypass release rules.

**Primary category:** QC

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 25 — OOS / OOT Management Specification

**Objective:** Defines laboratory OOS and trend-based OOT workflows with original-result preservation.

**Main functionalities / scope:** Phase I review, investigation, retest/resample authorization, manufacturing investigation, root cause, batch impact, disposition, trend detection, historical comparison, closure.

**Existing-system comparison focus:** Compare whether original failed results remain, whether retest/resample is controlled, and whether OOS/OOT links to batch release and CAPA.

**Primary category:** QC

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# F. QMS

## Document 26 — Deviation & Investigation Management

**Objective:** Defines planned/unplanned deviation handling from initiation to closure.

**Main functionalities / scope:** Classification, severity, containment, investigation, root cause, impact assessment, batch/material/equipment links, disposition, approval, extensions, trending.

**Existing-system comparison focus:** Compare deviation lifecycle depth, root-cause tools, batch impact, approvals, closure rules, and traceability to CAPA/change.

**Primary category:** QMS

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 27 — CAPA Management

**Objective:** Defines corrective/preventive action management and effectiveness verification.

**Main functionalities / scope:** CAPA source, root cause, actions, owners, due dates, evidence, escalation, effectiveness criteria, effectiveness check, closure/reopen.

**Existing-system comparison focus:** Compare CAPA lifecycle, overdue escalation, action evidence, effectiveness checks, and repeat-issue detection.

**Primary category:** QMS

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 28 — Nonconformance Management

**Objective:** Defines nonconforming material, component, device, or finished product controls.

**Main functionalities / scope:** Identification, segregation, evaluation, disposition, rework, scrap, concession/use-as-is where permitted, approval, genealogy impact, closure.

**Existing-system comparison focus:** Compare segregation, disposition controls, rework linkage, and traceability to affected product.

**Primary category:** QMS

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 29 — Change Control

**Objective:** Defines controlled changes to product, process, software, equipment, specifications, recipes, and documents.

**Main functionalities / scope:** Initiation, reason, affected objects, risk, regulatory impact, validation impact, implementation plan, approvals, training impact, effective date, post-implementation review.

**Existing-system comparison focus:** Compare whether changes are impact-assessed across manufacturing, validation, training, software, and regulatory records.

**Primary category:** QMS

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 30 — Document Control

**Objective:** Defines lifecycle of SOPs, specifications, procedures, forms, and controlled documents.

**Main functionalities / scope:** Draft, review, approval, versioning, effective date, obsolescence, controlled copy, periodic review, archival, training impact, signatures.

**Existing-system comparison focus:** Compare document lifecycle, obsolete-copy prevention, version history, training linkage, and controlled exports.

**Primary category:** QMS

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 31 — Training & Personnel Qualification

**Objective:** Defines training and qualification needed before a person performs regulated work.

**Main functionalities / scope:** Curricula, role requirements, SOP assignment, completion, exam/effectiveness, qualification, expiry, retraining, equipment/area authorization, execution blocking.

**Existing-system comparison focus:** Compare whether training merely records completion or actively blocks unqualified operators from regulated tasks.

**Primary category:** QMS

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 32 — Supplier Quality / SCAR

**Objective:** Defines supplier performance, quality incidents, corrective actions, and supplier status changes.

**Main functionalities / scope:** Supplier risk, audits, quality incidents, SCAR, supplier response, root cause, corrective action, effectiveness, requalification, suspension/disqualification.

**Existing-system comparison focus:** Compare supplier quality integration with procurement, material release, and quality events.

**Primary category:** QMS

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 33 — Risk Management

**Objective:** Defines product/process/system risk records and their linkage to quality events and changes.

**Main functionalities / scope:** Hazard/risk, probability/severity, controls, residual risk, mitigation, review, link to CAPA/deviation/change/product/process.

**Existing-system comparison focus:** Compare how risk is assessed, linked, versioned, and used in decisions rather than maintained as isolated spreadsheets.

**Primary category:** QMS

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 34 — Internal Audit Management

**Objective:** Defines planning, execution, findings, response, follow-up, and closure of internal audits.

**Main functionalities / scope:** Audit plan, scope, checklist, auditor independence, finding classification, response, CAPA link, follow-up, closure, audit metrics.

**Existing-system comparison focus:** Compare audit traceability, finding-to-CAPA linkage, overdue follow-up, and audit-readiness.

**Primary category:** QMS

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 35 — Complaint Management

**Objective:** Defines product complaint intake, investigation, traceability, and escalation.

**Main functionalities / scope:** Complaint intake, product/lot/serial, constituent classification, seriousness, investigation, batch/device history, CAPA link, reportability assessment, closure.

**Existing-system comparison focus:** Compare complaint-to-genealogy linkage, affected product search, investigation depth, and regulatory assessment workflow.

**Primary category:** QMS

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 36 — Recall / Field Action

**Objective:** Defines affected-product identification, action planning, reconciliation, and closure.

**Main functionalities / scope:** Recall initiation, lot/serial search, distribution scope, hold, communication evidence, returned units, effectiveness, reconciliation, closure.

**Existing-system comparison focus:** Compare how quickly existing system can find affected product and support field action/recall execution.

**Primary category:** QMS

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 37 — Quality Metrics, Trending & Effectiveness Checks

**Objective:** Defines dashboards and analytics for recurring issues and quality performance.

**Main functionalities / scope:** Deviation trends, OOS/OOT trends, CAPA aging, repeat issues, complaint trends, supplier quality, batch-release cycle, effectiveness checks, configurable KPIs.

**Existing-system comparison focus:** Compare whether existing system provides actionable quality intelligence or only transactional records.

**Primary category:** QMS

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# G. EQUIPMENT / STERILE / ASEPTIC

## Document 38 — Equipment Master, Usage, Maintenance, Calibration & Qualification

**Objective:** Defines equipment identity, status, calibration, qualification, maintenance, and batch usage.

**Main functionalities / scope:** Equipment master, class, location, calibration, maintenance, IQ/OQ/PQ references, availability, due dates, automatic execution blocking, usage history.

**Existing-system comparison focus:** Compare whether overdue/unqualified equipment is automatically prevented from use and fully linked to batch records.

**Primary category:** Equipment

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 39 — Cleaning, Line Clearance & Equipment Status

**Objective:** Defines cleaning and line-clearance controls before/after regulated operations.

**Main functionalities / scope:** Cleaning status, procedure version, agent, performed/verified, line clearance checklist, previous-product clearance, status labels, hold/release, audit.

**Existing-system comparison focus:** Compare line clearance, cleaning traceability, verification, and automatic eligibility enforcement.

**Primary category:** Equipment

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 40 — Sterile / Aseptic Manufacturing Specification

**Objective:** Defines regulated sterile/aseptic execution for applicable injectable DDCP and pharma profiles.

**Main functionalities / scope:** Cleanroom areas, gowning qualification, interventions, aseptic holds, filling, sterile components, environmental linkage, filters, sterilization evidence, excursions, release impact.

**Existing-system comparison focus:** Compare sterile-process coverage, area/personnel qualification, intervention capture, hold-time control, and batch-impact assessment.

**Primary category:** Sterile

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 41 — Environmental Monitoring Integration

**Objective:** Defines integration and use of viable/non-viable/environmental data during manufacturing.

**Main functionalities / scope:** Particles, viable counts, temperature, humidity, differential pressure, alert/action limits, source identity, time windows, excursions, batch correlation.

**Existing-system comparison focus:** Compare whether environmental excursions automatically identify affected batches/steps and block release when required.

**Primary category:** Sterile

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 42 — Sterilization / CIP / SIP / Filter Management Specification

**Objective:** Defines sterilization and cleaning-process evidence linked to batches/equipment.

**Main functionalities / scope:** Autoclave/sterilizer cycles, CIP/SIP, load, parameters, filter ID, installation, pre/post integrity testing, cycle result, exceptions, batch impact.

**Existing-system comparison focus:** Compare machine evidence capture, cycle result traceability, filter lifecycle, and release dependencies.

**Primary category:** Sterile

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# H. EDGE / FACTORY CONNECTIVITY

## Document 43 — Generic Edge Gateway Technical Specification

**Objective:** Defines the local plant gateway for industrial/lab/device connectivity and resilient data delivery.

**Main functionalities / scope:** Device registry, protocol plugins, data capture, local buffer, validation, unit normalization, quality codes, encryption, retries, sync, diagnostics, updates.

**Existing-system comparison focus:** Compare whether current system connects directly from application to devices or has a resilient, secure edge abstraction.

**Primary category:** Edge

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 44 — Device/Instrument Registry & Identity

**Objective:** Defines trusted identity and lifecycle for machines, scanners, balances, and instruments.

**Main functionalities / scope:** Device ID, certificates, type, site/area, protocol, calibration/qualification link, ownership, status, credential rotation, decommissioning.

**Existing-system comparison focus:** Compare whether device data is attributable to a registered trusted source and whether device credentials are managed.

**Primary category:** Edge

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 45 — OPC UA / Modbus / MQTT / Serial / REST Connector Architecture

**Objective:** Defines standardized connector contracts for common industrial and laboratory protocols.

**Main functionalities / scope:** Connection config, polling/subscription, mapping, quality, sequence, retries, alarms, protocol-specific security, plugin lifecycle.

**Existing-system comparison focus:** Compare supported protocols, connector reuse, diagnostics, security, and ability to add vendor-specific drivers without changing core.

**Primary category:** Edge

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 46 — Edge Buffering, Synchronization & Data Integrity

**Objective:** Defines how plant data survives WAN/server outages and synchronizes safely.

**Main functionalities / scope:** Local durable queue, sequence numbers, deduplication, encryption, timestamp preservation, retries, acknowledgements, conflict handling, health metrics.

**Existing-system comparison focus:** Compare data-loss behavior during outages, replay protection, ordering, and integrity verification.

**Primary category:** Edge

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 47 — Barcode, Balance & Scanner Integration

**Objective:** Defines controlled human-device interaction for scanning and weighing.

**Main functionalities / scope:** Barcode formats, scanner input, material/container verification, balance readings, stable-weight rules, manual fallback, device identity, operator confirmation.

**Existing-system comparison focus:** Compare wrong-item prevention, automatic capture, manual override controls, and equipment attribution.

**Primary category:** Edge

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# I. ENTERPRISE INTEGRATIONS

## Document 48 — ERP Integration Architecture

**Objective:** Defines vendor-neutral ERP boundaries and provider contracts.

**Main functionalities / scope:** Master sync, procurement, inventory, warehouse, consumption, returns, financial reference, mapping, reconciliation, retry, idempotency.

**Existing-system comparison focus:** Compare ERP coupling, system-of-record clarity, synchronization conflicts, and ability to switch ERP vendors.

**Primary category:** Integration

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 49 — ERPNext Adapter

**Objective:** Defines concrete integration with ERPNext when used by smaller/medium customers.

**Main functionalities / scope:** Items, suppliers, PO, stock, warehouse, lot/batch, goods receipt, consumption, returns, sync status, mapping.

**Existing-system comparison focus:** Compare whether existing ERPNext integration is upgrade-safe, adapter-based, and does not leak ERPNext assumptions into eBMR core.

**Primary category:** Integration

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 50 — SAP Adapter Contract

**Objective:** Defines the contract and mappings needed for SAP integration without hardcoding SAP into core.

**Main functionalities / scope:** Material master, vendor, PO, batch/lot, goods movements, inventory, production references, IDoc/API/OData mapping, retry/reconciliation.

**Existing-system comparison focus:** Compare whether current solution can integrate with SAP at enterprise customers without a rewrite.

**Primary category:** Integration

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 51 — Oracle/Dynamics/Custom ERP Adapter Contract

**Objective:** Defines common integration expectations for other major ERP systems.

**Main functionalities / scope:** Master data, procurement, inventory, movements, consumption, mappings, error handling, idempotency, reconciliation.

**Existing-system comparison focus:** Compare portability and time required to add a new ERP.

**Primary category:** Integration

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 52 — Master Data Synchronization & Reconciliation

**Objective:** Defines ownership, mapping, conflict rules, and reconciliation for shared masters.

**Main functionalities / scope:** Golden-source rules, IDs, cross-reference tables, version/date, conflict detection, manual resolution, sync audit, reconciliation reports.

**Existing-system comparison focus:** Compare duplicate-master risk, synchronization transparency, and conflict resolution.

**Primary category:** Integration

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 53 — Integration Error Handling, Retry & Idempotency

**Objective:** Defines standard behavior for failed or duplicate external transactions.

**Main functionalities / scope:** Retry policy, backoff, dead-letter, idempotency, correlation ID, operator retry, reconciliation, alerting, replay safety.

**Existing-system comparison focus:** Compare whether integrations can fail safely without duplicate stock/QC/batch actions.

**Primary category:** Integration

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# J. DDCP MANUFACTURING PROFILES

## Document 54 — DDCP Profile A — Prefilled Syringe / Injectable Drug Delivery

**Objective:** Defines the detailed reference manufacturing profile for prefilled syringe-type DDCP.

**Main functionalities / scope:** Bulk/formulation linkage, sterile components, filling, stoppering/plunger, inspection, CCI/leak checks, device components, labeling, packaging, genealogy, release.

**Existing-system comparison focus:** Compare current system coverage against a representative injectable DDCP end-to-end process.

**Primary category:** DDCP Profile

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 55 — DDCP Profile A2 — Autoinjector / Insulin Pen / Cartridge + Injector

**Objective:** Defines device-assembly-heavy injectable DDCP manufacturing.

**Main functionalities / scope:** Cartridge/syringe constituent, mechanical components, assembly, serial/lot genealogy, functional testing, force/dose tests, labeling, packaging, final release.

**Existing-system comparison focus:** Compare mechanical assembly, device testing, serial traceability, and drug-to-device constituent linkage.

**Primary category:** DDCP Profile

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 56 — DDCP Profile B — Inhalation Delivery

**Objective:** Defines reference manufacturing for inhalation combination products.

**Main functionalities / scope:** Drug formulation/fill, canister/capsule/reservoir, valve/metering system, actuator, assembly, leak/dose tests, labeling, genealogy, release.

**Existing-system comparison focus:** Compare inhalation-specific component/process/test coverage.

**Primary category:** DDCP Profile

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 57 — DDCP Profile C — Drug-Eluting / Drug-Coated Device

**Objective:** Defines reference manufacturing for drug-coated/eluting devices.

**Main functionalities / scope:** Device substrate genealogy, coating solution, application, drying/curing, thickness/load tests, device inspection, sterilization, UDI/serial, packaging, release.

**Existing-system comparison focus:** Compare coating-process controls, drug-load evidence, device genealogy, sterilization, and final release.

**Primary category:** DDCP Profile

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# K. DDCP POSTMARKET

## Document 58 — DDCP Complaint & Postmarket Assessment

**Objective:** Defines complaint processing specific to combination-product constituents and interfaces.

**Main functionalities / scope:** Complaint intake, drug/device/interface classification, affected lot/serial, investigation, seriousness, constituent responsibility, CAPA/recall links.

**Existing-system comparison focus:** Compare whether complaints can be investigated across both drug and device histories.

**Primary category:** Postmarket

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 59 — Reportability Assessment

**Objective:** Defines configurable workflow to assess whether an event may require regulatory reporting.

**Main functionalities / scope:** Event classification, seriousness, timelines, rationale, reviewer, due dates, evidence, submission status/reference.

**Existing-system comparison focus:** Compare regulatory assessment workflow, due-date control, rationale capture, and auditability.

**Primary category:** Postmarket

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 60 — Combination-Product Recall / Field Action & Affected-Product Analysis

**Objective:** Defines recall/field-action impact across all constituent and finished-product genealogy.

**Main functionalities / scope:** Affected material/constituent search, lots/serials, distribution scope, holds, notifications, reconciliation, effectiveness, closure.

**Existing-system comparison focus:** Compare recall speed and completeness across drug and device constituents.

**Primary category:** Postmarket

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# L. SECURITY

## Document 61 — Security Architecture

**Objective:** Defines the overall security model and controls for regulated SaaS/private/on-prem deployments.

**Main functionalities / scope:** Trust zones, IAM, network segmentation, encryption, secrets, APIs, logs, admin access, monitoring, secure configuration, tenant isolation.

**Existing-system comparison focus:** Compare existing security architecture against enterprise US customer expectations and GxP operational risks.

**Primary category:** Security

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 62 — Threat Model

**Objective:** Identifies system threats, attack paths, mitigations, residual risks, and security test requirements.

**Main functionalities / scope:** Account compromise, DB tampering, audit manipulation, signature replay, integration compromise, edge spoofing, ransomware, CI/CD compromise, tenant exposure.

**Existing-system comparison focus:** Compare whether current product has a formal threat model and mapped mitigations.

**Primary category:** Security

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 63 — IAM / Keycloak / Customer SSO Deployment

**Objective:** Defines identity federation and authentication architecture.

**Main functionalities / scope:** OIDC/SAML, Entra/Okta/AD, MFA, step-up, sessions, user lifecycle, service accounts, break-glass, claims mapping.

**Existing-system comparison focus:** Compare SSO flexibility, MFA, user lifecycle, identity assurance, and Part 11 signing support.

**Primary category:** Security

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 64 — Privileged Access Management

**Objective:** Defines controls for admins, DBAs, infrastructure teams, and vendor support.

**Main functionalities / scope:** Privileged roles, approvals, time-limited access, MFA, session logging, break-glass, post-access review, production restrictions.

**Existing-system comparison focus:** Compare whether administrators can alter regulated data without independent trace/evidence.

**Primary category:** Security

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 65 — Encryption, Key & Secrets Management

**Objective:** Defines cryptographic handling of data, secrets, signing keys, and key rotation.

**Main functionalities / scope:** TLS, at-rest encryption, KMS/HSM, customer-managed keys, key rotation, secrets vault, backup encryption, certificate lifecycle.

**Existing-system comparison focus:** Compare cryptographic maturity, key ownership, rotation, and secret leakage risk.

**Primary category:** Security

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 66 — API / Integration Security

**Objective:** Defines security controls for external and service APIs.

**Main functionalities / scope:** OAuth/mTLS, scopes, rate limits, anti-replay, idempotency, signing, IP/network controls, schema validation, audit, service identity.

**Existing-system comparison focus:** Compare API authentication, replay protection, service-account separation, and integration security.

**Primary category:** Security

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 67 — Secure SDLC / DevSecOps

**Objective:** Defines security controls across development and release.

**Main functionalities / scope:** SAST, DAST, SCA, secret scan, container scan, SBOM, code review, branch protection, patch management, dependency approval, security regression.

**Existing-system comparison focus:** Compare existing software-development security maturity and evidence available for enterprise due diligence.

**Primary category:** Security

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 68 — Incident Response & Security Monitoring

**Objective:** Defines detection, escalation, investigation, containment, recovery, and regulated impact assessment.

**Main functionalities / scope:** SIEM, alerting, incidents, affected records/batches, evidence preservation, deviation/CAPA linkage, customer notification, post-incident review.

**Existing-system comparison focus:** Compare monitoring coverage, incident evidence, response workflow, and linkage to quality events.

**Primary category:** Security

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# M. DATA / INFRASTRUCTURE

## Document 69 — Database & Data Model Architecture

**Objective:** Defines relational domains, ownership, IDs, versioning, partitioning, constraints, and data relationships.

**Main functionalities / scope:** MariaDB/Frappe, PostgreSQL/GxP, schemas, aggregates, audit, genealogy, indexes, concurrency, migration strategy.

**Existing-system comparison focus:** Compare existing data model normalization, authoritative boundaries, traceability, and ability to scale without losing integrity.

**Primary category:** Infrastructure

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 70 — Audit/Data Partitioning & Retention

**Objective:** Defines how large regulated datasets are partitioned, retained, archived, and queried over long periods.

**Main functionalities / scope:** Partition keys, retention classes, archive tiers, query strategy, legal hold, no-delete rules, restore, audit retention.

**Existing-system comparison focus:** Compare long-term data strategy and performance for 10+ year records.

**Primary category:** Infrastructure

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 71 — Evidence/Object Storage & WORM Architecture

**Objective:** Defines storage of PDFs, COAs, images, machine files, exports, and immutable evidence.

**Main functionalities / scope:** S3/Azure/on-prem abstraction, hashes, manifests, malware scan, retention, immutability/WORM, versioning, retrieval, legal hold.

**Existing-system comparison focus:** Compare evidence integrity, file versioning, immutability, and inspection retrieval.

**Primary category:** Infrastructure

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 72 — Backup / Restore

**Objective:** Defines complete backup and tested restoration of application, GxP data, identity, and evidence.

**Main functionalities / scope:** Backup schedules, encryption, offsite copies, immutability, restore runbooks, testing, evidence, monitoring.

**Existing-system comparison focus:** Compare whether backups are merely created or regularly restored and validated.

**Primary category:** Infrastructure

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 73 — Disaster Recovery / Business Continuity

**Objective:** Defines recovery from site/cloud/service failure and manufacturing continuity.

**Main functionalities / scope:** RPO/RTO, failover, alternate region/site, recovery sequencing, Edge buffer, identity recovery, communication, testing.

**Existing-system comparison focus:** Compare actual DR capability against contractual enterprise requirements.

**Primary category:** Infrastructure

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 74 — High Availability & Scalability

**Objective:** Defines horizontal/vertical scaling and removal of single points of failure.

**Main functionalities / scope:** API replicas, DB HA, Temporal workers, event bus, object storage, load balancing, scaling, performance testing.

**Existing-system comparison focus:** Compare current bottlenecks, single points of failure, and supported enterprise growth.

**Primary category:** Infrastructure

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 75 — AWS Reference Architecture

**Objective:** Defines validated reference deployment on AWS.

**Main functionalities / scope:** VPC, EKS/ECS choice, RDS, S3, KMS, secrets, WAF, logging, backup, HA, network zones, deployment automation.

**Existing-system comparison focus:** Compare ease of deploying current system for US AWS-centric customers.

**Primary category:** Infrastructure

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 76 — Azure Reference Architecture

**Objective:** Defines validated reference deployment on Microsoft Azure.

**Main functionalities / scope:** VNet, AKS, managed DBs, Blob, Key Vault, Entra integration, WAF, logging, backup, HA.

**Existing-system comparison focus:** Compare Azure readiness, especially for customers standardized on Microsoft identity/cloud.

**Primary category:** Infrastructure

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 77 — On-Premise / Private Cloud Architecture

**Objective:** Defines deployment into customer-controlled datacenter/private cloud.

**Main functionalities / scope:** Kubernetes/containers, local DB, object storage, IdP, Edge, internal ingress, backup, upgrades, support access, monitoring.

**Existing-system comparison focus:** Compare whether current product genuinely supports regulated on-prem without cloud dependencies.

**Primary category:** Infrastructure

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 78 — Kubernetes / Container Deployment Specification

**Objective:** Defines repeatable packaging and deployment of all platform components.

**Main functionalities / scope:** Images, Helm/Kustomize, namespaces, secrets, probes, resources, network policies, upgrade/rollback, observability, image signing.

**Existing-system comparison focus:** Compare deployment repeatability, environment parity, upgrade safety, and supportability.

**Primary category:** Infrastructure

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# N. VALIDATION / REGULATORY READINESS

## Document 79 — Intended Use & Regulatory Use Statement

**Objective:** Defines exactly what the software is intended to do and what regulated records/processes it supports.

**Main functionalities / scope:** Intended users, environments, product profiles, regulated functions, exclusions, assumptions, boundaries, claims.

**Existing-system comparison focus:** Compare whether existing system has a clearly defined intended use or vague marketing claims.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 80 — User Requirements Specification — URS

**Objective:** Defines user/business/regulatory requirements in testable language.

**Main functionalities / scope:** Production, QA, QC, Warehouse, Engineering, Admin, Auditor requirements; common and profile-specific requirements; interfaces; performance; security.

**Existing-system comparison focus:** Compare every existing feature against formal user requirements and identify missing/partial capabilities.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 81 — Functional Requirements Specification — FRS

**Objective:** Translates URS into detailed system behavior.

**Main functionalities / scope:** Inputs, outputs, states, rules, validations, errors, signatures, audit events, permissions, integrations, sub-functionalities.

**Existing-system comparison focus:** Compare actual system behavior to required behavior rather than only screen presence.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 82 — Software Design Specification — SDS

**Objective:** Defines detailed technical design implementing the FRS.

**Main functionalities / scope:** Components, classes/services, schemas, APIs, sequences, error handling, transactions, storage, algorithms, integration logic.

**Existing-system comparison focus:** Compare implementation architecture and technical debt against intended design.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 83 — 21 CFR Part 11 Assessment

**Objective:** Maps Part 11 requirements to product controls, procedures, evidence, gaps, and validation tests.

**Main functionalities / scope:** Access, audit, signatures, record copies, retention, operational checks, authority checks, documentation controls.

**Existing-system comparison focus:** Compare existing product against each Part 11 control and classify native/partial/missing.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 84 — 21 CFR Part 4 Compliance Matrix

**Objective:** Maps combination-product CGMP requirements to system functions and customer procedures.

**Main functionalities / scope:** Drug/device constituent requirements, streamlined approach support, testing/release, expiry, stability, reserve samples, constituent interactions.

**Existing-system comparison focus:** Compare DDCP compliance coverage and unsupported constituent scenarios.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 85 — 21 CFR 210/211 Compliance Matrix

**Objective:** Maps drug CGMP requirements relevant to eBMR/pharma manufacturing.

**Main functionalities / scope:** Materials, equipment, production/process controls, packaging, laboratory controls, records, complaints, returns, computerized systems.

**Existing-system comparison focus:** Compare pharma readiness of existing system.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 86 — QMSR / ISO 13485 Compliance Matrix

**Objective:** Maps current device QMSR/ISO 13485 requirements to device/eDHR/QMS functions.

**Main functionalities / scope:** Production/service controls, traceability, nonconformance, CAPA, complaints, supplier controls, records, labeling/packaging, risk linkage.

**Existing-system comparison focus:** Compare medical-device readiness of existing system.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 87 — Data Integrity / ALCOA+ Assessment

**Objective:** Evaluates whether data is attributable, legible, contemporaneous, original, accurate, complete, consistent, enduring, and available.

**Main functionalities / scope:** Audit, timestamps, source identity, corrections, metadata, retention, original data, failed result preservation, admin controls.

**Existing-system comparison focus:** Compare existing data integrity weaknesses and remediation effort.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 88 — GxP Risk Assessment

**Objective:** Identifies functional failures that could affect product quality, patient safety, or regulated records.

**Main functionalities / scope:** Risk scenarios, severity, probability, detectability/customer method, controls, residual risk, tests, mitigation ownership.

**Existing-system comparison focus:** Compare which current features are high-risk and under-controlled.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 89 — Security Risk Assessment

**Objective:** Assesses security threats in relation to confidentiality, integrity, availability, and regulated record trust.

**Main functionalities / scope:** Threats, vulnerabilities, control effectiveness, residual risk, testing, remediation, acceptance.

**Existing-system comparison focus:** Compare current security risk posture.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 90 — Requirements Traceability Matrix

**Objective:** Links every requirement through design, code, risk, test, result, and release evidence.

**Main functionalities / scope:** Requirement IDs, design IDs, risk IDs, test IDs, status, defects, release, validation result.

**Existing-system comparison focus:** Compare whether existing product can prove each claimed function is implemented and tested.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 91 — CSA / Validation Plan

**Objective:** Defines the risk-based validation approach for the product and customer deployment.

**Main functionalities / scope:** Scope, responsibilities, risk tiers, test strategy, automated/manual evidence, environments, deviations, approval, release criteria.

**Existing-system comparison focus:** Compare current validation process and evidence gaps.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 92 — IQ Package

**Objective:** Provides installation/deployment qualification evidence and templates.

**Main functionalities / scope:** Components, versions, infrastructure, configuration, prerequisites, installation verification, checksums, environment evidence.

**Existing-system comparison focus:** Compare reproducibility of existing deployment.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 93 — OQ Package

**Objective:** Provides operational qualification test scenarios for critical regulated functions.

**Main functionalities / scope:** Signature, audit, recipe, batch execution, QMS, material, QC, release, security, backup, errors, integrations.

**Existing-system comparison focus:** Compare existing system against controlled functional qualification tests.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 94 — PQ / UAT Template

**Objective:** Provides customer/site-specific performance/user-acceptance validation templates.

**Main functionalities / scope:** Real workflows, configured recipes, user roles, equipment, materials, customer SOP alignment, acceptance evidence.

**Existing-system comparison focus:** Compare how much customer-specific validation work current product requires.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 95 — Validation Summary Report

**Objective:** Summarizes validation scope, results, deviations, unresolved items, and final release conclusion.

**Main functionalities / scope:** Requirements covered, tests passed/failed, deviations, risks, known limitations, approvals.

**Existing-system comparison focus:** Compare completeness of existing validation evidence.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 96 — Release Validation & Change Impact Procedure

**Objective:** Defines how future releases are assessed, tested, approved, and deployed without revalidating everything blindly.

**Main functionalities / scope:** Change classification, affected requirements, risk, regression scope, documentation updates, customer notification, rollback, approval.

**Existing-system comparison focus:** Compare upgrade/change-control maturity of existing product.

**Primary category:** Validation

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# O. DEVELOPMENT / AI GOVERNANCE

## Document 97 — Coding Standards

**Objective:** Defines coding conventions for Frappe, TypeScript GxP services, SQL, integrations, and tests.

**Main functionalities / scope:** Naming, module structure, error handling, typing, logging, comments, security, database patterns, prohibited practices.

**Existing-system comparison focus:** Compare current code quality/consistency and refactoring needs.

**Primary category:** Engineering

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 98 — Architecture Rules for Claude Code / Codex

**Objective:** Defines mandatory instructions AI coding agents must follow to protect architecture and compliance.

**Main functionalities / scope:** No core edits, no direct GxP writes, no audit deletion, no signature bypass, requirement IDs, tests, migrations, license checks, APIs, traceability.

**Existing-system comparison focus:** Compare whether AI-assisted development of existing code could safely continue without architectural drift.

**Primary category:** Engineering

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 99 — Repository & Branching Standard

**Objective:** Defines Git organization, protected branches, PR requirements, releases, and ownership.

**Main functionalities / scope:** Repo structure, branches, reviewers, CODEOWNERS, commit/PR metadata, release tags, hotfix, artifacts.

**Existing-system comparison focus:** Compare existing repository governance and acquisition due-diligence readiness.

**Primary category:** Engineering

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 100 — Database Migration Standard

**Objective:** Defines safe schema/data changes for Frappe and GxP databases.

**Main functionalities / scope:** Migration scripts, forward/rollback strategy, representative testing, backup, reconciliation, checksums, no destructive history loss.

**Existing-system comparison focus:** Compare migration safety and upgrade history.

**Primary category:** Engineering

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 101 — API & Event Contract Standard

**Objective:** Defines stable API/event design and versioning rules.

**Main functionalities / scope:** OpenAPI, AsyncAPI, JSON Schema, compatibility, errors, idempotency, correlation, deprecation, consumer tests.

**Existing-system comparison focus:** Compare integration stability and risk of breaking customer systems.

**Primary category:** Engineering

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 102 — Testing Strategy

**Objective:** Defines test layers and minimum coverage for regulated and non-regulated functionality.

**Main functionalities / scope:** Unit, property/rule, API, integration, workflow replay, security, concurrency, failure, performance, validation scenarios.

**Existing-system comparison focus:** Compare current automated test depth and critical untested areas.

**Primary category:** Engineering

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 103 — CI/CD & Release Process

**Objective:** Defines automated build, security checks, packaging, evidence generation, and controlled deployment.

**Main functionalities / scope:** Lint, tests, SAST/SCA, SBOM, container scan, migration test, signing, release approval, deployment, rollback.

**Existing-system comparison focus:** Compare current release automation and control maturity.

**Primary category:** Engineering

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 104 — SBOM / Third-Party License Management

**Objective:** Defines dependency inventory, license approval, vulnerability tracking, and acquisition-ready evidence.

**Main functionalities / scope:** Package/version/license, source, obligations, SBOM, vulnerability status, approvals, upgrades, prohibited licenses.

**Existing-system comparison focus:** Compare open-source/IP exposure and missing license records in existing system.

**Primary category:** Engineering

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

## Document 105 — AI Governance for Regulated Manufacturing

**Objective:** Defines safe use of AI inside product and development lifecycle.

**Main functionalities / scope:** Advisory use cases, prohibited autonomous decisions, model/version logging, access control, human review, data protection, prompt/tool controls, validation considerations.

**Existing-system comparison focus:** Compare any current AI features against regulated-use safeguards and determine which can remain advisory vs require redesign.

**Primary category:** Engineering

**Expected output from this document:** A detailed, requirement-ID-based specification with all required sub-functionalities, states, permissions, audit/signature behavior, integrations, failure cases, validation criteria and acceptance tests for this scope.

---

# Recommended Comparison Sequence

Do not compare all 105 documents at the same depth on day one. Use this order:

1. **Documents 01–02:** confirm overall product scope and architecture.
2. **Documents 03–08:** check whether the existing system has a trustworthy GxP/Part 11 core.
3. **Documents 09–17:** compare actual eBMR/eDHR manufacturing capability.
4. **Documents 18–25:** compare material, inventory, dispensing, QC and LIMS capability.
5. **Documents 26–37:** compare QMS depth.
6. **Documents 38–47:** compare equipment, sterile manufacturing and factory connectivity.
7. **Documents 48–60:** compare ERP/LIMS/DDCP profile/postmarket capability.
8. **Documents 61–78:** compare security, infrastructure, cloud/on-prem and resilience.
9. **Documents 79–96:** compare compliance and validation readiness.
10. **Documents 97–105:** compare engineering quality, AI-assisted development readiness and acquisition/IP posture.

# Suggested Build-vs-Reuse Decision Rule

- **Reuse** when the existing module is functionally complete, maintainable, secure, and can be validated without architectural compromise.
- **Extend** when roughly 70–80% of the required behavior exists and the remaining gap can be added without bypassing GxP controls.
- **Integrate** when the existing capability belongs in another system of record, such as ERP, LIMS, IdP, historian or CMMS.
- **Replace** when the existing module permits uncontrolled record mutation, lacks reliable audit/signature/version controls, is tightly coupled to obsolete architecture, or would be harder to validate than rebuilding.
- **Build new proprietary core** for the Mutation Gateway, regulated electronic signatures, immutable audit, record version vault, execution rules, genealogy, release/disposition and other differentiating GxP controls.

# Final Purpose

This file is the **master map of the entire documentation and development program**. It is intentionally not the detailed specification for each module. Its purpose is to make it possible to take an existing product, inspect it module-by-module, mark FULL/PARTIAL/MISSING/REPLACE/REUSE/INTEGRATE, and then decide exactly which parts of the new platform must be developed from scratch, extended, or integrated.
