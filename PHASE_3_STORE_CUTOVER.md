# Phase 3 (part 1) — SG-173 / ADR-0013 store cutover

**Date:** 2026-09-10
**Goal:** make `ebmr.gxp_batch` (`app.modules.batch_execution`) the single authoritative Batch store in
practice — the biggest cluster of backend test failure (Phase 1: ~100 of ~140).

---

## 3a — `delete_site()` referential guard — ALREADY DONE (no-op)

SG-149's write-up flagged `iam/commands.py::delete_site()` as checking only 6 legacy tables. **A prior
session already fixed it** — it now calls `find_all_blocking_references(session, "iam", "sites", ...)`,
which is schema-driven (walks `pg_constraint` for every FK into `iam.sites`). Verified: `gxp_batch`,
`gxp_product_version`, `gxp_recipe_version`, `gxp_recipe_family` all carry a real FK to `iam.sites`, so
they are already covered. No change needed.

## 3b — test fixtures cut over to `gxp_batch`

The DDCP/injector/inhalation/coated-device **command modules were already on `batch_execution`**
(`from app.modules.batch_execution.models import Batch`, reading only `.id` / `.site_id` / `.state`) —
only their **test fixtures** still built scaffold `ebmr.batches` rows. Rewrote `_create_batch` in:

- `tests/test_ddcp_flow.py`, `tests/test_injector_flow.py`, `tests/test_inhalation_flow.py`,
  `tests/test_coated_device_flow.py` — build a minimal released `product_master` / `recipe_master` pair
  + a `gxp_batch` row directly; `from app.modules.batch.models import Batch` → `batch_execution`;
  dropped the `product` / `recipe` scaffold imports; `bulk_batch.status` → `.state` (the command reads
  `source.state == "released"`).
- `tests/test_inventory_flow.py::_create_batch` (shared by `test_dispensing_flow` and
  `test_material_consumption_flow`) — same, via a `SessionLocal()` session so the `(client, token,
  site_id, code)` signature and all ~30 call sites are unchanged.

`tests/test_batch_flow.py` and `tests/test_tenancy.py` still import `app.modules.batch` **by design** —
they test the not-yet-dropped scaffold module directly; they already pass.

## 3c — FK repoint — migration 0090 existed but had never applied to the test DB

`e5f7a9c1b3d6_0090_retarget_batch_dependents_to_gxp_batch.py` already exists (prior session): it drops
and re-adds all **32 `batch_id` / `batch_step_id` FK constraints** across `ddcp` (11), `equipment` (9),
`materials` (7 + 5 step), `machine_integration` (2 + 1 step) so they reference `ebmr.gxp_batch` /
`ebmr.gxp_batch_step` instead of the scaffold. The **main `ebmr_new_gxp` DB has it** (37 FKs → gxp_batch,
0 → batches). The **test DB did not** — same stamped-but-unapplied drift as migrations 0084 / 0089 found
in Phase 1. Applied 0090's exact retargets (generated from its own constraint lists) directly to
`ebmr_new_gxp_test`. Now: 37 FKs → `gxp_batch`; only the scaffold `batch` module's own tables
(`batch_steps`, `batch_reviews`, `batch_releases`) still point at `ebmr.batches`.

**This makes it 3 stamped-but-unapplied migrations in the test DB (0084, 0089, 0090).** The test DB
needs a clean `alembic downgrade base && upgrade head` rebuild, not more hand-patches — and the
`alembic check` guard added to CI in Phase 2 now blocks this class of drift.

---

## Verification

