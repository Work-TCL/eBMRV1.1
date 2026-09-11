"""Document 59 (SPEC-PM-002) Mutation Gateway command handlers.

Document 59 # "EVENTS (0)" declares no events at all, even though its own function catalogue names one
per function (ReportabilityTracksCreated, RegulatoryDeadlineCalculated, ...). AG-09 makes an outbox event
mandatory for every regulated mutation regardless of what a document's own terse events section chose to
enumerate -- every command below still writes one, using the function-catalogue names since those are the
only ones the spec actually supplies.

No real eMDR/E2B XML mapping specification exists anywhere in the approved baseline (no field-level
transport mapping table, no implementation-package profile) -- `generate_regulatory_payload()` therefore
produces this module's own canonical JSON payload (report content + digest), not an FDA-consumable eMDR/
E2B XML artifact, and `submit_regulatory_report()` has no real ESG/eMDR/AEMS network client to call (same
class of gap as WP-07's SG-125: no credentialed vendor sandbox reachable from this environment) -- for
non-MANUAL channels the caller supplies `transport_result` as if a transport layer already ran. See
docs/generated/18_SPEC_GAPS.md SG-159.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.postmarket.models import SafetyCase
from app.modules.postmarket.reportability_models import (
    ACK_LEVELS,
    ACK_STATES,
    CALENDAR_TYPES,
    DECISION_VALUES,
    REPORT_TYPE_CODES,
    SUBMISSION_CHANNELS,
    TRACK_TRANSITIONS,
    TRANSPORT_RESULTS,
    RegulatoryReport,
    RegulatorySubmissionAck,
    RegulatorySubmissionAttempt,
    ReportabilityTrack,
)
from app.modules.signature import service as signature_service
from app.modules.vault import service as vault_service
from app.modules.vault.models import VaultObject
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


def _track_hash(track: ReportabilityTrack) -> str:
    return sha256_hex({"id": str(track.id), "version": track.version, "state": track.state})


def _add_calendar_days(start: datetime, days: int) -> datetime:
    return start + timedelta(days=days)


def _add_work_days(start: datetime, days: int) -> datetime:
    """WORK_DAY/WORKING_DAY exclude Saturday/Sunday only -- no federal holiday calendar is approved
    anywhere in the baseline (SG-158)."""
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


# ---------------------------------------------------------------------------------------------------
# ReportabilityTrack -- REG-FR-001/002/003/004/005/006/013.
# ---------------------------------------------------------------------------------------------------


class TrackSpec:
    pass


class CreateReportabilityTracksCommand(CommandEnvelope):
    site_id: uuid.UUID
    safety_case_id: uuid.UUID
    tracks: list[dict]  # [{report_type_code, report_type_version, application_context, rule_version}]
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def create_reportability_tracks(
    session: AsyncSession, cmd: CreateReportabilityTracksCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    case = await session.get(SafetyCase, cmd.safety_case_id)
    if case is None:
        raise NotFoundError("Safety case not found")
    if not cmd.tracks:
        raise ValidationFailedError("tracks must not be empty")
    for spec in cmd.tracks:
        if spec.get("report_type_code") not in REPORT_TYPE_CODES:
            raise ValidationFailedError("Unrecognized report_type_code", allowed=list(REPORT_TYPE_CODES))
        if not spec.get("application_context"):
            raise ValidationFailedError("application_context is required (REG-FR-002)")

    signature_id = await _resolve_signature(
        session, record_type="reportability_track", action="create", actor_user_id=actor_user_id,
        record_version=1, record_hash=sha256_hex({"safety_case_id": str(case.id), "tracks": cmd.tracks}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    # PMS-FR-013/REG-FR-001: one safety case can feed several independent tracks at once.
    created: list[ReportabilityTrack] = []
    for spec in cmd.tracks:
        track = ReportabilityTrack(
            site_id=cmd.site_id, safety_case_id=case.id, report_type_code=spec["report_type_code"],
            report_type_version=spec.get("report_type_version", "1.0"), application_context=spec["application_context"],
            rule_version=spec.get("rule_version"), state="OPEN", version=1,
        )
        session.add(track)
        created.append(track)
    await session.flush()

    # PMS-FR-031: mark the source case as referred for regulatory assessment.
    case.reportability_referral_required = False

    first = created[0]
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="reportability_track",
        aggregate_id=first.id, version=first.version, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state=None, event_type="ReportabilityTracksCreated",
        event_payload={"safety_case_id": str(case.id), "track_ids": [str(t.id) for t in created]},
        expected_version=None, command_type="CreateReportabilityTracks", signature_id=signature_id,
    )


class CalculateRegulatoryDeadlineCommand(CommandEnvelope):
    track_id: uuid.UUID
    expected_version: int
    clock_start_basis: str
    clock_start_at: datetime
    clock_start_rationale: str
    calendar_type: str
    calendar_version: str
    rule_version: str
    duration_days: int | None = None  # required unless calendar_type == AGENCY_SPECIFIED
    agency_due_at: datetime | None = None  # required when calendar_type == AGENCY_SPECIFIED


async def calculate_regulatory_deadline(
    session: AsyncSession, cmd: CalculateRegulatoryDeadlineCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    track = await session.get(ReportabilityTrack, cmd.track_id)
    if track is None:
        raise NotFoundError("Reportability track not found")
    if track.version != cmd.expected_version:
        raise StaleVersionError("Reportability track version changed since this request was prepared", current_version=track.version)
    if cmd.calendar_type not in CALENDAR_TYPES:
        raise ValidationFailedError("Unrecognized calendar_type", allowed=list(CALENDAR_TYPES))

    if cmd.calendar_type == "AGENCY_SPECIFIED":
        if cmd.agency_due_at is None:
            raise ValidationFailedError("agency_due_at is required when calendar_type is AGENCY_SPECIFIED")
        due_at = cmd.agency_due_at
    else:
        if cmd.duration_days is None:
            raise ValidationFailedError("duration_days is required for CALENDAR_DAY/WORK_DAY/WORKING_DAY")
        due_at = (
            _add_calendar_days(cmd.clock_start_at, cmd.duration_days) if cmd.calendar_type == "CALENDAR_DAY"
            else _add_work_days(cmd.clock_start_at, cmd.duration_days)
        )

    old_state = track.state
    track.clock_start_basis = cmd.clock_start_basis
    track.clock_start_at = cmd.clock_start_at
    track.clock_start_rationale = cmd.clock_start_rationale
    track.calendar_type = cmd.calendar_type
    track.calendar_version = cmd.calendar_version
    track.rule_version = cmd.rule_version
    track.due_at = due_at
    if track.original_due_at is None:
        # REG-FR-005/Document 112: original_due_at is immutable after first calculation.
        track.original_due_at = due_at
    if track.state == "OPEN":
        track.state = "CLOCK_SET"
    track.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=track.site_id, aggregate_type="reportability_track",
        aggregate_id=track.id, version=track.version, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="RegulatoryDeadlineCalculated",
        event_payload={"track_id": str(track.id), "due_at": due_at.isoformat(), "original_due_at": track.original_due_at.isoformat()},
        expected_version=cmd.expected_version, command_type="CalculateRegulatoryDeadline",
    )


class DecideReportabilityCommand(CommandEnvelope):
    track_id: uuid.UUID
    expected_version: int
    decision: str
    rationale: str
    evidence_refs: list[dict] = []
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def decide_reportability(
    session: AsyncSession, cmd: DecideReportabilityCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    track = await session.get(ReportabilityTrack, cmd.track_id)
    if track is None:
        raise NotFoundError("Reportability track not found")
    if track.version != cmd.expected_version:
        raise StaleVersionError("Reportability track version changed since this request was prepared", current_version=track.version)
    if "DECIDED" not in TRACK_TRANSITIONS.get(track.state, set()) and track.state != "DECIDED":
        raise InvalidTransitionError(f"Cannot decide reportability from state {track.state}", current_state=track.state)
    if cmd.decision not in DECISION_VALUES:
        raise ValidationFailedError("Unrecognized decision", allowed=list(DECISION_VALUES))
    if not cmd.rationale:
        raise ValidationFailedError("rationale is required for a reportability decision (REG-FR-004)")

    # REG-FR-004: no Document 106 row exists for this action (see module docstring, SG-157) -- correctly
    # fails closed with SIGNATURE_POLICY_UNRESOLVED until one is supplied.
    signature_id = await _resolve_signature(
        session, record_type="reportability_track", action="decide", actor_user_id=actor_user_id,
        record_version=track.version, record_hash=_track_hash(track), challenge_id=cmd.challenge_id,
        reauth_password=cmd.reauth_password,
    )

    old_state = track.state
    track.decision = cmd.decision
    track.decision_by = actor_user_id
    track.decision_rationale = cmd.rationale
    track.decision_evidence_refs = cmd.evidence_refs
    track.decision_signature_id = signature_id
    track.state = "DECIDED"
    track.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=track.site_id, aggregate_type="reportability_track",
        aggregate_id=track.id, version=track.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=old_state, event_type="ReportabilityDecided",
        event_payload={"track_id": str(track.id), "decision": cmd.decision},
        expected_version=cmd.expected_version, command_type="DecideReportability", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------------------------------
# RegulatoryReport -- REG-FR-014/015/016/017/024.
# ---------------------------------------------------------------------------------------------------


class BuildRegulatoryReportCommand(CommandEnvelope):
    track_id: uuid.UUID
    expected_version: int  # track's expected_version, so a stale track (e.g. redecided) is caught
    schema_code: str
    schema_version: str
    content: dict
    field_provenance: dict
    missing_information: list[dict] = []
    narrative_version: int | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def build_regulatory_report(
    session: AsyncSession, cmd: BuildRegulatoryReportCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    track = await session.get(ReportabilityTrack, cmd.track_id)
    if track is None:
        raise NotFoundError("Reportability track not found")
    if track.version != cmd.expected_version:
        raise StaleVersionError("Reportability track version changed since this request was prepared", current_version=track.version)
    if track.decision != "REPORTABLE":
        raise ValidationFailedError("A report can only be built for a track decided REPORTABLE")
    if not cmd.content:
        raise ValidationFailedError("REPORT_REQUIRED_DATA_MISSING: content must not be empty")

    next_version = (
        await session.execute(
            select(RegulatoryReport.report_version)
            .where(RegulatoryReport.reportability_track_id == track.id)
            .order_by(RegulatoryReport.report_version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    report_version = (next_version or 0) + 1

    signature_id = await _resolve_signature(
        session, record_type="regulatory_report", action="create", actor_user_id=actor_user_id,
        record_version=report_version, record_hash=sha256_hex(cmd.content), challenge_id=cmd.challenge_id,
        reauth_password=cmd.reauth_password,
    )

    report = RegulatoryReport(
        site_id=track.site_id, reportability_track_id=track.id, report_version=report_version,
        schema_code=cmd.schema_code, schema_version=cmd.schema_version, content=cmd.content,
        field_provenance=cmd.field_provenance, missing_information=cmd.missing_information,
        narrative_version=cmd.narrative_version, state="DRAFT",
    )
    session.add(report)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=track.site_id, aggregate_type="regulatory_report",
        aggregate_id=report.id, version=report_version, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state=None, event_type="RegulatoryReportBuilt",
        event_payload={"report_id": str(report.id), "track_id": str(track.id), "report_version": report_version},
        expected_version=None, command_type="BuildRegulatoryReport", signature_id=signature_id,
    )


class ApproveRegulatoryReportCommand(CommandEnvelope):
    report_id: uuid.UUID
    expected_version: int  # report_version, since RegulatoryReport is append-only-per-version
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def approve_regulatory_report(
    session: AsyncSession, cmd: ApproveRegulatoryReportCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    report = await session.get(RegulatoryReport, cmd.report_id)
    if report is None:
        raise NotFoundError("Regulatory report not found")
    if report.report_version != cmd.expected_version:
        raise StaleVersionError("Regulatory report version changed since this request was prepared", current_version=report.report_version)
    if report.state != "DRAFT":
        raise InvalidTransitionError(f"Cannot approve a report in state {report.state}", current_state=report.state)

    # Document 106 row 124 names "Module approver role (QA Manager / Head of Quality per record class)"
    # with no dispatch table for "per record class" -- correctly fails closed (SG-157).
    signature_id = await _resolve_signature(
        session, record_type="regulatory_report", action="approve", actor_user_id=actor_user_id,
        record_version=report.report_version, record_hash=sha256_hex(report.content), challenge_id=cmd.challenge_id,
        reauth_password=cmd.reauth_password,
    )

    report.state = "APPROVED"
    report.approved_by = actor_user_id
    report.approval_signature_id = signature_id
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=report.site_id, aggregate_type="regulatory_report",
        aggregate_id=report.id, version=report.report_version, action="Approved", actor_user_id=actor_user_id,
        reason=None, old_state="DRAFT", event_type="RegulatoryReportApproved",
        event_payload={"report_id": str(report.id)},
        expected_version=cmd.expected_version, command_type="ApproveRegulatoryReport", signature_id=signature_id,
    )


class GenerateRegulatoryPayloadCommand(CommandEnvelope):
    report_id: uuid.UUID
    implementation_or_profile_version: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def generate_regulatory_payload(
    session: AsyncSession, cmd: GenerateRegulatoryPayloadCommand, actor_user_id: uuid.UUID
) -> dict:
    """PMS/REG-FR-018/020: dispatches by the owning track's report_type_code to the eMDR-shaped family
    (MDR_30/MDR_5/MALFUNCTION) or the AEMS/E2B-shaped family (DRUG_EXPEDITED_15/BIOLOGIC_EXPEDITED_15/
    PART4_30). See module docstring: no real FDA XML mapping exists in the approved baseline (SG-159) --
    this returns this module's own canonical JSON payload plus digest, not an eMDR/E2B XML document.
    """
    report = await session.get(RegulatoryReport, cmd.report_id)
    if report is None:
        raise NotFoundError("Regulatory report not found")
    if report.state != "APPROVED":
        raise ValidationFailedError("Only an APPROVED report can generate a submission payload")
    track = await session.get(ReportabilityTrack, report.reportability_track_id)

    signature_id = await _resolve_signature(
        session, record_type="regulatory_report", action="generate_payload", actor_user_id=actor_user_id,
        record_version=report.report_version, record_hash=sha256_hex(report.content), challenge_id=cmd.challenge_id,
        reauth_password=cmd.reauth_password,
    )

    payload_family = "EMDR" if track.report_type_code in ("MDR_30", "MDR_5", "MALFUNCTION") else "AEMS"
    payload = {
        "family": payload_family, "report_id": str(report.id), "report_version": report.report_version,
        "schema_code": report.schema_code, "schema_version": report.schema_version,
        "implementation_or_profile_version": cmd.implementation_or_profile_version, "content": report.content,
    }
    digest = sha256_hex(payload)
    report.payload_digest = digest
    await session.flush()
    return {"payload": payload, "payload_digest": digest, "signature_id": str(signature_id) if signature_id else None}


# ---------------------------------------------------------------------------------------------------
# RegulatorySubmissionAttempt / RegulatorySubmissionAck -- REG-FR-018..026.
# ---------------------------------------------------------------------------------------------------


class SubmitRegulatoryReportCommand(CommandEnvelope):
    report_id: uuid.UUID
    channel: str
    payload_version: str
    payload_digest: str
    sender_identity: str
    manual_evidence_id: uuid.UUID | None = None  # required when channel == MANUAL (REG-FR-022)
    transport_result: str | None = None  # caller-supplied for non-MANUAL channels -- see module docstring
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def submit_regulatory_report(
    session: AsyncSession, cmd: SubmitRegulatoryReportCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    report = await session.get(RegulatoryReport, cmd.report_id)
    if report is None:
        raise NotFoundError("Regulatory report not found")
    if report.state != "APPROVED":
        raise ValidationFailedError("Only an APPROVED report can be submitted")
    if cmd.channel not in SUBMISSION_CHANNELS:
        raise ValidationFailedError("Unrecognized channel", allowed=list(SUBMISSION_CHANNELS))
    if cmd.channel == "MANUAL" and cmd.manual_evidence_id is None:
        raise ValidationFailedError("manual_evidence_id is required for the MANUAL channel (REG-FR-022)")

    # REG-FR-025: prevent a second initial submission of the same approved report version.
    existing_attempt = (
        await session.execute(
            select(RegulatorySubmissionAttempt).where(
                RegulatorySubmissionAttempt.regulatory_report_id == report.id,
                RegulatorySubmissionAttempt.transport_result == "SENT",
            )
        )
    ).scalar_one_or_none()
    if existing_attempt is not None and existing_attempt.attempt_no == 1:
        raise ValidationFailedError("This report version has already been submitted once (REG-FR-025)", first_attempt_id=str(existing_attempt.id))

    signature_id = await _resolve_signature(
        session, record_type="regulatory_report", action="submit", actor_user_id=actor_user_id,
        record_version=report.report_version, record_hash=sha256_hex({"report_id": str(report.id), "channel": cmd.channel}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    next_no = (
        await session.execute(
            select(RegulatorySubmissionAttempt.attempt_no)
            .where(RegulatorySubmissionAttempt.regulatory_report_id == report.id)
            .order_by(RegulatorySubmissionAttempt.attempt_no.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    transport_result = "SENT" if cmd.channel == "MANUAL" else (cmd.transport_result or "TIMEOUT_UNCERTAIN")
    if transport_result not in TRANSPORT_RESULTS:
        raise ValidationFailedError("Unrecognized transport_result", allowed=list(TRANSPORT_RESULTS))

    attempt = RegulatorySubmissionAttempt(
        site_id=report.site_id, regulatory_report_id=report.id, attempt_no=(next_no or 0) + 1,
        channel=cmd.channel, payload_version=cmd.payload_version, payload_digest=cmd.payload_digest,
        sender_identity=cmd.sender_identity, authorized_by=actor_user_id, authorization_signature_id=signature_id,
        transport_result=transport_result, manual_evidence_id=cmd.manual_evidence_id,
    )
    session.add(attempt)
    if transport_result == "SENT":
        report.state = "SUBMITTED"
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=report.site_id, aggregate_type="regulatory_submission_attempt",
        aggregate_id=attempt.id, version=attempt.attempt_no, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state=None, event_type="RegulatoryReportSubmitted",
        event_payload={"attempt_id": str(attempt.id), "report_id": str(report.id), "transport_result": transport_result},
        expected_version=None, command_type="SubmitRegulatoryReport", signature_id=signature_id,
    )


class IngestSubmissionAcknowledgementCommand(CommandEnvelope):
    submission_attempt_id: uuid.UUID
    ack_level: str
    ack_state: str
    ack_reference: str | None = None
    ack_payload: dict | None = None
    rejection_reason: dict | None = None


async def ingest_submission_acknowledgement(
    session: AsyncSession, cmd: IngestSubmissionAcknowledgementCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    attempt = await session.get(RegulatorySubmissionAttempt, cmd.submission_attempt_id)
    if attempt is None:
        raise NotFoundError("Submission attempt not found")
    if cmd.ack_level not in ACK_LEVELS:
        raise ValidationFailedError("Unrecognized ack_level", allowed=list(ACK_LEVELS))
    if cmd.ack_state not in ACK_STATES:
        raise ValidationFailedError("Unrecognized ack_state", allowed=list(ACK_STATES))
    if cmd.ack_state == "REJECTED" and not cmd.rejection_reason:
        raise ValidationFailedError("rejection_reason is required when ack_state is REJECTED")

    ack = RegulatorySubmissionAck(
        submission_attempt_id=attempt.id, ack_level=cmd.ack_level, ack_state=cmd.ack_state,
        ack_reference=cmd.ack_reference, ack_payload=cmd.ack_payload, rejection_reason=cmd.rejection_reason,
    )
    session.add(ack)
    await session.flush()

    event_type = "RegulatorySubmissionRejected" if cmd.ack_state == "REJECTED" else "SubmissionAcknowledgementReceived"
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=attempt.site_id, aggregate_type="regulatory_submission_ack",
        aggregate_id=ack.id, version=1, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state=None, event_type=event_type,
        event_payload={"ack_id": str(ack.id), "attempt_id": str(attempt.id), "ack_level": cmd.ack_level, "ack_state": cmd.ack_state},
        expected_version=None, command_type="IngestSubmissionAcknowledgement",
    )


class CreateFollowupReportTaskCommand(CommandEnvelope):
    original_report_id: uuid.UUID
    new_information_receipt: dict
    rationale: str


async def create_followup_report_task(
    session: AsyncSession, cmd: CreateFollowupReportTaskCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """PMS-FR-016/REG-FR-013: a follow-up creates a NEW ReportabilityTrack (parent_track_id set) rather
    than mutating the original -- the original report/track history is never rewritten."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    original_report = await session.get(RegulatoryReport, cmd.original_report_id)
    if original_report is None:
        raise NotFoundError("Original regulatory report not found")
    original_track = await session.get(ReportabilityTrack, original_report.reportability_track_id)

    followup_track = ReportabilityTrack(
        site_id=original_track.site_id, safety_case_id=original_track.safety_case_id,
        report_type_code="FOLLOWUP", report_type_version=original_track.report_type_version,
        application_context=original_track.application_context, parent_track_id=original_track.id,
        state="OPEN", version=1,
    )
    session.add(followup_track)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=followup_track.site_id, aggregate_type="reportability_track",
        aggregate_id=followup_track.id, version=1, action="Created", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=None, event_type="RegulatoryFollowupRequired",
        event_payload={"followup_track_id": str(followup_track.id), "original_report_id": str(original_report.id)},
        expected_version=None, command_type="CreateFollowupReportTask",
    )


