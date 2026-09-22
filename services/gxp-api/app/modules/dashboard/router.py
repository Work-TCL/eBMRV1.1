from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.dashboard import service as dashboard_service

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
