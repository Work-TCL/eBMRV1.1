"""Document 73 (SPEC-DATA-005), WP-11 (ADR-0011, SG-183): the real NATS JetStream publisher.

Every test here runs against a genuinely live local NATS JetStream server (`infra/nats-server.conf`,
container `ebmr-new-nats` on `127.0.0.1:4222`) -- not a mock. If no broker is reachable at
`GXP_NATS_URL` (default `nats://127.0.0.1:4222`), every test in this module is skipped rather than
silently passing against nothing (never fabricate evidence of a broker round trip that did not happen).
"""

import json
import uuid

import pytest

from app.core.config import settings
from app.modules.eventbus import jetstream
from app.modules.eventbus.outbox import _canonical_envelope, publish_outbox_event, subject_for
from app.modules.mutation.models import OutboxEvent


async def _nats_reachable() -> bool:
    try:
        await jetstream.connect()
        return jetstream.is_connected()
    except Exception:  # noqa: BLE001 - genuinely "not reachable", not a test failure
        return False


@pytest.fixture(scope="module", autouse=True)
async def _jetstream_connection():
    """Module-scoped: the reachability probe (and its connect timeout if no broker exists) runs once
    for this whole file, not once per test -- six independent ~5s connect-timeout cycles would otherwise
    add up whenever no broker is reachable (e.g. CI, which has none configured)."""
    if not await _nats_reachable():
        pytest.skip(f"No live NATS JetStream broker reachable at {settings.nats_url} -- skipping, not faking")
    yield
    await jetstream.close()


def _make_event(**overrides) -> OutboxEvent:
    # Unique subject per call (not just per-field id) -- each test gets its own JetStream subject so
    # cross-talk from another test's still-retained messages on the shared stream is impossible, rather
    # than relying on consumer deliver-policy nuances to skip older messages.
    unique = uuid.uuid4().hex[:12]
    defaults = dict(
        id=uuid.uuid4(), event_type=f"TestEventPublished_{unique}", schema_version="1.0",
        aggregate_type="test_aggregate", aggregate_id=uuid.uuid4(), aggregate_version=1,
        payload={"hello": "world"}, correlation_id=uuid.uuid4(), causation_id=None,
    )
    defaults.update(overrides)
    from datetime import datetime, timezone
    event = OutboxEvent(**defaults)
    event.occurred_at = datetime.now(timezone.utc)
    return event


async def test_publish_outbox_event_round_trips_through_real_jetstream():
    event = _make_event()
    receipt = await publish_outbox_event(event)
    assert receipt["acknowledged"] is True
    assert receipt["subject"] == subject_for(event)
    assert receipt["seq"] >= 1
    assert receipt["duplicate"] is False


async def test_publish_outbox_event_envelope_is_the_canonical_shape():
    event = _make_event()
    from nats.js.client import JetStreamContext

    js: JetStreamContext = jetstream._js  # noqa: SLF001 - test-only introspection of the connected context
    subject = subject_for(event)

    sub = await js.pull_subscribe(subject, durable=f"test-durable-{uuid.uuid4().hex[:8]}")
    await publish_outbox_event(event)
    msgs = await sub.fetch(1, timeout=5)
    assert len(msgs) == 1
    body = json.loads(msgs[0].data)
    assert body == _canonical_envelope(event)
    await msgs[0].ack()


async def test_republishing_the_same_event_id_is_recognized_as_a_duplicate():
    """Simulates the crash-between-publish-and-mark-published scenario: the same outbox row is
    published twice with the same event_id -- JetStream's own dedup window (keyed on Nats-Msg-Id, which
    publish_outbox_event sets to str(event.id)) recognizes the second as a duplicate rather than a new
    message, so a retried publish after a crash never double-delivers."""
    event = _make_event()
    first = await publish_outbox_event(event)
    second = await publish_outbox_event(event)
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    # same message, not appended twice
    assert first["seq"] == second["seq"]


async def test_publish_raises_when_not_connected():
    await jetstream.close()
    event = _make_event()
    with pytest.raises(ConnectionError):
        await publish_outbox_event(event)


async def test_connect_is_idempotent():
    await jetstream.connect()
    await jetstream.connect()
    assert jetstream.is_connected() is True
