# US eBMR / eDHR Regulated Manufacturing Platform
## Document 15 — Release / Disposition Engine Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EBMR-006  
**Parent Documents:** Document 01 v1.1; Document 02 v1.0  
**Primary Dependencies:** Documents 03–14; QMS/QC/Materials/Packaging/Equipment/Genealogy  
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

Define the authoritative final quality decision engine for release, rejection, hold, rework/reprocess and other controlled dispositions.

The Rules Engine determines eligibility. Authorized Quality makes the final release decision. The software must never automatically release regulated product solely because rules are green.

# 2. Architecture

```text
Batch / Device / DDCP Scope
      ↓
Release Eligibility Engine
      ├── QA Review
      ├── QC
      ├── QMS
      ├── Materials
      ├── Equipment
      ├── Sterile/Environment
      ├── Packaging
      ├── Genealogy
      ├── Yield/Reconciliation
      └── Signatures
      ↓
ELIGIBLE / BLOCKED
      ↓
Authorized QA + Fresh E-Signature
      ↓
Immutable Release/Disposition Package
      ↓
Released Event → ERP/WMS/Export
```

# 3. Functional Requirements

| ID | Functionality | Detailed behavior | Acceptance intent |
|---|---|---|---|
| REL-FR-001 | Release scope | Define release/disposition object for exact product/batch/device lot/serial/combination scope. | Decision target unambiguous. |
| REL-FR-002 | Separate DDCP final release | Drug/device constituent acceptance/release are prerequisites but never automatically equal final combination-product release. | Final DDCP authority separate. |
| REL-FR-003 | Eligibility evaluation | Evaluate released rule set against manufacturing completeness, QA review, QC, QMS, materials, equipment, environment, packaging, genealogy, yield/reconciliation and signatures. | No manual checklist-only release. |
| REL-FR-004 | Blocker model | Return machine-readable blockers with severity, source record and resolution action. | User knows exact reason. |
| REL-FR-005 | Warning model | Warnings may require acknowledgement/comment but cannot be used to downgrade mandatory blocker without controlled rule/change. | No ad hoc bypass. |
| REL-FR-006 | QA authority | Only authorized current QA Release signer(s) may execute final release/disposition. | Authority controlled. |
| REL-FR-007 | Step-up signature | Final release/reject/disposition uses Document 04 signature bound to exact release package/version/hash. | Exact decision signed. |
| REL-FR-008 | Re-evaluation before commit | Immediately before release commit, recheck batch version, eligibility rules, open blockers and signature validity. | No stale green status. |
| REL-FR-009 | Release snapshot | Commit immutable release package containing exact decision inputs, rule versions, review package, signatures, batch/record hash and genealogy completeness status. | Historical release reproducible. |
| REL-FR-010 | Release states | Draft Evaluation, Eligible, Blocked, Pending Signature, Released, Rejected, Hold, Rework, Reprocess, Destruction, Return/Other configured disposition. | Explicit disposition. |
| REL-FR-011 | Hold disposition | Quality can place release hold with reason and signature; release eligibility may continue updating but product cannot distribute. | Hold enforced. |
| REL-FR-012 | Reject | Reject decision records reason, affected scope, inventory status and downstream disposition requirement. | Rejected product controlled. |
| REL-FR-013 | Rework/reprocess | Disposition links to approved route; original release scope remains unreleased until new execution/review complete. | No shortcut. |
| REL-FR-014 | Destruction | Disposition can require destruction workflow/evidence/witness before closure. | Material/product accounted. |
| REL-FR-015 | Partial release | Only supported when product/profile explicitly allows defined sub-lot/serial scope with independent genealogy/QC/reconciliation; default disabled. | No accidental partial release. |
| REL-FR-016 | Serial release | Device units may inherit lot release only when profile/rules permit and all unit exceptions are resolved. | High-volume support. |
| REL-FR-017 | Expiry/retest/status | Evaluate expiration, stability/release test and relevant constituent status rules. | Expired/ineligible product cannot release. |
| REL-FR-018 | Open QMS events | Evaluate deviations/OOS/OOT/NCR/CAPA dependencies according to released profile; unresolved critical event blocks. | Quality integrated. |
| REL-FR-019 | Material status | All consumed critical material lots must have acceptable use status or approved deviation captured. | Traceable. |
| REL-FR-020 | Equipment status at use | Eligibility considers equipment status at operation time and unresolved equipment-impact events. | Historical correctness. |
| REL-FR-021 | Sterile/environment | Applicable sterile/environmental release evidence and excursion dispositions required. | Aseptic product support. |
| REL-FR-022 | Packaging/label | Packaging completion, label correctness and reconciliation required where applicable. | Final product correctly labeled. |
| REL-FR-023 | Genealogy | Required material/constituent/serial/package genealogy completeness required. | Recall-ready. |
| REL-FR-024 | Yield/reconciliation | Configured yield/material/label reconciliation within limits or resolved investigation required. | Numerical closure. |
| REL-FR-025 | Review package | QA review must be current/not invalidated and signed when required. | Review not stale. |
| REL-FR-026 | Release correction | Release decision itself cannot be edited; if later found erroneous, create controlled post-release quality/field-action path, not overwrite history. | Release history immutable. |
| REL-FR-027 | Distribution integration | After release, emit event to ERP/WMS; integration failure does not undo release but prevents/flags downstream availability according to interface policy. | System boundaries clear. |
| REL-FR-028 | Release certificate/export | Generate release summary/certificate if configured, with signer, time, product/batch, decision and source package hash. | Customer evidence. |
| REL-FR-029 | Release audit | Audit eligibility evaluation, blockers, acknowledgements, signature and final decision. | Inspection-ready. |
| REL-FR-030 | Bulk release | Batching multiple independent release scopes into one UI action may be allowed, but each scope gets independent eligibility/signature binding/decision record. | No one signature ambiguously covers unknown scope. |
| REL-FR-031 | Revoke availability | Post-release hold/recall is a new controlled status/action; released historical decision remains intact. | No history rewrite. |
| REL-FR-032 | Release SLA metrics | Track review/release cycle time and blocker aging without influencing regulatory decision. | Operational analytics. |

