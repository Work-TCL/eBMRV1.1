"""Document 73 (SPEC-DATA-005) real NATS JetStream transport -- ADR-0011 (SG-183), replacing the Phase 1
in-process stand-in `outbox.py::publish_outbox_event()` documented as swappable from day one.

Owns the one process-wide NATS connection + JetStream context. `app/main.py`'s lifespan connects at
startup and closes at shutdown. A connection failure here never blocks a regulated mutation from
committing (AG-09: NATS is transport, not authoritative -- the outbox row is) -- it only delays
`outbox_publisher_loop`'s next successful publish, which retries every iteration.

`connect()` is deliberately bounded (`asyncio.wait_for(..., timeout=CONNECT_TIMEOUT_SECONDS)`), not
nats-py's own `max_reconnect_attempts=-1`: that setting governs nats-py's *initial* connection attempt
too, not just post-connect reconnection (verified against nats-py's own `Client.connect()` source -- on
`NoServersError` with a negative `max_reconnect_attempts` it `continue`s its retry loop forever rather
than raising). Left unbounded, a single unreachable broker would hang `connect()` -- and therefore
`app/main.py`'s startup `await` of it -- indefinitely, which is a *worse* failure than the "logged, not
fatal" behavior this module documents. The bound makes `connect()` fail fast and predictably instead;
resilience against a later, temporary broker outage comes from `outbox_publisher_loop`'s own existing
every-2-seconds retry calling `publish()`, not from an internal infinite reconnect loop.

WP-11 Stage 3 (SG-183): `pull_subscribe()` adds the durable pull-consumer primitive (EVT-FR-009) the
Stage 1 producer-only pass deliberately left open. Same bounded-timeout discipline as `connect()` --
`_js.pull_subscribe()`'s own consumer-create round trip to the broker is wrapped in
`asyncio.wait_for(..., timeout=SUBSCRIBE_TIMEOUT_SECONDS)` rather than left to hang if the broker never
responds.
"""

from __future__ import annotations

import asyncio
import logging

import nats
from nats.aio.client import Client as NatsClient
from nats.js import api as js_api
from nats.js.client import JetStreamContext

from app.core.config import settings

logger = logging.getLogger("gxp_api.eventbus.jetstream")

# Hard ceiling on the initial connection attempt -- see connect()'s own docstring for why this exists
# instead of relying on nats-py's max_reconnect_attempts for the first connect.
CONNECT_TIMEOUT_SECONDS = 5

# Hard ceiling on creating/binding a durable pull consumer -- same rationale as CONNECT_TIMEOUT_SECONDS.
SUBSCRIBE_TIMEOUT_SECONDS = 5

# EVT-FR-009 consumer durability defaults: bounded redelivery (not infinite) and a bounded ack window
# (not the library default) so a hung handler doesn't hold a message un-redeliverable indefinitely.
DEFAULT_MAX_DELIVER = 6
DEFAULT_ACK_WAIT_SECONDS = 30.0

# EVT-FR-007: versioned subject namespace, environment.domain.event. One stream captures every
# subject this service ever publishes under `gxp.v1.*` (outbox.py's own `_SUBJECT_PREFIX`).
STREAM_NAME = "GXP_EVENTS"
STREAM_SUBJECTS = ["gxp.v1.>"]

_nc: NatsClient | None = None
_js: JetStreamContext | None = None


async def _on_error(e: Exception) -> None:
    logger.warning("NATS client error: %s", e)


async def _on_disconnected() -> None:
    logger.warning("NATS disconnected, reconnecting...")


async def _on_reconnected() -> None:
    logger.info("NATS reconnected")


