"""SG-146 (remainder, module 4 of 8) — the MIG-FR-004 *migrate/backfill* step for
`ebmr.batches.uom_id` (the expand step, migration `0051`, added the column nullable). `ebmr.batches` is
mutable (UPDATE granted, migration `329495c9e651` 0002's blanket grant), so a backfill is possible and
this module has one.

Same chunked/resumable/idempotent shape as every prior module's backfill (MIG-FR-012): `uom_id IS NULL`
alone guarantees idempotency; `after_id` only bounds each batch. Additive linkage only (AG-08); no
signature/audit-event ceremony applies (MIG-FR-013's migration-provenance carve-out).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch.models import Batch
from app.modules.rules import service as rules_service
from app.mutation.errors import UomUnknownError


@dataclass(frozen=True)
class BackfillResult:
    processed: int
    matched: int
    unmatched: int
    last_id: uuid.UUID | None


async def backfill_batches(
    session: AsyncSession, *, batch_size: int = 500, after_id: uuid.UUID | None = None
) -> BackfillResult:
    query = select(Batch).where(Batch.uom_id.is_(None), Batch.uom.is_not(None)).order_by(Batch.id).limit(batch_size)
    if after_id is not None:
        query = query.where(Batch.id > after_id)
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
