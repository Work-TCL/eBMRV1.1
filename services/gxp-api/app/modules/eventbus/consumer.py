"""Document 73 (SPEC-DATA-005) consumer-side idempotency -- EVT-FR-005/006/026/027.

`consume_event_idempotently()` wraps a consumer handler with the `consumer_inbox` dedupe record: if
`(consumer_name, event_id)` was already processed, the prior result is returned and the handler does
not run again (safe under at-least-once delivery / redelivery / replay). A handler failure records the
attempt (with `attempt_count` incremented) and re-raises as `HandlerFailedError` -- a business-validation
failure, distinct from a transient dependency failure the caller should retry untouched (EVT-FR-026).
"""

from __future__ import annotations

import uuid
from typing import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.eventbus.models import ConsumerInbox
from app.mutation.errors import EventAlreadyProcessedError, HandlerFailedError


async def consume_event_idempotently(
    session: AsyncSession,
    *,
    consumer_name: str,
    event_id: uuid.UUID,
    aggregate_version: int | None,
    handler: Callable[[], Awaitable[dict]],
    raise_if_duplicate: bool = False,
) -> dict:
    """Runs `handler()` at most once per `(consumer_name, event_id)`. On redelivery, returns the
    recorded `detail` from the first successful processing (or raises `EventAlreadyProcessedError` if
    `raise_if_duplicate=True`, for a caller that wants to distinguish "already done" from "just did
    it"). Must be called inside the caller's own transaction so the inbox row commits atomically with
    whatever domain effect `handler()` produces (same shape as the Mutation Gateway's one-transaction
    rule)."""
    existing = (
        await session.execute(
            select(ConsumerInbox).where(
                ConsumerInbox.consumer_name == consumer_name, ConsumerInbox.event_id == event_id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.result == "DEAD_LETTERED":
            raise HandlerFailedError(
                "Event was already dead-lettered for this consumer", consumer_name=consumer_name,
                event_id=str(event_id),
            )
        if raise_if_duplicate:
            raise EventAlreadyProcessedError(
                "Event already processed by this consumer", consumer_name=consumer_name,
                event_id=str(event_id),
            )
        return existing.detail

    try:
        result = await handler()
    except Exception as exc:  # noqa: BLE001 -- classified as a business-validation failure here
        # Deliberately does NOT write a consumer_inbox row here: this call is inside the caller's
        # transaction, which is about to roll back with this exception, so any insert here would be
        # rolled back too. Attempt/failure history is `handle_poison_event()`'s job, in its own
        # committed transaction after `attempts` such failures (EVT-FR-010/026).
        raise HandlerFailedError(
            "Consumer handler failed", consumer_name=consumer_name, event_id=str(event_id), detail=str(exc)
        ) from exc

    session.add(
        ConsumerInbox(
            consumer_name=consumer_name, event_id=event_id, aggregate_version=aggregate_version,
            result="PROCESSED", detail=result or {}, attempt_count=1,
        )
    )
    return result or {}
