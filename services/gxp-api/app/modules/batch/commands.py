import uuid
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.batch.models import ALLOWED_TRANSITIONS, Batch, BatchRelease, BatchReview, BatchStep
from app.modules.iam.models import User
from app.modules.iam.service import require_role
from app.modules.recipe.models import RecipeStep
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import (
    check_idempotency,
    record_command_receipt,
    write_audit_event,
    write_outbox_event,
)
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


async def _load_batch_for_update(session: AsyncSession, batch_id: uuid.UUID, expected_version: int) -> Batch:
    result = await session.execute(select(Batch).where(Batch.id == batch_id).with_for_update())
    batch = result.scalar_one_or_none()
    if batch is None:
        raise NotFoundError("Batch not found", batch_id=str(batch_id))
    if batch.version != expected_version:
        raise StaleVersionError(
            "Batch was modified by another actor since it was read",
            expected_version=expected_version,
            current_version=batch.version,
        )
    return batch


def _assert_transition(batch: Batch, new_status: str) -> None:
    if new_status not in ALLOWED_TRANSITIONS.get(batch.status, set()):
        raise InvalidTransitionError(
            f"Cannot move batch from '{batch.status}' to '{new_status}'",
            current_status=batch.status,
            requested_status=new_status,
        )


def batch_record_hash(batch: Batch) -> str:
    return sha256_hex(
        {"id": str(batch.id), "version": batch.version, "status": batch.status}
    )


# ---------------------------------------------------------------------------
# CreateBatch
# ---------------------------------------------------------------------------


class CreateBatchCommand(CommandEnvelope):
    site_id: uuid.UUID
    product_id: uuid.UUID
    recipe_id: uuid.UUID
    recipe_version: int
    batch_number: str
    target_quantity: Decimal
    uom: str


