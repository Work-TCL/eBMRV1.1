# 18 — SPEC_GAP Register

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Resolutions APPROVED 2026-08-21 — all 20 gaps closed  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Every missing or conflicting decision found in Documents 01–105, with impact, options and the document that resolves it.

---

**Total gaps:** 20 | **Blocking:** 9 | **Non-blocking:** 11  
**Regulated decisions (class R):** 6 | **Design decisions (class D):** 2 | **Editorial/engineering (class E):** 12

Class R gaps are **not** resolved by this package on its own authority. Each has a proposed resolution document containing analysis, options and a recommended baseline, and each carries an approval block that a named human must sign before the value becomes controlled truth. Until then the value is `PROPOSED` and Claude Code must treat it as configuration with an open gap reference.

## Summary

| Gap | Class | Blocking | Title | Resolved by | Owner |
|---|---|---|---|---|---|
| SG-001 | E | **YES** | Requirement-ID namespace collision: DRV-FR used by two documents | Document 115 | Specification Owner / Document Control |
| SG-002 | E | **YES** | Requirement-ID namespace collision: DEP-FR used by two documents | Document 115 | Specification Owner / Document Control |
| SG-003 | E | **YES** | Event producer ambiguity — three event types declared by more than one document | Document 115 | Platform Architect / Contract Owner |
| SG-004 | R | **YES** | Baseline electronic-signature policy (action → meaning → signer → count/order) is not defined | Document 106 | Head of Quality (approver) + Regulatory Affairs + Product Owner |
| SG-005 | R | no | Record retention, archival, legal-hold and disposal periods are not numerically defined | Document 108 | Head of Quality + Regulatory Affairs + Legal |
| SG-006 | R | no | RPO / RTO targets per component are not numerically defined | Document 109 | Product Owner + Customer Quality (per deployment) + SRE Lead |
| SG-007 | R | **YES** | Calculation precision, rounding mode and UOM conversion defaults are not defined | Document 110 | Head of Quality + Product Owner + Rules Engine Owner |
| SG-008 | D | no | Performance / SLO numeric targets per operation class are not defined | Document 109 | Product Owner + SRE Lead + Validation Lead |
| SG-009 | R | **YES** | Incompatible-role (SoD) baseline matrix is not enumerated | Document 107 | Head of Quality + Security Officer |
| SG-010 | R | **YES** | GxP function risk classification is not assigned to modules or functions | Document 111 | Validation Lead + Head of Quality |
| SG-011 | E | **YES** | Named entities without column, type, constraint or index definition | Document 112 | Data Architect + owning module owner |
| SG-012 | E | no | No stable error-code registry in most module specifications | Document 113 | Contract Owner (API) + module owners |
| SG-013 | E | **YES** | API request/response schemas are not defined at field level | Document 113 | Contract Owner (API/Events) |
| SG-014 | E | no | Idempotency / replay behaviour not stated for QMS module commands | Document 113 | QMS module owner + Mutation Gateway owner |
| SG-015 | E | no | Migration / upgrade behaviour not stated for entity-owning specifications | Document 112 | Data Architect + module owners |
| SG-016 | E | no | Observability / alerting not stated for a number of specifications | Document 109 | SRE Lead + module owners |
| SG-017 | E | no | No controlled platform glossary / terminology set | Document 114 | Specification Owner |
| SG-018 | D | no | Module exposure boundary unstated for specifications that declare no API or event surface | Document 113 | Platform Architect |
| SG-019 | E | no | Document 01 capability IDs are not traced forward into Documents 03–105 | Document 115 | Specification Owner + Validation Lead |
| SG-020 | E | no | Document 05 has no acceptance-criteria section | Document 115 | Specification Owner |

---

## Gap entries

### SG-001 — Requirement-ID namespace collision: DRV-FR used by two documents

`DRV-FR-001..0nn` is used as the requirement namespace in both Document 44 (Industrial Device & Protocol Connectivity / Drivers) and Document 91 (Backup, Restore, PITR & DR Qualification). 22 identifiers collide.

```yaml
spec_gap_id: SG-001
title: Requirement-ID namespace collision: DRV-FR used by two documents
class: E  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  `DRV-FR-001..0nn` is used as the requirement namespace in both Document 44 (Industrial Device & Protocol Connectivity / Drivers) and Document 91 (Backup, Restore, PITR & DR Qualification). 22 identifiers collide.
source_documents:
  - Document 44
  - Document 91
  - Document 81 (traceability)
  - Document 100/101
source_requirement_ids:
  - DRV-FR-001
  - DRV-FR-002
  - DRV-FR-003
  - DRV-FR-004
  - DRV-FR-005
  - DRV-FR-006
  - ...
affected_modules:
  - SPEC-EDGE-002
  - SPEC-VAL-013
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  A requirement identifier must resolve to exactly one requirement. Two owners of `DRV-FR-013` make the requirement registry, validation traceability matrix, test traceability and change impact analysis ambiguous.
risk_if_guessed: >
  Validation traceability cannot be proven; a test could be credited against the wrong requirement; change impact analysis silently misses one of the two documents.
options:
  - (A) Re-namespace Document 91 to `DRQ-FR-nnn` (DR Qualification) — recommended: Document 44 owns the natural meaning of DRV (driver).
  - (B) Re-namespace Document 44 to `DRVR-FR-nnn`.
  - (C) Prefix all identifiers with the specification ID (`SPEC-EDGE-002:DRV-FR-013`) — larger edit surface, breaks existing cross references.
blocking: true
owner: Specification Owner / Document Control
resolution_document: Document 115
status: RESOLVED_APPROVED_2026-08-21
```

