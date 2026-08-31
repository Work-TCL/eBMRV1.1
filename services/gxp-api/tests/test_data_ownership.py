"""Document 69 (SPEC-DATA-001) -- Enterprise Data Ownership, Persistence Topology & Data Lineage.

Executable evidence for DATA-FR-001..030 and the specification's mandatory test catalogue
(foreign service tries GxP write / projection lags one version / rebuild / migration count-hash
mismatch / generic delete denied) plus the module-suite negatives (unauthenticated, unauthorized,
missing/stale expected_version, duplicate idempotency key, one-audit-event-per-commit).
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text

from app.main import app
from app.modules.audit.models import AuditEvent
from app.modules.dataops.commands import (
    RecordMigrationProvenanceCommand,
    RegisterDataClassCommand,
    record_migration_provenance,
    register_data_class,
    rebuild_projection,
    RebuildProjectionCommand,
)
from app.modules.dataops.consistency import get_projection_freshness, verify_cross_store_consistency
from app.modules.dataops.models import DataOwnershipRegistry, MigrationBatch, ProjectionCheckpoint
from app.modules.dataops.registry import (
    assert_authoritative_write_allowed,
    lint_ownership_seed,
    resolve_data_owner,
)
from app.modules.mutation.models import OutboxEvent
from app.mutation.errors import (
    DataOwnerUnknownError,
    ForbiddenDataOwnerWriteError,
    IdempotencyConflictError,
    InvalidTransitionError,
    StaleVersionError,
)
from tests.conftest import auth_headers, idem, login


@pytest.fixture
async def client_fixture():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------------------------------
# DATA-FR-001 / DATA-FR-027 -- authoritative-store registry + data dictionary
# ---------------------------------------------------------------------------------------------------


async def test_resolve_data_owner_returns_single_authoritative_store(db, seeded):
    """TC-069-001-01 / DATA-FR-001: every seeded entity resolves to exactly one authoritative
    owner + store."""
    row = await resolve_data_owner(db, "gxp_batch")
    assert row.authoritative_service == "gxp-api"
    assert row.authoritative_store == "POSTGRES"
    assert row.state == "EFFECTIVE"
    assert "FRAPPE_MARIADB" in row.projection_targets


async def test_resolve_data_owner_unknown_fails_closed(db, seeded):
    """TC-069-001 negative / AG-15: an unregistered entity type is an error, never a guessed owner."""
    with pytest.raises(DataOwnerUnknownError) as exc:
        await resolve_data_owner(db, "totally_unknown_entity")
    assert exc.value.code == "DATA_OWNER_UNKNOWN"


async def test_object_and_historian_tiers_are_registered(db, seeded):
    """DATA-FR-009 / DATA-FR-010: binary evidence -> OBJECT, high-frequency telemetry -> HISTORIAN."""
    assert (await resolve_data_owner(db, "evidence_object")).authoritative_store == "OBJECT"
    assert (await resolve_data_owner(db, "edge_observation")).authoritative_store == "HISTORIAN"


async def test_mariadb_scope_is_frappe_config_only(db, seeded):
    """TC-069-003-01 / DATA-FR-003: MariaDB owns UI/config metadata, not regulated truth."""
    row = await resolve_data_owner(db, "frappe_ui_configuration")
    assert row.authoritative_store == "MARIADB"
    assert row.authoritative_service == "ebmr_frappe"
    assert row.classification == "CONFIG"


async def test_ownership_lint_is_clean(seeded):
    """DATA-FR-030: the change-controlled ownership seed passes the static lint (single store per
    entity, valid tiers, no duplicate = no dual master)."""
    assert lint_ownership_seed() == []


async def test_data_dictionary_endpoint(client_fixture, seeded):
    """TC-069-027-01 / DATA-FR-027: machine-readable dictionary generated from the live registry.
    Endpoint RBAC is proven by the 403 for a non-holder; the generator payload is asserted directly
    (conftest seeds no bare 'admin' user to log in as)."""
    from app.core.db import SessionLocal
    from app.modules.dataops.registry import build_data_dictionary

    token = await login(client_fixture, "operator1")
    resp = await client_fixture.get("/platform/v1/data-dictionary", headers=auth_headers(token))
    assert resp.status_code == 403

    async with SessionLocal() as s:
        async with s.begin():
            payload = await build_data_dictionary(s)
    assert payload["entity_count"] >= 30
    assert payload["by_authoritative_store"]["POSTGRES"] >= 20
    assert "OBJECT" in payload["by_authoritative_store"]
    assert any(e["entity_type"] == "audit_event" for e in payload["entries"])


# ---------------------------------------------------------------------------------------------------
# DATA-FR-025 / DATA-FR-030 -- foreign service tries an authoritative write  (spec test S001)
# ---------------------------------------------------------------------------------------------------


async def test_foreign_service_write_is_rejected(db, seeded):
    """TC-069-S001 / DATA-FR-025: a service that is not the declared owner cannot write the entity."""
    owner = await assert_authoritative_write_allowed(
        db, service_identity="gxp-api", entity_type="gxp_batch", operation="UPDATE"
    )
    assert owner.authoritative_service == "gxp-api"

    with pytest.raises(ForbiddenDataOwnerWriteError) as exc:
        await assert_authoritative_write_allowed(
            db, service_identity="ebmr_frappe", entity_type="gxp_batch", operation="UPDATE"
        )
    assert exc.value.code == "FORBIDDEN_DATA_OWNER_WRITE"

    # a read by a non-owner is always allowed by contract
    await assert_authoritative_write_allowed(
        db, service_identity="ebmr_frappe", entity_type="gxp_batch", operation="READ"
    )


# ---------------------------------------------------------------------------------------------------
# DATA-FR-011 / DATA-FR-028 -- rebuildProjection() through the Mutation Gateway
# ---------------------------------------------------------------------------------------------------


async def _rebuild(client, token, body):
    return await client.post(
        f"/platform/v1/projections/{body['projection_type']}:rebuild",
        json=body,
        headers=auth_headers(token),
    )


async def test_rebuild_projection_commits_one_audit_and_outbox(db, seeded):
    """TC-069-001-01 / TC-069-M11 / DATA-FR-006: a committed rebuild bumps the checkpoint version and
    writes exactly one audit event + a ProjectionRebuilt outbox row in the same transaction."""
    from app.core.db import SessionLocal

    async with SessionLocal() as s:
        async with s.begin():
            receipt = await rebuild_projection(
                s,
                RebuildProjectionCommand(
                    idempotency_key=idem(), projection_type="frappe.batch_list",
                    source_stream="gxp_batch", reason="initial build",
                ),
                seeded["users"]["operator1"].id,
            )
    assert receipt.resulting_version == 2  # created at 1, advanced to 2

    async with SessionLocal() as s:
        cp = (await s.execute(
            select(ProjectionCheckpoint).where(ProjectionCheckpoint.projection_type == "frappe.batch_list")
        )).scalar_one()
        assert cp.state == "LIVE"
        assert cp.projected_at is not None
        audits = (await s.execute(
            select(func.count()).select_from(AuditEvent).where(AuditEvent.aggregate_id == cp.id)
        )).scalar_one()
        assert audits == 1
        events = (await s.execute(
            select(OutboxEvent.event_type).where(OutboxEvent.aggregate_id == cp.id)
        )).scalars().all()
        assert "ProjectionRebuilt" in events
        assert "ProjectionUpdateRequested" in events


async def test_rebuild_projection_stale_expected_version_rejected(db, seeded):
    """TC-069-M08 / MUT-FR-009: a second rebuild carrying the wrong checkpoint version is rejected."""
    from app.core.db import SessionLocal

    async with SessionLocal() as s:
        async with s.begin():
            await rebuild_projection(
                s,
                RebuildProjectionCommand(
                    idempotency_key=idem(), projection_type="search.batches",
                    source_stream="gxp_batch", reason="build",
                ),
                seeded["users"]["operator1"].id,
            )
    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(StaleVersionError) as exc:
                await rebuild_projection(
                    s,
                    RebuildProjectionCommand(
                        idempotency_key=idem(), projection_type="search.batches",
                        source_stream="gxp_batch", expected_version=1, reason="stale",
                    ),
                    seeded["users"]["operator1"].id,
                )
    assert exc.value.code == "STALE_VERSION"


async def test_rebuild_projection_idempotency(db, seeded):
    """TC-069-M09 / MUT-FR-010: same idempotency key + payload returns the original receipt."""
    from app.core.db import SessionLocal

    key = idem()
    cmd_kwargs = dict(idempotency_key=key, projection_type="analytics.yield", source_stream="gxp_batch", reason="x")
    async with SessionLocal() as s:
        async with s.begin():
            r1 = await rebuild_projection(s, RebuildProjectionCommand(**cmd_kwargs), seeded["users"]["operator1"].id)
    async with SessionLocal() as s:
        async with s.begin():
            r2 = await rebuild_projection(s, RebuildProjectionCommand(**cmd_kwargs), seeded["users"]["operator1"].id)
    assert r1.command_id == r2.command_id

    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(IdempotencyConflictError):
                await rebuild_projection(
                    s,
                    RebuildProjectionCommand(idempotency_key=key, projection_type="analytics.yield",
                                             source_stream="gxp_batch", reason="different"),
                    seeded["users"]["operator1"].id,
                )


async def test_rebuild_projection_requires_permission(client_fixture, seeded):
    """TC-069-M01 / TC-069-M02: unauthenticated -> 401; authenticated without projection.rebuild -> 403."""
    body = {"idempotency_key": idem(), "projection_type": "frappe.batch_list", "source_stream": "gxp_batch"}
    anon = await client_fixture.post("/platform/v1/projections/frappe.batch_list:rebuild", json=body)
    assert anon.status_code == 401

    token = await login(client_fixture, "operator1")
    denied = await _rebuild(client_fixture, token, body)
    assert denied.status_code == 403


# ---------------------------------------------------------------------------------------------------
# DATA-FR-007 / DATA-FR-008 -- projection freshness  (spec test S002: projection lags one version)
# ---------------------------------------------------------------------------------------------------


async def test_projection_freshness_flags_a_lagging_projection(db, seeded):
    """TC-069-008-01 / TC-069-S002 / DATA-FR-008: after the authoritative aggregate advances past the
    checkpoint cursor, freshness reports stale=True."""
    from app.core.db import SessionLocal
    from app.mutation.gateway import write_audit_event

    entity_id = uuid.uuid4()
    async with SessionLocal() as s:
        async with s.begin():
            await rebuild_projection(
                s,
                RebuildProjectionCommand(idempotency_key=idem(), projection_type="frappe.batch_list",
                                         source_stream="gxp_batch", reason="build"),
                seeded["users"]["operator1"].id,
            )
    # authoritative aggregate now advances to version 5 (a real audit row is the authoritative signal)
    async with SessionLocal() as s:
        async with s.begin():
            await write_audit_event(
                s, site_id=None, aggregate_type="gxp_batch", aggregate_id=entity_id,
                aggregate_version=5, action="Changed", actor_id=seeded["users"]["operator1"].id,
                correlation_id=uuid.uuid4(),
            )
    async with SessionLocal() as s:
        fresh = await get_projection_freshness(s, projection_type="frappe.batch_list", entity_id=entity_id)
    assert fresh["authoritative_version"] == 5
    assert fresh["projected_source_version"] == 0  # no gxp_batch audit rows existed at rebuild time
    assert fresh["stale"] is True


async def test_cross_store_consistency_detects_and_repairs(db, seeded):
    """TC-069-028-01 / DATA-FR-028: a mismatch is detected and its repair action is a rebuild from the
    authoritative source (never an edit of the authoritative record)."""
    from app.core.db import SessionLocal
    from app.mutation.gateway import write_audit_event

    async with SessionLocal() as s:
        async with s.begin():
            await rebuild_projection(
                s,
                RebuildProjectionCommand(idempotency_key=idem(), projection_type="search.batches",
                                         source_stream="gxp_batch", reason="build"),
                seeded["users"]["operator1"].id,
            )
            report = await verify_cross_store_consistency(s, projection_type="search.batches")
            assert report["consistent"] is True

    async with SessionLocal() as s:
        async with s.begin():
            await write_audit_event(
                s, site_id=None, aggregate_type="gxp_batch", aggregate_id=uuid.uuid4(),
                aggregate_version=3, action="Created", actor_id=seeded["users"]["operator1"].id,
                correlation_id=uuid.uuid4(),
            )
    async with SessionLocal() as s:
        report = await verify_cross_store_consistency(s, projection_type="search.batches")
    assert report["consistent"] is False
    assert report["version_lag"] == 3
    assert report["repair_action"] == "rebuild_projection"


# ---------------------------------------------------------------------------------------------------
# DATA-FR-024 -- recordMigrationProvenance()  (spec test S006: migration count/hash mismatch)
# ---------------------------------------------------------------------------------------------------


async def test_migration_provenance_reconciled_and_mismatch(db, seeded):
    """TC-069-024-01 / TC-069-S006 / DATA-FR-024: matching row counts -> RECONCILED; a count mismatch
    stays PENDING (never silently RECONCILED)."""
    from datetime import datetime, timezone

    from app.core.db import SessionLocal

    now = datetime.now(timezone.utc)
    async with SessionLocal() as s:
        async with s.begin():
            await record_migration_provenance(
                s,
                RecordMigrationProvenanceCommand(
                    idempotency_key=idem(), batch_ref="MIG-OK-1", source_system="legacy-mes",
                    source_artifact="batches.csv", source_hash="abc", transform_version="v1",
                    started_at=now, completed_at=now, source_row_count=100, loaded_row_count=100,
                    approver="data.engineer", reason="cutover",
                ),
                seeded["users"]["operator1"].id,
            )
            await record_migration_provenance(
                s,
                RecordMigrationProvenanceCommand(
                    idempotency_key=idem(), batch_ref="MIG-BAD-1", source_system="legacy-mes",
                    source_artifact="lots.csv", source_hash="def", transform_version="v1",
                    started_at=now, source_row_count=100, loaded_row_count=97,
                    approver="data.engineer", reason="cutover",
                ),
                seeded["users"]["operator1"].id,
            )
    async with SessionLocal() as s:
        rows = {r.batch_ref: r for r in (await s.execute(select(MigrationBatch))).scalars().all()}
    assert rows["MIG-OK-1"].reconciliation_status == "RECONCILED"
    assert rows["MIG-BAD-1"].reconciliation_status == "PENDING"

    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(InvalidTransitionError):
                await record_migration_provenance(
                    s,
                    RecordMigrationProvenanceCommand(
                        idempotency_key=idem(), batch_ref="MIG-OK-1", source_system="x",
                        source_artifact="y", source_hash="z", transform_version="v1",
                        started_at=now, approver="a", reason="dup",
                    ),
                    seeded["users"]["operator1"].id,
                )


# ---------------------------------------------------------------------------------------------------
# DATA-FR-023 -- generic delete denied at the DB privilege level  (spec test S007)
# ---------------------------------------------------------------------------------------------------


async def test_generic_delete_denied_at_db_privilege_level(db, seeded):
    """TC-069-023-01 / TC-069-S007 / DATA-FR-023: the runtime app role has no DELETE privilege on the
    registry -- a generic delete is refused by PostgreSQL, not just by application code."""
    with pytest.raises(Exception) as exc:
        await db.execute(text("DELETE FROM dataops.data_ownership_registry"))
        await db.commit()
    assert "permission denied" in str(exc.value).lower() or "InsufficientPrivilege" in type(exc.value).__name__


# ---------------------------------------------------------------------------------------------------
# DATA-FR-001 -- registerDataClass() supersede semantics
# ---------------------------------------------------------------------------------------------------


async def test_register_data_class_supersedes_with_version_bump(db, seeded):
    """DATA-FR-001 / AG-08: re-registering an entity bumps version and keeps the audit history."""
    from app.core.db import SessionLocal

    async with SessionLocal() as s:
        async with s.begin():
            await register_data_class(
                s,
                RegisterDataClassCommand(
                    idempotency_key=idem(), entity_type="new_widget", authoritative_service="gxp-api",
                    authoritative_store="POSTGRES", projection_targets=["FRAPPE_MARIADB"],
                    classification="GXP", reason="declare",
                ),
                seeded["users"]["operator1"].id,
            )
    async with SessionLocal() as s:
        async with s.begin():
            r2 = await register_data_class(
                s,
                RegisterDataClassCommand(
                    idempotency_key=idem(), entity_type="new_widget", authoritative_service="gxp-api",
                    authoritative_store="POSTGRES", projection_targets=["FRAPPE_MARIADB", "SEARCH"],
                    classification="GXP", expected_version=1, reason="add search projection",
                ),
                seeded["users"]["operator1"].id,
            )
    assert r2.resulting_version == 2
    async with SessionLocal() as s:
        row = (await s.execute(
            select(DataOwnershipRegistry).where(DataOwnershipRegistry.entity_type == "new_widget")
        )).scalar_one()
        assert row.version == 2
        assert "SEARCH" in row.projection_targets
