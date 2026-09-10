"""Document 76 (SPEC-DATA-008) Mutation Gateway command handlers. No signature anywhere (Document 106
has no SPEC-DATA-008 row) -- RBAC-gated + mandatory reason, same precedent as every other unsigned
module in this codebase.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.disaster_recovery.models import (
    BACKUP_TYPES,
    RECOVERY_TIERS,
    BackupInventory,
    RecoveryObjectiveProfile,
    RestoreTest,
)
from app.mutation.errors import NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version, audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _finalize(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, aggregate_type: str,
    aggregate_id: uuid.UUID, version: int, action: str, actor_user_id: uuid.UUID, reason: str | None,
    old_value: dict | None, new_value: dict, event_type: str, expected_version: int | None, command_type: str,
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
# createRecoveryObjectiveProfile() -- DR-FR-001/002/009
# =================================================================================================


class CreateRecoveryObjectiveProfileCommand(CommandEnvelope):
    component: str
    tier: str
    rpo_seconds: int | None = None
    rto_seconds: int
    approved_by: str
    expected_version: int | None = None
    reason: str


async def create_recovery_objective_profile(
    session: AsyncSession, cmd: CreateRecoveryObjectiveProfileCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.tier not in RECOVERY_TIERS:
        raise ValidationFailedError(f"tier must be one of {RECOVERY_TIERS}")
    if cmd.rto_seconds < 0 or (cmd.rpo_seconds is not None and cmd.rpo_seconds < 0):
        raise ValidationFailedError("rpo_seconds/rto_seconds must be >= 0")
    if not cmd.component or not cmd.approved_by or not cmd.reason:
        raise ValidationFailedError("component, approved_by and reason are required")

    row = (
        await session.execute(select(RecoveryObjectiveProfile).where(RecoveryObjectiveProfile.component == cmd.component))
    ).scalar_one_or_none()
    created = row is None
    old_value = None
    if created:
        row = RecoveryObjectiveProfile(
            component=cmd.component, tier=cmd.tier, rpo_seconds=cmd.rpo_seconds, rto_seconds=cmd.rto_seconds,
            approved_by=cmd.approved_by, state="EFFECTIVE", version=1,
        )
        session.add(row)
    else:
        if cmd.expected_version is None or row.version != cmd.expected_version:
            raise StaleVersionError("Recovery objective profile changed since this request was prepared",
                                    current_version=row.version)
        old_value = {"tier": row.tier, "rpo_seconds": row.rpo_seconds, "rto_seconds": row.rto_seconds}
        row.tier = cmd.tier
        row.rpo_seconds = cmd.rpo_seconds
        row.rto_seconds = cmd.rto_seconds
        row.approved_by = cmd.approved_by
        row.version += 1
    await session.flush()

    new_value = {"component": row.component, "tier": row.tier, "rpo_seconds": row.rpo_seconds,
                 "rto_seconds": row.rto_seconds, "approved_by": row.approved_by}
    return await _finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="recovery_objective_profile",
        aggregate_id=row.id, version=row.version, action="Created" if created else "Changed",
        actor_user_id=actor_user_id, reason=cmd.reason, old_value=old_value, new_value=new_value,
        event_type="RecoveryObjectiveConfigured", expected_version=None if created else cmd.expected_version,
        command_type="CreateRecoveryObjectiveProfile",
    )


# =================================================================================================
# recordBackupExecution() -- DR-FR-005/013/015. No HTTP endpoint (DR-automation entry point, same
# "internal, no independent API" shape as evidence provider-migration / dataops migration-provenance).
# =================================================================================================


class RecordBackupExecutionCommand(CommandEnvelope):
    component: str
    backup_type: str
    started_at: datetime
    completed_at: datetime | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    manifest_ref: str | None = None
    encrypted: bool = True
    status: str = "SUCCESS"
    reason: str


async def record_backup_execution(
    session: AsyncSession, cmd: RecordBackupExecutionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.backup_type not in BACKUP_TYPES:
        raise ValidationFailedError(f"backup_type must be one of {BACKUP_TYPES}")
    if cmd.status == "SUCCESS" and not cmd.checksum:
        raise ValidationFailedError("checksum is required for a SUCCESS backup record (DR-FR-005)")

    row = BackupInventory(
        component=cmd.component, backup_type=cmd.backup_type, started_at=cmd.started_at,
        completed_at=cmd.completed_at, size_bytes=cmd.size_bytes, checksum=cmd.checksum,
        manifest_ref=cmd.manifest_ref, encrypted=cmd.encrypted, status=cmd.status, version=1,
    )
    session.add(row)
    await session.flush()

    new_value = {"backup_id": str(row.id), "component": row.component, "backup_type": row.backup_type,
                 "status": row.status, "encrypted": row.encrypted}
    return await _finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="backup_inventory", aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=cmd.reason, old_value=None,
        new_value=new_value, event_type="BackupRecorded", expected_version=None, command_type="RecordBackupExecution",
    )


# =================================================================================================
# executePostgresRestoreTest() -- DR-FR-016/017/030
# =================================================================================================


class ExecutePostgresRestoreTestCommand(CommandEnvelope):
    backup_id: uuid.UUID
    target_environment: str
    pitr_target: datetime | None = None
    started_at: datetime
    completed_at: datetime
    integrity_checks: dict
    evidence_ref: str | None = None
    reason: str


async def execute_postgres_restore_test(
    session: AsyncSession, cmd: ExecutePostgresRestoreTestCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    backup = await session.get(BackupInventory, cmd.backup_id)
    if backup is None:
        raise NotFoundError("Backup inventory row not found")
    if not cmd.integrity_checks:
        raise ValidationFailedError("integrity_checks must record at least one check")
    if cmd.completed_at < cmd.started_at:
        raise ValidationFailedError("completed_at must not precede started_at")

    objective = (
        await session.execute(
            select(RecoveryObjectiveProfile).where(RecoveryObjectiveProfile.component == backup.component)
        )
    ).scalar_one_or_none()

    rto_achieved = int((cmd.completed_at - cmd.started_at).total_seconds())
    if cmd.pitr_target is not None:
        # A successful PITR recovery lands exactly at its chosen target -- zero *additional* loss
        # beyond that target (whether the target itself was recent enough is a separate question for
        # recordDataLossAssessment(), not this measurement).
        rpo_achieved = 0
    elif backup.completed_at:
        # Base-backup-only restore (no PITR): everything committed after the backup completed is
        # genuinely lost -- the backup's own staleness at restore time IS the achieved RPO.
        rpo_achieved = max(0, int((cmd.started_at - backup.completed_at).total_seconds()))
    else:
        rpo_achieved = None

    checks_passed = all(bool(v) for v in cmd.integrity_checks.values())
    rto_ok = objective is None or objective.rto_seconds is None or rto_achieved <= objective.rto_seconds
    rpo_ok = (
        objective is None or objective.rpo_seconds is None or rpo_achieved is None
        or rpo_achieved <= objective.rpo_seconds
    )
    result = "PASS" if (checks_passed and rto_ok and rpo_ok) else "FAIL"

    row = RestoreTest(
        backup_id=cmd.backup_id, target_environment=cmd.target_environment, pitr_target=cmd.pitr_target,
        started_at=cmd.started_at, completed_at=cmd.completed_at, rpo_achieved_seconds=rpo_achieved,
        rto_achieved_seconds=rto_achieved, integrity_checks=cmd.integrity_checks, result=result,
        evidence_ref=cmd.evidence_ref, version=1,
    )
    session.add(row)
    await session.flush()

    new_value = {
        "restore_test_id": str(row.id), "backup_id": str(cmd.backup_id), "result": result,
        "rpo_achieved_seconds": rpo_achieved, "rto_achieved_seconds": rto_achieved,
        "target_environment": cmd.target_environment,
    }
    return await _finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="restore_test", aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=cmd.reason, old_value=None,
        new_value=new_value,
        event_type="PostgresRestoreTestCompleted" if result == "PASS" else "RestoreTestFailed",
        expected_version=None, command_type="ExecutePostgresRestoreTest",
    )
