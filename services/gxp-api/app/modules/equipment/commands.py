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
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.reference_resolution import build_code_index
from app.core.security import verify_password
from app.modules.codegen import service as codegen_service
from app.modules.equipment.cleaning_models import EquipmentArea
from app.modules.equipment.models import (
    CALIBRATION_RESULTS,
    CALIBRATION_TYPES,
    MAINTENANCE_TYPES,
    EquipmentAsset,
    EquipmentCalibration,
    EquipmentUseLog,
    MaintenanceWorkOrder,
)
from app.modules.iam.models import Role, User
from app.modules.policy.service import effective_role_names
from app.modules.qms.change_commands import CreateChangeCommand, create_change
from app.modules.recipe_master.service import list_equipment_classes
from app.modules.qms.change_models import CHANGE_CLASSIFICATIONS
from app.modules.supplier_quality.models import Supplier
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    CalibrationApprovalPendingError,
    RecalibrationRequiredError,
    CalibrationExpiredError,
    CalibrationOotImpactRequiredError,
    CleaningRequiredError,
    EquipmentNotQualifiedError,
    EquipmentOutOfServiceError,
    EquipmentReservationConflictError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    PostMaintenanceVerificationRequiredError,
    RoleMissingError,
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
    elif asset.calibration_status in ("pending_approval", "rejected"):
        # Client gap-analysis Phase 4: a recorded pass result is not enough on its own -- it must also be
        # reviewed/approved by someone independent of the performer (SoD) before the equipment is
        # eligible, same "Pass/Fail is objective, Approved/Not-Approved is a separate QA disposition"
        # distinction the client drew for material/QC results.
        reasons.append((
            "CALIBRATION_APPROVAL_PENDING",
            "Most recent calibration has not yet been approved"
            if asset.calibration_status == "pending_approval"
            else "Most recent calibration was not approved",
        ))
    elif asset.calibration_status not in (None, "current"):
        reasons.append(("CALIBRATION_EXPIRED", "Calibration is due or overdue"))
    elif asset.next_calibration_due_date is not None and asset.next_calibration_due_date < today:
        reasons.append(("CALIBRATION_EXPIRED", "Calibration due date has passed"))
    # Client gap-analysis Phase 7: a breakdown maintenance event (not flagged non-critical) requires a new
    # calibration -- recorded AND approved, not just verified maintenance -- before this equipment is
    # eligible again. Checked independently of the calibration_status chain above since a breakdown can
    # happen to equipment whose prior calibration was otherwise still current.
    if asset.recalibration_required:
        reasons.append(("RECALIBRATION_REQUIRED", "A breakdown requires recalibration before this equipment is eligible for use"))
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
    equipment_code: str | None = None
    equipment_class_id: uuid.UUID
    manufacturer: str | None = None
    model: str | None = None
    serial_no: str | None = None
    location_id: uuid.UUID | None = None
    dedicated: bool = False
    firmware_version: str | None = None
    # Client gap-analysis Phase 7: mandatory-at-creation computer-operated-vs-manual question (required,
    # no default -- same treatment Phase 6 gave the Material Receipt examine booleans).
    is_computer_operated: bool


