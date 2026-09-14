"""Document 74 (SPEC-DATA-006), WP-11 Stage 5 (ADR-0011, SG-183 / SG-048): BAT-FR-029 restart/recovery --
"Worker/application restart resumes from authoritative batch/Temporal state without duplicate regulated
actions."

Scope, deliberately narrow, same discipline as every prior WP-11 stage: proves restart/recovery for the
one real workflow this codebase runs (`StepStuckDetectionWorkflow`, built Stage 2) -- not a general-purpose
restart framework, and not the other 19 still-open SG-048 items (each entangled with a different unbuilt
module, per SG-048's own text).

Every test here runs against the real local Temporal server (`infra/README.md`, PM2 `ebmr-new-temporal`)
and real `temporalio.worker.Worker` instances -- not a mock. "App/worker restart" is simulated the way it
actually happens in this deployment: the embedded worker (`workflowops/worker.py::run_worker`, started
from `app/main.py`'s lifespan) stops polling when the process goes down, while the workflow's own state
stays durably on the Temporal server (a separate, independently-running process) the whole time -- a new
`Worker` instance binding to the same task queue is exactly what a restarted app process does. No fault
is ever injected into Temporal's own server; that is infrastructure availability, a different concern from
BAT-FR-029's "worker/application restart."
"""

import asyncio
import uuid

import pytest
from sqlalchemy import func, select
from temporalio.worker import Worker

from app.core.config import settings
from app.modules.mutation.models import OutboxEvent
from app.modules.workflowops import client as workflowops_client
from app.modules.workflowops import commands
from app.modules.workflowops.activities import check_step_still_in_progress, emit_stuck_signal
from app.modules.workflowops.workflows import StepStuckDetectionWorkflow
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login
from tests.test_workflowops_temporal import _in_progress_step


async def _temporal_reachable() -> bool:
    try:
        await workflowops_client.connect()
        return workflowops_client.is_connected()
    except Exception:  # noqa: BLE001 - genuinely "not reachable", not a test failure
        return False


@pytest.fixture(scope="module", autouse=True)
async def _temporal_connection():
    if not await _temporal_reachable():
        pytest.skip(f"No live Temporal server reachable at {settings.temporal_target} -- skipping, not faking")
    yield
    await workflowops_client.close()


def _new_worker() -> Worker:
    """A fresh `Worker` instance bound to the same real task queue -- what a restarted app process's own
    embedded worker looks like: no state carried over from any prior instance, everything it knows about
    this workflow comes from Temporal's own durable server-side history."""
    return Worker(
        workflowops_client.get_client(), task_queue=workflowops_client.TASK_QUEUE,
        workflows=[StepStuckDetectionWorkflow], activities=[check_step_still_in_progress, emit_stuck_signal],
    )


async def test_workflow_resumes_after_worker_restart_without_duplicate_signal(client, seeded, db):
    _admin_token, batch_id, step_id = await _in_progress_step(client, seeded, db, "wf-restart1")

    # "Worker A" -- the app process before a restart. Starts the workflow, lets it actually begin
    # executing (enter its durable sleep), then stops polling entirely -- simulating the app process
    # being killed while the workflow is asleep with zero worker connected.
    worker_a = _new_worker()
    async with worker_a:
        workflow_id = await commands.start_step_stuck_detection(
            batch_id=uuid.UUID(batch_id), step_id=uuid.UUID(step_id), threshold_seconds=3,
        )
        await asyncio.sleep(0.5)  # let the workflow task actually start (enter workflow.sleep) first

    # Confirm it is genuinely still running with no worker connected -- proves the "outage" is real, not
    # a no-op (the workflow did not somehow already complete before worker_a stopped).
    handle = workflowops_client.get_client().get_workflow_handle_for(StepStuckDetectionWorkflow.run, workflow_id)
    description = await handle.describe()
    assert description.status.name == "RUNNING"

    # "Worker B" -- the restarted app process's own new embedded worker, picking the same task queue back
    # up. Nothing here references worker_a; this is a completely independent Worker instance.
    worker_b = _new_worker()
    async with worker_b:
        result = await handle.result()

    assert result.still_in_progress is True
    assert result.state == "in_progress"

    async with db.begin():
        n = await db.scalar(
            select(func.count()).select_from(OutboxEvent).where(
                OutboxEvent.event_type == "WorkflowStuckDetected",
                OutboxEvent.payload["step_id"].astext == step_id,
            )
        )
        # Exactly one signal -- not zero (the restart didn't lose the workflow) and not duplicated (the
        # restart didn't cause it to re-execute the already-durable sleep/check from scratch).
        assert n == 1


async def test_step_completed_during_worker_outage_is_not_stale_on_resume(client, seeded, db):
    """AG-10 + BAT-FR-029 together: the resumed workflow must re-read the step's *current* authoritative
    state, not anything it might have seen or decided before the restart. Completes the step while no
    worker is connected at all -- if the resumed run used stale state, it would wrongly emit a stuck
    signal for a step that was actually completed during the outage."""
    admin_token, batch_id, step_id = await _in_progress_step(client, seeded, db, "wf-restart2")

    worker_a = _new_worker()
    async with worker_a:
        workflow_id = await commands.start_step_stuck_detection(
            batch_id=uuid.UUID(batch_id), step_id=uuid.UUID(step_id), threshold_seconds=3,
        )
        await asyncio.sleep(0.5)

    handle = workflowops_client.get_client().get_workflow_handle_for(StepStuckDetectionWorkflow.run, workflow_id)
    assert (await handle.describe()).status.name == "RUNNING"

    # The "outage": step is completed for real (signed) while zero worker is connected to this task queue.
    from app.modules.batch_execution.models import BatchStep

    async with db.begin():
        step = await db.get(BatchStep, uuid.UUID(step_id))
        expected_version = step.version
    from tests.test_batch_execution import _sign_step

    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": expected_version,
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    worker_b = _new_worker()
    async with worker_b:
        result = await handle.result()

    # Re-read live on resume -- not stale, not decided before the restart.
    assert result.still_in_progress is False
    assert result.state == "complete"

    async with db.begin():
        n = await db.scalar(
            select(func.count()).select_from(OutboxEvent).where(
                OutboxEvent.event_type == "WorkflowStuckDetected",
                OutboxEvent.payload["step_id"].astext == step_id,
            )
        )
        assert n == 0