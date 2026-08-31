"""Document 15 (SPEC-EBMR-006) — the buildable slice of the Release / Disposition Engine: evaluate a
scope (get-or-create + eligibility computation), release/hold/reject (all signature-gated). Rework/
reprocess/destroy have no approved-route entity to link to (same gap as BAT-FR-024/DHR-FR-012) and are
not built this pass -- see SG-056. Only `scope_type == "batch"` is supported -- device lot/serial/
combination scope needs deeper Document 12/13 integration this pass doesn't build.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.release import service as release_service
from app.modules.release.models import ALLOWED_TRANSITIONS, ReleaseDecision, ReleaseEvaluation, ReleaseScope
from app.modules.signature import service as signature_service
from app.modules.vault import service as vault_service
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


async def _load_scope_for_update(session: AsyncSession, scope_id: uuid.UUID, expected_version: int) -> ReleaseScope:
    result = await session.execute(select(ReleaseScope).where(ReleaseScope.id == scope_id).with_for_update())
    scope = result.scalar_one_or_none()
    if scope is None:
        raise NotFoundError("Release scope not found")
    if scope.version != expected_version:
        raise StaleVersionError(
            "Release scope was modified by another actor since it was read",
            expected_version=expected_version,
            current_version=scope.version,
        )
    return scope


async def _resolve_signature(session: AsyncSession, *, action: str, actor_user_id: uuid.UUID, record_version: int, record_hash: str, challenge_id: uuid.UUID | None, reauth_password: str | None):
    policy = await signature_service.resolve_signature_requirement(session, record_type="release_scope", action=action)
    if not policy.signature_required:
        return None
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"Release decision '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=record_version, record_hash=record_hash,
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


# ---------------------------------------------------------------------------
# EvaluateReleaseScope — REL-FR-001/003/004/008/025 (partial), get-or-create + (re-)evaluate
# ---------------------------------------------------------------------------


class EvaluateReleaseScopeCommand(CommandEnvelope):
    scope_type: str
    scope_id: uuid.UUID


async def evaluate_release_scope(session: AsyncSession, cmd: EvaluateReleaseScopeCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.scope_type != "batch":
        raise ValidationFailedError("Only scope_type 'batch' is supported this pass", scope_type=cmd.scope_type)

    batch = await release_service.get_batch(session, cmd.scope_id)
    scope = await release_service.get_scope_for_target(session, cmd.scope_type, cmd.scope_id)
    created = scope is None
    if created:
        scope = ReleaseScope(
            site_id=batch.site_id, scope_type=cmd.scope_type, scope_id=cmd.scope_id,
            product_version_id=batch.product_version_id, batch_id=batch.id, state="draft_evaluation",
        )
        session.add(scope)
        await session.flush()
    else:
        if scope.state in ("released", "rejected"):
            raise InvalidTransitionError("Release scope cannot be re-evaluated from a terminal state", current_state=scope.state, requested="eligible/blocked")

    blockers, warnings = await release_service.evaluate_eligibility(session, batch)
    eligible = not blockers

    evaluation = ReleaseEvaluation(
        release_scope_id=scope.id, scope_version=scope.version, evaluated_batch_version=batch.version,
        blockers=blockers, warnings=warnings, eligible=eligible,
    )
    session.add(evaluation)
    await session.flush()

    old_state = scope.state
    scope.current_evaluation_id = evaluation.id
    # REL-FR-011: while on hold, eligibility continues updating but the hold itself is a deliberate
    # quality lock -- a re-evaluation never silently clears it. There's no resume-from-hold endpoint in
    # this pass (same reasoning as batch_execution/device holds), so hold is otherwise terminal here.
    if scope.state != "hold":
        scope.state = "eligible" if eligible else "blocked"
    scope.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=scope.site_id, aggregate_type="release_scope", aggregate_id=scope.id,
        aggregate_version=scope.version, action="Created" if created else "Changed", actor_id=actor_user_id,
        correlation_id=correlation_id, old_value=None if created else {"state": old_state},
        new_value={"state": scope.state, "eligible": eligible, "blocker_count": len(blockers)},
    )
    await write_outbox_event(
        session, event_type="ReleaseEvaluationCompleted", aggregate_type="release_scope", aggregate_id=scope.id,
        aggregate_version=scope.version, payload={"id": str(scope.id), "eligible": eligible}, correlation_id=correlation_id,
    )
    if not created:
        await write_outbox_event(
            session, event_type="ReleaseEligibilityChanged", aggregate_type="release_scope", aggregate_id=scope.id,
            aggregate_version=scope.version, payload={"id": str(scope.id), "eligible": eligible}, correlation_id=correlation_id,
        )
    receipt = await record_command_receipt(
        session, site_id=scope.site_id, command_type="EvaluateReleaseScope", aggregate_type="release_scope",
        aggregate_id=scope.id, expected_version=None if created else scope.version - 1, resulting_version=scope.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(command_id=receipt.id, aggregate_id=scope.id, resulting_version=scope.version, audit_event_id=audit_event.id, correlation_id=correlation_id)


# ---------------------------------------------------------------------------
# ReleaseScope — REL-FR-006/007/008/009
# ---------------------------------------------------------------------------


class ReleaseDecisionCommand(CommandEnvelope):
    scope_id: uuid.UUID
    expected_version: int
    reason: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def release_scope_decision(session: AsyncSession, cmd: ReleaseDecisionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    scope = await _load_scope_for_update(session, cmd.scope_id, cmd.expected_version)
    if "released" not in ALLOWED_TRANSITIONS.get(scope.state, set()):
        raise InvalidTransitionError("Illegal release scope transition", current_state=scope.state, requested="released")

    # REL-FR-008: re-evaluate immediately before commit -- no stale green status.
    batch = await release_service.get_batch(session, scope.batch_id)
    blockers, warnings = await release_service.evaluate_eligibility(session, batch)
    if blockers:
        raise ValidationFailedError("Release scope is no longer eligible", blockers=blockers)
    evaluation = ReleaseEvaluation(
        release_scope_id=scope.id, scope_version=scope.version, evaluated_batch_version=batch.version,
        blockers=blockers, warnings=warnings, eligible=True,
    )
    session.add(evaluation)
    await session.flush()

    signature_id = await _resolve_signature(
        session, action="release", actor_user_id=actor_user_id, record_version=scope.version,
        record_hash=sha256_hex({"id": str(scope.id), "version": scope.version}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    vault_object = await vault_service.release_master(
        session, object_type="release_package", business_id=str(scope.id), site_id=scope.site_id,
        actor_user_id=actor_user_id, business_version_label=str(scope.version),
        canonical_payload={
            "release_scope_id": str(scope.id), "batch_id": str(scope.batch_id), "batch_version": batch.version,
            "product_version_id": str(scope.product_version_id), "evaluation_id": str(evaluation.id),
            "signature_id": str(signature_id) if signature_id else None,
        },
    )

    decision = ReleaseDecision(
        release_scope_id=scope.id, evaluation_id=evaluation.id, decision_code="RELEASED", reason=cmd.reason,
        signature_id=signature_id, release_package_hash=vault_object.digest,
    )
    session.add(decision)

    old_state = scope.state
    scope.state = "released"
    scope.current_evaluation_id = evaluation.id
    scope.released_vault_object_id = vault_object.object_id
    scope.decision_at = datetime.now(timezone.utc)
    scope.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=scope.site_id, aggregate_type="release_scope", aggregate_id=scope.id,
        aggregate_version=scope.version, action="Released", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=cmd.reason, old_value={"state": old_state}, new_value={"state": "released"}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="ProductReleased", aggregate_type="release_scope", aggregate_id=scope.id,
        aggregate_version=scope.version, payload={"id": str(scope.id), "batch_id": str(scope.batch_id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=scope.site_id, command_type="ReleaseScope", aggregate_type="release_scope",
        aggregate_id=scope.id, expected_version=cmd.expected_version, resulting_version=scope.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(command_id=receipt.id, aggregate_id=scope.id, resulting_version=scope.version, audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id)


# ---------------------------------------------------------------------------
# Hold / Reject — REL-FR-011/012
# ---------------------------------------------------------------------------


async def _decide_terminal_or_hold(session: AsyncSession, cmd: ReleaseDecisionCommand, actor_user_id: uuid.UUID, *, new_state: str, decision_code: str, action: str, event_type: str, audit_action: str) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    scope = await _load_scope_for_update(session, cmd.scope_id, cmd.expected_version)
    if new_state not in ALLOWED_TRANSITIONS.get(scope.state, set()):
        raise InvalidTransitionError("Illegal release scope transition", current_state=scope.state, requested=new_state)

    signature_id = await _resolve_signature(
        session, action=action, actor_user_id=actor_user_id, record_version=scope.version,
        record_hash=sha256_hex({"id": str(scope.id), "version": scope.version}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    if scope.current_evaluation_id is None:
        raise ValidationFailedError("Release scope has never been evaluated")

    decision = ReleaseDecision(
        release_scope_id=scope.id, evaluation_id=scope.current_evaluation_id, decision_code=decision_code,
        reason=cmd.reason, signature_id=signature_id,
    )
    session.add(decision)

    old_state = scope.state
    scope.state = new_state
    scope.decision_at = datetime.now(timezone.utc)
    scope.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=scope.site_id, aggregate_type="release_scope", aggregate_id=scope.id,
        aggregate_version=scope.version, action=audit_action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=cmd.reason, old_value={"state": old_state}, new_value={"state": new_state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="release_scope", aggregate_id=scope.id,
        aggregate_version=scope.version, payload={"id": str(scope.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=scope.site_id, command_type=f"{decision_code.title()}ReleaseScope", aggregate_type="release_scope",
        aggregate_id=scope.id, expected_version=cmd.expected_version, resulting_version=scope.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(command_id=receipt.id, aggregate_id=scope.id, resulting_version=scope.version, audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id)


async def hold_scope(session: AsyncSession, cmd: ReleaseDecisionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    return await _decide_terminal_or_hold(session, cmd, actor_user_id, new_state="hold", decision_code="HOLD", action="hold", event_type="ReleaseHoldPlaced", audit_action="Changed")


async def reject_scope(session: AsyncSession, cmd: ReleaseDecisionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    return await _decide_terminal_or_hold(session, cmd, actor_user_id, new_state="rejected", decision_code="REJECTED", action="reject", event_type="ProductRejected", audit_action="Rejected")
