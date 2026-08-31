"""SG-146 (remainder, module 4 of 8) — the MIG-FR-004 *migrate/backfill* step for
`ebmr.gxp_recipe_version.batch_size_uom_id` and `ebmr.gxp_recipe_parameter.uom_id` (the expand step,
migration `0051`, added both columns nullable). Both tables are mutable (UPDATE/DELETE granted,
migration `d0a1a1bdfaef` 0011), so both get a backfill.

Same chunked/resumable/idempotent shape as every prior module's backfill (MIG-FR-012).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.recipe_master.models import RecipeParameter, RecipeVersion
from app.modules.rules import service as rules_service
from app.mutation.errors import UomUnknownError


@dataclass(frozen=True)
class BackfillResult:
    processed: int
    matched: int
    unmatched: int
    last_id: uuid.UUID | None


async def backfill_recipe_versions(
    session: AsyncSession, *, batch_size: int = 500, after_id: uuid.UUID | None = None
) -> BackfillResult:
    query = (
        select(RecipeVersion)
        .where(RecipeVersion.batch_size_uom_id.is_(None), RecipeVersion.batch_size_uom.is_not(None))
        .order_by(RecipeVersion.id)
        .limit(batch_size)
    )
    if after_id is not None:
        query = query.where(RecipeVersion.id > after_id)
    rows = (await session.execute(query)).scalars().all()

    matched = unmatched = 0
    last_id: uuid.UUID | None = None
    for row in rows:
        try:
            resolved = await rules_service.resolve_uom(session, row.batch_size_uom)
        except UomUnknownError:
            unmatched += 1
            last_id = row.id
            continue
        row.batch_size_uom_id = resolved.uom_id
        matched += 1
        last_id = row.id
    await session.flush()
    return BackfillResult(processed=len(rows), matched=matched, unmatched=unmatched, last_id=last_id)


async def backfill_recipe_parameters(
    session: AsyncSession, *, batch_size: int = 500, after_id: uuid.UUID | None = None
) -> BackfillResult:
    query = (
        select(RecipeParameter)
        .where(RecipeParameter.uom_id.is_(None), RecipeParameter.uom.is_not(None))
        .order_by(RecipeParameter.id)
        .limit(batch_size)
    )
    if after_id is not None:
        query = query.where(RecipeParameter.id > after_id)
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
