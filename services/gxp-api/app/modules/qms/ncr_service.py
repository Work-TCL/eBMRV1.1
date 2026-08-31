"""Document 28 — read helpers shared by ncr_commands.py and the router."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.qms.ncr_models import NcrDisposition, NonconformanceRecord
from app.mutation.errors import NotFoundError


async def get_ncr(session: AsyncSession, ncr_id: uuid.UUID) -> NonconformanceRecord:
    ncr = await session.get(NonconformanceRecord, ncr_id)
    if ncr is None:
        raise NotFoundError("Nonconformance record not found")
    return ncr


async def get_dispositions(session: AsyncSession, ncr_id: uuid.UUID) -> list[NcrDisposition]:
    return (
        (await session.execute(select(NcrDisposition).where(NcrDisposition.ncr_id == ncr_id).order_by(NcrDisposition.created_at)))
        .scalars()
        .all()
    )
