"""Document 59 (SPEC-PM-002) REST surface, prefix `/regulatory/v1`.

`evaluateSameEventReportDeduplication()` and `freezeReportabilityAuditPackage()` are named functions in
Document 59's own contract catalogue; the latter has no operation in the terse 10-op `# APIs` list at
all -- exposed here as an extra endpoint (same precedent used for Document 58's equivalents).
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.postmarket import reportability_commands as commands
from app.modules.postmarket.models import SafetyCase
from app.modules.postmarket.reportability_commands import _track_hash
from app.modules.postmarket.reportability_models import (
    RegulatoryReport,
    RegulatorySubmissionAck,
    RegulatorySubmissionAttempt,
    ReportabilityTrack,
)
from app.modules.signature.service import create_challenge, resolve_signature_requirement
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/regulatory/v1", tags=["postmarket-regulatory"])


def _track_dict(t: ReportabilityTrack) -> dict:
    return {
        "id": str(t.id), "site_id": str(t.site_id), "safety_case_id": str(t.safety_case_id),
        "report_type_code": t.report_type_code, "report_type_version": t.report_type_version,
        "application_context": t.application_context,
        "clock_start_basis": t.clock_start_basis,
        "clock_start_at": t.clock_start_at.isoformat() if t.clock_start_at else None,
        "clock_start_rationale": t.clock_start_rationale,
        "calendar_type": t.calendar_type, "calendar_version": t.calendar_version,
        "due_at": t.due_at.isoformat() if t.due_at else None,
        "original_due_at": t.original_due_at.isoformat() if t.original_due_at else None,
        "decision": t.decision, "decision_by": str(t.decision_by) if t.decision_by else None,
        "decision_signature_id": str(t.decision_signature_id) if t.decision_signature_id else None,
        "decision_rationale": t.decision_rationale, "decision_evidence_refs": t.decision_evidence_refs,
        "rule_version": t.rule_version,
        "parent_track_id": str(t.parent_track_id) if t.parent_track_id else None,
        "state": t.state, "version": t.version, "created_at": t.created_at.isoformat(),
    }


def _report_dict(r: RegulatoryReport) -> dict:
    return {
        "id": str(r.id), "site_id": str(r.site_id), "reportability_track_id": str(r.reportability_track_id),
        "report_version": r.report_version, "schema_code": r.schema_code, "schema_version": r.schema_version,
        "content": r.content, "field_provenance": r.field_provenance, "missing_information": r.missing_information,
        "narrative_version": r.narrative_version,
        "approved_by": str(r.approved_by) if r.approved_by else None,
        "approval_signature_id": str(r.approval_signature_id) if r.approval_signature_id else None,
        "payload_digest": r.payload_digest, "state": r.state, "created_at": r.created_at.isoformat(),
    }


def _ack_dict(a: RegulatorySubmissionAck) -> dict:
    return {
        "id": str(a.id), "submission_attempt_id": str(a.submission_attempt_id), "ack_level": a.ack_level,
        "ack_state": a.ack_state, "ack_reference": a.ack_reference, "ack_payload": a.ack_payload,
        "ack_received_at": a.ack_received_at.isoformat(), "rejection_reason": a.rejection_reason,
    }


def _attempt_dict(a: RegulatorySubmissionAttempt) -> dict:
    return {
        "id": str(a.id), "site_id": str(a.site_id), "regulatory_report_id": str(a.regulatory_report_id),
        "attempt_no": a.attempt_no, "channel": a.channel, "endpoint_profile": a.endpoint_profile,
        "payload_version": a.payload_version, "payload_digest": a.payload_digest,
        "sender_identity": a.sender_identity, "authorized_by": str(a.authorized_by),
        "authorization_signature_id": str(a.authorization_signature_id) if a.authorization_signature_id else None,
        "attempted_at": a.attempted_at.isoformat(), "transport_result": a.transport_result,
        "failure_detail": a.failure_detail,
        "manual_evidence_id": str(a.manual_evidence_id) if a.manual_evidence_id else None,
    }


@router.get("/tracks/{track_id}")
async def get_track(
    track_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    track = await session.get(ReportabilityTrack, track_id)
    if track is None:
        raise NotFoundError("Reportability track not found")
    await evaluate_policy(session, actor.user_id, action="reportability_track.view", site_id=track.site_id)
    reports = (
        (await session.execute(select(RegulatoryReport).where(RegulatoryReport.reportability_track_id == track_id).order_by(RegulatoryReport.report_version)))
        .scalars()
        .all()
    )
    body = _track_dict(track)
    body["reports"] = [_report_dict(r) for r in reports]
    return body


@router.get("/reports/{report_id}")
async def get_report(
    report_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    report = await session.get(RegulatoryReport, report_id)
    if report is None:
        raise NotFoundError("Regulatory report not found")
    await evaluate_policy(session, actor.user_id, action="reportability_track.view", site_id=report.site_id)
    attempts = (
        (await session.execute(select(RegulatorySubmissionAttempt).where(RegulatorySubmissionAttempt.regulatory_report_id == report_id).order_by(RegulatorySubmissionAttempt.attempt_no)))
        .scalars()
        .all()
    )
    attempt_dicts = []
    for a in attempts:
        acks = (
            (await session.execute(select(RegulatorySubmissionAck).where(RegulatorySubmissionAck.submission_attempt_id == a.id)))
            .scalars()
            .all()
        )
        d = _attempt_dict(a)
        d["acks"] = [_ack_dict(k) for k in acks]
        attempt_dicts.append(d)
    body = _report_dict(report)
    body["submission_attempts"] = attempt_dicts
    return body


@router.get("/submissions/{attempt_id}")
async def get_submission_attempt(
    attempt_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    attempt = await session.get(RegulatorySubmissionAttempt, attempt_id)
    if attempt is None:
        raise NotFoundError("Submission attempt not found")
    await evaluate_policy(session, actor.user_id, action="reportability_track.view", site_id=attempt.site_id)
    acks = (
        (await session.execute(select(RegulatorySubmissionAck).where(RegulatorySubmissionAck.submission_attempt_id == attempt_id)))
        .scalars()
        .all()
    )
    body = _attempt_dict(attempt)
    body["acks"] = [_ack_dict(k) for k in acks]
    return body


async def _create_signature_challenge(
    session: AsyncSession, *, actor: AuthenticatedActor, record_type: str, record_id: uuid.UUID,
    record_version: int, record_hash: str, action: str,
) -> dict:
    """Same shape as `app.modules.postmarket.router._create_signature_challenge` -- resolves `meaning`
    from the Document 106 policy row rather than hardcoding it."""
    policy = await resolve_signature_requirement(session, record_type=record_type, action=action)
    challenge = await create_challenge(
        session, user_id=actor.user_id, record_type=record_type, record_id=record_id,
        record_version=record_version, record_hash=record_hash, meaning=policy.meaning,
    )
    return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/cases/{case_id}/reportability-tracks", response_model=MutationReceipt)
async def post_create_reportability_tracks(
    case_id: uuid.UUID, cmd: commands.CreateReportabilityTracksCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.safety_case_id != case_id:
        raise ValidationFailedError("case_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="reportability_track.create", site_id=cmd.site_id)
        return await commands.create_reportability_tracks(session, cmd, actor.user_id)


@router.post("/tracks/{track_id}/deadline:calculate", response_model=MutationReceipt)
async def post_calculate_deadline(
    track_id: uuid.UUID, cmd: commands.CalculateRegulatoryDeadlineCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.track_id != track_id:
        raise ValidationFailedError("track_id in path and body must match")
    async with session.begin():
        track = await session.get(ReportabilityTrack, track_id)
        if track is None:
            raise NotFoundError("Reportability track not found")
        await evaluate_policy(session, actor.user_id, action="reportability_track.calculate_deadline", site_id=track.site_id)
        return await commands.calculate_regulatory_deadline(session, cmd, actor.user_id)


@router.post("/tracks/{track_id}/decision-signature-challenges")
async def post_decide_reportability_signature_challenge(
    track_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        track = await session.get(ReportabilityTrack, track_id)
        if track is None:
            raise NotFoundError("Reportability track not found")
        return await _create_signature_challenge(
            session, actor=actor, record_type="reportability_track", record_id=track.id,
            record_version=track.version, record_hash=_track_hash(track), action="decide",
        )


@router.post("/tracks/{track_id}/decisions", response_model=MutationReceipt)
async def post_decide_reportability(
    track_id: uuid.UUID, cmd: commands.DecideReportabilityCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.track_id != track_id:
        raise ValidationFailedError("track_id in path and body must match")
    async with session.begin():
        track = await session.get(ReportabilityTrack, track_id)
        if track is None:
            raise NotFoundError("Reportability track not found")
        await evaluate_policy(session, actor.user_id, action="reportability_track.decide", site_id=track.site_id)
        return await commands.decide_reportability(session, cmd, actor.user_id)


@router.post("/tracks/{track_id}/reports", response_model=MutationReceipt)
async def post_build_report(
    track_id: uuid.UUID, cmd: commands.BuildRegulatoryReportCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.track_id != track_id:
        raise ValidationFailedError("track_id in path and body must match")
    async with session.begin():
        track = await session.get(ReportabilityTrack, track_id)
        if track is None:
            raise NotFoundError("Reportability track not found")
        await evaluate_policy(session, actor.user_id, action="regulatory_report.create", site_id=track.site_id)
        return await commands.build_regulatory_report(session, cmd, actor.user_id)


@router.post("/reports/{report_id}/approval-signature-challenges")
async def post_approve_report_signature_challenge(
    report_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        report = await session.get(RegulatoryReport, report_id)
        if report is None:
            raise NotFoundError("Regulatory report not found")
        return await _create_signature_challenge(
            session, actor=actor, record_type="regulatory_report", record_id=report.id,
            record_version=report.report_version, record_hash=sha256_hex(report.content), action="approve",
        )


@router.post("/reports/{report_id}/approve", response_model=MutationReceipt)
async def post_approve_report(
    report_id: uuid.UUID, cmd: commands.ApproveRegulatoryReportCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.report_id != report_id:
        raise ValidationFailedError("report_id in path and body must match")
    async with session.begin():
        report = await session.get(RegulatoryReport, report_id)
        if report is None:
            raise NotFoundError("Regulatory report not found")
        await evaluate_policy(session, actor.user_id, action="regulatory_report.approve", site_id=report.site_id)
        return await commands.approve_regulatory_report(session, cmd, actor.user_id)


@router.post("/reports/{report_id}/payloads:generate")
async def post_generate_payload(
    report_id: uuid.UUID, cmd: commands.GenerateRegulatoryPayloadCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    if cmd.report_id != report_id:
        raise ValidationFailedError("report_id in path and body must match")
    async with session.begin():
        report = await session.get(RegulatoryReport, report_id)
        if report is None:
            raise NotFoundError("Regulatory report not found")
        await evaluate_policy(session, actor.user_id, action="regulatory_report.generate_payload", site_id=report.site_id)
        return await commands.generate_regulatory_payload(session, cmd, actor.user_id)


@router.post("/reports/{report_id}/submissions", response_model=MutationReceipt)
async def post_submit_report(
    report_id: uuid.UUID, cmd: commands.SubmitRegulatoryReportCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.report_id != report_id:
        raise ValidationFailedError("report_id in path and body must match")
    async with session.begin():
        report = await session.get(RegulatoryReport, report_id)
        if report is None:
            raise NotFoundError("Regulatory report not found")
        await evaluate_policy(session, actor.user_id, action="regulatory_report.submit", site_id=report.site_id)
        return await commands.submit_regulatory_report(session, cmd, actor.user_id)


@router.post("/submissions/{attempt_id}/acknowledgements", response_model=MutationReceipt)
async def post_ingest_acknowledgement(
    attempt_id: uuid.UUID, cmd: commands.IngestSubmissionAcknowledgementCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.submission_attempt_id != attempt_id:
        raise ValidationFailedError("attempt_id in path and body must match")
    async with session.begin():
        attempt = await session.get(RegulatorySubmissionAttempt, attempt_id)
        if attempt is None:
            raise NotFoundError("Submission attempt not found")
        await evaluate_policy(session, actor.user_id, action="regulatory_submission.acknowledge", site_id=attempt.site_id)
        return await commands.ingest_submission_acknowledgement(session, cmd, actor.user_id)


@router.post("/reports/{report_id}/followups", response_model=MutationReceipt)
async def post_create_followup(
    report_id: uuid.UUID, cmd: commands.CreateFollowupReportTaskCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.original_report_id != report_id:
        raise ValidationFailedError("report_id in path and body must match")
    async with session.begin():
        report = await session.get(RegulatoryReport, report_id)
        if report is None:
            raise NotFoundError("Regulatory report not found")
        await evaluate_policy(session, actor.user_id, action="regulatory_report.followup", site_id=report.site_id)
        return await commands.create_followup_report_task(session, cmd, actor.user_id)


@router.post("/cases/{case_id}/part4-deduplication:evaluate")
async def post_evaluate_dedup(
    case_id: uuid.UUID, cmd: commands.EvaluateSameEventDeduplicationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        case = await session.get(SafetyCase, case_id)
        if case is None:
            raise NotFoundError("Safety case not found")
        await evaluate_policy(session, actor.user_id, action="reportability_track.view", site_id=case.site_id)
        return await commands.evaluate_same_event_report_deduplication(session, cmd)


@router.post("/audit-packages:freeze")
async def post_freeze_audit_package(
    cmd: commands.FreezeReportabilityAuditPackageCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="reportability_track.view", site_id=cmd.site_id)
        return await commands.freeze_reportability_audit_package(session, cmd, actor.user_id)
