# US eBMR / eDHR Regulated Manufacturing Platform
## Document 81 — Requirements, Design Inputs & Validation Traceability Management — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-003  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 01–80; all module specifications  
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

Define the authoritative requirement and traceability graph linking source specifications, risks, functions, APIs, schemas, tests, failures and release baselines.

# 2. Actors / Components

- Validation
- Engineering
- QA
- Product Owner
- Claude Code ingestion process
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| REQ-FR-001 | Requirement registry | Ingest all stable requirements with source document/ID/version. | Single registry. |
| REQ-FR-002 | Requirement types | Classify business/GxP/security/data/interface/performance/validation/config requirements. | Coverage. |
| REQ-FR-003 | Testability | Requirement must be verifiable or explicitly rationale-based design constraint. | Quality. |
| REQ-FR-004 | Acceptance criteria | Critical requirements include objective acceptance criteria. | No vague pass. |
| REQ-FR-005 | Regulatory source | Derived requirement stores source and binding/guidance status. | Explainability. |
| REQ-FR-006 | Risk link | Requirement links risk/intended-use function assessment. | Risk trace. |
| REQ-FR-007 | Design link | Requirement maps function/service/API/schema/UI/config artifact. | Design trace. |
| REQ-FR-008 | Test link | Requirement maps tests/evidence or justified alternative verification. | Evidence. |
| REQ-FR-009 | Defect link | Failed evidence links defect/deviation. | Closure. |
| REQ-FR-010 | Release baseline | Release identifies exact requirement versions in scope. | Configuration control. |
| REQ-FR-011 | Supersession | Superseded requirements remain retained/versioned. | History. |
| REQ-FR-012 | Change impact | Requirement change identifies affected design/tests/risk/docs. | Efficient revalidation. |
| REQ-FR-013 | Bidirectional trace | Navigate requirement→test and test→requirements. | Inspection. |
| REQ-FR-014 | Orphan detection | Detect unimplemented/untested critical requirements and orphan tests. | Completeness. |
| REQ-FR-015 | Coverage metrics | Coverage by risk/module/profile visible but percentage not sole release criterion. | Visibility. |
| REQ-FR-016 | Function catalogue link | Claude-generated function contracts become design trace targets. | Construction. |
| REQ-FR-017 | API/event/schema trace | OpenAPI/AsyncAPI/DB migration entries map requirement IDs. | Technical trace. |
| REQ-FR-018 | Automated metadata | Test code/results carry stable test/requirement IDs. | Repeatability. |
| REQ-FR-019 | Customer URS | Customer-specific URS layers on product requirements without overwriting vendor baseline. | Commercial. |
| REQ-FR-020 | SPEC_GAP | SPEC_GAP tracked as unresolved requirement/design issue and release blocker by severity. | No guessing. |
| REQ-FR-021 | Baseline freeze | Freeze requirement set/version/hash for validation/release. | Controlled. |
| REQ-FR-022 | Export | Traceability export CSV/PDF/JSON generated from authoritative graph. | Inspection. |
| REQ-FR-023 | No spreadsheet authority | Spreadsheet is export, not authoritative traceability source. | Integrity. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| ingestRequirement() | Spec ingestion/Validation | source_doc; req_id; version; text; classification | Stable source ID | Creates/version-controls requirement | RequirementVersion | RequirementIngested |
| linkRequirementToDesign() | Engineering/Extractor | requirement; function/API/schema/artifact ref | Artifacts exist | Creates typed trace link | TraceLink | RequirementDesignLinked |
| linkRequirementToTest() | Validation | requirement; test/version; coverage type | Both exist/current | Creates verification link | TraceLink | RequirementTestLinked |
| freezeRequirementBaseline() | Validation Lead | release/scope; versions; exclusions | Approvals/risk current | Creates immutable baseline/hash | RequirementBaseline | RequirementBaselineFrozen |
| detectTraceabilityGaps() | Release gate | baseline; risk rules | Baseline exists | Finds orphan/missing/obsolete links | TraceabilityGapReport | TraceabilityGapDetected |
| generateTraceabilityMatrix() | Validation/Inspection | baseline/release; format | Trace graph available | Produces bidirectional trace matrix | TraceabilityMatrix | TraceabilityMatrixGenerated |


# 5. Validation State / Control Model

```text
SOURCE REQUIREMENT → VERSION → RISK + DESIGN/FUNCTION/API/SCHEMA + TEST/EVIDENCE + DEFECT → RELEASE BASELINE
```

# 6. Data / Evidence Model

`validation_requirement`: stable code, source doc/version/section, text, class, regulatory source, current version.
`trace_link`: source artifact/version → target artifact/version + relation type.
`requirement_baseline`: release/customer scope, requirement version list, exclusions/rationale, hash/Vault ref.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/requirements:ingest`
- `POST /validation/v1/trace-links`
- `POST /validation/v1/baselines`
- `GET /validation/v1/traceability`
- `GET /validation/v1/traceability/gaps`

# 8. UI / Validation Workspace

1. Requirement Registry
2. Design Trace
3. Test Trace
4. Gaps
5. Baseline Freeze
6. Traceability Export

# 9. Events

- `RequirementIngested`
- `RequirementBaselineFrozen`
- `TraceabilityGapDetected`
- `TraceabilityMatrixGenerated`

# 10. Mandatory Test / Evidence Catalogue

- orphan critical requirement
- test to superseded requirement
- API change impact
- customer URS layer
- critical SPEC_GAP

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

Claude Code and Validation can produce reproducible requirement-to-code-to-test-to-release traceability without a separately maintained spreadsheet.

# 13. Claude Code / Codex Prohibitions

- Never renumber stable IDs casually.
- Never delete superseded requirements.
- Never treat 100% link coverage as proof of test adequacy.
- Never make spreadsheet the only traceability source.


