# US eBMR / eDHR Regulated Manufacturing Platform
## Document 10 — Master Recipe / Master Manufacturing Record Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EBMR-001  
**Parent Documents:** Document 01 v1.1; Document 02 v1.0  
**Primary Dependencies:** Documents 03–09; Rules Engine; Vault; Materials/QC/Equipment/Packaging specs  
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

Define how manufacturing instructions are authored, reviewed, released, frozen, versioned and converted into an executable batch/device production snapshot.

For drug and DDCP profiles, this module provides the architecture to support controlled master production/control record content and complete executable instructions. For device profiles it provides the released manufacturing specification/work instructions used to create production history.

# 2. Non-Goals

- No arbitrary user-written scripts in recipe.
- No dynamic “latest spec/rule” lookup after batch issue.
- No recipe release directly from Frappe workflow without GxP Vault/signature.
- No full process simulation/digital twin in V1.

# 3. Actors

- Manufacturing Engineer / Recipe Author
- Process SME
- Production Reviewer
- QA Reviewer/Approver
- QC Reviewer
- Packaging/Label Reviewer
- Regulatory/Quality Reviewer
- Read-only Auditor

# 4. Architecture

```text
Frappe Recipe Authoring
   ↓
Draft Graph + Materials + Parameters + Rules
   ↓
Completeness/Graph/Profile Validation
   ↓
Independent Review + E-Signatures
   ↓
GxP Vault Released Recipe Version
   ↓
Effective Date
   ↓
Batch Issue
   ↓
Immutable Execution Snapshot
```

# 5. Functional Requirements

| ID | Functionality | Sub-functional behavior | Acceptance intent |
|---|---|---|---|
| RCP-FR-001 | Recipe family | Create recipe/MMR family under exact product version/profile and manufacturing site scope. | Recipe has clear governing product. |
| RCP-FR-002 | Recipe version lifecycle | Draft, review, approved/released, effective, superseded, obsolete, suspended. Released version immutable. | Production only uses eligible release. |
| RCP-FR-003 | Batch-size variants | Support controlled batch-size variants and scaling policy; drug profile may require distinct master records by batch size as applicable. | Scaling is never an uncontrolled multiplier. |
| RCP-FR-004 | Structured sections | Recipe contains ordered sections/stages with purpose, area, expected duration and dependencies. | No single free-text blob. |
| RCP-FR-005 | Step definition | Each step has stable step ID, instruction, type, sequence/dependencies, performer role, inputs, outputs, validations and completion criteria. | Executable semantics explicit. |
| RCP-FR-006 | Step types | Support Instruction, Data Entry, Scan, Weigh, Equipment Check, Calculation, IPC/QC, Signature, Verification, Timer, Hold Point, Material Consume, Assembly, Test, Packaging, Custom Approved Type. | Common engine reusable. |
| RCP-FR-007 | Dependencies | Directed dependency graph supports sequential, parallel and join behavior without cycles unless an explicitly modelled repeat/rework structure is used. | Graph validates before release. |
| RCP-FR-008 | Conditional branches | Released rule determines branch based on structured result; operator cannot choose hidden uncontrolled path. | Branch reason auditable. |
| RCP-FR-009 | Material requirements | Each requirement references material/component specification, target quantity/formula, tolerance, stage and alternative-policy reference. | Wrong material blocked. |
| RCP-FR-010 | Equipment requirements | Step references equipment class/asset eligibility, qualification/calibration/cleaning status and optional redundancy. | Equipment checks enforceable. |
| RCP-FR-011 | Personnel requirements | Step references roles, training and qualifications including independent verifier where required. | Execution gating possible. |
| RCP-FR-012 | Area/environment requirement | Step references permitted site/area/room/line and environmental/sterile profile. | Execution location constrained. |
| RCP-FR-013 | Parameter definition | Structured parameter includes code, label, type, UOM, source, target/limits, precision, mandatory flag and rule references. | Data capture validated. |
| RCP-FR-014 | Source type | Parameter source can be Manual, Device/Edge, Calculated, LIMS, ERP, Imported Evidence or System; allowed fallback explicitly configured. | Manual substitution cannot occur silently. |
| RCP-FR-015 | Manual fallback policy | If automated source unavailable, rule defines whether manual entry is prohibited or allowed with reason, qualification and verification/signature. | Fallback controlled. |
| RCP-FR-016 | Calculation reference | Recipe references released calculation/rule version from Document 08. | No embedded arbitrary formula. |
| RCP-FR-017 | IPC/QC point | Step can create required sample/test orders, acceptance criteria and continuation/release hold. | QC integrated. |
| RCP-FR-018 | Timer/hold time | Step may start, pause or stop controlled timer with max/min duration and exception behavior. | Time limits enforced. |
| RCP-FR-019 | Electronic-signature requirement | Recipe specifies signature policy by step/action without embedding authentication mechanics. | Document 04 reused. |
| RCP-FR-020 | Independent verification | Step supports performer/verifier and history-aware SoD. | Independent check enforced. |
| RCP-FR-021 | Attachment/evidence requirement | Step can require photo, instrument file, document, certificate or machine evidence with type constraints. | Evidence completeness testable. |
| RCP-FR-022 | Instruction version integrity | Instruction shown at execution comes from exact issued recipe snapshot. | Later edits cannot change open batch. |
| RCP-FR-023 | Line clearance/cleaning | Recipe may require prerequisite line-clearance/cleaning evidence before stage start. | Packaging/sterile controls integrated. |
| RCP-FR-024 | Sterile-specific step metadata | For applicable profile, support intervention classification, sterile component status, filter/cycle references, hold times and environmental dependencies. | Aseptic profile extensible. |
| RCP-FR-025 | Device assembly metadata | Support component lot/serial inputs, assembly relationship, device test result and unit/lot scope. | eDHR reuse. |
| RCP-FR-026 | Packaging/label step | Reference packaging/label configuration and issuance/reconciliation requirements. | Document 16 integration. |
| RCP-FR-027 | Expected yield points | Declare manufacturing phases at which yield/reconciliation calculation is required. | Document 17 integration. |
| RCP-FR-028 | Exception policy | Each step defines what happens on out-of-limit, missing evidence, timeout, failed device read or ineligible resource: block, hold, deviation, retry under rule. | No ad hoc operator decision. |
| RCP-FR-029 | Rework/reprocess route | Approved alternative route is modelled as separate released route/profile; cannot be improvised during batch execution. | Controlled rework. |
| RCP-FR-030 | Recipe completeness validator | Before release, validate graph, dependencies, missing specs, rules, signature policies, unsupported step types, unused references and profile-specific requirements. | Invalid recipe cannot release. |
| RCP-FR-031 | Independent master review | Release policy supports author + independent checker/approver; signatures bind exact canonical recipe version. | 211.186-style master control support. |
| RCP-FR-032 | Effective date and site | Recipe validity depends on product/site/effective date and released dependencies. | Issue eligibility deterministic. |
| RCP-FR-033 | Change impact | Changing released recipe creates new version and evaluates open batches, materials, labels, validation and training impact. | Existing batch unaffected unless controlled change path. |
| RCP-FR-034 | Recipe compare | Provide semantic version comparison: instructions, steps, limits, materials, equipment, rules, signatures, branches. | Reviewer can see critical change. |
| RCP-FR-035 | Simulation | Non-production simulation validates graph/rules/inputs without creating regulated batch. | Authoring quality improved. |
| RCP-FR-036 | Template reuse | Reusable step/section templates may be inserted into draft recipe; final recipe stores resolved exact template version/content. | No live mutable template at execution. |

