# US eBMR / eDHR Regulated Manufacturing Platform
## Document 102 — Testing Strategy — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-ENG-006  
**Parent Documents:** Documents 01–96  
**Primary Dependencies:** Documents 03–96, 97–101, 103  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This document is a normative engineering-control source for Claude Code/Codex and human developers.

Every implementation must preserve:
- stable requirement IDs;
- explicit function input/output/error contracts;
- authorization/SoD/signature behavior;
- data owner and transaction boundaries;
- API/event schema and compatibility;
- validation/test evidence;
- security/dependency/license controls;
- actual rather than claimed CI/release evidence.

Where regulated behavior is not specified, create a `SPEC_GAP` and block the guess.

# Cross-Document Non-Negotiables

- Frappe/ERPNext core remains unmodified.
- GxP-authoritative writes flow through proprietary services/Mutation Gateway.
- No generic CRUD of released regulated records.
- No signature, authorization, audit, retention, data-owner or validation bypass.
- PostgreSQL is GxP authority; MariaDB/read models/cache/search/message/orchestration are not competing sources of truth.
- Transactional outbox/idempotent consumers are used where specified.
- Production release must match approved validated release authorization.
- AI remains advisory unless a future explicitly approved controlled specification authorizes a different risk class.

# 1. Objective

Define engineering test layers, risk-based minimum assurance, CI evidence, failure/concurrency testing and reuse of trustworthy engineering tests as validation evidence.

# 2. Actors / Components