async def connect() -> None:
    """Idempotent: a second call while already connected is a no-op. Declares the stream if it does
    not exist yet (JetStream's own `add_stream` is idempotent against an identical config). Raises
    `ConnectionError` (never hangs) if no broker is reachable within `CONNECT_TIMEOUT_SECONDS`."""
    global _nc, _js
    if _nc is not None and _nc.is_connected:
        return
    try:
        _nc = await asyncio.wait_for(
            nats.connect(
                settings.nats_url, reconnect_time_wait=2, max_reconnect_attempts=5,
                name="gxp-api-outbox-publisher",
                error_cb=_on_error, disconnected_cb=_on_disconnected, reconnected_cb=_on_reconnected,
            ),
            timeout=CONNECT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise ConnectionError(
            f"No NATS JetStream broker reachable at {settings.nats_url} within {CONNECT_TIMEOUT_SECONDS}s"
        ) from exc
    _js = _nc.jetstream()
    await _js.add_stream(name=STREAM_NAME, subjects=STREAM_SUBJECTS)
    logger.info("connected to NATS JetStream at %s, stream=%s", settings.nats_url, STREAM_NAME)


async def close() -> None:
    global _nc, _js
    if _nc is not None:
        await _nc.drain()
    _nc = None
    _js = None


def is_connected() -> bool:
    return _nc is not None and _nc.is_connected


async def publish(subject: str, payload: bytes, *, msg_id: str | None = None) -> dict:
    """Publishes to JetStream and waits for the broker's PubAck (EVT-FR-004: never acknowledge before
    the broker durably stores it). `msg_id` (the outbox event_id) is sent as the `Nats-Msg-Id` header --
    JetStream's own dedup window recognizes a republish of the same id as a duplicate rather than a new
    message, which is what a crash between publish and `mark_outbox_published` produces. Raises
    (ConnectionError / nats.errors.* / nats.js.errors.*) on not-connected, nack or timeout -- callers
    must never mark an outbox row published without a successful return here."""
    if _js is None:
        raise ConnectionError("NATS JetStream is not connected")
    headers = {"Nats-Msg-Id": msg_id} if msg_id else None
    ack = await _js.publish(subject, payload, headers=headers)
    return {"stream": ack.stream, "seq": ack.seq, "duplicate": bool(ack.duplicate)}


async def pull_subscribe(
    subject: str,
    *,
    durable_name: str,
    max_deliver: int = DEFAULT_MAX_DELIVER,
    ack_wait_seconds: float = DEFAULT_ACK_WAIT_SECONDS,
) -> JetStreamContext.PullSubscription:
    """EVT-FR-009: binds (creating if absent) a durable named pull consumer on `subject` -- explicit ack
    policy, `deliver_policy=ALL` (a new durable starts from the beginning of the stream's retention, not
    "now", so it never silently skips events published before it first bound), bounded `max_deliver`
    (EVT-FR-010: a message stops being redelivered after this many attempts -- the caller is responsible
    for dead-lettering at that point, this function only creates the consumer) and `ack_wait_seconds`
    (how long the broker waits for an ack before treating a delivery as failed and redelivering).
    JetStream's own `pull_subscribe` is idempotent against an identical existing consumer config, same as
    `connect()`'s `add_stream`. Raises `ConnectionError` (never hangs) if not connected or the broker does
    not respond within `SUBSCRIBE_TIMEOUT_SECONDS`."""
    if _js is None:
        raise ConnectionError("NATS JetStream is not connected")
    config = js_api.ConsumerConfig(
        durable_name=durable_name,
        ack_policy=js_api.AckPolicy.EXPLICIT,
        deliver_policy=js_api.DeliverPolicy.ALL,
        max_deliver=max_deliver,
        ack_wait=ack_wait_seconds,
    )
    try:
        return await asyncio.wait_for(
            _js.pull_subscribe(subject, durable=durable_name, config=config),
            timeout=SUBSCRIBE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise ConnectionError(
            f"Could not create/bind durable consumer {durable_name!r} on {subject!r} within "
            f"{SUBSCRIBE_TIMEOUT_SECONDS}s"
        ) from exc
