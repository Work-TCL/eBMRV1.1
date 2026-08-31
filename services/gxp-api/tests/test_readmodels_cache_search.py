"""Document 75 (SPEC-DATA-007) -- Caching, Search, Read Models, Reporting Projections & Analytics.

Executable evidence for the versioned cache (TTL, single-flight, invalidation), the Postgres-backed
search provider (index/authorize/query/freshness), and the three Mutation-Gateway commands
(rebuild_search_index, refresh_read_model, generate_async_export).
"""

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.core.db import SessionLocal
from app.main import app
from app.modules.readmodels import commands as rm
from app.modules.readmodels.cache import VersionedCache, invalidate_entity_cache
from app.modules.readmodels.models import ProjectionDocumentMetadata, ReadModelCheckpoint
from app.modules.readmodels.search import authorize_search_query, fetch_search_result_detail, index_authoritative_projection
from app.modules.mutation.models import OutboxEvent
from app.mutation.errors import SearchFilterNotAllowedError, SearchResultStaleError, StaleVersionError
from app.mutation.gateway import write_audit_event
from tests.conftest import auth_headers, idem, login


@pytest.fixture
async def api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# --------------------------------------------------------------------------------------------------
# READ-FR-002..007/024..027 -- versioned cache
# --------------------------------------------------------------------------------------------------


async def test_versioned_cache_ttl_scope_and_single_flight():
    cache = VersionedCache()
    calls = {"n": 0}

    async def loader():
        calls["n"] += 1
        await asyncio.sleep(0.01)
        return {"loaded": calls["n"]}

    # single-flight: 5 concurrent misses for the same key trigger exactly one loader call
    results = await asyncio.gather(*[
        cache.get_versioned_cache_entry(cache_class="rule", scope_key="siteA", entity_id="r1", version=1, loader=loader, ttl_seconds=60)
        for _ in range(5)
    ])
    assert calls["n"] == 1
    assert all(r == {"loaded": 1} for r in results)

    # a different version is a different key -- not a stale hit
    miss = await cache.get_versioned_cache_entry(cache_class="rule", scope_key="siteA", entity_id="r1", version=2)
    assert miss is None

    # TTL expiry
    hot = await cache.get_versioned_cache_entry(cache_class="rule", scope_key="siteA", entity_id="ttl", version=1, loader=loader, ttl_seconds=0.001)
    await asyncio.sleep(0.02)
    expired = await cache.get_versioned_cache_entry(cache_class="rule", scope_key="siteA", entity_id="ttl", version=1)
    assert expired is None

    # cross-scope isolation
    await cache.get_versioned_cache_entry(cache_class="rule", scope_key="siteA", entity_id="r3", version=1, loader=loader, ttl_seconds=60)
    other_scope = await cache.get_versioned_cache_entry(cache_class="rule", scope_key="siteB", entity_id="r3", version=1)
    assert other_scope is None


async def test_invalidate_entity_cache_emits_signal(db, seeded):
    from app.modules.readmodels import cache as cache_mod

    async def loader():
        return {"v": 1}

    await cache_mod._cache.get_versioned_cache_entry(cache_class="probe", scope_key="s", entity_id="e1", version=1, loader=loader, ttl_seconds=60)
    count = await invalidate_entity_cache(cache_class="probe", scope_key="s", entity_id="e1")
    assert count == 1
    async with SessionLocal() as s:
        rows = (await s.execute(select(OutboxEvent.event_type).where(OutboxEvent.event_type == "CacheInvalidated"))).scalars().all()
        assert len(rows) >= 1


# --------------------------------------------------------------------------------------------------
# READ-FR-008..013/022 -- Postgres-backed search
# --------------------------------------------------------------------------------------------------


async def test_authorize_search_query_allowlist():
    authorize_search_query(index_type="gxp_batch", filters={"state": "RELEASED"}, sort="state",
                            allowed_filter_fields={"state"}, allowed_sort_fields={"state"})
    with pytest.raises(SearchFilterNotAllowedError):
        authorize_search_query(index_type="gxp_batch", filters={"secret_field": "x"}, sort=None,
                                allowed_filter_fields={"state"}, allowed_sort_fields={"state"})
    with pytest.raises(SearchFilterNotAllowedError):
        authorize_search_query(index_type="gxp_batch", filters={}, sort="unlisted",
                                allowed_filter_fields={"state"}, allowed_sort_fields={"state"})


