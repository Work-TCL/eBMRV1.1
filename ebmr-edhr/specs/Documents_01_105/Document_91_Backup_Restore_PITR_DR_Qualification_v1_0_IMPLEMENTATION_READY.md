# US eBMR / eDHR Regulated Manufacturing Platform
## Document 91 — Backup, Restore, PITR & Disaster Recovery Qualification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-013  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 65, 72–77, 82–90  
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

Define objective qualification of backups and disaster recovery by executing actual restores, PITR/failover scenarios, measuring RPO/RTO and validating GxP/evidence integrity.

# 2. Actors / Components

- SRE/DR Operator
- DBA
- Validation
- QA
- Security
- Customer IT
- System Owner

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| DRV-FR-001 | Scope | Map all persistent/critical components to RPO/RTO profile. | Complete. |
| DRV-FR-002 | Backup evidence | Verify backup/manifest/WAL/object/config evidence. | Protection. |
| DRV-FR-003 | Actual restore | Restore real data into isolated environment. | Objective recovery. |
| DRV-FR-004 | PITR | Recover PostgreSQL to selected timestamp/LSN. | PITR. |
| DRV-FR-005 | RPO | Measure latest recovered data vs expected source marker. | Objective. |
| DRV-FR-006 | RTO | Measure recovery declaration/start to validated service-ready. | Objective. |
| DRV-FR-007 | Audit continuity | Verify audit/version/outbox relationships. | GxP. |
| DRV-FR-008 | Evidence | Verify metadata→object hash/availability. | Evidence. |
| DRV-FR-009 | MariaDB | Restore/rebuild/reconcile Frappe projections. | UI recovery. |
| DRV-FR-010 | NATS | Recover/config and verify outbox catch-up. | Messaging. |
| DRV-FR-011 | Temporal | Resume orchestration without false domain state. | Orchestration. |
| DRV-FR-012 | Secrets/keys | Recovered data remains decryptable; missing/rotated key behavior tested. | Crypto. |
| DRV-FR-013 | Failover | Standby promotion/split-brain prevention where HA. | Availability. |
| DRV-FR-014 | Failback | Controlled rejoin/failback where applicable. | Operations. |
| DRV-FR-015 | Regional/site DR | Secondary region/site activation where required. | Enterprise. |
| DRV-FR-016 | Network/DNS/cert | Recovery endpoints/routing/trust validated. | Accessibility. |
| DRV-FR-017 | Security | Recovery preserves auth/network/least privilege. | Secure recovery. |
| DRV-FR-018 | GxP smoke | Representative create/read/sign/audit/evidence operation after recovery. | Business verification. |
| DRV-FR-019 | Data-loss detection | Missing interval detection/assessment works if RPO exceeded. | Transparency. |
| DRV-FR-020 | Runbook | Current operators can execute runbook; deviations update procedure. | Human readiness. |
| DRV-FR-021 | Cadence | Restore/DR qualification repeated per risk/profile. | Ongoing. |
| DRV-FR-022 | Approval | Qualification approved with achieved RPO/RTO. | Gate. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createDRQualificationScenario() | SRE/Validation | failure scenario; scope; target RPO/RTO; restore point | DR profile approved | Creates scenario/runbook version | DRScenario | DRQualificationScenarioCreated |
| executeRestoreQualification() | DR operator | scenario; backup set; isolated target | Backup/key available | Performs restore/PITR and captures evidence | DRExecution | DRRestoreExecuted |
| measureRecoveryObjectives() | Validation | execution; source marker; ready time | Execution complete enough | Calculates actual RPO/RTO | RecoveryObjectiveResult | RecoveryObjectivesMeasured |
| runRecoveredGxPSmoke() | Validation | recovered environment; smoke profile | Core stores restored | Runs auth/mutation/sign/audit/evidence checks | RecoverySmokeResult | RecoveredGxPSmokeCompleted |
| approveDRQualification() | QA/Validation | results/deviations | Objectives accepted | Freezes qualification | DRQualification | DRQualificationApproved |


# 5. Validation State / Control Model

```text
BACKUPS → FAILURE/SCENARIO → RESTORE/PITR/FAILOVER → MEASURE RPO/RTO → AUDIT/EVIDENCE/SECURITY RECONCILE → GxP SMOKE → APPROVE
```

# 6. Data / Evidence Model

`dr_qualification_scenario`: failure type, components, recovery method, target RPO/RTO, restore order, acceptance.
`dr_qualification_execution`: backup set, restore point/timeline, actual objectives, integrity/smoke results, deviations.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/dr/scenarios`
- `POST /validation/v1/dr/executions`
- `POST /validation/v1/dr/{id}/measure`
- `POST /validation/v1/dr/{id}/approve`

# 8. UI / Validation Workspace

1. DR Scenarios
2. Restore Timeline
3. RPO/RTO
4. Integrity/Smoke
5. DR Qualification

# 9. Events

- `DRRestoreExecuted`
- `RecoveryObjectivesMeasured`
- `RecoveredGxPSmokeCompleted`
- `DRQualificationApproved`

# 10. Mandatory Test / Evidence Catalogue

- PITR
- standby failover
- object mismatch
- outbox recovery
- Temporal resume
- MariaDB rebuild
- key unavailable
- RPO exceeded

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

The team can demonstrate it can recover a representative regulated environment and preserve intended GxP/evidence integrity within approved objectives.

# 13. Claude Code / Codex Prohibitions

- Never validate backup by green job status only.
- Never destructive-restore live production target.
- Never declare ready before GxP/evidence checks.
- Never hide RPO miss.


