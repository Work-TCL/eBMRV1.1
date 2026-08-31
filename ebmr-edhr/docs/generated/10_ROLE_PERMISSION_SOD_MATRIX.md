# 10 — Role / Permission / SoD Matrix

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Reference role model (Doc 01 §6.1), SoD rule classes (Doc 01 §6.2) and the policy contract (Doc 07).

---

## Reference roles (configurable — customer role names are configuration, not code)

**Enterprise / IT**
- Enterprise Administrator
- Site Administrator
- Application Administrator
- Security Administrator
- Integration Service Account
- Read-only Auditor / Inspector

**Production**
- Production Manager
- Production Supervisor
- Operator
- Dispensing Operator
- Packaging Operator

**Quality Assurance**
- Head of Quality
- QA Manager
- QA Reviewer
- QA Approver / Batch Release
- Deviation Investigator
- CAPA Owner

**Quality Control**
- QC Manager
- QC Analyst
- Sampler

**Warehouse / Material**
- Warehouse Manager
- Material Receiver
- Material Issuer
- Material Handler

**Procurement / Supplier Quality**
- Procurement Manager
- Buyer
- Supplier Quality Manager / Engineer

**Engineering**
- Engineering Manager
- Maintenance Technician
- Calibration Technician
- Equipment Administrator

**QMS Support**
- Document Controller
- Training Coordinator
- Complaint Investigator
- Internal Auditor

## Segregation-of-duties rule classes the policy engine must support

1. performer cannot verify the same controlled action where independent verification is required
2. verifier cannot be substituted silently after execution
3. production performer cannot perform independent QA release where prohibited by customer procedure
4. authors cannot approve their own released master record where configured
5. system administrators cannot create regulatory signatures on behalf of users
6. security administrators cannot alter released batch content
7. emergency access must be time-limited, reason-coded and independently reviewed
8. incompatible role combinations shall be configurable and reportable
9. every privilege elevation shall be audited
10. periodic access review reports shall be available

## Authorization decision inputs (Doc 07 / Doc 02 §20.1)

```text
subject (human | service | device) → roles → site/tenant scope → qualifications/training currency
→ resource type/state/version → requested action → SoD context → time/session assurance
→ ALLOW | DENY + obligation (signature, reason, second signer)
```

## Module permission surface

