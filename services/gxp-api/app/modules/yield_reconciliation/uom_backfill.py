"""SG-146 (remainder) — the MIG-FR-004 *migrate/backfill* step for `ebmr.manufacturing_calculations.
uom_id`/`ebmr.reconciliation_records.uom_id` (the expand step, migration `a4d9e6c2f8b1`, added both
columns nullable).

Chunked, resumable, idempotent (MIG-FR-012): each call processes at most `batch_size` rows with
`uom_id IS NULL AND uom IS NOT NULL`, ordered by primary key, and returns a cursor (`last_id`) to resume
from. A second run over already-backfilled rows is a no-op regardless of the cursor, because the
`uom_id IS NULL` filter alone already guarantees idempotency — `after_id` only bounds each batch so a
long-running backfill does not repeatedly rescan rows it already handled in the same session.

This only ADDS a reference into a previously-NULL column; it never rewrites `uom`, `result`, `state`,
`variance` or any other regulated field, so it is additive linkage, not a correction of a regulated
decision (AG-08) — no signature/audit-event ceremony applies (MIG-FR-013's "migration-generated change
is marked as migration provenance, not a user action"). Requires no UOM master row to pre-exist: an
unresolved `uom` string is left NULL and counted as unmatched, never guessed (AG-15) — a value like
`"each"` (label reconciliation's hardcoded UOM) legitimately stays unmatched until/unless a deployment
releases a UOM row at that code.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rules import service as rules_service
from app.modules.yield_reconciliation.models import ManufacturingCalculation, ReconciliationRecord
from app.mutation.errors import UomUnknownError


@dataclass(frozen=True)
class BackfillResult:
    processed: int
    matched: int
    unmatched: int
    last_id: uuid.UUID | None  # None when this batch found nothing left to process


async def _backfill_batch(
    session: AsyncSession, model, *, batch_size: int, after_id: uuid.UUID | None
) -> BackfillResult:
    query = select(model).where(model.uom_id.is_(None), model.uom.is_not(None)).order_by(model.id).limit(batch_size)
    if after_id is not None:
        query = query.where(model.id > after_id)
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


async def backfill_manufacturing_calculations(
    session: AsyncSession, *, batch_size: int = 500, after_id: uuid.UUID | None = None
) -> BackfillResult:
    return await _backfill_batch(session, ManufacturingCalculation, batch_size=batch_size, after_id=after_id)


async def backfill_reconciliation_records(
    session: AsyncSession, *, batch_size: int = 500, after_id: uuid.UUID | None = None
) -> BackfillResult:
    return await _backfill_batch(session, ReconciliationRecord, batch_size=batch_size, after_id=after_id)
