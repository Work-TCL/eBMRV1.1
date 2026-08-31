"""Document 36 (SPEC-QMS-011) — Recall / Field Action Management command handlers. See
field_action_models.py's module docstring for the state-machine fold-in rationale and the deferred scope
(SG-105/SG-106).
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.qms.field_action_models import (
    ACTION_TYPES,
    TRIGGER_TYPES,
    FieldAction,
    FieldActionCommunication,
    FieldActionReconciliation,
    FieldActionScopeItem,
)
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    CommunicationNotApprovedError,
    EffectivenessRequiredError,
    FieldActionClosureBlockedError,
    FieldActionScopeRequiredError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    ReconciliationIncompleteError,
    ReportabilityAssessmentRequiredError,
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


async def _load_field_action_for_update(session: AsyncSession, field_action_id: uuid.UUID, expected_version: int | None = None) -> FieldAction:
    result = await session.execute(select(FieldAction).where(FieldAction.id == field_action_id).with_for_update())
    field_action = result.scalar_one_or_none()
    if field_action is None:
        raise NotFoundError("Field action not found")
    if expected_version is not None and field_action.version != expected_version:
        raise StaleVersionError(
            "Field action was modified by another actor since it was read",
            expected_version=expected_version, current_version=field_action.version,
        )
    return field_action


def _record_hash(field_action: FieldAction) -> str:
    return sha256_hex({"id": str(field_action.id), "version": field_action.version})


async def _resolve_signature(
    session: AsyncSession, *, action: str, actor_user_id: uuid.UUID, field_action: FieldAction,
    challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type="field_action", action=action)
    if not policy.signature_required:
        return None
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"Field action '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=field_action.version, record_hash=_record_hash(field_action),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


async def _write_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, field_action: FieldAction, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    signature_id: uuid.UUID | None, expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=field_action.site_id, aggregate_type="field_action", aggregate_id=field_action.id,
        aggregate_version=field_action.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": field_action.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="field_action", aggregate_id=field_action.id,
        aggregate_version=field_action.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=field_action.site_id, command_type=command_type, aggregate_type="field_action",
        aggregate_id=field_action.id, expected_version=expected_version, resulting_version=field_action.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=field_action.id, resulting_version=field_action.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create field action — FAR-FR-001/002/005
# ---------------------------------------------------------------------------


class CreateFieldActionCommand(CommandEnvelope):
    site_id: uuid.UUID
    action_number: str
    action_type: str
    trigger_ref: dict
    risk_assessment_ref: uuid.UUID | None = None


async def create_field_action(session: AsyncSession, cmd: CreateFieldActionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.action_type not in ACTION_TYPES:
        raise ValidationFailedError("Unrecognized action_type", action_type=cmd.action_type, allowed=list(ACTION_TYPES))
    if not cmd.trigger_ref or cmd.trigger_ref.get("source_type") not in TRIGGER_TYPES:
        raise ValidationFailedError("trigger_ref.source_type must be one of the recognized trigger types", allowed=list(TRIGGER_TYPES))

    conflict = (await session.execute(select(FieldAction).where(FieldAction.action_number == cmd.action_number))).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("action_number is already in use", action_number=cmd.action_number)

    field_action = FieldAction(
        site_id=cmd.site_id, action_number=cmd.action_number, action_type=cmd.action_type,
        trigger_ref=cmd.trigger_ref, risk_assessment_ref=cmd.risk_assessment_ref, state="ASSESSMENT",
    )
    session.add(field_action)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, field_action=field_action, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="ASSESSMENT", event_type="FieldActionAssessmentOpened",
        event_payload={"id": str(field_action.id), "action_number": field_action.action_number, "action_type": field_action.action_type},
        signature_id=None, expected_version=None, command_type="CreateFieldAction",
    )


# ---------------------------------------------------------------------------
# Scope — FAR-FR-003/004/007/008/019
# ---------------------------------------------------------------------------


class ScopeItemInput(BaseModel):
    product_ref: uuid.UUID | None = None
    lot_batch_serial_refs: dict | None = None
    distribution_ref: dict | None = None
    distribution_hold: bool = False
    action_required: str | None = None


class DefineScopeCommand(CommandEnvelope):
    field_action_id: uuid.UUID
    expected_version: int
    items: list[ScopeItemInput]
    reason: str | None = None


async def define_scope(session: AsyncSession, cmd: DefineScopeCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    field_action = await _load_field_action_for_update(session, cmd.field_action_id, cmd.expected_version)
    if field_action.state not in ("ASSESSMENT", "SCOPE_DEFINITION", "CLOSED"):
        raise InvalidTransitionError("Illegal field action transition", current_state=field_action.state, requested="SCOPE_DEFINITION")
    if not cmd.items:
        raise FieldActionScopeRequiredError("At least one scope item is required")

    is_expansion = field_action.state == "CLOSED"
    for item in cmd.items:
        session.add(
            FieldActionScopeItem(
                site_id=field_action.site_id, field_action_id=field_action.id, product_ref=item.product_ref,
                lot_batch_serial_refs=item.lot_batch_serial_refs, distribution_ref=item.distribution_ref,
                distribution_hold=item.distribution_hold, action_required=item.action_required,
            )
        )

    old_state = field_action.state
    field_action.scope_snapshot_id = uuid.uuid4()
    if is_expansion:
        field_action.revision += 1
        field_action.state = "SCOPE_DEFINITION"
        field_action.closed_at = None
        event_type = "FieldActionScopeExpanded"
    else:
        field_action.state = "SCOPE_DEFINITION"
        event_type = "FieldActionScopeFrozen"
    field_action.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, field_action=field_action, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type=event_type,
        event_payload={"id": str(field_action.id), "item_count": len(cmd.items), "scope_snapshot_id": str(field_action.scope_snapshot_id)},
        signature_id=None, expected_version=cmd.expected_version, command_type="DefineScope",
    )


# ---------------------------------------------------------------------------
# Reportability — FAR-FR-006/015/016 (signature: Document 106 row 105)
# ---------------------------------------------------------------------------


class ReportabilityCommand(CommandEnvelope):
    field_action_id: uuid.UUID
    expected_version: int
    applicable_regimes: list[str]
    rationale: str
    decision: str
    due_date: datetime | None = None
    # FAR-FR-014: regulatory report/submission IDs/dates/acknowledgments.
    submission_reference: str | None = None
    submission_status: str | None = None
    capa_required: bool = False
    capa_rationale: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def assess_field_action_reportability(session: AsyncSession, cmd: ReportabilityCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    field_action = await _load_field_action_for_update(session, cmd.field_action_id, cmd.expected_version)
    if field_action.state != "SCOPE_DEFINITION":
        raise InvalidTransitionError("Illegal field action transition", current_state=field_action.state, requested="REGULATORY_DECISION")
    if not cmd.applicable_regimes:
        raise ValidationFailedError("applicable_regimes must name at least one regime")
    if not cmd.rationale.strip():
        raise ValidationFailedError("rationale is required")
    if cmd.decision not in ("reportable", "not_reportable"):
        raise ValidationFailedError("decision must be 'reportable' or 'not_reportable'", decision=cmd.decision)

    signature_id = await _resolve_signature(
        session, action="reportability", actor_user_id=actor_user_id, field_action=field_action,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = field_action.state
    field_action.reportability_assessment = {
        "applicable_regimes": cmd.applicable_regimes, "rationale": cmd.rationale, "decision": cmd.decision,
        "due_date": cmd.due_date.isoformat() if cmd.due_date else None,
        "submission_reference": cmd.submission_reference, "submission_status": cmd.submission_status,
        "assessed_by": str(actor_user_id), "assessed_at": datetime.now(timezone.utc).isoformat(),
    }
    field_action.capa_required = cmd.capa_required
    field_action.capa_rationale = cmd.capa_rationale
    field_action.state = "REGULATORY_DECISION"
    field_action.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, field_action=field_action, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=old_state, event_type="FieldActionAssessmentOpened",
        event_payload={"id": str(field_action.id), "decision": cmd.decision}, signature_id=signature_id,
        expected_version=cmd.expected_version, command_type="AssessFieldActionReportability",
    )


# ---------------------------------------------------------------------------
# Approve — FAR-FR-009 (signature: Document 106 row 103)
# ---------------------------------------------------------------------------


class ApproveFieldActionCommand(CommandEnvelope):
    field_action_id: uuid.UUID
    expected_version: int
    conclusion: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def approve_field_action(session: AsyncSession, cmd: ApproveFieldActionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    field_action = await _load_field_action_for_update(session, cmd.field_action_id, cmd.expected_version)
    if field_action.state == "SCOPE_DEFINITION":
        raise ReportabilityAssessmentRequiredError("Reportability must be assessed before approval", current_state=field_action.state)
    if field_action.state != "REGULATORY_DECISION":
        raise InvalidTransitionError("Illegal field action transition", current_state=field_action.state, requested="APPROVAL")
    if not cmd.conclusion.strip():
        raise ValidationFailedError("conclusion is required")

    signature_id = await _resolve_signature(
        session, action="approve", actor_user_id=actor_user_id, field_action=field_action,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = field_action.state
    field_action.state = "APPROVAL"
    field_action.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, field_action=field_action, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.conclusion, old_state=old_state, event_type="FieldActionApproved",
        event_payload={"id": str(field_action.id)}, signature_id=signature_id, expected_version=cmd.expected_version,
        command_type="ApproveFieldAction",
    )


# ---------------------------------------------------------------------------
# Communications — FAR-FR-009/010
# ---------------------------------------------------------------------------


class RecordCommunicationCommand(CommandEnvelope):
    field_action_id: uuid.UUID
    expected_version: int
    recipient: str
    message: str
    package_version: int = 1
    channel: str | None = None
    sent_at: datetime | None = None
    delivery_status: str = "pending"
    ack_status: str | None = None


async def record_field_action_communication(session: AsyncSession, cmd: RecordCommunicationCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    field_action = await _load_field_action_for_update(session, cmd.field_action_id, cmd.expected_version)
    if field_action.state == "REGULATORY_DECISION":
        raise CommunicationNotApprovedError("The communication package must be approved before notifications are sent", current_state=field_action.state)
    if field_action.state not in ("APPROVAL", "EXECUTION_NOTIFICATION"):
        raise InvalidTransitionError("Illegal field action transition", current_state=field_action.state, requested="EXECUTION_NOTIFICATION")
    if not cmd.recipient.strip() or not cmd.message.strip():
        raise ValidationFailedError("recipient and message are required")

    communication = FieldActionCommunication(
        site_id=field_action.site_id, field_action_id=field_action.id, package_version=cmd.package_version,
        recipient=cmd.recipient, channel=cmd.channel, message=cmd.message, sent_at=cmd.sent_at,
        delivery_status=cmd.delivery_status, ack_status=cmd.ack_status,
    )
    session.add(communication)
    await session.flush()

    old_state = field_action.state
    field_action.state = "EXECUTION_NOTIFICATION"
    field_action.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, field_action=field_action, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="FieldActionNotificationSent",
        event_payload={"id": str(field_action.id), "communication_id": str(communication.id)}, signature_id=None,
        expected_version=cmd.expected_version, command_type="RecordFieldActionCommunication",
    )


# ---------------------------------------------------------------------------
# Reconcile — FAR-FR-011/012
# ---------------------------------------------------------------------------


class ReconcileCommand(CommandEnvelope):
    field_action_id: uuid.UUID
    expected_version: int
    affected_count: int
    contacted_count: int = 0
    returned_count: int = 0
    corrected_count: int = 0
    destroyed_count: int = 0
    unavailable_count: int = 0
    outstanding_count: int = 0


async def reconcile_field_action(session: AsyncSession, cmd: ReconcileCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    field_action = await _load_field_action_for_update(session, cmd.field_action_id, cmd.expected_version)
    if field_action.state not in ("EXECUTION_NOTIFICATION", "RECONCILIATION"):
        raise InvalidTransitionError("Illegal field action transition", current_state=field_action.state, requested="RECONCILIATION")
    if cmd.affected_count < 0:
        raise ValidationFailedError("affected_count cannot be negative")

    reconciliation = (
        await session.execute(select(FieldActionReconciliation).where(FieldActionReconciliation.field_action_id == field_action.id))
    ).scalar_one_or_none()
    if reconciliation is None:
        reconciliation = FieldActionReconciliation(site_id=field_action.site_id, field_action_id=field_action.id, version=1)
        session.add(reconciliation)
    else:
        reconciliation.version += 1
    reconciliation.affected_count = cmd.affected_count
    reconciliation.contacted_count = cmd.contacted_count
    reconciliation.returned_count = cmd.returned_count
    reconciliation.corrected_count = cmd.corrected_count
    reconciliation.destroyed_count = cmd.destroyed_count
    reconciliation.unavailable_count = cmd.unavailable_count
    reconciliation.outstanding_count = cmd.outstanding_count
    await session.flush()

    old_state = field_action.state
    field_action.state = "RECONCILIATION"
    field_action.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, field_action=field_action, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="FieldActionUnitReturned",
        event_payload={"id": str(field_action.id), "outstanding_count": cmd.outstanding_count}, signature_id=None,
        expected_version=cmd.expected_version, command_type="ReconcileFieldAction",
    )


# ---------------------------------------------------------------------------
# Effectiveness — FAR-FR-013
# ---------------------------------------------------------------------------


class EffectivenessCommand(CommandEnvelope):
    field_action_id: uuid.UUID
    expected_version: int
    result: str
    evidence: dict | None = None


async def record_field_action_effectiveness(session: AsyncSession, cmd: EffectivenessCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    field_action = await _load_field_action_for_update(session, cmd.field_action_id, cmd.expected_version)
    if field_action.state != "RECONCILIATION":
        raise InvalidTransitionError("Illegal field action transition", current_state=field_action.state, requested="EFFECTIVENESS")
    if cmd.result not in ("pass", "fail"):
        raise ValidationFailedError("result must be 'pass' or 'fail'", result=cmd.result)

    old_state = field_action.state
    field_action.effectiveness_check = {
        "result": cmd.result, "evidence": cmd.evidence, "verified_by": str(actor_user_id),
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    field_action.state = "EFFECTIVENESS"
    field_action.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, field_action=field_action, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="FieldActionEffectivenessCompleted",
        event_payload={"id": str(field_action.id), "result": cmd.result}, signature_id=None,
        expected_version=cmd.expected_version, command_type="RecordFieldActionEffectiveness",
    )


# ---------------------------------------------------------------------------
# Close — FAR-FR-018 (signature: Document 106 row 104)
# ---------------------------------------------------------------------------


class CloseFieldActionCommand(CommandEnvelope):
    field_action_id: uuid.UUID
    expected_version: int
    conclusion: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def close_field_action(session: AsyncSession, cmd: CloseFieldActionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    field_action = await _load_field_action_for_update(session, cmd.field_action_id, cmd.expected_version)
    if field_action.state in ("ASSESSMENT", "SCOPE_DEFINITION", "REGULATORY_DECISION", "APPROVAL", "EXECUTION_NOTIFICATION", "RECONCILIATION"):
        raise FieldActionClosureBlockedError("Field action has not completed reconciliation and effectiveness yet", current_state=field_action.state)
    if field_action.state != "EFFECTIVENESS":
        raise InvalidTransitionError("Illegal field action transition", current_state=field_action.state, requested="CLOSED")
    if not cmd.conclusion.strip():
        raise ValidationFailedError("conclusion is required")

    if not field_action.effectiveness_check:
        raise EffectivenessRequiredError("Effectiveness must be verified before closure")

    reconciliation = (
        await session.execute(select(FieldActionReconciliation).where(FieldActionReconciliation.field_action_id == field_action.id))
    ).scalar_one_or_none()
    if reconciliation is None or reconciliation.outstanding_count > 0:
        raise ReconciliationIncompleteError("Reconciliation must show no outstanding units before closure")

    signature_id = await _resolve_signature(
        session, action="close", actor_user_id=actor_user_id, field_action=field_action,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = field_action.state
    field_action.state = "CLOSED"
    field_action.closed_at = datetime.now(timezone.utc)
    field_action.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, field_action=field_action, action="Closed", actor_user_id=actor_user_id,
        reason=cmd.conclusion, old_state=old_state, event_type="FieldActionClosed",
        event_payload={"id": str(field_action.id)}, signature_id=signature_id, expected_version=cmd.expected_version,
        command_type="CloseFieldAction",
    )
