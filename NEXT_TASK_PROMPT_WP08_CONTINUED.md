# Next development prompt — WP-08 continued: finish Document 54, then start Document 55

## STATUS NOTE — written 2026-08-29, end of the WP-03/WP-06/WP-08-Document-54 session

This file is a coordination brief for a **new, separate Claude Code chat session** working on the same
`eBMR-new` repository as at least one other active session. Read this file in full before doing anything.

**Shared-test-DB contention is a live, ongoing problem today, not a hypothetical.** During this session, a
peer session (`ebmr-new-33`) independently ran `pytest tests/test_ddcp_flow.py` against `ebmr_new_gxp_test`
while this session was mid-build, then a broader regression run from this session and a
`test_machine_integration_flow.py` run from that peer overlapped, and a follow-up "clean" re-run attempt
from this session *also* collided with a peer re-run — three collisions in under 30 minutes despite both
sessions actively messaging each other about timing. **Check `ps -ef | grep -i pytest` immediately before
running anything, message any peer session you find via `ListAgents`/`SendMessage` before running your own
tests, and treat any failure that looks like `ForeignKeyViolationError` on `sites`/`products`, a `KeyError`
on a seeded fixture value, or a `401` from `/auth/token` as contamination until proven otherwise (re-run
in true isolation) — never report it as a real defect.** As of this file being written, `ebmr-new-33` is
*still* running `test_machine_integration_flow.py` (started 09:38) — do not assume the DB is free just
because your own last check was clear a few minutes ago.

## What is already done this session (verified 2026-08-29, do not re-verify from scratch — trust this, spot-check if in doubt)

- **WP-03 and WP-06 test-case bookkeeping fixed.** `test-cases/TEST_CASE_LIBRARY.csv` had the same
  stale-duplicate-row bug WP-07 already had fixed: every WP-03/WP-06 test case carried a second, empty
  `NOT_STARTED` "ghost" row alongside its real result, which silently zeroed out `rollup.py`'s verified-
  requirement counts for both work packages. 516 duplicate rows removed (123 WP-03 + 393 WP-06), restoring
  the file to exactly **9,150 rows** — the documented canonical total. `status/build-status.json` now shows
  real verified counts for WP-03/WP-06 modules (e.g. SPEC-EBMR-008 20/32 verified, SPEC-EQP-001 11/30).
  **WP-01, WP-02, WP-04, WP-05, WP-07 have not been checked for the same bug** — if you have spare capacity
  and no one else has claimed it, `python3 -c "import csv; from collections import Counter; rows=list(csv.DictReader(open('test-cases/TEST_CASE_LIBRARY.csv'))); [print(wp, c) for wp,ids in ... ]"` (see the
  dedup approach in `docs/generated/18_SPEC_GAPS.md` SG-147's resolution, or just ask this session's
  predecessor's transcript) would confirm quickly — every work package this pattern has been found in so
  far has had it.

- **WP-08 Document 54 (SPEC-DDCP-001) built from zero.** No `app/modules/ddcp` existed before this
  session. Now: `app/modules/ddcp/{models.py, commands.py, router.py}` (9 tables from Document 112's real
  approved DDL, 16 command functions, 16 endpoints), migration `0052_ddcp_prefilled_syringe_schema`,
  `contracts/openapi/spec-ddcp-001.yaml` (passes `tooling/contracts/validate.py --strict-coverage` with 0
  violations), `tests/test_ddcp_flow.py` (9 tests, **genuinely isolated clean run: 9/9 PASS**, confirmed via
  `ps -ef` immediately before and after with zero concurrent pytest — this evidence predates the DB-
  contention cascade above and is not entangled with it).
- **18 of Document 54's 30 PFS-FR requirements have real test evidence**: PFS-FR-001, 002, 003, 004, 006,
  009, 010, 011, 012, 013, 014, 015, 017, 018, 022, 023, 024, 030. `traceability/TRACEABILITY_MASTER.csv`,
  `traceability/WP-08_TRACEABILITY.md`, `status/build-status.json`/`BUILD_STATUS.md`, and 18 rows in
  `test-cases/WP-08/Document_54_SPEC-DDCP-001_TEST_CASES.md` + `TEST_CASE_LIBRARY.csv` are all updated to
  match.
- **12 of Document 54's 30 requirements have zero implementation** — left `NOT_STARTED`, not guessed:
  PFS-FR-005 (component prep washing/depyrogenation tracking), PFS-FR-007 (bulk hold-time limit
  enforcement), PFS-FR-008 (sterile filtration pre/post integrity binding — `complete_filling_stage`
  accepts an optional `filter_use_id` and checks it via Document 42's `get_item_status`, but no test
  exercises a real filter reference), PFS-FR-016 (silicone/tungsten/particulate attribute enforcement —
  captured JSONB only), PFS-FR-019 (serialization/UDI), PFS-FR-020 (label/packaging reconciliation),
  PFS-FR-021 (a dedicated genealogy traversal/report — the underlying handoff/assembly/count data already
  carries the batch-scoped references it would need), PFS-FR-025 (a batch review-by-exception read
  composition, the PFS analogue of `equipment.aseptic_commands.get_review_summary`), PFS-FR-026
  (stability/retain sample plan linkage), PFS-FR-027 (rework-restriction enforcement — `REWORK` is a
  captured `device_assembly_record.result` value with no gating logic), PFS-FR-028 (biologic-subtype-
  specific requirements), PFS-FR-029 (Change Control linkage on constituent/process changes).
- **`docs/generated/18_SPEC_GAPS.md` SG-148** records five judgment calls made while implementing Document
  112's already-approved schema (read it before writing any more DDCP code — it explains the `site_id`/
  `tenant_id` deviation, the unsigned-action resolution, the missing `ebmr.batches -> ddcp_profile_version`
  link, why fill IPC uses the rules engine instead of the full QC pipeline, and the
  `ConstituentHandoff.to_constituent` join-key convention). Reuse these decisions for Documents 55/56/57
  rather than re-deriving them — the same gap classes will very likely recur (no Document 106 rows exist
  for those documents either; the same universal-aggregate `site_id` question will come up again).