| Module | Work package | Actions requiring policy decision | Qualification gate | SoD sensitivity |
|---|---|---|---|---|
| SPEC-GXP-001 — GxP Mutation Gateway | WP-01 | 2 | yes | HIGH |
| SPEC-GXP-002 — 21 CFR Part 11 Electronic Signature | WP-01 | 3 | yes | HIGH |
| SPEC-GXP-003 — Immutable Audit Ledger & Audit Review | WP-01 | 1 | per configuration | HIGH |
| SPEC-GXP-004 — Record Version Vault, Locking, Amendment & Controlled Correction | WP-01 | 3 | yes | HIGH |
| SPEC-IAM-001 — Identity, Authorization, RBAC, Qualification & Segregation-of-Duties | WP-01 | 4 | yes | HIGH |
| SPEC-GXP-006 — Regulatory Rules & Calculation Engine | WP-01 | 5 | yes | HIGH |
| SPEC-EBMR-000 — Product, Constituent & Regulatory Profile Master | WP-02 | 7 | per configuration | HIGH |
| SPEC-EBMR-001 — Master Recipe / Master Manufacturing Record Specification | WP-02 | 6 | yes | HIGH |
| SPEC-EBMR-002 — Batch Execution Engine & State Machine Specification | WP-02 | 12 | yes | HIGH |
| SPEC-EBMR-003 — eDHR / Device Production History Specification | WP-02 | 8 | yes | HIGH |
| SPEC-EBMR-004 — Genealogy & Traceability Engine Specification | WP-03 | 2 | yes | HIGH |
| SPEC-EBMR-005 — Review-by-Exception & QA Review Specification | WP-03 | 6 | yes | HIGH |
| SPEC-EBMR-006 — Release / Disposition Engine Specification | WP-03 | 7 | yes | HIGH |
| SPEC-EBMR-007 — Packaging, Labeling & Reconciliation Specification | WP-03 | 10 | yes | HIGH |
| SPEC-EBMR-008 — Yield, Calculations & Manufacturing Reconciliation Specification | WP-03 | 7 | yes | HIGH |
| SPEC-MAT-001 — Procurement & Supplier Quality Specification | WP-04 | 8 | yes | HIGH |
| SPEC-MAT-002A — Material Receipt, Quarantine & Quality Status Specification | WP-04 | 7 | yes | HIGH |
| SPEC-MAT-002B — Inventory, Lot/Container & Warehouse Specification | WP-04 | 6 | yes | HIGH |
| SPEC-MAT-002C — Material Dispensing & Weighing Specification | WP-04 | 8 | yes | HIGH |
| SPEC-MAT-002D — Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification | WP-04 | 7 | yes | HIGH |
| SPEC-QC-001 — Native Basic QC & Sampling Specification | WP-04 | 11 | yes | HIGH |
| SPEC-QC-002 — LIMS Integration Architecture & Generic Adapter Contract | WP-04 | 5 | yes | HIGH |
| SPEC-QC-003 — OOS / OOT Management Specification | WP-04 | 11 | yes | HIGH |
| SPEC-QMS-001 — Deviation & Investigation Management | WP-05 | 9 | yes | HIGH |
| SPEC-QMS-002 — CAPA Management | WP-05 | 8 | yes | HIGH |
| SPEC-QMS-003 — Nonconformance Management | WP-05 | 6 | yes | HIGH |
| SPEC-QMS-004 — Change Control | WP-05 | 8 | per configuration | HIGH |
| SPEC-QMS-005 — Document Control | WP-05 | 6 | per configuration | HIGH |
| SPEC-QMS-006 — Training & Personnel Qualification | WP-05 | 6 | yes | HIGH |
| SPEC-QMS-007 — Supplier Quality / SCAR | WP-05 | 6 | yes | HIGH |
| SPEC-QMS-008 — Risk Management | WP-05 | 5 | yes | HIGH |
| SPEC-QMS-009 — Internal Audit Management | WP-05 | 6 | yes | HIGH |
| SPEC-QMS-010 — Complaint Management | WP-05 | 7 | per configuration | HIGH |
| SPEC-QMS-011 — Recall / Field Action Management | WP-05 | 8 | yes | HIGH |
| SPEC-QMS-012 — Quality Metrics, Trending & Effectiveness Checks | WP-05 | 6 | yes | HIGH |
| SPEC-EQP-001 — Equipment, Calibration, Qualification & Maintenance | WP-06 | 6 | yes | HIGH |
| SPEC-EQP-002 — Cleaning, Sanitization & Line Clearance | WP-06 | 6 | per configuration | HIGH |
| SPEC-EQP-003 — Sterile / Aseptic Manufacturing Operations | WP-06 | 5 | yes | HIGH |
| SPEC-EQP-004 — Environmental Monitoring & Cleanroom State Control | WP-06 | 6 | per configuration | HIGH |
| SPEC-EQP-005 — Sterilization, CIP/SIP & Sterile Filtration Management | WP-06 | 8 | yes | HIGH |
| SPEC-EDGE-001 — Edge Gateway Runtime Architecture & Construction Specification | WP-06 | 5 | yes | HIGH |
| SPEC-EDGE-002 — Industrial Device & Protocol Connectivity / Driver Specification | WP-06 | 12 | yes | HIGH |
| SPEC-EDGE-003 — Store-and-Forward, Offline Buffering, Time Integrity & Data Quality | WP-06 | 10 | yes | HIGH |
| SPEC-EDGE-004 — Barcode, Scanner, Balance, Printer, Tester & Peripheral Integration | WP-06 | 10 | per configuration | HIGH |
| SPEC-EDGE-005 — Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary | WP-06 | 10 | yes | HIGH |
| SPEC-ERP-001 — Enterprise ERP Integration Architecture & Provider Contract | WP-07 | 10 | yes | HIGH |
| SPEC-ERP-002 — ERPNext Adapter Detailed Contract | WP-07 | 10 | yes | HIGH |
| SPEC-ERP-003 — SAP S/4HANA Adapter Contract | WP-07 | 8 | yes | HIGH |
| SPEC-ERP-004 — Oracle Fusion, Dynamics 365 & Custom ERP Adapter Contracts | WP-07 | 9 | yes | HIGH |
| SPEC-ERP-005 — Master Data Synchronization, Mapping & Reconciliation | WP-07 | 10 | yes | standard |
| SPEC-ERP-006 — Integration Error Handling, Retry, Idempotency & Reconciliation | WP-07 | 12 | yes | HIGH |
| SPEC-DDCP-001 — Prefilled Syringe & Injectable DDCP Manufacturing Profile | WP-08 | 11 | yes | HIGH |
| SPEC-DDCP-002 — Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile | WP-08 | 10 | yes | HIGH |
| SPEC-DDCP-003 — Inhalation DDCP Manufacturing Profile — MDI / DPI | WP-08 | 9 | yes | HIGH |
| SPEC-DDCP-004 — Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile | WP-08 | 10 | yes | HIGH |
| SPEC-PM-001 — Postmarket Surveillance, Safety Case & Signal Management | WP-09 | 10 | per configuration | HIGH |
| SPEC-PM-002 — Regulatory Reportability Assessment & Electronic Safety Submission Management | WP-09 | 10 | yes | HIGH |
| SPEC-PM-003 — Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar | WP-09 | 14 | per configuration | standard |
| SPEC-SEC-001 — Security Architecture, Threat Model & Control Framework | WP-10 | 5 | yes | HIGH |
| SPEC-SEC-002 — Identity Federation, SSO, MFA, Sessions & Service Identities | WP-10 | 4 | yes | HIGH |
| SPEC-SEC-003 — Privileged Access, Support Access, Break-Glass & Administrative Security | WP-10 | 6 | per configuration | HIGH |
| SPEC-SEC-004 — Application, API, UI & Secure Runtime Engineering | WP-10 | 2 | yes | HIGH |
| SPEC-SEC-005 — Secrets Management, PKI, Cryptography & Key Lifecycle | WP-10 | 4 | yes | HIGH |
| SPEC-SEC-006 — Network, Tenant, Deployment Isolation & Zero-Trust Architecture | WP-10 | 6 | yes | standard |
| SPEC-SEC-007 — Security Logging, Monitoring, Incident Response & Forensic Evidence | WP-10 | 5 | yes | HIGH |
| SPEC-SEC-008 — Secure SDLC, Software Supply Chain, SBOM, Vulnerability & Release Security | WP-10 | 3 | yes | HIGH |
| SPEC-DATA-001 — Enterprise Data Ownership, Persistence Topology & Data Lineage | WP-11 | 1 | yes | HIGH |
| SPEC-DATA-002 — PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency | WP-11 | 8 | yes | HIGH |
| SPEC-DATA-003 — Frappe / MariaDB Operational Database, Projection & UI Data Architecture | WP-11 | 6 | yes | HIGH |
| SPEC-DATA-004 — Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle | WP-11 | 5 | yes | HIGH |
| SPEC-DATA-005 — NATS / JetStream Event Bus, Transactional Outbox & Async Contracts | WP-11 | 8 | yes | HIGH |
| SPEC-DATA-006 — Temporal Durable Workflow Orchestration Architecture | WP-11 | 8 | yes | HIGH |
| SPEC-DATA-007 — Caching, Search, Read Models, Reporting Projections & Analytics Data Access | WP-11 | 2 | yes | HIGH |
| SPEC-DATA-008 — Backup, Restore, Point-in-Time Recovery & Disaster Recovery | WP-11 | 2 | yes | HIGH |
| SPEC-DATA-009 — Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture | WP-11 | 8 | per configuration | HIGH |
| SPEC-DATA-010 — Performance, Capacity, Observability, SLOs & SRE Operations | WP-11 | 9 | per configuration | HIGH |
| SPEC-VAL-001 — Validation Master Plan & Computer Software Assurance Strategy | WP-12 | 2 | yes | HIGH |
| SPEC-VAL-002 — Intended Use, GxP Criticality & Software Function Risk Classification | WP-12 | 3 | yes | HIGH |
| SPEC-VAL-003 — Requirements, Design Inputs & Validation Traceability Management | WP-12 | 3 | yes | HIGH |
| SPEC-VAL-004 — Validation Test Strategy, Test Methods & Objective Evidence Governance | WP-12 | 5 | yes | HIGH |
| SPEC-VAL-005 — Installation Qualification (IQ) & Installed Baseline Verification | WP-12 | 4 | per configuration | HIGH |
| SPEC-VAL-006 — Operational Qualification (OQ) & Functional Control Verification | WP-12 | 3 | per configuration | HIGH |
| SPEC-VAL-007 — Performance Qualification (PQ), UAT & Business Process Verification | WP-14 | 4 | yes | HIGH |
| SPEC-VAL-008 — Infrastructure, Cloud, Platform & Environment Qualification | WP-12 | 4 | per configuration | HIGH |
| SPEC-VAL-009 — Data Migration, Conversion, Cutover & Reconciliation Validation | WP-14 | 4 | yes | HIGH |
| SPEC-VAL-010 — 21 CFR Part 11 Electronic Records & Electronic Signature Validation | WP-12 | 2 | yes | HIGH |
| SPEC-VAL-011 — Audit Trail, Record Version Vault & Data Integrity Validation | WP-12 | 3 | yes | HIGH |
| SPEC-VAL-012 — Integration, Edge, Device, Peripheral & Interface Validation | WP-12 | 4 | yes | HIGH |
| SPEC-VAL-013 — Backup, Restore, PITR & Disaster Recovery Qualification | WP-12 | 4 | yes | HIGH |
| SPEC-VAL-014 — Security Qualification, Vulnerability Verification & Penetration Testing | WP-12 | 4 | yes | HIGH |
| SPEC-VAL-015 — Performance, Load, Capacity & Reliability Qualification | WP-12 | 3 | per configuration | HIGH |
| SPEC-VAL-016 — Validation Defect, Deviation, Test Exception & Remediation Management | WP-12 | 4 | yes | HIGH |
| SPEC-VAL-017 — Validation Summary Report, Release-to-Production & Go-Live Authorization | WP-14 | 4 | yes | HIGH |
| SPEC-VAL-018 — Periodic Review, Change Impact, Revalidation & Validated-State Maintenance | WP-12 | 6 | per configuration | HIGH |
| SPEC-ENG-001 — Coding Standards | WP-00 | 8 | yes | HIGH |
| SPEC-ENG-002 — Architecture Rules for Claude Code / Codex | WP-00 | 8 | per configuration | HIGH |
| SPEC-ENG-003 — Repository & Branching Standard | WP-00 | 8 | yes | HIGH |
| SPEC-ENG-004 — Database Migration Standard | WP-00 | 8 | per configuration | HIGH |
| SPEC-ENG-005 — API & Event Contract Standard | WP-00 | 8 | yes | HIGH |
| SPEC-ENG-006 — Testing Strategy | WP-00 | 8 | yes | HIGH |
| SPEC-ENG-007 — CI/CD & Release Process | WP-00 | 9 | yes | HIGH |
| SPEC-ENG-008 — SBOM / Third-Party License Management | WP-00 | 8 | yes | HIGH |
| SPEC-AI-001 — AI Governance for Regulated Manufacturing | WP-13 | 13 | yes | HIGH |

> **SG-009**: the product-default incompatible-role matrix (which concrete reference roles may not be held together) is not enumerated in the baseline. The engine is specified; the default data set is not. Do not invent it — see `18_SPEC_GAPS.md`.