### SG-002 — Requirement-ID namespace collision: DEP-FR used by two documents

`DEP-FR-001..0nn` is used in both Document 77 (Cloud-Neutral Deployment / Kubernetes) and Document 104 (SBOM / Third-Party License Management). 35 identifiers collide.

```yaml
spec_gap_id: SG-002
title: Requirement-ID namespace collision: DEP-FR used by two documents
class: E  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  `DEP-FR-001..0nn` is used in both Document 77 (Cloud-Neutral Deployment / Kubernetes) and Document 104 (SBOM / Third-Party License Management). 35 identifiers collide.
source_documents:
  - Document 77
  - Document 104
  - Document 81
  - Document 68
source_requirement_ids:
  - DEP-FR-001
  - DEP-FR-002
  - DEP-FR-003
  - DEP-FR-004
  - DEP-FR-005
  - DEP-FR-006
  - ...
affected_modules:
  - SPEC-DATA-009
  - SPEC-ENG-008
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Same defect class as SG-001. Additionally these two documents feed different CI gates (deployment gate vs dependency/licence gate), so a mis-resolved ID mis-routes a release control.
risk_if_guessed: >
  Release evidence maps a deployment requirement onto a licence control or vice versa.
options:
  - (A) Re-namespace Document 104 to `DEPS-FR-nnn` (dependencies) — recommended: Document 77 owns 'deployment'.
  - (B) Re-namespace Document 77 to `DPL-FR-nnn`.
  - (C) Specification-qualified IDs everywhere.
blocking: true
owner: Specification Owner / Document Control
resolution_document: Document 115
status: RESOLVED_APPROVED_2026-08-21
```

### SG-003 — Event producer ambiguity — three event types declared by more than one document

Events declared by multiple documents: `LineClearanceCompleted` (Docs 16, 39); `MaterialReconciliationCalculated` (Docs 17, 22); `OutboxLagExceeded` (Docs 73, 78); `ProjectionLagExceeded` (Docs 75, 78); `ProjectionStaleDetected` (Docs 69, 71). Document 101 requires exactly one producing owner per event type.

```yaml
spec_gap_id: SG-003
title: Event producer ambiguity — three event types declared by more than one document
class: E  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Events declared by multiple documents: `LineClearanceCompleted` (Docs 16, 39); `MaterialReconciliationCalculated` (Docs 17, 22); `OutboxLagExceeded` (Docs 73, 78); `ProjectionLagExceeded` (Docs 75, 78); `ProjectionStaleDetected` (Docs 69, 71). Document 101 requires exactly one producing owner per event type.
source_documents:
  - Document 101
  - Document 69
  - Document 71
  - Document 73
  - Document 75
  - Document 78
source_requirement_ids:
  - EVT-FR (Doc 101 ownership rules)
affected_modules:
  - SPEC-DATA-001
  - SPEC-DATA-003
  - SPEC-DATA-005
  - SPEC-DATA-007
  - SPEC-DATA-010
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Two producers of the same event type produce two incompatible payload schemas and two owners for compatibility/deprecation decisions.
risk_if_guessed: >
  Consumers break silently on payload drift; schema registry cannot enforce compatibility; alerting duplicates or gaps.
options:
  - (A) Assign each operational-signal event to the observability owner (Document 78) and have Docs 69/71/73/75 consume it — recommended.
  - (B) Assign each event to the component that detects the condition and rename the Document 78 usage.
  - (C) Split into distinct event types per producer (`projection.stale.detected.frappe` vs `...readmodel`).
blocking: true
owner: Platform Architect / Contract Owner
resolution_document: Document 115
status: RESOLVED_APPROVED_2026-08-21
```

### SG-004 — Baseline electronic-signature policy (action → meaning → signer → count/order) is not defined

Document 04 SIG-FR-004 requires a record/action policy defining required meaning, signer role/qualification, number and order of signatures and independence rules. The mechanism is fully specified; no controlled document fixes the product-default policy values. 100+ candidate signature points exist across Documents 09–60.

