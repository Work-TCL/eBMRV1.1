"""Document 61 (SPEC-SEC-001) Mutation Gateway command handlers. See models.py's module docstring for
why `mapSecurityControl()`, `calculateSecurityRisk()`, `acceptResidualSecurityRisk()` and
`triggerThreatModelReview()` write onto the 4 owned tables' fields/JSONB history instead of dedicated
tables.

SG-161 RESOLVED_APPROVED 2026-09-14 (project-owner-directed): Document 106 gets no row at all for risk
acceptance and only "elevated authority defined by the record class" (no dispatch table) for exception
opening. Resolution: both use the "Security Risk Approver" role already seeded anticipating exactly this
gap, and both require a signer independent of whoever's judgment is being approved.

For `acceptResidualSecurityRisk()`, independence is checked against `residual_risk["calculated_by"]`
(the SEC-THR-014 risk-scoring actor already recorded by `calculate_security_risk()` -- no new column
needed). For `openSecurityException()`, independence has no meaning in a single-step create+sign command
(the signer and the record's only stored actor are the same person by construction) -- per project-owner
direction this pass, the endpoint is split exactly like SG-160's correction-removal fix: an unsigned
`requestSecurityException()` records who identified the need (`opened_by`), and a new, signed
`approveSecurityException()` is checked for independence against that requester and moves the record from
PENDING_APPROVAL to OPEN.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.security.models import (
    DEPLOYMENT_PROFILES,
    THREAT_TYPES,
    SecurityControl,
    SecurityException,
    SecurityThreat,
    SecurityThreatModelVersion,
)
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    MissingSignatureError,
    NotFoundError,
    SecurityRiskInputIncompleteError,
    StaleVersionError,
    ThreatScopeInvalidError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

MAPPING_TYPES = ("PREVENTIVE", "DETECTIVE", "RECOVERY")
RISK_STAGES = ("INHERENT", "RESIDUAL")


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
        audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _write_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, aggregate_type: str, aggregate_id: uuid.UUID,
    version: int, action: str, actor_user_id: uuid.UUID, reason: str | None, old_state: str | None,
    event_type: str, event_payload: dict, expected_version: int | None, command_type: str,
    signature_id: uuid.UUID | None = None,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state} if old_state else None, new_value=event_payload,
        signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type=command_type, aggregate_type=aggregate_type,
        aggregate_id=aggregate_id, expected_version=expected_version, resulting_version=version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=aggregate_id, resulting_version=version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


async def _resolve_signature(
    session: AsyncSession, *, record_type: str, action: str, actor_user_id: uuid.UUID,
    record_version: int, record_hash: str, challenge_id: uuid.UUID | None, reauth_password: str | None,
    disqualified_subject_ids: tuple[uuid.UUID | None, ...] = (),
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type=record_type, action=action)
    if not policy.signature_required:
        return None
    await signature_service.enforce_signer_policy(
        session, policy=policy, actor_user_id=actor_user_id, site_id=None,
        action_label=f"{record_type}.{action}", disqualified_subject_ids=disqualified_subject_ids,
    )
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"{record_type} '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=record_version, record_hash=record_hash,
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


def _threat_hash(threat: SecurityThreat) -> str:
    return sha256_hex({"id": str(threat.id), "version": threat.version, "state": threat.state})


def _exception_hash(exception: SecurityException) -> str:
    return sha256_hex({"id": str(exception.id), "version": exception.version, "state": exception.state})


async def _get_threat_model_for_update(session: AsyncSession, tmv_id: uuid.UUID, expected_version: int) -> SecurityThreatModelVersion:
    tmv = await session.get(SecurityThreatModelVersion, tmv_id)
    if tmv is None:
        raise NotFoundError("Security threat model version not found")
    if tmv.version != expected_version:
        raise StaleVersionError("Threat model version changed since this request was prepared", current_version=tmv.version)
    return tmv


async def _get_threat_for_update(session: AsyncSession, threat_id: uuid.UUID, expected_version: int) -> SecurityThreat:
    threat = await session.get(SecurityThreat, threat_id)
    if threat is None:
        raise NotFoundError("Security threat not found")
    if threat.version != expected_version:
        raise StaleVersionError("Security threat changed since this request was prepared", current_version=threat.version)
    return threat


# ---------------------------------------------------------------------------------------------------
# SecurityThreatModelVersion -- SEC-THR-001/002/003/004/005/019/025.
# ---------------------------------------------------------------------------------------------------


class CreateThreatModelVersionCommand(CommandEnvelope):
    system_version: str
    methodology_version: str
    deployment_profile: str
    scope: dict | None = None
    assets: dict | None = None
    boundaries: dict | None = None
    reason: str | None = None


async def create_threat_model_version(
    session: AsyncSession, cmd: CreateThreatModelVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.deployment_profile not in DEPLOYMENT_PROFILES:
        raise ThreatScopeInvalidError("Unrecognized deployment_profile", allowed=list(DEPLOYMENT_PROFILES))

    tmv = SecurityThreatModelVersion(
        system_version=cmd.system_version, methodology_version=cmd.methodology_version,
        deployment_profile=cmd.deployment_profile, scope=cmd.scope, assets=cmd.assets, boundaries=cmd.boundaries,
        state="DRAFT", version=1,
    )
    session.add(tmv)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="security_threat_model_version",
        aggregate_id=tmv.id, version=tmv.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=None, event_type="ThreatModelDraftCreated",
        event_payload={"threat_model_version_id": str(tmv.id), "deployment_profile": tmv.deployment_profile},
        expected_version=None, command_type="CreateThreatModelVersion",
    )


class TriggerThreatModelReviewCommand(CommandEnvelope):
    threat_model_version_id: uuid.UUID
    expected_version: int
    change_id: str
    trigger_type: str
    affected_modules: list[str] = []
    reason: str | None = None


async def trigger_threat_model_review(
    session: AsyncSession, cmd: TriggerThreatModelReviewCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    tmv = await _get_threat_model_for_update(session, cmd.threat_model_version_id, cmd.expected_version)
    if not cmd.trigger_type:
        raise ValidationFailedError("trigger_type is required")

    tmv.review_triggers = [
        *tmv.review_triggers,
        {
            "change_id": cmd.change_id, "trigger_type": cmd.trigger_type, "affected_modules": cmd.affected_modules,
            "triggered_at": datetime.now(timezone.utc).isoformat(), "triggered_by": str(actor_user_id),
        },
    ]
    tmv.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="security_threat_model_version",
        aggregate_id=tmv.id, version=tmv.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=tmv.state, event_type="ThreatModelReviewRequired",
        event_payload={"threat_model_version_id": str(tmv.id), "change_id": cmd.change_id, "trigger_type": cmd.trigger_type},
        expected_version=cmd.expected_version, command_type="TriggerThreatModelReview",
    )


# ---------------------------------------------------------------------------------------------------
# SecurityThreat -- SEC-THR-003/004/005/006/007/008/009/010/011/012/013/014/015.
# ---------------------------------------------------------------------------------------------------


class RegisterThreatCommand(CommandEnvelope):
    threat_model_version_id: uuid.UUID
    asset_or_boundary: str
    threat_type: str
    abuse_case: str
    attack_preconditions: dict | None = None
    impacted_attributes: list[str] = []
    evidence: dict | None = None
    reason: str | None = None


async def register_threat(
    session: AsyncSession, cmd: RegisterThreatCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    tmv = await session.get(SecurityThreatModelVersion, cmd.threat_model_version_id)
    if tmv is None:
        raise NotFoundError("Security threat model version not found")
    if cmd.threat_type not in THREAT_TYPES:
        raise ValidationFailedError("Unrecognized threat_type", allowed=list(THREAT_TYPES))
    if not cmd.abuse_case:
        raise ValidationFailedError("abuse_case is required")

    threat = SecurityThreat(
        threat_model_version_id=tmv.id, asset_or_boundary=cmd.asset_or_boundary, threat_type=cmd.threat_type,
        abuse_case=cmd.abuse_case, attack_preconditions=cmd.attack_preconditions,
        impacted_attributes=cmd.impacted_attributes, evidence=cmd.evidence, state="OPEN", version=1,
    )
    session.add(threat)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="security_threat",
        aggregate_id=threat.id, version=threat.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=None, event_type="ThreatRegistered",
        event_payload={"threat_id": str(threat.id), "threat_model_version_id": str(tmv.id), "threat_type": threat.threat_type},
        expected_version=None, command_type="RegisterThreat",
    )


class MapSecurityControlCommand(CommandEnvelope):
    threat_id: uuid.UUID
    expected_version: int
    control_code: str
    mapping_type: str
    implementation_refs: dict | None = None
    objective: str | None = None
    implementation_owner: str | None = None
    evidence_source: str | None = None
    test_owner: str | None = None
    framework_mappings: dict | None = None
    reason: str | None = None


async def map_security_control(
    session: AsyncSession, cmd: MapSecurityControlCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    threat = await _get_threat_for_update(session, cmd.threat_id, cmd.expected_version)
    if cmd.mapping_type not in MAPPING_TYPES:
        raise ValidationFailedError("Unrecognized mapping_type", allowed=list(MAPPING_TYPES))

    # get-or-create against the control catalogue -- see models.py module docstring.
    control = (
        await session.execute(select(SecurityControl).where(SecurityControl.control_code == cmd.control_code))
    ).scalar_one_or_none()
    if control is None:
        control = SecurityControl(
            control_code=cmd.control_code, objective=cmd.objective, implementation_owner=cmd.implementation_owner,
            evidence_source=cmd.evidence_source, test_owner=cmd.test_owner, framework_mappings=cmd.framework_mappings,
        )
        session.add(control)
        await session.flush()
    else:
        if cmd.objective is not None:
            control.objective = cmd.objective
        if cmd.implementation_owner is not None:
            control.implementation_owner = cmd.implementation_owner
        if cmd.evidence_source is not None:
            control.evidence_source = cmd.evidence_source
        if cmd.test_owner is not None:
            control.test_owner = cmd.test_owner
        if cmd.framework_mappings is not None:
            control.framework_mappings = cmd.framework_mappings

    old_state = threat.state
    threat.control_mappings = [
        *threat.control_mappings,
        {
            "control_id": str(control.id), "control_code": control.control_code, "mapping_type": cmd.mapping_type,
            "implementation_refs": cmd.implementation_refs, "mapped_at": datetime.now(timezone.utc).isoformat(),
            "mapped_by": str(actor_user_id),
        },
    ]
    threat.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="security_threat",
        aggregate_id=threat.id, version=threat.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="SecurityControlMapped",
        event_payload={"threat_id": str(threat.id), "control_code": control.control_code, "mapping_type": cmd.mapping_type},
        expected_version=cmd.expected_version, command_type="MapSecurityControl",
    )


class CalculateSecurityRiskCommand(CommandEnvelope):
    threat_id: uuid.UUID
    expected_version: int
    risk_stage: str
    impact_inputs: dict
    likelihood_inputs: dict
    methodology: str
    rating: dict
    reason: str | None = None


async def calculate_security_risk(
    session: AsyncSession, cmd: CalculateSecurityRiskCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """SEC-THR-014: no risk-scoring formula/matrix is defined in any approved baseline (checked
    `app/modules/qms/risk_commands.py` -- `score` is caller-supplied there too, the established platform
    precedent, not a fresh gap). `rating` is the caller's own computed impact/likelihood/exposure
    conclusion; this function persists it deterministically and reproducibly, appending the prior value
    onto `risk_calculation_history` rather than silently overwriting it (Document 33 RSK-FR-012 precedent).
    """
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    threat = await _get_threat_for_update(session, cmd.threat_id, cmd.expected_version)
    if cmd.risk_stage not in RISK_STAGES:
        raise ValidationFailedError("Unrecognized risk_stage", allowed=list(RISK_STAGES))
    if not cmd.impact_inputs or not cmd.likelihood_inputs or not cmd.rating:
        raise SecurityRiskInputIncompleteError("impact_inputs, likelihood_inputs and rating are all required")

    record = {
        "impact_inputs": cmd.impact_inputs, "likelihood_inputs": cmd.likelihood_inputs,
        "methodology": cmd.methodology, "rating": cmd.rating,
        "calculated_at": datetime.now(timezone.utc).isoformat(), "calculated_by": str(actor_user_id),
    }
    old_state = threat.state
    field = "inherent_risk" if cmd.risk_stage == "INHERENT" else "residual_risk"
    prior = getattr(threat, field)
    if prior is not None:
        threat.risk_calculation_history = [*threat.risk_calculation_history, {"risk_stage": cmd.risk_stage, **prior}]
    setattr(threat, field, record)
    threat.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="security_threat",
        aggregate_id=threat.id, version=threat.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="SecurityRiskCalculated",
        event_payload={"threat_id": str(threat.id), "risk_stage": cmd.risk_stage, "rating": cmd.rating},
        expected_version=cmd.expected_version, command_type="CalculateSecurityRisk",
    )


class AcceptResidualSecurityRiskCommand(CommandEnvelope):
    # Document 61 `# 4` names this input `risk_id` -- there is no separate SecurityRiskAssessment table
    # (see models.py module docstring), so it is the owning `security_threat.id`.
    risk_id: uuid.UUID
    expected_version: int
    rationale: str
    expiry_review_date: datetime | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def accept_residual_security_risk(
    session: AsyncSession, cmd: AcceptResidualSecurityRiskCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """SG-161 RESOLVED_APPROVED 2026-09-14: "Security Risk Approver" signs, independent of whoever
    calculated the residual risk being accepted (`residual_risk["calculated_by"]` -- SEC-THR-014's own
    risk-scoring actor, already recorded; no new column needed)."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    threat = await _get_threat_for_update(session, cmd.risk_id, cmd.expected_version)
    if threat.residual_risk is None:
        raise SecurityRiskInputIncompleteError("Residual risk must be calculated before it can be accepted")

    calculated_by = threat.residual_risk.get("calculated_by")
    signature_id = await _resolve_signature(
        session, record_type="security_threat", action="accept_risk", actor_user_id=actor_user_id,
        record_version=threat.version, record_hash=_threat_hash(threat), challenge_id=cmd.challenge_id,
        reauth_password=cmd.reauth_password,
        disqualified_subject_ids=(uuid.UUID(calculated_by) if calculated_by else None,),
    )

    old_state = threat.state
    threat.residual_risk_acceptance = {
        "rationale": cmd.rationale, "accepted_by": str(actor_user_id),
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "expiry_review_date": cmd.expiry_review_date.isoformat() if cmd.expiry_review_date else None,
        "signature_id": str(signature_id) if signature_id else None,
    }
    threat.state = "RISK_ACCEPTED"
    threat.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="security_threat",
        aggregate_id=threat.id, version=threat.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=old_state, event_type="ResidualSecurityRiskAccepted",
        event_payload={"threat_id": str(threat.id), "state": threat.state},
        expected_version=cmd.expected_version, command_type="AcceptResidualSecurityRisk", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------------------------------
