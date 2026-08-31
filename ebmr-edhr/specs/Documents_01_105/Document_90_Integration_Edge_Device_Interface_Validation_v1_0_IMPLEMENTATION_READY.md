# US eBMR / eDHR Regulated Manufacturing Platform
## Document 90 — Integration, Edge, Device, Peripheral & Interface Validation — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-012  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 43–53, 73–74, 82–89  
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

Define validation of enterprise integrations, industrial Edge/protocol connections and peripherals including mapping, source identity, offline behavior, retry/idempotency and reconciliation.

# 2. Actors / Components

- Integration Engineer
- Edge Engineer
- Validation
- QA
- Customer IT
- Simulator/Sandbox
- Security

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| IFV-FR-001 | Interface inventory | Every GxP ERP/LIMS/Edge/device/API/file interface identified by owner/version/use. | Complete scope. |
| IFV-FR-002 | Contract version | Validate exact schema/API/event/mapping/profile version. | Contract assurance. |
| IFV-FR-003 | Authentication | Validate mTLS/OAuth/token/cert and unauthorized rejection. | Security. |
| IFV-FR-004 | Data mapping | Source→canonical→GxP field/UOM/status test vectors. | Accuracy. |
| IFV-FR-005 | Source identity | Verify system/device/site/tenant attribution. | Trace. |
| IFV-FR-006 | Timestamp | Verify source/receive time and clock-quality handling. | Chronology. |
| IFV-FR-007 | Quality status | Bad/uncertain/stale/comm-error propagation. | No false good. |
| IFV-FR-008 | Idempotency | Duplicate/replay does not duplicate effect. | Reliability. |
| IFV-FR-009 | Ordering | Out-of-order/stale version handling. | Consistency. |
| IFV-FR-010 | Store-forward | Outage/recovery preserves events with no loss/duplicate GxP effect. | Edge resilience. |
| IFV-FR-011 | Buffer capacity | Expected offline horizon/disk threshold behavior. | Operational. |
| IFV-FR-012 | ERP uncertain commit | Timeout after external commit reconciles before retry. | No duplicate posting. |
| IFV-FR-013 | LIMS result | Wrong sample/method/spec/version rejected. | Lab integrity. |
| IFV-FR-014 | Barcode/balance | Wrong identity/unstable/calibration/manual fallback behavior. | Peripheral. |
| IFV-FR-015 | PLC/SCADA | Wrong mapping/program/context/quality blocked. | Machine evidence. |
| IFV-FR-016 | Machine command | If enabled test allowlist/signature/interlock/readback; otherwise verify disabled. | Safety. |
| IFV-FR-017 | File transfer | Checksum/schema/duplicate/ack/rejection tested. | Batch integration. |
| IFV-FR-018 | Schema evolution | Compatible/breaking contract changes tested. | Lifecycle. |
| IFV-FR-019 | Security abuse | Replay/spoof invalid cert/webhook tests. | Security. |
| IFV-FR-020 | Recovery | Adapter/gateway restart resumes correctly. | Reliability. |
| IFV-FR-021 | Reconciliation | External/internal transaction/master-data reconciliation. | Completeness. |
| IFV-FR-022 | Failure visibility | Failure appears in operations/QA review as intended. | No silent failure. |
| IFV-FR-023 | Simulator | Controlled simulators reproduce failures and edge cases. | Repeatability. |
| IFV-FR-024 | Customer delta | Customer interface configuration receives delta qualification. | Deployment. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createInterfaceValidationProfile() | Integration/Validation | interface; version; intended use; mappings; failure modes | Contract approved | Creates validation scope | InterfaceValidationProfile | InterfaceValidationProfileCreated |
| executeInterfaceContractTests() | CI/Validation | profile; simulator/sandbox; environment | Endpoint available | Runs auth/schema/mapping/idempotency/error tests | InterfaceTestRun | InterfaceContractTestsCompleted |
| executeEdgeOutageQualification() | Validation/Edge | gateway/profile; outage duration/load | Gateway qualified | Disconnects, generates, reconnects and reconciles IDs/sequence/hash | EdgeOutageTest | EdgeOutageQualificationCompleted |
| verifyExternalReconciliation() | Validation | interface transactions; external records | Readback available | Compares expected/external effects | InterfaceReconciliation | InterfaceReconciliationVerified |
| approveInterfaceQualification() | Validation/QA | profile/results/deviations | Critical tests passed | Freezes interface qualification | InterfaceQualification | InterfaceQualificationApproved |


# 5. Validation State / Control Model

```text
INTERFACE CONTRACT → AUTH/SCHEMA/MAPPING → HAPPY/NEGATIVE/DUPLICATE/OUTAGE/RECOVERY → READBACK/RECONCILIATION → QUALIFIED INTERFACE
```

# 6. Data / Evidence Model

`interface_validation_profile`: provider/device, contract/mapping versions, intended use/risk, auth/source/time/quality expectations, failure scenarios.
`interface_test_execution`: inputs/raw payloads, canonical outputs, GxP results, external reconciliation.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/interfaces/profiles`
- `POST /validation/v1/interfaces/tests`
- `POST /validation/v1/interfaces/edge-outage-tests`
- `POST /validation/v1/interfaces/{id}/approve`

# 8. UI / Validation Workspace

1. Interface Inventory
2. Contract Tests
3. Edge Offline
4. Device Tests
5. Reconciliation
6. Qualification

# 9. Events

- `InterfaceContractTestsCompleted`
- `EdgeOutageQualificationCompleted`
- `InterfaceReconciliationVerified`
- `InterfaceQualificationApproved`

# 10. Mandatory Test / Evidence Catalogue

- duplicate ERP receipt
- wrong LIMS sample
- 72h Edge outage synthetic
- bad OPC quality
- unstable balance
- wrong barcode
- spoofed webhook
- command disabled

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

A GxP-relevant external/plant source can be proven to deliver the correct attributable data/business effect under normal, duplicate, invalid, delayed and outage conditions.

# 13. Claude Code / Codex Prohibitions

- Never validate only happy path.
- Never rely on vendor sandbox without reconciliation.
- Never map timeout to zero/good.
- Never enable machine write merely to test.


