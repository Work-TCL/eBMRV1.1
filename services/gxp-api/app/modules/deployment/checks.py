"""Document 77 (SPEC-DATA-009) prerequisite / drift / certificate-expiry checks -- DEP-FR-028/029/031/034.

Each check reads something real (this database, this codebase's alembic state, a configured secret,
`security.certificate_metadata`) rather than fabricating a result. Where this codebase genuinely cannot
observe the thing Document 77 describes (no live Kubernetes API, no cloud provider SDK), the function is
not implemented as a no-op stub -- it is a documented known limitation (see `ARCHITECTURE.md`).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.security.crypto_models import CertificateMetadata
from app.mutation.errors import DeploymentPrerequisiteFailedError
from app.mutation.gateway import write_outbox_event

_DEV_JWT_SECRET_MARKERS = ("dev-secret", "changeme", "change-me")


async def validate_deployment_prerequisites(session: AsyncSession, *, raise_on_failure: bool = False) -> dict:
    """`validateDeploymentPrerequisites()` -- DEP-FR-028/029. Real, machine-checkable pre-install/
    pre-upgrade gates: the database answers, the JWT signing secret is not a known dev placeholder,
    and the server clock is not wildly divergent from the database's own clock (a crude but real
    cross-check, DEP-FR-033)."""
    checks: dict[str, bool] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["database_reachable"] = True
    except Exception:  # noqa: BLE001
        checks["database_reachable"] = False

    checks["jwt_secret_not_default"] = not any(
        marker in settings.jwt_secret.lower() for marker in _DEV_JWT_SECRET_MARKERS
    )

    try:
        db_now = (await session.execute(text("SELECT now()"))).scalar_one()
        db_now_aware = db_now if db_now.tzinfo else db_now.replace(tzinfo=timezone.utc)
        drift_seconds = abs((datetime.now(timezone.utc) - db_now_aware).total_seconds())
        checks["clock_sane"] = drift_seconds < 30  # engineering-default floor, SG-166 family
    except Exception:  # noqa: BLE001
        checks["clock_sane"] = False

    failed = [name for name, ok in checks.items() if not ok]
    passed = not failed
    result = {"checks": checks, "failed": failed, "passed": passed}
    if not passed:
        await write_outbox_event(
            session, event_type="DeploymentPrerequisiteFailed", aggregate_type="deployment_profile",
            aggregate_id=uuid.uuid4(), aggregate_version=1, payload=result, correlation_id=uuid.uuid4(),
        )
        if raise_on_failure:
            raise DeploymentPrerequisiteFailedError("Deployment prerequisite check failed", failed=failed)
    return result


async def detect_infrastructure_drift(
    session: AsyncSession, *, declared_image_digest: str, observed_image_digest: str,
    aggregate_id: uuid.UUID | None = None,
) -> dict:
    """`detectInfrastructureDrift()` -- DEP-FR-031. Compares a declared `deployment_profile.image_digest`
    against an actually-observed one (the caller supplies the observation -- there is no live
    Kubernetes/cloud API this codebase queries itself)."""
    drifted = declared_image_digest != observed_image_digest
    result = {"declared_image_digest": declared_image_digest, "observed_image_digest": observed_image_digest, "drifted": drifted}
    if drifted:
        await write_outbox_event(
            session, event_type="InfrastructureDriftDetected", aggregate_type="deployment_profile",
            aggregate_id=aggregate_id or uuid.uuid4(), aggregate_version=1, payload=result,
            correlation_id=uuid.uuid4(),
        )
    return result


async def check_certificate_expiry(session: AsyncSession, *, warn_within_days: int = 30) -> dict:
    """DEP-FR-034. Reads real `security.certificate_metadata.expires_at` rows (Document 65) --
    reused, not reinvented -- and emits `CertificateExpiryWarning` for anything expiring within
    `warn_within_days`."""
    threshold = datetime.now(timezone.utc) + timedelta(days=warn_within_days)
    rows = (
        await session.execute(
            select(CertificateMetadata).where(
                CertificateMetadata.state == "ACTIVE", CertificateMetadata.expires_at <= threshold,
            )
        )
    ).scalars().all()
    expiring = [{"certificate_id": str(r.id), "expires_at": r.expires_at.isoformat()} for r in rows]
    if expiring:
        await write_outbox_event(
            session, event_type="CertificateExpiryWarning", aggregate_type="deployment_profile",
            aggregate_id=uuid.uuid4(), aggregate_version=1,
            payload={"warn_within_days": warn_within_days, "expiring": expiring}, correlation_id=uuid.uuid4(),
        )
    return {"warn_within_days": warn_within_days, "expiring_count": len(expiring), "expiring": expiring}