| Test set | Before | After 3b+3c+fix |
|---|---|---|
| `test_ddcp_flow` + `test_injector_flow` + `test_inhalation_flow` + `test_coated_device_flow` | ~47 fail | **59 / 59 pass** |
| `test_inventory_flow` + `test_dispensing_flow` + `test_material_consumption_flow` | ~52 fail | **76 / 76 pass** |
| `test_material_flow` | 1 fail | **5 / 5 pass** (all 3 in-file batch creations moved to `_create_batch`) |
| `test_machine_integration_flow` (straggler — borrows `test_batch_flow`'s scaffold helper) | 3 fail | **22 / 22 pass** (cut over to `_create_batch`) |
| `test_batch_flow` (scaffold — regression check) | — | **pass** (unaffected by the `post_issue_material` change) |

### Full-suite re-run (post-cutover baseline)

**1116 passed / 43 failed / 0 errors — 96.3 %** (2 h 22 m), up from 968 / 191 (83.5 %) pre-cutover.
With the `test_machine_integration_flow` fix (landed after this run): **~1119 / 1159 (96.5 %)**.

The 40 remaining failures, all mapped to a tracked gap:

| Cause | Count | Disposition |
|---|---|---|
| `SignaturePolicyUnresolvedError` in `test_validation_wp12/wp14_*` (+ 1 authz assert) | 36 | **SG-172** — validation-platform signature policies never authored. Open Quality gap, by design; `signature_support.py` deliberately does not seed them. Not a defect. |
| genuine backend defects | 4 → **3** | ~~`test_contract_conformance` (SG-013)~~ **fixed by the M1 contract pass**; `test_eventbus_outbox_consumer` ×2 (**SG-183**), `test_ai_governance` ×1 remain |

`test_contract_conformance.py`: **48 / 48 pass** after the M1 contract pass (was 1 failing).

### Genuine code defect found: `POST /batches/{id}/material-issues` was half-cut-over

The one remaining material failure (`test_full_material_genealogy_flow`) exposed a real bug, not a test
issue. The endpoint handler in the scaffold `app/modules/batch/router.py::post_issue_material` looked the
batch up in `ebmr.batches`, then called `issue_material_to_batch` (a WP-04 material command) which looks
it up in `ebmr.gxp_batch` — and every `materials.material_issues.batch_id` FK now targets `gxp_batch`
(migration 0090). So the endpoint could never succeed for **either** batch type. Fixed: the handler now
resolves the batch from `ebmr.gxp_batch` (`GxpBatch`), matching the command and the FK. The rest of the
scaffold `batch/router.py` (its own batch-lifecycle endpoints) is untouched — that is step 3e.

Full-suite re-run pending to lock in the post-cutover baseline.

---

## SG-013 — contract commits (started)

Ran the conformance gate with the app importable: **64 CTRC-FR-001 violations** (implemented operations
missing from a surface that already has a committed contract), not the "3" the venv-less run showed.
Breakdown: ~24 in `spec-val-001.yaml` (WP-12, not M1); the rest across product / recipe / batch /
qa-review / release / qc / materials / equipment / ddcp — a mix of M1 `GET` list endpoints and
`signature-challenges` POSTs added by recent SG fixes but never contracted.

**Done — the full M1 contract surface (WP-01/02/03/04) is now CLEAN.** 23 operations across 9 files:

| File | Ops contracted |
|---|---|
| `spec-ebmr-002` (batch) | `postRecordStepResults`, `postCompleteStepV1`, `postHoldStep`, `postResumeStep`, `postProductionCompleteBatch`, `postStepSignatureChallenge`, `postBatchSignatureChallengeV1` |
| `spec-ebmr-000` (product) | `getProductBusinessIds`, `getSterileProfiles`, `postProductVersionSignatureChallenge` |
| `spec-ebmr-001` (recipe) | `getRecipeFamilies`, `postRecipeReleaseSignatureChallenge` |
| `spec-ebmr-005` (qa-review) | `postQaReviewSignatureChallenge` |
| `spec-ebmr-006` (release) | `getReleaseScopeByTarget`, `postReleaseSignatureChallenge` |
| `spec-gxp-006` (rules) | `getReleasedRules` |
| `spec-mat-002a` (receipts) | `listMaterialReceipts` |
| `spec-mat-002b` (inventory) | `listAdjustmentRequests`, `listWarehouseLocations`, `postCreateWarehouseLocation` |
| `spec-qc-001` (qc) | `listQcSpecifications`, `listQcSamples`, `listQcResultsForBatch` |

All pass the structural checks — closed command payloads (CTRC-FR-003), `x-requirement-ids` on every
operation and named schema (CTRC-FR-009), canonical `MutationReceipt`/`ErrorResponse` refs (CTR-FR-002),
globally-unique operationIds (three collided with `spec-legacy-001.yaml` → renamed `…V1`). Two dup
path-key merges (`get` + `post` under one path). `BatchState`/`BatchStepState` enums extended.

**Gate: 64 → 41 CTRC-FR-001.** All 41 residuals are non-M1: `spec-val-001` (~24, WP-12),
`spec-eqp-*` (~13, WP-06), `spec-ddcp-001` (4, WP-08), `spec-erp-006` + `spec-qc-002` (2).
The `x-requirement-ids` on the new picker/list ops are best-effort (`<MODULE>-FR-001, CTR-FR-012`) —
worth a reviewer pass against the requirement registry.

## Genuine backend defects — fixes

| Test | Root cause | Fix |
|---|---|---|
| `test_contract_conformance` | WP-01 operation with no committed contract | ✅ M1 contract pass (above) |
| `test_eventbus_outbox_consumer::test_outbox_event_carries_schema_version` | `write_outbox_event()` does `session.add()` with no flush → the `id` (`default=uuid.uuid4`, applied at flush) is `None` when the caller reads `event.id` in the same transaction | `app/mutation/gateway.py::write_outbox_event` now `await session.flush()` before returning. Every caller is already inside the command transaction, so the row still commits together — the flush just moves a step earlier. |
| `test_eventbus_outbox_consumer::test_claim_publish_mark_and_reject_double_mark` | same (`eid` was `None` → `claim_outbox_batch` never matched) | same fix |
| `test_ai_governance::test_authorize_tool_call_read_tool_fails_closed_on_signature` | the test's `gxp_read_lookup` tool was never seeded into `ai_tool_registry`, so the call hit `AIToolNotAllowlistedError` before reaching the SG-167/168 signature lookup it's meant to exercise | seed an active READ-class `gxp_read_lookup` row (no regulated scope) inline in the test |

**Verified: `test_eventbus_outbox_consumer.py` + `test_ai_governance.py` — 33 / 33 pass.** The genuine
backend defect backlog is now **0**.

**Full-suite re-run (post everything): 1123 passed / 36 failed / 0 errors — 96.9 %** (2 h 20 m). Every
one of the 36 failures is in `test_validation_wp12_*` / `test_validation_wp14_*`: 35
`SignaturePolicyUnresolvedError` + 1 authz assert = the **SG-172** cluster (validation-platform
Document 106 signature policies never authored — open Quality gap, by design). **Zero failures outside
SG-172** — the `gateway.py` flush change, the store cutover, the 47 contract additions and the
`errors.py` / `packaging` fixes have no fallout.

Session progression: 968 / 191 (83.5 %) → DB repair ~998 → store cutover 1116 / 43 (96.3 %) →
**1123 / 36 (96.9 %)**.

## `FilterIntegrityFailedError` duplicate — RESOLVED (no decision needed)

Investigation: `FilterIntegrityFailedError` (`FILTER_INTEGRITY_FAILED`) is **referenced by nothing** —
both copies were dead code. So it was never a 409-vs-422 regulated decision in practice. Removed the
accidental second definition (status 422, which shadowed the first); kept the original at 409, next to
the sterile/filter errors it belongs with. Also cleared the other two pyflakes bugs the Phase 2 gate
found: a duplicate `evaluate_policy` import in `packaging/router.py`, and an unbound `current_id` path
in `scripts/fill_document_22_test_cases.py`. **`ruff check app scripts --select F --ignore F401,F841`
is now clean**, so the CI pyflakes floor was tightened to also block F811 (redefinition) and F821
(undefined name). `errors.py` + `packaging/router.py` edits verified by import + ruff; formal test
coverage rides the next full-suite run.

## SG-013 — validation-platform contracts + CI gate flipped to BLOCKING

Contracted all **24 `spec-val-001.yaml` signature-challenge operations** (WP-12/14) — same scripted
pattern as the M1 sig-challenges; 3 shared schemas (`SignatureChallengeRequest`,
`SignatureChallengeResponse`, `SignatureChallengeWithNewRecordResponse`, `IssueReleaseAuthorizationChallengeBody`).
Two intra-file operationId collisions (path-param vs signed-CREATE) renamed `…CreateSignatureChallenge`.

**Contract gate: 41 → 17.** All 17 residuals are non-M1: `spec-eqp-*` (13, WP-06), `spec-ddcp-001`
(3, WP-08), `spec-erp-006` + `spec-qc-002` (2, WP-07).

Added `--baseline` support to `tooling/contracts/validate.py` + `contracts/openapi/.conformance-baseline`
(the 17 residuals). **The CI contract gate is now BLOCKING** (was `continue-on-error`): a new
uncontracted operation fails CI, a baselined one doesn't, and a stale baseline line fails (so the
backlog can only shrink). Remove a baseline line as its work package contracts the op.

