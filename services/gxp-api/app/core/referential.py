"""Referential-integrity guard for delete commands on master/reference data. Master data (Organization,
Site, User, Role, Product, Material, Recipe) is never hard-deleted while something else still points at
it — this checks that up front and returns a clear, human-readable reason instead of letting a raw FK
violation reach the client as an unhandled 500.
"""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def find_blocking_reference(
    session: AsyncSession, checks: list[tuple[Any, Any, uuid.UUID, str]]
) -> str | None:
    """`checks` is a list of (model, column, value, noun) tuples, e.g.
    `(Batch, Batch.recipe_id, recipe.id, "batch")`. Returns a human-readable label for the first
    referencing table with a non-zero count (e.g. "3 batch(es)"), or None if nothing references it.
    """
    for model, column, value, noun in checks:
        count = (
            await session.execute(select(func.count()).select_from(model).where(column == value))
        ).scalar_one()
        if count > 0:
            return f"{count} {noun}(s)"
    return None
