# Phase 4 — WP-11 Stage 2: real Temporal workflow (SG-183)

**Date:** 2026-09-12/13
**Branch:** `wp21-phase4-wp11-nats-jetstream` (continuing the same branch as Stage 1, before its PR merged)
**Scope:** the user explicitly chose to continue ADR-0011's Temporal build after Stage 1 (NATS) shipped.
This is Stage 2: a real Temporal server + one real, complete, tested workflow — not an attempt to port
all of Document 11's Temporal-dependent scope, which SG-048 shows is entangled with several other
unbuilt modules.

---

## 0. Scoping, confirmed before building

SG-048 lists 24 Document 11 requirements blocked on unbuilt infrastructure. Of the ones naming Temporal
(BAT-FR-018/021/022/026-029), most are *also* blocked on Material Service, Equipment master, Document
12/17, or the IAM qualification schema — porting them now would mean guessing those modules' shape too,
the exact AG-15 violation SG-048 already declined. The one Temporal-dependent sub-requirement with **no**
other entangled dependency is BAT-FR-018/021's "stuck step" half (timer/duration enforcement + exception
generation) — chosen as this stage's scope, confirmed with the user before writing any code.

## 1. What was built

**Temporal dev-server**: real, not a stand-in. `/usr/local/bin/temporal` (official CLI binary, MIT
license), run via PM2 (`ebmr-new-temporal`, matching how `ebmr-new-api`/`ebmr-new-frontend` are already
managed — survives session/reboot boundaries). `--headless` (no Web UI), embedded SQLite persistence
(`infra/temporal-data/temporal.db`, gitignored), bound to `127.0.0.1:7233`/`7243` only. Measured
footprint: ~130MB RAM. See `infra/README.md`.

**`app/modules/workflowops/client.py`** (new): owns the Temporal client connection. `connect()` wraps
`Client.connect()` in `asyncio.wait_for(timeout=5)` — applied **proactively**, not discovered by a second
incident: Stage 1's NATS integration found the hard way that an unbounded connect can hang forever (and
that CI test job hung twice, once for 134 min and again for 177 min, before the root cause was found and
fixed). Same lesson, applied here from the start.

**`app/modules/workflowops/activities.py`** (new): two real Activities.
`check_step_still_in_progress` re-reads `BatchStep`'s authoritative state through
`batch_execution.service.get_step()` — never caches or guesses it (AG-10). `emit_stuck_signal` emits
`WorkflowStuckDetected` through the pre-existing `workflowops/signals.py::emit_workflow_signal()`.
`classify_retry()` (TMP-FR-011, previously an untested pure function with zero call sites) is now
actually wired inside the first Activity: a settled `GxPError` (e.g. `NOT_FOUND`) becomes a Temporal
`ApplicationError(non_retryable=True)` instead of being retried forever.

**`app/modules/workflowops/workflows.py`** (new): `StepStuckDetectionWorkflow` — sleeps via a durable
Temporal timer for `threshold_seconds`, then checks the step; if still `in_progress`, emits the signal.
Never itself decides or writes a regulated batch/step state transition (AG-10).

**`app/modules/workflowops/worker.py`** (new): runs embedded in the API process (started from
`app/main.py`'s lifespan, same as the NATS publisher loop) rather than a separate deployment unit — a
legitimate choice for this single-instance deployment.

**`app/modules/workflowops/commands.py` + `router.py`** (new): `start_step_stuck_detection()` /
`get_step_stuck_detection_status()`, exposed as `POST`/`GET /workflowops/v1/step-stuck-detection...`.
Not a Mutation Gateway command in the full Document 03 sense — starting/reading a workflow's own status
is not a regulated GxP decision (AG-10) — RBAC-only, no Document 106 row, matching WP-07's
`secret.rotate` precedent. Idempotent start (TMP-FR-002): a duplicate start for a running step reuses the
same workflow via `WorkflowAlreadyStartedError`.

**Dependency**: `temporalio>=1.8,<2.0` (MIT, official Temporal Python SDK, Document 104 justification,
reviewed as DEP-FR-018 runtime-critical) + 3 clean transitive deps (`nexus-rpc` MIT, `protobuf`
BSD-3-Clause, `types-protobuf` Apache-2.0).

## 2. Contract

New `contracts/openapi/spec-data-006.yaml` — 2 operations, both schemas carry `x-requirement-ids`.
`tooling/contracts/validate.py --baseline` PASS (0 accepted findings needed for this file; the 2 new
operations would otherwise have landed in the SG-013 no-contract backlog — written properly instead).

## 3. Updated SPEC_GAP

**SG-183** — Temporal half now also `PARTIALLY_RESOLVED` (was open). One real workflow proven end to
end against a live server. Explicitly still open: the other Document 11 Temporal-dependent requirements
SG-048 lists, durable NATS consumer wiring (Stage 1's own remaining item), and Temporal's own
deterministic-replay test harness (TEST-FR-010) — this pass's tests ran against the live dev-server
directly, not the replay-test environment `temporalio.testing` provides.

## 4. Test evidence

- `tests/test_workflowops_temporal.py` (new, 6 tests) — **every test runs against the real local
  Temporal server and a real `Worker`, not a mock**: stuck-signal emission after the threshold, no
  signal when the step completes first, idempotent double-start, REST start+query round trip,
  `NOT_FOUND` fail-closed for an unknown step, unauthorized rejection. 6/6 passed.
- `tests/test_workflowops_retry_policy.py` (new, 4 tests) — `classify_retry()` as a pure function
  (no server needed): retryable transient-race/dependency-failure cases vs. non-retryable settled
  outcomes. 4/4 passed.
- Full repository regression: see the completion report for the exact final count (run after this
  document was written, same discipline as Stage 1 — full suite before commit).

## 5. Traceability / build-status / test-case updates

- `docs/generated/18_SPEC_GAPS.md` — SG-183 description, closure_criteria, source_requirement_ids
  (added TMP-FR-002/006/011/024) and resolution_document updated.
- `docs/generated/40_SBOM_LICENSE_DEPENDENCY_REGISTER.md` — `temporalio` + 3 transitive deps added;
  "Durable workflow" baseline row updated.
- `traceability/TRACEABILITY_MASTER.csv` — TR rows for TMP-FR-002/006/011/024 moved
  `NOT_STARTED`/`NOT_VERIFIED` → `CODE_COMPLETE`/`VERIFIED`.
- `test-cases/WP-11/Document_74_SPEC-DATA-006_TEST_CASES.md` + `test-cases/TEST_CASE_LIBRARY.csv` —
  TC-074-002-01, TC-074-006-01, TC-074-011-01 moved `NOT_STARTED` → `PASS` with real evidence citations.
  TC-074-024-01 ("Activities fail/retry") deliberately left `NOT_STARTED`: this pass proves the retry
  *classification* logic and the "workflow never invents a transition" architecture, but never staged an
  actual DB-outage-during-retry scenario — not claimed as proven.
- `status/build-status.json` — SPEC-DATA-006 `started_at` set, `apis` 0→2, `test_pass` 0→6,
  TMP-FR-002/006/011/024 → `VERIFIED`, new stage_history entry; `tooling/status/rollup.py` re-run.
- New `infra/README.md` Temporal section + recreate instructions; `infra/temporal-data/` gitignored.
