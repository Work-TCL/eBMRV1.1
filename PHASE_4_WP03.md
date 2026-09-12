# Phase 4 — WP-03 remainder: YLD-FR-022 supersede/correction (SG-133 partial)

**Date:** 2026-09-12
**Branch:** `wp19-phase4-wp03-yield-supersede` (based on `main` at the merge of PR #15's WP-07 secret-manager work)
**Scope:** the "preserves original" half of YLD-FR-022 (Document 17, yield/reconciliation correction),
chosen after a research pass across Documents 13-17 found this was the single cleanest buildable item —
the schema (`supersedes_id` on both tables, `SUPERSEDED` state) was already built and never wired to a
command.

---

## 0. Scoping investigation before building anything

A research pass across WP-03's 5 documents (Genealogy, QA Review, Release/Disposition, Packaging, Yield)
found most of the recorded open gaps (SG-051/053/055/056/134/135/136/137) are correctly blocked on a
missing baseline entity, a missing quality-policy decision, or a cross-module dependency (waiver
authority, loss-category vocabulary, label-master entities) — none safely buildable without guessing
regulated behavior. SG-132 was already found `PARTIALLY_RESOLVED` (5 of 6 items closed 2026-08-27).

SG-133 (9 Document 17 requirements with no distinct implementation beyond generic mechanics) named
YLD-FR-022 as one item where the schema was already DDL-ready (`supersedes_id` + `SUPERSEDED` state on
both `manufacturing_calculation` and `reconciliation_record`) but "no command in this module ever sets
it." This is ordinary engineering work — reusing `genealogy.service.correct_edge()`'s already-established
supersede discipline — not a regulated-behavior guess, so it was picked as this branch's scope.

## 1. What was built

Added `supersedes_id: uuid.UUID | None` + `reason: str | None` (required when `supersedes_id` is set) to
all five `Evaluate*` commands in `app/modules/yield_reconciliation/commands.py`
(`EvaluateYieldCommand`, `EvaluatePotencyCommand`, `EvaluateReconciliationCommand`,
`EvaluateLabelReconciliationCommand`, `EvaluateComponentReconciliationCommand`) — additive fields on
**existing** endpoints, no new endpoint (Document 17's own 8-op API list already covers all five).

New shared helper `_apply_supersede()`: after the new row is flushed, if `supersedes_id` is present it
loads the original row `with_for_update()`, verifies it exists, is not already `SUPERSEDED`, matches the
new row's `calculation_type`/`reconciliation_type` and `batch_id`, then flags it `SUPERSEDED`, links the
new row via `supersedes_id`, and writes a `Corrected` audit event + `ReconciliationSuperseded` outbox
event on the **original** row — the exact same shape `genealogy.service.correct_edge()` already
established (AG-08: never UPDATE a result/state in place, a correction is always a new row).

`ReconciliationSuperseded` was already declared in `docs/generated/07_EVENT_CATALOGUE.yaml` with no
producing code path (explicitly noted in the prior event-contract pass) — reused that exact name for
both aggregate types (`manufacturing_calculation` and `reconciliation_record`) rather than inventing two
new event names, since the catalogue only ever declared the one.

## 2. Contract

`contracts/openapi/spec-ebmr-008.yaml` — `supersedes_id`/`reason` added to all 5 command schemas
(`additionalProperties: false`, so this was required), `YLD-FR-022` added to each schema's
`x-requirement-ids`. `contracts/events/event-ebmr-008.json` — new `ReconciliationSupersededPayload`
schema + 2 event entries (one per aggregate_type, same producer, no `CTRC-FR-008` collision).
`tooling/contracts/validate.py --baseline` PASS; `tooling/events/validate.py` shows the same 2
pre-existing SG-174 collisions as before (unaffected by this change, not introduced by it).

## 3. Updated SPEC_GAP

**SG-133** — YLD-FR-022's supersede half moved to `PARTIALLY_RESOLVED`; the other 8 requirements in this
umbrella gap (YLD-FR-004/008/014/016/017/024/025/032) and YLD-FR-022's own "automatically re-evaluate
downstream results" half remain open — no baseline anywhere defines what "downstream" means for a
yield/reconciliation calculation, so that half stays a recorded gap rather than a guess.

## 4. Test evidence

`tests/test_yield_reconciliation.py` grew from 33 to 37 tests, **37/37 passed**: happy-path supersede for
both yield (`ManufacturingCalculation`) and material reconciliation (`ReconciliationRecord`), missing-reason
rejection, double-supersede-of-the-same-original rejection, and cross-batch `supersedes_id` rejection.

TC-017-022-01/02 (the only 2 pre-written cases for YLD-FR-022) stay **BLOCKED** in the test-case book,
not forced to PASS: their literal expected result requires both halves of YLD-FR-022, and only the first
is built. Actual-result text updated honestly to describe exactly what is now verified vs. still missing.

## 5. Traceability / build-status updates

- `docs/generated/18_SPEC_GAPS.md` — SG-133 description + resolution_document updated, status still
  `PARTIALLY_RESOLVED` at the gap level (unchanged label, new note).
- `traceability/TRACEABILITY_MASTER.csv` — TR row for YLD-FR-022 left at `IN_DEVELOPMENT`/`BLOCKED`
  (honest: the row's full literal scope, including downstream re-evaluation, is not yet verified).
- `test-cases/WP-03/Document_17_SPEC-EBMR-008_TEST_CASES.md` — TC-017-022-01/02 actual-result text
  updated with real evidence citations, status unchanged (BLOCKED).
- `status/build-status.json` — SPEC-EBMR-008 stage_history entry added describing the real work and
  evidence; numeric test_pass/test_blocked counts unchanged (they track the book, not raw pytest count,
  and the book's own case status didn't change); `tooling/status/rollup.py` re-run.
