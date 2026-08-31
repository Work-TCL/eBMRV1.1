# eBMR / eDHR — Master Document Index & How-to-Use Guide

**Baseline date:** 2026-08-20  
**Document set:** Documents 01–105  
**Purpose:** Single entry point for humans, Claude Code, Codex and project/validation teams.

---

# 1. What This File Is

This is the **main file to open first** before using the 105-document specification set. It explains:

- what each document group contains;
- which documents define system-wide non-negotiables;
- how documents connect to one another;
- what order Claude Code/Codex should ingest them;
- what must be generated before broad production coding starts;
- which documents are used during implementation, validation, deployment and later change control.

The 105 documents together are the **implementation baseline**. No single document should be treated as a complete specification of the platform by itself.

# 2. The Five Files to Read First

Use this sequence before any implementation work:

1. **This Master Index & Usage Guide** — understand the whole system and ingestion sequence.
2. **Document 01** — product/compliance/architecture source of truth.
3. **Document 02** — system architecture and GxP Core technical boundaries.
4. **Specification Authoring Standard** — defines the implementation depth expected from all module specifications.
5. **Claude Code / Codex Master Project Construction Instructions v1.7** — tells the coding agent how to transform Documents 01–105 into a complete project blueprint before broad coding.

# 3. Core Architectural Rules That Override Local Convenience

Claude Code/Codex must preserve these rules across every module:

- Frappe is the UI/configuration/application framework; do **not** modify or fork Frappe/ERPNext core.
- Proprietary GxP Core is the primary regulated IP.
- PostgreSQL is authoritative for proprietary regulated GxP state.
- Frappe/MariaDB contains framework, UI/configuration and approved projection/non-authoritative state.
- A regulated entity must have exactly one authoritative owner/store.
- Regulated writes go through the Mutation Gateway/domain service path.
- Electronic signatures are separate from normal login/MFA and follow Part 11 signature controls.
- Audit/record-version/evidence history is immutable/superseding, not editable in place.
- NATS/JetStream is transport; PostgreSQL transactional outbox is the authoritative event source.
- Temporal coordinates long-running workflows but never becomes regulatory truth.
- Redis/search/read models are rebuildable and cannot be the sole regulated source.
- External ERP/LIMS/Edge systems follow explicit ownership/integration contracts.
- AI is advisory by default and cannot autonomously sign, release, disposition, alter audit history or make final regulated decisions.
- If regulated behavior is missing or ambiguous, create a `SPEC_GAP` and do not guess.

# 4. Document Groups and When to Use Them

## A. Foundation & Architecture — Documents 01–02

Master product/compliance/architecture baseline and technical architecture. Read first; these define the system-wide rules every later document must respect.

## B. Proprietary GxP Core — Documents 03–08

Mutation Gateway, Part 11 signatures, immutable audit, version Vault, identity/RBAC/qualification/SoD, and regulatory rules/calculation engine.

## C. eBMR / eDHR Manufacturing Core — Documents 09–17

Product/constituent master, recipes, batch execution, eDHR, genealogy, review-by-exception, release/disposition, packaging/labeling, yield/reconciliation.

## D. Procurement & Materials — Documents 18–22

Supplier quality/procurement, receipt/quarantine/status, inventory, dispensing/weighing, consumption/return/destruction/reconciliation.

## E. QC / Laboratory — Documents 23–25

Native QC/sampling, generic LIMS integration, OOS/OOT management.

## F. Quality Management System — Documents 26–37

Deviation, CAPA, nonconformance, change/document/training/supplier quality/risk/audit/complaint/recall/metrics and related QMS controls.

## G. Equipment / Sterile / Manufacturing Readiness — Documents 38–42

Equipment, calibration/maintenance/cleaning and sterile/aseptic/manufacturing readiness controls.

## H. Edge / OT Integration — Documents 43–47

Industrial Edge gateway, device/protocol connectivity, store-and-forward, machine/peripheral integration and edge security/reliability.

## I. Enterprise Integration — Documents 48–53

ERP, LIMS and enterprise system integration contracts, mappings, retries, reconciliation and external-system ownership boundaries.

## J. DDCP Product Profiles — Documents 54–57

Drug-device combination product-specific execution profiles and constituent rules.

## K. Postmarket / Regulatory Operations — Documents 58–60

Complaint/postmarket/regulatory/field-action data and workflow interfaces.

## L. Security Architecture & Cybersecurity — Documents 61–68

Security architecture, identity federation, privileged access, secure application/API/runtime, secrets/PKI, network isolation, monitoring/IR and secure SDLC/supply chain.

## M. Data Architecture & Infrastructure — Documents 69–78

Authoritative data ownership, PostgreSQL, Frappe/MariaDB, evidence storage/WORM, NATS/outbox, Temporal, cache/search/read models, DR, deployment and SRE/capacity.

## N. Validation / CSA / Qualification — Documents 79–96

