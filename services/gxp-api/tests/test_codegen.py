"""Client requirement #1 -- shared code-generation counter. Sequential increment, per-key isolation,
and a real concurrency check (two overlapping transactions must never mint the same code) against the
actual test Postgres database, no mocking."""

import asyncio
import uuid

from app.core.db import SessionLocal
from app.modules.codegen.service import next_code


async def test_next_code_increments_sequentially(db):
    async with db.begin():
        first = await next_code(db, entity_type="MATERIAL", prefix="MAT", site_id=uuid.uuid4())
    site_id = uuid.uuid4()
    async with db.begin():
        a = await next_code(db, entity_type="MATERIAL", prefix="MAT", site_id=site_id)
    async with db.begin():
        b = await next_code(db, entity_type="MATERIAL", prefix="MAT", site_id=site_id)
    assert a == "MAT-000001"
    assert b == "MAT-000002"


async def test_next_code_isolated_by_site(db):
    site_a = uuid.uuid4()
    site_b = uuid.uuid4()
    async with db.begin():
        code_a = await next_code(db, entity_type="MATERIAL", prefix="MAT", site_id=site_a)
    async with db.begin():
        code_b = await next_code(db, entity_type="MATERIAL", prefix="MAT", site_id=site_b)
    assert code_a == "MAT-000001"
    assert code_b == "MAT-000001"


async def test_next_code_global_scope_ignores_site(db):
    async with db.begin():
        a = await next_code(db, entity_type="EQUIPMENT_ASSET", prefix="EQP", site_id=None)
    async with db.begin():
        b = await next_code(db, entity_type="EQUIPMENT_ASSET", prefix="EQP", site_id=None)
    assert a == "EQP-000001"
    assert b == "EQP-000002"


async def test_next_code_isolated_by_entity_type_and_prefix(db):
    site_id = uuid.uuid4()
    async with db.begin():
        material_code = await next_code(db, entity_type="MATERIAL", prefix="MAT", site_id=site_id)
    async with db.begin():
        other_code = await next_code(db, entity_type="OTHER", prefix="MAT", site_id=site_id)
    assert material_code == "MAT-000001"
    assert other_code == "MAT-000001"


async def test_next_code_concurrent_calls_never_collide():
    site_id = uuid.uuid4()

    async def _issue():
        async with SessionLocal() as session:
            async with session.begin():
                return await next_code(session, entity_type="SUPPLIER", prefix="SUP", site_id=site_id)

    results = await asyncio.gather(*[_issue() for _ in range(10)])
    assert len(set(results)) == 10
    assert sorted(results) == [f"SUP-{n:06d}" for n in range(1, 11)]
