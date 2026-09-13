"""Document 74 (SPEC-DATA-006) real Temporal Activities -- ADR-0011 (SG-183) Stage 2.

An Activity is the only place Temporal workflow code may perform I/O (AG-10: workflow code itself must
be deterministic and never touch the database or the outbox directly). Both activities here re-read
authoritative state from `batch_execution`'s own query interface rather than caching or guessing it
(AG-10's "authoritative state re-read from the owning service"), and neither writes GxP regulated state
-- `check_step_still_in_progress` is read-only, `emit_stuck_signal` writes only the non-regulated
`workflow_orchestration` signal stream `workflowops/signals.py` already owns (Document 74 # 9, "Temporal
history/search attributes are not the regulated record").
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.core.db import SessionLocal
from app.modules.batch_execution import service as batch_execution_service
from app.modules.workflowops.retry_policy import classify_retry
from app.modules.workflowops.signals import emit_workflow_signal
from app.mutation.errors import GxPError


@dataclass(frozen=True)
class StepCheckInput:
    batch_id: str
    step_id: str


@dataclass(frozen=True)
class StepCheckResult:
    state: str
    still_in_progress: bool


@activity.defn
async def check_step_still_in_progress(inp: StepCheckInput) -> StepCheckResult:
    """TMP-FR-011: wraps the real `GxPError` taxonomy through `classify_retry()` so a settled business
    outcome (e.g. the step or batch no longer exists) fails the Activity permanently instead of retrying
    forever, while a transient dependency failure (e.g. the authoritative DB is briefly unreachable)
    lets Temporal's own retry policy run again."""
    try:
        async with SessionLocal() as session:
            step = await batch_execution_service.get_step(session, uuid.UUID(inp.batch_id), uuid.UUID(inp.step_id))
            return StepCheckResult(state=step.state, still_in_progress=step.state == "in_progress")
    except GxPError as exc:
        decision = classify_retry(exc)
        if decision.retryable:
            raise
        raise ApplicationError(
            f"{exc.code}: {exc}", type=exc.code, non_retryable=True,
        ) from exc


@dataclass(frozen=True)
class StuckSignalInput:
    batch_id: str
    step_id: str
    threshold_seconds: int


@activity.defn
async def emit_stuck_signal(inp: StuckSignalInput) -> None:
    """Document 74 # 9 `WorkflowStuckDetected` -- an operational signal, not a GxP audit event (this
    never touches `ebmr.gxp_batch_step`, only the `workflow_orchestration` outbox stream
    `workflowops/signals.py` already declares)."""
    await emit_workflow_signal(
        "WorkflowStuckDetected",
        {
            "batch_id": inp.batch_id, "step_id": inp.step_id,
            "threshold_seconds": inp.threshold_seconds,
            "reason": f"step still in_progress after {inp.threshold_seconds}s",
        },
    )