# 4. Data Model

## `release_scope`

```text
id uuid PK
tenant_id uuid
site_id uuid
scope_type varchar(40)
scope_id uuid
product_version_id uuid
batch_id uuid
state varchar(40)
version bigint
current_evaluation_id uuid
released_vault_object_id uuid
created_at timestamptz
decision_at timestamptz
```

## `release_evaluation`
- scope/version
- rule set version
- evaluated batch/source version
- blockers JSON/reference
- warnings
- eligible bool
- evaluation time

## `release_decision`
- exact scope
- evaluation ID
- decision code
- reason/comment
- signature ID
- decision time
- release package hash

# 5. Eligibility API

- `POST /release/v1/scopes/{type}/{id}/evaluate`
- `GET /release/v1/scopes/{id}/eligibility`
- `POST /release/v1/scopes/{id}/release`
- `POST /release/v1/scopes/{id}/hold`
- `POST /release/v1/scopes/{id}/reject`
- `POST /release/v1/scopes/{id}/rework`
- `POST /release/v1/scopes/{id}/reprocess`
- `POST /release/v1/scopes/{id}/destroy`
- `GET /release/v1/scopes/{id}/package`

Errors:
`RELEASE_BLOCKED`, `REVIEW_NOT_CURRENT`, `OPEN_CRITICAL_QUALITY_EVENT`, `QC_INCOMPLETE`, `GENEALOGY_INCOMPLETE`, `RECONCILIATION_FAILED`, `SIGNATURE_INVALID`, `RELEASE_SCOPE_CHANGED`.

# 6. Release Blocker Contract

```json
{
  "code":"OPEN_OOS",
  "severity":"CRITICAL",
  "source_type":"OOS",
  "source_id":"...",
  "message_key":"release.blocker.open_oos",
  "resolution_action":"RESOLVE_QUALITY_EVENT"
}
```

Use message keys + structured data, not business logic encoded in text.

# 7. UI

1. Release Dashboard
2. Scope Header
3. Eligibility Summary
4. Blockers/Warnings
5. QA Review Status
6. QC/QMS
7. Materials/Genealogy
8. Packaging/Label
9. Yield/Reconciliation
10. Release Decision
11. Signature Dialog
12. Release Package

# 8. DDCP Final Release

DDCP release package shall explicitly show:
- drug constituent exact version/batch/status;
- device constituent version/lot/serial scope/status;
- compatibility version;
- integrated assembly/test evidence;
- final packaging/label;
- final QA authority.

# 9. Events

- ReleaseEvaluationCompleted
- ReleaseEligibilityChanged
- ReleaseHoldPlaced
- ProductReleased
- ProductRejected
- ReworkDispositionApproved
- ReprocessDispositionApproved
- DestructionDispositionApproved
- PostReleaseHoldPlaced

# 10. Concurrency

Release command includes:
- scope version;
- batch/device record version;
- review package version/hash;
- evaluation ID.

Any source change invalidates stale evaluation/signature.

# 11. Integration

ERP/WMS receives `ProductReleased` or disposition events.
External system cannot call a generic endpoint to mark GxP release complete.

# 12. Repository Structure

```text
services/gxp-api/src/modules/release/
apps/ebmr_frappe/ebmr/release/
contracts/events/release/
validation/requirements/release/
```

# 13. Tests

- fully eligible release;
- open deviation;
- OOS;
- missing QC;
- stale QA review;
- missing material genealogy;
- equipment exception;
- sterile excursion;
- failed label reconciliation;
- yield failure;
- same user SoD conflict;
- record changes during signature;
- ERP outage after release;
- reject;
- rework;
- partial release disabled;
- DDCP constituent released but final not released.

# 14. Acceptance

A final DDCP cannot be distributed through normal integration until a separate final release decision is committed and signed.

# 15. Codex / Claude Rules

Never auto-release product because all rules pass.
Never convert constituent release status into final DDCP release.
Never let ERP inventory status write final QA release.
Never overwrite a prior release decision.

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