async def create_equipment_asset(
    session: AsyncSession, cmd: CreateEquipmentAssetCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.equipment_code and cmd.equipment_code.strip():
        conflict = (
            await session.execute(select(EquipmentAsset).where(EquipmentAsset.equipment_code == cmd.equipment_code))
        ).scalar_one_or_none()
        if conflict is not None:
            raise ValidationFailedError("equipment_code is already in use", equipment_code=cmd.equipment_code)
        equipment_code = cmd.equipment_code
    else:
        equipment_code = await codegen_service.next_code(session, entity_type="EQUIPMENT_ASSET", prefix="EQP")

    # Bug fix: equipment_class_id used to be captured-but-unvalidated, so an asset could be created with a
    # class that later made every step-start referencing it fail EQUIPMENT_CLASS_MISMATCH with no earlier
    # warning. Validated the same way product_master validates sterile_profile_id against its own
    # registry -- through the existing cross-module read function router.py already uses for the picker
    # (list_equipment_classes), not by importing recipe_master's EquipmentClass model directly (AG-02).
    known_class_ids = {c.id for c in await list_equipment_classes(session)}
    if cmd.equipment_class_id not in known_class_ids:
        raise NotFoundError("equipment_class_id does not reference a known equipment class", equipment_class_id=str(cmd.equipment_class_id))

    asset = EquipmentAsset(
        site_id=cmd.site_id, equipment_code=equipment_code, equipment_class_id=cmd.equipment_class_id,
        manufacturer=cmd.manufacturer, model=cmd.model, serial_no=cmd.serial_no, location_id=cmd.location_id,
        state="INSTALLED", dedicated=cmd.dedicated, firmware_version=cmd.firmware_version,
        is_computer_operated=cmd.is_computer_operated, version=1,
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
# CreateEquipmentArea — added 2026-09-07, project-owner-directed. `EquipmentArea`'s own docstring
# (cleaning_models.py) called it a shared master "provisioned outside the app today" -- no write endpoint
# existed anywhere in Document 38/39/40/41/42's declared API lists, only the read-only `GET
# /equipment/v1/areas` listing this pass's own real-picker work added for the `areaSelect` field type.
# Found while building that same picker for the `/aseptic` "Create aseptic operation" form and asked
# directly whether to also build create capability for the rows behind it -- same "own considered create
# contract, not a guessed one" precedent as `warehouse_location.create`/`aseptic_profile_version.create`.
# No qualification/release workflow exists for an area (unlike EquipmentAsset's INSTALLED->...->
# QUALIFIED_AVAILABLE chain) -- created directly at status="active", matching the model's own default.
# ---------------------------------------------------------------------------


class CreateEquipmentAreaCommand(CommandEnvelope):
    site_id: uuid.UUID
    area_code: str | None = None
    area_type: str | None = None
    classification: str | None = None
    criticality: str | None = None
    cleanliness_status: str | None = None


async def create_equipment_area(
    session: AsyncSession, cmd: CreateEquipmentAreaCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.area_code and cmd.area_code.strip():
        # Matches the DB's own UniqueConstraint("area_code") — table-wide, not per-site.
        conflict = (
            await session.execute(select(EquipmentArea).where(EquipmentArea.area_code == cmd.area_code))
        ).scalar_one_or_none()
        if conflict is not None:
            raise ValidationFailedError(
                "area_code is already in use", area_code=cmd.area_code, existing_id=str(conflict.id)
            )
        area_code = cmd.area_code
    else:
        area_code = await codegen_service.next_code(session, entity_type="EQUIPMENT_AREA", prefix="ARE")

    area = EquipmentArea(
        site_id=cmd.site_id, area_code=area_code, area_type=cmd.area_type,
        classification=cmd.classification, criticality=cmd.criticality,
        cleanliness_status=cmd.cleanliness_status, status="active", version=1,
    )
    session.add(area)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=area.site_id, aggregate_type="equipment_area", aggregate_id=area.id,
        aggregate_version=1, action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"area_code": area.area_code, "classification": area.classification},
    )
    await write_outbox_event(
        session, event_type="EquipmentAreaCreated", aggregate_type="equipment_area", aggregate_id=area.id,
        aggregate_version=1, payload={"id": str(area.id), "area_code": area.area_code}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=area.site_id, command_type="CreateEquipmentArea", aggregate_type="equipment_area",
        aggregate_id=area.id, expected_version=None, resulting_version=1,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=area.id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
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
#
# Client gap-analysis Phase 4 (2026-10-05): when `calibration_id` is supplied, this same command reviews/
# approves an *existing* calibration instead of recording a new one — the "Approved/Not-Approved" step the
# client described as distinct from the objective "Pass/Fail" result, SoD-enforced (approver independent
# of performer) the same way `supplier_quality.approve_supplier_qualification` is. This mirrors
# RecordMaintenance's own `work_order_id`-provided-means-continue pattern immediately below in this file,
# rather than inventing a different shape for a second "continue an existing row" command in this module.
# ---------------------------------------------------------------------------


class RecordCalibrationCommand(CommandEnvelope):
    asset_id: uuid.UUID
    expected_version: int
    # Required to record a new calibration; not used when calibration_id is provided (approval branch).
    due_date: date | None = None
    performed_date: date | None = None
    result: str | None = None
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
    # Client requirement #7.
    calibration_type: str = "internal"
    provider_name: str | None = None
    # Client gap-analysis Phase 6: optional reference to a known Supplier (role_type "service_provider"
    # or "both") instead of only free-text provider_name, which stays for a provider not yet onboarded.
    provider_supplier_id: uuid.UUID | None = None
    certificate_reference: str | None = None
    # Client gap-analysis Phase 4: when set, this call approves/rejects the named existing calibration
    # instead of creating a new one. `approved` is required (and only meaningful) in that branch.
    calibration_id: uuid.UUID | None = None
    approved: bool | None = None


async def record_calibration(
    session: AsyncSession, cmd: RecordCalibrationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    asset = await _load_asset_for_update(session, cmd.asset_id, cmd.expected_version)
    old_state = asset.state

    if cmd.calibration_id is not None:
        # --- Approval branch -------------------------------------------------------------------
        if cmd.approved is None:
            raise ValidationFailedError("approved is required when approving an existing calibration")
        result = await session.execute(
            select(EquipmentCalibration).where(EquipmentCalibration.id == cmd.calibration_id).with_for_update()
        )
        calibration = result.scalar_one_or_none()
        if calibration is None or calibration.equipment_asset_id != asset.id:
            raise NotFoundError("Equipment calibration not found")
        if calibration.approved is not None:
            raise InvalidTransitionError(
                "This calibration has already been reviewed", current_approved=calibration.approved
            )
        if actor_user_id == calibration.performer_user_id:
            raise InvalidTransitionError(
                "Approver must be independent of the performer for this calibration (SoD)"
            )

        calibration.approved = cmd.approved
        calibration.approved_by_user_id = actor_user_id
        calibration.approved_at = datetime.now(timezone.utc)
        calibration.version += 1

        # Only the asset's *latest* calibration gates its eligibility (asset.calibration_status is a
        # denormalized summary, not a live join) — an approval/rejection on an older, superseded
        # calibration still gets recorded (full history, never edited) but must not resurrect a stale
        # status over whatever the most recent calibration already set.
        latest = (
            await session.execute(
                select(EquipmentCalibration)
                .where(EquipmentCalibration.equipment_asset_id == asset.id)
                .order_by(EquipmentCalibration.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if latest is not None and latest.id == calibration.id and asset.calibration_status in (
            "pending_approval", "rejected",
        ):
            asset.calibration_status = "current" if cmd.approved else "rejected"
            # Client gap-analysis Phase 7: a breakdown's recalibration requirement is satisfied only by a
            # new calibration that is both recorded and approved -- the same bar CALIBRATION_APPROVAL_
            # PENDING already applies to "current" above, not just a verified maintenance work order.
            if cmd.approved and asset.recalibration_required:
                asset.recalibration_required = False
        asset.version += 1

        return await _write_receipt(
            session, cmd=cmd, payload_hash=payload_hash, asset=asset, action="Approved", actor_user_id=actor_user_id,
            reason=cmd.reason, old_state=old_state,
            event_type="EquipmentCalibrationApproved" if cmd.approved else "EquipmentCalibrationRejected",
            event_payload={"id": str(asset.id), "calibration_id": str(calibration.id), "approved": cmd.approved},
            expected_version=cmd.expected_version, command_type="ApproveCalibration",
        )

    # --- Creation branch -------------------------------------------------------------------------
    if cmd.due_date is None or cmd.performed_date is None or cmd.result is None:
        raise ValidationFailedError("due_date, performed_date and result are required to record a calibration")
    if cmd.result not in CALIBRATION_RESULTS:
        raise ValidationFailedError("Unrecognized result", result=cmd.result, allowed=list(CALIBRATION_RESULTS))
    if cmd.calibration_type not in CALIBRATION_TYPES:
        raise ValidationFailedError(
            "Unrecognized calibration_type", calibration_type=cmd.calibration_type, allowed=list(CALIBRATION_TYPES)
        )
    provider_name = cmd.provider_name
    if cmd.calibration_type == "external":
        if cmd.provider_supplier_id is not None:
            provider = await session.get(Supplier, cmd.provider_supplier_id)
            if provider is None or provider.role_type not in ("service_provider", "both"):
                raise ValidationFailedError(
                    "provider_supplier_id must reference a Supplier with role_type 'service_provider' or 'both'"
                )
            provider_name = provider_name or provider.legal_name
        if not (provider_name and provider_name.strip()):
            raise ValidationFailedError("provider_name or provider_supplier_id is required for an external calibration")

    is_oot = cmd.result in ("fail", "oot")
    calibration = EquipmentCalibration(
        equipment_asset_id=asset.id, site_id=asset.site_id, calibration_plan_ref=cmd.calibration_plan_ref,
        procedure_version=cmd.procedure_version, frequency_days=cmd.frequency_days, tolerance=cmd.tolerance,
        due_date=cmd.due_date, performed_date=cmd.performed_date, as_found=cmd.as_found,
        adjustments=cmd.adjustments, as_left=cmd.as_left, standard_reference=cmd.standard_reference,
        standard_calibration_status=cmd.standard_calibration_status, standard_expiry_date=cmd.standard_expiry_date,
        performer_user_id=actor_user_id, reviewer_user_id=cmd.reviewer_user_id, result=cmd.result,
        impact_assessment_required=is_oot, state="completed", version=1,
        calibration_type=cmd.calibration_type, provider_name=provider_name,
        provider_supplier_id=cmd.provider_supplier_id,
        certificate_reference=cmd.certificate_reference,
    )
    session.add(calibration)
    await session.flush()

    # Client requirement #8: when a calibration interval is supplied, calculate the asset's next due
    # date from it instead of trusting the caller's own due_date field (which represents the due date
    # *this* calibration was performed against, a distinct fact) -- the whole point of the feature is to
    # stop callers hand-computing this themselves.
    asset.next_calibration_due_date = (
        cmd.performed_date + timedelta(days=cmd.frequency_days) if cmd.frequency_days else cmd.due_date
    )
    if is_oot:
        asset.calibration_status = "oot"
        asset.hold_flag = True
        asset.hold_reason = f"Calibration out of tolerance ({calibration.id})"
        asset.hold_source = "calibration"
        asset.state = "OUT_OF_SERVICE"
        event_type = "CalibrationOutOfTolerance"
    else:
        # Client gap-analysis Phase 4: a passing result alone is no longer enough to clear eligibility --
        # it now needs the separate approval step above before `_ineligibility_reasons()` will let this
        # asset be used (CALIBRATION_APPROVAL_PENDING until then).
        asset.calibration_status = "pending_approval"
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
    # Client requirement #9: caller-entered actual downtime, typically supplied on the continuation
    # (work_order_id-provided) call once the real elapsed impact is known.
    actual_downtime_hours: Decimal | None = None
    post_maintenance_verification_required: bool = True
    verified: bool = False
    reason: str | None = None
    critical_modification: bool = False
    change_classification: str | None = None
    change_reason: str | None = None
    owner_subject_id: uuid.UUID | None = None
    # Client gap-analysis Phase 7: breakdown-only override that skips the recalibration-required gate
    # below. Meaningless (ignored) for planned/corrective -- only "breakdown" sets the gate in the first
    # place.
    non_critical: bool = False
    # Client gap-analysis Phase 7: repeatable Activity/Result checklist, meaningful for "planned" --
    # captured as-is (JSONB), not validated row-by-row (same unenforced-structure precedent as
    # `parts_used`).
    activities: list[dict] | None = None


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
            actual_downtime_hours=cmd.actual_downtime_hours,
            technician_user_id=actor_user_id,
            post_maintenance_verification_required=cmd.post_maintenance_verification_required,
            non_critical=cmd.non_critical, activities=cmd.activities,
            state="open", version=1,
        )
        session.add(work_order)
        await session.flush()

        if cmd.next_due_date is not None:
            asset.next_maintenance_due_date = cmd.next_due_date
        if cmd.type in ("corrective", "breakdown"):
            asset.hold_flag = True
            asset.hold_reason = f"Breakdown ({work_order.id})"
            asset.hold_source = "maintenance"
            asset.state = "OUT_OF_SERVICE"
        elif asset.state in ("QUALIFIED_AVAILABLE", "CALIBRATION_DUE"):
            asset.state = "MAINTENANCE_DUE"
        asset.maintenance_status = "in_progress"
        # Client gap-analysis Phase 7: a breakdown defaults to requiring recalibration before the
        # equipment is eligible for use again, unless this work order is flagged non-critical.
        if cmd.type == "breakdown" and not cmd.non_critical:
            asset.recalibration_required = True
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
        if cmd.activities is not None:
            work_order.activities = cmd.activities
        if cmd.actual_downtime_hours is not None:
            work_order.actual_downtime_hours = cmd.actual_downtime_hours

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
    "CALIBRATION_APPROVAL_PENDING": CalibrationApprovalPendingError,
    "RECALIBRATION_REQUIRED": RecalibrationRequiredError,
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
# ReserveEquipment -- EQP-FR-016, Client Topic 14 (SG-112, project-owner-directed): "allow specific
# equipment to be reserved for a particular batch and/or time window ... show the equipment, batch, user,
# and reserved period to prevent scheduling conflicts." No dedicated reservation entity is added -- Document
# 38's frozen 4-entity data model (models.py's own module docstring) already declares exactly the "no 5th
# table" discipline SG-112 itself names, and `equipment_use_log.log_type` already carries a `"reservation"`
# value (USE_LOG_TYPES) for exactly this, with no command that ever wrote one until now. Unsigned -- the
# client asked for conflict prevention, not an approval/signature on reserving -- RBAC-gated only, same
# "no Document 106 row = unsigned" precedent as every other not-yet-signed action in this module.
# ---------------------------------------------------------------------------


class ReserveEquipmentCommand(CommandEnvelope):
    asset_id: uuid.UUID
    batch_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    reason: str | None = None


async def reserve_equipment(
    session: AsyncSession, cmd: ReserveEquipmentCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.end_at <= cmd.start_at:
        raise ValidationFailedError("end_at must be after start_at")

    asset = await session.get(EquipmentAsset, cmd.asset_id)
    if asset is None:
        raise NotFoundError("Equipment asset not found")
    if asset.state == "RETIRED":
        raise InvalidTransitionError("Equipment is retired and can no longer be reserved", current_state=asset.state)

    # EQP-FR-016's own "prevent scheduling conflicts": any existing reservation-type log row for this
    # asset whose [occurred_at, ended_at) window overlaps the requested one blocks the new request.
    overlapping = (
        await session.execute(
            select(EquipmentUseLog).where(
                EquipmentUseLog.equipment_asset_id == cmd.asset_id,
                EquipmentUseLog.log_type == "reservation",
                EquipmentUseLog.occurred_at < cmd.end_at,
                EquipmentUseLog.ended_at > cmd.start_at,
            )
        )
    ).scalars().all()
    if overlapping:
        raise EquipmentReservationConflictError(
            "The requested reservation window overlaps an existing reservation for this equipment",
            conflicting_reservation_ids=[str(r.id) for r in overlapping],
        )

    log = EquipmentUseLog(
        equipment_asset_id=asset.id, site_id=asset.site_id, log_type="reservation", batch_id=cmd.batch_id,
        operator_user_id=actor_user_id, source="manual", event_reference=cmd.reason,
        occurred_at=cmd.start_at, ended_at=cmd.end_at,
    )
    session.add(log)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=asset.site_id, aggregate_type="equipment_use_log", aggregate_id=log.id,
        aggregate_version=1, action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=cmd.reason, old_value=None,
        new_value={
            "equipment_asset_id": str(asset.id), "batch_id": str(cmd.batch_id),
            "start_at": cmd.start_at.isoformat(), "end_at": cmd.end_at.isoformat(),
        },
    )
    await write_outbox_event(
        session, event_type="EquipmentReserved", aggregate_type="equipment_use_log", aggregate_id=log.id,
        aggregate_version=1,
        payload={"id": str(log.id), "equipment_asset_id": str(asset.id), "batch_id": str(cmd.batch_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=asset.site_id, command_type="ReserveEquipment", aggregate_type="equipment_use_log",
        aggregate_id=log.id, expected_version=None, resulting_version=1,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=log.id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# RetireEquipment -- EQP-FR-027, Client Topic 14 (SG-112, project-owner-directed): "approval and
# electronic sign-off from an authorized supervisor or designated responsible person ... retain the
# equipment's historical records and record the reason, date, and person who approved." RETIRED is
# already modeled in EQUIPMENT_STATES and `_load_asset_for_update()` already rejects any further mutation
# once an asset reaches it -- this is the one command that ever writes it. New Document 106 row
# (`equipment_asset`/`retire`, meaning "Approved", required role "Supervisor" per the client's own literal
# wording, no independence requirement asked for) -- the client's own answer is the authorization for this
# row, same "client answer is the authorization" precedent used throughout this session.
# ---------------------------------------------------------------------------


class RetireEquipmentCommand(CommandEnvelope):
    asset_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def retire_equipment(
    session: AsyncSession, cmd: RetireEquipmentCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required to retire equipment")

    asset = await _load_asset_for_update(session, cmd.asset_id, cmd.expected_version)
    old_state = asset.state

    policy = await signature_service.resolve_signature_requirement(session, record_type="equipment_asset", action="retire")
    signature_id = None
    if policy.signature_required:
        if policy.required_role_id is not None:
            required_role_name = await session.scalar(select(Role.name).where(Role.id == policy.required_role_id))
            if required_role_name not in await effective_role_names(session, actor_user_id, asset.site_id):
                raise RoleMissingError(
                    "Retiring equipment requires the signing role named by the signature policy",
                    action="equipment_asset.retire", required_role=required_role_name,
                )
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id, record_version=asset.version,
            record_hash=equipment_record_hash(asset),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    asset.state = "RETIRED"
    asset.version += 1

    await _write_use_log(session, asset=asset, log_type="use", actor_user_id=actor_user_id, event_reference="retirement")

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=asset.site_id, aggregate_type="equipment_asset", aggregate_id=asset.id,
        aggregate_version=asset.version, action="StatusChanged", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=cmd.reason, old_value={"state": old_state}, new_value={"state": asset.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="EquipmentRetired", aggregate_type="equipment_asset", aggregate_id=asset.id,
        aggregate_version=asset.version, payload={"id": str(asset.id), "state": asset.state}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=asset.site_id, command_type="RetireEquipment", aggregate_type="equipment_asset",
        aggregate_id=asset.id, expected_version=cmd.expected_version, resulting_version=asset.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=asset.id, resulting_version=asset.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# RelocateEquipment -- EQP-FR-026, Client Topic 14 (SG-112, project-owner-directed): "flag it as requiring
# any applicable re-qualification, verification ... before it can be used again. The equipment should
# remain unavailable for use until the required checks are completed and documented." Reuses the exact
# qualification_status/state mechanism `record_qualification()` already enforces -- no new column (e.g. a
# separate `requires_requalification` flag) is added: clearing `qualification_status` and moving `state`
# back to `QUALIFICATION_PENDING` makes `_ineligibility_reasons()`/`get_eligibility()` correctly report the
# asset unavailable through the exact same path every other qualification gap already uses, until a fresh
# `record_qualification(qualified=True)` clears it. Cleaning is deliberately NOT reset -- Document 39's
# cleaning enforcement does not exist yet (SG-110); inventing a cleaning-block here would be guessing a
# dependency this pass has no authority to build. Unsigned -- the client asked for an automatic
# availability flag, not an approval/signature on the move itself.
# ---------------------------------------------------------------------------


class RelocateEquipmentCommand(CommandEnvelope):
    asset_id: uuid.UUID
    expected_version: int
    new_location_id: uuid.UUID
    reason: str | None = None


async def relocate_equipment(
    session: AsyncSession, cmd: RelocateEquipmentCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    asset = await _load_asset_for_update(session, cmd.asset_id, cmd.expected_version)
    old_state = asset.state

    asset.location_id = cmd.new_location_id
    asset.qualification_status = None
    asset.qualification_expiry_date = None
    asset.state = "QUALIFICATION_PENDING"
    asset.version += 1

    await _write_use_log(session, asset=asset, log_type="use", actor_user_id=actor_user_id, event_reference="relocation")

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, asset=asset, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="EquipmentRelocated",
        event_payload={"id": str(asset.id), "location_id": str(asset.location_id), "state": asset.state},
        expected_version=cmd.expected_version, command_type="RelocateEquipment",
    )


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
                "id": str(c.id), "calibration_plan_ref": c.calibration_plan_ref,
                "procedure_version": c.procedure_version, "frequency_days": c.frequency_days,
                "tolerance": c.tolerance, "due_date": c.due_date.isoformat(),
                "performed_date": c.performed_date.isoformat() if c.performed_date else None, "result": c.result,
                "standard_reference": c.standard_reference,
                "standard_calibration_status": c.standard_calibration_status,
                "standard_expiry_date": c.standard_expiry_date.isoformat() if c.standard_expiry_date else None,
                "calibration_type": c.calibration_type, "provider_name": c.provider_name,
                "provider_supplier_id": str(c.provider_supplier_id) if c.provider_supplier_id else None,
                "certificate_reference": c.certificate_reference,
                "as_found": c.as_found, "adjustments": c.adjustments, "as_left": c.as_left,
                "impact_assessment_required": c.impact_assessment_required,
                "deviation_reference_id": str(c.deviation_reference_id) if c.deviation_reference_id else None,
                "performer_user_id": str(c.performer_user_id) if c.performer_user_id else None,
                "reviewer_user_id": str(c.reviewer_user_id) if c.reviewer_user_id else None,
                "approved": c.approved,
                "approved_by_user_id": str(c.approved_by_user_id) if c.approved_by_user_id else None,
                "approved_at": c.approved_at.isoformat() if c.approved_at else None,
                "state": c.state, "version": c.version,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in calibrations
        ],
        "maintenance_work_orders": [
            {
                "id": str(w.id), "type": w.type, "state": w.state, "started_at": w.started_at.isoformat(),
                "completed_at": w.completed_at.isoformat() if w.completed_at else None,
                "fault_description": w.fault_description, "diagnosis": w.diagnosis,
                "work_performed": w.work_performed, "parts_used": w.parts_used,
                "non_critical": w.non_critical, "activities": w.activities,
                "procedure_version": w.procedure_version, "frequency_days": w.frequency_days,
                "next_due_date": w.next_due_date.isoformat() if w.next_due_date else None,
                "expected_downtime_hours": str(w.expected_downtime_hours) if w.expected_downtime_hours is not None else None,
                "actual_downtime_hours": str(w.actual_downtime_hours) if w.actual_downtime_hours is not None else None,
                "post_maintenance_verification_required": w.post_maintenance_verification_required,
                "verified_at": w.verified_at.isoformat() if w.verified_at else None,
                "verified_by_user_id": str(w.verified_by_user_id) if w.verified_by_user_id else None,
                "technician_user_id": str(w.technician_user_id),
                "version": w.version, "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in work_orders
        ],
        "use_log": [
            {
                "id": str(u.id), "log_type": u.log_type, "occurred_at": u.occurred_at.isoformat(),
                "ended_at": u.ended_at.isoformat() if u.ended_at else None,
                "batch_id": str(u.batch_id) if u.batch_id else None,
                "operator_user_id": str(u.operator_user_id) if u.operator_user_id else None,
                "event_reference": u.event_reference,
            }
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


# ---------------------------------------------------------------------------
# BulkImportEquipment — Client gap-analysis Phase 7 (2026-10-05): a new capability beyond Document 38 §6's
# declared 9 operations, same "own considered contract, not a guessed one" precedent as
# `warehouse_location.create`/`aseptic_profile_version.create`/`iam.bulk_import_users` (Phase 1) before it.
# Reuses Phase 1's exact preview/commit shape: validate-only preview reports per-row errors; commit is
# all-or-nothing and reuses `create_equipment_asset` per row rather than bypassing its validation.
# `equipment_class_code` (not a raw id) is the one thing a spreadsheet realistically carries by hand, same
# "business code, not a UUID" choice Phase 1 made for role_name/site_code.
# ---------------------------------------------------------------------------


class BulkImportEquipmentRow(BaseModel):
    equipment_code: str | None = None
    equipment_class_code: str
    manufacturer: str | None = None
    model: str | None = None
    serial_no: str | None = None
    firmware_version: str | None = None
    dedicated: bool = False
    is_computer_operated: bool = False


class BulkImportEquipmentRowValidation(BaseModel):
    row_index: int
    equipment_code: str | None
    ok: bool
    error: str | None = None


async def validate_bulk_import_equipment_rows(
    session: AsyncSession, rows: list[BulkImportEquipmentRow]
) -> list[BulkImportEquipmentRowValidation]:
    """Read-only. Used by both the preview endpoint and (defense in depth) bulk_import_equipment itself
    right before committing, since rows can go stale between a client's preview call and its commit call."""
    results: list[BulkImportEquipmentRowValidation] = []
    seen_codes: set[str] = set()
    class_codes = set(build_code_index(await list_equipment_classes(session), "class_code"))
    candidate_codes = {row.equipment_code for row in rows if row.equipment_code}
    existing_codes = (
        {
            c
            for c in (
                await session.execute(select(EquipmentAsset.equipment_code).where(EquipmentAsset.equipment_code.in_(candidate_codes)))
            ).scalars().all()
        }
        if candidate_codes
        else set()
    )

    for idx, row in enumerate(rows):
        if row.equipment_class_code not in class_codes:
            results.append(
                BulkImportEquipmentRowValidation(
                    row_index=idx, equipment_code=row.equipment_code, ok=False,
                    error=f"unknown equipment_class_code '{row.equipment_class_code}'",
                )
            )
            continue
        if row.equipment_code:
            if row.equipment_code in seen_codes:
                results.append(
                    BulkImportEquipmentRowValidation(
                        row_index=idx, equipment_code=row.equipment_code, ok=False,
                        error="duplicate equipment_code within this import",
                    )
                )
                continue
            seen_codes.add(row.equipment_code)
            if row.equipment_code in existing_codes:
                results.append(
                    BulkImportEquipmentRowValidation(
                        row_index=idx, equipment_code=row.equipment_code, ok=False,
                        error="equipment_code is already in use",
                    )
                )
                continue
        results.append(BulkImportEquipmentRowValidation(row_index=idx, equipment_code=row.equipment_code, ok=True))
    return results


class BulkImportEquipmentCommand(CommandEnvelope):
    site_id: uuid.UUID
    rows: list[BulkImportEquipmentRow]


class BulkImportedEquipment(BaseModel):
    row_index: int
    asset_id: uuid.UUID
    equipment_code: str


class BulkImportEquipmentResult(BaseModel):
    command_id: uuid.UUID
    correlation_id: uuid.UUID
    created: list[BulkImportedEquipment]


async def bulk_import_equipment(
    session: AsyncSession, cmd: BulkImportEquipmentCommand, actor_user_id: uuid.UUID
) -> BulkImportEquipmentResult:
    if not cmd.rows:
        raise ValidationFailedError("No rows to import")

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return BulkImportEquipmentResult(command_id=existing_receipt.id, correlation_id=existing_receipt.id, created=[])

    validations = await validate_bulk_import_equipment_rows(session, cmd.rows)
    errors = [v for v in validations if not v.ok]
    if errors:
        raise ValidationFailedError(
            "One or more rows failed validation -- no equipment was created",
            errors=[{"row_index": e.row_index, "equipment_code": e.equipment_code, "error": e.error} for e in errors],
        )

    class_by_code = build_code_index(await list_equipment_classes(session), "class_code")

    correlation_id = uuid.uuid4()
    created: list[BulkImportedEquipment] = []
    for idx, row in enumerate(cmd.rows):
        asset_class = class_by_code[row.equipment_class_code]
        receipt = await create_equipment_asset(
            session,
            CreateEquipmentAssetCommand(
                idempotency_key=f"{cmd.idempotency_key}:row-{idx}",
                site_id=cmd.site_id,
                equipment_code=row.equipment_code,
                equipment_class_id=asset_class.id,
                manufacturer=row.manufacturer,
                model=row.model,
                serial_no=row.serial_no,
                firmware_version=row.firmware_version,
                dedicated=row.dedicated,
                is_computer_operated=row.is_computer_operated,
            ),
            actor_user_id,
        )
        asset = await session.get(EquipmentAsset, receipt.aggregate_id)
        created.append(BulkImportedEquipment(row_index=idx, asset_id=receipt.aggregate_id, equipment_code=asset.equipment_code))

    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="BulkImportEquipment",
        aggregate_type="equipment_bulk_import",
        aggregate_id=uuid.uuid4(),
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return BulkImportEquipmentResult(command_id=receipt.id, correlation_id=correlation_id, created=created)