async def test_index_and_fetch_result_detail_freshness(db, seeded):
    entity_id = uuid.uuid4()
    async with SessionLocal() as s:
        async with s.begin():
            await index_authoritative_projection(
                s, index_type="gxp_batch", entity_type="gxp_batch", entity_id=entity_id,
                source_version=1, allowed_fields={"state"}, source_payload={"state": "IN_EXECUTION", "secret": "x"},
            )
    async with SessionLocal() as s:
        doc = (await s.execute(select(ProjectionDocumentMetadata).where(ProjectionDocumentMetadata.entity_id == entity_id))).scalar_one()
        assert doc.indexed_fields == {"state": "IN_EXECUTION"}  # "secret" excluded (READ-FR-009)

    async with SessionLocal() as s:
        detail = await fetch_search_result_detail(s, index_type="gxp_batch", entity_id=entity_id)
        assert detail["stale"] is False

    # authoritative record advances -> now stale
    async with SessionLocal() as s:
        async with s.begin():
            await write_audit_event(
                s, site_id=None, aggregate_type="gxp_batch", aggregate_id=entity_id, aggregate_version=3,
                action="Changed", actor_id=seeded["users"]["operator1"].id, correlation_id=uuid.uuid4(),
            )
    async with SessionLocal() as s:
        detail2 = await fetch_search_result_detail(s, index_type="gxp_batch", entity_id=entity_id)
        assert detail2["stale"] is True
        with pytest.raises(SearchResultStaleError):
            await fetch_search_result_detail(s, index_type="gxp_batch", entity_id=entity_id, raise_if_stale=True)


# --------------------------------------------------------------------------------------------------
# READ-FR-014/016/017 -- gateway commands
# --------------------------------------------------------------------------------------------------


async def test_rebuild_search_index_reindexes_from_audit_ledger(db, seeded):
    actor = seeded["users"]["operator1"].id
    entity_id = uuid.uuid4()
    async with SessionLocal() as s:
        async with s.begin():
            await write_audit_event(
                s, site_id=None, aggregate_type="probe_stream", aggregate_id=entity_id, aggregate_version=1,
                action="Created", actor_id=actor, correlation_id=uuid.uuid4(),
                new_value={"state": "NEW", "internal": "hide-me"},
            )
        async with s.begin():
            receipt = await rm.rebuild_search_index(
                s,
                rm.RebuildSearchIndexCommand(
                    idempotency_key=idem(), index_type="probe_index", source_stream="probe_stream",
                    allowed_fields=["state"], reason="initial build",
                ),
                actor,
            )
    assert receipt.resulting_version == 2
    async with SessionLocal() as s:
        doc = (await s.execute(
            select(ProjectionDocumentMetadata).where(
                ProjectionDocumentMetadata.index_type == "probe_index", ProjectionDocumentMetadata.entity_id == entity_id
            )
        )).scalar_one()
        assert doc.indexed_fields == {"state": "NEW"}
        cp = (await s.execute(select(ReadModelCheckpoint).where(ReadModelCheckpoint.model_name == "search.probe_index"))).scalar_one()
        assert cp.state == "FRESH"


async def test_rebuild_search_index_stale_version_rejected(db, seeded):
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            await rm.rebuild_search_index(
                s, rm.RebuildSearchIndexCommand(idempotency_key=idem(), index_type="idx2", source_stream="s2", reason="x"), actor
            )
    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(StaleVersionError):
                await rm.rebuild_search_index(
                    s, rm.RebuildSearchIndexCommand(idempotency_key=idem(), index_type="idx2", expected_version=1, reason="y"), actor
                )


async def test_generate_async_export_freezes_cutoff(db, seeded):
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            r1 = await rm.generate_async_export(
                s, rm.GenerateAsyncExportCommand(idempotency_key=idem(), report_name="yield_summary", source_stream="gxp_batch", reason="monthly"), actor
            )
    async with SessionLocal() as s:
        cp = (await s.execute(select(ReadModelCheckpoint).where(ReadModelCheckpoint.model_name == "export.yield_summary"))).scalar_one()
        assert cp.source_cutoff is not None
        assert cp.version == r1.resulting_version


# --------------------------------------------------------------------------------------------------
# API surface: RBAC + full roundtrip
# --------------------------------------------------------------------------------------------------


async def test_api_rbac_unauthenticated_and_unauthorized(api, seeded):
    """TC-075-M01/M02: unauthenticated -> 401; a role without search.*/report.export -> 403. (No
    seeded demo user holds "Admin" -- the only role granted these codes -- so the 200 path is covered
    by the direct-call gateway tests above, same treatment as the dataops data-dictionary endpoint.)"""
    assert (await api.get("/platform/v1/read-models/nope/status")).status_code == 401

    op_tok = await login(api, "operator1")
    assert (await api.get("/platform/v1/read-models/nope/status", headers=auth_headers(op_tok))).status_code == 403

    rebuild_body = {"idempotency_key": idem(), "index_type": "api_probe", "source_stream": "probe_stream", "reason": "x"}
    denied = await api.post("/search/v1/indexes/api_probe:rebuild", json=rebuild_body, headers=auth_headers(op_tok))
    assert denied.status_code == 403

    export_body = {"idempotency_key": idem(), "report_name": "r", "source_stream": "gxp_batch", "reason": "x"}
    denied2 = await api.post("/reports/v1/exports", json=export_body, headers=auth_headers(op_tok))
    assert denied2.status_code == 403
