import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.equipment.cleaning_commands import (
    CompleteCleaningCommand,
    CompleteLineClearanceCommand,
    CreateCleaningExecutionCommand,
    CreateLineClearanceCommand,
    RecordCleaningStepCommand,
    VerifyCleaningCommand,
    cleaning_record_hash,
    complete_cleaning,
    complete_line_clearance,
    create_cleaning_execution,
    create_line_clearance,
    get_equipment_cleaning_status,
    line_clearance_record_hash,
    record_cleaning_step,
    verify_cleaning,
)
from app.modules.equipment.cleaning_models import CleaningExecution, LineClearance
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/cleaning/v1", tags=["cleaning"])
line_clearance_router = APIRouter(prefix="/line-clearance/v1", tags=["cleaning"])


def _execution_dict(execution: CleaningExecution) -> dict:
    return {
        "id": str(execution.id),
        "site_id": str(execution.site_id),
        "equipment_id": str(execution.equipment_id) if execution.equipment_id else None,
        "area_id": str(execution.area_id) if execution.area_id else None,
        "procedure_version_id": str(execution.procedure_version_id),
        "state": execution.state,
        "dirty_since": execution.dirty_since.isoformat(),
        "clean_until": execution.clean_until.isoformat() if execution.clean_until else None,
        "verification_result": execution.verification_result,
        "dirty_hold_exceeded": execution.dirty_hold_exceeded,
        "requires_deviation": execution.requires_deviation,
        "swab_sample_id": str(execution.swab_sample_id) if execution.swab_sample_id else None,
        "protection_state": execution.protection_state,
        "sterilization_cycle_id": str(execution.sterilization_cycle_id) if execution.sterilization_cycle_id else None,
        "version": execution.version,
    }


@router.post("/executions", response_model=MutationReceipt)
async def post_create_execution(
    cmd: CreateCleaningExecutionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="cleaning_execution.create", site_id=cmd.site_id)
        return await create_cleaning_execution(session, cmd, actor.user_id)


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    execution = await session.get(CleaningExecution, execution_id)
    if execution is None:
        raise NotFoundError("Cleaning execution not found")
    return _execution_dict(execution)


@router.post("/executions/{execution_id}/steps", response_model=MutationReceipt)
async def post_record_step(
    execution_id: uuid.UUID,
    cmd: RecordCleaningStepCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.execution_id != execution_id:
        raise ValidationFailedError("execution_id in path and body must match")
    async with session.begin():
        execution = await session.get(CleaningExecution, execution_id)
        if execution is None:
            raise NotFoundError("Cleaning execution not found")
        await evaluate_policy(session, actor.user_id, action="cleaning_execution.create", site_id=execution.site_id)
        return await record_cleaning_step(session, cmd, actor.user_id)


class CleaningSignatureChallengeRequest(BaseModel):
    action: str  # "complete" | "verify"


_CLEANING_CHALLENGE_MEANINGS = {"complete": "Performed", "verify": "Verified"}


@router.post("/executions/{execution_id}/signature-challenges")
async def post_cleaning_signature_challenge(
    execution_id: uuid.UUID,
    body: CleaningSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        execution = await session.get(CleaningExecution, execution_id)
        if execution is None:
            raise NotFoundError("Cleaning execution not found")
        meaning = _CLEANING_CHALLENGE_MEANINGS.get(body.action)
        if meaning is None:
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="cleaning_execution", record_id=execution.id,
            record_version=execution.version, record_hash=cleaning_record_hash(execution), meaning=meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/executions/{execution_id}/complete", response_model=MutationReceipt)
async def post_complete_cleaning(
    execution_id: uuid.UUID,
    cmd: CompleteCleaningCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.execution_id != execution_id:
        raise ValidationFailedError("execution_id in path and body must match")
    async with session.begin():
        execution = await session.get(CleaningExecution, execution_id)
        if execution is None:
            raise NotFoundError("Cleaning execution not found")
        await evaluate_policy(session, actor.user_id, action="cleaning_execution.complete", site_id=execution.site_id)
        return await complete_cleaning(session, cmd, actor.user_id)


@router.post("/executions/{execution_id}/verify", response_model=MutationReceipt)
async def post_verify_cleaning(
    execution_id: uuid.UUID,
    cmd: VerifyCleaningCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.execution_id != execution_id:
        raise ValidationFailedError("execution_id in path and body must match")
    async with session.begin():
        execution = await session.get(CleaningExecution, execution_id)
        if execution is None:
            raise NotFoundError("Cleaning execution not found")
        await evaluate_policy(session, actor.user_id, action="cleaning_execution.verify", site_id=execution.site_id)
        return await verify_cleaning(session, cmd, actor.user_id)


@router.get("/equipment/{equipment_id}/status")
async def get_status(equipment_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        return await get_equipment_cleaning_status(session, equipment_id)


def _clearance_dict(clearance: LineClearance) -> dict:
    return {
        "id": str(clearance.id),
        "site_id": str(clearance.site_id),
        "area_id": str(clearance.area_id) if clearance.area_id else None,
        "previous_batch_id": str(clearance.previous_batch_id) if clearance.previous_batch_id else None,
        "next_batch_id": str(clearance.next_batch_id) if clearance.next_batch_id else None,
        "items": clearance.items,
        "state": clearance.state,
        "expiry_at": clearance.expiry_at.isoformat() if clearance.expiry_at else None,
        "version": clearance.version,
    }


@line_clearance_router.post("", response_model=MutationReceipt)
async def post_create_line_clearance(
    cmd: CreateLineClearanceCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="line_clearance.create", site_id=cmd.site_id)
        return await create_line_clearance(session, cmd, actor.user_id)


@line_clearance_router.get("/{clearance_id}")
async def get_line_clearance(clearance_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    clearance = await session.get(LineClearance, clearance_id)
    if clearance is None:
        raise NotFoundError("Line clearance not found")
    return _clearance_dict(clearance)


class LineClearanceSignatureChallengeRequest(BaseModel):
    action: str = "complete"


@line_clearance_router.post("/{clearance_id}/signature-challenges")
async def post_line_clearance_signature_challenge(
    clearance_id: uuid.UUID,
    body: LineClearanceSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        clearance = await session.get(LineClearance, clearance_id)
        if clearance is None:
            raise NotFoundError("Line clearance not found")
        if body.action != "complete":
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="line_clearance", record_id=clearance.id,
            record_version=clearance.version, record_hash=line_clearance_record_hash(clearance), meaning="Performed",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@line_clearance_router.post("/{clearance_id}/complete", response_model=MutationReceipt)
async def post_complete_line_clearance(
    clearance_id: uuid.UUID,
    cmd: CompleteLineClearanceCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.clearance_id != clearance_id:
        raise ValidationFailedError("clearance_id in path and body must match")
    async with session.begin():
        clearance = await session.get(LineClearance, clearance_id)
        if clearance is None:
            raise NotFoundError("Line clearance not found")
        await evaluate_policy(session, actor.user_id, action="line_clearance.complete", site_id=clearance.site_id)
        return await complete_line_clearance(session, cmd, actor.user_id)
