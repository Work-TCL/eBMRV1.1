"""Document 70 (SPEC-DATA-002) -- PostgreSQL GxP Database Architecture, Schema, Partitioning &
Concurrency. Executable evidence for the PG-FR guarantees that are code/DB-observable: optimistic
concurrency (PG-FR-008), deadlock retry (PG-FR-012), outbox atomicity (PG-FR-014), append-only
privilege (PG-FR-015), partition coverage / create refusal (PG-FR-016/030), integrity check
(PG-FR-023/032), primary/replica read routing (PG-FR-031), and the operational-signal emitter.
"""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from app.core.db import SessionLocal
from app.modules.audit.models import AuditEvent
from app.modules.dataops.models import DataOwnershipRegistry
from app.modules.dbops.concurrency import apply_optimistic_update, with_deadlock_retry
from app.modules.dbops.integrity import run_database_integrity_check
from app.modules.dbops.partitioning import create_time_partition, verify_partition_coverage
from app.modules.dbops.read_routing import get_primary_consistency_read, run_read_replica_query
from app.modules.dbops.signals import emit_db_signal
from app.modules.mutation.models import OutboxEvent
from app.mutation.errors import (
    DeadlockDetectedError,
    PartitionCreateFailedError,
    StaleVersionError,
)
from app.mutation.gateway import write_outbox_event


# --------------------------------------------------------------------------------------------------
# PG-FR-008 -- optimistic concurrency helper
# --------------------------------------------------------------------------------------------------


async def test_apply_optimistic_update_happy_and_stale(db, seeded):
    """TC-070-008-01/02: conditional UPDATE bumps version when expected matches; a stale expected
    version changes no row and raises STALE_VERSION."""
    async with SessionLocal() as s:
        async with s.begin():
            row = DataOwnershipRegistry(
                entity_type=f"dbops_probe_{uuid.uuid4().hex[:8]}", authoritative_service="gxp-api",
                authoritative_store="POSTGRES", projection_targets=[], classification="CONFIG", version=1,
            )
            s.add(row)
            await s.flush()
            rid = row.id

        async with s.begin():
            new_v = await apply_optimistic_update(
                s, schema="dataops", table="data_ownership_registry", row_id=rid,
                expected_version=1, set_columns={"classification": "OPERATIONAL"},
            )
            assert new_v == 2

        async with s.begin():
            with pytest.raises(StaleVersionError) as exc:
                await apply_optimistic_update(
                    s, schema="dataops", table="data_ownership_registry", row_id=rid,
                    expected_version=1, set_columns={"classification": "GXP"},
                )
            assert exc.value.code == "STALE_VERSION"


# --------------------------------------------------------------------------------------------------
# PG-FR-012 -- deadlock / serialization-failure retry
# --------------------------------------------------------------------------------------------------


class _FakeOrig(Exception):
    def __init__(self, sqlstate):
        super().__init__("simulated")
        self.sqlstate = sqlstate
        self.pgcode = sqlstate


async def test_with_deadlock_retry_recovers_then_gives_up():
    """TC-070-012-02: a transient 40P01 is retried and then succeeds; a persistent one is re-raised as
    DEADLOCK_DETECTED after the bounded attempt count."""
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise OperationalError("UPDATE ...", {}, _FakeOrig("40P01"))
        return "ok"

    assert await with_deadlock_retry(flaky, attempts=3, base_delay_seconds=0) == "ok"
    assert calls["n"] == 3

    async def always_deadlocks():
        raise OperationalError("UPDATE ...", {}, _FakeOrig("40P01"))

    with pytest.raises(DeadlockDetectedError) as exc:
        await with_deadlock_retry(always_deadlocks, attempts=2, base_delay_seconds=0)
    assert exc.value.code == "DEADLOCK_DETECTED"

    async def other_error():
        raise OperationalError("UPDATE ...", {}, _FakeOrig("23505"))  # unique_violation -> not retried

    with pytest.raises(OperationalError):
        await with_deadlock_retry(other_error, attempts=3, base_delay_seconds=0)


# --------------------------------------------------------------------------------------------------
# PG-FR-014 -- outbox atomicity (rollback leaves no orphan)
# --------------------------------------------------------------------------------------------------


