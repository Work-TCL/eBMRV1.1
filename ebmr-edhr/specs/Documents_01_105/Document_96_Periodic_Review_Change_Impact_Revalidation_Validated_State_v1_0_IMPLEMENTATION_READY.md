# US eBMR / eDHR Regulated Manufacturing Platform
## Document 96 — Periodic Review, Change Impact, Revalidation & Validated-State Maintenance — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-018  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 29, 61–78, 79–95  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This specification is intended for direct ingestion by Claude Code, Codex, Validation/Quality, and engineering teams.

Before implementation, the coding agent shall extract:
1. requirement IDs and compliance/risk linkage;
2. validation artifact types;
3. validation lifecycle/state machines;
4. function/service contract catalogue;
5. typed input/output schemas;
6. authorization/qualification/SoD/signature requirements;
7. database reads/writes and transaction boundaries;
8. evidence/object-storage contracts;
9. test execution/result schemas;
10. traceability relationships;
11. deviation/defect linkage;
12. release/periodic-review gates;
13. automated/manual test obligations;
14. validation evidence retention.

For every public/domain validation function defined below, preserve caller/trigger, typed inputs, auth/signature prerequisites, validations, DB/evidence reads/writes, transaction boundary, output, events, stable errors, idempotency/concurrency, audit evidence, and test obligations.

If a missing decision can alter intended use, GxP risk, acceptance criteria, validation evidence, release eligibility, or revalidation scope, create a `SPEC_GAP` rather than guessing.

# Current U.S. Validation / CSA Regulatory Baseline

- FDA issued the final **Computer Software Assurance for Production and Quality Management System Software** guidance in February 2026. It recommends a risk-based approach for medical-device production/QMS software and supersedes the September 24, 2025 final guidance.
- The QMSR became effective February 2, 2026 and incorporates ISO 13485:2016 by reference. Maintain a licensed compliance mapping; do not reproduce copyrighted ISO clauses.
- 21 CFR §11.10 includes validation to ensure accuracy, reliability, consistent intended performance and the ability to discern invalid or altered records, plus copies, retention, access, audit, operational, authority, device, training and documentation controls.
- FDA's Part 11 Scope and Application guidance states Part 11 remains in effect while FDA exercises enforcement discretion for certain provisions as described there; predicate-rule obligations remain.
- 21 CFR §211.68 requires appropriate controls over computer/related systems used in drug manufacturing and addresses authorized changes, input/output checks, backups and appropriate validation data.
- IQ/OQ/PQ and GAMP-style lifecycle classifications are useful validation/industry methods, not universal FDA-mandated document names.

Primary references:
- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/computer-software-assurance-production-and-quality-management-system-software
- https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr
- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application
- https://www.law.cornell.edu/cfr/text/21/11.10
- https://www.law.cornell.edu/cfr/text/21/211.68

# Validation Architecture Principles

- Validation is intended-use and risk based.
- The validated state belongs to a released system configuration/version + environment + controlled procedures, not source code alone.
- Every critical requirement must trace to design/implementation and objective evidence.
- Automated tests are encouraged where deterministic, reliable and reviewable.
- Exploratory testing may be appropriate for lower-risk functions when objective evidence is retained.
- Higher-risk GxP functions require greater assurance rigor.
- Failed tests remain immutable; rerun never erases failure.
- Production release requires software release evidence and validation release evidence.
# 1. Objective

Define ongoing maintenance of validated state through change impact, risk-based revalidation, periodic review, drift/security/DR/performance assessment and controlled decommissioning.

# 2. Actors / Components