```yaml
spec_gap_id: SG-004
title: Baseline electronic-signature policy (action → meaning → signer → count/order) is not defined
class: R  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Document 04 SIG-FR-004 requires a record/action policy defining required meaning, signer role/qualification, number and order of signatures and independence rules. The mechanism is fully specified; no controlled document fixes the product-default policy values. 100+ candidate signature points exist across Documents 09–60.
source_documents:
  - Document 04 (SIG-FR-003, SIG-FR-004, SIG-FR-017, SIG-FR-018)
  - Document 07
  - Document 88
  - Document 01 §6.2
source_requirement_ids:
  - SIG-FR-003
  - SIG-FR-004
  - SIG-FR-017
  - SIG-FR-018
  - MUT-FR-012
affected_modules:
  - SPEC-GXP-002
  - SPEC-GXP-001
  - all regulated domain modules
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Whether an action requires a signature, with which meaning and by whom, is a Part 11 / predicate-rule decision. It cannot be inferred from an endpoint name.
risk_if_guessed: >
  Guessing produces either unlawful unsigned regulated approvals or unnecessary signatures that break customer process and validation.
options:
  - (A) Ship a validated product-default policy set that customers may tighten but not weaken below the platform floor — recommended.
  - (B) Ship no defaults and require every customer to author the full policy during PQ (high implementation risk, no platform validation baseline).
  - (C) Derive signature requirement from record class only (too coarse — misses performer/verifier and independence).
blocking: true
owner: Head of Quality (approver) + Regulatory Affairs + Product Owner
resolution_document: Document 106
status: RESOLVED_APPROVED_2026-08-21
```

### SG-005 — Record retention, archival, legal-hold and disposal periods are not numerically defined

Document 06 VLT-FR-019 requires a retention class per vault object; Document 60 PMO-FR-025..028 requires longest-applicable retention and legal hold. No document assigns concrete durations or trigger events per record class. 14 specifications that own entities or APIs do not mention retention at all.

```yaml
spec_gap_id: SG-005
title: Record retention, archival, legal-hold and disposal periods are not numerically defined
class: R  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Document 06 VLT-FR-019 requires a retention class per vault object; Document 60 PMO-FR-025..028 requires longest-applicable retention and legal hold. No document assigns concrete durations or trigger events per record class. 14 specifications that own entities or APIs do not mention retention at all.
source_documents:
  - Document 06 (VLT-FR-019/021/022)
  - Document 60 (PMO-FR-025..028)
  - Document 69
  - Document 72
  - Document 05
source_requirement_ids:
  - VLT-FR-019
  - PMO-FR-025
  - PMO-FR-026
  - PMO-FR-027
  - PMO-FR-028
affected_modules:
  - SPEC-GXP-004
  - SPEC-DATA-004
  - SPEC-PM-003
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Retention duration is a predicate-rule obligation (e.g. §211.180, §820.180/§820.184, §4.105, Part 806 recordkeeping) and varies by product, market and record class. Deleting or purging early is unrecoverable.
risk_if_guessed: >
  Early destruction of a regulated record is an irreversible compliance failure; over-retention creates privacy exposure for postmarket patient data.
options:
  - (A) Define retention classes with rule-based durations bound to predicate-rule citations and product profile, defaulting to the longest applicable rule and never auto-purging without an authorized disposal decision — recommended.
  - (B) Fixed global duration for all records (simple, non-compliant for DDCP and postmarket).
  - (C) Customer-configured only, no platform default (blocks platform-level validation of the retention engine).
blocking: false
owner: Head of Quality + Regulatory Affairs + Legal
resolution_document: Document 108
status: RESOLVED_APPROVED_2026-08-21
```

### SG-006 — RPO / RTO targets per component are not numerically defined

Documents 76 and 91 require RPO/RTO to be assigned per component and business capability and approved by the customer, and require DR qualification to test against those targets. No numeric baseline exists, so DR qualification has no acceptance limits.

```yaml
spec_gap_id: SG-006
title: RPO / RTO targets per component are not numerically defined
class: R  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Documents 76 and 91 require RPO/RTO to be assigned per component and business capability and approved by the customer, and require DR qualification to test against those targets. No numeric baseline exists, so DR qualification has no acceptance limits.
source_documents:
  - Document 76
  - Document 91
  - Document 78
  - Document 86
source_requirement_ids:
  - DR-FR (Doc 76)
  - Doc 91 qualification acceptance
affected_modules:
  - SPEC-DATA-008
  - SPEC-VAL-013
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  A qualification protocol without a numeric acceptance criterion cannot pass or fail objectively.
risk_if_guessed: >
  DR qualification becomes a narrative exercise; a customer discovers unacceptable data loss after go-live.
options:
  - (A) Platform default RPO/RTO tiers per component class, contractually overridable per deployment — recommended.
  - (B) Leave entirely to customer contract (no platform DR qualification possible).
  - (C) Single global RPO/RTO for everything (ignores that outbox, evidence store and read models have different recovery semantics).
blocking: false
owner: Product Owner + Customer Quality (per deployment) + SRE Lead
resolution_document: Document 109
status: RESOLVED_APPROVED_2026-08-21
```

