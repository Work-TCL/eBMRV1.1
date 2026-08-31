"""Document 69 (SPEC-DATA-001) Mutation Gateway command handlers.

Three state-changing operations, all RBAC-gated and **audit-only -- no signature**. Document 106 has no
SPEC-DATA-001 row and Document 106 # 10 explicitly lists "Projection rebuilds and cache invalidation"
and "Search, export and read operations" as operations that require no signature.

Only `rebuild_projection()` has a public HTTP endpoint (`POST /platform/v1/projections/{type}:rebuild`).
`record_migration_provenance()` and `register_data_class()` are governance/migration-tooling entry
points (same "no dedicated HTTP surface, still goes through the gateway" shape as
`release_security_evidence`); they are exercised directly in tests.

Each handler follows the kernel pattern: `check_idempotency` -> domain write (version++) ->
`write_audit_event` + `write_outbox_event` + `record_command_receipt`, all inside the caller's one
PostgreSQL transaction (MUT-FR-015 / DATA-FR-006). External I/O never happens inside the transaction.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent
from app.modules.dataops.models import (
    AUTHORITATIVE_STORES,
    DATA_CLASSIFICATIONS,
    PROJECTION_TIERS,
    DataOwnershipRegistry,
    MigrationBatch,
    ProjectionCheckpoint,
)
from app.mutation.errors import InvalidTransitionError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version, audit_event_id=existing.id,
        correlation_id=existing.id,
    )


async def _finalize(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, aggregate_type: str,
    aggregate_id: uuid.UUID, version: int, action: str, actor_user_id: uuid.UUID, reason: str | None,
    old_value: dict | None, new_value: dict, event_type: str, expected_version: int | None,
    command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value=old_value, new_value=new_value,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, payload=new_value, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type=command_type, aggregate_type=aggregate_type,
        aggregate_id=aggregate_id, expected_version=expected_version, resulting_version=version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=aggregate_id, resulting_version=version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# =================================================================================================
# rebuildProjection() -- DATA-FR-011 / DATA-FR-028. State-changing; the projection_checkpoint is the
# aggregate. First call for a projection_type creates the checkpoint (no expected_version); later calls
# require the current checkpoint version. Advances the cursor to the authoritative source's current
# max version (or an explicit, clamped source_cutoff).
# =================================================================================================


class RebuildProjectionCommand(CommandEnvelope):
    projection_type: str
    source_stream: str | None = None
    source_cutoff: int | None = None
    expected_version: int | None = None
    reason: str | None = None


async def rebuild_projection(
    session: AsyncSession, cmd: RebuildProjectionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.projection_type:
        raise ValidationFailedError("projection_type is required")
    if cmd.source_cutoff is not None and cmd.source_cutoff < 0:
        raise ValidationFailedError("source_cutoff must be >= 0")

    checkpoint = (
        await session.execute(
            select(ProjectionCheckpoint).where(ProjectionCheckpoint.projection_type == cmd.projection_type)
        )
    ).scalar_one_or_none()

    created = checkpoint is None
    if created:
        if not cmd.source_stream:
            raise ValidationFailedError("source_stream is required when first registering a projection")
        if cmd.expected_version not in (None, 0):
            raise StaleVersionError("Projection checkpoint does not exist yet", current_version=0)
        checkpoint = ProjectionCheckpoint(
            projection_type=cmd.projection_type, source_stream=cmd.source_stream,
            last_source_version=0, state="IDLE", version=1,
        )
        session.add(checkpoint)
        await session.flush()
    else:
        if cmd.expected_version is None or checkpoint.version != cmd.expected_version:
            raise StaleVersionError(
                "Projection checkpoint changed since this request was prepared",
                current_version=checkpoint.version,
            )
        if checkpoint.state == "REBUILDING":
            raise InvalidTransitionError("A rebuild is already in progress for this projection")
        if cmd.source_stream and cmd.source_stream != checkpoint.source_stream:
            raise ValidationFailedError("source_stream cannot be changed for an existing projection")

    old_value = {
        "state": checkpoint.state,
        "last_source_version": checkpoint.last_source_version,
        "version": checkpoint.version,
    }

    authoritative_max_version = (
        await session.execute(
            select(func.max(AuditEvent.aggregate_version)).where(
                AuditEvent.aggregate_type == checkpoint.source_stream
            )
        )
    ).scalar_one_or_none() or 0
    target_version = (
        min(cmd.source_cutoff, authoritative_max_version)
        if cmd.source_cutoff is not None
        else authoritative_max_version
    )

    checkpoint.last_source_version = target_version
    checkpoint.last_source_event_id = uuid.uuid4()
    checkpoint.projected_at = datetime.now(timezone.utc)
    checkpoint.state = "LIVE"
    checkpoint.error = None
    checkpoint.version += 1

    new_value = {
        "projection_type": checkpoint.projection_type,
        "source_stream": checkpoint.source_stream,
        "state": checkpoint.state,
        "last_source_version": checkpoint.last_source_version,
        "projected_at": checkpoint.projected_at.isoformat(),
        "authoritative_max_version": authoritative_max_version,
        "version": checkpoint.version,
    }

    receipt = await _finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="projection_checkpoint",
        aggregate_id=checkpoint.id, version=checkpoint.version,
        action="Created" if created else "Rebuilt", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value=None if created else old_value, new_value=new_value,
        event_type="ProjectionRebuilt",
        expected_version=None if created else cmd.expected_version, command_type="RebuildProjection",
    )
    # A rebuild also asks downstream projections to refresh from the new cursor (DATA-FR-006).
    await write_outbox_event(
        session, event_type="ProjectionUpdateRequested", aggregate_type="projection_checkpoint",
        aggregate_id=checkpoint.id, aggregate_version=checkpoint.version,
        payload={"projection_type": checkpoint.projection_type, "to_source_version": checkpoint.last_source_version},
        correlation_id=receipt.correlation_id,
    )
    return receipt


# =================================================================================================
# recordMigrationProvenance() -- DATA-FR-024 / MIG-FR-013. Append-only provenance for one imported
# data set; not a user action. No HTTP endpoint (migration-tooling entry point).
# =================================================================================================


class RecordMigrationProvenanceCommand(CommandEnvelope):
    batch_ref: str
    source_system: str
    source_artifact: str
    source_hash: str
    transform_version: str
    started_at: datetime
    completed_at: datetime | None = None
    source_row_count: int | None = None
    loaded_row_count: int | None = None
    reconciliation_hash: str | None = None
    destination_refs: list = []
    approver: str
    evidence_ref: str | None = None
    reason: str


async def record_migration_provenance(
    session: AsyncSession, cmd: RecordMigrationProvenanceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    for field in ("batch_ref", "source_system", "source_artifact", "source_hash", "transform_version", "approver", "reason"):
        if not getattr(cmd, field):
            raise ValidationFailedError(f"{field} is required")
    for field in ("source_row_count", "loaded_row_count"):
        val = getattr(cmd, field)
        if val is not None and (not isinstance(val, int) or val < 0):
            raise ValidationFailedError(f"{field} must be a non-negative integer")

    dup = (
        await session.execute(select(MigrationBatch).where(MigrationBatch.batch_ref == cmd.batch_ref))
    ).scalar_one_or_none()
    if dup is not None:
        raise InvalidTransitionError("A migration_batch with this batch_ref already exists (supersede with a new ref)")

    reconciled = (
        cmd.source_row_count is not None
        and cmd.loaded_row_count is not None
        and cmd.source_row_count == cmd.loaded_row_count
    )
    row = MigrationBatch(
        batch_ref=cmd.batch_ref, source_system=cmd.source_system, source_artifact=cmd.source_artifact,
        source_hash=cmd.source_hash, transform_version=cmd.transform_version,
        destination_refs=cmd.destination_refs, started_at=cmd.started_at, completed_at=cmd.completed_at,
        source_row_count=cmd.source_row_count, loaded_row_count=cmd.loaded_row_count,
        reconciliation_hash=cmd.reconciliation_hash,
        reconciliation_status="RECONCILED" if reconciled else "PENDING",
        approver=cmd.approver, evidence_ref=cmd.evidence_ref, state="RECORDED", version=1,
    )
    session.add(row)
    await session.flush()

    new_value = {
        "batch_ref": row.batch_ref, "source_system": row.source_system, "source_hash": row.source_hash,
        "transform_version": row.transform_version, "reconciliation_status": row.reconciliation_status,
        "source_row_count": row.source_row_count, "loaded_row_count": row.loaded_row_count,
        "approver": row.approver,
    }
    return await _finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="migration_batch",
        aggregate_id=row.id, version=row.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.reason, old_value=None, new_value=new_value,
        event_type="MigrationProvenanceRecorded", expected_version=None,
        command_type="RecordMigrationProvenance",
    )


# =================================================================================================
# registerDataClass() -- DATA-FR-001 / DATA-FR-021 / DATA-FR-027. Creates or supersedes a
# data_ownership_registry entry. No HTTP endpoint (data-governance entry point); the baseline set is
# seeded from 05_DATABASE_OWNERSHIP_MATRIX.md.
# =================================================================================================


class RegisterDataClassCommand(CommandEnvelope):
    entity_type: str
    authoritative_service: str
    authoritative_store: str
    projection_targets: list = []
    tenant_scoped: bool = False
    site_scoped: bool = False
    classification: str = "GXP"
    retention_policy_id: uuid.UUID | None = None
    encryption_profile_id: uuid.UUID | None = None
    source_reference: str | None = None
    expected_version: int | None = None
    reason: str


async def register_data_class(
    session: AsyncSession, cmd: RegisterDataClassCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.entity_type or not cmd.authoritative_service or not cmd.reason:
        raise ValidationFailedError("entity_type, authoritative_service and reason are required")
    if cmd.authoritative_store not in AUTHORITATIVE_STORES:
        raise ValidationFailedError(f"authoritative_store must be one of {sorted(AUTHORITATIVE_STORES)}")
    if cmd.classification not in DATA_CLASSIFICATIONS:
        raise ValidationFailedError(f"classification must be one of {sorted(DATA_CLASSIFICATIONS)}")
    for tier in cmd.projection_targets:
        if tier not in PROJECTION_TIERS:
            raise ValidationFailedError(f"projection tier {tier!r} must be one of {sorted(PROJECTION_TIERS)}")

    row = (
        await session.execute(
            select(DataOwnershipRegistry).where(DataOwnershipRegistry.entity_type == cmd.entity_type)
        )
    ).scalar_one_or_none()

    created = row is None
    old_value = None
    if created:
        row = DataOwnershipRegistry(
            entity_type=cmd.entity_type, authoritative_service=cmd.authoritative_service,
            authoritative_store=cmd.authoritative_store, projection_targets=cmd.projection_targets,
            tenant_scoped=cmd.tenant_scoped, site_scoped=cmd.site_scoped,
            classification=cmd.classification, retention_policy_id=cmd.retention_policy_id,
            encryption_profile_id=cmd.encryption_profile_id, source_reference=cmd.source_reference,
            state="EFFECTIVE", version=1,
        )
        session.add(row)
    else:
        # The unique constraint is on entity_type alone, so an update is in place; the superseding
        # history for this CONFIG entity lives in the audit ledger (AG-08), same treatment as the
        # security catalogue rows. optimistic-version guarded.
        if cmd.expected_version is None or row.version != cmd.expected_version:
            raise StaleVersionError(
                "data_ownership_registry entry changed since this request was prepared",
                current_version=row.version,
            )
        old_value = {
            "authoritative_service": row.authoritative_service,
            "authoritative_store": row.authoritative_store,
            "projection_targets": row.projection_targets,
            "classification": row.classification, "version": row.version,
        }
        row.authoritative_service = cmd.authoritative_service
        row.authoritative_store = cmd.authoritative_store
        row.projection_targets = cmd.projection_targets
        row.tenant_scoped = cmd.tenant_scoped
        row.site_scoped = cmd.site_scoped
        row.classification = cmd.classification
        row.retention_policy_id = cmd.retention_policy_id
        row.encryption_profile_id = cmd.encryption_profile_id
        row.source_reference = cmd.source_reference
        row.state = "EFFECTIVE"
        row.version += 1
    await session.flush()

    new_value = {
        "entity_type": row.entity_type, "authoritative_service": row.authoritative_service,
        "authoritative_store": row.authoritative_store, "projection_targets": row.projection_targets,
        "classification": row.classification, "version": row.version,
    }
    return await _finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="data_ownership_registry",
        aggregate_id=row.id, version=row.version, action="Created" if created else "Changed",
        actor_user_id=actor_user_id, reason=cmd.reason, old_value=old_value, new_value=new_value,
        event_type="DataClassRegistered",
        expected_version=None if created else cmd.expected_version, command_type="RegisterDataClass",
    )