Validation master plan, intended use/risk, traceability, test strategy, IQ/OQ/PQ, infrastructure/migration/Part11/data-integrity/integration/DR/security/performance qualification, validation exceptions, VSR and ongoing validated state.

## O. Engineering / Development / AI Governance — Documents 97–105

Coding standards, Claude Code/Codex architecture rules, repository/branching, DB migration, API/event contracts, testing, CI/CD, SBOM/license and AI governance.

# 5. Full Document Index

| Doc | Specification ID | Title | Group | File |
|---:|---|---|---|---|
| 001 | — | Master Product, Compliance & Architecture Bible | A. Foundation & Architecture | `Document_01_US_eBMR_eDHR_Master_Product_Compliance_Architecture_Bible_v1.1_FROZEN.md` |
| 002 | — | System Architecture & GxP Core Technical Specification | A. Foundation & Architecture | `Document_02_System_Architecture_GxP_Core_Technical_Specification_v1.0.md` |
| 003 | SPEC-GXP-001 | GxP Mutation Gateway — Detailed Functional & Technical Specification | B. Proprietary GxP Core | `Document_03_GxP_Mutation_Gateway_Specification_v1.1_IMPLEMENTATION_READY.md` |
| 004 | SPEC-GXP-002 | 21 CFR Part 11 Electronic Signature — Detailed Functional & Technical Specification | B. Proprietary GxP Core | `Document_04_Part_11_Electronic_Signature_Specification_v1.1_IMPLEMENTATION_READY.md` |
| 005 | SPEC-GXP-003 | Immutable Audit Ledger & Audit Review — Detailed Functional & Technical Specification | B. Proprietary GxP Core | `Document_05_Immutable_Audit_Ledger_and_Audit_Review_Specification_v1.1_IMPLEMENTATION_READY.md` |
| 006 | SPEC-GXP-004 | Record Version Vault, Locking, Amendment & Controlled Correction — Specification | B. Proprietary GxP Core | `Document_06_Record_Version_Vault_Locking_Amendment_Correction_Specification_v1.1_IMPLEMENTATION_READY.md` |
| 007 | SPEC-IAM-001 | Identity, Authorization, RBAC, Qualification & Segregation-of-Duties — Specification | B. Proprietary GxP Core | `Document_07_Identity_Authorization_RBAC_Qualification_SoD_Specification_v1.1_IMPLEMENTATION_READY.md` |
| 008 | SPEC-GXP-006 | Regulatory Rules & Calculation Engine — Detailed Functional & Technical Specification | B. Proprietary GxP Core | `Document_08_Regulatory_Rules_and_Calculation_Engine_Specification_v1.1_IMPLEMENTATION_READY.md` |
| 009 | SPEC-EBMR-000 | Product, Constituent & Regulatory Profile Master | C. eBMR / eDHR Manufacturing Core | `Document_09_Product_Constituent_Regulatory_Profile_Master_v1.0_IMPLEMENTATION_READY.md` |
| 010 | SPEC-EBMR-001 | Master Recipe / Master Manufacturing Record Specification | C. eBMR / eDHR Manufacturing Core | `Document_10_Master_Recipe_Master_Manufacturing_Record_v1.0_IMPLEMENTATION_READY.md` |
| 011 | SPEC-EBMR-002 | Batch Execution Engine & State Machine Specification | C. eBMR / eDHR Manufacturing Core | `Document_11_Batch_Execution_Engine_State_Machine_v1.0_IMPLEMENTATION_READY.md` |
| 012 | SPEC-EBMR-003 | eDHR / Device Production History Specification | C. eBMR / eDHR Manufacturing Core | `Document_12_eDHR_Device_Production_History_v1.0_IMPLEMENTATION_READY.md` |
| 013 | SPEC-EBMR-004 | Genealogy & Traceability Engine Specification | C. eBMR / eDHR Manufacturing Core | `Document_13_Genealogy_Traceability_Engine_v1.0_IMPLEMENTATION_READY.md` |
| 014 | SPEC-EBMR-005 | Review-by-Exception & QA Review Specification | C. eBMR / eDHR Manufacturing Core | `Document_14_Review_by_Exception_QA_Review_v1.0_IMPLEMENTATION_READY.md` |
| 015 | SPEC-EBMR-006 | Release / Disposition Engine Specification | C. eBMR / eDHR Manufacturing Core | `Document_15_Release_Disposition_Engine_v1.0_IMPLEMENTATION_READY.md` |
| 016 | SPEC-EBMR-007 | Packaging, Labeling & Reconciliation Specification | C. eBMR / eDHR Manufacturing Core | `Document_16_Packaging_Labeling_Reconciliation_v1.0_IMPLEMENTATION_READY.md` |
| 017 | SPEC-EBMR-008 | Yield, Calculations & Manufacturing Reconciliation Specification | C. eBMR / eDHR Manufacturing Core | `Document_17_Yield_Calculations_Manufacturing_Reconciliation_v1.0_IMPLEMENTATION_READY.md` |
| 018 | SPEC-MAT-001 | Procurement & Supplier Quality Specification | D. Procurement & Materials | `Document_18_Procurement_Supplier_Quality_v1.0_IMPLEMENTATION_READY.md` |
| 019 | SPEC-MAT-002A | Material Receipt, Quarantine & Quality Status Specification | D. Procurement & Materials | `Document_19_Material_Receipt_Quarantine_Quality_Status_v1.0_IMPLEMENTATION_READY.md` |
| 020 | SPEC-MAT-002B | Inventory, Lot/Container & Warehouse Specification | D. Procurement & Materials | `Document_20_Inventory_Lot_Container_Warehouse_v1.0_IMPLEMENTATION_READY.md` |
| 021 | SPEC-MAT-002C | Material Dispensing & Weighing Specification | D. Procurement & Materials | `Document_21_Material_Dispensing_Weighing_v1.0_IMPLEMENTATION_READY.md` |
| 022 | SPEC-MAT-002D | Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification | D. Procurement & Materials | `Document_22_Material_Consumption_Return_Adjustment_Destruction_Reconciliation_v1.0_IMPLEMENTATION_READY.md` |
| 023 | SPEC-QC-001 | Native Basic QC & Sampling Specification | E. QC / Laboratory | `Document_23_Native_Basic_QC_Sampling_v1.0_IMPLEMENTATION_READY.md` |
| 024 | SPEC-QC-002 | LIMS Integration Architecture & Generic Adapter Contract | E. QC / Laboratory | `Document_24_LIMS_Integration_Generic_Adapter_v1.0_IMPLEMENTATION_READY.md` |
| 025 | SPEC-QC-003 | OOS / OOT Management Specification | E. QC / Laboratory | `Document_25_OOS_OOT_Management_v1.0_IMPLEMENTATION_READY.md` |
| 026 | SPEC-QMS-001 | Deviation & Investigation Management | F. Quality Management System | `Document_26_Deviation_Investigation_Management_v1.0_IMPLEMENTATION_READY.md` |
| 027 | SPEC-QMS-002 | CAPA Management | F. Quality Management System | `Document_27_CAPA_Management_v1.0_IMPLEMENTATION_READY.md` |
| 028 | SPEC-QMS-003 | Nonconformance Management | F. Quality Management System | `Document_28_Nonconformance_Management_v1.0_IMPLEMENTATION_READY.md` |
| 029 | SPEC-QMS-004 | Change Control | F. Quality Management System | `Document_29_Change_Control_v1.0_IMPLEMENTATION_READY.md` |
| 030 | SPEC-QMS-005 | Document Control | F. Quality Management System | `Document_30_Document_Control_v1.0_IMPLEMENTATION_READY.md` |
| 031 | SPEC-QMS-006 | Training & Personnel Qualification | F. Quality Management System | `Document_31_Training_Personnel_Qualification_v1.0_IMPLEMENTATION_READY.md` |
| 032 | SPEC-QMS-007 | Supplier Quality / SCAR | F. Quality Management System | `Document_32_Supplier_Quality_SCAR_v1.0_IMPLEMENTATION_READY.md` |
| 033 | SPEC-QMS-008 | Risk Management | F. Quality Management System | `Document_33_Risk_Management_v1.0_IMPLEMENTATION_READY.md` |
| 034 | SPEC-QMS-009 | Internal Audit Management | F. Quality Management System | `Document_34_Internal_Audit_Management_v1.0_IMPLEMENTATION_READY.md` |
| 035 | SPEC-QMS-010 | Complaint Management | F. Quality Management System | `Document_35_Complaint_Management_v1.0_IMPLEMENTATION_READY.md` |
| 036 | SPEC-QMS-011 | Recall / Field Action Management | F. Quality Management System | `Document_36_Recall_Field_Action_Management_v1.0_IMPLEMENTATION_READY.md` |
| 037 | SPEC-QMS-012 | Quality Metrics, Trending & Effectiveness Checks | F. Quality Management System | `Document_37_Quality_Metrics_Trending_Effectiveness_v1.0_IMPLEMENTATION_READY.md` |
| 038 | SPEC-EQP-001 | Equipment, Calibration, Qualification & Maintenance | G. Equipment / Sterile / Manufacturing Readiness | `Document_38_Equipment_Calibration_Qualification_Maintenance_v1.0_IMPLEMENTATION_READY.md` |
| 039 | SPEC-EQP-002 | Cleaning, Sanitization & Line Clearance | G. Equipment / Sterile / Manufacturing Readiness | `Document_39_Cleaning_Sanitization_Line_Clearance_v1.0_IMPLEMENTATION_READY.md` |
| 040 | SPEC-EQP-003 | Sterile / Aseptic Manufacturing Operations | G. Equipment / Sterile / Manufacturing Readiness | `Document_40_Sterile_Aseptic_Manufacturing_Operations_v1.0_IMPLEMENTATION_READY.md` |
| 041 | SPEC-EQP-004 | Environmental Monitoring & Cleanroom State Control | G. Equipment / Sterile / Manufacturing Readiness | `Document_41_Environmental_Monitoring_Cleanroom_State_Control_v1.0_IMPLEMENTATION_READY.md` |
| 042 | SPEC-EQP-005 | Sterilization, CIP/SIP & Sterile Filtration Management | G. Equipment / Sterile / Manufacturing Readiness | `Document_42_Sterilization_CIP_SIP_Sterile_Filtration_v1.0_IMPLEMENTATION_READY.md` |
| 043 | SPEC-EDGE-001 | Edge Gateway Runtime Architecture & Construction Specification | H. Edge / OT Integration | `Document_43_Edge_Gateway_Runtime_Architecture_v1.0_IMPLEMENTATION_READY.md` |
| 044 | SPEC-EDGE-002 | Industrial Device & Protocol Connectivity / Driver Specification | H. Edge / OT Integration | `Document_44_Industrial_Device_Protocol_Connectivity_Drivers_v1.0_IMPLEMENTATION_READY.md` |
| 045 | SPEC-EDGE-003 | Store-and-Forward, Offline Buffering, Time Integrity & Data Quality | H. Edge / OT Integration | `Document_45_Store_Forward_Offline_Buffering_Time_Data_Quality_v1.0_IMPLEMENTATION_READY.md` |
| 046 | SPEC-EDGE-004 | Barcode, Scanner, Balance, Printer, Tester & Peripheral Integration | H. Edge / OT Integration | `Document_46_Barcode_Scanner_Balance_Printer_Tester_Peripheral_Integration_v1.0_IMPLEMENTATION_READY.md` |
| 047 | SPEC-EDGE-005 | Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary | H. Edge / OT Integration | `Document_47_PLC_SCADA_Data_Acquisition_Evidence_Mapping_Command_Boundary_v1.0_IMPLEMENTATION_READY.md` |
| 048 | SPEC-ERP-001 | Enterprise ERP Integration Architecture & Provider Contract | I. Enterprise Integration | `Document_48_Enterprise_ERP_Integration_Architecture_Provider_Contract_v1.0_IMPLEMENTATION_READY.md` |
| 049 | SPEC-ERP-002 | ERPNext Adapter Detailed Contract | I. Enterprise Integration | `Document_49_ERPNext_Adapter_Detailed_Contract_v1.0_IMPLEMENTATION_READY.md` |
| 050 | SPEC-ERP-003 | SAP S/4HANA Adapter Contract | I. Enterprise Integration | `Document_50_SAP_S4HANA_Adapter_Contract_v1.0_IMPLEMENTATION_READY.md` |
| 051 | SPEC-ERP-004 | Oracle Fusion, Dynamics 365 & Custom ERP Adapter Contracts | I. Enterprise Integration | `Document_51_Oracle_Dynamics_Custom_ERP_Adapter_Contracts_v1.0_IMPLEMENTATION_READY.md` |
| 052 | SPEC-ERP-005 | Master Data Synchronization, Mapping & Reconciliation | I. Enterprise Integration | `Document_52_Master_Data_Synchronization_Mapping_Reconciliation_v1.0_IMPLEMENTATION_READY.md` |
| 053 | SPEC-ERP-006 | Integration Error Handling, Retry, Idempotency & Reconciliation | I. Enterprise Integration | `Document_53_Integration_Error_Retry_Idempotency_Reconciliation_v1.0_IMPLEMENTATION_READY.md` |
| 054 | SPEC-DDCP-001 | Prefilled Syringe & Injectable DDCP Manufacturing Profile | J. DDCP Product Profiles | `Document_54_Prefilled_Syringe_Injectable_DDCP_Profile_v1.0_IMPLEMENTATION_READY.md` |
| 055 | SPEC-DDCP-002 | Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile | J. DDCP Product Profiles | `Document_55_Autoinjector_Pen_Cartridge_DDCP_Profile_v1.0_IMPLEMENTATION_READY.md` |
| 056 | SPEC-DDCP-003 | Inhalation DDCP Manufacturing Profile — MDI / DPI | J. DDCP Product Profiles | `Document_56_Inhalation_MDI_DPI_DDCP_Profile_v1.0_IMPLEMENTATION_READY.md` |
| 057 | SPEC-DDCP-004 | Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile | J. DDCP Product Profiles | `Document_57_Drug_Eluting_Coated_Device_DDCP_Profile_v1.0_IMPLEMENTATION_READY.md` |
| 058 | SPEC-PM-001 | Postmarket Surveillance, Safety Case & Signal Management | K. Postmarket / Regulatory Operations | `Document_58_Postmarket_Surveillance_Safety_Case_Signal_Management_v1.0_IMPLEMENTATION_READY.md` |
| 059 | SPEC-PM-002 | Regulatory Reportability Assessment & Electronic Safety Submission Management | K. Postmarket / Regulatory Operations | `Document_59_Regulatory_Reportability_Electronic_Safety_Submission_v1.0_IMPLEMENTATION_READY.md` |
| 060 | SPEC-PM-003 | Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar | K. Postmarket / Regulatory Operations | `Document_60_Combination_Product_Postmarket_Regulatory_Coordination_v1.0_IMPLEMENTATION_READY.md` |
| 061 | SPEC-SEC-001 | Security Architecture, Threat Model & Control Framework | L. Security Architecture & Cybersecurity | `Document_61_Security_Architecture_Threat_Model_Control_Framework_v1.0_IMPLEMENTATION_READY.md` |
| 062 | SPEC-SEC-002 | Identity Federation, SSO, MFA, Sessions & Service Identities | L. Security Architecture & Cybersecurity | `Document_62_Identity_Federation_SSO_MFA_Sessions_Service_Identities_v1.0_IMPLEMENTATION_READY.md` |
| 063 | SPEC-SEC-003 | Privileged Access, Support Access, Break-Glass & Administrative Security | L. Security Architecture & Cybersecurity | `Document_63_Privileged_Support_BreakGlass_Admin_Security_v1.0_IMPLEMENTATION_READY.md` |
| 064 | SPEC-SEC-004 | Application, API, UI & Secure Runtime Engineering | L. Security Architecture & Cybersecurity | `Document_64_Application_API_UI_Secure_Runtime_Engineering_v1.0_IMPLEMENTATION_READY.md` |
| 065 | SPEC-SEC-005 | Secrets Management, PKI, Cryptography & Key Lifecycle | L. Security Architecture & Cybersecurity | `Document_65_Secrets_PKI_Cryptography_Key_Lifecycle_v1.0_IMPLEMENTATION_READY.md` |
| 066 | SPEC-SEC-006 | Network, Tenant, Deployment Isolation & Zero-Trust Architecture | L. Security Architecture & Cybersecurity | `Document_66_Network_Tenant_Deployment_Isolation_Zero_Trust_v1.0_IMPLEMENTATION_READY.md` |
| 067 | SPEC-SEC-007 | Security Logging, Monitoring, Incident Response & Forensic Evidence | L. Security Architecture & Cybersecurity | `Document_67_Security_Logging_Monitoring_Incident_Response_Forensics_v1.0_IMPLEMENTATION_READY.md` |
| 068 | SPEC-SEC-008 | Secure SDLC, Software Supply Chain, SBOM, Vulnerability & Release Security | L. Security Architecture & Cybersecurity | `Document_68_Secure_SDLC_Software_Supply_Chain_SBOM_Vulnerability_Release_v1.0_IMPLEMENTATION_READY.md` |
| 069 | SPEC-DATA-001 | Enterprise Data Ownership, Persistence Topology & Data Lineage | M. Data Architecture & Infrastructure | `Document_69_Data_Ownership_Persistence_Topology_Lineage_v1.0_IMPLEMENTATION_READY.md` |
| 070 | SPEC-DATA-002 | PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency | M. Data Architecture & Infrastructure | `Document_70_PostgreSQL_GxP_Database_Schema_Partitioning_Concurrency_v1.0_IMPLEMENTATION_READY.md` |
| 071 | SPEC-DATA-003 | Frappe / MariaDB Operational Database, Projection & UI Data Architecture | M. Data Architecture & Infrastructure | `Document_71_Frappe_MariaDB_Operational_Projection_UI_Data_Architecture_v1.0_IMPLEMENTATION_READY.md` |
| 072 | SPEC-DATA-004 | Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle | M. Data Architecture & Infrastructure | `Document_72_Immutable_Evidence_Object_Storage_WORM_Archive_File_Lifecycle_v1.0_IMPLEMENTATION_READY.md` |
| 073 | SPEC-DATA-005 | NATS / JetStream Event Bus, Transactional Outbox & Async Contracts | M. Data Architecture & Infrastructure | `Document_73_NATS_JetStream_Transactional_Outbox_Async_Contracts_v1.0_IMPLEMENTATION_READY.md` |
| 074 | SPEC-DATA-006 | Temporal Durable Workflow Orchestration Architecture | M. Data Architecture & Infrastructure | `Document_74_Temporal_Durable_Workflow_Orchestration_Architecture_v1.0_IMPLEMENTATION_READY.md` |
| 075 | SPEC-DATA-007 | Caching, Search, Read Models, Reporting Projections & Analytics Data Access | M. Data Architecture & Infrastructure | `Document_75_Caching_Search_Read_Models_Reporting_Analytics_v1.0_IMPLEMENTATION_READY.md` |
| 076 | SPEC-DATA-008 | Backup, Restore, Point-in-Time Recovery & Disaster Recovery | M. Data Architecture & Infrastructure | `Document_76_Backup_Restore_PITR_Disaster_Recovery_v1.0_IMPLEMENTATION_READY.md` |
| 077 | SPEC-DATA-009 | Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture | M. Data Architecture & Infrastructure | `Document_77_Cloud_Neutral_Kubernetes_OnPrem_Deployment_Upgrade_v1.0_IMPLEMENTATION_READY.md` |
| 078 | SPEC-DATA-010 | Performance, Capacity, Observability, SLOs & SRE Operations | M. Data Architecture & Infrastructure | `Document_78_Performance_Capacity_Observability_SLO_SRE_v1.0_IMPLEMENTATION_READY.md` |
| 079 | SPEC-VAL-001 | Validation Master Plan & Computer Software Assurance Strategy | N. Validation / CSA / Qualification | `Document_79_Validation_Master_Plan_CSA_Strategy_v1.0_IMPLEMENTATION_READY.md` |
| 080 | SPEC-VAL-002 | Intended Use, GxP Criticality & Software Function Risk Classification | N. Validation / CSA / Qualification | `Document_80_Intended_Use_GxP_Criticality_Function_Risk_Classification_v1.0_IMPLEMENTATION_READY.md` |
| 081 | SPEC-VAL-003 | Requirements, Design Inputs & Validation Traceability Management | N. Validation / CSA / Qualification | `Document_81_Requirements_Design_Inputs_Validation_Traceability_v1.0_IMPLEMENTATION_READY.md` |
| 082 | SPEC-VAL-004 | Validation Test Strategy, Test Methods & Objective Evidence Governance | N. Validation / CSA / Qualification | `Document_82_Validation_Test_Strategy_Methods_Objective_Evidence_v1.0_IMPLEMENTATION_READY.md` |
| 083 | SPEC-VAL-005 | Installation Qualification (IQ) & Installed Baseline Verification | N. Validation / CSA / Qualification | `Document_83_Installation_Qualification_IQ_v1.0_IMPLEMENTATION_READY.md` |
| 084 | SPEC-VAL-006 | Operational Qualification (OQ) & Functional Control Verification | N. Validation / CSA / Qualification | `Document_84_Operational_Qualification_OQ_Functional_Verification_v1.0_IMPLEMENTATION_READY.md` |
| 085 | SPEC-VAL-007 | Performance Qualification (PQ), UAT & Business Process Verification | N. Validation / CSA / Qualification | `Document_85_Performance_Qualification_PQ_UAT_Business_Process_v1.0_IMPLEMENTATION_READY.md` |
| 086 | SPEC-VAL-008 | Infrastructure, Cloud, Platform & Environment Qualification | N. Validation / CSA / Qualification | `Document_86_Infrastructure_Cloud_Platform_Environment_Qualification_v1.0_IMPLEMENTATION_READY.md` |
| 087 | SPEC-VAL-009 | Data Migration, Conversion, Cutover & Reconciliation Validation | N. Validation / CSA / Qualification | `Document_87_Data_Migration_Conversion_Cutover_Reconciliation_Validation_v1.0_IMPLEMENTATION_READY.md` |
| 088 | SPEC-VAL-010 | 21 CFR Part 11 Electronic Records & Electronic Signature Validation | N. Validation / CSA / Qualification | `Document_88_21CFR_Part11_Electronic_Records_Signature_Validation_v1.0_IMPLEMENTATION_READY.md` |
| 089 | SPEC-VAL-011 | Audit Trail, Record Version Vault & Data Integrity Validation | N. Validation / CSA / Qualification | `Document_89_Audit_Vault_Data_Integrity_Validation_v1.0_IMPLEMENTATION_READY.md` |
| 090 | SPEC-VAL-012 | Integration, Edge, Device, Peripheral & Interface Validation | N. Validation / CSA / Qualification | `Document_90_Integration_Edge_Device_Interface_Validation_v1.0_IMPLEMENTATION_READY.md` |
| 091 | SPEC-VAL-013 | Backup, Restore, PITR & Disaster Recovery Qualification | N. Validation / CSA / Qualification | `Document_91_Backup_Restore_PITR_DR_Qualification_v1.0_IMPLEMENTATION_READY.md` |
| 092 | SPEC-VAL-014 | Security Qualification, Vulnerability Verification & Penetration Testing | N. Validation / CSA / Qualification | `Document_92_Security_Qualification_Vulnerability_Penetration_Testing_v1.0_IMPLEMENTATION_READY.md` |
| 093 | SPEC-VAL-015 | Performance, Load, Capacity & Reliability Qualification | N. Validation / CSA / Qualification | `Document_93_Performance_Load_Capacity_Reliability_Qualification_v1.0_IMPLEMENTATION_READY.md` |
| 094 | SPEC-VAL-016 | Validation Defect, Deviation, Test Exception & Remediation Management | N. Validation / CSA / Qualification | `Document_94_Validation_Defect_Deviation_Exception_Remediation_v1.0_IMPLEMENTATION_READY.md` |
| 095 | SPEC-VAL-017 | Validation Summary Report, Release-to-Production & Go-Live Authorization | N. Validation / CSA / Qualification | `Document_95_Validation_Summary_Release_GoLive_Authorization_v1.0_IMPLEMENTATION_READY.md` |
| 096 | SPEC-VAL-018 | Periodic Review, Change Impact, Revalidation & Validated-State Maintenance | N. Validation / CSA / Qualification | `Document_96_Periodic_Review_Change_Impact_Revalidation_Validated_State_v1.0_IMPLEMENTATION_READY.md` |
| 097 | SPEC-ENG-001 | Coding Standards | O. Engineering / Development / AI Governance | `Document_97_Coding_Standards_v1.0_IMPLEMENTATION_READY.md` |
| 098 | SPEC-ENG-002 | Architecture Rules for Claude Code / Codex | O. Engineering / Development / AI Governance | `Document_98_Architecture_Rules_ClaudeCode_Codex_v1.0_IMPLEMENTATION_READY.md` |
| 099 | SPEC-ENG-003 | Repository & Branching Standard | O. Engineering / Development / AI Governance | `Document_99_Repository_Branching_Standard_v1.0_IMPLEMENTATION_READY.md` |
| 100 | SPEC-ENG-004 | Database Migration Standard | O. Engineering / Development / AI Governance | `Document_100_Database_Migration_Standard_v1.0_IMPLEMENTATION_READY.md` |
| 101 | SPEC-ENG-005 | API & Event Contract Standard | O. Engineering / Development / AI Governance | `Document_101_API_Event_Contract_Standard_v1.0_IMPLEMENTATION_READY.md` |
| 102 | SPEC-ENG-006 | Testing Strategy | O. Engineering / Development / AI Governance | `Document_102_Testing_Strategy_v1.0_IMPLEMENTATION_READY.md` |
| 103 | SPEC-ENG-007 | CI/CD & Release Process | O. Engineering / Development / AI Governance | `Document_103_CI_CD_Release_Process_v1.0_IMPLEMENTATION_READY.md` |
| 104 | SPEC-ENG-008 | SBOM / Third-Party License Management | O. Engineering / Development / AI Governance | `Document_104_SBOM_Third_Party_License_Management_v1.0_IMPLEMENTATION_READY.md` |
| 105 | SPEC-AI-001 | AI Governance for Regulated Manufacturing | O. Engineering / Development / AI Governance | `Document_105_AI_Governance_Regulated_Manufacturing_v1.0_IMPLEMENTATION_READY.md` |

