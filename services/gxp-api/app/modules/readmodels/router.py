"""Document 75 (SPEC-DATA-007) REST surface. The 4 operations Document 75 # 7 lists:

  GET  /search/v1/{index_type}                          -- authorized search query
  GET  /search/v1/{index_type}/{entity_id}               -- authoritative-checked result detail
  POST /search/v1/indexes/{index_type}:rebuild           -- rebuild an index (state-changing)
  POST /reports/v1/exports                               -- generate a frozen-cutoff export (state-changing)
  GET  /platform/v1/read-models/{name}/status            -- read-model freshness

No signature (Document 106 has no SPEC-DATA-007 row; Document 106 # 10 exempts rebuilds/reads).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.readmodels import commands
from app.modules.readmodels.models import ReadModelCheckpoint
from app.modules.readmodels.search import authorize_search_query, fetch_search_result_detail, query_search_index
from app.mutation.errors import NotFoundError
from app.mutation.schemas import MutationReceipt

search_router = APIRouter(prefix="/search/v1", tags=["readmodels-search"])
reports_router = APIRouter(prefix="/reports/v1", tags=["readmodels-reports"])
platform_router = APIRouter(prefix="/platform/v1", tags=["readmodels-status"])

# READ-FR-022: per-index-type allowlist. Seeded minimally; a real deployment extends this per index.
_ALLOWED_FILTERS = {"gxp_batch": {"state", "product_code"}, "material_lot": {"state"}}
_ALLOWED_SORT = {"gxp_batch": {"state"}, "material_lot": {"state"}}


@search_router.get("/{index_type}")
async def get_search_query(
    index_type: str, sort: str | None = None, limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    # SG-213 NOT fixable here, flagged rather than guessed: search.py's own authorize_search_query()
    # docstring says "tenant/site scoping is applied by the caller... before this", but there is nothing
    # to scope by -- ProjectionDocumentMetadata (readmodels/models.py) explicitly carries no site_id
    # ("platform/product-level tracking", ADR-0006) and _ALLOWED_FILTERS above doesn't expose one either.
    # A rebuild indexes a source_stream's aggregates across every site into one shared index (see
    # rebuild_search_index in commands.py), so today any actor holding search.query at ANY site can read
    # indexed_fields for every site's hits -- the same "anywhere" leak SG-213 closes elsewhere, but closing
    # it here means either adding a site signal to the index row or re-checking every hit against its
    # authoritative entity's real site (type-dispatched per index_type) -- an authorization-semantics
    # decision for a human, not a mechanical argument fix.
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="search.query", site_id=None)
        plan = authorize_search_query(
            index_type=index_type, filters={}, sort=sort,
            allowed_filter_fields=_ALLOWED_FILTERS.get(index_type, set()),
            allowed_sort_fields=_ALLOWED_SORT.get(index_type, set()),
        )
        rows = await query_search_index(session, plan=plan, limit=limit)
    return {
        "index_type": index_type, "count": len(rows),
        "results": [
            {"entity_id": str(r.entity_id), "source_version": r.source_version,
             "indexed_fields": r.indexed_fields, "state": r.state,
             "projected_at": r.projected_at.isoformat() if r.projected_at else None}
            for r in rows
        ],
    }


@search_router.get("/{index_type}/{entity_id}")
async def get_search_result_detail(
    index_type: str, entity_id: uuid.UUID,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    # SG-213 NOT fixable here -- same gap as get_search_query above: fetch_search_result_detail() checks
    # the indexed document's freshness against the authoritative version, but never the authoritative
    # entity's site, and ProjectionDocumentMetadata has no site_id to check locally either.
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="search.query", site_id=None)
        return await fetch_search_result_detail(session, index_type=index_type, entity_id=entity_id)


@search_router.post("/indexes/{index_type}:rebuild", response_model=MutationReceipt)
async def post_rebuild_index(
    index_type: str, cmd: commands.RebuildSearchIndexCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.index_type != index_type:
        from app.mutation.errors import ValidationFailedError

        raise ValidationFailedError("index_type in path and body must match")
    # SG-213 reviewed: ReadModelCheckpoint (models.py) has no site_id by design (ADR-0006, "platform/
    # product-level tracking") and rebuild_search_index() (commands.py) deliberately reindexes a
    # source_stream's aggregates across every site into one shared index -- there is no single site this
    # mutates, so site_id=None is correct, not a gap.
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="search.rebuild", site_id=None)
        return await commands.rebuild_search_index(session, cmd, actor.user_id)


@reports_router.post("/exports", response_model=MutationReceipt)
async def post_generate_export(
    cmd: commands.GenerateAsyncExportCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    # SG-213 reviewed: same as post_rebuild_index above -- generate_async_export() (commands.py) counts
    # aggregates for a source_stream across every site under one platform-wide ReadModelCheckpoint
    # (model has no site_id), so site_id=None is correct here too.
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="report.export", site_id=None)
        return await commands.generate_async_export(session, cmd, actor.user_id)


@platform_router.get("/read-models/{name}/status")
async def get_read_model_status(
    name: str,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    # SG-213 reviewed: ReadModelCheckpoint has no site_id (see post_rebuild_index's comment above) --
    # a checkpoint's freshness status is a platform-wide fact, not a per-site one, so site_id=None here
    # is correct.
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="search.query", site_id=None)
        row = (
            await session.execute(select(ReadModelCheckpoint).where(ReadModelCheckpoint.model_name == name))
        ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("No read-model checkpoint with this name")
    return {
        "model_name": row.model_name, "source_stream": row.source_stream, "state": row.state,
        "source_cutoff": row.source_cutoff.isoformat() if row.source_cutoff else None,
        "refreshed_at": row.refreshed_at.isoformat() if row.refreshed_at else None, "version": row.version,
    }
