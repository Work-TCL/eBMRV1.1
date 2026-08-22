# 00 — Project Outline

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Platform → work package → module → functionality → function decomposition compiled from Documents 01–105.

---

## Platform decomposition rule

```text
Platform
  → Work package
    → Module (one controlled specification document)
      → Functionality (requirement row)
        → Sub-functionality (requirement behaviour clause)
          → Service / function (03_FUNCTION_CATALOGUE.csv)
            → typed inputs → validations → authorization/signature → DB reads/writes
            → transaction boundary → outputs → events → errors → UI → tests → validation evidence
```

## Logical GxP Core component map (Document 02 §11 — mandatory logical boundaries)

- Mutation Gateway
- Identity Context Service
- Authorization / Policy Service
- Electronic Signature Service
- Audit Ledger Service
- Record Version Vault
- Recipe Release Service
- Batch / Execution Service
- Rules & Calculation Service
- Material Eligibility Service
- Equipment Eligibility Service
- Qualification Service
- Genealogy Service
- Quality Event Service
- Release / Disposition Service
- Evidence Service
- Regulatory Export Service
- Integration Command Service
- Compliance Reporting Service

Deployment units may be consolidated; logical boundaries may not.


---

## WP-00 — Repository, Tooling & Contract Foundations

**Depends on:** none  
**Scope summary:** Monorepo skeleton, contract tooling, CI gates, architecture guardrails, migration/test/release standards.  
**Source documents:** 01, 02, 97, 98, 99, 100, 101, 102, 103, 104

### Module DOC-001 — Master Product, Compliance & Architecture Bible (Document 01)

- **Authoritative store:** n/a (standard / governance document)
- **Code location:** `docs/architecture`
- **Requirements:** C-001..069 (69); MAT-001..022 (22); ST-001..020 (20); QMS-001..018 (18); CP-001..020 (20); PM-001..010 (10); MD-001..025 (25); PH-001..030 (30); SPEC-SEC-001..001 (1)
- **Functionalities (requirement rows):** 215
- **Function/service contracts in source:** 0
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 0
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** N/A (architecture / compliance baseline document) — automation role: enforcement + automated gating
- **Failure behaviour (source):** The system should define per-customer: - uptime objective, - RPO, - RTO, - backup frequency, - restore procedure, - failover architecture, - offline-production behavior, - edge buffering, - degraded-mode rules. For production operations, loss of the SaaS connection must never silently cause loss of 

### Module DOC-002 — System Architecture & GxP Core Technical Specification (Document 02)

- **Authoritative store:** n/a (standard / governance document)
- **Code location:** `docs/architecture`
- **Requirements:** ARC-001..018 (18); MUT-001..015 (15); SIG-001..016 (16)
- **Functionalities (requirement rows):** 49
- **Function/service contracts in source:** 0
- **Data entities:** 16 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 27
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** N/A (architecture / compliance baseline document) — automation role: enforcement + automated gating
- **Failure behaviour (source):** If Temporal is temporarily unavailable: - authoritative GxP state remains intact; - new orchestration operations may pause; - existing evidence is not lost; - recovery/reconciliation restarts from authoritative state. ---

### Module SPEC-ENG-001 — Coding Standards (Document 97)

**Objective:** Define enforceable coding conventions and prohibited implementation patterns for Frappe/Python, TypeScript GxP services, SQL, integrations, configuration, logging and tests.

- **Authoritative store:** n/a (standard / governance document)
- **Code location:** `tooling`
- **Requirements:** CODE-FR-001..036 (36)
- **Functionalities (requirement rows):** 36
- **Function/service contracts in source:** 8
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** INDIRECT_GXP (engineering control) — automation role: enforcement + automated gating

### Module SPEC-ENG-002 — Architecture Rules for Claude Code / Codex (Document 98)

**Objective:** Define mandatory operating rules for AI coding agents so generated code cannot silently violate GxP architecture, Part 11 controls, data ownership, validation, security or IP/dependency governance.

- **Authoritative store:** n/a (standard / governance document)
- **Code location:** `tooling`
- **Requirements:** AGT-FR-001..036 (36)
- **Functionalities (requirement rows):** 36
- **Function/service contracts in source:** 8
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=False, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** INDIRECT_GXP (engineering control) — automation role: informational/record-keeping

### Module SPEC-ENG-003 — Repository & Branching Standard (Document 99)

**Objective:** Define Git repository organization, branch protection, PR review, CODEOWNERS, release tags, hotfix governance and provenance needed for safe AI-assisted development and acquisition due diligence.

- **Authoritative store:** n/a (standard / governance document)
- **Code location:** `tooling`
- **Requirements:** GIT-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 8
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** INDIRECT_GXP (engineering control) — automation role: enforcement + automated gating

### Module SPEC-ENG-004 — Database Migration Standard (Document 100)

**Objective:** Define safe schema and data evolution for PostgreSQL GxP databases and Frappe/MariaDB, including compatibility, backfills, locking, reconciliation, recovery and validation evidence.

- **Authoritative store:** n/a (standard / governance document)
- **Code location:** `tooling`
- **Requirements:** MIG-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 8
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 8
- **Regulated markers:** signature=False, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** INDIRECT_GXP (engineering control) — automation role: informational/record-keeping

### Module SPEC-ENG-005 — API & Event Contract Standard (Document 101)

**Objective:** Define stable API/event design, schema/versioning, idempotency, concurrency, errors, compatibility, deprecation and consumer testing for internal and customer integrations.

- **Authoritative store:** n/a (standard / governance document)
- **Code location:** `tooling`
- **Requirements:** CTR-FR-001..036 (36)
- **Functionalities (requirement rows):** 36
- **Function/service contracts in source:** 8
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=False, audit=False, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** INDIRECT_GXP (engineering control) — automation role: calculation

### Module SPEC-ENG-006 — Testing Strategy (Document 102)

**Objective:** Define engineering test layers, risk-based minimum assurance, CI evidence, failure/concurrency testing and reuse of trustworthy engineering tests as validation evidence.

- **Authoritative store:** n/a (standard / governance document)
- **Code location:** `tooling`
- **Requirements:** TEST-FR-001..036 (36)
- **Functionalities (requirement rows):** 36
- **Function/service contracts in source:** 8
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** INDIRECT_GXP (engineering control) — automation role: enforcement + automated gating

### Module SPEC-ENG-007 — CI/CD & Release Process (Document 103)

**Objective:** Define automated build, security/test gates, immutable packaging, release evidence, validated production authorization, deployment and rollback.

- **Authoritative store:** n/a (standard / governance document)
- **Code location:** `tooling`
- **Requirements:** CICD-FR-001..036 (36)
- **Functionalities (requirement rows):** 36
- **Function/service contracts in source:** 9
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** INDIRECT_GXP (engineering control) — automation role: enforcement + automated gating

### Module SPEC-ENG-008 — SBOM / Third-Party License Management (Document 104)

**Objective:** Define dependency inventory, SBOM generation, license/IP approval, vulnerability/EOL management and acquisition-ready third-party evidence.

- **Authoritative store:** n/a (standard / governance document)
- **Code location:** `tooling`
- **Requirements:** DEP-FR-001..036 (36)
- **Functionalities (requirement rows):** 36
- **Function/service contracts in source:** 8
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=False, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** INDIRECT_GXP (engineering control) — automation role: enforcement + automated gating


---

## WP-01 — GxP Core — Mutation / Signature / Audit / Vault / IAM / Rules

**Depends on:** WP-00  
**Scope summary:** The regulated kernel: every later module depends on these six services.  
**Source documents:** 03, 04, 05, 06, 07, 08

### Module SPEC-GXP-001 — GxP Mutation Gateway (Document 03)

**Objective:** Define the sole controlled technical pathway through which authoritative regulated state may be created or changed.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/mutation`
- **Requirements:** MUT-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 0
- **Data entities:** 5 | **APIs:** 4 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 30
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** | Failure | Required behavior | |---|---| | PostgreSQL unavailable | No regulated mutation succeeds | | Policy unavailable | Fail closed | | Signature unavailable and signature required | Command remains uncommitted | | Event bus unavailable | Authoritative commit succeeds if outbox commit succeeds;

### Module SPEC-GXP-002 — 21 CFR Part 11 Electronic Signature (Document 04)

**Objective:** Define the electronic-signature subsystem used for regulated signings throughout eBMR/eDHR, QMS, QC, materials, equipment and release workflows.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/signature`
- **Requirements:** SIG-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 0
- **Data entities:** 2 | **APIs:** 3 | **Events:** 0 | **UI surfaces:** 24 | **Test scenarios:** 30
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** | Condition | Result | |---|---| | Wrong user completes challenge | Reject | | Record changed | Mark stale, require new challenge | | Challenge expired | Reject | | IdP unavailable | Signing unavailable; no bypass | | Authentication succeeds but Mutation commit fails | Challenge/signature state must