# 6. Recommended Claude Code / Codex Ingestion Order

For the first construction pass, ingest files in this order:

```text
STEP 1  → This Master Index & How-to-Use Guide
STEP 2  → Document 01
STEP 3  → Document 02
STEP 4  → Specification Authoring Standard
STEP 5  → Documents 03–08   (GxP Core)
STEP 6  → Documents 09–60   (Manufacturing/QMS/Edge/Integration/DDCP/Postmarket)
STEP 7  → Documents 61–78   (Security + Data/Infrastructure)
STEP 8  → Documents 79–96   (Validation/CSA/Qualification)
STEP 9  → Documents 97–105  (Engineering/Agent/Release/AI Governance)
STEP 10 → Claude Code Master Project Construction Instructions v1.7
```

The agent should **read everything before broad production coding**. It may create the Phase‑0 project blueprint while reading.

# 7. What Claude Code Must Produce Before Broad Coding

The v1.7 construction instruction requires **41 Phase‑0 generated artifacts**. The most important outputs are:

- complete project/module outline;
- module dependency map;
- full function/service catalogue with typed input/output;
- data model and database ownership matrix;
- API catalogue and event catalogue;
- state-machine catalogue;
- UI → action → API map;
- RBAC/SoD/qualification matrix;
- signature policy map;
- audit-event map;
- integration contract map;
- error-code registry;
- security controls/threat register;
- validation risk/traceability/test catalogue;
- database migration catalogue;
- engineering test matrix;
- CI/CD release evidence model;
- SBOM/license/dependency register;
- AI governance register;
- implementation work-package plan;
- `SPEC_GAP` register.

