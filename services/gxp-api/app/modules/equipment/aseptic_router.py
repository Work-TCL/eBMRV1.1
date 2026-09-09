import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.equipment.aseptic_commands import (
    CompleteOperationCommand,
    CreateAsepticOperationCommand,
    CreateAsepticProfileVersionCommand,
    RecordEventCommand,
    RecordInterventionCommand,
    StartOperationCommand,
    SupersedeAsepticProfileVersionCommand,
    complete_operation,
    create_operation,
    create_profile_version,
    get_readiness,
    get_review_summary,
    list_profile_versions,
    operation_record_hash,
    record_event,
    record_intervention,
    start_operation,
    supersede_profile_version,
)
from app.modules.equipment.aseptic_models import AsepticIntervention, AsepticOperation, AsepticProfileVersion
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


def _profile_dict(profile: AsepticProfileVersion) -> dict:
    return {
        "id": str(profile.id),
        "site_id": str(profile.site_id),
        "profile_number": profile.profile_number,
        "version_no": profile.version_no,
        "product_id": str(profile.product_id) if profile.product_id else None,
        "required_area_classification": profile.required_area_classification,
        "validation_reference": profile.validation_reference,
        "state": profile.state,
        "supersedes_profile_version_id": str(profile.supersedes_profile_version_id) if profile.supersedes_profile_version_id else None,
        "version": profile.version,
    }


@router.get("/profiles")
async def list_profiles(site_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    """Full browsable history (RELEASED and SUPERSEDED) for `/aseptic`'s own list section. The narrower
    RELEASED-only picker feed (`GET /products/v1/sterile-profiles` and this module's own
    `list_released_profile_versions`) is a separate function, not this endpoint."""
    profiles = await list_profile_versions(session, site_id)
    return [_profile_dict(p) for p in profiles]


@router.post("/profiles", response_model=MutationReceipt)
async def post_create_profile(
    cmd: CreateAsepticProfileVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="aseptic_profile_version.create", site_id=cmd.site_id)
        return await create_profile_version(session, cmd, actor.user_id)


@router.post("/profiles/{profile_version_id}/supersede", response_model=MutationReceipt)
async def post_supersede_profile(
    profile_version_id: uuid.UUID,
    cmd: SupersedeAsepticProfileVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.previous_profile_version_id != profile_version_id:
        raise ValidationFailedError("profile_version_id in path and body must match")
    async with session.begin():
        previous = await session.get(AsepticProfileVersion, profile_version_id)
        if previous is None:
            raise NotFoundError("Sterile process profile not found")
        # Same permission as create — superseding is authoring a new version, same actor/activity.
        await evaluate_policy(session, actor.user_id, action="aseptic_profile_version.create", site_id=previous.site_id)
        return await supersede_profile_version(session, cmd, actor.user_id)


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


@router.get("/interventions")
async def list_interventions(site_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    """Real picker data for any field that references an `AsepticIntervention` by id -- DDCP's "Record an
    aseptic intervention" `source_aseptic_intervention_id` (fill_operation link into the aseptic module,
    ddcp/commands.py) is the first caller, previously free-text UUID entry with no way to discover a real
    one. Same SG-081 read-side precedent as every other picker added this pass: a plain read-only GET
    listing doesn't conflict with any future write/CRUD contract. Joined to the owning operation for
    site-scoping and area context, newest first."""
    rows = (
        await session.execute(
            select(AsepticIntervention, AsepticOperation.area_id)
            .join(AsepticOperation, AsepticOperation.id == AsepticIntervention.operation_id)
            .where(AsepticOperation.site_id == site_id)
            .order_by(AsepticIntervention.created_at.desc())
        )
    ).all()
    return [
        {
            "id": str(intervention.id),
            "operation_id": str(intervention.operation_id),
            "label": (
                f"{intervention.intervention_type} ({'planned' if intervention.planned else 'unplanned'})"
                + (f" — {intervention.location}" if intervention.location else "")
            ),
        }
        for intervention, _area_id in rows
    ]


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
