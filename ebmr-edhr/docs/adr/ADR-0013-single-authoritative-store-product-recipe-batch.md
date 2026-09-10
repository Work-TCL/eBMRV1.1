# ADR-0013-SINGLE-AUTHORITATIVE-STORE-PRODUCT-RECIPE-BATCH — retire the day-one scaffolds; `_master`/`_execution` are authoritative

**Status:** Accepted — resolves SG-173
**Date:** 2026-09-09
**Deciders:** Project Owner (via Claude Code session), Platform Architect, Head of Quality (data-integrity sign-off)

---

## Context

SG-173 found two independent, both-live authoritative stores for the platform's three most central
regulated entities — an AG-05 / DATA-FR-001 / DATA-FR-005 violation:

| Entity | Scaffold module (retire) | Authoritative module (keep) |
|---|---|---|
| Product (Doc 09) | `app/modules/product/` → `ebmr.products` | `app/modules/product_master/` → `gxp_product_family`, `gxp_product_version`, `gxp_product_constituent`, `gxp_constituent_compatibility_version` |
| Recipe (Doc 10) | `app/modules/recipe/` → `ebmr.recipes`, `recipe_steps` | `app/modules/recipe_master/` → `gxp_recipe_family`, `gxp_recipe_version`, `gxp_recipe_section`, `gxp_recipe_step`, `gxp_recipe_step_dependency`, `gxp_recipe_parameter`, `gxp_recipe_evidence_requirement` |
| Batch (Doc 11) | `app/modules/batch/` → `ebmr.batches`, `batch_steps`, `batch_reviews`, `batch_releases` | `app/modules/batch_execution/` → `gxp_batch`, `gxp_batch_step` (+ `gxp_step_result`, `gxp_batch_hold` per SG-047/048) |

Three independent signals agree the `_master`/`_execution` side is correct, none point the other way:
git history (scaffolds added in the "Initial commit" before spec-driven work; `_master`/`_execution`
added in the deliberate build pass), `docs/generated/05_DATABASE_OWNERSHIP_MATRIX.md` (names `gxp_batch`
for SPEC-EBMR-002, never `batches`), and the codebase-wide `gxp_`/module-prefix convention for every
other authoritative regulated table.

Live-DB fact (2026-09-08, `ebmr_new_gxp`): `ebmr.gxp_batch` = **0 rows**; `ebmr.batches` = 2 demo rows;
`ddcp.constituent_handoff` = 3 rows FK'd to the demo batch. No customer batch history exists on either
side. **This is the cheapest window this cutover will ever have.**

The Project Owner selected "retire the scaffolds, cut over now, all three entities in one pass" over
batch-only, keep-both-with-sync, and accept-as-debt.

## Decision

1. **`product_master`, `recipe_master`, `batch_execution` are the sole authoritative stores** for
   Product, Recipe and Batch. `app/modules/product`, `app/modules/recipe`, `app/modules/batch` and their
   tables (`ebmr.products`, `ebmr.recipes`, `ebmr.recipe_steps`, `ebmr.batches`, `ebmr.batch_steps`,
   `ebmr.batch_reviews`, `ebmr.batch_releases`) are **retired**.

