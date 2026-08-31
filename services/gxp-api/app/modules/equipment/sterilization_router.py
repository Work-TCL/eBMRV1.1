import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.equipment.sterilization_commands import (
    CompleteFilterUseCommand,
    CreateProcessCycleCommand,
    InstallFilterCommand,
    RecordCycleDataCommand,
    RecordFilterIntegrityTestCommand,
    ReviewCycleCommand,
    StartCycleCommand,
    complete_filter_use,
    create_process_cycle,
    cycle_record_hash,
    filter_use_record_hash,
    get_item_status,
    install_filter,
    record_cycle_data,
    record_filter_integrity_test,
    review_cycle,
    start_cycle,
)
from app.modules.equipment.sterilization_models import ProcessCycle, SterileFilterUse
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/sterilization/v1", tags=["sterilization"])
cip_sip_router = APIRouter(prefix="/cip-sip/v1", tags=["sterilization"])
filtration_router = APIRouter(prefix="/filtration/v1", tags=["sterilization"])


def _cycle_dict(cycle: ProcessCycle) -> dict:
    return {
        "id": str(cycle.id),
        "site_id": str(cycle.site_id),
        "process_type": cycle.process_type,
        "equipment_id": str(cycle.equipment_id),
        "state": cycle.state,
        "critical_alarm": cycle.critical_alarm,
        "indicator_results": cycle.indicator_results,
        "reprocessing_authorization_ref": cycle.reprocessing_authorization_ref,
        "requires_deviation": cycle.requires_deviation,
        "version": cycle.version,
    }


@router.post("/cycles", response_model=MutationReceipt)
async def post_create_cycle(
    cmd: CreateProcessCycleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="process_cycle.create", site_id=cmd.site_id)
        return await create_process_cycle(session, cmd, actor.user_id)


@cip_sip_router.post("/cycles", response_model=MutationReceipt)
async def post_create_cip_sip_cycle(
    cmd: CreateProcessCycleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="process_cycle.create", site_id=cmd.site_id)
        return await create_process_cycle(session, cmd, actor.user_id)


@router.get("/cycles/{cycle_id}")
async def get_cycle(cycle_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    cycle = await session.get(ProcessCycle, cycle_id)
    if cycle is None:
        raise NotFoundError("Process cycle not found")
    return _cycle_dict(cycle)


class CycleSignatureChallengeRequest(BaseModel):
    action: str  # "start" | "review"


_CYCLE_CHALLENGE_MEANINGS = {"start": "Performed", "review": "Reviewed"}


@router.post("/cycles/{cycle_id}/signature-challenges")
async def post_cycle_signature_challenge(
    cycle_id: uuid.UUID,
    body: CycleSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        cycle = await session.get(ProcessCycle, cycle_id)
        if cycle is None:
            raise NotFoundError("Process cycle not found")
        meaning = _CYCLE_CHALLENGE_MEANINGS.get(body.action)
        if meaning is None:
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="process_cycle", record_id=cycle.id,
            record_version=cycle.version, record_hash=cycle_record_hash(cycle), meaning=meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/cycles/{cycle_id}/start", response_model=MutationReceipt)
async def post_start_cycle(
    cycle_id: uuid.UUID,
    cmd: StartCycleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.cycle_id != cycle_id:
        raise ValidationFailedError("cycle_id in path and body must match")
    async with session.begin():
        cycle = await session.get(ProcessCycle, cycle_id)
        if cycle is None:
            raise NotFoundError("Process cycle not found")
        await evaluate_policy(session, actor.user_id, action="process_cycle.start", site_id=cycle.site_id)
        return await start_cycle(session, cmd, actor.user_id)


@router.post("/cycles/{cycle_id}/data", response_model=MutationReceipt)
async def post_record_data(
    cycle_id: uuid.UUID,
    cmd: RecordCycleDataCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.cycle_id != cycle_id:
        raise ValidationFailedError("cycle_id in path and body must match")
    async with session.begin():
        cycle = await session.get(ProcessCycle, cycle_id)
        if cycle is None:
            raise NotFoundError("Process cycle not found")
        await evaluate_policy(session, actor.user_id, action="process_cycle.start", site_id=cycle.site_id)
        return await record_cycle_data(session, cmd, actor.user_id)


@router.post("/cycles/{cycle_id}/review", response_model=MutationReceipt)
async def post_review_cycle(
    cycle_id: uuid.UUID,
    cmd: ReviewCycleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.cycle_id != cycle_id:
        raise ValidationFailedError("cycle_id in path and body must match")
    async with session.begin():
        cycle = await session.get(ProcessCycle, cycle_id)
        if cycle is None:
            raise NotFoundError("Process cycle not found")
        await evaluate_policy(session, actor.user_id, action="process_cycle.review", site_id=cycle.site_id)
        return await review_cycle(session, cmd, actor.user_id)


@router.get("/items/{item_id}/status")
async def get_status(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        return await get_item_status(session, item_id)


def _filter_use_dict(use: SterileFilterUse) -> dict:
    return {
        "id": str(use.id),
        "site_id": str(use.site_id),
        "filter_serial": use.filter_serial,
        "state": use.state,
        "pre_use_integrity_result": use.pre_use_integrity_result,
        "post_use_integrity_result": use.post_use_integrity_result,
        "reuse_count": use.reuse_count,
        "requires_deviation": use.requires_deviation,
        "version": use.version,
    }


@filtration_router.post("/filters/install", response_model=MutationReceipt)
async def post_install_filter(
    cmd: InstallFilterCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="sterile_filter_use.create", site_id=cmd.site_id)
        return await install_filter(session, cmd, actor.user_id)


@filtration_router.get("/filters/{use_id}")
async def get_filter_use(use_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    use = await session.get(SterileFilterUse, use_id)
    if use is None:
        raise NotFoundError("Sterile filter use not found")
    return _filter_use_dict(use)


@filtration_router.post("/filters/{use_id}/integrity-tests", response_model=MutationReceipt)
async def post_integrity_test(
    use_id: uuid.UUID,
    cmd: RecordFilterIntegrityTestCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.use_id != use_id:
        raise ValidationFailedError("use_id in path and body must match")
    async with session.begin():
        use = await session.get(SterileFilterUse, use_id)
        if use is None:
            raise NotFoundError("Sterile filter use not found")
        await evaluate_policy(session, actor.user_id, action="sterile_filter_use.create", site_id=use.site_id)
        return await record_filter_integrity_test(session, cmd, actor.user_id)


class FilterUseSignatureChallengeRequest(BaseModel):
    action: str = "complete"


@filtration_router.post("/uses/{use_id}/signature-challenges")
async def post_filter_use_signature_challenge(
    use_id: uuid.UUID,
    body: FilterUseSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        use = await session.get(SterileFilterUse, use_id)
        if use is None:
            raise NotFoundError("Sterile filter use not found")
        if body.action != "complete":
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="sterile_filter_use", record_id=use.id,
            record_version=use.version, record_hash=filter_use_record_hash(use), meaning="Performed",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@filtration_router.post("/uses/{use_id}/complete", response_model=MutationReceipt)
async def post_complete_filter_use(
    use_id: uuid.UUID,
    cmd: CompleteFilterUseCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.use_id != use_id:
        raise ValidationFailedError("use_id in path and body must match")
    async with session.begin():
        use = await session.get(SterileFilterUse, use_id)
        if use is None:
            raise NotFoundError("Sterile filter use not found")
        await evaluate_policy(session, actor.user_id, action="sterile_filter_use.complete", site_id=use.site_id)
        return await complete_filter_use(session, cmd, actor.user_id)
