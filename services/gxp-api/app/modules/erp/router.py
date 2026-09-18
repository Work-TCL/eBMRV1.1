"""Document 53 (SPEC-ERP-006) owns the *only* contract surface for Documents 48-52 (Document 113 §6:
49/50/51 are "adapter implementation behind the Document 48/53 provider contract"; 52 is "master-data
sync jobs behind the Document 53 integration gateway; no independent public API"). One router, one
prefix, for the whole WP-07 package -- not one router per document."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.erp import commands as erp_commands
from app.modules.erp.models import (
    ErpExternalMapping,
    ErpInstance,
    IntegrationBulkJob,
    IntegrationCommand,
    IntegrationReconciliationRun,
)
from app.modules.policy.service import evaluate_policy
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/integration/v1", tags=["integration"])


# --- ERP instance -------------------------------------------------------------------------------------


@router.post("/instances", response_model=MutationReceipt)
async def post_register_instance(
    cmd: erp_commands.RegisterERPInstanceCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="erp_instance.administer", site_id=cmd.site_id)
        return await erp_commands.register_erp_instance(session, cmd, actor.user_id)


@router.get("/instances/{instance_id}")
async def get_instance(instance_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        instance = await session.get(ErpInstance, instance_id)
        if instance is None:
            raise NotFoundError("ERP instance not found")
        return {
            "id": str(instance.id), "site_id": str(instance.site_id) if instance.site_id else None,
            "instance_name": instance.instance_name, "vendor": instance.vendor,
            "environment": instance.environment, "base_url": instance.base_url,
            "auth_method": instance.auth_method, "capabilities": instance.capabilities,
            "contract_version": instance.contract_version, "status": instance.status,
            "version": instance.version, "validated": instance.validated,
            "validated_by_user_id": str(instance.validated_by_user_id) if instance.validated_by_user_id else None,
            "validated_at": instance.validated_at.isoformat() if instance.validated_at else None,
            "service_actor_user_id": str(instance.service_actor_user_id) if instance.service_actor_user_id else None,
            "created_at": instance.created_at.isoformat(),
        }


INSTANCE_SORTABLE = {"instance_name": ErpInstance.instance_name}


# Read-only list — lets the frontend offer a "pick an instance" selector instead of requiring the
# operator to already have the instance id in hand (it's otherwise only ever shown once, in the
# register-instance response).
@router.get("/instances")
async def list_instances(session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params)) -> dict:
    stmt = select(ErpInstance)
    if params.q:
        stmt = stmt.where(ErpInstance.instance_name.ilike(f"%{params.q}%"))
    rows, envelope = await paginate(session, stmt, params, sortable=INSTANCE_SORTABLE, default_sort=ErpInstance.instance_name)
    return {
        **envelope,
        "items": [
            {"id": str(i.id), "instance_name": i.instance_name, "vendor": i.vendor, "environment": i.environment, "status": i.status}
            for (i,) in rows
        ],
    }


@router.post("/instances/{instance_id}/validate", response_model=MutationReceipt)
async def post_validate_instance(
    instance_id: uuid.UUID, cmd: erp_commands.ValidateERPInstanceCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    """MULTI-FR-024."""
    if cmd.instance_id != instance_id:
        raise ValidationFailedError("instance_id in path and body must match")
    async with session.begin():
        instance = await session.get(ErpInstance, instance_id)
        if instance is None:
            raise NotFoundError("ERP instance not found")
        await evaluate_policy(session, actor.user_id, action="erp_instance.administer", site_id=instance.site_id)
        return await erp_commands.validate_erp_instance(session, cmd, actor.user_id)


@router.get("/instances/{instance_id}/capabilities")
async def get_instance_capabilities(instance_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        return await erp_commands.get_capabilities(session, instance_id)


# --- Master-data mapping (Document 52) -----------------------------------------------------------------


@router.post("/mappings", response_model=MutationReceipt)
async def post_propose_mapping(
    cmd: erp_commands.ProposeMappingCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        instance = await session.get(ErpInstance, cmd.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="erp_mapping.propose", site_id=instance.site_id if instance else None)
        return await erp_commands.propose_mapping(session, cmd, actor.user_id)


@router.post("/mappings/{mapping_id}/approve", response_model=MutationReceipt)
async def post_approve_mapping(
    mapping_id: uuid.UUID, cmd: erp_commands.ApproveMappingCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.mapping_id != mapping_id:
        raise ValidationFailedError("mapping_id in path and body must match")
    async with session.begin():
        mapping = await session.get(ErpExternalMapping, mapping_id)
        if mapping is None:
            raise NotFoundError("Mapping not found")
        instance = await session.get(ErpInstance, mapping.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="erp_mapping.approve", site_id=instance.site_id if instance else None)
        return await erp_commands.approve_mapping(session, cmd, actor.user_id)


@router.post("/mappings/{mapping_id}/external-change", response_model=MutationReceipt)
async def post_apply_external_change(
    mapping_id: uuid.UUID, cmd: erp_commands.ApplyExternalChangeCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.mapping_id != mapping_id:
        raise ValidationFailedError("mapping_id in path and body must match")
    async with session.begin():
        mapping = await session.get(ErpExternalMapping, mapping_id)
        if mapping is None:
            raise NotFoundError("Mapping not found")
        instance = await session.get(ErpInstance, mapping.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="erp_mapping.propose", site_id=instance.site_id if instance else None)
        return await erp_commands.apply_external_change(session, cmd, actor.user_id)


@router.post("/mapping-conflicts/{conflict_id}/resolve", response_model=MutationReceipt)
async def post_resolve_conflict(
    conflict_id: uuid.UUID, cmd: erp_commands.ResolveMasterConflictCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.conflict_id != conflict_id:
        raise ValidationFailedError("conflict_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="erp_mapping.resolve_conflict", site_id=None)
        return await erp_commands.resolve_master_conflict(session, cmd, actor.user_id)


@router.post("/sync-checkpoints", response_model=MutationReceipt)
async def post_advance_checkpoint(
    cmd: erp_commands.AdvanceSyncCheckpointCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        instance = await session.get(ErpInstance, cmd.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="erp_sync.checkpoint", site_id=instance.site_id if instance else None)
        return await erp_commands.advance_sync_checkpoint(session, cmd, actor.user_id)


# --- Integration command ledger (Document 53, used by every adapter) ----------------------------------


@router.post("/commands", response_model=MutationReceipt)
async def post_queue_command(
    cmd: erp_commands.QueueERPCommandCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        instance = await session.get(ErpInstance, cmd.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_command.queue", site_id=instance.site_id if instance else None)
        return await erp_commands.queue_erp_command(session, cmd, actor.user_id)


@router.get("/commands/{command_id}")
async def get_command(command_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        command = await session.get(IntegrationCommand, command_id)
        if command is None:
            raise NotFoundError("Integration command not found")
        return {
            "id": str(command.id), "command_type": command.command_type, "state": command.state,
            "attempt_count": command.attempt_count, "external_reference": command.external_reference,
            "last_error_category": command.last_error_category, "version": command.version,
        }


@router.post("/commands/{command_id}/dispatch", response_model=MutationReceipt)
async def post_dispatch_command(
    command_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    # No enclosing `async with session.begin()` here -- dispatch_erp_command manages its own two
    # transactions around the real outbound HTTP call (see its docstring; rule 01 forbids I/O inside a
    # Mutation Gateway transaction).
    async with session.begin():
        command = await session.get(IntegrationCommand, command_id)
        if command is None:
            raise NotFoundError("Integration command not found")
        instance = await session.get(ErpInstance, command.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_command.dispatch", site_id=instance.site_id if instance else None)
    return await erp_commands.dispatch_erp_command(session, command_id, actor.user_id)


@router.post("/commands/{command_id}/retry", response_model=MutationReceipt)
async def post_retry_command(
    command_id: uuid.UUID, cmd: erp_commands.RetryERPCommandCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.command_id != command_id:
        raise ValidationFailedError("command_id in path and body must match")
    async with session.begin():
        command = await session.get(IntegrationCommand, command_id)
        if command is None:
            raise NotFoundError("Integration command not found")
        instance = await session.get(ErpInstance, command.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_command.retry", site_id=instance.site_id if instance else None)
        return await erp_commands.retry_erp_command(session, cmd, actor.user_id)


@router.post("/commands/{command_id}/cancel", response_model=MutationReceipt)
async def post_cancel_command(
    command_id: uuid.UUID, cmd: erp_commands.CancelPendingERPCommandCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.command_id != command_id:
        raise ValidationFailedError("command_id in path and body must match")
    async with session.begin():
        command = await session.get(IntegrationCommand, command_id)
        if command is None:
            raise NotFoundError("Integration command not found")
        instance = await session.get(ErpInstance, command.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_command.cancel", site_id=instance.site_id if instance else None)
        return await erp_commands.cancel_pending_erp_command(session, cmd, actor.user_id)


@router.post("/commands/{command_id}/correct", response_model=MutationReceipt)
async def post_correct_command(
    command_id: uuid.UUID, cmd: erp_commands.CreateCorrectedCommandCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.original_command_id != command_id:
        raise ValidationFailedError("command_id in path and body must match")
    async with session.begin():
        command = await session.get(IntegrationCommand, command_id)
        if command is None:
            raise NotFoundError("Integration command not found")
        instance = await session.get(ErpInstance, command.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_command.queue", site_id=instance.site_id if instance else None)
        return await erp_commands.create_corrected_command(session, cmd, actor.user_id)


@router.post("/commands/{command_id}/reconcile-uncertain", response_model=MutationReceipt)
async def post_reconcile_uncertain(
    command_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        command = await session.get(IntegrationCommand, command_id)
        if command is None:
            raise NotFoundError("Integration command not found")
        instance = await session.get(ErpInstance, command.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_command.retry", site_id=instance.site_id if instance else None)
        return await erp_commands.reconcile_uncertain_commit(session, command_id, actor.user_id)


@router.post("/commands/{command_id}/compensate", response_model=MutationReceipt)
async def post_compensate_command(
    command_id: uuid.UUID, cmd: erp_commands.CreateCompensationCommandCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    """INT-FR-016. Reuses `integration_command.queue` (same permission as /correct -- both are "queue a
    new command against this instance"; compensation's own guardrail is the code-level check that the
    original succeeded and a `gxp_authorization_reference` is present, not a distinct RBAC grant)."""
    if cmd.original_command_id != command_id:
        raise ValidationFailedError("command_id in path and body must match")
    async with session.begin():
        command = await session.get(IntegrationCommand, command_id)
        if command is None:
            raise NotFoundError("Integration command not found")
        instance = await session.get(ErpInstance, command.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_command.queue", site_id=instance.site_id if instance else None)
        return await erp_commands.create_compensation_command(session, cmd, actor.user_id)


@router.get("/instances/{instance_id}/sla-metrics")
async def get_sla_metrics(
    instance_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """INT-FR-021. Read/reporting only -- no regulated decision is made from this (rule 11 governs
    decisions read from a projection, not observability metrics)."""
    instance = await session.get(ErpInstance, instance_id)
    if instance is None:
        raise NotFoundError("ERP instance not found")
    await evaluate_policy(session, actor.user_id, action="integration_command.queue", site_id=instance.site_id)
    return await erp_commands.get_integration_sla_metrics(session, instance_id)


@router.get("/instances/{instance_id}/data-quality-metrics")
async def get_data_quality_metrics(
    instance_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """MDS-FR-026."""
    instance = await session.get(ErpInstance, instance_id)
    if instance is None:
        raise NotFoundError("ERP instance not found")
    await evaluate_policy(session, actor.user_id, action="integration_command.queue", site_id=instance.site_id)
    return await erp_commands.get_master_data_quality_metrics(session, instance_id)


# --- Bulk jobs -----------------------------------------------------------------------------------------


@router.post("/bulk-jobs", response_model=MutationReceipt)
async def post_start_bulk_job(
    cmd: erp_commands.StartBulkJobCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        instance = await session.get(ErpInstance, cmd.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_command.queue", site_id=instance.site_id if instance else None)
        return await erp_commands.start_bulk_job(session, cmd, actor.user_id)


@router.post("/bulk-jobs/{job_id}/progress", response_model=MutationReceipt)
async def post_record_bulk_job_progress(
    job_id: uuid.UUID, cmd: erp_commands.RecordBulkJobProgressCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.job_id != job_id:
        raise ValidationFailedError("job_id in path and body must match")
    async with session.begin():
        job = await session.get(IntegrationBulkJob, job_id)
        if job is None:
            raise NotFoundError("Bulk job not found")
        instance = await session.get(ErpInstance, job.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_command.queue", site_id=instance.site_id if instance else None)
        return await erp_commands.record_bulk_job_progress(session, cmd, actor.user_id)


@router.post("/bulk-jobs/{job_id}/complete", response_model=MutationReceipt)
async def post_complete_bulk_job(
    job_id: uuid.UUID, cmd: erp_commands.CompleteBulkJobCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.job_id != job_id:
        raise ValidationFailedError("job_id in path and body must match")
    async with session.begin():
        job = await session.get(IntegrationBulkJob, job_id)
        if job is None:
            raise NotFoundError("Bulk job not found")
        instance = await session.get(ErpInstance, job.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_command.queue", site_id=instance.site_id if instance else None)
        return await erp_commands.complete_bulk_job(session, cmd, actor.user_id)


# --- Migration package provenance -----------------------------------------------------------------------


@router.post("/migration-packages", response_model=MutationReceipt)
async def post_record_migration_package(
    cmd: erp_commands.RecordMigrationPackageCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="integration_command.queue", site_id=cmd.site_id)
        return await erp_commands.record_migration_package(session, cmd, actor.user_id)


# --- Inbound event ledger --------------------------------------------------------------------------


@router.post("/events", response_model=MutationReceipt)
async def post_ingest_event(
    cmd: erp_commands.IngestERPEventCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        instance = await session.get(ErpInstance, cmd.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_event.ingest", site_id=instance.site_id if instance else None)
        return await erp_commands.ingest_erp_event(session, cmd, actor.user_id)


# --- Reconciliation ------------------------------------------------------------------------------------


@router.post("/reconciliation-runs", response_model=MutationReceipt)
async def post_create_reconciliation_run(
    cmd: erp_commands.CreateReconciliationRunCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        instance = await session.get(ErpInstance, cmd.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_reconciliation.manage", site_id=instance.site_id if instance else None)
        return await erp_commands.create_reconciliation_run(session, cmd, actor.user_id)


@router.post("/reconciliation-runs/{run_id}/differences", response_model=MutationReceipt)
async def post_record_difference(
    run_id: uuid.UUID, cmd: erp_commands.RecordReconciliationDifferenceCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.run_id != run_id:
        raise ValidationFailedError("run_id in path and body must match")
    async with session.begin():
        run = await session.get(IntegrationReconciliationRun, run_id)
        if run is None:
            raise NotFoundError("Reconciliation run not found")
        instance = await session.get(ErpInstance, run.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_reconciliation.manage", site_id=instance.site_id if instance else None)
        return await erp_commands.record_reconciliation_difference(session, cmd, actor.user_id)


@router.post("/reconciliation-differences/{difference_id}/resolve", response_model=MutationReceipt)
async def post_resolve_difference(
    difference_id: uuid.UUID, cmd: erp_commands.ResolveReconciliationDifferenceCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.difference_id != difference_id:
        raise ValidationFailedError("difference_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="integration_reconciliation.manage", site_id=None)
        return await erp_commands.resolve_reconciliation_difference(session, cmd, actor.user_id)


@router.post("/reconciliation-runs/{run_id}/complete", response_model=MutationReceipt)
async def post_complete_run(
    run_id: uuid.UUID, cmd: erp_commands.CompleteReconciliationRunCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.run_id != run_id:
        raise ValidationFailedError("run_id in path and body must match")
    async with session.begin():
        run = await session.get(IntegrationReconciliationRun, run_id)
        if run is None:
            raise NotFoundError("Reconciliation run not found")
        instance = await session.get(ErpInstance, run.erp_instance_id)
        await evaluate_policy(session, actor.user_id, action="integration_reconciliation.manage", site_id=instance.site_id if instance else None)
        return await erp_commands.complete_reconciliation_run(session, cmd, actor.user_id)
