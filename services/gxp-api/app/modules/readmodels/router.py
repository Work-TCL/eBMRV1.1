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
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="search.rebuild", site_id=None)
        return await commands.rebuild_search_index(session, cmd, actor.user_id)


@reports_router.post("/exports", response_model=MutationReceipt)
async def post_generate_export(
    cmd: commands.GenerateAsyncExportCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="report.export", site_id=None)
        return await commands.generate_async_export(session, cmd, actor.user_id)


@platform_router.get("/read-models/{name}/status")
async def get_read_model_status(
    name: str,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
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
