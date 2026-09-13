# Phase 4 — WP-11 Stage 1: real NATS JetStream transport (SG-183)

**Date:** 2026-09-12
**Branch:** `wp21-phase4-wp11-nats-jetstream` (based on `main` at the merge of PR #17's WP-05 deviation-FK work)
**Scope:** the user explicitly chose to build ADR-0011's NATS/JetStream + Temporal decision "for real,
multi-stage" rather than defer it. This is **Stage 1 of that multi-stage build**: a real NATS JetStream
producer replacing the in-process stand-in publisher. Temporal (Document 74) and durable consumer wiring
are separate, not-yet-started stages of the same gap.

---

## 0. A real operational finding before building anything

Before provisioning any new service, `df -h` / `free -h` showed this shared host (also running
unrelated production sites: industrial-rfq, wordpress, scada, tiledesk) at **98% disk (3.6GB free)** and
**~720MB free RAM**. Standing up new persistent services here without checking first would have risked
disk exhaustion or OOM affecting other tenants, not just this project — this was flagged to the user
before any provisioning, rather than proceeding silently. By the time provisioning started, other
activity on the host had freed disk to ~13GB; the user chose to proceed with tight resource limits
regardless of the improved margin, which is what was built.

## 1. What was built

**NATS JetStream** (`infra/nats-server.conf`, container `ebmr-new-nats`): single node, bound to
`127.0.0.1` only (never exposed), `--memory=160m` hard cap, JetStream `max_file_store: 512MB` /
`max_memory_store: 64MB`, log rotation capped, `--restart unless-stopped` (survives host reboots without
PM2). Measured footprint: ~10MB RAM at rest. See `infra/README.md` for the recreate command.

**`app/modules/eventbus/jetstream.py`** (new module): owns the one process-wide NATS connection +
JetStream context. `connect()` is idempotent and declares the `GXP_EVENTS` stream (subjects
`gxp.v1.>`) if it doesn't exist. `publish()` sends with a `Nats-Msg-Id` header and returns only after
the broker's `PubAck`. `app/main.py`'s `lifespan()` connects at startup and closes at shutdown — a
connection failure at startup is logged, **never fatal**: AG-09 makes NATS transport, not authoritative
truth, so the API must keep accepting and committing regulated mutations even if the broker is
temporarily unreachable. `connect()` is bounded (5s) rather than relying on nats-py's own infinite
reconnect for the initial attempt — see §6 below for why that distinction turned out to matter; recovery
from a later, temporary outage is the publisher loop's own existing retry-every-2s behavior.

**`app/modules/eventbus/outbox.py::publish_outbox_event()`** (real transport, docstring always said this
was swappable): builds the canonical EVT-FR-001 envelope directly from the outbox row (`_canonical_envelope()`)
and publishes it as JSON, with `Nats-Msg-Id` set to the event's own `event_id`. This gives JetStream's
own dedup window the exact property EVT-FR-004 calls for: if the publisher crashes between a successful
publish and `mark_outbox_published()`, the retried publish carries the same `event_id` and the broker
recognizes it as a duplicate (`ack.duplicate = true`) rather than delivering it twice — a genuine
crash-recovery guarantee, not merely a documented intention.

**Dependency**: `nats-py>=2.10` added with a Document 104 justification in `pyproject.toml` (official
`nats-io` client, Apache-2.0, pure-Python, **zero transitive dependencies**, async-native). `uv.lock`
updated.

## 2. Contract

New `contracts/events/asyncapi-data-005-transport.yaml` — the broker-level subject/stream/dedup
convention (stream `GXP_EVENTS`, subject `gxp.v1.{aggregate_type}.{event_type}`, `Nats-Msg-Id` dedup key).
References `event-data-005.json`'s existing `EventEnvelope` schema rather than redefining the payload
shape. Explicitly scoped in its own description as producer-side only — SG-183's consumer-side closure
criterion is not claimed here.

## 3. Updated SPEC_GAP

**SG-183** — moved to `PARTIALLY_RESOLVED`. NATS/JetStream producer side is real and proven against a
live broker. Still open, not silently assumed done: durable consumer wiring (nothing subscribes yet —
this pass proves the producer publishes and dedups correctly, not that anything downstream consumes),
offline-buffer-then-reconnect proof (TC-073-004-02), and all of Temporal (Document 74) — `workflowops`
and batch-execution recovery/escalation paths are completely untouched by this pass.

## 4. Test evidence

`tests/test_eventbus_jetstream.py` (new file, 5 tests) — **every test runs against the actual live NATS
container, not a mock**, and skips (rather than fakes a pass) if no broker is reachable at `GXP_NATS_URL`:
- round-trip publish + PubAck
- exact canonical-envelope byte-for-byte shape, read back via a real pull subscription
- republishing the same `event_id` is recognized as a duplicate by the broker (the crash-recovery case)
- publishing with no connection raises `ConnectionError`
- `connect()` is idempotent

5/5 passed. Confirmed via code inspection that `httpx.ASGITransport` (used by every existing test's
`client` fixture) never sends ASGI `lifespan` events, so `outbox_publisher_loop`/`jetstream.connect()`
never runs during the rest of the test suite via the HTTP client path.

**One real regression found and fixed by the full-suite run**: `tests/test_eventbus_outbox_consumer.py::
test_claim_publish_mark_and_reject_double_mark` called `publish_outbox_event()` directly (not through the
HTTP client) to exercise the claim/publish/mark mechanics, and had never needed a live broker before since
the old stand-in always faked an ack. First full run: 1 failed, 1219 passed. Fixed the same honest way as
the new test file: connect to the real broker first, `pytest.skip()` (not a fabricated pass) if
unreachable. Re-ran the full suite after the fix: **1220/1220 passed**.

## 6. A second, more serious bug found by a genuinely hung CI run

After the first PR push, PR #18's CI `test` job hung for ~134 minutes (no prior run this session had
exceeded 52 min), and a re-run hung again at ~177 minutes. Rather than assume flakiness a third time,
the actual per-step timestamps in the job log were inspected: pytest progressed normally (5%→29% in ~9
minutes) then produced **zero output for the following ~2h48m** until cancelled -- a real, deterministic
hang, not slowness, landing exactly where the new NATS-dependent tests sit alphabetically.

