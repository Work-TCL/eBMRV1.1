"""Document 73 (SPEC-DATA-005) -- NATS/JetStream Event Bus, Transactional Outbox & Async Contracts.

Executable evidence for the outbox-publisher functions, consumer-side idempotency (`consumer_inbox`),
poison-event handling, schema-compatibility checking, replay bookkeeping, and the additive
`schema_version` envelope field (migration 0072).
"""

import uuid

import pytest
from sqlalchemy import select, text

from app.core.config import settings
from app.core.db import SessionLocal
from app.modules.eventbus import dead_letter, jetstream, replay
from app.modules.eventbus.consumer import consume_event_idempotently
from app.modules.eventbus.models import ConsumerInbox
from app.modules.eventbus.outbox import (
    check_outbox_lag,
    claim_outbox_batch,
    mark_outbox_published,
    outbox_lag_seconds,
    publish_outbox_event,
    subject_for,
)
from app.modules.eventbus.schema_registry import verify_event_schema_compatibility
from app.modules.mutation.models import OutboxEvent
from app.mutation.errors import (
    EventAlreadyProcessedError,
    EventSchemaBreakingChangeError,
    HandlerFailedError,
    OutboxPublishStateConflictError,
)
from app.mutation.gateway import write_outbox_event


async def _write_event(s, **overrides):
    kwargs = dict(
        event_type="ProbeEvent", aggregate_type="probe", aggregate_id=uuid.uuid4(),
        aggregate_version=1, payload={"x": 1}, correlation_id=uuid.uuid4(),
    )
    kwargs.update(overrides)
    return await write_outbox_event(s, **kwargs)


# --------------------------------------------------------------------------------------------------
# EVT-FR-001 -- schema_version is a real transported field (migration 0072)
# --------------------------------------------------------------------------------------------------


async def test_outbox_event_carries_schema_version(db, seeded):
    async with SessionLocal() as s:
        async with s.begin():
            ev = await _write_event(s)
            eid = ev.id
    async with SessionLocal() as s:
        row = await s.get(OutboxEvent, eid)
        assert row.schema_version == "1.0"


# --------------------------------------------------------------------------------------------------
# EVT-FR-002/003/004 -- outbox publisher: claim / publish / mark
# --------------------------------------------------------------------------------------------------


async def test_claim_publish_mark_and_reject_double_mark(db, seeded):
    """WP-11: publish_outbox_event() now publishes for real to NATS JetStream (see
    tests/test_eventbus_jetstream.py for the dedicated transport tests) -- this test needs a live
    connection to exercise the claim/publish/mark mechanics end to end, and skips rather than fakes a
    pass if no broker is reachable."""
    try:
        await jetstream.connect()
    except Exception:  # noqa: BLE001 - genuinely "not reachable", not a test failure
        pytest.skip(f"No live NATS JetStream broker reachable at {settings.nats_url} -- skipping, not faking")

    async with SessionLocal() as s:
        async with s.begin():
            ev = await _write_event(s, event_type="ClaimProbe")
            eid = ev.id

    async with SessionLocal() as s:
        async with s.begin():
            batch = await claim_outbox_batch(s, batch_size=500)
            target = next(e for e in batch if e.id == eid)
            assert subject_for(target) == f"gxp.v1.probe.ClaimProbe"
            receipt = await publish_outbox_event(target)
            assert receipt["acknowledged"] is True
            await mark_outbox_published(s, event=target, publish_receipt=receipt)

    async with SessionLocal() as s:
        row = await s.get(OutboxEvent, eid)
        assert row.published_at is not None

        with pytest.raises(OutboxPublishStateConflictError):
            await mark_outbox_published(s, event=row, publish_receipt={"acknowledged": True})


async def test_outbox_lag_and_threshold_signal(db, seeded):
    async with SessionLocal() as s:
        async with s.begin():
            await _write_event(s, event_type="LagProbe")
    async with SessionLocal() as s:
        lag = await outbox_lag_seconds(s)
        assert lag is not None and lag >= 0
        result = await check_outbox_lag(s, threshold_seconds=-1)  # forces "exceeded"
        assert result["exceeded"] is True


# --------------------------------------------------------------------------------------------------
# EVT-FR-005/006 -- consumer_inbox idempotency
# --------------------------------------------------------------------------------------------------


async def test_consume_event_idempotently_runs_once(db, seeded):
    event_id = uuid.uuid4()
    calls = {"n": 0}

    async def handler():
        calls["n"] += 1
        return {"ok": True, "n": calls["n"]}

    async with SessionLocal() as s:
        async with s.begin():
            r1 = await consume_event_idempotently(
                s, consumer_name="frappe_projector", event_id=event_id, aggregate_version=3, handler=handler
            )
    assert r1 == {"ok": True, "n": 1}

    async with SessionLocal() as s:
        async with s.begin():
            r2 = await consume_event_idempotently(
                s, consumer_name="frappe_projector", event_id=event_id, aggregate_version=3, handler=handler
            )
    assert r2 == {"ok": True, "n": 1}  # not re-run
    assert calls["n"] == 1

    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(EventAlreadyProcessedError):
                await consume_event_idempotently(
                    s, consumer_name="frappe_projector", event_id=event_id, aggregate_version=3,
                    handler=handler, raise_if_duplicate=True,
                )


