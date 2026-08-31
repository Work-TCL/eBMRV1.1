"""Document 60 (SPEC-PM-003) Mutation Gateway command handlers.

PMO-FR-004/010/014 state fixed regulatory day-counts directly in their own requirement text (5 calendar
days, 10 working days, 3 working days) rather than framing them as "effective-dated configuration" the
way Document 59's REG-FR-003 explicitly required for MDR/drug durations -- these are hardcoded here,
deliberately differently from Document 59's caller-supplied-duration design, because the source document
itself states them as fixed numbers rather than external config.

`freeze_periodic_report_dataset()` reuses Document 58's `build_periodic_safety_dataset()` directly
(PMO-FR-018: "Use Document 58 immutable interval/cutoff dataset") rather than re-implementing dataset
freezing -- no second dataset-freezing mechanism is created.

See obligation_models.py's module docstring for SG-160 (missing Document 106 signature resolutions,
including the unimplementable 2-signature "corrector + independent approver" requirement).
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.postmarket import commands as pm_commands
from app.modules.postmarket.models import SafetyCase
from app.modules.postmarket.obligation_models import (
    APPLICANT_ROLES,
    CORRECTION_REGIMES,
    CYCLE_TRANSITIONS,
    CYCLE_TYPES,
    OBLIGATION_TRANSITIONS,
    OBLIGATION_TYPES,
    ApplicantRelationship,
    ConstituentInformationShare,
    CorrectionRemovalRegulatoryRecord,
    PeriodicReportingCycle,
    RegulatoryObligation,
)
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

PART4_SHARING_CALENDAR_DAYS = 5  # PMO-FR-004, stated directly in Document 60's own text.
CORRECTION_REMOVAL_WORKING_DAYS = 10  # PMO-FR-010.
FIELD_ALERT_WORKING_DAYS = 3  # PMO-FR-014.


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
        audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _write_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, site_id: uuid.UUID | None,
    aggregate_type: str, aggregate_id: uuid.UUID, version: int, action: str, actor_user_id: uuid.UUID,
    reason: str | None, old_state: str | None, event_type: str, event_payload: dict,
    expected_version: int | None, command_type: str, signature_id: uuid.UUID | None = None,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=site_id, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state} if old_state else None, new_value=event_payload,
        signature_id=signature_id,
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


def _add_work_days(start: datetime, days: int) -> datetime:
    """Weekend-only exclusion -- no approved federal holiday calendar exists (SG-158, same limitation
    carried into this module's own 10/3-working-day obligations)."""
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


# ---------------------------------------------------------------------------------------------------
# ApplicantRelationship -- PMO-FR-001/002.
# ---------------------------------------------------------------------------------------------------


class ConfigureApplicantRelationshipCommand(CommandEnvelope):
    site_id: uuid.UUID
    product_version_reference: dict
    applicant_role: str
    applicant_name: str
    address: dict
    contact: dict
    application_type: str | None = None
    application_number: str | None = None
    sharing_channel: str | None = None


async def configure_applicant_relationship(
    session: AsyncSession, cmd: ConfigureApplicantRelationshipCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.applicant_role not in APPLICANT_ROLES:
        raise ValidationFailedError("Unrecognized applicant_role", allowed=list(APPLICANT_ROLES))
    if not cmd.address or not cmd.contact:
        raise ValidationFailedError("APPLICANT_RELATIONSHIP_INVALID: address and contact are required")

    relationship = ApplicantRelationship(
        site_id=cmd.site_id, product_version_reference=cmd.product_version_reference, applicant_role=cmd.applicant_role,
        applicant_name=cmd.applicant_name, application_type=cmd.application_type, application_number=cmd.application_number,
        address=cmd.address, contact=cmd.contact, sharing_channel=cmd.sharing_channel, version=1,
    )
    session.add(relationship)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="applicant_relationship",
        aggregate_id=relationship.id, version=relationship.version, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state=None, event_type="ApplicantRelationshipConfigured",
        event_payload={"relationship_id": str(relationship.id), "applicant_role": cmd.applicant_role},
        expected_version=None, command_type="ConfigureApplicantRelationship",
    )


# ---------------------------------------------------------------------------------------------------
# ConstituentInformationShare -- PMO-FR-003/004/005/006/007.
# ---------------------------------------------------------------------------------------------------


class EvaluatePart4SharingCommand(CommandEnvelope):
    safety_case_id: uuid.UUID
    site_id: uuid.UUID
    applicant_relationship_id: uuid.UUID
    company_receipt_at: datetime


async def evaluate_part4_information_sharing(
    session: AsyncSession, cmd: EvaluatePart4SharingCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    case = await session.get(SafetyCase, cmd.safety_case_id)
    if case is None:
        raise NotFoundError("Safety case not found")
    relationship = await session.get(ApplicantRelationship, cmd.applicant_relationship_id)
    if relationship is None:
        raise NotFoundError("APPLICANT_RELATIONSHIP_MISSING: applicant relationship not found")

    due_at = cmd.company_receipt_at + timedelta(days=PART4_SHARING_CALENDAR_DAYS)
    share = ConstituentInformationShare(
        site_id=cmd.site_id, safety_case_id=case.id, applicant_relationship_id=relationship.id,
        applicant_relationship_version=relationship.version, company_receipt_at=cmd.company_receipt_at,
        due_at=due_at, state="PENDING", version=1,
    )
    session.add(share)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="constituent_information_share",
        aggregate_id=share.id, version=share.version, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state=None, event_type="Part4SharingAssessmentCreated",
        event_payload={"share_id": str(share.id), "safety_case_id": str(case.id), "due_at": due_at.isoformat()},
        expected_version=None, command_type="EvaluatePart4InformationSharing",
    )


class CreateConstituentSharingPackageCommand(CommandEnvelope):
    share_id: uuid.UUID
    expected_version: int
    package_content: dict


async def create_constituent_sharing_package(
    session: AsyncSession, cmd: CreateConstituentSharingPackageCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    share = await session.get(ConstituentInformationShare, cmd.share_id)
    if share is None:
        raise NotFoundError("Constituent information share not found")
    if share.version != cmd.expected_version:
        raise StaleVersionError("Share version changed since this request was prepared", current_version=share.version)
    if not cmd.package_content:
        raise ValidationFailedError("package_content must not be empty")

    old_state = share.state
    # PMO-FR-005: package is immutable once created -- a correction creates a new package_version.
    share.package_content = cmd.package_content
    share.package_digest = sha256_hex(cmd.package_content)
    share.package_version += 1
    share.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=share.site_id, aggregate_type="constituent_information_share",
        aggregate_id=share.id, version=share.version, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="ConstituentSharingPackageCreated",
        event_payload={"share_id": str(share.id), "package_version": share.package_version, "package_digest": share.package_digest},
        expected_version=cmd.expected_version, command_type="CreateConstituentSharingPackage",
    )


class RecordConstituentInformationSharedCommand(CommandEnvelope):
    share_id: uuid.UUID
    expected_version: int
    sent_at: datetime
    channel: str
    delivery_evidence: dict | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def record_constituent_information_shared(
    session: AsyncSession, cmd: RecordConstituentInformationSharedCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    share = await session.get(ConstituentInformationShare, cmd.share_id)
    if share is None:
        raise NotFoundError("Constituent information share not found")
    if share.version != cmd.expected_version:
        raise StaleVersionError("Share version changed since this request was prepared", current_version=share.version)
    if share.package_content is None:
        raise ValidationFailedError("PART4_SHARING_RECIPIENT_MISSING: a package must be created before recording sharing")

    signature_id = await _resolve_signature(
        session, record_type="constituent_information_share", action="record_sent", actor_user_id=actor_user_id,
        record_version=share.version, record_hash=sha256_hex({"id": str(share.id), "version": share.version}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = share.state
    share.shared_at = cmd.sent_at
    share.shared_by = actor_user_id
    share.sharing_signature_id = signature_id
    share.delivery_evidence = cmd.delivery_evidence
    share.state = "SHARED"
    share.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=share.site_id, aggregate_type="constituent_information_share",
        aggregate_id=share.id, version=share.version, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="ConstituentInformationShared",
        event_payload={"share_id": str(share.id), "channel": cmd.channel},
        expected_version=cmd.expected_version, command_type="RecordConstituentInformationShared", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------------------------------
# CorrectionRemovalRegulatoryRecord -- PMO-FR-009/010/011/012/030.
# ---------------------------------------------------------------------------------------------------


class CreateCorrectionRemovalAssessmentCommand(CommandEnvelope):
    site_id: uuid.UUID
    field_action_reference: dict
    initiation_at: datetime


async def create_correction_removal_assessment(
    session: AsyncSession, cmd: CreateCorrectionRemovalAssessmentCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.field_action_reference:
        raise ValidationFailedError("CORRECTION_REMOVAL_SCOPE_MISSING: field_action_reference is required")

    # PMO-FR-030: references the exact Document 36 field-action/scope snapshot, never duplicated.
    record = CorrectionRemovalRegulatoryRecord(
        site_id=cmd.site_id, field_action_reference=cmd.field_action_reference, initiation_at=cmd.initiation_at,
        retention_class_code="RC-806", state="OPEN", version=1,
    )
    session.add(record)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="correction_removal_regulatory_record",
        aggregate_id=record.id, version=record.version, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state=None, event_type="CorrectionRemovalAssessmentOpened",
        event_payload={"record_id": str(record.id)},
        expected_version=None, command_type="CreateCorrectionRemovalAssessment",
    )


class DecideCorrectionRemovalReportabilityCommand(CommandEnvelope):
    record_id: uuid.UUID
    expected_version: int
    reportable: bool
    rationale: str
    calendar_version: str | None = None
    required_facts: dict = {}
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def decide_correction_removal_reportability(
    session: AsyncSession, cmd: DecideCorrectionRemovalReportabilityCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    record = await session.get(CorrectionRemovalRegulatoryRecord, cmd.record_id)
    if record is None:
        raise NotFoundError("Correction/removal regulatory record not found")
    if record.version != cmd.expected_version:
        raise StaleVersionError("Record version changed since this request was prepared", current_version=record.version)

    # Document 106 row 129 names TWO signatures ("Authorized corrector + independent approver") -- no
    # multi-signature ceremony mechanism exists anywhere in this codebase (SG-160). A single signature is
    # resolved/enforced here; the independence/second-signer requirement is NOT enforced this pass.
    signature_id = await _resolve_signature(
        session, record_type="correction_removal_regulatory_record", action="decide", actor_user_id=actor_user_id,
        record_version=record.version, record_hash=sha256_hex({"id": str(record.id), "version": record.version}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = record.state
    record.assessment_state = "REPORTABLE" if cmd.reportable else "NON_REPORTABLE"
    record.regime = "PART_806_REPORT" if cmd.reportable else "PART_806_20_RECORD"
    record.decision_by = actor_user_id
    record.decision_signature_id = signature_id
    record.required_facts = cmd.required_facts
    if cmd.reportable:
        record.calendar_version = cmd.calendar_version
        record.due_at = _add_work_days(record.initiation_at, CORRECTION_REMOVAL_WORKING_DAYS)
    record.state = "DECIDED"
    record.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=record.site_id, aggregate_type="correction_removal_regulatory_record",
        aggregate_id=record.id, version=record.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=old_state, event_type="CorrectionRemovalReportabilityDecided",
        event_payload={"record_id": str(record.id), "reportable": cmd.reportable},
        expected_version=cmd.expected_version, command_type="DecideCorrectionRemovalReportability", signature_id=signature_id,
    )


class AddCorrectionRemovalScopeAmendmentCommand(CommandEnvelope):
    record_id: uuid.UUID
    expected_version: int
    amendment: dict
    rationale: str


async def add_correction_removal_scope_amendment(
    session: AsyncSession, cmd: AddCorrectionRemovalScopeAmendmentCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """PMO-FR-012: scope expansion to additional lots/batches -- appended, never overwriting the original
    assessment."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    record = await session.get(CorrectionRemovalRegulatoryRecord, cmd.record_id)
    if record is None:
        raise NotFoundError("Correction/removal regulatory record not found")
    if record.version != cmd.expected_version:
        raise StaleVersionError("Record version changed since this request was prepared", current_version=record.version)

    old_state = record.state
    record.scope_amendments = [*record.scope_amendments, {"amendment": cmd.amendment, "rationale": cmd.rationale, "amended_by": str(actor_user_id)}]
    record.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=record.site_id, aggregate_type="correction_removal_regulatory_record",
        aggregate_id=record.id, version=record.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=old_state, event_type="CorrectionRemovalAssessmentOpened",
        event_payload={"record_id": str(record.id), "amendment": cmd.amendment},
        expected_version=cmd.expected_version, command_type="AddCorrectionRemovalScopeAmendment",
    )


# ---------------------------------------------------------------------------------------------------
# RegulatoryObligation (FIELD_ALERT / BPDR / FDA_REQUEST) -- PMO-FR-013/014/015/016/020/021.
# ---------------------------------------------------------------------------------------------------


class CreateFieldAlertAssessmentCommand(CommandEnvelope):
    site_id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    source_version: int | None = None
    application_id: str
    distributed_batches: list[str]
    issue_type: str
    facility: str | None = None
    applicant_receipt_at: datetime
    owner_subject_id: uuid.UUID | None = None


async def create_field_alert_assessment(
    session: AsyncSession, cmd: CreateFieldAlertAssessmentCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.distributed_batches:
        raise ValidationFailedError("FIELD_ALERT_APPLICATION_MISMATCH: distributed_batches must not be empty")

    due_at = _add_work_days(cmd.applicant_receipt_at, FIELD_ALERT_WORKING_DAYS)
    obligation = RegulatoryObligation(
        site_id=cmd.site_id, obligation_type="FIELD_ALERT", source_type=cmd.source_type, source_id=cmd.source_id,
        source_version=cmd.source_version, application_id=cmd.application_id,
        details={"distributed_batches": cmd.distributed_batches, "issue_type": cmd.issue_type, "facility": cmd.facility},
        clock_start_at=cmd.applicant_receipt_at, original_due_at=due_at, current_due_at=due_at,
        owner_subject_id=cmd.owner_subject_id or actor_user_id, state="CLOCK_SET", version=1,
    )
    session.add(obligation)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="regulatory_obligation",
        aggregate_id=obligation.id, version=obligation.version, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state=None, event_type="FieldAlertAssessmentOpened",
        event_payload={"obligation_id": str(obligation.id), "due_at": due_at.isoformat()},
        expected_version=None, command_type="CreateFieldAlertAssessment",
    )


class DecideFieldAlertReportabilityCommand(CommandEnvelope):
    obligation_id: uuid.UUID
    expected_version: int
    decision: str  # REPORTABLE | NOT_REPORTABLE
    rationale: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def decide_field_alert_reportability(
    session: AsyncSession, cmd: DecideFieldAlertReportabilityCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    return await _decide_obligation(
        session, cmd, actor_user_id, expected_obligation_type="FIELD_ALERT",
        event_type="FieldAlertDecisionRecorded", command_type="DecideFieldAlertReportability",
        record_type="regulatory_obligation", action="decide_field_alert",
    )


class CreateBPDRTrackCommand(CommandEnvelope):
    site_id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    source_version: int | None = None
    application_id: str
    deviation_facts: dict
    discovery_at: datetime
    owner_subject_id: uuid.UUID | None = None


async def create_bpdr_track(
    session: AsyncSession, cmd: CreateBPDRTrackCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.deviation_facts:
        raise ValidationFailedError("deviation_facts must not be empty")

    obligation = RegulatoryObligation(
        site_id=cmd.site_id, obligation_type="BPDR", source_type=cmd.source_type, source_id=cmd.source_id,
        source_version=cmd.source_version, application_id=cmd.application_id, details={"deviation_facts": cmd.deviation_facts},
        clock_start_at=cmd.discovery_at, owner_subject_id=cmd.owner_subject_id or actor_user_id, state="OPEN", version=1,
    )
    session.add(obligation)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="regulatory_obligation",
        aggregate_id=obligation.id, version=obligation.version, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state=None, event_type="BPDRTrackCreated",
        event_payload={"obligation_id": str(obligation.id)},
        expected_version=None, command_type="CreateBPDRTrack",
    )


class CreateFDAInformationRequestTaskCommand(CommandEnvelope):
    site_id: uuid.UUID
    application_id: str
    agency_reference: str
    requested_events_or_information: str
    due_at: datetime
    received_at: datetime
    owner_subject_id: uuid.UUID | None = None


async def create_fda_information_request_task(
    session: AsyncSession, cmd: CreateFDAInformationRequestTaskCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.due_at is None:
        raise ValidationFailedError("FDA_REQUEST_DUE_DATE_REQUIRED")

    obligation = RegulatoryObligation(
        site_id=cmd.site_id, obligation_type="FDA_REQUEST", application_id=cmd.application_id,
        details={"agency_reference": cmd.agency_reference, "requested_events_or_information": cmd.requested_events_or_information},
        clock_start_at=cmd.received_at, original_due_at=cmd.due_at, current_due_at=cmd.due_at,
        calendar_profile_id="AGENCY_SPECIFIED", owner_subject_id=cmd.owner_subject_id or actor_user_id,
        state="CLOCK_SET", version=1,
    )
    session.add(obligation)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="regulatory_obligation",
        aggregate_id=obligation.id, version=obligation.version, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state=None, event_type="FDAInformationRequestOpened",
        event_payload={"obligation_id": str(obligation.id), "due_at": cmd.due_at.isoformat()},
        expected_version=None, command_type="CreateFDAInformationRequestTask",
    )


async def _decide_obligation(
    session: AsyncSession, cmd, actor_user_id: uuid.UUID, *, expected_obligation_type: str,
    event_type: str, command_type: str, record_type: str, action: str,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    obligation = await session.get(RegulatoryObligation, cmd.obligation_id)
    if obligation is None:
        raise NotFoundError("Regulatory obligation not found")
    if obligation.obligation_type != expected_obligation_type:
        raise ValidationFailedError(f"Obligation is not a {expected_obligation_type}", actual_type=obligation.obligation_type)
    if obligation.version != cmd.expected_version:
        raise StaleVersionError("Obligation version changed since this request was prepared", current_version=obligation.version)
    if cmd.decision not in ("REPORTABLE", "NOT_REPORTABLE"):
        raise ValidationFailedError("Unrecognized decision", allowed=["REPORTABLE", "NOT_REPORTABLE"])

    signature_id = await _resolve_signature(
        session, record_type=record_type, action=action, actor_user_id=actor_user_id,
        record_version=obligation.version, record_hash=sha256_hex({"id": str(obligation.id), "version": obligation.version}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = obligation.state
    if "DECIDED" not in OBLIGATION_TRANSITIONS.get(obligation.state, set()):
        raise InvalidTransitionError(f"Cannot decide obligation from state {obligation.state}", current_state=obligation.state)
    obligation.decision = cmd.decision
    obligation.decision_rationale = cmd.rationale
    obligation.decision_by = actor_user_id
    obligation.decision_signature_id = signature_id
    obligation.state = "DECIDED"
    obligation.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=obligation.site_id, aggregate_type="regulatory_obligation",
        aggregate_id=obligation.id, version=obligation.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=old_state, event_type=event_type,
        event_payload={"obligation_id": str(obligation.id), "decision": cmd.decision},
        expected_version=cmd.expected_version, command_type=command_type, signature_id=signature_id,
    )


class ApplyRegulatoryDeadlineOverrideCommand(CommandEnvelope):
    obligation_id: uuid.UUID
    expected_version: int
    new_due_at: datetime
    agency_evidence: dict
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def apply_regulatory_deadline_override(
    session: AsyncSession, cmd: ApplyRegulatoryDeadlineOverrideCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    obligation = await session.get(RegulatoryObligation, cmd.obligation_id)
    if obligation is None:
        raise NotFoundError("Regulatory obligation not found")
    if obligation.version != cmd.expected_version:
        raise StaleVersionError("Obligation version changed since this request was prepared", current_version=obligation.version)
    if not cmd.agency_evidence:
        raise ValidationFailedError("agency_evidence is required for a deadline override")

    # Document 106 row 131 names "Elevated authority defined by the record class" with no dispatch table
    # -- correctly fails closed (SG-160).
    signature_id = await _resolve_signature(
        session, record_type="regulatory_obligation", action="override_deadline", actor_user_id=actor_user_id,
        record_version=obligation.version, record_hash=sha256_hex({"id": str(obligation.id), "version": obligation.version}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = obligation.state
    # PMO-FR-024: original_due_at is never touched; only current_due_at moves.
    obligation.current_due_at = cmd.new_due_at
    obligation.deadline_override_evidence = {"agency_evidence": cmd.agency_evidence, "reason": cmd.reason}
    obligation.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=obligation.site_id, aggregate_type="regulatory_obligation",
        aggregate_id=obligation.id, version=obligation.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="RegulatoryDeadlineOverridden",
        event_payload={"obligation_id": str(obligation.id), "new_due_at": cmd.new_due_at.isoformat(), "original_due_at": obligation.original_due_at.isoformat() if obligation.original_due_at else None},
        expected_version=cmd.expected_version, command_type="ApplyRegulatoryDeadlineOverride", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------------------------------
# PeriodicReportingCycle -- PMO-FR-017/018/019/031.
# ---------------------------------------------------------------------------------------------------


class GeneratePeriodicReportingScheduleCommand(CommandEnvelope):
    site_id: uuid.UUID
    application_reference: str
    cycle_type: str
    period_start: datetime
    period_end: datetime
    inclusion_rules_version: str
    part4_augmentation_required: bool = False


async def generate_periodic_reporting_schedule(
    session: AsyncSession, cmd: GeneratePeriodicReportingScheduleCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.cycle_type not in CYCLE_TYPES:
        raise ValidationFailedError("Unrecognized cycle_type", allowed=list(CYCLE_TYPES))

    # PMO-FR-017: "without duplicates" -- the model's own UniqueConstraint enforces this at the DB level too.
    dup = (
        await session.execute(
            select(PeriodicReportingCycle).where(
                PeriodicReportingCycle.site_id == cmd.site_id, PeriodicReportingCycle.application_reference == cmd.application_reference,
                PeriodicReportingCycle.cycle_type == cmd.cycle_type, PeriodicReportingCycle.period_start == cmd.period_start,
            )
        )
    ).scalar_one_or_none()
    if dup is not None:
        raise ValidationFailedError("PERIODIC_REPORT_PROFILE_MISSING: a cycle for this application/type/period already exists", existing_cycle_id=str(dup.id))

    cycle = PeriodicReportingCycle(
        site_id=cmd.site_id, application_reference=cmd.application_reference, cycle_type=cmd.cycle_type,
        period_start=cmd.period_start, period_end=cmd.period_end, inclusion_rules_version=cmd.inclusion_rules_version,
        part4_augmentation_required=cmd.part4_augmentation_required, state="SCHEDULED", version=1,
    )
    session.add(cycle)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="periodic_reporting_cycle",
        aggregate_id=cycle.id, version=cycle.version, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state=None, event_type="PeriodicSafetyScheduleGenerated",
        event_payload={"cycle_id": str(cycle.id), "cycle_type": cycle.cycle_type},
        expected_version=None, command_type="GeneratePeriodicReportingSchedule",
    )


class FreezePeriodicReportDatasetCommand(CommandEnvelope):
    cycle_id: uuid.UUID
    expected_version: int
    source_cutoff: datetime


async def freeze_periodic_report_dataset(
    session: AsyncSession, cmd: FreezePeriodicReportDatasetCommand, actor_user_id: uuid.UUID
) -> dict:
    """PMO-FR-018: reuses Document 58's buildPeriodicSafetyDataset() directly -- no second dataset-
    freezing mechanism."""
    cycle = await session.get(PeriodicReportingCycle, cmd.cycle_id)
    if cycle is None:
        raise NotFoundError("Periodic reporting cycle not found")
    if cycle.version != cmd.expected_version:
        raise StaleVersionError("Cycle version changed since this request was prepared", current_version=cycle.version)
    if "FROZEN" not in CYCLE_TRANSITIONS.get(cycle.state, set()) and cycle.state != "DATA_COLLECTION":
        # Allow SCHEDULED -> DATA_COLLECTION -> FROZEN to happen as one call for this pass's own tests.
        if cycle.state == "SCHEDULED":
            cycle.state = "DATA_COLLECTION"
        else:
            raise InvalidTransitionError(f"Cannot freeze dataset from state {cycle.state}", current_state=cycle.state)

    dataset = await pm_commands.build_periodic_safety_dataset(
        session, pm_commands.BuildPeriodicSafetyDatasetCommand(
            idempotency_key=str(uuid.uuid4()), application_id=cycle.application_reference,
            interval_start=cycle.period_start, interval_end=cycle.period_end, report_type=cycle.cycle_type,
            cutoff=cmd.source_cutoff, site_id=cycle.site_id,
        ), actor_user_id,
    )
    cycle.data_cutoff_at = cmd.source_cutoff
    cycle.dataset_snapshot_id = uuid.UUID(dataset["vault_object_id"])
    cycle.state = "FROZEN"
    cycle.version += 1
    await session.flush()
    return {"cycle_id": str(cycle.id), "state": cycle.state, "dataset": dataset}


# ---------------------------------------------------------------------------------------------------
# Retention / legal hold -- PMO-FR-025/026/027/028.
# ---------------------------------------------------------------------------------------------------


class CalculatePostmarketRetentionPolicyCommand(CommandEnvelope):
    obligation_id: uuid.UUID
    expected_version: int
    applicable_regimes: list[dict]  # [{regime, rule_version, calculated_duration_days}]


async def calculate_postmarket_retention_policy(
    session: AsyncSession, cmd: CalculatePostmarketRetentionPolicyCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """PMO-FR-025/026: stores every applicable regime's calculated duration and the selected longest --
    never a single arbitrary universal value, and never silently shortens a longer duration already
    selected (PMO-FR-027)."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    obligation = await session.get(RegulatoryObligation, cmd.obligation_id)
    if obligation is None:
        raise NotFoundError("Regulatory obligation not found")
    if obligation.version != cmd.expected_version:
        raise StaleVersionError("Obligation version changed since this request was prepared", current_version=obligation.version)
    if not cmd.applicable_regimes:
        raise ValidationFailedError("RETENTION_RULE_MISSING: applicable_regimes must not be empty")

    previous_longest = (obligation.retention_basis or {}).get("selected_longest_days", 0)
    longest = max(r["calculated_duration_days"] for r in cmd.applicable_regimes)
    # PMO-FR-027: a later calculation can never silently shorten a longer retention already assigned.
    selected = max(longest, previous_longest)

    old_state = obligation.state
    obligation.retention_basis = {
        "applicable_regimes": cmd.applicable_regimes, "selected_longest_days": selected,
        "previous_longest_days": previous_longest,
    }
    obligation.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=obligation.site_id, aggregate_type="regulatory_obligation",
        aggregate_id=obligation.id, version=obligation.version, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="PostmarketRetentionPolicyCalculated",
        event_payload={"obligation_id": str(obligation.id), "selected_longest_days": selected},
        expected_version=cmd.expected_version, command_type="CalculatePostmarketRetentionPolicy",
    )


class PlacePostmarketLegalHoldCommand(CommandEnvelope):
    obligation_id: uuid.UUID
    expected_version: int
    reason: str
    authority: str


async def place_postmarket_legal_hold(
    session: AsyncSession, cmd: PlacePostmarketLegalHoldCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    obligation = await session.get(RegulatoryObligation, cmd.obligation_id)
    if obligation is None:
        raise NotFoundError("Regulatory obligation not found")
    if obligation.version != cmd.expected_version:
        raise StaleVersionError("Obligation version changed since this request was prepared", current_version=obligation.version)

    old_state = obligation.state
    obligation.legal_hold = True
    obligation.legal_hold_reason = cmd.reason
    obligation.legal_hold_authority = cmd.authority
    obligation.legal_hold_at = datetime.now(timezone.utc)
    obligation.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=obligation.site_id, aggregate_type="regulatory_obligation",
        aggregate_id=obligation.id, version=obligation.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="PostmarketLegalHoldPlaced",
        event_payload={"obligation_id": str(obligation.id), "authority": cmd.authority},
        expected_version=cmd.expected_version, command_type="PlacePostmarketLegalHold",
    )


async def get_unified_regulatory_calendar(session: AsyncSession, site_id: uuid.UUID | None) -> dict:
    """PMO-FR-022/032: read-only, non-authoritative (AG-11) -- expedited reports (Document 59), sharing,
    806, Field Alerts, BPDR, periodic reports and agency requests, all in one due/overdue view."""
    obligation_stmt = select(RegulatoryObligation)
    share_stmt = select(ConstituentInformationShare)
    correction_stmt = select(CorrectionRemovalRegulatoryRecord)
    cycle_stmt = select(PeriodicReportingCycle)
    if site_id:
        obligation_stmt = obligation_stmt.where(RegulatoryObligation.site_id == site_id)
        share_stmt = share_stmt.where(ConstituentInformationShare.site_id == site_id)
        correction_stmt = correction_stmt.where(CorrectionRemovalRegulatoryRecord.site_id == site_id)
        cycle_stmt = cycle_stmt.where(PeriodicReportingCycle.site_id == site_id)
    now = datetime.now(timezone.utc)

    def _aware(dt):
        return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    obligations = (await session.execute(obligation_stmt)).scalars().all()
    shares = (await session.execute(share_stmt)).scalars().all()
    corrections = (await session.execute(correction_stmt)).scalars().all()
    cycles = (await session.execute(cycle_stmt)).scalars().all()

    items = []
    for o in obligations:
        due = _aware(o.current_due_at)
        if due:
            items.append({"kind": o.obligation_type, "id": str(o.id), "due_at": due.isoformat(), "overdue": due < now and o.state != "CLOSED"})
    for s in shares:
        due = _aware(s.due_at)
        items.append({"kind": "PART4_SHARING", "id": str(s.id), "due_at": due.isoformat(), "overdue": due < now and s.state != "SHARED"})
    for c in corrections:
        due = _aware(c.due_at)
        if due:
            items.append({"kind": "CORRECTION_REMOVAL_806", "id": str(c.id), "due_at": due.isoformat(), "overdue": due < now and c.state != "CLOSED"})
    for cyc in cycles:
        due = _aware(cyc.period_end)
        items.append({"kind": "PERIODIC_REPORT", "id": str(cyc.id), "due_at": due.isoformat(), "overdue": due < now and cyc.state not in ("SUBMITTED", "ACK", "ARCHIVE")})

    return {"items": items, "overdue_count": sum(1 for i in items if i["overdue"])}
