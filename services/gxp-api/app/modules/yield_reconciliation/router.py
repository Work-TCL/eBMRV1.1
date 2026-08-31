import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import create_challenge
from app.modules.yield_reconciliation import commands as yr_commands
from app.modules.yield_reconciliation.models import ManufacturingCalculation, ReconciliationRecord
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(tags=["yield-reconciliation"])


@router.post("/manufacturing-calculations/v1/yield/evaluate", response_model=MutationReceipt)
async def post_evaluate_yield(
    cmd: yr_commands.EvaluateYieldCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="yield_calculation.evaluate", site_id=None)
        return await yr_commands.evaluate_yield(session, cmd, actor.user_id)


@router.post("/manufacturing-calculations/v1/potency/evaluate", response_model=MutationReceipt)
async def post_evaluate_potency(
    cmd: yr_commands.EvaluatePotencyCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="yield_calculation.evaluate", site_id=None)
        return await yr_commands.evaluate_potency(session, cmd, actor.user_id)


@router.post("/reconciliation/v1/material/evaluate", response_model=MutationReceipt)
async def post_evaluate_material(
    cmd: yr_commands.EvaluateReconciliationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="reconciliation.evaluate", site_id=None)
        return await yr_commands.evaluate_material_reconciliation(session, cmd, actor.user_id)


@router.post("/reconciliation/v1/packaging/evaluate", response_model=MutationReceipt)
async def post_evaluate_packaging(
    cmd: yr_commands.EvaluateReconciliationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="reconciliation.evaluate", site_id=None)
        return await yr_commands.evaluate_packaging_reconciliation(session, cmd, actor.user_id)


@router.post("/reconciliation/v1/labels/evaluate", response_model=MutationReceipt)
async def post_evaluate_labels(
    cmd: yr_commands.EvaluateLabelReconciliationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="reconciliation.evaluate", site_id=None)
        return await yr_commands.evaluate_label_reconciliation(session, cmd, actor.user_id)


@router.post("/reconciliation/v1/components/evaluate", response_model=MutationReceipt)
async def post_evaluate_components(
    cmd: yr_commands.EvaluateComponentReconciliationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="reconciliation.evaluate", site_id=None)
        return await yr_commands.evaluate_component_reconciliation(session, cmd, actor.user_id)


class VerifySignatureChallengeRequest(BaseModel):
    record_kind: str  # "CALCULATION" | "RECONCILIATION"


@router.post("/reconciliation/v1/{record_id}/signature-challenges")
async def post_verify_signature_challenge(
    record_id: uuid.UUID, body: VerifySignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        if body.record_kind == "CALCULATION":
            record = await session.get(ManufacturingCalculation, record_id)
            record_hash = yr_commands.calculation_record_hash(record) if record else None
            record_type = "manufacturing_calculation"
        elif body.record_kind == "RECONCILIATION":
            record = await session.get(ReconciliationRecord, record_id)
            record_hash = yr_commands.reconciliation_record_hash(record) if record else None
            record_type = "reconciliation_record"
        else:
            raise ValidationFailedError("record_kind must be CALCULATION or RECONCILIATION")
        if record is None:
            raise NotFoundError("Record not found")
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type=record_type, record_id=record.id,
            record_version=record.version, record_hash=record_hash, meaning="Verified",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/reconciliation/v1/{record_id}/verify", response_model=MutationReceipt)
async def post_verify_record(
    record_id: uuid.UUID, cmd: yr_commands.VerifyRecordCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.record_id != record_id:
        raise ValidationFailedError("record_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="reconciliation.verify", site_id=None)
        return await yr_commands.verify_record(session, cmd, actor.user_id)


@router.get("/reconciliation/v1/batches/{batch_id}/summary")
async def get_batch_summary(batch_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        return await yr_commands.get_batch_summary(session, batch_id)
