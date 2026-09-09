"""Referential-integrity guard for delete commands on master/reference data. Master data (Organization,
Site, User, Role, Product, Material, Recipe) is never hard-deleted while something else still points at
it — this checks that up front and returns a clear, human-readable reason instead of letting a raw FK
violation reach the client as an unhandled 500.
"""

import uuid
from typing import Any

from sqlalchemy import func, select, text
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


async def find_all_blocking_references(
    session: AsyncSession, schema: str, table: str, value: uuid.UUID
) -> list[str]:
    """Schema-driven counterpart to `find_blocking_reference()`, for entities too widely referenced to
    hand-maintain a model list against safely (`iam.sites` alone has 112 FK columns across every module
    in the platform as of 2026-09-08 — a hand-maintained check list drifts out of sync the moment a new
    module adds its own `site_id` column, and the gap is invisible until someone hits a raw, unhandled
    FK-violation 500 instead of the clean `ValidationFailedError` this module exists to produce).

    Walks `pg_constraint` for every FK column that actually references `schema.table` in the live
    database (not a hand-maintained model list, so it can never miss a table added after this was last
    reviewed), counts matching rows for `value` in each, and returns a human-readable label
    ("N row(s) in schema.table") for every one that isn't empty -- ordered, so a delete blocked by
    several tables reports all of them at once instead of one at a time across repeated retries.

    Table/column identifiers here come only from `pg_constraint` (the database's own catalog), never
    from caller input, so building the per-table COUNT query by string interpolation is safe -- there is
    no injection surface.
    """
    fk_columns = (
        await session.execute(
            text(
                """
                SELECT n.nspname, cl.relname, a.attname
                FROM pg_constraint c
                JOIN pg_class cl ON cl.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = cl.relnamespace
                JOIN unnest(c.conkey) WITH ORDINALITY AS ck(attnum, ord) ON true
                JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ck.attnum
                WHERE c.contype = 'f' AND c.confrelid = (:schema || '.' || :table)::regclass
                ORDER BY 1, 2, 3
                """
            ),
            {"schema": schema, "table": table},
        )
    ).all()

    blockers: list[str] = []
    for ref_schema, ref_table, ref_column in fk_columns:
        count = (
            await session.execute(
                text(f'SELECT count(*) FROM "{ref_schema}"."{ref_table}" WHERE "{ref_column}" = :value'),
                {"value": value},
            )
        ).scalar_one()
        if count > 0:
            blockers.append(f"{count} row(s) in {ref_schema}.{ref_table}")
    return blockers
