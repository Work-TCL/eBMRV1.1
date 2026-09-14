"""Document 73 (SPEC-DATA-005), WP-11 Stage 3 (ADR-0011, SG-183): the real durable pull-consumer + the
first at-least-once consumer wired end to end (`readmodels/projector.py`, `material_lot` -> the Postgres
search index).

Every test here runs against a genuinely live local NATS JetStream broker (same `ebmr-new-nats` container
`tests/test_eventbus_jetstream.py` uses) and a real Postgres test database -- not mocked. If no broker is
reachable, every test in this module is skipped rather than silently passing against nothing, matching
`test_eventbus_jetstream.py`'s own established pattern.

Each test uses its own unique subject (`gxp.v1.material_lot.TestLot..._<unique>`) and durable consumer
name so it only ever sees messages it published itself -- the `GXP_EVENTS` stream is long-lived and
shared across test runs on this host, and a fresh durable consumer defaults to replaying the stream from
the beginning (`deliver_policy=ALL`, EVT-FR-... "a new durable never silently skips already-published
events"), so an unscoped subject would pick up every other test's (and every prior run's) messages too.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.modules.eventbus import consumer as eventbus_consumer
from app.modules.eventbus import jetstream
from app.modules.eventbus.models import ConsumerInbox
from app.modules.mutation.models import OutboxEvent
from app.modules.readmodels import projector
from app.modules.readmodels.models import ProjectionDocumentMetadata
from app.mutation.gateway import write_audit_event


async def _nats_reachable() -> bool:
    try:
        await jetstream.connect()
        return jetstream.is_connected()
    except Exception:  # noqa: BLE001 - genuinely "not reachable", not a test failure
        return False


@pytest.fixture(scope="module", autouse=True)
async def _jetstream_connection():
    if not await _nats_reachable():
        pytest.skip(f"No live NATS JetStream broker reachable at {settings.nats_url} -- skipping, not faking")
    yield
    await jetstream.close()


def _envelope(*, aggregate_id: uuid.UUID, aggregate_version: int, event_id: uuid.UUID | None = None, event_type: str) -> dict:
    return {
        "event_id": str(event_id or uuid.uuid4()), "event_type": event_type, "schema_version": "1.0",
        "aggregate_type": "material_lot", "aggregate_id": str(aggregate_id), "aggregate_version": aggregate_version,
        "payload": {}, "correlation_id": str(uuid.uuid4()), "causation_id": None,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }


async def _publish(envelope: dict) -> None:
    await jetstream.publish(
        f"gxp.v1.material_lot.{envelope['event_type']}", json.dumps(envelope).encode("utf-8"),
        msg_id=envelope["event_id"],
    )


async def test_pull_subscribe_creates_a_real_durable_consumer():
    unique = uuid.uuid4().hex[:10]
    subject = f"gxp.v1.material_lot.TestLotSub_{unique}"
    sub = await jetstream.pull_subscribe(subject, durable_name=f"test-sub-{unique}")
    assert sub is not None
    # binding the same durable again is idempotent, not an error
    sub2 = await jetstream.pull_subscribe(subject, durable_name=f"test-sub-{unique}")
    assert sub2 is not None


async def test_projector_indexes_a_real_material_lot_event_end_to_end(db, seeded):
    """The full real path: publish a real material_lot envelope -> fetch it off the real broker via a
    real durable pull consumer -> `_process_one_message` runs `consume_event_idempotently` +
    `handle_material_lot_event` in one DB transaction -> the search index row exists with exactly the
    allowlisted field, and the message is acked (no further redelivery)."""
    unique = uuid.uuid4().hex[:10]
    subject = f"gxp.v1.material_lot.TestLotOK_{unique}"
    durable = f"test-ok-{unique}"
    aggregate_id = uuid.uuid4()
    actor = seeded["users"]["operator1"].id

    async with SessionLocal() as s:
        async with s.begin():
            await write_audit_event(
                s, site_id=None, aggregate_type="material_lot", aggregate_id=aggregate_id, aggregate_version=1,
                action="Created", actor_id=actor, correlation_id=uuid.uuid4(),
                new_value={"state": "QUARANTINED", "internal_lot": "SECRET-DO-NOT-INDEX"},
            )

    envelope = _envelope(aggregate_id=aggregate_id, aggregate_version=1, event_type=f"TestLotOK_{unique}")
    await _publish(envelope)

    sub = await jetstream.pull_subscribe(subject, durable_name=durable)
    msgs = await sub.fetch(1, timeout=5)
    assert len(msgs) == 1
    await eventbus_consumer._process_one_message(
        msgs[0], consumer_name=durable, handler=projector.handle_material_lot_event, max_deliver=6,
    )

    async with SessionLocal() as s:
        row = (
            await s.execute(
                select(ProjectionDocumentMetadata).where(ProjectionDocumentMetadata.entity_id == aggregate_id)
            )
        ).scalar_one()
        assert row.source_version == 1
        # READ-FR-009: only the allowlisted field made it in -- "internal_lot" did not.
        assert row.indexed_fields == {"state": "QUARANTINED"}

        inbox = (
            await s.execute(
                select(ConsumerInbox).where(
                    ConsumerInbox.consumer_name == durable, ConsumerInbox.event_id == uuid.UUID(envelope["event_id"])
                )
            )
        ).scalar_one()
        assert inbox.result == "PROCESSED"

    # acked -- nothing left to redeliver
    with pytest.raises(TimeoutError):
        await sub.fetch(1, timeout=2)


async def test_duplicate_event_id_does_not_rerun_the_handler(db, seeded):
    """EVT-FR-005/006: whatever real mechanism causes a second delivery of the same event_id (broker
    redelivery after a lost ack, an authorized replay), `consume_event_idempotently`'s DB-backed dedupe
    guard is what actually prevents the business effect from running twice -- this proves that guard
    directly against the real database, by calling it a second time for an event already recorded
    PROCESSED and asserting the handler is never invoked."""
    aggregate_id = uuid.uuid4()
    event_id = uuid.uuid4()
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            await write_audit_event(
                s, site_id=None, aggregate_type="material_lot", aggregate_id=aggregate_id, aggregate_version=1,
                action="Created", actor_id=actor, correlation_id=uuid.uuid4(), new_value={"state": "RELEASED"},
            )

    calls = {"n": 0}

    async def counting_handler(session, envelope):
        calls["n"] += 1
        return await projector.handle_material_lot_event(session, envelope)

    envelope = _envelope(aggregate_id=aggregate_id, aggregate_version=1, event_id=event_id, event_type="dup-probe")

    async with SessionLocal() as s:
        async with s.begin():
            await eventbus_consumer.consume_event_idempotently(
                s, consumer_name="test-dup-consumer", event_id=event_id, aggregate_version=1,
                handler=lambda: counting_handler(s, envelope),
            )
    assert calls["n"] == 1

    # second delivery of the identical event_id
    async def failing_if_called(session, envelope):
        raise AssertionError("handler must not run again for an already-processed event_id")

    async with SessionLocal() as s:
        async with s.begin():
            result = await eventbus_consumer.consume_event_idempotently(
                s, consumer_name="test-dup-consumer", event_id=event_id, aggregate_version=1,
                handler=lambda: failing_if_called(s, envelope),
            )
    assert calls["n"] == 1  # unchanged -- the real handler never ran a second time
    assert result["entity_id"] == str(aggregate_id)  # returns the first call's recorded result

    async with SessionLocal() as s:
        rows = (
            await s.execute(
                select(ProjectionDocumentMetadata).where(ProjectionDocumentMetadata.entity_id == aggregate_id)
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].version == 1  # only ever indexed once


async def test_failed_handler_naks_for_real_broker_redelivery_then_dead_letters(db, seeded):
    """EVT-FR-009/010/026: a real handler failure (no matching audit event -- genuinely raised by
    `handle_material_lot_event`, not injected via a test double) naks instead of acking, the real broker
    redelivers (num_delivered increments for real), and once `max_deliver` is reached the message is
    dead-lettered (`consumer_inbox.result=DEAD_LETTERED` + a real `EventDeadLettered` outbox row) and
    `term()`-ed so the broker stops redelivering it -- proven by a subsequent fetch timing out."""
    unique = uuid.uuid4().hex[:10]
    subject = f"gxp.v1.material_lot.TestLotPoison_{unique}"
    durable = f"test-poison-{unique}"
    aggregate_id = uuid.uuid4()
    event_id = uuid.uuid4()
    max_deliver = 2

    # Deliberately no matching AuditEvent row -- handle_material_lot_event raises a real ValueError.
    envelope = _envelope(
        aggregate_id=aggregate_id, aggregate_version=1, event_id=event_id, event_type=f"TestLotPoison_{unique}"
    )
    await _publish(envelope)

    sub = await jetstream.pull_subscribe(subject, durable_name=durable, max_deliver=max_deliver, ack_wait_seconds=5)
    for attempt in range(1, max_deliver + 1):
        msgs = await sub.fetch(1, timeout=5)
        assert len(msgs) == 1
        assert msgs[0].metadata.num_delivered == attempt
        await eventbus_consumer._process_one_message(
            msgs[0], consumer_name=durable, handler=projector.handle_material_lot_event, max_deliver=max_deliver,
        )

    # dead-lettered: no further redelivery even though it was never acked
    with pytest.raises(TimeoutError):
        await sub.fetch(1, timeout=2)

    async with SessionLocal() as s:
        inbox = (
            await s.execute(
                select(ConsumerInbox).where(ConsumerInbox.consumer_name == durable, ConsumerInbox.event_id == event_id)
            )
        ).scalar_one()
        assert inbox.result == "DEAD_LETTERED"
        assert inbox.attempt_count >= 1

        dead_letter_events = (
            await s.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_type == "EventDeadLettered", OutboxEvent.aggregate_id == inbox.id,
                )
            )
        ).scalars().all()
        assert len(dead_letter_events) == 1
        assert dead_letter_events[0].payload["event_id"] == str(event_id)
        assert dead_letter_events[0].payload["consumer_name"] == durable

        # the original event is never deleted -- still indexed nowhere (the handler never succeeded),
        # but the consumer_inbox record of it (and the dead-letter outbox event) are permanent evidence.
        indexed = (
            await s.execute(
                select(ProjectionDocumentMetadata).where(ProjectionDocumentMetadata.entity_id == aggregate_id)
            )
        ).scalars().all()
        assert indexed == []


async def test_out_of_order_delivery_does_not_regress_the_index(db, seeded):
    """EVT-FR-014/027: at-least-once delivery gives no total-order guarantee. Apply version 2 first
    (the newer state), then version 1 (an older, late-arriving redelivery) -- the index must keep
    reflecting version 2, not regress to version 1's stale data."""
    aggregate_id = uuid.uuid4()
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            await write_audit_event(
                s, site_id=None, aggregate_type="material_lot", aggregate_id=aggregate_id, aggregate_version=1,
                action="Created", actor_id=actor, correlation_id=uuid.uuid4(), new_value={"state": "QUARANTINED"},
            )
        async with s.begin():
            await write_audit_event(
                s, site_id=None, aggregate_type="material_lot", aggregate_id=aggregate_id, aggregate_version=2,
                action="Changed", actor_id=actor, correlation_id=uuid.uuid4(), new_value={"state": "RELEASED"},
            )

    envelope_v2 = _envelope(aggregate_id=aggregate_id, aggregate_version=2, event_type="ooo-v2")
    envelope_v1 = _envelope(aggregate_id=aggregate_id, aggregate_version=1, event_type="ooo-v1")

    async with SessionLocal() as s:
        async with s.begin():
            await eventbus_consumer.consume_event_idempotently(
                s, consumer_name="test-ooo-consumer", event_id=uuid.UUID(envelope_v2["event_id"]), aggregate_version=2,
                handler=lambda: projector.handle_material_lot_event(s, envelope_v2),
            )
    async with SessionLocal() as s:
        async with s.begin():
            await eventbus_consumer.consume_event_idempotently(
                s, consumer_name="test-ooo-consumer", event_id=uuid.UUID(envelope_v1["event_id"]), aggregate_version=1,
                handler=lambda: projector.handle_material_lot_event(s, envelope_v1),
            )

    async with SessionLocal() as s:
        row = (
            await s.execute(
                select(ProjectionDocumentMetadata).where(ProjectionDocumentMetadata.entity_id == aggregate_id)
            )
        ).scalar_one()
        assert row.source_version == 2  # not regressed to 1
        assert row.indexed_fields == {"state": "RELEASED"}  # not overwritten with the stale "QUARANTINED"
