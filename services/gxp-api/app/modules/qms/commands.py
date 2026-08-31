"""Document 26 (SPEC-QMS-001) — the buildable slice of Deviation & Investigation Management: the linear
OPEN -> TRIAGE -> CONTAINMENT -> INVESTIGATION -> IMPACT_ASSESSMENT -> DISPOSITION -> CLOSED pipeline Document
26 §4 describes, plus CLOSED -> REOPENED. Every state-changing operation matches the module's own 9-op API
list exactly; no additional operation is exposed (see models.py's module docstring and
docs/generated/18_SPEC_GAPS.md SG-059..SG-062 for what is deliberately not built this pass).

QA_REVIEW (named in Document 26 §4) is not a separately reachable persisted state -- there is no
dedicated "enter QA review" operation in the 9-op API list, only `close`. Exactly like release_scope's
PENDING_SIGNATURE (SG-055's reasoning), the Document 106 signature ceremony for closure is synchronous
inside close_deviation() itself; DISPOSITION transitions straight to CLOSED once the ceremony completes.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.qms.models import (
    ALLOWED_TRANSITIONS,
    DISPOSITION_CODES,
    SOURCE_TYPES,
    DeviationImpactLink,
    DeviationRecord,
)
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    ContainmentRequiredError,
    DeviationSourceInvalidError,
    DispositionRequiredError,
    ImpactRequiredError,
    InvalidTransitionError,
    InvestigationIncompleteError,
    MissingSignatureError,
    NotFoundError,
    PlannedDeviationExpiredError,
    QaClosureRequiredError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


async def _load_for_update(session: AsyncSession, deviation_id: uuid.UUID, expected_version: int) -> DeviationRecord:
    result = await session.execute(select(DeviationRecord).where(DeviationRecord.id == deviation_id).with_for_update())
    deviation = result.scalar_one_or_none()
    if deviation is None:
        raise NotFoundError("Deviation record not found")
    if deviation.version != expected_version:
        raise StaleVersionError(
            "Deviation record was modified by another actor since it was read",
            expected_version=expected_version,
            current_version=deviation.version,
        )
    return deviation


def _record_hash(deviation: DeviationRecord) -> str:
    return sha256_hex({"id": str(deviation.id), "version": deviation.version})


async def _resolve_signature(
    session: AsyncSession, *, action: str, actor_user_id: uuid.UUID, deviation: DeviationRecord,
    challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type="deviation_record", action=action)
    if not policy.signature_required:
        return None
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"Deviation '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id,
        record_version=deviation.version, record_hash=_record_hash(deviation),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


def _assert_not_expired_planned(deviation: DeviationRecord) -> None:
    """DEV-FR-016: a planned deviation cannot become a permanent alternative process. Once its declared
    end_date has passed it can no longer be advanced through the pipeline -- see §16's own
    PLANNED_DEVIATION_EXPIRED error code."""
    if not deviation.planned or not deviation.planned_scope:
        return
    end_date = deviation.planned_scope.get("end_date")
    if end_date is None:
        return
    parsed = datetime.fromisoformat(end_date)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if parsed < datetime.now(timezone.utc):
        raise PlannedDeviationExpiredError(
            "Planned deviation scope has expired", deviation_id=str(deviation.id), end_date=end_date
        )


async def _write_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, deviation: DeviationRecord,
    action: str, actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str,
    event_payload: dict, signature_id: uuid.UUID | None, expected_version: int | None,
    command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=deviation.site_id, aggregate_type="deviation_record", aggregate_id=deviation.id,
        aggregate_version=deviation.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": deviation.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="deviation_record", aggregate_id=deviation.id,
        aggregate_version=deviation.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=deviation.site_id, command_type=command_type, aggregate_type="deviation_record",
        aggregate_id=deviation.id, expected_version=expected_version, resulting_version=deviation.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=deviation.id, resulting_version=deviation.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create — DEV-FR-001/002 (partial, see SG-059)/016
# ---------------------------------------------------------------------------


class CreateDeviationCommand(CommandEnvelope):
    site_id: uuid.UUID
    deviation_number: str
    deviation_type: str
    source_type: str
    source_id: uuid.UUID
    source_version: int | None = None
    severity: str
    owner_subject_id: uuid.UUID
    planned: bool = False
    planned_scope: dict | None = None


async def create_deviation(session: AsyncSession, cmd: CreateDeviationCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.source_type not in SOURCE_TYPES:
        raise DeviationSourceInvalidError("Unrecognized deviation source_type", source_type=cmd.source_type, allowed=list(SOURCE_TYPES))
    if not cmd.deviation_type.strip() or not cmd.severity.strip():
        raise ValidationFailedError("deviation_type and severity are required")
    if cmd.planned:
        if not cmd.planned_scope or not all(k in cmd.planned_scope for k in ("scope", "start_date", "end_date")):
            raise ValidationFailedError("planned deviations require planned_scope.scope/start_date/end_date")

    conflict = (
        await session.execute(select(DeviationRecord).where(DeviationRecord.deviation_number == cmd.deviation_number))
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("deviation_number is already in use", deviation_number=cmd.deviation_number)

    deviation = DeviationRecord(
        site_id=cmd.site_id, deviation_number=cmd.deviation_number, deviation_type=cmd.deviation_type,
        source_type=cmd.source_type, source_id=cmd.source_id, source_version=cmd.source_version,
        severity=cmd.severity, owner_subject_id=cmd.owner_subject_id, planned=cmd.planned,
        planned_scope=cmd.planned_scope, state="OPEN",
    )
    session.add(deviation)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, deviation=deviation, action="Created",
        actor_user_id=actor_user_id, reason=None, old_state="OPEN",
        event_type="DeviationOpened", event_payload={"id": str(deviation.id), "deviation_number": deviation.deviation_number},
        signature_id=None, expected_version=None, command_type="CreateDeviation",
    )


# ---------------------------------------------------------------------------
# Triage — DEV-FR-003
# ---------------------------------------------------------------------------


class TriageDeviationCommand(CommandEnvelope):
    deviation_id: uuid.UUID
    expected_version: int
    severity: str
    investigation_priority: str
    product_impact: str | None = None
    deviation_type: str | None = None


async def triage_deviation(session: AsyncSession, cmd: TriageDeviationCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    deviation = await _load_for_update(session, cmd.deviation_id, cmd.expected_version)
    if "TRIAGE" not in ALLOWED_TRANSITIONS.get(deviation.state, set()):
        raise InvalidTransitionError("Illegal deviation transition", current_state=deviation.state, requested="TRIAGE")
    _assert_not_expired_planned(deviation)
    if not cmd.severity.strip() or not cmd.investigation_priority.strip():
        raise ValidationFailedError("severity and investigation_priority are required")

    old_state = deviation.state
    deviation.severity = cmd.severity
    if cmd.deviation_type:
        deviation.deviation_type = cmd.deviation_type
    deviation.state = "TRIAGE"
    deviation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, deviation=deviation, action="Changed",
        actor_user_id=actor_user_id, reason=None, old_state=old_state,
        event_type="DeviationOpened", event_payload={"id": str(deviation.id), "state": "TRIAGE"},
        signature_id=None, expected_version=cmd.expected_version, command_type="TriageDeviation",
    )


# ---------------------------------------------------------------------------
# Contain — DEV-FR-004/005
# ---------------------------------------------------------------------------


class ContainDeviationCommand(CommandEnvelope):
    deviation_id: uuid.UUID
    expected_version: int
    immediate_correction: dict | None = None
    containment: dict | None = None
    reason: str | None = None


async def contain_deviation(session: AsyncSession, cmd: ContainDeviationCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    deviation = await _load_for_update(session, cmd.deviation_id, cmd.expected_version)
    if "CONTAINMENT" not in ALLOWED_TRANSITIONS.get(deviation.state, set()):
        raise InvalidTransitionError("Illegal deviation transition", current_state=deviation.state, requested="CONTAINMENT")
    _assert_not_expired_planned(deviation)
    if not cmd.immediate_correction and not cmd.containment:
        raise ContainmentRequiredError("At least one of immediate_correction/containment is required")

    old_state = deviation.state
    if cmd.immediate_correction:
        deviation.immediate_correction = cmd.immediate_correction
    if cmd.containment:
        deviation.containment = cmd.containment
    deviation.state = "CONTAINMENT"
    deviation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, deviation=deviation, action="Changed",
        actor_user_id=actor_user_id, reason=cmd.reason, old_state=old_state,
        event_type="DeviationContained", event_payload={"id": str(deviation.id)},
        signature_id=None, expected_version=cmd.expected_version, command_type="ContainDeviation",
    )


# ---------------------------------------------------------------------------
# Investigation — DEV-FR-006/007/008/009/010
# ---------------------------------------------------------------------------


class InvestigationCommand(CommandEnvelope):
    deviation_id: uuid.UUID
    expected_version: int
    investigator_subject_id: uuid.UUID | None = None
    due_date: datetime | None = None
    investigation_plan: dict | None = None
    cross_batch_ids: list[uuid.UUID] | None = None
    evidence_links: list[dict] | None = None
    root_cause: dict | None = None
    reason: str | None = None


async def record_investigation(session: AsyncSession, cmd: InvestigationCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    deviation = await _load_for_update(session, cmd.deviation_id, cmd.expected_version)
    entering = deviation.state in ("CONTAINMENT", "REOPENED")
    if not entering and deviation.state != "INVESTIGATION":
        raise InvalidTransitionError("Illegal deviation transition", current_state=deviation.state, requested="INVESTIGATION")
    _assert_not_expired_planned(deviation)

    if entering:
        if cmd.investigator_subject_id is None or cmd.due_date is None:
            raise ValidationFailedError("investigator_subject_id and due_date are required to open an investigation")
    if cmd.root_cause is not None:
        no_cause = bool(cmd.root_cause.get("no_assignable_cause", False))
        if no_cause and not cmd.root_cause.get("justification", "").strip():
            raise ValidationFailedError("root_cause.justification is required when no_assignable_cause is true")
        if not no_cause and not cmd.root_cause.get("method", "").strip():
            raise ValidationFailedError("root_cause.method is required unless no_assignable_cause is true")

    old_state = deviation.state
    # DEV-FR-006: reassignment audited -- it is captured via the old/new values on the audit event below.
    if cmd.investigator_subject_id is not None:
        deviation.investigator_subject_id = cmd.investigator_subject_id
    if cmd.due_date is not None:
        deviation.due_date = cmd.due_date
    if cmd.investigation_plan is not None:
        deviation.investigation_plan = cmd.investigation_plan
    if cmd.cross_batch_ids is not None:
        deviation.cross_batch_ids = [str(i) for i in cmd.cross_batch_ids]
    if cmd.root_cause is not None:
        deviation.root_cause = cmd.root_cause
    for link in cmd.evidence_links or []:
        session.add(
            DeviationImpactLink(
                deviation_id=deviation.id, impacted_record_type=link["impacted_record_type"],
                impacted_record_id=link["impacted_record_id"], impacted_record_version=link.get("impacted_record_version"),
                created_by=actor_user_id,
            )
        )
    deviation.state = "INVESTIGATION"
    deviation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, deviation=deviation, action="Changed",
        actor_user_id=actor_user_id, reason=cmd.reason, old_state=old_state,
        event_type="DeviationInvestigationStarted", event_payload={"id": str(deviation.id)},
        signature_id=None, expected_version=cmd.expected_version, command_type="RecordInvestigation",
    )


# ---------------------------------------------------------------------------
# Impact — DEV-FR-011
# ---------------------------------------------------------------------------

IMPACT_CATEGORIES = (
    "quality_impact",
    "patient_user_impact",
    "released_distributed_product_impact",
    "validation_impact",
    "data_integrity_impact",
    "regulatory_impact",
)


class ImpactCommand(CommandEnvelope):
    deviation_id: uuid.UUID
    expected_version: int
    impact_assessment: dict
    impact_links: list[dict] | None = None
    reason: str | None = None


async def assess_impact(session: AsyncSession, cmd: ImpactCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    deviation = await _load_for_update(session, cmd.deviation_id, cmd.expected_version)
    entering = deviation.state == "INVESTIGATION"
    if not entering and deviation.state not in ("IMPACT_ASSESSMENT", "REOPENED"):
        raise InvalidTransitionError("Illegal deviation transition", current_state=deviation.state, requested="IMPACT_ASSESSMENT")
    _assert_not_expired_planned(deviation)
    if entering and (deviation.investigator_subject_id is None or deviation.root_cause is None):
        raise InvestigationIncompleteError("Investigation must have an investigator and a concluded root cause before impact assessment")
    missing = [k for k in IMPACT_CATEGORIES if not str(cmd.impact_assessment.get(k, "")).strip()]
    if missing:
        raise ValidationFailedError("impact_assessment is missing required categories", missing=missing)

    old_state = deviation.state
    deviation.impact_assessment = cmd.impact_assessment
    for link in cmd.impact_links or []:
        session.add(
            DeviationImpactLink(
                deviation_id=deviation.id, impacted_record_type=link["impacted_record_type"],
                impacted_record_id=link["impacted_record_id"], impacted_record_version=link.get("impacted_record_version"),
                impact_category=link.get("impact_category"), hold_disposition_reference=link.get("hold_disposition_reference"),
                created_by=actor_user_id,
            )
        )
    deviation.state = "IMPACT_ASSESSMENT"
    deviation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, deviation=deviation, action="Changed",
        actor_user_id=actor_user_id, reason=cmd.reason, old_state=old_state,
        event_type="DeviationImpactAssessed", event_payload={"id": str(deviation.id)},
        signature_id=None, expected_version=cmd.expected_version, command_type="AssessImpact",
    )


# ---------------------------------------------------------------------------
# Disposition — DEV-FR-012/013/014(partial, SG-060)/015(partial, SG-060)/019(signature)
# ---------------------------------------------------------------------------


class DispositionCommand(CommandEnvelope):
    deviation_id: uuid.UUID
    expected_version: int
    disposition_code: str
    disposition_rationale: str
    capa_required: bool
    capa_rationale: str
    change_control_required: bool = False
    change_control_rationale: str | None = None
    training_required: bool = False
    training_rationale: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def disposition_deviation(session: AsyncSession, cmd: DispositionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    deviation = await _load_for_update(session, cmd.deviation_id, cmd.expected_version)
    entering = deviation.state == "IMPACT_ASSESSMENT"
    if not entering and deviation.state not in ("DISPOSITION", "REOPENED"):
        raise InvalidTransitionError("Illegal deviation transition", current_state=deviation.state, requested="DISPOSITION")
    _assert_not_expired_planned(deviation)
    if not deviation.immediate_correction and not deviation.containment:
        raise ContainmentRequiredError("Containment must be recorded before disposition")
    if entering and deviation.impact_assessment is None:
        raise ImpactRequiredError("Impact assessment must be recorded before disposition")
    if cmd.disposition_code not in DISPOSITION_CODES:
        raise ValidationFailedError("Unrecognized disposition_code", disposition_code=cmd.disposition_code, allowed=list(DISPOSITION_CODES))
    if not cmd.disposition_rationale.strip():
        raise ValidationFailedError("disposition_rationale is required")
    if not cmd.capa_rationale.strip():
        raise ValidationFailedError("capa_rationale is required")

    signature_id = await _resolve_signature(
        session, action="disposition", actor_user_id=actor_user_id, deviation=deviation,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = deviation.state
    deviation.disposition_code = cmd.disposition_code
    deviation.disposition_rationale = cmd.disposition_rationale
    deviation.capa_required = cmd.capa_required
    deviation.capa_rationale = cmd.capa_rationale
    deviation.change_control_required = cmd.change_control_required
    deviation.change_control_rationale = cmd.change_control_rationale
    deviation.training_required = cmd.training_required
    deviation.training_rationale = cmd.training_rationale
    deviation.state = "DISPOSITION"
    deviation.version += 1

    receipt = await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, deviation=deviation, action="Changed",
        actor_user_id=actor_user_id, reason=cmd.disposition_rationale, old_state=old_state,
        event_type="DeviationDispositionApproved", event_payload={"id": str(deviation.id), "disposition_code": cmd.disposition_code},
        signature_id=signature_id, expected_version=cmd.expected_version, command_type="DispositionDeviation",
    )
    if cmd.capa_required:
        await write_outbox_event(
            session, event_type="DeviationCAPARequired", aggregate_type="deviation_record", aggregate_id=deviation.id,
            aggregate_version=deviation.version, payload={"id": str(deviation.id)}, correlation_id=receipt.correlation_id,
        )
    return receipt


# ---------------------------------------------------------------------------
# Extend — DEV-FR-017
# ---------------------------------------------------------------------------


class ExtendCommand(CommandEnvelope):
    deviation_id: uuid.UUID
    expected_version: int
    new_due_date: datetime
    reason: str
    risk_review: str


async def extend_deviation(session: AsyncSession, cmd: ExtendCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    deviation = await _load_for_update(session, cmd.deviation_id, cmd.expected_version)
    if deviation.state not in ("INVESTIGATION", "IMPACT_ASSESSMENT", "DISPOSITION", "REOPENED"):
        raise InvalidTransitionError("Deviation is not in a state where the due date can be extended", current_state=deviation.state, requested="extend")
    if deviation.due_date is None:
        raise ValidationFailedError("Deviation has no due date to extend yet")
    if not cmd.reason.strip() or not cmd.risk_review.strip():
        raise ValidationFailedError("reason and risk_review are required")
    current_due_date = deviation.due_date if deviation.due_date.tzinfo is not None else deviation.due_date.replace(tzinfo=timezone.utc)
    new_due_date = cmd.new_due_date if cmd.new_due_date.tzinfo is not None else cmd.new_due_date.replace(tzinfo=timezone.utc)
    if new_due_date <= current_due_date:
        raise ValidationFailedError("new_due_date must be later than the current due date")

    old_state = deviation.state
    deviation.extension_history = [
        *deviation.extension_history,
        {
            "previous_due_date": deviation.due_date.isoformat(), "new_due_date": cmd.new_due_date.isoformat(),
            "reason": cmd.reason, "risk_review": cmd.risk_review, "approved_by": str(actor_user_id),
            "approved_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    deviation.due_date = cmd.new_due_date
    deviation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, deviation=deviation, action="Changed",
        actor_user_id=actor_user_id, reason=cmd.reason, old_state=old_state,
        event_type="DeviationOpened", event_payload={"id": str(deviation.id), "new_due_date": cmd.new_due_date.isoformat()},
        signature_id=None, expected_version=cmd.expected_version, command_type="ExtendDeviation",
    )


# ---------------------------------------------------------------------------
# Close — DEV-FR-018/019 (signature)
# ---------------------------------------------------------------------------


class CloseCommand(CommandEnvelope):
    deviation_id: uuid.UUID
    expected_version: int
    conclusion: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def close_deviation(session: AsyncSession, cmd: CloseCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    deviation = await _load_for_update(session, cmd.deviation_id, cmd.expected_version)
    if deviation.state not in ("DISPOSITION", "REOPENED"):
        raise InvalidTransitionError("Illegal deviation transition", current_state=deviation.state, requested="CLOSED")
    _assert_not_expired_planned(deviation)

    # DEV-FR-018: investigation, impact, disposition and mandatory linked actions before QA closure.
    if not deviation.immediate_correction and not deviation.containment:
        raise ContainmentRequiredError("Containment must be recorded before closure")
    if deviation.investigator_subject_id is None or deviation.root_cause is None:
        raise InvestigationIncompleteError("Investigation must be complete before closure")
    if deviation.impact_assessment is None:
        raise ImpactRequiredError("Impact assessment must be recorded before closure")
    if deviation.disposition_code is None:
        raise DispositionRequiredError("Disposition must be recorded before closure")
    if not cmd.conclusion.strip():
        raise QaClosureRequiredError("A final written conclusion is required for QA closure")

    signature_id = await _resolve_signature(
        session, action="close", actor_user_id=actor_user_id, deviation=deviation,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = deviation.state
    now = datetime.now(timezone.utc)
    if deviation.closed_at is None:
        deviation.closed_at = now
    deviation.closure_history = [
        *deviation.closure_history,
        {"conclusion": cmd.conclusion, "closed_at": now.isoformat(), "closed_by": str(actor_user_id),
         "signature_id": str(signature_id) if signature_id else None},
    ]
    deviation.state = "CLOSED"
    deviation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, deviation=deviation, action="Closed",
        actor_user_id=actor_user_id, reason=cmd.conclusion, old_state=old_state,
        event_type="DeviationClosed", event_payload={"id": str(deviation.id)},
        signature_id=signature_id, expected_version=cmd.expected_version, command_type="CloseDeviation",
    )


# ---------------------------------------------------------------------------
# Reopen — DEV-FR-020
# ---------------------------------------------------------------------------


class ReopenCommand(CommandEnvelope):
    deviation_id: uuid.UUID
    expected_version: int
    reason: str
    new_evidence: str


async def reopen_deviation(session: AsyncSession, cmd: ReopenCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    deviation = await _load_for_update(session, cmd.deviation_id, cmd.expected_version)
    if "REOPENED" not in ALLOWED_TRANSITIONS.get(deviation.state, set()):
        raise InvalidTransitionError("Illegal deviation transition", current_state=deviation.state, requested="REOPENED")
    if not cmd.reason.strip() or not cmd.new_evidence.strip():
        raise ValidationFailedError("reason and new_evidence are required to reopen a closed deviation")

    old_state = deviation.state
    # DEV-FR-020: reopen preserves prior closure -- closed_at and closure_history are never cleared or
    # rewritten, only appended to on the *next* closure.
    deviation.reopen_history = [
        *deviation.reopen_history,
        {
            "previous_closed_at": deviation.closed_at.isoformat() if deviation.closed_at else None,
            "reason": cmd.reason, "new_evidence": cmd.new_evidence, "reopened_by": str(actor_user_id),
            "reopened_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    deviation.state = "REOPENED"
    deviation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, deviation=deviation, action="Changed",
        actor_user_id=actor_user_id, reason=cmd.reason, old_state=old_state,
        event_type="DeviationReopened", event_payload={"id": str(deviation.id)},
        signature_id=None, expected_version=cmd.expected_version, command_type="ReopenDeviation",
    )