- Developer
- Test Engineer
- Validation
- CI
- Security
- Performance Engineer
- Claude Code/Codex
- Reviewer

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| TEST-FR-001 | Test pyramid/portfolio | Use multiple test layers selected by risk; no single coverage metric substitutes for assurance. | Balanced quality. |
| TEST-FR-002 | Unit tests | Deterministic domain functions, parsers, calculations and state/rule helpers receive fast isolated tests. | Fast feedback. |
| TEST-FR-003 | Property tests | Calculations, conversions, parsers, idempotency and invariants use property/fuzz testing where valuable. | Edge-case confidence. |
| TEST-FR-004 | Rule vectors | Regulated rules/calculations maintain approved table-driven golden vectors including boundary/rounding/UOM cases. | Accuracy. |
| TEST-FR-005 | Repository tests | Repository persistence tests verify constraints/versioning/transaction behavior against real database where needed. | Data correctness. |
| TEST-FR-006 | API tests | Each operation tests schema, auth, business success, validation errors, expected-version and idempotency. | Contract correctness. |
| TEST-FR-007 | Contract tests | Provider/consumer compatibility tests for internal/external APIs/events. | Integration stability. |
| TEST-FR-008 | Event tests | Outbox/event envelope, duplicate, replay, ordering and poison-event behavior verified. | Async correctness. |
| TEST-FR-009 | Integration tests | Real/test-container dependencies used for PostgreSQL, NATS, object storage, Temporal and adapters where fake would miss behavior. | System confidence. |
| TEST-FR-010 | Workflow replay tests | Temporal workflows tested with deterministic replay/version fixtures and time-skipping. | Upgrade safety. |
| TEST-FR-011 | Frappe tests | Projection read-only, permissions, server controller routing and UI action/API mapping tested. | Framework boundary. |
| TEST-FR-012 | UI component tests | High-risk UI controls verify state, required fields, read-only/source version and safe error display. | UX correctness. |
| TEST-FR-013 | End-to-end tests | Critical eBMR/QMS/material/QC/release flows tested across real service boundaries in controlled environment. | Business confidence. |
| TEST-FR-014 | Authorization tests | Positive/negative roles, tenant/site scope, SoD and qualification checks automated. | Security/GxP. |
| TEST-FR-015 | Signature tests | Fresh challenge, incorrect auth, expired nonce, stale record, meaning, manifestation/linking tested. | Part 11. |
| TEST-FR-016 | Audit/Vault tests | Old/new values, append-only, hash chain, canonicalization, corrections and archive retrieval tested. | Data integrity. |
| TEST-FR-017 | Concurrency tests | Race, stale version, duplicate request, lock/deadlock/retry conditions tested for contested aggregates. | No lost updates. |
| TEST-FR-018 | Failure injection | DB/NATS/Temporal/object/ERP/LIMS/Edge outages and timeout ambiguity tested. | Resilience. |
| TEST-FR-019 | Recovery tests | Restart/crash after each durable boundary verifies correct resume/idempotency. | Reliability. |
| TEST-FR-020 | Security tests | SAST/SCA plus BOLA/injection/SSRF/XSS/CSRF/file/rate/secret/PKI/network tests per Doc92. | Security. |
| TEST-FR-021 | Performance tests | Load/soak/capacity tests tied NFRs and qualified scale. | Performance. |
| TEST-FR-022 | Migration tests | Every migration runs on previous supported schema plus representative data and reconciliation. | Upgrade safety. |
| TEST-FR-023 | Backup/restore tests | Restore/PITR tests verify application-level integrity. | DR. |
| TEST-FR-024 | Mutation testing | Selected high-risk pure domain/rules packages may use mutation testing to identify weak tests. | Test quality. |
| TEST-FR-025 | Coverage metrics | Line/branch coverage reported by package but thresholds are risk-tiered; critical function trace coverage matters more. | Useful metrics. |
| TEST-FR-026 | Critical requirement coverage | Every higher-risk requirement has at least one objective verification link. | Validation. |
| TEST-FR-027 | No flaky tolerance | Flaky tests quarantined only with owner/issue/expiry; release-critical flakiness is blocker. | Reliable CI. |
| TEST-FR-028 | Test determinism | Tests control clock/ID/randomness/network and avoid order dependence. | Repeatability. |
| TEST-FR-029 | Synthetic data | Test fixtures synthetic/deidentified, stable and versioned; no production secrets/data in repo. | Privacy. |
| TEST-FR-030 | Test isolation | Parallel tests do not share mutable tenant/site/global state unless scenario explicitly exercises concurrency. | Stability. |
| TEST-FR-031 | Evidence output | Validation-eligible tests emit machine-readable result, environment/build/test IDs and artifacts. | CSA reuse. |
| TEST-FR-032 | Failure retention | CI/validation preserves failed result; rerun is separate evidence. | Integrity. |
| TEST-FR-033 | Test ownership | Each suite/package has CODEOWNER/maintainer; orphan tests treated as engineering debt. | Governance. |
| TEST-FR-034 | Test review | Critical tests reviewed when requirement/risk behavior changes, not blindly reused. | Validated state. |
| TEST-FR-035 | Test tagging | Tags classify unit/integration/contract/e2e/security/performance/validation and risk level. | Selective execution. |
| TEST-FR-036 | No mock-only critical proof | Mocks can isolate units but cannot be sole proof of DB/broker/crypto/integration semantics. | Real behavior. |

# 4. Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB or artifact effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| deriveRequiredTestSet() | CI/Change impact | changed requirements/functions/files; risk matrix | Trace graph current | Returns required unit/contract/integration/security/validation suites | RequiredTestSet | RequiredTestsDerived |
| runUnitTestSuite() | CI | package; commit; test profile | Build successful | Executes isolated tests, records JUnit-equivalent results | TestRun | UnitTestsCompleted |
| runIntegrationTestEnvironment() | CI | suite; container/service versions; config | Ephemeral dependencies provisioned | Executes real-boundary tests and captures logs/metrics | IntegrationTestRun | IntegrationTestsCompleted |
| runConcurrencyScenario() | CI/Performance | scenario; worker count; seed; target function | Test data isolated | Runs synchronized competing operations and verifies versions/idempotency/invariants | ConcurrencyResult | ConcurrencyScenarioCompleted |
| runFailureInjectionScenario() | Resilience test | dependency; failure mode; duration; expected behavior | Safe test environment | Injects failure and verifies fail-closed/retry/recovery | FailureInjectionResult | FailureInjectionCompleted |
| importTestRunAsValidationEvidence() | Validation integration | CI run ID; test IDs; build/environment fingerprint | Run trusted and tests mapped to validation | Creates immutable evidence links without altering CI result | ValidationEvidenceImport | EngineeringEvidenceImported |
| detectFlakyTest() | CI analytics | test history; threshold/policy | Sufficient run history | Flags inconsistent outcome and blocks/quarantines per policy | FlakyTestFinding | FlakyTestDetected |
| evaluateTestReleaseGate() | Release CI | required test set; runs; exceptions | Current commit/release | Returns PASS/BLOCK with missing/failed/flaky suites | TestGateDecision | TestReleaseGateEvaluated |

