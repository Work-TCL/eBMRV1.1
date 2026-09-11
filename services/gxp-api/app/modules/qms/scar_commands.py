"""Document 32 (SPEC-QMS-007) — Supplier Quality / SCAR command handlers. See scar_models.py's module
docstring for the state-machine fold-in rationale and the deferred cross-module scope (SG-091).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.qms.scar_models import (
    SCAR_SOURCE_TYPES,
    SOURCE_STATUS_DECISIONS,
    ScarRecord,
    SupplierQualityCase,
)
from app.modules.qms.signature_support import enforce_signer_policy
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    EffectivenessRequiredError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    ScarReviewRejectedError,
    ScarSourceRequiredError,
    StaleVersionError,
    SupplierResponseIncompleteError,
    SupplierSourceSuspendedError,
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


async def _load_case_for_update(session: AsyncSession, case_id: uuid.UUID, expected_version: int | None = None) -> SupplierQualityCase:
    result = await session.execute(select(SupplierQualityCase).where(SupplierQualityCase.id == case_id).with_for_update())
    case = result.scalar_one_or_none()
    if case is None:
        raise NotFoundError("Supplier quality case not found")
    if expected_version is not None and case.version != expected_version:
        raise StaleVersionError(
            "Supplier quality case was modified by another actor since it was read",
            expected_version=expected_version, current_version=case.version,
        )
    return case


async def _load_scar_for_update(session: AsyncSession, scar_id: uuid.UUID, expected_version: int) -> ScarRecord:
    result = await session.execute(select(ScarRecord).where(ScarRecord.id == scar_id).with_for_update())
    scar = result.scalar_one_or_none()
    if scar is None:
        raise NotFoundError("SCAR record not found")
    if scar.version != expected_version:
        raise StaleVersionError(
            "SCAR record was modified by another actor since it was read",
            expected_version=expected_version, current_version=scar.version,
        )
    return scar


def _record_hash(scar: ScarRecord) -> str:
    return sha256_hex({"id": str(scar.id), "version": scar.version})


async def _resolve_signature(
    session: AsyncSession, *, action: str, actor_user_id: uuid.UUID, scar: ScarRecord,
    challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type="scar_record", action=action)
    if not policy.signature_required:
        return None
    # Document 106 section 9 rows 95/96: review is `Reviewed` by a "QA Reviewer" independent of the
    # performer; close is `Approved` by a "QA Releaser" independent of the investigator/owner. ScarRecord
    # stores no performer/owner identity of its own (only a `case_id` to the parent SupplierQualityCase),
    # so only the required role is enforced here -- same honest limitation recorded for
    # qa_review_package/complete.
    await enforce_signer_policy(
        session, policy=policy, actor_user_id=actor_user_id, site_id=scar.site_id,
        action_label=f"scar.{action}",
    )
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"SCAR '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=scar.version, record_hash=_record_hash(scar),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


async def _write_case_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, case: SupplierQualityCase, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    expected_version: int | None, command_type: str,
) -> MutationReceipt:
    """Full receipt (audit + outbox + command receipt + idempotency row) for commands whose *primary*
    aggregate is the case -- `create_supplier_case` only. `issue_scar`/`close_scar` touch the case as a
    secondary aggregate of a scar-primary command and use `_write_case_audit_outbox` instead: one
    idempotency key maps to exactly one `CommandReceipt` row (MUT-FR-010), so a command that mutates two
    aggregates records its one receipt against the primary aggregate and writes plain audit+outbox for
    the other (same pattern as ncr_commands.py's disposition_ncr's extra `NCRReworkStarted` outbox row).
    """
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=case.site_id, aggregate_type="supplier_quality_case", aggregate_id=case.id,
        aggregate_version=case.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": case.state}, signature_id=None,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="supplier_quality_case", aggregate_id=case.id,
        aggregate_version=case.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=case.site_id, command_type=command_type, aggregate_type="supplier_quality_case",
        aggregate_id=case.id, expected_version=expected_version, resulting_version=case.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=case.id, resulting_version=case.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


async def _write_case_audit_outbox(
    session: AsyncSession, *, case: SupplierQualityCase, action: str, actor_user_id: uuid.UUID,
    reason: str | None, old_state: str, event_type: str, event_payload: dict, correlation_id: uuid.UUID,
) -> None:
    await write_audit_event(
        session, site_id=case.site_id, aggregate_type="supplier_quality_case", aggregate_id=case.id,
        aggregate_version=case.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": case.state}, signature_id=None,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="supplier_quality_case", aggregate_id=case.id,
        aggregate_version=case.version, payload=event_payload, correlation_id=correlation_id,
    )


async def _write_scar_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, scar: ScarRecord, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    signature_id: uuid.UUID | None, expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=scar.site_id, aggregate_type="scar_record", aggregate_id=scar.id,
        aggregate_version=scar.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": scar.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="scar_record", aggregate_id=scar.id,
        aggregate_version=scar.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=scar.site_id, command_type=command_type, aggregate_type="scar_record",
        aggregate_id=scar.id, expected_version=expected_version, resulting_version=scar.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=scar.id, resulting_version=scar.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create supplier quality case — SCAR-FR-001/002/003(partial)/012(partial)
# ---------------------------------------------------------------------------


class CreateSupplierCaseCommand(CommandEnvelope):
    site_id: uuid.UUID
    case_number: str
    supplier_id: uuid.UUID
    supplier_site_id: uuid.UUID | None = None
    material_id: uuid.UUID | None = None
    material_spec_ref: dict | None = None
    affected_lots: list[dict]
    defect_code: str
    severity: str
    internal_owner_subject_id: uuid.UUID
    source_type: str | None = None
    source_id: uuid.UUID | None = None
    source_version: int | None = None
    containment: dict | None = None
    alternate_source_ref: dict | None = None


async def create_supplier_case(session: AsyncSession, cmd: CreateSupplierCaseCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.affected_lots:
        raise ScarSourceRequiredError("affected_lots must name at least one affected lot/product")
    if cmd.source_type is not None and cmd.source_type not in SCAR_SOURCE_TYPES:
        raise ValidationFailedError("Unrecognized source_type", source_type=cmd.source_type, allowed=list(SCAR_SOURCE_TYPES))
    if not cmd.defect_code.strip():
        raise ValidationFailedError("defect_code is required")

    conflict = (await session.execute(select(SupplierQualityCase).where(SupplierQualityCase.case_number == cmd.case_number))).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("case_number is already in use", case_number=cmd.case_number)

    # SCAR-FR-011: a supplier whose most recent closed SCAR decided "suspend" (with no later "reinstate")
    # cannot have a new independent case opened against it from this module -- see scar_models.py's
    # module docstring / SG-091 for what this deliberately does not do (materials-side procurement gate).
    latest_closed = (
        await session.execute(
            select(ScarRecord)
            .join(SupplierQualityCase, SupplierQualityCase.id == ScarRecord.case_id)
            .where(SupplierQualityCase.supplier_id == cmd.supplier_id, ScarRecord.state == "CLOSED")
            .order_by(ScarRecord.closed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest_closed is not None and latest_closed.source_status_decision == "suspend":
        raise SupplierSourceSuspendedError("Supplier source is currently suspended pending resolution", supplier_id=str(cmd.supplier_id))

    case = SupplierQualityCase(
        site_id=cmd.site_id, case_number=cmd.case_number, source_type=cmd.source_type, source_id=cmd.source_id,
        source_version=cmd.source_version, supplier_id=cmd.supplier_id, supplier_site_id=cmd.supplier_site_id,
        material_id=cmd.material_id, material_spec_ref=cmd.material_spec_ref, affected_lots=cmd.affected_lots,
        defect_code=cmd.defect_code, severity=cmd.severity, containment=cmd.containment,
        internal_owner_subject_id=cmd.internal_owner_subject_id, alternate_source_ref=cmd.alternate_source_ref,
        state="CONTAINMENT" if cmd.containment else "OPEN",
    )
    session.add(case)
    await session.flush()

    return await _write_case_receipt(
        session, cmd=cmd, payload_hash=payload_hash, case=case, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="OPEN", event_type="SupplierQualityCaseOpened",
        event_payload={"id": str(case.id), "case_number": case.case_number}, expected_version=None,
        command_type="CreateSupplierCase",
    )


# ---------------------------------------------------------------------------
# Issue SCAR — SCAR-FR-004/014(computed)
# ---------------------------------------------------------------------------


class IssueScarCommand(CommandEnvelope):
    case_id: uuid.UUID
    case_expected_version: int
    scar_number: str
    due_date: datetime | None = None
    problem_statement: str
    evidence: dict | None = None


async def issue_scar(session: AsyncSession, cmd: IssueScarCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    case = await _load_case_for_update(session, cmd.case_id, cmd.case_expected_version)
    if case.state not in ("OPEN", "CONTAINMENT"):
        raise InvalidTransitionError("Illegal supplier case transition", current_state=case.state, requested="SCAR_ISSUED")
    if not cmd.problem_statement.strip():
        raise ValidationFailedError("problem_statement is required")

    open_scar = (
        await session.execute(
            select(ScarRecord).where(ScarRecord.case_id == case.id, ScarRecord.state != "CLOSED")
        )
    ).scalar_one_or_none()
    if open_scar is not None:
        raise ValidationFailedError("An open SCAR already exists for this case", scar_id=str(open_scar.id))

    conflict = (await session.execute(select(ScarRecord).where(ScarRecord.scar_number == cmd.scar_number))).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("scar_number is already in use", scar_number=cmd.scar_number)

    # SCAR-FR-014: repeat-issue detection by supplier + defect code across prior cases.
    related = (
        await session.execute(
            select(SupplierQualityCase.id).where(
                SupplierQualityCase.supplier_id == case.supplier_id,
                SupplierQualityCase.defect_code == case.defect_code,
                SupplierQualityCase.id != case.id,
            )
        )
    ).scalars().all()

    scar = ScarRecord(
        site_id=case.site_id, case_id=case.id, scar_number=cmd.scar_number,
        issued_at=datetime.now(timezone.utc), due_date=cmd.due_date, problem_statement=cmd.problem_statement,
        evidence=cmd.evidence, state="SCAR_ISSUED", is_repeat_issue=bool(related),
        related_case_ids=[str(rid) for rid in related] if related else None,
    )
    session.add(scar)
    await session.flush()

    old_case_state = case.state
    case.state = "SCAR_ISSUED"
    case.version += 1

    receipt = await _write_scar_receipt(
        session, cmd=cmd, payload_hash=payload_hash, scar=scar, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="SCAR_ISSUED", event_type="SCARIssued",
        event_payload={"id": str(scar.id), "case_id": str(case.id), "scar_number": scar.scar_number, "is_repeat_issue": scar.is_repeat_issue},
        signature_id=None, expected_version=None, command_type="IssueScar",
    )
    await _write_case_audit_outbox(
        session, case=case, action="Changed", actor_user_id=actor_user_id, reason=None, old_state=old_case_state,
        event_type="SCARIssued", event_payload={"case_id": str(case.id), "scar_id": str(scar.id)},
        correlation_id=receipt.correlation_id,
    )
    return receipt


# ---------------------------------------------------------------------------
# Supplier response — SCAR-FR-005/006/007
# ---------------------------------------------------------------------------


class RecordSupplierResponseCommand(CommandEnvelope):
    scar_id: uuid.UUID
    expected_version: int
    acknowledgment: dict | None = None
    supplier_root_cause: dict | None = None
    supplier_actions: dict | None = None
    reason: str | None = None


async def record_supplier_response(session: AsyncSession, cmd: RecordSupplierResponseCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    scar = await _load_scar_for_update(session, cmd.scar_id, cmd.expected_version)
    if scar.state not in ("SCAR_ISSUED", "SUPPLIER_RESPONSE"):
        raise InvalidTransitionError("Illegal SCAR transition", current_state=scar.state, requested="SUPPLIER_RESPONSE")

    old_state = scar.state
    if cmd.acknowledgment is not None:
        scar.acknowledgment = cmd.acknowledgment
    if cmd.supplier_root_cause is not None:
        # SCAR-FR-006: recorded as the supplier's own statement -- never merged into `internal_review`,
        # which is where Quality's own accepted/rejected judgement on it is formed separately.
        scar.supplier_root_cause = cmd.supplier_root_cause
    if cmd.supplier_actions is not None:
        scar.supplier_actions = cmd.supplier_actions
    scar.state = "SUPPLIER_RESPONSE"
    scar.version += 1

    return await _write_scar_receipt(
        session, cmd=cmd, payload_hash=payload_hash, scar=scar, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="SCARResponseReceived",
        event_payload={"id": str(scar.id)}, signature_id=None, expected_version=cmd.expected_version,
        command_type="RecordSupplierResponse",
    )


# ---------------------------------------------------------------------------
# Internal review — SCAR-FR-008(signature)
# ---------------------------------------------------------------------------


class ReviewScarCommand(CommandEnvelope):
    scar_id: uuid.UUID
    expected_version: int
    decision: str  # "accepted" | "rejected"
    rationale: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def review_scar(session: AsyncSession, cmd: ReviewScarCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    scar = await _load_scar_for_update(session, cmd.scar_id, cmd.expected_version)
    if scar.state != "SUPPLIER_RESPONSE":
        raise InvalidTransitionError("Illegal SCAR transition", current_state=scar.state, requested="INTERNAL_REVIEW")
    if cmd.decision not in ("accepted", "rejected"):
        raise ValidationFailedError("decision must be 'accepted' or 'rejected'", decision=cmd.decision)
    if not (scar.acknowledgment and scar.supplier_root_cause and scar.supplier_actions):
        raise SupplierResponseIncompleteError("Supplier response is missing acknowledgment, root cause or corrective actions")
    if not cmd.rationale.strip():
        raise ValidationFailedError("rationale is required")

    signature_id = await _resolve_signature(
        session, action="review", actor_user_id=actor_user_id, scar=scar,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    review_record = {
        "decision": cmd.decision, "rationale": cmd.rationale, "reviewed_by": str(actor_user_id),
        "reviewed_at": datetime.now(timezone.utc).isoformat(), "signature_id": str(signature_id) if signature_id else None,
    }
    old_state = scar.state
    scar.internal_review = review_record
    scar.review_history = [*scar.review_history, review_record]
    scar.state = "IMPLEMENTATION" if cmd.decision == "accepted" else "SUPPLIER_RESPONSE"
    scar.version += 1

    return await _write_scar_receipt(
        session, cmd=cmd, payload_hash=payload_hash, scar=scar, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=old_state,
        event_type="SCARResponseReceived", event_payload={"id": str(scar.id), "decision": cmd.decision},
        signature_id=signature_id, expected_version=cmd.expected_version, command_type="ReviewScar",
    )


# ---------------------------------------------------------------------------
# Effectiveness — SCAR-FR-009
# ---------------------------------------------------------------------------


class RecordEffectivenessCommand(CommandEnvelope):
    scar_id: uuid.UUID
    expected_version: int
    result: str  # "pass" | "fail"
    evidence: dict | None = None
    reason: str | None = None


async def record_effectiveness(session: AsyncSession, cmd: RecordEffectivenessCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    scar = await _load_scar_for_update(session, cmd.scar_id, cmd.expected_version)
    if scar.state not in ("IMPLEMENTATION", "EFFECTIVENESS"):
        if scar.state == "SUPPLIER_RESPONSE" and scar.internal_review and scar.internal_review.get("decision") == "rejected":
            raise ScarReviewRejectedError("Internal review rejected the supplier response; a new response and review are required")
        raise InvalidTransitionError("Illegal SCAR transition", current_state=scar.state, requested="EFFECTIVENESS")
    if cmd.result not in ("pass", "fail"):
        raise ValidationFailedError("result must be 'pass' or 'fail'", result=cmd.result)

    effectiveness_record = {
        "result": cmd.result, "evidence": cmd.evidence, "verified_by": str(actor_user_id),
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    old_state = scar.state
    scar.effectiveness = effectiveness_record
    scar.effectiveness_history = [*scar.effectiveness_history, effectiveness_record]
    scar.state = "EFFECTIVENESS"
    scar.version += 1

    return await _write_scar_receipt(
        session, cmd=cmd, payload_hash=payload_hash, scar=scar, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state,
        event_type="SCAREffectivenessPassed" if cmd.result == "pass" else "SCARResponseReceived",
        event_payload={"id": str(scar.id), "result": cmd.result}, signature_id=None,
        expected_version=cmd.expected_version, command_type="RecordEffectiveness",
    )


# ---------------------------------------------------------------------------
# Close — SCAR-FR-010/011/013/016(signature)
# ---------------------------------------------------------------------------


class CloseScarCommand(CommandEnvelope):
    scar_id: uuid.UUID
    expected_version: int
    source_status_decision: str
    conclusion: str
    requalification_required: bool = False
    requalification_rationale: str | None = None
    capa_required: bool = False
    capa_rationale: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def close_scar(session: AsyncSession, cmd: CloseScarCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    scar = await _load_scar_for_update(session, cmd.scar_id, cmd.expected_version)
    if scar.state != "EFFECTIVENESS":
        raise InvalidTransitionError("Illegal SCAR transition", current_state=scar.state, requested="CLOSED")
    if not scar.effectiveness or scar.effectiveness.get("result") != "pass":
        raise EffectivenessRequiredError("Effectiveness verification must pass before closure")
    if cmd.source_status_decision not in SOURCE_STATUS_DECISIONS:
        raise ValidationFailedError("Unrecognized source_status_decision", source_status_decision=cmd.source_status_decision, allowed=list(SOURCE_STATUS_DECISIONS))
    if not cmd.conclusion.strip():
        raise ValidationFailedError("conclusion is required for QA closure")

    signature_id = await _resolve_signature(
        session, action="close", actor_user_id=actor_user_id, scar=scar,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = scar.state
    now = datetime.now(timezone.utc)
    scar.source_status_decision = cmd.source_status_decision
    scar.requalification_required = cmd.requalification_required
    scar.requalification_rationale = cmd.requalification_rationale
    scar.capa_required = cmd.capa_required
    scar.capa_rationale = cmd.capa_rationale
    if scar.closed_at is None:
        scar.closed_at = now
    scar.closure_history = [
        *scar.closure_history,
        {"conclusion": cmd.conclusion, "source_status_decision": cmd.source_status_decision, "closed_at": now.isoformat(),
         "closed_by": str(actor_user_id), "signature_id": str(signature_id) if signature_id else None},
    ]
    scar.state = "CLOSED"
    scar.version += 1

    case = await _load_case_for_update(session, scar.case_id)
    old_case_state = case.state
    case.state = "CLOSED"
    case.closed_at = now
    case.version += 1

    receipt = await _write_scar_receipt(
        session, cmd=cmd, payload_hash=payload_hash, scar=scar, action="Closed", actor_user_id=actor_user_id,
        reason=cmd.conclusion, old_state=old_state, event_type="SCARClosed",
        event_payload={"id": str(scar.id), "source_status_decision": cmd.source_status_decision},
        signature_id=signature_id, expected_version=cmd.expected_version, command_type="CloseScar",
    )
    await _write_case_audit_outbox(
        session, case=case, action="Closed", actor_user_id=actor_user_id, reason=cmd.conclusion, old_state=old_case_state,
        event_type="SCARClosed", event_payload={"id": str(case.id), "scar_id": str(scar.id)},
        correlation_id=receipt.correlation_id,
    )
    if cmd.source_status_decision == "suspend":
        await write_outbox_event(
            session, event_type="SupplierSourceSuspended", aggregate_type="supplier_quality_case", aggregate_id=case.id,
            aggregate_version=case.version, payload={"case_id": str(case.id), "supplier_id": str(case.supplier_id)},
            correlation_id=receipt.correlation_id,
        )
    return receipt
