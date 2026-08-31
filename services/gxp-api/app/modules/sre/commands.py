"""Document 78 (SPEC-DATA-010) Mutation Gateway command handlers. No signature (Document 106 has no
SPEC-DATA-010 row). **No HTTP router** -- Document 78 declares 0 owned APIs; these are called by CI/SRE
tooling directly, same "no independent API" shape as Document 68's `release_security_evidence`.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sre.models import CapacityForecast, SloDefinition
from app.mutation.errors import StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version, audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _finalize(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, aggregate_type: str,
    aggregate_id: uuid.UUID, version: int, action: str, actor_user_id: uuid.UUID, reason: str | None,
    old_value: dict | None, new_value: dict, event_type: str, expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value=old_value, new_value=new_value,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, payload=new_value, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type=command_type, aggregate_type=aggregate_type,
        aggregate_id=aggregate_id, expected_version=expected_version, resulting_version=version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=aggregate_id, resulting_version=version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# =================================================================================================
# recordServiceLevelObjective() -- SRE-FR-001/002/007
# =================================================================================================


class RecordServiceLevelObjectiveCommand(CommandEnvelope):
    operation_class: str
    sli_name: str
    p95_target_ms: int
    p99_target_ms: int
    window: str = "steady-state"
    expected_version: int | None = None
    reason: str


async def record_service_level_objective(
    session: AsyncSession, cmd: RecordServiceLevelObjectiveCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.p95_target_ms < 0 or cmd.p99_target_ms < 0:
        raise ValidationFailedError("p95_target_ms/p99_target_ms must be >= 0")
    if cmd.p99_target_ms < cmd.p95_target_ms:
        raise ValidationFailedError("p99_target_ms must be >= p95_target_ms")
    if not cmd.operation_class or not cmd.sli_name or not cmd.reason:
        raise ValidationFailedError("operation_class, sli_name and reason are required")

    row = (
        await session.execute(select(SloDefinition).where(SloDefinition.operation_class == cmd.operation_class))
    ).scalar_one_or_none()
    created = row is None
    old_value = None
    if created:
        row = SloDefinition(
            operation_class=cmd.operation_class, sli_name=cmd.sli_name, p95_target_ms=cmd.p95_target_ms,
            p99_target_ms=cmd.p99_target_ms, window=cmd.window, state="EFFECTIVE", version=1,
        )
        session.add(row)
    else:
        if cmd.expected_version is None or row.version != cmd.expected_version:
            raise StaleVersionError("SLO definition changed since this request was prepared", current_version=row.version)
        old_value = {"p95_target_ms": row.p95_target_ms, "p99_target_ms": row.p99_target_ms}
        row.sli_name = cmd.sli_name
        row.p95_target_ms = cmd.p95_target_ms
        row.p99_target_ms = cmd.p99_target_ms
        row.window = cmd.window
        row.version += 1
    await session.flush()

    new_value = {"operation_class": row.operation_class, "sli_name": row.sli_name,
                 "p95_target_ms": row.p95_target_ms, "p99_target_ms": row.p99_target_ms}
    return await _finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="slo_definition", aggregate_id=row.id,
        version=row.version, action="Created" if created else "Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_value=old_value, new_value=new_value, event_type="ServiceLevelObjectiveDefined",
        expected_version=None if created else cmd.expected_version, command_type="RecordServiceLevelObjective",
    )


# =================================================================================================
# calculateCapacityForecast() -- SRE-FR-005/006/033/034
# =================================================================================================


class RecordCapacityForecastCommand(CommandEnvelope):
    dimension: str
    reference_value: int
    current_value: int | None = None
    growth_rate_pct_bp: int | None = None  # basis points; 1% = 100
    horizon_days: int = 90
    headroom_pct_bp: int | None = None
    expected_version: int | None = None
    reason: str


async def record_capacity_forecast(
    session: AsyncSession, cmd: RecordCapacityForecastCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.reference_value < 0 or cmd.horizon_days <= 0:
        raise ValidationFailedError("reference_value must be >= 0 and horizon_days must be > 0")
    if not cmd.dimension or not cmd.reason:
        raise ValidationFailedError("dimension and reason are required")

    forecasted = None
    if cmd.current_value is not None and cmd.growth_rate_pct_bp is not None:
        # integer basis-points growth over the horizon, expressed monthly-compounded in whole percent
        # steps -- deliberately simple/integer, no float, and never applied to a regulated quantity.
        months = max(1, cmd.horizon_days // 30)
        forecasted = cmd.current_value
        for _ in range(months):
            forecasted = forecasted + (forecasted * cmd.growth_rate_pct_bp) // 10_000

    row = (
        await session.execute(select(CapacityForecast).where(CapacityForecast.dimension == cmd.dimension))
    ).scalar_one_or_none()
    created = row is None
    old_value = None
    if created:
        row = CapacityForecast(
            dimension=cmd.dimension, reference_value=cmd.reference_value, current_value=cmd.current_value,
            growth_rate_pct=cmd.growth_rate_pct_bp, horizon_days=cmd.horizon_days, forecasted_value=forecasted,
            headroom_pct=cmd.headroom_pct_bp, state="EFFECTIVE", version=1,
        )
        session.add(row)
    else:
        if cmd.expected_version is None or row.version != cmd.expected_version:
            raise StaleVersionError("Capacity forecast changed since this request was prepared", current_version=row.version)
        old_value = {"current_value": row.current_value, "forecasted_value": row.forecasted_value}
        row.reference_value = cmd.reference_value
        row.current_value = cmd.current_value
        row.growth_rate_pct = cmd.growth_rate_pct_bp
        row.horizon_days = cmd.horizon_days
        row.forecasted_value = forecasted
        row.headroom_pct = cmd.headroom_pct_bp
        row.version += 1
    await session.flush()

    new_value = {"dimension": row.dimension, "reference_value": row.reference_value,
                 "current_value": row.current_value, "forecasted_value": row.forecasted_value,
                 "horizon_days": row.horizon_days}
    # Document 78 # 9's events table names this event CapacityThresholdForecasted (the function
    # catalogue's own "CapacityForecastGenerated" is the same underlying outcome under a different
    # name -- a spec self-inconsistency; the events table is treated as canonical, same "one real name"
    # resolution event-data-008.json already applied to Document 76's own naming overlap).
    return await _finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="capacity_forecast", aggregate_id=row.id,
        version=row.version, action="Created" if created else "Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_value=old_value, new_value=new_value, event_type="CapacityThresholdForecasted",
        expected_version=None if created else cmd.expected_version, command_type="RecordCapacityForecast",
    )
