# Phase 4 — WP-11 Stage 4: real ERP integration consumer (SG-183 / SG-098)

**Date:** 2026-09-14
**Branch:** `wp24-phase4-wp11-stage4-erp-consumer` (off `origin/main`, after PR #20 merged)
**Scope:** closes the **integrations** half of SG-183's remaining open item ("at-least-once consumers for
projections + integrations" — Stage 3 closed projections). Deliberately scoped to ERPNext-only
consumption posting, confirmed with the project owner across several real design forks the deeper dive
surfaced — this was not a simple "wire an event" task, and the forks below are the actual content of this
stage, not incidental detail.

---

## 0. Scoping and design forks, confirmed before building

**Fork 1 — which slice.** `app/modules/erp/`, `lims_integration/`, and `edge/` all have real, mature
outbound command machinery with zero live-event wiring (confirmed by grep: nothing in
`material/`/`batch/`/`qc/` ever called `queue_erp_command()`). SG-098 already flagged the exact target —
CON-FR-025/026, ERP posting after material consumption — though its text predates WP-07 actually landing.
Chose ERP consumption posting over LIMS, confirmed with the project owner.

**Fork 2 — no vendor-neutral payload mapping exists.** Deeper investigation found every ERP adapter
(`erpnext.py`, `sap.py`, `oracle_fusion.py`, `dynamics365.py`) forwards `IntegrationCommand.payload` to
its vendor **verbatim**, with zero transformation layer. There is no canonical, vendor-neutral consumption
payload anywhere in this codebase — inventing one for 4 vendors without ever verifying against a live
tenant would be exactly the AG-15 guess this project's own precedent (SG-125's disclosed caveats) treats
as real risk. Confirmed with the project owner: scope to ERPNext only.

**Fork 3 — no actor identity for a background consumer.** `queue_erp_command()` writes a real audit row
needing a human `iam.users.id`; a background NATS consumer has none. Found the LIMS module had already
solved this exact problem: `lims_instance.service_actor_user_id`, explicitly documented as "a stand-in for
a dedicated machine-identity model, which does not exist anywhere in this codebase" (SG-067/LIMS-FR-013).
Confirmed with the project owner: mirror that pattern onto `ErpInstance` rather than inventing a new one.

