"""Document 73 (SPEC-DATA-005) authorized outbox/consumer replay -- EVT-FR-016/017.

`replay_consumer_events()` is an Integration Admin operation: it announces and audits an intended
replay window (`EventReplayStarted`) but does **not** clear or delete existing `consumer_inbox` rows --
the app role has no `DELETE` grant on `eventbus.*` (same append-only discipline as everywhere else),
and silently forcing re-processing of an already-PROCESSED event risks re-executing a non-idempotent
business effect (the exact failure mode EVT-FR-016 exists to prevent). A genuine replay is therefore a
controlled two-step: this call records *why* and *what scope* is being replayed and returns the
existing dispositions for that scope; actually re-driving the consumer for a specific event is a
separate, explicit per-event operational action outside Phase 1's scope (recorded as a known
limitation, not guessed).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.eventbus.models import ConsumerInbox
from app.mutation.gateway import write_outbox_event


async def replay_consumer_events(
    session: AsyncSession,
    *,
    consumer_name: str,
    event_ids: list[uuid.UUID],
    reason: str,
    actor_user_id: uuid.UUID,
) -> dict:
    if not event_ids:
        raise ValueError("event_ids must be non-empty")
    if not reason:
        raise ValueError("reason is required for a replay (EVT-FR-016/017)")

    existing = (
        await session.execute(
            select(ConsumerInbox).where(
                ConsumerInbox.consumer_name == consumer_name, ConsumerInbox.event_id.in_(event_ids)
            )
        )
    ).scalars().all()
    already_processed = {str(r.event_id) for r in existing if r.result == "PROCESSED"}
    already_dead_lettered = {str(r.event_id) for r in existing if r.result == "DEAD_LETTERED"}
    never_processed = [str(e) for e in event_ids if str(e) not in already_processed | already_dead_lettered]

    correlation_id = uuid.uuid4()
    await write_outbox_event(
        session, event_type="EventReplayStarted", aggregate_type="consumer_inbox",
        aggregate_id=uuid.uuid4(), aggregate_version=1,
        payload={
            "consumer_name": consumer_name, "event_ids": [str(e) for e in event_ids], "reason": reason,
            "requested_by": str(actor_user_id), "started_at": datetime.now(timezone.utc).isoformat(),
        },
        correlation_id=correlation_id,
    )
    return {
        "consumer_name": consumer_name, "scope": [str(e) for e in event_ids],
        "already_processed": sorted(already_processed), "already_dead_lettered": sorted(already_dead_lettered),
        "never_processed": never_processed, "reason": reason,
    }