### Module SPEC-GXP-003 — Immutable Audit Ledger & Audit Review (Document 05)

**Objective:** Define the independent GxP audit system that records who did what, when, to which regulated record, from which source, under which rule/signature context, while preserving previous information and supporting long-term review.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/audit`
- **Requirements:** AUD-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 0
- **Data entities:** 0 | **APIs:** 5 | **Events:** 0 | **UI surfaces:** 15 | **Test scenarios:** 37
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: calculation
- **Failure behaviour (source):** If audit insert in the authoritative transaction fails, regulated mutation fails. If integrity-checkpoint generation fails after prior audit events were committed, events remain valid but health alert is raised and checkpoint retried. If audit read projection fails, authoritative ledger remains avai

### Module SPEC-GXP-004 — Record Version Vault, Locking, Amendment & Controlled Correction (Document 06)

**Objective:** Define how regulated information becomes immutable, versioned, historically reproducible and safely correctable without obscuring the original record.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/vault`
- **Requirements:** VLT-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 0
- **Data entities:** 5 | **APIs:** 6 | **Events:** 0 | **UI surfaces:** 6 | **Test scenarios:** 31
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-IAM-001 — Identity, Authorization, RBAC, Qualification & Segregation-of-Duties (Document 07)

**Objective:** Define identity and authority so that only properly authenticated, authorized and qualified humans/services/devices can perform the exact regulated action at the exact site/resource/state.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/policy`
- **Requirements:** IAM-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 0
- **Data entities:** 4 | **APIs:** 7 | **Events:** 0 | **UI surfaces:** 8 | **Test scenarios:** 27
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-GXP-006 — Regulatory Rules & Calculation Engine (Document 08)

**Objective:** Define a deterministic, version-controlled engine for regulatory/manufacturing decisions and calculations without allowing customers or developers to inject uncontrolled executable code.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/rules`
- **Requirements:** RUL-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 0
- **Data entities:** 2 | **APIs:** 6 | **Events:** 0 | **UI surfaces:** 9 | **Test scenarios:** 35
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - missing critical input → fail/hold per released rule; - invalid unit → reject; - divide by zero/domain error → controlled calculation failure; - unreleased rule → cannot execute production; - rule engine unavailable → dependent regulated action fails closed; - rule version not found for historical


---

## WP-02 — Product / Recipe / Batch Execution

**Depends on:** WP-01  
**Scope summary:** Product & constituent master, master recipe/MMR, batch execution state machine, eDHR.  
**Source documents:** 09, 10, 11, 12

### Module SPEC-EBMR-000 — Product, Constituent & Regulatory Profile Master (Document 09)

**Objective:** Define the canonical regulated master for products, drug/device constituents, DDCP compatibility, manufacturing profiles, site applicability and product-level regulatory configuration.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/ebmr`
- **Requirements:** PRD-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 0
- **Data entities:** 6 | **APIs:** 11 | **Events:** 8 | **UI surfaces:** 10 | **Test scenarios:** 16
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: calculation

### Module SPEC-EBMR-001 — Master Recipe / Master Manufacturing Record Specification (Document 10)

**Objective:** Define how manufacturing instructions are authored, reviewed, released, frozen, versioned and converted into an executable batch/device production snapshot.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/ebmr`
- **Requirements:** RCP-FR-001..036 (36)
- **Functionalities (requirement rows):** 36
- **Function/service contracts in source:** 0
- **Data entities:** 9 | **APIs:** 10 | **Events:** 6 | **UI surfaces:** 14 | **Test scenarios:** 18
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-EBMR-002 — Batch Execution Engine & State Machine Specification (Document 11)

**Objective:** Define runtime manufacturing execution from batch creation through production completion and QA handoff.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/ebmr`
- **Requirements:** BAT-FR-001..036 (36)
- **Functionalities (requirement rows):** 36
- **Function/service contracts in source:** 0
- **Data entities:** 5 | **APIs:** 15 | **Events:** 16 | **UI surfaces:** 18 | **Test scenarios:** 21
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** | Failure | Behavior | |---|---| | Browser closes | Authoritative step remains; reopen from server state | | Frappe restart | Batch state persists | | Temporal worker restart | Workflow replay/resume | | PostgreSQL unavailable | Regulated mutation stops | | Edge unavailable | Automated source pendin

### Module SPEC-EBMR-003 — eDHR / Device Production History Specification (Document 12)

**Objective:** Define the electronic device production-history capability used for the device constituent of DDCP V1 and future standalone medical-device manufacturing.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/ebmr`
- **Requirements:** DHR-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 0
- **Data entities:** 5 | **APIs:** 11 | **Events:** 9 | **UI surfaces:** 10 | **Test scenarios:** 24
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating


---

## WP-03 — Genealogy / Review / Release / Packaging / Yield

**Depends on:** WP-02  
**Scope summary:** Traceability, review-by-exception, disposition, packaging/labeling reconciliation and yield.  
**Source documents:** 13, 14, 15, 16, 17

### Module SPEC-EBMR-004 — Genealogy & Traceability Engine Specification (Document 13)

**Objective:** Provide one proprietary cross-domain genealogy engine for drug, device and combination-product manufacturing.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/ebmr`
- **Requirements:** GEN-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 0
- **Data entities:** 2 | **APIs:** 8 | **Events:** 5 | **UI surfaces:** 8 | **Test scenarios:** 13
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-EBMR-005 — Review-by-Exception & QA Review Specification (Document 14)

**Objective:** Define a QA review system that reduces review effort through exception prioritization while preserving full-record access and independent completeness checks.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/ebmr`
- **Requirements:** RBE-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 0
- **Data entities:** 3 | **APIs:** 9 | **Events:** 6 | **UI surfaces:** 15 | **Test scenarios:** 13
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-EBMR-006 — Release / Disposition Engine Specification (Document 15)

**Objective:** Define the authoritative final quality decision engine for release, rejection, hold, rework/reprocess and other controlled dispositions.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/ebmr`
- **Requirements:** REL-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 0
- **Data entities:** 3 | **APIs:** 9 | **Events:** 9 | **UI surfaces:** 12 | **Test scenarios:** 16
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-EBMR-007 — Packaging, Labeling & Reconciliation Specification (Document 16)

**Objective:** Define packaging and labeling controls that prevent mix-ups, preserve exact label/artwork/UDI history, reconcile controlled label quantities, and integrate packaging evidence into the batch/eDHR and final release.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/ebmr`
- **Requirements:** PKG-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 0
- **Data entities:** 4 | **APIs:** 10 | **Events:** 11 | **UI surfaces:** 11 | **Test scenarios:** 15
- **Regulated markers:** signature=False, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-EBMR-008 — Yield, Calculations & Manufacturing Reconciliation Specification (Document 17)

**Objective:** Define manufacturing yield, potency/quantity calculations and material/packaging/label/component reconciliation used throughout eBMR/eDHR and DDCP final review/release.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/ebmr`
- **Requirements:** YLD-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 0
- **Data entities:** 2 | **APIs:** 8 | **Events:** 7 | **UI surfaces:** 10 | **Test scenarios:** 18
- **Regulated markers:** signature=True, release=True, audit=False, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating


---

## WP-04 — Procurement / Materials / QC

**Depends on:** WP-02  
**Scope summary:** Supplier/procurement, receipt/quarantine, inventory, dispensing, consumption, QC/sampling, LIMS, OOS/OOT.  
**Source documents:** 18, 19, 20, 21, 22, 23, 24, 25

### Module SPEC-MAT-001 — Procurement & Supplier Quality Specification (Document 18)

**Objective:** Define regulated supplier qualification and procurement controls while maintaining a clean boundary between commercial purchasing and GxP material eligibility.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/materials`
- **Requirements:** SUP-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 0
- **Data entities:** 6 | **APIs:** 10 | **Events:** 7 | **UI surfaces:** 10 | **Test scenarios:** 12
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-MAT-002A — Material Receipt, Quarantine & Quality Status Specification (Document 19)

**Objective:** Define controlled receipt, identification, quarantine, sampling/testing and quality disposition of incoming materials, components, drug-product containers and closures.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/materials`
- **Requirements:** RCV-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 0
- **Data entities:** 5 | **APIs:** 9 | **Events:** 9 | **UI surfaces:** 10 | **Test scenarios:** 15
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-MAT-002B — Inventory, Lot/Container & Warehouse Specification (Document 20)

**Objective:** Define regulated inventory control for released/quarantined/rejected materials and components across lots, containers, warehouses and sites.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/materials`
- **Requirements:** INV-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 0
- **Data entities:** 4 | **APIs:** 9 | **Events:** 9 | **UI surfaces:** 11 | **Test scenarios:** 12
- **Regulated markers:** signature=False, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-MAT-002C — Material Dispensing & Weighing Specification (Document 21)