# 5. Test Layer Matrix

| Layer | Primary purpose | Typical dependencies | Validation reuse |
|---|---|---|---|
| Unit | pure function/invariant | none/fakes | yes where traceable |
| Property/Fuzz | input/invariant edge cases | pure/test harness | yes |
| Repository | DB constraints/transactions | real PostgreSQL/MariaDB | yes |
| API | transport/auth/domain contract | service + DB | yes |
| Contract | producer/consumer compatibility | contracts/stubs/provider | yes |
| Integration | actual service infrastructure | DB/NATS/object/Temporal | yes |
| E2E | critical business workflow | integrated stack | yes |
| Security | abuse/threat controls | integrated/security harness | yes |
| Performance | load/soak/failure envelope | production-like | yes |
| IQ/OQ/PQ | qualified intended-use evidence | controlled validation env | authoritative validation evidence |


# 6. Risk-Based Coverage Rules

Suggested baseline, subject to Document 80 risk classification:

**Higher-risk**
- deterministic unit/property tests where possible;
- API/domain positive + negative;
- authorization/state/concurrency/failure tests;
- integration or E2E evidence for critical path;
- explicit requirement trace;
- independent validation review/evidence as required.

**Standard-risk**
- appropriate automated unit/API/UI tests;
- selected integration;
- exploratory/manual evidence when justified.

Coverage percentages are diagnostics, not a regulatory conclusion.

# 7. Test Evidence Envelope

```json
{
  "test_run_id":"uuid",
  "commit":"sha",
  "release_candidate":"...",
  "environment_fingerprint":"sha256:...",
  "runner_image_digest":"sha256:...",
  "suite_version":"...",
  "started_at":"...",
  "completed_at":"...",
  "results_ref":"...",
  "artifact_manifest_ref":"..."
}
```

# 8. Required Critical Scenarios

At minimum the engineering catalogue shall include stable IDs for:
- duplicate Mutation Gateway command;
- stale expected version;
- two QA decisions racing;
- signature challenge expiry/replay;
- audit event tampering;
- outbox publish acknowledgement loss;
- consumer crash after effect before ack;
- ERP timeout after commit;
- Edge offline buffer/reconnect;
- object evidence hash mismatch;
- migration partial failure/restart;
- database failover/restore;
- cross-tenant object access attempt.

# 9. Mandatory Test / Enforcement Catalogue

- unit/property rule vectors
- real PostgreSQL repository constraints
- API BOLA negative tests
- outbox duplicate consumer crash scenario
- Temporal replay compatibility
- migration previous-version matrix
- flaky critical test
- CI evidence imported into validation

# 10. Acceptance Criteria

Every higher-risk function has reproducible engineering tests that exercise its critical invariants and failure modes, and trustworthy results can flow directly into validation traceability.

# 11. Claude Code / Codex Prohibitions

- Never pursue coverage percentage by meaningless tests.
- Never use mocks as sole proof of database/broker/security semantics.
- Never auto-rerun failed test until green without preserving first result.
- Never disable critical test because it is slow without replacement assurance.
