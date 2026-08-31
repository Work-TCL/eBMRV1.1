"""Document 57 (SPEC-DDCP-004) — Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile.

SG-150: reuses Document 54's already-seeded RBAC action codes -- see injector_router.py's module
docstring for the full rationale.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.ddcp import coated_device_commands
from app.modules.ddcp import commands as ddcp_commands
from app.modules.ddcp.models import DdcpProcessOperation, DdcpProfileVersion
from app.modules.policy.service import evaluate_policy
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/ddcp/v1/coated-device", tags=["ddcp-coated-device"])


@router.post("/profiles", response_model=MutationReceipt)
async def post_create_profile(
    cmd: coated_device_commands.CreateCoatedDeviceProfileVersionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_profile.author", site_id=cmd.site_id)
        return await coated_device_commands.create_coated_device_profile_version(session, cmd, actor.user_id)


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
            raise NotFoundError("Coated device profile version not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_profile.release", site_id=profile.site_id)
        return await ddcp_commands.release_injectable_profile_version(session, cmd, actor.user_id)


@router.get("/batches/{batch_id}/readiness")
async def get_coating_run_readiness(
    batch_id: uuid.UUID, profile_version_id: uuid.UUID, session: AsyncSession = Depends(get_session),
) -> dict:
    async with session.begin():
        return await coated_device_commands.evaluate_coating_run_readiness(session, batch_id=batch_id, profile_version_id=profile_version_id)


@router.post("/coating-runs", response_model=MutationReceipt)
async def post_start_coating_run(
    cmd: coated_device_commands.StartCoatingRunCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.start", site_id=None)
        return await coated_device_commands.start_coating_run(session, cmd, actor.user_id)


@router.post("/coating-runs/{operation_id}/process-evidence", response_model=MutationReceipt)
async def post_record_coating_process_evidence(
    operation_id: uuid.UUID, cmd: coated_device_commands.RecordCoatingProcessEvidenceCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.operation_id != operation_id:
        raise ValidationFailedError("operation_id in path and body must match")
    async with session.begin():
        operation = await session.get(DdcpProcessOperation, operation_id)
        if operation is None:
            raise NotFoundError("Coating run not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.record_intervention", site_id=operation.site_id)
        return await coated_device_commands.record_coating_process_evidence(session, cmd, actor.user_id)


@router.post("/coating-runs/{operation_id}/complete", response_model=MutationReceipt)
async def post_complete_coating_run(
    operation_id: uuid.UUID, cmd: coated_device_commands.CompleteCoatingRunCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.operation_id != operation_id:
        raise ValidationFailedError("operation_id in path and body must match")
    async with session.begin():
        operation = await session.get(DdcpProcessOperation, operation_id)
        if operation is None:
            raise NotFoundError("Coating run not found")
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.complete", site_id=operation.site_id)
        return await coated_device_commands.complete_coating_run(session, cmd, actor.user_id)


@router.post("/drug-coating-usage", response_model=MutationReceipt)
async def post_record_drug_coating_usage(
    cmd: coated_device_commands.RecordDrugCoatingUsageCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_fill.record_count", site_id=None)
        return await coated_device_commands.record_drug_coating_usage(session, cmd, actor.user_id)


@router.post("/device-coating-bindings", response_model=MutationReceipt)
async def post_bind_device_to_coating_constituent(
    cmd: coated_device_commands.BindDeviceToCoatingConstituentCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_constituent.handoff", site_id=None)
        return await coated_device_commands.bind_device_to_coating_constituent(session, cmd, actor.user_id)


@router.post("/drug-loading-results", response_model=MutationReceipt)
async def post_record_drug_loading_result(
    cmd: coated_device_commands.RecordDrugLoadingResultCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_device.record_test", site_id=None)
        return await coated_device_commands.record_drug_loading_result(session, cmd, actor.user_id)


@router.post("/post-sterilization-tests", response_model=MutationReceipt)
async def post_record_post_sterilization_test(
    cmd: coated_device_commands.RecordPostSterilizationTestCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_device.record_test", site_id=None)
        return await coated_device_commands.record_post_sterilization_test(session, cmd, actor.user_id)


@router.post("/batches/{batch_id}/release-readiness")
async def post_evaluate_release_readiness(
    batch_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_release.evaluate", site_id=None)
        return await coated_device_commands.evaluate_coated_device_release_readiness(session, batch_id, actor.user_id)


@router.post("/batches/{batch_id}/evidence-package", response_model=MutationReceipt)
async def post_create_evidence_package(
    batch_id: uuid.UUID, cmd: coated_device_commands.CreateCoatedDeviceBatchEvidencePackageCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_release.export", site_id=None)
        return await coated_device_commands.create_coated_device_batch_evidence_package(session, cmd, actor.user_id)


@router.get("/batches/{batch_id}/complaint-trace")
async def get_complaint_trace(
    batch_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    # Authenticated, not yet RBAC-scoped -- matches Document 54's own genealogy-read posture.
    del actor
    async with session.begin():
        return await coated_device_commands.trace_coated_device_complaint(session, batch_id)


@router.post("/functional-tests", response_model=MutationReceipt)
async def post_record_device_functional_test(
    cmd: coated_device_commands.RecordDeviceFunctionalTestCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_device.record_test", site_id=None)
        return await coated_device_commands.record_device_functional_test(session, cmd, actor.user_id)


@router.post("/unit-dispositions", response_model=MutationReceipt)
async def post_record_coated_device_disposition(
    cmd: coated_device_commands.RecordCoatedDeviceDispositionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ddcp_device.verify", site_id=None)
        return await coated_device_commands.record_coated_device_disposition(session, cmd, actor.user_id)
