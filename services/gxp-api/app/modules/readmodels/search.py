"""Document 75 (SPEC-DATA-007) Postgres-backed default search provider -- READ-FR-008..014/022.

Phase 1 has no live OpenSearch/Elasticsearch (READ-FR-008: "pluggable... not hard-dependent on one
commercial engine" -- this *is* the pluggable default, not a placeholder pending a real one).
`index_authoritative_projection()` upserts one `readmodels.projection_document_metadata` row per
entity with only the caller's allowlisted fields (READ-FR-009); `authorize_search_query()` validates a
filter/sort request against a per-`index_type` allowlist before any query runs (READ-FR-022);
`fetch_search_result_detail()` compares the indexed document's `source_version` against the
authoritative version (via the audit ledger, same technique as
`app/modules/dataops/consistency.py::get_projection_freshness`) and can enforce freshness rather than
silently trusting a stale hit (READ-FR-011/013).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent
from app.modules.readmodels.models import ProjectionDocumentMetadata
from app.modules.readmodels.signals import emit_search_document_indexed
from app.mutation.errors import NotFoundError, SearchFilterNotAllowedError, SearchResultStaleError


async def index_authoritative_projection(
    session: AsyncSession,
    *,
    index_type: str,
    entity_type: str,
    entity_id: uuid.UUID,
    source_version: int,
    allowed_fields: set[str],
    source_payload: dict,
) -> ProjectionDocumentMetadata:
    indexed = {k: v for k, v in (source_payload or {}).items() if k in allowed_fields}
    row = (
        await session.execute(
            select(ProjectionDocumentMetadata).where(
                ProjectionDocumentMetadata.index_type == index_type,
                ProjectionDocumentMetadata.entity_type == entity_type,
                ProjectionDocumentMetadata.entity_id == entity_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = ProjectionDocumentMetadata(
            index_type=index_type, entity_type=entity_type, entity_id=entity_id,
            source_version=source_version, indexed_fields=indexed, state="LIVE", version=1,
        )
        session.add(row)
    else:
        # EVT-FR-014/027 (WP-11 Stage 3): a live at-least-once consumer has no total-order guarantee
        # across redeliveries -- an older event for this same entity can arrive after a newer one already
        # landed here. Applying it would regress the index to stale data, exactly what these requirements
        # forbid ("reject stale projections" / "ignores duplicate/stale event safely"). The full-rebuild
        # caller (`rebuild_search_index`) is unaffected: it always computes `source_version` as the true
        # per-aggregate max from the audit ledger, so it never passes a version <= what's already stored
        # for a value that genuinely changed; a repeat rebuild with nothing new to apply now correctly
        # no-ops instead of bumping `version`/re-emitting a signal for identical data.
        if source_version <= row.source_version:
            return row
        row.source_version = source_version
        row.indexed_fields = indexed
        row.state = "LIVE"
        row.projected_at = datetime.now(timezone.utc)
        row.version += 1
    await session.flush()
    await emit_search_document_indexed({
        "index_type": index_type, "entity_type": entity_type, "entity_id": str(entity_id),
        "source_version": source_version,
    })
    return row


def authorize_search_query(
    *, index_type: str, filters: dict, sort: str | None, allowed_filter_fields: set[str], allowed_sort_fields: set[str]
) -> dict:
    """READ-FR-022: every filter/sort field must be on the per-`index_type` allowlist. Tenant/site/role
    scoping is applied by the caller (the authenticated request's policy check) before this; this
    function only bounds *which fields* a query may touch."""
    for field in filters:
        if field not in allowed_filter_fields:
            raise SearchFilterNotAllowedError(
                f"filter field {field!r} is not allowed for index {index_type!r}",
                index_type=index_type, field=field,
            )
    if sort is not None and sort.lstrip("-") not in allowed_sort_fields:
        raise SearchFilterNotAllowedError(
            f"sort field {sort!r} is not allowed for index {index_type!r}", index_type=index_type, field=sort
        )
    return {"index_type": index_type, "filters": filters, "sort": sort}


async def query_search_index(
    session: AsyncSession, *, plan: dict, limit: int = 50
) -> list[ProjectionDocumentMetadata]:
    """Runs an already-authorized plan (`authorize_search_query()`'s output) against the Postgres-backed
    index: exact-match on each allowlisted filter's `indexed_fields` key (READ-FR-009/010). Result IDs
    still need re-authorization on fetch (READ-FR-010) -- that's the caller's job, same as any list."""
    stmt = select(ProjectionDocumentMetadata).where(ProjectionDocumentMetadata.index_type == plan["index_type"])
    for field, value in plan["filters"].items():
        stmt = stmt.where(ProjectionDocumentMetadata.indexed_fields[field].astext == str(value))
    if plan.get("sort"):
        col = ProjectionDocumentMetadata.projected_at
        stmt = stmt.order_by(col.desc() if plan["sort"].startswith("-") else col.asc())
    return list((await session.execute(stmt.limit(min(limit, 200)))).scalars().all())


async def fetch_search_result_detail(
    session: AsyncSession, *, index_type: str, entity_id: uuid.UUID, raise_if_stale: bool = False
) -> dict:
    doc = (
        await session.execute(
            select(ProjectionDocumentMetadata).where(
                ProjectionDocumentMetadata.index_type == index_type,
                ProjectionDocumentMetadata.entity_id == entity_id,
            )
        )
    ).scalar_one_or_none()
    if doc is None:
        raise NotFoundError("No indexed document for this entity in this index")

    authoritative_version = (
        await session.execute(
            select(func.max(AuditEvent.aggregate_version)).where(AuditEvent.aggregate_id == entity_id)
        )
    ).scalar_one_or_none()
    stale = authoritative_version is not None and authoritative_version > doc.source_version
    result = {
        "entity_id": str(entity_id), "index_type": index_type, "indexed_source_version": doc.source_version,
        "authoritative_version": authoritative_version, "indexed_fields": doc.indexed_fields,
        "projected_at": doc.projected_at.isoformat() if doc.projected_at else None, "stale": bool(stale),
    }
    if stale and raise_if_stale:
        raise SearchResultStaleError(
            "Indexed document lags the authoritative record; re-fetch the authoritative detail",
            entity_id=str(entity_id), indexed_source_version=doc.source_version,
            authoritative_version=authoritative_version,
        )
    return result