## Why this next

Per `work-packages/WP-08/CLAUDE_CODE_PROMPT.md`'s own stated execution order (54 → 55 → 56 → 57) and
Document 54's own sub-prompt ("implement `app/modules/ddcp/` for Document 54 end to end, including tests,
before moving to Document 55"), Document 54 is 60% done (18/30 requirements), not finished. There are two
reasonable paths and this file does not force a choice — pick based on your own judgment of value, but lean
towards finishing Document 54 first unless a specific reason argues otherwise:

1. **Finish Document 54's remaining 12 requirements** (recommended default — matches the stated
   sequencing). Highest-value candidates, roughly in order of how directly they reuse patterns already
   built this session: PFS-FR-025 (batch review package — copy `aseptic_commands.get_review_summary`'s
   shape, composing `ConstituentHandoff`/`FillOperation`/`DeviceAssemblyRecord`/`DeviceFunctionalTestLink`
   rows for a batch into one review read), PFS-FR-021 (genealogy — a read composition over the same
   tables, no new writes), PFS-FR-007 (bulk hold time — needs a compounding-to-filtration timestamp pair
   and a released-limit comparison; check whether `constituent_handoff.attributes` or a new captured field
   on `fill_operation` is the right place, and whether any Document 106/109-style numeric-limit gap applies
   — if no baseline limit exists anywhere, that is itself a new SG-148-class gap, not something to guess).
   The remaining ones (005, 008 test coverage, 016, 019, 020, 026, 027, 028, 029) are lower-value/more
   speculative "support X when configured" requirements — treat each on its own merits, and do not force
   an entity/column that Document 112's approved schema does not already provide (raise a new SPEC_GAP
   instead, same discipline SG-148 already models).
2. **Start Document 55** (`prompts/WP-08/55_SPEC-DDCP-002.md`, Autoinjector/Pen/Cartridge DDCP, INJ-FR-
   001..030) if you judge breadth-first more valuable than depth-first for this work package. Read Document
   112 for this document's own approved entity schema before writing any model — it likely exists there the
   same way Document 54's did. Expect the same signature/site_id/linkage gap classes SG-148 already covers;
   extend SG-148 or open a new SG-14x rather than re-deriving the same reasoning from scratch.

## Standing project rules (from CLAUDE.md — do not skip these)

- `specs/` is read-only. Never edit it.
- Never invent regulated behaviour (signature requirements, SoD, retention, precision, authorization,
  audit/vault semantics, release decisions, a numeric limit/tolerance with no baseline). Missing decision →
  append a SPEC_GAP entry to `docs/generated/18_SPEC_GAPS.md` (state affected requirements, risk, options,
  blocking yes/no) and continue on unaffected work. SG-148 is the existing entry for this module — extend
  it or add a new SG-14x if you resolve or find a new gap; don't silently reinterpret it as fully closed.
- Never fabricate a test run, scan result, coverage number or signature. A failed test is evidence — never
  delete it, re-run over it, or edit the expected result to pass. A run contaminated by concurrent shared-
  DB access is not a real result either way — re-run in verified isolation before reporting anything.
- Update `traceability/TRACEABILITY_MASTER.csv`, `traceability/WP-08_TRACEABILITY.md` and
  `status/build-status.json` as you go, and run `python tooling/status/rollup.py` before your completion
  report (this is a pure file-processing script — no DB access — safe to run any time, even mid-collision).
- Run Python via `su -s /bin/bash frappe -c "cd services/gxp-api && ..."`; `chown -R frappe:frappe`
  anything you create or touch as root (check with `find <paths> -not -user frappe` before finishing —
  this session caught its own root-owned files this way more than once).
- Re-run `tooling/contracts/validate.py --strict-coverage` after any endpoint change (it does not touch the
  DB — safe to run any time). It currently passes cleanly for `spec-ddcp-001.yaml`.
- Before declaring the task complete, deliver the full CLAUDE.md §6 twelve-point completion report:
  requirement IDs implemented; functions created/changed; files changed; migrations; API/event contract
  changes; dependency/licence changes; security impact; test cases executed (PASS/FAIL/BLOCKED counts +
  failure ids); validation/change impact; traceability/status updated (include the `rollup.py` summary
  line); unresolved SPEC_GAPs; known limitations.

## Suggested opening move for the new session

1. Read this file in full (done, if you're reading this).
2. `ps -ef | grep -i pytest` and `ListAgents` — confirm the DB is actually free and message any peer found
   before running anything against `ebmr_new_gxp_test`.
3. Read `docs/generated/18_SPEC_GAPS.md` SG-148 in full.
4. Read `app/modules/ddcp/{models.py, commands.py}` (this session's own code) for 10-15 minutes to
   internalize the idiom before extending it — pay particular attention to `evaluate_pfs_release_readiness`
   and `_compute_readiness`-style cross-module composition, since PFS-FR-021/025 reuse that exact shape.
5. If continuing Document 54: read `equipment.aseptic_commands.get_review_summary` for the review-package
   shape (PFS-FR-025's closest existing analogue), implement it, then genealogy (PFS-FR-021), then work
   through the remaining lower-value items, adding tests to `tests/test_ddcp_flow.py` for each.
   If starting Document 55: read `prompts/WP-08/55_SPEC-DDCP-002.md` and the corresponding Document 112
   entity section in full before writing any code, the same way this session read Document 54's before
   starting.
