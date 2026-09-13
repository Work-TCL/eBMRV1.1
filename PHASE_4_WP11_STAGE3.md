# Phase 4 — WP-11 Stage 3: real NATS/JetStream consumer-side wiring (SG-183)

**Date:** 2026-09-13
**Branch:** `wp23-phase4-wp11-stage3-nats-consumers` (off `origin/main`, after PR #19 merged)
**Scope:** closes the remaining open item SG-183 Stage 1 (producer-only) left open: "at-least-once
consumers for projections + integrations; EVT/TEST contract tests (duplicate, replay by event_id,
out-of-order, poison event) green beyond the producer-side duplicate test built this pass." This stage
covers the **projections** half only, deliberately — same narrow-scoping discipline Stage 2 used for
Temporal. Integration consumers (ERP/LIMS/Edge) remain open, a future stage.

---

## 0. Scoping, confirmed before building

Before writing any code: verified against the repo, not the task's summary, that `jetstream.py` had no
subscribe/pull-consumer primitive at all, and that `consumer.py::consume_event_idempotently()` +
`dead_letter.py::handle_poison_event()` (built Stage 1-adjacent) had zero call sites outside their own
docstrings (confirmed by grep) — nothing subscribed yet. Also verified `readmodels/` was genuinely
disconnected from the bus: its three Mutation-Gateway commands
(`rebuild_search_index`/`refresh_read_model`/`generate_async_export`) are explicit, operator-triggered
REST calls that rescan the audit ledger; nothing consumed live events.

Two design forks confirmed with the user before building:

1. **First consumer target: `material_lot` events → the readmodels search projector**, not `gxp_batch`.
   `material_lot` is both the real `aggregate_type` `material/commands.py` publishes under and the
   `index_type` `readmodels/router.py`'s own `_ALLOWED_FILTERS` already carries a reviewed `{"state"}`
   allowlist for — a 1:1 match reused verbatim, no new aggregate_type→index_type mapping and no new
   field-exposure decision invented. `gxp_batch` was set aside: its outbox events publish as
   `aggregate_type="batch"`, not `"gxp_batch"` — wiring it would have meant inventing that mapping.
2. **Integration consumers (ERP/LIMS/Edge) deliberately deferred**, a future stage — same reasoning
   Stage 2 used to not guess at Temporal-dependent requirements entangled with other unbuilt modules.

## 1. What was built

**`app/modules/eventbus/jetstream.py`**: `pull_subscribe()` — a durable JetStream pull consumer
(EVT-FR-009: `ack_policy=EXPLICIT`, `deliver_policy=ALL` so a new durable never silently skips
already-published events, bounded `max_deliver`/`ack_wait`). Same bounded-`asyncio.wait_for` discipline
`connect()` already used, applied here to consumer creation too (`SUBSCRIBE_TIMEOUT_SECONDS=5`).

**`app/modules/eventbus/consumer.py`**: `run_pull_consumer()` — the generic driver. Runs until a
`stop_event` is set (same embedded-background-task shape as `outbox_publisher_loop` and
`workflowops/worker.py::run_worker`). Per fetched message: one DB session/transaction runs
`consume_event_idempotently()` around the caller-supplied handler (so the `consumer_inbox` dedupe row and
whatever the handler writes commit atomically), acks only after that commits, naks (real broker
redelivery) on a handler failure below `max_deliver`, and dead-letters
(`handle_poison_event()` + `msg.term()`) once exhausted. `msg.term()` stops redelivery without deleting
the message — `GXP_EVENTS` uses limits retention, not work-queue, so EVT-FR-010's "without deleting the
original event" holds regardless.

**`app/modules/readmodels/projector.py`** (new): `handle_material_lot_event()` reads the audit ledger's
own `new_value` for the exact `(aggregate_id, aggregate_version)` in the envelope — the same authoritative
source `rebuild_search_index()` reads, not the outbox envelope's own deliberately-minimal payload — and
calls `index_authoritative_projection()` with the `material_lot: {"state"}` allowlist copied verbatim from
`router.py`. A version not found in the audit ledger is a real handler failure (nak/redeliver, then
dead-letter), not silently skipped.

**`app/modules/readmodels/search.py::index_authoritative_projection()`**: gained an EVT-FR-014/027
ordering guard — an incoming `source_version` no greater than what's already indexed for that entity is a
safe no-op (no version bump, no re-emitted signal). The pre-existing full-rebuild caller is unaffected (it
always computes the true per-aggregate max from the audit ledger); a live incremental consumer needs it,
since at-least-once delivery gives no total-order guarantee across redeliveries.

**`app/main.py`**: wired next to the outbox publisher and Temporal worker in the lifespan — same fail-open
posture (a connect failure is logged, never fatal; AG-09 makes NATS transport, not authoritative).

No new dependency. No new migration (both tables this pass writes to, `eventbus.consumer_inbox` and
`readmodels.projection_document_metadata`, already existed).

## 2. Contract

`contracts/events/asyncapi-data-005-transport.yaml` — added the `consumeMaterialLotEvents` operation
(action: receive) documenting the durable consumer, its failure/dead-letter/ordering handling, and the
reused field allowlist. `x-requirement-ids` on the shared `gxpEvent` message extended with
EVT-FR-005/006/009/010/014/026/027.

## 3. Updated SPEC_GAP

**SG-183** — the "at-least-once consumers for projections + integrations" closure bullet is now
`[PARTIAL 2026-09-13, Stage 3]`: projections closed for one real consumer; integrations (ERP/LIMS/Edge)
explicitly still open. `source_requirement_ids` and `affected_functions` extended.

## 4. Test evidence

`tests/test_eventbus_consumer.py` (new, 5 tests) — every test runs against the real local NATS JetStream
broker (`ebmr-new-nats`) and a real Postgres test database, not mocked:

- `test_pull_subscribe_creates_a_real_durable_consumer` — creation + idempotent rebind.
- `test_projector_indexes_a_real_material_lot_event_end_to_end` — full real path: publish → fetch off the
  real broker → `consume_event_idempotently()` + `handle_material_lot_event()` in one transaction → the
  allowlisted field lands in the index, the disallowed field does not, message acked (no redelivery).
- `test_duplicate_event_id_does_not_rerun_the_handler` — a second `consume_event_idempotently()` call for
  an already-`PROCESSED` `event_id` returns the stored result without invoking the handler (a handler that
  raises `AssertionError` if called proves this directly against the real database — forcing the live
  broker to redeliver an already-acked message is not a deterministic event to wait on).
- `test_failed_handler_naks_for_real_broker_redelivery_then_dead_letters` — a real handler failure (no
  matching audit event, not injected) naks for real broker redelivery (`num_delivered` incrementing for
  real across fetches), and is dead-lettered (`consumer_inbox.result=DEAD_LETTERED` + a real
  `EventDeadLettered` outbox row) with `term()` confirmed via a subsequent fetch timing out.
- `test_out_of_order_delivery_does_not_regress_the_index` — version 2 applied, then a late version 1 —
  the index stays at version 2.

5/5 passed. Regression: `tests/test_eventbus_jetstream.py` (5), `tests/test_readmodels_cache_search.py`
(9), `tests/test_workflowops_temporal.py` (10), `tests/test_material_flow.py` +
`tests/test_material_receipt_flow.py` (24) — 48/48 passed, no regressions. Full-suite run not attempted
this pass (known fixture-race noise unrelated to any change — see project memory); the targeted regression
above covers every module this stage touched or depends on.

## 5. Traceability / build-status / test-case updates

- `docs/generated/18_SPEC_GAPS.md` — SG-183 description, closure_criteria, source_requirement_ids (added
  EVT-FR-005/006/009/010/014/026/027), affected_functions and resolution_document updated.
- `traceability/TRACEABILITY_MASTER.csv` — TR rows for EVT-FR-005/010 moved
  `NOT_STARTED`/`NOT_VERIFIED` → `CODE_COMPLETE`/`VERIFIED`; EVT-FR-006/009/014/026/027 moved to
  `IN_DEVELOPMENT`/`IN_PROGRESS` (their sibling `-02`/`-03` negative/concurrency test-case variants were
  not exercised this pass and stay `NOT_STARTED` — not claimed as verified).
- `test-cases/WP-11/Document_73_SPEC-DATA-005_TEST_CASES.md` + `test-cases/TEST_CASE_LIBRARY.csv` —
  TC-073-005-01, TC-073-006-01, TC-073-009-01, TC-073-010-01, TC-073-014-01, TC-073-026-01, TC-073-027-01
  moved `NOT_STARTED` → `PASS` with real evidence citations. Every `-02`/`-03` sibling case (negative,
  concurrency, replay-by-external-source-id, timeout-uncertain-outcome) deliberately left `NOT_STARTED`:
  none of those literal scenarios were exercised this pass.
- `status/build-status.json` — SPEC-DATA-005 `requirements_state` and `test_pass` (9) recomputed by
  `tooling/status/rollup.py` from the real CSV state (this also corrected a pre-existing drift: EVT-FR-004
  had been `NOT_STARTED` despite its own TC-073-004-01 already being `PASS` from Stage 1 — rollup fixed it
  to `IN_PROGRESS`, matching its sibling TC-073-004-02 still being open); new stage_history entry appended.
  `tooling/status/rollup.py` re-run: `97 started, 770/2965 requirements verified, 2531 test cases executed`.
- `contracts/events/asyncapi-data-005-transport.yaml` — consumer operation + extended
  `x-requirement-ids` (contract §2 above).