2. **The 5 existing demo rows are deleted, not migrated** — via a controlled repair migration in the
   pattern of migrations `0087`/`0088` (`RCP-SMOKE*`/`PRD-SMOKE*` cleanup). They are code-testing
   artifacts (`PFS-DEMO-PROD`, `MJ-PFS-B-SMOKE-01`), not customer records; audit/vault rows are left
   untouched (AG-08). This migration names this ADR as its change reference (Hard Prohibition #10).

3. **Cutover follows the SG-149 (2026-09-08) phased plan**, expand → migrate → contract per Document 100
   / `.claude/rules/08-database-migrations.md`, all three entities in one programme:

   - **Phase 0 (independent, do first):** fix `app/modules/iam/commands.py::delete_site()` —
     `find_blocking_reference` checks only the legacy `Product`/`Batch`/`Material` tables and never
     `gxp_product_version` / `gxp_recipe_version` / `gxp_batch`, so a site with real Product/Recipe
     Master / batch-execution data can be deleted today with no warning. Add the three `gxp_*` tables to
     the guard. No dependency on anything below.
   - **Phase 1 — repoint dependents.** `ddcp`, `material`, `machine_integration`, `equipment` (5 files)
     carry hard FKs into `ebmr.batches` (~27 columns); `iam` and `ddcp` carry Python-level imports of
     the scaffold modules. Repoint every FK to `gxp_batch`; swap every
     `from app.modules.batch.models import Batch` (and product/recipe equivalents) to the
     `_execution`/`_master` module. Field coupling is shallow — dependents read only `.id`, `.site_id`
     and (2 sites) `.status` → `.state` (identical string values for the first three states); nothing
     reads `batch.product_id`/`recipe_id`/`recipe_version` (those become `product_version_id` /
     `recipe_version_id` on `gxp_batch`).
   - **Phase 2 — behavioural cutover (the real work).** Legacy `ebmr.batches` owns its own terminal
     disposition states via `app/modules/batch/commands.py` (`submit_for_review`, `review_batch`,
     `release_batch`). `gxp_batch`'s lifecycle stops at `on_hold`/`aborted`; disposition is handled by
     the separate `qa_review` and `release/v1` modules (as `packaging`/`qc`/`yield_reconciliation`
     already expect). DDCP's "batch is done → QA" step must move off `batch.review`/`batch.release` onto
     `qa_review` + `release/v1`. **Open build-time question for the DDCP + Release module owners**
     (Document 54/15, not schema, not blocking the Product/Recipe/Batch cutover and out of the M1 scope
     per ADR-0012): does `release/v1`'s generic eligibility check already cover DDCP's
     evidence-freeze / IND-001 preconditions, or does it need a DDCP-specific extension?
   - **Phase 3 — frontend consolidation.** Retarget `frontend/` `/batches/new`, `/batches/[id]` and the
     product/recipe pages at the `_master`/`_execution` endpoints, or fold them into `/batch-execution`
     + `/product-master` + `/recipe-master` — whichever the UI owner prefers. Last step, after the
     backend agrees on one store.
   - **Phase 4 — contract.** After a bake period (Doc 100 "at least two releases between expand and
     contract"), drop the `app/modules/product`, `recipe`, `batch` routes and tables entirely.

4. **SG-162** (`iam.service_identities` vs `security.service_identity` naming collision) is resolved in
   the same direction: fold the Edge bearer-credential store into the Document 62
   `security.service_identity` registry as one more row (`auth_method=MTLS`, `credential_ref` →
   existing `credential_hash` mechanism) during this programme, or — if WP-06/Edge scheduling makes that
   unsafe to touch — document the two-registry split as permanent in a follow-up. Not on the M1 path.

## Rationale

Every signal agrees on which side is authoritative; the only real question SG-173 reserved was the
data-migration/cutover plan and whether real data needed migrating first. The live DB answers the second
(no), and the SG-149 update already scoped the first in detail. Doing all three entities together while
data is near-zero avoids paying the Product/Recipe cutover cost twice and removes a live AG-05 violation
from the M1 critical path.

## Consequences

- **SG-173 → RESOLVED** (decision recorded; execution tracked as a WP-02 task with its own migration
  IDs). **SG-149**'s architectural half is resolved; PFS-FR-020 implementation still waits on the DDCP
  behavioural cutover (Phase 2) and is not in M1.
- `docs/generated/05_DATABASE_OWNERSHIP_MATRIX.md` adds explicit Product/Recipe rows naming
  `gxp_product_version` / `gxp_recipe_version`.
- `status/build-status.json` and `traceability/TRACEABILITY_MASTER.csv` re-point every WP-02 function/
  test row from `app/modules/{product,recipe,batch}` to the authoritative modules.
- The repair migration deleting the 5 demo rows is logged in
  `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md` with this ADR as the change reference.
- Regression risk is concentrated in Phase 2 (DDCP disposition path); Phases 0–1 are mechanical and
  covered by the existing `ddcp`/`material`/`equipment` test suites plus new FK-integrity tests.
- The `delete_site()` guard fix (Phase 0) ships independently and immediately.
