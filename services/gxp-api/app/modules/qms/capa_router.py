import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qms.capa_commands import (
    AddCapaActionCommand,
    CloseCapaCommand,
    CompleteCapaActionCommand,
    CreateCapaCommand,
    EffectivenessCommand,
    ExtendCapaCommand,
    PlanCapaCommand,
    ReopenCapaCommand,
    add_capa_action,
    close_capa,
    complete_capa_action,
    create_capa,
    extend_capa,
    plan_capa,
    record_effectiveness,
    reopen_capa,
)
from app.modules.qms.capa_models import CapaAction, CapaEffectivenessCheck, CapaRecord
from app.modules.qms.read_support import filtered, iso, sid
from app.modules.qms.signature_support import SignatureChallengeRequest, create_qms_signature_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

capa_router = APIRouter(prefix="/qms/v1/capas", tags=["qms-capa"])
capa_action_router = APIRouter(prefix="/qms/v1/actions", tags=["qms-capa"])

CAPA_SIGNATURE_ACTIONS = ("close", "effectiveness")


@capa_router.post("", response_model=MutationReceipt)
async def post_create_capa(
    cmd: CreateCapaCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="capa.create", site_id=cmd.site_id)
        return await create_capa(session, cmd, actor.user_id)


@capa_router.post("/{capa_id}/plan", response_model=MutationReceipt)
async def post_plan_capa(
    capa_id: uuid.UUID, cmd: PlanCapaCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.capa_id != capa_id:
        raise ValidationFailedError("capa_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="capa.plan", site_id=None)
        return await plan_capa(session, cmd, actor.user_id)


@capa_router.post("/{capa_id}/actions", response_model=MutationReceipt)
async def post_add_action(
    capa_id: uuid.UUID, cmd: AddCapaActionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.capa_id != capa_id:
        raise ValidationFailedError("capa_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="capa.action.add", site_id=None)
        return await add_capa_action(session, cmd, actor.user_id)


@capa_action_router.post("/{action_id}/complete", response_model=MutationReceipt)
async def post_complete_action(
    action_id: uuid.UUID, cmd: CompleteCapaActionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.action_id != action_id:
        raise ValidationFailedError("action_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="capa.action.complete", site_id=None)
        return await complete_capa_action(session, cmd, actor.user_id)


@capa_router.post("/{capa_id}/effectiveness", response_model=MutationReceipt)
async def post_effectiveness(
    capa_id: uuid.UUID, cmd: EffectivenessCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.capa_id != capa_id:
        raise ValidationFailedError("capa_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="capa.effectiveness", site_id=None)
        return await record_effectiveness(session, cmd, actor.user_id)


@capa_router.post("/{capa_id}/extend", response_model=MutationReceipt)
async def post_extend_capa(
    capa_id: uuid.UUID, cmd: ExtendCapaCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.capa_id != capa_id:
        raise ValidationFailedError("capa_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="capa.extend", site_id=None)
        return await extend_capa(session, cmd, actor.user_id)


@capa_router.post("/{capa_id}/signature-challenges")
async def post_signature_challenge(
    capa_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        capa = await session.get(CapaRecord, capa_id)
        if capa is None:
            raise NotFoundError("CAPA not found")
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="capa_record", record=capa,
            action=body.action, allowed_actions=CAPA_SIGNATURE_ACTIONS,
        )


@capa_router.post("/{capa_id}/close", response_model=MutationReceipt)
async def post_close_capa(
    capa_id: uuid.UUID, cmd: CloseCapaCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.capa_id != capa_id:
        raise ValidationFailedError("capa_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="capa.close", site_id=None)
        return await close_capa(session, cmd, actor.user_id)


@capa_router.post("/{capa_id}/reopen", response_model=MutationReceipt)
async def post_reopen_capa(
    capa_id: uuid.UUID, cmd: ReopenCapaCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.capa_id != capa_id:
        raise ValidationFailedError("capa_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="capa.reopen", site_id=None)
        return await reopen_capa(session, cmd, actor.user_id)


# --- Read side ---------------------------------------------------------------------------------

CAPA_SORTABLE = {
    "capa_number": CapaRecord.capa_number,
    "state": CapaRecord.state,
    "risk_class": CapaRecord.risk_class,
    "target_date": CapaRecord.target_date,
    "created_at": CapaRecord.created_at,
}


def _capa_dict(record: CapaRecord) -> dict:
    return {
        "id": str(record.id),
        "site_id": str(record.site_id),
        "quality_event_id": str(record.quality_event_id),
        "capa_number": record.capa_number,
        "source_type": record.source_type,
        "source_id": str(record.source_id),
        "source_version": record.source_version,
        "problem_statement": record.problem_statement,
        "scope_type": record.scope_type,
        "risk_class": record.risk_class,
        "state": record.state,
        "owner_subject_id": str(record.owner_subject_id),
        "target_date": iso(record.target_date),
        "version": record.version,
        "created_at": iso(record.created_at),
        "closed_at": iso(record.closed_at),
    }


def _action_dict(action: CapaAction) -> dict:
    return {
        "id": str(action.id),
        "capa_id": str(action.capa_id),
        "action_type": action.action_type,
        "description": action.description,
        "owner_subject_id": str(action.owner_subject_id),
        "due_date": iso(action.due_date),
        "dependency_links": action.dependency_links,
        "implementation_evidence": action.implementation_evidence,
        "state": action.state,
        "verification_status": action.verification_status,
        "verified_by": sid(action.verified_by),
        "verified_at": iso(action.verified_at),
        "version": action.version,
        "created_at": iso(action.created_at),
    }


@capa_router.get("")
async def list_capas(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    state: str | None = None,
) -> dict:
    await evaluate_policy(session, actor.user_id, action="capa.view", site_id=site_id)
    stmt = filtered(CapaRecord, params, search_column=CapaRecord.capa_number, site_id=site_id, state=state)
    rows, envelope = await paginate(
        session, stmt, params, sortable=CAPA_SORTABLE, default_sort=CapaRecord.created_at
    )
    return {**envelope, "items": [_capa_dict(r) for (r,) in rows]}


@capa_router.get("/{capa_id}")
async def get_capa(
    capa_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    record = await session.get(CapaRecord, capa_id)
    if record is None:
        raise NotFoundError("CAPA not found")
    await evaluate_policy(session, actor.user_id, action="capa.view", site_id=record.site_id)
    actions = (
        await session.execute(select(CapaAction).where(CapaAction.capa_id == capa_id))
    ).scalars().all()
    checks = (
        await session.execute(
            select(CapaEffectivenessCheck).where(CapaEffectivenessCheck.capa_id == capa_id)
        )
    ).scalars().all()
    return {
        **_capa_dict(record),
        "scope_refs": record.scope_refs,
        "root_cause_ref": record.root_cause_ref,
        "effectiveness_plan": record.effectiveness_plan,
        "corrective_action": record.corrective_action,
        "preventive_action": record.preventive_action,
        "recurrence_links": record.recurrence_links,
        "cancel_reason": record.cancel_reason,
        "extension_history": record.extension_history,
        "closure_history": record.closure_history,
        "reopen_history": record.reopen_history,
        "actions": [_action_dict(a) for a in actions],
        "effectiveness_checks": [
            {
                "id": str(c.id),
                "criterion": c.criterion,
                "data_source": c.data_source,
                "observation_start": iso(c.observation_start),
                "observation_end": iso(c.observation_end),
                "due_date": iso(c.due_date),
                "result": c.result,
                "evidence": c.evidence,
                "reviewer_subject_id": sid(c.reviewer_subject_id),
                "evaluated_at": iso(c.evaluated_at),
            }
            for c in checks
        ],
    }


@capa_action_router.get("")
async def list_capa_actions(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    capa_id: uuid.UUID | None = None,
    state: str | None = None,
) -> dict:
    """Cross-CAPA action worklist (CAPA-FR-019 "my open actions"), or one CAPA's actions via capa_id."""
    await evaluate_policy(session, actor.user_id, action="capa.view", site_id=None)
    stmt = select(CapaAction)
    if capa_id is not None:
        stmt = stmt.where(CapaAction.capa_id == capa_id)
    if state:
        stmt = stmt.where(CapaAction.state == state)
    if params.q:
        stmt = stmt.where(CapaAction.description.ilike(f"%{params.q}%"))
    rows, envelope = await paginate(
        session,
        stmt,
        params,
        sortable={"due_date": CapaAction.due_date, "state": CapaAction.state, "created_at": CapaAction.created_at},
        default_sort=CapaAction.due_date,
    )
    return {**envelope, "items": [_action_dict(a) for (a,) in rows]}
