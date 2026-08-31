"""Document 73 (SPEC-DATA-005) # 9 monitoring signals -- EventPublished, EventSchemaBreakingChangeDetected,
ConsumerLagExceeded, OutboxLagExceeded. Same self-committing, best-effort pattern as
`app/modules/dataops/signals.py` / `app/modules/dbops/signals.py`: these describe the transport/pipeline
itself, not a domain state change, so they are never written inside the transaction of the thing they
are describing (publishing `EventPublished` transactionally for every outbox publish would recurse
forever) -- and a signal write failure must never break the pipeline it is observing.

`EventDeadLettered` and `EventReplayStarted` are NOT here -- they are real domain-adjacent state
changes and are emitted transactionally by `dead_letter.py` / `replay.py` through the Mutation Gateway
outbox (EVT-FR-002).
"""

from __future__ import annotations

import logging
import uuid

from app.core.db import SessionLocal
from app.mutation.gateway import write_outbox_event

logger = logging.getLogger("gxp_api.eventbus_signals")

_EVENT_TYPES = {"EventPublished", "EventSchemaBreakingChangeDetected", "ConsumerLagExceeded", "OutboxLagExceeded"}


async def emit_eventbus_signal(event_type: str, payload: dict) -> None:
    if event_type not in _EVENT_TYPES:
        raise ValueError(f"unknown eventbus signal {event_type!r}")
    try:
        async with SessionLocal() as session:
            async with session.begin():
                await write_outbox_event(
                    session, event_type=event_type, aggregate_type="event_pipeline",
                    aggregate_id=uuid.uuid4(), aggregate_version=1, payload=payload,
                    correlation_id=uuid.uuid4(),
                )
    except Exception:  # noqa: BLE001 - a monitoring signal must never break the pipeline it observed
        logger.exception("failed to emit eventbus signal event_type=%s", event_type)
