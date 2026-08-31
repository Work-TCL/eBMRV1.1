# US eBMR / eDHR Regulated Manufacturing Platform
## Document 09 — Product, Constituent & Regulatory Profile Master — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EBMR-000  
**Parent Documents:** Document 01 v1.1; Document 02 v1.0  
**Primary Dependencies:** Documents 03–08; DDCP profile specs; Material/QC/Packaging specs  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products (DDCP)  
**Future Profiles:** Medical Devices, Pharmaceuticals  
**Date:** 2026-08-20

---


# Implementation Standard Applied to This Document

This specification is intended to be sufficient for Codex, Claude Code, or a human development team to implement the module with minimal interpretation.

Where applicable, the document therefore defines:

- objective and scope;
- non-goals/exclusions;
- actors/roles;
- functionality and sub-functionality;
- workflows and state machines;
- business rules;
- authorization and segregation of duties;
- electronic-signature behavior;
- audit behavior;
- entities, fields, relationships and ownership;
- PostgreSQL/Frappe storage boundaries;
- suggested tables, indexes and constraints;
- APIs and stable error codes;
- events/outbox contracts;
- UI screens/actions;
- integrations;
- calculations/validations;
- concurrency/idempotency;
- failure/recovery behavior;
- configuration;
- observability;
- retention/archival;
- migrations;
- performance/scaling;
- repository/module structure;
- implementation sequence;
- test cases;
- acceptance criteria;
- requirement traceability;
- explicit coding-agent rules.

If a future implementation decision changes regulated behavior and is not defined here, the coding agent shall raise a specification gap rather than inventing behavior.


# 1. Objective

Define the canonical regulated master for products, drug/device constituents, DDCP compatibility, manufacturing profiles, site applicability and product-level regulatory configuration.

The module must prevent a customer from treating “product” as a loose Frappe Item. A product used for regulated execution is a versioned domain object released through the GxP Vault.

# 2. Scope

Included:
- product identity/version;
- constituent identity and relationship;
- DDCP configuration;
- manufacturing profile;
- lot/serial strategy;
- UDI applicability;
- sterile applicability;
- site admission;
- quality/packaging/specification references;
- compatibility version;
- release/effective dating;
- integration IDs.

Excluded:
- detailed recipe steps → Document 10;
- batch execution → Document 11;
- detailed UDI/label execution → Document 16;
- detailed material master → Documents 18–22;
- full regulatory-submission management.

# 3. Actors

- Product Master Author
- Regulatory/Quality Reviewer
- Product Approver
- QA Master Data Administrator
- Manufacturing Engineer
- Packaging/Label Administrator
- Read-only Auditor
- Integration Service

# 4. Architecture Boundary

```text
Frappe Product Authoring UI
        ↓
Draft Product/Constituent Objects
        ↓
Completeness + Profile Validation
        ↓
Approval / E-Signature
        ↓
GxP Vault Product Version
        ↓
ProductReleased Event
        ↓
Recipe / QC / Packaging / ERP projections
```

Frappe is the authoring experience. The released product version is authoritative in the GxP Vault.

