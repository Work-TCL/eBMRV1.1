"""Document 27 (SPEC-QMS-002) — the buildable slice of CAPA Management: the linear OPEN -> PLAN ->
IMPLEMENTATION -> IMPLEMENTATION_VERIFIED -> EFFECTIVENESS_MONITORING -> EFFECTIVENESS_REVIEW -> CLOSED
pipeline Document 27 §4 describes, plus EFFECTIVENESS_FAILED -> REOPENED/IMPLEMENTATION and
CLOSED -> REOPENED. Every state-changing operation matches the module's own 8-op API list exactly; no
additional operation is exposed (see capa_models.py's module docstring and docs/generated/18_SPEC_GAPS.md
SG-063/SG-064/SG-065 for what is deliberately not built this pass).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.qms.capa_models import (
    ACTION_TYPES,
    CAPA_ALLOWED_TRANSITIONS,
    CAPA_SCOPE_TYPES,
    CAPA_SOURCE_TYPES,
    EFFECTIVENESS_RESULTS,
    NON_CANCELLABLE_STATES,
    CapaAction,
    CapaEffectivenessCheck,
    CapaRecord,
)
from app.modules.qms.signature_support import enforce_signer_policy
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    ActionDependencyOpenError,
    ActionEvidenceRequiredError,
    CapaClosureBlockedError,
    CapaRootCauseRequiredError,
    CapaSourceRequiredError,
    EffectivenessPlanRequiredError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
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


async def _load_capa_for_update(session: AsyncSession, capa_id: uuid.UUID, expected_version: int) -> CapaRecord:
    result = await session.execute(select(CapaRecord).where(CapaRecord.id == capa_id).with_for_update())
    capa = result.scalar_one_or_none()
    if capa is None:
        raise NotFoundError("CAPA record not found")
    if capa.version != expected_version:
        raise StaleVersionError(
            "CAPA record was modified by another actor since it was read",
            expected_version=expected_version, current_version=capa.version,
        )
    return capa


async def _load_action_for_update(session: AsyncSession, action_id: uuid.UUID, expected_version: int) -> CapaAction:
    result = await session.execute(select(CapaAction).where(CapaAction.id == action_id).with_for_update())
    action = result.scalar_one_or_none()
    if action is None:
        raise NotFoundError("CAPA action not found")
    if action.version != expected_version:
        raise StaleVersionError(
            "CAPA action was modified by another actor since it was read",
            expected_version=expected_version, current_version=action.version,
        )
    return action


def _record_hash(capa: CapaRecord) -> str:
    return sha256_hex({"id": str(capa.id), "version": capa.version})


async def _resolve_signature(
    session: AsyncSession, *, action: str, actor_user_id: uuid.UUID, capa: CapaRecord,
    challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type="capa_record", action=action)
    if not policy.signature_required:
        return None
    # Document 106 section 9 row 80 (`close`): `Approved` by "QA Approver for the record class", "MUST be
    # independent of the investigator/owner" (Document 107 IND-005 / SOD-006 shape). The CAPA record's
    # only stored identity is `owner_subject_id`; enforced here, same bespoke pattern as close_deviation().
    await enforce_signer_policy(
        session, policy=policy, actor_user_id=actor_user_id, site_id=capa.site_id,
        action_label=f"capa.{action}", disqualified_subject_ids=(capa.owner_subject_id,),
    )
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"CAPA '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=capa.version, record_hash=_record_hash(capa),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


async def _write_capa_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, capa: CapaRecord, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    signature_id: uuid.UUID | None, expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=capa.site_id, aggregate_type="capa_record", aggregate_id=capa.id,
        aggregate_version=capa.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": capa.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="capa_record", aggregate_id=capa.id,
        aggregate_version=capa.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=capa.site_id, command_type=command_type, aggregate_type="capa_record",
        aggregate_id=capa.id, expected_version=expected_version, resulting_version=capa.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=capa.id, resulting_version=capa.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create — CAPA-FR-001/002/003/004/019 (partial)
# ---------------------------------------------------------------------------


class CreateCapaCommand(CommandEnvelope):
    site_id: uuid.UUID
    capa_number: str
    source_type: str
    source_id: uuid.UUID
    source_version: int | None = None
    problem_statement: str
    risk_class: str
    owner_subject_id: uuid.UUID
    target_date: datetime
    root_cause_ref: dict
    scope_type: str = "site"
    scope_refs: list | None = None
    recurrence_links: list | None = None


async def create_capa(session: AsyncSession, cmd: CreateCapaCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.source_type not in CAPA_SOURCE_TYPES:
        raise CapaSourceRequiredError("Unrecognized CAPA source_type", source_type=cmd.source_type, allowed=list(CAPA_SOURCE_TYPES))
    if not cmd.root_cause_ref or not (cmd.root_cause_ref.get("investigation_ref") or cmd.root_cause_ref.get("proactive_rationale")):
        raise CapaRootCauseRequiredError("root_cause_ref requires investigation_ref or proactive_rationale")
    if not cmd.problem_statement.strip():
        raise ValidationFailedError("problem_statement is required")
    if cmd.scope_type not in CAPA_SCOPE_TYPES:
        raise ValidationFailedError("Unrecognized scope_type", scope_type=cmd.scope_type, allowed=list(CAPA_SCOPE_TYPES))

    conflict = (await session.execute(select(CapaRecord).where(CapaRecord.capa_number == cmd.capa_number))).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("capa_number is already in use", capa_number=cmd.capa_number)

    capa = CapaRecord(
        site_id=cmd.site_id, capa_number=cmd.capa_number, source_type=cmd.source_type, source_id=cmd.source_id,
        source_version=cmd.source_version, problem_statement=cmd.problem_statement, scope_type=cmd.scope_type,
        scope_refs=cmd.scope_refs, risk_class=cmd.risk_class, root_cause_ref=cmd.root_cause_ref,
        owner_subject_id=cmd.owner_subject_id, target_date=cmd.target_date, recurrence_links=cmd.recurrence_links,
        state="OPEN",
    )
    session.add(capa)
    await session.flush()

    return await _write_capa_receipt(
        session, cmd=cmd, payload_hash=payload_hash, capa=capa, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="OPEN", event_type="CAPAOpened",
        event_payload={"id": str(capa.id), "capa_number": capa.capa_number}, signature_id=None,
        expected_version=None, command_type="CreateCapa",
    )


# ---------------------------------------------------------------------------
# Plan — CAPA-FR-005/006/010(partial)
# ---------------------------------------------------------------------------


class PlanCapaCommand(CommandEnvelope):
    capa_id: uuid.UUID
    expected_version: int
    corrective_action: dict
    preventive_action: dict | None = None
    effectiveness_plan: dict | None = None
    reason: str | None = None


async def plan_capa(session: AsyncSession, cmd: PlanCapaCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    capa = await _load_capa_for_update(session, cmd.capa_id, cmd.expected_version)
    if "PLAN" not in CAPA_ALLOWED_TRANSITIONS.get(capa.state, set()):
        raise InvalidTransitionError("Illegal CAPA transition", current_state=capa.state, requested="PLAN")
    if not cmd.corrective_action or not str(cmd.corrective_action.get("description", "")).strip():
        raise ValidationFailedError("corrective_action.description is required")

    old_state = capa.state
    capa.corrective_action = cmd.corrective_action
    capa.preventive_action = cmd.preventive_action
    capa.effectiveness_plan = cmd.effectiveness_plan
    capa.state = "PLAN"
    capa.version += 1

    return await _write_capa_receipt(
        session, cmd=cmd, payload_hash=payload_hash, capa=capa, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="CAPAPlanApproved", event_payload={"id": str(capa.id)},
        signature_id=None, expected_version=cmd.expected_version, command_type="PlanCapa",
    )


# ---------------------------------------------------------------------------
# Add action — CAPA-FR-005/006/007/008(partial, SG-063)
# ---------------------------------------------------------------------------


class AddCapaActionCommand(CommandEnvelope):
    capa_id: uuid.UUID
    expected_version: int
    action_type: str
    description: str
    owner_subject_id: uuid.UUID
    due_date: datetime
    dependency_links: list | None = None
    reason: str | None = None


async def add_capa_action(session: AsyncSession, cmd: AddCapaActionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    capa = await _load_capa_for_update(session, cmd.capa_id, cmd.expected_version)
    entering = capa.state == "PLAN"
    if not entering and capa.state != "IMPLEMENTATION":
        raise InvalidTransitionError("Illegal CAPA transition", current_state=capa.state, requested="IMPLEMENTATION")
    if cmd.action_type not in ACTION_TYPES:
        raise ValidationFailedError("Unrecognized action_type", action_type=cmd.action_type, allowed=list(ACTION_TYPES))
    if not cmd.description.strip():
        raise ValidationFailedError("description is required")

    action = CapaAction(
        capa_id=capa.id, action_type=cmd.action_type, description=cmd.description,
        owner_subject_id=cmd.owner_subject_id, due_date=cmd.due_date, dependency_links=cmd.dependency_links,
        state="open",
    )
    session.add(action)

    old_state = capa.state
    capa.state = "IMPLEMENTATION"
    capa.version += 1
    await session.flush()

    receipt = await _write_capa_receipt(
        session, cmd=cmd, payload_hash=payload_hash, capa=capa, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="CAPAActionAssigned",
        event_payload={"id": str(capa.id), "action_id": str(action.id)}, signature_id=None,
        expected_version=cmd.expected_version, command_type="AddCapaAction",
    )
    return receipt


# ---------------------------------------------------------------------------
# Complete action — CAPA-FR-007/008(partial)/009
# ---------------------------------------------------------------------------


class CompleteCapaActionCommand(CommandEnvelope):
    action_id: uuid.UUID
    expected_version: int
    implementation_evidence: dict
    verified_by: uuid.UUID
    verification_status: str = "verified"
    reason: str | None = None


async def complete_capa_action(session: AsyncSession, cmd: CompleteCapaActionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    action = await _load_action_for_update(session, cmd.action_id, cmd.expected_version)
    if action.state != "open":
        raise InvalidTransitionError("CAPA action is not open", current_state=action.state, requested="completed")
    if not cmd.implementation_evidence or not str(cmd.implementation_evidence.get("description", "")).strip():
        raise ActionEvidenceRequiredError("implementation_evidence.description is required -- not checkbox-only")

    # CAPA-FR-008 (partial, SG-063): only an internal dependency on another capa_action within the same
    # CAPA is enforced -- Change Control/Training/Validation/Software-Release/Equipment don't exist as
    # entities in this codebase to verify against.
    for link in action.dependency_links or []:
        if link.get("dependency_type") == "capa_action":
            dep_id = link.get("reference_id")
            if dep_id:
                dep_action = await session.get(CapaAction, uuid.UUID(dep_id))
                if dep_action is not None and dep_action.state != "completed":
                    raise ActionDependencyOpenError("A dependent CAPA action is not yet completed", dependency_action_id=dep_id)

    capa = await session.get(CapaRecord, action.capa_id)
    if capa is None:
        raise NotFoundError("CAPA record not found")

    old_action_version = action.version
    action.implementation_evidence = cmd.implementation_evidence
    action.state = "completed"
    action.verification_status = cmd.verification_status
    action.verified_by = cmd.verified_by
    action.verified_at = datetime.now(timezone.utc)
    action.version += 1

    open_actions = (
        await session.execute(select(CapaAction).where(CapaAction.capa_id == capa.id, CapaAction.state == "open"))
    ).scalars().all()
    old_state = capa.state
    if not open_actions and capa.state == "IMPLEMENTATION":
        capa.state = "IMPLEMENTATION_VERIFIED"
        capa.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=capa.site_id, aggregate_type="capa_action", aggregate_id=action.id,
        aggregate_version=action.version, action="Changed", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=cmd.reason, old_value={"state": "open"}, new_value={"state": "completed"},
    )
    await write_outbox_event(
        session, event_type="CAPAActionCompleted", aggregate_type="capa_action", aggregate_id=action.id,
        aggregate_version=action.version, payload={"id": str(action.id), "capa_id": str(capa.id)}, correlation_id=correlation_id,
    )
    if capa.state != old_state:
        await write_outbox_event(
            session, event_type="CAPAActionCompleted", aggregate_type="capa_record", aggregate_id=capa.id,
            aggregate_version=capa.version, payload={"id": str(capa.id), "state": capa.state}, correlation_id=correlation_id,
            causation_id=audit_event.id,
        )
    receipt = await record_command_receipt(
        session, site_id=capa.site_id, command_type="CompleteCapaAction", aggregate_type="capa_action",
        aggregate_id=action.id, expected_version=old_action_version, resulting_version=action.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=action.id, resulting_version=action.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Effectiveness — CAPA-FR-010/011/012
# ---------------------------------------------------------------------------


class EffectivenessCommand(CommandEnvelope):
    capa_id: uuid.UUID
    expected_version: int
    check_id: uuid.UUID | None = None
    criterion: str | None = None
    data_source: str | None = None
    observation_start: datetime | None = None
    observation_end: datetime | None = None
    due_date: datetime | None = None
    result: str | None = None
    evidence: dict | None = None
    reviewer_subject_id: uuid.UUID | None = None
    reason: str | None = None


async def record_effectiveness(session: AsyncSession, cmd: EffectivenessCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    capa = await _load_capa_for_update(session, cmd.capa_id, cmd.expected_version)

    if cmd.result is None:
        # Defining criteria (CAPA-FR-010) -- entering EFFECTIVENESS_MONITORING for the first time, or
        # adding another check while already monitoring.
        entering = capa.state == "IMPLEMENTATION_VERIFIED"
        if not entering and capa.state not in ("EFFECTIVENESS_MONITORING", "REOPENED"):
            raise InvalidTransitionError("Illegal CAPA transition", current_state=capa.state, requested="EFFECTIVENESS_MONITORING")
        if not cmd.criterion or not cmd.data_source or not cmd.observation_start or not cmd.observation_end or not cmd.due_date:
            raise ValidationFailedError("criterion/data_source/observation_start/observation_end/due_date are all required to define an effectiveness check")
        check = CapaEffectivenessCheck(
            capa_id=capa.id, criterion=cmd.criterion, data_source=cmd.data_source,
            observation_start=cmd.observation_start, observation_end=cmd.observation_end, due_date=cmd.due_date,
        )
        session.add(check)
        old_state = capa.state
        capa.state = "EFFECTIVENESS_MONITORING"
        capa.version += 1
        await session.flush()
        return await _write_capa_receipt(
            session, cmd=cmd, payload_hash=payload_hash, capa=capa, action="Changed", actor_user_id=actor_user_id,
            reason=cmd.reason, old_state=old_state, event_type="CAPAEffectivenessStarted",
            event_payload={"id": str(capa.id), "check_id": str(check.id)}, signature_id=None,
            expected_version=cmd.expected_version, command_type="DefineEffectivenessCheck",
        )

    # Recording a result (CAPA-FR-011/012).
    if cmd.result not in EFFECTIVENESS_RESULTS:
        raise ValidationFailedError("Unrecognized result", result=cmd.result, allowed=list(EFFECTIVENESS_RESULTS))
    if capa.state not in ("EFFECTIVENESS_MONITORING",):
        raise InvalidTransitionError("CAPA is not in effectiveness monitoring", current_state=capa.state, requested="effectiveness result")
    if cmd.check_id is None:
        raise EffectivenessPlanRequiredError("check_id is required to record a result -- no effectiveness check was ever defined")
    check = await session.get(CapaEffectivenessCheck, cmd.check_id)
    if check is None or check.capa_id != capa.id:
        raise EffectivenessPlanRequiredError("No matching effectiveness check exists for this CAPA")
    if not cmd.evidence:
        raise ValidationFailedError("evidence is required to record an effectiveness result")

    check.result = cmd.result
    check.evidence = cmd.evidence
    check.reviewer_subject_id = cmd.reviewer_subject_id or actor_user_id
    check.evaluated_at = datetime.now(timezone.utc)

    old_state = capa.state
    capa.state = "EFFECTIVENESS_FAILED" if cmd.result == "fail" else "EFFECTIVENESS_REVIEW"
    capa.version += 1

    event_type = "CAPAEffectivenessFailed" if cmd.result == "fail" else "CAPAEffectivenessStarted"
    return await _write_capa_receipt(
        session, cmd=cmd, payload_hash=payload_hash, capa=capa, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type=event_type,
        event_payload={"id": str(capa.id), "check_id": str(check.id), "result": cmd.result}, signature_id=None,
        expected_version=cmd.expected_version, command_type="RecordEffectivenessResult",
    )


# ---------------------------------------------------------------------------
# Extend — CAPA-FR-013
# ---------------------------------------------------------------------------


class ExtendCapaCommand(CommandEnvelope):
    capa_id: uuid.UUID
    expected_version: int
    new_target_date: datetime
    reason: str
    risk_review: str


async def extend_capa(session: AsyncSession, cmd: ExtendCapaCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    capa = await _load_capa_for_update(session, cmd.capa_id, cmd.expected_version)
    if capa.state in ("CLOSED", "CANCELLED"):
        raise InvalidTransitionError("CAPA is in a terminal state and cannot be extended", current_state=capa.state, requested="extend")
    if not cmd.reason.strip() or not cmd.risk_review.strip():
        raise ValidationFailedError("reason and risk_review are required")
    current_target = capa.target_date if capa.target_date.tzinfo is not None else capa.target_date.replace(tzinfo=timezone.utc)
    new_target = cmd.new_target_date if cmd.new_target_date.tzinfo is not None else cmd.new_target_date.replace(tzinfo=timezone.utc)
    if new_target <= current_target:
        raise ValidationFailedError("new_target_date must be later than the current target date")

    old_state = capa.state
    capa.extension_history = [
        *capa.extension_history,
        {
            "previous_target_date": capa.target_date.isoformat(), "new_target_date": cmd.new_target_date.isoformat(),
            "reason": cmd.reason, "risk_review": cmd.risk_review, "approved_by": str(actor_user_id),
            "approved_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    capa.target_date = cmd.new_target_date
    capa.version += 1

    return await _write_capa_receipt(
        session, cmd=cmd, payload_hash=payload_hash, capa=capa, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="CAPAOpened",
        event_payload={"id": str(capa.id), "new_target_date": cmd.new_target_date.isoformat()}, signature_id=None,
        expected_version=cmd.expected_version, command_type="ExtendCapa",
    )


# ---------------------------------------------------------------------------
# Close / Cancel — CAPA-FR-015/016/021(partial, SG-065)
# ---------------------------------------------------------------------------


class CloseCapaCommand(CommandEnvelope):
    capa_id: uuid.UUID
    expected_version: int
    conclusion: str | None = None
    cancellation_reason: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def close_capa(session: AsyncSession, cmd: CloseCapaCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    capa = await _load_capa_for_update(session, cmd.capa_id, cmd.expected_version)

    if cmd.cancellation_reason:
        # CAPA-FR-016: cancellation, reusing close()'s signature ceremony -- see capa_models.py's module
        # docstring for why there is no separate cancel operation.
        if capa.state in NON_CANCELLABLE_STATES:
            raise InvalidTransitionError("CAPA is already in a terminal state", current_state=capa.state, requested="CANCELLED")
        signature_id = await _resolve_signature(
            session, action="close", actor_user_id=actor_user_id, capa=capa,
            challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
        )
        old_state = capa.state
        capa.cancel_reason = cmd.cancellation_reason
        capa.cancelled_at = datetime.now(timezone.utc)
        capa.state = "CANCELLED"
        capa.version += 1
        return await _write_capa_receipt(
            session, cmd=cmd, payload_hash=payload_hash, capa=capa, action="Changed", actor_user_id=actor_user_id,
            reason=cmd.cancellation_reason, old_state=old_state, event_type="CAPAClosed",
            event_payload={"id": str(capa.id), "state": "CANCELLED"}, signature_id=signature_id,
            expected_version=cmd.expected_version, command_type="CancelCapa",
        )

    if capa.state not in ("EFFECTIVENESS_REVIEW", "REOPENED"):
        raise InvalidTransitionError("Illegal CAPA transition", current_state=capa.state, requested="CLOSED")

    # CAPA-FR-015: all mandatory actions and effectiveness complete before QA closure.
    open_actions = (
        await session.execute(select(CapaAction).where(CapaAction.capa_id == capa.id, CapaAction.state == "open"))
    ).scalars().all()
    if open_actions:
        raise CapaClosureBlockedError("Open CAPA actions remain", open_action_count=len(open_actions))
    checks = (
        await session.execute(select(CapaEffectivenessCheck).where(CapaEffectivenessCheck.capa_id == capa.id))
    ).scalars().all()
    if not checks or not any(c.result == "pass" for c in checks):
        raise CapaClosureBlockedError("No passed effectiveness check exists for this CAPA")
    if not cmd.conclusion or not cmd.conclusion.strip():
        raise CapaClosureBlockedError("A final written conclusion is required for QA closure")

    signature_id = await _resolve_signature(
        session, action="close", actor_user_id=actor_user_id, capa=capa,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = capa.state
    now = datetime.now(timezone.utc)
    if capa.closed_at is None:
        capa.closed_at = now
    capa.closure_history = [
        *capa.closure_history,
        {"conclusion": cmd.conclusion, "closed_at": now.isoformat(), "closed_by": str(actor_user_id),
         "signature_id": str(signature_id) if signature_id else None},
    ]
    capa.state = "CLOSED"
    capa.version += 1

    return await _write_capa_receipt(
        session, cmd=cmd, payload_hash=payload_hash, capa=capa, action="Closed", actor_user_id=actor_user_id,
        reason=cmd.conclusion, old_state=old_state, event_type="CAPAClosed",
        event_payload={"id": str(capa.id)}, signature_id=signature_id,
        expected_version=cmd.expected_version, command_type="CloseCapa",
    )


# ---------------------------------------------------------------------------
# Reopen — CAPA-FR-012/017
# ---------------------------------------------------------------------------


class ReopenCapaCommand(CommandEnvelope):
    capa_id: uuid.UUID
    expected_version: int
    reason: str
    new_evidence: str


async def reopen_capa(session: AsyncSession, cmd: ReopenCapaCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    capa = await _load_capa_for_update(session, cmd.capa_id, cmd.expected_version)
    if "REOPENED" not in CAPA_ALLOWED_TRANSITIONS.get(capa.state, set()):
        raise InvalidTransitionError("Illegal CAPA transition", current_state=capa.state, requested="REOPENED")
    if not cmd.reason.strip() or not cmd.new_evidence.strip():
        raise ValidationFailedError("reason and new_evidence are required to reopen a CAPA")

    old_state = capa.state
    capa.reopen_history = [
        *capa.reopen_history,
        {
            "previous_closed_at": capa.closed_at.isoformat() if capa.closed_at else None,
            "reason": cmd.reason, "new_evidence": cmd.new_evidence, "reopened_by": str(actor_user_id),
            "reopened_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    capa.state = "REOPENED"
    capa.version += 1

    return await _write_capa_receipt(
        session, cmd=cmd, payload_hash=payload_hash, capa=capa, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="CAPAReopened", event_payload={"id": str(capa.id)},
        signature_id=None, expected_version=cmd.expected_version, command_type="ReopenCapa",
    )
