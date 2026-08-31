"""Document 78 (SPEC-DATA-010) -- Performance, Capacity, Observability, SLOs & SRE Operations.
Executable evidence for the Document 109 SLO/capacity seed, SLO/forecast management, operational
alerting, performance-regression gating, graceful-degradation verification and DB saturation checks.
"""

import uuid

import pytest
from sqlalchemy import select, text

from app.core.db import SessionLocal
from app.modules.sre import commands as sre
from app.modules.sre import monitor
from app.modules.sre.models import CapacityForecast, SloDefinition
from app.modules.mutation.models import OutboxEvent
from app.mutation.errors import StaleVersionError, ValidationFailedError
from tests.conftest import idem


async def test_document_109_slo_and_capacity_seed_present(db, seeded):
    async with SessionLocal() as s:
        oc1 = (await s.execute(select(SloDefinition).where(SloDefinition.operation_class == "OC-1"))).scalar_one()
        oc3 = (await s.execute(select(SloDefinition).where(SloDefinition.operation_class == "OC-3"))).scalar_one()
        cap = (await s.execute(select(CapacityForecast).where(CapacityForecast.dimension == "regulated_mutations_per_hour_peak"))).scalar_one()
    assert oc1.p95_target_ms == 300 and oc1.p99_target_ms == 800
    assert oc3.p95_target_ms == 1500 and oc3.p99_target_ms == 3000
    assert cap.reference_value == 20_000


async def test_record_slo_create_update_and_validation(db, seeded):
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            with pytest.raises(ValidationFailedError):
                await sre.record_service_level_objective(
                    s, sre.RecordServiceLevelObjectiveCommand(
                        idempotency_key=idem(), operation_class="OC-99", sli_name="x",
                        p95_target_ms=500, p99_target_ms=100, reason="bad: p99 < p95",
                    ), actor,
                )
        async with s.begin():
            r1 = await sre.record_service_level_objective(
                s, sre.RecordServiceLevelObjectiveCommand(
                    idempotency_key=idem(), operation_class="OC-CUSTOM", sli_name="custom probe",
                    p95_target_ms=100, p99_target_ms=300, reason="new capability",
                ), actor,
            )
        async with s.begin():
            with pytest.raises(StaleVersionError):
                await sre.record_service_level_objective(
                    s, sre.RecordServiceLevelObjectiveCommand(
                        idempotency_key=idem(), operation_class="OC-CUSTOM", sli_name="custom probe",
                        p95_target_ms=100, p99_target_ms=300, reason="retry",
                    ), actor,
                )
    assert r1.resulting_version == 1


async def test_record_capacity_forecast_computes_integer_growth(db, seeded):
    actor = seeded["users"]["operator1"].id
    async with SessionLocal() as s:
        async with s.begin():
            receipt = await sre.record_capacity_forecast(
                s, sre.RecordCapacityForecastCommand(
                    idempotency_key=idem(), dimension="custom_dimension", reference_value=1000,
                    current_value=1000, growth_rate_pct_bp=1000, horizon_days=90,  # 10%/month, 3 months
                    reason="Q1 review",
                ), actor,
            )
    async with SessionLocal() as s:
        row = await s.get(CapacityForecast, receipt.aggregate_id)
        assert row.forecasted_value == 1331  # 1000 * 1.1^3, integer basis-points compounding
        events = (await s.execute(select(OutboxEvent.event_type).where(OutboxEvent.aggregate_id == row.id))).scalars().all()
        assert "CapacityThresholdForecasted" in events


async def test_evaluate_operational_alert_breach_and_no_breach(db, seeded):
    async with SessionLocal() as s:
        async with s.begin():
            ok = await monitor.evaluate_operational_alert(s, metric_name="oc1_probe", value_ms=250, p95_target_ms=300, p99_target_ms=800)
            assert ok["breached"] is False
        async with s.begin():
            breach = await monitor.evaluate_operational_alert(s, metric_name="oc1_probe", value_ms=1000, p95_target_ms=300, p99_target_ms=800)
            assert breach["breached"] is True
    async with SessionLocal() as s:
        rows = (await s.execute(select(OutboxEvent.event_type).where(OutboxEvent.event_type == "OperationalAlertRaised"))).scalars().all()
        assert len(rows) >= 1


async def test_evaluate_release_performance_gate_integer_math(db, seeded):
    async with SessionLocal() as s:
        async with s.begin():
            ok = await monitor.evaluate_release_performance_gate(
                s, operation_class="OC-2", baseline_p99_ms=1000, candidate_p99_ms=1050, allowed_regression_pct_bp=1000
            )
            assert ok["regressed"] is False  # +5% within a 10% allowance
        async with s.begin():
            bad = await monitor.evaluate_release_performance_gate(
                s, operation_class="OC-2", baseline_p99_ms=1000, candidate_p99_ms=1300, allowed_regression_pct_bp=1000
            )
            assert bad["regressed"] is True  # +30% exceeds a 10% allowance
    async with SessionLocal() as s:
        rows = (await s.execute(select(OutboxEvent.event_type).where(OutboxEvent.event_type == "PerformanceRegressionDetected"))).scalars().all()
        assert len(rows) >= 1


async def test_verify_graceful_degradation_flags_violations(db, seeded):
    async with SessionLocal() as s:
        async with s.begin():
            clean = await monitor.verify_graceful_degradation(
                s, failed_dependency="search_index", capability_results={"batch_execution": True, "search": False},
                must_stop_capabilities={"search"},
            )
            assert clean["verified"] is True
        async with s.begin():
            bad = await monitor.verify_graceful_degradation(
                s, failed_dependency="postgres_gxp", capability_results={"batch_execution": True},
                must_stop_capabilities={"batch_execution"},  # should have stopped but didn't
            )
            assert bad["verified"] is False and bad["violations"]
    async with SessionLocal() as s:
        rows = (await s.execute(select(OutboxEvent.event_type).where(OutboxEvent.event_type == "GracefulDegradationVerified"))).scalars().all()
        assert len(rows) >= 2


async def test_check_database_saturation_real_pg_stat(db, seeded):
    """Reads real pg_stat_activity/max_connections -- a live test DB is never saturated at 80%+ during
    a test run, so this exercises the real query path and asserts a sane, non-saturated result."""
    async with SessionLocal() as s:
        result = await monitor.check_database_saturation(s)
    assert result["max_connections"] > 0
    assert 0 <= result["saturation_pct_bp"] < 10_000
    assert result["saturated"] is False


async def test_generic_delete_denied_at_db_privilege_level(db, seeded):
    with pytest.raises(Exception) as exc:
        await db.execute(text("DELETE FROM sre.slo_definition"))
        await db.commit()
    assert "permission denied" in str(exc.value).lower() or "InsufficientPrivilege" in type(exc.value).__name__