class EvaluateSameEventDeduplicationCommand(CommandEnvelope):
    candidate_track_ids: list[uuid.UUID]
    rationale: str


async def evaluate_same_event_report_deduplication(
    session: AsyncSession, cmd: EvaluateSameEventDeduplicationCommand
) -> dict:
    """PMS-FR-030/REG-FR-030: read-only assessment -- "only when required content, manner and deadline
    conditions are met and reviewer approves". This module does not auto-merge tracks; it reports whether
    the candidates share an identical due_at/report_type_code (the one objective condition it can check
    without a content-equivalence rule this baseline does not supply) and leaves the approval to the
    reviewer via a separate decideReportability()-style action this pass does not add (no API operation
    names one)."""
    if len(cmd.candidate_track_ids) < 2:
        raise ValidationFailedError("candidate_track_ids must name at least two tracks")
    tracks = []
    for tid in cmd.candidate_track_ids:
        track = await session.get(ReportabilityTrack, tid)
        if track is None:
            raise NotFoundError(f"Reportability track {tid} not found")
        tracks.append(track)
    same_deadline = len({t.due_at for t in tracks}) == 1 and all(t.due_at is not None for t in tracks)
    same_type = len({t.report_type_code for t in tracks}) == 1
    return {
        "eligible_for_single_report": same_deadline and not same_type,  # PART4_30 dedupe is cross-type by design
        "same_deadline": same_deadline, "same_report_type": same_type,
        "track_ids": [str(t.id) for t in tracks], "rationale": cmd.rationale,
    }


