"""Document 78 (SPEC-DATA-010) alerting / gate / degradation-verification library -- SRE-FR-018/022/
023/028/032/035.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mutation.gateway import write_outbox_event


async def evaluate_operational_alert(
    session: AsyncSession, *, metric_name: str, value_ms: int, p95_target_ms: int, p99_target_ms: int,
    percentile: str = "p99",
) -> dict:
    """`evaluateOperationalAlert()` -- SRE-FR-007/028. Compares an already-measured latency value
    against an `slo_definition` target; raises `OperationalAlertRaised` (transactional, since this is
    a real recorded operational decision, not a background poll) when the breached percentile's target
    is exceeded. Does not measure anything itself -- callers supply the real observed value."""
    target = p99_target_ms if percentile == "p99" else p95_target_ms
    breached = value_ms > target
    result = {"metric_name": metric_name, "percentile": percentile, "value_ms": value_ms,
              "target_ms": target, "breached": breached}
    if breached:
        await write_outbox_event(
            session, event_type="OperationalAlertRaised", aggregate_type="sre", aggregate_id=uuid.uuid4(),
            aggregate_version=1, payload=result, correlation_id=uuid.uuid4(),
        )
    return result


async def evaluate_release_performance_gate(
    session: AsyncSession, *, operation_class: str, baseline_p99_ms: int, candidate_p99_ms: int,
    allowed_regression_pct_bp: int,
) -> dict:
    """`evaluateReleasePerformanceGate()` -- SRE-FR-035. Compares a candidate build's measured p99
    against the baseline; a regression beyond `allowed_regression_pct_bp` (basis points, integer) fails
    the gate and emits `PerformanceRegressionDetected`. Never a float comparison."""
    if baseline_p99_ms <= 0:
        raise ValueError("baseline_p99_ms must be > 0")
    delta_bp = ((candidate_p99_ms - baseline_p99_ms) * 10_000) // baseline_p99_ms
    regressed = delta_bp > allowed_regression_pct_bp
    result = {
        "operation_class": operation_class, "baseline_p99_ms": baseline_p99_ms,
        "candidate_p99_ms": candidate_p99_ms, "delta_pct_bp": delta_bp,
        "allowed_regression_pct_bp": allowed_regression_pct_bp, "regressed": regressed,
    }
    if regressed:
        await write_outbox_event(
            session, event_type="PerformanceRegressionDetected", aggregate_type="sre",
            aggregate_id=uuid.uuid4(), aggregate_version=1, payload=result, correlation_id=uuid.uuid4(),
        )
    return result


async def verify_graceful_degradation(
    session: AsyncSession, *, failed_dependency: str, capability_results: dict[str, bool],
    must_stop_capabilities: set[str],
) -> dict:
    """`verifyGracefulDegradation()` -- SRE-FR-022. `capability_results` is what the resilience test
    actually observed (capability -> still_available). Verifies every capability in
    `must_stop_capabilities` (the critical GxP execution dependency matrix for this failure) actually
    stopped, and every capability NOT in that set stayed available -- i.e. derived surfaces degraded
    independently without taking down regulated execution, and regulated execution correctly refused
    to continue on a dependency it cannot safely operate without."""
    violations = []
    for cap in must_stop_capabilities:
        if capability_results.get(cap, False):
            violations.append(f"{cap} should have stopped on {failed_dependency} failure but stayed available")
    for cap, available in capability_results.items():
        if cap not in must_stop_capabilities and not available:
            violations.append(f"{cap} should have stayed available on {failed_dependency} failure but stopped")

    verified = not violations
    result = {"failed_dependency": failed_dependency, "violations": violations, "verified": verified}
    await write_outbox_event(
        session, event_type="GracefulDegradationVerified", aggregate_type="sre", aggregate_id=uuid.uuid4(),
        aggregate_version=1, payload=result, correlation_id=uuid.uuid4(),
    )
    return result


async def check_database_saturation(
    session: AsyncSession, *, max_connections_threshold_pct_bp: int = 8_000  # 80% default floor, SG-166 family
) -> dict:
    """SRE-FR-013. Reads real `pg_stat_activity`/`max_connections` state (not a synthetic metric) and
    emits `DatabaseSaturationDetected` if active-connection saturation exceeds the threshold."""
    row = (
        await session.execute(
            text(
                "SELECT (SELECT count(*) FROM pg_stat_activity) AS active, "
                "(SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_conn"
            )
        )
    ).one()
    saturation_bp = (row.active * 10_000) // row.max_conn if row.max_conn else 0
    saturated = saturation_bp > max_connections_threshold_pct_bp
    result = {"active_connections": row.active, "max_connections": row.max_conn,
              "saturation_pct_bp": saturation_bp, "saturated": saturated}
    if saturated:
        await write_outbox_event(
            session, event_type="DatabaseSaturationDetected", aggregate_type="sre", aggregate_id=uuid.uuid4(),
            aggregate_version=1, payload=result, correlation_id=uuid.uuid4(),
        )
    return result