**Objective:** Define controlled material picking, scanning, weighing, verification, labeling and issue to a batch.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/materials`
- **Requirements:** DSP-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 0
- **Data entities:** 4 | **APIs:** 9 | **Events:** 7 | **UI surfaces:** 10 | **Test scenarios:** 14
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-MAT-002D — Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification (Document 22)

**Objective:** Define the complete post-dispensing material lifecycle and ensure every regulated quantity is accounted for before batch completion/release.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/materials`
- **Requirements:** CON-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 0
- **Data entities:** 5 | **APIs:** 8 | **Events:** 9 | **UI surfaces:** 9 | **Test scenarios:** 15
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-QC-001 — Native Basic QC & Sampling Specification (Document 23)

**Objective:** Provide a native QC capability sufficient for customers that do not operate a full external LIMS, while using the same data-integrity, signature, audit and release principles as the rest of the platform.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qc`
- **Requirements:** QC-FR-001..038 (38)
- **Functionalities (requirement rows):** 38
- **Function/service contracts in source:** 0
- **Data entities:** 6 | **APIs:** 13 | **Events:** 10 | **UI surfaces:** 12 | **Test scenarios:** 49
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-QC-002 — LIMS Integration Architecture & Generic Adapter Contract (Document 24)

**Objective:** Define a vendor-neutral LIMS integration contract so native QC and external laboratory systems can coexist without coupling the eBMR domain to one LIMS vendor.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qc`
- **Requirements:** LIMS-FR-001..034 (34)
- **Functionalities (requirement rows):** 34
- **Function/service contracts in source:** 0
- **Data entities:** 0 | **APIs:** 6 | **Events:** 8 | **UI surfaces:** 12 | **Test scenarios:** 17
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-QC-003 — OOS / OOT Management Specification (Document 25)

**Objective:** Define scientifically controlled investigation of Out-of-Specification results and configurable Out-of-Trend signals.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qc`
- **Requirements:** OOS-FR-001..030 (30); OOT-FR-001..010 (10)
- **Functionalities (requirement rows):** 40
- **Function/service contracts in source:** 0
- **Data entities:** 5 | **APIs:** 12 | **Events:** 13 | **UI surfaces:** 16 | **Test scenarios:** 30
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating


---

## WP-05 — Quality Management System

**Depends on:** WP-01, WP-02  
**Scope summary:** Deviation, CAPA, NC, change, document, training, SCAR, risk, audit, complaint, recall, metrics.  
**Source documents:** 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37

### Module SPEC-QMS-001 — Deviation & Investigation Management (Document 26)

**Objective:** Define controlled planned/unplanned deviation handling from detection through containment, investigation, impact, disposition, follow-up and Quality closure.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qms`
- **Requirements:** DEV-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 0
- **Data entities:** 2 | **APIs:** 9 | **Events:** 8 | **UI surfaces:** 10 | **Test scenarios:** 11
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - DB unavailable: no regulated transition succeeds. - Policy/signature unavailable: required action fails closed. - Notification failure: authoritative state may commit; outbox retries notifications. - Stale version: reject and refresh. - Worker restart: due-date/escalation processing resumes from p

### Module SPEC-QMS-002 — CAPA Management (Document 27)

**Objective:** Define corrective/preventive action management from verified problem/root cause through action implementation, objective effectiveness verification and Quality closure.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qms`
- **Requirements:** CAPA-FR-001..022 (22)
- **Functionalities (requirement rows):** 22
- **Function/service contracts in source:** 0
- **Data entities:** 3 | **APIs:** 8 | **Events:** 8 | **UI surfaces:** 10 | **Test scenarios:** 9
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - DB unavailable: no regulated transition succeeds. - Policy/signature unavailable: required action fails closed. - Notification failure: authoritative state may commit; outbox retries notifications. - Stale version: reject and refresh. - Worker restart: due-date/escalation processing resumes from p

### Module SPEC-QMS-003 — Nonconformance Management (Document 28)

**Objective:** Define identification, segregation, evaluation, controlled disposition and verification of nonconforming material, components, device units and finished product.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qms`
- **Requirements:** NCR-FR-001..018 (18)
- **Functionalities (requirement rows):** 18
- **Function/service contracts in source:** 0
- **Data entities:** 2 | **APIs:** 6 | **Events:** 6 | **UI surfaces:** 10 | **Test scenarios:** 9
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - DB unavailable: no regulated transition succeeds. - Policy/signature unavailable: required action fails closed. - Notification failure: authoritative state may commit; outbox retries notifications. - Stale version: reject and refresh. - Worker restart: due-date/escalation processing resumes from p

### Module SPEC-QMS-004 — Change Control (Document 29)

**Objective:** Define controlled evaluation, approval, implementation, validation, effective dating and closure of regulated product/process/system changes.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qms`
- **Requirements:** CHG-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 0
- **Data entities:** 3 | **APIs:** 8 | **Events:** 8 | **UI surfaces:** 11 | **Test scenarios:** 10
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: informational/record-keeping
- **Failure behaviour (source):** - DB unavailable: no regulated transition succeeds. - Policy/signature unavailable: required action fails closed. - Notification failure: authoritative state may commit; outbox retries notifications. - Stale version: reject and refresh. - Worker restart: due-date/escalation processing resumes from p

### Module SPEC-QMS-005 — Document Control (Document 30)

**Objective:** Define lifecycle and distribution control of SOPs, policies, specifications, work instructions, forms and other regulated documents.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qms`
- **Requirements:** DOC-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 0
- **Data entities:** 3 | **APIs:** 7 | **Events:** 6 | **UI surfaces:** 9 | **Test scenarios:** 9
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: informational/record-keeping
- **Failure behaviour (source):** - DB unavailable: no regulated state transition. - Signature/Policy unavailable: fail closed where required. - Notification/outbox failures retry. - Stale version rejects. - Scheduled due/expiry jobs resume from persisted records.

### Module SPEC-QMS-006 — Training & Personnel Qualification (Document 31)

**Objective:** Define role-based training, competency assessment and qualification so untrained or unqualified personnel are actively prevented from regulated work.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qms`
- **Requirements:** TRN-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 0
- **Data entities:** 3 | **APIs:** 8 | **Events:** 7 | **UI surfaces:** 10 | **Test scenarios:** 9
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - DB unavailable: no regulated state transition. - Signature/Policy unavailable: fail closed where required. - Notification/outbox failures retry. - Stale version rejects. - Scheduled due/expiry jobs resume from persisted records.

### Module SPEC-QMS-007 — Supplier Quality / SCAR (Document 32)

**Objective:** Define supplier corrective-action and supplier-quality case management integrated with approved-source status and incoming-material control.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qms`
- **Requirements:** SCAR-FR-001..018 (18)
- **Functionalities (requirement rows):** 18
- **Function/service contracts in source:** 0
- **Data entities:** 2 | **APIs:** 6 | **Events:** 6 | **UI surfaces:** 9 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - DB unavailable: no regulated state transition. - Signature/Policy unavailable: fail closed where required. - Notification/outbox failures retry. - Stale version rejects. - Scheduled due/expiry jobs resume from persisted records.

### Module SPEC-QMS-008 — Risk Management (Document 33)

**Objective:** Define a configurable, versioned quality-risk system connecting hazards/failures to controls, residual risk, mitigations and authorized acceptance.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qms`
- **Requirements:** RSK-FR-001..018 (18)
- **Functionalities (requirement rows):** 18
- **Function/service contracts in source:** 0
- **Data entities:** 2 | **APIs:** 6 | **Events:** 6 | **UI surfaces:** 8 | **Test scenarios:** 7
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - DB unavailable: no regulated state transition. - Signature/Policy unavailable: fail closed where required. - Notification/outbox failures retry. - Stale version rejects. - Scheduled due/expiry jobs resume from persisted records.

### Module SPEC-QMS-009 — Internal Audit Management (Document 34)

**Objective:** Define internal quality audit planning, execution, findings, responses, CAPA linkage, verification and closure.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qms`
- **Requirements:** AUDIT-FR-001..017 (17)
- **Functionalities (requirement rows):** 17
- **Function/service contracts in source:** 0
- **Data entities:** 2 | **APIs:** 6 | **Events:** 6 | **UI surfaces:** 9 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - DB unavailable: no regulated transition. - Signature/Policy unavailable: required action fails closed. - Notification/integration failure: outbox retries; authoritative state remains. - Stale version: reject. - Scheduled due-date/metric jobs recover from persisted state.

### Module SPEC-QMS-010 — Complaint Management (Document 35)

