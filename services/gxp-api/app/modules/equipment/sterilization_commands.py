"""Document 42 (SPEC-EQP-005) — exactly the 9 declared operations (§6). `POST /sterilization/v1/cycles`
and `POST /cip-sip/v1/cycles` both create a `ProcessCycle` row (distinguished by `process_type`), matching
the data model's single `process_cycle` entity.
"""

import uuid
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.equipment import commands as equipment_commands
from app.modules.equipment.sterilization_models import (
    INTEGRITY_TEST_PHASES,
    ProcessCycle,
    ProcessCycleProfileVersion,
    SterileFilterUse,
    SterilizationLoadItem,
)
from app.modules.iam.models import User
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    ReprocessingAuthorizationRequiredError,
    StaleVersionError,
    SterilizerIneligibleError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def cycle_record_hash(cycle: ProcessCycle) -> str:
    return sha256_hex({"id": str(cycle.id), "version": cycle.version, "state": cycle.state})


def filter_use_record_hash(use: SterileFilterUse) -> str:
    return sha256_hex({"id": str(use.id), "version": use.version, "state": use.state})


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


async def _load_cycle_for_update(session: AsyncSession, cycle_id: uuid.UUID, expected_version: int) -> ProcessCycle:
    result = await session.execute(select(ProcessCycle).where(ProcessCycle.id == cycle_id).with_for_update())
    cycle = result.scalar_one_or_none()
    if cycle is None:
        raise NotFoundError("Process cycle not found")
    if cycle.version != expected_version:
        raise StaleVersionError(
            "Process cycle was modified by another actor since it was read",
            expected_version=expected_version, current_version=cycle.version,
        )
    return cycle


async def _load_filter_use_for_update(session: AsyncSession, use_id: uuid.UUID, expected_version: int) -> SterileFilterUse:
    result = await session.execute(select(SterileFilterUse).where(SterileFilterUse.id == use_id).with_for_update())
    use = result.scalar_one_or_none()
    if use is None:
        raise NotFoundError("Sterile filter use not found")
    if use.version != expected_version:
        raise StaleVersionError(
            "Sterile filter use was modified by another actor since it was read",
            expected_version=expected_version, current_version=use.version,
        )
    return use


# ---------------------------------------------------------------------------
# CreateProcessCycle / CreateCipSipCycle — STR-FR-004/005/006. Both endpoints create the same ProcessCycle
# entity, distinguished by process_type. Unsigned (no Document 106 row for creation).
# ---------------------------------------------------------------------------


class LoadItemInput(BaseModel):
    item_type: str
    item_reference: str
    position: str | None = None


class CreateProcessCycleCommand(CommandEnvelope):
    site_id: uuid.UUID
    process_type: str
    equipment_id: uuid.UUID
    profile_version_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    load_items: list[LoadItemInput] = []
    reprocessing_authorization_ref: dict | None = None


async def create_process_cycle(
    session: AsyncSession, cmd: CreateProcessCycleCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    profile = await session.get(ProcessCycleProfileVersion, cmd.profile_version_id)
    if profile is None:
        raise NotFoundError("Process cycle profile version not found")
    if not cmd.load_items:
        raise ValidationFailedError("load_items must not be empty")

    # STR-FR-005: the sterilizer/CIP-SIP equipment itself must be currently qualified/calibrated before a
    # cycle can start (Document 38's own eligibility gate, same reuse precedent as CLN-FR-019/EM-FR-006).
    eligibility = await equipment_commands.get_eligibility(session, cmd.equipment_id)
    if not eligibility["eligible"]:
        raise SterilizerIneligibleError(
            "Sterilizer/CIP-SIP equipment is not currently eligible", equipment_id=str(cmd.equipment_id),
            reasons=eligibility["reasons"],
        )

    # STR-FR-026: reprocessing a load that previously FAILED requires an explicit authorization reference
    # -- fail-closed on the already-declared REPROCESSING_AUTHORIZATION_REQUIRED rather than silently
    # allowing an uncontrolled rerun. "Same load" is read literally as sharing an item_reference with a
    # FAILED cycle's own load items; the reference itself is not validated against any specific QMS record
    # shape, since none exists yet to validate against (structurally required, not content-checked).
    incoming_refs = {item.item_reference for item in cmd.load_items}
    if incoming_refs:
        prior_failed = (
            await session.execute(
                select(SterilizationLoadItem.item_reference)
                .join(ProcessCycle, ProcessCycle.id == SterilizationLoadItem.cycle_id)
                .where(ProcessCycle.state == "FAILED", SterilizationLoadItem.item_reference.in_(incoming_refs))
            )
        ).scalars().all()
        if prior_failed and cmd.reprocessing_authorization_ref is None:
            raise ReprocessingAuthorizationRequiredError(
                "A prior cycle for this load failed; reprocessing requires an authorization reference",
                item_references=list(set(prior_failed)),
            )

    cycle = ProcessCycle(
        site_id=cmd.site_id, process_type=cmd.process_type, equipment_id=cmd.equipment_id,
        profile_version_id=cmd.profile_version_id, batch_id=cmd.batch_id,
        reprocessing_authorization_ref=cmd.reprocessing_authorization_ref, state="DRAFT", version=1,
    )
    session.add(cycle)
    await session.flush()

    for item in cmd.load_items:
        session.add(
            SterilizationLoadItem(
                cycle_id=cycle.id, item_type=item.item_type, item_reference=item.item_reference,
                position=item.position, version=1,
            )
        )

    # No dedicated "cycle created/drafted" event is declared in Document 42's own event list (§8) -- reuse
    # the closest declared event rather than invent one, same precedent as Document 38's create_equipment_
    # asset reusing "EquipmentInstalled".
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="process_cycle",
        aggregate_id=cycle.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="SterilizationCycleStarted",
        event_payload={"id": str(cycle.id), "process_type": cycle.process_type}, expected_version=None,
        command_type="CreateProcessCycle",
    )


