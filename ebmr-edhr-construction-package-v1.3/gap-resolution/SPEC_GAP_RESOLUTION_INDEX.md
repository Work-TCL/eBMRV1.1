# SPEC_GAP Resolution Index

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Resolutions APPROVED 2026-08-21 — all 20 gaps closed  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Status, approval routing and implementation effect of every gap resolution.

---

## Resolution route by class

| Class | Meaning | Who may resolve | Effect when approved |
|---|---|---|---|
| E | Editorial / engineering defect or omission with no change to regulated behaviour | Specification Owner + affected module owner | Patch or addendum applied to the source document |
| D | Design decision inside the freedom the specifications leave | Platform Architect (recorded as ADR) | ADR + resolution document become controlled input |
| R | Regulated decision that changes GxP behaviour, Part 11 controls, retention, risk or release | Named approver (Quality / Regulatory / Security) | Resolution document becomes a controlled specification; validation impact assessed |

## Resolution documents

| New document | Spec ID | Title | Closes | Approval required from |
|---|---|---|---|---|
| Document 106 | SPEC-GXP-007 | Electronic Signature Policy Baseline & Signature Point Register | SG-004 | Head of Quality; Regulatory Affairs; Product Owner |
| Document 107 | SPEC-IAM-002 | Segregation of Duties & Incompatible Role Baseline | SG-009 | Head of Quality; Security Officer |
| Document 108 | SPEC-DATA-011 | Record Retention, Archival, Legal Hold & Disposal Baseline | SG-005 | Head of Quality; Regulatory Affairs; Legal |
| Document 109 | SPEC-DATA-012 | Availability, RPO/RTO, Performance SLO, Capacity & Observability Baseline | SG-006, SG-008, SG-016 | Product Owner; SRE Lead; Validation Lead |
| Document 110 | SPEC-GXP-008 | Calculation Precision, Rounding, UOM & Numeric Integrity Baseline | SG-007 | Head of Quality; Product Owner |
| Document 111 | SPEC-VAL-019 | GxP Function Risk Classification Baseline | SG-010 | Validation Lead; Head of Quality |
| Document 112 | SPEC-DATA-013 | Entity Schema Completion & Migration Contract Addendum | SG-011, SG-015 | Data Architect; module owners |
| Document 113 | SPEC-ENG-009 | Contract Completion Standard — Schemas, Error Codes, Idempotency & Exposure Boundaries | SG-012, SG-013, SG-014, SG-018 | Platform Architect; Contract Owner |
| Document 114 | SPEC-ENG-010 | Platform Glossary & Controlled Terminology | SG-017 | Specification Owner |
| Document 115 | SPEC-ENG-011 | Requirement ID Namespace, Event Ownership, Capability Traceability & Document Patches | SG-001, SG-002, SG-003, SG-019, SG-020 | Specification Owner; Platform Architect |

## Blocking analysis — what each gap blocks

| Gap | Blocks | Work packages affected | Safe to start without resolution? |
|---|---|---|---|
| SG-001 | Requirement registry, validation traceability | WP-06, WP-12 | No — fix before traceability artefacts are frozen |
| SG-002 | Release gate mapping | WP-11, WP-00 | No |
| SG-003 | Event schema registry, compatibility checks | WP-11 | No |
| SG-004 | Any regulated approval/release endpoint | WP-01 → WP-09, WP-14 | Partially — mechanism (Doc 04) can be built; policy data cannot be seeded |
| SG-005 | Vault retention class, purge/archive jobs | WP-11, WP-09 | Yes for build, no for go-live |
| SG-006 | DR qualification acceptance | WP-11, WP-12 | Yes for build, no for qualification |
| SG-007 | Rules/calculation engine defaults, yield and dispensing | WP-01, WP-02, WP-03, WP-04 | No for calculation-bearing modules |
| SG-008 | Performance qualification acceptance | WP-11, WP-12 | Yes for build |
| SG-009 | Policy engine seed data, signature independence | WP-01, all regulated WPs | No |
| SG-010 | Test depth and evidence class for every module | all | No — sets WP entry gates |
| SG-011 | First migration for the affected entities | WP-01, WP-08, WP-09 | No |
| SG-012 | Client error handling contracts | all | Yes with the platform taxonomy applied |
| SG-013 | Contract-first codegen and contract tests | all | No |
| SG-014 | QMS duplicate prevention | WP-05 | Yes with the platform rule applied |
| SG-015 | Migration catalogue completeness | WP-11 | Yes with the Doc 100 default contract |
| SG-016 | Integrity alerting | WP-11 | Yes |
| SG-017 | Consistent implementation vocabulary | all | Yes |
| SG-018 | Interface ownership | WP-06, WP-07, WP-08 | No |
| SG-019 | Design-input coverage evidence | WP-12 | Yes for build, no for validation summary |
| SG-020 | Audit ledger build-readiness gate | WP-01 | Yes |

## Approval block (to be completed by named humans)

| Resolution document | Approver role | Name | Decision (approve / approve-with-change / reject) | Date | Signature reference |
|---|---|---|---|---|---|
| Document 106 | Head of Quality |  |  |  |  |
| Document 106 | Regulatory Affairs |  |  |  |  |
| Document 107 | Head of Quality |  |  |  |  |
| Document 107 | Security Officer |  |  |  |  |
| Document 108 | Head of Quality |  |  |  |  |
| Document 108 | Regulatory Affairs |  |  |  |  |
| Document 109 | Product Owner |  |  |  |  |
| Document 109 | SRE Lead |  |  |  |  |
| Document 110 | Head of Quality |  |  |  |  |
| Document 111 | Validation Lead |  |  |  |  |
| Document 111 | Head of Quality |  |  |  |  |
| Document 112 | Data Architect |  |  |  |  |
| Document 113 | Platform Architect |  |  |  |  |
| Document 114 | Specification Owner |  |  |  |  |
| Document 115 | Specification Owner |  |  |  |  |

> Until an approval row is completed, the corresponding baseline values remain `PROPOSED` and every artefact that consumes them carries the open gap reference. Claude Code must not remove a gap reference from generated code, contracts or validation artefacts on its own authority.
