"""Document 69 (SPEC-DATA-001) projection-freshness / cross-store-consistency library.

Pure read functions. The authoritative signal is the GxP audit ledger (`audit.audit_events`): every
committed regulated mutation writes one row carrying `aggregate_type` + `aggregate_id` +
`aggregate_version`, so `max(aggregate_version)` is the authoritative current version and there is no
need to reach into every domain repository.

A `projection_checkpoint` row is the cursor for one rebuildable projection: everything in its
`source_stream` up to `last_source_version` has been projected. A projected record is *stale* when the
authoritative aggregate has advanced past that cursor (DATA-FR-008); a regulated action must then
re-read the authoritative record, never trust the projection (DATA-FR-007 / DATA-FR-012 / AG-11).
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent
from app.modules.dataops.models import ProjectionCheckpoint
from app.mutation.errors import CrossStoreMismatchError, NotFoundError, ProjectionStaleError


async def _checkpoint(session: AsyncSession, projection_type: str) -> ProjectionCheckpoint:
    row = (
        await session.execute(
            select(ProjectionCheckpoint).where(ProjectionCheckpoint.projection_type == projection_type)
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("No projection checkpoint for this projection type", projection_type=projection_type)
    return row


async def get_projection_freshness(
    session: AsyncSession,
    *,
    projection_type: str,
    entity_id: uuid.UUID,
    raise_if_stale: bool = False,
) -> dict:
    """`getProjectionFreshness()` -- DATA-FR-008. Compares the projection cursor against the
    authoritative current version of `entity_id`. Returns a `ProjectionFreshness` dict; if
    `raise_if_stale` and the projection lags the authoritative record, raises `ProjectionStaleError`
    (`PROJECTION_STALE`)."""
    checkpoint = await _checkpoint(session, projection_type)

    authoritative_version = (
        await session.execute(
            select(func.max(AuditEvent.aggregate_version)).where(AuditEvent.aggregate_id == entity_id)
        )
    ).scalar_one_or_none()
    authoritative_event_at = (
        await session.execute(
            select(func.max(AuditEvent.occurred_at)).where(AuditEvent.aggregate_id == entity_id)
        )
    ).scalar_one_or_none()

    stale = authoritative_version is not None and authoritative_version > checkpoint.last_source_version
    degraded = checkpoint.state in ("ERROR", "REBUILDING")

    result = {
        "projection_type": projection_type,
        "entity_id": str(entity_id),
        "projected_source_version": checkpoint.last_source_version,
        "projected_at": checkpoint.projected_at.isoformat() if checkpoint.projected_at else None,
        "authoritative_version": authoritative_version,
        "authoritative_event_at": authoritative_event_at.isoformat() if authoritative_event_at else None,
        "checkpoint_state": checkpoint.state,
        "stale": bool(stale),
        "degraded": bool(degraded),
    }
    if raise_if_stale and stale:
        raise ProjectionStaleError(
            "Projection lags the authoritative record; re-read the authoritative source",
            projection_type=projection_type,
            entity_id=str(entity_id),
            projected_source_version=checkpoint.last_source_version,
            authoritative_version=authoritative_version,
        )
    return result


async def verify_cross_store_consistency(
    session: AsyncSession,
    *,
    projection_type: str,
    raise_if_mismatch: bool = False,
) -> dict:
    """`verifyCrossStoreConsistency()` -- DATA-FR-028. Compares the projection cursor against the
    authoritative max version / row count for its whole `source_stream`. Returns a `ConsistencyReport`;
    if `raise_if_mismatch` and the projection lags, raises `CrossStoreMismatchError`
    (`CROSS_STORE_MISMATCH`). The report is always safe to act on: the fix is a rebuild from the
    authoritative source, never an edit of the authoritative record."""
    checkpoint = await _checkpoint(session, projection_type)

    authoritative_max_version = (
        await session.execute(
            select(func.max(AuditEvent.aggregate_version)).where(
                AuditEvent.aggregate_type == checkpoint.source_stream
            )
        )
    ).scalar_one_or_none() or 0
    authoritative_aggregate_count = (
        await session.execute(
            select(func.count(func.distinct(AuditEvent.aggregate_id))).where(
                AuditEvent.aggregate_type == checkpoint.source_stream
            )
        )
    ).scalar_one()

    lag = authoritative_max_version - checkpoint.last_source_version
    mismatch = lag > 0

    report = {
        "projection_type": projection_type,
        "source_stream": checkpoint.source_stream,
        "projected_source_version": checkpoint.last_source_version,
        "authoritative_max_version": authoritative_max_version,
        "authoritative_aggregate_count": authoritative_aggregate_count,
        "version_lag": lag,
        "consistent": not mismatch,
        "checkpoint_state": checkpoint.state,
        "repair_action": "rebuild_projection" if mismatch else None,
    }
    if raise_if_mismatch and mismatch:
        raise CrossStoreMismatchError(
            "Projection diverged from the authoritative source; rebuild required",
            projection_type=projection_type,
            version_lag=lag,
        )
    return report
