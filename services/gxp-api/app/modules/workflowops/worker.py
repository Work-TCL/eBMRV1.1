"""Document 74 (SPEC-DATA-006) Temporal worker -- ADR-0011 (SG-183) Stage 2. Registers this codebase's
one real workflow + its two activities against `client.TASK_QUEUE`, and polls it for work.

Runs embedded in the same process as the API (started from `app/main.py`'s lifespan, alongside the
NATS `outbox_publisher_loop`), not as a separate deployment unit -- a legitimate, common choice for a
single-instance deployment (Document 74 does not mandate a separate worker process), and consistent
with how `outbox_publisher_loop` is already embedded rather than split out.
"""

from __future__ import annotations

import asyncio
import logging

from temporalio.worker import Worker

from app.modules.workflowops import client as workflowops_client
from app.modules.workflowops.activities import check_step_still_in_progress, emit_stuck_signal
from app.modules.workflowops.workflows import StepStuckDetectionWorkflow

logger = logging.getLogger("gxp_api.workflowops.worker")


async def run_worker(*, stop_event: asyncio.Event) -> None:
    """Runs until `stop_event` is set (app shutdown). Never raises out to the caller -- a worker that
    cannot run (e.g. Temporal unreachable) must not crash the API process; it logs and returns, same
    fail-open-for-transport posture as the NATS publisher loop (AG-10: Temporal is orchestration, not
    regulatory truth, so its unavailability cannot block the regulated API)."""
    try:
        worker = Worker(
            workflowops_client.get_client(),
            task_queue=workflowops_client.TASK_QUEUE,
            workflows=[StepStuckDetectionWorkflow],
            activities=[check_step_still_in_progress, emit_stuck_signal],
        )
    except Exception:  # noqa: BLE001 - not connected yet; nothing to run this pass
        logger.exception("could not construct Temporal worker (client not connected); worker will not run")
        return

    async with worker:
        logger.info("Temporal worker polling task_queue=%s", workflowops_client.TASK_QUEUE)
        await stop_event.wait()
    logger.info("Temporal worker stopped")
