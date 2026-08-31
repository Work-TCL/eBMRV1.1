# US eBMR / eDHR Regulated Manufacturing Platform
## Document 111 — GxP Function Risk Classification Baseline — v1.0 APPROVED

**Specification ID:** SPEC-VAL-019
**Status:** APPROVED v1.0 (construction baseline) — approvers of record: Validation Lead and Head of Quality
**Closes:** SG-010
**Approval:** Approved by the Project Owner during construction review on 2026-08-21. A formal Part 11 signature record must be captured in the QMS against this version before validated release; the approval block below is the record of the construction decision.

**Primary Dependencies:** Document 80 (intended use/GxP criticality method), Document 79 (VMP/CSA), Document 82 (test strategy), Document 81 (traceability), Document 84/85 (OQ/PQ)

---

# 0. Why this document exists

Document 80 defines the classification **method** (intended use, GxP impact, quality impact, failure mode, detectability, automation role, record role, signature role, constituent scope, risk category, assurance method). It assigns no classification to any module or function. Every downstream CSA decision — how deeply to test, whether review must be independent, what evidence to retain, which qualification stage applies — depends on that assignment, so the validation programme currently has no basis.

This document proposes the **module-level classification for all 105 specifications**, derived from objective evidence in each document rather than opinion. Function-level classification inherits the module classification unless a work package raises it.

# 1. Derivation rule (auditable, reproducible)

```text
GxP impact      := DIRECT   if the module creates/changes/governs predicate-rule records or enforces a quality decision
                   INDIRECT if the module supports, protects or produces evidence about such records
                   N/A      for architecture/compliance baseline documents
signature role  := yes if the module's requirements reference electronic signature behaviour
record role     := creates/versions predicate-rule records | supports records held elsewhere
automation role := enforcement+gating | calculation | enforcement | advisory | informational
risk category   := HIGHER-PROCESS-RISK if (release|disposition) or signature or audit-immutability
                                          or (calculation AND enforcement) appears in the requirements
                   STANDARD-RISK otherwise
assurance       := HIGHER  → scripted, independently reviewed, mandatory negative/failure evidence
                   STANDARD→ hybrid/unscripted with automated regression evidence
```

The derivation is mechanical and re-runnable against the specification baseline, so re-classification after a specification change is deterministic and reviewable rather than a fresh opinion.

# 2. Classification summary

| Category | Count |
|---|---|
| HIGHER-PROCESS-RISK modules | 102 |
| STANDARD-RISK modules | 1 |
| DIRECT GxP impact | 67 |
| INDIRECT GxP impact | 36 |
| Modules with a signature role | 36 |

# 3. Module classification table (PROPOSED)

