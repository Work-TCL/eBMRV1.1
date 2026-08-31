"""Document 67 (SPEC-SEC-007) Mutation Gateway command handlers: open a security incident, execute an
allowlisted containment action, preserve forensic evidence with chain-of-custody, record the GxP-impact
assessment, and close the incident. Only `close` is Part 11 signed (Document 106 row 140 -> `Approved`,
independent QA Releaser). One PostgreSQL transaction per mutation = domain row + version + audit +
outbox -> MutationReceipt.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.security.incident_models import CONTAINMENT_COMMANDS, ForensicEvidence, SecurityIncident
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    GxpImpactAssessmentRequiredError,
    IncidentContainmentNotAllowedError,
    IncidentEvidenceRequiredError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    SodIndependenceRequiredError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version, audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _write_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, aggregate_type: str,
    aggregate_id: uuid.UUID, version: int, action: str, actor_user_id: uuid.UUID, reason: str | None,
    old_state: str | None, event_type: str, event_payload: dict, expected_version: int | None,
    command_type: str, signature_id: uuid.UUID | None = None,
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


# =================================================================================================
# openSecurityIncident() -- MON-FR-012/013. No signature.
# =================================================================================================


class OpenSecurityIncidentCommand(CommandEnvelope):
    title: str
    severity: str
    detected_at: datetime
    affected_scope: dict = {}
    alert_refs: list = []
    reason: str


async def open_security_incident(
    session: AsyncSession, cmd: OpenSecurityIncidentCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.severity not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        raise ValidationFailedError("severity must be LOW, MEDIUM, HIGH or CRITICAL")
    if not cmd.title or not cmd.reason:
        raise ValidationFailedError("title and reason are required")

    number = "SEC-INC-" + uuid.uuid4().hex[:10].upper()
    incident = SecurityIncident(
        incident_number=number, title=cmd.title, severity=cmd.severity, state="OPEN",
        owner_subject_id=actor_user_id, affected_scope=cmd.affected_scope, alert_refs=cmd.alert_refs,
        detected_at=cmd.detected_at, gxp_impact_state="NOT_ASSESSED", version=1,
    )
    session.add(incident)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="security_incident",
        aggregate_id=incident.id, version=incident.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=None, event_type="SecurityIncidentOpened",
        event_payload={"incident_id": str(incident.id), "incident_number": number, "severity": cmd.severity},
        expected_version=None, command_type="OpenSecurityIncident",
    )


# =================================================================================================
# executeIncidentContainment() -- MON-FR-015. No signature (RBAC + allowlist).
# =================================================================================================


class ExecuteIncidentContainmentCommand(CommandEnvelope):
    incident_id: uuid.UUID
    expected_version: int
    containment_command: str
    target: dict
    reason: str
    outcome: str = "APPLIED"


async def execute_incident_containment(
    session: AsyncSession, cmd: ExecuteIncidentContainmentCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    incident = await session.get(SecurityIncident, cmd.incident_id)
    if incident is None:
        raise NotFoundError("Security incident not found")
    if incident.version != cmd.expected_version:
        raise StaleVersionError("Incident changed since this request was prepared", current_version=incident.version)
    if incident.state not in ("OPEN", "CONTAINED", "RECOVERED"):
        raise InvalidTransitionError(f"Cannot run containment on an incident in state {incident.state}")
    if cmd.containment_command not in CONTAINMENT_COMMANDS:
        raise IncidentContainmentNotAllowedError(
            "containment_command is not on the allowlist (MON-FR-015)", allowed=list(CONTAINMENT_COMMANDS))
    if not cmd.reason:
        raise ValidationFailedError("reason is required")

    old_state = incident.state
    incident.containment_actions = [
        *incident.containment_actions,
        {
            "command": cmd.containment_command, "target": cmd.target, "outcome": cmd.outcome,
            "actor_id": str(actor_user_id), "at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    if incident.state == "OPEN":
        incident.state = "CONTAINED"
        incident.contained_at = datetime.now(timezone.utc)
    incident.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="security_incident",
        aggregate_id=incident.id, version=incident.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="IncidentContainmentExecuted",
        event_payload={"incident_id": str(incident.id), "command": cmd.containment_command, "outcome": cmd.outcome},
        expected_version=cmd.expected_version, command_type="ExecuteIncidentContainment",
    )


# =================================================================================================
# preserveForensicEvidence() -- MON-FR-014. No signature.
# =================================================================================================


class PreserveForensicEvidenceCommand(CommandEnvelope):
    incident_id: uuid.UUID
    source: str
    acquisition_at: datetime
    hash_algorithm: str = "SHA-256"
    digest: str
    object_ref: str | None = None
    custody_note: str
    reason: str


async def preserve_forensic_evidence(
    session: AsyncSession, cmd: PreserveForensicEvidenceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    incident = await session.get(SecurityIncident, cmd.incident_id)
    if incident is None:
        raise NotFoundError("Security incident not found")
    if incident.state == "CLOSED":
        raise InvalidTransitionError("Cannot attach evidence to a closed incident")
    if cmd.hash_algorithm not in ("SHA-256", "SHA-384", "SHA-512"):
        raise ValidationFailedError("hash_algorithm must be SHA-256, SHA-384 or SHA-512")
    if not cmd.digest or not cmd.source or not cmd.reason:
        raise ValidationFailedError("digest, source and reason are required")

    now = datetime.now(timezone.utc)
    evidence = ForensicEvidence(
        incident_id=incident.id, source=cmd.source, acquisition_at=cmd.acquisition_at,
        acquired_by=actor_user_id, hash_algorithm=cmd.hash_algorithm, digest=cmd.digest,
        object_ref=cmd.object_ref,
        chain_of_custody=[{"event": "ACQUIRED", "by": str(actor_user_id), "at": now.isoformat(),
                           "note": cmd.custody_note}],
        version=1,
    )
    session.add(evidence)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="forensic_evidence",
        aggregate_id=evidence.id, version=evidence.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=None, event_type="ForensicEvidencePreserved",
        event_payload={"evidence_id": str(evidence.id), "incident_id": str(incident.id),
                       "hash_algorithm": cmd.hash_algorithm, "digest": cmd.digest},
        expected_version=None, command_type="PreserveForensicEvidence",
    )


# =================================================================================================
# assessGxPIncidentImpact() -- MON-FR-016. RBAC + reason; QMS deviation linkage deferred (see docstring).
# =================================================================================================


class AssessGxpIncidentImpactCommand(CommandEnvelope):
    incident_id: uuid.UUID
    expected_version: int
    impact_state: str  # NO_IMPACT | IMPACT_CONFIRMED
    assessment: dict
    qms_reference: str | None = None
    reason: str


async def assess_gxp_incident_impact(
    session: AsyncSession, cmd: AssessGxpIncidentImpactCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    incident = await session.get(SecurityIncident, cmd.incident_id)
    if incident is None:
        raise NotFoundError("Security incident not found")
    if incident.version != cmd.expected_version:
        raise StaleVersionError("Incident changed since this request was prepared", current_version=incident.version)
    if incident.state == "CLOSED":
        raise InvalidTransitionError("Incident is already closed")
    if cmd.impact_state not in ("NO_IMPACT", "IMPACT_CONFIRMED"):
        raise ValidationFailedError("impact_state must be NO_IMPACT or IMPACT_CONFIRMED")
    if cmd.impact_state == "IMPACT_CONFIRMED" and not cmd.qms_reference:
        raise ValidationFailedError("qms_reference is required when GxP impact is confirmed (MON-FR-016)")
    if not cmd.reason:
        raise ValidationFailedError("reason is required")

    old_state = incident.state
    incident.gxp_impact_state = cmd.impact_state
    incident.gxp_impact = {**cmd.assessment, "qms_reference": cmd.qms_reference,
                           "assessed_by": str(actor_user_id), "assessed_at": datetime.now(timezone.utc).isoformat()}
    incident.state = "GXP_IMPACT_ASSESSED"
    incident.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="security_incident",
        aggregate_id=incident.id, version=incident.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="SecurityGxPImpactAssessed",
        event_payload={"incident_id": str(incident.id), "impact_state": cmd.impact_state,
                       "qms_reference": cmd.qms_reference},
        expected_version=cmd.expected_version, command_type="AssessGxpIncidentImpact",
    )


# =================================================================================================
# closeSecurityIncident() -- Signature: incident/close (Document 106 row 140, independent QA Releaser).
# =================================================================================================


class CloseSecurityIncidentCommand(CommandEnvelope):
    incident_id: uuid.UUID
    expected_version: int
    root_cause: str
    corrective_actions: list
    residual_risk: str
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def close_security_incident(
    session: AsyncSession, cmd: CloseSecurityIncidentCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """Document 106 row 140: closer MUST be independent of the investigator/owner -- enforced here
    against `owner_subject_id` (same real check as Document 63's privileged_session.close). Closure is
    blocked until the GxP-impact assessment is recorded (Document 67 # 14) and at least the containment
    evidence the policy names exists (MON-FR-014)."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    incident = await session.get(SecurityIncident, cmd.incident_id)
    if incident is None:
        raise NotFoundError("Security incident not found")
    if incident.version != cmd.expected_version:
        raise StaleVersionError("Incident changed since this request was prepared", current_version=incident.version)
    if incident.state == "CLOSED":
        raise InvalidTransitionError("Incident is already closed")
    if actor_user_id == incident.owner_subject_id:
        raise SodIndependenceRequiredError(
            "Closer must be independent of the incident owner/investigator (Document 106 row 140)")
    if incident.gxp_impact_state == "NOT_ASSESSED":
        raise GxpImpactAssessmentRequiredError("GxP-impact assessment must be recorded before closure")
    if not incident.containment_actions:
        raise IncidentEvidenceRequiredError("At least one containment action must be recorded before closure")
    if not cmd.root_cause or not cmd.residual_risk or not cmd.reason:
        raise ValidationFailedError("root_cause, residual_risk and reason are required")

    signature_id = await _resolve_signature(
        session, record_type="security_incident", action="close", actor_user_id=actor_user_id,
        record_version=incident.version, record_hash=sha256_hex({"id": str(incident.id), "version": incident.version}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = incident.state
    incident.state = "CLOSED"
    incident.closed_at = datetime.now(timezone.utc)
    incident.root_cause = cmd.root_cause
    incident.corrective_actions = cmd.corrective_actions
    incident.residual_risk = cmd.residual_risk
    incident.signature_id = signature_id
    incident.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="security_incident",
        aggregate_id=incident.id, version=incident.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="SecurityIncidentClosed",
        event_payload={"incident_id": str(incident.id), "residual_risk": cmd.residual_risk},
        expected_version=cmd.expected_version, command_type="CloseSecurityIncident", signature_id=signature_id,
    )


async def _resolve_signature(
    session: AsyncSession, *, record_type: str, action: str, actor_user_id: uuid.UUID,
    record_version: int, record_hash: str, challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type=record_type, action=action)
    if not policy.signature_required:
        return None
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
