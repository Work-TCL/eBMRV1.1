import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qms.change_commands import (
    AddChangeTaskCommand,
    ApproveChangeCommand,
    AssessImpactCommand,
    CloseChangeCommand,
    CreateChangeCommand,
    ImplementChangeCommand,
    MakeEffectiveCommand,
    VerifyChangeCommand,
    add_change_task,
    approve_change,
    assess_impact,
    close_change,
    create_change,
    implement_change,
    make_effective_change,
    verify_change,
)
from app.modules.qms.change_models import ChangeAffectedObject, ChangeControl, ChangeTask
from app.modules.qms.read_support import filtered, iso, sid
from app.modules.qms.signature_support import SignatureChallengeRequest, create_qms_signature_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

change_router = APIRouter(prefix="/qms/v1/changes", tags=["qms-change-control"])

CHANGE_SIGNATURE_ACTIONS = ("approve", "verify", "close")


@change_router.post("", response_model=MutationReceipt)
async def post_create_change(
    cmd: CreateChangeCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="change.create", site_id=cmd.site_id)
        return await create_change(session, cmd, actor.user_id)


@change_router.post("/{change_id}/impact", response_model=MutationReceipt)
async def post_assess_impact(
    change_id: uuid.UUID, cmd: AssessImpactCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.change_id != change_id:
        raise ValidationFailedError("change_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="change.impact", site_id=None)
        return await assess_impact(session, cmd, actor.user_id)


@change_router.post("/{change_id}/approve", response_model=MutationReceipt)
async def post_approve_change(
    change_id: uuid.UUID, cmd: ApproveChangeCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.change_id != change_id:
        raise ValidationFailedError("change_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="change.approve", site_id=None)
        return await approve_change(session, cmd, actor.user_id)


@change_router.post("/{change_id}/tasks", response_model=MutationReceipt)
async def post_add_task(
    change_id: uuid.UUID, cmd: AddChangeTaskCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.change_id != change_id:
        raise ValidationFailedError("change_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="change.task.add", site_id=None)
        return await add_change_task(session, cmd, actor.user_id)


@change_router.post("/{change_id}/implement", response_model=MutationReceipt)
async def post_implement_change(
    change_id: uuid.UUID, cmd: ImplementChangeCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.change_id != change_id:
        raise ValidationFailedError("change_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="change.implement", site_id=None)
        return await implement_change(session, cmd, actor.user_id)


@change_router.post("/{change_id}/verify", response_model=MutationReceipt)
async def post_verify_change(
    change_id: uuid.UUID, cmd: VerifyChangeCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.change_id != change_id:
        raise ValidationFailedError("change_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="change.verify", site_id=None)
        return await verify_change(session, cmd, actor.user_id)


@change_router.post("/{change_id}/make-effective", response_model=MutationReceipt)
async def post_make_effective(
    change_id: uuid.UUID, cmd: MakeEffectiveCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.change_id != change_id:
        raise ValidationFailedError("change_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="change.make_effective", site_id=None)
        return await make_effective_change(session, cmd, actor.user_id)


@change_router.post("/{change_id}/signature-challenges")
async def post_signature_challenge(
    change_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        change = await session.get(ChangeControl, change_id)
        if change is None:
            raise NotFoundError("Change control not found")
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="change_control", record=change,
            action=body.action, allowed_actions=CHANGE_SIGNATURE_ACTIONS,
        )


@change_router.post("/{change_id}/close", response_model=MutationReceipt)
async def post_close_change(
    change_id: uuid.UUID, cmd: CloseChangeCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.change_id != change_id:
        raise ValidationFailedError("change_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="change.close", site_id=None)
        return await close_change(session, cmd, actor.user_id)


# --- Read side ---------------------------------------------------------------------------------

CHANGE_SORTABLE = {
    "change_number": ChangeControl.change_number,
    "classification": ChangeControl.classification,
    "state": ChangeControl.state,
    "created_at": ChangeControl.created_at,
}


def _change_dict(record: ChangeControl) -> dict:
    return {
        "id": str(record.id),
        "site_id": str(record.site_id),
        "quality_event_id": str(record.quality_event_id),
        "change_number": record.change_number,
        "change_type": record.change_type,
        "classification": record.classification,
        "reason": record.reason,
        "state": record.state,
        "owner_subject_id": str(record.owner_subject_id),
        "emergency": record.emergency,
        "retrospective_review_completed": record.retrospective_review_completed,
        "effective_at": iso(record.effective_at),
        "version": record.version,
        "created_at": iso(record.created_at),
        "closed_at": iso(record.closed_at),
    }


@change_router.get("")
async def list_changes(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    state: str | None = None,
) -> dict:
    await evaluate_policy(session, actor.user_id, action="change.view", site_id=site_id)
    stmt = filtered(
        ChangeControl, params, search_column=ChangeControl.change_number, site_id=site_id, state=state
    )
    rows, envelope = await paginate(
        session, stmt, params, sortable=CHANGE_SORTABLE, default_sort=ChangeControl.created_at
    )
    return {**envelope, "items": [_change_dict(r) for (r,) in rows]}


@change_router.get("/{change_id}")
async def get_change(
    change_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    record = await session.get(ChangeControl, change_id)
    if record is None:
        raise NotFoundError("Change control not found")
    await evaluate_policy(session, actor.user_id, action="change.view", site_id=record.site_id)
    objects = (
        await session.execute(select(ChangeAffectedObject).where(ChangeAffectedObject.change_id == change_id))
    ).scalars().all()
    tasks = (
        await session.execute(select(ChangeTask).where(ChangeTask.change_id == change_id))
    ).scalars().all()
    return {
        **_change_dict(record),
        "current_state": record.current_state,
        "proposed_state": record.proposed_state,
        "risk_ref": sid(record.risk_ref),
        "regulatory_impact": record.regulatory_impact,
        "validation_impact": record.validation_impact,
        "training_impact": record.training_impact,
        "impact_assessment": record.impact_assessment,
        "emergency_reason": record.emergency_reason,
        "retrospective_review": record.retrospective_review,
        "cancel_reason": record.cancel_reason,
        "closure_history": record.closure_history,
        "affected_objects": [
            {
                "id": str(o.id),
                "object_type": o.object_type,
                "object_id": str(o.object_id),
                "object_version": o.object_version,
                "impact_category": o.impact_category,
                "action_required": o.action_required,
                "created_by": sid(o.created_by),
                "created_at": iso(o.created_at),
            }
            for o in objects
        ],
        "tasks": [
            {
                "id": str(t.id),
                "description": t.description,
                "owner_subject_id": str(t.owner_subject_id),
                "due_date": iso(t.due_date),
                "dependency_links": t.dependency_links,
                "evidence": t.evidence,
                "status": t.status,
                "version": t.version,
                "completed_at": iso(t.completed_at),
            }
            for t in tasks
        ],
    }
