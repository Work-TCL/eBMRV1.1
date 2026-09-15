# Phase 4 — WP-02: Recipe material/equipment requirements & batch↔DDCP step sync

**Date:** 2026-09-11
**Branch:** `wp16-phase4-wp02-recipe-batch-sync` (based on `main` at `1f9333f`, the merge of
`wp12-14-rbac-signature-fixes` + `wp15-phase3-deferred-decisions`)
**Scope:** the WP-02 remainder from `DOCS_VS_IMPLEMENTATION_GAP_ANALYSIS.md` §10 Phase 4, chosen after a
full scope-reconciliation pass against the current state of `18_SPEC_GAPS.md` and `build-status.json`
(the original §10 text was written before Phases 0–3; most of it was still open, one item — WP-04's
OOS/OOT — turned out to already be built).

---

## 0. Prerequisite check (before any Phase 4 work started)

`wp12-14-rbac-signature-fixes` (Phase 0–3) and `wp15-phase3-deferred-decisions` (the Phase 3 deferred-items
follow-up) were confirmed merged into `origin/main` — but only after finding the current HEAD of
`wp12-14-rbac-signature-fixes` was 27 commits past what `origin/main`'s PR #2 had actually merged, and that
`wp15-phase3-deferred-decisions` was merged into that branch, never into `main`, with no PR of its own.
Opened PR #3 to bring `main` current. That PR's first-ever full CI run on this code found 3 real, pre-
existing failures unrelated to this session's own commits — a frontend `react-hooks/set-state-in-effect`
bug, a missing `next typegen` step, a shallow-clone gitleaks failure, and a CI Postgres bootstrap gap
(missing app role, 2 missing schemas, an `alembic_version`-vs-`include_object` false positive) — all fixed,
verified end-to-end against a throwaway `postgres:14` container mirroring the CI service exactly, then
merged. Full detail in the PR #3 commit messages (`d16be67`, `3aede65`) — not repeated here since this
document is Phase 4 proper.

## 1. Scope reconciliation

Cross-checked every §10 Phase 4 line item against current `18_SPEC_GAPS.md` status and
`build-status.json` stage. Summary (full table given to the user before any code was written):

| WP | Verdict |
|---|---|
| WP-02 | Still fully open (chosen for this branch) |
| WP-03 | Still fully open |
| WP-04 remainder | Partially done — OOS/OOT core already built (32/40 VERIFIED); method master + UOM conversion engine still open |
| WP-05 | Still fully open |
| WP-06 edge | Still fully open, confirmed `NOT_STARTED` |
| WP-07 ERP | Mostly done (automated pull pipeline + fuzzy-match built) |
| WP-09 | Still fully open |
| WP-11 | Partially done — 9/10 modules have real code, but NATS/JetStream + Temporal themselves confirmed NOT built (contradicts prior session-memory claim) |
| WP-13 AI | Partially done — adversarial tests real and substantial; eval-set infrastructure not built |

