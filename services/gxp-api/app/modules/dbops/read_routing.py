"""Document 70 (SPEC-DATA-002) primary/replica read routing -- PG-FR-031.

The rule: a regulated command / signature-target / release-decision read MUST come from the
authoritative primary (`get_primary_consistency_read()`); reporting / dashboards MAY use a replica
only when the caller states an acceptable `max_staleness` and the replica's lag is within it
(`run_read_replica_query()`), otherwise `REPLICA_TOO_STALE`.

Phase 1 note: this deployment runs a single primary and no read replica. `run_read_replica_query()`
therefore reports `served_by = "primary"` and `replica_configured = False` -- it degrades to the
primary rather than inventing a replica, and still enforces the `max_staleness` contract shape so
callers are written correctly for a future replica. `get_primary_consistency_read()` raises
`PRIMARY_UNAVAILABLE` (fail closed) if the primary connection is down -- never a silent fallback.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.mutation.errors import PrimaryUnavailableError, ReplicaTooStaleError


async def get_primary_consistency_read(
    session: AsyncSession,
    *,
    fetch,
):
    """PG-FR-031. Run `fetch(session)` against the authoritative primary. Any connection-level
    failure becomes `PRIMARY_UNAVAILABLE` (503, fail closed) -- a regulated read never silently
    downgrades to a replica."""
    try:
        # Cheap liveness probe on the same connection the read will use.
        await session.execute(text("SELECT 1"))
        return await fetch(session)
    except OperationalError as exc:
        raise PrimaryUnavailableError(
            "Authoritative primary is unavailable; regulated read fails closed"
        ) from exc


async def replica_lag_seconds(session: AsyncSession) -> float | None:
    """Best-effort replica lag. On a primary this returns None (`pg_last_wal_receive_lsn()` is NULL);
    on a standby it returns `now() - pg_last_xact_replay_timestamp()` in seconds."""
    row = await session.execute(
        text(
            "SELECT CASE WHEN pg_is_in_recovery() "
            "THEN EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) "
            "ELSE NULL END AS lag"
        )
    )
    return row.scalar_one_or_none()


async def run_read_replica_query(
    session: AsyncSession,
    *,
    fetch,
    max_staleness_seconds: float,
):
    """PG-FR-031/026. Reporting read. If a replica is configured and its lag exceeds
    `max_staleness_seconds`, raise `REPLICA_TOO_STALE`. With no replica configured (Phase 1) the query
    runs on the primary and the report notes `replica_configured = False`."""
    if max_staleness_seconds < 0:
        raise ValueError("max_staleness_seconds must be >= 0")
    lag = await replica_lag_seconds(session)
    replica_configured = lag is not None
    if replica_configured and lag > max_staleness_seconds:
        raise ReplicaTooStaleError(
            "Replica lag exceeds the caller's max_staleness",
            lag_seconds=lag,
            max_staleness_seconds=max_staleness_seconds,
        )
    data = await fetch(session)
    return {
        "served_by": "replica" if replica_configured else "primary",
        "replica_configured": replica_configured,
        "lag_seconds": lag,
        "max_staleness_seconds": max_staleness_seconds,
        "data": data,
    }