# 8. Function-Level Construction Rule

For every substantial domain/service function, Claude Code must extract or define all of the following from the specifications:

```text
Function name / ID
Purpose
Caller / Trigger
Inputs
  - name
  - type
  - requiredness
  - source
Preconditions / validations
Authorization / qualification / SoD
Electronic-signature requirement
Processing/business rules
Database reads
Database writes
Transaction boundary
Outputs / return type
Events emitted
Events consumed
External dependencies
Idempotency
Concurrency
Errors
Audit/security events
UI/caller integration
Configuration
Tests
Validation evidence
Source requirement IDs
```

A file that merely says “create batch service” or “build QC module” is not sufficient.

# 9. Development Gates

Use the following gates:

### Gate A — GxP Core
Documents **03–08** must be understood before regulated application modules.

### Gate B — Core eBMR
Documents **09–15** define the minimum serious eBMR execution/review/release backbone.

### Gate C — Complete DDCP V1 functional scope
Documents **16–60** complete packaging/yield/materials/QC/QMS/equipment/Edge/integrations/DDCP/postmarket.

### Gate D — Regulated pilot readiness
Documents **61–96** are required for security, infrastructure, validation/CSA, qualification and production readiness.

### Gate E — Engineering governance
Documents **97–105** must be enforced continuously during development, release and AI feature work.