- System Owner
- QA
- Validation
- Change Control
- Engineering
- SRE/Security
- Records Manager
- Customer Process Owner

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| VSM-FR-001 | Validated baseline | Inventory software/services/config/rules/interfaces/infrastructure/procedures in validated state. | Known state. |
| VSM-FR-002 | Change trigger | Every controlled change evaluates validation impact before production. | Lifecycle. |
| VSM-FR-003 | Impact scope | Identify affected requirements/risk/functions/tests/interfaces/data/security/performance/SOP/training. | Complete impact. |
| VSM-FR-004 | Revalidation level | NONE_WITH_RATIONALE/DOC_REVIEW/TARGETED_TEST/PARTIAL/FULL_REQUALIFICATION. | Proportionate. |
| VSM-FR-005 | Emergency change | Expedited route allowed with risk/evidence and retrospective completion. | Continuity. |
| VSM-FR-006 | Patches | OS/runtime/library/security patches use risk-based impact, not blanket full regression. | CSA. |
| VSM-FR-007 | GxP config | Rule/workflow/form/signature/role/interface config change assessed. | Configured state. |
| VSM-FR-008 | Infrastructure change | DB/cloud/K8s/storage/network changes map requalification scope. | Environment. |
| VSM-FR-009 | Interface change | ERP/LIMS/device schema/version change maps requalification. | Integration. |
| VSM-FR-010 | Data change | Migration/bulk repair/master conversion receives validation scope. | Integrity. |
| VSM-FR-011 | Periodic schedule | Validated deployments reviewed at risk/contract interval. | Ongoing assurance. |
| VSM-FR-012 | Review inputs | Changes, incidents, CAPA, defects, vulnerabilities, DR, performance, access, vendor/EOL and audit trends. | Holistic. |
| VSM-FR-013 | Version support | Unsupported/EOL dependencies flagged/remediated. | Lifecycle. |
| VSM-FR-014 | Drift review | Production config/infrastructure compared to validated baseline. | State control. |
| VSM-FR-015 | Training/SOP | Procedure/training currentness/effectiveness reviewed after process change. | Human system. |
| VSM-FR-016 | Part 11 review | Identity/signature/audit/archive control changes/incidents assessed. | Compliance. |
| VSM-FR-017 | DR review | Latest restore/DR evidence and RPO/RTO issues reviewed. | Recovery. |
| VSM-FR-018 | Security review | Pen/scans/open findings/incidents/exceptions reviewed. | Cybersecurity. |
| VSM-FR-019 | Capacity review | Growth/headroom/SLO issues reviewed. | Reliability. |
| VSM-FR-020 | Customer review | Enabled modules/config/interfaces/site deviations included. | Deployment. |
| VSM-FR-021 | Decision | VALIDATED_CONFIRMED/ACTION_REQUIRED/REVALIDATION_REQUIRED/SUSPENDED. | Explicit. |
| VSM-FR-022 | Actions | Findings create Change/CAPA/validation action with owner/due date. | Improvement. |
| VSM-FR-023 | Suspension | Critical integrity/security/validation issue can suspend affected use. | Risk control. |
| VSM-FR-024 | Release continuity | Each release references prior baseline/change impact/delta or VSR. | Continuity. |
| VSM-FR-025 | Evidence | Periodic review/revalidation retained with system history. | Inspection. |
| VSM-FR-026 | Decommission | Retirement includes record archive/retrieval/access/integration shutdown. | Lifecycle end. |
| VSM-FR-027 | Supplier change | Major cloud/identity/vendor dependency change triggers impact. | External dependency. |
| VSM-FR-028 | No perpetual validation | Initial validation never means permanent assurance without controlled lifecycle. | Principle. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| assessValidationChangeImpact() | Change Control | change; changed artifacts/config; target env | Validated baseline exists | Traverses trace graph and proposes revalidation scope | ValidationChangeImpact | ValidationChangeImpactAssessed |
| approveRevalidationPlan() | Validation/QA | impact; selected tests/level; rationale | Impact complete | Freezes revalidation plan | RevalidationPlan | RevalidationPlanApproved |
| executeRevalidation() | Validation/CI | plan; target release/environment | Plan approved | Runs selected evidence and links change | RevalidationExecution | RevalidationCompleted |
| createPeriodicReview() | Scheduled/System Owner | deployment/baseline; period | Review due | Collects changes/incidents/security/DR/performance/access/vendor data | PeriodicReview | PeriodicReviewCreated |
| evaluateValidatedState() | QA/System Owner | periodic review inputs/actions | Evidence complete | Records validated-state decision | ValidatedStateDecision | ValidatedStateEvaluated |
| decommissionValidatedSystem() | System Owner/Records/QA | deployment; archive/retention/shutdown plan | Retention/legal requirements resolved | Executes controlled retirement and final evidence package | DecommissionRecord | ValidatedSystemDecommissioned |


# 5. Validation State / Control Model

```text
VALIDATED BASELINE → CHANGE/INCIDENT/PERIODIC REVIEW → IMPACT → NONE/TARGETED/PARTIAL/FULL/SUSPEND → EVIDENCE/APPROVAL → NEW BASELINE
```

# 6. Data / Evidence Model

`validated_state_baseline`: release/config/environment/VSR/component inventory/state.
`validation_change_impact`: change, affected trace artifacts, proposed revalidation level, rationale.
`periodic_validation_review`: period, changes/incidents/security/DR/performance/access/vendor inputs, findings/actions/decision.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/change-impacts`
- `POST /validation/v1/revalidation-plans`
- `POST /validation/v1/revalidations`
- `POST /validation/v1/periodic-reviews`
- `POST /validation/v1/periodic-reviews/{id}/decision`
- `POST /validation/v1/decommission`

# 8. UI / Validation Workspace

1. Validated Baseline
2. Change Impact
3. Revalidation Plans
4. Periodic Review
5. Drift/Issues
6. Validated-State Decision
7. Decommission

# 9. Events

- `ValidationChangeImpactAssessed`
- `RevalidationPlanApproved`
- `RevalidationCompleted`
- `PeriodicReviewCreated`
- `ValidatedStateEvaluated`
- `ValidatedSystemDecommissioned`

# 10. Mandatory Test / Evidence Catalogue

- security patch targeted regression
- DB major upgrade
- release rule change
- IdP change Part11 retest
- expired DR qualification
- critical incident suspension
- decommission archive

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

Every production change and periodic review demonstrates whether the deployed system remains within an approved validated state and what evidence supports that conclusion.

# 13. Claude Code / Codex Prohibitions

- Never assume initial validation remains valid indefinitely.
- Never make all changes full revalidation by default.
- Never deploy GxP config change without impact assessment.
- Never decommission before record retention/access plan.