# 6. Recipe Data Model

## `recipe_family`
- id
- tenant
- product_business_id
- recipe_code
- site scope
- manufacturing profile
- lifecycle

## `recipe_version`

```text
id uuid PK
recipe_family_id uuid NOT NULL
version_no bigint NOT NULL
product_version_id uuid NOT NULL
site_id uuid NOT NULL
batch_size_value numeric(24,8)
batch_size_uom varchar(40)
status varchar(40)
effective_from/to
graph_version varchar(20)
released_vault_object_id uuid
digest char(64)
```

## `recipe_section`
- id
- recipe_version_id
- stable_section_code
- name
- sequence
- area_requirement_id
- parallel_group
- expected_duration

## `recipe_step`

```text
id uuid PK
recipe_version_id uuid
stable_step_code varchar(120)
section_id uuid
step_type varchar(60)
instruction_markdown/text
sequence_hint int
required_role_code
qualification_policy_id
signature_policy_id
exception_policy_id
is_critical boolean
```

## `recipe_step_dependency`
- predecessor_step_id
- successor_step_id
- dependency_type: FINISH_TO_START / PARALLEL_JOIN / CONDITION
- condition_rule_id/version

## `recipe_parameter`
- step_id
- parameter_code
- data_type
- uom
- source_type
- target/min/max
- precision
- required
- rule_id/version
- manual_fallback_policy

## `recipe_material_requirement`
- step_id
- material_spec_version_id
- target quantity/formula reference
- tolerance rule
- alternative policy
- consume mode
- genealogy required

## `recipe_equipment_requirement`
- step_id
- equipment class
- exact equipment optional
- calibration/qualification/cleaning policies

## `recipe_evidence_requirement`
- step_id
- evidence type
- required count
- allowed MIME/file source
- retention class

# 7. Graph Validation