# 10. Recommended Implementation Work Packages

```text
WP-00  Repository / toolchain / contract foundations
WP-01  GxP Core: Mutation / Signature / Audit / Vault / IAM / Rules
WP-02  Product / Recipe / Batch execution
WP-03  Genealogy / Review / Release / Packaging / Yield
WP-04  Procurement / Materials / QC
WP-05  QMS
WP-06  Equipment / Sterile / Edge
WP-07  Enterprise integrations
WP-08  DDCP profiles
WP-09  Postmarket
WP-10  Security
WP-11  Data / Infrastructure / DR / SRE
WP-12  Validation platform / evidence / qualification
WP-13  AI advisory capabilities
WP-14  Customer deployment / PQ / go-live
```

Do not build these as disconnected vertical silos. Every work package must use the common GxP, security, data, event and validation foundations.

# 11. How to Use the Documents During an Individual Coding Task

For each coding task:

1. Identify the primary module document.
2. Load all dependencies referenced in that document.
3. Load Documents 03–08 for GxP behavior if the task mutates regulated state.
4. Load Documents 61–78 for security/data/infrastructure impacts where relevant.
5. Load Documents 79–96 for validation/change impact.
6. Load Documents 97–104 for coding/repository/migration/contracts/tests/release/dependencies.
7. Load Document 105 if AI is involved.
8. Build the task plan before editing.
9. If a required regulated decision is missing, create a `SPEC_GAP`.
10. After code changes, update traceability/tests/contracts/migrations/validation impact before calling the task complete.