### SG-007 — Calculation precision, rounding mode and UOM conversion defaults are not defined

Document 08 and Document 17 require rounding mode, stage, decimal places/significant figures and precision policy to be explicit and versioned. The mechanism and the requirement to version it are specified; the default numeric policy per calculation class is not.

```yaml
spec_gap_id: SG-007
title: Calculation precision, rounding mode and UOM conversion defaults are not defined
class: R  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Document 08 and Document 17 require rounding mode, stage, decimal places/significant figures and precision policy to be explicit and versioned. The mechanism and the requirement to version it are specified; the default numeric policy per calculation class is not.
source_documents:
  - Document 08
  - Document 17
  - Document 21
  - Document 97
source_requirement_ids:
  - RUL-FR (precision/rounding policy)
  - YLD-FR (yield reconciliation)
  - DSP-FR (dispensing tolerance)
affected_modules:
  - SPEC-GXP-006
  - SPEC-EBMR-008
  - SPEC-MAT-002C
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Rounding stage and mode change whether a batch passes or fails a limit. This is a regulated calculation decision, not an implementation detail.
risk_if_guessed: >
  A yield or dispensing tolerance result differs between UI, service and report; a batch is released on a rounded value that the raw data does not support.
options:
  - (A) Define calculation classes with mandatory decimal arithmetic, explicit rounding stage (round only at presentation and at declared decision points), and versioned per-class policy — recommended.
  - (B) Round at every step (accumulates error; not defensible).
  - (C) Leave per-customer (each customer's yields become incomparable; platform cannot validate the calculation engine).
blocking: true
owner: Head of Quality + Product Owner + Rules Engine Owner
resolution_document: Document 110
status: RESOLVED_APPROVED_2026-08-21
```

### SG-008 — Performance / SLO numeric targets per operation class are not defined

Document 78 requires p95/p99 targets by operation class; Document 93 qualifies performance against them. No numeric baseline exists.

```yaml
spec_gap_id: SG-008
title: Performance / SLO numeric targets per operation class are not defined
class: D  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Document 78 requires p95/p99 targets by operation class; Document 93 qualifies performance against them. No numeric baseline exists.
source_documents:
  - Document 78
  - Document 93
  - Document 85
source_requirement_ids:
  - SRE-FR (SLO definition)
  - PERFQ-FR (performance qualification)
affected_modules:
  - SPEC-DATA-010
  - SPEC-VAL-015
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Performance qualification and capacity planning both need declared numbers; operator-facing execution latency also affects GxP usability risk.
risk_if_guessed: >
  Performance qualification cannot fail; production capacity is unplanned; slow signature ceremonies cause workarounds on the shop floor.
options:
  - (A) Platform SLO baseline per operation class with per-deployment override — recommended.
  - (B) Customer-defined only.
  - (C) No SLOs (unacceptable for a regulated production system).
blocking: false
owner: Product Owner + SRE Lead + Validation Lead
resolution_document: Document 109
status: RESOLVED_APPROVED_2026-08-21
```

### SG-009 — Incompatible-role (SoD) baseline matrix is not enumerated

Document 01 §6.2 lists the SoD rule classes the policy engine must support and Document 07 specifies the engine. Neither enumerates which concrete reference roles may not be combined, nor the default performer/verifier independence rules per action.

```yaml
spec_gap_id: SG-009
title: Incompatible-role (SoD) baseline matrix is not enumerated
class: R  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Document 01 §6.2 lists the SoD rule classes the policy engine must support and Document 07 specifies the engine. Neither enumerates which concrete reference roles may not be combined, nor the default performer/verifier independence rules per action.
source_documents:
  - Document 01 §6.1/§6.2
  - Document 07
  - Document 04 (SIG-FR-018)
  - Document 63
source_requirement_ids:
  - IAM-FR (SoD evaluation)
  - SIG-FR-018
affected_modules:
  - SPEC-IAM-001
  - SPEC-GXP-002
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  SoD conflicts are a direct data-integrity and Part 11 control. Which combinations are prohibited is a quality-system decision.
risk_if_guessed: >
  A single user performs and independently verifies the same regulated action; QA release performed by the production performer.
options:
  - (A) Platform-default incompatible-role matrix plus per-action independence rules, tightenable by customer — recommended.
  - (B) Only per-action independence, no role-pair matrix (misses standing privilege conflicts).
  - (C) Customer-defined only (no platform validation baseline; every deployment re-derives the control).
blocking: true
owner: Head of Quality + Security Officer
resolution_document: Document 107
status: RESOLVED_APPROVED_2026-08-21
```

### SG-010 — GxP function risk classification is not assigned to modules or functions

