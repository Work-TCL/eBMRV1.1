"""Document 39 (SPEC-EQP-002) — exactly the 7 declared operations (§6). `equipment_area` and
`cleaning_procedure_version` are seed-only master data (no create/release endpoint in the declared list),
same precedent as `material.WarehouseLocation`.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.equipment import commands as equipment_commands
from app.modules.equipment.cleaning_models import (
    LINE_CLEARANCE_STATES,
    CleaningExecution,
    CleaningProcedureVersion,
    EquipmentArea,
    LineClearance,
)
from app.modules.equipment.models import EquipmentAsset
from app.modules.equipment.sterilization_models import ProcessCycle
from app.modules.iam.models import User
from app.modules.qc import commands as qc_commands
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
    WrongEquipmentInstalledError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def cleaning_record_hash(execution: CleaningExecution) -> str:
    return sha256_hex({"id": str(execution.id), "version": execution.version, "state": execution.state})


def line_clearance_record_hash(clearance: LineClearance) -> str:
    return sha256_hex({"id": str(clearance.id), "version": clearance.version, "state": clearance.state})


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
        audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _write_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, site_id: uuid.UUID,
    aggregate_type: str, aggregate_id: uuid.UUID, version: int, action: str, actor_user_id: uuid.UUID,
    reason: str | None, old_state: str | None, event_type: str, event_payload: dict,
    expected_version: int | None, command_type: str, signature_id: uuid.UUID | None = None,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=site_id, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state} if old_state else None,
        new_value=event_payload, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=site_id, command_type=command_type, aggregate_type=aggregate_type,
        aggregate_id=aggregate_id, expected_version=expected_version, resulting_version=version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=aggregate_id, resulting_version=version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


async def _resolve_signature(
    session: AsyncSession, *, record_type: str, action: str, actor_user_id: uuid.UUID,
    record_version: int, record_hash: str, challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type=record_type, action=action)
    if not policy.signature_required:
        return None
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"{record_type} '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=record_version, record_hash=record_hash,
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


async def _load_execution_for_update(session: AsyncSession, execution_id: uuid.UUID, expected_version: int) -> CleaningExecution:
    result = await session.execute(select(CleaningExecution).where(CleaningExecution.id == execution_id).with_for_update())
    execution = result.scalar_one_or_none()
    if execution is None:
        raise NotFoundError("Cleaning execution not found")
    if execution.version != expected_version:
        raise StaleVersionError(
            "Cleaning execution was modified by another actor since it was read",
            expected_version=expected_version, current_version=execution.version,
        )
    return execution


async def _mirror_cleanliness(session: AsyncSession, execution: CleaningExecution, status: str) -> None:
    """CLN-FR-027: the cleaning_execution lifecycle is where equipment_asset.cleanliness_status /
    equipment_area.cleanliness_status (captured-only since Document 38, SG-113) becomes real."""
    if execution.equipment_id is not None:
        asset = await session.get(EquipmentAsset, execution.equipment_id)
        if asset is not None:
            asset.cleanliness_status = status
    if execution.area_id is not None:
        area = await session.get(EquipmentArea, execution.area_id)
        if area is not None:
            area.cleanliness_status = status


# ---------------------------------------------------------------------------
# CreateCleaningExecution — CLN-FR-003/004/005/006/007. Represents "equipment/area is dirty and cleaning
# has started" in one step -- no separate "mark dirty" endpoint exists in the declared 7-op API list.
# ---------------------------------------------------------------------------


class CreateCleaningExecutionCommand(CommandEnvelope):
    site_id: uuid.UUID
    equipment_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    procedure_version_id: uuid.UUID
    batch_context: dict | None = None
    dirty_since: datetime | None = None
    critical: bool = False
    sterilization_cycle_id: uuid.UUID | None = None


# CLN-FR-006: states in which a cleaning is actively underway and not yet resolved. HOLD is deliberately
# excluded -- per Document 39's own state model (ANY -> HOLD, no separate "resume from hold" operation in
# the declared 7-op API), the only path off HOLD is a fresh CreateCleaningExecution re-attempt, so blocking
# creation while HOLD would make a held equipment/area permanently unrecoverable.
_ACTIVE_CLEANING_STATES = ("CLEANING", "CLEANING_VERIFICATION")


async def create_cleaning_execution(
    session: AsyncSession, cmd: CreateCleaningExecutionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if (cmd.equipment_id is None) == (cmd.area_id is None):
        raise ValidationFailedError("Exactly one of equipment_id or area_id must be set")

    procedure = await session.get(CleaningProcedureVersion, cmd.procedure_version_id)
    if procedure is None:
        raise NotFoundError("Cleaning procedure version not found")

    # CLN-FR-006: equipment/area is "unavailable for use" while a cleaning is in progress -- a second
    # concurrent cleaning attempt on the same equipment/area is a duplicate-execution race, not a valid
    # parallel action.
    scope_column = CleaningExecution.equipment_id if cmd.equipment_id is not None else CleaningExecution.area_id
    scope_value = cmd.equipment_id if cmd.equipment_id is not None else cmd.area_id
    active = (
        await session.execute(
            select(CleaningExecution).where(
                scope_column == scope_value, CleaningExecution.state.in_(_ACTIVE_CLEANING_STATES)
            )
        )
    ).scalar_one_or_none()
    if active is not None:
        raise ValidationFailedError(
            "A cleaning execution is already active for this equipment/area",
            active_execution_id=str(active.id), active_state=active.state,
        )

    if cmd.sterilization_cycle_id is not None:
        cycle = await session.get(ProcessCycle, cmd.sterilization_cycle_id)
        if cycle is None:
            raise NotFoundError("Sterilization/CIP-SIP process cycle not found")

    execution = CleaningExecution(
        site_id=cmd.site_id, equipment_id=cmd.equipment_id, area_id=cmd.area_id,
        procedure_version_id=cmd.procedure_version_id, batch_context=cmd.batch_context,
        critical=cmd.critical, state="CLEANING", dirty_since=cmd.dirty_since or datetime.now(timezone.utc),
        sterilization_cycle_id=cmd.sterilization_cycle_id,
        performer_user_id=actor_user_id, version=1,
    )
    session.add(execution)
    await session.flush()
    await _mirror_cleanliness(session, execution, "CLEANING")

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="cleaning_execution",
        aggregate_id=execution.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="CleaningStarted",
        event_payload={"id": str(execution.id), "state": execution.state}, expected_version=None,
        command_type="CreateCleaningExecution",
    )


# ---------------------------------------------------------------------------
# RecordCleaningStep — CLN-FR-007/008. Append-only progress capture.
# ---------------------------------------------------------------------------


class RecordCleaningStepCommand(CommandEnvelope):
    execution_id: uuid.UUID
    expected_version: int
    step: dict
    agents_used: dict | None = None
    disassembly_verified: bool | None = None


async def record_cleaning_step(
    session: AsyncSession, cmd: RecordCleaningStepCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    execution = await _load_execution_for_update(session, cmd.execution_id, cmd.expected_version)
    if execution.state != "CLEANING":
        raise InvalidTransitionError("Steps can only be recorded while cleaning is in progress", current_state=execution.state)

    steps = list(execution.steps_log or [])
    steps.append({**cmd.step, "recorded_at": datetime.now(timezone.utc).isoformat(), "recorded_by": str(actor_user_id)})
    execution.steps_log = steps
    if cmd.agents_used is not None:
        execution.agents_used = {**(execution.agents_used or {}), **cmd.agents_used}
    if cmd.disassembly_verified is not None:
        execution.disassembly_verified = cmd.disassembly_verified
    execution.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=execution.site_id, aggregate_type="cleaning_execution",
        aggregate_id=execution.id, version=execution.version, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=execution.state, event_type="CleaningStarted",
        event_payload={"id": str(execution.id), "step_count": len(steps)}, expected_version=cmd.expected_version,
        command_type="RecordCleaningStep",
    )


# ---------------------------------------------------------------------------
# CompleteCleaning — Document 106 row 109. `reason` required only when `critical` (application-level,
# since SignaturePolicy.reason_required is a flat boolean).
# ---------------------------------------------------------------------------


class CompleteCleaningCommand(CommandEnvelope):
    execution_id: uuid.UUID
    expected_version: int
    previous_batch_identity_removed: bool
    inspection_result: dict | None = None
    protection_state: dict | None = None
    reason: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def complete_cleaning(
    session: AsyncSession, cmd: CompleteCleaningCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    execution = await _load_execution_for_update(session, cmd.execution_id, cmd.expected_version)
    if execution.state != "CLEANING":
        raise InvalidTransitionError("Only an in-progress cleaning can be completed", current_state=execution.state)
    if execution.critical and not cmd.reason:
        raise ValidationFailedError("reason is required to complete a cleaning execution flagged critical")

    signature_id = await _resolve_signature(
        session, record_type="cleaning_execution", action="complete", actor_user_id=actor_user_id,
        record_version=execution.version, record_hash=cleaning_record_hash(execution),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = execution.state
    execution.previous_batch_identity_removed = cmd.previous_batch_identity_removed
    execution.inspection_result = cmd.inspection_result
    # CLN-FR-014: captured as recorded (cover/closure/storage state) -- not gated/enforced, no controlled
    # vocabulary exists for it (see cleaning_models.CleaningExecution docstring).
    if cmd.protection_state is not None:
        execution.protection_state = cmd.protection_state
    execution.performer_user_id = actor_user_id
    execution.state = "CLEANING_VERIFICATION"
    execution.version += 1
    await _mirror_cleanliness(session, execution, "CLEANING_VERIFICATION")

    # CLN-FR-010: where the released procedure calls for swab/rinse sampling, create the QC sample now
    # (once, idempotent on execution.swab_sample_id) -- matches material.commands.collect_sample()'s
    # existing precedent for calling into the qc module. Spec/limit resolution against the sample is QC's
    # own normal workflow, not reinvented here.
    procedure = await session.get(CleaningProcedureVersion, execution.procedure_version_id)
    if procedure is not None and procedure.sample_inspection_requirements and execution.swab_sample_id is None:
        requirements = procedure.sample_inspection_requirements
        sample_receipt = await qc_commands.create_sample(
            session,
            qc_commands.CreateSampleCommand(
                idempotency_key=str(uuid.uuid4()),
                sample_number=f"CLN-{execution.id.hex[:8]}",
                sample_type="cleaning_verification",
                source_type="cleaning_execution",
                source_id=execution.id,
                source_location_ref=requirements.get("location") if isinstance(requirements, dict) else None,
                sampled_at=datetime.now(timezone.utc),
            ),
            actor_user_id,
        )
        execution.swab_sample_id = sample_receipt.aggregate_id

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=execution.site_id, aggregate_type="cleaning_execution",
        aggregate_id=execution.id, version=execution.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="CleaningCompleted",
        event_payload={"id": str(execution.id), "state": execution.state}, expected_version=cmd.expected_version,
        command_type="CompleteCleaning", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------
# VerifyCleaning — Document 106 row 110. Independent verifier (MUST NOT be the performer). A failed
# verification is a valid, signed outcome (state -> HOLD, requires_deviation) -- never silently overwritten
# by a later successful repeat, and the original result is retained (Codex rule §15).
# ---------------------------------------------------------------------------


class VerifyCleaningCommand(CommandEnvelope):
    execution_id: uuid.UUID
    expected_version: int
    result: str  # "pass" | "fail"
    reason: str | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def verify_cleaning(
    session: AsyncSession, cmd: VerifyCleaningCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.result not in ("pass", "fail"):
        raise ValidationFailedError("result must be 'pass' or 'fail'")

    execution = await _load_execution_for_update(session, cmd.execution_id, cmd.expected_version)
    if execution.state != "CLEANING_VERIFICATION":
        raise InvalidTransitionError("Only a cleaning pending verification can be verified", current_state=execution.state)
    if execution.performer_user_id == actor_user_id:
        raise ValidationFailedError("Verifier must be independent of the performer (SIG-FR-018)")

    signature_id = await _resolve_signature(
        session, record_type="cleaning_execution", action="verify", actor_user_id=actor_user_id,
        record_version=execution.version, record_hash=cleaning_record_hash(execution),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = execution.state
    execution.reviewer_user_id = actor_user_id
    execution.verification_result = cmd.result
    execution.completed_at = datetime.now(timezone.utc)

    procedure = await session.get(CleaningProcedureVersion, execution.procedure_version_id)
    dirty_limit = procedure.dirty_hold_limit_minutes if procedure else None
    if dirty_limit is not None:
        elapsed_minutes = (execution.completed_at - execution.dirty_since).total_seconds() / 60
        execution.dirty_hold_exceeded = elapsed_minutes > dirty_limit

    if cmd.result == "fail":
        execution.state = "HOLD"
        execution.requires_deviation = True
        event_type = "CleaningVerificationFailed"
        await _mirror_cleanliness(session, execution, "HOLD")
    else:
        execution.state = "CLEAN"
        clean_limit = procedure.clean_hold_limit_minutes if procedure else None
        execution.clean_until = (
            execution.completed_at + timedelta(minutes=clean_limit) if clean_limit is not None else None
        )
        if execution.dirty_hold_exceeded:
            execution.requires_deviation = True
        event_type = "EquipmentMarkedClean"
        await _mirror_cleanliness(session, execution, "CLEAN")
    execution.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=execution.site_id, aggregate_type="cleaning_execution",
        aggregate_id=execution.id, version=execution.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type=event_type,
        event_payload={"id": str(execution.id), "state": execution.state, "result": cmd.result},
        expected_version=cmd.expected_version, command_type="VerifyCleaning", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------
# CreateLineClearance / CompleteLineClearance — CLN-FR-016..023. Document 106 row 111.
# ---------------------------------------------------------------------------


class CreateLineClearanceCommand(CommandEnvelope):
    site_id: uuid.UUID
    area_id: uuid.UUID | None = None
    previous_batch_id: uuid.UUID | None = None
    next_batch_id: uuid.UUID | None = None
    checklist_version: str | None = None
    # dict | list: the model's own docstring never fixed a shape for this JSONB field (LineClearance.items)
    # before this pass -- CLN-FR-019's list-of-checklist-item convention (see
    # _check_equipment_items_eligible()) needs a list; the pre-existing dict-shaped free-form checklist
    # convention (e.g. {"labels_removed": true}) stays valid too.
    items: dict | list | None = None
    critical: bool = False


async def create_line_clearance(
    session: AsyncSession, cmd: CreateLineClearanceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    clearance = LineClearance(
        site_id=cmd.site_id, area_id=cmd.area_id, previous_batch_id=cmd.previous_batch_id,
        next_batch_id=cmd.next_batch_id, checklist_version=cmd.checklist_version, items=cmd.items,
        critical=cmd.critical, performer_user_id=actor_user_id, state="IN_PROGRESS", version=1,
    )
    session.add(clearance)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="line_clearance",
        aggregate_id=clearance.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="LineClearanceStarted",
        event_payload={"id": str(clearance.id), "state": clearance.state}, expected_version=None,
        command_type="CreateLineClearance",
    )


async def _check_equipment_items_eligible(session: AsyncSession, items: dict | None) -> None:
    """CLN-FR-019: cross-check that any equipment-type checklist item is currently qualified/calibrated/
    maintenance-clear/not-on-hold (Document 38's own `get_eligibility()`) and clean (read directly from
    `EquipmentAsset.cleanliness_status`, since Document 38's eligibility check evaluates a different set of
    gates -- see the EQP-FR-025/SG-110 note in equipment/commands.py). `items` had no consumer anywhere in
    this codebase before this pass (`LineClearance.items` docstring: captured JSONB, no shape enforced) --
    this is the first real reader, so it also defines the convention: a list of dicts, each carrying
    `item_type` ("material" | "label" | "equipment") and, for `item_type == "equipment"`, an
    `equipment_id`. Anything not matching that shape (including non-list `items`) is left alone; only
    genuine equipment items are checked, and material/label reconciliation stays unbuilt (SPEC_GAP,
    LineClearance docstring).
    """
    if not isinstance(items, list):
        return
    for item in items:
        if not isinstance(item, dict) or item.get("item_type") != "equipment":
            continue
        equipment_id = item.get("equipment_id")
        if not equipment_id:
            continue
        asset_id = uuid.UUID(str(equipment_id))
        asset = await session.get(EquipmentAsset, asset_id)
        if asset is None:
            raise WrongEquipmentInstalledError(
                "Line clearance references an unknown equipment asset", equipment_id=str(asset_id),
            )
        eligibility = await equipment_commands.get_eligibility(session, asset_id)
        if not eligibility["eligible"]:
            raise WrongEquipmentInstalledError(
                "Equipment installed for this line clearance is not currently eligible",
                equipment_id=str(asset_id), reasons=eligibility["reasons"],
            )
        if asset.cleanliness_status is not None and asset.cleanliness_status not in ("CLEAN", "READY_FOR_USE"):
            raise WrongEquipmentInstalledError(
                "Equipment installed for this line clearance is not in a clean/ready state",
                equipment_id=str(asset_id), cleanliness_status=asset.cleanliness_status,
            )


class CompleteLineClearanceCommand(CommandEnvelope):
    clearance_id: uuid.UUID
    expected_version: int
    passed: bool
    expiry_at: datetime | None = None
    reason: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def complete_line_clearance(
    session: AsyncSession, cmd: CompleteLineClearanceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(LineClearance).where(LineClearance.id == cmd.clearance_id).with_for_update())
    clearance = result.scalar_one_or_none()
    if clearance is None:
        raise NotFoundError("Line clearance not found")
    if clearance.version != cmd.expected_version:
        raise StaleVersionError(
            "Line clearance was modified by another actor since it was read",
            expected_version=cmd.expected_version, current_version=clearance.version,
        )
    if clearance.state not in ("IN_PROGRESS", "VERIFICATION_PENDING"):
        raise InvalidTransitionError("Only an in-progress line clearance can be completed", current_state=clearance.state)
    if clearance.critical and not cmd.reason:
        raise ValidationFailedError("reason is required to complete a line clearance flagged critical")
    if cmd.passed:
        # CLN-FR-019: only enforced on the path that would actually clear the line -- a caller failing
        # their own clearance (cmd.passed=False) needs no additional gate.
        await _check_equipment_items_eligible(session, clearance.items)

    signature_id = await _resolve_signature(
        session, record_type="line_clearance", action="complete", actor_user_id=actor_user_id,
        record_version=clearance.version, record_hash=line_clearance_record_hash(clearance),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = clearance.state
    clearance.verifier_user_id = actor_user_id
    clearance.state = "CLEARED" if cmd.passed else "NOT_STARTED"
    clearance.expiry_at = cmd.expiry_at
    clearance.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=clearance.site_id, aggregate_type="line_clearance",
        aggregate_id=clearance.id, version=clearance.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state,
        event_type="LineClearanceCompleted" if cmd.passed else "LineClearanceFailed",
        event_payload={"id": str(clearance.id), "state": clearance.state}, expected_version=cmd.expected_version,
        command_type="CompleteLineClearance", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------
# Read query — GET /cleaning/v1/equipment/{id}/status. Clean-hold expiry is computed on read (no
# background scheduler exists in this codebase, SPEC_GAP), never persisted speculatively.
# ---------------------------------------------------------------------------


async def get_equipment_cleaning_status(session: AsyncSession, equipment_id: uuid.UUID) -> dict:
    asset = await session.get(EquipmentAsset, equipment_id)
    if asset is None:
        raise NotFoundError("Equipment asset not found")
    result = await session.execute(
        select(CleaningExecution)
        .where(CleaningExecution.equipment_id == equipment_id)
        .order_by(CleaningExecution.created_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    effective_status = asset.cleanliness_status
    if latest is not None and latest.state == "CLEAN" and latest.clean_until is not None:
        if datetime.now(timezone.utc) > latest.clean_until.replace(tzinfo=timezone.utc):
            effective_status = "CLEAN_EXPIRED"
    return {
        "equipment_id": str(equipment_id),
        "cleanliness_status": effective_status,
        "latest_execution_id": str(latest.id) if latest else None,
        "latest_execution_state": latest.state if latest else None,
        "clean_until": latest.clean_until.isoformat() if latest and latest.clean_until else None,
    }


# ---------------------------------------------------------------------------
# Read query added to serve Document 40 (SPEC-EQP-003) ASP-FR-006's readiness composition -- not one of
# Document 39's own 7 declared operations, same precedent as em_commands.get_area_readiness() (added to
# EM to serve the same cross-module payoff).
# ---------------------------------------------------------------------------


async def get_area_line_clearance_status(session: AsyncSession, area_id: uuid.UUID) -> dict:
    result = await session.execute(
        select(LineClearance)
        .where(LineClearance.area_id == area_id)
        .order_by(LineClearance.created_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    effective_state = latest.state if latest else "NOT_STARTED"
    if latest is not None and latest.state == "CLEARED" and latest.expiry_at is not None:
        if datetime.now(timezone.utc) > latest.expiry_at.replace(tzinfo=timezone.utc):
            effective_state = "EXPIRED"
    return {
        "area_id": str(area_id),
        "state": effective_state,
        "cleared": effective_state == "CLEARED",
        "latest_line_clearance_id": str(latest.id) if latest else None,
    }
