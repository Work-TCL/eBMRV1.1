# ADR-0009-INTEGRATION-GATEWAY-DEPLOYMENT-AND-SCHEMA — WP-07 deployment unit and provisional entity schema

**Status:** Accepted
**Date:** 2026-08-26
**Deciders:** Platform Architect (Claude Code, plan-mode sign-off from the user)

---

## Context

WP-07 (Documents 48–53, SPEC-ERP-001..006) is the first package in this codebase whose regulated mutation
path makes a real outbound HTTP call to an external system. Two open questions blocked starting the build:

1. **Deployment unit.** Every WP-07 document's own catalogue entry (`docs/generated/00_PROJECT_OUTLINE.md`,
   `traceability/TRACEABILITY_MASTER.csv`) and the pre-scaffolded `work-packages/WP-07/` prompts declare
   `code_location = services/integration-gateway`, a separate deployable. Every prior module in this
   codebase (Documents 03–43) declared its own `services/gxp-api/src/modules/<x>` location in the same
   catalogue and was instead built as `services/gxp-api/app/modules/<x>/` — one consolidated service with
   enforced logical-module boundaries, which `.claude/rules/00-architecture-non-negotiables.md` explicitly
   permits ("Logical service boundaries … are mandatory even when deployment units are consolidated into
   `services/gxp-api`"), recorded for the equipment module in ADR-0002.

2. **Entity schema.** `docs/generated/04_DATA_MODEL_CATALOGUE.md` and `00_PROJECT_OUTLINE.md` declare
   **zero data entities** for all six WP-07 modules. Document 112 (Entity Schema Completion & Migration
   Contract Addendum — the approved baseline that exists specifically to close this class of gap for other
   modules) does not cover SPEC-ERP-001..006 either. Yet ERP-ARC-021/022 (outbound command ledger, inbound
   event ledger), the whole of Document 53's reliability model (retry state, dead-letter, circuit breaker,
   reconciliation), and Document 52's mapping/conflict tables are all requirements that can only be
   satisfied by persistent state. Both the top-level rule ("no migration for an entity absent from the data
   model catalogue") and this package's own `work-packages/WP-07/CLAUDE_CODE_PROMPT.md` ("Do not write a
   migration for an entity absent from `docs/generated/04_DATA_MODEL_CATALOGUE.md`") forbid inventing one
   silently.

## Decision

1. **Deployment unit:** build WP-07 as `services/gxp-api/app/modules/erp/`, one new logical module inside
   the existing consolidated service, following the exact file-triplet convention
   (`models.py`/`commands.py`/`router.py`, prefixed per document where a document adds its own slice) that
   Documents 39/40/41/42 established inside `equipment/`. Same rationale as ADR-0002: the regulated
   transaction (domain state + version + audit + outbox in one PostgreSQL transaction, MUT-FR-015) cannot
   cross a network boundary, and Document 53 owns the *only* contract surface for Documents 48–52
   (Document 113 §6 — 49/50/51 are "adapter implementation behind the Document 48/53 provider contract";
   52 is "master-data sync jobs behind the Document 53 integration gateway; no independent public API"), so
   there is no independent-service boundary to preserve in the first place.

2. **Entity schema:** adopt a **provisional schema**, authored by Claude Code following Document 70's
   universal aggregate baseline (`id, site_id, state, version, created_at, updated_at` plus retention
   class) and Document 112's own completed-schema format, under the `erp` PostgreSQL schema. Ten tables:
   `erp_instances`, `erp_external_mappings`, `erp_mapping_conflicts`, `erp_sync_checkpoints`,
   `integration_commands`, `integration_command_attempts`, `integration_inbound_events`,
   `integration_reconciliation_runs`, `integration_reconciliation_differences`,
   `integration_circuit_breakers`. Full column definitions are in
   `services/gxp-api/migrations/versions/<rev>_0044_erp_integration_gateway_schema.py`. This is recorded
   as **SG-121** (blocking a human Document 112 amendment, not blocking this build) rather than silently
   invented: the schema is real, implemented, and tested, but is provisional pending human sign-off,
   exactly as Document 112 would eventually formalize it for any other module.

## Rationale

Real code against a clearly-flagged provisional schema, with the gap on record, serves the platform's
actual goal (regulated ERP integration state that is genuinely persisted, auditable and reconcilable)
better than either (a) no persistence at all — which would leave essentially every WP-07 requirement
uncodeable, since almost all of them describe stored ledgers/mappings/reconciliation state — or (b) waiting
indefinitely for a human to author a Document 112 addendum this package cannot itself produce with
authority. The user weighed this tradeoff explicitly (deviating from the literal "no migration for an
undeclared entity" rule) and selected this option over "build only the persistence-free slice" and "stop
and wait for a human schema decision."

## Consequences

- `erp.*` tables are provisional. A human amending Document 112 to formally declare these entities may
  require a follow-up migration to reconcile column names/types — tracked in SG-121, not silently absorbed.
- No independent Frappe/UI screens declare authority over `erp.*` state beyond read-only projections (same
  AG-04 treatment as every other module) — the nine UI surfaces Document 48 names are conceptual dashboards
  over this schema, not a separate data-ownership question.
- If Document 112 is amended with materially different entities, this ADR and SG-121 are the record of
  what shipped in the interim and why, per AG-15.