Document 80 defines the classification method (intended use, GxP impact, automation role, record/signature role, detectability, risk category) but assigns no classification to any module or function. Every downstream CSA decision — test depth, independence, evidence class, qualification stage — depends on that assignment.

```yaml
spec_gap_id: SG-010
title: GxP function risk classification is not assigned to modules or functions
class: R  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Document 80 defines the classification method (intended use, GxP impact, automation role, record/signature role, detectability, risk category) but assigns no classification to any module or function. Every downstream CSA decision — test depth, independence, evidence class, qualification stage — depends on that assignment.
source_documents:
  - Document 80
  - Document 79
  - Document 82
  - Document 81
source_requirement_ids:
  - RISK-FR-001..014
affected_modules:
  - all
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Test strategy, evidence rigour and revalidation triggers are all risk-driven. Without an approved classification the validation programme has no basis.
risk_if_guessed: >
  Either everything is tested as high risk (unaffordable, and CSA-contrary) or high-risk functions receive low-risk assurance.
options:
  - (A) Publish a proposed classification for all 105 modules derived from objective document evidence (signature role, record role, enforcement role) for Quality approval — recommended.
  - (B) Classify only at function level during each work package (delays every WP entry gate).
  - (C) Classify everything as higher-process-risk (defensible but wasteful and contrary to Document 79 CSA strategy).
blocking: true
owner: Validation Lead + Head of Quality
resolution_document: Document 111
status: RESOLVED_APPROVED_2026-08-21
```

### SG-011 — Named entities without column, type, constraint or index definition

23 entities are named in the specifications with no field-level definition: `vault_object` (Doc 06), `vault_evidence_manifest` (Doc 06), `iam_qualification` (Doc 07), `ddcp_profile_version` (Doc 54), `constituent_requirement` (Doc 54), `constituent_handoff` (Doc 54), `fill_operation` (Doc 54), `production_count_ledger` (Doc 54), `device_assembly_record` (Doc 54), `device_functional_test_link` (Doc 54), `ddcp_release_checkpoint` (Doc 54), `batch_evidence_manifest` (Doc 54), `postmarket_source` (Doc 58), `safety_case_followup` (Doc 58), `safety_signal` (Doc 58), `reportability_track` (Doc 59), `regulatory_report` (Doc 59), `regulatory_submission_attempt` (Doc 59), `regulatory_submission_ack` (Doc 59), `applicant_relationship` (Doc 60), `constituent_information_share` (Doc 60), `correction_removal_regulatory_record` (Doc 60), `periodic_reporting_cycle` (Doc 60)

```yaml
spec_gap_id: SG-011
title: Named entities without column, type, constraint or index definition
class: E  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  23 entities are named in the specifications with no field-level definition: `vault_object` (Doc 06), `vault_evidence_manifest` (Doc 06), `iam_qualification` (Doc 07), `ddcp_profile_version` (Doc 54), `constituent_requirement` (Doc 54), `constituent_handoff` (Doc 54), `fill_operation` (Doc 54), `production_count_ledger` (Doc 54), `device_assembly_record` (Doc 54), `device_functional_test_link` (Doc 54), `ddcp_release_checkpoint` (Doc 54), `batch_evidence_manifest` (Doc 54), `postmarket_source` (Doc 58), `safety_case_followup` (Doc 58), `safety_signal` (Doc 58), `reportability_track` (Doc 59), `regulatory_report` (Doc 59), `regulatory_submission_attempt` (Doc 59), `regulatory_submission_ack` (Doc 59), `applicant_relationship` (Doc 60), `constituent_information_share` (Doc 60), `correction_removal_regulatory_record` (Doc 60), `periodic_reporting_cycle` (Doc 60)
source_documents:
  - Document 06
  - Document 07
  - Document 54
  - Document 58
  - Document 59
  - Document 60
  - Document 70
  - Document 100
source_requirement_ids:
  - Construction instruction §8 Database Gate
  - Doc 70 aggregate table baseline
affected_modules:
  - SPEC-DDCP-001
  - SPEC-GXP-004
  - SPEC-IAM-001
  - SPEC-PM-001
  - SPEC-PM-002
  - SPEC-PM-003
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  The Database Gate prohibits writing a migration before columns, types, constraints, indexes, versioning and retention behaviour are defined.
risk_if_guessed: >
  Claude Code invents schemas per module, producing inconsistent tenancy, versioning and retention behaviour on regulated tables.
options:
  - (A) Complete the schemas in a controlled addendum using the Document 70 aggregate baseline plus the owning document's requirements — recommended.
  - (B) Defer to implementation time per work package (guarantees drift).
  - (C) Store as JSONB blobs (loses constraints, indexes and query semantics on regulated data).
blocking: true
owner: Data Architect + owning module owner
resolution_document: Document 112
status: RESOLVED_APPROVED_2026-08-21
```

### SG-012 — No stable error-code registry in most module specifications

