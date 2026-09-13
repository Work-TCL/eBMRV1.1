"""Document 74 (SPEC-DATA-006) real Temporal Workflow -- ADR-0011 (SG-183) Stage 2, the first concrete
orchestration this codebase runs on Temporal.

Scope, deliberately narrow (see PHASE_4_WP11_STAGE2.md): BAT-FR-018 (timer/duration enforcement) and
BAT-FR-021 (exception generation)'s "stuck step" half only. The other 22 Document 11 requirements SG-048
lists as blocked on Temporal/other unbuilt modules (Material Service, Equipment master, Document 12/17,
...) are NOT touched here -- this proves the real workflow+activity+worker pattern end to end without
inventing behavior for dependencies that do not exist yet.

AG-10 discipline: this workflow never holds regulated truth. It sleeps (a durable timer, not a database
poll), calls one Activity to *read* the step's current authoritative state, and calls a second Activity
only to emit a non-regulated operational signal if the step is still running -- it never decides a
regulated batch/step state transition itself.
"""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.modules.workflowops.activities import (
        StepCheckInput,
        StepCheckResult,
        StuckSignalInput,
        check_step_still_in_progress,
        emit_stuck_signal,
    )

# TMP-FR-024: dependency-failure retries get backoff; a non-retryable ApplicationError (a settled
# business outcome, per classify_retry()) is never retried regardless of this policy.
_ACTIVITY_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1), backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30), maximum_attempts=5,
)


@workflow.defn
class StepStuckDetectionWorkflow:
    """TMP-FR-002 (workflow ID is `derive_workflow_id(workflow_type="step_stuck_detection", ...)`,
    the caller's job, not this class's) -- BAT-FR-018/021's "stuck step" half. Started once a step
    begins execution; sleeps for `threshold_seconds`, then checks whether the step is still
    `in_progress`. If so, emits `WorkflowStuckDetected` for a human to act on -- this workflow never
    holds, blocks, or auto-resolves the step itself."""

    @workflow.run
    async def run(self, batch_id: str, step_id: str, threshold_seconds: int) -> StepCheckResult:
        await workflow.sleep(timedelta(seconds=threshold_seconds))

        result: StepCheckResult = await workflow.execute_activity(
            check_step_still_in_progress, StepCheckInput(batch_id=batch_id, step_id=step_id),
            start_to_close_timeout=timedelta(seconds=10), retry_policy=_ACTIVITY_RETRY_POLICY,
        )

        if result.still_in_progress:
            await workflow.execute_activity(
                emit_stuck_signal,
                StuckSignalInput(batch_id=batch_id, step_id=step_id, threshold_seconds=threshold_seconds),
                start_to_close_timeout=timedelta(seconds=10), retry_policy=_ACTIVITY_RETRY_POLICY,
            )

        return result
