"""Document 76 (SPEC-DATA-008) monitoring signals -- `BackupRPOAtRisk`. Best-effort, self-committing,
own transaction (same pattern as every other module's signals.py) -- a monitoring read must never
break on a signal-write failure. `RestoreTestFailed`, `EvidenceRestoreMismatch`,
`PlatformRecoveryValidated`/`RecoveryValidationFailed`, `RecoveryDataLossDetected` and
`DatabaseFailoverCompleted` are emitted transactionally elsewhere in this module (`commands.py`,
`recovery.py`, `failover.py`) because each is a real recorded outcome, not a background signal.
"""

from __future__ import annotations

import logging
import uuid

from app.core.db import SessionLocal
from app.mutation.gateway import write_outbox_event

logger = logging.getLogger("gxp_api.dr_signals")

_EVENT_TYPES = {"BackupRPOAtRisk"}


async def emit_dr_signal(event_type: str, payload: dict) -> None:
    if event_type not in _EVENT_TYPES:
        raise ValueError(f"unknown disaster_recovery signal {event_type!r}")
    try:
        async with SessionLocal() as session:
            async with session.begin():
                await write_outbox_event(
                    session, event_type=event_type, aggregate_type="disaster_recovery",
                    aggregate_id=uuid.uuid4(), aggregate_version=1, payload=payload,
                    correlation_id=uuid.uuid4(),
                )
    except Exception:  # noqa: BLE001 - a monitoring signal must never break the read it observed
        logger.exception("failed to emit disaster_recovery signal event_type=%s", event_type)