Root cause, confirmed by reading `nats-py`'s own `Client.connect()` source: `max_reconnect_attempts=-1`
governs the **initial** connection attempt too, not just reconnection after a drop. On `NoServersError`
(no broker reachable at all -- exactly CI's situation, which has no NATS service configured) it `continue`s
its retry loop forever rather than raising. `jetstream.connect()`'s own `_nats_reachable()` probe (used by
both test files to decide whether to skip) called this with no bound, so in an environment with no broker
it never returned and never raised -- pytest just sat there.

**This is a real production bug, not only a test problem**: `app/main.py`'s `lifespan()` awaits
`eventbus_jetstream.connect()` directly. Had NATS been down at deployment startup, the entire API would
have hung at boot forever, despite the `try/except` around that call and the module's own documented
intent ("a connection failure here never blocks a regulated mutation") -- the `except` clause can only
run if `connect()` ever raises, which it would not have.

**Fix**: `connect()` now wraps the `nats.connect()` call in `asyncio.wait_for(..., timeout=5)` and raises
a `ConnectionError` on timeout, with `max_reconnect_attempts` lowered from `-1` to `5` (bounded either
way). Resilience against a *later*, temporary broker outage still comes from `outbox_publisher_loop`'s own
pre-existing every-2-second retry, not from nats-py's internal infinite reconnect. Verified directly, not
assumed: a raw `lifespan()` invocation with the broker stopped now completes in 5.1s (logs the failure,
does not hang); `jetstream.connect()` against an unreachable port now raises in exactly 5.0s. Also made
`test_eventbus_jetstream.py`'s reachability probe module-scoped (once per file, not once per test) so a
broker-less environment like CI's now skips its 14 NATS-dependent tests in ~35s total instead of the
~65s six independent probes would have cost.

## 7. Bundled bookkeeping fix (WP-13, unrelated to NATS)

While cross-checking `status/build-status.json` for stale entries during this session, found
SPEC-AI-001's row still listed SG-167 as an active blocker and `test_pass: 4`, both stale: SG-167 was
already fully resolved 2026-09-11 (`wp15-phase3-deferred-decisions`, `PHASE_3_DEFERRED_DECISIONS.md` item
C), and `tests/test_ai_governance.py` is really 24/24 passing. Fixed as a small bundled addition rather
than a separate branch — no code changed, `blockers` cleared and `test_pass` corrected, with a
stage_history note explaining exactly what was and wasn't re-verified (the 56 individual AI-FR
requirement states were not re-checked one by one, so `stage` stays `IN_DEVELOPMENT`, not bumped to
`CODE_COMPLETE` on the strength of this bookkeeping pass alone).

## 5. Traceability / build-status / test-case updates

- `docs/generated/18_SPEC_GAPS.md` — SG-183 description, closure_criteria (marked DONE/OPEN/PARTIAL
  per item) and resolution_document updated; status `PARTIALLY_RESOLVED`.
- `docs/generated/40_SBOM_LICENSE_DEPENDENCY_REGISTER.md` — `nats-py` added to the direct-dependency
  table; "Event bus" row in the approved-technology-baseline table updated from "committed" to "real,
  single-node (WP-11 Stage 1)".
- `traceability/TRACEABILITY_MASTER.csv` — TR-02025 (EVT-FR-003) moved `NOT_STARTED`/`NOT_VERIFIED` →
  `CODE_COMPLETE`/`VERIFIED`. TR-02026 (EVT-FR-004) deliberately left as-is: one of its two mapped test
  cases (TC-073-004-02, offline buffering) is not yet proven, and `VERIFIED` requires all mapped cases
  to pass.
- `test-cases/WP-11/Document_73_SPEC-DATA-005_TEST_CASES.md` + `test-cases/TEST_CASE_LIBRARY.csv` —
  TC-073-003-01 and TC-073-004-01 moved `NOT_STARTED` → `PASS` with real evidence citations.
- `status/build-status.json` — SPEC-DATA-005 `started_at` set, `EVT-FR-003` → `VERIFIED`, `test_pass`
  0→5, new stage_history entry. SPEC-DATA-006 (Temporal) deliberately untouched — still accurately `0`
  everything, since nothing was built there this pass. `tooling/status/rollup.py` re-run.
- New `infra/README.md` + `infra/nats-server.conf` (committed) and `infra/nats-data/` (gitignored,
  rebuildable runtime state, AG-09).
