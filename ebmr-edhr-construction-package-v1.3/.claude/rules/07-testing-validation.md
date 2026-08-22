# Testing and validation evidence

**Purpose:** Testing and validation evidence for the eBMR/eDHR platform.
**Applicable paths/modules:** see `docs/generated/17_REPOSITORY_STRUCTURE.md`; this rule applies to every
service, the Frappe app, edge and integration code unless a narrower scope is stated below.
**Source documents:** Document 102 (SPEC-ENG-006), Document 82 (SPEC-VAL-004), Document 79 (SPEC-VAL-001), Document 94 (SPEC-VAL-016)
**Source requirement IDs:** TEST-FR-001..036 (36); TST-FR-001..024 (24); VAL-FR-001..028 (28); VEX-FR-001..022 (22)

---

## Required implementation pattern

Test depth is selected by the approved risk class (`docs/generated/28_INTENDED_USE_GXP_RISK_MATRIX.md`),
not by preference. HIGHER-PROCESS-RISK functions require scripted tests, independent review and explicit
negative/failure evidence. Every requirement maps to at least one test; every test maps to a requirement.

## Forbidden patterns

- coverage percentage presented as validation evidence
- deleting or re-running over a failed execution
- changing an assertion to make a test pass
- claiming a test run that did not happen
- marking a requirement verified without an executed test

## Completion checks

traceability updated (`15_TEST_TRACEABILITY_MATRIX.csv`, `29_VALIDATION_TRACEABILITY_MASTER.csv`);
validation impact stated; exceptions raised through Document 94.


## Source requirements (extract)

| ID | Requirement | Required behaviour |
|---|---|---|
| TEST-FR-001 | Test pyramid/portfolio | Use multiple test layers selected by risk; no single coverage metric substitutes for assurance. |
| TEST-FR-002 | Unit tests | Deterministic domain functions, parsers, calculations and state/rule helpers receive fast isolated tests. |
| TEST-FR-003 | Property tests | Calculations, conversions, parsers, idempotency and invariants use property/fuzz testing where valuable. |
| TEST-FR-004 | Rule vectors | Regulated rules/calculations maintain approved table-driven golden vectors including boundary/rounding/UOM cases. |
| TEST-FR-005 | Repository tests | Repository persistence tests verify constraints/versioning/transaction behavior against real database where needed. |
| TEST-FR-006 | API tests | Each operation tests schema, auth, business success, validation errors, expected-version and idempotency. |
| TEST-FR-007 | Contract tests | Provider/consumer compatibility tests for internal/external APIs/events. |
| TEST-FR-008 | Event tests | Outbox/event envelope, duplicate, replay, ordering and poison-event behavior verified. |
| TEST-FR-009 | Integration tests | Real/test-container dependencies used for PostgreSQL, NATS, object storage, Temporal and adapters where fake would miss behavior. |
| TEST-FR-010 | Workflow replay tests | Temporal workflows tested with deterministic replay/version fixtures and time-skipping. |
| TEST-FR-011 | Frappe tests | Projection read-only, permissions, server controller routing and UI action/API mapping tested. |
| TEST-FR-012 | UI component tests | High-risk UI controls verify state, required fields, read-only/source version and safe error display. |
| TEST-FR-013 | End-to-end tests | Critical eBMR/QMS/material/QC/release flows tested across real service boundaries in controlled environment. |
| TEST-FR-014 | Authorization tests | Positive/negative roles, tenant/site scope, SoD and qualification checks automated. |
| TEST-FR-015 | Signature tests | Fresh challenge, incorrect auth, expired nonce, stale record, meaning, manifestation/linking tested. |
| TEST-FR-016 | Audit/Vault tests | Old/new values, append-only, hash chain, canonicalization, corrections and archive retrieval tested. |
| TEST-FR-017 | Concurrency tests | Race, stale version, duplicate request, lock/deadlock/retry conditions tested for contested aggregates. |
| TEST-FR-018 | Failure injection | DB/NATS/Temporal/object/ERP/LIMS/Edge outages and timeout ambiguity tested. |
| TEST-FR-019 | Recovery tests | Restart/crash after each durable boundary verifies correct resume/idempotency. |
| TEST-FR-020 | Security tests | SAST/SCA plus BOLA/injection/SSRF/XSS/CSRF/file/rate/secret/PKI/network tests per Doc92. |
| TEST-FR-021 | Performance tests | Load/soak/capacity tests tied NFRs and qualified scale. |
| TEST-FR-022 | Migration tests | Every migration runs on previous supported schema plus representative data and reconciliation. |
| TEST-FR-023 | Backup/restore tests | Restore/PITR tests verify application-level integrity. |
| TEST-FR-024 | Mutation testing | Selected high-risk pure domain/rules packages may use mutation testing to identify weak tests. |
| TEST-FR-025 | Coverage metrics | Line/branch coverage reported by package but thresholds are risk-tiered; critical function trace coverage matters more. |
| TEST-FR-026 | Critical requirement coverage | Every higher-risk requirement has at least one objective verification link. |
| TEST-FR-027 | No flaky tolerance | Flaky tests quarantined only with owner/issue/expiry; release-critical flakiness is blocker. |
| TEST-FR-028 | Test determinism | Tests control clock/ID/randomness/network and avoid order dependence. |
| TEST-FR-029 | Synthetic data | Test fixtures synthetic/deidentified, stable and versioned; no production secrets/data in repo. |
| TEST-FR-030 | Test isolation | Parallel tests do not share mutable tenant/site/global state unless scenario explicitly exercises concurrency. |
| TEST-FR-031 | Evidence output | Validation-eligible tests emit machine-readable result, environment/build/test IDs and artifacts. |
| TEST-FR-032 | Failure retention | CI/validation preserves failed result; rerun is separate evidence. |
| TEST-FR-033 | Test ownership | Each suite/package has CODEOWNER/maintainer; orphan tests treated as engineering debt. |
| TEST-FR-034 | Test review | Critical tests reviewed when requirement/risk behavior changes, not blindly reused. |
| TEST-FR-035 | Test tagging | Tags classify unit/integration/contract/e2e/security/performance/validation and risk level. |
| TEST-FR-036 | No mock-only critical proof | Mocks can isolate units but cannot be sole proof of DB/broker/crypto/integration semantics. |
| TST-FR-001 | Test methods | Support automated, scripted manual, exploratory, review/inspection, analysis and supplier-evidence verification. |
| TST-FR-002 | Method selection | Risk, complexity, determinism and control drive test method. |
| TST-FR-003 | Versioning | Approved/executed test definition immutable/versioned. |
| TST-FR-004 | Preconditions | Define environment/config/data/roles/dependencies. |

## SPEC_GAP triggers

Raise a SPEC_GAP rather than deciding, if you encounter: a missing signature/authorization/retention/
precision value, a conflict between two source documents, an entity without an owner, an event without a
producer, or any requirement that would need a regulated behaviour you cannot trace to
Document 102, Document 82, Document 79, Document 94 or Documents 106–115.