Release validator must detect:
- cycles not explicitly supported;
- unreachable steps;
- dead-end paths;
- branch without default/fail-safe outcome;
- missing join;
- missing signature/rule dependency;
- unresolved draft reference;
- incompatible product/site/profile;
- references to obsolete dependencies;
- unsupported sterile/device feature.

# 8. Recipe Release Workflow

1. Author creates draft.
2. Draft validates structurally.
3. Submit for review.
4. Reviewers compare to prior version.
5. Required QA/process signatures.
6. Canonical snapshot generated.
7. Vault release commit.
8. Event `RecipeVersionReleased`.
9. Frappe projection becomes read-only Released.
10. Effective scheduler marks eligible at effective date.

# 9. Batch Snapshot Contract

Snapshot contains:
- product version;
- recipe version;
- every step/section;
- material requirement versions;
- equipment policies;
- qualification policies;
- parameter definitions;
- rule/calculation versions;
- signature policies;
- QC/sampling requirements;
- packaging/label profile;
- expected yield/reconciliation points;
- evidence requirements;
- sterile/environment profile where applicable.

# 10. APIs

- `POST /recipes/v1/drafts`
- `PUT /recipes/v1/drafts/{id}`
- `POST /recipes/v1/drafts/{id}/validate`
- `POST /recipes/v1/drafts/{id}/simulate`
- `POST /recipes/v1/drafts/{id}/submit`
- `POST /recipes/v1/drafts/{id}/release`
- `GET /recipes/v1/{familyId}/versions`
- `GET /recipes/v1/versions/{id}`
- `GET /recipes/v1/versions/{id}/compare/{otherId}`
- `GET /recipes/v1/versions/{id}/issue-eligibility?site=...&date=...`

Errors:
`RECIPE_GRAPH_INVALID`, `DEPENDENCY_UNRELEASED`, `PRODUCT_VERSION_MISMATCH`, `SITE_NOT_ADMITTED`, `PROFILE_REQUIREMENT_MISSING`, `RULE_VERSION_MISSING`, `SIGNATURE_POLICY_MISSING`, `RECIPE_NOT_EFFECTIVE`.

# 11. Events

- RecipeDraftSubmitted
- RecipeValidationFailed
- RecipeVersionReleased
- RecipeVersionEffective
- RecipeVersionSuspended
- RecipeVersionSuperseded

# 12. UI

1. Recipe Catalogue
2. Recipe Header/Product/Batch Size
3. Section & Step Builder
4. Dependency Graph View
5. Materials
6. Equipment
7. Parameters/Calculations
8. QC/Sampling
9. Signatures/Verification
10. Exceptions/Timers
11. Packaging/Label
12. Release Readiness
13. Version Compare
14. Simulation

# 13. Frappe Implementation

Use linked DocTypes, not unsupported deep nested child-table structures for critical hierarchy.

Recommended:
- Recipe Draft
- Recipe Section Draft
- Recipe Step Draft
- separate linked parameter/material/equipment tables
- released recipe shown as projection/Virtual DocType/read-only view.

# 14. Concurrency

Draft editing uses optimistic version/modified timestamp.
Release locks draft version and validates no modification occurred after signature challenge.
Only one release operation per draft version.

# 15. Repository Structure

```text
apps/ebmr_frappe/ebmr/recipe/
services/gxp-api/src/modules/recipe/
services/gxp-api/src/modules/snapshot/
contracts/openapi/recipe.yaml
contracts/events/recipe/
packages/recipe-graph/
validation/requirements/recipe/
```

# 16. Implementation Sequence

1. recipe family/version;
2. sections/steps;
3. graph validation;
4. parameters;
5. materials/equipment;
6. rules/signatures;
7. QC/evidence;
8. profile validators;
9. release/Vault;
10. batch snapshot;
11. compare/simulation.

# 17. Tests

- normal sequential recipe;
- parallel/join;
- conditional branch;
- cycle rejection;
- unreachable step;
- missing material spec;
- missing rule;
- obsolete equipment policy;
- wrong product version;
- independent approval;
- recipe changed after signature challenge;
- issue snapshot immutable;
- master superseded while batch active;
- manual fallback rule;
- rework route;
- sterile profile requirement;
- batch size variant;
- recipe compare.

# 18. Acceptance

A coding agent can implement Batch Engine only after:
- step type contract;
- graph semantics;
- snapshot schema;
- recipe release state model;
- rule/signature references
are frozen.

# 19. Codex / Claude Rules

Never implement recipe instructions as uncontrolled HTML/JS.
Never resolve critical dependency by “latest” version during execution.
Never add a new step type without schema, execution handler, audit behavior and tests.
Never auto-scale a recipe unless released scaling rule explicitly permits it.

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
