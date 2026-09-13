"""Document 74 (SPEC-DATA-006) -- ADR-0011 (SG-183) Stage 2. Starts/queries the one real workflow this
codebase runs on Temporal.

Not a Mutation Gateway command in the full Document 03 sense: starting a workflow is not itself a
regulated GxP state change (AG-10, "Temporal orchestrates workflows but is never regulatory truth") --
no domain row is created, no GxP audit event is warranted. It still gets the operational-signal
treatment Document 74 # 9 declares (`WorkflowStarted`), and TMP-FR-002's own idempotency: starting twice
for the same step reuses the same running workflow rather than erroring or double-orchestrating.
"""

from __future__ import annotations

import uuid

from temporalio.exceptions import WorkflowAlreadyStartedError

from app.modules.workflowops.client import TASK_QUEUE, get_client
from app.modules.workflowops.identity import derive_workflow_id
from app.modules.workflowops.signals import emit_workflow_signal
from app.modules.workflowops.workflows import StepStuckDetectionWorkflow
from app.mutation.errors import ValidationFailedError

DEFAULT_STUCK_THRESHOLD_SECONDS = 900  # SG-163-class engineering-default floor -- see PHASE_4_WP11_STAGE2.md


async def start_step_stuck_detection(
    *, batch_id: uuid.UUID, step_id: uuid.UUID, threshold_seconds: int = DEFAULT_STUCK_THRESHOLD_SECONDS,
) -> str:
    if threshold_seconds < 1 or threshold_seconds > 86400:
        raise ValidationFailedError("threshold_seconds must be between 1 and 86400")

    workflow_id = derive_workflow_id(workflow_type="step_stuck_detection", business_id=str(step_id))
    client = get_client()
    try:
        await client.start_workflow(
            StepStuckDetectionWorkflow.run, args=[str(batch_id), str(step_id), threshold_seconds],
            id=workflow_id, task_queue=TASK_QUEUE,
        )
        started = True
    except WorkflowAlreadyStartedError:
        started = False  # already running for this step -- idempotent no-op, not an error (TMP-FR-002)

    if started:
        await emit_workflow_signal(
            "WorkflowStarted",
            {"workflow_id": workflow_id, "workflow_type": "step_stuck_detection",
             "batch_id": str(batch_id), "step_id": str(step_id), "threshold_seconds": threshold_seconds},
        )
    return workflow_id


async def get_step_stuck_detection_status(*, step_id: uuid.UUID) -> dict:
    """Read-only query -- describes the workflow's own run state (Temporal orchestration bookkeeping,
    AG-10) plus its result once it completes. Never itself a source of a regulated batch/step decision."""
    workflow_id = derive_workflow_id(workflow_type="step_stuck_detection", business_id=str(step_id))
    client = get_client()
    handle = client.get_workflow_handle_for(StepStuckDetectionWorkflow.run, workflow_id)
    description = await handle.describe()
    status = description.status.name if description.status else "UNKNOWN"
    result = None
    if status == "COMPLETED":
        outcome = await handle.result()
        result = {"state": outcome.state, "still_in_progress": outcome.still_in_progress}
    return {"workflow_id": workflow_id, "status": status, "result": result}
