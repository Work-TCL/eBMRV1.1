import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.batch_execution import service as batch_execution_service
from app.modules.batch_execution.commands import (
    BatchTransitionCommand,
    CreateBatchCommand,
    IssueBatchCommand,
    StartStepCommand,
    abort_batch,
    create_batch,
    hold_batch,
    issue_batch,
    resume_batch,
    start_batch,
    start_step,
)
from app.modules.policy.service import evaluate_policy
from app.mutation.errors import ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/batches/v1", tags=["batch_execution"])


def _batch_dict(batch) -> dict:
    return {
        "batch_id": str(batch.id),
        "site_id": str(batch.site_id),
        "batch_number": batch.batch_number,
        "product_version_id": str(batch.product_version_id),
        "recipe_version_id": str(batch.recipe_version_id),
        "recipe_vault_object_id": str(batch.recipe_vault_object_id) if batch.recipe_vault_object_id else None,
        "execution_snapshot_id": str(batch.execution_snapshot_id) if batch.execution_snapshot_id else None,
        "target_qty": str(batch.target_qty),
        "target_uom": batch.target_uom,
        "state": batch.state,
        "version": batch.version,
        "production_order_ref": batch.production_order_ref,
        "issued_at": batch.issued_at.isoformat() if batch.issued_at else None,
        "started_at": batch.started_at.isoformat() if batch.started_at else None,
    }


def _step_dict(step) -> dict:
    return {
        "step_id": str(step.id),
        "batch_id": str(step.batch_id),
        "recipe_step_code": step.recipe_step_code,
        "state": step.state,
        "version": step.version,
        "assigned_subject_id": str(step.assigned_subject_id) if step.assigned_subject_id else None,
        "started_at": step.started_at.isoformat() if step.started_at else None,
    }


@router.post("", response_model=MutationReceipt)
async def post_create_batch(
    cmd: CreateBatchCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.create", site_id=cmd.site_id)
        return await create_batch(session, cmd, actor.user_id)


@router.post("/{batch_id}/issue", response_model=MutationReceipt)
async def post_issue_batch(
    batch_id: uuid.UUID,
    cmd: IssueBatchCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.issue", site_id=None)
        return await issue_batch(session, cmd, actor.user_id)


@router.post("/{batch_id}/start", response_model=MutationReceipt)
async def post_start_batch(
    batch_id: uuid.UUID,
    cmd: BatchTransitionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await start_batch(session, cmd, actor.user_id)


@router.post("/{batch_id}/hold", response_model=MutationReceipt)
async def post_hold_batch(
    batch_id: uuid.UUID,
    cmd: BatchTransitionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await hold_batch(session, cmd, actor.user_id)


@router.post("/{batch_id}/resume", response_model=MutationReceipt)
async def post_resume_batch(
    batch_id: uuid.UUID,
    cmd: BatchTransitionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await resume_batch(session, cmd, actor.user_id)


@router.post("/{batch_id}/abort", response_model=MutationReceipt)
async def post_abort_batch(
    batch_id: uuid.UUID,
    cmd: BatchTransitionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await abort_batch(session, cmd, actor.user_id)


@router.post("/{batch_id}/steps/{step_id}/start", response_model=MutationReceipt)
async def post_start_step(
    batch_id: uuid.UUID,
    step_id: uuid.UUID,
    cmd: StartStepCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id or cmd.step_id != step_id:
        raise ValidationFailedError("batch_id/step_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await start_step(session, cmd, actor.user_id)


@router.get("")
async def get_batch_list(
    site_id: uuid.UUID,
    state: str | None = None,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """BAT-FR-035 (partial production dashboard): active batches + hold state at a site. Bottlenecks,
    overdue timers and operator-assignment analytics are not built this pass -- see SG-048."""
    await evaluate_policy(session, actor.user_id, action="batch_execution.view", site_id=None)
    batches = await batch_execution_service.list_batches(session, site_id, state)
    return {
        "batches": [_batch_dict(b) for b in batches],
        "on_hold_count": sum(1 for b in batches if b.state == "on_hold"),
    }


@router.get("/{batch_id}")
async def get_batch_detail(
    batch_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="batch_execution.view", site_id=None)
    batch = await batch_execution_service.get_batch(session, batch_id)
    return _batch_dict(batch)


@router.get("/{batch_id}/execution-view")
async def get_execution_view(
    batch_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="batch_execution.view", site_id=None)
    view = await batch_execution_service.get_execution_view(session, batch_id)
    return {
        "batch": _batch_dict(view["batch"]),
        "steps": [_step_dict(s) for s in view["steps"]],
        "blockers": view["blockers"],
    }
