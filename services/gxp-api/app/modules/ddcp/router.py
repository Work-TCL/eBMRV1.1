"""Document 54 (SPEC-DDCP-001) — the only contract surface for this module (no "no independent API"
exposure-boundary note exists for Document 54 in Document 113 §6, unlike Document 52's master-data sync --
this module's operations are genuinely public, matching its own §4 function catalogue)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.ddcp import commands as ddcp_commands
from app.modules.ddcp.models import (
    INJECTABLE_SUBTYPES,
    ConstituentHandoff,
    DdcpProfileVersion,
    DeviceAssemblyRecord,
    FillOperation,
)
from app.modules.policy.service import evaluate_policy
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/ddcp/v1/prefilled-syringe", tags=["ddcp-prefilled-syringe"])

PROFILE_SORTABLE = {"profile_code": DdcpProfileVersion.profile_code, "created_at": DdcpProfileVersion.created_at}


def _profile_summary_dict(profile: DdcpProfileVersion) -> dict:
    return {
        "id": str(profile.id), "profile_code": profile.profile_code, "subtype": profile.subtype,
        "version": profile.version, "state": profile.state,
        "product_version_id": str(profile.product_version_id) if profile.product_version_id else None,
    }


# --- DdcpProfileVersion (PFS-FR-001/002/028/029) -------------------------------------------------------


@router.post("/profiles", response_model=MutationReceipt)
async def post_create_profile(
    cmd: ddcp_commands.CreateInjectableProfileVersionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_profile.author", site_id=cmd.site_id)
        return await ddcp_commands.create_injectable_profile_version(session, cmd, actor.user_id)


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
            raise NotFoundError("Injectable profile version not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_profile.release", site_id=profile.site_id)
        return await ddcp_commands.release_injectable_profile_version(session, cmd, actor.user_id)


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        profile = await session.get(DdcpProfileVersion, profile_id)
        if profile is None:
            raise NotFoundError("Injectable profile version not found")
        return _profile_summary_dict(profile)


# Read-only list — lets the frontend offer a "pick a profile" selector instead of requiring the operator
# to already have the profile id in hand (the id is otherwise only ever shown once, in the create/release
# response). `state` defaults to RELEASED (the only state a batch can actually use), matching what a
# picker for "which profile does this batch follow" needs; pass state= explicitly for DRAFT/SUPERSEDED.
#
# `ddcp_profile_version` is the one table Documents 54/55/56/57 all share (see models.py's module
# docstring) with no family/document-type column of its own, so a PFS-only list has to distinguish by
# `subtype` — INJECTABLE_SUBTYPES never overlaps INJECTOR_SUBTYPES/INHALATION_SUBTYPES (grep-verified),
# so this is exact for any profile that set a subtype. A PFS profile created with no subtype (it's
# optional on this document only) won't appear here — under-inclusion, not the wrong-family
# over-inclusion a blanket list would risk.
@router.get("/profiles")
async def list_profiles(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params), state: str | None = "RELEASED",
) -> dict:
    async with session.begin():
        stmt = select(DdcpProfileVersion).where(DdcpProfileVersion.subtype.in_(INJECTABLE_SUBTYPES))
        if params.q:
            stmt = stmt.where(DdcpProfileVersion.profile_code.ilike(f"%{params.q}%"))
        if state:
            stmt = stmt.where(DdcpProfileVersion.state == state)
        rows, envelope = await paginate(session, stmt, params, sortable=PROFILE_SORTABLE, default_sort=DdcpProfileVersion.created_at)
        return {**envelope, "items": [_profile_summary_dict(p) for (p,) in rows]}


# --- ConstituentHandoff (PFS-FR-003/004, §8) -------------------------------------------------------------


@router.post("/constituent-handoffs", response_model=MutationReceipt)
async def post_record_handoff(
    cmd: ddcp_commands.RecordConstituentHandoffCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_constituent.handoff", site_id=None)
        return await ddcp_commands.record_constituent_handoff(session, cmd, actor.user_id)


@router.post("/constituent-handoffs/{handoff_id}/decide", response_model=MutationReceipt)
async def post_decide_handoff(
    handoff_id: uuid.UUID, cmd: ddcp_commands.DecideConstituentHandoffCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.handoff_id != handoff_id:
        raise ValidationFailedError("handoff_id in path and body must match")
    async with session.begin():
        handoff = await session.get(ConstituentHandoff, handoff_id)
        if handoff is None:
            raise NotFoundError("Constituent handoff not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_constituent.decide", site_id=handoff.site_id)
        return await ddcp_commands.decide_constituent_handoff(session, cmd, actor.user_id)


# --- Readiness (PFS-FR-006/007/008) ---------------------------------------------------------------------


@router.get("/batches/{batch_id}/readiness")
async def get_batch_readiness(
    batch_id: uuid.UUID, profile_version_id: uuid.UUID, line_id: uuid.UUID | None = None,
    filler_equipment_id: uuid.UUID | None = None, session: AsyncSession = Depends(get_session),
) -> dict:
    async with session.begin():
        return await ddcp_commands.evaluate_injectable_batch_readiness(
            session, batch_id=batch_id, profile_version_id=profile_version_id, line_id=line_id, filler_equipment_id=filler_equipment_id,
        )


# --- FillOperation (PFS-FR-006..011) --------------------------------------------------------------------


@router.post("/fill-operations", response_model=MutationReceipt)
async def post_start_filling_stage(
    cmd: ddcp_commands.StartFillingStageCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.start", site_id=None)
        return await ddcp_commands.start_filling_stage(session, cmd, actor.user_id)


@router.post("/fill-operations/{fill_operation_id}/ipc-results", response_model=MutationReceipt)
async def post_record_fill_ipc(
    fill_operation_id: uuid.UUID, cmd: ddcp_commands.RecordFillIpcResultCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.fill_operation_id != fill_operation_id:
        raise ValidationFailedError("fill_operation_id in path and body must match")
    async with session.begin():
        fill_op = await session.get(FillOperation, fill_operation_id)
        if fill_op is None:
            raise NotFoundError("Fill operation not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.record_ipc", site_id=fill_op.site_id)
        return await ddcp_commands.record_fill_ipc_result(session, cmd, actor.user_id)


@router.post("/production-counts", response_model=MutationReceipt)
async def post_record_count(
    cmd: ddcp_commands.RecordSyringeUnitOrCountCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.record_count", site_id=None)
        return await ddcp_commands.record_syringe_unit_or_count(session, cmd, actor.user_id)


@router.post("/fill-operations/{fill_operation_id}/interventions", response_model=MutationReceipt)
async def post_record_intervention(
    fill_operation_id: uuid.UUID, cmd: ddcp_commands.RecordAsepticInterventionForFillCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.fill_operation_id != fill_operation_id:
        raise ValidationFailedError("fill_operation_id in path and body must match")
    async with session.begin():
        fill_op = await session.get(FillOperation, fill_operation_id)
        if fill_op is None:
            raise NotFoundError("Fill operation not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.record_intervention", site_id=fill_op.site_id)
        return await ddcp_commands.record_aseptic_intervention_for_fill(session, cmd, actor.user_id)


@router.post("/fill-operations/{fill_operation_id}/complete", response_model=MutationReceipt)
async def post_complete_filling_stage(
    fill_operation_id: uuid.UUID, cmd: ddcp_commands.CompleteFillingStageCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.fill_operation_id != fill_operation_id:
        raise ValidationFailedError("fill_operation_id in path and body must match")
    async with session.begin():
        fill_op = await session.get(FillOperation, fill_operation_id)
        if fill_op is None:
            raise NotFoundError("Fill operation not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.complete", site_id=fill_op.site_id)
        return await ddcp_commands.complete_filling_stage(session, cmd, actor.user_id)


# --- DeviceAssemblyRecord (PFS-FR-012/013/018) ------------------------------------------------------------


@router.post("/device-assembly", response_model=MutationReceipt)
async def post_record_device_assembly(
    cmd: ddcp_commands.RecordDeviceAssemblyStepCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_device.assemble", site_id=None)
        return await ddcp_commands.record_device_assembly_step(session, cmd, actor.user_id)


@router.post("/device-assembly/{record_id}/verify", response_model=MutationReceipt)
async def post_verify_device_assembly(
    record_id: uuid.UUID, cmd: ddcp_commands.VerifyDeviceAssemblyStepCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.record_id != record_id:
        raise ValidationFailedError("record_id in path and body must match")
    async with session.begin():
        record = await session.get(DeviceAssemblyRecord, record_id)
        if record is None:
            raise NotFoundError("Device assembly record not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_device.verify", site_id=record.site_id)
        return await ddcp_commands.verify_device_assembly_step(session, cmd, actor.user_id)


# --- DeviceFunctionalTestLink (PFS-FR-014/017) --------------------------------------------------------


@router.post("/functional-tests", response_model=MutationReceipt)
async def post_record_functional_test(
    cmd: ddcp_commands.RecordPfsFunctionalTestCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_device.record_test", site_id=None)
        return await ddcp_commands.record_pfs_functional_test(session, cmd, actor.user_id)


# --- Release readiness / evidence (PFS-FR-023/024/025/030) ---------------------------------------------


@router.post("/batches/{batch_id}/release-readiness")
async def post_evaluate_release_readiness(
    batch_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_release.evaluate", site_id=None)
        return await ddcp_commands.evaluate_pfs_release_readiness(session, batch_id, actor.user_id)


@router.post("/batches/{batch_id}/evidence-package", response_model=MutationReceipt)
async def post_create_evidence_package(
    batch_id: uuid.UUID, cmd: ddcp_commands.CreatePfsBatchEvidencePackageCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_release.export", site_id=None)
        return await ddcp_commands.create_pfs_batch_evidence_package(session, cmd, actor.user_id)


@router.get("/batches/{batch_id}/genealogy")
async def get_batch_genealogy(
    batch_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    # Requires a valid authenticated actor but does not call evaluate_policy -- no per-action RBAC code
    # for this read exists yet (unlike ddcp_release.evaluate/export). Same posture as this module's own
    # pre-existing get_profile/get_batch_readiness reads; genuinely open (no actor at all) would have
    # matched that precedent exactly, but a review/genealogy composition surfaces deviation and QC-
    # exception data, so this pass at minimum requires authentication. Adding a dedicated RBAC action
    # (e.g. ddcp_release.review) is a straightforward follow-up, deliberately not done here to avoid
    # touching the shared tests/conftest.py permission seed under active multi-session contention.
    del actor
    async with session.begin():
        return await ddcp_commands.get_pfs_batch_genealogy(session, batch_id)


@router.get("/batches/{batch_id}/review-summary")
async def get_batch_review_summary(
    batch_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    # See get_batch_genealogy() above -- same posture: authenticated, not yet RBAC-scoped.
    del actor
    async with session.begin():
        return await ddcp_commands.get_pfs_batch_review_summary(session, batch_id)


# --- PFS-FR-026/019/029 (Document 54 remaining gaps) --------------------------------------------------


@router.post("/stability-retain-samples", response_model=MutationReceipt)
async def post_record_stability_retain_reference(
    cmd: ddcp_commands.RecordStabilityRetainReferenceCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.record_count", site_id=None)
        return await ddcp_commands.record_stability_retain_reference(session, cmd, actor.user_id)


@router.get("/batches/{batch_id}/serialization-compliance")
async def get_serialization_compliance(
    batch_id: uuid.UUID, profile_version_id: uuid.UUID, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    # Authenticated, not yet RBAC-scoped -- see get_batch_genealogy() above.
    del actor
    async with session.begin():
        return await ddcp_commands.verify_pfs_serialization_compliance(session, batch_id, profile_version_id)


@router.get("/change-linkage")
async def get_change_linkage(
    object_type: str, object_id: uuid.UUID, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    # Authenticated, not yet RBAC-scoped -- see get_batch_genealogy() above.
    del actor
    async with session.begin():
        return await ddcp_commands.get_ddcp_change_linkage(session, object_type, object_id)