# 12. SPEC_GAP Rule

Claude Code/Codex may make normal software implementation choices, but must not guess anything that materially changes:

- regulated behavior;
- record authority;
- signature requirements;
- authorization/SoD/qualification;
- audit/retention/correction semantics;
- quality/release decisions;
- calculation precision or acceptance criteria;
- contract compatibility;
- migration/data-loss behavior;
- security trust boundaries;
- validation acceptance;
- AI decision authority.

For such a gap, write it into `18_SPEC_GAPS.md` and continue only with unaffected work.

# 13. How to Use the Set for Validation and Customer Deployment

The implementation specs are also the validation inputs.

```text
Specification requirements
      ↓
Intended use / GxP risk
      ↓
Design / functions / contracts
      ↓
Engineering tests
      ↓
IQ / OQ / PQ / Part 11 / Security / DR / Performance evidence
      ↓
Validation exceptions
      ↓
Validation Summary Report
      ↓
Validated Release Authorization
      ↓
Exact artifact + configuration promoted to production
```

Customer-specific workflows, roles, interfaces, product profiles, rules and procedures require customer/site validation impact and usually PQ/UAT evidence even when the common platform is already validated.

# 14. What Not to Do

- Do not give Claude Code only a random module document and ask it to invent missing architecture.
- Do not use Frappe DocTypes as an accidental second GxP source of truth.
- Do not make ERP/LIMS approval equal final product release.
- Do not let Temporal workflow state replace domain state.
- Do not let search/cache/analytics drive signature or release without authoritative re-read.
- Do not edit failed tests, OOS results, audit events or released record versions into a later “clean” state.
- Do not allow AI to self-approve code, validation evidence, signatures, QA decisions or releases.
- Do not perform production DB fixes that are not captured through a controlled migration/repair/change mechanism.

