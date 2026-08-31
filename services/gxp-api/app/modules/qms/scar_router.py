import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qms.scar_commands import (
    CloseScarCommand,
    CreateSupplierCaseCommand,
    IssueScarCommand,
    RecordEffectivenessCommand,
    RecordSupplierResponseCommand,
    ReviewScarCommand,
    close_scar,
    create_supplier_case,
    issue_scar,
    record_effectiveness,
    record_supplier_response,
    review_scar,
)
from app.modules.qms.scar_models import ScarRecord, SupplierQualityCase
from app.modules.qms.read_support import filtered, iso, sid
from app.modules.qms.signature_support import SignatureChallengeRequest, create_qms_signature_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

supplier_case_router = APIRouter(prefix="/qms/v1/supplier-cases", tags=["qms-scar"])
scar_router = APIRouter(prefix="/qms/v1/scars", tags=["qms-scar"])

SCAR_SIGNATURE_ACTIONS = ("review", "close")


@supplier_case_router.post("", response_model=MutationReceipt)
async def post_create_supplier_case(
    cmd: CreateSupplierCaseCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="scar.case.create", site_id=cmd.site_id)
        return await create_supplier_case(session, cmd, actor.user_id)


@supplier_case_router.post("/{case_id}/scar", response_model=MutationReceipt)
async def post_issue_scar(
    case_id: uuid.UUID, cmd: IssueScarCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.case_id != case_id:
        raise ValidationFailedError("case_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="scar.issue", site_id=None)
        return await issue_scar(session, cmd, actor.user_id)


@scar_router.post("/{scar_id}/response", response_model=MutationReceipt)
async def post_record_supplier_response(
    scar_id: uuid.UUID, cmd: RecordSupplierResponseCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.scar_id != scar_id:
        raise ValidationFailedError("scar_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="scar.response", site_id=None)
        return await record_supplier_response(session, cmd, actor.user_id)


@scar_router.post("/{scar_id}/review", response_model=MutationReceipt)
async def post_review_scar(
    scar_id: uuid.UUID, cmd: ReviewScarCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.scar_id != scar_id:
        raise ValidationFailedError("scar_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="scar.review", site_id=None)
        return await review_scar(session, cmd, actor.user_id)


@scar_router.post("/{scar_id}/effectiveness", response_model=MutationReceipt)
async def post_record_effectiveness(
    scar_id: uuid.UUID, cmd: RecordEffectivenessCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.scar_id != scar_id:
        raise ValidationFailedError("scar_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="scar.effectiveness", site_id=None)
        return await record_effectiveness(session, cmd, actor.user_id)


@scar_router.post("/{scar_id}/signature-challenges")
async def post_signature_challenge(
    scar_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        scar = await session.get(ScarRecord, scar_id)
        if scar is None:
            raise NotFoundError("SCAR not found")
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="scar_record", record=scar,
            action=body.action, allowed_actions=SCAR_SIGNATURE_ACTIONS,
        )


@scar_router.post("/{scar_id}/close", response_model=MutationReceipt)
async def post_close_scar(
    scar_id: uuid.UUID, cmd: CloseScarCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.scar_id != scar_id:
        raise ValidationFailedError("scar_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="scar.close", site_id=None)
        return await close_scar(session, cmd, actor.user_id)


# --- Read side ---------------------------------------------------------------------------------

CASE_SORTABLE = {
    "case_number": SupplierQualityCase.case_number,
    "severity": SupplierQualityCase.severity,
    "state": SupplierQualityCase.state,
    "created_at": SupplierQualityCase.created_at,
}
SCAR_SORTABLE = {
    "scar_number": ScarRecord.scar_number,
    "state": ScarRecord.state,
    "due_date": ScarRecord.due_date,
    "issued_at": ScarRecord.issued_at,
}


def _case_dict(record: SupplierQualityCase) -> dict:
    return {
        "id": str(record.id),
        "site_id": str(record.site_id),
        "quality_event_id": str(record.quality_event_id),
        "case_number": record.case_number,
        "source_type": record.source_type,
        "source_id": sid(record.source_id),
        "supplier_id": str(record.supplier_id),
        "supplier_site_id": sid(record.supplier_site_id),
        "material_id": sid(record.material_id),
        "affected_lots": record.affected_lots,
        "defect_code": record.defect_code,
        "severity": record.severity,
        "internal_owner_subject_id": str(record.internal_owner_subject_id),
        "state": record.state,
        "version": record.version,
        "created_at": iso(record.created_at),
        "closed_at": iso(record.closed_at),
    }


def _scar_dict(record: ScarRecord) -> dict:
    return {
        "id": str(record.id),
        "site_id": str(record.site_id),
        "case_id": str(record.case_id),
        "scar_number": record.scar_number,
        "issued_at": iso(record.issued_at),
        "due_date": iso(record.due_date),
        "problem_statement": record.problem_statement,
        "requalification_required": record.requalification_required,
        "source_status_decision": record.source_status_decision,
        "capa_required": record.capa_required,
        "is_repeat_issue": record.is_repeat_issue,
        "state": record.state,
        "version": record.version,
        "created_at": iso(record.created_at),
        "closed_at": iso(record.closed_at),
    }


@supplier_case_router.get("")
async def list_supplier_cases(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    state: str | None = None,
) -> dict:
    await evaluate_policy(session, actor.user_id, action="scar.view", site_id=site_id)
    stmt = filtered(
        SupplierQualityCase, params, search_column=SupplierQualityCase.case_number, site_id=site_id, state=state
    )
    rows, envelope = await paginate(
        session, stmt, params, sortable=CASE_SORTABLE, default_sort=SupplierQualityCase.created_at
    )
    return {**envelope, "items": [_case_dict(r) for (r,) in rows]}


@supplier_case_router.get("/{case_id}")
async def get_supplier_case(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    record = await session.get(SupplierQualityCase, case_id)
    if record is None:
        raise NotFoundError("Supplier quality case not found")
    await evaluate_policy(session, actor.user_id, action="scar.view", site_id=record.site_id)
    scars = (
        await session.execute(select(ScarRecord).where(ScarRecord.case_id == case_id))
    ).scalars().all()
    return {
        **_case_dict(record),
        "material_spec_ref": record.material_spec_ref,
        "containment": record.containment,
        "asl_impact": record.asl_impact,
        "alternate_source_ref": record.alternate_source_ref,
        "scars": [_scar_dict(s) for s in scars],
    }


@scar_router.get("")
async def list_scars(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    state: str | None = None,
) -> dict:
    await evaluate_policy(session, actor.user_id, action="scar.view", site_id=site_id)
    stmt = filtered(ScarRecord, params, search_column=ScarRecord.scar_number, site_id=site_id, state=state)
    rows, envelope = await paginate(
        session, stmt, params, sortable=SCAR_SORTABLE, default_sort=ScarRecord.issued_at
    )
    return {**envelope, "items": [_scar_dict(r) for (r,) in rows]}


@scar_router.get("/{scar_id}")
async def get_scar(
    scar_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    record = await session.get(ScarRecord, scar_id)
    if record is None:
        raise NotFoundError("SCAR not found")
    await evaluate_policy(session, actor.user_id, action="scar.view", site_id=record.site_id)
    return {
        **_scar_dict(record),
        "evidence": record.evidence,
        "acknowledgment": record.acknowledgment,
        "supplier_root_cause": record.supplier_root_cause,
        "supplier_actions": record.supplier_actions,
        "internal_review": record.internal_review,
        "review_history": record.review_history,
        "effectiveness": record.effectiveness,
        "effectiveness_history": record.effectiveness_history,
        "requalification_rationale": record.requalification_rationale,
        "capa_rationale": record.capa_rationale,
        "related_case_ids": record.related_case_ids,
        "closure_history": record.closure_history,
    }
