"""SG-146 (remainder, module 4 of 8) — the MIG-FR-004 *migrate/backfill* step for
`ebmr.gxp_product_version.strength_uom_id` (the expand step, migration `0051`, added the column
nullable). `ebmr.gxp_product_version` is mutable (UPDATE granted, migration `d5d48a66187f` 0010), so a
backfill is possible.

Same chunked/resumable/idempotent shape as every prior module's backfill (MIG-FR-012).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.product_master.models import ProductVersion
from app.modules.rules import service as rules_service
from app.mutation.errors import UomUnknownError


@dataclass(frozen=True)
class BackfillResult:
    processed: int
    matched: int
    unmatched: int
    last_id: uuid.UUID | None


async def backfill_product_versions(
    session: AsyncSession, *, batch_size: int = 500, after_id: uuid.UUID | None = None
) -> BackfillResult:
    query = (
        select(ProductVersion)
        .where(ProductVersion.strength_uom_id.is_(None), ProductVersion.strength_uom.is_not(None))
        .order_by(ProductVersion.id)
        .limit(batch_size)
    )
    if after_id is not None:
        query = query.where(ProductVersion.id > after_id)
    rows = (await session.execute(query)).scalars().all()

    matched = unmatched = 0
    last_id: uuid.UUID | None = None
    for row in rows:
        try:
            resolved = await rules_service.resolve_uom(session, row.strength_uom)
        except UomUnknownError:
            unmatched += 1
            last_id = row.id
            continue
        row.strength_uom_id = resolved.uom_id
        matched += 1
        last_id = row.id
    await session.flush()
    return BackfillResult(processed=len(rows), matched=matched, unmatched=unmatched, last_id=last_id)
