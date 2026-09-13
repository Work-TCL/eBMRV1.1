"""Document 74 (SPEC-DATA-006), WP-11 (ADR-0011, SG-183) Stage 2: the first real Temporal
workflow+activity+worker this codebase runs -- `StepStuckDetectionWorkflow` (BAT-FR-018/021's "stuck
step" half only, see workflows.py's own docstring for the deliberately narrow scope).

Every test here runs a real local Temporal server (`infra/README.md`, PM2 process
`ebmr-new-temporal`, `127.0.0.1:7233`) and a real `temporalio.worker.Worker` -- not a mock. If no
server is reachable, every test in this module is skipped rather than silently passing against nothing
(TEST-FR-036: no mock-only critical proof).
"""

import uuid

import pytest
from sqlalchemy import func, select
from temporalio.worker import Worker

from app.core.config import settings
from app.modules.batch_execution.models import BatchStep
from app.modules.mutation.models import OutboxEvent
from app.modules.workflowops import client as workflowops_client
from app.modules.workflowops import commands
from app.modules.workflowops.activities import check_step_still_in_progress, emit_stuck_signal
from app.modules.workflowops.identity import derive_workflow_id
from app.modules.workflowops.workflows import StepStuckDetectionWorkflow
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login
from tests.test_batch_execution import _create_body, _issue_start_and_get_ready_step, _released_pair, _sign_step


async def _temporal_reachable() -> bool:
    try:
        await workflowops_client.connect()
        return workflowops_client.is_connected()
    except Exception:  # noqa: BLE001 - genuinely "not reachable", not a test failure
        return False


@pytest.fixture(scope="module", autouse=True)
async def _temporal_connection():
    """Module-scoped: connect once for the whole file (same lesson as WP-11 Stage 1's NATS tests --
    one bounded connect-timeout cycle, not one per test, if no server is reachable)."""
    if not await _temporal_reachable():
        pytest.skip(f"No live Temporal server reachable at {settings.temporal_target} -- skipping, not faking")
    yield
    await workflowops_client.close()


@pytest.fixture
async def _worker():
    """A real worker polling the real task queue for the duration of one test."""
    worker = Worker(
        workflowops_client.get_client(), task_queue=workflowops_client.TASK_QUEUE,
        workflows=[StepStuckDetectionWorkflow], activities=[check_step_still_in_progress, emit_stuck_signal],
    )
    async with worker:
        yield worker


async def _in_progress_step(client, seeded, db, tag):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, tag)
    resp = await client.post(
        "/batches/v1", json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, f"BAT-WF-{tag}"),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["aggregate_id"]
    step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step["step_id"], "expected_version": step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return admin_token, batch_id, step["step_id"]


async def test_stuck_step_emits_signal_when_still_in_progress_after_threshold(client, seeded, db, _worker):
    _admin_token, batch_id, step_id = await _in_progress_step(client, seeded, db, "wf1")

    workflow_id = await commands.start_step_stuck_detection(
        batch_id=uuid.UUID(batch_id), step_id=uuid.UUID(step_id), threshold_seconds=1,
    )
    assert workflow_id == derive_workflow_id(workflow_type="step_stuck_detection", business_id=step_id)

    handle = workflowops_client.get_client().get_workflow_handle_for(StepStuckDetectionWorkflow.run, workflow_id)
    result = await handle.result()
    assert result.still_in_progress is True
    assert result.state == "in_progress"

    async with db.begin():
        signal_event = (
            await db.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_type == "WorkflowStuckDetected",
                    OutboxEvent.payload["step_id"].astext == step_id,
                )
            )
        ).scalar_one()
        assert signal_event.payload["batch_id"] == batch_id
        assert signal_event.payload["threshold_seconds"] == 1
        started_event = (
            await db.execute(
                select(func.count()).select_from(OutboxEvent).where(
                    OutboxEvent.event_type == "WorkflowStarted",
                    OutboxEvent.payload["step_id"].astext == step_id,
                )
            )
        )
        assert started_event.scalar_one() == 1


async def test_step_completed_before_threshold_never_emits_stuck_signal(client, seeded, db, _worker):
    admin_token, batch_id, step_id = await _in_progress_step(client, seeded, db, "wf2")

    workflow_id = await commands.start_step_stuck_detection(
        batch_id=uuid.UUID(batch_id), step_id=uuid.UUID(step_id), threshold_seconds=3,
    )

    # Complete the step (a real signed completion, Document 106 row 21) before the workflow's
    # 3-second timer fires.
    async with db.begin():
        step = await db.get(BatchStep, uuid.UUID(step_id))
        expected_version = step.version
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

    handle = workflowops_client.get_client().get_workflow_handle_for(StepStuckDetectionWorkflow.run, workflow_id)
    result = await handle.result()
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


async def test_starting_twice_for_the_same_step_is_idempotent(client, seeded, db, _worker):
    _admin_token, batch_id, step_id = await _in_progress_step(client, seeded, db, "wf3")

    first_id = await commands.start_step_stuck_detection(
        batch_id=uuid.UUID(batch_id), step_id=uuid.UUID(step_id), threshold_seconds=30,
    )
    second_id = await commands.start_step_stuck_detection(
        batch_id=uuid.UUID(batch_id), step_id=uuid.UUID(step_id), threshold_seconds=30,
    )
    assert first_id == second_id

    async with db.begin():
        n = await db.scalar(
            select(func.count()).select_from(OutboxEvent).where(
                OutboxEvent.event_type == "WorkflowStarted",
                OutboxEvent.payload["step_id"].astext == step_id,
            )
        )
        # only the first start() actually launched a workflow -- the second was recognized as already
        # running and did not re-emit WorkflowStarted (TMP-FR-002)
        assert n == 1

    await workflowops_client.get_client().get_workflow_handle(first_id).terminate(reason="test cleanup")


async def test_rest_endpoints_start_and_query_status(client, seeded, db, _worker):
    admin_token, batch_id, step_id = await _in_progress_step(client, seeded, db, "wf4")

    resp = await client.post(
        "/workflowops/v1/step-stuck-detection",
        json={"batch_id": batch_id, "step_id": step_id, "threshold_seconds": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    workflow_id = resp.json()["workflow_id"]

    await workflowops_client.get_client().get_workflow_handle_for(StepStuckDetectionWorkflow.run, workflow_id).result()

    status_resp = await client.get(f"/workflowops/v1/step-stuck-detection/{step_id}", headers=auth_headers(admin_token))
    assert status_resp.status_code == 200, status_resp.text
    body = status_resp.json()
    assert body["status"] == "COMPLETED"
    assert body["result"]["still_in_progress"] is True


async def test_start_unknown_step_fails_closed_not_found(client, seeded, db):
    admin_token, _product_version_id, _recipe_version_id = await _released_pair(db, client, seeded, "wf5")
    resp = await client.post(
        "/workflowops/v1/step-stuck-detection",
        json={"batch_id": str(uuid.uuid4()), "step_id": str(uuid.uuid4()), "threshold_seconds": 60},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404, resp.text


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post(
        "/workflowops/v1/step-stuck-detection",
        json={"batch_id": str(uuid.uuid4()), "step_id": str(uuid.uuid4())},
        headers={},
    )
    assert resp.status_code == 401
