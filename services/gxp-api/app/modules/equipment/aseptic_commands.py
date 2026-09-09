"""Document 40 (SPEC-EQP-003) — exactly the 7 declared operations (§6). Built last in the WP-06 pass so
`get_readiness` (and `start_operation`, which reuses the same composition) can call the real cross-module
functions Documents 38/39/41/42 already built, instead of raising forward-dependency SPEC_GAPs for the
document's own most central requirements (ASP-FR-005/006/007/008).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.equipment import cleaning_commands, commands as equipment_commands, em_commands
from app.modules.equipment import sterilization_commands
from app.modules.equipment.aseptic_models import (
    EVENT_SEVERITIES,
    INTERVENTION_TYPES,
    AsepticEventTimeline,
    AsepticIntervention,
    AsepticOperation,
    AsepticProfileVersion,
)
from app.modules.iam.models import User
from app.modules.qc.models import QcResult, QcTestOrder
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    AsepticAreaNotReadyError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    SterileComponentIneligibleError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def operation_record_hash(operation: AsepticOperation) -> str:
    return sha256_hex({"id": str(operation.id), "version": operation.version, "state": operation.state})


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


async def _load_operation_for_update(session: AsyncSession, operation_id: uuid.UUID, expected_version: int) -> AsepticOperation:
    result = await session.execute(select(AsepticOperation).where(AsepticOperation.id == operation_id).with_for_update())
    operation = result.scalar_one_or_none()
    if operation is None:
        raise NotFoundError("Aseptic operation not found")
    if operation.version != expected_version:
        raise StaleVersionError(
            "Aseptic operation was modified by another actor since it was read",
            expected_version=expected_version, current_version=operation.version,
        )
    return operation


# ---------------------------------------------------------------------------
# CreateAsepticOperation — ASP-FR-004/009. Unsigned (no Document 106 row for creation).
# ---------------------------------------------------------------------------


class CreateAsepticOperationCommand(CommandEnvelope):
    site_id: uuid.UUID
    area_id: uuid.UUID
    profile_version_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    batch_step_id: uuid.UUID | None = None
    sterile_input_refs: list[dict] = []
    equipment_ids: list[str] = []
    media_fill_reference: dict | None = None


async def create_operation(
    session: AsyncSession, cmd: CreateAsepticOperationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    profile = await session.get(AsepticProfileVersion, cmd.profile_version_id)
    if profile is None:
        raise NotFoundError("Aseptic profile version not found")

    operation = AsepticOperation(
        site_id=cmd.site_id, area_id=cmd.area_id, profile_version_id=cmd.profile_version_id,
        batch_id=cmd.batch_id, batch_step_id=cmd.batch_step_id,
        sterile_input_refs={"items": cmd.sterile_input_refs}, equipment_ids={"ids": cmd.equipment_ids},
        media_fill_reference=cmd.media_fill_reference, state="PREPARATION", version=1,
    )
    session.add(operation)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="aseptic_operation",
        aggregate_id=operation.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="AsepticOperationStarted",
        event_payload={"id": str(operation.id), "state": operation.state}, expected_version=None,
        command_type="CreateAsepticOperation",
    )


# ---------------------------------------------------------------------------
# Cross-module query interface (AG-02/AG-05) — callers outside this module (product_master's
# sterile_profile_id FK-check/picker, added 2026-09-07) resolve/list profiles through these two functions
# instead of importing AsepticProfileVersion and querying equipment.aseptic_profile_versions directly.
# ---------------------------------------------------------------------------


async def get_released_profile_version(session: AsyncSession, profile_version_id: uuid.UUID) -> AsepticProfileVersion | None:
    return await session.get(AsepticProfileVersion, profile_version_id)


async def list_profile_versions(session: AsyncSession, site_id: uuid.UUID) -> list[AsepticProfileVersion]:
    """Every state (RELEASED and SUPERSEDED) — the browsable list on `/aseptic`'s own page, so a
    superseded profile's history stays visible even though `list_released_profile_versions` below
    (the picker feed) excludes it."""
    return (
        (
            await session.execute(
                select(AsepticProfileVersion)
                .where(AsepticProfileVersion.site_id == site_id)
                .order_by(AsepticProfileVersion.profile_number, AsepticProfileVersion.version_no.desc())
            )
        )
        .scalars()
        .all()
    )


async def list_released_profile_versions(session: AsyncSession, site_id: uuid.UUID) -> list[AsepticProfileVersion]:
    return (
        (
            await session.execute(
                select(AsepticProfileVersion)
                .where(AsepticProfileVersion.site_id == site_id, AsepticProfileVersion.state == "RELEASED")
                .order_by(AsepticProfileVersion.profile_number, AsepticProfileVersion.version_no)
            )
        )
        .scalars()
        .all()
    )


# ---------------------------------------------------------------------------
# CreateAsepticProfileVersion — added 2026-09-07, project-owner-directed. Document 40's own 7-op API list
# (§6) declares no create/release operation for aseptic_profile_version either — `aseptic_models.py`'s own
# docstring calls it "seed-only", same precedent as `cleaning_procedure_version`/
# `process_cycle_profile_version`. It was genuinely uncreatable through the app (only the one seeded
# `ASP-PROC-001` row existed per site) and Product Master's `sterile_profile_id` picker needed real
# profiles to choose from beyond that single row — same "own considered create contract, not a guessed
# one" precedent SG-081 established for `warehouse_location.create`. Created directly at state=RELEASED
# (no draft/review stage — there is no transition endpoint for this record either, so a draft row would
# be permanently stuck); no signature (Document 106 has no row for it, same "row absent, not optional"
# precedent as every other unsigned create in this module).
# ---------------------------------------------------------------------------


class CreateAsepticProfileVersionCommand(CommandEnvelope):
    site_id: uuid.UUID
    profile_number: str
    version_no: int = 1
    product_id: uuid.UUID | None = None
    required_area_classification: str | None = None
    personnel_qualifications: dict | None = None
    sterile_input_requirements: dict | None = None
    intervention_catalogue: dict | None = None
    hold_time_rules: dict | None = None
    em_dependencies: dict | None = None
    filter_sterilization_requirements: dict | None = None
    release_blockers: dict | None = None
    validation_reference: str | None = None


async def create_profile_version(
    session: AsyncSession, cmd: CreateAsepticProfileVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.profile_number.strip():
        raise ValidationFailedError("profile_number is required")

    # Matches the DB's own UniqueConstraint("profile_number", "version_no") — table-wide, not per-site.
    duplicate = (
        await session.execute(
            select(AsepticProfileVersion).where(
                AsepticProfileVersion.profile_number == cmd.profile_number,
                AsepticProfileVersion.version_no == cmd.version_no,
            )
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise ValidationFailedError(
            "A sterile process profile with this profile number and version already exists",
            existing_id=str(duplicate.id),
        )

    profile = AsepticProfileVersion(
        site_id=cmd.site_id,
        profile_number=cmd.profile_number,
        version_no=cmd.version_no,
        product_id=cmd.product_id,
        required_area_classification=cmd.required_area_classification,
        personnel_qualifications=cmd.personnel_qualifications,
        sterile_input_requirements=cmd.sterile_input_requirements,
        intervention_catalogue=cmd.intervention_catalogue,
        hold_time_rules=cmd.hold_time_rules,
        em_dependencies=cmd.em_dependencies,
        filter_sterilization_requirements=cmd.filter_sterilization_requirements,
        release_blockers=cmd.release_blockers,
        validation_reference=cmd.validation_reference,
        state="RELEASED",
        version=1,
    )
    session.add(profile)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="aseptic_profile_version",
        aggregate_id=profile.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="AsepticProfileVersionCreated",
        event_payload={"id": str(profile.id), "profile_number": profile.profile_number, "version_no": profile.version_no},
        expected_version=None, command_type="CreateAsepticProfileVersion",
    )


# ---------------------------------------------------------------------------
# SupersedeAsepticProfileVersion — added 2026-09-07, project-owner-directed follow-up to
# CreateAsepticProfileVersion above (SG-176). This is the "update"/"delete" equivalent for a RELEASED
# sterile process profile: this record's content is never edited or removed in place (AG-08/DATA-FR-017,
# same restraint as ProductVersion/DdcpProfileVersion), so a change instead creates a new version
# (`version_no + 1`, same `profile_number`/`site_id` — those are identity fields, not editable, same
# "wholesale field replace, identity fixed" precedent as `product_master.update_draft`) and marks the
# previous version SUPERSEDED. A SUPERSEDED row is immediately excluded from `list_released_profile_versions`
# (state != "RELEASED") and from `get_released_profile_version`'s own state check callers (product_master's
# `_validate_sterile_profile`) — so it drops out of every picker without ever being deleted, same
# "supersede is this app's delete" pattern DdcpProfileVersion's own release-time supersession already
# established (`ddcp/commands.py::release_injectable_profile_version`).
# ---------------------------------------------------------------------------


class SupersedeAsepticProfileVersionCommand(CommandEnvelope):
    previous_profile_version_id: uuid.UUID
    expected_version: int
    product_id: uuid.UUID | None = None
    required_area_classification: str | None = None
    personnel_qualifications: dict | None = None
    sterile_input_requirements: dict | None = None
    intervention_catalogue: dict | None = None
    hold_time_rules: dict | None = None
    em_dependencies: dict | None = None
    filter_sterilization_requirements: dict | None = None
    release_blockers: dict | None = None
    validation_reference: str | None = None


async def supersede_profile_version(
    session: AsyncSession, cmd: SupersedeAsepticProfileVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(
        select(AsepticProfileVersion).where(AsepticProfileVersion.id == cmd.previous_profile_version_id).with_for_update()
    )
    previous = result.scalar_one_or_none()
    if previous is None:
        raise NotFoundError("Sterile process profile not found")
    if previous.version != cmd.expected_version:
        raise StaleVersionError(
            "Sterile process profile was modified by another actor since it was read",
            expected_version=cmd.expected_version, current_version=previous.version,
        )
    if previous.state != "RELEASED":
        raise ValidationFailedError(
            "Only a RELEASED sterile process profile can be superseded", current_state=previous.state,
        )

    new_version_no = previous.version_no + 1
    duplicate = (
        await session.execute(
            select(AsepticProfileVersion).where(
                AsepticProfileVersion.profile_number == previous.profile_number,
                AsepticProfileVersion.version_no == new_version_no,
            )
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise ValidationFailedError(
            "A sterile process profile with this profile number and version already exists",
            existing_id=str(duplicate.id),
        )

    new_profile = AsepticProfileVersion(
        site_id=previous.site_id,
        profile_number=previous.profile_number,
        version_no=new_version_no,
        product_id=cmd.product_id,
        required_area_classification=cmd.required_area_classification,
        personnel_qualifications=cmd.personnel_qualifications,
        sterile_input_requirements=cmd.sterile_input_requirements,
        intervention_catalogue=cmd.intervention_catalogue,
        hold_time_rules=cmd.hold_time_rules,
        em_dependencies=cmd.em_dependencies,
        filter_sterilization_requirements=cmd.filter_sterilization_requirements,
        release_blockers=cmd.release_blockers,
        validation_reference=cmd.validation_reference,
        state="RELEASED",
        supersedes_profile_version_id=previous.id,
        version=1,
    )
    session.add(new_profile)
    await session.flush()

    old_state = previous.state
    previous.state = "SUPERSEDED"
    previous.version += 1

    correlation_id = uuid.uuid4()
    await write_audit_event(
        session, site_id=previous.site_id, aggregate_type="aseptic_profile_version", aggregate_id=previous.id,
        aggregate_version=previous.version, action="Changed", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": "SUPERSEDED", "superseded_by": str(new_profile.id)},
    )
    await write_outbox_event(
        session, event_type="AsepticProfileVersionSuperseded", aggregate_type="aseptic_profile_version",
        aggregate_id=previous.id, aggregate_version=previous.version,
        payload={"id": str(previous.id), "superseded_by": str(new_profile.id)}, correlation_id=correlation_id,
    )

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=new_profile.site_id, aggregate_type="aseptic_profile_version",
        aggregate_id=new_profile.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="AsepticProfileVersionCreated",
        event_payload={
            "id": str(new_profile.id), "profile_number": new_profile.profile_number,
            "version_no": new_profile.version_no, "supersedes_profile_version_id": str(previous.id),
        },
        expected_version=None, command_type="SupersedeAsepticProfileVersion",
    )


# ---------------------------------------------------------------------------
# Readiness composition — ASP-FR-005/006/007/008. The cross-module payoff: real reads against Document 41
# (EM area readiness), Document 39 (line clearance), Document 38 (equipment eligibility) and Document 42
# (sterile input status), not stubs.
# ---------------------------------------------------------------------------


async def _compute_readiness(session: AsyncSession, operation: AsepticOperation) -> dict:
    blockers: list[dict] = []

    em_readiness = await em_commands.get_area_readiness(session, operation.area_id)
    if not em_readiness["ready"]:
        blockers.append({"code": "ASEPTIC_AREA_NOT_READY", "message": f"EM area status is {em_readiness['status']}"})

    line_clearance = await cleaning_commands.get_area_line_clearance_status(session, operation.area_id)
    if not line_clearance["cleared"]:
        blockers.append({"code": "ASEPTIC_AREA_NOT_READY", "message": f"Line clearance state is {line_clearance['state']}"})

    equipment_checks = []
    for eq_id in (operation.equipment_ids or {}).get("ids", []):
        eligibility = await equipment_commands.get_eligibility(session, uuid.UUID(eq_id))
        equipment_checks.append(eligibility)
        if not eligibility["eligible"]:
            blockers.append({"code": "STERILIZATION_STATUS_INVALID", "message": f"Equipment {eq_id} is not eligible", "reasons": eligibility["reasons"]})

    sterile_input_checks = []
    for ref in (operation.sterile_input_refs or {}).get("items", []):
        item_status = await sterilization_commands.get_item_status(session, uuid.UUID(ref["item_id"]))
        sterile_input_checks.append(item_status)
        eligible = item_status.get("sterile_status") == "eligible" or item_status.get("state") == "ACCEPTED"
        if not eligible:
            blockers.append({"code": "STERILE_COMPONENT_INELIGIBLE", "message": f"Sterile input {ref['item_id']} is not eligible"})

    return {
        "operation_id": str(operation.id),
        "area_id": str(operation.area_id),
        "ready": not blockers,
        "blockers": blockers,
        "em_readiness": em_readiness,
        "line_clearance": line_clearance,
        "equipment_checks": equipment_checks,
        "sterile_input_checks": sterile_input_checks,
    }


async def get_readiness(session: AsyncSession, operation_id: uuid.UUID) -> dict:
    operation = await session.get(AsepticOperation, operation_id)
    if operation is None:
        raise NotFoundError("Aseptic operation not found")
    return await _compute_readiness(session, operation)


# ---------------------------------------------------------------------------
# StartOperation — Document 106 row 113. Production Supervisor or qualified issuer, no independence.
# Refuses to start unless the full readiness composition above passes (Codex rule: never start with
# failed area readiness).
# ---------------------------------------------------------------------------


class StartOperationCommand(CommandEnvelope):
    operation_id: uuid.UUID
    expected_version: int
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def start_operation(
    session: AsyncSession, cmd: StartOperationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    operation = await _load_operation_for_update(session, cmd.operation_id, cmd.expected_version)
    if operation.state != "PREPARATION":
        raise InvalidTransitionError("Only a preparation-stage operation can be started", current_state=operation.state)

    readiness = await _compute_readiness(session, operation)
    if not readiness["ready"]:
        first = readiness["blockers"][0]
        if first["code"] == "STERILE_COMPONENT_INELIGIBLE":
            raise SterileComponentIneligibleError(first["message"], blockers=readiness["blockers"])
        raise AsepticAreaNotReadyError(first["message"], blockers=readiness["blockers"])

    signature_id = await _resolve_signature(
        session, record_type="aseptic_operation", action="start", actor_user_id=actor_user_id,
        record_version=operation.version, record_hash=operation_record_hash(operation),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = operation.state
    operation.state = "EXECUTION"
    operation.started_at = datetime.now(timezone.utc)
    operation.started_by_user_id = actor_user_id
    operation.readiness_snapshot = readiness
    operation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=operation.site_id, aggregate_type="aseptic_operation",
        aggregate_id=operation.id, version=operation.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_state=old_state, event_type="AsepticOperationStarted", event_payload={"id": str(operation.id), "state": operation.state},
        expected_version=cmd.expected_version, command_type="StartOperation", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------
# RecordIntervention — ASP-FR-010/011/012. Unsigned. `planned=False` holds the operation and always
# requires a deviation (Codex rule: never hide an unplanned intervention).
# ---------------------------------------------------------------------------


class RecordInterventionCommand(CommandEnvelope):
    operation_id: uuid.UUID
    expected_version: int
    intervention_type: str
    planned: bool = True
    started_at: datetime | None = None
    ended_at: datetime | None = None
    location: str | None = None
    reason: str | None = None
    impacted_unit_scope: dict | None = None
    evidence_ref: dict | None = None


async def record_intervention(
    session: AsyncSession, cmd: RecordInterventionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.intervention_type not in INTERVENTION_TYPES:
        raise ValidationFailedError("Unrecognized intervention_type", allowed=list(INTERVENTION_TYPES))

    operation = await _load_operation_for_update(session, cmd.operation_id, cmd.expected_version)
    if operation.state not in ("EXECUTION", "HOLD"):
        raise InvalidTransitionError("Interventions can only be recorded during execution", current_state=operation.state)
    if not cmd.planned and not cmd.reason:
        raise ValidationFailedError("reason is required for an unplanned intervention")

    intervention = AsepticIntervention(
        operation_id=operation.id, intervention_type=cmd.intervention_type, planned=cmd.planned,
        operator_user_id=actor_user_id, started_at=cmd.started_at, ended_at=cmd.ended_at,
        location=cmd.location, reason=cmd.reason, impacted_unit_scope=cmd.impacted_unit_scope,
        evidence_ref=cmd.evidence_ref, requires_deviation=not cmd.planned, version=1,
    )
    session.add(intervention)
    await session.flush()

    old_state = operation.state
    if not cmd.planned:
        operation.state = "HOLD"
        operation.requires_deviation = True
        event_type = "UnplannedInterventionDetected"
    else:
        event_type = "AsepticInterventionRecorded"
    operation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=operation.site_id, aggregate_type="aseptic_operation",
        aggregate_id=operation.id, version=operation.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type=event_type,
        event_payload={"id": str(operation.id), "intervention_id": str(intervention.id), "state": operation.state},
        expected_version=cmd.expected_version, command_type="RecordIntervention",
    )


# ---------------------------------------------------------------------------
# RecordEvent — ASP-FR-021/022/025. Unsigned. `severity="critical"` holds the operation (an EM/HVAC
# excursion or operator/gown breach during execution).
# ---------------------------------------------------------------------------


class RecordEventCommand(CommandEnvelope):
    operation_id: uuid.UUID
    expected_version: int
    event_type: str
    source: str | None = None
    severity: str = "info"
    payload: dict | None = None


async def record_event(
    session: AsyncSession, cmd: RecordEventCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.severity not in EVENT_SEVERITIES:
        raise ValidationFailedError("Unrecognized severity", allowed=list(EVENT_SEVERITIES))

    operation = await _load_operation_for_update(session, cmd.operation_id, cmd.expected_version)
    if operation.state not in ("EXECUTION", "HOLD"):
        raise InvalidTransitionError("Events can only be recorded during execution", current_state=operation.state)

    event = AsepticEventTimeline(
        operation_id=operation.id, event_type=cmd.event_type, source=cmd.source,
        severity=cmd.severity, payload=cmd.payload,
    )
    session.add(event)
    await session.flush()

    old_state = operation.state
    if cmd.severity == "critical":
        operation.state = "HOLD"
        operation.requires_deviation = True
        outbox_event_type = "AsepticEnvironmentExcursionDetected"
    else:
        outbox_event_type = "AsepticInterventionRecorded"
    operation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=operation.site_id, aggregate_type="aseptic_operation",
        aggregate_id=operation.id, version=operation.version, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type=outbox_event_type,
        event_payload={"id": str(operation.id), "event_id": str(event.id), "state": operation.state},
        expected_version=cmd.expected_version, command_type="RecordEvent",
    )


# ---------------------------------------------------------------------------
# CompleteOperation — Document 106 row 112. Qualified performer, no independence required unless flagged
# critical (same conditional-reason restraint as cleaning_execution.complete -- `SignaturePolicy.
# reason_required` is a flat boolean, enforced conditionally in code instead). Refuses to complete while
# `requires_deviation` is unresolved (ASP-FR-026, Codex rule: never complete while a critical sterile-
# status dependency is unresolved).
# ---------------------------------------------------------------------------


class CompleteOperationCommand(CommandEnvelope):
    operation_id: uuid.UUID
    expected_version: int
    critical: bool = False
    reason: str | None = None
    qc_test_order_id: uuid.UUID | None = None
    qc_result_id: uuid.UUID | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def complete_operation(
    session: AsyncSession, cmd: CompleteOperationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    operation = await _load_operation_for_update(session, cmd.operation_id, cmd.expected_version)
    if operation.state != "EXECUTION":
        raise InvalidTransitionError("Only an in-execution operation can be completed", current_state=operation.state)
    if operation.requires_deviation:
        raise ValidationFailedError("Operation cannot complete while an unresolved deviation is required (ASP-FR-026)")
    if cmd.critical and not cmd.reason:
        raise ValidationFailedError("reason is required to complete a critical aseptic operation")

    # ASP-FR-019: captured linkage only -- existence-checked so the reference is real, not content-
    # validated against the test order's/result's own outcome (that cross-check and any resulting
    # release-blocker wiring has no established precedent anywhere in this codebase yet, SG-117).
    if cmd.qc_test_order_id is not None and await session.get(QcTestOrder, cmd.qc_test_order_id) is None:
        raise NotFoundError("QC test order not found")
    if cmd.qc_result_id is not None and await session.get(QcResult, cmd.qc_result_id) is None:
        raise NotFoundError("QC result not found")

    signature_id = await _resolve_signature(
        session, record_type="aseptic_operation", action="complete", actor_user_id=actor_user_id,
        record_version=operation.version, record_hash=operation_record_hash(operation),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = operation.state
    operation.state = "ASEPTIC_COMPLETE"
    operation.completed_at = datetime.now(timezone.utc)
    operation.completed_by_user_id = actor_user_id
    operation.complete_signature_id = signature_id
    if cmd.qc_test_order_id is not None:
        operation.qc_test_order_id = cmd.qc_test_order_id
    if cmd.qc_result_id is not None:
        operation.qc_result_id = cmd.qc_result_id
    operation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=operation.site_id, aggregate_type="aseptic_operation",
        aggregate_id=operation.id, version=operation.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="AsepticOperationCompleted",
        event_payload={"id": str(operation.id), "state": operation.state}, expected_version=cmd.expected_version,
        command_type="CompleteOperation", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------
# Read query — GET /aseptic/v1/operations/{id}/review-summary. ASP-FR-025/027: overlays interventions and
# events for QA review-by-exception. A read composition, not a signed action (no Document 106 row exists
# for a "QA review" action on this document).
# ---------------------------------------------------------------------------


async def get_review_summary(session: AsyncSession, operation_id: uuid.UUID) -> dict:
    operation = await session.get(AsepticOperation, operation_id)
    if operation is None:
        raise NotFoundError("Aseptic operation not found")

    interventions = (
        await session.execute(
            select(AsepticIntervention).where(AsepticIntervention.operation_id == operation_id).order_by(AsepticIntervention.created_at)
        )
    ).scalars().all()
    events = (
        await session.execute(
            select(AsepticEventTimeline).where(AsepticEventTimeline.operation_id == operation_id).order_by(AsepticEventTimeline.occurred_at)
        )
    ).scalars().all()

    return {
        "operation_id": str(operation_id),
        "state": operation.state,
        "requires_deviation": operation.requires_deviation,
        "unplanned_intervention_count": sum(1 for i in interventions if not i.planned),
        "critical_event_count": sum(1 for e in events if e.severity == "critical"),
        "interventions": [
            {"id": str(i.id), "intervention_type": i.intervention_type, "planned": i.planned, "requires_deviation": i.requires_deviation}
            for i in interventions
        ],
        "events": [
            {"id": str(e.id), "event_type": e.event_type, "severity": e.severity, "occurred_at": e.occurred_at.isoformat()}
            for e in events
        ],
    }