**Objective:** Define complaint intake, product/constituent identification, investigation, reportability-assessment workflow, CAPA/field-action linkage and closure for drug, device and DDCP products.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qms`
- **Requirements:** CMP-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 0
- **Data entities:** 3 | **APIs:** 7 | **Events:** 7 | **UI surfaces:** 11 | **Test scenarios:** 11
- **Regulated markers:** signature=True, release=True, audit=False, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: informational/record-keeping
- **Failure behaviour (source):** - DB unavailable: no regulated transition. - Signature/Policy unavailable: required action fails closed. - Notification/integration failure: outbox retries; authoritative state remains. - Stale version: reject. - Scheduled due-date/metric jobs recover from persisted state.

### Module SPEC-QMS-011 — Recall / Field Action Management (Document 36)

**Objective:** Define affected-product analysis, regulatory assessment, communication, correction/removal execution, reconciliation, effectiveness and closure for recalls and field actions.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qms`
- **Requirements:** FAR-FR-001..020 (20)
- **Functionalities (requirement rows):** 20
- **Function/service contracts in source:** 0
- **Data entities:** 4 | **APIs:** 8 | **Events:** 9 | **UI surfaces:** 11 | **Test scenarios:** 10
- **Regulated markers:** signature=True, release=False, audit=False, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement
- **Failure behaviour (source):** - DB unavailable: no regulated transition. - Signature/Policy unavailable: required action fails closed. - Notification/integration failure: outbox retries; authoritative state remains. - Stale version: reject. - Scheduled due-date/metric jobs recover from persisted state.

### Module SPEC-QMS-012 — Quality Metrics, Trending & Effectiveness Checks (Document 37)

**Objective:** Define versioned quality metrics, cross-module trending, alerting and a reusable effectiveness-check framework for CAPA, supplier actions and field actions.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/qms`
- **Requirements:** MET-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 0
- **Data entities:** 3 | **APIs:** 7 | **Events:** 7 | **UI surfaces:** 9 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - DB unavailable: no regulated transition. - Signature/Policy unavailable: required action fails closed. - Notification/integration failure: outbox retries; authoritative state remains. - Stale version: reject. - Scheduled due-date/metric jobs recover from persisted state.


---

## WP-06 — Equipment / Sterile / Edge

**Depends on:** WP-02, WP-04  
**Scope summary:** Equipment/calibration, cleaning/line clearance, aseptic, EM, sterilization plus the Edge/OT stack.  
**Source documents:** 38, 39, 40, 41, 42, 43, 44, 45, 46, 47

### Module SPEC-EQP-001 — Equipment, Calibration, Qualification & Maintenance (Document 38)

**Objective:** Define regulated equipment lifecycle, qualification, calibration, maintenance, use history and execution eligibility for manufacturing, laboratory and packaging equipment.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/equipment`
- **Requirements:** EQP-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 0
- **Data entities:** 4 | **APIs:** 9 | **Events:** 10 | **UI surfaces:** 10 | **Test scenarios:** 11
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - PostgreSQL unavailable: no regulated state transition. - Edge/device unavailable: behavior follows released fallback policy; no fabricated reading/result. - Calibration/qualification status cannot be assumed when source unavailable. - Worker restart resumes scheduled maintenance/calibration/EM/ste

### Module SPEC-EQP-002 — Cleaning, Sanitization & Line Clearance (Document 39)

**Objective:** Define controlled equipment/area cleaning, sanitization, cleanliness verification, clean/dirty hold times and manufacturing/packaging line clearance.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/equipment`
- **Requirements:** CLN-FR-001..028 (28)
- **Functionalities (requirement rows):** 28
- **Function/service contracts in source:** 0
- **Data entities:** 3 | **APIs:** 7 | **Events:** 8 | **UI surfaces:** 8 | **Test scenarios:** 10
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: informational/record-keeping
- **Failure behaviour (source):** - PostgreSQL unavailable: no regulated state transition. - Edge/device unavailable: behavior follows released fallback policy; no fabricated reading/result. - Calibration/qualification status cannot be assumed when source unavailable. - Worker restart resumes scheduled maintenance/calibration/EM/ste

### Module SPEC-EQP-003 — Sterile / Aseptic Manufacturing Operations (Document 40)

**Objective:** Define aseptic-manufacturing execution controls for sterile/DDCP profiles, including classified-area readiness, personnel qualification, sterile component/equipment status, interventions, process hold times and batch-impact review.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/equipment`
- **Requirements:** ASP-FR-001..028 (28)
- **Functionalities (requirement rows):** 28
- **Function/service contracts in source:** 0
- **Data entities:** 4 | **APIs:** 7 | **Events:** 7 | **UI surfaces:** 10 | **Test scenarios:** 10
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - PostgreSQL unavailable: no regulated state transition. - Edge/device unavailable: behavior follows released fallback policy; no fabricated reading/result. - Calibration/qualification status cannot be assumed when source unavailable. - Worker restart resumes scheduled maintenance/calibration/EM/ste

### Module SPEC-EQP-004 — Environmental Monitoring & Cleanroom State Control (Document 41)

**Objective:** Define environmental-monitoring program execution, continuous/frequent cleanroom condition monitoring, excursion handling, trending and batch/area state correlation.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/equipment`
- **Requirements:** EM-FR-001..026 (26)
- **Functionalities (requirement rows):** 26
- **Function/service contracts in source:** 0
- **Data entities:** 4 | **APIs:** 8 | **Events:** 8 | **UI surfaces:** 11 | **Test scenarios:** 10
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: informational/record-keeping
- **Failure behaviour (source):** - PostgreSQL unavailable: no regulated state transition. - Edge/device unavailable: behavior follows released fallback policy; no fabricated reading/result. - Calibration/qualification status cannot be assumed when source unavailable. - Worker restart resumes scheduled maintenance/calibration/EM/ste

### Module SPEC-EQP-005 — Sterilization, CIP/SIP & Sterile Filtration Management (Document 42)

**Objective:** Define validated sterilization and automated cleaning/sterilization cycles plus sterile-filtration identity, integrity testing, process evidence and downstream sterile-status issuance.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/equipment`
- **Requirements:** STR-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 0
- **Data entities:** 4 | **APIs:** 9 | **Events:** 10 | **UI surfaces:** 10 | **Test scenarios:** 11
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - PostgreSQL unavailable: no regulated state transition. - Edge/device unavailable: behavior follows released fallback policy; no fabricated reading/result. - Calibration/qualification status cannot be assumed when source unavailable. - Worker restart resumes scheduled maintenance/calibration/EM/ste

### Module SPEC-EDGE-001 — Edge Gateway Runtime Architecture & Construction Specification (Document 43)

**Objective:** Define the plant-side Edge Gateway runtime that securely acquires industrial evidence, normalizes it, buffers it through outages, and forwards it to the central/local GxP services without becoming the GxP system of record.

- **Authoritative store:** Edge local store (buffered, pre-authoritative) → PostgreSQL on acceptance
- **Code location:** `edge`
- **Requirements:** EDGE-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 16
- **Data entities:** 0 | **APIs:** 6 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 14
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-EDGE-002 — Industrial Device & Protocol Connectivity / Driver Specification (Document 44)

**Objective:** Define protocol-neutral driver contracts and reference behavior for OPC UA, Modbus TCP/RTU, MQTT, SNMP and controlled custom/instrument adapters.

- **Authoritative store:** Edge local store (buffered, pre-authoritative) → PostgreSQL on acceptance
- **Code location:** `edge`
- **Requirements:** DRV-FR-001..025 (25)
- **Functionalities (requirement rows):** 25
- **Function/service contracts in source:** 12
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 11
- **Regulated markers:** signature=False, release=True, audit=False, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-EDGE-003 — Store-and-Forward, Offline Buffering, Time Integrity & Data Quality (Document 45)

**Objective:** Define durable Edge buffering, outage recovery, acknowledgement, replay, time/freshness semantics and data-quality propagation so plant evidence is not lost or silently altered during network interruptions.

- **Authoritative store:** Edge local store (buffered, pre-authoritative) → PostgreSQL on acceptance
- **Code location:** `edge`
- **Requirements:** BUF-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 10
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 0
- **Regulated markers:** signature=False, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-EDGE-004 — Barcode, Scanner, Balance, Printer, Tester & Peripheral Integration (Document 46)

**Objective:** Define operator-facing peripheral integration contracts for barcode scanning, weighing, controlled printing, testers, vision systems and file-producing instruments used by material, packaging, QC and device-production workflows.

- **Authoritative store:** Edge local store (buffered, pre-authoritative) → PostgreSQL on acceptance
- **Code location:** `edge`
- **Requirements:** PER-FR-001..025 (25)
- **Functionalities (requirement rows):** 25
- **Function/service contracts in source:** 10
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 7 | **Test scenarios:** 0
- **Regulated markers:** signature=False, release=True, audit=False, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: informational/record-keeping

