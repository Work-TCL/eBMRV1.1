"""Document 14 (SPEC-EBMR-005) — the buildable slice of Review-by-Exception & QA Review: create a
package (with inline completeness computation, standing in for the separate CREATED/INDEXING phases --
see models.py), complete it (signature-gated, gated on computed completeness), and reindex it (recomputes
completeness against the batch's current version; reopens a completed package if the batch changed
underneath it). Everything needing qa_review_item/qa_review_comment or the modules/entities SG-054 lists
is out of scope this pass.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.qa_review import service as qa_review_service
from app.modules.qa_review.models import ALLOWED_TRANSITIONS, QaReviewPackage
from app.modules.signature import service as signature_service
from app.mutation.errors import InvalidTransitionError, MissingSignatureError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


async def _load_package_for_update(session: AsyncSession, package_id: uuid.UUID, expected_version: int) -> QaReviewPackage:
    result = await session.execute(select(QaReviewPackage).where(QaReviewPackage.id == package_id).with_for_update())
    package = result.scalar_one_or_none()
    if package is None:
        raise NotFoundError("QA review package not found")
    if package.version != expected_version:
        raise StaleVersionError(
            "QA review package was modified by another actor since it was read",
            expected_version=expected_version,
            current_version=package.version,
        )
    return package


def _batch_snapshot_hash(batch) -> str:
    return sha256_hex(
        {"id": str(batch.id), "version": batch.version, "state": batch.state, "execution_snapshot_id": str(batch.execution_snapshot_id) if batch.execution_snapshot_id else None}
    )


# ---------------------------------------------------------------------------
# CreateReviewPackage — RBE-FR-001/003/005 (partial)
# ---------------------------------------------------------------------------


class CreateReviewPackageCommand(CommandEnvelope):
    batch_id: uuid.UUID


async def create_review_package(session: AsyncSession, cmd: CreateReviewPackageCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await qa_review_service.get_batch(session, cmd.batch_id)
    if (await qa_review_service.get_package_for_batch(session, cmd.batch_id)) is not None:
        raise ValidationFailedError("A QA review package already exists for this batch", batch_id=str(cmd.batch_id))

    corrections = await qa_review_service.get_batch_corrections(session, cmd.batch_id)
    completeness_status, _blockers = await qa_review_service.compute_completeness(session, batch, corrections)

    package = QaReviewPackage(
        site_id=batch.site_id,
        batch_id=batch.id,
        batch_version=batch.version,
        record_hash=_batch_snapshot_hash(batch),
        exception_index_version=1,
        completeness_status=completeness_status,
        state="READY_FOR_REVIEW",
    )
    session.add(package)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="qa_review_package",
        aggregate_id=package.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"batch_id": str(batch.id), "batch_version": batch.version, "completeness_status": completeness_status},
    )
    await write_outbox_event(
        session, event_type="QAReviewPackageCreated", aggregate_type="qa_review_package", aggregate_id=package.id,
        aggregate_version=1, payload={"id": str(package.id), "batch_id": str(batch.id)}, correlation_id=correlation_id,
    )
    await write_outbox_event(
        session, event_type="QAExceptionIndexed", aggregate_type="qa_review_package", aggregate_id=package.id,
        aggregate_version=1, payload={"id": str(package.id), "completeness_status": completeness_status}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=batch.site_id, command_type="CreateReviewPackage", aggregate_type="qa_review_package",
        aggregate_id=package.id, expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(command_id=receipt.id, aggregate_id=package.id, resulting_version=1, audit_event_id=audit_event.id, correlation_id=correlation_id)


# ---------------------------------------------------------------------------
# ReindexReviewPackage — RBE-FR-024/028 (partial)
# ---------------------------------------------------------------------------


class ReindexReviewPackageCommand(CommandEnvelope):
    package_id: uuid.UUID
    expected_version: int


async def reindex_review_package(session: AsyncSession, cmd: ReindexReviewPackageCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    package = await _load_package_for_update(session, cmd.package_id, cmd.expected_version)
    batch = await qa_review_service.get_batch(session, package.batch_id)
    corrections = await qa_review_service.get_batch_corrections(session, package.batch_id)
    completeness_status, _blockers = await qa_review_service.compute_completeness(session, batch, corrections)

    old_state = package.state
    old_completeness_status = package.completeness_status
    batch_changed = batch.version != package.batch_version
    new_state = old_state
    if package.state == "REVIEW_COMPLETE" and batch_changed:
        new_state = "REOPENED"  # RBE-FR-024: new evidence/correction after completion reopens the review
    elif package.state == "REOPENED":
        new_state = "READY_FOR_REVIEW"

    package.batch_version = batch.version
    package.record_hash = _batch_snapshot_hash(batch)
    package.completeness_status = completeness_status
    package.exception_index_version += 1
    package.state = new_state
    package.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=package.site_id, aggregate_type="qa_review_package", aggregate_id=package.id,
        aggregate_version=package.version, action="Changed", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state, "completeness_status": old_completeness_status},
        new_value={"state": new_state, "completeness_status": completeness_status, "exception_index_version": package.exception_index_version},
    )
    await write_outbox_event(
        session, event_type="QAReviewReopened" if new_state == "REOPENED" else "QAExceptionIndexed",
        aggregate_type="qa_review_package", aggregate_id=package.id, aggregate_version=package.version,
        payload={"id": str(package.id), "completeness_status": completeness_status}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=package.site_id, command_type="ReindexReviewPackage", aggregate_type="qa_review_package",
        aggregate_id=package.id, expected_version=cmd.expected_version, resulting_version=package.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(command_id=receipt.id, aggregate_id=package.id, resulting_version=package.version, audit_event_id=audit_event.id, correlation_id=correlation_id)


# ---------------------------------------------------------------------------
# CompleteReviewPackage — RBE-FR-020/022/023
# ---------------------------------------------------------------------------


class CompleteReviewPackageCommand(CommandEnvelope):
    package_id: uuid.UUID
    expected_version: int
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def complete_review_package(session: AsyncSession, cmd: CompleteReviewPackageCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    package = await _load_package_for_update(session, cmd.package_id, cmd.expected_version)
    if "REVIEW_COMPLETE" not in ALLOWED_TRANSITIONS.get(package.state, set()):
        raise InvalidTransitionError("Illegal QA review package transition", current_state=package.state, requested="REVIEW_COMPLETE")
    if package.completeness_status != "complete":
        # RBE-FR-020: cannot complete while exceptions are outstanding -- there is no itemised
        # disposition/acceptance path this pass (qa_review_item, SG-053), so "complete" is the only
        # acceptable status a package can be completed from.
        raise ValidationFailedError(
            "QA review package cannot be completed while its completeness_status is not 'complete'",
            completeness_status=package.completeness_status,
        )

    policy = await signature_service.resolve_signature_requirement(session, record_type="qa_review_package", action="complete")
    signature_id = None
    if policy.signature_required:
        if cmd.challenge_id is None or not cmd.reauth_password:
            raise MissingSignatureError("Completing a QA review package requires a signature", required_meaning=policy.meaning)
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id, record_version=package.version,
            record_hash=sha256_hex({"id": str(package.id), "version": package.version}),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    old_state = package.state
    package.state = "REVIEW_COMPLETE"
    package.completed_at = datetime.now(timezone.utc)
    package.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=package.site_id, aggregate_type="qa_review_package", aggregate_id=package.id,
        aggregate_version=package.version, action="Reviewed", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": "REVIEW_COMPLETE"}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="QAReviewCompleted", aggregate_type="qa_review_package", aggregate_id=package.id,
        aggregate_version=package.version, payload={"id": str(package.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=package.site_id, command_type="CompleteReviewPackage", aggregate_type="qa_review_package",
        aggregate_id=package.id, expected_version=cmd.expected_version, resulting_version=package.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(command_id=receipt.id, aggregate_id=package.id, resulting_version=package.version, audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id)
