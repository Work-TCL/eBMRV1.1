"""Document 73 (SPEC-DATA-005) named outbox-publisher functions -- EVT-FR-002/003/004/018/025.

These formalize the three steps `app/main.py::outbox_publisher_loop` already performs (claim a batch
under `FOR UPDATE SKIP LOCKED`, publish, mark published) as independently testable functions, and are
what that loop now calls. The *pattern* -- write the domain event in the same PostgreSQL transaction as
the domain state (EVT-FR-002, already `app/mutation/gateway.py::write_outbox_event`), then publish only
after commit, idempotently, marking published only after broker acknowledgement (EVT-FR-004) -- is
unchanged; this module makes the three publisher steps nameable, testable and monitorable.

WP-11 (ADR-0011, SG-183): `publish_outbox_event()` now publishes for real to NATS JetStream
(`app.modules.eventbus.jetstream`) -- the canonical EVT-FR-001 envelope (event_id, event_type,
schema_version, aggregate id/version, payload, correlation/causation, occurred_at) is the JSON body;
`event_id` is also the JetStream message's `Nats-Msg-Id` header, giving the broker itself dedup-on-republish
for free (a crash between publish and `mark_outbox_published` simply republishes the same event_id, which
JetStream's own duplicate window recognizes as a duplicate -- `ack.duplicate` is recorded but never
treated as an error, same event, same effect). Raises on nack/timeout/not-connected, exactly as the prior
stand-in's docstring always said a real client would.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.eventbus import jetstream
from app.modules.mutation.models import OutboxEvent
from app.mutation.errors import OutboxPublishStateConflictError

logger = logging.getLogger("gxp_api.eventbus")

# EVT-FR-007: versioned subject namespace, environment.domain.event -- no sensitive data in the name.
_SUBJECT_PREFIX = "gxp.v1"


def subject_for(event: OutboxEvent) -> str:
    return f"{_SUBJECT_PREFIX}.{event.aggregate_type}.{event.event_type}"


async def claim_outbox_batch(
    session: AsyncSession, *, batch_size: int = 50
) -> list[OutboxEvent]:
    """`claimOutboxBatch()` -- reads committed, unpublished outbox rows under `SKIP LOCKED` so multiple
    publisher workers never double-claim the same row (EVT-FR-003)."""
    result = await session.execute(
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.occurred_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())


def _canonical_envelope(event: OutboxEvent) -> dict:
    """EVT-FR-001's canonical event envelope, built directly from the outbox row -- no second event
    shape, no re-derivation of anything the row does not already carry."""
    return {
        "event_id": str(event.id),
        "event_type": event.event_type,
        "schema_version": event.schema_version,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": str(event.aggregate_id),
        "aggregate_version": event.aggregate_version,
        "payload": event.payload,
        "correlation_id": str(event.correlation_id),
        "causation_id": str(event.causation_id) if event.causation_id else None,
        "occurred_at": event.occurred_at.isoformat(),
    }


async def publish_outbox_event(event: OutboxEvent) -> dict:
    """`publishOutboxEvent()` -- WP-11: publishes the canonical envelope to real NATS JetStream and
    waits for the broker's PubAck before returning. Raises on nack/timeout/not-connected so the caller
    (`mark_outbox_published`) never marks an unacknowledged publish as done (EVT-FR-004)."""
    subject = subject_for(event)
    envelope = _canonical_envelope(event)
    ack = await jetstream.publish(subject, json.dumps(envelope).encode("utf-8"), msg_id=str(event.id))
    logger.info(
        "published subject=%s event_id=%s aggregate=%s/%s version=%s stream=%s seq=%s duplicate=%s",
        subject, event.id, event.aggregate_type, event.aggregate_id, event.aggregate_version,
        ack["stream"], ack["seq"], ack["duplicate"],
    )
    return {
        "event_id": str(event.id), "subject": subject, "acknowledged": True,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "stream": ack["stream"], "seq": ack["seq"], "duplicate": ack["duplicate"],
    }


async def mark_outbox_published(
    session: AsyncSession, *, event: OutboxEvent, publish_receipt: dict
) -> None:
    """`markOutboxPublished()` -- only after `publish_receipt["acknowledged"]` is true. Raises
    `OutboxPublishStateConflictError` if this row was already marked published (a second publisher
    lost the race after claiming, or a caller re-marks an already-published row)."""
    if event.published_at is not None:
        raise OutboxPublishStateConflictError(
            "Outbox event was already marked published", event_id=str(event.id)
        )
    if not publish_receipt.get("acknowledged"):
        raise ValueError("cannot mark published without a broker acknowledgement")
    event.published_at = datetime.now(timezone.utc)


async def outbox_lag_seconds(session: AsyncSession) -> float | None:
    """EVT-FR-025 observability signal: age of the oldest unpublished outbox row, in seconds."""
    oldest = (
        await session.execute(
            select(OutboxEvent.occurred_at)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.occurred_at)
            .limit(1)
        )
    ).scalar_one_or_none()
    if oldest is None:
        return None
    now = datetime.now(timezone.utc)
    oldest_aware = oldest if oldest.tzinfo else oldest.replace(tzinfo=timezone.utc)
    return (now - oldest_aware).total_seconds()


async def check_outbox_lag(session: AsyncSession, *, threshold_seconds: float) -> dict:
    """EVT-FR-025: compares `outbox_lag_seconds()` to `threshold_seconds` and emits
    `OutboxLagExceeded` (best-effort monitoring signal) when it is exceeded."""
    from app.modules.eventbus.signals import emit_eventbus_signal

    lag = await outbox_lag_seconds(session)
    exceeded = lag is not None and lag > threshold_seconds
    if exceeded:
        await emit_eventbus_signal(
            "OutboxLagExceeded", {"lag_seconds": lag, "threshold_seconds": threshold_seconds}
        )
    return {"lag_seconds": lag, "threshold_seconds": threshold_seconds, "exceeded": exceeded}
