"""Document 34 (SPEC-QMS-009) — Internal Audit Management command handlers. See
internal_audit_models.py's module docstring for the state-machine fold-in rationale and the deferred scope
(SG-101/SG-102).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.qms.internal_audit_models import AuditFinding, InternalAudit
from app.modules.qms.signature_support import enforce_signer_policy
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    AuditClosureBlockedError,
    AuditorSodConflictError,
    AuditScopeIncompleteError,
    FindingResponseRequiredError,
    FindingVerificationRequiredError,
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


async def _load_audit_for_update(session: AsyncSession, audit_id: uuid.UUID, expected_version: int | None = None) -> InternalAudit:
    result = await session.execute(select(InternalAudit).where(InternalAudit.id == audit_id).with_for_update())
    audit = result.scalar_one_or_none()
    if audit is None:
        raise NotFoundError("Internal audit not found")
    if expected_version is not None and audit.version != expected_version:
        raise StaleVersionError(
            "Internal audit was modified by another actor since it was read",
            expected_version=expected_version, current_version=audit.version,
        )
    return audit


async def _load_finding_for_update(session: AsyncSession, finding_id: uuid.UUID, expected_version: int) -> AuditFinding:
    result = await session.execute(select(AuditFinding).where(AuditFinding.id == finding_id).with_for_update())
    finding = result.scalar_one_or_none()
    if finding is None:
        raise NotFoundError("Audit finding not found")
    if finding.version != expected_version:
        raise StaleVersionError(
            "Audit finding was modified by another actor since it was read",
            expected_version=expected_version, current_version=finding.version,
        )
    return finding


def _record_hash(record) -> str:
    return sha256_hex({"id": str(record.id), "version": record.version})


async def _resolve_signature(
    session: AsyncSession, *, record_type: str, action: str, actor_user_id: uuid.UUID, record,
    challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    policy = await signature_service.resolve_signature_requirement(session, record_type=record_type, action=action)
    if not policy.signature_required:
        return None
    # Document 106 section 9 rows 98/99/100: internal_audit/close is `Approved` by a "QA Releaser"
    # independent of the investigator/owner (the audit's `lead_auditor_id`); internal_audit/start is
    # `Performed` with no fixed role and no independence rule; audit_finding/verify is `Verified` by a
    # qualified independent verifier who "MUST NOT be the performer" (the finding's `owner_subject_id`).
    await enforce_signer_policy(
        session, policy=policy, actor_user_id=actor_user_id, site_id=record.site_id,
        action_label=f"{record_type}.{action}",
        disqualified_subject_ids=(
            getattr(record, "lead_auditor_id", None),
            getattr(record, "owner_subject_id", None),
        ),
    )
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"{record_type} '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=record.version, record_hash=_record_hash(record),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


async def _write_audit_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, audit: InternalAudit, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    signature_id: uuid.UUID | None, expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=audit.site_id, aggregate_type="internal_audit", aggregate_id=audit.id,
        aggregate_version=audit.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": audit.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="internal_audit", aggregate_id=audit.id,
        aggregate_version=audit.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=audit.site_id, command_type=command_type, aggregate_type="internal_audit",
        aggregate_id=audit.id, expected_version=expected_version, resulting_version=audit.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=audit.id, resulting_version=audit.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


async def _write_audit_secondary_audit_outbox(
    session: AsyncSession, *, audit: InternalAudit, action: str, actor_user_id: uuid.UUID,
    old_state: str, event_type: str, event_payload: dict, correlation_id: uuid.UUID,
) -> None:
    await write_audit_event(
        session, site_id=audit.site_id, aggregate_type="internal_audit", aggregate_id=audit.id,
        aggregate_version=audit.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=None, old_value={"state": old_state}, new_value={"state": audit.state}, signature_id=None,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="internal_audit", aggregate_id=audit.id,
        aggregate_version=audit.version, payload=event_payload, correlation_id=correlation_id,
    )


async def _write_finding_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, finding: AuditFinding, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    signature_id: uuid.UUID | None, expected_version: int | None, command_type: str,
    correlation_id: uuid.UUID | None = None,
) -> MutationReceipt:
    correlation_id = correlation_id or uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=finding.site_id, aggregate_type="audit_finding", aggregate_id=finding.id,
        aggregate_version=finding.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": finding.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="audit_finding", aggregate_id=finding.id,
        aggregate_version=finding.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=finding.site_id, command_type=command_type, aggregate_type="audit_finding",
        aggregate_id=finding.id, expected_version=expected_version, resulting_version=finding.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=finding.id, resulting_version=finding.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create internal audit — AUDIT-FR-001/002/003
# ---------------------------------------------------------------------------


class CreateInternalAuditCommand(CommandEnvelope):
    site_id: uuid.UUID
    audit_number: str
    program_ref: str
    criteria_refs: dict
    lead_auditor_id: uuid.UUID
    scheduled_at: datetime
    site_scope: dict | None = None
    process_scope: dict | None = None
    team: list[uuid.UUID] | None = None
    auditees: list[uuid.UUID] | None = None


async def create_internal_audit(session: AsyncSession, cmd: CreateInternalAuditCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.program_ref.strip() or not cmd.criteria_refs or not (cmd.site_scope or cmd.process_scope):
        raise AuditScopeIncompleteError("program_ref, criteria_refs and at least one of site_scope/process_scope are required")

    conflict = (await session.execute(select(InternalAudit).where(InternalAudit.audit_number == cmd.audit_number))).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("audit_number is already in use", audit_number=cmd.audit_number)

    auditees = {str(a) for a in (cmd.auditees or [])}
    team_ids = {str(t) for t in (cmd.team or [])}
    if str(cmd.lead_auditor_id) in auditees or (team_ids & auditees):
        raise AuditorSodConflictError("lead_auditor_id/team must not overlap with auditees")

    audit = InternalAudit(
        site_id=cmd.site_id, audit_number=cmd.audit_number, program_ref=cmd.program_ref,
        site_scope=cmd.site_scope, process_scope=cmd.process_scope, criteria_refs=cmd.criteria_refs,
        lead_auditor_id=cmd.lead_auditor_id, team=[str(t) for t in cmd.team] if cmd.team else None,
        auditees=[str(a) for a in cmd.auditees] if cmd.auditees else None,
        scheduled_at=cmd.scheduled_at, state="SCHEDULED",
    )
    session.add(audit)
    await session.flush()

    return await _write_audit_receipt(
        session, cmd=cmd, payload_hash=payload_hash, audit=audit, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="SCHEDULED", event_type="InternalAuditScheduled",
        event_payload={"id": str(audit.id), "audit_number": audit.audit_number},
        signature_id=None, expected_version=None, command_type="CreateInternalAudit",
    )


# ---------------------------------------------------------------------------
# Start internal audit — signature: Document 106 row 99
# ---------------------------------------------------------------------------


class StartInternalAuditCommand(CommandEnvelope):
    audit_id: uuid.UUID
    expected_version: int
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def start_internal_audit(session: AsyncSession, cmd: StartInternalAuditCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    audit = await _load_audit_for_update(session, cmd.audit_id, cmd.expected_version)
    if audit.state != "SCHEDULED":
        raise InvalidTransitionError("Illegal internal audit transition", current_state=audit.state, requested="IN_PROGRESS")

    signature_id = await _resolve_signature(
        session, record_type="internal_audit", action="start", actor_user_id=actor_user_id, record=audit,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = audit.state
    audit.actual_start_at = datetime.now(timezone.utc)
    audit.state = "IN_PROGRESS"
    audit.version += 1

    return await _write_audit_receipt(
        session, cmd=cmd, payload_hash=payload_hash, audit=audit, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="InternalAuditStarted",
        event_payload={"id": str(audit.id)}, signature_id=signature_id, expected_version=cmd.expected_version,
        command_type="StartInternalAudit",
    )


# ---------------------------------------------------------------------------
# Add finding — AUDIT-FR-004/005/006/014
# ---------------------------------------------------------------------------


class AddFindingCommand(CommandEnvelope):
    audit_id: uuid.UUID
    audit_expected_version: int
    finding_number: str
    requirement_ref: str
    observation: str
    severity: str
    owner_subject_id: uuid.UUID
    evidence: dict | None = None
    due_date: datetime | None = None


async def add_finding(session: AsyncSession, cmd: AddFindingCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    audit = await _load_audit_for_update(session, cmd.audit_id, cmd.audit_expected_version)
    if audit.state not in ("IN_PROGRESS", "FINDINGS_OPEN"):
        raise InvalidTransitionError("Illegal internal audit transition", current_state=audit.state, requested="FINDINGS_OPEN")
    if not cmd.requirement_ref.strip() or not cmd.observation.strip() or not cmd.severity.strip():
        raise ValidationFailedError("requirement_ref, observation and severity are required")

    conflict = (await session.execute(select(AuditFinding).where(AuditFinding.finding_number == cmd.finding_number))).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("finding_number is already in use", finding_number=cmd.finding_number)

    # AUDIT-FR-014: repeat-finding detection by requirement_ref across all prior findings.
    repeat = (
        await session.execute(select(AuditFinding.id).where(AuditFinding.requirement_ref == cmd.requirement_ref))
    ).first()

    finding = AuditFinding(
        site_id=audit.site_id, audit_id=audit.id, finding_number=cmd.finding_number,
        requirement_ref=cmd.requirement_ref, observation=cmd.observation, evidence=cmd.evidence,
        severity=cmd.severity, owner_subject_id=cmd.owner_subject_id, due_date=cmd.due_date,
        is_repeat_finding=bool(repeat), state="OPEN",
    )
    session.add(finding)
    await session.flush()

    old_audit_state = audit.state
    report_just_approved = audit.state == "IN_PROGRESS"
    if report_just_approved:
        audit.state = "FINDINGS_OPEN"
        audit.version += 1

    receipt = await _write_finding_receipt(
        session, cmd=cmd, payload_hash=payload_hash, finding=finding, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="OPEN", event_type="AuditFindingOpened",
        event_payload={"id": str(finding.id), "audit_id": str(audit.id), "finding_number": finding.finding_number, "is_repeat_finding": finding.is_repeat_finding},
        signature_id=None, expected_version=None, command_type="AddFinding",
    )
    if report_just_approved:
        await _write_audit_secondary_audit_outbox(
            session, audit=audit, action="Changed", actor_user_id=actor_user_id, old_state=old_audit_state,
            event_type="AuditReportApproved", event_payload={"id": str(audit.id)}, correlation_id=receipt.correlation_id,
        )
    return receipt


# ---------------------------------------------------------------------------
# Respond to finding — AUDIT-FR-007/008
# ---------------------------------------------------------------------------


class RespondToFindingCommand(CommandEnvelope):
    finding_id: uuid.UUID
    expected_version: int
    correction: str
    root_cause: str
    action: str
    due_date: datetime | None = None
    capa_required: bool = False
    capa_rationale: str | None = None
    reason: str | None = None


async def respond_to_finding(session: AsyncSession, cmd: RespondToFindingCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    finding = await _load_finding_for_update(session, cmd.finding_id, cmd.expected_version)
    if finding.state != "OPEN":
        raise InvalidTransitionError("Illegal audit finding transition", current_state=finding.state, requested="RESPONSE_SUBMITTED")
    if not cmd.correction.strip() or not cmd.root_cause.strip() or not cmd.action.strip():
        raise ValidationFailedError("correction, root_cause and action are required")

    old_state = finding.state
    finding.response = {
        "correction": cmd.correction, "root_cause": cmd.root_cause, "action": cmd.action,
        "responded_by": str(actor_user_id), "responded_at": datetime.now(timezone.utc).isoformat(),
    }
    if cmd.due_date is not None:
        finding.due_date = cmd.due_date
    finding.capa_required = cmd.capa_required
    finding.capa_rationale = cmd.capa_rationale
    finding.state = "RESPONSE_SUBMITTED"
    finding.version += 1

    return await _write_finding_receipt(
        session, cmd=cmd, payload_hash=payload_hash, finding=finding, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="AuditFindingOpened",
        event_payload={"id": str(finding.id), "state": finding.state}, signature_id=None,
        expected_version=cmd.expected_version, command_type="RespondToFinding",
    )


# ---------------------------------------------------------------------------
# Verify finding — AUDIT-FR-009 (signature: Document 106 row 100)
# ---------------------------------------------------------------------------


class VerifyFindingCommand(CommandEnvelope):
    finding_id: uuid.UUID
    expected_version: int
    verification_notes: str
    effective: bool
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def verify_finding(session: AsyncSession, cmd: VerifyFindingCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    finding = await _load_finding_for_update(session, cmd.finding_id, cmd.expected_version)
    if finding.state == "OPEN":
        raise FindingResponseRequiredError("A response must be submitted before this finding can be verified")
    if finding.state != "RESPONSE_SUBMITTED":
        raise InvalidTransitionError("Illegal audit finding transition", current_state=finding.state, requested="VERIFIED")
    if not cmd.verification_notes.strip():
        raise ValidationFailedError("verification_notes is required")

    signature_id = await _resolve_signature(
        session, record_type="audit_finding", action="verify", actor_user_id=actor_user_id, record=finding,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = finding.state
    finding.verification = {
        "notes": cmd.verification_notes, "effective": cmd.effective, "verified_by": str(actor_user_id),
        "verified_at": datetime.now(timezone.utc).isoformat(), "signature_id": str(signature_id) if signature_id else None,
    }
    finding.state = "VERIFIED"
    finding.closed_at = datetime.now(timezone.utc)
    finding.version += 1

    return await _write_finding_receipt(
        session, cmd=cmd, payload_hash=payload_hash, finding=finding, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="AuditFindingClosed",
        event_payload={"id": str(finding.id), "effective": cmd.effective}, signature_id=signature_id,
        expected_version=cmd.expected_version, command_type="VerifyFinding",
    )


# ---------------------------------------------------------------------------
# Close internal audit — AUDIT-FR-011 (signature: Document 106 row 98)
# ---------------------------------------------------------------------------


class CloseInternalAuditCommand(CommandEnvelope):
    audit_id: uuid.UUID
    expected_version: int
    conclusion: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def close_internal_audit(session: AsyncSession, cmd: CloseInternalAuditCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    audit = await _load_audit_for_update(session, cmd.audit_id, cmd.expected_version)
    if audit.state in ("SCHEDULED", "IN_PROGRESS"):
        raise AuditClosureBlockedError("Internal audit report has not been approved yet (no findings recorded)", current_state=audit.state)
    if audit.state != "FINDINGS_OPEN":
        raise InvalidTransitionError("Illegal internal audit transition", current_state=audit.state, requested="CLOSED")
    if not cmd.conclusion.strip():
        raise ValidationFailedError("conclusion is required")

    unverified = (
        await session.execute(
            select(AuditFinding.id).where(AuditFinding.audit_id == audit.id, AuditFinding.state != "VERIFIED")
        )
    ).first()
    if unverified is not None:
        raise FindingVerificationRequiredError("All findings must be verified before the audit can be closed")

    signature_id = await _resolve_signature(
        session, record_type="internal_audit", action="close", actor_user_id=actor_user_id, record=audit,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = audit.state
    audit.actual_end_at = datetime.now(timezone.utc)
    audit.state = "CLOSED"
    audit.version += 1

    return await _write_audit_receipt(
        session, cmd=cmd, payload_hash=payload_hash, audit=audit, action="Closed", actor_user_id=actor_user_id,
        reason=cmd.conclusion, old_state=old_state, event_type="InternalAuditClosed",
        event_payload={"id": str(audit.id)}, signature_id=signature_id, expected_version=cmd.expected_version,
        command_type="CloseInternalAudit",
    )
