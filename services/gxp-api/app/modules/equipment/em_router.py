import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.equipment.em_commands import (
    CollectEmTaskCommand,
    CreateEmProgramCommand,
    CreateEmTaskCommand,
    RecordEmResultCommand,
    RecordExcursionImpactCommand,
    ReviewEmResultCommand,
    collect_em_task,
    create_em_program,
    create_em_task,
    em_sample_record_hash,
    get_area_readiness,
    get_trends,
    record_em_result,
    record_excursion_impact,
    review_em_result,
)
from app.modules.equipment.em_models import EmExcursion, EmSampleOrReading
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/em/v1", tags=["environmental-monitoring"])


def _sample_dict(sample: EmSampleOrReading) -> dict:
    return {
        "id": str(sample.id),
        "site_id": str(sample.site_id),
        "program_version_id": str(sample.program_version_id),
        "location_id": str(sample.location_id),
        "monitoring_type": sample.monitoring_type,
        "batch_id": str(sample.batch_id) if sample.batch_id else None,
        "aseptic_operation_id": str(sample.aseptic_operation_id) if sample.aseptic_operation_id else None,
        "instrument_or_media_ref": sample.instrument_or_media_ref,
        "scheduled_at": sample.scheduled_at.isoformat() if sample.scheduled_at else None,
        "sampled_at": sample.sampled_at.isoformat() if sample.sampled_at else None,
        "operator_user_id": str(sample.operator_user_id) if sample.operator_user_id else None,
        "reviewer_user_id": str(sample.reviewer_user_id) if sample.reviewer_user_id else None,
        "state": sample.state,
        "result": sample.result,
        "alert_action_status": sample.alert_action_status,
        "media_reagent_ref": sample.media_reagent_ref,
        "incubation_conditions": sample.incubation_conditions,
        "requires_deviation": sample.requires_deviation,
        "deviation_reference_id": str(sample.deviation_reference_id) if sample.deviation_reference_id else None,
        "version": sample.version,
        "created_at": sample.created_at.isoformat() if sample.created_at else None,
    }


@router.post("/programs", response_model=MutationReceipt)
async def post_create_program(
    cmd: CreateEmProgramCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="em_program.create", site_id=cmd.site_id)
        return await create_em_program(session, cmd, actor.user_id)


@router.post("/tasks", response_model=MutationReceipt)
async def post_create_task(
    cmd: CreateEmTaskCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="em_sample.create", site_id=cmd.site_id)
        return await create_em_task(session, cmd, actor.user_id)


@router.get("/tasks/{sample_id}")
async def get_task(sample_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    sample = await session.get(EmSampleOrReading, sample_id)
    if sample is None:
        raise NotFoundError("EM sample/reading not found")
    return _sample_dict(sample)


@router.post("/tasks/{sample_id}/collect", response_model=MutationReceipt)
async def post_collect_task(
    sample_id: uuid.UUID,
    cmd: CollectEmTaskCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.sample_id != sample_id:
        raise ValidationFailedError("sample_id in path and body must match")
    async with session.begin():
        sample = await session.get(EmSampleOrReading, sample_id)
        if sample is None:
            raise NotFoundError("EM sample/reading not found")
        await evaluate_policy(session, actor.user_id, action="em_sample.create", site_id=sample.site_id)
        return await collect_em_task(session, cmd, actor.user_id)


class EmSignatureChallengeRequest(BaseModel):
    action: str  # "record_result" | "review"


_EM_CHALLENGE_MEANINGS = {"record_result": "Performed", "review": "Reviewed"}


@router.post("/results/{sample_id}/signature-challenges")
async def post_em_signature_challenge(
    sample_id: uuid.UUID,
    body: EmSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        sample = await session.get(EmSampleOrReading, sample_id)
        if sample is None:
            raise NotFoundError("EM sample/reading not found")
        meaning = _EM_CHALLENGE_MEANINGS.get(body.action)
        if meaning is None:
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="em_sample_or_reading", record_id=sample.id,
            record_version=sample.version, record_hash=em_sample_record_hash(sample), meaning=meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/results", response_model=MutationReceipt)
async def post_record_result(
    cmd: RecordEmResultCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        site_id = cmd.site_id
        if cmd.sample_id is not None:
            sample = await session.get(EmSampleOrReading, cmd.sample_id)
            if sample is None:
                raise NotFoundError("EM sample/reading not found")
            site_id = sample.site_id
        await evaluate_policy(session, actor.user_id, action="em_sample.record_result", site_id=site_id)
        return await record_em_result(session, cmd, actor.user_id)


@router.get("/results/{sample_id}")
async def get_result(sample_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    sample = await session.get(EmSampleOrReading, sample_id)
    if sample is None:
        raise NotFoundError("EM sample/reading not found")
    return _sample_dict(sample)


@router.post("/results/{sample_id}/review", response_model=MutationReceipt)
async def post_review_result(
    sample_id: uuid.UUID,
    cmd: ReviewEmResultCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.sample_id != sample_id:
        raise ValidationFailedError("sample_id in path and body must match")
    async with session.begin():
        sample = await session.get(EmSampleOrReading, sample_id)
        if sample is None:
            raise NotFoundError("EM sample/reading not found")
        await evaluate_policy(session, actor.user_id, action="em_sample.review", site_id=sample.site_id)
        return await review_em_result(session, cmd, actor.user_id)


@router.post("/excursions/{excursion_id}/impact", response_model=MutationReceipt)
async def post_excursion_impact(
    excursion_id: uuid.UUID,
    cmd: RecordExcursionImpactCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.excursion_id != excursion_id:
        raise ValidationFailedError("excursion_id in path and body must match")
    async with session.begin():
        excursion = await session.get(EmExcursion, excursion_id)
        if excursion is None:
            raise NotFoundError("EM excursion not found")
        await evaluate_policy(session, actor.user_id, action="em_excursion.impact", site_id=excursion.site_id)
        return await record_excursion_impact(session, cmd, actor.user_id)


@router.get("/areas/{area_id}/readiness")
async def get_readiness(area_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        return await get_area_readiness(session, area_id)


@router.get("/trends")
async def get_trends_endpoint(
    location_id: uuid.UUID, monitoring_type: str | None = None, session: AsyncSession = Depends(get_session)
) -> dict:
    async with session.begin():
        return await get_trends(session, location_id, monitoring_type)
