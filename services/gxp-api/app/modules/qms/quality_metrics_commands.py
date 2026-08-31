"""Document 37 (SPEC-QMS-012) — Quality Metrics, Trending & Effectiveness Checks command handlers. See
quality_metrics_models.py's module docstring for the state-machine fold-in rationale and the deferred
scope (SG-107/SG-108).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.qms.quality_metrics_models import (
    EFFECTIVENESS_RESULTS,
    EffectivenessCheck,
    QualityMetricDefinition,
    QualityMetricSnapshot,
)
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    EffectivenessCriterionRequiredError,
    EffectivenessInconclusiveError,
    InvalidTransitionError,
    ManagementPackageFrozenError,
    MetricDefinitionNotReleasedError,
    MetricSourceIncompleteError,
    MissingSignatureError,
    NotFoundError,
    SnapshotStaleError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
        audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _load_definition_for_update(session: AsyncSession, definition_id: uuid.UUID, expected_version: int | None = None) -> QualityMetricDefinition:
    result = await session.execute(select(QualityMetricDefinition).where(QualityMetricDefinition.id == definition_id).with_for_update())
    definition = result.scalar_one_or_none()
    if definition is None:
        raise NotFoundError("Quality metric definition not found")
    if expected_version is not None and definition.version != expected_version:
        raise StaleVersionError(
            "Quality metric definition was modified by another actor since it was read",
            expected_version=expected_version, current_version=definition.version,
        )
    return definition


def _record_hash(record) -> str:
    return sha256_hex({"id": str(record.id), "version": record.version})


async def _resolve_signature(
    session: AsyncSession, *, record_type: str, action: str, actor_user_id: uuid.UUID, record,
    challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type=record_type, action=action)
    if not policy.signature_required:
        return None
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"{record_type} '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=record.version, record_hash=_record_hash(record),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


async def _write_definition_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, definition: QualityMetricDefinition, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    signature_id: uuid.UUID | None, expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=definition.site_id, aggregate_type="quality_metric_definition", aggregate_id=definition.id,
        aggregate_version=definition.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": definition.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="quality_metric_definition", aggregate_id=definition.id,
        aggregate_version=definition.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=definition.site_id, command_type=command_type, aggregate_type="quality_metric_definition",
        aggregate_id=definition.id, expected_version=expected_version, resulting_version=definition.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=definition.id, resulting_version=definition.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create metric definition — MET-FR-001/013
# ---------------------------------------------------------------------------


class CreateMetricDefinitionCommand(CommandEnvelope):
    site_id: uuid.UUID
    metric_code: str
    owner_subject_id: uuid.UUID
    source_model_id: str
    numerator_definition: dict
    frequency: str
    denominator_definition: dict | None = None
    formula_rule_id: uuid.UUID | None = None
    scope_dimensions: dict | None = None
    threshold_rule_ids: list[uuid.UUID] | None = None


async def create_metric_definition(session: AsyncSession, cmd: CreateMetricDefinitionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.metric_code.strip() or not cmd.numerator_definition or not cmd.frequency.strip():
        raise ValidationFailedError("metric_code, numerator_definition and frequency are required")

    prior_max = (
        await session.execute(
            select(QualityMetricDefinition.version_no)
            .where(QualityMetricDefinition.metric_code == cmd.metric_code)
            .order_by(QualityMetricDefinition.version_no.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    version_no = (prior_max or 0) + 1

    definition = QualityMetricDefinition(
        site_id=cmd.site_id, metric_code=cmd.metric_code, version_no=version_no, owner_subject_id=cmd.owner_subject_id,
        source_model_id=cmd.source_model_id, numerator_definition=cmd.numerator_definition,
        denominator_definition=cmd.denominator_definition, formula_rule_id=cmd.formula_rule_id,
        scope_dimensions=cmd.scope_dimensions, frequency=cmd.frequency,
        threshold_rule_ids=[str(t) for t in cmd.threshold_rule_ids] if cmd.threshold_rule_ids else None,
        state="DRAFT",
    )
    session.add(definition)
    await session.flush()

    return await _write_definition_receipt(
        session, cmd=cmd, payload_hash=payload_hash, definition=definition, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="DRAFT", event_type="QualityMetricCalculated",
        event_payload={"id": str(definition.id), "metric_code": definition.metric_code, "version_no": definition.version_no},
        signature_id=None, expected_version=None, command_type="CreateMetricDefinition",
    )


# ---------------------------------------------------------------------------
# Release metric definition — MET-FR-002 (signature: Document 106 row 106)
# ---------------------------------------------------------------------------


class ReleaseMetricDefinitionCommand(CommandEnvelope):
    definition_id: uuid.UUID
    expected_version: int
    effective_from: datetime
    effective_to: datetime | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def release_metric_definition(session: AsyncSession, cmd: ReleaseMetricDefinitionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    definition = await _load_definition_for_update(session, cmd.definition_id, cmd.expected_version)
    if definition.state != "DRAFT":
        raise InvalidTransitionError("Illegal metric definition transition", current_state=definition.state, requested="RELEASED")

    signature_id = await _resolve_signature(
        session, record_type="quality_metric_definition", action="release", actor_user_id=actor_user_id, record=definition,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    # MET-FR-002: supersede the prior released version of this metric_code, never edit it.
    prior_released = (
        await session.execute(
            select(QualityMetricDefinition).where(
                QualityMetricDefinition.metric_code == definition.metric_code,
                QualityMetricDefinition.state == "RELEASED",
                QualityMetricDefinition.id != definition.id,
            )
        )
    ).scalar_one_or_none()

    old_state = definition.state
    definition.effective_from = cmd.effective_from
    definition.effective_to = cmd.effective_to
    definition.state = "RELEASED"
    definition.version += 1
    await session.flush()

    receipt = await _write_definition_receipt(
        session, cmd=cmd, payload_hash=payload_hash, definition=definition, action="Released", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="QualityMetricCalculated",
        event_payload={"id": str(definition.id), "metric_code": definition.metric_code, "version_no": definition.version_no},
        signature_id=signature_id, expected_version=cmd.expected_version, command_type="ReleaseMetricDefinition",
    )
    if prior_released is not None:
        prior_old_state = prior_released.state
        prior_released.state = "SUPERSEDED"
        prior_released.version += 1
        await write_audit_event(
            session, site_id=prior_released.site_id, aggregate_type="quality_metric_definition", aggregate_id=prior_released.id,
            aggregate_version=prior_released.version, action="Changed", actor_id=actor_user_id, correlation_id=receipt.correlation_id,
            reason=None, old_value={"state": prior_old_state}, new_value={"state": prior_released.state}, signature_id=None,
        )
        await write_outbox_event(
            session, event_type="QualityMetricCalculated", aggregate_type="quality_metric_definition", aggregate_id=prior_released.id,
            aggregate_version=prior_released.version, payload={"id": str(prior_released.id), "state": "SUPERSEDED"},
            correlation_id=receipt.correlation_id,
        )
    return receipt


# ---------------------------------------------------------------------------
# Calculate snapshot — MET-FR-012/014/017/023/024
# ---------------------------------------------------------------------------


class CalculateSnapshotCommand(CommandEnvelope):
    site_id: uuid.UUID
    metric_definition_id: uuid.UUID
    period_start: datetime
    period_end: datetime
    result: dict
    scope: dict | None = None
    threshold_exceeded: bool = False


async def calculate_snapshot(session: AsyncSession, cmd: CalculateSnapshotCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    definition = await session.get(QualityMetricDefinition, cmd.metric_definition_id)
    if definition is None:
        raise NotFoundError("Quality metric definition not found")
    if definition.state != "RELEASED":
        raise MetricDefinitionNotReleasedError("Metric definition must be released before it can be calculated", current_state=definition.state)
    if not cmd.result:
        raise MetricSourceIncompleteError("result must not be empty")

    snapshot = QualityMetricSnapshot(
        site_id=cmd.site_id, metric_definition_id=definition.id, period_start=cmd.period_start, period_end=cmd.period_end,
        scope=cmd.scope, source_cutoff=datetime.now(timezone.utc), result=cmd.result, formula_version=str(definition.version_no),
        threshold_exceeded=cmd.threshold_exceeded, state="COMPLETE",
    )
    session.add(snapshot)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=snapshot.site_id, aggregate_type="quality_metric_snapshot", aggregate_id=snapshot.id,
        aggregate_version=snapshot.version, action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=None, old_value={"state": "COMPLETE"}, new_value={"state": snapshot.state}, signature_id=None,
    )
    await write_outbox_event(
        session, event_type="QualityMetricCalculated", aggregate_type="quality_metric_snapshot", aggregate_id=snapshot.id,
        aggregate_version=snapshot.version, payload={"id": str(snapshot.id), "metric_definition_id": str(definition.id)},
        correlation_id=correlation_id,
    )
    if cmd.threshold_exceeded:
        await write_outbox_event(
            session, event_type="QualityTrendThresholdExceeded", aggregate_type="quality_metric_snapshot", aggregate_id=snapshot.id,
            aggregate_version=snapshot.version, payload={"id": str(snapshot.id)}, correlation_id=correlation_id,
        )
        await write_outbox_event(
            session, event_type="QualitySignalAssessmentOpened", aggregate_type="quality_metric_snapshot", aggregate_id=snapshot.id,
            aggregate_version=snapshot.version, payload={"id": str(snapshot.id)}, correlation_id=correlation_id,
        )
    receipt = await record_command_receipt(
        session, site_id=snapshot.site_id, command_type="CalculateSnapshot", aggregate_type="quality_metric_snapshot",
        aggregate_id=snapshot.id, expected_version=None, resulting_version=snapshot.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=snapshot.id, resulting_version=snapshot.version,
        audit_event_id=audit_event.id, signature_id=None, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Management review package — MET-FR-016/023 (signature: Document 106 row 107)
# ---------------------------------------------------------------------------


class FreezeManagementReviewPackageCommand(CommandEnvelope):
    site_id: uuid.UUID
    snapshot_ids: list[uuid.UUID]
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def freeze_management_review_package(session: AsyncSession, cmd: FreezeManagementReviewPackageCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.snapshot_ids:
        raise ValidationFailedError("snapshot_ids must name at least one snapshot")

    snapshots = []
    for snapshot_id in cmd.snapshot_ids:
        snapshot = (
            await session.execute(select(QualityMetricSnapshot).where(QualityMetricSnapshot.id == snapshot_id).with_for_update())
        ).scalar_one_or_none()
        if snapshot is None:
            raise NotFoundError("Quality metric snapshot not found", snapshot_id=str(snapshot_id))
        if snapshot.state == "FROZEN":
            raise ManagementPackageFrozenError("Snapshot is already part of a frozen management review package", snapshot_id=str(snapshot_id))
        if snapshot.state != "COMPLETE":
            raise InvalidTransitionError("Illegal snapshot transition", current_state=snapshot.state, requested="FROZEN")
        definition = await session.get(QualityMetricDefinition, snapshot.metric_definition_id)
        if definition is not None and definition.state == "SUPERSEDED":
            raise SnapshotStaleError("Snapshot's metric definition has been superseded by a newer released version", snapshot_id=str(snapshot_id))
        snapshots.append(snapshot)

    # Resolve the signature against the first snapshot (the package as a whole is one signed decision).
    signature_id = await _resolve_signature(
        session, record_type="quality_metric_snapshot", action="management_review", actor_user_id=actor_user_id, record=snapshots[0],
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    review_package_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    first_audit_event = None
    for snapshot in snapshots:
        old_state = snapshot.state
        snapshot.review_package_id = review_package_id
        snapshot.state = "FROZEN"
        snapshot.version += 1
        audit_event = await write_audit_event(
            session, site_id=snapshot.site_id, aggregate_type="quality_metric_snapshot", aggregate_id=snapshot.id,
            aggregate_version=snapshot.version, action="Closed", actor_id=actor_user_id, correlation_id=correlation_id,
            reason=None, old_value={"state": old_state}, new_value={"state": snapshot.state}, signature_id=signature_id,
        )
        if first_audit_event is None:
            first_audit_event = audit_event
        await write_outbox_event(
            session, event_type="ManagementReviewPackageFrozen", aggregate_type="quality_metric_snapshot", aggregate_id=snapshot.id,
            aggregate_version=snapshot.version, payload={"id": str(snapshot.id), "review_package_id": str(review_package_id)},
            correlation_id=correlation_id,
        )

    # record_command_receipt() flushes internally, which is what actually assigns .id to the audit_event
    # rows added above -- read first_audit_event.id only after this call returns, never before.
    receipt = await record_command_receipt(
        session, site_id=cmd.site_id, command_type="FreezeManagementReviewPackage", aggregate_type="quality_metric_snapshot",
        aggregate_id=review_package_id, expected_version=None, resulting_version=len(snapshots),
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=review_package_id, resulting_version=len(snapshots),
        audit_event_id=first_audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Effectiveness checks — MET-FR-018/019
# ---------------------------------------------------------------------------


class CreateEffectivenessCheckCommand(CommandEnvelope):
    site_id: uuid.UUID
    source_module: str
    source_record_id: uuid.UUID
    criterion: str
    observation_period_start: datetime
    observation_period_end: datetime
    metric_definition_id: uuid.UUID | None = None
    due_date: datetime | None = None


async def create_effectiveness_check(session: AsyncSession, cmd: CreateEffectivenessCheckCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.criterion.strip():
        raise EffectivenessCriterionRequiredError("criterion is required")
    if not cmd.source_module.strip():
        raise ValidationFailedError("source_module is required")

    check = EffectivenessCheck(
        site_id=cmd.site_id, source_module=cmd.source_module, source_record_id=cmd.source_record_id,
        criterion=cmd.criterion, metric_definition_id=cmd.metric_definition_id,
        observation_period_start=cmd.observation_period_start, observation_period_end=cmd.observation_period_end,
        due_date=cmd.due_date, state="OBSERVATION",
    )
    session.add(check)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=check.site_id, aggregate_type="effectiveness_check", aggregate_id=check.id,
        aggregate_version=check.version, action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=None, old_value={"state": "OBSERVATION"}, new_value={"state": check.state}, signature_id=None,
    )
    await write_outbox_event(
        session, event_type="EffectivenessCheckDue", aggregate_type="effectiveness_check", aggregate_id=check.id,
        aggregate_version=check.version, payload={"id": str(check.id), "source_module": check.source_module},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=check.site_id, command_type="CreateEffectivenessCheck", aggregate_type="effectiveness_check",
        aggregate_id=check.id, expected_version=None, resulting_version=check.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=check.id, resulting_version=check.version,
        audit_event_id=audit_event.id, signature_id=None, correlation_id=correlation_id,
    )


class EvaluateEffectivenessCheckCommand(CommandEnvelope):
    check_id: uuid.UUID
    expected_version: int
    result: str
    evidence: dict | None = None
    next_observation_due: datetime | None = None
    escalation_required: bool = False
    escalation_rationale: str | None = None


async def evaluate_effectiveness_check(session: AsyncSession, cmd: EvaluateEffectivenessCheckCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    check = (
        await session.execute(select(EffectivenessCheck).where(EffectivenessCheck.id == cmd.check_id).with_for_update())
    ).scalar_one_or_none()
    if check is None:
        raise NotFoundError("Effectiveness check not found")
    if check.version != cmd.expected_version:
        raise StaleVersionError("Effectiveness check was modified by another actor since it was read", expected_version=cmd.expected_version, current_version=check.version)
    if check.state != "OBSERVATION":
        raise InvalidTransitionError("Illegal effectiveness check transition", current_state=check.state, requested="EVALUATION")
    if cmd.result not in EFFECTIVENESS_RESULTS:
        raise ValidationFailedError("result must be 'pass', 'fail' or 'inconclusive'", result=cmd.result)
    if cmd.result == "inconclusive" and cmd.next_observation_due is None:
        raise EffectivenessInconclusiveError("An inconclusive result requires a next_observation_due follow-up date")

    old_state = check.state
    check.result = cmd.result
    check.evidence = cmd.evidence
    check.reviewer_subject_id = actor_user_id
    check.next_observation_due = cmd.next_observation_due
    if cmd.result == "fail":
        check.escalation_required = cmd.escalation_required
        check.escalation_rationale = cmd.escalation_rationale
    check.state = cmd.result.upper()
    check.evaluated_at = datetime.now(timezone.utc)
    check.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=check.site_id, aggregate_type="effectiveness_check", aggregate_id=check.id,
        aggregate_version=check.version, action="Changed", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=cmd.escalation_rationale, old_value={"state": old_state}, new_value={"state": check.state}, signature_id=None,
    )
    event_type = "EffectivenessCheckPassed" if cmd.result == "pass" else "EffectivenessCheckFailed"
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="effectiveness_check", aggregate_id=check.id,
        aggregate_version=check.version, payload={"id": str(check.id), "result": cmd.result}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=check.site_id, command_type="EvaluateEffectivenessCheck", aggregate_type="effectiveness_check",
        aggregate_id=check.id, expected_version=cmd.expected_version, resulting_version=check.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=check.id, resulting_version=check.version,
        audit_event_id=audit_event.id, signature_id=None, correlation_id=correlation_id,
    )
