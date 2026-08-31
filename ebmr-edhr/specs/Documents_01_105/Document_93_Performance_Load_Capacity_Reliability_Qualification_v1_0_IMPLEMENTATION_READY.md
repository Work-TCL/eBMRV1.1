# US eBMR / eDHR Regulated Manufacturing Platform
## Document 93 — Performance, Load, Capacity & Reliability Qualification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-VAL-015  
**Parent Documents:** Documents 01–78  
**Primary Dependencies:** Documents 70–78, 82–92  
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

Define qualification of the operating envelope under realistic enterprise load, including latency, throughput, audit/event volume, Edge catch-up, soak, failover and headroom.

# 2. Actors / Components

- Performance Engineer
- SRE
- DBA
- Validation
- System Owner
- Edge Engineer

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| PERFQ-FR-001 | Load model | Use target users/plants/batches/steps/audit/device event assumptions. | Representative scale. |
| PERFQ-FR-002 | Critical latency | Measure mutation/read/sign/review/release p50/p95/p99. | Responsiveness. |
| PERFQ-FR-003 | Throughput | Measure sustainable mutation/audit/outbox/event rates. | Capacity. |
| PERFQ-FR-004 | Concurrent users | Test target role mix and concurrency. | Enterprise. |
| PERFQ-FR-005 | Batch scale | Test thousands of steps/batch and simultaneous batches. | eBMR. |
| PERFQ-FR-006 | Audit scale | Test millions audit/day equivalent/bursts. | Data scale. |
| PERFQ-FR-007 | Event lag | Outbox/NATS consumer lag under burst/recovery. | Async. |
| PERFQ-FR-008 | Edge catch-up | Configured long offline backlog catch-up without core overload. | Plant. |
| PERFQ-FR-009 | Object evidence | Large upload/download/manifest performance. | Storage. |
| PERFQ-FR-010 | Search/report isolation | Heavy reads do not starve critical execution. | Read layer. |
| PERFQ-FR-011 | Signature latency | Fresh step-up/signature transaction measured. | Critical UX. |
| PERFQ-FR-012 | DB saturation | Monitor connection/WAL/locks/IO/bloat under load. | Bottleneck. |
| PERFQ-FR-013 | Autoscaling | Stateless scaling and DB-pool limits verified. | Elasticity. |
| PERFQ-FR-014 | Backpressure | Overload is bounded, not data loss/crash. | Resilience. |
| PERFQ-FR-015 | Soak | Long duration catches leaks/growth/partition issues. | Stability. |
| PERFQ-FR-016 | Failover under load | Selected DB/broker/worker failure tests. | Resilience. |
| PERFQ-FR-017 | Graceful degradation | Dependency outages follow capability matrix. | Availability. |
| PERFQ-FR-018 | Headroom | Identify validated capacity/headroom/scaling trigger. | Sizing. |
| PERFQ-FR-019 | On-prem sizing | Translate results to hardware profile. | Commercial deployment. |
| PERFQ-FR-020 | Regression | Baseline performance versioned by release. | Quality. |
| PERFQ-FR-021 | NFR trace | Thresholds link NFR/SLO requirement IDs. | Trace. |
| PERFQ-FR-022 | Production-equivalent durability | Use real fsync/WAL/audit/security settings. | Validity. |
| PERFQ-FR-023 | Data volume realism | Use representative table/index cardinality. | Realism. |
| PERFQ-FR-024 | Approval | Approved envelope/limitations retained. | Transparency. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createPerformanceQualificationScenario() | Performance/Validation | workload; NFRs/SLOs; environment; duration | Environment qualified | Creates versioned scenario | PerformanceScenario | PerformanceScenarioCreated |
| executePerformanceQualification() | Load harness | scenario; synthetic data; release/config fingerprint | Environment stable | Runs workload/failure and captures metrics/traces | PerformanceRun | PerformanceQualificationExecuted |
| evaluatePerformanceAcceptance() | Performance/Validation | run; thresholds | Run complete | Computes pass/fail/headroom/bottleneck | PerformanceQualificationResult | PerformanceAcceptanceEvaluated |
| deriveDeploymentSizing() | Capacity service | qualified results; customer load | Comparable model | Produces sizing with assumptions | DeploymentSizingProfile | DeploymentSizingDerived |
| approvePerformanceQualification() | Validation/SRE/System Owner | results; limitations; deviations | Criteria met | Freezes performance envelope | PerformanceQualification | PerformanceQualificationApproved |


# 5. Validation State / Control Model

```text
QUALIFIED ENV + WORKLOAD MODEL → LOAD/STRESS/SOAK/FAILURE → METRICS → NFR/SLO EVALUATION → HEADROOM/SIZING → APPROVE
```

# 6. Data / Evidence Model

`performance_qualification_scenario`: release/environment, user/process load, data cardinality, duration, failures, thresholds.
`performance_run`: build/config, harness, metrics/traces/errors/resources, headroom/bottleneck.

# 7. APIs / Internal Interfaces

- `POST /validation/v1/performance/scenarios`
- `POST /validation/v1/performance/runs`
- `POST /validation/v1/performance/{id}/evaluate`
- `GET /validation/v1/performance/sizing`

# 8. UI / Validation Workspace

1. Performance Scenarios
2. Load Results
3. SLO Acceptance
4. Bottlenecks
5. Sizing
6. Regression

# 9. Events

- `PerformanceQualificationExecuted`
- `PerformanceAcceptanceEvaluated`
- `DeploymentSizingDerived`
- `PerformanceQualificationApproved`

# 10. Mandatory Test / Evidence Catalogue

- 250 concurrent
- several-thousand-step batch
- millions audit/day
- long Edge catch-up
- DB failover
- NATS outage
- soak
- heavy report

# 11. Failure / Recovery

- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

# 12. Acceptance Criteria

The reference architecture has a measured operating envelope and sizing model without relaxing durability, audit or security controls.

# 13. Claude Code / Codex Prohibitions

- Never benchmark with fsync/audit/security disabled.
- Never use empty DB as sole proof.
- Never promise unlimited scale.
- Never hide p99 failure behind average.


