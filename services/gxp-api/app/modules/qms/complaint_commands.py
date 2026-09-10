"""Document 35 (SPEC-QMS-010) — Complaint Management command handlers. See complaint_models.py's module
docstring for the state-machine fold-in rationale and the deferred scope (SG-103/SG-104).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.qms.complaint_models import (
    CONSTITUENT_CLASSIFICATIONS,
    SOURCE_CHANNELS,
    ComplaintCommunication,
    ComplaintReportabilityAssessment,
    ComplaintRecord,
)
from app.modules.qms.signature_support import enforce_signer_policy
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    ComplaintClosureBlockedError,
    ComplaintProductUnresolvedError,
    InvalidTransitionError,
    InvestigationDecisionRequiredError,
    MissingSignatureError,
    NoInvestigationRationaleRequiredError,
    NotFoundError,
    ReportabilityAssessmentRequiredError,
    StaleVersionError,
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


async def _load_complaint_for_update(session: AsyncSession, complaint_id: uuid.UUID, expected_version: int | None = None) -> ComplaintRecord:
    result = await session.execute(select(ComplaintRecord).where(ComplaintRecord.id == complaint_id).with_for_update())
    complaint = result.scalar_one_or_none()
    if complaint is None:
        raise NotFoundError("Complaint record not found")
    if expected_version is not None and complaint.version != expected_version:
        raise StaleVersionError(
            "Complaint record was modified by another actor since it was read",
            expected_version=expected_version, current_version=complaint.version,
        )
    return complaint


def _record_hash(complaint: ComplaintRecord) -> str:
    return sha256_hex({"id": str(complaint.id), "version": complaint.version})


async def _resolve_signature(
    session: AsyncSession, *, action: str, actor_user_id: uuid.UUID, complaint: ComplaintRecord,
    challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type="complaint_record", action=action)
    if not policy.signature_required:
        return None
    # Document 106 section 9 rows 101/102: close is `Approved` by a "QA Releaser" independent of the
    # investigator/owner; reportability is `Approved` by a "Regulatory Affairs authorized submitter"
    # (-> the "Postmarket Regulatory Affairs" role, project-owner-directed 2026-09-10) and is human-only,
    # not a person-independence rule (requires_independent_signer=False in the policy). ComplaintRecord
    # carries no owner/investigator identity column, so the `close` independence check has no data source
    # -- role is still enforced; the gap is the same one recorded for qa_review_package/complete.
    await enforce_signer_policy(
        session, policy=policy, actor_user_id=actor_user_id, site_id=complaint.site_id,
        action_label=f"complaint.{action}",
    )
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"Complaint '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=complaint.version, record_hash=_record_hash(complaint),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


async def _write_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, complaint: ComplaintRecord, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    signature_id: uuid.UUID | None, expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=complaint.site_id, aggregate_type="complaint_record", aggregate_id=complaint.id,
        aggregate_version=complaint.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": complaint.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="complaint_record", aggregate_id=complaint.id,
        aggregate_version=complaint.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=complaint.site_id, command_type=command_type, aggregate_type="complaint_record",
        aggregate_id=complaint.id, expected_version=expected_version, resulting_version=complaint.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=complaint.id, resulting_version=complaint.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create complaint — CMP-FR-001/002/004/005/023
# ---------------------------------------------------------------------------


class CreateComplaintCommand(CommandEnvelope):
    site_id: uuid.UUID
    complaint_number: str
    received_at: datetime
    source_channel: str
    nature_code: str
    description: str
    product_ref: uuid.UUID | None = None
    lot_batch_serial_refs: dict | None = None
    complainant_info: dict | None = None
    constituent_classification: str | None = None
    duplicate_of_id: uuid.UUID | None = None


async def create_complaint(session: AsyncSession, cmd: CreateComplaintCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.source_channel not in SOURCE_CHANNELS:
        raise ValidationFailedError("Unrecognized source_channel", source_channel=cmd.source_channel, allowed=list(SOURCE_CHANNELS))
    if cmd.constituent_classification is not None and cmd.constituent_classification not in CONSTITUENT_CLASSIFICATIONS:
        raise ValidationFailedError(
            "Unrecognized constituent_classification", constituent_classification=cmd.constituent_classification,
            allowed=list(CONSTITUENT_CLASSIFICATIONS),
        )
    if not cmd.nature_code.strip() or not cmd.description.strip():
        raise ValidationFailedError("nature_code and description are required")

    conflict = (await session.execute(select(ComplaintRecord).where(ComplaintRecord.complaint_number == cmd.complaint_number))).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("complaint_number is already in use", complaint_number=cmd.complaint_number)

    # CMP-FR-023: auto-detect a likely duplicate by nature_code + product_ref, plus any caller-supplied
    # duplicate_of_id -- never deletes or blocks the new intake, only links it.
    related_ids: list[str] = []
    if cmd.duplicate_of_id is not None:
        prior = await session.get(ComplaintRecord, cmd.duplicate_of_id)
        if prior is None:
            raise ValidationFailedError("duplicate_of_id does not reference an existing complaint", duplicate_of_id=str(cmd.duplicate_of_id))
        related_ids.append(str(prior.id))
    if cmd.product_ref is not None:
        auto_matches = (
            await session.execute(
                select(ComplaintRecord.id).where(
                    ComplaintRecord.nature_code == cmd.nature_code, ComplaintRecord.product_ref == cmd.product_ref,
                )
            )
        ).scalars().all()
        related_ids.extend(str(m) for m in auto_matches if str(m) not in related_ids)

    complaint = ComplaintRecord(
        site_id=cmd.site_id, complaint_number=cmd.complaint_number, received_at=cmd.received_at,
        source_channel=cmd.source_channel, product_ref=cmd.product_ref, lot_batch_serial_refs=cmd.lot_batch_serial_refs,
        complainant_info=cmd.complainant_info, nature_code=cmd.nature_code, description=cmd.description,
        constituent_classification=cmd.constituent_classification, is_potential_duplicate=bool(related_ids),
        related_complaint_ids=related_ids or None, state="RECEIVED",
    )
    session.add(complaint)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, complaint=complaint, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="RECEIVED", event_type="ComplaintReceived",
        event_payload={"id": str(complaint.id), "complaint_number": complaint.complaint_number, "is_potential_duplicate": complaint.is_potential_duplicate},
        signature_id=None, expected_version=None, command_type="CreateComplaint",
    )


# ---------------------------------------------------------------------------
# Triage — CMP-FR-004/005/006
# ---------------------------------------------------------------------------


class TriageComplaintCommand(CommandEnvelope):
    complaint_id: uuid.UUID
    expected_version: int
    triage: dict
    constituent_classification: str | None = None
    reason: str | None = None


async def triage_complaint(session: AsyncSession, cmd: TriageComplaintCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    complaint = await _load_complaint_for_update(session, cmd.complaint_id, cmd.expected_version)
    if complaint.state != "RECEIVED":
        raise InvalidTransitionError("Illegal complaint transition", current_state=complaint.state, requested="TRIAGE")
    if complaint.product_ref is None:
        raise ComplaintProductUnresolvedError("product_ref must be resolved before triage")
    if not cmd.triage:
        raise ValidationFailedError("triage assessment is required")
    if cmd.constituent_classification is not None and cmd.constituent_classification not in CONSTITUENT_CLASSIFICATIONS:
        raise ValidationFailedError(
            "Unrecognized constituent_classification", constituent_classification=cmd.constituent_classification,
            allowed=list(CONSTITUENT_CLASSIFICATIONS),
        )

    old_state = complaint.state
    complaint.triage = cmd.triage
    if cmd.constituent_classification is not None:
        complaint.constituent_classification = cmd.constituent_classification
    complaint.state = "TRIAGE"
    complaint.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, complaint=complaint, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="ComplaintReceived",
        event_payload={"id": str(complaint.id), "state": complaint.state}, signature_id=None,
        expected_version=cmd.expected_version, command_type="TriageComplaint",
    )


# ---------------------------------------------------------------------------
# Investigation decision — CMP-FR-007/008
# ---------------------------------------------------------------------------


class InvestigationDecisionCommand(CommandEnvelope):
    complaint_id: uuid.UUID
    expected_version: int
    investigation_required: bool
    no_investigation_reason: str | None = None


async def investigation_decision(session: AsyncSession, cmd: InvestigationDecisionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    complaint = await _load_complaint_for_update(session, cmd.complaint_id, cmd.expected_version)
    if complaint.state != "TRIAGE":
        raise InvalidTransitionError("Illegal complaint transition", current_state=complaint.state, requested="INVESTIGATION_DECISION")

    old_state = complaint.state
    complaint.investigation_required = cmd.investigation_required
    if cmd.investigation_required:
        complaint.state = "INVESTIGATION"
        event_type = "ComplaintInvestigationRequired"
    else:
        if not cmd.no_investigation_reason or not cmd.no_investigation_reason.strip():
            raise NoInvestigationRationaleRequiredError("no_investigation_reason is required when investigation_required is False")
        complaint.no_investigation_reason = cmd.no_investigation_reason
        complaint.state = "NO_INVESTIGATION_JUSTIFIED"
        event_type = "ComplaintInvestigationWaivedWithRationale"
    complaint.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, complaint=complaint, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.no_investigation_reason, old_state=old_state, event_type=event_type,
        event_payload={"id": str(complaint.id), "investigation_required": cmd.investigation_required},
        signature_id=None, expected_version=cmd.expected_version, command_type="InvestigationDecision",
    )


# ---------------------------------------------------------------------------
# Investigation — CMP-FR-009/010/011
# ---------------------------------------------------------------------------


class InvestigateComplaintCommand(CommandEnvelope):
    complaint_id: uuid.UUID
    expected_version: int
    findings: dict
    conclusion: str
    reason: str | None = None


async def investigate_complaint(session: AsyncSession, cmd: InvestigateComplaintCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    complaint = await _load_complaint_for_update(session, cmd.complaint_id, cmd.expected_version)
    if complaint.state != "INVESTIGATION":
        raise InvalidTransitionError("Illegal complaint transition", current_state=complaint.state, requested="REPORTABILITY_ASSESSMENT")
    if not cmd.findings:
        raise ValidationFailedError("findings are required")
    if not cmd.conclusion.strip():
        raise ValidationFailedError("conclusion is required")

    old_state = complaint.state
    complaint.investigation_findings = cmd.findings
    complaint.investigation_conclusion = cmd.conclusion
    complaint.state = "REPORTABILITY_ASSESSMENT"
    complaint.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, complaint=complaint, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="ComplaintInvestigationRequired",
        event_payload={"id": str(complaint.id), "state": complaint.state}, signature_id=None,
        expected_version=cmd.expected_version, command_type="InvestigateComplaint",
    )


# ---------------------------------------------------------------------------
# Reportability assessment — CMP-FR-012/013/014/015/017/018 (signature: Document 106 row 102)
# ---------------------------------------------------------------------------


class ReportabilityAssessmentCommand(CommandEnvelope):
    complaint_id: uuid.UUID
    expected_version: int
    applicable_regimes: list[str]
    rationale: str
    assessment_inputs: dict | None = None
    trigger_date: datetime | None = None
    due_date: datetime | None = None
    submission_reference: str | None = None
    submission_status: str | None = None
    capa_required: bool = False
    capa_rationale: str | None = None
    field_action_required: bool = False
    field_action_rationale: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def assess_reportability(session: AsyncSession, cmd: ReportabilityAssessmentCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    complaint = await _load_complaint_for_update(session, cmd.complaint_id, cmd.expected_version)
    if complaint.state == "TRIAGE":
        raise InvestigationDecisionRequiredError("An investigation decision must be made before reportability can be assessed")
    if complaint.state not in ("NO_INVESTIGATION_JUSTIFIED", "REPORTABILITY_ASSESSMENT"):
        raise InvalidTransitionError("Illegal complaint transition", current_state=complaint.state, requested="RESPONSE")
    if not cmd.applicable_regimes:
        raise ValidationFailedError("applicable_regimes must name at least one regime")
    if not cmd.rationale.strip():
        raise ValidationFailedError("rationale is required")

    signature_id = await _resolve_signature(
        session, action="reportability", actor_user_id=actor_user_id, complaint=complaint,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    assessment = ComplaintReportabilityAssessment(
        site_id=complaint.site_id, complaint_id=complaint.id, applicable_regimes=cmd.applicable_regimes,
        assessment_inputs=cmd.assessment_inputs, rationale=cmd.rationale, trigger_date=cmd.trigger_date,
        due_date=cmd.due_date, reviewer_subject_id=actor_user_id, submission_reference=cmd.submission_reference,
        submission_status=cmd.submission_status, capa_required=cmd.capa_required, capa_rationale=cmd.capa_rationale,
        field_action_required=cmd.field_action_required, field_action_rationale=cmd.field_action_rationale,
    )
    session.add(assessment)
    await session.flush()

    old_state = complaint.state
    complaint.state = "RESPONSE"
    complaint.version += 1

    receipt = await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, complaint=complaint, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=old_state, event_type="ComplaintReportabilityAssessmentCompleted",
        event_payload={"id": str(complaint.id), "assessment_id": str(assessment.id), "applicable_regimes": cmd.applicable_regimes},
        signature_id=signature_id, expected_version=cmd.expected_version, command_type="AssessReportability",
    )
    if cmd.capa_required:
        await write_outbox_event(
            session, event_type="ComplaintCAPAOpened", aggregate_type="complaint_record", aggregate_id=complaint.id,
            aggregate_version=complaint.version, payload={"id": str(complaint.id), "capa_rationale": cmd.capa_rationale},
            correlation_id=receipt.correlation_id,
        )
    if cmd.field_action_required:
        await write_outbox_event(
            session, event_type="ComplaintFieldActionAssessmentOpened", aggregate_type="complaint_record", aggregate_id=complaint.id,
            aggregate_version=complaint.version, payload={"id": str(complaint.id), "field_action_rationale": cmd.field_action_rationale},
            correlation_id=receipt.correlation_id,
        )
    return receipt


# ---------------------------------------------------------------------------
# Communication (acknowledgment / response) — CMP-FR-003/019
# ---------------------------------------------------------------------------


class RecordCommunicationCommand(CommandEnvelope):
    complaint_id: uuid.UUID
    expected_version: int
    direction: str
    communication_type: str
    message: str
    occurred_at: datetime
    recipient: str | None = None
    channel: str | None = None
    reference: str | None = None


async def record_communication(session: AsyncSession, cmd: RecordCommunicationCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    complaint = await _load_complaint_for_update(session, cmd.complaint_id, cmd.expected_version)
    if complaint.state == "CLOSED":
        raise InvalidTransitionError("Illegal complaint transition", current_state=complaint.state, requested="communication")
    if cmd.direction not in ("inbound", "outbound"):
        raise ValidationFailedError("direction must be 'inbound' or 'outbound'", direction=cmd.direction)
    if cmd.communication_type not in ("acknowledgment", "response", "update"):
        raise ValidationFailedError("Unrecognized communication_type", communication_type=cmd.communication_type)
    if not cmd.message.strip():
        raise ValidationFailedError("message is required")

    communication = ComplaintCommunication(
        site_id=complaint.site_id, complaint_id=complaint.id, direction=cmd.direction,
        communication_type=cmd.communication_type, recipient=cmd.recipient, channel=cmd.channel,
        occurred_at=cmd.occurred_at, message=cmd.message, reference=cmd.reference,
    )
    session.add(communication)
    await session.flush()

    old_state = complaint.state
    complaint.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, complaint=complaint, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="ComplaintReceived",
        event_payload={"id": str(complaint.id), "communication_id": str(communication.id), "communication_type": cmd.communication_type},
        signature_id=None, expected_version=cmd.expected_version, command_type="RecordCommunication",
    )


# ---------------------------------------------------------------------------
# Close — CMP-FR-020 (signature: Document 106 row 101)
# ---------------------------------------------------------------------------


class CloseComplaintCommand(CommandEnvelope):
    complaint_id: uuid.UUID
    expected_version: int
    conclusion: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def close_complaint(session: AsyncSession, cmd: CloseComplaintCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    complaint = await _load_complaint_for_update(session, cmd.complaint_id, cmd.expected_version)
    if complaint.state in ("RECEIVED", "TRIAGE", "NO_INVESTIGATION_JUSTIFIED", "INVESTIGATION"):
        raise ReportabilityAssessmentRequiredError("Reportability must be assessed before the complaint can be closed", current_state=complaint.state)
    if complaint.state != "RESPONSE":
        raise InvalidTransitionError("Illegal complaint transition", current_state=complaint.state, requested="CLOSED")
    if not cmd.conclusion.strip():
        raise ValidationFailedError("conclusion is required")

    responded = (
        await session.execute(
            select(ComplaintCommunication.id).where(
                ComplaintCommunication.complaint_id == complaint.id, ComplaintCommunication.direction == "outbound",
            )
        )
    ).first()
    if responded is None:
        raise ComplaintClosureBlockedError("A response to the complainant must be recorded before closure")

    signature_id = await _resolve_signature(
        session, action="close", actor_user_id=actor_user_id, complaint=complaint,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = complaint.state
    complaint.state = "CLOSED"
    complaint.closed_at = datetime.now(timezone.utc)
    complaint.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, complaint=complaint, action="Closed", actor_user_id=actor_user_id,
        reason=cmd.conclusion, old_state=old_state, event_type="ComplaintClosed",
        event_payload={"id": str(complaint.id)}, signature_id=signature_id, expected_version=cmd.expected_version,
        command_type="CloseComplaint",
    )
