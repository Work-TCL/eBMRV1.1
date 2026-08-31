"""SG-146 (remainder, module 4 of 8) — the MIG-FR-004 *migrate/backfill* step for
`ebmr.genealogy_edge.uom_id` (the expand step, migration `0051`, added the column nullable).
`ebmr.genealogy_edge` is mutable (UPDATE granted, migration `5e23e1067790` 0014), so a backfill is
possible (`genealogy_node` has no UOM column and is append-only, irrelevant here).

Same chunked/resumable/idempotent shape as every prior module's backfill (MIG-FR-012).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.genealogy.models import GenealogyEdge
from app.modules.rules import service as rules_service
from app.mutation.errors import UomUnknownError


@dataclass(frozen=True)
class BackfillResult:
    processed: int
    matched: int
    unmatched: int
    last_id: uuid.UUID | None


async def backfill_genealogy_edges(
    session: AsyncSession, *, batch_size: int = 500, after_id: uuid.UUID | None = None
) -> BackfillResult:
    query = (
        select(GenealogyEdge)
        .where(GenealogyEdge.uom_id.is_(None), GenealogyEdge.uom.is_not(None))
        .order_by(GenealogyEdge.id)
        .limit(batch_size)
    )
    if after_id is not None:
        query = query.where(GenealogyEdge.id > after_id)
    rows = (await session.execute(query)).scalars().all()

    matched = unmatched = 0
    last_id: uuid.UUID | None = None
    for row in rows:
        try:
            resolved = await rules_service.resolve_uom(session, row.uom)
        except UomUnknownError:
            unmatched += 1
            last_id = row.id
            continue
        row.uom_id = resolved.uom_id
        matched += 1
        last_id = row.id
    await session.flush()
    return BackfillResult(processed=len(rows), matched=matched, unmatched=unmatched, last_id=last_id)
