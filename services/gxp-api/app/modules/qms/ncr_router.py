import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qms.ncr_commands import (
    CloseNcrCommand,
    CreateNcrCommand,
    DispositionNcrCommand,
    EvaluateNcrCommand,
    SegregateNcrCommand,
    VerifyNcrCommand,
    close_ncr,
    create_ncr,
    disposition_ncr,
    evaluate_ncr,
    segregate_ncr,
    verify_ncr,
)
from app.modules.qms.ncr_models import NcrDisposition, NonconformanceRecord
from app.modules.qms.read_support import filtered, iso, sid
from app.modules.qms.signature_support import SignatureChallengeRequest, create_qms_signature_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

ncr_router = APIRouter(prefix="/qms/v1/nonconformances", tags=["qms-ncr"])

NCR_SIGNATURE_ACTIONS = ("disposition", "verify", "close")


@ncr_router.post("", response_model=MutationReceipt)
async def post_create_ncr(
    cmd: CreateNcrCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ncr.create", site_id=cmd.site_id)
        return await create_ncr(session, cmd, actor.user_id)


@ncr_router.post("/{ncr_id}/segregate", response_model=MutationReceipt)
async def post_segregate_ncr(
    ncr_id: uuid.UUID, cmd: SegregateNcrCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.ncr_id != ncr_id:
        raise ValidationFailedError("ncr_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ncr.segregate", site_id=None)
        return await segregate_ncr(session, cmd, actor.user_id)


@ncr_router.post("/{ncr_id}/evaluate", response_model=MutationReceipt)
async def post_evaluate_ncr(
    ncr_id: uuid.UUID, cmd: EvaluateNcrCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.ncr_id != ncr_id:
        raise ValidationFailedError("ncr_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ncr.evaluate", site_id=None)
        return await evaluate_ncr(session, cmd, actor.user_id)


@ncr_router.post("/{ncr_id}/disposition", response_model=MutationReceipt)
async def post_disposition_ncr(
    ncr_id: uuid.UUID, cmd: DispositionNcrCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.ncr_id != ncr_id:
        raise ValidationFailedError("ncr_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ncr.disposition", site_id=None)
        return await disposition_ncr(session, cmd, actor.user_id)


@ncr_router.post("/{ncr_id}/verify", response_model=MutationReceipt)
async def post_verify_ncr(
    ncr_id: uuid.UUID, cmd: VerifyNcrCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.ncr_id != ncr_id:
        raise ValidationFailedError("ncr_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ncr.verify", site_id=None)
        return await verify_ncr(session, cmd, actor.user_id)


@ncr_router.post("/{ncr_id}/signature-challenges")
async def post_signature_challenge(
    ncr_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        ncr = await session.get(NonconformanceRecord, ncr_id)
        if ncr is None:
            raise NotFoundError("Nonconformance not found")
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="nonconformance_record", record=ncr,
            action=body.action, allowed_actions=NCR_SIGNATURE_ACTIONS,
        )


@ncr_router.post("/{ncr_id}/close", response_model=MutationReceipt)
async def post_close_ncr(
    ncr_id: uuid.UUID, cmd: CloseNcrCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.ncr_id != ncr_id:
        raise ValidationFailedError("ncr_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="ncr.close", site_id=None)
        return await close_ncr(session, cmd, actor.user_id)


# --- Read side ---------------------------------------------------------------------------------

NCR_SORTABLE = {
    "ncr_number": NonconformanceRecord.ncr_number,
    "severity": NonconformanceRecord.severity,
    "state": NonconformanceRecord.state,
    "created_at": NonconformanceRecord.created_at,
}


def _ncr_dict(record: NonconformanceRecord) -> dict:
    return {
        "id": str(record.id),
        "site_id": str(record.site_id),
        "quality_event_id": str(record.quality_event_id),
        "ncr_number": record.ncr_number,
        "source_type": record.source_type,
        "source_id": sid(record.source_id),
        "scope_type": record.scope_type,
        "defect_code": record.defect_code,
        "severity": record.severity,
        "state": record.state,
        "owner_subject_id": str(record.owner_subject_id),
        "capa_required": record.capa_required,
        "release_blocker_active": record.release_blocker_active,
        "version": record.version,
        "created_at": iso(record.created_at),
        "closed_at": iso(record.closed_at),
    }


@ncr_router.get("")
async def list_ncrs(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    state: str | None = None,
) -> dict:
    await evaluate_policy(session, actor.user_id, action="ncr.view", site_id=site_id)
    stmt = filtered(
        NonconformanceRecord, params, search_column=NonconformanceRecord.ncr_number, site_id=site_id, state=state
    )
    rows, envelope = await paginate(
        session, stmt, params, sortable=NCR_SORTABLE, default_sort=NonconformanceRecord.created_at
    )
    return {**envelope, "items": [_ncr_dict(r) for (r,) in rows]}


@ncr_router.get("/{ncr_id}")
async def get_ncr(
    ncr_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    record = await session.get(NonconformanceRecord, ncr_id)
    if record is None:
        raise NotFoundError("Nonconformance not found")
    await evaluate_policy(session, actor.user_id, action="ncr.view", site_id=record.site_id)
    dispositions = (
        await session.execute(select(NcrDisposition).where(NcrDisposition.ncr_id == ncr_id))
    ).scalars().all()
    return {
        **_ncr_dict(record),
        "scope_records": record.scope_records,
        "requirement_ref": record.requirement_ref,
        "segregation": record.segregation,
        "evaluation": record.evaluation,
        "supplier_link": record.supplier_link,
        "capa_rationale": record.capa_rationale,
        "verification": record.verification,
        "closure_history": record.closure_history,
        "dispositions": [
            {
                "id": str(d.id),
                "affected_scope": d.affected_scope,
                "quantity": d.quantity,
                "serials": d.serials,
                "disposition_type": d.disposition_type,
                "justification": d.justification,
                "rework_route": d.rework_route,
                "follow_up_test_requirements": d.follow_up_test_requirements,
                "use_as_is_authorized_by": sid(d.use_as_is_authorized_by),
                "signature_id": sid(d.signature_id),
                "created_at": iso(d.created_at),
            }
            for d in dispositions
        ],
    }