MUT-FR-021 requires stable machine-readable error codes for every rejected regulated command, and Document 101 makes codes contract surface. 69 of 103 module specifications declare no stable error codes.

```yaml
spec_gap_id: SG-012
title: No stable error-code registry in most module specifications
class: E  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  MUT-FR-021 requires stable machine-readable error codes for every rejected regulated command, and Document 101 makes codes contract surface. 69 of 103 module specifications declare no stable error codes.
source_documents:
  - Document 03 (MUT-FR-021)
  - Document 101
  - Document 05
  - Document 06
  - Document 08
  - Document 09
  - Document 10
  - Document 11
  - Document 12
  - Document 13
source_requirement_ids:
  - MUT-FR-021
  - CTR-FR (Doc 101)
affected_modules:
  - all
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Clients must branch on codes, not free text. Missing codes force each implementer to invent them, breaking client compatibility and validation evidence.
risk_if_guessed: >
  UI and integrations branch on message strings; error behaviour changes silently between releases.
options:
  - (A) Platform error-code taxonomy plus mandatory per-module code derivation rules and a registry file under version control — recommended.
  - (B) Free-form per-module codes (no cross-module consistency).
  - (C) HTTP status codes only (insufficient granularity for regulated rejection reasons).
blocking: false
owner: Contract Owner (API) + module owners
resolution_document: Document 113
status: RESOLVED_APPROVED_2026-08-21
```

### SG-013 — API request/response schemas are not defined at field level

498 API operations and 484 event types are declared by path/name across the baseline, but only a small number of documents provide request/response or payload examples (authoring standard items 18 and 21). Contract-first code generation, consumer contract tests and compatibility checks all require field-level schemas.

```yaml
spec_gap_id: SG-013
title: API request/response schemas are not defined at field level
class: E  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  498 API operations and 484 event types are declared by path/name across the baseline, but only a small number of documents provide request/response or payload examples (authoring standard items 18 and 21). Contract-first code generation, consumer contract tests and compatibility checks all require field-level schemas.
source_documents:
  - Document 101
  - Document 03 §19
  - Authoring Standard items 17–21
source_requirement_ids:
  - CTR-FR (Doc 101)
  - MUT-FR-005
  - MUT-FR-030
affected_modules:
  - all
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Without schemas, each implementation invents payloads and the compatibility registry cannot detect a breaking change.
risk_if_guessed: >
  Silent breaking changes to validated interfaces; no meaningful contract testing.
options:
  - (A) Mandate contract-first: OpenAPI/AsyncAPI + JSON Schema authored before implementation in each work package, with a standard envelope and field-derivation rules from the entity model — recommended.
  - (B) Generate schemas from implementation code after the fact (contract follows code; breaks the gate).
  - (C) Author all 982 contracts centrally before any work package starts (blocks all implementation for months).
blocking: true
owner: Contract Owner (API/Events)
resolution_document: Document 113
status: RESOLVED_APPROVED_2026-08-21
```

### SG-014 — Idempotency / replay behaviour not stated for QMS module commands

MUT-FR-010 requires an idempotency key for commands capable of duplicate submission. Documents 26, 28, 29, 30, 31, 32, 33, 34, 36, 37 declare mutation APIs without stating idempotency or replay behaviour.

```yaml
spec_gap_id: SG-014
title: Idempotency / replay behaviour not stated for QMS module commands
class: E  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  MUT-FR-010 requires an idempotency key for commands capable of duplicate submission. Documents 26, 28, 29, 30, 31, 32, 33, 34, 36, 37 declare mutation APIs without stating idempotency or replay behaviour.
source_documents:
  - Document 03 (MUT-FR-010, MUT-FR-025)
  - Document 26
  - Document 28
  - Document 29
  - Document 30
  - Document 31
  - Document 32
  - Document 33
  - Document 34
  - Document 36
  - Document 37
source_requirement_ids:
  - MUT-FR-010
  - MUT-FR-025
affected_modules:
  - SPEC-QMS-*
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Duplicate CAPA, deviation or change records created by a double click or a retried request corrupt quality metrics and inspection history.
risk_if_guessed: >
  Duplicate quality records; duplicated escalation and notification; corrupted trending.
options:
  - (A) Apply the platform idempotency rule uniformly to every state-changing command with a documented per-command key derivation — recommended.
  - (B) Per-module opt-in (inconsistent).
  - (C) UI-side debounce only (does not survive retries or integration callers).
blocking: false
owner: QMS module owner + Mutation Gateway owner
resolution_document: Document 113
status: RESOLVED_APPROVED_2026-08-21
```

### SG-015 — Migration / upgrade behaviour not stated for entity-owning specifications

Authoring standard item 31 requires migration/upgrade behaviour. Documents 31, 32, 33, 34, 35, 36, 37, 54, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68, 75, 76, 78, 80, 82, 84, 85, 86, 88, 90, 91, 92, 93, 94 own entities but state none.

