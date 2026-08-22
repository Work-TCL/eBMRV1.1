# Testing Strategy

**Derived from:** Document 102 (SPEC-ENG-006) — controlled source in `specs/`
**Purpose:** Test types, risk-driven depth and evidence rules.
**Requirements:** TEST-FR-001..036 (36)

> This file is the working engineering standard. The controlled source is Document 102; where the two
> differ, the specification wins and this file is corrected.

## Requirements

| ID | Requirement | Required behaviour | Acceptance intent |
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

## Enforcement

See `docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md`,
`docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md` and `.github/workflows/ci.yml`.

## Tests

- unit/property rule vectors
- real PostgreSQL repository constraints
- API BOLA negative tests
- outbox duplicate consumer crash scenario
- Temporal replay compatibility
- migration previous-version matrix
- flaky critical test
- CI evidence imported into validation
