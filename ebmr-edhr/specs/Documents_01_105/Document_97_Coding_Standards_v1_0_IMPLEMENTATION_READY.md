# US eBMR / eDHR Regulated Manufacturing Platform
## Document 97 — Coding Standards — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-ENG-001  
**Parent Documents:** Documents 01–96  
**Primary Dependencies:** Documents 02–08, 61–78, 81–82, 98–104  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This specification is itself a control source for Claude Code/Codex. Engineering agents shall not treat it as optional style advice when the requirement is marked mandatory.

For every engineering-control function defined below preserve:

- caller/trigger;
- input type, source and requiredness;
- preconditions;
- authorization/ownership where applicable;
- repository/database/artifact reads;
- repository/database/artifact writes;
- transaction/atomicity boundary;
- output/return type;
- events/evidence;
- stable error codes;
- CI enforcement mechanism;
- positive and negative tests.

If a requirement cannot be implemented because of a conflict with another numbered specification, create a `SPEC_GAP` and stop the conflicting change rather than silently choosing a new architecture.

# Engineering Non-Negotiables

- Never modify or fork Frappe/ERPNext core.
- GxP-authoritative mutations enter through the proprietary Mutation Gateway/domain APIs.
- Frappe/MariaDB projections are not authoritative GxP records.
- No generic CRUD over released/regulated records.
- No direct SQL repair of regulated records outside controlled repair/migration mechanisms.
- No bypass of authorization, SoD, qualification or Part 11 signature requirements.
- No deletion/rewriting of immutable audit/version/evidence history.
- No external side effect inside a database transaction unless a specification explicitly establishes a safe protocol.
- Transactional outbox and idempotency are mandatory where specified.
- Temporal orchestrates; it does not own regulatory truth.
- Redis/search/NATS projections or caches are not GxP truth.
- Regulated calculations use exact decimal/UOM/rounding rules.
- All public contracts, DB migrations and release artifacts are versioned and traceable to requirement IDs.
- Production deployment must match a validated release authorization.
- AI is advisory by default; autonomous regulated decisions are prohibited unless a future separately approved specification explicitly changes that rule.

# 1. Objective

Define enforceable coding conventions and prohibited implementation patterns for Frappe/Python, TypeScript GxP services, SQL, integrations, configuration, logging and tests.

# 2. Actors / Components

- Developer
- Reviewer
- Claude Code/Codex
- CI System
- Security
- Architecture
- Validation

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| CODE-FR-001 | Language baselines | Use pinned supported Python/Frappe, Node.js LTS/TypeScript and SQL versions defined by release toolchain; never code against floating latest. | Reproducible builds. |
| CODE-FR-002 | TypeScript strictness | Enable strict TypeScript with noUncheckedIndexedAccess/exactOptionalPropertyTypes or documented equivalent; `any` requires narrow justified exception. | Type safety. |
| CODE-FR-003 | Python typing | Public Python services/functions use type hints; data structures use typed models/dataclasses/Pydantic-style validation as architecture permits. | Clarity. |
| CODE-FR-004 | Naming | Use domain-specific names; avoid vague manager/helper/util names for regulated concepts. | Maintainability. |
| CODE-FR-005 | Module size | Split modules by cohesive responsibility; avoid god classes/services and cross-domain utility dumping grounds. | Architecture. |
| CODE-FR-006 | Function contract | Public/domain functions declare typed inputs/outputs, errors and side effects; hidden DB/network behavior prohibited. | Predictability. |
| CODE-FR-007 | Pure domain logic | Calculations/rules/state-transition logic kept deterministic and independently testable where feasible. | Validation. |
| CODE-FR-008 | Decimal arithmetic | Use Decimal/NUMERIC-compatible types for regulated values; binary floating point prohibited for regulated calculations unless raw measurement semantics require it. | Accuracy. |
| CODE-FR-009 | UOM | Quantities carry explicit UOM and conversion provenance; unitless magic numbers prohibited. | Safety. |
| CODE-FR-010 | Time | Persist UTC `timestamptz`/timezone-aware datetimes; naive datetime prohibited in regulated code. | Chronology. |
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

