"""Document 76 (SPEC-DATA-008) recovery orchestration library -- DR-FR-018/019/020/025/026.

These deliberately reuse the mechanisms Documents 69/72/75 already built rather than re-deriving them:
evidence reconciliation is `evidence.verify_evidence_integrity()` (Document 72), derived-store rebuild
is `dataops.rebuild_projection()` / `readmodels.rebuild_search_index()` / `refresh_read_model()`
(Documents 69/75). Document 76's own job is *sequencing and gating* recovery across those, not
reinventing per-store rebuild logic (AG-05 extended to recovery tooling).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.disaster_recovery.models import RecoveryObjectiveProfile
from app.modules.disaster_recovery.signals import emit_dr_signal
from app.modules.evidence.commands import VerifyEvidenceIntegrityCommand, verify_evidence_integrity
from app.mutation.errors import EvidenceMissingError, RecoveryValidationFailedError
from app.mutation.gateway import write_audit_event, write_outbox_event


async def verify_backup_freshness(session: AsyncSession, *, component: str, last_backup_completed_at: datetime | None) -> dict:
    """`verifyBackupFreshness()` -- DR-FR-002/015. Compares the component's most recent backup age
    against its `recovery_objective_profile.rpo_seconds`. Emits `BackupRPOAtRisk` (best-effort) when
    at risk rather than raising -- this is a monitoring read, not a gate."""
    objective = (
        await session.execute(select(RecoveryObjectiveProfile).where(RecoveryObjectiveProfile.component == component))
    ).scalar_one_or_none()
    if objective is None:
        return {"component": component, "objective_defined": False, "at_risk": None}

    if last_backup_completed_at is None:
        at_risk = objective.rpo_seconds is not None  # no backup at all and an RPO commitment exists
        age_seconds = None
    else:
        completed = last_backup_completed_at if last_backup_completed_at.tzinfo else last_backup_completed_at.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - completed).total_seconds()
        at_risk = objective.rpo_seconds is not None and age_seconds > objective.rpo_seconds

    result = {
        "component": component, "objective_defined": True, "tier": objective.tier,
        "rpo_seconds": objective.rpo_seconds, "backup_age_seconds": age_seconds, "at_risk": at_risk,
    }
    if at_risk:
        await emit_dr_signal("BackupRPOAtRisk", result)
    return result


async def reconcile_evidence_after_restore(
    session: AsyncSession, *, owner_type: str, owner_id: uuid.UUID, actor_user_id: uuid.UUID
) -> dict:
    """`reconcileEvidenceAfterRestore()` -- DR-FR-019. Thin wrapper over
    `evidence.verify_evidence_integrity()` scoped to the restored owner; on a mismatch, records
    `EvidenceRestoreMismatch` in addition to the underlying `EvidenceMissing`/`EvidenceHashMismatch`
    events that command already emits."""
    try:
        return await verify_evidence_integrity(
            session,
            VerifyEvidenceIntegrityCommand(
                idempotency_key=str(uuid.uuid4()), owner_type=owner_type, owner_id=owner_id,
                mode="full", reason="post-restore reconciliation (Document 76 DR-FR-019)",
            ),
            actor_user_id,
        )
    except EvidenceMissingError as exc:
        correlation_id = uuid.uuid4()
        await write_outbox_event(
            session, event_type="EvidenceRestoreMismatch", aggregate_type="disaster_recovery",
            aggregate_id=uuid.uuid4(), aggregate_version=1,
            payload={"owner_type": owner_type, "owner_id": str(owner_id), "detail": exc.details},
            correlation_id=correlation_id,
        )
        raise


async def validate_recovered_platform(
    session: AsyncSession, *, checks: dict[str, bool], actor_user_id: uuid.UUID
) -> dict:
    """`validateRecoveredPlatform()` -- DR-FR-025. `checks` is the smoke/integrity/security/GxP check
    result set the recovery runbook actually ran (e.g. {"db_reachable": True, "audit_chain_intact":
    True, "signature_policy_seeded": True}); this function does not invent or run checks itself, it
    gates on what was reported. All-true -> PlatformRecoveryValidated; any false -> raises
    RECOVERY_VALIDATION_FAILED and records why, never silently declaring the platform healthy."""
    if not checks:
        raise RecoveryValidationFailedError("No recovery validation checks were reported")
    failed = [name for name, ok in checks.items() if not ok]
    healthy = not failed

    correlation_id = uuid.uuid4()
    await write_outbox_event(
        session,
        event_type="PlatformRecoveryValidated" if healthy else "RecoveryValidationFailed",
        aggregate_type="disaster_recovery", aggregate_id=uuid.uuid4(), aggregate_version=1,
        payload={"checks": checks, "failed": failed, "healthy": healthy}, correlation_id=correlation_id,
    )
    if not healthy:
        raise RecoveryValidationFailedError(
            "Recovered environment failed mandatory checks", failed_checks=failed
        )
    return {"healthy": True, "checks": checks}


async def record_data_loss_assessment(
    session: AsyncSession, *, restore_point: datetime, expected_latest: datetime,
    missing_scope: str, actor_user_id: uuid.UUID, reason: str,
) -> dict:
    """`recordDataLossAssessment()` -- DR-FR-026. If a restore lands before `expected_latest`, records
    the gap as a real audited assessment (aggregate_type disaster_recovery) rather than silently
    accepting the loss. Never computed from a guess -- both timestamps are the caller's own measured
    values (the restore's actual recovery point and the last known-committed authoritative time)."""
    gap_seconds = max(0, int((expected_latest - restore_point).total_seconds()))
    correlation_id = uuid.uuid4()
    aggregate_id = uuid.uuid4()
    await write_audit_event(
        session, site_id=None, aggregate_type="disaster_recovery", aggregate_id=aggregate_id,
        aggregate_version=1, action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason,
        new_value={"restore_point": restore_point.isoformat(), "expected_latest": expected_latest.isoformat(),
                   "gap_seconds": gap_seconds, "missing_scope": missing_scope},
    )
    await write_outbox_event(
        session, event_type="RecoveryDataLossDetected", aggregate_type="disaster_recovery",
        aggregate_id=aggregate_id, aggregate_version=1,
        payload={"restore_point": restore_point.isoformat(), "expected_latest": expected_latest.isoformat(),
                 "gap_seconds": gap_seconds, "missing_scope": missing_scope},
        correlation_id=correlation_id,
    )
    return {"gap_seconds": gap_seconds, "missing_scope": missing_scope, "assessment_id": str(aggregate_id)}