async def create_batch(
    session: AsyncSession, cmd: CreateBatchCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = Batch(
        site_id=cmd.site_id,
        product_id=cmd.product_id,
        recipe_id=cmd.recipe_id,
        recipe_version=cmd.recipe_version,
        batch_number=cmd.batch_number,
        status="planned",
        target_quantity=cmd.target_quantity,
        uom=cmd.uom,
        version=1,
    )
    session.add(batch)
    await session.flush()

    recipe_steps = (
        await session.execute(
            select(RecipeStep).where(RecipeStep.recipe_id == cmd.recipe_id).order_by(RecipeStep.step_number)
        )
    ).scalars().all()
    if not recipe_steps:
        raise ValidationFailedError("Recipe has no steps", recipe_id=str(cmd.recipe_id))
    for step in recipe_steps:
        session.add(BatchStep(batch_id=batch.id, recipe_step_id=step.id, status="pending"))

    return await _commit_batch_mutation(
        session,
        batch=batch,
        actor_user_id=actor_user_id,
        command_type="CreateBatch",
        action="Created",
        cmd=cmd,
        payload_hash=payload_hash,
        new_value={"batch_number": batch.batch_number, "status": batch.status},
    )


# ---------------------------------------------------------------------------
# IssueBatch
# ---------------------------------------------------------------------------


class IssueBatchCommand(CommandEnvelope):
    batch_id: uuid.UUID
    expected_version: int


async def issue_batch(
    session: AsyncSession, cmd: IssueBatchCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await _load_batch_for_update(session, cmd.batch_id, cmd.expected_version)
    _assert_transition(batch, "issued")
    old_status = batch.status
    batch.status = "issued"
    batch.version += 1

    # First ready step(s) become claimable.
    first_step = (
        await session.execute(
            select(BatchStep, RecipeStep)
            .join(RecipeStep, RecipeStep.id == BatchStep.recipe_step_id)
            .where(BatchStep.batch_id == batch.id)
            .order_by(RecipeStep.step_number)
            .limit(1)
        )
    ).first()
    if first_step is not None:
        first_step[0].status = "ready"

    return await _commit_batch_mutation(
        session,
        batch=batch,
        actor_user_id=actor_user_id,
        command_type="IssueBatch",
        action="StatusChanged",
        cmd=cmd,
        payload_hash=payload_hash,
        old_value={"status": old_status},
        new_value={"status": batch.status},
    )


# ---------------------------------------------------------------------------
# StartStep
# ---------------------------------------------------------------------------


class StartStepCommand(CommandEnvelope):
    batch_id: uuid.UUID
    expected_version: int
    batch_step_id: uuid.UUID


async def start_step(
    session: AsyncSession, cmd: StartStepCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await _load_batch_for_update(session, cmd.batch_id, cmd.expected_version)
    if batch.status not in ("issued", "in_execution"):
        raise InvalidTransitionError("Batch is not in an executable state", current_status=batch.status)

    await require_role(session, actor_user_id, site_id, "Operator", "Supervisor")

    step = await session.get(BatchStep, cmd.batch_step_id)
    if step is None or step.batch_id != batch.id:
        raise NotFoundError("Batch step not found", batch_step_id=str(cmd.batch_step_id))
    if step.status != "ready":
        raise InvalidTransitionError(
            "Step is not ready to start", current_status=step.status
        )

    step.status = "in_progress"
    step.started_at = datetime.now(timezone.utc)
    step.performed_by_user_id = actor_user_id

    old_status = batch.status
    batch.status = "in_execution"
    batch.version += 1

    return await _commit_batch_mutation(
        session,
        batch=batch,
        actor_user_id=actor_user_id,
        command_type="StartStep",
        action="StepStarted",
        cmd=cmd,
        payload_hash=payload_hash,
        old_value={"batch_status": old_status, "step_status": "ready"},
        new_value={"batch_status": batch.status, "step_status": step.status, "step_id": str(step.id)},
    )


# ---------------------------------------------------------------------------
# CompleteStep
# ---------------------------------------------------------------------------


class CompleteStepCommand(CommandEnvelope):
    batch_id: uuid.UUID
    expected_version: int
    batch_step_id: uuid.UUID
    data: dict = {}
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def complete_step(
    session: AsyncSession, cmd: CompleteStepCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await _load_batch_for_update(session, cmd.batch_id, cmd.expected_version)
    step = await session.get(BatchStep, cmd.batch_step_id)
    if step is None or step.batch_id != batch.id:
        raise NotFoundError("Batch step not found", batch_step_id=str(cmd.batch_step_id))
    if step.status != "in_progress":
        raise InvalidTransitionError("Step is not in progress", current_status=step.status)

    recipe_step = await session.get(RecipeStep, step.recipe_step_id)
    signature_id = None
    if recipe_step.requires_signature:
        if cmd.challenge_id is None or not cmd.reauth_password:
            raise MissingSignatureError(
                "This step requires a signature",
                required_meaning=recipe_step.signature_meaning,
            )
        signature_id = await _verify_reauth_and_consume(
            session, actor_user_id, cmd.challenge_id, cmd.reauth_password, batch
        )

    step.status = "completed"
    step.completed_at = datetime.now(timezone.utc)
    step.data = cmd.data
    step.signature_id = signature_id

    # Advance the next step to "ready", or mark production complete.
    next_step = (
        await session.execute(
            select(BatchStep, RecipeStep)
            .join(RecipeStep, RecipeStep.id == BatchStep.recipe_step_id)
            .where(BatchStep.batch_id == batch.id, RecipeStep.step_number > recipe_step.step_number)
            .order_by(RecipeStep.step_number)
            .limit(1)
        )
    ).first()

    old_status = batch.status
    if next_step is not None:
        next_step[0].status = "ready"
    else:
        batch.status = "production_complete"
    batch.version += 1

    return await _commit_batch_mutation(
        session,
        batch=batch,
        actor_user_id=actor_user_id,
        command_type="CompleteStep",
        action="StepCompleted",
        cmd=cmd,
        payload_hash=payload_hash,
        old_value={"batch_status": old_status, "step_status": "in_progress"},
        new_value={"batch_status": batch.status, "step_status": "completed", "step_id": str(step.id)},
        signature_id=signature_id,
    )


# ---------------------------------------------------------------------------
# SubmitForReview
# ---------------------------------------------------------------------------


class SubmitForReviewCommand(CommandEnvelope):
    batch_id: uuid.UUID
    expected_version: int


async def submit_for_review(
    session: AsyncSession, cmd: SubmitForReviewCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await _load_batch_for_update(session, cmd.batch_id, cmd.expected_version)
    incomplete = (
        await session.execute(
            select(BatchStep).where(
                BatchStep.batch_id == batch.id, BatchStep.status != "completed"
            )
        )
    ).scalars().all()
    if incomplete:
        raise InvalidTransitionError(
            "All batch steps must be completed before submitting for QA review",
            incomplete_step_count=len(incomplete),
        )
    _assert_transition(batch, "qa_review")
    old_status = batch.status
    batch.status = "qa_review"
    batch.version += 1

    return await _commit_batch_mutation(
        session,
        batch=batch,
        actor_user_id=actor_user_id,
        command_type="SubmitForReview",
        action="StatusChanged",
        cmd=cmd,
        payload_hash=payload_hash,
        old_value={"status": old_status},
        new_value={"status": batch.status},
    )


# ---------------------------------------------------------------------------
# ReviewBatch / ReleaseBatch
# ---------------------------------------------------------------------------


class ReviewBatchCommand(CommandEnvelope):
    batch_id: uuid.UUID
    expected_version: int
    decision: str  # "approved" | "rejected"
    reason: str | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def review_batch(
    session: AsyncSession, cmd: ReviewBatchCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await _load_batch_for_update(session, cmd.batch_id, cmd.expected_version)
    if batch.status != "qa_review":
        raise InvalidTransitionError("Batch is not awaiting QA review", current_status=batch.status)
    if cmd.decision not in ("approved", "rejected"):
        raise ValidationFailedError("decision must be 'approved' or 'rejected'")

    await require_role(session, actor_user_id, site_id, "QA Reviewer")
    signature_id = await _verify_reauth_and_consume(
        session, actor_user_id, cmd.challenge_id, cmd.reauth_password, batch
    )

    session.add(
        BatchReview(
            batch_id=batch.id,
            reviewer_user_id=actor_user_id,
            decision=cmd.decision,
            reason=cmd.reason,
            signature_id=signature_id,
        )
    )

    # Review does not itself release — it only unblocks release; status stays qa_review until release.
    old_status = batch.status
    batch.version += 1

    return await _commit_batch_mutation(
        session,
        batch=batch,
        actor_user_id=actor_user_id,
        command_type="ReviewBatch",
        action="Reviewed",
        cmd=cmd,
        payload_hash=payload_hash,
        old_value={"status": old_status},
        new_value={"decision": cmd.decision, "reason": cmd.reason},
        signature_id=signature_id,
        reason=cmd.reason,
    )


class ReleaseBatchCommand(CommandEnvelope):
    batch_id: uuid.UUID
    expected_version: int
    decision: str  # "released" | "rejected"
    challenge_id: uuid.UUID
    reauth_password: str


async def release_batch(
    session: AsyncSession, cmd: ReleaseBatchCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await _load_batch_for_update(session, cmd.batch_id, cmd.expected_version)
    if batch.status != "qa_review":
        raise InvalidTransitionError("Batch is not awaiting release", current_status=batch.status)
    if cmd.decision not in ("released", "rejected"):
        raise ValidationFailedError("decision must be 'released' or 'rejected'")

    latest_review = (
        await session.execute(
            select(BatchReview)
            .where(BatchReview.batch_id == batch.id)
            .order_by(BatchReview.reviewed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest_review is None or latest_review.decision != "approved":
        raise InvalidTransitionError("Batch has not been approved by QA review")

    await require_role(session, actor_user_id, site_id, "QA Releaser")
    if actor_user_id == latest_review.reviewer_user_id:
        raise InvalidTransitionError(
            "Releaser must be independent of the reviewer for this batch (SoD)"
        )

    signature_id = await _verify_reauth_and_consume(
        session, actor_user_id, cmd.challenge_id, cmd.reauth_password, batch
    )

    session.add(
        BatchRelease(
            batch_id=batch.id,
            released_by_user_id=actor_user_id,
            decision=cmd.decision,
            signature_id=signature_id,
        )
    )

    _assert_transition(batch, cmd.decision)
    old_status = batch.status
    batch.status = cmd.decision
    batch.version += 1

    return await _commit_batch_mutation(
        session,
        batch=batch,
        actor_user_id=actor_user_id,
        command_type="ReleaseBatch",
        action="StatusChanged",
        cmd=cmd,
        payload_hash=payload_hash,
        old_value={"status": old_status},
        new_value={"status": batch.status},
        signature_id=signature_id,
    )


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------


async def _verify_reauth_and_consume(
    session: AsyncSession,
    actor_user_id: uuid.UUID,
    challenge_id: uuid.UUID,
    reauth_password: str,
    batch: Batch,
) -> uuid.UUID:
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session,
        challenge_id=challenge_id,
        user_id=actor_user_id,
        record_version=batch.version,
        record_hash=batch_record_hash(batch),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


async def _commit_batch_mutation(
    session: AsyncSession,
    *,
    batch: Batch,
    actor_user_id: uuid.UUID,
    command_type: str,
    action: str,
    cmd: BaseModel,
    payload_hash: str,
    new_value: dict,
    old_value: dict | None = None,
    signature_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=batch.version,
        action=action,
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value=old_value,
        new_value=new_value,
        signature_id=signature_id,
        reason=reason,
    )
    await write_outbox_event(
        session,
        event_type=f"Batch{action}",
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=batch.version,
        payload={"id": str(batch.id), **new_value},
        correlation_id=correlation_id,
    )
    expected_version = getattr(cmd, "expected_version", None)
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type=command_type,
        aggregate_type="batch",
        aggregate_id=batch.id,
        expected_version=expected_version,
        resulting_version=batch.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=batch.id,
        resulting_version=batch.version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )
