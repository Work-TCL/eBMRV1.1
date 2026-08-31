"""Document 33 (SPEC-QMS-008) — Risk Management command handlers. See risk_models.py's module docstring
for the state-machine fold-in rationale, the methodology reuse of the rules module, and the deferred scope
(SG-099/SG-100).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.qms.risk_models import (
    RISK_TYPES,
    RiskAssessmentVersion,
    RiskRecord,
)
from app.modules.rules.models import RuleDefinition
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    ResidualRiskReviewRequiredError,
    RiskAcceptanceNotAuthorizedError,
    RiskInputIncompleteError,
    RiskMethodNotReleasedError,
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


async def _load_risk_for_update(session: AsyncSession, risk_id: uuid.UUID, expected_version: int) -> RiskRecord:
    result = await session.execute(select(RiskRecord).where(RiskRecord.id == risk_id).with_for_update())
    risk = result.scalar_one_or_none()
    if risk is None:
        raise NotFoundError("Risk record not found")
    if risk.version != expected_version:
        raise StaleVersionError(
            "Risk record was modified by another actor since it was read",
            expected_version=expected_version, current_version=risk.version,
        )
    return risk


async def _load_current_version(session: AsyncSession, risk_id: uuid.UUID) -> RiskAssessmentVersion | None:
    result = await session.execute(
        select(RiskAssessmentVersion).where(
            RiskAssessmentVersion.risk_record_id == risk_id, RiskAssessmentVersion.is_current.is_(True)
        )
    )
    return result.scalar_one_or_none()


async def _resolve_methodology(session: AsyncSession, methodology_id: uuid.UUID) -> RuleDefinition:
    """RSK-FR-002/015: methodology selection reuses the existing rules module (Document 08) rather than a
    second methodology master (AG-05). A methodology reference that does not resolve to a released rule
    is rejected -- RISK_METHOD_NOT_RELEASED (Document 33 §16).
    """
    rule = await session.get(RuleDefinition, methodology_id)
    if rule is None or rule.status != "released":
        raise RiskMethodNotReleasedError(
            "methodology_id does not reference a released risk methodology", methodology_id=str(methodology_id)
        )
    return rule


def _record_hash(risk: RiskRecord) -> str:
    return sha256_hex({"id": str(risk.id), "version": risk.version})


async def _resolve_signature(
    session: AsyncSession, *, action: str, actor_user_id: uuid.UUID, risk: RiskRecord,
    challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type="risk_record", action=action)
    if not policy.signature_required:
        return None
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"Risk '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=risk.version, record_hash=_record_hash(risk),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


async def _write_risk_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, risk: RiskRecord, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    signature_id: uuid.UUID | None, expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=risk.site_id, aggregate_type="risk_record", aggregate_id=risk.id,
        aggregate_version=risk.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": risk.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="risk_record", aggregate_id=risk.id,
        aggregate_version=risk.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=risk.site_id, command_type=command_type, aggregate_type="risk_record",
        aggregate_id=risk.id, expected_version=expected_version, resulting_version=risk.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=risk.id, resulting_version=risk.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create risk — RSK-FR-001/003/011
# ---------------------------------------------------------------------------


class CreateRiskCommand(CommandEnvelope):
    site_id: uuid.UUID
    risk_number: str
    risk_type: str
    hazard_problem: str
    potential_effect: str
    owner_subject_id: uuid.UUID
    context: dict | None = None
    methodology_id: uuid.UUID | None = None


async def create_risk(session: AsyncSession, cmd: CreateRiskCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.risk_type not in RISK_TYPES:
        raise ValidationFailedError("Unrecognized risk_type", risk_type=cmd.risk_type, allowed=list(RISK_TYPES))
    if not cmd.hazard_problem.strip() or not cmd.potential_effect.strip():
        raise RiskInputIncompleteError("hazard_problem and potential_effect are required")

    conflict = (await session.execute(select(RiskRecord).where(RiskRecord.risk_number == cmd.risk_number))).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("risk_number is already in use", risk_number=cmd.risk_number)

    if cmd.methodology_id is not None:
        await _resolve_methodology(session, cmd.methodology_id)

    risk = RiskRecord(
        site_id=cmd.site_id, risk_number=cmd.risk_number, risk_type=cmd.risk_type,
        hazard_problem=cmd.hazard_problem, potential_effect=cmd.potential_effect,
        owner_subject_id=cmd.owner_subject_id, context=cmd.context, methodology_id=cmd.methodology_id,
        state="DRAFT",
    )
    session.add(risk)
    await session.flush()

    return await _write_risk_receipt(
        session, cmd=cmd, payload_hash=payload_hash, risk=risk, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="DRAFT", event_type="RiskCreated",
        event_payload={"id": str(risk.id), "risk_number": risk.risk_number, "risk_type": risk.risk_type},
        signature_id=None, expected_version=None, command_type="CreateRisk",
    )


# ---------------------------------------------------------------------------
# Add assessment (initial or residual, folded per state) — RSK-FR-004/006/012
# ---------------------------------------------------------------------------


class AddAssessmentCommand(CommandEnvelope):
    risk_id: uuid.UUID
    expected_version: int
    scoring_inputs: dict
    score: dict
    methodology_id: uuid.UUID | None = None
    reason: str | None = None


async def add_assessment(session: AsyncSession, cmd: AddAssessmentCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    risk = await _load_risk_for_update(session, cmd.risk_id, cmd.expected_version)
    if not cmd.scoring_inputs or not cmd.score:
        raise RiskInputIncompleteError("scoring_inputs and score are required")

    old_state = risk.state
    is_new_cycle = risk.state in ("DRAFT", "NEW_VERSION")
    is_residual = risk.state == "CONTROLS_MITIGATION"
    if not is_new_cycle and not is_residual:
        raise InvalidTransitionError(
            "Illegal risk transition", current_state=risk.state, requested="INITIAL_ASSESSMENT/RESIDUAL_ASSESSMENT"
        )

    if is_new_cycle:
        methodology_id = cmd.methodology_id or risk.methodology_id
        if methodology_id is None:
            raise RiskMethodNotReleasedError("methodology_id is required before the first assessment of a cycle")
        rule = await _resolve_methodology(session, methodology_id)
        risk.methodology_id = methodology_id

        prior_cycles = (
            await session.execute(
                select(RiskAssessmentVersion.cycle_number)
                .where(RiskAssessmentVersion.risk_record_id == risk.id)
                .order_by(RiskAssessmentVersion.cycle_number.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        cycle_number = (prior_cycles or 0) + 1

        version = RiskAssessmentVersion(
            site_id=risk.site_id, risk_record_id=risk.id, cycle_number=cycle_number,
            methodology_id=methodology_id, methodology_version=rule.semantic_version,
            scoring_inputs=cmd.scoring_inputs, initial_score=cmd.score, is_current=True,
        )
        session.add(version)
        await session.flush()

        risk.state = "INITIAL_ASSESSMENT"
        risk.version += 1

        event_type = "RiskAssessmentCompleted" if cycle_number == 1 else "RiskReassessed"
        event_payload = {"id": str(risk.id), "version_id": str(version.id), "cycle_number": cycle_number}
    else:
        version = await _load_current_version(session, risk.id)
        if version is None:
            raise InvalidTransitionError("No current assessment version to update", current_state=risk.state, requested="RESIDUAL_ASSESSMENT")
        version.residual_inputs = cmd.scoring_inputs
        version.residual_score = cmd.score

        risk.state = "RESIDUAL_ASSESSMENT"
        risk.version += 1

        event_type = "RiskAssessmentCompleted"
        event_payload = {"id": str(risk.id), "version_id": str(version.id), "cycle_number": version.cycle_number}

    return await _write_risk_receipt(
        session, cmd=cmd, payload_hash=payload_hash, risk=risk, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type=event_type, event_payload=event_payload,
        signature_id=None, expected_version=cmd.expected_version, command_type="AddAssessment",
    )


# ---------------------------------------------------------------------------
# Add controls / mitigation actions — RSK-FR-005/008
# ---------------------------------------------------------------------------


class AddControlsCommand(CommandEnvelope):
    risk_id: uuid.UUID
    expected_version: int
    controls: list[dict]
    mitigation_actions: list[dict] | None = None
    reason: str | None = None


async def add_controls(session: AsyncSession, cmd: AddControlsCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    risk = await _load_risk_for_update(session, cmd.risk_id, cmd.expected_version)
    if risk.state != "INITIAL_ASSESSMENT":
        raise InvalidTransitionError("Illegal risk transition", current_state=risk.state, requested="CONTROLS_MITIGATION")
    if not cmd.controls:
        raise RiskInputIncompleteError("controls must name at least one preventive/detective control")

    version = await _load_current_version(session, risk.id)
    if version is None:
        raise InvalidTransitionError("No current assessment version to update", current_state=risk.state, requested="CONTROLS_MITIGATION")
    version.controls = cmd.controls
    version.mitigation_actions = cmd.mitigation_actions

    old_state = risk.state
    risk.state = "CONTROLS_MITIGATION"
    risk.version += 1

    return await _write_risk_receipt(
        session, cmd=cmd, payload_hash=payload_hash, risk=risk, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="RiskMitigationRequired",
        event_payload={"id": str(risk.id), "version_id": str(version.id)},
        signature_id=None, expected_version=cmd.expected_version, command_type="AddControls",
    )


# ---------------------------------------------------------------------------
# Accept — RSK-FR-007
# ---------------------------------------------------------------------------


class AcceptRiskCommand(CommandEnvelope):
    risk_id: uuid.UUID
    expected_version: int
    accepted_role: str
    rationale: str
    next_review_due_at: datetime | None = None


async def accept_risk(session: AsyncSession, cmd: AcceptRiskCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    risk = await _load_risk_for_update(session, cmd.risk_id, cmd.expected_version)
    if risk.state != "RESIDUAL_ASSESSMENT":
        raise InvalidTransitionError("Illegal risk transition", current_state=risk.state, requested="ACCEPTED")
    if not cmd.rationale.strip() or not cmd.accepted_role.strip():
        raise RiskAcceptanceNotAuthorizedError("accepted_role and rationale are required to accept a risk")

    version = await _load_current_version(session, risk.id)
    if version is None or not version.residual_score:
        raise ResidualRiskReviewRequiredError("Residual assessment must be completed before acceptance")

    acceptance_record = {
        "accepted_role": cmd.accepted_role, "rationale": cmd.rationale,
        "accepted_by": str(actor_user_id), "accepted_at": datetime.now(timezone.utc).isoformat(),
    }
    version.acceptance_criteria = {"residual_score": version.residual_score}
    version.acceptance = acceptance_record

    old_state = risk.state
    risk.state = "ACCEPTED"
    risk.next_review_due_at = cmd.next_review_due_at
    risk.version += 1

    return await _write_risk_receipt(
        session, cmd=cmd, payload_hash=payload_hash, risk=risk, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=old_state, event_type="RiskAccepted",
        event_payload={"id": str(risk.id), "version_id": str(version.id)},
        signature_id=None, expected_version=cmd.expected_version, command_type="AcceptRisk",
    )


# ---------------------------------------------------------------------------
# Review — RSK-FR-013/014 (signature: Document 106 row 97)
# ---------------------------------------------------------------------------


class ReviewRiskCommand(CommandEnvelope):
    risk_id: uuid.UUID
    expected_version: int
    trigger_type: str  # "periodic" | "triggered"
    outcome: str  # "still_current" | "reassessment_required"
    rationale: str
    trigger_source_ref: dict | None = None
    next_review_due_at: datetime | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def review_risk(session: AsyncSession, cmd: ReviewRiskCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    risk = await _load_risk_for_update(session, cmd.risk_id, cmd.expected_version)
    if risk.state != "ACCEPTED":
        raise InvalidTransitionError("Illegal risk transition", current_state=risk.state, requested="PERIODIC_REVIEW/TRIGGERED_REVIEW")
    if cmd.trigger_type not in ("periodic", "triggered"):
        raise ValidationFailedError("trigger_type must be 'periodic' or 'triggered'", trigger_type=cmd.trigger_type)
    if cmd.outcome not in ("still_current", "reassessment_required"):
        raise ValidationFailedError("outcome must be 'still_current' or 'reassessment_required'", outcome=cmd.outcome)
    if not cmd.rationale.strip():
        raise ValidationFailedError("rationale is required")

    signature_id = await _resolve_signature(
        session, action="review", actor_user_id=actor_user_id, risk=risk,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    version = await _load_current_version(session, risk.id)
    review_record = {
        "trigger_type": cmd.trigger_type, "outcome": cmd.outcome, "rationale": cmd.rationale,
        "trigger_source_ref": cmd.trigger_source_ref, "reviewed_by": str(actor_user_id),
        "reviewed_at": datetime.now(timezone.utc).isoformat(), "signature_id": str(signature_id) if signature_id else None,
    }
    if version is not None:
        version.review_history = [*version.review_history, review_record]

    old_state = risk.state
    if cmd.outcome == "reassessment_required":
        risk.state = "NEW_VERSION"
        if version is not None:
            version.is_current = False
            version.closed_at = datetime.now(timezone.utc)
    else:
        risk.state = "ACCEPTED"
        risk.next_review_due_at = cmd.next_review_due_at
    risk.version += 1

    return await _write_risk_receipt(
        session, cmd=cmd, payload_hash=payload_hash, risk=risk, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=old_state, event_type="RiskReviewTriggered",
        event_payload={"id": str(risk.id), "trigger_type": cmd.trigger_type, "outcome": cmd.outcome},
        signature_id=signature_id, expected_version=cmd.expected_version, command_type="ReviewRisk",
    )
