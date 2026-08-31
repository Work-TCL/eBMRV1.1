"""Document 73 (SPEC-DATA-005) poison-event handling -- EVT-FR-010/026.

`handle_poison_event()` is called by the consumer supervisor after a bounded number of handler
failures for one `(consumer_name, event_id)`. It records the disposition in `consumer_inbox`
(`result="DEAD_LETTERED"`, full attempt/error history) and emits `EventDeadLettered` -- the original
outbox event is never deleted or edited; the record is purely additive (AG-08 shape: append, never
mutate history away).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.eventbus.models import ConsumerInbox
from app.mutation.gateway import write_outbox_event


async def handle_poison_event(
    session: AsyncSession,
    *,
    consumer_name: str,
    event_id: uuid.UUID,
    failure_history: list[str],
    reason: str,
) -> ConsumerInbox:
    """Runs inside its own committed transaction (the failing handler's transaction already rolled
    back). Upserts the `consumer_inbox` row to `DEAD_LETTERED` and emits `EventDeadLettered`."""
    row = (
        await session.execute(
            select(ConsumerInbox).where(
                ConsumerInbox.consumer_name == consumer_name, ConsumerInbox.event_id == event_id
            )
        )
    ).scalar_one_or_none()
    attempt_count = len(failure_history) or 1
    last_error = failure_history[-1] if failure_history else reason

    if row is None:
        row = ConsumerInbox(
            consumer_name=consumer_name, event_id=event_id, result="DEAD_LETTERED",
            detail={"reason": reason, "failure_history": failure_history}, attempt_count=attempt_count,
            last_error=last_error,
        )
        session.add(row)
    else:
        row.result = "DEAD_LETTERED"
        row.detail = {"reason": reason, "failure_history": failure_history}
        row.attempt_count = attempt_count
        row.last_error = last_error
    await session.flush()

    await write_outbox_event(
        session, event_type="EventDeadLettered", aggregate_type="consumer_inbox", aggregate_id=row.id,
        aggregate_version=1,
        payload={
            "consumer_name": consumer_name, "event_id": str(event_id), "attempt_count": attempt_count,
            "reason": reason, "dead_lettered_at": datetime.now(timezone.utc).isoformat(),
        },
        correlation_id=uuid.uuid4(),
    )
    return row
