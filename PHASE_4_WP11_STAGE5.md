# Phase 4 — WP-11 Stage 5: real Temporal restart/recovery proof (SG-183 / SG-048)

**Date:** 2026-09-14
**Branch:** `wp26-phase4-wp11-stage5-temporal-restart` (off `origin/main`, after PR #21 merged)
**Scope:** closes BAT-FR-029 (restart/recovery) for the one real Temporal workflow this codebase runs
(`StepStuckDetectionWorkflow`, built Stage 2). Pure verification, no new runtime capability — the
requirement was already true by construction of how Temporal and the existing workflow work; this stage
proves it with real tests rather than leaving it asserted but untested.

---

## 0. Scoping, confirmed before building

**LIMS/Edge investigated first, set aside.** The natural continuation of the "integrations" thread (SG-183
Stage 4 closed ERP) would be LIMS or Edge. Investigation found neither has any outbound-to-external-system
machinery at all — confirmed by inspection: no HTTP adapter/provider layer in `lims_integration/` or
`edge/`, unlike ERP's 4 real vendor adapters. Both modules are purely reactive/inbound (LIMS/edge devices
call this platform; it never calls them — `request_lims_sample`, on inspection, actually *creates* the
internal `qc_sample` from an externally-supplied id, the reverse direction from what its name suggests).
Building a NATS integration consumer for either would mean inventing a whole new outbound adapter layer
first — confirmed with the project owner: set aside, pivot to Temporal instead.

**BAT-FR-029 chosen over the other 22 SG-048 items.** SG-048 lists 24 Document 11 requirements blocked on
unbuilt infrastructure; Stage 2 already found and resolved the one item (BAT-FR-018) with no entangled
dependency. Re-checking after Stage 2: BAT-FR-029 ("Worker/application restart resumes from authoritative
batch/Temporal state without duplicate regulated actions") is the *second* item with no entangled
dependency — it's a property of the one workflow that already exists, not a new capability needing
Material Service, Equipment master, or any other unbuilt module. Confirmed with the project owner.

## 1. What was built

Nothing in `app/` changed. BAT-FR-029 is a property Temporal provides by construction (durable server-side
workflow history, independent of which worker process is polling) combined with how
`StepStuckDetectionWorkflow` was already written (Stage 2): a durable timer, not a database poll; an
Activity that re-reads authoritative state live rather than caching it. This stage is the test proof that
was missing, not new code.

**`tests/test_workflowops_restart_recovery.py`** (new, 2 tests) — "app/worker restart" is simulated the
way it actually happens in this deployment: the embedded worker (`workflowops/worker.py::run_worker`,
started from `app/main.py`'s lifespan) stops polling when the process goes down, while the workflow's own
state stays durably on the Temporal server (PM2 `ebmr-new-temporal`, a separate, independently-running
process) the whole time. A brand-new `Worker` instance binding to the same task queue — nothing carried
over from the prior one — is exactly what a restarted app process's own new embedded worker looks like.
No fault is injected into Temporal's own server process; that's infrastructure availability, a different
concern from this requirement's "worker/application restart."

## 2. Contract

No contract change — no new operation, event, or schema.

## 3. Updated SPEC_GAPs

- **SG-183** — Temporal's closure bullet gains a `[PARTIAL 2026-09-14, Stage 5]` entry for BAT-FR-029;
  the LIMS/Edge investigation and its finding are recorded so a future pass doesn't re-derive it from
  scratch.
- **SG-048** — corrected a bookkeeping gap found while updating it: Stage 2's own BAT-FR-018 resolution
  (2026-09-12) was never reflected here, so the tally was stuck at "2 of 24" through Stage 2, 3 and 4.
  Now reads "4 of 24" (#018, #020, #026, #029), 18 remain fully open, #012/#013 still explicitly deferred
  (blocked on SG-045).

## 4. Test evidence

`tests/test_workflowops_restart_recovery.py`, both tests against the real local Temporal server:

- `test_workflow_resumes_after_worker_restart_without_duplicate_signal` — worker A starts the workflow,
  is stopped while it's durably asleep on its timer with zero worker connected; `handle.describe()`
  confirms the workflow is genuinely still `RUNNING` with no worker at all; a completely independent
  worker B resumes it, and it completes correctly with exactly one `WorkflowStuckDetected` signal — not
  zero (lost) and not duplicated (re-executed from scratch).
- `test_step_completed_during_worker_outage_is_not_stale_on_resume` — same restart, but the step is
  completed for real (a signed `POST .../complete`) *during* the outage, with zero worker connected. The
  resumed workflow correctly re-reads live authoritative state (AG-10) and emits no signal, rather than
  acting on anything decided or cached before the restart.

2/2 passed, none mocked. Regression: `test_workflowops_temporal.py` (6) + `test_workflowops_restart_recovery.py`
(2) + `test_workflowops_retry_policy.py` (4) = 12/12 passed, no regressions.

## 5. Traceability / build-status / test-case updates

- `docs/generated/18_SPEC_GAPS.md` — SG-183 and SG-048 both updated as detailed above.
- `test-cases/WP-02/Document_11_SPEC-EBMR-002_TEST_CASES.md` + `test-cases/TEST_CASE_LIBRARY.csv` —
  `TC-011-029-01` moved `NOT_STARTED`/(recorded `BLOCKED` in the CSV) → `PASS` with real evidence.
  `TC-011-029-02` ("Illegal state transition is rejected", a generic negative-path template not matching
  this scenario) deliberately left untouched.
- `traceability/TRACEABILITY_MASTER.csv` — `BAT-FR-029`'s row moved `verification_state` `BLOCKED` →
  `IN_PROGRESS` (not `VERIFIED` — its sibling `TC-011-029-02` stays open).
- `status/build-status.json` — `SPEC-EBMR-002`'s `BAT-FR-029` requirement state recomputed by
  `tooling/status/rollup.py` from the real CSV state; new stage_history entry appended.
  `tooling/status/rollup.py` re-run: `97 started, 770/2965 requirements verified, 2533 test cases
  executed`.

## 6. Also in this pass: a small standalone citation fix (PR #22, separate branch)

While starting this stage's research, found `lims_instance.py`'s own docstring (and several other
pre-existing files) cite **SG-067** for the LIMS-FR-013 machine-identity stand-in — SG-067 is actually an
unrelated NCR gap; the correct number is **SG-070**. This had already propagated into Stage 4's new
`erp/models.py`/migration docstrings and SG-183/SG-098's own SPEC_GAP text (copied without independently
verifying). Corrected everywhere it appears for this specific topic, in `wp25-citation-fix-sg070` (PR #22,
separate from this branch since it touches unrelated files) and again here where this branch's own copy
of `18_SPEC_GAPS.md` still carried the stale citation.