# 15. Recommended First Prompt to Claude Code

Use the following instruction after placing the full package in the repository:

```text
Read MASTER_00_eBMR_eDHR_Document_Index_and_Usage_Guide.md first.
Then ingest Documents 01–105, the Specification Authoring Standard, and
ClaudeCode_Master_Project_Construction_Instructions_v1.7_FINAL_Documents_01_105.md.

Do not start broad production coding.

First execute Phase 0 exactly as defined in the construction instructions.
Generate all required /docs/generated artifacts, especially the complete project outline,
function catalogue with typed inputs/outputs, module dependency map, data ownership matrix,
API/event catalogues, validation traceability, migration catalogue, test coverage matrix,
CI/CD evidence model, dependency/SBOM register and AI governance register.

For every missing regulated decision, create a SPEC_GAP and do not guess.

When Phase 0 is complete, generate PHASE_0_CONSTRUCTION_REVIEW.md and stop for review.
```

# 16. Package Verification

The package should contain exactly one preferred numbered Markdown document for each number **01 through 105**. Use the ingestion manifest/checksums if you need to verify that no file was omitted or altered.

# 17. Status

**Documents 01–105 are complete as a proposed implementation/construction baseline.**

Before calling the entire set frozen, perform a cross-document consistency review covering IDs, terminology, data ownership, state machines, API/event names, duplicated or conflicting rules, regulatory references, validation traceability and implementation depth.