## SG-035 remainder — CANNOT be completed by engineering (confirmed 2026-09-10)

`PHASE_0_DECISIONS.md §3` lists SG-035 among items *"still requiring a Quality / Regulatory sign-off …
cannot be made by engineering or by this project's SPEC_GAP process."* It does **not** contain policy
values. The SG-035 register entry confirms the same: `product_version/release` and
`recipe_version/release` were resolved earlier (project-owner-directed, independent QA Releaser); the
**5 remaining pairs have no approved values in any source**:

| record_type | action | current behaviour | test evidence |
|---|---|---|---|
| `vault_object` | `release` | `SIGNATURE_POLICY_UNRESOLVED` (409), correct | `test_vault.py::test_generic_release_fails_closed_pending_signature_policy` — **PASS** |
| `record_correction` | `complete` | `SIGNATURE_POLICY_UNRESOLVED` (409), correct | `test_vault.py::test_correction_request_then_complete_fails_closed` — **PASS** |
| `rule` | `release` | `SIGNATURE_POLICY_UNRESOLVED` (409), correct | `test_rules.py::test_release_fails_closed_pending_signature_policy` — **PASS** |
| `product_version` | `suspend` | `SIGNATURE_POLICY_UNRESOLVED` (409), correct | asserted in `test_product_master.py::test_release_requires_signature_and_succeeds_with_a_valid_challenge` — **PASS** |
| `product_version` | `reinstate` | `SIGNATURE_POLICY_UNRESOLVED` (409), correct | covered by the same product-master signature suite — **PASS** |

