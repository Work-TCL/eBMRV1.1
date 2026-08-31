# Claude Code prompt — WP-00 / Document 97: Coding Standards

TASK:
Implement the Coding Standards module (SPEC-ENG-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_97_Coding_Standards_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: CODE-FR-001..036 (36)
- Approved baselines: Document 106 (signature policy), 107 (SoD), 108 (retention), 109 (SLO/RPO),
  110 (precision/UOM), 111 (risk class), 112 (schemas/migrations), 113 (contracts), 114 (glossary)
- Phase-0 artefacts: `docs/generated/03_FUNCTION_CATALOGUE.csv`, `04_DATA_MODEL_CATALOGUE.md`,
  `05_DATABASE_OWNERSHIP_MATRIX.md`, `06_API_CATALOGUE.yaml`, `07_EVENT_CATALOGUE.yaml`,
  `14_ERROR_CODE_REGISTRY.md`, `28_INTENDED_USE_GXP_RISK_MATRIX.md`

RISK CLASS: **HIGHER-PROCESS-RISK** → scripted tests, independent review, mandatory negative and failure evidence

ARCHITECTURE CONSTRAINTS:
- Frappe is UI/configuration only; no core fork or edit.
- PostgreSQL is authoritative for regulated state; MariaDB holds read-only projections.
- Every regulated write goes through the Mutation Gateway → one PostgreSQL transaction carrying
  domain state + record version + audit event + outbox event.
- Signatures follow Document 04 + the approved Document 106 policy; login/MFA is never a signature.
- Audit, vault and evidence history is append-only and superseding.
- Outbox is the authoritative event source; NATS is transport; Temporal is orchestration only.
- Caches, projections, search and reports are rebuildable and never a regulated decision source.
- Adapters and edge never write GxP tables; they submit integration commands.
- AI is advisory; it cannot sign, release, disposition, approve, alter audit or submit reports.

PRECONDITIONS:
- WP-00 foundations exist (contracts tooling, guardrails, CI gates).

- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `tooling` and its tests
- `contracts/` entries owned by this module
- migrations for entities owned by this module
- Frappe UI surfaces for this module in `apps/ebmr_frappe/`

DO NOT:
- Do not modify anything under `specs/`.
- Do not implement a signature requirement not present in the approved Document 106 policy set
  (emit a policy row and reference the gap instead).
- Do not create a second authoritative store for an entity owned elsewhere.
- Do not add an endpoint to a module whose exposure boundary is "no independent API" (Document 113 §6).
- Do not write a migration for an entity absent from `docs/generated/04_DATA_MODEL_CATALOGUE.md`.
- Do not use binary floating point for a regulated quantity.
- Do not fabricate a test run, scan result or qualification record.
- Do not start work in another work package.

FILES TO CREATE/MODIFY:
```text
tooling/src/            # domain services, command handlers, repositories
tooling/migrations/     # owned entities only
tooling/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-eng-001.yaml
contracts/events/spec-eng-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-eng-001/
```

REQUIREMENTS TO IMPLEMENT (36):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| CODE-FR-001 | Language baselines | Use pinned supported Python/Frappe, Node.js LTS/TypeScript and SQL versions defined by release toolchain; never code against floating latest. | Reproducible builds. |
| CODE-FR-002 | TypeScript strictness | Enable strict TypeScript with noUncheckedIndexedAccess/exactOptionalPropertyTypes or documented equivalent; any requires narrow justified exception. | Type safety. |
| CODE-FR-003 | Python typing | Public Python services/functions use type hints; data structures use typed models/dataclasses/Pydantic-style validation as architecture permits. | Clarity. |
| CODE-FR-004 | Naming | Use domain-specific names; avoid vague manager/helper/util names for regulated concepts. | Maintainability. |
| CODE-FR-005 | Module size | Split modules by cohesive responsibility; avoid god classes/services and cross-domain utility dumping grounds. | Architecture. |
| CODE-FR-006 | Function contract | Public/domain functions declare typed inputs/outputs, errors and side effects; hidden DB/network behavior prohibited. | Predictability. |
| CODE-FR-007 | Pure domain logic | Calculations/rules/state-transition logic kept deterministic and independently testable where feasible. | Validation. |
| CODE-FR-008 | Decimal arithmetic | Use Decimal/NUMERIC-compatible types for regulated values; binary floating point prohibited for regulated calculations unless raw measurement semantics require it. | Accuracy. |
| CODE-FR-009 | UOM | Quantities carry explicit UOM and conversion provenance; unitless magic numbers prohibited. | Safety. |
| CODE-FR-010 | Time | Persist UTC timestamptz/timezone-aware datetimes; naive datetime prohibited in regulated code. | Chronology. |
| CODE-FR-011 | Identifiers | Use stable immutable IDs; external/business IDs are data, not DB ownership keys. | Traceability. |
| CODE-FR-012 | Errors | Use typed/stable domain error codes; do not branch application logic on exception message strings. | Contract stability. |
| CODE-FR-013 | No swallowed errors | Catch only errors that can be handled; preserve cause/correlation; silent catch prohibited. | Failure visibility. |
| CODE-FR-014 | Logging | Structured logs use correlation/tenant/site/service/operation fields; secrets and unnecessary PII/GxP payloads redacted. | Observability/security. |
| CODE-FR-015 | Comments | Comments explain why/invariant/regulatory reasoning, not restate obvious code; TODOs require issue/spec reference. | Maintainability. |
| CODE-FR-016 | Requirement tags | Regulated/high-risk implementation and tests reference stable requirement/function IDs in metadata/comments where tooling expects. | Traceability. |
| CODE-FR-017 | No core edits | Custom Frappe/ERPNext behavior implemented only in proprietary apps/hooks/adapters. | Upgrade safety. |
| CODE-FR-018 | Frappe controller boundary | Frappe UI/controller calls GxP APIs for regulated mutations; direct PostgreSQL GxP access prohibited. | Data ownership. |
| CODE-FR-019 | ORM boundaries | Repositories belong to bounded context; no generic cross-schema ActiveRecord-style access. | Service isolation. |
| CODE-FR-020 | SQL parameters | All dynamic values parameterized; string-concatenated SQL from request/config prohibited. | Injection defense. |
| CODE-FR-021 | Transaction scope | Transactions are short and deterministic; no user think-time or external HTTP calls while open. | Availability. |
| CODE-FR-022 | Idempotency | Retryable commands/integrations use explicit idempotency keys/receipts as specified. | Distributed correctness. |
| CODE-FR-023 | Concurrency | Expected-version/locking semantics explicit for contested regulated aggregates. | No lost update. |
| CODE-FR-024 | Events | Events use canonical schemas and outbox; direct ad-hoc publish after DB write prohibited for authoritative business events. | Reliability. |
| CODE-FR-025 | Security defaults | Authorization server-side, input schemas strict, outbound destinations controlled, sensitive output minimized. | Secure coding. |
| CODE-FR-026 | Feature flags | Flags have owner/default/expiry; GxP behavior flags are controlled config, not developer backdoors. | Validated state. |
| CODE-FR-027 | Configuration | No environment-specific constants/secrets in source; use typed validated config. | Portability. |
| CODE-FR-028 | Dependency injection | External services/clock/ID providers injected at boundaries to enable deterministic tests. | Testability. |
| CODE-FR-029 | No arbitrary execution | No customer-configured eval/exec/dynamic SQL/template code in regulated runtime. | RCE prevention. |
| CODE-FR-030 | Generated code | Generated clients/schemas live in designated folders and are regenerated from contract source; manual edits rejected. | Contract authority. |
| CODE-FR-031 | Formatting/lint | Formatting/lint/type checks mandatory in CI with version-pinned configuration. | Consistency. |
| CODE-FR-032 | Dead code | Remove unused code/flags after controlled deprecation; commented-out production code prohibited. | Clarity. |
| CODE-FR-033 | Public API docs | Public/internal service operations documented via OpenAPI/AsyncAPI/function catalog, not tribal knowledge. | Maintainability. |
| CODE-FR-034 | Repository test co-location | Tests follow documented module convention and stable IDs; critical logic cannot be untestable private spaghetti. | Assurance. |
| CODE-FR-035 | Sensitive comparison | Use constant-time primitives where comparing secrets/tokens/signatures as appropriate. | Security. |
| CODE-FR-036 | File handling | Paths/filenames untrusted; evidence storage APIs used rather than arbitrary filesystem persistence. | Security/data integrity. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| lintSourceFile() | Pre-commit/CI | file_path; language; coding_profile_version | LintResult | CodingStandardViolation |
| typeCheckPackage() | CI | package_path; tsconfig/python typing profile | TypeCheckReport | TypeCheckFailed |
| validateRegulatedNumericUsage() | CI semantic rule | AST/source files; regulated module catalogue | NumericSafetyReport | RegulatedFloatUsageDetected |
| validateFrappeBoundary() | CI architecture rule | Python/JS import/call graph | BoundaryReport | FrappeBoundaryViolation |
| validateLoggingStatement() | Static/runtime test | logging call; redaction policy | LoggingCheck | SensitiveLoggingViolation |
| validateDomainErrorRegistry() | CI | source error codes; registry | ErrorRegistryReport | UnregisteredDomainError |
| scanForbiddenConstructs() | CI | repo; policy version | ForbiddenConstructReport | ForbiddenConstructDetected |
| generateCodingComplianceReport() | Release CI | all lint/type/security/architecture results | CodingComplianceReport | CodingComplianceGenerated |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (0 entities owned by this module):
_none declared in the source specifications_

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (0):
_none declared in the source specifications_

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- none declared

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
Fail closed on any compliance-critical dependency outage; no degraded-mode commit.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- TypeScript strict compilation
- Python typing/static checks
- float arithmetic rejection in regulated calculation module
- direct GxP DB access from Frappe blocked
- secret-in-log negative test
- dynamic SQL/eval forbidden scan
- transaction/external-call code review rule
- generated client drift test
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-00/Document_97_SPEC-ENG-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-ENG-001/<test_case_id>/`.
- A failed case is evidence: never delete it, re-run over it, or edit the expected result to make it pass.
  Raise a defect, record the reference, re-execute as a new dated execution.

TRACEABILITY & STATUS (mandatory at the end of this prompt):
- Update `traceability/TRACEABILITY_MASTER.csv` for every requirement you touched: `build_stage`,
  `verification_state`, `test_case_ids`, `evidence_location`.
- Update `status/build-status.json`: set this module's `stage`, append to `stage_history`, set
  `requirements_state` per requirement, and set `test_pass` / `test_fail` / `test_blocked` from the
  actual recorded results.
- You may only set stages you can evidence, up to and including CODE_COMPLETE and the test states.
  `REVIEWED`, `OQ_EXECUTED`, `QUALIFIED` and `RELEASED` are set by humans, never by you.
- Run `python tooling/status/rollup.py` and include the printed summary in your completion report.

VALIDATION / TRACEABILITY:
- update `docs/generated/15_TEST_TRACEABILITY_MATRIX.csv` and `29_VALIDATION_TRACEABILITY_MASTER.csv`
- state IQ/OQ/PQ impact; HIGHER-PROCESS-RISK functions need retained objective evidence
- Part 11 impact where signatures are involved (Document 88)

ACCEPTANCE CRITERIA:
- every requirement above implemented, traced and tested
- all listed tests executed with real results
- no architecture guardrail violation
- contracts committed before implementation and compatible

SPEC_GAP RULE:
Do not guess regulated behaviour. Append unresolved decisions to `docs/generated/18_SPEC_GAPS.md`
with affected requirements, risk, options and blocking status, then continue only on unaffected work.

BEFORE COMPLETION:
Run lint, typecheck, unit, contract, integration and guardrail checks. Report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; **test cases executed with PASS/FAIL/BLOCKED counts and
the case ids of every failure**; validation impact; **traceability and status files updated (include the
rollup summary)**; unresolved SPEC_GAPs; known limitations.