# 5. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| PRD-FR-001 | Product master | Create controlled product identity with immutable internal ID, business code, marketed/internal names, lifecycle state, product family, dosage/device form, strength/configuration, manufacturing profile, and site applicability. | Product can be uniquely referenced across recipes, batches, QC, genealogy and release. |
| PRD-FR-002 | Product lifecycle | Support Draft, Under Review, Approved/Released, Effective, Suspended, Obsolete, Superseded. Released product versions are immutable. | Obsolete/suspended product cannot start new production unless controlled exception policy permits. |
| PRD-FR-003 | Product version | Product changes create a new version with effective dating and Vault release; historical batches remain linked to prior version. | No silent historical drift. |
| PRD-FR-004 | Constituent model | A DDCP product may contain Drug, Device, Biologic, HCT/P or Other constituent types; V1 actively supports Drug + Device and structurally supports later profiles. | Combination product is not represented as two unrelated masters. |
| PRD-FR-005 | Constituent role | Record primary/secondary constituent role, manufacturer/site source, business identity, exact version, lot/serial strategy and regulated handoff requirements. | Cross-constituent evidence can be validated. |
| PRD-FR-006 | Combination-product type | Support Single Entity, Co-Packaged and Cross-Labeled/Other relationship metadata as controlled product attributes; exact regulatory applicability remains customer/regulatory decision. | Workflow can distinguish product relationship type. |
| PRD-FR-007 | PMOA metadata | Store customer-approved PMOA/lead-center/regulatory-context reference without software deciding PMOA. | Product does not infer regulatory classification. |
| PRD-FR-008 | Part 4 operating-system profile | Store customer-approved compliance approach/profile reference and applicable supplementary control set. | Release/rules can select applicable profile. |
| PRD-FR-009 | Manufacturing profile | Assign one or more controlled manufacturing profiles: Injectable DDCP, Inhalation DDCP, Drug-Eluting/Coated Device, Device, Pharma, future extensions. | Recipe authoring can inherit valid process capabilities. |
| PRD-FR-010 | Sterile/aseptic applicability | Flag whether sterile/aseptic controls apply and reference released sterile-process profile rather than free-text setting. | Sterile-required product cannot use non-sterile recipe path. |
| PRD-FR-011 | Lot/serial strategy | Configure finished lot, device lot, unit serial, combination-product serial, or hybrid genealogy strategy. | Execution creates required identifiers. |
| PRD-FR-012 | UDI applicability | Configure UDI requirement, issuing-agency metadata, DI rules, production-identifier sources and packaging-level requirements where applicable. | Device/combination records support UDI capture. |
| PRD-FR-013 | Drug batch identity strategy | Configure drug batch/lot identification and whether final product shares or differs from drug-constituent batch identity. | Genealogy remains explicit. |
| PRD-FR-014 | Strength/concentration | Represent drug strength/concentration using structured quantity + UOM and product-specific calculation metadata. | No free-text-only strength. |
| PRD-FR-015 | Device configuration | Represent device model/configuration/version and compatible drug constituent constraints. | Wrong device configuration cannot be paired. |
| PRD-FR-016 | Constituent compatibility | Release controlled compatibility versions specifying allowed exact drug/device constituent combinations and critical interface constraints. | Final DDCP issue checks compatibility. |
| PRD-FR-017 | Packaging configuration | Reference released packaging hierarchy/configuration and label profile by product/version. | Packaging module uses exact approved configuration. |
| PRD-FR-018 | Shelf-life/expiration profile | Reference released expiration/stability policy; product master does not hard-code computed expiration logic. | Expiration is rule/profile driven. |
| PRD-FR-019 | Storage conditions | Reference structured storage/environment requirements and acceptable ranges. | Warehouse and batch rules can evaluate conditions. |
| PRD-FR-020 | Material/BOM relationship | Reference approved material/component structures; material specification versions remain separate controlled objects. | Product version does not duplicate mutable material specs. |
| PRD-FR-021 | Quality specification links | Reference released finished/in-process/device test specifications and sampling profiles. | QC receives correct requirements. |
| PRD-FR-022 | Equipment/process class requirements | Reference allowed equipment/process classes and special validation requirements. | Recipe validation checks compatibility. |
| PRD-FR-023 | Site admission | Product version has approved manufacturing/packaging/release sites and optional contract-manufacturing relationships. | Unauthorized site cannot issue batch. |
| PRD-FR-024 | Regulatory attribute provenance | Critical regulatory profile fields store source/decision reference, approver and effective version. | Audit can show basis of configuration. |
| PRD-FR-025 | Product change impact | Changing regulated product attributes triggers impact assessment for recipes, specs, labels, QC, validation, inventory, open batches and genealogy. | Downstream affected objects identified. |
| PRD-FR-026 | Clone/template creation | Allow draft clone from approved family/template, but cloned product receives new identity and requires full review/release. | No inherited approval. |
| PRD-FR-027 | Search/filter | Search by code, name, constituent type, manufacturing profile, site, lifecycle, UDI DI, device model, strength. | Operational usability. |
| PRD-FR-028 | API/integration mapping | Maintain external-system IDs for ERP/LIMS/label systems without using external ID as internal primary key. | ERP mappings do not contaminate domain identity. |
| PRD-FR-029 | Product suspension | Quality may suspend future issue with reason/signature while preserving active/in-process batch policy separately. | Suspension does not rewrite past batches. |
| PRD-FR-030 | Inspection export | Produce human-readable product/profile/version report with constituents, applicability, approved sites, labels/spec references and release signatures. | Controlled master can be reviewed externally. |
| PRD-FR-031 | Configuration completeness | Before product release, validate mandatory attributes based on active manufacturing/regulatory profile. | Incomplete DDCP cannot release. |
| PRD-FR-032 | Profile admission gate | Unsupported specialist context (e.g. biologic-specific or unsupported implantable/connected-device profile) fails closed unless corresponding profile package is approved. | Configuration cannot enable unsupported scope. |