### Module SPEC-EDGE-005 — Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary (Document 47)

**Objective:** Define how machine/PLC/SCADA signals are mapped into regulated manufacturing evidence, how high-frequency telemetry is separated from GxP records, how batch context is bound, and how any future machine command path is strictly allowlisted and validated.

- **Authoritative store:** Edge local store (buffered, pre-authoritative) → PostgreSQL on acceptance
- **Code location:** `edge`
- **Requirements:** MAP-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 10
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 12
- **Regulated markers:** signature=True, release=True, audit=False, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating


---

## WP-07 — Enterprise Integrations

**Depends on:** WP-01, WP-04  
**Scope summary:** ERP architecture and adapters, master-data sync, integration error/retry/reconciliation.  
**Source documents:** 48, 49, 50, 51, 52, 53

### Module SPEC-ERP-001 — Enterprise ERP Integration Architecture & Provider Contract (Document 48)

**Objective:** Define the vendor-neutral ERP integration architecture, source-of-truth boundaries, provider interfaces, command/event ledgers and transaction/reconciliation behavior for ERPNext, SAP, Oracle, Dynamics and customer ERPs.

- **Authoritative store:** External ERP (commercial truth) / PostgreSQL (GxP truth) per Doc 48 ownership matrix
- **Code location:** `services/integration-gateway`
- **Requirements:** ERP-ARC-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 10
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 9 | **Test scenarios:** 10
- **Regulated markers:** signature=False, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** Example: GxP material consumption commits, SAP posting fails. Result: - GxP consumption remains valid; - integration command becomes FAILED/RETRY_WAIT; - batch review can display `ERP_POSTING_PENDING`; - worker retries; - reconciliation verifies eventual external reference; - nobody edits the GxP co

### Module SPEC-ERP-002 — ERPNext Adapter Detailed Contract (Document 49)

**Objective:** Define the concrete ERPNext adapter while preserving the independent eBMR/GxP application architecture and avoiding ERPNext core modifications.

- **Authoritative store:** External ERP (commercial truth) / PostgreSQL (GxP truth) per Doc 48 ownership matrix
- **Code location:** `services/integration-gateway`
- **Requirements:** ENXT-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 10
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 11
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-ERP-003 — SAP S/4HANA Adapter Contract (Document 50)

**Objective:** Define the SAP S/4HANA adapter boundary and canonical mappings for product/material references, inventory/material documents, production-order references and reconciliation without coupling GxP services to SAP semantics.

- **Authoritative store:** External ERP (commercial truth) / PostgreSQL (GxP truth) per Doc 48 ownership matrix
- **Code location:** `services/integration-gateway`
- **Requirements:** SAP-FR-001..025 (25)
- **Functionalities (requirement rows):** 25
- **Function/service contracts in source:** 8
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 10
- **Regulated markers:** signature=False, release=True, audit=False, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-ERP-004 — Oracle Fusion, Dynamics 365 & Custom ERP Adapter Contracts (Document 51)

**Objective:** Define implementation contracts for Oracle Fusion Cloud SCM, Microsoft Dynamics 365 Finance/Supply Chain, and generic customer ERP adapters while maintaining one canonical ERPProvider interface.

- **Authoritative store:** External ERP (commercial truth) / PostgreSQL (GxP truth) per Doc 48 ownership matrix
- **Code location:** `services/integration-gateway`
- **Requirements:** MULTI-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 9
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 9
- **Regulated markers:** signature=False, release=True, audit=False, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-ERP-005 — Master Data Synchronization, Mapping & Reconciliation (Document 52)

**Objective:** Define controlled master-data synchronization and mapping between eBMR/GxP and external ERP systems, with explicit field ownership, staging, conflict handling, approval and historical mapping versioning.

- **Authoritative store:** External ERP (commercial truth) / PostgreSQL (GxP truth) per Doc 48 ownership matrix
- **Code location:** `services/integration-gateway`
- **Requirements:** MDS-FR-001..028 (28)
- **Functionalities (requirement rows):** 28
- **Function/service contracts in source:** 10
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 11
- **Regulated markers:** signature=False, release=False, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: calculation

### Module SPEC-ERP-006 — Integration Error Handling, Retry, Idempotency & Reconciliation (Document 53)

**Objective:** Define one consistent integration reliability model across ERP, LIMS, Edge and other enterprise adapters, with explicit error classification, retries, idempotency, uncertain-commit reconciliation, dead-letter handling and human-controlled recovery.

- **Authoritative store:** External ERP (commercial truth) / PostgreSQL (GxP truth) per Doc 48 ownership matrix
- **Code location:** `services/integration-gateway`
- **Requirements:** INT-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 12
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 14
- **Regulated markers:** signature=False, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating


---

## WP-08 — DDCP Product Profiles

**Depends on:** WP-02, WP-03, WP-06  
**Scope summary:** Prefilled syringe, autoinjector/pen, inhalation MDI/DPI and drug-eluting device execution profiles.  
**Source documents:** 54, 55, 56, 57

### Module SPEC-DDCP-001 — Prefilled Syringe & Injectable DDCP Manufacturing Profile (Document 54)

**Objective:** Define the executable product-family profile for prefilled syringe and closely related sterile injectable drug-delivery combination products, from released bulk constituent and primary components through aseptic filling, closure, inspection, device-functional evidence, packaging and final DDCP release.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/ddcp`
- **Requirements:** PFS-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 11
- **Data entities:** 9 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 12 | **Test scenarios:** 12
- **Regulated markers:** signature=False, release=True, audit=False, calculation=True, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-DDCP-002 — Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile (Document 55)

**Objective:** Define injector-device assembly and performance evidence for autoinjectors, injector pens and cartridge/PFS-based delivery systems, including unit-level drug-container pairing, device assembly, delivery-performance testing, genealogy and final DDCP release.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/ddcp`
- **Requirements:** INJ-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 10
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 11 | **Test scenarios:** 10
- **Regulated markers:** signature=True, release=True, audit=False, calculation=True, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-DDCP-003 — Inhalation DDCP Manufacturing Profile — MDI / DPI (Document 56)

**Objective:** Define a configurable inhalation combination-product manufacturing profile for metered-dose inhalers and dry-powder inhalers, covering drug formulation/blend, container/device components, filling/assembly, closure integrity, inhalation performance testing, packaging, genealogy and final release.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/ddcp`
- **Requirements:** INH-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 9
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 10 | **Test scenarios:** 9
- **Regulated markers:** signature=True, release=True, audit=False, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating

### Module SPEC-DDCP-004 — Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile (Document 57)

**Objective:** Define the product-family profile for devices coated, impregnated or otherwise combined with a drug (and extensibly biologic), with explicit substrate/drug constituent handoffs, coating process evidence, dual material/unit reconciliation, sterilization interaction, product testing, genealogy and final DDCP release.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/ddcp`
- **Requirements:** COAT-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 10
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 12 | **Test scenarios:** 12
- **Regulated markers:** signature=False, release=True, audit=False, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating


---

## WP-09 — Postmarket

**Depends on:** WP-05  
**Scope summary:** Postmarket surveillance/signal, reportability & electronic submission, combination-product coordination.  
**Source documents:** 58, 59, 60

### Module SPEC-PM-001 — Postmarket Surveillance, Safety Case & Signal Management (Document 58)

**Objective:** Define postmarket safety surveillance across complaints, service/repair, literature, manufacturing/QC events, field actions and external sources; normalize them into linked safety cases; detect/assess safety signals; and create controlled handoffs into QMS and formal regulatory reporting.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/postmarket`
- **Requirements:** PMS-FR-001..034 (34)
- **Functionalities (requirement rows):** 34
- **Function/service contracts in source:** 13
- **Data entities:** 4 | **APIs:** 11 | **Events:** 9 | **UI surfaces:** 12 | **Test scenarios:** 13
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: informational/record-keeping
- **Failure behaviour (source):** Use optimistic concurrency for case/signal versions. Follow-up received during review creates a new version and forces reviewer refresh. Analytics failure cannot close a signal. Missing product identity or denominator is explicit, not inferred.

### Module SPEC-PM-002 — Regulatory Reportability Assessment & Electronic Safety Submission Management (Document 59)

**Objective:** Define reportability assessment, regulatory clocks, report construction, approval, electronic/manual submission, acknowledgement, rejection recovery and follow-up for device, drug, biologic and combination-product postmarket safety reports.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/postmarket`
- **Requirements:** REG-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 13
- **Data entities:** 4 | **APIs:** 10 | **Events:** 0 | **UI surfaces:** 12 | **Test scenarios:** 15
- **Regulated markers:** signature=True, release=False, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: calculation

### Module SPEC-PM-003 — Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar (Document 60)

