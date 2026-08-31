# ADR-0007-PYTHON-FASTAPI-GXP-SERVICES — Python/FastAPI supersedes ADR-010 for GxP services

**Status:** Accepted  
**Date:** 2026-08-22  
**Deciders:** Platform Architect, Specification Owner

---

## Context

Document 02 §6.1 froze **ADR-010: TypeScript/Node.js LTS for GxP services** as part of the Document 01
Master Architecture Bible. The Phase 1 kernel (`services/gxp-api`) that actually passed gate review is
Python 3.12 + FastAPI + async SQLAlchemy 2.0 + Alembic — a different language and stack from what was
frozen. This is a real, working deviation from a frozen decision, not a proposal: the Mutation Gateway,
signature service, audit ledger and outbox pattern (REMEDIATION_R1's own subject) are all implemented in
Python today. An unrecorded deviation from a frozen architecture decision means the validation package
would claim a stack that was never built.

## Decision

Python 3.12 + FastAPI + async SQLAlchemy 2.0 + Alembic is the implementation stack for `services/gxp-api`
and all GxP Core services, superseding ADR-010's TypeScript/Node.js LTS decision.

## Rationale

- **Single language with the Frappe app layer.** `apps/ebmr_frappe` is a Frappe app (Python); building the
  GxP Core in Python as well means one team, one language, and no context-switch at the service boundary
  that AG-02 already requires (Frappe calls GxP Core over the API — the call is cross-process either way,
  but a shared language lowers the engineering cost of maintaining that boundary correctly).
- **Async SQLAlchemy 2.0 gives the explicit transaction control the Mutation Gateway needs.** MUT-FR-015
  requires domain state, audit event and outbox row committed in one PostgreSQL transaction
  (`app/mutation/gateway.py`); SQLAlchemy's `async with session.begin():` pattern makes that boundary
  explicit and testable (see the Fix 3a rollback tests in `tests/test_batch_flow.py`).
- **Alembic covers the Document 100 migration standard** (expand-migrate-contract, forward-first,
  deterministic revision ordering) without needing an equivalent tool built or adopted for a Node stack.
- **`Decimal` discipline replaces the TypeScript decimal library requirement.** Every regulated quantity in
  `services/gxp-api` is `Numeric`/`Decimal` end to end (Doc 110 CALC-FR-001) — `app/modules/batch/models.py`'s
  `target_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))` and equivalents — never a binary float.
  This needs a lint rule (see Consequences) the way the TypeScript path would have needed a decimal library.

## Consequences

- `docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md`'s enforcement column names Python tooling
  (ruff, mypy strict) in place of the eslint/tsc row ADR-010 implied.
- `packages/data-contracts` codegen (Document 113 contract-first generation, ADR-0003) targets Pydantic
  models for `services/gxp-api`, not TypeScript interfaces, for this service.
- A lint rule forbidding `float`/`double precision`/`real` on any regulated quantity column or Pydantic
  field is a Document 104-tracked addition to the Python tooling, replacing the TypeScript decimal library
  ADR-010 would have required.
- This ADR does not change the Frappe/`apps/ebmr_frappe` stack — Frappe remains Python by its own nature
  (see ADR-0005 and ADR-0008), so this decision only formally extends the same language choice to the GxP
  Core service tier that ADR-010 had assigned to TypeScript.
