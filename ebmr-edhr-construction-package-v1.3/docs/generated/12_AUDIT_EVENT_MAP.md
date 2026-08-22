# 12 — Audit Event Map

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Every committed regulated mutation produces exactly one audit event in the same transaction (MUT-FR-015/016).

---

## Audit event content (Doc 05 / Doc 02 §15.2)

```text
actor (subject, name at time of action, source system/device)
action / command type
UTC timestamp (server-assigned)
record type / record id / previous version / resulting version
old → new representation or immutable reference
reason for change (where required)
signature reference (where applicable)
correlation id / causation id
rule version / software version
stream hash chain link (tamper evidence — ADR-015)
```

## Per-module audit surface

| Module | Auditable actions | Audit stream | Review-by-exception source | Source |
|---|---|---|---|---|
| SPEC-GXP-001 — GxP Mutation Gateway | 2 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 03 |
| SPEC-GXP-002 — 21 CFR Part 11 Electronic Signature | 3 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 04 |
| SPEC-GXP-003 — Immutable Audit Ledger & Audit Review | 1 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 05 |
| SPEC-GXP-004 — Record Version Vault, Locking, Amendment & Controlled Correction | 3 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 06 |
| SPEC-IAM-001 — Identity, Authorization, RBAC, Qualification & Segregation-of-Duties | 4 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 07 |
| SPEC-GXP-006 — Regulatory Rules & Calculation Engine | 5 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 08 |
| SPEC-EBMR-000 — Product, Constituent & Regulatory Profile Master | 7 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 09 |
| SPEC-EBMR-001 — Master Recipe / Master Manufacturing Record Specification | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 10 |
| SPEC-EBMR-002 — Batch Execution Engine & State Machine Specification | 12 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 11 |
| SPEC-EBMR-003 — eDHR / Device Production History Specification | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 12 |
| SPEC-EBMR-004 — Genealogy & Traceability Engine Specification | 2 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 13 |
| SPEC-EBMR-005 — Review-by-Exception & QA Review Specification | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 14 |
| SPEC-EBMR-006 — Release / Disposition Engine Specification | 7 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 15 |
| SPEC-EBMR-007 — Packaging, Labeling & Reconciliation Specification | 10 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 16 |
| SPEC-EBMR-008 — Yield, Calculations & Manufacturing Reconciliation Specification | 7 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 17 |
| SPEC-MAT-001 — Procurement & Supplier Quality Specification | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 18 |
| SPEC-MAT-002A — Material Receipt, Quarantine & Quality Status Specification | 7 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 19 |
| SPEC-MAT-002B — Inventory, Lot/Container & Warehouse Specification | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 20 |
| SPEC-MAT-002C — Material Dispensing & Weighing Specification | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 21 |
| SPEC-MAT-002D — Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification | 7 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 22 |
| SPEC-QC-001 — Native Basic QC & Sampling Specification | 11 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 23 |
| SPEC-QC-002 — LIMS Integration Architecture & Generic Adapter Contract | 5 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 24 |
| SPEC-QC-003 — OOS / OOT Management Specification | 11 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 25 |
| SPEC-QMS-001 — Deviation & Investigation Management | 9 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 26 |
| SPEC-QMS-002 — CAPA Management | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 27 |
| SPEC-QMS-003 — Nonconformance Management | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 28 |
| SPEC-QMS-004 — Change Control | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 29 |
| SPEC-QMS-005 — Document Control | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 30 |
| SPEC-QMS-006 — Training & Personnel Qualification | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 31 |
| SPEC-QMS-007 — Supplier Quality / SCAR | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 32 |
| SPEC-QMS-008 — Risk Management | 5 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 33 |
| SPEC-QMS-009 — Internal Audit Management | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 34 |
| SPEC-QMS-010 — Complaint Management | 7 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 35 |
| SPEC-QMS-011 — Recall / Field Action Management | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 36 |
| SPEC-QMS-012 — Quality Metrics, Trending & Effectiveness Checks | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 37 |
| SPEC-EQP-001 — Equipment, Calibration, Qualification & Maintenance | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 38 |
| SPEC-EQP-002 — Cleaning, Sanitization & Line Clearance | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 39 |
| SPEC-EQP-003 — Sterile / Aseptic Manufacturing Operations | 5 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 40 |
| SPEC-EQP-004 — Environmental Monitoring & Cleanroom State Control | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 41 |
| SPEC-EQP-005 — Sterilization, CIP/SIP & Sterile Filtration Management | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 42 |
| SPEC-EDGE-001 — Edge Gateway Runtime Architecture & Construction Specification | 5 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 43 |
| SPEC-EDGE-002 — Industrial Device & Protocol Connectivity / Driver Specification | 12 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 44 |
| SPEC-EDGE-003 — Store-and-Forward, Offline Buffering, Time Integrity & Data Quality | 10 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 45 |
| SPEC-EDGE-004 — Barcode, Scanner, Balance, Printer, Tester & Peripheral Integration | 10 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 46 |
| SPEC-EDGE-005 — Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary | 10 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 47 |
| SPEC-ERP-001 — Enterprise ERP Integration Architecture & Provider Contract | 10 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 48 |
| SPEC-ERP-002 — ERPNext Adapter Detailed Contract | 10 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 49 |
| SPEC-ERP-003 — SAP S/4HANA Adapter Contract | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 50 |
| SPEC-ERP-004 — Oracle Fusion, Dynamics 365 & Custom ERP Adapter Contracts | 9 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 51 |
| SPEC-ERP-005 — Master Data Synchronization, Mapping & Reconciliation | 10 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 52 |
| SPEC-ERP-006 — Integration Error Handling, Retry, Idempotency & Reconciliation | 12 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 53 |
| SPEC-DDCP-001 — Prefilled Syringe & Injectable DDCP Manufacturing Profile | 11 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 54 |
| SPEC-DDCP-002 — Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile | 10 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 55 |
| SPEC-DDCP-003 — Inhalation DDCP Manufacturing Profile — MDI / DPI | 9 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 56 |
| SPEC-DDCP-004 — Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile | 10 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 57 |
| SPEC-PM-001 — Postmarket Surveillance, Safety Case & Signal Management | 10 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 58 |
| SPEC-PM-002 — Regulatory Reportability Assessment & Electronic Safety Submission Management | 10 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 59 |
| SPEC-PM-003 — Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar | 14 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 60 |
| SPEC-SEC-001 — Security Architecture, Threat Model & Control Framework | 5 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 61 |
| SPEC-SEC-002 — Identity Federation, SSO, MFA, Sessions & Service Identities | 4 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 62 |
| SPEC-SEC-003 — Privileged Access, Support Access, Break-Glass & Administrative Security | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 63 |
| SPEC-SEC-004 — Application, API, UI & Secure Runtime Engineering | 2 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 64 |
| SPEC-SEC-005 — Secrets Management, PKI, Cryptography & Key Lifecycle | 4 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 65 |
| SPEC-SEC-006 — Network, Tenant, Deployment Isolation & Zero-Trust Architecture | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 66 |
| SPEC-SEC-007 — Security Logging, Monitoring, Incident Response & Forensic Evidence | 5 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 67 |
| SPEC-SEC-008 — Secure SDLC, Software Supply Chain, SBOM, Vulnerability & Release Security | 3 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 68 |
| SPEC-DATA-001 — Enterprise Data Ownership, Persistence Topology & Data Lineage | 1 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 69 |
| SPEC-DATA-002 — PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 70 |
| SPEC-DATA-003 — Frappe / MariaDB Operational Database, Projection & UI Data Architecture | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 71 |
| SPEC-DATA-004 — Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle | 5 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 72 |
| SPEC-DATA-005 — NATS / JetStream Event Bus, Transactional Outbox & Async Contracts | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 73 |
| SPEC-DATA-006 — Temporal Durable Workflow Orchestration Architecture | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 74 |
| SPEC-DATA-007 — Caching, Search, Read Models, Reporting Projections & Analytics Data Access | 2 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 75 |
| SPEC-DATA-008 — Backup, Restore, Point-in-Time Recovery & Disaster Recovery | 2 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 76 |
| SPEC-DATA-009 — Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 77 |
| SPEC-DATA-010 — Performance, Capacity, Observability, SLOs & SRE Operations | 9 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 78 |
| SPEC-VAL-001 — Validation Master Plan & Computer Software Assurance Strategy | 2 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 79 |
| SPEC-VAL-002 — Intended Use, GxP Criticality & Software Function Risk Classification | 3 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 80 |
| SPEC-VAL-003 — Requirements, Design Inputs & Validation Traceability Management | 3 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 81 |
| SPEC-VAL-004 — Validation Test Strategy, Test Methods & Objective Evidence Governance | 5 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 82 |
| SPEC-VAL-005 — Installation Qualification (IQ) & Installed Baseline Verification | 4 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 83 |
| SPEC-VAL-006 — Operational Qualification (OQ) & Functional Control Verification | 3 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 84 |
| SPEC-VAL-007 — Performance Qualification (PQ), UAT & Business Process Verification | 4 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 85 |
| SPEC-VAL-008 — Infrastructure, Cloud, Platform & Environment Qualification | 4 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 86 |
| SPEC-VAL-009 — Data Migration, Conversion, Cutover & Reconciliation Validation | 4 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 87 |
| SPEC-VAL-010 — 21 CFR Part 11 Electronic Records & Electronic Signature Validation | 2 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 88 |
| SPEC-VAL-011 — Audit Trail, Record Version Vault & Data Integrity Validation | 3 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 89 |
| SPEC-VAL-012 — Integration, Edge, Device, Peripheral & Interface Validation | 4 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 90 |
| SPEC-VAL-013 — Backup, Restore, PITR & Disaster Recovery Qualification | 4 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 91 |
| SPEC-VAL-014 — Security Qualification, Vulnerability Verification & Penetration Testing | 4 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 92 |
| SPEC-VAL-015 — Performance, Load, Capacity & Reliability Qualification | 3 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 93 |
| SPEC-VAL-016 — Validation Defect, Deviation, Test Exception & Remediation Management | 4 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 94 |
| SPEC-VAL-017 — Validation Summary Report, Release-to-Production & Go-Live Authorization | 4 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 95 |
| SPEC-VAL-018 — Periodic Review, Change Impact, Revalidation & Validated-State Maintenance | 6 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 96 |
| SPEC-ENG-001 — Coding Standards | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 97 |
| SPEC-ENG-002 — Architecture Rules for Claude Code / Codex | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 98 |
| SPEC-ENG-003 — Repository & Branching Standard | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 99 |
| SPEC-ENG-004 — Database Migration Standard | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 100 |
| SPEC-ENG-005 — API & Event Contract Standard | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 101 |
| SPEC-ENG-006 — Testing Strategy | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 102 |
| SPEC-ENG-007 — CI/CD & Release Process | 9 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 103 |
| SPEC-ENG-008 — SBOM / Third-Party License Management | 8 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 104 |
| SPEC-AI-001 — AI Governance for Regulated Manufacturing | 13 | `gxp_audit_event` (partitioned, Doc 70) | exceptions, corrections, overrides, holds | Doc 105 |

## Invariants

- No regulated state may commit without its audit companion in the same transaction.
- Audit records are append-only: no UPDATE, no DELETE, no re-ordering (AG-08).
- Per-record-stream hash chain plus periodic signed integrity checkpoint (ADR-015).
- Audit review is a first-class product surface, not a database query (Doc 05).
- Security events (denied/replay/malformed) are a separate stream from GxP audit (MUT-FR-031).
