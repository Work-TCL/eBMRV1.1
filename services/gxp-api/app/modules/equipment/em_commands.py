"""Document 41 (SPEC-EQP-004) — exactly the 8 declared operations (§6). `em_location` is seed-only (no
create endpoint); `em_program_version` has a real, unsigned create command.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.equipment import commands as equipment_commands
from app.modules.equipment.em_models import ALERT_ACTION_STATUSES, EmExcursion, EmLocation, EmProgramVersion, EmSampleOrReading
from app.modules.equipment.cleaning_models import EquipmentArea
from app.modules.iam.models import User
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    EmInstrumentIneligibleError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def em_sample_record_hash(sample: EmSampleOrReading) -> str:
    return sha256_hex({"id": str(sample.id), "version": sample.version, "state": sample.state})


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


async def _load_sample_for_update(session: AsyncSession, sample_id: uuid.UUID, expected_version: int) -> EmSampleOrReading:
    result = await session.execute(select(EmSampleOrReading).where(EmSampleOrReading.id == sample_id).with_for_update())
    sample = result.scalar_one_or_none()
    if sample is None:
        raise NotFoundError("EM sample/reading not found")
    if sample.version != expected_version:
        raise StaleVersionError(
            "EM sample/reading was modified by another actor since it was read",
            expected_version=expected_version, current_version=sample.version,
        )
    return sample


# ---------------------------------------------------------------------------
# CreateEmProgram — EM-FR-001. Unsigned (no Document 106 row).
# ---------------------------------------------------------------------------


class CreateEmProgramCommand(CommandEnvelope):
    site_id: uuid.UUID
    program_number: str
    monitoring_types: dict | None = None
    method_version: str | None = None
    frequency: dict | None = None
    alert_limits: dict | None = None
    action_limits: dict | None = None
    operation_shift_coverage: dict | None = None
    review_trend_rules: dict | None = None


async def create_em_program(
    session: AsyncSession, cmd: CreateEmProgramCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.program_number.strip():
        raise ValidationFailedError("program_number is required")

    program = EmProgramVersion(
        site_id=cmd.site_id, program_number=cmd.program_number, version_no=1,
        monitoring_types=cmd.monitoring_types, method_version=cmd.method_version, frequency=cmd.frequency,
        alert_limits=cmd.alert_limits, action_limits=cmd.action_limits,
        operation_shift_coverage=cmd.operation_shift_coverage, review_trend_rules=cmd.review_trend_rules,
        state="RELEASED", version=1,
    )
    session.add(program)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="em_program_version",
        aggregate_id=program.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="EMTaskScheduled", event_payload={"id": str(program.id)},
        expected_version=None, command_type="CreateEmProgram",
    )


# ---------------------------------------------------------------------------
# CreateEmTask / CollectEmTask — EM-FR-005/006/008.
# ---------------------------------------------------------------------------


class CreateEmTaskCommand(CommandEnvelope):
    site_id: uuid.UUID
    program_version_id: uuid.UUID
    location_id: uuid.UUID
    monitoring_type: str
    batch_id: uuid.UUID | None = None
    aseptic_operation_id: uuid.UUID | None = None


async def create_em_task(
    session: AsyncSession, cmd: CreateEmTaskCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    program = await session.get(EmProgramVersion, cmd.program_version_id)
    if program is None:
        raise NotFoundError("EM program version not found")
    location = await session.get(EmLocation, cmd.location_id)
    if location is None:
        raise NotFoundError("EM location not found")

    sample = EmSampleOrReading(
        site_id=cmd.site_id, program_version_id=cmd.program_version_id, location_id=cmd.location_id,
        monitoring_type=cmd.monitoring_type, batch_id=cmd.batch_id, aseptic_operation_id=cmd.aseptic_operation_id,
        state="SAMPLE_TASK", version=1,
    )
    session.add(sample)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="em_sample_or_reading",
        aggregate_id=sample.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="EMTaskScheduled", event_payload={"id": str(sample.id)},
        expected_version=None, command_type="CreateEmTask",
    )


class CollectEmTaskCommand(CommandEnvelope):
    sample_id: uuid.UUID
    expected_version: int
    instrument_or_media_ref: dict | None = None
    instrument_equipment_id: uuid.UUID | None = None
    media_reagent_ref: dict | None = None


async def collect_em_task(
    session: AsyncSession, cmd: CollectEmTaskCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    sample = await _load_sample_for_update(session, cmd.sample_id, cmd.expected_version)
    if sample.state != "SAMPLE_TASK":
        raise InvalidTransitionError("Only a scheduled task can be collected", current_state=sample.state)

    # EM-FR-006: where a specific instrument/sensor is used to collect this sample, it must be currently
    # qualified/calibrated (Document 38's own eligibility gate, same reuse precedent as CLN-FR-019).
    # instrument_equipment_id is optional -- not every monitoring_type uses a discrete calibrated
    # instrument (e.g. settle_plate/personnel sampling has none), so its absence is not itself a failure.
    if cmd.instrument_equipment_id is not None:
        eligibility = await equipment_commands.get_eligibility(session, cmd.instrument_equipment_id)
        if not eligibility["eligible"]:
            raise EmInstrumentIneligibleError(
                "Instrument is not currently eligible for EM collection",
                equipment_id=str(cmd.instrument_equipment_id), reasons=eligibility["reasons"],
            )

    old_state = sample.state
    sample.sampled_at = datetime.now(timezone.utc)
    sample.instrument_or_media_ref = cmd.instrument_or_media_ref
    sample.media_reagent_ref = cmd.media_reagent_ref
    sample.operator_user_id = actor_user_id
    sample.state = "COLLECTED"
    sample.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=sample.site_id, aggregate_type="em_sample_or_reading",
        aggregate_id=sample.id, version=sample.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_state=old_state, event_type="EMSampleCollected", event_payload={"id": str(sample.id), "state": sample.state},
        expected_version=cmd.expected_version, command_type="CollectEmTask",
    )


# ---------------------------------------------------------------------------
# RecordEmResult — Document 106 row 114. Auto-creates an EmExcursion when action_excursion (EM-FR-012).
# `sample_id=None` creates a fresh direct result (e.g. a continuous-sensor manual entry, EM-FR-015),
# skipping the SAMPLE_TASK/COLLECTED phases.
# ---------------------------------------------------------------------------


class RecordEmResultCommand(CommandEnvelope):
    site_id: uuid.UUID | None = None
    sample_id: uuid.UUID | None = None
    expected_version: int | None = None
    program_version_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    monitoring_type: str | None = None
    result: dict
    alert_action_status: str
    incubation_conditions: dict | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def record_em_result(
    session: AsyncSession, cmd: RecordEmResultCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.alert_action_status not in ALERT_ACTION_STATUSES:
        raise ValidationFailedError("Unrecognized alert_action_status", allowed=list(ALERT_ACTION_STATUSES))

    if cmd.sample_id is not None:
        if cmd.expected_version is None:
            raise ValidationFailedError("expected_version is required when sample_id is provided")
        sample = await _load_sample_for_update(session, cmd.sample_id, cmd.expected_version)
        if sample.state not in ("SAMPLE_TASK", "COLLECTED"):
            raise InvalidTransitionError("Only a task pending a result can have one recorded", current_state=sample.state)
        old_state = sample.state
        expected_version = cmd.expected_version
    else:
        if cmd.site_id is None or cmd.program_version_id is None or cmd.location_id is None or cmd.monitoring_type is None:
            raise ValidationFailedError("site_id, program_version_id, location_id and monitoring_type are required when sample_id is not provided")
        sample = EmSampleOrReading(
            site_id=cmd.site_id, program_version_id=cmd.program_version_id, location_id=cmd.location_id,
            monitoring_type=cmd.monitoring_type, state="COLLECTED", version=1,
        )
        session.add(sample)
        await session.flush()
        old_state = None
        expected_version = None

    signature_id = await _resolve_signature(
        session, record_type="em_sample_or_reading", action="record_result", actor_user_id=actor_user_id,
        record_version=sample.version, record_hash=em_sample_record_hash(sample),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    sample.result = cmd.result
    sample.alert_action_status = cmd.alert_action_status
    if cmd.incubation_conditions is not None:
        sample.incubation_conditions = cmd.incubation_conditions
    sample.state = "RESULT_PENDING"
    sample.operator_user_id = sample.operator_user_id or actor_user_id
    sample.version += 1

    excursion_id = None
    if cmd.alert_action_status == "action_excursion":
        location = await session.get(EmLocation, sample.location_id)
        excursion = EmExcursion(
            site_id=sample.site_id, sample_id=sample.id, area_id=location.area_id, requires_deviation=True, version=1,
        )
        session.add(excursion)
        await session.flush()
        excursion_id = excursion.id
        sample.requires_deviation = True

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=sample.site_id, aggregate_type="em_sample_or_reading",
        aggregate_id=sample.id, version=sample.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_state=old_state,
        event_type="EMActionLimitExceeded" if cmd.alert_action_status == "action_excursion" else (
            "EMAlertTriggered" if cmd.alert_action_status == "alert" else "EMResultRecorded"
        ),
        event_payload={"id": str(sample.id), "alert_action_status": cmd.alert_action_status, "excursion_id": str(excursion_id) if excursion_id else None},
        expected_version=expected_version, command_type="RecordEmResult", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------
# ReviewEmResult — Document 106 row 115. MUST be independent of the performer (SIG-FR-018).
# ---------------------------------------------------------------------------


class ReviewEmResultCommand(CommandEnvelope):
    sample_id: uuid.UUID
    expected_version: int
    reason: str | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def review_em_result(
    session: AsyncSession, cmd: ReviewEmResultCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    sample = await _load_sample_for_update(session, cmd.sample_id, cmd.expected_version)
    if sample.state != "RESULT_PENDING":
        raise InvalidTransitionError("Only a result pending review can be reviewed", current_state=sample.state)
    if sample.operator_user_id == actor_user_id:
        raise ValidationFailedError("Reviewer must be independent of the performer (SIG-FR-018)")

    signature_id = await _resolve_signature(
        session, record_type="em_sample_or_reading", action="review", actor_user_id=actor_user_id,
        record_version=sample.version, record_hash=em_sample_record_hash(sample),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = sample.state
    sample.reviewer_user_id = actor_user_id
    sample.state = "REVIEWED"
    sample.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=sample.site_id, aggregate_type="em_sample_or_reading",
        aggregate_id=sample.id, version=sample.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="EMResultRecorded",
        event_payload={"id": str(sample.id), "state": sample.state}, expected_version=cmd.expected_version,
        command_type="ReviewEmResult", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------
# RecordExcursionImpact — EM-FR-012/019/021. Unsigned (no Document 106 row). Never overwrites the
# original excursion trigger -- only adds impact/disposition data (EM-FR-022: resampling doesn't erase it).
# ---------------------------------------------------------------------------


class RecordExcursionImpactCommand(CommandEnvelope):
    excursion_id: uuid.UUID
    expected_version: int
    affected_time_start: datetime | None = None
    affected_time_end: datetime | None = None
    affected_batch_ids: dict | None = None
    organism_details: dict | None = None
    disposition: str | None = None


async def record_excursion_impact(
    session: AsyncSession, cmd: RecordExcursionImpactCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(EmExcursion).where(EmExcursion.id == cmd.excursion_id).with_for_update())
    excursion = result.scalar_one_or_none()
    if excursion is None:
        raise NotFoundError("EM excursion not found")
    if excursion.version != cmd.expected_version:
        raise StaleVersionError(
            "EM excursion was modified by another actor since it was read",
            expected_version=cmd.expected_version, current_version=excursion.version,
        )

    excursion.affected_time_start = cmd.affected_time_start or excursion.affected_time_start
    excursion.affected_time_end = cmd.affected_time_end or excursion.affected_time_end
    excursion.affected_batch_ids = cmd.affected_batch_ids or excursion.affected_batch_ids
    excursion.organism_details = cmd.organism_details or excursion.organism_details
    excursion.disposition = cmd.disposition or excursion.disposition
    excursion.impact_assessed_by_user_id = actor_user_id
    excursion.impact_assessed_at = datetime.now(timezone.utc)
    excursion.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=excursion.site_id, aggregate_type="em_excursion",
        aggregate_id=excursion.id, version=excursion.version, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=None, event_type="EMExcursionClosed" if cmd.disposition else "EMActionLimitExceeded",
        event_payload={"id": str(excursion.id), "disposition": excursion.disposition},
        expected_version=cmd.expected_version, command_type="RecordExcursionImpact",
    )


# ---------------------------------------------------------------------------
# Read queries — EM-FR-020 (area readiness -- the Document 40 cross-module payoff) / EM-FR-017 (trends).
# ---------------------------------------------------------------------------


async def get_area_readiness(session: AsyncSession, area_id: uuid.UUID) -> dict:
    """EM-FR-020: derived from current program/tasks/excursions, never a manual toggle."""
    area = await session.get(EquipmentArea, area_id)
    if area is None:
        raise NotFoundError("Equipment area not found")

    open_excursions = (
        await session.execute(
            select(EmExcursion).where(EmExcursion.area_id == area_id, EmExcursion.disposition.is_(None))
        )
    ).scalars().all()

    location_ids = (
        await session.execute(select(EmLocation.id).where(EmLocation.area_id == area_id))
    ).scalars().all()
    recent_alerts = []
    if location_ids:
        recent_alerts = (
            await session.execute(
                select(EmSampleOrReading)
                .where(EmSampleOrReading.location_id.in_(location_ids), EmSampleOrReading.alert_action_status == "alert")
                .order_by(EmSampleOrReading.created_at.desc())
                .limit(5)
            )
        ).scalars().all()

    if open_excursions:
        status = "HOLD"
    elif recent_alerts:
        status = "WARNING"
    else:
        status = "READY"

    return {
        "area_id": str(area_id),
        "status": status,
        "ready": status == "READY",
        "open_excursion_count": len(open_excursions),
        "recent_alert_count": len(recent_alerts),
    }


async def get_trends(session: AsyncSession, location_id: uuid.UUID, monitoring_type: str | None = None) -> dict:
    """EM-FR-017/018 (partial): raw result history by location -- trend baseline/statistical detection is
    not built this pass (SPEC_GAP)."""
    stmt = select(EmSampleOrReading).where(EmSampleOrReading.location_id == location_id)
    if monitoring_type:
        stmt = stmt.where(EmSampleOrReading.monitoring_type == monitoring_type)
    rows = (await session.execute(stmt.order_by(EmSampleOrReading.created_at.desc()).limit(50))).scalars().all()
    return {
        "location_id": str(location_id),
        "samples": [
            {"id": str(r.id), "monitoring_type": r.monitoring_type, "result": r.result, "alert_action_status": r.alert_action_status, "created_at": r.created_at.isoformat()}
            for r in rows
        ],
    }