# 6. Product State Machine

```text
DRAFT
  ↓ submit
UNDER_REVIEW
  ├─→ DRAFT (rework)
  ↓ approve + sign
RELEASED
  ↓ effective date reached
EFFECTIVE
  ├─→ SUSPENDED
  ├─→ SUPERSEDED
  └─→ OBSOLETE

SUSPENDED
  ├─→ EFFECTIVE (controlled reinstatement)
  └─→ OBSOLETE
```

No new batch may be issued from `DRAFT`, `UNDER_REVIEW`, `SUSPENDED`, `SUPERSEDED` or `OBSOLETE` product versions unless a specific validated exception path exists.

# 7. Core Data Model

## 7.1 `product_family`

```text
id uuid PK
tenant_id uuid
family_code varchar(80)
name varchar(255)
profile_code varchar(80)
status varchar(40)
```

## 7.2 `product_version`

```text
id uuid PK
tenant_id uuid NOT NULL
product_business_id varchar(120) NOT NULL
version_no bigint NOT NULL
product_code varchar(120) NOT NULL
name varchar(255) NOT NULL
product_family_id uuid
lifecycle_state varchar(40) NOT NULL
manufacturing_profile_code varchar(80) NOT NULL
combination_product_type varchar(40)
pmoa_reference varchar(255)
part4_profile_code varchar(80)
sterile_profile_id uuid
finished_tracking_strategy varchar(40)
udi_applicable boolean
strength_value numeric(24,8)
strength_uom varchar(40)
device_model_code varchar(120)
effective_from timestamptz
effective_to timestamptz
released_vault_object_id uuid
version_hash char(64)
created_at timestamptz
```

Unique:
- `(tenant_id, product_business_id, version_no)`
- `(tenant_id, product_code, version_no)`

## 7.3 `product_constituent`

```text
id uuid PK
product_version_id uuid NOT NULL
constituent_type varchar(40) NOT NULL
role_code varchar(40)
constituent_business_id varchar(120) NOT NULL
constituent_version_id uuid NOT NULL
source_site_id uuid
tracking_strategy varchar(40)
sequence_no int
```

## 7.4 `constituent_compatibility_version`

```text
id uuid PK
tenant_id uuid
compatibility_code varchar(120)
version_no bigint
drug_constituent_version_id uuid
device_constituent_version_id uuid
interface_constraints jsonb
status varchar(40)
effective_from timestamptz
effective_to timestamptz
vault_object_id uuid
```

## 7.5 `product_site_admission`
- product_version_id
- site_id
- operations allowed: manufacture/assemble/package/test/release
- effective dates
- status
- approval reference

## 7.6 `product_external_mapping`
- system_type
- system_instance_id
- product_version/business ID
- external_id
- mapping status/version

# 8. Relationship Model

```text
Product Family
   └── Product Version
       ├── Constituent Version(s)
       ├── Compatibility Version
       ├── Manufacturing Profile
       ├── Site Admissions
       ├── Released Specifications
       ├── Packaging Configuration
       ├── Label Profile
       ├── QC Profile
       ├── Sterile Profile
       └── Recipe Families
```

# 9. APIs

- `POST /products/v1/drafts`
- `PUT /products/v1/drafts/{id}`
- `POST /products/v1/drafts/{id}/submit`
- `POST /products/v1/drafts/{id}/release` → Mutation Gateway + signatures
- `POST /products/v1/{id}/suspend`
- `POST /products/v1/{id}/reinstate`
- `GET /products/v1/{businessId}/versions`
- `GET /products/v1/{id}`
- `POST /products/v1/{id}/validate-completeness`
- `GET /products/v1/{id}/compatibility`
- `GET /products/v1/{id}/issue-eligibility?site=...`

Stable errors:
`PRODUCT_PROFILE_INCOMPLETE`, `SITE_NOT_ADMITTED`, `UNSUPPORTED_PROFILE`, `CONSTITUENT_MISSING`, `CONSTITUENT_INCOMPATIBLE`, `PRODUCT_NOT_EFFECTIVE`, `PRODUCT_SUSPENDED`, `UDI_PROFILE_INCOMPLETE`.

# 10. Events

