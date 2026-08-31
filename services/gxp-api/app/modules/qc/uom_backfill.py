"""SG-146 (remainder) — the MIG-FR-004 *migrate/backfill* step for `ebmr.qc_sample.sample_uom_id`
(the expand step, migration `b2e7f4a9c3d6`, added the column nullable).

Only `qc_sample` gets a backfill: `qc_test_definition` and `qc_result` have no UPDATE grant
(append-only once written, AG-08 — migration `4b6e8f0a1c2d` 0021), so a pre-existing row on either of
those two tables can never be backfilled and none is attempted; `uom_id` on those tables is set only at
INSERT time (`app/modules/qc/commands.py::_resolve_uom_id`).

Same chunked/resumable/idempotent shape as `app.modules.yield_reconciliation.uom_backfill` (MIG-FR-012):
each call processes at most `batch_size` rows with `sample_uom_id IS NULL AND sample_uom IS NOT NULL`,
ordered by primary key, and returns a cursor to resume from. Additive linkage only — never rewrites
`sample_uom`, `state` or any other regulated field (AG-08); no signature/audit-event ceremony applies
(MIG-FR-013's migration-provenance carve-out).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.qc.models import QcSample
from app.modules.rules import service as rules_service
from app.mutation.errors import UomUnknownError


@dataclass(frozen=True)
class BackfillResult:
    processed: int
    matched: int
    unmatched: int
    last_id: uuid.UUID | None


async def backfill_qc_samples(
    session: AsyncSession, *, batch_size: int = 500, after_id: uuid.UUID | None = None
) -> BackfillResult:
    query = (
        select(QcSample)
        .where(QcSample.sample_uom_id.is_(None), QcSample.sample_uom.is_not(None))
        .order_by(QcSample.id)
        .limit(batch_size)
    )
    if after_id is not None:
        query = query.where(QcSample.id > after_id)
    rows = (await session.execute(query)).scalars().all()

    matched = unmatched = 0
    last_id: uuid.UUID | None = None
    for row in rows:
        try:
            resolved = await rules_service.resolve_uom(session, row.sample_uom)
        except UomUnknownError:
            unmatched += 1
            last_id = row.id
            continue
        row.sample_uom_id = resolved.uom_id
        matched += 1
        last_id = row.id
    await session.flush()
    return BackfillResult(processed=len(rows), matched=matched, unmatched=unmatched, last_id=last_id)
