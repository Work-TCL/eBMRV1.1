"""Shared security-telemetry emitter for WP-10 (Documents 64-68).

MUT-FR-031 / Document 67 # 14: security-monitoring events (`APIAccessDenied`, `RateLimitTriggered`,
`SSRFBlocked`, `MaliciousUploadDetected`, `WebhookReplayDetected`, `DeprecatedAPIUsed`,
`SecretAccessDenied`, `CryptoHealthFailed`, `KeyAccessAnomaly`, `ForbiddenNetworkPathDetected`,
`TenantScopeMismatchDetected`, `WorkloadHardeningFailed`, `UnexpectedPublicExposureDetected`) go to the
transactional outbox, kept distinct from the GxP audit ledger.

The catch: these events fire on a *rejection* path -- the security control refused something and the
caller's transaction is about to roll back. So the event MUST be written in its own committed
transaction, exactly like `app/core/security.py::get_current_actor` opens its own short-lived
`SessionLocal()` to avoid the route handler's autobegin. And it is **best-effort**: a telemetry write
failure is logged, never raised -- it must never mask or block the security decision (fail-closed on the
control, fail-open on the telemetry).
"""

import logging
import uuid

from app.core.db import SessionLocal
from app.mutation.gateway import write_outbox_event

logger = logging.getLogger("gxp_api.security_telemetry")


async def record_security_event(event_type: str, payload: dict) -> None:
    try:
        async with SessionLocal() as session:
            async with session.begin():
                await write_outbox_event(
                    session,
                    event_type=event_type,
                    aggregate_type="security_event",
                    aggregate_id=uuid.uuid4(),
                    aggregate_version=1,
                    payload=payload,
                    correlation_id=uuid.uuid4(),
                )
    except Exception:  # noqa: BLE001 - telemetry must never break the security decision
        logger.exception("failed to record security telemetry event_type=%s", event_type)