| Doc | Module | Title | WP | GxP impact | Automation role | Record role | Signature role | Risk category | Assurance method |
|---|---|---|---|---|---|---|---|---|---|
| 01 | DOC-001 | Master Product, Compliance & Architecture Bible | WP-00 | N/A | enforcement / automated gating | supports records held elsewhere | n/a | **N/A** | governed through the documents it constrains |
| 02 | DOC-002 | System Architecture & GxP Core Technical Specification | WP-00 | N/A | enforcement / automated gating | supports records held elsewhere | n/a | **N/A** | governed through the documents it constrains |
| 03 | SPEC-GXP-001 | GxP Mutation Gateway | WP-01 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 04 | SPEC-GXP-002 | 21 CFR Part 11 Electronic Signature | WP-01 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 05 | SPEC-GXP-003 | Immutable Audit Ledger & Audit Review | WP-01 | DIRECT | calculation | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 06 | SPEC-GXP-004 | Record Version Vault, Locking, Amendment & Controlled Correction | WP-01 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 07 | SPEC-IAM-001 | Identity, Authorization, RBAC, Qualification & Segregation-of-Duties | WP-01 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 08 | SPEC-GXP-006 | Regulatory Rules & Calculation Engine | WP-01 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 09 | SPEC-EBMR-000 | Product, Constituent & Regulatory Profile Master | WP-02 | DIRECT | calculation | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 10 | SPEC-EBMR-001 | Master Recipe / Master Manufacturing Record Specification | WP-02 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 11 | SPEC-EBMR-002 | Batch Execution Engine & State Machine Specification | WP-02 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 12 | SPEC-EBMR-003 | eDHR / Device Production History Specification | WP-02 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 13 | SPEC-EBMR-004 | Genealogy & Traceability Engine Specification | WP-03 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 14 | SPEC-EBMR-005 | Review-by-Exception & QA Review Specification | WP-03 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 15 | SPEC-EBMR-006 | Release / Disposition Engine Specification | WP-03 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 16 | SPEC-EBMR-007 | Packaging, Labeling & Reconciliation Specification | WP-03 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 17 | SPEC-EBMR-008 | Yield, Calculations & Manufacturing Reconciliation Specification | WP-03 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 18 | SPEC-MAT-001 | Procurement & Supplier Quality Specification | WP-04 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 19 | SPEC-MAT-002A | Material Receipt, Quarantine & Quality Status Specification | WP-04 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 20 | SPEC-MAT-002B | Inventory, Lot/Container & Warehouse Specification | WP-04 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 21 | SPEC-MAT-002C | Material Dispensing & Weighing Specification | WP-04 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 22 | SPEC-MAT-002D | Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification | WP-04 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 23 | SPEC-QC-001 | Native Basic QC & Sampling Specification | WP-04 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 24 | SPEC-QC-002 | LIMS Integration Architecture & Generic Adapter Contract | WP-04 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 25 | SPEC-QC-003 | OOS / OOT Management Specification | WP-04 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 26 | SPEC-QMS-001 | Deviation & Investigation Management | WP-05 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 27 | SPEC-QMS-002 | CAPA Management | WP-05 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 28 | SPEC-QMS-003 | Nonconformance Management | WP-05 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 29 | SPEC-QMS-004 | Change Control | WP-05 | DIRECT | informational / record-keeping | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 30 | SPEC-QMS-005 | Document Control | WP-05 | DIRECT | informational / record-keeping | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 31 | SPEC-QMS-006 | Training & Personnel Qualification | WP-05 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 32 | SPEC-QMS-007 | Supplier Quality / SCAR | WP-05 | DIRECT | enforcement | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 33 | SPEC-QMS-008 | Risk Management | WP-05 | DIRECT | enforcement | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 34 | SPEC-QMS-009 | Internal Audit Management | WP-05 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 35 | SPEC-QMS-010 | Complaint Management | WP-05 | DIRECT | informational / record-keeping | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 36 | SPEC-QMS-011 | Recall / Field Action Management | WP-05 | DIRECT | enforcement | creates and versions predicate-rule records | no | **STANDARD-RISK** | scripted or hybrid testing with automated regression evidence |
| 37 | SPEC-QMS-012 | Quality Metrics, Trending & Effectiveness Checks | WP-05 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 38 | SPEC-EQP-001 | Equipment, Calibration, Qualification & Maintenance | WP-06 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 39 | SPEC-EQP-002 | Cleaning, Sanitization & Line Clearance | WP-06 | DIRECT | informational / record-keeping | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 40 | SPEC-EQP-003 | Sterile / Aseptic Manufacturing Operations | WP-06 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 41 | SPEC-EQP-004 | Environmental Monitoring & Cleanroom State Control | WP-06 | DIRECT | informational / record-keeping | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 42 | SPEC-EQP-005 | Sterilization, CIP/SIP & Sterile Filtration Management | WP-06 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 43 | SPEC-EDGE-001 | Edge Gateway Runtime Architecture & Construction Specification | WP-06 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 44 | SPEC-EDGE-002 | Industrial Device & Protocol Connectivity / Driver Specification | WP-06 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 45 | SPEC-EDGE-003 | Store-and-Forward, Offline Buffering, Time Integrity & Data Quality | WP-06 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 46 | SPEC-EDGE-004 | Barcode, Scanner, Balance, Printer, Tester & Peripheral Integration | WP-06 | DIRECT | informational / record-keeping | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 47 | SPEC-EDGE-005 | Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary | WP-06 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 48 | SPEC-ERP-001 | Enterprise ERP Integration Architecture & Provider Contract | WP-07 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 49 | SPEC-ERP-002 | ERPNext Adapter Detailed Contract | WP-07 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 50 | SPEC-ERP-003 | SAP S/4HANA Adapter Contract | WP-07 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 51 | SPEC-ERP-004 | Oracle Fusion, Dynamics 365 & Custom ERP Adapter Contracts | WP-07 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 52 | SPEC-ERP-005 | Master Data Synchronization, Mapping & Reconciliation | WP-07 | DIRECT | enforcement | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 53 | SPEC-ERP-006 | Integration Error Handling, Retry, Idempotency & Reconciliation | WP-07 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 54 | SPEC-DDCP-001 | Prefilled Syringe & Injectable DDCP Manufacturing Profile | WP-08 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 55 | SPEC-DDCP-002 | Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile | WP-08 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 56 | SPEC-DDCP-003 | Inhalation DDCP Manufacturing Profile — MDI / DPI | WP-08 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 57 | SPEC-DDCP-004 | Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile | WP-08 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 58 | SPEC-PM-001 | Postmarket Surveillance, Safety Case & Signal Management | WP-09 | DIRECT | informational / record-keeping | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 59 | SPEC-PM-002 | Regulatory Reportability Assessment & Electronic Safety Submission Management | WP-09 | DIRECT | calculation | creates and versions predicate-rule records | yes | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 60 | SPEC-PM-003 | Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar | WP-09 | DIRECT | calculation | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 61 | SPEC-SEC-001 | Security Architecture, Threat Model & Control Framework | WP-10 | DIRECT | enforcement | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 62 | SPEC-SEC-002 | Identity Federation, SSO, MFA, Sessions & Service Identities | WP-10 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 63 | SPEC-SEC-003 | Privileged Access, Support Access, Break-Glass & Administrative Security | WP-10 | INDIRECT | informational / record-keeping | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 64 | SPEC-SEC-004 | Application, API, UI & Secure Runtime Engineering | WP-10 | DIRECT | enforcement | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 65 | SPEC-SEC-005 | Secrets Management, PKI, Cryptography & Key Lifecycle | WP-10 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 66 | SPEC-SEC-006 | Network, Tenant, Deployment Isolation & Zero-Trust Architecture | WP-10 | INDIRECT | enforcement | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 67 | SPEC-SEC-007 | Security Logging, Monitoring, Incident Response & Forensic Evidence | WP-10 | DIRECT | enforcement | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 68 | SPEC-SEC-008 | Secure SDLC, Software Supply Chain, SBOM, Vulnerability & Release Security | WP-10 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 69 | SPEC-DATA-001 | Enterprise Data Ownership, Persistence Topology & Data Lineage | WP-11 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 70 | SPEC-DATA-002 | PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency | WP-11 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 71 | SPEC-DATA-003 | Frappe / MariaDB Operational Database, Projection & UI Data Architecture | WP-11 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 72 | SPEC-DATA-004 | Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle | WP-11 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 73 | SPEC-DATA-005 | NATS / JetStream Event Bus, Transactional Outbox & Async Contracts | WP-11 | DIRECT | enforcement | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 74 | SPEC-DATA-006 | Temporal Durable Workflow Orchestration Architecture | WP-11 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 75 | SPEC-DATA-007 | Caching, Search, Read Models, Reporting Projections & Analytics Data Access | WP-11 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 76 | SPEC-DATA-008 | Backup, Restore, Point-in-Time Recovery & Disaster Recovery | WP-11 | DIRECT | enforcement / automated gating | creates and versions predicate-rule records | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 77 | SPEC-DATA-009 | Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture | WP-11 | INDIRECT | informational / record-keeping | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 78 | SPEC-DATA-010 | Performance, Capacity, Observability, SLOs & SRE Operations | WP-11 | INDIRECT | informational / record-keeping | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 79 | SPEC-VAL-001 | Validation Master Plan & Computer Software Assurance Strategy | WP-12 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 80 | SPEC-VAL-002 | Intended Use, GxP Criticality & Software Function Risk Classification | WP-12 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 81 | SPEC-VAL-003 | Requirements, Design Inputs & Validation Traceability Management | WP-12 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 82 | SPEC-VAL-004 | Validation Test Strategy, Test Methods & Objective Evidence Governance | WP-12 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 83 | SPEC-VAL-005 | Installation Qualification (IQ) & Installed Baseline Verification | WP-12 | INDIRECT | informational / record-keeping | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 84 | SPEC-VAL-006 | Operational Qualification (OQ) & Functional Control Verification | WP-12 | INDIRECT | calculation | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 85 | SPEC-VAL-007 | Performance Qualification (PQ), UAT & Business Process Verification | WP-14 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 86 | SPEC-VAL-008 | Infrastructure, Cloud, Platform & Environment Qualification | WP-12 | INDIRECT | informational / record-keeping | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 87 | SPEC-VAL-009 | Data Migration, Conversion, Cutover & Reconciliation Validation | WP-14 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 88 | SPEC-VAL-010 | 21 CFR Part 11 Electronic Records & Electronic Signature Validation | WP-12 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 89 | SPEC-VAL-011 | Audit Trail, Record Version Vault & Data Integrity Validation | WP-12 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 90 | SPEC-VAL-012 | Integration, Edge, Device, Peripheral & Interface Validation | WP-12 | INDIRECT | enforcement | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 91 | SPEC-VAL-013 | Backup, Restore, PITR & Disaster Recovery Qualification | WP-12 | INDIRECT | enforcement | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 92 | SPEC-VAL-014 | Security Qualification, Vulnerability Verification & Penetration Testing | WP-12 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 93 | SPEC-VAL-015 | Performance, Load, Capacity & Reliability Qualification | WP-12 | INDIRECT | informational / record-keeping | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 94 | SPEC-VAL-016 | Validation Defect, Deviation, Test Exception & Remediation Management | WP-12 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 95 | SPEC-VAL-017 | Validation Summary Report, Release-to-Production & Go-Live Authorization | WP-14 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 96 | SPEC-VAL-018 | Periodic Review, Change Impact, Revalidation & Validated-State Maintenance | WP-12 | INDIRECT | informational / record-keeping | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 97 | SPEC-ENG-001 | Coding Standards | WP-00 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 98 | SPEC-ENG-002 | Architecture Rules for Claude Code / Codex | WP-00 | INDIRECT | informational / record-keeping | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 99 | SPEC-ENG-003 | Repository & Branching Standard | WP-00 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 100 | SPEC-ENG-004 | Database Migration Standard | WP-00 | INDIRECT | informational / record-keeping | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 101 | SPEC-ENG-005 | API & Event Contract Standard | WP-00 | INDIRECT | enforcement | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 102 | SPEC-ENG-006 | Testing Strategy | WP-00 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 103 | SPEC-ENG-007 | CI/CD & Release Process | WP-00 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 104 | SPEC-ENG-008 | SBOM / Third-Party License Management | WP-00 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |
| 105 | SPEC-AI-001 | AI Governance for Regulated Manufacturing | WP-13 | INDIRECT | enforcement / automated gating | supports records held elsewhere | no | **HIGHER-PROCESS-RISK** | scripted testing with independent review, mandatory negative/failure cases, retained objective evidence |

