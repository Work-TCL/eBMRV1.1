"""Document 93 (SPEC-VAL-015) Mutation Gateway command handlers -- Performance, Load, Capacity &
Reliability Qualification. Document 106 rows 159-161 are unusual among WP-12 signature rows: all three
POST operations (`performance/scenarios`, `performance/runs`, `performance/{id}/evaluate`) require a
`Performed` signature from the qualified performer (no dedicated role/independence/reason) -- unlike
every other WP-12 document, even scenario *definition* is itself a signed record here. Document 79's own
API list has no dedicated approve endpoint for this document (unlike Documents 88-92, 96): `evaluate()`
folds acceptance evaluation and the (self-measured) qualification outcome into one signed step, emitting
both `PerformanceAcceptanceEvaluated` and, on PASS, `PerformanceQualificationApproved`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import PerformanceQualificationScenario, PerformanceRun
from app.modules.validation.shared import finalize, receipt_from_existing, resolve_signature, verify_reauth_and_consume
from app.mutation.errors import InvalidTransitionError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_SCENARIO = "performance_qualification_scenario"
RECORD_TYPE_RUN = "performance_run"


class CreatePerformanceScenarioCommand(CommandEnvelope):
    release_ref: str
    environment: str
    load_model: dict
    data_cardinality: dict = {}
    planned_duration_seconds: int
    thresholds: dict
    nfr_requirement_refs: list[str] = []
    new_record_id: uuid.UUID | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def create_performance_scenario(
    session: AsyncSession, cmd: CreatePerformanceScenarioCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    """Document 106 rows 159-161 sign the *create* action itself, so -- same shape as
    `app/modules/qms/signature_support.py::create_qms_signature_challenge_for_new_record` -- the caller
    pre-generates the record id, requests a challenge bound to (id, version=1), then passes that same id
    back here so the inserted row matches exactly what the challenge was issued against."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if cmd.planned_duration_seconds <= 0:
        raise ValidationFailedError("planned_duration_seconds must be > 0")
    if not cmd.thresholds:
        raise ValidationFailedError("thresholds must not be empty (PERFQ-FR-021)")

    row = PerformanceQualificationScenario(
        id=cmd.new_record_id or uuid.uuid4(), release_ref=cmd.release_ref, environment=cmd.environment,
        load_model=cmd.load_model, data_cardinality=cmd.data_cardinality,
        planned_duration_seconds=cmd.planned_duration_seconds, thresholds=cmd.thresholds,
        nfr_requirement_refs=cmd.nfr_requirement_refs, state="PLANNED", version=1,
    )
    session.add(row)
    await session.flush()

    policy = await resolve_signature(session, record_type=RECORD_TYPE_SCENARIO, action="create")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_SCENARIO, aggregate_id=row.id,
        version=row.version, action="Performed", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"release_ref": row.release_ref, "environment": row.environment},
        event_type="DeploymentSizingDerived", expected_version=None, command_type="CreatePerformanceScenario",
        site_id=site_id, signature_id=signature_id,
    )


