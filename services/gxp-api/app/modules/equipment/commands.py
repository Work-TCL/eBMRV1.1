"""Document 38 (SPEC-EQP-001) — exactly the 9 declared operations (§6), no invented endpoint. EQP-FR-022
(Change Control link) is folded into `record_maintenance`'s creation path rather than given its own
endpoint, for the same reason. EQP-FR-013/016 (use log / reservation) has no dedicated create endpoint
either — every mutating command below leaves its own `equipment_use_log` row, so the log stays complete
without a 10th operation.

State-machine design note (EQP-FR-030 "no status bypass"): `QUALIFIED_AVAILABLE` is written in exactly one
place — `return_to_service`, after it re-checks qualification/calibration/maintenance/hold evidence. Every
other completion path (`record_qualification(qualified=True)`, a passing `record_calibration`, a verified
maintenance work order) moves the asset to `VERIFICATION` and clears its own status field, but never sets
`QUALIFIED_AVAILABLE` itself. `get_eligibility` and `return_to_service` share one predicate function so the
two can never disagree.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.equipment.models import (
    CALIBRATION_RESULTS,
    MAINTENANCE_TYPES,
    EquipmentAsset,
    EquipmentCalibration,
    EquipmentUseLog,
    MaintenanceWorkOrder,
)
from app.modules.qms.change_commands import CreateChangeCommand, create_change
from app.modules.qms.change_models import CHANGE_CLASSIFICATIONS
from app.modules.signature import service as signature_service
from app.core.security import verify_password
from app.modules.iam.models import User
from app.mutation.errors import (
    CalibrationExpiredError,
    CalibrationOotImpactRequiredError,
    CleaningRequiredError,
    EquipmentNotQualifiedError,
    EquipmentOutOfServiceError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    PostMaintenanceVerificationRequiredError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

QUALIFIED_MARKER = "QUALIFIED"
RETURNABLE_STATES = ("SUSPENDED", "OUT_OF_SERVICE", "VERIFICATION", "MAINTENANCE_DUE", "CALIBRATION_DUE")


def equipment_record_hash(asset: EquipmentAsset) -> str:
    return sha256_hex({"id": str(asset.id), "version": asset.version, "state": asset.state})


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


async def _load_asset_for_update(session: AsyncSession, asset_id: uuid.UUID, expected_version: int) -> EquipmentAsset:
    result = await session.execute(select(EquipmentAsset).where(EquipmentAsset.id == asset_id).with_for_update())
    asset = result.scalar_one_or_none()
    if asset is None:
        raise NotFoundError("Equipment asset not found")
    if asset.version != expected_version:
        raise StaleVersionError(
            "Equipment asset was modified by another actor since it was read",
            expected_version=expected_version,
            current_version=asset.version,
        )
    if asset.state == "RETIRED":
        raise InvalidTransitionError("Equipment is retired and can no longer be modified", current_state=asset.state)
    return asset


def _ineligibility_reasons(asset: EquipmentAsset, today: date) -> list[tuple[str, str]]:
    """Shared predicate (EQP-FR-015/030): returns (stable_error_code, message) pairs. Empty means
    eligible. `return_to_service` raises on the first one; `get_eligibility` returns them all.

    Most-specific-first ordering, and `hold_source` distinguishes an explicit `hold_equipment` hold (which
    only a human `return_to_service` call can lift) from a calibration/maintenance-triggered hold (which
    `record_calibration`/`record_maintenance` already clear themselves once the underlying condition
    resolves -- see those functions) -- otherwise a caller would see a stale generic
    EQUIPMENT_OUT_OF_SERVICE reason even after the real problem was fixed.
    """
    reasons: list[tuple[str, str]] = []
    if asset.qualification_status != QUALIFIED_MARKER:
        reasons.append(("EQUIPMENT_NOT_QUALIFIED", "Equipment has no current qualification record"))
    if asset.qualification_expiry_date is not None and asset.qualification_expiry_date < today:
        reasons.append(("EQUIPMENT_NOT_QUALIFIED", "Qualification has expired"))
    if asset.calibration_status == "oot":
        reasons.append(("CALIBRATION_OOT_IMPACT_REQUIRED", "Most recent calibration was out of tolerance"))
    elif asset.calibration_status not in (None, "current"):
        reasons.append(("CALIBRATION_EXPIRED", "Calibration is due or overdue"))
    elif asset.next_calibration_due_date is not None and asset.next_calibration_due_date < today:
        reasons.append(("CALIBRATION_EXPIRED", "Calibration due date has passed"))
    if asset.maintenance_status == "pending_verification":
        reasons.append(("POST_MAINTENANCE_VERIFICATION_REQUIRED", "Maintenance was performed but not yet verified"))
    elif asset.maintenance_status == "in_progress":
        reasons.append(("POST_MAINTENANCE_VERIFICATION_REQUIRED", "Maintenance is in progress"))
    if asset.hold_flag and asset.hold_source == "manual":
        reasons.append(("EQUIPMENT_OUT_OF_SERVICE", asset.hold_reason or "Equipment is on hold"))
    # EQP-FR-025 / SG-110: Document 39 now exists and is the sole writer of cleanliness_status (via
    # cleaning_commands._mirror_cleanliness()) -- only gate on it for equipment this module's cleaning
    # workflow actually tracks; `None` means no cleaning execution has ever touched this asset (e.g. it
    # has no cleaning requirement at all), which must not be treated as "dirty" by default.
    if asset.cleanliness_status is not None and asset.cleanliness_status not in ("CLEAN", "READY_FOR_USE"):
        reasons.append((
            "CLEANING_REQUIRED",
            f"Equipment cleanliness status is {asset.cleanliness_status}, not clean/ready for use",
        ))
    return reasons


async def _write_use_log(
    session: AsyncSession, *, asset: EquipmentAsset, log_type: str, actor_user_id: uuid.UUID,
    event_reference: str | None = None,
) -> None:
    session.add(
        EquipmentUseLog(
            equipment_asset_id=asset.id,
            site_id=asset.site_id,
            log_type=log_type,
            operator_user_id=actor_user_id,
            source="manual",
            event_reference=event_reference,
        )
    )


async def _write_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, asset: EquipmentAsset, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=asset.site_id, aggregate_type="equipment_asset", aggregate_id=asset.id,
        aggregate_version=asset.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": asset.state},
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="equipment_asset", aggregate_id=asset.id,
        aggregate_version=asset.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=asset.site_id, command_type=command_type, aggregate_type="equipment_asset",
        aggregate_id=asset.id, expected_version=expected_version, resulting_version=asset.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=asset.id, resulting_version=asset.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CreateEquipmentAsset — EQP-FR-001/002/003/014/018/019/023. No dedicated "install" operation exists in
# the declared API list, so creation enters directly at INSTALLED (EquipmentInstalled event) rather than
# PLANNED — there is no command that would ever move it out of PLANNED otherwise.
# ---------------------------------------------------------------------------


class CreateEquipmentAssetCommand(CommandEnvelope):
    site_id: uuid.UUID
    equipment_code: str
    equipment_class_id: uuid.UUID | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_no: str | None = None
    location_id: uuid.UUID | None = None
    dedicated: bool = False
    firmware_version: str | None = None


async def create_equipment_asset(
    session: AsyncSession, cmd: CreateEquipmentAssetCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.equipment_code.strip():
        raise ValidationFailedError("equipment_code is required")
    conflict = (
        await session.execute(select(EquipmentAsset).where(EquipmentAsset.equipment_code == cmd.equipment_code))
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("equipment_code is already in use", equipment_code=cmd.equipment_code)

    asset = EquipmentAsset(
        site_id=cmd.site_id, equipment_code=cmd.equipment_code, equipment_class_id=cmd.equipment_class_id,
        manufacturer=cmd.manufacturer, model=cmd.model, serial_no=cmd.serial_no, location_id=cmd.location_id,
        state="INSTALLED", dedicated=cmd.dedicated, firmware_version=cmd.firmware_version, version=1,
    )
    session.add(asset)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, asset=asset, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="INSTALLED", event_type="EquipmentInstalled",
        event_payload={"id": str(asset.id), "equipment_code": asset.equipment_code}, expected_version=None,
        command_type="CreateEquipmentAsset",
    )


# ---------------------------------------------------------------------------
# RecordQualification — EQP-FR-004. `qualified=True` is the terminal "qualification complete" event;
# anything else is progress capture (IQ/OQ/PQ reference free text — no controlled code list beyond prose,
# same "captured, not enumerated" precedent as `MaterialReceipt.discrepancy_type`).
# ---------------------------------------------------------------------------


class RecordQualificationCommand(CommandEnvelope):
    asset_id: uuid.UUID
    expected_version: int
    qualification_status: str
    qualification_scope: dict | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    qualified: bool = False
    reason: str | None = None


async def record_qualification(
    session: AsyncSession, cmd: RecordQualificationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.qualification_status.strip():
        raise ValidationFailedError("qualification_status is required")

    asset = await _load_asset_for_update(session, cmd.asset_id, cmd.expected_version)
    old_state = asset.state

    asset.qualification_scope = cmd.qualification_scope
    asset.qualification_effective_date = cmd.effective_date
    asset.qualification_expiry_date = cmd.expiry_date
    if cmd.qualified:
        asset.qualification_status = QUALIFIED_MARKER
        if asset.state in ("INSTALLED", "QUALIFICATION_PENDING", "SUSPENDED", "OUT_OF_SERVICE"):
            asset.state = "VERIFICATION"
        event_type = "EquipmentQualified"
    else:
        asset.qualification_status = cmd.qualification_status
        if asset.state == "INSTALLED":
            asset.state = "QUALIFICATION_PENDING"
        event_type = "EquipmentQualified"
    asset.version += 1

    await _write_use_log(session, asset=asset, log_type="use", actor_user_id=actor_user_id, event_reference="qualification")

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, asset=asset, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type=event_type,
        event_payload={"id": str(asset.id), "qualification_status": asset.qualification_status},
        expected_version=cmd.expected_version, command_type="RecordQualification",
    )


# ---------------------------------------------------------------------------
# RecordCalibration — EQP-FR-005/006/007/008. One POST captures plan + execution + result atomically
# (the spec declares one calibration operation, not separate plan/execute endpoints). A `fail`/`oot`
# result automatically holds the asset (EQP-FR-007); this module never auto-creates a deviation/CAPA for
# it (spec says "may trigger", not "shall") — `impact_assessment_required` is captured for a human to act
# on, same restraint precedent as SG-108.
# ---------------------------------------------------------------------------


class RecordCalibrationCommand(CommandEnvelope):
    asset_id: uuid.UUID
    expected_version: int
    due_date: date
    performed_date: date
    result: str
    calibration_plan_ref: str | None = None
    procedure_version: str | None = None
    frequency_days: int | None = None
    tolerance: dict | None = None
    as_found: dict | None = None
    adjustments: dict | None = None
    as_left: dict | None = None
    standard_reference: str | None = None
    standard_calibration_status: str | None = None
    standard_expiry_date: date | None = None
    reviewer_user_id: uuid.UUID | None = None
    reason: str | None = None


async def record_calibration(
    session: AsyncSession, cmd: RecordCalibrationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.result not in CALIBRATION_RESULTS:
        raise ValidationFailedError("Unrecognized result", result=cmd.result, allowed=list(CALIBRATION_RESULTS))

    asset = await _load_asset_for_update(session, cmd.asset_id, cmd.expected_version)
    old_state = asset.state

    is_oot = cmd.result in ("fail", "oot")
    calibration = EquipmentCalibration(
        equipment_asset_id=asset.id, site_id=asset.site_id, calibration_plan_ref=cmd.calibration_plan_ref,
        procedure_version=cmd.procedure_version, frequency_days=cmd.frequency_days, tolerance=cmd.tolerance,
        due_date=cmd.due_date, performed_date=cmd.performed_date, as_found=cmd.as_found,
        adjustments=cmd.adjustments, as_left=cmd.as_left, standard_reference=cmd.standard_reference,
        standard_calibration_status=cmd.standard_calibration_status, standard_expiry_date=cmd.standard_expiry_date,
        performer_user_id=actor_user_id, reviewer_user_id=cmd.reviewer_user_id, result=cmd.result,
        impact_assessment_required=is_oot, state="completed", version=1,
    )
    session.add(calibration)
    await session.flush()

    asset.next_calibration_due_date = cmd.due_date
    if is_oot:
        asset.calibration_status = "oot"
        asset.hold_flag = True
        asset.hold_reason = f"Calibration out of tolerance ({calibration.id})"
        asset.hold_source = "calibration"
        asset.state = "OUT_OF_SERVICE"
        event_type = "CalibrationOutOfTolerance"
    else:
        asset.calibration_status = "current"
        if asset.hold_source == "calibration":
            asset.hold_flag = False
            asset.hold_reason = None
            asset.hold_source = None
        if asset.state in ("CALIBRATION_DUE", "OUT_OF_SERVICE", "SUSPENDED"):
            asset.state = "VERIFICATION"
        event_type = "EquipmentCalibrated"
    asset.version += 1

    await _write_use_log(
        session, asset=asset, log_type="calibration", actor_user_id=actor_user_id,
        event_reference=str(calibration.id),
    )

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, asset=asset, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type=event_type,
        event_payload={"id": str(asset.id), "calibration_id": str(calibration.id), "result": cmd.result},
        expected_version=cmd.expected_version, command_type="RecordCalibration",
    )


# ---------------------------------------------------------------------------
# RecordMaintenance — EQP-FR-009/010/011/012/021. `work_order_id=None` creates a new work order (a
# `corrective` type immediately holds the asset — EQP-FR-012 breakdown); a provided `work_order_id`
# continues/verifies it. EQP-FR-022 (Change Control link) is folded in here via `critical_modification`
# rather than a 10th endpoint — it calls the owning `qms.change_commands.create_change` (never writes qms
# tables directly, AG-05/AG-06), same cross-module precedent the Document 22 session used for
# `qms.commands.create_deviation`. `change_classification` is caller-supplied, never guessed (Document 29
# treats temporary/permanent as a real regulated decision).
# ---------------------------------------------------------------------------


class RecordMaintenanceCommand(CommandEnvelope):
    asset_id: uuid.UUID
    expected_version: int
    work_order_id: uuid.UUID | None = None
    type: str | None = None
    fault_description: str | None = None
    diagnosis: str | None = None
    work_performed: str | None = None
    parts_used: dict | None = None
    # EQP-FR-009: preventive-maintenance-plan fields, meaningful on a `planned` work order.
    procedure_version: str | None = None
    frequency_days: int | None = None
    next_due_date: date | None = None
    expected_downtime_hours: Decimal | None = None
    post_maintenance_verification_required: bool = True
    verified: bool = False
    reason: str | None = None
    critical_modification: bool = False
    change_classification: str | None = None
    change_reason: str | None = None
    owner_subject_id: uuid.UUID | None = None


async def record_maintenance(
    session: AsyncSession, cmd: RecordMaintenanceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    asset = await _load_asset_for_update(session, cmd.asset_id, cmd.expected_version)
    old_state = asset.state

    if cmd.work_order_id is None:
        if cmd.type not in MAINTENANCE_TYPES:
            raise ValidationFailedError("Unrecognized type", type=cmd.type, allowed=list(MAINTENANCE_TYPES))
        work_order = MaintenanceWorkOrder(
            equipment_asset_id=asset.id, site_id=asset.site_id, type=cmd.type,
            fault_description=cmd.fault_description, diagnosis=cmd.diagnosis, work_performed=cmd.work_performed,
            parts_used=cmd.parts_used, procedure_version=cmd.procedure_version, frequency_days=cmd.frequency_days,
            next_due_date=cmd.next_due_date, expected_downtime_hours=cmd.expected_downtime_hours,
            technician_user_id=actor_user_id,
            post_maintenance_verification_required=cmd.post_maintenance_verification_required,
            state="open", version=1,
        )
        session.add(work_order)
        await session.flush()

        if cmd.next_due_date is not None:
            asset.next_maintenance_due_date = cmd.next_due_date
        if cmd.type == "corrective":
            asset.hold_flag = True
            asset.hold_reason = f"Breakdown ({work_order.id})"
            asset.hold_source = "maintenance"
            asset.state = "OUT_OF_SERVICE"
        elif asset.state in ("QUALIFIED_AVAILABLE", "CALIBRATION_DUE"):
            asset.state = "MAINTENANCE_DUE"
        asset.maintenance_status = "in_progress"
        event_type = "MaintenanceDue" if cmd.type == "planned" else "EquipmentOutOfService"

        if cmd.critical_modification:
            if cmd.change_classification not in CHANGE_CLASSIFICATIONS:
                raise ValidationFailedError(
                    "change_classification is required and must be a valid classification for a critical modification",
                    allowed=list(CHANGE_CLASSIFICATIONS),
                )
            change_receipt = await create_change(
                session,
                CreateChangeCommand(
                    idempotency_key=str(uuid.uuid4()),
                    site_id=asset.site_id,
                    change_number=f"EQP-{asset.equipment_code}-{work_order.id.hex[:8]}",
                    change_type="equipment",
                    classification=cmd.change_classification,
                    current_state={"equipment_asset_id": str(asset.id), "firmware_version": asset.firmware_version},
                    proposed_state={"description": cmd.change_reason or cmd.work_performed or cmd.diagnosis or ""},
                    reason=cmd.change_reason or cmd.reason or "Critical equipment modification",
                    owner_subject_id=cmd.owner_subject_id or actor_user_id,
                ),
                actor_user_id,
            )
            asset.change_control_id = change_receipt.aggregate_id
    else:
        result = await session.execute(
            select(MaintenanceWorkOrder).where(MaintenanceWorkOrder.id == cmd.work_order_id).with_for_update()
        )
        work_order = result.scalar_one_or_none()
        if work_order is None or work_order.equipment_asset_id != asset.id:
            raise NotFoundError("Maintenance work order not found")
        if work_order.state == "verified":
            raise InvalidTransitionError("Work order is already verified", current_state=work_order.state)

        if cmd.work_performed is not None:
            work_order.work_performed = cmd.work_performed
        if cmd.diagnosis is not None:
            work_order.diagnosis = cmd.diagnosis
        if cmd.parts_used is not None:
            work_order.parts_used = cmd.parts_used

        if cmd.verified:
            work_order.state = "verified"
            work_order.verified_at = datetime.now(timezone.utc)
            work_order.verified_by_user_id = actor_user_id
            work_order.completed_at = datetime.now(timezone.utc)
            asset.maintenance_status = "complete"
            if asset.hold_source == "maintenance":
                asset.hold_flag = False
                asset.hold_reason = None
                asset.hold_source = None
            if asset.state in ("MAINTENANCE_DUE", "OUT_OF_SERVICE", "SUSPENDED"):
                asset.state = "VERIFICATION"
            event_type = "MaintenanceCompleted"
        else:
            work_order.state = "in_progress"
            asset.maintenance_status = "pending_verification"
            event_type = "MaintenanceDue"
        work_order.version += 1

    asset.version += 1

    await _write_use_log(
        session, asset=asset, log_type="maintenance", actor_user_id=actor_user_id,
        event_reference=str(work_order.id),
    )

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, asset=asset, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type=event_type,
        event_payload={"id": str(asset.id), "work_order_id": str(work_order.id), "type": work_order.type},
        expected_version=cmd.expected_version, command_type="RecordMaintenance",
    )


# ---------------------------------------------------------------------------
# HoldEquipment — Document 106 row 108: the one signed operation in this module. `required_role_id=None`
# because the declared signer class is "Authorized holder (Production / QA)" — a role pair, not one
# dedicated role (same treatment as `destruction_record.execute`'s policy row); reason is required.
# ---------------------------------------------------------------------------


class HoldEquipmentCommand(CommandEnvelope):
    asset_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def hold_equipment(
    session: AsyncSession, cmd: HoldEquipmentCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required to hold equipment")

    asset = await _load_asset_for_update(session, cmd.asset_id, cmd.expected_version)
    old_state = asset.state

    policy = await signature_service.resolve_signature_requirement(session, record_type="equipment_asset", action="hold")
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id, record_version=asset.version,
            record_hash=equipment_record_hash(asset),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    asset.state = "SUSPENDED"
    asset.hold_flag = True
    asset.hold_reason = cmd.reason
    asset.hold_source = "manual"
    asset.version += 1

    await _write_use_log(session, asset=asset, log_type="hold", actor_user_id=actor_user_id)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=asset.site_id, aggregate_type="equipment_asset", aggregate_id=asset.id,
        aggregate_version=asset.version, action="StatusChanged", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=cmd.reason, old_value={"state": old_state}, new_value={"state": asset.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="EquipmentOutOfService", aggregate_type="equipment_asset", aggregate_id=asset.id,
        aggregate_version=asset.version, payload={"id": str(asset.id), "state": asset.state}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=asset.site_id, command_type="HoldEquipment", aggregate_type="equipment_asset",
        aggregate_id=asset.id, expected_version=cmd.expected_version, resulting_version=asset.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=asset.id, resulting_version=asset.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ReturnToService — EQP-FR-011/030. The single place `QUALIFIED_AVAILABLE` is ever written. Unsigned
# (no Document 106 row) — RBAC-gated only, same "no row = unsigned" precedent as every prior document.
# ---------------------------------------------------------------------------


class ReturnToServiceCommand(CommandEnvelope):
    asset_id: uuid.UUID
    expected_version: int
    reason: str | None = None


_CODE_TO_ERROR = {
    "EQUIPMENT_OUT_OF_SERVICE": EquipmentOutOfServiceError,
    "EQUIPMENT_NOT_QUALIFIED": EquipmentNotQualifiedError,
    "CALIBRATION_OOT_IMPACT_REQUIRED": CalibrationOotImpactRequiredError,
    "CALIBRATION_EXPIRED": CalibrationExpiredError,
    "POST_MAINTENANCE_VERIFICATION_REQUIRED": PostMaintenanceVerificationRequiredError,
    "CLEANING_REQUIRED": CleaningRequiredError,
}


async def return_to_service(
    session: AsyncSession, cmd: ReturnToServiceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    asset = await _load_asset_for_update(session, cmd.asset_id, cmd.expected_version)
    old_state = asset.state
    if asset.state not in RETURNABLE_STATES:
        raise InvalidTransitionError(
            "Equipment is not in a state eligible for return to service", current_state=asset.state
        )

    reasons = _ineligibility_reasons(asset, datetime.now(timezone.utc).date())
    if reasons:
        code, message = reasons[0]
        raise _CODE_TO_ERROR[code](message)

    asset.state = "QUALIFIED_AVAILABLE"
    asset.hold_flag = False
    asset.hold_reason = None
    asset.hold_source = None
    asset.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, asset=asset, action="StatusChanged", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="EquipmentReturnedToService",
        event_payload={"id": str(asset.id), "state": asset.state}, expected_version=cmd.expected_version,
        command_type="ReturnToService",
    )


# ---------------------------------------------------------------------------
# Retirement is out of Document 38's declared 9-op API list (§6 doesn't name a retire operation despite
# EQP-FR-027 describing it) — same "no invented endpoint" discipline. RETIRED is reachable only via a
# direct DB migration/data-repair path today; raised as a SPEC_GAP, not guessed onto an existing endpoint.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Read queries — EQP-FR-015/028/029.
# ---------------------------------------------------------------------------


async def get_eligibility(session: AsyncSession, asset_id: uuid.UUID) -> dict:
    asset = await session.get(EquipmentAsset, asset_id)
    if asset is None:
        raise NotFoundError("Equipment asset not found")
    reasons = _ineligibility_reasons(asset, datetime.now(timezone.utc).date())
    return {
        "asset_id": str(asset.id),
        "state": asset.state,
        "eligible": not reasons,
        "reasons": [{"code": code, "message": message} for code, message in reasons],
    }


async def get_equipment_history(session: AsyncSession, asset_id: uuid.UUID) -> dict:
    asset = await session.get(EquipmentAsset, asset_id)
    if asset is None:
        raise NotFoundError("Equipment asset not found")
    calibrations = (
        await session.execute(
            select(EquipmentCalibration)
            .where(EquipmentCalibration.equipment_asset_id == asset_id)
            .order_by(EquipmentCalibration.created_at.desc())
        )
    ).scalars().all()
    work_orders = (
        await session.execute(
            select(MaintenanceWorkOrder)
            .where(MaintenanceWorkOrder.equipment_asset_id == asset_id)
            .order_by(MaintenanceWorkOrder.created_at.desc())
        )
    ).scalars().all()
    use_logs = (
        await session.execute(
            select(EquipmentUseLog)
            .where(EquipmentUseLog.equipment_asset_id == asset_id)
            .order_by(EquipmentUseLog.occurred_at.desc())
            .limit(200)
        )
    ).scalars().all()
    return {
        "asset_id": str(asset.id),
        "calibrations": [
            {
                "id": str(c.id), "due_date": c.due_date.isoformat(),
                "performed_date": c.performed_date.isoformat() if c.performed_date else None, "result": c.result,
                "standard_reference": c.standard_reference,
                "standard_calibration_status": c.standard_calibration_status,
                "standard_expiry_date": c.standard_expiry_date.isoformat() if c.standard_expiry_date else None,
                "as_found": c.as_found, "adjustments": c.adjustments, "as_left": c.as_left,
                "impact_assessment_required": c.impact_assessment_required,
                "performer_user_id": str(c.performer_user_id) if c.performer_user_id else None,
            }
            for c in calibrations
        ],
        "maintenance_work_orders": [
            {
                "id": str(w.id), "type": w.type, "state": w.state, "started_at": w.started_at.isoformat(),
                "fault_description": w.fault_description, "diagnosis": w.diagnosis,
                "work_performed": w.work_performed, "parts_used": w.parts_used,
                "procedure_version": w.procedure_version, "frequency_days": w.frequency_days,
                "next_due_date": w.next_due_date.isoformat() if w.next_due_date else None,
                "expected_downtime_hours": str(w.expected_downtime_hours) if w.expected_downtime_hours is not None else None,
                "post_maintenance_verification_required": w.post_maintenance_verification_required,
                "verified_at": w.verified_at.isoformat() if w.verified_at else None,
                "technician_user_id": str(w.technician_user_id),
            }
            for w in work_orders
        ],
        "use_log": [
            {"id": str(u.id), "log_type": u.log_type, "occurred_at": u.occurred_at.isoformat()}
            for u in use_logs
        ],
    }


async def get_dashboard(session: AsyncSession, site_id: uuid.UUID) -> dict:
    """EQP-FR-028 (partial): due calibration/maintenance counts and the out-of-service list. Utilization
    and recurring-failure analytics need a time-series/analytics engine this codebase doesn't have yet —
    not attempted here."""
    today = datetime.now(timezone.utc).date()
    assets = (await session.execute(select(EquipmentAsset).where(EquipmentAsset.site_id == site_id))).scalars().all()
    due_calibration = [a for a in assets if a.next_calibration_due_date is not None and a.next_calibration_due_date <= today]
    due_maintenance = [a for a in assets if a.maintenance_status in ("in_progress", "pending_verification")]
    out_of_service = [a for a in assets if a.state in ("OUT_OF_SERVICE", "SUSPENDED")]
    return {
        "site_id": str(site_id),
        "due_calibration_count": len(due_calibration),
        "due_maintenance_count": len(due_maintenance),
        "out_of_service": [{"id": str(a.id), "equipment_code": a.equipment_code, "state": a.state} for a in out_of_service],
    }