# ---------------------------------------------------------------------------
# StartCycle — Document 106 row 118. Production Supervisor or qualified issuer, no independence.
# ---------------------------------------------------------------------------


class StartCycleCommand(CommandEnvelope):
    cycle_id: uuid.UUID
    expected_version: int
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def start_cycle(
    session: AsyncSession, cmd: StartCycleCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    cycle = await _load_cycle_for_update(session, cmd.cycle_id, cmd.expected_version)
    if cycle.state != "DRAFT":
        raise InvalidTransitionError("Only a draft cycle can be started", current_state=cycle.state)

    signature_id = await _resolve_signature(
        session, record_type="process_cycle", action="start", actor_user_id=actor_user_id,
        record_version=cycle.version, record_hash=cycle_record_hash(cycle),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = cycle.state
    cycle.state = "CYCLE_STARTED"
    cycle.started_at = datetime.now(timezone.utc)
    cycle.started_by_user_id = actor_user_id
    cycle.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cycle.site_id, aggregate_type="process_cycle",
        aggregate_id=cycle.id, version=cycle.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_state=old_state, event_type="SterilizationCycleStarted", event_payload={"id": str(cycle.id), "state": cycle.state},
        expected_version=cmd.expected_version, command_type="StartCycle", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------
# RecordCycleData — STR-FR-007/008/009. Never accepts an operator-asserted pass/fail (STR-FR-009) --
# only raw telemetry and a controller-reported `critical_alarm` flag, which immediately holds the cycle.
# ---------------------------------------------------------------------------


class RecordCycleDataCommand(CommandEnvelope):
    cycle_id: uuid.UUID
    expected_version: int
    controller_cycle_id: str | None = None
    parameter_data: dict | None = None
    alarm_data: dict | None = None
    indicator_results: dict | None = None
    critical_alarm: bool = False
    final: bool = False


async def record_cycle_data(
    session: AsyncSession, cmd: RecordCycleDataCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    cycle = await _load_cycle_for_update(session, cmd.cycle_id, cmd.expected_version)
    if cycle.state not in ("CYCLE_STARTED", "CYCLE_RUNNING"):
        raise InvalidTransitionError("Data can only be recorded while the cycle is running", current_state=cycle.state)

    old_state = cycle.state
    if cmd.controller_cycle_id:
        cycle.controller_cycle_id = cmd.controller_cycle_id
    if cmd.parameter_data:
        cycle.parameter_summary = {**(cycle.parameter_summary or {}), **cmd.parameter_data}
    if cmd.alarm_data:
        cycle.alarm_summary = {**(cycle.alarm_summary or {}), **cmd.alarm_data}
    if cmd.indicator_results:
        cycle.indicator_results = {**(cycle.indicator_results or {}), **cmd.indicator_results}

    if cmd.critical_alarm:
        cycle.critical_alarm = True
        cycle.requires_deviation = True
        cycle.state = "HOLD"
        event_type = "SterilizationCycleFailed"
    elif cmd.final:
        cycle.state = "REVIEW_PENDING"
        cycle.completed_at = datetime.now(timezone.utc)
        event_type = "SterilizationCycleCompleted"
    else:
        cycle.state = "CYCLE_RUNNING"
        event_type = "SterilizationCycleStarted"
    cycle.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cycle.site_id, aggregate_type="process_cycle",
        aggregate_id=cycle.id, version=cycle.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_state=old_state, event_type=event_type, event_payload={"id": str(cycle.id), "state": cycle.state},
        expected_version=cmd.expected_version, command_type="RecordCycleData",
    )


# ---------------------------------------------------------------------------
# ReviewCycle — Document 106 row 117. MUST be independent of the performer (started_by_user_id).
# Accept issues sterile status onto every load item (STR-FR-012). A cycle that ever raised critical_alarm
# cannot be accepted (Codex rule §15: never let a controller 'complete' equal accepted).
# ---------------------------------------------------------------------------


class ReviewCycleCommand(CommandEnvelope):
    cycle_id: uuid.UUID
    expected_version: int
    decision: str  # "accept" | "reject"
    reason: str | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def review_cycle(
    session: AsyncSession, cmd: ReviewCycleCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.decision not in ("accept", "reject"):
        raise ValidationFailedError("decision must be 'accept' or 'reject'")

    cycle = await _load_cycle_for_update(session, cmd.cycle_id, cmd.expected_version)
    if cycle.state not in ("REVIEW_PENDING", "HOLD"):
        raise InvalidTransitionError("Only a cycle pending review or on hold can be reviewed", current_state=cycle.state)
    if cycle.started_by_user_id == actor_user_id:
        raise ValidationFailedError("Reviewer must be independent of the performer who started the cycle (SIG-FR-018)")
    if cmd.decision == "accept" and cycle.critical_alarm:
        raise ValidationFailedError("A cycle that raised a critical alarm cannot be accepted")
    if cmd.decision == "reject" and not cmd.reason:
        raise ValidationFailedError("reason is required to reject a process cycle")

    signature_id = await _resolve_signature(
        session, record_type="process_cycle", action="review", actor_user_id=actor_user_id,
        record_version=cycle.version, record_hash=cycle_record_hash(cycle),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = cycle.state
    cycle.reviewer_user_id = actor_user_id
    cycle.review_signature_id = signature_id

    if cmd.decision == "accept":
        cycle.state = "ACCEPTED"
        profile = await session.get(ProcessCycleProfileVersion, cycle.profile_version_id)
        validity_hours = profile.sterile_status_validity_hours if profile else None
        expiry = (
            datetime.now(timezone.utc) + timedelta(hours=validity_hours) if validity_hours is not None else None
        )
        items = (
            await session.execute(select(SterilizationLoadItem).where(SterilizationLoadItem.cycle_id == cycle.id))
        ).scalars().all()
        for item in items:
            item.sterile_status = "eligible"
            item.sterile_status_expiry = expiry
            item.version += 1
        event_type = "SterilizationCycleAccepted"
    else:
        cycle.state = "FAILED"
        cycle.requires_deviation = True
        event_type = "SterilizationCycleFailed"
    cycle.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cycle.site_id, aggregate_type="process_cycle",
        aggregate_id=cycle.id, version=cycle.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type=event_type,
        event_payload={"id": str(cycle.id), "state": cycle.state}, expected_version=cmd.expected_version,
        command_type="ReviewCycle", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------
# InstallFilter / RecordFilterIntegrityTest / CompleteFilterUse — STR-FR-016..023. Only complete_filter_use
# (row 116) is signed; install/integrity-test capture are unsigned.
# ---------------------------------------------------------------------------


class InstallFilterCommand(CommandEnvelope):
    site_id: uuid.UUID
    filter_serial: str
    filter_lot: str | None = None
    filter_type: str | None = None
    manufacturer: str | None = None
    batch_id: uuid.UUID | None = None
    sterilization_cycle_id: uuid.UUID | None = None
    housing_location: str | None = None
    direction: str | None = None


async def install_filter(
    session: AsyncSession, cmd: InstallFilterCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.filter_serial.strip():
        raise ValidationFailedError("filter_serial is required")

    # STR-FR-022: reuse tracking, not reuse enforcement (the module's own long-standing precedent --
    # single-use remains the safe default only by omission of a limit, never guessed here). A prior
    # ACCEPTED use of the same physical filter (by filter_serial, scoped to this site) counts as one prior
    # reuse cycle; reuse_count is the count of those, computed at install time, never hand-set.
    prior_accepted_uses = (
        await session.execute(
            select(func.count())
            .select_from(SterileFilterUse)
            .where(SterileFilterUse.site_id == cmd.site_id, SterileFilterUse.filter_serial == cmd.filter_serial,
                   SterileFilterUse.state == "ACCEPTED")
        )
    ).scalar_one()

    use = SterileFilterUse(
        site_id=cmd.site_id, filter_serial=cmd.filter_serial, filter_lot=cmd.filter_lot,
        filter_type=cmd.filter_type, manufacturer=cmd.manufacturer, batch_id=cmd.batch_id,
        sterilization_cycle_id=cmd.sterilization_cycle_id, housing_location=cmd.housing_location,
        direction=cmd.direction, installed_by_user_id=actor_user_id, installed_at=datetime.now(timezone.utc),
        reuse_count=prior_accepted_uses, state="INSTALLED", version=1,
    )
    session.add(use)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="sterile_filter_use",
        aggregate_id=use.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="FilterInstalled", event_payload={"id": str(use.id), "state": use.state},
        expected_version=None, command_type="InstallFilter",
    )


class RecordFilterIntegrityTestCommand(CommandEnvelope):
    use_id: uuid.UUID
    expected_version: int
    phase: str  # "pre" | "post"
    result: str  # "pass" | "fail"
    test_ref: dict | None = None


async def record_filter_integrity_test(
    session: AsyncSession, cmd: RecordFilterIntegrityTestCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.phase not in INTEGRITY_TEST_PHASES:
        raise ValidationFailedError("Unrecognized phase", allowed=list(INTEGRITY_TEST_PHASES))
    if cmd.result not in ("pass", "fail"):
        raise ValidationFailedError("result must be 'pass' or 'fail'")

    use = await _load_filter_use_for_update(session, cmd.use_id, cmd.expected_version)
    old_state = use.state

    if cmd.phase == "pre":
        if use.state != "INSTALLED":
            raise InvalidTransitionError("Pre-use integrity test requires an installed filter", current_state=use.state)
        use.pre_use_integrity_result = cmd.result
        use.pre_use_integrity_ref = cmd.test_ref
        if cmd.result == "fail":
            use.state = "FAILED"
            use.requires_deviation = True
            event_type = "FilterIntegrityFailed"
        else:
            use.state = "IN_USE"
            event_type = "FilterIntegrityPassed"
    else:
        if use.state != "IN_USE":
            raise InvalidTransitionError("Post-use integrity test requires a filter in use", current_state=use.state)
        use.post_use_integrity_result = cmd.result
        use.post_use_integrity_ref = cmd.test_ref
        use.state = "POST_USE_TEST"
        if cmd.result == "fail":
            use.requires_deviation = True
        event_type = "FilterIntegrityPassed" if cmd.result == "pass" else "FilterIntegrityFailed"
    use.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=use.site_id, aggregate_type="sterile_filter_use",
        aggregate_id=use.id, version=use.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_state=old_state, event_type=event_type, event_payload={"id": str(use.id), "state": use.state, "phase": cmd.phase, "result": cmd.result},
        expected_version=cmd.expected_version, command_type="RecordFilterIntegrityTest",
    )


class CompleteFilterUseCommand(CommandEnvelope):
    use_id: uuid.UUID
    expected_version: int
    process_parameters: dict | None = None
    reason: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def complete_filter_use(
    session: AsyncSession, cmd: CompleteFilterUseCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    use = await _load_filter_use_for_update(session, cmd.use_id, cmd.expected_version)
    if use.state != "POST_USE_TEST":
        raise InvalidTransitionError("Only a filter with a recorded post-use test can be completed", current_state=use.state)

    signature_id = await _resolve_signature(
        session, record_type="sterile_filter_use", action="complete", actor_user_id=actor_user_id,
        record_version=use.version, record_hash=filter_use_record_hash(use),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = use.state
    use.process_parameters = cmd.process_parameters
    use.performer_user_id = actor_user_id
    use.state = "ACCEPTED" if use.post_use_integrity_result == "pass" else "FAILED"
    use.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=use.site_id, aggregate_type="sterile_filter_use",
        aggregate_id=use.id, version=use.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="FilterIntegrityPassed" if use.state == "ACCEPTED" else "FilterIntegrityFailed",
        event_payload={"id": str(use.id), "state": use.state}, expected_version=cmd.expected_version,
        command_type="CompleteFilterUse", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------
# Read query — GET /sterilization/v1/items/{id}/status. Polymorphic: tries a load item first, then a
# filter use (no separate 'item type' discriminator exists at the API boundary).
# ---------------------------------------------------------------------------


async def get_item_status(session: AsyncSession, item_id: uuid.UUID) -> dict:
    load_item = await session.get(SterilizationLoadItem, item_id)
    if load_item is not None:
        expired = (
            load_item.sterile_status_expiry is not None
            and datetime.now(timezone.utc) > load_item.sterile_status_expiry.replace(tzinfo=timezone.utc)
        )
        return {
            "item_id": str(item_id), "item_kind": "sterilization_load_item",
            "sterile_status": "expired" if expired else load_item.sterile_status,
            "sterile_status_expiry": load_item.sterile_status_expiry.isoformat() if load_item.sterile_status_expiry else None,
        }
    filter_use = await session.get(SterileFilterUse, item_id)
    if filter_use is not None:
        return {
            "item_id": str(item_id), "item_kind": "sterile_filter_use", "state": filter_use.state,
            "pre_use_integrity_result": filter_use.pre_use_integrity_result,
            "post_use_integrity_result": filter_use.post_use_integrity_result,
        }
    raise NotFoundError("No sterilization load item or filter use found for this id")