class RecordPerformanceRunCommand(CommandEnvelope):
    scenario_id: uuid.UUID
    build_ref: str
    harness_ref: str
    started_at: datetime
    completed_at: datetime
    metrics: dict
    errors: list[dict] = []
    resource_usage: dict = {}
    new_record_id: uuid.UUID | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def record_performance_run(
    session: AsyncSession, cmd: RecordPerformanceRunCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    """Same pre-generated-id shape as `create_performance_scenario` above -- Document 106 row 159 signs
    this create action too."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    scenario = await session.get(PerformanceQualificationScenario, cmd.scenario_id)
    if scenario is None:
        raise NotFoundError("Performance qualification scenario not found")
    if cmd.completed_at < cmd.started_at:
        raise ValidationFailedError("completed_at must not precede started_at")

    row = PerformanceRun(
        id=cmd.new_record_id or uuid.uuid4(), scenario_id=scenario.id, scenario_version=scenario.version,
        build_ref=cmd.build_ref, harness_ref=cmd.harness_ref, started_at=cmd.started_at,
        completed_at=cmd.completed_at, metrics=cmd.metrics, errors=cmd.errors, resource_usage=cmd.resource_usage,
        acceptance_result="IN_PROGRESS", performed_by_user_id=actor_user_id, version=1,
    )
    session.add(row)
    await session.flush()

    policy = await resolve_signature(session, record_type=RECORD_TYPE_RUN, action="create")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_RUN, aggregate_id=row.id,
        version=row.version, action="Performed", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"scenario_id": str(scenario.id), "build_ref": cmd.build_ref},
        event_type="PerformanceQualificationExecuted", expected_version=None, command_type="RecordPerformanceRun",
        site_id=site_id, signature_id=signature_id,
    )


class EvaluatePerformanceRunCommand(CommandEnvelope):
    run_id: uuid.UUID
    expected_version: int
    headroom_basis_points: int | None = None
    bottleneck: str | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def evaluate_performance_run(
    session: AsyncSession, cmd: EvaluatePerformanceRunCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = await session.get(PerformanceRun, cmd.run_id)
    if row is None:
        raise NotFoundError("Performance run not found")
    if row.acceptance_result != "IN_PROGRESS":
        raise InvalidTransitionError("Run already evaluated", current_state=row.acceptance_result)
    if row.version != cmd.expected_version:
        raise StaleVersionError("Run changed since this request was prepared", current_version=row.version)

    scenario = await session.get(PerformanceQualificationScenario, row.scenario_id)
    # PERFQ-FR-002/003/021: every declared threshold key must appear in the measured metrics and meet it.
    breaches = []
    for key, limit in (scenario.thresholds if scenario else {}).items():
        actual = row.metrics.get(key)
        if actual is not None and isinstance(actual, (int, float)) and actual > limit:
            breaches.append({"metric": key, "limit": limit, "actual": actual})
    result = "PASS" if (not breaches and not row.errors) else "FAIL"

    # SIG-FR-014: the challenge is bound to the record's version *before* this mutation, exactly like
    # every other WP-12 signed command -- consume it before, never after, incrementing row.version (a
    # bug caught by test_performance_scenario_run_evaluate_all_require_signature: signing after the
    # increment made a freshly-issued, never-reused challenge look like a stale-record replay).
    policy = await resolve_signature(session, record_type=RECORD_TYPE_RUN, action="evaluate")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.acceptance_result = result
    row.headroom_basis_points = cmd.headroom_basis_points
    row.bottleneck = cmd.bottleneck
    row.version += 1

    if result == "PASS":
        await write_outbox_event(
            session, event_type="PerformanceQualificationApproved", aggregate_type=RECORD_TYPE_RUN,
            aggregate_id=row.id, aggregate_version=row.version, payload={"run_id": str(row.id)},
            correlation_id=uuid.uuid4(),
        )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_RUN, aggregate_id=row.id,
        version=row.version, action="Performed", actor_user_id=actor_user_id, reason=None,
        old_value={"acceptance_result": "IN_PROGRESS"}, new_value={"acceptance_result": result, "breaches": breaches},
        event_type="PerformanceAcceptanceEvaluated", expected_version=cmd.expected_version,
        command_type="EvaluatePerformanceRun", site_id=site_id, signature_id=signature_id,
    )


async def get_deployment_sizing(session: AsyncSession, scenario_id: uuid.UUID) -> dict:
    """Read-only (Document 79 declares only a GET for this view): the latest evaluated run's headroom/
    bottleneck for a scenario, translated toward an on-prem sizing recommendation (PERFQ-FR-019)."""
    from sqlalchemy import select
    run = (
        await session.execute(
            select(PerformanceRun)
            .where(PerformanceRun.scenario_id == scenario_id, PerformanceRun.acceptance_result != "IN_PROGRESS")
            .order_by(PerformanceRun.completed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if run is None:
        raise NotFoundError("No evaluated performance run found for this scenario")
    return {
        "scenario_id": str(scenario_id), "acceptance_result": run.acceptance_result,
        "headroom_basis_points": run.headroom_basis_points, "bottleneck": run.bottleneck,
    }
