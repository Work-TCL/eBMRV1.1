"""Document 56 (SPEC-DDCP-003) — Inhalation MDI/DPI DDCP Manufacturing Profile.

SG-150: reuses Document 54's already-seeded RBAC action codes (`ddcp_profile.*`, `ddcp_fill.*`,
`ddcp_device.*`, `ddcp_release.*`) for the conceptually equivalent operation on this document's own
tables/functions -- see injector_router.py's module docstring for the full rationale.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.ddcp import commands as ddcp_commands
from app.modules.ddcp import inhalation_commands
from app.modules.ddcp.models import INHALATION_SUBTYPES, DdcpProcessOperation, DdcpProfileVersion
from app.modules.policy.service import evaluate_policy
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/ddcp/v1/inhalation", tags=["ddcp-inhalation"])

PROFILE_SORTABLE = {"profile_code": DdcpProfileVersion.profile_code, "created_at": DdcpProfileVersion.created_at}


def _profile_summary_dict(profile: DdcpProfileVersion) -> dict:
    return {
        "id": str(profile.id), "profile_code": profile.profile_code, "subtype": profile.subtype,
        "version": profile.version, "state": profile.state,
        "product_version_id": str(profile.product_version_id) if profile.product_version_id else None,
    }


@router.post("/profiles", response_model=MutationReceipt)
async def post_create_profile(
    cmd: inhalation_commands.CreateInhalationProfileVersionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_profile.author", site_id=cmd.site_id)
        return await inhalation_commands.create_inhalation_profile_version(session, cmd, actor.user_id)


# Read-only list — same rationale as Document 54's own `/profiles` list. `subtype` (MDI|DPI) is
# required on every inhalation profile, so filtering by INHALATION_SUBTYPES exactly separates this
# family from the other three sharing the same table.
@router.get("/profiles")
async def list_profiles(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params), state: str | None = "RELEASED",
) -> dict:
    async with session.begin():
        stmt = select(DdcpProfileVersion).where(DdcpProfileVersion.subtype.in_(INHALATION_SUBTYPES))
        if params.q:
            stmt = stmt.where(DdcpProfileVersion.profile_code.ilike(f"%{params.q}%"))
        if state:
            stmt = stmt.where(DdcpProfileVersion.state == state)
        rows, envelope = await paginate(session, stmt, params, sortable=PROFILE_SORTABLE, default_sort=DdcpProfileVersion.created_at)
        return {**envelope, "items": [_profile_summary_dict(p) for (p,) in rows]}


@router.post("/profiles/{profile_id}/release", response_model=MutationReceipt)
async def post_release_profile(
    profile_id: uuid.UUID, cmd: ddcp_commands.ReleaseInjectableProfileVersionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.profile_id != profile_id:
        raise ValidationFailedError("profile_id in path and body must match")
    async with session.begin():
        profile = await session.get(DdcpProfileVersion, profile_id)
        if profile is None:
            raise NotFoundError("Inhalation profile version not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_profile.release", site_id=profile.site_id)
        return await ddcp_commands.release_injectable_profile_version(session, cmd, actor.user_id)


@router.get("/batches/{batch_id}/readiness")
async def get_inhalation_readiness(
    batch_id: uuid.UUID, profile_version_id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> dict:
    async with session.begin():
        return await inhalation_commands.evaluate_inhalation_readiness(session, batch_id=batch_id, profile_version_id=profile_version_id)


@router.post("/fill-runs", response_model=MutationReceipt)
async def post_start_fill_run(
    cmd: inhalation_commands.StartInhalerFillRunCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.start", site_id=None)
        return await inhalation_commands.start_inhaler_fill_run(session, cmd, actor.user_id)


@router.post("/fill-runs/{operation_id}/complete", response_model=MutationReceipt)
async def post_complete_fill_run(
    operation_id: uuid.UUID, cmd: inhalation_commands.CompleteInhalerManufacturingRunCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.operation_id != operation_id:
        raise ValidationFailedError("operation_id in path and body must match")
    async with session.begin():
        operation = await session.get(DdcpProcessOperation, operation_id)
        if operation is None:
            raise NotFoundError("Inhaler fill run not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.complete", site_id=operation.site_id)
        return await inhalation_commands.complete_inhaler_manufacturing_run(session, cmd, actor.user_id)


@router.post("/closure-results", response_model=MutationReceipt)
async def post_record_closure_result(
    cmd: inhalation_commands.RecordCrimpOrClosureResultCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_device.record_test", site_id=None)
        return await inhalation_commands.record_crimp_or_closure_result(session, cmd, actor.user_id)


@router.post("/dose-tests", response_model=MutationReceipt)
async def post_record_dose_test(
    cmd: inhalation_commands.RecordInhalerDoseTestCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_device.record_test", site_id=None)
        return await inhalation_commands.record_inhaler_dose_test(session, cmd, actor.user_id)


@router.post("/dose-counter-tests", response_model=MutationReceipt)
async def post_record_dose_counter_test(
    cmd: inhalation_commands.RecordDoseCounterTestCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_device.record_test", site_id=None)
        return await inhalation_commands.record_dose_counter_test(session, cmd, actor.user_id)


@router.post("/batches/{batch_id}/release-readiness")
async def post_evaluate_release_readiness(
    batch_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_release.evaluate", site_id=None)
        return await inhalation_commands.evaluate_inhaler_release_readiness(session, batch_id, actor.user_id)


@router.post("/batches/{batch_id}/evidence-package", response_model=MutationReceipt)
async def post_create_evidence_package(
    batch_id: uuid.UUID, cmd: inhalation_commands.CreateInhalerBatchEvidencePackageCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_release.export", site_id=None)
        return await inhalation_commands.create_inhaler_batch_evidence_package(session, cmd, actor.user_id)


@router.get("/batches/{batch_id}/genealogy")
async def get_inhaler_lot_trace(
    batch_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    # Authenticated, not yet RBAC-scoped -- matches Document 54's own genealogy-read posture.
    del actor
    async with session.begin():
        return await inhalation_commands.trace_inhaler_lot(session, batch_id)


@router.post("/dose-unit-bindings", response_model=MutationReceipt)
async def post_bind_dose_unit_to_device(
    cmd: inhalation_commands.BindDoseUnitToDeviceCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_constituent.handoff", site_id=None)
        return await inhalation_commands.bind_dose_unit_to_device(session, cmd, actor.user_id)
