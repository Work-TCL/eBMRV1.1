import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qms.commands import (
    CloseCommand,
    ContainDeviationCommand,
    CreateDeviationCommand,
    DispositionCommand,
    ExtendCommand,
    ImpactCommand,
    InvestigationCommand,
    ReopenCommand,
    TriageDeviationCommand,
    assess_impact,
    close_deviation,
    contain_deviation,
    create_deviation,
    disposition_deviation,
    extend_deviation,
    record_investigation,
    reopen_deviation,
    triage_deviation,
)
from app.modules.qms.models import DeviationImpactLink, DeviationRecord
from app.modules.qms.read_support import filtered, iso, sid
from app.modules.qms.signature_support import SignatureChallengeRequest, create_qms_signature_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/qms/v1/deviations", tags=["qms-deviations"])

DEVIATION_SIGNATURE_ACTIONS = ("disposition", "close")


@router.post("", response_model=MutationReceipt)
async def post_create(
    cmd: CreateDeviationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qms_deviation.create", site_id=cmd.site_id)
        return await create_deviation(session, cmd, actor.user_id)


@router.post("/{deviation_id}/triage", response_model=MutationReceipt)
async def post_triage(
    deviation_id: uuid.UUID,
    cmd: TriageDeviationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.deviation_id != deviation_id:
        raise ValidationFailedError("deviation_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qms_deviation.triage", site_id=None)
        return await triage_deviation(session, cmd, actor.user_id)


@router.post("/{deviation_id}/contain", response_model=MutationReceipt)
async def post_contain(
    deviation_id: uuid.UUID,
    cmd: ContainDeviationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.deviation_id != deviation_id:
        raise ValidationFailedError("deviation_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qms_deviation.contain", site_id=None)
        return await contain_deviation(session, cmd, actor.user_id)


@router.post("/{deviation_id}/investigation", response_model=MutationReceipt)
async def post_investigation(
    deviation_id: uuid.UUID,
    cmd: InvestigationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.deviation_id != deviation_id:
        raise ValidationFailedError("deviation_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qms_deviation.investigate", site_id=None)
        return await record_investigation(session, cmd, actor.user_id)


@router.post("/{deviation_id}/impact", response_model=MutationReceipt)
async def post_impact(
    deviation_id: uuid.UUID,
    cmd: ImpactCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.deviation_id != deviation_id:
        raise ValidationFailedError("deviation_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qms_deviation.impact", site_id=None)
        return await assess_impact(session, cmd, actor.user_id)


@router.post("/{deviation_id}/disposition", response_model=MutationReceipt)
async def post_disposition(
    deviation_id: uuid.UUID,
    cmd: DispositionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.deviation_id != deviation_id:
        raise ValidationFailedError("deviation_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qms_deviation.disposition", site_id=None)
        return await disposition_deviation(session, cmd, actor.user_id)


@router.post("/{deviation_id}/extend", response_model=MutationReceipt)
async def post_extend(
    deviation_id: uuid.UUID,
    cmd: ExtendCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.deviation_id != deviation_id:
        raise ValidationFailedError("deviation_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qms_deviation.extend", site_id=None)
        return await extend_deviation(session, cmd, actor.user_id)


@router.post("/{deviation_id}/close", response_model=MutationReceipt)
async def post_close(
    deviation_id: uuid.UUID,
    cmd: CloseCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.deviation_id != deviation_id:
        raise ValidationFailedError("deviation_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qms_deviation.close", site_id=None)
        return await close_deviation(session, cmd, actor.user_id)


@router.post("/{deviation_id}/signature-challenges")
async def post_signature_challenge(
    deviation_id: uuid.UUID,
    body: SignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        deviation = await session.get(DeviationRecord, deviation_id)
        if deviation is None:
            raise NotFoundError("Deviation record not found")
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="deviation_record", record=deviation,
            action=body.action, allowed_actions=DEVIATION_SIGNATURE_ACTIONS,
        )


@router.post("/{deviation_id}/reopen", response_model=MutationReceipt)
async def post_reopen(
    deviation_id: uuid.UUID,
    cmd: ReopenCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.deviation_id != deviation_id:
        raise ValidationFailedError("deviation_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qms_deviation.reopen", site_id=None)
        return await reopen_deviation(session, cmd, actor.user_id)


# --- Read side (DEV-FR-024 record retrieval) ---------------------------------------------------
#
# Non-authoritative reads (AG-11): they let a reviewer find and open a deviation. Every regulated
# transition above still goes through its own command with expected_version.

DEVIATION_SORTABLE = {
    "deviation_number": DeviationRecord.deviation_number,
    "severity": DeviationRecord.severity,
    "state": DeviationRecord.state,
    "due_date": DeviationRecord.due_date,
    "created_at": DeviationRecord.created_at,
}


def _deviation_dict(record: DeviationRecord) -> dict:
    return {
        "id": str(record.id),
        "site_id": str(record.site_id),
        "quality_event_id": str(record.quality_event_id),
        "deviation_number": record.deviation_number,
        "deviation_type": record.deviation_type,
        "source_type": record.source_type,
        "source_id": str(record.source_id),
        "source_version": record.source_version,
        "severity": record.severity,
        "state": record.state,
        "owner_subject_id": str(record.owner_subject_id),
        "investigator_subject_id": sid(record.investigator_subject_id),
        "planned": record.planned,
        "disposition_code": record.disposition_code,
        "capa_required": record.capa_required,
        "change_control_required": record.change_control_required,
        "training_required": record.training_required,
        "due_date": iso(record.due_date),
        "version": record.version,
        "created_at": iso(record.created_at),
        "closed_at": iso(record.closed_at),
    }


@router.get("")
async def list_deviations(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    state: str | None = None,
    severity: str | None = None,
) -> dict:
    await evaluate_policy(session, actor.user_id, action="qms_deviation.view", site_id=site_id)
    stmt = filtered(
        DeviationRecord, params, search_column=DeviationRecord.deviation_number, site_id=site_id, state=state
    )
    if severity:
        stmt = stmt.where(DeviationRecord.severity == severity)
    rows, envelope = await paginate(
        session, stmt, params, sortable=DEVIATION_SORTABLE, default_sort=DeviationRecord.created_at
    )
    return {**envelope, "items": [_deviation_dict(r) for (r,) in rows]}


@router.get("/{deviation_id}")
async def get_deviation(
    deviation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    record = await session.get(DeviationRecord, deviation_id)
    if record is None:
        raise NotFoundError("Deviation not found")
    await evaluate_policy(session, actor.user_id, action="qms_deviation.view", site_id=record.site_id)
    links = (
        await session.execute(
            select(DeviationImpactLink).where(DeviationImpactLink.deviation_id == deviation_id)
        )
    ).scalars().all()
    return {
        **_deviation_dict(record),
        "planned_scope": record.planned_scope,
        "immediate_correction": record.immediate_correction,
        "containment": record.containment,
        "investigation_plan": record.investigation_plan,
        "cross_batch_ids": record.cross_batch_ids,
        "root_cause": record.root_cause,
        "impact_assessment": record.impact_assessment,
        "disposition_rationale": record.disposition_rationale,
        "capa_rationale": record.capa_rationale,
        "change_control_rationale": record.change_control_rationale,
        "training_rationale": record.training_rationale,
        "extension_history": record.extension_history,
        "closure_history": record.closure_history,
        "reopen_history": record.reopen_history,
        "impact_links": [
            {
                "id": str(link.id),
                "impacted_record_type": link.impacted_record_type,
                "impacted_record_id": str(link.impacted_record_id),
                "impacted_record_version": link.impacted_record_version,
                "impact_category": link.impact_category,
                "hold_disposition_reference": link.hold_disposition_reference,
                "created_at": iso(link.created_at),
            }
            for link in links
        ],
    }