async def test_consume_event_handler_failure_does_not_persist_inbox_row(db, seeded):
    """A failing handler raises HANDLER_FAILED and -- because the whole caller transaction rolls back
    with it -- leaves no consumer_inbox row; attempt history is handle_poison_event()'s job."""
    event_id = uuid.uuid4()

    async def bad_handler():
        raise RuntimeError("business validation failed")

    async with SessionLocal() as s:
        with pytest.raises(HandlerFailedError):
            async with s.begin():
                await consume_event_idempotently(
                    s, consumer_name="bad_consumer", event_id=event_id, aggregate_version=1, handler=bad_handler
                )

    async with SessionLocal() as s:
        row = (await s.execute(
            select(ConsumerInbox).where(ConsumerInbox.consumer_name == "bad_consumer", ConsumerInbox.event_id == event_id)
        )).scalar_one_or_none()
        assert row is None


# --------------------------------------------------------------------------------------------------
# EVT-FR-010 -- poison-event / dead-letter handling
# --------------------------------------------------------------------------------------------------


async def test_handle_poison_event_dead_letters_and_blocks_reprocessing(db, seeded):
    event_id = uuid.uuid4()
    async with SessionLocal() as s:
        async with s.begin():
            row = await dead_letter.handle_poison_event(
                s, consumer_name="lims_adapter", event_id=event_id,
                failure_history=["timeout", "timeout", "validation error"], reason="exceeded max attempts",
            )
            assert row.result == "DEAD_LETTERED"
            assert row.attempt_count == 3

    async with SessionLocal() as s:
        outbox_types = (await s.execute(
            select(OutboxEvent.event_type).where(OutboxEvent.aggregate_id == row.id)
        )).scalars().all()
        assert "EventDeadLettered" in outbox_types

    async def handler():
        return {"ran": True}

    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(HandlerFailedError):
                await consume_event_idempotently(
                    s, consumer_name="lims_adapter", event_id=event_id, aggregate_version=1, handler=handler
                )


# --------------------------------------------------------------------------------------------------
# EVT-FR-011/012 -- schema compatibility
# --------------------------------------------------------------------------------------------------


def test_schema_compatibility_additive_and_breaking():
    old = {"properties": {"a": {"type": "string"}}, "required": ["a"]}
    additive = {"properties": {"a": {"type": "string"}, "b": {"type": "integer"}}, "required": ["a"]}
    report = verify_event_schema_compatibility(old, additive)
    assert report["compatible"] is True
    assert report["added_properties"] == ["b"]

    removed = {"properties": {}, "required": []}
    report2 = verify_event_schema_compatibility(old, removed)
    assert report2["compatible"] is False
    assert "removed" in report2["violations"][0]

    with pytest.raises(EventSchemaBreakingChangeError):
        verify_event_schema_compatibility(old, removed, enforce=True)

    newly_required = {"properties": {"a": {"type": "string"}, "c": {"type": "string"}}, "required": ["a", "c"]}
    report3 = verify_event_schema_compatibility(old, newly_required)
    assert report3["compatible"] is False


# --------------------------------------------------------------------------------------------------
# EVT-FR-016/017 -- replay bookkeeping
# --------------------------------------------------------------------------------------------------


async def test_replay_consumer_events_reports_scope_without_clearing_inbox(db, seeded):
    processed_id, never_id = uuid.uuid4(), uuid.uuid4()
    actor = seeded["users"]["operator1"].id
    async def handler():
        return {"done": True}

    async with SessionLocal() as s:
        async with s.begin():
            await consume_event_idempotently(
                s, consumer_name="search_indexer", event_id=processed_id, aggregate_version=1, handler=handler
            )
        async with s.begin():
            out = await replay.replay_consumer_events(
                s, consumer_name="search_indexer", event_ids=[processed_id, never_id],
                reason="rebuild after index corruption", actor_user_id=actor,
            )
    assert out["already_processed"] == [str(processed_id)]
    assert out["never_processed"] == [str(never_id)]

    # the original consumer_inbox row is untouched -- replay announces, never force-clears
    async with SessionLocal() as s:
        row = (await s.execute(
            select(ConsumerInbox).where(ConsumerInbox.consumer_name == "search_indexer", ConsumerInbox.event_id == processed_id)
        )).scalar_one()
        assert row.result == "PROCESSED"


async def test_generic_delete_denied_at_db_privilege_level(db, seeded):
    with pytest.raises(Exception) as exc:
        await db.execute(text("DELETE FROM eventbus.consumer_inbox"))
        await db.commit()
    assert "permission denied" in str(exc.value).lower() or "InsufficientPrivilege" in type(exc.value).__name__
