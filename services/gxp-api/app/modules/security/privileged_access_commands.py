"""Document 63 (SPEC-SEC-003) Mutation Gateway command handlers. See privileged_access_models.py's
module docstring for the Document 106 rows 134-136 signature resolution (QA Releaser, same established
non-QMS mapping precedent as `inventory_adjustment_request.approve`/`oos_record.close`) and why nothing
here can grant GxP/signature authority (PAM-FR-002/012).
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.security import identity_commands
from app.modules.security.identity_models import ApplicationSession
from app.modules.security.privileged_access_models import (
    PrivilegedAccessRequest,
    PrivilegedGrant,
    PrivilegedSession,
)
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    AdminCommandNotAllowedError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    PrivilegedAccessDeniedError,
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


# ---------------------------------------------------------------------------------------------------
# PrivilegedAccessRequest / PrivilegedGrant -- PAM-FR-001..005/016/017.
# ---------------------------------------------------------------------------------------------------


class RequestPrivilegedAccessCommand(CommandEnvelope):
    requested_role: str
    scope: dict
    reason: str
    requested_start: datetime
    requested_end: datetime
    ticket_ref: str | None = None


async def request_privileged_access(
    session: AsyncSession, cmd: RequestPrivilegedAccessCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.reason:
        raise ValidationFailedError("reason is required (PAM-FR-005)")
    if cmd.requested_end <= cmd.requested_start:
        raise ValidationFailedError("requested_end must be after requested_start")

    request = PrivilegedAccessRequest(
        subject_id=actor_user_id, requested_role=cmd.requested_role, scope=cmd.scope, reason=cmd.reason,
        ticket_ref=cmd.ticket_ref, requested_start=cmd.requested_start, requested_end=cmd.requested_end,
        state="PENDING_APPROVAL", version=1,
    )
    session.add(request)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="privileged_access_request",
        aggregate_id=request.id, version=request.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=None, event_type="PrivilegedAccessRequested",
        event_payload={"request_id": str(request.id), "requested_role": request.requested_role, "subject_id": str(actor_user_id)},
        expected_version=None, command_type="RequestPrivilegedAccess",
    )


class ApprovePrivilegedAccessCommand(CommandEnvelope):
    request_id: uuid.UUID
    expected_version: int
    decision: str
    comments: str
    duration_minutes: int = 240
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def approve_privileged_access(
    session: AsyncSession, cmd: ApprovePrivilegedAccessCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """PAM-FR-016: the requester cannot approve their own elevation (SoD, enforced here for real --
    Document 106 row 135's "MUST be independent of the author")."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    request = await session.get(PrivilegedAccessRequest, cmd.request_id)
    if request is None:
        raise NotFoundError("Privileged access request not found")
    if request.version != cmd.expected_version:
        raise StaleVersionError("Privileged access request changed since this request was prepared", current_version=request.version)
    if request.state != "PENDING_APPROVAL":
        raise InvalidTransitionError(f"Cannot decide a request in state {request.state}")
    if cmd.decision not in ("APPROVED", "DENIED"):
        raise ValidationFailedError("decision must be APPROVED or DENIED")
    if actor_user_id == request.subject_id:
        raise ValidationFailedError("Requester cannot approve their own privileged access request (PAM-FR-016)")

    signature_id = await _resolve_signature(
        session, record_type="privileged_access_request", action="approve", actor_user_id=actor_user_id,
        record_version=request.version, record_hash=sha256_hex({"id": str(request.id), "version": request.version}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = request.state
    request.state = cmd.decision
    request.approver_id = actor_user_id
    request.version += 1

    grant = None
    if cmd.decision == "APPROVED":
        now = datetime.now(timezone.utc)
        grant = PrivilegedGrant(
            request_id=request.id, grant_type="JIT", role=request.requested_role, scope=request.scope,
            effective_from=now, expiry=min(request.requested_end, now + timedelta(minutes=cmd.duration_minutes)),
            auth_strength={"methods": ["PASSWORD"]}, state="ACTIVE", granted_by=actor_user_id,
            subject_id=request.subject_id, version=1,
        )
        session.add(grant)
        await session.flush()

    receipt = await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="privileged_access_request",
        aggregate_id=request.id, version=request.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.comments, old_state=old_state, event_type="PrivilegedAccessGranted" if cmd.decision == "APPROVED" else "PrivilegedAccessRequested",
        event_payload={"request_id": str(request.id), "decision": cmd.decision, "grant_id": str(grant.id) if grant else None},
        expected_version=cmd.expected_version, command_type="ApprovePrivilegedAccess", signature_id=signature_id,
    )
    return receipt


async def evaluate_privileged_grant(
    session: AsyncSession, *, subject_id: uuid.UUID, requested_role: str, resource: str | None = None,
) -> dict:
    """`evaluatePrivilegedGrant()` -- read-only allow/deny check (PAM-FR-005/017). Raises
    PrivilegedAccessDeniedError on deny rather than returning a false-looking 200, so a denied check is
    unambiguous and itself auditable by the caller's own error handling."""
    now = datetime.now(timezone.utc)
    grant = (
        await session.execute(
            select(PrivilegedGrant).where(
                PrivilegedGrant.subject_id == subject_id, PrivilegedGrant.role == requested_role,
                PrivilegedGrant.state == "ACTIVE",
            ).order_by(PrivilegedGrant.effective_from.desc()).limit(1)
        )
    ).scalar_one_or_none()
    if grant is None:
        raise PrivilegedAccessDeniedError("No active privileged grant for this subject/role")
    effective_from = grant.effective_from if grant.effective_from.tzinfo else grant.effective_from.replace(tzinfo=timezone.utc)
    expiry = grant.expiry if grant.expiry.tzinfo else grant.expiry.replace(tzinfo=timezone.utc)
    if now < effective_from or now > expiry:
        raise PrivilegedAccessDeniedError("Grant is not currently within its effective window", expiry=expiry.isoformat())
    if resource is not None and grant.scope.get("resources") and resource not in grant.scope["resources"]:
        raise PrivilegedAccessDeniedError("Grant scope does not cover this resource")
    return {"allow": True, "grant_id": str(grant.id), "role": grant.role, "expiry": expiry.isoformat()}


async def revoke_active_grants_for_subject(session: AsyncSession, *, subject_id: uuid.UUID, reason: str) -> list[uuid.UUID]:
    """PAM-FR-025: offboarding/termination immediately revokes JIT/break-glass grants too, not only the
    application sessions Document 62's `revoke_user_sessions()` already covers. Called from
    `iam.commands._set_user_status()`'s disable path, in the same transaction as the status change --
    a lightweight state update (no separate Mutation Gateway receipt) since it is a side-effect of that
    outer aggregate's own audited transition, same treatment as a plain internal helper."""
    grants = (
        await session.execute(
            select(PrivilegedGrant).where(PrivilegedGrant.subject_id == subject_id, PrivilegedGrant.state == "ACTIVE")
        )
    ).scalars().all()
    revoked_ids = []
    for grant in grants:
        grant.state = "REVOKED"
        grant.version += 1
        revoked_ids.append(grant.id)
    if revoked_ids:
        await session.flush()
    return revoked_ids


# ---------------------------------------------------------------------------------------------------
# PrivilegedSession -- PAM-FR-006/007/008/009/013/014/015/020/023/026.
# ---------------------------------------------------------------------------------------------------


class OpenSupportSessionCommand(CommandEnvelope):
    grant_id: uuid.UUID
    support_case_ref: str
    customer_scope_ref: str | None = None
    connection_source: dict | None = None
    reason: str | None = None


async def open_support_session(
    session: AsyncSession, cmd: OpenSupportSessionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """PAM-FR-007/008: support session always opens read-only (`review_status="NOT_REQUIRED"` by
    default -- mutation requires the separately-approved `executeControlledAdminCommand()` path)."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    grant = await session.get(PrivilegedGrant, cmd.grant_id)
    if grant is None:
        raise NotFoundError("Privileged grant not found")
    if grant.state != "ACTIVE":
        raise InvalidTransitionError(f"Cannot open a session against a {grant.state} grant")
    if not cmd.support_case_ref:
        raise ValidationFailedError("support_case_ref is required (PAM-FR-007)")

    privileged_session = PrivilegedSession(
        grant_id=grant.id, session_type="SUPPORT", customer_scope_ref=cmd.customer_scope_ref,
        support_case_ref=cmd.support_case_ref, opened_by=actor_user_id, connection_source=cmd.connection_source,
        review_status="NOT_REQUIRED", state="ACTIVE", version=1,
    )
    session.add(privileged_session)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="privileged_session",
        aggregate_id=privileged_session.id, version=privileged_session.version, action="Created",
        actor_user_id=actor_user_id, reason=cmd.reason, old_state=None, event_type="SupportSessionOpened",
        event_payload={"session_id": str(privileged_session.id), "support_case_ref": cmd.support_case_ref},
        expected_version=None, command_type="OpenSupportSession",
    )


class ActivateBreakGlassCommand(CommandEnvelope):
    requested_role: str
    incident_ref: str
    reason: str
    duration_minutes: int = 60
    scope: dict = {}


async def activate_break_glass(
    session: AsyncSession, cmd: ActivateBreakGlassCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """PAM-FR-011/012: emergency path, no approval gate, no GxP/signature authority -- creates a
    short-lived grant + session directly (EMERGENCY -> BREAK_GLASS_ACTIVE, Doc 63 `# 5`).
    `review_status="PENDING"` unconditionally (PAM-FR-011's "immediate post-use review")."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.incident_ref or not cmd.reason:
        raise ValidationFailedError("incident_ref and reason are both required (PAM-FR-011/026)")

    now = datetime.now(timezone.utc)
    grant = PrivilegedGrant(
        request_id=None, grant_type="BREAK_GLASS", role=cmd.requested_role, scope=cmd.scope,
        effective_from=now, expiry=now + timedelta(minutes=cmd.duration_minutes),
        auth_strength={"methods": ["PASSWORD"], "emergency": True}, state="ACTIVE", incident_ref=cmd.incident_ref,
        granted_by=actor_user_id, subject_id=actor_user_id, version=1,
    )
    session.add(grant)
    await session.flush()

    privileged_session = PrivilegedSession(
        grant_id=grant.id, session_type="BREAK_GLASS", opened_by=actor_user_id, review_status="PENDING",
        state="ACTIVE", version=1,
    )
    session.add(privileged_session)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="privileged_session",
        aggregate_id=privileged_session.id, version=privileged_session.version, action="Created",
        actor_user_id=actor_user_id, reason=cmd.reason, old_state=None, event_type="BreakGlassActivated",
        event_payload={"session_id": str(privileged_session.id), "grant_id": str(grant.id), "incident_ref": cmd.incident_ref},
        expected_version=None, command_type="ActivateBreakGlass",
    )


# PAM-FR-018: the entire allowlist. Each handler is typed, validated and never accepts arbitrary SQL/code.
async def _cmd_list_active_sessions(session: AsyncSession, parameters: dict, actor_user_id: uuid.UUID) -> dict:
    rows = (await session.execute(select(ApplicationSession).where(ApplicationSession.state == "ACTIVE"))).scalars().all()
    return {"active_session_count": len(rows), "session_ids": [str(r.id) for r in rows]}


async def _cmd_force_revoke_session(session: AsyncSession, parameters: dict, actor_user_id: uuid.UUID) -> dict:
    target_session_id = parameters.get("session_id")
    if not target_session_id:
        raise ValidationFailedError("parameters.session_id is required for FORCE_REVOKE_SESSION")
    receipt = await identity_commands.revoke_session(
        session, identity_commands.RevokeSessionCommand(
            idempotency_key=str(uuid.uuid4()), session_id=uuid.UUID(target_session_id),
            reason="Privileged admin command FORCE_REVOKE_SESSION",
        ),
        actor_user_id,
    )
    return {"revoked_session_id": target_session_id, "receipt_command_id": str(receipt.command_id)}


CONTROLLED_ADMIN_COMMANDS = {
    "LIST_ACTIVE_SESSIONS": _cmd_list_active_sessions,
    "FORCE_REVOKE_SESSION": _cmd_force_revoke_session,
}


class ExecuteControlledAdminCommandCommand(CommandEnvelope):
    privileged_session_id: uuid.UUID
    command_code: str
    parameters: dict = {}
    reason: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def execute_controlled_admin_command(
    session: AsyncSession, cmd: ExecuteControlledAdminCommandCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    privileged_session = await session.get(PrivilegedSession, cmd.privileged_session_id)
    if privileged_session is None:
        raise NotFoundError("Privileged session not found")
    if privileged_session.state != "ACTIVE":
        raise InvalidTransitionError(f"Cannot execute a command against a {privileged_session.state} session")
    handler = CONTROLLED_ADMIN_COMMANDS.get(cmd.command_code)
    if handler is None:
        raise AdminCommandNotAllowedError("command_code is not on the allowlist (PAM-FR-018)", allowed=list(CONTROLLED_ADMIN_COMMANDS))

    grant = await session.get(PrivilegedGrant, privileged_session.grant_id)
    await evaluate_privileged_grant(session, subject_id=grant.subject_id, requested_role=grant.role)

    signature_id = await _resolve_signature(
        session, record_type="admin_command", action="execute", actor_user_id=actor_user_id,
        record_version=privileged_session.version, record_hash=sha256_hex({"id": str(privileged_session.id), "command_code": cmd.command_code}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    result = await handler(session, cmd.parameters, actor_user_id)

    old_state = privileged_session.state
    privileged_session.actions = [
        *privileged_session.actions,
        {
            "command_code": cmd.command_code, "parameters": cmd.parameters, "result": result,
            "actor_id": str(actor_user_id), "executed_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    privileged_session.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="privileged_session",
        aggregate_id=privileged_session.id, version=privileged_session.version, action="Changed",
        actor_user_id=actor_user_id, reason=cmd.reason, old_state=old_state, event_type="AdminCommandExecuted",
        event_payload={"session_id": str(privileged_session.id), "command_code": cmd.command_code},
        expected_version=None, command_type="ExecuteControlledAdminCommand", signature_id=signature_id,
    )


class ClosePrivilegedSessionCommand(CommandEnvelope):
    privileged_session_id: uuid.UUID
    expected_version: int
    outcome: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def close_privileged_session(
    session: AsyncSession, cmd: ClosePrivilegedSessionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """Document 106 row 136: independence "MUST be independent of the investigator/owner" -- enforced
    here against `opened_by` for real, except for a break-glass session's own emergency operator closing
    their own emergency access, which PAM-FR-011 treats as the expected self-terminating shape (closing
    is not the mandatory review -- reviewPrivilegedSession() still requires a distinct reviewer below)."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    privileged_session = await session.get(PrivilegedSession, cmd.privileged_session_id)
    if privileged_session is None:
        raise NotFoundError("Privileged session not found")
    if privileged_session.version != cmd.expected_version:
        raise StaleVersionError("Privileged session changed since this request was prepared", current_version=privileged_session.version)
    if privileged_session.state != "ACTIVE":
        raise InvalidTransitionError(f"Cannot close a session in state {privileged_session.state}")
    if privileged_session.session_type != "BREAK_GLASS" and actor_user_id == privileged_session.opened_by:
        raise ValidationFailedError("Closer must be independent of the session's own opener (Document 106 row 136)")

    signature_id = await _resolve_signature(
        session, record_type="privileged_session", action="close", actor_user_id=actor_user_id,
        record_version=privileged_session.version, record_hash=sha256_hex({"id": str(privileged_session.id), "version": privileged_session.version}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = privileged_session.state
    privileged_session.state = "CLOSED"
    privileged_session.ended_at = datetime.now(timezone.utc)
    privileged_session.close_outcome = cmd.outcome
    privileged_session.closed_by = actor_user_id
    if privileged_session.session_type == "BREAK_GLASS":
        privileged_session.review_status = "PENDING"
    privileged_session.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="privileged_session",
        aggregate_id=privileged_session.id, version=privileged_session.version, action="Changed",
        actor_user_id=actor_user_id, reason=cmd.outcome, old_state=old_state, event_type="PrivilegedSessionClosed",
        event_payload={"session_id": str(privileged_session.id), "outcome": cmd.outcome},
        expected_version=cmd.expected_version, command_type="ClosePrivilegedSession", signature_id=signature_id,
    )


class ReviewPrivilegedSessionCommand(CommandEnvelope):
    privileged_session_id: uuid.UUID
    expected_version: int
    findings: str
    outcome: str = "NO_ISSUES"


async def review_privileged_session(
    session: AsyncSession, cmd: ReviewPrivilegedSessionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """Extra op (not in Document 63 `# 7`'s 6-op list, same "named function missing from the terse API
    list" precedent as Documents 61/62's own extra ops) -- PAM-FR-011/024's mandatory break-glass /
    periodic review has no reachable REVIEWED transition otherwise."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    privileged_session = await session.get(PrivilegedSession, cmd.privileged_session_id)
    if privileged_session is None:
        raise NotFoundError("Privileged session not found")
    if privileged_session.version != cmd.expected_version:
        raise StaleVersionError("Privileged session changed since this request was prepared", current_version=privileged_session.version)
    if privileged_session.state != "CLOSED":
        raise InvalidTransitionError("Only a closed session can be reviewed")
    if privileged_session.review_status == "REVIEWED":
        raise InvalidTransitionError("Session already reviewed")
    if actor_user_id == privileged_session.opened_by:
        raise ValidationFailedError("Reviewer must be independent of the session's own opener")

    old_state = privileged_session.review_status
    privileged_session.review = {
        "findings": cmd.findings, "outcome": cmd.outcome, "reviewed_by": str(actor_user_id),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    privileged_session.review_status = "REVIEWED"
    privileged_session.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="privileged_session",
        aggregate_id=privileged_session.id, version=privileged_session.version, action="Changed",
        actor_user_id=actor_user_id, reason=cmd.findings, old_state=old_state, event_type="PrivilegedSessionReviewed",
        event_payload={"session_id": str(privileged_session.id), "outcome": cmd.outcome},
        expected_version=cmd.expected_version, command_type="ReviewPrivilegedSession",
    )
