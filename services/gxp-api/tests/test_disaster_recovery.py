"""Document 76 (SPEC-DATA-008) -- Backup, Restore, Point-in-Time Recovery & Disaster Recovery.
Executable evidence for the Document 109 tier seed, recovery-objective management, backup recording,
restore-test PASS/FAIL determination against the objective, backup-freshness/RPO-at-risk detection,
evidence reconciliation reuse, recovery validation gating, data-loss assessment and failover recording.
"""

import base64
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.core.db import SessionLocal
from app.main import app
from app.modules.disaster_recovery import commands as dr
from app.modules.disaster_recovery import failover, recovery
from app.modules.disaster_recovery.models import BackupInventory, RecoveryObjectiveProfile, RestoreTest
from app.modules.evidence import commands as ev
from app.modules.evidence.store import LocalEvidenceStore, set_store, sha256_bytes
from app.modules.mutation.models import OutboxEvent
from app.mutation.errors import RecoveryValidationFailedError, StaleVersionError, ValidationFailedError
from tests.conftest import auth_headers, idem, login


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    set_store(LocalEvidenceStore(base_dir=str(tmp_path / "dr_evstore")))
    yield
    set_store(LocalEvidenceStore())


@pytest.fixture
async def api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_document_109_tier_seed_present(db, seeded):
    """DR-FR-001/002: the platform-default recovery tiers from Document 109 are seeded verbatim."""
    async with SessionLocal() as s:
        t0 = (await s.execute(select(RecoveryObjectiveProfile).where(RecoveryObjectiveProfile.component == "postgres_gxp"))).scalar_one()
        t4 = (await s.execute(select(RecoveryObjectiveProfile).where(RecoveryObjectiveProfile.component == "readmodels_search_cache"))).scalar_one()
    assert t0.tier == "T0" and t0.rpo_seconds == 0 and t0.rto_seconds == 4 * 3600
    assert t4.tier == "T4" and t4.rpo_seconds is None  # "rebuildable, no RPO commitment"


async def test_create_recovery_objective_profile_create_and_update(db, seeded):
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            r1 = await dr.create_recovery_objective_profile(
                s, dr.CreateRecoveryObjectiveProfileCommand(
                    idempotency_key=idem(), component="custom_search_cluster", tier="T4",
                    rto_seconds=3600, approved_by="Customer Quality override", reason="new component",
                ), actor,
            )
        async with s.begin():
            with pytest.raises(StaleVersionError):
                await dr.create_recovery_objective_profile(
                    s, dr.CreateRecoveryObjectiveProfileCommand(
                        idempotency_key=idem(), component="custom_search_cluster", tier="T4",
                        rto_seconds=1800, approved_by="x", reason="y",
                    ), actor,
                )
        async with s.begin():
            r2 = await dr.create_recovery_objective_profile(
                s, dr.CreateRecoveryObjectiveProfileCommand(
                    idempotency_key=idem(), component="custom_search_cluster", tier="T4",
                    rto_seconds=1800, approved_by="Customer Quality override", expected_version=r1.resulting_version,
                    reason="tighten RTO",
                ), actor,
            )
    assert r2.resulting_version == r1.resulting_version + 1


async def test_record_backup_requires_checksum_on_success(db, seeded):
    actor = seeded["users"]["operator1"].id
    now = datetime.now(timezone.utc)
    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await dr.record_backup_execution(
                    s, dr.RecordBackupExecutionCommand(
                        idempotency_key=idem(), component="postgres_gxp", backup_type="FULL",
                        started_at=now, completed_at=now, status="SUCCESS", reason="nightly",
                    ), actor,
                )
        async with s.begin():
            receipt = await dr.record_backup_execution(
                s, dr.RecordBackupExecutionCommand(
                    idempotency_key=idem(), component="postgres_gxp", backup_type="FULL",
                    started_at=now, completed_at=now, checksum="abc123", status="SUCCESS", reason="nightly",
                ), actor,
            )
    async with SessionLocal() as s:
        row = await s.get(BackupInventory, receipt.aggregate_id)
        assert row.status == "SUCCESS" and row.checksum == "abc123"


async def test_restore_test_pass_and_fail_against_objective(db, seeded):
    """DR-FR-016/017/030: postgres_gxp is T0 (RPO=0, RTO<=4h). PASS requires a PITR-targeted restore
    (zero additional loss beyond the target -- Document 109's own RPO-0-via-synchronous-replication-or-
    equivalent interpretation) with all integrity checks holding; a base-backup-only restore (no PITR)
    genuinely misses the RPO-0 objective and FAILs, same as a failed integrity check does."""
    actor = seeded["users"]["operator1"].id
    now = datetime.now(timezone.utc)
    async with SessionLocal() as s:
        async with s.begin():
            backup = await dr.record_backup_execution(
                s, dr.RecordBackupExecutionCommand(
                    idempotency_key=idem(), component="postgres_gxp", backup_type="FULL",
                    started_at=now - timedelta(hours=1), completed_at=now - timedelta(minutes=30),
                    checksum="c1", status="SUCCESS", reason="nightly",
                ), actor,
            )
        async with s.begin():
            passed = await dr.execute_postgres_restore_test(
                s, dr.ExecutePostgresRestoreTestCommand(
                    idempotency_key=idem(), backup_id=backup.aggregate_id, target_environment="isolated-dr-1",
                    pitr_target=now - timedelta(minutes=1), started_at=now, completed_at=now + timedelta(minutes=10),
                    integrity_checks={"row_counts_match": True, "checksum_verified": True}, reason="quarterly drill",
                ), actor,
            )
        async with s.begin():
            failed = await dr.execute_postgres_restore_test(
                s, dr.ExecutePostgresRestoreTestCommand(
                    idempotency_key=idem(), backup_id=backup.aggregate_id, target_environment="isolated-dr-1",
                    started_at=now, completed_at=now + timedelta(minutes=10),
                    integrity_checks={"row_counts_match": False}, reason="quarterly drill",
                ), actor,
            )
    async with SessionLocal() as s:
        p = await s.get(RestoreTest, passed.aggregate_id)
        f = await s.get(RestoreTest, failed.aggregate_id)
        assert p.result == "PASS" and f.result == "FAIL"
        types = (await s.execute(select(OutboxEvent.event_type).where(OutboxEvent.aggregate_id.in_([p.id, f.id])))).scalars().all()
        assert "PostgresRestoreTestCompleted" in types and "RestoreTestFailed" in types


