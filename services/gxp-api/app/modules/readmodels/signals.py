"""Document 75 (SPEC-DATA-007) best-effort signals -- `SearchDocumentIndexed`, `CacheInvalidated`,
`ProjectionLagExceeded`. Same self-committing pattern as every other module's signals.py: these
describe the cache/search tier itself (or a single indexed document), not a domain state change, and a
signal write failure must never break the cache/index operation it observed.

`SearchIndexRebuilt`, `ReadModelRefreshed` and `ExportGenerated` are NOT here -- they are the
Mutation-Gateway outbox events for this module's 3 state-changing commands (`commands.py`).
"""

from __future__ import annotations

import logging
import uuid

from app.core.db import SessionLocal
from app.mutation.gateway import write_outbox_event

logger = logging.getLogger("gxp_api.readmodels_signals")

_EVENT_TYPES = {"SearchDocumentIndexed", "CacheInvalidated", "ProjectionLagExceeded"}


async def _emit(event_type: str, payload: dict) -> None:
    if event_type not in _EVENT_TYPES:
        raise ValueError(f"unknown readmodels signal {event_type!r}")
    try:
        async with SessionLocal() as session:
            async with session.begin():
                await write_outbox_event(
                    session, event_type=event_type, aggregate_type="read_model_pipeline",
                    aggregate_id=uuid.uuid4(), aggregate_version=1, payload=payload,
                    correlation_id=uuid.uuid4(),
                )
    except Exception:  # noqa: BLE001 - a monitoring signal must never break the operation it observed
        logger.exception("failed to emit readmodels signal event_type=%s", event_type)


async def emit_search_document_indexed(payload: dict) -> None:
    await _emit("SearchDocumentIndexed", payload)


async def emit_cache_invalidated(payload: dict) -> None:
    await _emit("CacheInvalidated", payload)


async def emit_projection_lag_exceeded(payload: dict) -> None:
    await _emit("ProjectionLagExceeded", payload)
