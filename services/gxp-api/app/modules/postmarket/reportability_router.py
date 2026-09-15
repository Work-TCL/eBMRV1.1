"""Document 59 (SPEC-PM-002) REST surface, prefix `/regulatory/v1`.

`evaluateSameEventReportDeduplication()` and `freezeReportabilityAuditPackage()` are named functions in
Document 59's own contract catalogue; the latter has no operation in the terse 10-op `# APIs` list at
all -- exposed here as an extra endpoint (same precedent used for Document 58's equivalents).
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.postmarket import reportability_commands as commands
from app.modules.postmarket.models import SafetyCase
from app.modules.postmarket.reportability_commands import _track_hash
from app.modules.postmarket.reportability_models import (
    RegulatoryReport,
    RegulatorySubmissionAttempt,
    ReportabilityTrack,
)
from app.modules.signature.service import create_challenge, resolve_signature_requirement
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/regulatory/v1", tags=["postmarket-regulatory"])


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