```yaml
spec_gap_id: SG-015
title: Migration / upgrade behaviour not stated for entity-owning specifications
class: E  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Authoring standard item 31 requires migration/upgrade behaviour. Documents 31, 32, 33, 34, 35, 36, 37, 54, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68, 75, 76, 78, 80, 82, 84, 85, 86, 88, 90, 91, 92, 93, 94 own entities but state none.
source_documents:
  - Document 100
  - Document 87
  - Document 31
  - Document 32
  - Document 33
  - Document 34
  - Document 35
  - Document 36
  - Document 37
  - Document 54
source_requirement_ids:
  - MIG-FR (Doc 100)
affected_modules:
  - SPEC-DATA-007
  - SPEC-DATA-008
  - SPEC-DATA-010
  - SPEC-DDCP-001
  - SPEC-PM-001
  - SPEC-PM-002
  - SPEC-PM-003
  - SPEC-QMS-006
  - SPEC-QMS-007
  - SPEC-QMS-008
  - SPEC-QMS-009
  - SPEC-QMS-010
  - SPEC-QMS-011
  - SPEC-QMS-012
  - SPEC-SEC-001
  - SPEC-SEC-002
  - SPEC-SEC-003
  - SPEC-SEC-004
  - SPEC-SEC-006
  - SPEC-SEC-007
  - SPEC-SEC-008
  - SPEC-VAL-002
  - SPEC-VAL-004
  - SPEC-VAL-006
  - SPEC-VAL-007
  - SPEC-VAL-008
  - SPEC-VAL-010
  - SPEC-VAL-012
  - SPEC-VAL-013
  - SPEC-VAL-014
  - SPEC-VAL-015
  - SPEC-VAL-016
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Every regulated table needs a declared compatibility window, backfill strategy, lock risk and rollback path before its first migration.
risk_if_guessed: >
  Locking migrations on high-volume regulated tables; irreversible data transformations without reconciliation evidence.
options:
  - (A) Apply the Document 100 migration standard as a default contract for every entity, with per-entity entries in the migration catalogue — recommended.
  - (B) Per-module migration policy (drift).
  - (C) Recreate-and-copy migrations (unacceptable downtime and evidence risk).
blocking: false
owner: Data Architect + module owners
resolution_document: Document 112
status: RESOLVED_APPROVED_2026-08-21
```

### SG-016 — Observability / alerting not stated for a number of specifications

Authoring standard item 29 requires observability and alerts. Documents 30, 31, 32, 33, 54, 57, 64, 80, 82, 84, 85, 87, 88, 89, 90, 91, 94, 96, 98, 99, 101, 103, 104 state none.

```yaml
spec_gap_id: SG-016
title: Observability / alerting not stated for a number of specifications
class: E  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Authoring standard item 29 requires observability and alerts. Documents 30, 31, 32, 33, 54, 57, 64, 80, 82, 84, 85, 87, 88, 89, 90, 91, 94, 96, 98, 99, 101, 103, 104 state none.
source_documents:
  - Document 78
  - Document 67
source_requirement_ids:
  - SRE-FR
  - MON-FR
affected_modules:
  - multiple
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Undetected failure of a regulated projection, outbox publisher or interface silently degrades data integrity.
risk_if_guessed: >
  Stale projections or unpublished events discovered only during inspection.
options:
  - (A) Platform observability baseline: every module inherits mandatory signal classes (saturation, lag, failure, integrity) with per-module additions — recommended.
  - (B) Per-module bespoke metrics (gaps).
  - (C) Infrastructure metrics only (misses regulated integrity signals).
blocking: false
owner: SRE Lead + module owners
resolution_document: Document 109
status: RESOLVED_APPROVED_2026-08-21
```

### SG-017 — No controlled platform glossary / terminology set

Authoring standard item 4 requires terminology. No document defines the controlled vocabulary, and terms such as record, version, snapshot, evidence, projection, release, disposition and qualification carry precise and different meanings across modules.

```yaml
spec_gap_id: SG-017
title: No controlled platform glossary / terminology set
class: E  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Authoring standard item 4 requires terminology. No document defines the controlled vocabulary, and terms such as record, version, snapshot, evidence, projection, release, disposition and qualification carry precise and different meanings across modules.
source_documents:
  - Authoring Standard item 4
  - Documents 01–105
source_requirement_ids:
  - Authoring Standard §4
affected_modules:
  - all
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Terminology drift causes implementation drift: 'release' means recipe release, batch release, material release and software release in different documents.
risk_if_guessed: >
  A developer implements 'release' semantics from the wrong domain.
options:
  - (A) Single controlled glossary with per-term owning document and prohibited synonyms — recommended.
  - (B) Per-document glossaries (repetition and divergence).
  - (C) None (status quo).
blocking: false
owner: Specification Owner
resolution_document: Document 114
status: RESOLVED_APPROVED_2026-08-21
```