async def test_outbox_atomic_rollback(db):
    """TC-070-014-01: an outbox insert that shares a transaction with a failing domain write is rolled
    back with it -- no orphan event row."""
    marker = uuid.uuid4()
    with pytest.raises(RuntimeError):
        async with SessionLocal() as s:
            async with s.begin():
                await write_outbox_event(
                    s, event_type="DeadlockDetected", aggregate_type="database_health",
                    aggregate_id=marker, aggregate_version=1, payload={"probe": True},
                    correlation_id=uuid.uuid4(),
                )
                raise RuntimeError("domain write failed after the outbox append")

    async with SessionLocal() as s:
        found = (await s.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == marker)
        )).scalar_one_or_none()
    assert found is None


# --------------------------------------------------------------------------------------------------
# PG-FR-015 -- append-only tables: no DELETE privilege for the runtime role
# --------------------------------------------------------------------------------------------------


async def test_audit_delete_denied_at_db_privilege_level(db, seeded):
    """TC-070-015-02: the runtime app role cannot DELETE from audit.audit_events -- refused by
    PostgreSQL, not merely by application code."""
    with pytest.raises(Exception) as exc:
        await db.execute(text("DELETE FROM audit.audit_events"))
        await db.commit()
    assert "permission denied" in str(exc.value).lower() or "InsufficientPrivilege" in type(exc.value).__name__


# --------------------------------------------------------------------------------------------------
# PG-FR-016 / PG-FR-030 -- partition helpers
# --------------------------------------------------------------------------------------------------


async def test_partition_coverage_reports_unpartitioned(db):
    """TC-070-016-01: a non-partitioned parent reports partitioned=False (no false gap alarm) rather
    than raising."""
    async with SessionLocal() as s:
        rep = await verify_partition_coverage(s, schema="audit", table="audit_events")
    assert rep["partitioned"] is False
    assert rep["covered"] is None


async def test_create_partition_refuses_nonpartitioned_parent(db):
    """TC-070-016 negative: create_time_partition on a plain table is PARTITION_CREATE_FAILED."""
    from datetime import datetime, timezone

    async with SessionLocal() as s:
        with pytest.raises(PartitionCreateFailedError) as exc:
            await create_time_partition(
                s, schema="audit", table="audit_events",
                lower=datetime(2027, 1, 1, tzinfo=timezone.utc),
                upper=datetime(2027, 2, 1, tzinfo=timezone.utc),
            )
    assert exc.value.code == "PARTITION_CREATE_FAILED"


# --------------------------------------------------------------------------------------------------
# PG-FR-023 / PG-FR-032 -- integrity check
# --------------------------------------------------------------------------------------------------


async def test_database_integrity_check_healthy(db):
    """TC-070-023-01 / TC-070-032-01: on a healthy test DB the integrity report has zero checksum
    failures and healthy=True."""
    async with SessionLocal() as s:
        rep = await run_database_integrity_check(s)
    assert rep["checksum_failures"] == 0
    assert rep["healthy"] is True
    assert "deadlocks" in rep


# --------------------------------------------------------------------------------------------------
# PG-FR-031 -- primary / replica read routing
# --------------------------------------------------------------------------------------------------


async def test_primary_read_and_replica_fallback(db):
    """TC-070-031-01: a regulated read runs on the primary; a reporting read with no replica
    configured is served by the primary and flagged replica_configured=False."""
    async def fetch(s):
        return (await s.execute(text("SELECT 42"))).scalar_one()

    async with SessionLocal() as s:
        assert await get_primary_consistency_read(s, fetch=fetch) == 42

    async with SessionLocal() as s:
        out = await run_read_replica_query(s, fetch=fetch, max_staleness_seconds=5)
    assert out["served_by"] == "primary"
    assert out["replica_configured"] is False
    assert out["data"] == 42

    async with SessionLocal() as s:
        with pytest.raises(ValueError):
            await run_read_replica_query(s, fetch=fetch, max_staleness_seconds=-1)


# --------------------------------------------------------------------------------------------------
# operational signal emitter
# --------------------------------------------------------------------------------------------------


async def test_emit_db_signal(db):
    """The six Document 70 # 9 signals go to the outbox best-effort; an unknown type is a programming
    error."""
    with pytest.raises(ValueError):
        await emit_db_signal("NotARealSignal", {})

    await emit_db_signal("PartitionGapDetected", {"table": "audit.audit_events", "gap_from": "2099-01"})
    async with SessionLocal() as s:
        rows = (await s.execute(
            select(OutboxEvent).where(OutboxEvent.event_type == "PartitionGapDetected")
        )).scalars().all()
    assert len(rows) >= 1
    assert rows[-1].aggregate_type == "database_health"
