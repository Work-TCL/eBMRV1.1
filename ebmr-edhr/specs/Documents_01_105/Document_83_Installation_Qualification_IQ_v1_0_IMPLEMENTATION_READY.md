# US eBMR / eDHR Regulated Manufacturing Platform
## Document 83 — Installation Qualification (IQ) & Installed Baseline Verification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-005  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 65–78, 79–82  
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

Define installation qualification proving the correct approved platform release, infrastructure components and prerequisites are installed before functional qualification.

# 2. Actors / Components

- Installer
- Validation
- SRE
- DBA
- Security
- Customer IT
- QA

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| IQ-FR-001 | Installation scope | Identify installed components, versions, environment topology and responsibilities. | Known installation. |
| IQ-FR-002 | Prerequisites | Verify OS/K8s/runtime/network/DNS/NTP/storage/DB/object/PKI/backups. | Ready environment. |
| IQ-FR-003 | Artifact identity | Verify deployed image/package digest/signature matches approved release. | Correct software. |
| IQ-FR-004 | SBOM/provenance | Reference approved SBOM/build provenance. | Supply-chain. |
| IQ-FR-005 | Configuration baseline | Capture environment/config/feature flags without secret values. | Reproducibility. |
| IQ-FR-006 | Secret/certs | Verify required secret references/cert validity/scope. | Security. |
| IQ-FR-007 | DB/schema | Verify PostgreSQL/MariaDB versions/migrations/schemas. | Persistence. |
| IQ-FR-008 | Object store | Verify encryption/immutability/access/evidence operations. | Evidence. |
| IQ-FR-009 | NATS/Temporal | Verify version/config/auth/storage/namespace. | Platform. |
| IQ-FR-010 | Frappe site | Verify Frappe app/site/migrations. | UI. |
| IQ-FR-011 | Network controls | Verify required and forbidden network paths. | Security. |
| IQ-FR-012 | Time sync | Verify UTC/NTP within approved threshold. | Chronology. |
| IQ-FR-013 | Backup config | Verify backup/PITR/key/monitoring configuration exists. | Recovery. |
| IQ-FR-014 | Observability | Verify critical metrics/logs/alerts registered. | Operations. |
| IQ-FR-015 | Host inventory | Capture nodes/specs/ownership. | Trace. |
| IQ-FR-016 | External endpoints | Verify IdP/ERP/LIMS/Edge endpoint/trust configs in scope. | Integration. |
| IQ-FR-017 | Environment segregation | Verify validation/prod data/secrets/endpoints not mixed. | SDLC. |
| IQ-FR-018 | Exceptions | Mismatches become validation deviations before IQ completion. | No silent variance. |
| IQ-FR-019 | Delta IQ | Upgrade/rebuild supports risk-based delta/full IQ. | Lifecycle. |
| IQ-FR-020 | Automated IQ | Controlled install/preflight automation may generate primary evidence. | Efficiency. |
| IQ-FR-021 | Approval | IQ requires reviewer approval and deviation disposition. | Gate. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createIQProtocol() | Validation/Installer | environment; release; deployment profile; component inventory | Approved release/profile | Creates versioned IQ checks | IQProtocol | IQProtocolCreated |
| captureInstalledInventory() | Qualification agent | environment | Authorized read-only | Collects versions/digests/config fingerprints/hardware refs | InstalledInventory | InstalledInventoryCaptured |
| verifyInstalledArtifact() | IQ executor | component; expected digest/signature/version | Release manifest available | Compares deployment to release | IQCheckResult | InstalledArtifactVerified/ARTIFACT_MISMATCH |
| verifyEnvironmentPrerequisites() | IQ executor | environment/profile | Profile effective | Runs prerequisite/network/time/storage/backup checks | IQCheckSet | IQPrerequisitesVerified |
| completeIQExecution() | Validation executor | IQ run; results; deviations | Mandatory checks complete | Closes PASS/FAIL with evidence manifest | IQResult | IQCompleted |
| approveIQ() | Validation/QA | IQ result; signature | PASS or approved deviations | Freezes IQ evidence/state | ApprovedIQ | IQApproved |


# 5. Validation State / Control Model

```text
APPROVED RELEASE/PROFILE → IQ PROTOCOL → INVENTORY/CONFIG/PREREQUISITE CHECKS → DEVIATIONS → IQ APPROVAL → OQ ELIGIBLE
```

# 6. Data / Evidence Model

`iq_protocol`: environment/release/profile, expected components/checks/acceptance.
`iq_execution`: installed inventory fingerprint, check results, deviations, evidence manifest, approval.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/iq/protocols`
- `POST /validation/v1/iq/executions`
- `POST /validation/v1/iq/executions/{id}/complete`
- `POST /validation/v1/iq/executions/{id}/approve`

# 8. UI / Validation Workspace

1. IQ Protocol
2. Installed Inventory
3. Prerequisite Checks
4. IQ Deviations
5. IQ Approval

# 9. Events

- `InstalledInventoryCaptured`
- `IQPrerequisitesVerified`
- `IQCompleted`
- `IQApproved`

# 10. Mandatory Test / Evidence Catalogue

- wrong image digest
- unsupported DB version
- NTP missing
- backup absent
- cert expired
- forbidden path open
- validation endpoint points to prod ERP

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

The OQ environment can be reproduced from a captured installation baseline and matches the approved release/deployment profile.

# 13. Claude Code / Codex Prohibitions

- Never treat deployment success as IQ success.
- Never record secret values in IQ evidence.
- Never approve unexplained config drift.
- Never use mutable image tag as installed identity.