### SG-018 — Module exposure boundary unstated for specifications that declare no API or event surface

Documents 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57 declare functions and requirements but no API or event surface. It is not stated whether these modules are exposed through another module's contract (for example Edge documents through the Document 43 gateway API, DDCP profiles through the Document 11 execution API) or are internal libraries.

```yaml
spec_gap_id: SG-018
title: Module exposure boundary unstated for specifications that declare no API or event surface
class: D  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Documents 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57 declare functions and requirements but no API or event surface. It is not stated whether these modules are exposed through another module's contract (for example Edge documents through the Document 43 gateway API, DDCP profiles through the Document 11 execution API) or are internal libraries.
source_documents:
  - Document 44
  - Document 45
  - Document 46
  - Document 47
  - Document 48
  - Document 49
  - Document 50
  - Document 51
  - Document 52
  - Document 53
  - Document 54
  - Document 55
  - Document 56
  - Document 57
source_requirement_ids:
  - Doc 101 ownership
affected_modules:
  - SPEC-EDGE-*
  - SPEC-ERP-*
  - SPEC-DDCP-*
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  An unstated exposure boundary is where an agent invents a new endpoint or, worse, a direct database write.
risk_if_guessed: >
  Duplicate or bypass interfaces; unowned contract surface.
options:
  - (A) Declare each such module's host contract explicitly (profile/driver/adapter modules are configuration and library layers behind an owning module's API) — recommended.
  - (B) Give every module its own API (contract sprawl, duplicate ownership).
  - (C) Leave to implementation (guaranteed bypass risk).
blocking: false
owner: Platform Architect
resolution_document: Document 113
status: RESOLVED_APPROVED_2026-08-21
```

### SG-019 — Document 01 capability IDs are not traced forward into Documents 03–105

Document 01 (frozen bible) defines 215 capability identifiers (C-nnn, MAT-nnn, PH-nnn, ST-nnn, CP-nnn, QMS-nnn, MD-nnn, PM-nnn). Sampling shows most are referenced only inside Document 01 itself, so the highest-precedence document has no forward traceability into the implementing specifications.

```yaml
spec_gap_id: SG-019
title: Document 01 capability IDs are not traced forward into Documents 03–105
class: E  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Document 01 (frozen bible) defines 215 capability identifiers (C-nnn, MAT-nnn, PH-nnn, ST-nnn, CP-nnn, QMS-nnn, MD-nnn, PM-nnn). Sampling shows most are referenced only inside Document 01 itself, so the highest-precedence document has no forward traceability into the implementing specifications.
source_documents:
  - Document 01
  - Document 81
source_requirement_ids:
  - Doc 01 capability IDs
  - REQ-FR (Doc 81)
affected_modules:
  - all
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  Source precedence puts Document 01 first. If its capabilities are not traced to implementing requirements, coverage against the frozen product definition cannot be demonstrated.
risk_if_guessed: >
  A frozen product capability is never implemented and nobody detects it; validation cannot show design-input coverage.
options:
  - (A) Build a capability→requirement coverage matrix as a Phase-0 artefact and fill unmapped capabilities as findings — recommended.
  - (B) Treat Document 01 as narrative only (contradicts the stated precedence).
  - (C) Re-write Document 01 requirements into the module documents (large change to a frozen document).
blocking: false
owner: Specification Owner + Validation Lead
resolution_document: Document 115
status: RESOLVED_APPROVED_2026-08-21
```

### SG-020 — Document 05 has no acceptance-criteria section

Authoring standard item 35 requires acceptance criteria in every module specification. Document 05 (Immutable Audit Ledger) is the only specification with no acceptance section, and it is one of the highest-risk modules in the platform.

```yaml
spec_gap_id: SG-020
title: Document 05 has no acceptance-criteria section
class: E  # E=editorial/engineering  D=design decision  R=regulated decision
description: >
  Authoring standard item 35 requires acceptance criteria in every module specification. Document 05 (Immutable Audit Ledger) is the only specification with no acceptance section, and it is one of the highest-risk modules in the platform.
source_documents:
  - Document 05
  - Authoring Standard item 35
source_requirement_ids:
  - AUD-FR-*
affected_modules:
  - SPEC-GXP-003
affected_functions:
  - see 03_FUNCTION_CATALOGUE.csv rows for the affected modules
why_material: >
  The audit ledger's build-readiness gate is undefined while every other GxP Core document has one.
risk_if_guessed: >
  Audit ledger declared complete without an objective gate.
options:
  - (A) Add an acceptance section to Document 05 mirroring the Document 03/04/06 pattern and the Document 89 qualification criteria — recommended.
  - (B) Rely on Document 89 alone (mixes specification acceptance with qualification evidence).
blocking: false
owner: Specification Owner
resolution_document: Document 115
status: RESOLVED_APPROVED_2026-08-21
```
