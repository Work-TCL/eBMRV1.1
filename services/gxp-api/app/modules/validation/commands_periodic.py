"""Document 96 (SPEC-VAL-018) Mutation Gateway command handlers -- Periodic Review, Change Impact,
Revalidation & Validated-State Maintenance. Document 106 rows 170/171: both `periodic-reviews` (create)
and `periodic-reviews/{id}/decision` require a `Reviewed` signature from a QA Reviewer independent of the
performer, no mandatory reason. `change-impacts`, `revalidation-plans`, `revalidations` and
`decommission` carry no Document 106 row -- unsigned.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import (
    REVALIDATION_LEVELS,
    VALIDATED_STATE_DECISIONS,
    PeriodicValidationReview,
    ValidatedStateBaseline,
    ValidationChangeImpact,
)
from app.modules.validation.shared import finalize, receipt_from_existing, resolve_signature, verify_reauth_and_consume
from app.mutation.errors import InvalidTransitionError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_PERIODIC_REVIEW = "periodic_validation_review"


class CreateChangeImpactCommand(CommandEnvelope):
    change_ref: str
    change_type: str
    affected_trace_artifacts: list[dict] = []
    is_emergency: bool = False
    revalidation_level: str
    rationale: str


async def create_change_impact(
    session: AsyncSession, cmd: CreateChangeImpactCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if cmd.revalidation_level not in REVALIDATION_LEVELS:
        raise ValidationFailedError(f"revalidation_level must be one of {REVALIDATION_LEVELS}")
    if not cmd.rationale:
        raise ValidationFailedError("rationale is required (VSM-FR-004: proportionate, never blanket)")

    row = ValidationChangeImpact(
        change_ref=cmd.change_ref, change_type=cmd.change_type, affected_trace_artifacts=cmd.affected_trace_artifacts,
        is_emergency=cmd.is_emergency, revalidation_level=cmd.revalidation_level, rationale=cmd.rationale, version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="validation_change_impact", aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"change_ref": row.change_ref, "revalidation_level": row.revalidation_level},
        event_type="ValidationChangeImpactAssessed", expected_version=None, command_type="CreateChangeImpact",
        site_id=site_id,
    )


class ApproveRevalidationPlanCommand(CommandEnvelope):
    change_impact_id: uuid.UUID
    expected_version: int
    revalidation_ref: str


async def approve_revalidation_plan(
    session: AsyncSession, cmd: ApproveRevalidationPlanCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = await session.get(ValidationChangeImpact, cmd.change_impact_id)
    if row is None:
        raise NotFoundError("Validation change impact not found")
    if row.approved_by_user_id is not None:
        raise InvalidTransitionError("Revalidation plan already approved")
    if row.version != cmd.expected_version:
        raise StaleVersionError("Change impact changed since this request was prepared", current_version=row.version)

    row.revalidation_ref = cmd.revalidation_ref
    row.approved_by_user_id = actor_user_id
    row.approved_at = datetime.now(timezone.utc)
    row.version += 1

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="validation_change_impact", aggregate_id=row.id,
        version=row.version, action="Approved", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"revalidation_ref": cmd.revalidation_ref}, event_type="RevalidationPlanApproved",
        expected_version=cmd.expected_version, command_type="ApproveRevalidationPlan", site_id=site_id,
    )


class CompleteRevalidationCommand(CommandEnvelope):
    change_impact_id: uuid.UUID
    expected_version: int
    evidence_ref: str


async def complete_revalidation(
    session: AsyncSession, cmd: CompleteRevalidationCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = await session.get(ValidationChangeImpact, cmd.change_impact_id)
    if row is None:
        raise NotFoundError("Validation change impact not found")
    if row.approved_by_user_id is None:
        raise InvalidTransitionError("Revalidation plan is not approved yet")
    if row.version != cmd.expected_version:
        raise StaleVersionError("Change impact changed since this request was prepared", current_version=row.version)

    row.completed_at = datetime.now(timezone.utc)
    row.version += 1

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="validation_change_impact", aggregate_id=row.id,
        version=row.version, action="Changed", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"evidence_ref": cmd.evidence_ref, "completed": True}, event_type="RevalidationCompleted",
        expected_version=cmd.expected_version, command_type="CompleteRevalidation", site_id=site_id,
    )


class CreatePeriodicReviewCommand(CommandEnvelope):
    release_ref: str
    period_start: datetime
    period_end: datetime
    inputs_considered: dict
    findings: list[dict] = []
    actions: list[dict] = []
    new_record_id: uuid.UUID | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def create_periodic_review(
    session: AsyncSession, cmd: CreatePeriodicReviewCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    """Document 106 row 170 signs this create action -- same pre-generated-id shape as
    `commands_performance.py::create_performance_scenario`."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if cmd.period_end < cmd.period_start:
        raise ValidationFailedError("period_end must not precede period_start")
    if not cmd.inputs_considered:
        raise ValidationFailedError("inputs_considered must not be empty (VSM-FR-012)")

    row = PeriodicValidationReview(
        id=cmd.new_record_id or uuid.uuid4(), release_ref=cmd.release_ref, period_start=cmd.period_start,
        period_end=cmd.period_end, inputs_considered=cmd.inputs_considered, findings=cmd.findings,
        actions=cmd.actions, performed_by_user_id=actor_user_id, state="DRAFT", version=1,
    )
    session.add(row)
    await session.flush()

    policy = await resolve_signature(session, record_type=RECORD_TYPE_PERIODIC_REVIEW, action="create")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_PERIODIC_REVIEW, aggregate_id=row.id,
        version=row.version, action="Reviewed", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"release_ref": row.release_ref, "finding_count": len(cmd.findings)},
        event_type="PeriodicReviewCreated", expected_version=None, command_type="CreatePeriodicReview",
        site_id=site_id, signature_id=signature_id,
    )


