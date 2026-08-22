# Coding Standards

**Derived from:** Document 97 (SPEC-ENG-001) — controlled source in `specs/`
**Purpose:** Coding standards enforced by lint, typecheck and guardrail jobs.
**Requirements:** CODE-FR-001..036 (36)

> This file is the working engineering standard. The controlled source is Document 97; where the two
> differ, the specification wins and this file is corrected.

## Requirements

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

## Enforcement

See `docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md`,
`docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md` and `.github/workflows/ci.yml`.

## Tests

- TypeScript strict compilation
- Python typing/static checks
- float arithmetic rejection in regulated calculation module
- direct GxP DB access from Frappe blocked
- secret-in-log negative test
- dynamic SQL/eval forbidden scan
- transaction/external-call code review rule
- generated client drift test
