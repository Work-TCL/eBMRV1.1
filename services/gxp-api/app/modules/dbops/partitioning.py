"""Document 70 (SPEC-DATA-002) declarative-partition maintenance -- PG-FR-016/017/030.

`verify_partition_coverage()` inspects `pg_catalog` for a RANGE-partitioned parent and reports whether
a partition covers now and every month out to a future horizon; a gap is `PARTITION_GAP_DETECTED`
(PG-FR-030: "missing partition fails visibly").

`create_time_partition()` issues `CREATE TABLE ... PARTITION OF ... FOR VALUES FROM (:lo) TO (:hi)`
under the migration/maintenance role. It refuses to run against a non-partitioned parent or with
overlapping bounds (`PARTITION_CREATE_FAILED`).

Phase 1 note: none of the kernel tables are declaratively partitioned yet -- `gxp_audit_event` /
`gxp_outbox` are the approved candidates (spec # 6). These helpers are the mechanism; wiring a parent
table to RANGE partitioning is a separate, measured migration (PG-FR-016: "justified by measured
volume", not applied pre-emptively). Until then `verify_partition_coverage()` returns
`partitioned = False` for those tables rather than raising.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mutation.errors import PartitionCreateFailedError, PartitionGapDetectedError

_IDENT_OK = lambda s: s.replace("_", "").isalnum()  # noqa: E731


async def _is_range_partitioned(session: AsyncSession, schema: str, table: str) -> bool:
    row = await session.execute(
        text(
            """
            SELECT pt.partstrat
            FROM pg_partitioned_table pt
            JOIN pg_class c ON c.oid = pt.partrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = :schema AND c.relname = :table
            """
        ),
        {"schema": schema, "table": table},
    )
    strat = row.scalar_one_or_none()
    return strat == "r"  # RANGE


async def verify_partition_coverage(
    session: AsyncSession,
    *,
    schema: str,
    table: str,
    horizon_months: int = 2,
    raise_on_gap: bool = False,
) -> dict:
    """PG-FR-030. Returns a coverage report: whether the parent is RANGE-partitioned, the child
    partition bounds it has, and whether now .. now+horizon is fully covered."""
    if not (_IDENT_OK(schema) and _IDENT_OK(table)):
        raise ValueError("schema/table must be plain identifiers")

    if not await _is_range_partitioned(session, schema, table):
        return {
            "schema": schema, "table": table, "partitioned": False,
            "covered": None, "gap_from": None, "partitions": [],
            "note": "parent is not declaratively RANGE-partitioned (Phase 1: not yet wired)",
        }

    rows = (
        await session.execute(
            text(
                """
                SELECT c.relname AS child,
                       pg_get_expr(c.relpartbound, c.oid) AS bound
                FROM pg_inherits i
                JOIN pg_class c ON c.oid = i.inhrelid
                JOIN pg_class p ON p.oid = i.inhparent
                JOIN pg_namespace n ON n.oid = p.relnamespace
                WHERE n.nspname = :schema AND p.relname = :table
                ORDER BY c.relname
                """
            ),
            {"schema": schema, "table": table},
        )
    ).all()
    partitions = [{"child": r.child, "bound": r.bound} for r in rows]

    # Coarse month-by-month check against the recorded upper bounds.
    now = datetime.now(timezone.utc)
    gap_from = None
    for m in range(horizon_months + 1):
        probe = (now + timedelta(days=31 * m)).strftime("%Y-%m")
        if not any(probe in p["bound"] or _covers_month(p["bound"], now + timedelta(days=31 * m)) for p in partitions):
            gap_from = probe
            break
    covered = gap_from is None
    if not covered and raise_on_gap:
        raise PartitionGapDetectedError(
            "No partition covers an imminent time window", table=f"{schema}.{table}", gap_from=gap_from
        )
    return {
        "schema": schema, "table": table, "partitioned": True, "covered": covered,
        "gap_from": gap_from, "partitions": partitions,
    }


def _covers_month(bound_expr: str, when: datetime) -> bool:
    """Best-effort parse of `FOR VALUES FROM ('lo') TO ('hi')` timestamp bounds."""
    try:
        import re

        m = re.findall(r"'([^']+)'", bound_expr or "")
        if len(m) != 2:
            return False
        lo = datetime.fromisoformat(m[0].replace(" ", "T").split("+")[0])
        hi = datetime.fromisoformat(m[1].replace(" ", "T").split("+")[0])
        naive = when.replace(tzinfo=None)
        return lo <= naive < hi
    except Exception:  # noqa: BLE001
        return False


async def create_time_partition(
    session: AsyncSession,
    *,
    schema: str,
    table: str,
    lower: datetime,
    upper: datetime,
) -> dict:
    """PG-FR-016/030. Create one RANGE child partition `[lower, upper)`. Runs under the caller's
    session (expected to be the migration/maintenance role). Raises `PARTITION_CREATE_FAILED` on a
    non-partitioned parent, bad bounds, or an overlap the database rejects."""
    if not (_IDENT_OK(schema) and _IDENT_OK(table)):
        raise ValueError("schema/table must be plain identifiers")
    if upper <= lower:
        raise PartitionCreateFailedError("upper bound must be after lower bound")
    if not await _is_range_partitioned(session, schema, table):
        raise PartitionCreateFailedError(
            "parent table is not RANGE-partitioned", table=f"{schema}.{table}"
        )
    child = f"{table}_p{lower.strftime('%Y%m')}"
    if not _IDENT_OK(child):
        raise PartitionCreateFailedError("derived child name is not a plain identifier")
    try:
        await session.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {schema}.{child} PARTITION OF {schema}.{table} "
                f"FOR VALUES FROM (:lo) TO (:hi)"
            ),
            {"lo": lower, "hi": upper},
        )
    except Exception as exc:  # noqa: BLE001
        raise PartitionCreateFailedError(
            "database rejected the partition create", table=f"{schema}.{table}", detail=str(exc)
        ) from exc
    return {"schema": schema, "parent": table, "child": child,
            "range": [lower.isoformat(), upper.isoformat()]}
