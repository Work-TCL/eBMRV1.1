import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qms.complaint_commands import (
    CloseComplaintCommand,
    CreateComplaintCommand,
    InvestigateComplaintCommand,
    InvestigationDecisionCommand,
    RecordCommunicationCommand,
    ReportabilityAssessmentCommand,
    TriageComplaintCommand,
    assess_reportability,
    close_complaint,
    create_complaint,
    investigate_complaint,
    investigation_decision,
    record_communication,
    triage_complaint,
)
from app.modules.qms.complaint_models import ComplaintCommunication, ComplaintRecord, ComplaintReportabilityAssessment
from app.modules.qms.read_support import filtered, iso, sid
from app.modules.qms.signature_support import SignatureChallengeRequest, create_qms_signature_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

complaint_router = APIRouter(prefix="/qms/v1/complaints", tags=["qms-complaint"])

COMPLAINT_SIGNATURE_ACTIONS = ("reportability", "close")


@complaint_router.post("", response_model=MutationReceipt)
async def post_create_complaint(
    cmd: CreateComplaintCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="complaint.create", site_id=cmd.site_id)
        return await create_complaint(session, cmd, actor.user_id)


@complaint_router.post("/{complaint_id}/triage", response_model=MutationReceipt)
async def post_triage_complaint(
    complaint_id: uuid.UUID, cmd: TriageComplaintCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.complaint_id != complaint_id:
        raise ValidationFailedError("complaint_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="complaint.triage", site_id=None)
        return await triage_complaint(session, cmd, actor.user_id)


@complaint_router.post("/{complaint_id}/investigation-decision", response_model=MutationReceipt)
async def post_investigation_decision(
    complaint_id: uuid.UUID, cmd: InvestigationDecisionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.complaint_id != complaint_id:
        raise ValidationFailedError("complaint_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="complaint.investigation_decision", site_id=None)
        return await investigation_decision(session, cmd, actor.user_id)


@complaint_router.post("/{complaint_id}/investigation", response_model=MutationReceipt)
async def post_investigate_complaint(
    complaint_id: uuid.UUID, cmd: InvestigateComplaintCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.complaint_id != complaint_id:
        raise ValidationFailedError("complaint_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="complaint.investigate", site_id=None)
        return await investigate_complaint(session, cmd, actor.user_id)


@complaint_router.post("/{complaint_id}/reportability", response_model=MutationReceipt)
async def post_assess_reportability(
    complaint_id: uuid.UUID, cmd: ReportabilityAssessmentCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.complaint_id != complaint_id:
        raise ValidationFailedError("complaint_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="complaint.reportability", site_id=None)
        return await assess_reportability(session, cmd, actor.user_id)


@complaint_router.post("/{complaint_id}/response", response_model=MutationReceipt)
async def post_record_communication(
    complaint_id: uuid.UUID, cmd: RecordCommunicationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.complaint_id != complaint_id:
        raise ValidationFailedError("complaint_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="complaint.response", site_id=None)
        return await record_communication(session, cmd, actor.user_id)


@complaint_router.post("/{complaint_id}/signature-challenges")
async def post_signature_challenge(
    complaint_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        complaint = await session.get(ComplaintRecord, complaint_id)
        if complaint is None:
            raise NotFoundError("Complaint not found")
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="complaint_record", record=complaint,
            action=body.action, allowed_actions=COMPLAINT_SIGNATURE_ACTIONS,
        )


@complaint_router.post("/{complaint_id}/close", response_model=MutationReceipt)
async def post_close_complaint(
    complaint_id: uuid.UUID, cmd: CloseComplaintCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.complaint_id != complaint_id:
        raise ValidationFailedError("complaint_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="complaint.close", site_id=None)
        return await close_complaint(session, cmd, actor.user_id)


# --- Read side ---------------------------------------------------------------------------------

COMPLAINT_SORTABLE = {
    "complaint_number": ComplaintRecord.complaint_number,
    "state": ComplaintRecord.state,
    "received_at": ComplaintRecord.received_at,
    "created_at": ComplaintRecord.created_at,
}


def _complaint_dict(record: ComplaintRecord) -> dict:
    return {
        "id": str(record.id),
        "site_id": str(record.site_id),
        "quality_event_id": str(record.quality_event_id),
        "complaint_number": record.complaint_number,
        "received_at": iso(record.received_at),
        "source_channel": record.source_channel,
        "product_ref": sid(record.product_ref),
        "nature_code": record.nature_code,
        "description": record.description,
        "constituent_classification": record.constituent_classification,
        "investigation_required": record.investigation_required,
        "investigation_conclusion": record.investigation_conclusion,
        "is_potential_duplicate": record.is_potential_duplicate,
        "state": record.state,
        "version": record.version,
        "created_at": iso(record.created_at),
        "closed_at": iso(record.closed_at),
    }


@complaint_router.get("")
async def list_complaints(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    state: str | None = None,
) -> dict:
    await evaluate_policy(session, actor.user_id, action="complaint.view", site_id=site_id)
    stmt = filtered(
        ComplaintRecord, params, search_column=ComplaintRecord.complaint_number, site_id=site_id, state=state
    )
    rows, envelope = await paginate(
        session, stmt, params, sortable=COMPLAINT_SORTABLE, default_sort=ComplaintRecord.received_at
    )
    return {**envelope, "items": [_complaint_dict(r) for (r,) in rows]}


@complaint_router.get("/{complaint_id}")
async def get_complaint(
    complaint_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    record = await session.get(ComplaintRecord, complaint_id)
    if record is None:
        raise NotFoundError("Complaint not found")
    await evaluate_policy(session, actor.user_id, action="complaint.view", site_id=record.site_id)
    assessments = (
        await session.execute(
            select(ComplaintReportabilityAssessment).where(
                ComplaintReportabilityAssessment.complaint_id == complaint_id
            )
        )
    ).scalars().all()
    communications = (
        await session.execute(
            select(ComplaintCommunication).where(ComplaintCommunication.complaint_id == complaint_id)
        )
    ).scalars().all()
    return {
        **_complaint_dict(record),
        "lot_batch_serial_refs": record.lot_batch_serial_refs,
        "complainant_info": record.complainant_info,
        "triage": record.triage,
        "no_investigation_reason": record.no_investigation_reason,
        "investigation_findings": record.investigation_findings,
        "related_complaint_ids": record.related_complaint_ids,
        "reportability_assessments": [
            {
                "id": str(a.id),
                "applicable_regimes": a.applicable_regimes,
                "assessment_inputs": a.assessment_inputs,
                "rationale": a.rationale,
                "trigger_date": iso(a.trigger_date),
                "due_date": iso(a.due_date),
                "reviewer_subject_id": str(a.reviewer_subject_id),
                "submission_reference": a.submission_reference,
                "submission_status": a.submission_status,
                "capa_required": a.capa_required,
                "field_action_required": a.field_action_required,
                "created_at": iso(a.created_at),
            }
            for a in assessments
        ],
        "communications": [
            {
                "id": str(c.id),
                "direction": c.direction,
                "communication_type": c.communication_type,
                "recipient": c.recipient,
                "channel": c.channel,
                "occurred_at": iso(c.occurred_at),
                "message": c.message,
                "reference": c.reference,
            }
            for c in communications
        ],
    }
