import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.equipment.aseptic_commands import (
    CompleteOperationCommand,
    CreateAsepticOperationCommand,
    RecordEventCommand,
    RecordInterventionCommand,
    StartOperationCommand,
    complete_operation,
    create_operation,
    get_readiness,
    get_review_summary,
    operation_record_hash,
    record_event,
    record_intervention,
    start_operation,
)
from app.modules.equipment.aseptic_models import AsepticOperation
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/aseptic/v1", tags=["aseptic"])


def _operation_dict(operation: AsepticOperation) -> dict:
    return {
        "id": str(operation.id),
        "site_id": str(operation.site_id),
        "area_id": str(operation.area_id),
        "state": operation.state,
        "media_fill_reference": operation.media_fill_reference,
        "qc_test_order_id": str(operation.qc_test_order_id) if operation.qc_test_order_id else None,
        "qc_result_id": str(operation.qc_result_id) if operation.qc_result_id else None,
        "requires_deviation": operation.requires_deviation,
        "version": operation.version,
    }


@router.post("/operations", response_model=MutationReceipt)
async def post_create_operation(
    cmd: CreateAsepticOperationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="aseptic_operation.create", site_id=cmd.site_id)
        return await create_operation(session, cmd, actor.user_id)


@router.get("/operations/{operation_id}")
async def get_operation(operation_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    operation = await session.get(AsepticOperation, operation_id)
    if operation is None:
        raise NotFoundError("Aseptic operation not found")
    return _operation_dict(operation)


class OperationSignatureChallengeRequest(BaseModel):
    action: str  # "start" | "complete"


_OPERATION_CHALLENGE_MEANINGS = {"start": "Performed", "complete": "Performed"}


@router.post("/operations/{operation_id}/signature-challenges")
async def post_operation_signature_challenge(
    operation_id: uuid.UUID,
    body: OperationSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        operation = await session.get(AsepticOperation, operation_id)
        if operation is None:
            raise NotFoundError("Aseptic operation not found")
        meaning = _OPERATION_CHALLENGE_MEANINGS.get(body.action)
        if meaning is None:
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="aseptic_operation", record_id=operation.id,
            record_version=operation.version, record_hash=operation_record_hash(operation), meaning=meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/operations/{operation_id}/start", response_model=MutationReceipt)
async def post_start_operation(
    operation_id: uuid.UUID,
    cmd: StartOperationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.operation_id != operation_id:
        raise ValidationFailedError("operation_id in path and body must match")
    async with session.begin():
        operation = await session.get(AsepticOperation, operation_id)
        if operation is None:
            raise NotFoundError("Aseptic operation not found")
        await evaluate_policy(session, actor.user_id, action="aseptic_operation.start", site_id=operation.site_id)
        return await start_operation(session, cmd, actor.user_id)


@router.post("/operations/{operation_id}/interventions", response_model=MutationReceipt)
async def post_record_intervention(
    operation_id: uuid.UUID,
    cmd: RecordInterventionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.operation_id != operation_id:
        raise ValidationFailedError("operation_id in path and body must match")
    async with session.begin():
        operation = await session.get(AsepticOperation, operation_id)
        if operation is None:
            raise NotFoundError("Aseptic operation not found")
        await evaluate_policy(session, actor.user_id, action="aseptic_operation.intervention", site_id=operation.site_id)
        return await record_intervention(session, cmd, actor.user_id)


@router.post("/operations/{operation_id}/events", response_model=MutationReceipt)
async def post_record_event(
    operation_id: uuid.UUID,
    cmd: RecordEventCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.operation_id != operation_id:
        raise ValidationFailedError("operation_id in path and body must match")
    async with session.begin():
        operation = await session.get(AsepticOperation, operation_id)
        if operation is None:
            raise NotFoundError("Aseptic operation not found")
        await evaluate_policy(session, actor.user_id, action="aseptic_operation.event", site_id=operation.site_id)
        return await record_event(session, cmd, actor.user_id)


@router.post("/operations/{operation_id}/complete", response_model=MutationReceipt)
async def post_complete_operation(
    operation_id: uuid.UUID,
    cmd: CompleteOperationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.operation_id != operation_id:
        raise ValidationFailedError("operation_id in path and body must match")
    async with session.begin():
        operation = await session.get(AsepticOperation, operation_id)
        if operation is None:
            raise NotFoundError("Aseptic operation not found")
        await evaluate_policy(session, actor.user_id, action="aseptic_operation.complete", site_id=operation.site_id)
        return await complete_operation(session, cmd, actor.user_id)


@router.get("/operations/{operation_id}/readiness")
async def get_operation_readiness(operation_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        return await get_readiness(session, operation_id)


@router.get("/operations/{operation_id}/review-summary")
async def get_operation_review_summary(operation_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        return await get_review_summary(session, operation_id)
