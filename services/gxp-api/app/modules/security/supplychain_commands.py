"""Document 68 (SPEC-SEC-008) Mutation Gateway command handlers for the vulnerability register:
`registerVulnerability`, `assessVulnerabilitySeverity`, `approveVulnerabilityException`.

`register` and `assess` are RBAC-gated only (no Document 106 row). `approve_vulnerability_exception()`
is Part 11 signed per Document 106 row 141 -- but that row's role ("Elevated authority defined by the
record class") is the same unresolvable shape as Document 61 row 133 (SG-161), so **no signature policy
row is seeded and the call fails closed with SIGNATURE_POLICY_UNRESOLVED**, the exact precedent
`open_security_exception()` set. See `docs/generated/18_SPEC_GAPS.md` SG-165.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.security.supplychain_models import VulnerabilityRecord
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    InvalidTransitionError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
    VulnerabilityExceptionConflictError,
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
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, aggregate_id: uuid.UUID,
    version: int, action: str, actor_user_id: uuid.UUID, reason: str | None, old_state: str | None,
    event_type: str, event_payload: dict, expected_version: int | None, command_type: str,
    signature_id: uuid.UUID | None = None,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="vulnerability_record", aggregate_id=aggregate_id,
        aggregate_version=version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state} if old_state else None, new_value=event_payload,
        signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="vulnerability_record", aggregate_id=aggregate_id,
        aggregate_version=version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type=command_type, aggregate_type="vulnerability_record",
        aggregate_id=aggregate_id, expected_version=expected_version, resulting_version=version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=aggregate_id, resulting_version=version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# =================================================================================================
# registerVulnerability() -- SDLC-FR-018. RBAC only.
# =================================================================================================


class RegisterVulnerabilityCommand(CommandEnvelope):
    vulnerability_id: str
    source: str
    component: dict
    affected_releases: list = []
    reason: str


_SOURCES = {"INTERNAL_SCAN", "SCA", "CONTAINER_SCAN", "CUSTOMER_REPORT", "RESEARCHER", "VENDOR_ADVISORY"}


async def register_vulnerability(
    session: AsyncSession, cmd: RegisterVulnerabilityCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.source not in _SOURCES:
        raise ValidationFailedError(f"source must be one of {sorted(_SOURCES)}")
    if not cmd.vulnerability_id or not isinstance(cmd.component, dict) or not cmd.component.get("name"):
        raise ValidationFailedError("vulnerability_id and component.name are required")
    if not cmd.reason:
        raise ValidationFailedError("reason is required")

    rec = VulnerabilityRecord(
        vulnerability_id=cmd.vulnerability_id, source=cmd.source, component=cmd.component,
        affected_releases=cmd.affected_releases, state="OPEN", kev_status=False, version=1,
    )
    session.add(rec)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=rec.id, version=rec.version,
        action="Created", actor_user_id=actor_user_id, reason=cmd.reason, old_state=None,
        event_type="VulnerabilityRegistered",
        event_payload={"record_id": str(rec.id), "vulnerability_id": cmd.vulnerability_id, "source": cmd.source},
        expected_version=None, command_type="RegisterVulnerability",
    )


# =================================================================================================
# assessVulnerabilitySeverity() -- SDLC-FR-019/020/021. RBAC only.
# =================================================================================================


class AssessVulnerabilitySeverityCommand(CommandEnvelope):
    vulnerability_id: uuid.UUID
    expected_version: int
    severity: str
    kev_status: bool
    gxp_impact: dict
    remediation_due: datetime
    assessment: dict
    reason: str


async def assess_vulnerability_severity(
    session: AsyncSession, cmd: AssessVulnerabilitySeverityCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    rec = await session.get(VulnerabilityRecord, cmd.vulnerability_id)
    if rec is None:
        raise NotFoundError("Vulnerability record not found")
    if rec.version != cmd.expected_version:
        raise StaleVersionError("Vulnerability changed since this request was prepared", current_version=rec.version)
    if rec.state not in ("OPEN", "ASSESSED"):
        raise InvalidTransitionError(f"Cannot (re)assess a vulnerability in state {rec.state}")
    if cmd.severity not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        raise ValidationFailedError("severity must be LOW, MEDIUM, HIGH or CRITICAL")
    if not cmd.reason:
        raise ValidationFailedError("reason is required")

    old_state = rec.state
    rec.severity = cmd.severity
    rec.kev_status = cmd.kev_status
    rec.gxp_impact = cmd.gxp_impact
    rec.remediation_due = cmd.remediation_due
    rec.assessment = {**cmd.assessment, "assessed_by": str(actor_user_id),
                      "assessed_at": datetime.now(timezone.utc).isoformat()}
    rec.state = "ASSESSED"
    rec.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=rec.id, version=rec.version,
        action="Changed", actor_user_id=actor_user_id, reason=cmd.reason, old_state=old_state,
        event_type="VulnerabilityAssessed",
        event_payload={"record_id": str(rec.id), "severity": cmd.severity, "kev_status": cmd.kev_status,
                       "remediation_due": cmd.remediation_due.isoformat()},
        expected_version=cmd.expected_version, command_type="AssessVulnerabilitySeverity",
    )


# =================================================================================================
# approveVulnerabilityException() -- SDLC-FR-021. Signed (Document 106 row 141) -- UNRESOLVED (SG-165):
# no signature policy row exists, so _resolve_signature() fails closed with SIGNATURE_POLICY_UNRESOLVED.
# =================================================================================================


class ApproveVulnerabilityExceptionCommand(CommandEnvelope):
    vulnerability_id: uuid.UUID
    expected_version: int
    rationale: str
    compensating_controls: list
    expiry: datetime
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def approve_vulnerability_exception(
    session: AsyncSession, cmd: ApproveVulnerabilityExceptionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    rec = await session.get(VulnerabilityRecord, cmd.vulnerability_id)
    if rec is None:
        raise NotFoundError("Vulnerability record not found")
    if rec.version != cmd.expected_version:
        raise StaleVersionError("Vulnerability changed since this request was prepared", current_version=rec.version)
    if rec.state != "ASSESSED":
        raise InvalidTransitionError("A vulnerability must be ASSESSED before an exception can be approved")
    if rec.exception and rec.exception.get("approved"):
        raise VulnerabilityExceptionConflictError("An active exception decision already exists for this vulnerability")
    if cmd.expiry.tzinfo is None or cmd.expiry <= datetime.now(timezone.utc):
        raise ValidationFailedError("expiry must be a future timezone-aware timestamp (time-bounded, SDLC-FR-021)")
    if not cmd.rationale or not cmd.compensating_controls or not cmd.reason:
        raise ValidationFailedError("rationale, compensating_controls and reason are all required")

    # Document 106 row 141: signed by an independent "Elevated authority defined by the record class".
    # That role is unresolvable (same as Document 61 row 133 / SG-161) -- resolve_signature_requirement
    # raises SignaturePolicyUnresolvedError because no policy row is seeded. Fail closed. (SG-165)
    await signature_service.resolve_signature_requirement(session, record_type="vulnerability", action="exception")

    # Unreachable until SG-165 is resolved and a signature policy row exists -- kept for completeness.
    old_state = rec.state  # pragma: no cover
    rec.exception = {  # pragma: no cover
        "approved": True, "rationale": cmd.rationale, "compensating_controls": cmd.compensating_controls,
        "expiry": cmd.expiry.isoformat(), "approved_by": str(actor_user_id),
    }
    rec.state = "EXCEPTION_APPROVED"  # pragma: no cover
    rec.version += 1  # pragma: no cover
    await session.flush()  # pragma: no cover
    return await _write_receipt(  # pragma: no cover
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=rec.id, version=rec.version,
        action="Changed", actor_user_id=actor_user_id, reason=cmd.reason, old_state=old_state,
        event_type="VulnerabilityExceptionApproved",
        event_payload={"record_id": str(rec.id), "expiry": cmd.expiry.isoformat()},
        expected_version=cmd.expected_version, command_type="ApproveVulnerabilityException",
    )
