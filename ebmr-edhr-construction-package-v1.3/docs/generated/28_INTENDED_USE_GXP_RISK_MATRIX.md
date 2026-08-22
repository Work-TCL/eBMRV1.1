# 28 — Intended Use & GxP Risk Matrix

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Approved module risk classification (Document 111) driving test depth and evidence class.

---

| Doc | Module | Intended use | GxP impact | Risk category | Assurance method |
|---|---|---|---|---|---|
| 01 | DOC-001 | Master Product, Compliance & Architecture Bible | N/A | **N/A** | governed through the documents it constrains |
| 02 | DOC-002 | System Architecture & GxP Core Technical Specification | N/A | **N/A** | governed through the documents it constrains |
| 03 | SPEC-GXP-001 | GxP Mutation Gateway | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 04 | SPEC-GXP-002 | 21 CFR Part 11 Electronic Signature | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 05 | SPEC-GXP-003 | Immutable Audit Ledger & Audit Review | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 06 | SPEC-GXP-004 | Record Version Vault, Locking, Amendment & Controlled Correction | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 07 | SPEC-IAM-001 | Identity, Authorization, RBAC, Qualification & Segregation-of-Duties | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 08 | SPEC-GXP-006 | Regulatory Rules & Calculation Engine | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 09 | SPEC-EBMR-000 | Product, Constituent & Regulatory Profile Master | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 10 | SPEC-EBMR-001 | Master Recipe / Master Manufacturing Record Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 11 | SPEC-EBMR-002 | Batch Execution Engine & State Machine Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 12 | SPEC-EBMR-003 | eDHR / Device Production History Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 13 | SPEC-EBMR-004 | Genealogy & Traceability Engine Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 14 | SPEC-EBMR-005 | Review-by-Exception & QA Review Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 15 | SPEC-EBMR-006 | Release / Disposition Engine Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 16 | SPEC-EBMR-007 | Packaging, Labeling & Reconciliation Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 17 | SPEC-EBMR-008 | Yield, Calculations & Manufacturing Reconciliation Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 18 | SPEC-MAT-001 | Procurement & Supplier Quality Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 19 | SPEC-MAT-002A | Material Receipt, Quarantine & Quality Status Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 20 | SPEC-MAT-002B | Inventory, Lot/Container & Warehouse Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 21 | SPEC-MAT-002C | Material Dispensing & Weighing Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 22 | SPEC-MAT-002D | Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 23 | SPEC-QC-001 | Native Basic QC & Sampling Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 24 | SPEC-QC-002 | LIMS Integration Architecture & Generic Adapter Contract | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 25 | SPEC-QC-003 | OOS / OOT Management Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 26 | SPEC-QMS-001 | Deviation & Investigation Management | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 27 | SPEC-QMS-002 | CAPA Management | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 28 | SPEC-QMS-003 | Nonconformance Management | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 29 | SPEC-QMS-004 | Change Control | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 30 | SPEC-QMS-005 | Document Control | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 31 | SPEC-QMS-006 | Training & Personnel Qualification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 32 | SPEC-QMS-007 | Supplier Quality / SCAR | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 33 | SPEC-QMS-008 | Risk Management | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 34 | SPEC-QMS-009 | Internal Audit Management | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 35 | SPEC-QMS-010 | Complaint Management | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 36 | SPEC-QMS-011 | Recall / Field Action Management | DIRECT | **STANDARD-RISK** | hybrid/unscripted with automated regression evidence |
| 37 | SPEC-QMS-012 | Quality Metrics, Trending & Effectiveness Checks | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 38 | SPEC-EQP-001 | Equipment, Calibration, Qualification & Maintenance | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 39 | SPEC-EQP-002 | Cleaning, Sanitization & Line Clearance | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 40 | SPEC-EQP-003 | Sterile / Aseptic Manufacturing Operations | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 41 | SPEC-EQP-004 | Environmental Monitoring & Cleanroom State Control | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 42 | SPEC-EQP-005 | Sterilization, CIP/SIP & Sterile Filtration Management | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 43 | SPEC-EDGE-001 | Edge Gateway Runtime Architecture & Construction Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 44 | SPEC-EDGE-002 | Industrial Device & Protocol Connectivity / Driver Specification | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 45 | SPEC-EDGE-003 | Store-and-Forward, Offline Buffering, Time Integrity & Data Quality | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 46 | SPEC-EDGE-004 | Barcode, Scanner, Balance, Printer, Tester & Peripheral Integration | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 47 | SPEC-EDGE-005 | Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 48 | SPEC-ERP-001 | Enterprise ERP Integration Architecture & Provider Contract | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 49 | SPEC-ERP-002 | ERPNext Adapter Detailed Contract | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 50 | SPEC-ERP-003 | SAP S/4HANA Adapter Contract | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 51 | SPEC-ERP-004 | Oracle Fusion, Dynamics 365 & Custom ERP Adapter Contracts | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 52 | SPEC-ERP-005 | Master Data Synchronization, Mapping & Reconciliation | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 53 | SPEC-ERP-006 | Integration Error Handling, Retry, Idempotency & Reconciliation | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 54 | SPEC-DDCP-001 | Prefilled Syringe & Injectable DDCP Manufacturing Profile | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 55 | SPEC-DDCP-002 | Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 56 | SPEC-DDCP-003 | Inhalation DDCP Manufacturing Profile — MDI / DPI | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 57 | SPEC-DDCP-004 | Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 58 | SPEC-PM-001 | Postmarket Surveillance, Safety Case & Signal Management | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 59 | SPEC-PM-002 | Regulatory Reportability Assessment & Electronic Safety Submission Management | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 60 | SPEC-PM-003 | Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 61 | SPEC-SEC-001 | Security Architecture, Threat Model & Control Framework | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 62 | SPEC-SEC-002 | Identity Federation, SSO, MFA, Sessions & Service Identities | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 63 | SPEC-SEC-003 | Privileged Access, Support Access, Break-Glass & Administrative Security | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 64 | SPEC-SEC-004 | Application, API, UI & Secure Runtime Engineering | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 65 | SPEC-SEC-005 | Secrets Management, PKI, Cryptography & Key Lifecycle | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 66 | SPEC-SEC-006 | Network, Tenant, Deployment Isolation & Zero-Trust Architecture | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 67 | SPEC-SEC-007 | Security Logging, Monitoring, Incident Response & Forensic Evidence | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 68 | SPEC-SEC-008 | Secure SDLC, Software Supply Chain, SBOM, Vulnerability & Release Security | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 69 | SPEC-DATA-001 | Enterprise Data Ownership, Persistence Topology & Data Lineage | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 70 | SPEC-DATA-002 | PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 71 | SPEC-DATA-003 | Frappe / MariaDB Operational Database, Projection & UI Data Architecture | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 72 | SPEC-DATA-004 | Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 73 | SPEC-DATA-005 | NATS / JetStream Event Bus, Transactional Outbox & Async Contracts | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 74 | SPEC-DATA-006 | Temporal Durable Workflow Orchestration Architecture | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 75 | SPEC-DATA-007 | Caching, Search, Read Models, Reporting Projections & Analytics Data Access | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 76 | SPEC-DATA-008 | Backup, Restore, Point-in-Time Recovery & Disaster Recovery | DIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 77 | SPEC-DATA-009 | Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 78 | SPEC-DATA-010 | Performance, Capacity, Observability, SLOs & SRE Operations | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 79 | SPEC-VAL-001 | Validation Master Plan & Computer Software Assurance Strategy | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 80 | SPEC-VAL-002 | Intended Use, GxP Criticality & Software Function Risk Classification | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 81 | SPEC-VAL-003 | Requirements, Design Inputs & Validation Traceability Management | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 82 | SPEC-VAL-004 | Validation Test Strategy, Test Methods & Objective Evidence Governance | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 83 | SPEC-VAL-005 | Installation Qualification (IQ) & Installed Baseline Verification | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 84 | SPEC-VAL-006 | Operational Qualification (OQ) & Functional Control Verification | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 85 | SPEC-VAL-007 | Performance Qualification (PQ), UAT & Business Process Verification | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 86 | SPEC-VAL-008 | Infrastructure, Cloud, Platform & Environment Qualification | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 87 | SPEC-VAL-009 | Data Migration, Conversion, Cutover & Reconciliation Validation | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 88 | SPEC-VAL-010 | 21 CFR Part 11 Electronic Records & Electronic Signature Validation | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 89 | SPEC-VAL-011 | Audit Trail, Record Version Vault & Data Integrity Validation | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 90 | SPEC-VAL-012 | Integration, Edge, Device, Peripheral & Interface Validation | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 91 | SPEC-VAL-013 | Backup, Restore, PITR & Disaster Recovery Qualification | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 92 | SPEC-VAL-014 | Security Qualification, Vulnerability Verification & Penetration Testing | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 93 | SPEC-VAL-015 | Performance, Load, Capacity & Reliability Qualification | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 94 | SPEC-VAL-016 | Validation Defect, Deviation, Test Exception & Remediation Management | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 95 | SPEC-VAL-017 | Validation Summary Report, Release-to-Production & Go-Live Authorization | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 96 | SPEC-VAL-018 | Periodic Review, Change Impact, Revalidation & Validated-State Maintenance | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 97 | SPEC-ENG-001 | Coding Standards | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 98 | SPEC-ENG-002 | Architecture Rules for Claude Code / Codex | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 99 | SPEC-ENG-003 | Repository & Branching Standard | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 100 | SPEC-ENG-004 | Database Migration Standard | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 101 | SPEC-ENG-005 | API & Event Contract Standard | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 102 | SPEC-ENG-006 | Testing Strategy | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 103 | SPEC-ENG-007 | CI/CD & Release Process | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 104 | SPEC-ENG-008 | SBOM / Third-Party License Management | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
| 105 | SPEC-AI-001 | AI Governance for Regulated Manufacturing | INDIRECT | **HIGHER-PROCESS-RISK** | scripted, independently reviewed, mandatory negative/failure evidence |
