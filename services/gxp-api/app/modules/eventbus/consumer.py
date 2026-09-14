"""Document 73 (SPEC-DATA-005) consumer-side idempotency -- EVT-FR-005/006/026/027.

`consume_event_idempotently()` wraps a consumer handler with the `consumer_inbox` dedupe record: if
`(consumer_name, event_id)` was already processed, the prior result is returned and the handler does
not run again (safe under at-least-once delivery / redelivery / replay). A handler failure records the
attempt (with `attempt_count` incremented) and re-raises as `HandlerFailedError` -- a business-validation
failure, distinct from a transient dependency failure the caller should retry untouched (EVT-FR-026).

WP-11 Stage 3 (SG-183): `run_pull_consumer()` is the generic real driver -- Stage 1/pre-Stage-3 built
`consume_event_idempotently()` and `dead_letter.py::handle_poison_event()` as standalone primitives with
nothing calling either from a real subscription; this is the first thing that does. It binds a durable
JetStream pull consumer (`jetstream.pull_subscribe`), and for each delivered message: opens one DB
session/transaction, runs the parsed envelope through `consume_event_idempotently()` (so the dedupe row
and whatever the handler writes commit atomically -- same one-transaction discipline the Mutation Gateway
uses), acks only after that commits, naks (lets the broker redeliver) on a handler failure below
`max_deliver`, and dead-letters (`handle_poison_event()` in its own committed transaction, then
`msg.term()`) once `max_deliver` is reached. `msg.term()` stops JetStream redelivering that message; it
does not delete it from the stream (EVT-FR-010's "without deleting the original event" -- the `GXP_EVENTS`
stream uses limits-based retention, not work-queue, so an acked/termed message stays retained regardless).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.modules.eventbus import jetstream
from app.modules.eventbus.dead_letter import handle_poison_event
from app.modules.eventbus.models import ConsumerInbox
from app.mutation.errors import EventAlreadyProcessedError, HandlerFailedError

logger = logging.getLogger("gxp_api.eventbus.consumer")


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


async def run_pull_consumer(
    *,
    subject: str,
    durable_name: str,
    handler: Callable[[AsyncSession, dict], Awaitable[dict]],
    consumer_name: str | None = None,
    max_deliver: int = jetstream.DEFAULT_MAX_DELIVER,
    ack_wait_seconds: float = jetstream.DEFAULT_ACK_WAIT_SECONDS,
    fetch_batch: int = 10,
    fetch_timeout_seconds: float = 5,
    idle_sleep_seconds: float = 1,
    stop_event: asyncio.Event,
) -> None:
    """Runs until `stop_event` is set (app shutdown) -- same embedded-background-task shape as
    `app/main.py::outbox_publisher_loop` and `workflowops/worker.py::run_worker`. Never raises out to the
    caller: if the durable consumer cannot even be created (broker unreachable at startup), this logs and
    returns without running, the same fail-open-for-transport posture `jetstream.connect()`'s own callers
    already use (AG-09: NATS is transport, its unavailability cannot block the regulated API)."""
    name = consumer_name or durable_name
    try:
        sub = await jetstream.pull_subscribe(
            subject, durable_name=durable_name, max_deliver=max_deliver, ack_wait_seconds=ack_wait_seconds
        )
    except Exception:  # noqa: BLE001 - not connected/reachable; nothing to run this pass
        logger.exception(
            "could not create durable consumer name=%s subject=%s; this consumer will not run", name, subject
        )
        return

    logger.info("consumer %s polling subject=%s durable=%s", name, subject, durable_name)
    while not stop_event.is_set():
        try:
            msgs = await sub.fetch(fetch_batch, timeout=fetch_timeout_seconds)
        except TimeoutError:
            # nats-py raises this on an empty fetch (no message within the timeout) -- expected under
            # normal idle polling, not a failure.
            continue
        except Exception:  # noqa: BLE001 - transport hiccup; keep polling, never die
            logger.exception("consumer %s fetch failed; retrying", name)
            await asyncio.sleep(idle_sleep_seconds)
            continue
        for msg in msgs:
            await _process_one_message(msg, consumer_name=name, handler=handler, max_deliver=max_deliver)
    logger.info("consumer %s stopped", name)


async def _process_one_message(
    msg, *, consumer_name: str, handler: Callable[[AsyncSession, dict], Awaitable[dict]], max_deliver: int
) -> None:
    """One delivered JetStream message end to end. Never raises -- a defect in one message must not take
    the whole consumer loop down; it is contained to that message (nak/dead-letter it) and logged."""
    try:
        envelope = json.loads(msg.data)
        event_id = uuid.UUID(envelope["event_id"])
    except Exception:  # noqa: BLE001 - not a parseable canonical envelope at all
        logger.exception("consumer %s received an unparseable message; dead-lettering without retry", consumer_name)
        await _dead_letter_message(
            msg, consumer_name=consumer_name, event_id=uuid.uuid4(), failure_history=["unparseable envelope"],
            reason="unparseable envelope -- not the canonical EVT-FR-001 shape",
        )
        return

    try:
        async with SessionLocal() as session:
            async with session.begin():
                await consume_event_idempotently(
                    session, consumer_name=consumer_name, event_id=event_id,
                    aggregate_version=envelope.get("aggregate_version"),
                    handler=lambda: handler(session, envelope),
                )
        await msg.ack()
    except HandlerFailedError as exc:
        num_delivered = (msg.metadata.num_delivered if msg.metadata else None) or 1
        if num_delivered >= max_deliver:
            await _dead_letter_message(
                msg, consumer_name=consumer_name, event_id=event_id,
                failure_history=[str(exc.details.get("detail", exc.message))], reason=str(exc.message),
            )
        else:
            logger.warning(
                "consumer %s handler failed for event_id=%s (attempt %s/%s); nak for redelivery: %s",
                consumer_name, event_id, num_delivered, max_deliver, exc,
            )
            await msg.nak()
    except Exception:  # noqa: BLE001 - unexpected failure outside consume_event_idempotently's own wrap
        logger.exception("consumer %s: unexpected failure processing event_id=%s; nak for redelivery", consumer_name, event_id)
        await msg.nak()


async def _dead_letter_message(
    msg, *, consumer_name: str, event_id: uuid.UUID, failure_history: list[str], reason: str
) -> None:
    """EVT-FR-010: bounded attempts exhausted -- record the disposition (own committed transaction, since
    the failing handler's transaction already rolled back) and `term()` the message so JetStream stops
    redelivering it. The original message is never deleted from the stream (limits retention, not
    work-queue)."""
    try:
        async with SessionLocal() as session:
            async with session.begin():
                await handle_poison_event(
                    session, consumer_name=consumer_name, event_id=event_id,
                    failure_history=failure_history, reason=reason,
                )
    except Exception:  # noqa: BLE001 - dead-lettering itself must not crash the consumer loop
        logger.exception("consumer %s: failed to dead-letter event_id=%s", consumer_name, event_id)
    await msg.term()
