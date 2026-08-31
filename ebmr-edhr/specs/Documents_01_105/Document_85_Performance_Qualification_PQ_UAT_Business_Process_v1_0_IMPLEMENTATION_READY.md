# US eBMR / eDHR Regulated Manufacturing Platform
## Document 85 — Performance Qualification (PQ), UAT & Business Process Verification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-007  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 54–60, 79–84; Customer procedures/training  
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

Define customer/site-specific end-to-end qualification demonstrating trained users can execute intended regulated processes using the released configuration and interfaces.

# 2. Actors / Components

- Process Owner
- Production User
- QA
- QC
- Warehouse
- Engineering
- Customer Validation
- System Owner

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| PQ-FR-001 | Business-process suitability | PQ verifies real intended workflows with trained representative users/procedures. | Fit for use. |
| PQ-FR-002 | Customer/site scope | PQ deployment/site/process-specific where configuration differs. | Configured product. |
| PQ-FR-003 | Representative scenarios | Use end-to-end product/process scenarios. | Operational relevance. |
| PQ-FR-004 | Representative roles | Production/QA/QC/warehouse/engineering roles participate as applicable. | User suitability. |
| PQ-FR-005 | Training prerequisite | PQ participants trained/qualified. | Credible execution. |
| PQ-FR-006 | Product profile | Include PFS/injector/inhalation/coated profile only when applicable. | Risk based. |
| PQ-FR-007 | Material flow | Receipt→quarantine→release→dispense→consume/return/reconcile. | End-to-end. |
| PQ-FR-008 | QC flow | Sample→test→review→OOS exception/disposition. | Lab. |
| PQ-FR-009 | Deviation flow | Batch exception→deviation→impact→resolution/release. | QMS. |
| PQ-FR-010 | Signature flow | Configured IdP/signature/approval/QA release executed by real role. | Actual use. |
| PQ-FR-011 | Edge/device flow | Representative scanner/balance/machine input if site uses it. | Factory. |
| PQ-FR-012 | ERP/LIMS flow | Customer interfaces included when go-live depends on them. | Integration. |
| PQ-FR-013 | Shift/handoff | Long-running handoff/resume represented when applicable. | Operations. |
| PQ-FR-014 | Procedure compatibility | SOP/work instruction must match actual UI/process. | Human system. |
| PQ-FR-015 | Usability observation | Capture confusion/error-prone workflow as validation observation. | Practical fit. |
| PQ-FR-016 | Business exceptions | Include realistic exception/recovery paths. | Operational confidence. |
| PQ-FR-017 | UAT equivalence | Controlled customer UAT may satisfy PQ evidence if VMP criteria met. | Efficiency. |
| PQ-FR-018 | Go-live blockers | Critical process/procedure/training failure blocks PQ. | Safe deployment. |
| PQ-FR-019 | Customer acceptance | Process Owner/System Owner/QA approvals according to matrix. | Ownership. |
| PQ-FR-020 | Template reuse | Vendor scenarios reusable as template, not customer acceptance substitute. | Scalable service. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createPQScenario() | Validation/Process SME | site/product/process; actors; prerequisites; steps; acceptance | OQ approved; config known | Creates controlled PQ scenario | PQScenario | PQScenarioCreated |
| assignPQParticipants() | Validation Admin | scenario; users/roles; training refs | Users eligible | Creates participant assignments | PQParticipantSet | PQParticipantsAssigned |
| executePQScenario() | Representative users | scenario; site/environment; dataset | Participants trained; procedures effective | Runs end-to-end scenario and captures evidence | PQExecution | PQScenarioCompleted |
| recordPQUsabilityObservation() | Tester/Observer | execution; observation; severity; impact | Execution active/review | Creates validation observation/change candidate | PQObservation | PQUsabilityObservationRecorded |
| approvePQ() | Process Owner/QA | scenario/executions; deviations; signatures | Required scenarios accepted | Freezes PQ/site acceptance | ApprovedPQ | PQApproved |


# 5. Validation State / Control Model

```text
OQ APPROVED + SOP/TRAINING READY → PQ SCENARIOS → TRAINED USERS EXECUTE → OBSERVATIONS/EXCEPTIONS → CUSTOMER/QA APPROVAL
```

# 6. Data / Evidence Model

`pq_scenario`: site/profile/process, roles/training, prerequisites, steps, interfaces/equipment, acceptance.
`pq_execution`: participant identities, environment/config, observations/results/evidence/deviations/approval.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/pq/scenarios`
- `POST /validation/v1/pq/scenarios/{id}/participants`
- `POST /validation/v1/pq/executions`
- `POST /validation/v1/pq/{id}/approve`

# 8. UI / Validation Workspace

1. PQ Scenarios
2. Participants/Training
3. PQ Execution
4. Usability Observations
5. Site Acceptance

# 9. Events

- `PQScenarioCreated`
- `PQScenarioCompleted`
- `PQUsabilityObservationRecorded`
- `PQApproved`

# 10. Mandatory Test / Evidence Catalogue

- untrained user blocked
- PFS batch scenario
- ERP unavailable
- signature flow
- batch deviation
- procedure/UI mismatch
- controlled UAT reuse

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

A customer can demonstrate with representative trained users that the configured system supports its intended manufacturing/quality process.

# 13. Claude Code / Codex Prohibitions

- Never use developer demo as PQ.
- Never reuse another customer's result without equivalence.
- Never ignore process mismatch because API passed.
- Never approve PQ before critical training.


