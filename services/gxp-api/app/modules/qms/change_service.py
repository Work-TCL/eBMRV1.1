"""Document 29 — read helpers shared by change_commands.py and the router."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.qms.change_models import ChangeAffectedObject, ChangeControl, ChangeTask
from app.mutation.errors import NotFoundError


async def get_change(session: AsyncSession, change_id: uuid.UUID) -> ChangeControl:
    change = await session.get(ChangeControl, change_id)
    if change is None:
        raise NotFoundError("Change control record not found")
    return change


async def get_affected_objects(session: AsyncSession, change_id: uuid.UUID) -> list[ChangeAffectedObject]:
    return (
        (await session.execute(select(ChangeAffectedObject).where(ChangeAffectedObject.change_id == change_id).order_by(ChangeAffectedObject.created_at)))
        .scalars()
        .all()
    )


async def get_tasks(session: AsyncSession, change_id: uuid.UUID) -> list[ChangeTask]:
    return (
        (await session.execute(select(ChangeTask).where(ChangeTask.change_id == change_id).order_by(ChangeTask.created_at)))
        .scalars()
        .all()
    )