**Objective:** Define combination-product applicant coordination, constituent-part applicant information sharing, correction/removal regulatory records, Field Alert/BPDR workflow hooks, periodic safety reporting calendar, FDA information requests, deadline overrides and postmarket recordkeeping/retention.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `services/gxp-api/src/modules/postmarket`
- **Requirements:** PMO-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 15
- **Data entities:** 5 | **APIs:** 14 | **Events:** 15 | **UI surfaces:** 12 | **Test scenarios:** 14
- **Regulated markers:** signature=False, release=False, audit=True, calculation=True, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: calculation


---

## WP-10 — Security

**Depends on:** WP-00, WP-01  
**Scope summary:** Security architecture, federation, privileged access, secure runtime, secrets/PKI, network, monitoring, SSDLC.  
**Source documents:** 61, 62, 63, 64, 65, 66, 67, 68

### Module SPEC-SEC-001 — Security Architecture, Threat Model & Control Framework (Document 61)

**Objective:** Define the platform-wide cybersecurity architecture, threat model, security risk/control catalogue and traceability framework so security decisions are explicit, testable and reviewable rather than scattered implementation choices.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `platform/security`
- **Requirements:** SEC-THR-001..028 (28)
- **Functionalities (requirement rows):** 28
- **Function/service contracts in source:** 8
- **Data entities:** 4 | **APIs:** 6 | **Events:** 6 | **UI surfaces:** 8 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=False, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement
- **Failure behaviour (source):** - Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies. - Security subsystem outage must not silently downgrade protection. - Retryable infrastructure failures use bounded retry/

### Module SPEC-SEC-002 — Identity Federation, SSO, MFA, Sessions & Service Identities (Document 62)

**Objective:** Define secure identity federation and session handling for humans, services and Edge/device identities while preserving the separate GxP authorization and Part 11 signature layers.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `platform/security`
- **Requirements:** IAMSEC-FR-001..026 (26)
- **Functionalities (requirement rows):** 26
- **Function/service contracts in source:** 8
- **Data entities:** 3 | **APIs:** 6 | **Events:** 7 | **UI surfaces:** 6 | **Test scenarios:** 9
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies. - Security subsystem outage must not silently downgrade protection. - Retryable infrastructure failures use bounded retry/

### Module SPEC-SEC-003 — Privileged Access, Support Access, Break-Glass & Administrative Security (Document 63)

**Objective:** Define controlled privileged technical access to production and customer environments so administrators and support personnel can operate the platform without acquiring Quality authority or bypassing GxP mutation controls.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `platform/security`
- **Requirements:** PAM-FR-001..026 (26)
- **Functionalities (requirement rows):** 26
- **Function/service contracts in source:** 8
- **Data entities:** 3 | **APIs:** 6 | **Events:** 7 | **UI surfaces:** 7 | **Test scenarios:** 7
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: informational/record-keeping
- **Failure behaviour (source):** - Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies. - Security subsystem outage must not silently downgrade protection. - Retryable infrastructure failures use bounded retry/

### Module SPEC-SEC-004 — Application, API, UI & Secure Runtime Engineering (Document 64)

**Objective:** Define implementation-level web, API and service security controls aligned to OWASP ASVS 5.0 and API Security Top 10, with server-side authorization, strict schemas, injection prevention, SSRF controls, safe file handling and abuse protection.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `platform/security`
- **Requirements:** APPSEC-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 9
- **Data entities:** 3 | **APIs:** 3 | **Events:** 6 | **UI surfaces:** 6 | **Test scenarios:** 11
- **Regulated markers:** signature=True, release=False, audit=False, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement
- **Failure behaviour (source):** - Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies. - Security subsystem outage must not silently downgrade protection. - Retryable infrastructure failures use bounded retry/

### Module SPEC-SEC-005 — Secrets Management, PKI, Cryptography & Key Lifecycle (Document 65)

**Objective:** Define secrets, service certificates, TLS, encryption, hashing and key lifecycle so credentials and cryptographic trust are isolated, rotatable and recoverable across cloud and on-prem deployments.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `platform/security`
- **Requirements:** KEY-FR-001..028 (28)
- **Functionalities (requirement rows):** 28
- **Function/service contracts in source:** 8
- **Data entities:** 3 | **APIs:** 5 | **Events:** 7 | **UI surfaces:** 6 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies. - Security subsystem outage must not silently downgrade protection. - Retryable infrastructure failures use bounded retry/

### Module SPEC-SEC-006 — Network, Tenant, Deployment Isolation & Zero-Trust Architecture (Document 66)

**Objective:** Define trust zones, service/network flows, OT boundaries, tenant/site isolation and workload hardening so deployment security does not rely on a flat trusted network.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `platform/security`
- **Requirements:** NET-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 6
- **Data entities:** 2 | **APIs:** 2 | **Events:** 4 | **UI surfaces:** 5 | **Test scenarios:** 7
- **Regulated markers:** signature=False, release=False, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement
- **Failure behaviour (source):** - Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies. - Security subsystem outage must not silently downgrade protection. - Retryable infrastructure failures use bounded retry/

### Module SPEC-SEC-007 — Security Logging, Monitoring, Incident Response & Forensic Evidence (Document 67)

**Objective:** Define security telemetry, detection, incident response, forensic evidence and GxP-impact assessment while keeping the regulatory audit ledger distinct from security logs.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `platform/security`
- **Requirements:** MON-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 8
- **Data entities:** 2 | **APIs:** 5 | **Events:** 6 | **UI surfaces:** 9 | **Test scenarios:** 9
- **Regulated markers:** signature=True, release=False, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement
- **Failure behaviour (source):** - Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies. - Security subsystem outage must not silently downgrade protection. - Retryable infrastructure failures use bounded retry/

### Module SPEC-SEC-008 — Secure SDLC, Software Supply Chain, SBOM, Vulnerability & Release Security (Document 68)

**Objective:** Define secure development, build provenance, dependency management, SBOM, vulnerability handling, penetration testing and release-security gates so the software itself is developed and delivered as a secure-by-design regulated platform.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `platform/security`
- **Requirements:** SDLC-FR-001..034 (34)
- **Functionalities (requirement rows):** 34
- **Function/service contracts in source:** 10
- **Data entities:** 3 | **APIs:** 4 | **Events:** 6 | **UI surfaces:** 7 | **Test scenarios:** 10
- **Regulated markers:** signature=True, release=True, audit=False, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies. - Security subsystem outage must not silently downgrade protection. - Retryable infrastructure failures use bounded retry/


---

## WP-11 — Data / Infrastructure / DR / SRE

**Depends on:** WP-00, WP-01  
**Scope summary:** Ownership/lineage, PostgreSQL, MariaDB projections, evidence/WORM, NATS/outbox, Temporal, read models, DR, deployment, SRE.  
**Source documents:** 69, 70, 71, 72, 73, 74, 75, 76, 77, 78

### Module SPEC-DATA-001 — Enterprise Data Ownership, Persistence Topology & Data Lineage (Document 69)

**Objective:** Define the authoritative ownership of every data class and the rules for PostgreSQL, Frappe/MariaDB, object storage, historian, cache, search, messaging and orchestration so Claude Code never creates dual-master regulated data.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `infrastructure`
- **Requirements:** DATA-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 8
- **Data entities:** 3 | **APIs:** 4 | **Events:** 5 | **UI surfaces:** 5 | **Test scenarios:** 7
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success. - Recovery must preserve idempotency and version/concurrency rules. - Data repair is performed through controlled tools/commands and evidence, not undocument

### Module SPEC-DATA-002 — PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency (Document 70)

**Objective:** Define the authoritative PostgreSQL construction standard for schema ownership, transactions, concurrency, audit/outbox atomicity, partitioning, indexes, performance, integrity and controlled migrations.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `infrastructure`
- **Requirements:** PG-FR-001..034 (34)
- **Functionalities (requirement rows):** 34
- **Function/service contracts in source:** 8
- **Data entities:** 0 | **APIs:** 0 | **Events:** 6 | **UI surfaces:** 6 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success. - Recovery must preserve idempotency and version/concurrency rules. - Data repair is performed through controlled tools/commands and evidence, not undocument

### Module SPEC-DATA-003 — Frappe / MariaDB Operational Database, Projection & UI Data Architecture (Document 71)

**Objective:** Define MariaDB's exact role as the Frappe operational/UI/configuration and projection database, including read-only source-derived DocTypes, projection rebuilds and explicit prohibition on using Frappe persistence as the sole GxP authority.

