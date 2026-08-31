"""Document 26 — read helpers shared by commands.py and the router."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.qms.models import DeviationImpactLink, DeviationRecord
from app.mutation.errors import NotFoundError


async def get_deviation(session: AsyncSession, deviation_id: uuid.UUID) -> DeviationRecord:
    deviation = await session.get(DeviationRecord, deviation_id)
    if deviation is None:
        raise NotFoundError("Deviation record not found")
    return deviation


async def get_impact_links(session: AsyncSession, deviation_id: uuid.UUID) -> list[DeviationImpactLink]:
    return (
        (
            await session.execute(
                select(DeviationImpactLink)
                .where(DeviationImpactLink.deviation_id == deviation_id)
                .order_by(DeviationImpactLink.created_at)
            )
        )
        .scalars()
        .all()
    )
