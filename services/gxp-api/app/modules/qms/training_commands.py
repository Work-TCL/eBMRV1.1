"""Document 31 (SPEC-QMS-006) -- Training & Personnel Qualification, matching the module's own 8-op API
list exactly (`/training/v1` prefix). Signature ceremony only on assignments create/complete/assess, per
the module's own section 6 API table -- requirements/qualifications/waivers carry no signature column.

TRN-FR-016 (the platform-wide execution gate: "Policy Service blocks operation when training/qualification
inactive") is cross-module by nature -- the enforcement point is in every OTHER module's Mutation Gateway
call, reading this module's own training_assignment/qualification_record state, not an operation this
module's own 8-op API list exposes. Building that wiring now would mean guessing which actions map to
which qualification codes across the whole platform, a decision Document 31 does not make. See
docs/generated/18_SPEC_GAPS.md SG-088.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.qms import training_service
from app.modules.qms.training_models import (
    ASSIGNMENT_ALLOWED_TRANSITIONS,
    SOURCE_TYPES,
    TRAINING_TYPES,
    QualificationRecord,
    TrainingAssignment,
    TrainingRequirement,
    TrainingWaiver,
)
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    StaleVersionError,
    TrainerNotQualifiedError,
    ValidationFailedError,
    WaiverNotAuthorizedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
        audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _load_assignment_for_update(session: AsyncSession, assignment_id: uuid.UUID, expected_version: int) -> TrainingAssignment:
    result = await session.execute(select(TrainingAssignment).where(TrainingAssignment.id == assignment_id).with_for_update())
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise NotFoundError("Training assignment not found")
    if assignment.version != expected_version:
        raise StaleVersionError(
            "Training assignment was modified by another actor since it was read",
            expected_version=expected_version, current_version=assignment.version,
        )
    return assignment


def _record_hash(assignment: TrainingAssignment) -> str:
    return sha256_hex({"id": str(assignment.id), "version": assignment.version})


async def _resolve_and_consume_signature(
    session: AsyncSession, *, record_type: str, action: str, actor_user_id: uuid.UUID, record_version: int,
    record_hash: str, challenge_id: uuid.UUID | None, reauth_password: str | None,
    site_id: uuid.UUID | None = None, disqualified_subject_ids: tuple = (),
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type=record_type, action=action)
    if not policy.signature_required:
        return None
    # SG-138 Kind B, RESOLVED 2026-09-11 (PHASE_3_DEFERRED_DECISIONS.md item A). Document 106 section 9
    # rows 91-93 defer create/complete/assess to "per policy lookup" rather than stating a value; the
    # project owner authored `assess` from the section 8 "verify" family: `Verified`, no fixed role
    # (RBAC-gated), independence "MUST NOT be the performer" read as MUST NOT be the trainee being
    # assessed. `create`/`complete` carry no independence requirement. Enforced the same way every other
    # Document 106 section 9 row with a required role/independence clause is -- resolve_signature_
    # requirement() itself does not read required_role_id/requires_independent_signer.
    await signature_service.enforce_signer_policy(
        session, policy=policy, actor_user_id=actor_user_id, site_id=site_id,
        action_label=f"training_assignment.{action}", disqualified_subject_ids=disqualified_subject_ids,
    )
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"{action} requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=record_version, record_hash=record_hash,
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


async def _write_assignment_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, assignment: TrainingAssignment, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    signature_id: uuid.UUID | None, expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=assignment.site_id, aggregate_type="training_assignment", aggregate_id=assignment.id,
        aggregate_version=assignment.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": assignment.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="training_assignment", aggregate_id=assignment.id,
        aggregate_version=assignment.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=assignment.site_id, command_type=command_type, aggregate_type="training_assignment",
        aggregate_id=assignment.id, expected_version=expected_version, resulting_version=assignment.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=assignment.id, resulting_version=assignment.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create requirement -- TRN-FR-001/002/004/005/012 (source)/017
# ---------------------------------------------------------------------------


class CreateTrainingRequirementCommand(CommandEnvelope):
    site_id: uuid.UUID
    title: str
    source_type: str
    training_type: str
    scope: dict | None = None
    source_reference_id: uuid.UUID | None = None
    content_document_version_id: uuid.UUID | None = None
    recurrence_interval_days: int | None = None
    requires_assessment: bool = False
    pass_score: float | None = None
    required_trainer_qualification_code: str | None = None


async def create_requirement(session: AsyncSession, cmd: CreateTrainingRequirementCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.source_type not in SOURCE_TYPES:
        raise ValidationFailedError("Unrecognized source_type", source_type=cmd.source_type, allowed=list(SOURCE_TYPES))
    if cmd.training_type not in TRAINING_TYPES:
        raise ValidationFailedError("Unrecognized training_type", training_type=cmd.training_type, allowed=list(TRAINING_TYPES))
    if not cmd.title.strip():
        raise ValidationFailedError("title is required")

    requirement = TrainingRequirement(
        site_id=cmd.site_id, title=cmd.title, scope=cmd.scope, source_type=cmd.source_type,
        source_reference_id=cmd.source_reference_id, training_type=cmd.training_type,
        content_document_version_id=cmd.content_document_version_id, recurrence_interval_days=cmd.recurrence_interval_days,
        requires_assessment=cmd.requires_assessment, pass_score=cmd.pass_score,
        required_trainer_qualification_code=cmd.required_trainer_qualification_code,
    )
    session.add(requirement)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=requirement.site_id, aggregate_type="training_requirement", aggregate_id=requirement.id,
        aggregate_version=requirement.version, action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=None, old_value=None, new_value={"title": requirement.title}, signature_id=None,
    )
    await write_outbox_event(
        session, event_type="TrainingRequirementCreated", aggregate_type="training_requirement", aggregate_id=requirement.id,
        aggregate_version=requirement.version, payload={"id": str(requirement.id), "title": requirement.title}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=requirement.site_id, command_type="CreateTrainingRequirement", aggregate_type="training_requirement",
        aggregate_id=requirement.id, expected_version=None, resulting_version=requirement.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=requirement.id, resulting_version=requirement.version,
        audit_event_id=audit_event.id, signature_id=None, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create assignment -- TRN-FR-003/005 (snapshot)/012(trigger)/021
# ---------------------------------------------------------------------------


class CreateTrainingAssignmentCommand(CommandEnvelope):
    requirement_id: uuid.UUID
    subject_id: uuid.UUID
    due_at: datetime | None = None
    retrain_of_assignment_id: uuid.UUID | None = None
    retraining_trigger: str | None = None
    waiver_id: uuid.UUID | None = None
    external_source: str | None = None
    external_reference: str | None = None
    # SG-138 fix: a signature challenge for this "create" action can only be issued for a record that
    # already has an id -- which does not exist before this command runs. assignment_id lets the caller
    # pre-generate the id (via POST /training/v1/assignments/signature-challenges) and hand it back here
    # so the row this command inserts is the exact (id, version=1) pair the challenge was bound to. When
    # omitted (no signature involved), the id is still server-generated as before.
    assignment_id: uuid.UUID | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def create_assignment(session: AsyncSession, cmd: CreateTrainingAssignmentCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    requirement = await training_service.get_requirement(session, cmd.requirement_id)

    assignment = TrainingAssignment(
        id=cmd.assignment_id or uuid.uuid4(),
        site_id=requirement.site_id, subject_id=cmd.subject_id, requirement_id=requirement.id,
        source_version_id=requirement.content_document_version_id, assigned_by_user_id=actor_user_id,
        due_at=cmd.due_at, state="ASSIGNED", retrain_of_assignment_id=cmd.retrain_of_assignment_id,
        retraining_trigger=cmd.retraining_trigger, waiver_id=cmd.waiver_id, external_source=cmd.external_source,
        external_reference=cmd.external_reference,
    )
    session.add(assignment)
    await session.flush()

    signature_id = await _resolve_and_consume_signature(
        session, record_type="training_assignment", action="create", actor_user_id=actor_user_id,
        record_version=assignment.version, record_hash=_record_hash(assignment),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password, site_id=assignment.site_id,
    )

    return await _write_assignment_receipt(
        session, cmd=cmd, payload_hash=payload_hash, assignment=assignment, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="ASSIGNED", event_type="TrainingAssigned",
        event_payload={"id": str(assignment.id), "subject_id": str(assignment.subject_id), "requirement_id": str(requirement.id)},
        signature_id=signature_id, expected_version=None, command_type="CreateTrainingAssignment",
    )


# ---------------------------------------------------------------------------
# Complete -- TRN-FR-006/017
# ---------------------------------------------------------------------------


class CompleteTrainingAssignmentCommand(CommandEnvelope):
    assignment_id: uuid.UUID
    expected_version: int
    trainer_user_id: uuid.UUID | None = None
    evidence_vault_object_id: uuid.UUID | None = None
    equivalency_credit: bool = False
    equivalency_evidence: str | None = None
    equivalency_approved_by_user_id: uuid.UUID | None = None
    reason: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def complete_assignment(session: AsyncSession, cmd: CompleteTrainingAssignmentCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    assignment = await _load_assignment_for_update(session, cmd.assignment_id, cmd.expected_version)
    requirement = await training_service.get_requirement(session, assignment.requirement_id)
    next_state = "ASSESSMENT_PENDING" if requirement.requires_assessment else "COMPLETED"
    if next_state not in ASSIGNMENT_ALLOWED_TRANSITIONS.get(assignment.state, set()):
        raise InvalidTransitionError("Illegal training assignment transition", current_state=assignment.state, requested=next_state)

    if cmd.equivalency_credit and not (cmd.equivalency_evidence and cmd.equivalency_approved_by_user_id):
        raise ValidationFailedError("Equivalency credit requires evidence and an approving subject")

    # TRN-FR-017: trainer/evaluator qualification where the curriculum author configured one.
    if cmd.trainer_user_id is not None and requirement.required_trainer_qualification_code:
        active = await training_service.has_active_qualification(
            session, cmd.trainer_user_id, requirement.required_trainer_qualification_code
        )
        if not active:
            raise TrainerNotQualifiedError(
                "Trainer does not hold the qualification this requirement demands",
                trainer_user_id=str(cmd.trainer_user_id), required_qualification_code=requirement.required_trainer_qualification_code,
            )

    signature_id = await _resolve_and_consume_signature(
        session, record_type="training_assignment", action="complete", actor_user_id=actor_user_id,
        record_version=assignment.version, record_hash=_record_hash(assignment),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password, site_id=assignment.site_id,
    )

    old_state = assignment.state
    assignment.trainer_user_id = cmd.trainer_user_id
    assignment.evidence_vault_object_id = cmd.evidence_vault_object_id
    assignment.equivalency_credit = cmd.equivalency_credit
    assignment.equivalency_evidence = cmd.equivalency_evidence
    assignment.equivalency_approved_by_user_id = cmd.equivalency_approved_by_user_id
    assignment.state = next_state
    if next_state == "COMPLETED":
        assignment.completed_at = datetime.now(timezone.utc)
        assignment.result = "COMPLETED"
    assignment.version += 1

    return await _write_assignment_receipt(
        session, cmd=cmd, payload_hash=payload_hash, assignment=assignment, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="TrainingCompleted" if next_state == "COMPLETED" else "TrainingAssigned",
        event_payload={"id": str(assignment.id), "state": next_state}, signature_id=signature_id,
        expected_version=cmd.expected_version, command_type="CompleteTrainingAssignment",
    )


# ---------------------------------------------------------------------------
# Assess -- TRN-FR-007/008
# ---------------------------------------------------------------------------


class AssessTrainingAssignmentCommand(CommandEnvelope):
    assignment_id: uuid.UUID
    expected_version: int
    passed: bool
    score: float | None = None
    practical_checklist: dict | None = None
    trainer_user_id: uuid.UUID | None = None
    reason: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def assess_assignment(session: AsyncSession, cmd: AssessTrainingAssignmentCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    assignment = await _load_assignment_for_update(session, cmd.assignment_id, cmd.expected_version)
    next_state = "COMPLETED" if cmd.passed else "FAILED"
    if next_state not in ASSIGNMENT_ALLOWED_TRANSITIONS.get(assignment.state, set()):
        raise InvalidTransitionError("Illegal training assignment transition", current_state=assignment.state, requested=next_state)

    requirement = await training_service.get_requirement(session, assignment.requirement_id)
    if cmd.trainer_user_id is not None and requirement.required_trainer_qualification_code:
        active = await training_service.has_active_qualification(
            session, cmd.trainer_user_id, requirement.required_trainer_qualification_code
        )
        if not active:
            raise TrainerNotQualifiedError(
                "Trainer/evaluator does not hold the qualification this requirement demands",
                trainer_user_id=str(cmd.trainer_user_id), required_qualification_code=requirement.required_trainer_qualification_code,
            )

    signature_id = await _resolve_and_consume_signature(
        session, record_type="training_assignment", action="assess", actor_user_id=actor_user_id,
        record_version=assignment.version, record_hash=_record_hash(assignment),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password, site_id=assignment.site_id,
        disqualified_subject_ids=(assignment.subject_id,),
    )

    old_state = assignment.state
    assignment.score = cmd.score
    assignment.practical_checklist = cmd.practical_checklist
    assignment.attempt_number += 1
    if cmd.trainer_user_id is not None:
        assignment.trainer_user_id = cmd.trainer_user_id
    assignment.state = next_state
    assignment.result = next_state
    if next_state == "COMPLETED":
        assignment.completed_at = datetime.now(timezone.utc)

    return await _write_assignment_receipt(
        session, cmd=cmd, payload_hash=payload_hash, assignment=assignment, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="TrainingCompleted" if next_state == "COMPLETED" else "TrainingFailed",
        event_payload={"id": str(assignment.id), "state": next_state, "score": cmd.score}, signature_id=signature_id,
        expected_version=cmd.expected_version, command_type="AssessTrainingAssignment",
    )


# ---------------------------------------------------------------------------
# Create qualification -- TRN-FR-009/010(renewal)
# ---------------------------------------------------------------------------


class CreateQualificationCommand(CommandEnvelope):
    site_id: uuid.UUID
    subject_id: uuid.UUID
    qualification_code: str
    effective_from: datetime
    effective_to: datetime | None = None
    scope: dict | None = None
    evaluator_user_id: uuid.UUID | None = None
    source_assignment_id: uuid.UUID | None = None
    renewed_from_qualification_id: uuid.UUID | None = None


async def create_qualification(session: AsyncSession, cmd: CreateQualificationCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.qualification_code.strip():
        raise ValidationFailedError("qualification_code is required")
    if cmd.source_assignment_id is not None:
        source_assignment = await training_service.get_assignment(session, cmd.source_assignment_id)
        if source_assignment.state != "COMPLETED":
            raise ValidationFailedError("source_assignment_id must reference a COMPLETED assignment")

    state = "QUALIFIED"
    qualification = QualificationRecord(
        site_id=cmd.site_id, subject_id=cmd.subject_id, qualification_code=cmd.qualification_code,
        scope=cmd.scope, effective_from=cmd.effective_from, effective_to=cmd.effective_to, state=state,
        evaluator_user_id=cmd.evaluator_user_id, source_assignment_id=cmd.source_assignment_id,
        renewed_from_qualification_id=cmd.renewed_from_qualification_id,
    )
    session.add(qualification)
    await session.flush()

    old_prior_state = None
    if cmd.renewed_from_qualification_id is not None:
        prior = await session.get(QualificationRecord, cmd.renewed_from_qualification_id)
        if prior is not None:
            old_prior_state = prior.state
            prior.state = "RENEWED"
            prior.version += 1
            await write_audit_event(
                session, site_id=prior.site_id, aggregate_type="qualification_record", aggregate_id=prior.id,
                aggregate_version=prior.version, action="Changed", actor_id=actor_user_id, correlation_id=uuid.uuid4(),
                reason="Superseded by a renewed qualification", old_value={"state": old_prior_state}, new_value={"state": "RENEWED"},
            )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=qualification.site_id, aggregate_type="qualification_record", aggregate_id=qualification.id,
        aggregate_version=qualification.version, action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=None, old_value=None, new_value={"qualification_code": qualification.qualification_code, "state": state},
        signature_id=None,
    )
    await write_outbox_event(
        session, event_type="QualificationIssued", aggregate_type="qualification_record", aggregate_id=qualification.id,
        aggregate_version=qualification.version,
        payload={"id": str(qualification.id), "subject_id": str(qualification.subject_id), "qualification_code": qualification.qualification_code},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=qualification.site_id, command_type="CreateQualification", aggregate_type="qualification_record",
        aggregate_id=qualification.id, expected_version=None, resulting_version=qualification.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=qualification.id, resulting_version=qualification.version,
        audit_event_id=audit_event.id, signature_id=None, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create waiver -- TRN-FR-015
# ---------------------------------------------------------------------------


class CreateWaiverCommand(CommandEnvelope):
    site_id: uuid.UUID
    subject_id: uuid.UUID
    requirement_id: uuid.UUID
    reason: str
    approved_by_user_id: uuid.UUID
    scope: dict | None = None
    expires_at: datetime | None = None


async def create_waiver(session: AsyncSession, cmd: CreateWaiverCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required")
    await training_service.get_requirement(session, cmd.requirement_id)
    # TRN-FR-015 "approver" independence: no dedicated approval step or signature exists for waivers in
    # this module's own API list, so the approving subject cannot be the same person the waiver exempts.
    if cmd.approved_by_user_id == cmd.subject_id:
        raise WaiverNotAuthorizedError("A waiver's approver cannot be the subject the waiver exempts")

    waiver = TrainingWaiver(
        site_id=cmd.site_id, subject_id=cmd.subject_id, requirement_id=cmd.requirement_id, reason=cmd.reason,
        scope=cmd.scope, approved_by_user_id=cmd.approved_by_user_id, expires_at=cmd.expires_at,
    )
    session.add(waiver)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=waiver.site_id, aggregate_type="training_waiver", aggregate_id=waiver.id,
        aggregate_version=waiver.version, action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=cmd.reason, old_value=None, new_value={"subject_id": str(waiver.subject_id)}, signature_id=None,
    )
    await write_outbox_event(
        session, event_type="TrainingWaiverApproved", aggregate_type="training_waiver", aggregate_id=waiver.id,
        aggregate_version=waiver.version, payload={"id": str(waiver.id), "subject_id": str(waiver.subject_id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=waiver.site_id, command_type="CreateWaiver", aggregate_type="training_waiver",
        aggregate_id=waiver.id, expected_version=None, resulting_version=waiver.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=waiver.id, resulting_version=waiver.version,
        audit_event_id=audit_event.id, signature_id=None, correlation_id=correlation_id,
    )