# 4. Functional requirements

| ID | Requirement | Detailed behaviour | Acceptance intent |
|---|---|---|---|
| RISKB-FR-001 | Every module classified | No module may enter a work package without an approved classification. | WP entry gate check. |
| RISKB-FR-002 | Function inheritance | Functions inherit the module classification; a work package may raise but not lower it without Quality approval. | Lowering attempt requires approval record. |
| RISKB-FR-003 | Assurance binding | Test depth, independence and evidence class are selected from the classification, not chosen per developer. | Test plan traceable to classification. |
| RISKB-FR-004 | Configuration risk separate | Customer configuration risk is assessed separately from platform code risk (Doc 80 RISK-FR-012). | Two distinct assessments exist. |
| RISKB-FR-005 | Re-derivation | Classification is re-derived and reviewed whenever a source specification changes. | Change impact record. |
| RISKB-FR-006 | Traceability | Every requirement inherits its module's classification in the requirement registry. | Registry column populated. |
| RISKB-FR-007 | Higher-risk negative testing | Every HIGHER-PROCESS-RISK function has explicit negative and failure tests. | Coverage matrix check. |
| RISKB-FR-008 | Evidence retention | Higher-risk evidence is retained per Document 108 RC-VALIDATION; failed executions remain immutable. | Doc 94 alignment. |

# 5. Acceptance criteria

1. All 105 modules carry an approved classification.
2. The requirement registry and test coverage matrix consume the classification.
3. Every HIGHER-PROCESS-RISK module has scripted, independently reviewed test evidence.
4. Re-derivation after a specification change produces a reviewable diff.

# 6. Claude Code / Codex prohibitions

- Do not lower a classification to reduce test scope.
- Do not mark a function STANDARD-RISK when it performs, blocks or records a release, signature or audit action.
- Do not treat automated regression alone as sufficient evidence for a HIGHER-PROCESS-RISK function.

# 7. Approval block

| Role | Name | Decision | Date | Signature reference |
|---|---|---|---|---|
| Validation Lead |  |  |  |  |
| Head of Quality |  |  |  |  |