**Fork 4 — first-deploy backlog.** `jetstream.pull_subscribe()` always binds with `deliver_policy=ALL`
(EVT-FR-009). For a projection consumer (Stage 3) that's unambiguously correct; for a consumer that posts
to a real external system, it means the very first deployment replays every retained `MaterialConsumed`
event and posts the whole backlog at once. Confirmed with the project owner: keep `ALL` (every event
genuinely happened, no live ERPNext tenant is connected yet so there's no near-term double-posting risk) —
documented as a deliberate, disclosed decision, not silently accepted.

## 1. What was built

**Migration `c3f7a9d2b6e4` / `0103_erp_instance_service_actor`**: adds `erp.erp_instances.
service_actor_user_id` (nullable FK -> `iam.users.id`, MIG-FR-004 expand step — no backfill decision
forced onto existing rows). `ErpInstance` model updated to match; `alembic check` clean.
`tests/conftest.py`'s `seeded` fixture and `scripts/seed.py`'s demo fixture both assign the existing
`integration.admin` user to the demo ERPNext instance (moved after user creation, since the instance was
previously created before any user existed in fixture order).

**`app/modules/erp/consumer.py`** (new): `handle_material_consumed_event()` — reads the full
`MaterialConsumption` row by id (not the outbox envelope's own minimal payload), resolves the site's
ACTIVE `ErpInstance` with `vendor="ERPNEXT"` and a non-null `service_actor_user_id` (anything else: skip,
acked as a successful no-op — ERP integration is optional per AG-13, this is the expected common case),
resolves the consumed material's ACTIVE `ErpExternalMapping` (entity_type=MATERIAL) → ERPNext item code
(no mapping: a real handler failure — nak, then dead-letter after `max_deliver`, a genuine actionable gap,
not silently dropped), and calls the existing `queue_erp_command(command_type="POST_CONSUMPTION",
payload={"items": [{"item_code", "qty", "uom"}]})`. Idempotency key derived from the source event_id, per
`queue_erp_command`'s own docstring requirement. `dispatch_erp_command()` itself — the actual outbound
HTTP call — is untouched; this module only ever queues, exactly like every other caller.

**`app/main.py`**: wired into the lifespan next to the readmodels consumer, same fail-open posture.

No new runtime dependency.

## 2. Contract

`contracts/events/asyncapi-data-005-transport.yaml` — added `consumeMaterialConsumedEvents` (action:
receive), documenting scope, skip/dead-letter behaviour, and the confirmed first-deploy backlog decision.

## 3. Updated SPEC_GAPs

- **SG-183** — the "integrations" half of the projections+integrations closure bullet is now
  `[PARTIAL 2026-09-14, Stage 4]`. LIMS/Edge integration consumers, SAP/Oracle/Dynamics posting, and
  warehouse mapping remain explicitly open.
- **SG-098** — CON-FR-025's "required behaviour" clause moves from fully open to real (its own text
  corrected: it predated WP-07 actually landing). CON-FR-025-02/03, all of CON-FR-026, and
  CON-FR-003/021/022/028 are untouched and remain open — status set to
  `PARTIALLY_RESOLVED_2026-09-14`, not `RESOLVED`.

## 4. Test evidence

`tests/test_erp_consumer.py` (new, 3 tests) — every test runs the real
`POST /materials/v1/consumptions` command (through `test_material_consumption_flow.py`'s existing real
dispense→consume REST chain, not hand-built fixtures), publishes the real resulting `MaterialConsumed`
outbox row for real via `outbox.publish_outbox_event()`, and processes it through a real durable JetStream
pull consumer against the live broker + a real Postgres test database:

- `test_mapped_erpnext_consumption_is_queued_end_to_end` — a mapped material is queued with the exact
  expected ERPNext Stock Entry payload.
- `test_site_with_no_active_erpnext_instance_is_skipped_not_dead_lettered` — no eligible instance is a
  clean skip (acked, `consumer_inbox.result=PROCESSED`), not an error.
- `test_unmapped_material_naks_then_dead_letters` — an unmapped material naks for real broker redelivery
  and is dead-lettered after `max_deliver`, same mechanism Stage 3 built.

3/3 passed, none mocked. `erp_consumer.SUBJECT` is a fixed, real production subject (unlike Stage 3's
per-test-unique subjects) — each test drains and acks away any unrelated leftover message on the shared,
long-lived `GXP_EVENTS` stream before asserting on its own, a real consequence of this being production
subject naming, not a test artifact to hide.

Regression, full targeted suite (no full-repo run — known fixture-race noise unrelated to any change, see
project memory): `test_erp_flow.py` + `test_erp_master_sync.py` (58), `test_eventbus_consumer.py` +
`test_eventbus_jetstream.py` + `test_readmodels_cache_search.py` (18), `test_workflowops_temporal.py`
(6), `test_material_consumption_flow.py` + `test_material_flow.py` (39) — 121/121 passed, no regressions.

## 5. Traceability / build-status / test-case updates

- `docs/generated/18_SPEC_GAPS.md` — SG-183 and SG-098 both updated (description, closure_criteria/
  affected_functions, resolution_document, status) as detailed above.
- `test-cases/WP-04/Document_22_SPEC-MAT-002D_TEST_CASES.md` + `test-cases/TEST_CASE_LIBRARY.csv` —
  `TC-022-025-01` moved `BLOCKED` → `PASS` with real evidence. `TC-022-025-02/03` (inbound replay/
  timeout-uncertain lookup) and all four `CON-FR-026` cases deliberately left as-is: none of those
  scenarios were exercised this pass.
- `traceability/TRACEABILITY_MASTER.csv` — `CON-FR-025`'s row moved `verification_state` `BLOCKED` →
  `IN_PROGRESS` (not `VERIFIED`: only 1 of its 3 test cases passed).
- `status/build-status.json` — `SPEC-MAT-002D`'s `CON-FR-025` requirement state recomputed by
  `tooling/status/rollup.py` from the real CSV state; new stage_history entry appended.
  `tooling/status/rollup.py` re-run: `97 started, 770/2965 requirements verified, 2532 test cases
  executed`.
