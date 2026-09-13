"""Document 74 (SPEC-DATA-006) REST surface, prefix `/workflowops/v1`. ADR-0011 (SG-183) Stage 2.

Both operations are RBAC-gated but unsigned -- starting/reading an orchestration's own status is not
itself a regulated GxP decision (AG-10); no Document 106 row exists for either action, matching every
other unsigned-by-design action elsewhere in this codebase (e.g. WP-07's secret.rotate).
"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.batch_execution import service as batch_execution_service
from app.modules.policy.service import evaluate_policy
from app.modules.workflowops import commands

router = APIRouter(prefix="/workflowops/v1", tags=["workflowops"])


class StartStepStuckDetectionRequest(BaseModel):
    model_config = {"extra": "forbid"}
    batch_id: uuid.UUID
    step_id: uuid.UUID
    threshold_seconds: int = commands.DEFAULT_STUCK_THRESHOLD_SECONDS


@router.post("/step-stuck-detection")
async def post_start_step_stuck_detection(
    body: StartStepStuckDetectionRequest,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="step_stuck_detection.start", site_id=None)
        # Confirms the step is real and belongs to the named batch before starting an orchestration for
        # it -- fails closed (NOT_FOUND) rather than launching a workflow for a nonexistent step.
        await batch_execution_service.get_step(session, body.batch_id, body.step_id)
    workflow_id = await commands.start_step_stuck_detection(
        batch_id=body.batch_id, step_id=body.step_id, threshold_seconds=body.threshold_seconds,
    )
    return {"workflow_id": workflow_id}


@router.get("/step-stuck-detection/{step_id}")
async def get_step_stuck_detection_status(
    step_id: uuid.UUID,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="step_stuck_detection.view", site_id=None)
    return await commands.get_step_stuck_detection_status(step_id=step_id)