- **Authoritative store:** MariaDB (Frappe operational/projection — NON-AUTHORITATIVE for GxP)
- **Code location:** `infrastructure`
- **Requirements:** MDB-FR-001..028 (28)
- **Functionalities (requirement rows):** 28
- **Function/service contracts in source:** 6
- **Data entities:** 0 | **APIs:** 1 | **Events:** 4 | **UI surfaces:** 5 | **Test scenarios:** 6
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success. - Recovery must preserve idempotency and version/concurrency rules. - Data repair is performed through controlled tools/commands and evidence, not undocument

### Module SPEC-DATA-004 — Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle (Document 72)

**Objective:** Define cloud-neutral object/evidence storage for immutable files, raw instrument data, images, PDFs, cycle files and evidence manifests, including content integrity, WORM retention, legal hold, export and provider migration.

- **Authoritative store:** Object store (WORM evidence) + PostgreSQL metadata
- **Code location:** `infrastructure`
- **Requirements:** OBJ-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 8
- **Data entities:** 2 | **APIs:** 6 | **Events:** 7 | **UI surfaces:** 7 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success. - Recovery must preserve idempotency and version/concurrency rules. - Data repair is performed through controlled tools/commands and evidence, not undocument

### Module SPEC-DATA-005 — NATS / JetStream Event Bus, Transactional Outbox & Async Contracts (Document 73)

**Objective:** Define event contracts and reliable asynchronous delivery using PostgreSQL transactional outbox plus NATS/JetStream, including idempotent consumers, schema governance, replay, DLQ and broker-failure behavior.

- **Authoritative store:** PostgreSQL transactional outbox (authoritative) / NATS JetStream (transport)
- **Code location:** `infrastructure`
- **Requirements:** EVT-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 8
- **Data entities:** 2 | **APIs:** 0 | **Events:** 6 | **UI surfaces:** 6 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=False, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement
- **Failure behaviour (source):** - A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success. - Recovery must preserve idempotency and version/concurrency rules. - Data repair is performed through controlled tools/commands and evidence, not undocument

### Module SPEC-DATA-006 — Temporal Durable Workflow Orchestration Architecture (Document 74)

**Objective:** Define how Temporal coordinates long-running batch/QMS/regulatory/integration workflows without becoming the regulatory system of record, including deterministic workflow code, idempotent Activities, timers, compensation and upgrade/replay behavior.

- **Authoritative store:** Temporal (orchestration only — NOT regulatory truth)
- **Code location:** `infrastructure`
- **Requirements:** TMP-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 8
- **Data entities:** 0 | **APIs:** 0 | **Events:** 5 | **UI surfaces:** 5 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success. - Recovery must preserve idempotency and version/concurrency rules. - Data repair is performed through controlled tools/commands and evidence, not undocument

### Module SPEC-DATA-007 — Caching, Search, Read Models, Reporting Projections & Analytics Data Access (Document 75)

**Objective:** Define Redis/cache, search indexing, read models, materialized reporting projections and optional analytics exports as rebuildable performance layers with explicit freshness and authorization.

- **Authoritative store:** Redis / search / read models (rebuildable, NON-AUTHORITATIVE)
- **Code location:** `infrastructure`
- **Requirements:** READ-FR-001..030 (30)
- **Functionalities (requirement rows):** 30
- **Function/service contracts in source:** 8
- **Data entities:** 2 | **APIs:** 4 | **Events:** 6 | **UI surfaces:** 6 | **Test scenarios:** 7
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success. - Recovery must preserve idempotency and version/concurrency rules. - Data repair is performed through controlled tools/commands and evidence, not undocument

### Module SPEC-DATA-008 — Backup, Restore, Point-in-Time Recovery & Disaster Recovery (Document 76)

**Objective:** Define component-specific backup, PITR, restore, failover, disaster recovery and validation so regulated data and evidence can be demonstrably recovered within agreed objectives.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `infrastructure`
- **Requirements:** DR-FR-001..032 (32)
- **Functionalities (requirement rows):** 32
- **Function/service contracts in source:** 8
- **Data entities:** 3 | **APIs:** 3 | **Events:** 6 | **UI surfaces:** 6 | **Test scenarios:** 16
- **Regulated markers:** signature=False, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** **Specification ID:** SPEC-DATA-008 **Parent Documents:** Documents 01–68 **Primary Dependencies:** Documents 05–06, 65, 69–75; Security Incident Response **Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze **Target Market:** United States **Primary Profiles:** DDCP

### Module SPEC-DATA-009 — Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture (Document 77)

**Objective:** Define reproducible production deployment architecture and lifecycle across cloud and on-prem environments, including Kubernetes/runtime topology, stateful service choices, IaC, probes, scaling, installation qualification, upgrades and rollback.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `infrastructure`
- **Requirements:** DEP-FR-001..035 (35)
- **Functionalities (requirement rows):** 35
- **Function/service contracts in source:** 8
- **Data entities:** 1 | **APIs:** 0 | **Events:** 7 | **UI surfaces:** 7 | **Test scenarios:** 9
- **Regulated markers:** signature=False, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: informational/record-keeping
- **Failure behaviour (source):** - A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success. - Recovery must preserve idempotency and version/concurrency rules. - Data repair is performed through controlled tools/commands and evidence, not undocument

### Module SPEC-DATA-010 — Performance, Capacity, Observability, SLOs & SRE Operations (Document 78)

**Objective:** Define measurable scale, performance, capacity, observability, graceful degradation and operational reliability targets so the platform can support enterprise plants without discovering architecture limits during customer deployment.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `infrastructure`
- **Requirements:** SRE-FR-001..036 (36)
- **Functionalities (requirement rows):** 36
- **Function/service contracts in source:** 9
- **Data entities:** 2 | **APIs:** 0 | **Events:** 7 | **UI surfaces:** 10 | **Test scenarios:** 11
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: calculation
- **Failure behaviour (source):** - A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success. - Recovery must preserve idempotency and version/concurrency rules. - Data repair is performed through controlled tools/commands and evidence, not undocument


---

## WP-12 — Validation Platform & Evidence

**Depends on:** WP-01, WP-11  
**Scope summary:** VMP/CSA, intended use & risk, traceability, test strategy, IQ/OQ, infrastructure/Part11/data-integrity/interface/DR/security/performance qualification, exceptions, periodic review.  
**Source documents:** 79, 80, 81, 82, 83, 84, 86, 88, 89, 90, 91, 92, 93, 94, 96

### Module SPEC-VAL-001 — Validation Master Plan & Computer Software Assurance Strategy (Document 79)

**Objective:** Define the master validation/CSA strategy, deliverables, responsibilities, assurance rigor, release gates and lifecycle required to validate the eBMR/eDHR platform for intended regulated use.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** VAL-FR-001..028 (28)
- **Functionalities (requirement rows):** 28
- **Function/service contracts in source:** 6
- **Data entities:** 3 | **APIs:** 4 | **Events:** 4 | **UI surfaces:** 5 | **Test scenarios:** 5
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-002 — Intended Use, GxP Criticality & Software Function Risk Classification (Document 80)

**Objective:** Define function-level intended use and risk classification that drives validation scope and assurance rigor under FDA's 2026 CSA approach while independently preserving Part 11 and drug CGMP controls.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** RISK-FR-001..022 (22)
- **Functionalities (requirement rows):** 22
- **Function/service contracts in source:** 5
- **Data entities:** 2 | **APIs:** 4 | **Events:** 5 | **UI surfaces:** 5 | **Test scenarios:** 6
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-003 — Requirements, Design Inputs & Validation Traceability Management (Document 81)

**Objective:** Define the authoritative requirement and traceability graph linking source specifications, risks, functions, APIs, schemas, tests, failures and release baselines.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** REQ-FR-001..023 (23)
- **Functionalities (requirement rows):** 23
- **Function/service contracts in source:** 6
- **Data entities:** 3 | **APIs:** 5 | **Events:** 4 | **UI surfaces:** 6 | **Test scenarios:** 5
- **Regulated markers:** signature=True, release=True, audit=False, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-004 — Validation Test Strategy, Test Methods & Objective Evidence Governance (Document 82)

**Objective:** **Specification ID:** SPEC-VAL-004  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 79–81; CI/CD; Evidence Store  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** TST-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 7
- **Data entities:** 2 | **APIs:** 5 | **Events:** 5 | **UI surfaces:** 6 | **Test scenarios:** 6
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-005 — Installation Qualification (IQ) & Installed Baseline Verification (Document 83)

**Objective:** Define installation qualification proving the correct approved platform release, infrastructure components and prerequisites are installed before functional qualification.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** IQ-FR-001..021 (21)
- **Functionalities (requirement rows):** 21
- **Function/service contracts in source:** 6
- **Data entities:** 2 | **APIs:** 4 | **Events:** 4 | **UI surfaces:** 5 | **Test scenarios:** 7
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: informational/record-keeping
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-006 — Operational Qualification (OQ) & Functional Control Verification (Document 84)

