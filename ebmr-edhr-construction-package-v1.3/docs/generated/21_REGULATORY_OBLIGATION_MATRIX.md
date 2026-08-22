# 21 — Regulatory Obligation Matrix

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Predicate rules and standards cited by each module, and the platform control that satisfies them.

---

| Doc | Module | Regulatory / standard citations found in the specification | Implementing controls |
|---|---|---|---|
| 01 | DOC-001 — Master Product, Compliance & Architecture Bible | 21 CFR Part 11, 21 CFR Part 4, 21 CFR Part 803, 21 CFR Part 806, 21 CFR Part 820, 21 CFR Part 821, 21 CFR Part 830, ISO 13485 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05); Record Version Vault (Doc 06); Policy/SoD (Doc 07 / Doc 107) |
| 03 | SPEC-GXP-001 — GxP Mutation Gateway | 21 CFR Part 11, §11.10, §11.100, §11.200, §11.300, §11.50, §11.70, §211.68 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05); Record Version Vault (Doc 06); Policy/SoD (Doc 07 / Doc 107); Retention (Doc 108) |
| 04 | SPEC-GXP-002 — 21 CFR Part 11 Electronic Signature | 21 CFR Part 11, §11.10, §11.100, §11.200, §11.300, §11.50, §11.70, §211.68 | Part 11 signature (Doc 04 / Doc 106); Record Version Vault (Doc 06) |
| 05 | SPEC-GXP-003 — Immutable Audit Ledger & Audit Review | 21 CFR Part 11, §11.10, §11.100, §11.200, §11.300, §11.50, §11.70, §211.68 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05); Record Version Vault (Doc 06); Retention (Doc 108) |
| 06 | SPEC-GXP-004 — Record Version Vault, Locking, Amendment & Controlled Correction | 21 CFR Part 11, §11.10, §11.100, §11.200, §11.300, §11.50, §11.70, §211.68 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05); Record Version Vault (Doc 06); Retention (Doc 108) |
| 07 | SPEC-IAM-001 — Identity, Authorization, RBAC, Qualification & Segregation-of-Duties | 21 CFR Part 11, §11.10, §11.100, §11.200, §11.300, §11.50, §11.70, §211.68 | Part 11 signature (Doc 04 / Doc 106); Policy/SoD (Doc 07 / Doc 107) |
| 08 | SPEC-GXP-006 — Regulatory Rules & Calculation Engine | 21 CFR Part 11, §11.10, §11.100, §11.200, §11.300, §11.50, §11.70, §211.103, §211.68 | Part 11 signature (Doc 04 / Doc 106); Record Version Vault (Doc 06) |
| 09 | SPEC-EBMR-000 — Product, Constituent & Regulatory Profile Master | 21 CFR Part 11, 21 CFR Part 211, 21 CFR Part 4, 21 CFR Part 820, 21 CFR Part 830, ISO 13485, §211.103, §211.186, §211.188, §820.10, §820.35, §820.45 | Record Version Vault (Doc 06); Policy/SoD (Doc 07 / Doc 107) |
| 10 | SPEC-EBMR-001 — Master Recipe / Master Manufacturing Record Specification | 21 CFR Part 11, 21 CFR Part 211, 21 CFR Part 4, 21 CFR Part 820, 21 CFR Part 830, ISO 13485, §211.103, §211.186, §211.188, §820.10, §820.35, §820.45 | Part 11 signature (Doc 04 / Doc 106); Record Version Vault (Doc 06) |
| 11 | SPEC-EBMR-002 — Batch Execution Engine & State Machine Specification | 21 CFR Part 11, 21 CFR Part 211, 21 CFR Part 4, 21 CFR Part 820, 21 CFR Part 830, ISO 13485, §211.103, §211.186, §211.188, §820.10, §820.35, §820.45 | Part 11 signature (Doc 04 / Doc 106); Policy/SoD (Doc 07 / Doc 107) |
| 12 | SPEC-EBMR-003 — eDHR / Device Production History Specification | 21 CFR Part 11, 21 CFR Part 211, 21 CFR Part 4, 21 CFR Part 820, 21 CFR Part 830, ISO 13485, §211.103, §211.186, §211.188, §820.10, §820.35, §820.45 | Part 11 signature (Doc 04 / Doc 106); Record Version Vault (Doc 06) |
| 13 | SPEC-EBMR-004 — Genealogy & Traceability Engine Specification | 21 CFR Part 11, 21 CFR Part 211, 21 CFR Part 4, 21 CFR Part 820, 21 CFR Part 830, ISO 13485, §211.103, §211.186, §211.188, §820.10, §820.35, §820.45 | Record Version Vault (Doc 06) |
| 14 | SPEC-EBMR-005 — Review-by-Exception & QA Review Specification | 21 CFR Part 11, 21 CFR Part 211, 21 CFR Part 4, 21 CFR Part 820, 21 CFR Part 830, ISO 13485, §211.103, §211.186, §211.188, §820.10, §820.35, §820.45 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05); Record Version Vault (Doc 06); Retention (Doc 108) |
| 15 | SPEC-EBMR-006 — Release / Disposition Engine Specification | 21 CFR Part 11, 21 CFR Part 211, 21 CFR Part 4, 21 CFR Part 820, 21 CFR Part 830, ISO 13485, §211.103, §211.186, §211.188, §820.10, §820.35, §820.45 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05) |
| 16 | SPEC-EBMR-007 — Packaging, Labeling & Reconciliation Specification | 21 CFR Part 11, 21 CFR Part 211, 21 CFR Part 4, 21 CFR Part 820, 21 CFR Part 830, ISO 13485, §211.103, §211.186, §211.188, §820.10, §820.35, §820.45 | Audit ledger (Doc 05); Record Version Vault (Doc 06) |
| 17 | SPEC-EBMR-008 — Yield, Calculations & Manufacturing Reconciliation Specification | 21 CFR Part 11, 21 CFR Part 211, 21 CFR Part 4, 21 CFR Part 820, 21 CFR Part 830, ISO 13485, §211.103, §211.186, §211.188, §820.10, §820.35, §820.45 | Part 11 signature (Doc 04 / Doc 106); Record Version Vault (Doc 06) |
| 18 | SPEC-MAT-001 — Procurement & Supplier Quality Specification | 21 CFR Part 4, 21 CFR Part 820, ISO 13485, §211.80, §211.82, §211.84, §211.86, §211.87, §211.89, §211.94 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05); Policy/SoD (Doc 07 / Doc 107) |
| 19 | SPEC-MAT-002A — Material Receipt, Quarantine & Quality Status Specification | 21 CFR Part 4, 21 CFR Part 820, ISO 13485, §211.80, §211.82, §211.84, §211.86, §211.87, §211.89, §211.94 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05) |
| 20 | SPEC-MAT-002B — Inventory, Lot/Container & Warehouse Specification | 21 CFR Part 4, 21 CFR Part 820, ISO 13485, §211.80, §211.82, §211.84, §211.86, §211.87, §211.89, §211.94 | Part 11 signature (Doc 04 / Doc 106); Retention (Doc 108) |
| 21 | SPEC-MAT-002C — Material Dispensing & Weighing Specification | 21 CFR Part 4, 21 CFR Part 820, ISO 13485, §211.80, §211.82, §211.84, §211.86, §211.87, §211.89, §211.94 | Audit ledger (Doc 05); Policy/SoD (Doc 07 / Doc 107) |
| 22 | SPEC-MAT-002D — Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification | 21 CFR Part 4, 21 CFR Part 820, ISO 13485, §211.80, §211.82, §211.84, §211.86, §211.87, §211.89, §211.94 | Audit ledger (Doc 05); Policy/SoD (Doc 07 / Doc 107) |
| 23 | SPEC-QC-001 — Native Basic QC & Sampling Specification | §211.160, §211.165, §211.194 | Part 11 signature (Doc 04 / Doc 106) |
| 24 | SPEC-QC-002 — LIMS Integration Architecture & Generic Adapter Contract | §211.160, §211.165, §211.194 | Audit ledger (Doc 05); Record Version Vault (Doc 06) |
| 25 | SPEC-QC-003 — OOS / OOT Management Specification | §211.160, §211.165, §211.194 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05); Policy/SoD (Doc 07 / Doc 107) |
| 26 | SPEC-QMS-001 — Deviation & Investigation Management | 21 CFR Part 820, ISO 13485, §211.192 | Part 11 signature (Doc 04 / Doc 106) |
| 27 | SPEC-QMS-002 — CAPA Management | 21 CFR Part 820, ISO 13485, §211.192 | Part 11 signature (Doc 04 / Doc 106) |
| 28 | SPEC-QMS-003 — Nonconformance Management | 21 CFR Part 820, ISO 13485, §211.192 | Part 11 signature (Doc 04 / Doc 106) |
| 29 | SPEC-QMS-004 — Change Control | 21 CFR Part 820, ISO 13485, §211.192 | Domain controls in the owning module |
| 30 | SPEC-QMS-005 — Document Control | 21 CFR Part 820, ISO 13485 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05); Record Version Vault (Doc 06) |
| 31 | SPEC-QMS-006 — Training & Personnel Qualification | 21 CFR Part 820, ISO 13485 | Part 11 signature (Doc 04 / Doc 106); Record Version Vault (Doc 06); Policy/SoD (Doc 07 / Doc 107) |
| 32 | SPEC-QMS-007 — Supplier Quality / SCAR | 21 CFR Part 820, ISO 13485 | Policy/SoD (Doc 07 / Doc 107) |
| 33 | SPEC-QMS-008 — Risk Management | 21 CFR Part 820, ISO 13485 | Part 11 signature (Doc 04 / Doc 106); Record Version Vault (Doc 06) |
| 34 | SPEC-QMS-009 — Internal Audit Management | 21 CFR Part 4, 21 CFR Part 806, ISO 13485, §211.198 | Audit ledger (Doc 05) |
| 35 | SPEC-QMS-010 — Complaint Management | 21 CFR Part 4, 21 CFR Part 806, ISO 13485, §211.198 | Retention (Doc 108) |
| 36 | SPEC-QMS-011 — Recall / Field Action Management | 21 CFR Part 4, 21 CFR Part 806, ISO 13485, §211.198 | Part 11 signature (Doc 04 / Doc 106); Record Version Vault (Doc 06) |
| 37 | SPEC-QMS-012 — Quality Metrics, Trending & Effectiveness Checks | 21 CFR Part 4, 21 CFR Part 806, ISO 13485, §211.198 | Audit ledger (Doc 05); Record Version Vault (Doc 06) |
| 38 | SPEC-EQP-001 — Equipment, Calibration, Qualification & Maintenance | ISO 13485, §211.113, §211.182, §211.42, §211.67, §211.68 | Audit ledger (Doc 05); Policy/SoD (Doc 07 / Doc 107) |
| 39 | SPEC-EQP-002 — Cleaning, Sanitization & Line Clearance | ISO 13485, §211.113, §211.182, §211.42, §211.67, §211.68 | Audit ledger (Doc 05) |
| 40 | SPEC-EQP-003 — Sterile / Aseptic Manufacturing Operations | ISO 13485, §211.113, §211.182, §211.42, §211.67, §211.68 | Audit ledger (Doc 05); Policy/SoD (Doc 07 / Doc 107) |
| 41 | SPEC-EQP-004 — Environmental Monitoring & Cleanroom State Control | ISO 13485, §211.113, §211.182, §211.42, §211.67, §211.68 | Retention (Doc 108) |
| 42 | SPEC-EQP-005 — Sterilization, CIP/SIP & Sterile Filtration Management | ISO 13485, §211.113, §211.182, §211.42, §211.67, §211.68 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05); Record Version Vault (Doc 06); Policy/SoD (Doc 07 / Doc 107) |
| 54 | SPEC-DDCP-001 — Prefilled Syringe & Injectable DDCP Manufacturing Profile | 21 CFR Part 4 | Part 11 signature (Doc 04 / Doc 106) |
| 55 | SPEC-DDCP-002 — Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile | 21 CFR Part 4 | Part 11 signature (Doc 04 / Doc 106) |
| 56 | SPEC-DDCP-003 — Inhalation DDCP Manufacturing Profile — MDI / DPI | 21 CFR Part 4 | Part 11 signature (Doc 04 / Doc 106) |
| 57 | SPEC-DDCP-004 — Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile | 21 CFR Part 4 | Part 11 signature (Doc 04 / Doc 106) |
| 59 | SPEC-PM-002 — Regulatory Reportability Assessment & Electronic Safety Submission Management | 21 CFR Part 803, §314.80, §4.102, §600.80 | Audit ledger (Doc 05); Record Version Vault (Doc 06) |
| 60 | SPEC-PM-003 — Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar | §314.81, §4.103, §4.105, §806.10, §806.20 | Audit ledger (Doc 05); Record Version Vault (Doc 06); Policy/SoD (Doc 07 / Doc 107); Retention (Doc 108) |
| 79 | SPEC-VAL-001 — Validation Master Plan & Computer Software Assurance Strategy | ISO 13485, §11.10, §211.68 | Part 11 signature (Doc 04 / Doc 106); Record Version Vault (Doc 06); Policy/SoD (Doc 07 / Doc 107); Retention (Doc 108) |
| 80 | SPEC-VAL-002 — Intended Use, GxP Criticality & Software Function Risk Classification | ISO 13485, §11.10, §211.68 | Part 11 signature (Doc 04 / Doc 106); Record Version Vault (Doc 06); Policy/SoD (Doc 07 / Doc 107) |
| 81 | SPEC-VAL-003 — Requirements, Design Inputs & Validation Traceability Management | ISO 13485, §11.10, §211.68 | Part 11 signature (Doc 04 / Doc 106) |
| 82 | SPEC-VAL-004 — Validation Test Strategy, Test Methods & Objective Evidence Governance | ISO 13485, §11.10, §211.68 | Part 11 signature (Doc 04 / Doc 106); Record Version Vault (Doc 06); Retention (Doc 108) |
| 83 | SPEC-VAL-005 — Installation Qualification (IQ) & Installed Baseline Verification | ISO 13485, §11.10, §211.68 | Domain controls in the owning module |
| 84 | SPEC-VAL-006 — Operational Qualification (OQ) & Functional Control Verification | ISO 13485, §11.10, §211.68 | Policy/SoD (Doc 07 / Doc 107) |
| 85 | SPEC-VAL-007 — Performance Qualification (PQ), UAT & Business Process Verification | ISO 13485, §11.10, §211.68 | Part 11 signature (Doc 04 / Doc 106); Policy/SoD (Doc 07 / Doc 107) |
| 86 | SPEC-VAL-008 — Infrastructure, Cloud, Platform & Environment Qualification | ISO 13485, §11.10, §211.68 | Policy/SoD (Doc 07 / Doc 107) |
| 87 | SPEC-VAL-009 — Data Migration, Conversion, Cutover & Reconciliation Validation | ISO 13485, §11.10, §211.68 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05); Retention (Doc 108) |
| 88 | SPEC-VAL-010 — 21 CFR Part 11 Electronic Records & Electronic Signature Validation | 21 CFR Part 11, ISO 13485, §11.10, §11.100, §211.68 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05); Record Version Vault (Doc 06); Retention (Doc 108) |
| 89 | SPEC-VAL-011 — Audit Trail, Record Version Vault & Data Integrity Validation | ISO 13485, §11.10, §211.68 | Audit ledger (Doc 05); Record Version Vault (Doc 06); Retention (Doc 108) |
| 90 | SPEC-VAL-012 — Integration, Edge, Device, Peripheral & Interface Validation | ISO 13485, §11.10, §211.68 | Record Version Vault (Doc 06) |
| 91 | SPEC-VAL-013 — Backup, Restore, PITR & Disaster Recovery Qualification | ISO 13485, §11.10, §211.68 | Audit ledger (Doc 05) |
| 92 | SPEC-VAL-014 — Security Qualification, Vulnerability Verification & Penetration Testing | ISO 13485, §11.10, §211.68 | Part 11 signature (Doc 04 / Doc 106); Policy/SoD (Doc 07 / Doc 107) |
| 93 | SPEC-VAL-015 — Performance, Load, Capacity & Reliability Qualification | ISO 13485, §11.10, §211.68 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05) |
| 94 | SPEC-VAL-016 — Validation Defect, Deviation, Test Exception & Remediation Management | ISO 13485, §11.10, §211.68 | Part 11 signature (Doc 04 / Doc 106); Audit ledger (Doc 05) |
| 95 | SPEC-VAL-017 — Validation Summary Report, Release-to-Production & Go-Live Authorization | ISO 13485, §11.10, §211.68 | Part 11 signature (Doc 04 / Doc 106) |
| 96 | SPEC-VAL-018 — Periodic Review, Change Impact, Revalidation & Validated-State Maintenance | ISO 13485, §11.10, §211.68 | Part 11 signature (Doc 04 / Doc 106); Record Version Vault (Doc 06) |
| 101 | SPEC-ENG-005 — API & Event Contract Standard | ISO 8601 | Domain controls in the owning module |

## Platform-wide obligations

- 21 CFR Part 11 — electronic records and signatures: Docs 04, 05, 06, 88, 106.
- 21 CFR Part 211 — drug CGMP records, yields, batch review: Docs 10–17, 21–25, 108.
- 21 CFR Part 820 / QMSR — device QMS and DHR: Docs 12, 26–37, 108.
- 21 CFR Part 4 — combination-product CGMP and postmarket: Docs 09, 54–60.
- 21 CFR Parts 803 / 806 / 830 — MDR, corrections/removals, UDI: Docs 58, 59, 60.
- ISO 13485 / ISO 14971 — QMS and risk management: Docs 26–37, 33, 80.
- GAMP 5 / CSA — validation approach: Docs 79–96, 111.