- `ProductDraftSubmitted`
- `ProductVersionReleased`
- `ProductVersionEffective`
- `ProductVersionSuspended`
- `ProductVersionReinstated`
- `ProductVersionSuperseded`
- `ConstituentCompatibilityReleased`
- `ProductSiteAdmissionChanged`

# 11. UI Screens

1. Product Catalogue
2. Product Version Editor
3. Constituent Builder
4. DDCP Compatibility Matrix
5. Regulatory/Manufacturing Profile
6. Site Admission
7. Specifications & Packaging Links
8. Release Readiness Checklist
9. Version Comparison
10. Product Audit / History

# 12. Authorization / Signature

- Authors can draft but not necessarily release.
- Release requires configured independent reviewer/approver.
- Suspension/reinstatement requires QA authority and e-signature where Part 11 applies.
- Regulatory profile changes require stronger approval than display-only metadata.

# 13. Audit

Audit:
- create/edit controlled draft;
- submit;
- review decisions;
- release;
- effective status;
- suspension/reinstatement;
- constituent change;
- compatibility change;
- external mapping changes if they influence GxP execution.

# 14. Frappe Implementation

Recommended Frappe DocTypes:
- Product Draft
- Product Constituent Draft
- Product Site Admission Draft
- Product External Mapping
- Product Release Projection

Released product truth must be read from GxP API/projection, not mutable Frappe draft.

# 15. Repository Structure

```text
apps/ebmr_frappe/ebmr/product/
services/gxp-api/src/modules/product/
contracts/openapi/product.yaml
contracts/events/product/
validation/requirements/product/
```

# 16. Implementation Sequence

1. product family/draft;
2. constituent model;
3. profile completeness rules;
4. site admission;
5. compatibility version;
6. release to Vault;
7. projections;
8. external mapping;
9. suspension/reinstatement;
10. audit/export.

# 17. Test Catalogue

- basic drug+device product release;
- missing constituent;
- incompatible constituents;
- future effective date;
- suspended product;
- wrong manufacturing site;
- clone does not inherit approval;
- product change creates version;
- old batch resolves old product version;
- UDI-required profile incomplete;
- sterile-required profile missing;
- concurrent product update;
- external mapping duplicate;
- unauthorized release;
- release signature stale after draft change;
- export/version comparison.

# 18. Acceptance Criteria

Module is build-ready when:
- product/constituent schemas are frozen;
- DDCP compatibility model supports injectable reference profile;
- site admission and product issue-eligibility are tested;
- Vault integration is proven;
- no batch can issue against mutable Frappe product draft.

# 19. Codex / Claude Code Rules

Never model DDCP merely as two independent Frappe Items.
Never let external ERP item ID become product primary key.
Never allow recipe/batch to reference “latest” product version.
Never infer PMOA or legal regulatory classification.
Never allow unsupported profile flags to bypass admission gates.

# Regulatory Engineering Basis

This specification is an engineering baseline, not legal advice and not a declaration that the software or a customer configuration is automatically compliant.

Relevant current U.S. regulatory sources include:

- 21 CFR Part 4 — combination-product CGMP framework;
- 21 CFR Part 11 — electronic records/electronic signatures when applicable;
- 21 CFR Parts 210/211 — drug CGMP;
- 21 CFR §211.186 — Master production and control records;
- 21 CFR §211.188 — Batch production and control records;
- 21 CFR §211.103 — Calculation of yield;
- 21 CFR Part 211 Subpart G — Packaging and labeling control;
- 21 CFR Part 820 — QMSR, effective February 2, 2026;
- 21 CFR §820.10 — requirements for a quality management system;
- 21 CFR §820.35 — control of records, including UDI-related records;
- 21 CFR §820.45 — device labeling and packaging controls;
- applicable UDI requirements under 21 CFR Part 830.

The current QMSR incorporates ISO 13485:2016 by reference. This document summarizes engineering implications and does not reproduce copyrighted ISO text.

Reference URLs:
- https://www.law.cornell.edu/cfr/text/21/4.4
- https://www.law.cornell.edu/cfr/text/21/211.186
- https://www.law.cornell.edu/cfr/text/21/211.188
- https://www.law.cornell.edu/cfr/text/21/211.103
- https://www.law.cornell.edu/cfr/text/21/part-211/subpart-G
- https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr
- https://www.law.cornell.edu/cfr/text/21/820.10
- https://www.law.cornell.edu/cfr/text/21/820.35
- https://www.law.cornell.edu/cfr/text/21/820.45
