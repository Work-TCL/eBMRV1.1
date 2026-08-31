"""Document 70 (SPEC-DATA-002) database integrity verification -- PG-FR-023/032.

`run_database_integrity_check()` collects the integrity signals PostgreSQL exposes without a
maintenance outage:
  * `pg_stat_database.checksum_failures` / `checksum_last_failure` (PG-FR-023 -- data checksums);
  * per-index structural check via the `amcheck` extension's `bt_index_check()` when the extension is
    installed and the scope names btree indexes;
  * `pg_stat_database` deadlock / conflict counters as a corruption-adjacent health signal.

It never mutates anything. A non-zero checksum failure count, or an `amcheck` error, is
`DB_INTEGRITY_FAILURE` when `raise_on_failure=True`; otherwise the report carries `healthy=False`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mutation.errors import DatabaseIntegrityFailureError


async def _amcheck_available(session: AsyncSession) -> bool:
    row = await session.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'amcheck'"))
    return row.scalar_one_or_none() is not None


async def run_database_integrity_check(
    session: AsyncSession,
    *,
    index_scope: list[str] | None = None,
    raise_on_failure: bool = False,
) -> dict:
    """PG-FR-032. `index_scope` is an optional list of `schema.index` btree names to structurally
    verify with `amcheck`. Returns an IntegrityCheckReport."""
    checked_at = datetime.now(timezone.utc)

    db_row = (
        await session.execute(
            text(
                """
                SELECT datname,
                       checksum_failures,
                       checksum_last_failure,
                       deadlocks,
                       conflicts
                FROM pg_stat_database
                WHERE datname = current_database()
                """
            )
        )
    ).one()
    checksum_failures = db_row.checksum_failures or 0

    index_results: list[dict] = []
    amcheck = await _amcheck_available(session)
    if index_scope and amcheck:
        for qualified in index_scope:
            if qualified.count(".") != 1 or not all(p.replace("_", "").isalnum() for p in qualified.split(".")):
                index_results.append({"index": qualified, "ok": False, "error": "not a plain schema.index identifier"})
                continue
            try:
                await session.execute(text("SELECT bt_index_check(:idx::regclass)"), {"idx": qualified})
                index_results.append({"index": qualified, "ok": True})
            except Exception as exc:  # noqa: BLE001
                index_results.append({"index": qualified, "ok": False, "error": str(exc)})

    index_failures = [r for r in index_results if not r["ok"]]
    healthy = checksum_failures == 0 and not index_failures

    report = {
        "checked_at": checked_at.isoformat(),
        "database": db_row.datname,
        "checksum_failures": checksum_failures,
        "checksum_last_failure": db_row.checksum_last_failure.isoformat() if db_row.checksum_last_failure else None,
        "deadlocks": db_row.deadlocks,
        "conflicts": db_row.conflicts,
        "amcheck_available": amcheck,
        "index_results": index_results,
        "healthy": healthy,
    }
    if not healthy and raise_on_failure:
        raise DatabaseIntegrityFailureError(
            "Database integrity check reported a failure",
            checksum_failures=checksum_failures,
            index_failures=[r["index"] for r in index_failures],
        )
    return report
