import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
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
from app.modules.equipment.cleaning_models import EquipmentArea
from app.modules.equipment.em_models import EmExcursion, EmLocation, EmProgramVersion, EmSampleOrReading
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/em/v1", tags=["environmental-monitoring"])


def _sample_dict(sample: EmSampleOrReading, refs: dict | None = None) -> dict:
    refs = refs or {}
    return {
        "id": str(sample.id),
        "site_id": str(sample.site_id),
        "program_version_id": str(sample.program_version_id),
        "program_number": refs.get("program_number"),
        "program_version_no": refs.get("program_version_no"),
        "location_id": str(sample.location_id),
        "location_code": refs.get("location_code"),
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


def _program_dict(program: EmProgramVersion) -> dict:
    return {
        "id": str(program.id),
        "site_id": str(program.site_id),
        "program_number": program.program_number,
        "version_no": program.version_no,
        "monitoring_types": program.monitoring_types,
        "method_version": program.method_version,
        "alert_limits": program.alert_limits,
        "action_limits": program.action_limits,
        "state": program.state,
        "version": program.version,
        "created_at": program.created_at.isoformat() if program.created_at else None,
    }


def _excursion_dict(excursion: EmExcursion, refs: dict | None = None) -> dict:
    refs = refs or {}
    return {
        "id": str(excursion.id),
        "site_id": str(excursion.site_id),
        "sample_id": str(excursion.sample_id),
        "sample_monitoring_type": refs.get("sample_monitoring_type"),
        "area_id": str(excursion.area_id),
        "area_code": refs.get("area_code"),
        "affected_time_start": excursion.affected_time_start.isoformat() if excursion.affected_time_start else None,
        "affected_time_end": excursion.affected_time_end.isoformat() if excursion.affected_time_end else None,
        "affected_batch_ids": excursion.affected_batch_ids,
        "organism_details": excursion.organism_details,
        "disposition": excursion.disposition,
        "impact_assessed_at": excursion.impact_assessed_at.isoformat() if excursion.impact_assessed_at else None,
        "requires_deviation": excursion.requires_deviation,
        "deviation_reference_id": str(excursion.deviation_reference_id) if excursion.deviation_reference_id else None,
        "version": excursion.version,
        "created_at": excursion.created_at.isoformat() if excursion.created_at else None,
    }


def _location_dict(location: EmLocation) -> dict:
    return {
        "id": str(location.id),
        "site_id": str(location.site_id),
        "area_id": str(location.area_id),
        "location_code": location.location_code,
        "criticality": location.criticality,
        "status": location.status,
        "version": location.version,
    }


LOCATION_SORTABLE = {"created_at": EmLocation.created_at, "location_code": EmLocation.location_code}
PROGRAM_SORTABLE = {"created_at": EmProgramVersion.created_at, "program_number": EmProgramVersion.program_number}
SAMPLE_SORTABLE = {"created_at": EmSampleOrReading.created_at, "state": EmSampleOrReading.state}
EXCURSION_SORTABLE = {"created_at": EmExcursion.created_at, "disposition": EmExcursion.disposition}


async def _resolve_sample_refs(session: AsyncSession, samples: list[EmSampleOrReading]) -> dict[uuid.UUID, dict]:
    """Batch-resolves the program/location foreign keys `_sample_dict` labels for -- same one-query-
    per-referenced-table shape as sterilization's `_resolve_cycle_refs`."""
    if not samples:
        return {}

    program_ids = {s.program_version_id for s in samples}
    location_ids = {s.location_id for s in samples}

    program_by_id = {
        row.id: (row.program_number, row.version_no)
        for row in (
            await session.execute(
                select(EmProgramVersion.id, EmProgramVersion.program_number, EmProgramVersion.version_no)
                .where(EmProgramVersion.id.in_(program_ids))
            )
        ).all()
    }
    location_by_id = dict(
        (await session.execute(select(EmLocation.id, EmLocation.location_code).where(EmLocation.id.in_(location_ids)))).all()
    )

    resolved: dict[uuid.UUID, dict] = {}
    for s in samples:
        program_number, program_version_no = program_by_id.get(s.program_version_id, (None, None))
        resolved[s.id] = {
            "program_number": program_number,
            "program_version_no": program_version_no,
            "location_code": location_by_id.get(s.location_id),
        }
    return resolved


async def _resolve_excursion_refs(session: AsyncSession, excursions: list[EmExcursion]) -> dict[uuid.UUID, dict]:
    """Batch-resolves the sample/area foreign keys `_excursion_dict` labels for."""
    if not excursions:
        return {}

    sample_ids = {e.sample_id for e in excursions}
    area_ids = {e.area_id for e in excursions}

    sample_by_id = dict(
        (await session.execute(select(EmSampleOrReading.id, EmSampleOrReading.monitoring_type).where(EmSampleOrReading.id.in_(sample_ids)))).all()
    )
    area_by_id = dict(
        (await session.execute(select(EquipmentArea.id, EquipmentArea.area_code).where(EquipmentArea.id.in_(area_ids)))).all()
    )

    resolved: dict[uuid.UUID, dict] = {}
    for e in excursions:
        resolved[e.id] = {
            "sample_monitoring_type": sample_by_id.get(e.sample_id),
            "area_code": area_by_id.get(e.area_id),
        }
    return resolved


@router.get("/locations")
async def list_locations(
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Picker data for `location_id` — `em_location` is seed-only (no create endpoint, Document 41's own
    8-op API list), but every caller that needs a real `em_locations.id` (schedule a sampling task, look
    up trends) still needs a way to discover one instead of typing a raw UUID. Same `Paged[T]` envelope
    `listAll()` already expects, so `useEntityOptions` can pick this up the same way it does `/equipment/
    v1/areas`."""
    async with session.begin():
        stmt = select(EmLocation)
        if params.q:
            stmt = stmt.where(EmLocation.location_code.ilike(f"%{params.q}%"))
        rows, envelope = await paginate(session, stmt, params, sortable=LOCATION_SORTABLE, default_sort=EmLocation.location_code)
        locations = [loc for (loc,) in rows]
        return {**envelope, "items": [_location_dict(loc) for loc in locations]}


@router.get("/programs")
async def list_programs(
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Browsable list for /em's own "Create an EM program" section -- previously no way to see what
    programs existed at all. Same SG-081 read-side precedent as every other list added this pass."""
    async with session.begin():
        stmt = select(EmProgramVersion)
        if params.q:
            stmt = stmt.where(EmProgramVersion.program_number.ilike(f"%{params.q}%"))
        rows, envelope = await paginate(session, stmt, params, sortable=PROGRAM_SORTABLE, default_sort=EmProgramVersion.created_at)
        programs = [p for (p,) in rows]
        return {**envelope, "items": [_program_dict(p) for p in programs]}


@router.get("/samples")
async def list_samples(
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Browsable list for /em's own page -- replaces the former by-id "EM sample / reading ID" lookup
    with a real searchable list. Same SG-081 read-side precedent as every other list added this pass, and
    the same "no site scoping on this table" call as cleaning.router.list_executions (no evaluate_policy
    on the single-record GETs either)."""
    async with session.begin():
        stmt = select(EmSampleOrReading)
        if params.q:
            stmt = stmt.where(EmSampleOrReading.monitoring_type.ilike(f"%{params.q}%"))
        rows, envelope = await paginate(session, stmt, params, sortable=SAMPLE_SORTABLE, default_sort=EmSampleOrReading.created_at)
        samples = [s for (s,) in rows]
        refs = await _resolve_sample_refs(session, samples)
        return {**envelope, "items": [_sample_dict(s, refs.get(s.id)) for s in samples]}


@router.get("/excursions")
async def list_excursions(
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Browsable list so "Record excursion impact" can be triggered from a real row instead of a blind
    "type an excursion ID" form. Same SG-081 read-side precedent as every other list added this pass."""
    async with session.begin():
        stmt = select(EmExcursion)
        if params.q:
            stmt = stmt.where(EmExcursion.disposition.ilike(f"%{params.q}%"))
        rows, envelope = await paginate(session, stmt, params, sortable=EXCURSION_SORTABLE, default_sort=EmExcursion.created_at)
        excursions = [e for (e,) in rows]
        refs = await _resolve_excursion_refs(session, excursions)
        return {**envelope, "items": [_excursion_dict(e, refs.get(e.id)) for e in excursions]}


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
async def get_task(
    sample_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    sample = await session.get(EmSampleOrReading, sample_id)
    if sample is None:
        raise NotFoundError("EM sample/reading not found")
    refs = await _resolve_sample_refs(session, [sample])
    return _sample_dict(sample, refs.get(sample.id))


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
async def get_result(
    sample_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    sample = await session.get(EmSampleOrReading, sample_id)
    if sample is None:
        raise NotFoundError("EM sample/reading not found")
    refs = await _resolve_sample_refs(session, [sample])
    return _sample_dict(sample, refs.get(sample.id))


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
async def get_readiness(
    area_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        return await get_area_readiness(session, area_id)


@router.get("/trends")
async def get_trends_endpoint(
    location_id: uuid.UUID,
    monitoring_type: str | None = None,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        return await get_trends(session, location_id, monitoring_type)
