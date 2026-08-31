"""Document 74 (SPEC-DATA-006) # 9 operational signals -- `WorkflowStarted`, `WorkflowStuckDetected`,
`TemporalWorkerVersionChanged`, `WorkflowCompensationExecuted`, `TemporalNamespaceUnavailable`. No live
Temporal cluster in this deployment (no `temporalio` dependency) -- these are the emitters a future
Temporal worker/supervisor calls; same self-committing best-effort pattern as every other module's
signals.py, aggregate_type `workflow_orchestration`, never inside the domain transaction they describe
(TMP-FR-006: Temporal history/search attributes are not the regulated record; MUT-FR-031-style
separation from the GxP audit ledger).
"""

from __future__ import annotations

import logging
import uuid

from app.core.db import SessionLocal
from app.mutation.gateway import write_outbox_event

logger = logging.getLogger("gxp_api.workflowops_signals")

_EVENT_TYPES = {
    "WorkflowStarted", "WorkflowStuckDetected", "TemporalWorkerVersionChanged",
    "WorkflowCompensationExecuted", "TemporalNamespaceUnavailable",
}


async def emit_workflow_signal(event_type: str, payload: dict) -> None:
    if event_type not in _EVENT_TYPES:
        raise ValueError(f"unknown workflowops signal {event_type!r}")
    try:
        async with SessionLocal() as session:
            async with session.begin():
                await write_outbox_event(
                    session, event_type=event_type, aggregate_type="workflow_orchestration",
                    aggregate_id=uuid.uuid4(), aggregate_version=1, payload=payload,
                    correlation_id=uuid.uuid4(),
                )
    except Exception:  # noqa: BLE001 - a signal must never break the orchestration state it observed
        logger.exception("failed to emit workflowops signal event_type=%s", event_type)
