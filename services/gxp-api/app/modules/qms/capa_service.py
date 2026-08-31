"""Document 27 — read helpers shared by capa_commands.py and the router."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.qms.capa_models import CapaAction, CapaEffectivenessCheck, CapaRecord
from app.mutation.errors import NotFoundError


async def get_capa(session: AsyncSession, capa_id: uuid.UUID) -> CapaRecord:
    capa = await session.get(CapaRecord, capa_id)
    if capa is None:
        raise NotFoundError("CAPA record not found")
    return capa


async def get_action(session: AsyncSession, action_id: uuid.UUID) -> CapaAction:
    action = await session.get(CapaAction, action_id)
    if action is None:
        raise NotFoundError("CAPA action not found")
    return action


async def get_actions(session: AsyncSession, capa_id: uuid.UUID) -> list[CapaAction]:
    return (
        (await session.execute(select(CapaAction).where(CapaAction.capa_id == capa_id).order_by(CapaAction.created_at)))
        .scalars()
        .all()
    )


async def get_effectiveness_checks(session: AsyncSession, capa_id: uuid.UUID) -> list[CapaEffectivenessCheck]:
    return (
        (
            await session.execute(
                select(CapaEffectivenessCheck).where(CapaEffectivenessCheck.capa_id == capa_id).order_by(CapaEffectivenessCheck.created_at)
            )
        )
        .scalars()
        .all()
    )
