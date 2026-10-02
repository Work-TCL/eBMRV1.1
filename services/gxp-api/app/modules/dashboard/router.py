import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.dashboard import service as dashboard_service
from app.modules.policy.service import evaluate_policy

router = APIRouter(prefix="/dashboard/v1", tags=["dashboard"])


@router.get("/reminders")
async def get_reminders(
    within_days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    """Client requirement #4 (Expiry / Retest / Important Date Reminders). Deliberately no
    evaluate_policy() beyond authentication itself -- same precedent as `GET /sites`
    (app/modules/iam/router.py): a cross-cutting "what's coming due" summary any signed-in user should
    see app-wide, not a module-specific regulated read."""
    return await dashboard_service.list_upcoming_reminders(session, within_days=within_days)


@router.get("/workflow-actions")
async def get_workflow_actions(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Workflow Handoff Notifications. No `evaluate_policy()` beyond authentication either, but for a
    different reason than /reminders: this list is *already* filtered to exactly the notifications whose
    required RBAC permission the caller currently holds at the relevant site
    (app/modules/notifications/service.py::list_visible_notifications) -- that filter IS the access
    control here, an actor with no matching permission simply gets an empty/partial list back, not a
    403. The lazy self-heal inside list_visible_notifications() can write (resolve a stale notification
    it discovers here), so this runs inside a transaction like any other write path, even though it's a
    GET."""
    async with session.begin():
        return await dashboard_service.list_workflow_actions(session, actor.user_id)


@router.post("/workflow-actions/{notification_id}/read")
async def post_workflow_action_read(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Per-viewer 'seen' state only -- never touches the regulated entity the notification points at, and
    never touches the notification row's own open/resolved state (that only ever changes via
    app/modules/notifications/service.py::sync_notification / the lazy self-heal in
    list_visible_notifications)."""
    async with session.begin():
        await dashboard_service.mark_workflow_action_read(session, notification_id=notification_id, actor_user_id=actor.user_id)
    return {"status": "ok"}


@router.post("/workflow-actions:rebuild")
async def post_workflow_actions_rebuild(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """AG-11 recovery path -- rescans every registered aggregate type's own authoritative table and
    re-syncs the notification projection from it, same operational role as
    `POST /search/v1/indexes/{index_type}:rebuild`. Gated the same way that endpoint is: a dedicated
    permission code, not open to every authenticated user, since a full rescan is an operational action,
    not a read."""
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="notifications.rebuild", site_id=None)
        return await dashboard_service.rebuild_workflow_actions(session)
