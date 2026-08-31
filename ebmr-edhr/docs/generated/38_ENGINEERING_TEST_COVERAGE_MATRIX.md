# 38 — Engineering Test Coverage Matrix

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Required test types per module, driven by the approved risk classification.

---

| Module | WP | Risk | unit | property/fuzz | repository | API | contract | integration | E2E | authorization | signature | concurrency | failure/recovery | security | performance | validation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPEC-GXP-001 — GxP Mutation Gateway | WP-01 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-GXP-002 — 21 CFR Part 11 Electronic Signature | WP-01 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-GXP-003 — Immutable Audit Ledger & Audit Review | WP-01 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-GXP-004 — Record Version Vault, Locking, Amendment & Controlled Correction | WP-01 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-IAM-001 — Identity, Authorization, RBAC, Qualification & Segregation-of-Duties | WP-01 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-GXP-006 — Regulatory Rules & Calculation Engine | WP-01 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | OQ |
| SPEC-EBMR-000 — Product, Constituent & Regulatory Profile Master | WP-02 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-EBMR-001 — Master Recipe / Master Manufacturing Record Specification | WP-02 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-EBMR-002 — Batch Execution Engine & State Machine Specification | WP-02 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-EBMR-003 — eDHR / Device Production History Specification | WP-02 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | OQ |
| SPEC-EBMR-004 — Genealogy & Traceability Engine Specification | WP-03 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | ✓ | OQ |
| SPEC-EBMR-005 — Review-by-Exception & QA Review Specification | WP-03 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | OQ |
| SPEC-EBMR-006 — Release / Disposition Engine Specification | WP-03 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-EBMR-007 — Packaging, Labeling & Reconciliation Specification | WP-03 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-EBMR-008 — Yield, Calculations & Manufacturing Reconciliation Specification | WP-03 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | OQ |
| SPEC-MAT-001 — Procurement & Supplier Quality Specification | WP-04 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | OQ |
| SPEC-MAT-002A — Material Receipt, Quarantine & Quality Status Specification | WP-04 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-MAT-002B — Inventory, Lot/Container & Warehouse Specification | WP-04 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | OQ |
| SPEC-MAT-002C — Material Dispensing & Weighing Specification | WP-04 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-MAT-002D — Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification | WP-04 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | ✓ | OQ |
| SPEC-QC-001 — Native Basic QC & Sampling Specification | WP-04 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-QC-002 — LIMS Integration Architecture & Generic Adapter Contract | WP-04 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-QC-003 — OOS / OOT Management Specification | WP-04 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-QMS-001 — Deviation & Investigation Management | WP-05 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-QMS-002 — CAPA Management | WP-05 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-QMS-003 — Nonconformance Management | WP-05 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-QMS-004 — Change Control | WP-05 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-QMS-005 — Document Control | WP-05 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-QMS-006 — Training & Personnel Qualification | WP-05 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-QMS-007 — Supplier Quality / SCAR | WP-05 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | ✓ | OQ |
| SPEC-QMS-008 — Risk Management | WP-05 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-QMS-009 — Internal Audit Management | WP-05 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-QMS-010 — Complaint Management | WP-05 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-QMS-011 — Recall / Field Action Management | WP-05 | S | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | ✓ | — | — | sampled |
| SPEC-QMS-012 — Quality Metrics, Trending & Effectiveness Checks | WP-05 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | OQ |
| SPEC-EQP-001 — Equipment, Calibration, Qualification & Maintenance | WP-06 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-EQP-002 — Cleaning, Sanitization & Line Clearance | WP-06 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-EQP-003 — Sterile / Aseptic Manufacturing Operations | WP-06 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-EQP-004 — Environmental Monitoring & Cleanroom State Control | WP-06 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | ✓ | OQ |
| SPEC-EQP-005 — Sterilization, CIP/SIP & Sterile Filtration Management | WP-06 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-EDGE-001 — Edge Gateway Runtime Architecture & Construction Specification | WP-06 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-EDGE-002 — Industrial Device & Protocol Connectivity / Driver Specification | WP-06 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-EDGE-003 — Store-and-Forward, Offline Buffering, Time Integrity & Data Quality | WP-06 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-EDGE-004 — Barcode, Scanner, Balance, Printer, Tester & Peripheral Integration | WP-06 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-EDGE-005 — Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary | WP-06 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | OQ |
| SPEC-ERP-001 — Enterprise ERP Integration Architecture & Provider Contract | WP-07 | H | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-ERP-002 — ERPNext Adapter Detailed Contract | WP-07 | H | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-ERP-003 — SAP S/4HANA Adapter Contract | WP-07 | H | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-ERP-004 — Oracle Fusion, Dynamics 365 & Custom ERP Adapter Contracts | WP-07 | H | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-ERP-005 — Master Data Synchronization, Mapping & Reconciliation | WP-07 | H | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-ERP-006 — Integration Error Handling, Retry, Idempotency & Reconciliation | WP-07 | H | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-DDCP-001 — Prefilled Syringe & Injectable DDCP Manufacturing Profile | WP-08 | H | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-DDCP-002 — Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile | WP-08 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | OQ |
| SPEC-DDCP-003 — Inhalation DDCP Manufacturing Profile — MDI / DPI | WP-08 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | OQ |
| SPEC-DDCP-004 — Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile | WP-08 | H | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-PM-001 — Postmarket Surveillance, Safety Case & Signal Management | WP-09 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-PM-002 — Regulatory Reportability Assessment & Electronic Safety Submission Management | WP-09 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-PM-003 — Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar | WP-09 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-SEC-001 — Security Architecture, Threat Model & Control Framework | WP-10 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-SEC-002 — Identity Federation, SSO, MFA, Sessions & Service Identities | WP-10 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-SEC-003 — Privileged Access, Support Access, Break-Glass & Administrative Security | WP-10 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-SEC-004 — Application, API, UI & Secure Runtime Engineering | WP-10 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-SEC-005 — Secrets Management, PKI, Cryptography & Key Lifecycle | WP-10 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-SEC-006 — Network, Tenant, Deployment Isolation & Zero-Trust Architecture | WP-10 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-SEC-007 — Security Logging, Monitoring, Incident Response & Forensic Evidence | WP-10 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-SEC-008 — Secure SDLC, Software Supply Chain, SBOM, Vulnerability & Release Security | WP-10 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-DATA-001 — Enterprise Data Ownership, Persistence Topology & Data Lineage | WP-11 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-DATA-002 — PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency | WP-11 | H | ✓ | — | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-DATA-003 — Frappe / MariaDB Operational Database, Projection & UI Data Architecture | WP-11 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-DATA-004 — Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle | WP-11 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-DATA-005 — NATS / JetStream Event Bus, Transactional Outbox & Async Contracts | WP-11 | H | ✓ | — | ✓ | — | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-DATA-006 — Temporal Durable Workflow Orchestration Architecture | WP-11 | H | ✓ | — | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-DATA-007 — Caching, Search, Read Models, Reporting Projections & Analytics Data Access | WP-11 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-DATA-008 — Backup, Restore, Point-in-Time Recovery & Disaster Recovery | WP-11 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-DATA-009 — Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture | WP-11 | H | ✓ | — | ✓ | — | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | ✓ | OQ |
| SPEC-DATA-010 — Performance, Capacity, Observability, SLOs & SRE Operations | WP-11 | H | ✓ | — | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | OQ |
| SPEC-VAL-001 — Validation Master Plan & Computer Software Assurance Strategy | WP-12 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | OQ |
| SPEC-VAL-002 — Intended Use, GxP Criticality & Software Function Risk Classification | WP-12 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-VAL-003 — Requirements, Design Inputs & Validation Traceability Management | WP-12 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-VAL-004 — Validation Test Strategy, Test Methods & Objective Evidence Governance | WP-12 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-VAL-005 — Installation Qualification (IQ) & Installed Baseline Verification | WP-12 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-VAL-006 — Operational Qualification (OQ) & Functional Control Verification | WP-12 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-VAL-007 — Performance Qualification (PQ), UAT & Business Process Verification | WP-14 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-VAL-008 — Infrastructure, Cloud, Platform & Environment Qualification | WP-12 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-VAL-009 — Data Migration, Conversion, Cutover & Reconciliation Validation | WP-14 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-VAL-010 — 21 CFR Part 11 Electronic Records & Electronic Signature Validation | WP-12 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-VAL-011 — Audit Trail, Record Version Vault & Data Integrity Validation | WP-12 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-VAL-012 — Integration, Edge, Device, Peripheral & Interface Validation | WP-12 | H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-VAL-013 — Backup, Restore, PITR & Disaster Recovery Qualification | WP-12 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-VAL-014 — Security Qualification, Vulnerability Verification & Penetration Testing | WP-12 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-VAL-015 — Performance, Load, Capacity & Reliability Qualification | WP-12 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | OQ |
| SPEC-VAL-016 — Validation Defect, Deviation, Test Exception & Remediation Management | WP-12 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-VAL-017 — Validation Summary Report, Release-to-Production & Go-Live Authorization | WP-14 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | OQ |
| SPEC-VAL-018 — Periodic Review, Change Impact, Revalidation & Validated-State Maintenance | WP-12 | H | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-ENG-001 — Coding Standards | WP-00 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-ENG-002 — Architecture Rules for Claude Code / Codex | WP-00 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-ENG-003 — Repository & Branching Standard | WP-00 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |
| SPEC-ENG-004 — Database Migration Standard | WP-00 | H | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-ENG-005 — API & Event Contract Standard | WP-00 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | OQ |
| SPEC-ENG-006 — Testing Strategy | WP-00 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | OQ |
| SPEC-ENG-007 — CI/CD & Release Process | WP-00 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | OQ |
| SPEC-ENG-008 — SBOM / Third-Party License Management | WP-00 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | OQ |
| SPEC-AI-001 — AI Governance for Regulated Manufacturing | WP-13 | H | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | OQ |

**Rules:** every HIGHER-PROCESS-RISK function has explicit negative and failure tests. Coverage percentage is never the sole evidence.