Seeding any of these would violate CLAUDE.md §4, SIG-FR-004 and AG-15. **SG-035 already documents this
exact scope** (`class R`, `blocking: false`, owner "Head of Quality + Product Owner", option (A) =
extend Document 106) — no new SPEC_GAP is raised (it would duplicate SG-035). The WP-01 code is complete
and correctly fails closed; this is a Quality decision, not an engineering gap.

**Test run (SG-035 verification, 2026-09-10):** `test_vault.py test_rules.py test_product_master.py
test_recipe_master.py` → **53 passed, 1 failed**. The 1 failure —
`test_vault.py::test_concurrent_release_same_business_id_raises_clean_conflict` — is **pre-existing and
unrelated**: it fails identically on a clean tree with every Phase 0–3 change stashed away, and **passes**
in the full-suite run (b598imzs7) with all changes present. It is an order-dependent concurrency test
(TEST-FR-017/030) — a known test-isolation defect, not a regression.

## Remaining in Phase 3

- **SG-035** — the 5 pairs above: **Quality sign-off blocker**, not engineering. Fail-closed gate
  verified working.
- **SG-013** — the 17 WP-06/07/08 contracts (baselined, not blocking); `expected_version` audit
  (batch-execution already carries it — SG-014 partly stale).
- **3d** — DDCP's post-completion flow off `batch.review` / `batch.release` onto `qa_review` /
  `release/v1` (needs a Doc 54/15 answer; DDCP is **out of M1** per ADR-0012 — deferred).
- **3e** — drop the scaffold `batch` / `product` / `recipe` modules + tables (after a bake period +
  frontend cutover).
- **SG-013** — commit the remaining contracts (starts with the 3 `spec-val-001.yaml` leaks), add
  `expected_version`, flip the CI contract gate to blocking.
- **`FilterIntegrityFailedError` duplicate** — 409 vs 422 decision for the error-registry owner.
- **ruff `--fix` cleanup PR** — clears ~78 `F401`/`I001`.
- **Frontend** — retarget `/batches/new`, `/products`, `/recipes` off the scaffold endpoints (Phase 5,
  tied to this cutover).