async def test_verify_backup_freshness_flags_at_risk(db, seeded):
    """Uses mariadb_frappe (T2, rpo_seconds=900s/15min) -- a periodic-backup-age RPO check is the
    semantically correct use of this function; T0's RPO=0 means synchronous replication, not backup
    age (Document 109 # 1 interpretation rule), so it isn't exercised via backup-age here."""
    async with SessionLocal() as s:
        fresh = await recovery.verify_backup_freshness(
            s, component="mariadb_frappe", last_backup_completed_at=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        assert fresh["at_risk"] is False
        stale = await recovery.verify_backup_freshness(
            s, component="mariadb_frappe", last_backup_completed_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        assert stale["at_risk"] is True
    async with SessionLocal() as s:
        rows = (await s.execute(select(OutboxEvent.event_type).where(OutboxEvent.event_type == "BackupRPOAtRisk"))).scalars().all()
        assert len(rows) >= 1


async def test_reconcile_evidence_after_restore_reuses_evidence_integrity(db, seeded):
    """DR-FR-019: reuses evidence.verify_evidence_integrity() rather than reinventing it."""
    actor = seeded["users"]["operator1"].id
    owner_id = uuid.uuid4()
    data = b"restored evidence bytes"
    async with SessionLocal() as s:
        async with s.begin():
            staged = await ev.stage_evidence_upload(
                s, ev.StageEvidenceUploadCommand(
                    idempotency_key=idem(), owner_type="gxp_batch", owner_id=owner_id, filename="r.pdf",
                    mime_type="application/pdf", expected_hash=sha256_bytes(data), reason="x",
                ), actor,
            )
        async with s.begin():
            await ev.finalize_evidence_upload(
                s, ev.FinalizeEvidenceUploadCommand(
                    idempotency_key=idem(), evidence_id=staged.aggregate_id, expected_version=1,
                    content_base64=base64.b64encode(data).decode(), reason="x",
                ), actor,
            )
        async with s.begin():
            report = await recovery.reconcile_evidence_after_restore(s, owner_type="gxp_batch", owner_id=owner_id, actor_user_id=actor)
    assert report["healthy"] is True


async def test_validate_recovered_platform_gates_on_checks(db, seeded):
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            ok = await recovery.validate_recovered_platform(s, checks={"db_reachable": True, "audit_chain_intact": True}, actor_user_id=actor)
        assert ok["healthy"] is True

        async with s.begin():
            with pytest.raises(RecoveryValidationFailedError):
                await recovery.validate_recovered_platform(s, checks={"db_reachable": True, "audit_chain_intact": False}, actor_user_id=actor)
    async with SessionLocal() as s:
        types = (await s.execute(select(OutboxEvent.event_type).where(OutboxEvent.event_type.in_(["PlatformRecoveryValidated", "RecoveryValidationFailed"])))).scalars().all()
        assert "PlatformRecoveryValidated" in types and "RecoveryValidationFailed" in types


async def test_record_data_loss_assessment_computes_gap(db, seeded):
    actor = seeded["users"]["operator1"].id
    restore_point = datetime.now(timezone.utc) - timedelta(minutes=20)
    expected_latest = datetime.now(timezone.utc)
    async with SessionLocal() as s:
        async with s.begin():
            out = await recovery.record_data_loss_assessment(
                s, restore_point=restore_point, expected_latest=expected_latest,
                missing_scope="ebmr.gxp_batch (site T1)", actor_user_id=actor, reason="PITR landed before incident",
            )
    assert 1190 <= out["gap_seconds"] <= 1210  # ~20 minutes


async def test_record_database_failover_requires_incident_and_distinct_primaries(db, seeded):
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await failover.record_database_failover(
                    s, incident_ref="", previous_primary="pg-a", new_primary="pg-b", reason="x", actor_user_id=actor,
                )
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await failover.record_database_failover(
                    s, incident_ref="INC-1", previous_primary="pg-a", new_primary="pg-a", reason="x", actor_user_id=actor,
                )
        async with s.begin():
            out = await failover.record_database_failover(
                s, incident_ref="INC-1", previous_primary="pg-a", new_primary="pg-b",
                reason="primary unresponsive", actor_user_id=actor,
            )
    assert out["new_primary"] == "pg-b"
    async with SessionLocal() as s:
        rows = (await s.execute(select(OutboxEvent.event_type).where(OutboxEvent.event_type == "DatabaseFailoverCompleted"))).scalars().all()
        assert len(rows) >= 1


async def test_generic_delete_denied_at_db_privilege_level(db, seeded):
    with pytest.raises(Exception) as exc:
        await db.execute(text("DELETE FROM disaster_recovery.restore_test"))
        await db.commit()
    assert "permission denied" in str(exc.value).lower() or "InsufficientPrivilege" in type(exc.value).__name__


async def test_api_backup_health_rbac(api, seeded):
    assert (await api.get("/platform/v1/backups/health")).status_code == 401
    op_tok = await login(api, "operator1")
    assert (await api.get("/platform/v1/backups/health", headers=auth_headers(op_tok))).status_code == 403
