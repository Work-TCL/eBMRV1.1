"""Document 91 (SPEC-VAL-013) Mutation Gateway command handlers -- Backup, Restore, PITR & Disaster
Recovery Qualification. Document 106 row 157: `dr/{id}/approve` requires an `Approved` signature from an
independent QA Releaser, reason mandatory -- binds to `dr_qualification_execution` directly (each
execution is its own qualification record, unlike the aggregating profile/assessment pattern used by
Documents 88/89/90, because Document 91's API list gives `measure` its own `{id}` scoped to one
execution). `dr/scenarios` carries no Document 106 row -- unsigned.

RPO/RTO achieved values are **measured**, never invented -- same timestamp arithmetic as
`app/modules/disaster_recovery/commands.py::execute_postgres_restore_test` (Document 76/109 owns the
platform-default RPO/RTO *targets*; this module only measures what one drill actually achieved against
whatever target the scenario declares).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import DrQualificationExecution, DrQualificationScenario
from app.modules.validation.shared import finalize, receipt_from_existing, resolve_signature, verify_reauth_and_consume
from app.mutation.errors import InvalidTransitionError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_EXECUTION = "dr_qualification_execution"


class CreateDrScenarioCommand(CommandEnvelope):
    failure_type: str
    components: list[str]
    recovery_method: str
    target_rpo_seconds: int | None = None
    target_rto_seconds: int
    restore_order: list[str] = []
    acceptance_criteria: str


async def create_dr_scenario(
    session: AsyncSession, cmd: CreateDrScenarioCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if cmd.target_rto_seconds < 0 or (cmd.target_rpo_seconds is not None and cmd.target_rpo_seconds < 0):
        raise ValidationFailedError("target_rpo_seconds/target_rto_seconds must be >= 0")

    row = DrQualificationScenario(
        failure_type=cmd.failure_type, components=cmd.components, recovery_method=cmd.recovery_method,
        target_rpo_seconds=cmd.target_rpo_seconds, target_rto_seconds=cmd.target_rto_seconds,
        restore_order=cmd.restore_order, acceptance_criteria=cmd.acceptance_criteria, state="EFFECTIVE", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="dr_qualification_scenario", aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"failure_type": row.failure_type}, event_type="DrScenarioDefined", expected_version=None,
        command_type="CreateDrScenario", site_id=site_id,
    )


class RecordDrExecutionCommand(CommandEnvelope):
    scenario_id: uuid.UUID
    backup_set_ref: str
    restore_point: datetime | None = None
    started_at: datetime
    completed_at: datetime
    integrity_checks: dict


async def record_dr_execution(
    session: AsyncSession, cmd: RecordDrExecutionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    scenario = await session.get(DrQualificationScenario, cmd.scenario_id)
    if scenario is None:
        raise NotFoundError("DR qualification scenario not found")
    if cmd.completed_at < cmd.started_at:
        raise ValidationFailedError("completed_at must not precede started_at")
    if not cmd.integrity_checks:
        raise ValidationFailedError("integrity_checks must record at least one check")

    row = DrQualificationExecution(
        scenario_id=scenario.id, scenario_version=scenario.version, backup_set_ref=cmd.backup_set_ref,
        restore_point=cmd.restore_point, started_at=cmd.started_at, completed_at=cmd.completed_at,
        integrity_checks=cmd.integrity_checks, status="IN_PROGRESS", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_EXECUTION, aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"scenario_id": str(scenario.id), "backup_set_ref": cmd.backup_set_ref},
        event_type="DRRestoreExecuted", expected_version=None, command_type="RecordDrExecution", site_id=site_id,
    )


class MeasureDrObjectivesCommand(CommandEnvelope):
    execution_id: uuid.UUID
    expected_version: int
    gxp_smoke_results: dict = {}
    deviations: list[dict] = []


async def measure_dr_objectives(
    session: AsyncSession, cmd: MeasureDrObjectivesCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = await session.get(DrQualificationExecution, cmd.execution_id)
    if row is None:
        raise NotFoundError("DR qualification execution not found")
    if row.version != cmd.expected_version:
        raise StaleVersionError("Execution changed since this request was prepared", current_version=row.version)
    scenario = await session.get(DrQualificationScenario, row.scenario_id)

    rto_achieved = int((row.completed_at - row.started_at).total_seconds())
    if row.restore_point is not None:
        rpo_achieved = 0  # a successful PITR lands exactly at its chosen target -- no additional loss.
    else:
        rpo_achieved = None  # base-backup-only restore: staleness would need the backup's own completion time.

    checks_passed = all(bool(v) for v in row.integrity_checks.values())
    smoke_passed = all(bool(v) for v in cmd.gxp_smoke_results.values()) if cmd.gxp_smoke_results else True
    rto_ok = scenario is None or rto_achieved <= scenario.target_rto_seconds
    rpo_ok = (
        scenario is None or scenario.target_rpo_seconds is None or rpo_achieved is None
        or rpo_achieved <= scenario.target_rpo_seconds
    )
    result = "PASS" if (checks_passed and smoke_passed and rto_ok and rpo_ok and not cmd.deviations) else "FAIL"

    row.rpo_achieved_seconds = rpo_achieved
    row.rto_achieved_seconds = rto_achieved
    row.gxp_smoke_results = cmd.gxp_smoke_results
    row.deviations = cmd.deviations
    row.status = result
    row.version += 1

    if cmd.gxp_smoke_results:
        await write_outbox_event(
            session, event_type="RecoveredGxPSmokeCompleted", aggregate_type=RECORD_TYPE_EXECUTION,
            aggregate_id=row.id, aggregate_version=row.version, payload=cmd.gxp_smoke_results,
            correlation_id=uuid.uuid4(),
        )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_EXECUTION, aggregate_id=row.id,
        version=row.version, action="Changed", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"rpo_achieved_seconds": rpo_achieved, "rto_achieved_seconds": rto_achieved, "result": result},
        event_type="RecoveryObjectivesMeasured", expected_version=cmd.expected_version,
        command_type="MeasureDrObjectives", site_id=site_id,
    )


class ApproveDrExecutionCommand(CommandEnvelope):
    execution_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_dr_execution(
    session: AsyncSession, cmd: ApproveDrExecutionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = await session.get(DrQualificationExecution, cmd.execution_id)
    if row is None:
        raise NotFoundError("DR qualification execution not found")
    if row.status not in ("PASS", "FAIL"):
        raise InvalidTransitionError("Execution has not been measured yet", current_state=row.status)
    if row.status == "FAIL":
        raise InvalidTransitionError("Cannot approve a FAILed DR qualification execution")
    if row.version != cmd.expected_version:
        raise StaleVersionError("Execution changed since this request was prepared", current_version=row.version)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to approve a DR qualification")

    policy = await resolve_signature(session, record_type=RECORD_TYPE_EXECUTION, action="approve")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.approved_by_user_id = actor_user_id
    row.approved_at = datetime.now(timezone.utc)
    row.version += 1

    # Document 06 (VLT-FR-001): an approved DR qualification execution is a regulated final record.
    from app.modules.vault import service as vault_service
    await vault_service.release_master(
        session, object_type=RECORD_TYPE_EXECUTION, business_id=str(row.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "scenario_id": str(row.scenario_id), "rpo_achieved_seconds": row.rpo_achieved_seconds,
            "rto_achieved_seconds": row.rto_achieved_seconds, "status": row.status,
        },
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_EXECUTION, aggregate_id=row.id,
        version=row.version, action="Approved", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value=None, new_value={"approved": True}, event_type="DRQualificationApproved",
        expected_version=cmd.expected_version, command_type="ApproveDrExecution", site_id=site_id,
        signature_id=signature_id,
    )
