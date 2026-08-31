"""Document 70 (SPEC-DATA-002) concurrency helpers -- PG-FR-008/012.

`apply_optimistic_update()` is the one canonical way to mutate an aggregate row: a conditional
`UPDATE ... WHERE id = :id AND version = :expected` that bumps `version`, asserting exactly one row
changed (else `STALE_VERSION`). `with_deadlock_retry()` wraps a transaction callable so a PostgreSQL
deadlock (SQLSTATE 40P01) or serialization failure (40001) retries the whole unit of work a bounded
number of times with backoff, rather than surfacing as a raw 500.

These are library functions used *inside* an already-open authoritative transaction (the Mutation
Gateway's `db.transaction(...)`); they never open or commit a transaction themselves and never do
external I/O (PG-FR-013).
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, TypeVar

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.mutation.errors import DeadlockDetectedError, StaleVersionError

T = TypeVar("T")

# PostgreSQL SQLSTATEs that mean "you lost a concurrency race; retrying the whole tx is correct".
_RETRYABLE_SQLSTATES = {"40P01", "40001"}  # deadlock_detected, serialization_failure


async def apply_optimistic_update(
    session: AsyncSession,
    *,
    schema: str,
    table: str,
    row_id,
    expected_version: int,
    set_columns: dict[str, object],
) -> int:
    """PG-FR-008: `UPDATE {schema}.{table} SET ..., version = version + 1 WHERE id = :id AND
    version = :expected`. Returns the new version. Raises `StaleVersionError` (`STALE_VERSION`) if the
    row count is not exactly 1 (concurrent writer already advanced it, or the row is gone).

    `schema`/`table` are validated against an identifier allowlist pattern -- they are never
    caller-supplied free text in practice, but the guard keeps this from becoming an injection sink.
    """
    if not (schema.replace("_", "").isalnum() and table.replace("_", "").isalnum()):
        raise ValueError("schema/table must be plain identifiers")
    assignments = ", ".join(f"{col} = :set_{col}" for col in set_columns)
    params = {f"set_{col}": val for col, val in set_columns.items()}
    params.update({"id": row_id, "expected": expected_version})
    stmt = text(
        f"UPDATE {schema}.{table} SET {assignments}{', ' if assignments else ''}"
        f"version = version + 1 WHERE id = :id AND version = :expected RETURNING version"
    )
    result = await session.execute(stmt, params)
    new_version = result.scalar_one_or_none()
    if new_version is None:
        raise StaleVersionError(
            "Row changed since this request was prepared (optimistic-version mismatch)",
            table=f"{schema}.{table}",
            expected_version=expected_version,
        )
    return new_version


def _sqlstate(exc: BaseException) -> str | None:
    orig = getattr(exc, "orig", None)
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


async def with_deadlock_retry(
    unit_of_work: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay_seconds: float = 0.05,
) -> T:
    """PG-FR-012: run `unit_of_work` (which must itself open+commit a fresh transaction each call) and
    retry on deadlock / serialization failure up to `attempts` times with exponential backoff. After
    the last attempt the failure is re-raised as `DeadlockDetectedError` (`DEADLOCK_DETECTED`)."""
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await unit_of_work()
        except (OperationalError, DBAPIError) as exc:  # noqa: PERF203
            if _sqlstate(exc) not in _RETRYABLE_SQLSTATES:
                raise
            last_exc = exc
            if attempt < attempts:
                await asyncio.sleep(base_delay_seconds * (2 ** (attempt - 1)))
    raise DeadlockDetectedError(
        "Transaction repeatedly lost a concurrency race and was not retried further",
        attempts=attempts,
    ) from last_exc
