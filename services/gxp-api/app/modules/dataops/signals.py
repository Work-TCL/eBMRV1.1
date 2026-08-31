"""Document 69 (SPEC-DATA-001) # 9 operational signals that are *detected on a read path* and so
cannot be written inside a domain transaction: `ProjectionStaleDetected`, `CrossStoreMismatchDetected`.

Same self-committing, best-effort pattern as `app/modules/security/telemetry.py::record_security_event`
-- its own short-lived `SessionLocal()` (the read handler's session may be mid-transaction or about to
close), and a write failure is logged, never raised: a monitoring signal must never break or block the
read it was observing.

`ProjectionRebuilt`, `ProjectionUpdateRequested` and `MigrationProvenanceRecorded` are NOT here -- they
are emitted transactionally from `commands.py` via the Mutation Gateway outbox (EVT-FR-002).
"""

from __future__ import annotations

import logging
import uuid

from app.core.db import SessionLocal
from app.mutation.gateway import write_outbox_event

logger = logging.getLogger("gxp_api.dataops_signals")


async def _emit(event_type: str, payload: dict) -> None:
    try:
        async with SessionLocal() as session:
            async with session.begin():
                await write_outbox_event(
                    session,
                    event_type=event_type,
                    aggregate_type="projection_checkpoint",
                    aggregate_id=uuid.uuid4(),
                    aggregate_version=1,
                    payload=payload,
                    correlation_id=uuid.uuid4(),
                )
    except Exception:  # noqa: BLE001 - a monitoring signal must never break the read it observed
        logger.exception("failed to emit dataops signal event_type=%s", event_type)


async def emit_projection_stale_detected(freshness: dict) -> None:
    await _emit("ProjectionStaleDetected", freshness)


async def emit_cross_store_mismatch_detected(report: dict) -> None:
    await _emit("CrossStoreMismatchDetected", report)
