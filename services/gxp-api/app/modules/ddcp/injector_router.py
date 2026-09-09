"""Document 55 (SPEC-DDCP-002) — Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile.

SG-150: reuses Document 54's already-seeded RBAC action codes (`ddcp_profile.*`, `ddcp_fill.*`,
`ddcp_device.*`, `ddcp_release.*`) for the conceptually equivalent operation on this document's own
tables/functions, rather than adding new unseeded action codes -- the DDCP Platform Rule frames these as
capabilities on a shared platform, not document-specific bureaucracy, and the existing "DDCP Engineer"/
"DDCP Operator" roles already cover this capability domain. Adding new codes would mean editing the shared
`tests/conftest.py`/`scripts/seed.py` permission floor under active multi-session contention for no real
authorization-semantics gain -- deliberately not done this pass.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.ddcp import commands as ddcp_commands
from app.modules.ddcp import injector_commands
from app.modules.ddcp.models import INJECTOR_SUBTYPES, DdcpProcessOperation, DdcpProfileVersion
from app.modules.policy.service import evaluate_policy
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/ddcp/v1/autoinjector", tags=["ddcp-autoinjector"])

PROFILE_SORTABLE = {"profile_code": DdcpProfileVersion.profile_code, "created_at": DdcpProfileVersion.created_at}


def _profile_summary_dict(profile: DdcpProfileVersion) -> dict:
    return {
        "id": str(profile.id), "profile_code": profile.profile_code, "subtype": profile.subtype,
        "version": profile.version, "state": profile.state,
        "product_version_id": str(profile.product_version_id) if profile.product_version_id else None,
    }


@router.post("/profiles", response_model=MutationReceipt)
async def post_create_profile(
    cmd: injector_commands.CreateInjectorProfileVersionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_profile.author", site_id=cmd.site_id)
        return await injector_commands.create_injector_profile_version(session, cmd, actor.user_id)


# Read-only list — same rationale as Document 54's own `/profiles` list (see that router's comment).
# `injector_type` is required on every injector profile (no optional-subtype gap here), so filtering by
# INJECTOR_SUBTYPES exactly separates this family from the other three sharing the same table.
@router.get("/profiles")
async def list_profiles(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params), state: str | None = "RELEASED",
) -> dict:
    async with session.begin():
        stmt = select(DdcpProfileVersion).where(DdcpProfileVersion.subtype.in_(INJECTOR_SUBTYPES))
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
            raise NotFoundError("Injector profile version not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_profile.release", site_id=profile.site_id)
        return await ddcp_commands.release_injectable_profile_version(session, cmd, actor.user_id)


@router.get("/batches/{batch_id}/readiness")
async def get_assembly_readiness(
    batch_id: uuid.UUID, profile_version_id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> dict:
    async with session.begin():
        return await injector_commands.evaluate_injector_assembly_readiness(session, batch_id=batch_id, profile_version_id=profile_version_id)


@router.post("/assembly-operations", response_model=MutationReceipt)
async def post_start_assembly_operation(
    cmd: injector_commands.StartInjectorAssemblyOperationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.start", site_id=None)
        return await injector_commands.start_injector_assembly_operation(session, cmd, actor.user_id)


@router.post("/assembly-operations/{operation_id}/parameters", response_model=MutationReceipt)
async def post_record_assembly_parameter(
    operation_id: uuid.UUID, cmd: injector_commands.RecordAssemblyParameterCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.operation_id != operation_id:
        raise ValidationFailedError("operation_id in path and body must match")
    async with session.begin():
        operation = await session.get(DdcpProcessOperation, operation_id)
        if operation is None:
            raise NotFoundError("Injector assembly operation not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.record_intervention", site_id=operation.site_id)
        return await injector_commands.record_assembly_parameter(session, cmd, actor.user_id)


@router.post("/assembly-operations/{operation_id}/complete", response_model=MutationReceipt)
async def post_complete_assembly_operation(
    operation_id: uuid.UUID, cmd: injector_commands.CompleteInjectorAssemblyOperationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.operation_id != operation_id:
        raise ValidationFailedError("operation_id in path and body must match")
    async with session.begin():
        operation = await session.get(DdcpProcessOperation, operation_id)
        if operation is None:
            raise NotFoundError("Injector assembly operation not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.complete", site_id=operation.site_id)
        return await injector_commands.complete_injector_assembly_operation(session, cmd, actor.user_id)


@router.post("/drug-container-bindings", response_model=MutationReceipt)
async def post_bind_drug_container(
    cmd: injector_commands.BindDrugContainerToInjectorUnitCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_constituent.handoff", site_id=None)
        return await injector_commands.bind_drug_container_to_injector_unit(session, cmd, actor.user_id)


@router.post("/functional-tests", response_model=MutationReceipt)
async def post_execute_functional_test(
    cmd: injector_commands.ExecuteInjectorFunctionalTestCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_device.record_test", site_id=None)
        return await injector_commands.execute_injector_functional_test(session, cmd, actor.user_id)


@router.post("/dose-delivery-results", response_model=MutationReceipt)
async def post_evaluate_dose_delivery_result(
    cmd: injector_commands.EvaluateDoseDeliveryResultCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_device.record_test", site_id=None)
        return await injector_commands.evaluate_dose_delivery_result(session, cmd, actor.user_id)


@router.post("/unit-dispositions", response_model=MutationReceipt)
async def post_record_unit_disposition(
    cmd: injector_commands.RecordUnitDispositionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_device.verify", site_id=None)
        return await injector_commands.record_unit_disposition(session, cmd, actor.user_id)


@router.post("/batches/{batch_id}/release-readiness")
async def post_evaluate_release_readiness(
    batch_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_release.evaluate", site_id=None)
        return await injector_commands.evaluate_injector_release_readiness(session, batch_id, actor.user_id)


@router.post("/batches/{batch_id}/evidence-package", response_model=MutationReceipt)
async def post_create_evidence_package(
    batch_id: uuid.UUID, cmd: injector_commands.CreateInjectorBatchEvidencePackageCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_release.export", site_id=None)
        return await injector_commands.create_injector_batch_evidence_package(session, cmd, actor.user_id)


@router.get("/complaint-trace/{finished_serial}")
async def get_complaint_trace(
    finished_serial: str, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    # Authenticated, not yet RBAC-scoped -- matches Document 54's own genealogy-read posture.
    del actor
    async with session.begin():
        return await injector_commands.trace_complaint_serial(session, finished_serial)


@router.post("/reusable-device-pairings", response_model=MutationReceipt)
async def post_record_reusable_device_pairing(
    cmd: injector_commands.RecordReusableDevicePairingCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_constituent.handoff", site_id=None)
        return await injector_commands.record_reusable_device_pairing(session, cmd, actor.user_id)