# SecurityException -- SEC-THR-023.
# ---------------------------------------------------------------------------------------------------


class RequestSecurityExceptionCommand(CommandEnvelope):
    control_or_requirement: str
    reason: str
    expiry: datetime
    risk_assessment_ref: dict | None = None
    compensating_controls: dict | None = None
    remediation_target: dict | None = None


async def request_security_exception(
    session: AsyncSession, cmd: RequestSecurityExceptionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """SG-161 RESOLVED_APPROVED 2026-09-14: unsigned request half of the request/approve split
    (`signature_required=False` for `security_exception.request`, same "deliberately no signature" data
    pattern as SG-119). Records `opened_by` as the requester independence is later checked against."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.expiry <= datetime.now(timezone.utc):
        raise ValidationFailedError("expiry must be in the future -- exceptions are time-bounded (SEC-THR-023)")

    await _resolve_signature(
        session, record_type="security_exception", action="request", actor_user_id=actor_user_id, record_version=1,
        record_hash=sha256_hex({"control_or_requirement": cmd.control_or_requirement}),
        challenge_id=None, reauth_password=None,
    )

    exception = SecurityException(
        control_or_requirement=cmd.control_or_requirement, risk_assessment_ref=cmd.risk_assessment_ref,
        compensating_controls=cmd.compensating_controls, reason=cmd.reason, expiry=cmd.expiry,
        remediation_target=cmd.remediation_target, approvers=[],
        state="PENDING_APPROVAL", opened_by=actor_user_id, version=1,
    )
    session.add(exception)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="security_exception",
        aggregate_id=exception.id, version=exception.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=None, event_type="SecurityExceptionRequested",
        event_payload={"exception_id": str(exception.id), "control_or_requirement": exception.control_or_requirement},
        expected_version=None, command_type="RequestSecurityException",
    )


class ApproveSecurityExceptionCommand(CommandEnvelope):
    expected_version: int
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def approve_security_exception(
    session: AsyncSession, exception_id: uuid.UUID, cmd: ApproveSecurityExceptionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """SG-161 RESOLVED_APPROVED 2026-09-14: "Security Risk Approver" signs, independent of whoever
    requested the exception (`opened_by`) -- Document 106 row 133's "MUST be independent of the
    requester", now checked, not merely stated."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    exception = await session.get(SecurityException, exception_id)
    if exception is None:
        raise NotFoundError("Security exception not found")
    if exception.version != cmd.expected_version:
        raise StaleVersionError("Security exception changed since this request was prepared", current_version=exception.version)
    if exception.state != "PENDING_APPROVAL":
        raise ValidationFailedError(f"Security exception is '{exception.state}', not PENDING_APPROVAL")

    signature_id = await _resolve_signature(
        session, record_type="security_exception", action="approve", actor_user_id=actor_user_id,
        record_version=exception.version, record_hash=_exception_hash(exception), challenge_id=cmd.challenge_id,
        reauth_password=cmd.reauth_password, disqualified_subject_ids=(exception.opened_by,),
    )

    old_state = exception.state
    exception.approvers = [*exception.approvers, {"user_id": str(actor_user_id), "signature_id": str(signature_id) if signature_id else None}]
    exception.state = "OPEN"
    exception.signature_id = signature_id
    exception.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="security_exception",
        aggregate_id=exception.id, version=exception.version, action="Approved", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="SecurityExceptionApproved",
        event_payload={"exception_id": str(exception.id), "state": exception.state},
        expected_version=cmd.expected_version, command_type="ApproveSecurityException", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------------------------------
# generateSecurityControlMatrix() -- read-only, SEC-THR-013/027. No owned table (see module docstring).
# ---------------------------------------------------------------------------------------------------


async def generate_security_control_matrix(
    session: AsyncSession, threat_model_version_id: uuid.UUID, deployment_profile: str | None = None,
) -> dict:
    tmv = await session.get(SecurityThreatModelVersion, threat_model_version_id)
    if tmv is None:
        raise NotFoundError("Security threat model version not found")
    if deployment_profile is not None and deployment_profile != tmv.deployment_profile:
        raise ValidationFailedError("deployment_profile does not match this threat model version")

    threats = (
        await session.execute(select(SecurityThreat).where(SecurityThreat.threat_model_version_id == tmv.id))
    ).scalars().all()
    control_codes = {m["control_code"] for t in threats for m in t.control_mappings}
    controls = {}
    if control_codes:
        rows = (await session.execute(select(SecurityControl).where(SecurityControl.control_code.in_(control_codes)))).scalars().all()
        controls = {c.control_code: c for c in rows}

    entries = []
    for threat in threats:
        for mapping in threat.control_mappings:
            control = controls.get(mapping["control_code"])
            entries.append({
                "threat_id": str(threat.id), "threat_type": threat.threat_type, "abuse_case": threat.abuse_case,
                "residual_risk": threat.residual_risk, "control_code": mapping["control_code"],
                "mapping_type": mapping["mapping_type"],
                "implementation_owner": control.implementation_owner if control else None,
                "evidence_source": control.evidence_source if control else None,
                "test_owner": control.test_owner if control else None,
            })

    return {
        "threat_model_version_id": str(tmv.id), "deployment_profile": tmv.deployment_profile,
        "generated_at": datetime.now(timezone.utc).isoformat(), "entries": entries,
    }
