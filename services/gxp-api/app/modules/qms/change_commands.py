"""Document 29 (SPEC-QMS-004) — the buildable slice of Change Control: the linear
DRAFT -> IMPACT_ASSESSMENT -> APPROVAL -> IMPLEMENTATION -> VERIFICATION -> EFFECTIVE -> CLOSED pipeline
Document 29 §4 describes, plus an emergency lane (DRAFT/IMPACT_ASSESSMENT -> IMPLEMENTATION directly,
bypassing pre-approval, with retrospective review recorded via approve() afterward) and CANCELLED (via
close()'s cancellation_reason, reusing the module's one signature-gated terminal endpoint). Every
state-changing operation matches the module's own 8-op API list exactly; no additional operation is
exposed (see change_models.py's module docstring and docs/generated/18_SPEC_GAPS.md SG-071..SG-073 for
what is deliberately not built this pass).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.qms.change_models import (
    CHANGE_CLASSIFICATIONS,
    CHANGE_TYPES,
    NON_CANCELLABLE_STATES,
    ChangeAffectedObject,
    ChangeControl,
    ChangeTask,
)
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    ChangeImpactIncompleteError,
    ChangeNotApprovedError,
    EffectiveDateBlockedError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    RegulatoryReviewRequiredError,
    StaleVersionError,
    TrainingIncompleteError,
    ValidationFailedError,
    ValidationIncompleteError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
        audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _load_change_for_update(session: AsyncSession, change_id: uuid.UUID, expected_version: int) -> ChangeControl:
    result = await session.execute(select(ChangeControl).where(ChangeControl.id == change_id).with_for_update())
    change = result.scalar_one_or_none()
    if change is None:
        raise NotFoundError("Change control record not found")
    if change.version != expected_version:
        raise StaleVersionError(
            "Change control record was modified by another actor since it was read",
            expected_version=expected_version, current_version=change.version,
        )
    return change


def _record_hash(change: ChangeControl) -> str:
    return sha256_hex({"id": str(change.id), "version": change.version})


async def _resolve_signature(
    session: AsyncSession, *, action: str, actor_user_id: uuid.UUID, change: ChangeControl,
    challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type="change_control", action=action)
    if not policy.signature_required:
        return None
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"Change control '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=change.version, record_hash=_record_hash(change),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


async def _write_change_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, change: ChangeControl, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    signature_id: uuid.UUID | None, expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=change.site_id, aggregate_type="change_control", aggregate_id=change.id,
        aggregate_version=change.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": change.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="change_control", aggregate_id=change.id,
        aggregate_version=change.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=change.site_id, command_type=command_type, aggregate_type="change_control",
        aggregate_id=change.id, expected_version=expected_version, resulting_version=change.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=change.id, resulting_version=change.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create — CHG-FR-001/002/003/014(partial)
# ---------------------------------------------------------------------------


class CreateChangeCommand(CommandEnvelope):
    site_id: uuid.UUID
    change_number: str
    change_type: str
    classification: str
    current_state: dict
    proposed_state: dict
    reason: str
    owner_subject_id: uuid.UUID
    emergency: bool = False
    emergency_reason: str | None = None


async def create_change(session: AsyncSession, cmd: CreateChangeCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.change_type not in CHANGE_TYPES:
        raise ValidationFailedError("Unrecognized change_type", change_type=cmd.change_type, allowed=list(CHANGE_TYPES))
    if cmd.classification not in CHANGE_CLASSIFICATIONS:
        raise ValidationFailedError("Unrecognized classification", classification=cmd.classification, allowed=list(CHANGE_CLASSIFICATIONS))
    if not cmd.current_state or not cmd.proposed_state:
        raise ValidationFailedError("current_state and proposed_state are both required")
    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required")
    if cmd.emergency and not (cmd.emergency_reason and cmd.emergency_reason.strip()):
        raise ValidationFailedError("emergency_reason is required for an emergency change")

    conflict = (await session.execute(select(ChangeControl).where(ChangeControl.change_number == cmd.change_number))).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("change_number is already in use", change_number=cmd.change_number)

    change = ChangeControl(
        site_id=cmd.site_id, change_number=cmd.change_number, change_type=cmd.change_type,
        classification=cmd.classification, current_state=cmd.current_state, proposed_state=cmd.proposed_state,
        reason=cmd.reason, owner_subject_id=cmd.owner_subject_id, emergency=cmd.emergency,
        emergency_reason=cmd.emergency_reason, state="DRAFT",
    )
    session.add(change)
    await session.flush()

    event_type = "EmergencyChangeOpened" if cmd.emergency else "ChangeRequested"
    return await _write_change_receipt(
        session, cmd=cmd, payload_hash=payload_hash, change=change, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="DRAFT", event_type=event_type,
        event_payload={"id": str(change.id), "change_number": change.change_number}, signature_id=None,
        expected_version=None, command_type="CreateChange",
    )


# ---------------------------------------------------------------------------
# Impact — CHG-FR-004/005/006/007/008/009/010/011
# ---------------------------------------------------------------------------


class AssessImpactCommand(CommandEnvelope):
    change_id: uuid.UUID
    expected_version: int
    regulatory_impact: dict | None = None
    validation_impact: dict | None = None
    training_impact: dict | None = None
    impact_assessment: dict | None = None
    risk_ref: uuid.UUID | None = None
    affected_objects: list[dict] | None = None
    reason: str | None = None


async def assess_impact(session: AsyncSession, cmd: AssessImpactCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    change = await _load_change_for_update(session, cmd.change_id, cmd.expected_version)
    entering = change.state == "DRAFT"
    if not entering and change.state != "IMPACT_ASSESSMENT":
        raise InvalidTransitionError("Illegal change transition", current_state=change.state, requested="IMPACT_ASSESSMENT")

    old_state = change.state
    if cmd.regulatory_impact is not None:
        change.regulatory_impact = cmd.regulatory_impact
    if cmd.validation_impact is not None:
        change.validation_impact = cmd.validation_impact
    if cmd.training_impact is not None:
        change.training_impact = cmd.training_impact
    if cmd.impact_assessment is not None:
        change.impact_assessment = cmd.impact_assessment
    if cmd.risk_ref is not None:
        change.risk_ref = cmd.risk_ref
    for obj in cmd.affected_objects or []:
        session.add(
            ChangeAffectedObject(
                change_id=change.id, object_type=obj["object_type"], object_id=obj["object_id"],
                object_version=obj.get("object_version"), impact_category=obj["impact_category"],
                action_required=obj["action_required"], created_by=actor_user_id,
            )
        )
    change.state = "IMPACT_ASSESSMENT"
    change.version += 1

    return await _write_change_receipt(
        session, cmd=cmd, payload_hash=payload_hash, change=change, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="ChangeImpactAssessed",
        event_payload={"id": str(change.id)}, signature_id=None, expected_version=cmd.expected_version,
        command_type="AssessChangeImpact",
    )


# ---------------------------------------------------------------------------
# Approve — CHG-FR-013 (pre-approval, signed) / CHG-FR-014 (retrospective review for emergency changes)
# ---------------------------------------------------------------------------


class ApproveChangeCommand(CommandEnvelope):
    change_id: uuid.UUID
    expected_version: int
    approval_notes: str | None = None
    retrospective_findings: dict | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def approve_change(session: AsyncSession, cmd: ApproveChangeCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    change = await _load_change_for_update(session, cmd.change_id, cmd.expected_version)

    signature_id = await _resolve_signature(
        session, action="approve", actor_user_id=actor_user_id, change=change,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )
    old_state = change.state

    if change.emergency and change.state not in ("DRAFT", "IMPACT_ASSESSMENT"):
        # CHG-FR-014: mandatory retrospective review after an emergency implementation -- records the
        # review without a further state transition (the emergency path already moved state on).
        if not cmd.retrospective_findings:
            raise ValidationFailedError("retrospective_findings is required for an emergency change's retrospective review")
        change.retrospective_review = cmd.retrospective_findings
        change.retrospective_review_completed = True
        change.version += 1
        return await _write_change_receipt(
            session, cmd=cmd, payload_hash=payload_hash, change=change, action="Changed", actor_user_id=actor_user_id,
            reason=cmd.approval_notes, old_state=old_state, event_type="ChangeApproved",
            event_payload={"id": str(change.id), "retrospective": True}, signature_id=signature_id,
            expected_version=cmd.expected_version, command_type="RetrospectiveReviewChange",
        )

    if change.state != "IMPACT_ASSESSMENT":
        raise InvalidTransitionError("Illegal change transition", current_state=change.state, requested="APPROVAL")
    if not change.regulatory_impact or not change.validation_impact or not change.training_impact:
        raise ChangeImpactIncompleteError("regulatory_impact, validation_impact and training_impact must all be assessed before approval")
    if change.regulatory_impact.get("requires_review") and not change.regulatory_impact.get("reviewed_by"):
        raise RegulatoryReviewRequiredError("Regulatory impact requires a qualified Regulatory/Quality reviewer before approval")

    change.state = "APPROVAL"
    change.version += 1

    return await _write_change_receipt(
        session, cmd=cmd, payload_hash=payload_hash, change=change, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.approval_notes, old_state=old_state, event_type="ChangeApproved",
        event_payload={"id": str(change.id), "retrospective": False}, signature_id=signature_id,
        expected_version=cmd.expected_version, command_type="ApproveChange",
    )


# ---------------------------------------------------------------------------
# Tasks — CHG-FR-012/015(partial)
# ---------------------------------------------------------------------------


class AddChangeTaskCommand(CommandEnvelope):
    change_id: uuid.UUID
    expected_version: int
    description: str
    owner_subject_id: uuid.UUID
    due_date: datetime
    dependency_links: list[dict] | None = None
    # CHG-FR-015 (partial): execution evidence known at task-creation time can be attached here.
    # Document 29's own 8-op API list has no operation to update/complete an existing task afterward
    # (unlike CAPA's dedicated `POST /qms/v1/actions/{id}/complete`) -- see SG-073.
    evidence: dict | None = None
    reason: str | None = None


async def add_change_task(session: AsyncSession, cmd: AddChangeTaskCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    change = await _load_change_for_update(session, cmd.change_id, cmd.expected_version)
    if change.state != "IMPLEMENTATION":
        raise InvalidTransitionError("Change tasks can only be added during implementation", current_state=change.state, requested="task")
    if not cmd.description.strip():
        raise ValidationFailedError("description is required")

    task = ChangeTask(
        change_id=change.id, description=cmd.description, owner_subject_id=cmd.owner_subject_id,
        due_date=cmd.due_date, dependency_links=cmd.dependency_links, evidence=cmd.evidence, status="pending",
    )
    session.add(task)

    old_state = change.state
    change.version += 1
    await session.flush()

    return await _write_change_receipt(
        session, cmd=cmd, payload_hash=payload_hash, change=change, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="ChangeImplementationStarted",
        event_payload={"id": str(change.id), "task_id": str(task.id)}, signature_id=None,
        expected_version=cmd.expected_version, command_type="AddChangeTask",
    )


# ---------------------------------------------------------------------------
# Implement — CHG-FR-013(gate)/014(emergency bypass)
# ---------------------------------------------------------------------------


class ImplementChangeCommand(CommandEnvelope):
    change_id: uuid.UUID
    expected_version: int
    reason: str | None = None


async def implement_change(session: AsyncSession, cmd: ImplementChangeCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    change = await _load_change_for_update(session, cmd.change_id, cmd.expected_version)
    if change.state == "APPROVAL":
        pass  # CHG-FR-013: normal path -- pre-approved.
    elif change.emergency and change.state in ("DRAFT", "IMPACT_ASSESSMENT"):
        pass  # CHG-FR-014: controlled emergency path -- bypasses pre-approval, retrospective review required later.
    else:
        raise ChangeNotApprovedError(
            "Change must be approved before implementation, unless it is a declared emergency change",
            current_state=change.state, emergency=change.emergency,
        )

    old_state = change.state
    change.state = "IMPLEMENTATION"
    change.version += 1

    return await _write_change_receipt(
        session, cmd=cmd, payload_hash=payload_hash, change=change, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="ChangeImplementationStarted",
        event_payload={"id": str(change.id)}, signature_id=None, expected_version=cmd.expected_version,
        command_type="ImplementChange",
    )


# ---------------------------------------------------------------------------
# Verify — CHG-FR-016 (signed)
# ---------------------------------------------------------------------------


class VerifyChangeCommand(CommandEnvelope):
    change_id: uuid.UUID
    expected_version: int
    verification_evidence: dict | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None
    reason: str | None = None


async def verify_change(session: AsyncSession, cmd: VerifyChangeCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    change = await _load_change_for_update(session, cmd.change_id, cmd.expected_version)
    if change.state != "IMPLEMENTATION":
        raise InvalidTransitionError("Illegal change transition", current_state=change.state, requested="VERIFICATION")
    if change.validation_impact and change.validation_impact.get("required") and not cmd.verification_evidence:
        raise ValidationIncompleteError("verification_evidence is required -- validation_impact marked validation/requalification as required")

    signature_id = await _resolve_signature(
        session, action="verify", actor_user_id=actor_user_id, change=change,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = change.state
    change.state = "VERIFICATION"
    change.version += 1

    return await _write_change_receipt(
        session, cmd=cmd, payload_hash=payload_hash, change=change, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="ChangeValidationCompleted",
        event_payload={"id": str(change.id)}, signature_id=signature_id, expected_version=cmd.expected_version,
        command_type="VerifyChange",
    )


# ---------------------------------------------------------------------------
# Make effective — CHG-FR-017
# ---------------------------------------------------------------------------


class MakeEffectiveCommand(CommandEnvelope):
    change_id: uuid.UUID
    expected_version: int
    effective_at: datetime
    training_confirmed: bool = False
    reason: str | None = None


async def make_effective_change(session: AsyncSession, cmd: MakeEffectiveCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    change = await _load_change_for_update(session, cmd.change_id, cmd.expected_version)
    if change.state != "VERIFICATION":
        raise InvalidTransitionError("Illegal change transition", current_state=change.state, requested="EFFECTIVE")
    if change.training_impact and change.training_impact.get("required") and not cmd.training_confirmed:
        raise TrainingIncompleteError("training_impact marked training as required and it has not been confirmed complete")
    effective_at = cmd.effective_at if cmd.effective_at.tzinfo is not None else cmd.effective_at.replace(tzinfo=timezone.utc)
    if effective_at < datetime.now(timezone.utc):
        raise EffectiveDateBlockedError("effective_at cannot be in the past -- controlled activation requires a present/future date")

    old_state = change.state
    change.effective_at = cmd.effective_at
    change.state = "EFFECTIVE"
    change.version += 1

    return await _write_change_receipt(
        session, cmd=cmd, payload_hash=payload_hash, change=change, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="ChangeMadeEffective",
        event_payload={"id": str(change.id), "effective_at": cmd.effective_at.isoformat()}, signature_id=None,
        expected_version=cmd.expected_version, command_type="MakeChangeEffective",
    )


# ---------------------------------------------------------------------------
# Close / Cancel — CHG-FR-018/020/021
# ---------------------------------------------------------------------------


class CloseChangeCommand(CommandEnvelope):
    change_id: uuid.UUID
    expected_version: int
    post_implementation_review: dict | None = None
    cancellation_reason: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def close_change(session: AsyncSession, cmd: CloseChangeCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    change = await _load_change_for_update(session, cmd.change_id, cmd.expected_version)

    if cmd.cancellation_reason:
        # CHG-FR-021: cancellation, reusing close()'s signature ceremony -- see change_models.py's
        # module docstring for why there is no separate cancel operation.
        if change.state in NON_CANCELLABLE_STATES:
            raise InvalidTransitionError("Change is already in a terminal state", current_state=change.state, requested="CANCELLED")
        signature_id = await _resolve_signature(
            session, action="close", actor_user_id=actor_user_id, change=change,
            challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
        )
        old_state = change.state
        change.cancel_reason = cmd.cancellation_reason
        change.cancelled_at = datetime.now(timezone.utc)
        change.state = "CANCELLED"
        change.version += 1
        return await _write_change_receipt(
            session, cmd=cmd, payload_hash=payload_hash, change=change, action="Changed", actor_user_id=actor_user_id,
            reason=cmd.cancellation_reason, old_state=old_state, event_type="ChangeClosed",
            event_payload={"id": str(change.id), "state": "CANCELLED"}, signature_id=signature_id,
            expected_version=cmd.expected_version, command_type="CancelChange",
        )

    if change.state != "EFFECTIVE":
        raise InvalidTransitionError("Illegal change transition", current_state=change.state, requested="CLOSED")
    # CHG-FR-018/020: post-implementation review required before closure.
    if not cmd.post_implementation_review or not str(cmd.post_implementation_review.get("conclusion", "")).strip():
        raise EffectiveDateBlockedError("post_implementation_review.conclusion is required before closure")

    signature_id = await _resolve_signature(
        session, action="close", actor_user_id=actor_user_id, change=change,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = change.state
    now = datetime.now(timezone.utc)
    if change.closed_at is None:
        change.closed_at = now
    change.closure_history = [
        *change.closure_history,
        {"post_implementation_review": cmd.post_implementation_review, "closed_at": now.isoformat(),
         "closed_by": str(actor_user_id), "signature_id": str(signature_id) if signature_id else None},
    ]
    change.state = "CLOSED"
    change.version += 1

    return await _write_change_receipt(
        session, cmd=cmd, payload_hash=payload_hash, change=change, action="Closed", actor_user_id=actor_user_id,
        reason=cmd.post_implementation_review.get("conclusion"), old_state=old_state, event_type="ChangeClosed",
        event_payload={"id": str(change.id)}, signature_id=signature_id, expected_version=cmd.expected_version,
        command_type="CloseChange",
    )
