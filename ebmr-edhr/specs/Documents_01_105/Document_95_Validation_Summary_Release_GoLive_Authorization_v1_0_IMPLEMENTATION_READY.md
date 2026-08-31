# US eBMR / eDHR Regulated Manufacturing Platform
## Document 95 — Validation Summary Report, Release-to-Production & Go-Live Authorization — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-017  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 79–94; Release/Deployment/Change  
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

Define the final validation summary and technical/Quality release gate binding objective evidence to the exact software/configuration/environment promoted into regulated production.

# 2. Actors / Components

- Validation Lead
- QA
- System Owner
- Release Engineer
- Customer Process Owner
- Security/SRE

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| VSR-FR-001 | VSR generation | Generate VSR from authoritative validation artifacts. | Final evidence. |
| VSR-FR-002 | Scope | State system/release/customer/environment/config/intended use. | Boundary. |
| VSR-FR-003 | Baselines | List requirement/risk/design/test/config/IQ/OQ/PQ/security/performance/DR baselines. | Reproducible. |
| VSR-FR-004 | Execution summary | Summarize evidence by method/risk/module/status. | Coverage. |
| VSR-FR-005 | Traceability | Include critical gap/orphan status. | Completeness. |
| VSR-FR-006 | Deviations | Include open/closed/accepted exceptions and release impact. | Transparency. |
| VSR-FR-007 | Security | Include qualification/findings/exceptions. | Risk. |
| VSR-FR-008 | Performance | Include operating envelope/limitations. | Operations. |
| VSR-FR-009 | DR | Include restore/DR qualification and achieved objectives. | Recovery. |
| VSR-FR-010 | Migration | Include migration validation if applicable. | Cutover. |
| VSR-FR-011 | Part 11 | Include Part 11 package/customer responsibilities. | Compliance. |
| VSR-FR-012 | Customer responsibilities | Outstanding SOP/training/certification/config duties explicit. | Shared validation. |
| VSR-FR-013 | Known limitations | Approved limitations/workarounds/monitoring listed. | Transparency. |
| VSR-FR-014 | Recommendation/approval | Validation recommendation separate from QA/System Owner authorization. | SoD. |
| VSR-FR-015 | Go-live prerequisites | Training, prod config, backups, interfaces, support, monitoring/cutover tasks checked. | Readiness. |
| VSR-FR-016 | Configuration fingerprint | Record approved production configuration hash. | Validated state. |
| VSR-FR-017 | Release identity | Exact image/code/SBOM/schema/migration/config versions. | Software identity. |
| VSR-FR-018 | Approval | VSR electronically approved/signed by required roles. | Controlled. |
| VSR-FR-019 | Decision | APPROVED/CONDITIONAL/REJECTED; condition cannot bypass critical GxP control. | Explicit. |
| VSR-FR-020 | Evidence manifest | VSR references immutable validation package. | Inspection. |
| VSR-FR-021 | Customer package | Generate vendor/customer subset based on responsibility/access. | Commercial. |
| VSR-FR-022 | Pipeline gate | Production promotion checks validated release authorization. | Technical gate. |
| VSR-FR-023 | Post-go-live | Defined smoke/monitoring verification. | Safe deployment. |
| VSR-FR-024 | Rollback | Failed post-go-live verification follows controlled rollback/incident/change. | Recovery. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| generateValidationSummaryReport() | Validation service | release/customer/site | Required artifacts current | Aggregates baselines/coverage/deviations/limitations | ValidationSummaryReport | ValidationSummaryGenerated |
| evaluateGoLiveReadiness() | Release gate | VSR scope; training/config/DR/security/interface gates | Current evidence | Returns prerequisites/blockers | GoLiveReadiness | GoLiveReadinessEvaluated |
| approveValidationSummary() | Validation Lead/QA/System Owner | VSR; recommendation; signatures | Blockers resolved | Vault-releases VSR | ApprovedVSR | ValidationSummaryApproved |
| issueValidatedReleaseAuthorization() | QA/System Owner | approved VSR; release/config fingerprint | Approval current | Creates signed authorization | ValidatedReleaseAuthorization | ValidatedReleaseAuthorized |
| verifyDeploymentAgainstValidationRelease() | Deploy pipeline | authorization; artifact/config fingerprint | Authorization active | Compares exact deployment | DeploymentValidationCheck | DeploymentMatchesValidatedRelease |
| recordPostGoLiveVerification() | Release/Validation | production release; smoke/monitor results | Deployment complete | Records success or rollback/incident trigger | PostGoLiveResult | PostGoLiveVerificationCompleted |


# 5. Validation State / Control Model

```text
VALIDATION ARTIFACTS → VSR → TRACE/DEVIATION/SECURITY/DR/PERFORMANCE/CUSTOMER READINESS → APPROVAL → VALIDATED RELEASE AUTH → DEPLOY → POST-GO-LIVE
```

# 6. Data / Evidence Model

`validation_summary_report`: scope, baselines, evidence refs, deviations, limitations, recommendation, signatures/Vault.
`validated_release_authorization`: VSR, artifact digests, schema/migrations, config fingerprint, environment/site, state.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/summary-reports`
- `GET /validation/v1/releases/{id}/go-live-readiness`
- `POST /validation/v1/summary-reports/{id}/approve`
- `POST /validation/v1/releases/{id}/authorize`
- `POST /validation/v1/releases/{id}/deployment-check`

# 8. UI / Validation Workspace

1. Validation Summary
2. Go-Live Checklist
3. Known Limitations
4. Release Authorization
5. Post-Go-Live

# 9. Events

- `ValidationSummaryGenerated`
- `GoLiveReadinessEvaluated`
- `ValidationSummaryApproved`
- `ValidatedReleaseAuthorized`
- `DeploymentMatchesValidatedRelease`
- `PostGoLiveVerificationCompleted`

# 10. Mandatory Test / Evidence Catalogue

- config mismatch
- open critical exception
- expired training
- DR missing
- security critical finding
- post-go-live smoke fail

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

Production promotion is tied to the exact validated release/configuration rather than a general statement that testing was completed.

# 13. Claude Code / Codex Prohibitions

- Never deploy materially different config than VSR baseline without impact assessment.
- Never let release engineer self-authorize validated go-live.
- Never omit known limitations.
- Never authorize unresolved critical blocker.


