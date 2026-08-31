# US eBMR / eDHR Regulated Manufacturing Platform
## Document 86 — Infrastructure, Cloud, Platform & Environment Qualification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-008  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 61–78, 83; cloud/on-prem deployment  
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

Define risk-based qualification of the technical environment including managed services, Kubernetes, databases, storage, messaging, orchestration, network, secrets, time, monitoring and drift.

# 2. Actors / Components

- Platform/SRE
- Validation
- Security
- DBA
- Customer IT
- QA

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| INFQ-FR-001 | Qualified baseline | Define qualified cloud/on-prem services, versions and config ranges. | Infrastructure control. |
| INFQ-FR-002 | Shared responsibility | Document provider/product/customer controls/evidence. | Cloud assurance. |
| INFQ-FR-003 | Supplier evidence | Vendor certifications/docs supplement actual configuration verification. | Balanced assurance. |
| INFQ-FR-004 | Kubernetes | Verify cluster/version/network/storage/security/time/admission config. | Runtime. |
| INFQ-FR-005 | Databases | Verify Postgres/MariaDB version/config/HA/backup/access/monitoring. | Persistence. |
| INFQ-FR-006 | Object store | Verify encryption/immutability/versioning/access/lifecycle/hash retrieval. | Evidence. |
| INFQ-FR-007 | NATS | Verify streams/replicas/storage/auth/TLS/monitoring. | Messaging. |
| INFQ-FR-008 | Temporal | Verify namespace/auth/persistence/worker connectivity/backup. | Orchestration. |
| INFQ-FR-009 | Secrets/KMS | Verify retrieval/rotation/cert renewal/key recovery. | Security. |
| INFQ-FR-010 | Network | Verify required/forbidden flows and Edge boundary. | Isolation. |
| INFQ-FR-011 | Clock | Verify NTP/UTC and alarms. | Chronology. |
| INFQ-FR-012 | Monitoring | Verify critical metrics/log/alerts. | Operations. |
| INFQ-FR-013 | Backup | Link actual restore evidence from Doc91. | Recovery. |
| INFQ-FR-014 | Capacity | Resources meet intended sizing. | Performance. |
| INFQ-FR-015 | HA | Failover behavior tested/justified by deployment tier. | Availability. |
| INFQ-FR-016 | On-prem | Customer hardware/storage/network prerequisites verified. | Deployment. |
| INFQ-FR-017 | Patching | Patch/change qualification model defined. | Lifecycle. |
| INFQ-FR-018 | Drift | Production drift monitored against qualified baseline. | Validated state. |
| INFQ-FR-019 | Environment equivalence | Validation→production intentional differences documented. | Confidence. |
| INFQ-FR-020 | Requalification | Material infrastructure change triggers scoped requalification. | Lifecycle. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createInfrastructureQualificationProfile() | Platform/Validation | deployment profile; inventory; control requirements | Architecture/release approved | Creates expected qualification baseline | InfraQualificationProfile | InfrastructureQualificationProfileCreated |
| captureInfrastructureFingerprint() | Qualification agent | environment | Read access | Captures versions/config hashes/network/storage/security refs | InfrastructureFingerprint | InfrastructureFingerprintCaptured |
| compareEnvironmentToQualifiedBaseline() | Validation | fingerprint; profile | Both current | Returns differences/materiality | InfrastructureComparison | InfrastructureQualificationDifferenceDetected |
| executeInfrastructureControlTest() | Validation/SRE | control/test code; environment | Safe test approved | Runs network/HA/time/storage/security tests | InfrastructureTestResult | InfrastructureControlTestCompleted |
| approveInfrastructureQualification() | Validation/QA | profile; tests; deviations; signature | Critical controls accepted | Freezes qualified baseline | QualifiedInfrastructure | InfrastructureQualified |


# 5. Validation State / Control Model

```text
DEPLOYMENT PROFILE → INFRA BASELINE → ENVIRONMENT FINGERPRINT → CONTROL/FAILOVER/SECURITY TESTS → DIFFERENCES → QUALIFIED ENVIRONMENT → DRIFT/CHANGE
```

# 6. Data / Evidence Model

`infrastructure_qualification_profile`: deployment/provider, required components/config ranges, control tests, supplier evidence, change triggers.
`infrastructure_fingerprint`: versions, config hashes, resources, network/security/time/backup refs.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/infrastructure/profiles`
- `POST /validation/v1/infrastructure/fingerprints`
- `POST /validation/v1/infrastructure/tests`
- `POST /validation/v1/infrastructure/{id}/approve`

# 8. UI / Validation Workspace

1. Infrastructure Baseline
2. Environment Fingerprint
3. Control Tests
4. Supplier Evidence
5. Drift/Requalification

# 9. Events

- `InfrastructureFingerprintCaptured`
- `InfrastructureQualificationDifferenceDetected`
- `InfrastructureQualified`

# 10. Mandatory Test / Evidence Catalogue

- prod/validation difference
- network deny
- managed DB failover
- NATS persistence
- Temporal reconnect
- clock alert
- object immutability

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

Production has objective evidence that material infrastructure controls match an approved qualified baseline.

# 13. Claude Code / Codex Prohibitions

- Never qualify cloud provider certification instead of actual config.
- Never assume managed service eliminates customer risk.
- Never ignore drift.
- Never include secret plaintext in fingerprint.