WP-02 chosen: smallest, most self-contained of the open items, and foundational (SG-045 was already
blocking part of WP-04's material/equipment linkage).

## 2. What WP-02's three items turned out to need

- **SG-045** (`recipe_material_requirement`/`recipe_equipment_requirement`): the material half's
  `material_spec_version_id` field named an entity — SG-057's "material specification version" — that
  doesn't exist anywhere in the codebase. Pulled SG-057 into scope (project-owner-directed) rather than
  stub the FK or defer the material half.
- **SG-180** (batch↔DDCP sync, option B chosen — DDCP drives the generic chain): building the write side
  surfaced that `_require_step_signature()` resolves `(batch_step, complete)`/`(batch_step, results)` from
  a single platform-wide Document 106 policy, not per-step — and it's unconditionally
  `signature_required=True`. An auto-completion write would always need a signature DDCP's own action
  doesn't collect. Declined to bypass it or treat DDCP's signature as interchangeable; built the
  declarative mapping + read-only sync-status view instead (the part that actually fixes the "two
  apparently unrelated trackers" confusion SG-180 was found from).
- **Step evidence links** (SG-047 remainder): reused `vault.gxp_vault_evidence`'s exact shape per that
  gap's own requirement to agree with Document 06's manifest, rather than invent a new one.

Every field on every new table is either (a) a direct reuse of an already-approved existing shape, or
(b) a captured-but-unenforced value following the same precedent `RecipeStep.required_role_code`/
`EquipmentAsset.equipment_class_id` already established elsewhere in this codebase — never a guessed new
regulated-content schema. Two genuine regulated decisions were found and escalated rather than guessed:
the SG-180 write-side mechanism question (resolved: don't build it, it'd be inert) and material
specification release's missing signature policy (new gap SG-185, correctly left fail-closed).

## 3. What was built

### New module: `app/modules/material_specification/` (SG-057)

`MaterialSpecification`/`MaterialSpecificationVersion` (migration `d2d738c7f191`) mirrors
`product_master.ProductVersion`'s master+immutable-version split exactly. Full create-draft/release
command surface + router (`POST /material-specifications/v1/drafts`, `GET .../{id}`,
`GET .../{business_id}/versions`, `POST .../{id}/release`, `POST .../{id}/signature-challenges`). Release
correctly fails closed with `SIGNATURE_POLICY_UNRESOLVED` — see SG-185.

### `recipe_master` extensions (SG-045)

`RecipeMaterialRequirement`/`RecipeEquipmentRequirement` (migration `4c2d52d2b8a2`), wired into
`_replace_graph()` alongside the existing `RecipeParameter`/`RecipeEvidenceRequirement` wholesale-replace
pattern — no new endpoints, extends `CreateRecipeDraftCommand`/`UpdateRecipeDraftCommand`'s existing
`StepInput.material_requirements`/`.equipment_requirements`. Exposed on `GET /recipes/v2/versions/{id}`.

### `batch_execution` extension (SG-047 remainder)

`StepEvidenceLink` (migration `2e0dcac852aa`), append-only (SELECT/INSERT only, no UPDATE — same as
`StepResult`). New unsigned command `link_step_evidence` + `POST /batches/v1/{id}/steps/{id}/evidence-links`.

### `ddcp` extension (SG-180 option B)

`DdcpStepMapping` (migration `1d2ce758fc70`) — declarative `(recipe_version_id, ddcp_action)` →
`stable_step_code` mapping, RBAC-gated create (`ddcp_profile.author`), plus
`GET /ddcp/v1/prefilled-syringe/batches/{id}/step-sync-status`, which joins a batch's declared mappings
against `gxp_batch_step.state`. No write-side auto-completion — see §2.

### Contracts (CTR-FR-001)

`spec-ddcp-001.yaml` (3 new operations + 3 schemas) and `spec-ebmr-002.yaml` (1 new operation + 2 schemas)
updated — both prefixes already had committed contracts, so `tooling/contracts/validate.py` correctly
flagged the 4 new undeclared operations as CTRC-FR-001 violations before this fix.
`material-specifications/v1` has no contract file yet (added to the same "SG-013 backlog" bucket ~30 other
uncontracted operations already sit in — the conformance gate doesn't fail a wholly new, contract-less
surface, only a new operation under an already-partially-contracted one) — a known limitation, not
attempted this pass given the branch's already-expanded scope.

## 4. New SPEC_GAP

**SG-185** — `material_specification_version/release` has no Document 106 signature policy row (class R,
not blocking). Correctly fails closed. Two options recorded for a future project-owner decision:
author from the closest existing analogue (product/recipe release: independent QA Releaser), or leave
fail-closed indefinitely.

## 5. Updated SPEC_GAPs

SG-045: OPEN → PARTIALLY RESOLVED. SG-057: OPEN → PARTIALLY RESOLVED. SG-047: PARTIALLY RESOLVED (evidence
link now built too; only `gxp_batch_hold`'s full generality remains). SG-180: OPEN → PARTIALLY RESOLVED.
Full resolution text in `18_SPEC_GAPS.md`.
