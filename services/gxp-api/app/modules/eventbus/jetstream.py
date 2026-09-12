"""Document 73 (SPEC-DATA-005) real NATS JetStream transport -- ADR-0011 (SG-183), replacing the Phase 1
in-process stand-in `outbox.py::publish_outbox_event()` documented as swappable from day one.

Owns the one process-wide NATS connection + JetStream context. `app/main.py`'s lifespan connects at
startup and closes at shutdown. A connection failure here never blocks a regulated mutation from
committing (AG-09: NATS is transport, not authoritative -- the outbox row is) -- it only delays
`outbox_publisher_loop`'s next successful publish, which retries every iteration via nats-py's own
infinite-reconnect client (`max_reconnect_attempts=-1`).
"""

from __future__ import annotations

import logging

import nats
from nats.aio.client import Client as NatsClient
from nats.js.client import JetStreamContext

from app.core.config import settings

logger = logging.getLogger("gxp_api.eventbus.jetstream")

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
    not exist yet (JetStream's own `add_stream` is idempotent against an identical config)."""
    global _nc, _js
    if _nc is not None and _nc.is_connected:
        return
    _nc = await nats.connect(
        settings.nats_url, reconnect_time_wait=2, max_reconnect_attempts=-1,
        name="gxp-api-outbox-publisher",
        error_cb=_on_error, disconnected_cb=_on_disconnected, reconnected_cb=_on_reconnected,
    )
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