class DecidePeriodicReviewCommand(CommandEnvelope):
    review_id: uuid.UUID
    expected_version: int
    decision: str
    challenge_id: uuid.UUID
    reauth_password: str


async def decide_periodic_review(
    session: AsyncSession, cmd: DecidePeriodicReviewCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if cmd.decision not in VALIDATED_STATE_DECISIONS:
        raise ValidationFailedError(f"decision must be one of {VALIDATED_STATE_DECISIONS}")

    row = await session.get(PeriodicValidationReview, cmd.review_id)
    if row is None:
        raise NotFoundError("Periodic validation review not found")
    if row.state != "DRAFT":
        raise InvalidTransitionError("Review already decided", current_state=row.state)
    if row.version != cmd.expected_version:
        raise StaleVersionError("Review changed since this request was prepared", current_version=row.version)
    if actor_user_id == row.performed_by_user_id:
        raise ValidationFailedError("Reviewer must be independent of the performer (Document 106 row 171)")

    policy = await resolve_signature(session, record_type=RECORD_TYPE_PERIODIC_REVIEW, action="decision")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.decision = cmd.decision
    row.reviewed_by_user_id = actor_user_id
    row.reviewed_at = datetime.now(timezone.utc)
    row.state = "DECIDED"
    row.version += 1

    # Document 06 (VLT-FR-001): the validated-state decision is a regulated final record.
    from app.modules.vault import service as vault_service
    await vault_service.release_master(
        session, object_type=RECORD_TYPE_PERIODIC_REVIEW, business_id=str(row.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "release_ref": row.release_ref, "decision": row.decision, "findings": row.findings,
        },
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_PERIODIC_REVIEW, aggregate_id=row.id,
        version=row.version, action="Reviewed", actor_user_id=actor_user_id, reason=None,
        old_value={"state": "DRAFT"}, new_value={"decision": cmd.decision}, event_type="ValidatedStateEvaluated",
        expected_version=cmd.expected_version, command_type="DecidePeriodicReview", site_id=site_id,
        signature_id=signature_id,
    )


class DecommissionValidatedSystemCommand(CommandEnvelope):
    baseline_id: uuid.UUID
    expected_version: int
    decommission_evidence: dict


async def decommission_validated_system(
    session: AsyncSession, cmd: DecommissionValidatedSystemCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if not cmd.decommission_evidence:
        raise ValidationFailedError("decommission_evidence must not be empty (VSM-FR-026)")

    row = await session.get(ValidatedStateBaseline, cmd.baseline_id)
    if row is None:
        raise NotFoundError("Validated state baseline not found")
    if row.state != "VALIDATED":
        raise InvalidTransitionError("Baseline is not in VALIDATED state", current_state=row.state)
    if row.version != cmd.expected_version:
        raise StaleVersionError("Baseline changed since this request was prepared", current_version=row.version)

    row.state = "DECOMMISSIONED"
    row.decommissioned_at = datetime.now(timezone.utc)
    row.decommission_evidence = cmd.decommission_evidence
    row.version += 1

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="validated_state_baseline", aggregate_id=row.id,
        version=row.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_value={"state": "VALIDATED"}, new_value={"state": "DECOMMISSIONED"},
        event_type="ValidatedSystemDecommissioned", expected_version=cmd.expected_version,
        command_type="DecommissionValidatedSystem", site_id=site_id,
    )