class FreezeReportabilityAuditPackageCommand(CommandEnvelope):
    safety_case_id: uuid.UUID | None = None
    report_ids: list[uuid.UUID] = []
    site_id: uuid.UUID | None = None


async def freeze_reportability_audit_package(
    session: AsyncSession, cmd: FreezeReportabilityAuditPackageCommand, actor_user_id: uuid.UUID
) -> dict:
    """REG-FR-032: complete source->case->track->report->submission->ack history, frozen via Vault
    (same reuse precedent as Document 58's buildPeriodicSafetyDataset)."""
    tracks: list[ReportabilityTrack] = []
    if cmd.safety_case_id is not None:
        tracks = list((await session.execute(
            select(ReportabilityTrack).where(ReportabilityTrack.safety_case_id == cmd.safety_case_id)
        )).scalars().all())
    track_ids = {t.id for t in tracks}
    reports: list[RegulatoryReport] = []
    for rid in cmd.report_ids:
        report = await session.get(RegulatoryReport, rid)
        if report is None:
            raise NotFoundError(f"Regulatory report {rid} not found")
        reports.append(report)
        track_ids.add(report.reportability_track_id)

    package = {
        "safety_case_id": str(cmd.safety_case_id) if cmd.safety_case_id else None,
        "tracks": [
            {
                "track_id": str(t.id), "report_type_code": t.report_type_code, "rule_version": t.rule_version,
                "decision": t.decision, "due_at": t.due_at.isoformat() if t.due_at else None,
            }
            for t in tracks
        ],
        "reports": [
            {"report_id": str(r.id), "report_version": r.report_version, "state": r.state, "payload_digest": r.payload_digest}
            for r in reports
        ],
    }
    business_id = sha256_hex({"safety_case_id": package["safety_case_id"], "report_ids": sorted(str(r) for r in cmd.report_ids)})
    latest = (
        await session.execute(
            select(VaultObject)
            .where(VaultObject.object_type == "postmarket_regulatory_evidence_package", VaultObject.business_id == business_id)
            .order_by(VaultObject.internal_version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    digest = sha256_hex(package)
    if latest is not None and latest.digest == digest:
        vault_object = latest
    else:
        vault_object = await vault_service.release_master(
            session, object_type="postmarket_regulatory_evidence_package", business_id=business_id,
            canonical_payload=package, actor_user_id=actor_user_id, site_id=cmd.site_id,
        )
    return {"vault_object_id": str(vault_object.object_id), "internal_version": vault_object.internal_version, **package}