# 4. Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB or repo effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| lintSourceFile() | Pre-commit/CI | file_path; language; coding_profile_version | File belongs to supported source tree | Runs formatter/linter/static policy rules; no source mutation in CI unless formatting check mode | LintResult | CodingStandardViolation |
| typeCheckPackage() | CI | package_path; tsconfig/python typing profile | Dependencies installed from lockfile | Runs TypeScript/Python type analysis and records diagnostics | TypeCheckReport | TypeCheckFailed |
| validateRegulatedNumericUsage() | CI semantic rule | AST/source files; regulated module catalogue | Catalogue current | Flags float arithmetic or implicit UOM in regulated calculation paths | NumericSafetyReport | RegulatedFloatUsageDetected |
| validateFrappeBoundary() | CI architecture rule | Python/JS import/call graph | Architecture registry exists | Detects direct GxP DB access/core patch/import violations | BoundaryReport | FrappeBoundaryViolation |
| validateLoggingStatement() | Static/runtime test | logging call; redaction policy | Logging framework registered | Checks structured fields and forbidden secret/payload patterns | LoggingCheck | SensitiveLoggingViolation |
| validateDomainErrorRegistry() | CI | source error codes; registry | Registry current | Ensures stable unique declared errors and forbids message-string branch patterns | ErrorRegistryReport | UnregisteredDomainError |
| scanForbiddenConstructs() | CI | repo; policy version | None | Flags eval/exec, shell interpolation, dynamic SQL, disabled TLS/auth, generic GxP CRUD patterns | ForbiddenConstructReport | ForbiddenConstructDetected |
| generateCodingComplianceReport() | Release CI | all lint/type/security/architecture results | Checks completed | Aggregates evidence by requirement/module | CodingComplianceReport | CodingComplianceGenerated |

# 5. Language and Formatting Profiles

### TypeScript / Node.js
- strict compiler mode;
- explicit DTO/schema types at boundaries;
- `unknown` preferred over `any`;
- async operations return typed results/errors;
- no implicit promise fire-and-forget for business side effects;
- no `Date` parsing without explicit timezone semantics;
- decimal library chosen centrally and wrapped in domain quantity helpers.

### Python / Frappe
- typed public functions;
- server-side permission checks for UI methods;
- DocType hooks may validate/projection-route, not become shadow GxP domain engine;
- background jobs call service APIs rather than direct foreign-schema writes;
- no monkey-patching framework core.

### SQL
- migrations own schema;
- runtime SQL parameterized;
- table/column names descriptive and snake_case;
- indexes/constraints named deterministically;
- regulated deletes require retention/migration procedure rather than generic repository method.

# 6. Error and Result Convention

Domain errors use a stable structure:

```ts
type DomainError = {
  code: string;
  message: string;           // safe human message
  correlationId: string;
  retryable: boolean;
  fieldErrors?: Array<{path:string; code:string}>;
  detailsRef?: string;       // internal diagnostics reference
};
```

Do not expose stack traces, SQL text, secrets, tokens or internal topology to end users.

# 7. Repository Coding Layout

```text
apps/ebmr_frappe/
services/gxp-*/
packages/contracts/
packages/domain-*/
packages/testing/
infrastructure/
validation/
docs/
```

Each regulated service should separate:
- transport/controller;
- application command/query;
- domain model/rules;
- repository;
- integration adapters;
- events/contracts;
- tests.

# 8. CI Enforcement

Minimum mandatory gates:
1. formatter;
2. lint;
3. type check;
4. forbidden pattern scan;
5. architecture boundary scan;
6. unit/property tests;
7. contract tests;
8. secret scan;
9. SAST/SCA;
10. traceability metadata checks for designated critical modules.

# 9. Mandatory Test / Enforcement Catalogue

- TypeScript strict compilation
- Python typing/static checks
- float arithmetic rejection in regulated calculation module
- direct GxP DB access from Frappe blocked
- secret-in-log negative test
- dynamic SQL/eval forbidden scan
- transaction/external-call code review rule
- generated client drift test

# 10. Acceptance Criteria

All production code passes automated coding/architecture checks and follows one predictable implementation pattern that preserves regulated boundaries.

# 11. Claude Code / Codex Prohibitions

- Never weaken compiler/linter/security rules merely to make a PR green.
- Never add broad `any`, `# type: ignore`, lint disable or security ignore without scoped rationale/issue.
- Never implement hidden architectural exception inside utility code.
- Never use comments to justify violation of a numbered architecture requirement.
