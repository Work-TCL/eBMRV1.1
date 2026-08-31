"""Document 77 (SPEC-DATA-009) -- Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade
Architecture. Executable evidence for deployment-profile registration/upgrade, deployment
prerequisites, infrastructure drift and certificate-expiry checks.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from app.core.db import SessionLocal
from app.modules.deployment import checks, commands as dep
from app.modules.deployment.models import DeploymentProfile
from app.modules.mutation.models import OutboxEvent
from app.modules.security.crypto_models import CertificateMetadata
from app.mutation.errors import StaleVersionError, ValidationFailedError
from tests.conftest import idem


async def test_register_and_upgrade_deployment_profile(db, seeded):
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            r1 = await dep.register_deployment_profile(
                s, dep.RegisterDeploymentProfileCommand(
                    idempotency_key=idem(), profile_name="plant-01", environment="prod",
                    cloud_provider="ON_PREM", ha_profile="COMPACT", image_digest="sha256:aaa",
                    reason="initial install",
                ), actor,
            )
        async with s.begin():
            with pytest.raises(StaleVersionError):
                await dep.register_deployment_profile(
                    s, dep.RegisterDeploymentProfileCommand(
                        idempotency_key=idem(), profile_name="plant-01", environment="prod",
                        cloud_provider="ON_PREM", reason="retry",
                    ), actor,
                )
        async with s.begin():
            upgraded = await dep.record_platform_upgrade(
                s, dep.RecordPlatformUpgradeCommand(
                    idempotency_key=idem(), profile_name="plant-01", expected_version=r1.resulting_version,
                    from_image_digest="sha256:aaa", to_image_digest="sha256:bbb",
                    migration_from_revision="a7d2f4b9c1e8", migration_to_revision="d1a6f3c8b5e2",
                    reason="quarterly release",
                ), actor,
            )
    async with SessionLocal() as s:
        row = await s.get(DeploymentProfile, upgraded.aggregate_id)
        assert row.image_digest == "sha256:bbb"
        events = (await s.execute(select(OutboxEvent.event_type).where(OutboxEvent.aggregate_id == row.id))).scalars().all()
        assert "InfrastructureApplied" in events and "PlatformUpgraded" in events


async def test_record_platform_upgrade_requires_migration_revisions(db, seeded):
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            r1 = await dep.register_deployment_profile(
                s, dep.RegisterDeploymentProfileCommand(
                    idempotency_key=idem(), profile_name="plant-02", environment="prod",
                    cloud_provider="AWS", reason="install",
                ), actor,
            )
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await dep.record_platform_upgrade(
                    s, dep.RecordPlatformUpgradeCommand(
                        idempotency_key=idem(), profile_name="plant-02", expected_version=r1.resulting_version,
                        from_image_digest=None, to_image_digest="sha256:ccc",
                        migration_from_revision="", migration_to_revision="d1a6f3c8b5e2", reason="x",
                    ), actor,
                )


async def test_validate_deployment_prerequisites_real_checks(db, seeded):
    """DEP-FR-028/029/033: real checks against this database (not fabricated)."""
    async with SessionLocal() as s:
        result = await checks.validate_deployment_prerequisites(s)
    assert result["checks"]["database_reachable"] is True
    assert result["checks"]["clock_sane"] is True
    assert isinstance(result["passed"], bool)


async def test_detect_infrastructure_drift(db, seeded):
    async with SessionLocal() as s:
        clean = await checks.detect_infrastructure_drift(s, declared_image_digest="sha256:aaa", observed_image_digest="sha256:aaa")
        assert clean["drifted"] is False
        drifted = await checks.detect_infrastructure_drift(s, declared_image_digest="sha256:aaa", observed_image_digest="sha256:zzz")
        assert drifted["drifted"] is True
    async with SessionLocal() as s:
        rows = (await s.execute(select(OutboxEvent.event_type).where(OutboxEvent.event_type == "InfrastructureDriftDetected"))).scalars().all()
        assert len(rows) >= 1


async def test_check_certificate_expiry_reuses_crypto_metadata(db, seeded):
    """DEP-FR-034: reuses security.certificate_metadata (Document 65) rather than reinventing it."""
    async with SessionLocal() as s:
        async with s.begin():
            s.add(CertificateMetadata(
                serial=f"CERT-{uuid.uuid4().hex[:8]}", subject_sans={"cn": "gxp-api.internal"},
                profile="SERVICE_MTLS", expires_at=datetime.now(timezone.utc) + timedelta(days=5),
                state="ACTIVE", issuer_ref="internal-ca",
            ))
    async with SessionLocal() as s:
        report = await checks.check_certificate_expiry(s, warn_within_days=30)
    assert report["expiring_count"] >= 1
    async with SessionLocal() as s:
        rows = (await s.execute(select(OutboxEvent.event_type).where(OutboxEvent.event_type == "CertificateExpiryWarning"))).scalars().all()
        assert len(rows) >= 1


async def test_generic_delete_denied_at_db_privilege_level(db, seeded):
    with pytest.raises(Exception) as exc:
        await db.execute(text("DELETE FROM deployment.deployment_profile"))
        await db.commit()
    assert "permission denied" in str(exc.value).lower() or "InsufficientPrivilege" in type(exc.value).__name__
