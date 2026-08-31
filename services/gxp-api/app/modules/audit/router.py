import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.audit.commands import CreateAuditExportCommand, create_audit_export
from app.modules.audit.models import AuditEvent
from app.modules.audit.service import (
    actor_accessible_sites,
    actor_usernames_for,
    apply_site_scope,
    assert_site_visible,
    event_to_dict,
    verify_chain,
)
from app.modules.policy.service import evaluate_policy
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/audit/v1", tags=["audit"])

SORTABLE = {
    "occurred_at": AuditEvent.occurred_at,
    "aggregate_type": AuditEvent.aggregate_type,
    "action": AuditEvent.action,
    "aggregate_version": AuditEvent.aggregate_version,
}


async def _list_and_respond(
    session: AsyncSession,
    stmt,
    params: PageParams,
    verify: bool,
    verify_key: tuple[str, uuid.UUID] | None,
) -> dict:
    rows, envelope = await paginate(session, stmt, params, sortable=SORTABLE, default_sort=AuditEvent.occurred_at)
    events = [e for (e,) in rows]
    usernames = await actor_usernames_for(session, events)
    items = [await event_to_dict(session, e, usernames) for e in events]

    if verify and verify_key is not None:
        chain = await verify_chain(session, verify_key[0], verify_key[1])
        for item in items:
            status = chain.get(uuid.UUID(item["id"]))
            item["chain_valid"] = bool(status and status["hash_valid"] and status["link_valid"]) if status else None

    return {**envelope, "items": items}


@router.get("/records/{aggregate_type}/{aggregate_id}")
async def get_records(
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    verify_chain: bool = False,
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="audit.review", site_id=None)
    accessible = await actor_accessible_sites(session, actor.user_id)
    stmt = apply_site_scope(
        select(AuditEvent).where(
            AuditEvent.aggregate_type == aggregate_type, AuditEvent.aggregate_id == aggregate_id
        ),
        accessible,
    )
    return await _list_and_respond(
        session, stmt, params, verify_chain, (aggregate_type, aggregate_id)
    )


@router.get("/batches/{batch_id}")
async def get_batch_records(
    batch_id: uuid.UUID,
    verify_chain: bool = False,
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    return await get_records(
        "batch", batch_id, verify_chain=verify_chain, session=session, params=params, actor=actor
    )


@router.get("/users/{subject_id}")
async def get_user_records(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="audit.review", site_id=None)
    accessible = await actor_accessible_sites(session, actor.user_id)
    stmt = apply_site_scope(select(AuditEvent).where(AuditEvent.actor_id == subject_id), accessible)
    return await _list_and_respond(session, stmt, params, False, None)


@router.get("/search")
async def search_records(
    aggregate_type: str | None = None,
    aggregate_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    has_signature: bool | None = None,
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="audit.review", site_id=None)
    if site_id is not None:
        await assert_site_visible(session, actor.user_id, site_id)

    stmt = select(AuditEvent)
    if aggregate_type:
        stmt = stmt.where(AuditEvent.aggregate_type == aggregate_type)
    if aggregate_id:
        stmt = stmt.where(AuditEvent.aggregate_id == aggregate_id)
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if site_id:
        stmt = stmt.where(AuditEvent.site_id == site_id)
    if occurred_from:
        stmt = stmt.where(AuditEvent.occurred_at >= occurred_from)
    if occurred_to:
        stmt = stmt.where(AuditEvent.occurred_at <= occurred_to)
    if has_signature is not None:
        stmt = stmt.where(AuditEvent.signature_id.is_not(None) if has_signature else AuditEvent.signature_id.is_(None))
    if params.q:
        needle = f"%{params.q}%"
        stmt = stmt.where(or_(AuditEvent.action.ilike(needle), AuditEvent.reason.ilike(needle)))

    accessible = await actor_accessible_sites(session, actor.user_id)
    stmt = apply_site_scope(stmt, accessible)
    return await _list_and_respond(session, stmt, params, False, None)


@router.post("/exports", response_model=MutationReceipt)
async def post_create_export(
    cmd: CreateAuditExportCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="audit.export", site_id=None)
        return await create_audit_export(session, cmd, actor.user_id)