**Objective:** Define functional qualification of the configured platform in an IQ-approved environment, emphasizing higher-risk GxP controls, negative paths, calculations and concurrency.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** OQ-FR-001..018 (18)
- **Functionalities (requirement rows):** 18
- **Function/service contracts in source:** 4
- **Data entities:** 2 | **APIs:** 4 | **Events:** 4 | **UI surfaces:** 5 | **Test scenarios:** 7
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: calculation
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-008 — Infrastructure, Cloud, Platform & Environment Qualification (Document 86)

**Objective:** Define risk-based qualification of the technical environment including managed services, Kubernetes, databases, storage, messaging, orchestration, network, secrets, time, monitoring and drift.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** INFQ-FR-001..020 (20)
- **Functionalities (requirement rows):** 20
- **Function/service contracts in source:** 5
- **Data entities:** 2 | **APIs:** 4 | **Events:** 3 | **UI surfaces:** 5 | **Test scenarios:** 7
- **Regulated markers:** signature=False, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: informational/record-keeping
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-010 — 21 CFR Part 11 Electronic Records & Electronic Signature Validation (Document 88)

**Objective:** Define explicit validation of Part 11 electronic-record and electronic-signature controls, including scope, copies, retention, access, audit, sequencing, authority/device checks and signature manifestation/linking.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** P11-FR-001..026 (26)
- **Functionalities (requirement rows):** 26
- **Function/service contracts in source:** 6
- **Data entities:** 2 | **APIs:** 3 | **Events:** 3 | **UI surfaces:** 6 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-011 — Audit Trail, Record Version Vault & Data Integrity Validation (Document 89)

**Objective:** Validate audit, immutable versions, evidence lineage, correction, hashes, archival and data-integrity controls—including deliberate tamper scenarios.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** DIV-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 6
- **Data entities:** 2 | **APIs:** 3 | **Events:** 4 | **UI surfaces:** 6 | **Test scenarios:** 7
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-012 — Integration, Edge, Device, Peripheral & Interface Validation (Document 90)

**Objective:** Define validation of enterprise integrations, industrial Edge/protocol connections and peripherals including mapping, source identity, offline behavior, retry/idempotency and reconciliation.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** IFV-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 5
- **Data entities:** 2 | **APIs:** 4 | **Events:** 4 | **UI surfaces:** 6 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=False, audit=False, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: calculation
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-013 — Backup, Restore, PITR & Disaster Recovery Qualification (Document 91)

**Objective:** Define objective qualification of backups and disaster recovery by executing actual restores, PITR/failover scenarios, measuring RPO/RTO and validating GxP/evidence integrity.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** DRV-FR-001..022 (22)
- **Functionalities (requirement rows):** 22
- **Function/service contracts in source:** 5
- **Data entities:** 2 | **APIs:** 4 | **Events:** 4 | **UI surfaces:** 5 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=False, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement
- **Failure behaviour (source):** **Specification ID:** SPEC-VAL-013 **Parent Documents:** Documents 01–78 **Primary Dependencies:** Documents 65, 72–77, 82–90 **Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze **Target Market:** United States **Primary Profiles:** DDCP V1; Medical Device V2; Pharm

### Module SPEC-VAL-014 — Security Qualification, Vulnerability Verification & Penetration Testing (Document 92)

**Objective:** Define release/deployment security qualification and penetration-testing evidence verifying threat-model controls and closing material security findings before regulated use.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** SECQ-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 5
- **Data entities:** 2 | **APIs:** 5 | **Events:** 4 | **UI surfaces:** 5 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=False, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-015 — Performance, Load, Capacity & Reliability Qualification (Document 93)

**Objective:** Define qualification of the operating envelope under realistic enterprise load, including latency, throughput, audit/event volume, Edge catch-up, soak, failover and headroom.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** PERFQ-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 5
- **Data entities:** 2 | **APIs:** 4 | **Events:** 4 | **UI surfaces:** 6 | **Test scenarios:** 8
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: informational/record-keeping
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-016 — Validation Defect, Deviation, Test Exception & Remediation Management (Document 94)

**Objective:** Define controlled lifecycle for validation failures, protocol/environment deviations, software defects, retest and risk disposition so failed evidence remains visible and release decisions are defensible.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** VEX-FR-001..022 (22)
- **Functionalities (requirement rows):** 22
- **Function/service contracts in source:** 6
- **Data entities:** 1 | **APIs:** 5 | **Events:** 4 | **UI surfaces:** 7 | **Test scenarios:** 5
- **Regulated markers:** signature=False, release=True, audit=True, calculation=False, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-018 — Periodic Review, Change Impact, Revalidation & Validated-State Maintenance (Document 96)

**Objective:** Define ongoing maintenance of validated state through change impact, risk-based revalidation, periodic review, drift/security/DR/performance assessment and controlled decommissioning.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** VSM-FR-001..028 (28)
- **Functionalities (requirement rows):** 28
- **Function/service contracts in source:** 6
- **Data entities:** 3 | **APIs:** 6 | **Events:** 6 | **UI surfaces:** 7 | **Test scenarios:** 7
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: informational/record-keeping
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall


---

## WP-13 — AI Advisory Capabilities

**Depends on:** WP-01, WP-10, WP-12  
**Scope summary:** Advisory-only AI use cases under Document 105 governance; no autonomous regulated authority.  
**Source documents:** 105

### Module SPEC-AI-001 — AI Governance for Regulated Manufacturing (Document 105)

**Objective:** Define safe, traceable and validation-ready use of AI in the product and development lifecycle, preserving human regulatory authority, data protection, model/prompt/tool governance, evaluation and provider portability.

- **Authoritative store:** n/a (standard / governance document)
- **Code location:** `services/ai-gateway`
- **Requirements:** AI-FR-001..056 (56)
- **Functionalities (requirement rows):** 56
- **Function/service contracts in source:** 13
- **Data entities:** 0 | **APIs:** 0 | **Events:** 0 | **UI surfaces:** 0 | **Test scenarios:** 9
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** | Failure | Required behavior | |---|---| | provider unavailable | explicit AI unavailable; core GxP remains usable | | timeout | no guessed result; retry only by use-case policy | | invalid JSON/schema | reject output; optionally bounded retry | | source unavailable/stale | state insufficient/stale


---

## WP-14 — Customer Deployment / PQ / Go-Live

**Depends on:** WP-12  
**Scope summary:** PQ/UAT, data migration/cutover/reconciliation validation, VSR and validated release authorization.  
**Source documents:** 85, 87, 95

### Module SPEC-VAL-007 — Performance Qualification (PQ), UAT & Business Process Verification (Document 85)

**Objective:** Define customer/site-specific end-to-end qualification demonstrating trained users can execute intended regulated processes using the released configuration and interfaces.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** PQ-FR-001..020 (20)
- **Functionalities (requirement rows):** 20
- **Function/service contracts in source:** 5
- **Data entities:** 2 | **APIs:** 4 | **Events:** 4 | **UI surfaces:** 5 | **Test scenarios:** 7
- **Regulated markers:** signature=True, release=True, audit=False, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-009 — Data Migration, Conversion, Cutover & Reconciliation Validation (Document 87)

**Objective:** Define validated migration of legacy GxP/master/record/evidence data with source snapshots, controlled transformations, identity/provenance preservation, reconciliation and cutover.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** MIGV-FR-001..022 (22)
- **Functionalities (requirement rows):** 22
- **Function/service contracts in source:** 6
- **Data entities:** 3 | **APIs:** 4 | **Events:** 4 | **UI surfaces:** 6 | **Test scenarios:** 7
- **Regulated markers:** signature=True, release=True, audit=True, calculation=True, integration=False
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall

### Module SPEC-VAL-017 — Validation Summary Report, Release-to-Production & Go-Live Authorization (Document 95)

**Objective:** Define the final validation summary and technical/Quality release gate binding objective evidence to the exact software/configuration/environment promoted into regulated production.

- **Authoritative store:** PostgreSQL (GxP Core, authoritative)
- **Code location:** `validation`
- **Requirements:** VSR-FR-001..024 (24)
- **Functionalities (requirement rows):** 24
- **Function/service contracts in source:** 6
- **Data entities:** 2 | **APIs:** 5 | **Events:** 6 | **UI surfaces:** 5 | **Test scenarios:** 6
- **Regulated markers:** signature=True, release=True, audit=True, calculation=False, integration=True
- **Provisional GxP risk (Doc 80 method):** HIGHER_PROCESS_RISK (PROPOSED) — automation role: enforcement + automated gating
- **Failure behaviour (source):** - Failed or interrupted validation execution remains recorded. - Re-run creates a new execution linked to prior execution/deviation. - Evidence-upload or DB failure must not produce PASS. - Stale requirement/design/test versions cannot be approved. - Signature failure blocks release rather than fall
