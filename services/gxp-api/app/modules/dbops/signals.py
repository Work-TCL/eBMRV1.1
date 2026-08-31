"""Document 70 (SPEC-DATA-002) # 9 operational signals.

Six DB-health events -- `DatabaseIntegrityFailure`, `PartitionGapDetected`, `ReplicaLagExceeded`,
`MigrationApplied`, `DeadlockDetected`, `ConnectionPoolExhausted`. They describe infrastructure
conditions observed by DBA automation / the migration runner / the connection pool, none of which sits
inside a domain transaction, so each is written best-effort in its own committed transaction -- the
same self-committing pattern as `app/modules/security/telemetry.py` and `app/modules/dataops/signals.py`.

`MigrationApplied` is emitted by the Alembic post-run hook (see `migrations/env.py` note); the others by
the `dbops` maintenance helpers when a check fails. A write failure here is logged, never raised.
"""

from __future__ import annotations

import logging
import uuid

from app.core.db import SessionLocal
from app.mutation.gateway import write_outbox_event

logger = logging.getLogger("gxp_api.dbops_signals")

_EVENT_TYPES = {
    "DatabaseIntegrityFailure",
    "PartitionGapDetected",
    "ReplicaLagExceeded",
    "MigrationApplied",
    "DeadlockDetected",
    "ConnectionPoolExhausted",
}


async def emit_db_signal(event_type: str, payload: dict) -> None:
    if event_type not in _EVENT_TYPES:
        raise ValueError(f"unknown dbops signal {event_type!r}")
    try:
        async with SessionLocal() as session:
            async with session.begin():
                await write_outbox_event(
                    session,
                    event_type=event_type,
                    aggregate_type="database_health",
                    aggregate_id=uuid.uuid4(),
                    aggregate_version=1,
                    payload=payload,
                    correlation_id=uuid.uuid4(),
                )
    except Exception:  # noqa: BLE001 - a health signal must never break the check that produced it
        logger.exception("failed to emit dbops signal event_type=%s", event_type)
