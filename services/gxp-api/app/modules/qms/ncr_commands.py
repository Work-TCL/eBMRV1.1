"""Document 28 (SPEC-QMS-003) — the buildable slice of Nonconformance Management: the linear
OPEN -> SEGREGATED -> EVALUATION -> {REWORK,REPAIR,RETURN,SCRAP,USE_AS_IS} -> VERIFICATION -> CLOSED
pipeline Document 28 §4 describes, matching the module's own 6-op API list exactly. No reopen operation is
built -- NCR-FR-016 names the capability but Document 28's own API list has no endpoint for it, unlike
Documents 26/27 (see ncr_models.py's module docstring and docs/generated/18_SPEC_GAPS.md SG-069).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.qms.ncr_models import (
    NCR_ALLOWED_TRANSITIONS,
    NCR_DISPOSITION_TYPES,
    NCR_SCOPE_TYPES,
    NCR_SOURCE_TYPES,
    REWORK_LIKE_DISPOSITIONS,
    NcrDisposition,
    NonconformanceRecord,
)
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    DispositionNotAllowedError,
    InvalidTransitionError,
    MissingSignatureError,
    NcrClosureBlockedError,
    NcrScopeRequiredError,
    NotFoundError,
    ReinspectionRequiredError,
    ReworkRouteRequiredError,
    SegregationRequiredError,
    StaleVersionError,
    UseAsIsNotAuthorizedError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
        audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _load_ncr_for_update(session: AsyncSession, ncr_id: uuid.UUID, expected_version: int) -> NonconformanceRecord:
    result = await session.execute(select(NonconformanceRecord).where(NonconformanceRecord.id == ncr_id).with_for_update())
    ncr = result.scalar_one_or_none()
    if ncr is None:
        raise NotFoundError("Nonconformance record not found")
    if ncr.version != expected_version:
        raise StaleVersionError(
            "Nonconformance record was modified by another actor since it was read",
            expected_version=expected_version, current_version=ncr.version,
        )
    return ncr


def _record_hash(ncr: NonconformanceRecord) -> str:
    return sha256_hex({"id": str(ncr.id), "version": ncr.version})


async def _resolve_signature(
    session: AsyncSession, *, action: str, actor_user_id: uuid.UUID, ncr: NonconformanceRecord,
    challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type="nonconformance_record", action=action)
    if not policy.signature_required:
        return None
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"Nonconformance '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=ncr.version, record_hash=_record_hash(ncr),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


async def _write_ncr_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, ncr: NonconformanceRecord, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    signature_id: uuid.UUID | None, expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=ncr.site_id, aggregate_type="nonconformance_record", aggregate_id=ncr.id,
        aggregate_version=ncr.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": ncr.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="nonconformance_record", aggregate_id=ncr.id,
        aggregate_version=ncr.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=ncr.site_id, command_type=command_type, aggregate_type="nonconformance_record",
        aggregate_id=ncr.id, expected_version=expected_version, resulting_version=ncr.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=ncr.id, resulting_version=ncr.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create — NCR-FR-001/002(partial)/004(partial)/010(partial)
# ---------------------------------------------------------------------------


class CreateNcrCommand(CommandEnvelope):
    site_id: uuid.UUID
    ncr_number: str
    scope_type: str
    scope_records: list[dict]
    requirement_ref: dict
    defect_code: str
    severity: str
    owner_subject_id: uuid.UUID
    source_type: str | None = None
    source_id: uuid.UUID | None = None
    source_version: int | None = None
    supplier_link: dict | None = None


async def create_ncr(session: AsyncSession, cmd: CreateNcrCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.scope_type not in NCR_SCOPE_TYPES:
        raise ValidationFailedError("Unrecognized scope_type", scope_type=cmd.scope_type, allowed=list(NCR_SCOPE_TYPES))
    if not cmd.scope_records:
        raise NcrScopeRequiredError("scope_records must name at least one affected lot/serial/quantity")
    if cmd.source_type is not None and cmd.source_type not in NCR_SOURCE_TYPES:
        raise ValidationFailedError("Unrecognized source_type", source_type=cmd.source_type, allowed=list(NCR_SOURCE_TYPES))
    if not cmd.requirement_ref or not (cmd.requirement_ref.get("spec_ref") or cmd.requirement_ref.get("test_ref")):
        raise ValidationFailedError("requirement_ref requires spec_ref or test_ref")
    if not cmd.defect_code.strip():
        raise ValidationFailedError("defect_code is required")

    conflict = (await session.execute(select(NonconformanceRecord).where(NonconformanceRecord.ncr_number == cmd.ncr_number))).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("ncr_number is already in use", ncr_number=cmd.ncr_number)

    ncr = NonconformanceRecord(
        site_id=cmd.site_id, ncr_number=cmd.ncr_number, scope_type=cmd.scope_type, scope_records=cmd.scope_records,
        requirement_ref=cmd.requirement_ref, defect_code=cmd.defect_code, severity=cmd.severity,
        owner_subject_id=cmd.owner_subject_id, source_type=cmd.source_type, source_id=cmd.source_id,
        source_version=cmd.source_version, supplier_link=cmd.supplier_link, state="OPEN",
    )
    session.add(ncr)
    await session.flush()

    return await _write_ncr_receipt(
        session, cmd=cmd, payload_hash=payload_hash, ncr=ncr, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="OPEN", event_type="NonconformanceOpened",
        event_payload={"id": str(ncr.id), "ncr_number": ncr.ncr_number}, signature_id=None,
        expected_version=None, command_type="CreateNcr",
    )


# ---------------------------------------------------------------------------
# Segregate — NCR-FR-003
# ---------------------------------------------------------------------------


class SegregateNcrCommand(CommandEnvelope):
    ncr_id: uuid.UUID
    expected_version: int
    locations: list[dict]
    reason: str | None = None


async def segregate_ncr(session: AsyncSession, cmd: SegregateNcrCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    ncr = await _load_ncr_for_update(session, cmd.ncr_id, cmd.expected_version)
    if "SEGREGATED" not in NCR_ALLOWED_TRANSITIONS.get(ncr.state, set()):
        raise InvalidTransitionError("Illegal nonconformance transition", current_state=ncr.state, requested="SEGREGATED")
    if not cmd.locations:
        raise ValidationFailedError("At least one segregation location is required")

    old_state = ncr.state
    ncr.segregation = {
        "locations": cmd.locations, "confirmed_by": str(actor_user_id),
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }
    ncr.state = "SEGREGATED"
    ncr.version += 1

    return await _write_ncr_receipt(
        session, cmd=cmd, payload_hash=payload_hash, ncr=ncr, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="NonconformingProductSegregated",
        event_payload={"id": str(ncr.id)}, signature_id=None, expected_version=cmd.expected_version,
        command_type="SegregateNcr",
    )


# ---------------------------------------------------------------------------
# Evaluate — NCR-FR-004/005
# ---------------------------------------------------------------------------

EVALUATION_KEYS = ("usability", "quality_impact", "safety_impact", "performance_impact", "investigation_needed")


class EvaluateNcrCommand(CommandEnvelope):
    ncr_id: uuid.UUID
    expected_version: int
    evaluation: dict
    requirement_ref: dict | None = None
    reason: str | None = None


async def evaluate_ncr(session: AsyncSession, cmd: EvaluateNcrCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    ncr = await _load_ncr_for_update(session, cmd.ncr_id, cmd.expected_version)
    entering = ncr.state == "SEGREGATED"
    if not entering and ncr.state != "EVALUATION":
        raise InvalidTransitionError("Illegal nonconformance transition", current_state=ncr.state, requested="EVALUATION")
    if ncr.segregation is None:
        raise SegregationRequiredError("Nonconformance must be segregated before evaluation")
    missing = [k for k in EVALUATION_KEYS if k not in cmd.evaluation]
    if missing:
        raise ValidationFailedError("evaluation is missing required keys", missing=missing)

    old_state = ncr.state
    ncr.evaluation = cmd.evaluation
    if cmd.requirement_ref:
        ncr.requirement_ref = cmd.requirement_ref
    ncr.state = "EVALUATION"
    ncr.version += 1

    return await _write_ncr_receipt(
        session, cmd=cmd, payload_hash=payload_hash, ncr=ncr, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="NonconformanceOpened",
        event_payload={"id": str(ncr.id), "state": "EVALUATION"}, signature_id=None,
        expected_version=cmd.expected_version, command_type="EvaluateNcr",
    )


# ---------------------------------------------------------------------------
# Disposition — NCR-FR-006/007/008/013/015(signature)
# ---------------------------------------------------------------------------


class DispositionNcrCommand(CommandEnvelope):
    ncr_id: uuid.UUID
    expected_version: int
    disposition_type: str
    affected_scope: list[dict]
    justification: str
    quantity: float | None = None
    serials: list[str] | None = None
    rework_route: dict | None = None
    follow_up_test_requirements: dict | None = None
    use_as_is_authorized_by: uuid.UUID | None = None
    capa_required: bool = False
    capa_rationale: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def disposition_ncr(session: AsyncSession, cmd: DispositionNcrCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    ncr = await _load_ncr_for_update(session, cmd.ncr_id, cmd.expected_version)
    if cmd.disposition_type not in NCR_DISPOSITION_TYPES:
        raise DispositionNotAllowedError("Unrecognized disposition_type", disposition_type=cmd.disposition_type, allowed=list(NCR_DISPOSITION_TYPES))
    if cmd.disposition_type not in NCR_ALLOWED_TRANSITIONS.get(ncr.state, set()):
        raise InvalidTransitionError("Illegal nonconformance transition", current_state=ncr.state, requested=cmd.disposition_type)
    if not cmd.affected_scope:
        raise NcrScopeRequiredError("affected_scope must name at least one lot/serial/quantity for this disposition")
    if not cmd.justification.strip():
        raise ValidationFailedError("justification is required")
    # NCR-FR-007: use-as-is is restricted by default -- a technical/Quality justification (the general
    # `justification` field, already required above) is necessary but not sufficient; an identified
    # authorizing subject is also required, distinct from ordinary narrative text.
    if cmd.disposition_type == "USE_AS_IS" and cmd.use_as_is_authorized_by is None:
        raise UseAsIsNotAuthorizedError("use-as-is requires an identified authorizing subject (use_as_is_authorized_by)")
    if cmd.disposition_type in REWORK_LIKE_DISPOSITIONS and not cmd.rework_route:
        raise ReworkRouteRequiredError("rework_route is required for REWORK/REPAIR disposition")

    signature_id = await _resolve_signature(
        session, action="disposition", actor_user_id=actor_user_id, ncr=ncr,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    disposition = NcrDisposition(
        ncr_id=ncr.id, affected_scope=cmd.affected_scope, quantity=cmd.quantity, serials=cmd.serials,
        disposition_type=cmd.disposition_type, justification=cmd.justification, rework_route=cmd.rework_route,
        follow_up_test_requirements=cmd.follow_up_test_requirements, use_as_is_authorized_by=cmd.use_as_is_authorized_by,
        signature_id=signature_id, created_by=actor_user_id,
    )
    session.add(disposition)

    old_state = ncr.state
    ncr.state = cmd.disposition_type
    ncr.capa_required = cmd.capa_required
    ncr.capa_rationale = cmd.capa_rationale
    ncr.version += 1
    await session.flush()

    receipt = await _write_ncr_receipt(
        session, cmd=cmd, payload_hash=payload_hash, ncr=ncr, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.justification, old_state=old_state, event_type="NCRDispositionApproved",
        event_payload={"id": str(ncr.id), "disposition_id": str(disposition.id), "disposition_type": cmd.disposition_type},
        signature_id=signature_id, expected_version=cmd.expected_version, command_type="DispositionNcr",
    )
    if cmd.disposition_type in REWORK_LIKE_DISPOSITIONS:
        await write_outbox_event(
            session, event_type="NCRReworkStarted", aggregate_type="nonconformance_record", aggregate_id=ncr.id,
            aggregate_version=ncr.version, payload={"id": str(ncr.id), "disposition_id": str(disposition.id)},
            correlation_id=receipt.correlation_id,
        )
    return receipt


# ---------------------------------------------------------------------------
# Verify — NCR-FR-009/015(signature)
# ---------------------------------------------------------------------------


class VerifyNcrCommand(CommandEnvelope):
    ncr_id: uuid.UUID
    expected_version: int
    reinspection_evidence: dict | None = None
    confirmation: dict | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None
    reason: str | None = None


async def verify_ncr(session: AsyncSession, cmd: VerifyNcrCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    ncr = await _load_ncr_for_update(session, cmd.ncr_id, cmd.expected_version)
    if "VERIFICATION" not in NCR_ALLOWED_TRANSITIONS.get(ncr.state, set()):
        raise InvalidTransitionError("Illegal nonconformance transition", current_state=ncr.state, requested="VERIFICATION")

    # NCR-FR-009: reinspection/retest is required after rework/repair specifically; other disposition
    # outcomes (return/scrap/use-as-is) only need a confirmation that the disposition was executed.
    if ncr.state in REWORK_LIKE_DISPOSITIONS:
        if not cmd.reinspection_evidence or not str(cmd.reinspection_evidence.get("result", "")).strip():
            raise ReinspectionRequiredError("reinspection_evidence.result is required after rework/repair")
    elif not cmd.confirmation:
        raise ValidationFailedError("confirmation is required to verify a non-rework disposition was executed")

    signature_id = await _resolve_signature(
        session, action="verify", actor_user_id=actor_user_id, ncr=ncr,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = ncr.state
    ncr.verification = {
        "reinspection_evidence": cmd.reinspection_evidence, "confirmation": cmd.confirmation,
        "verified_by": str(actor_user_id), "verified_at": datetime.now(timezone.utc).isoformat(),
        "prior_disposition_state": old_state,
    }
    ncr.state = "VERIFICATION"
    ncr.version += 1

    return await _write_ncr_receipt(
        session, cmd=cmd, payload_hash=payload_hash, ncr=ncr, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="NCRReinspectionCompleted",
        event_payload={"id": str(ncr.id)}, signature_id=signature_id, expected_version=cmd.expected_version,
        command_type="VerifyNcr",
    )


# ---------------------------------------------------------------------------
# Close — NCR-FR-015(signature)/018(partial)
# ---------------------------------------------------------------------------


class CloseNcrCommand(CommandEnvelope):
    ncr_id: uuid.UUID
    expected_version: int
    conclusion: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def close_ncr(session: AsyncSession, cmd: CloseNcrCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    ncr = await _load_ncr_for_update(session, cmd.ncr_id, cmd.expected_version)
    if ncr.state != "VERIFICATION":
        raise InvalidTransitionError("Illegal nonconformance transition", current_state=ncr.state, requested="CLOSED")

    dispositions = (await session.execute(select(NcrDisposition).where(NcrDisposition.ncr_id == ncr.id))).scalars().all()
    if not dispositions:
        raise NcrClosureBlockedError("No disposition has been recorded for this nonconformance")
    if not cmd.conclusion or not cmd.conclusion.strip():
        raise NcrClosureBlockedError("A final written conclusion is required for QA closure")

    signature_id = await _resolve_signature(
        session, action="close", actor_user_id=actor_user_id, ncr=ncr,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = ncr.state
    now = datetime.now(timezone.utc)
    if ncr.closed_at is None:
        ncr.closed_at = now
    ncr.closure_history = [
        *ncr.closure_history,
        {"conclusion": cmd.conclusion, "closed_at": now.isoformat(), "closed_by": str(actor_user_id),
         "signature_id": str(signature_id) if signature_id else None},
    ]
    ncr.state = "CLOSED"
    ncr.version += 1

    return await _write_ncr_receipt(
        session, cmd=cmd, payload_hash=payload_hash, ncr=ncr, action="Closed", actor_user_id=actor_user_id,
        reason=cmd.conclusion, old_state=old_state, event_type="NCRClosed",
        event_payload={"id": str(ncr.id)}, signature_id=signature_id, expected_version=cmd.expected_version,
        command_type="CloseNcr",
    )
