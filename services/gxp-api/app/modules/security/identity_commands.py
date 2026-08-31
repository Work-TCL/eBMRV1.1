"""Document 62 (SPEC-SEC-002) Mutation Gateway command handlers. See identity_models.py's module
docstring for the `service_identity` naming-collision note, the `identity_mapping` no-owned-table note,
and what is/isn't genuinely built for the `GET /auth/login`/`GET /auth/callback` federation flow.

No Document 106 signature row exists for any of this module's 6 declared operations (checked the full
register) -- none require a Part 11 signature, matching Document 62 `# 7`'s own "Signature: —" for all
six rows. No SPEC_GAP needed for signatures here (unlike Document 61's SG-161).
"""

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.iam.models import User
from app.modules.policy.service import effective_role_names
from app.modules.security.identity_models import (
    DEFAULT_DISALLOWED_MFA_METHODS,
    IDP_PROTOCOLS,
    MFA_METHODS,
    PRIVILEGED_ROLE_NAMES,
    SERVICE_AUTH_METHODS,
    ApplicationSession,
    IdentityProviderConfig,
    SecurityServiceIdentity,
)
from app.mutation.errors import (
    FreshAuthenticationRequiredError,
    InvalidTransitionError,
    NotFoundError,
    StaleVersionError,
    TokenInvalidError,
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
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state} if old_state else None, new_value=event_payload,
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
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------------------------------
# IdentityProviderConfig -- IAMSEC-FR-001/002/005/011/024/026.
# ---------------------------------------------------------------------------------------------------


class CreateIdentityProviderConfigCommand(CommandEnvelope):
    deployment_label: str
    issuer: str
    protocol: str
    trust_metadata: dict
    claim_mapping_version: str
    claim_mapping: dict | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    reason: str | None = None


async def create_identity_provider_config(
    session: AsyncSession, cmd: CreateIdentityProviderConfigCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.protocol not in IDP_PROTOCOLS:
        raise ValidationFailedError("Unrecognized protocol", allowed=list(IDP_PROTOCOLS))
    if not cmd.trust_metadata:
        raise ValidationFailedError("trust_metadata (signing keys/algorithm) is required")

    idp = IdentityProviderConfig(
        deployment_label=cmd.deployment_label, issuer=cmd.issuer, protocol=cmd.protocol,
        trust_metadata=cmd.trust_metadata, claim_mapping_version=cmd.claim_mapping_version,
        claim_mapping=cmd.claim_mapping, effective_from=cmd.effective_from, effective_to=cmd.effective_to,
        state="ACTIVE", version=1,
    )
    session.add(idp)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="identity_provider_config",
        aggregate_id=idp.id, version=idp.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=None, event_type="IdentityProviderConfigured",
        event_payload={"identity_provider_config_id": str(idp.id), "issuer": idp.issuer, "protocol": idp.protocol},
        expected_version=None, command_type="CreateIdentityProviderConfig",
    )


class MapExternalIdentityCommand(CommandEnvelope):
    identity_provider_config_id: uuid.UUID
    user_id: uuid.UUID
    issuer: str
    subject: str
    claims: dict = {}
    reason: str | None = None


async def map_external_identity(
    session: AsyncSession, cmd: MapExternalIdentityCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """IAMSEC-FR-011/026: writes onto `iam.users.external_issuer`/`external_subject` (already-existing,
    previously-unpopulated columns -- see identity_models.py module docstring). `User` carries no
    `version` column; `resulting_version=1` is hardcoded, the same precedent `iam/commands.py::
    _set_user_status` already uses for every `User` mutation in this codebase."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    idp = await session.get(IdentityProviderConfig, cmd.identity_provider_config_id)
    if idp is None:
        raise NotFoundError("Identity provider config not found")
    if cmd.issuer != idp.issuer:
        raise ValidationFailedError("issuer does not match the identity provider config's own issuer")

    user = await session.get(User, cmd.user_id)
    if user is None:
        raise NotFoundError("User not found")

    # Reject binding this (issuer, subject) pair to a second, different internal user -- prevents an
    # identity hijack/collision (IAMSEC-FR-011 policy boundary).
    collision = (
        await session.execute(
            select(User).where(
                User.external_issuer == cmd.issuer, User.external_subject == cmd.subject, User.id != user.id,
            )
        )
    ).scalar_one_or_none()
    if collision is not None:
        raise ValidationFailedError(
            "This external identity is already mapped to a different internal user", existing_user_id=str(collision.id)
        )

    user.external_issuer = cmd.issuer
    user.external_subject = cmd.subject

    idp.identity_mappings = [
        *idp.identity_mappings,
        {
            "user_id": str(user.id), "subject": cmd.subject, "claims": cmd.claims,
            "mapped_at": datetime.now(timezone.utc).isoformat(), "mapped_by": str(actor_user_id),
        },
    ]

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="user",
        aggregate_id=user.id, version=1, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=None, event_type="ExternalIdentityMapped",
        event_payload={"user_id": str(user.id), "identity_provider_config_id": str(idp.id), "subject": cmd.subject},
        expected_version=None, command_type="MapExternalIdentity",
    )


class ValidateIdentityTokenCommand(CommandEnvelope):
    identity_provider_config_id: uuid.UUID
    token: str
    expected_audience: str


async def validate_identity_token(session: AsyncSession, cmd: ValidateIdentityTokenCommand) -> dict:
    """IAMSEC-FR-005/024: real issuer/audience/signature/expiry/clock-skew validation against a
    configured provider's trust metadata. `trust_metadata` carries `{"algorithm": "HS256", "secret":
    "..."}` for the symmetric case this module actually exercises under test (a real external RS256/JWKS
    handshake needs a live IdP this environment does not have -- see module docstring)."""
    idp = await session.get(IdentityProviderConfig, cmd.identity_provider_config_id)
    if idp is None:
        raise NotFoundError("Identity provider config not found")
    if idp.state != "ACTIVE":
        raise TokenInvalidError("Identity provider config is not active")

    algorithm = idp.trust_metadata.get("algorithm")
    key = idp.trust_metadata.get("secret") or idp.trust_metadata.get("public_key")
    if not algorithm or not key:
        raise TokenInvalidError("Identity provider config has no usable signing key material")
    clock_skew = int(idp.trust_metadata.get("clock_skew_seconds", 60))

    try:
        claims = jwt.decode(
            cmd.token, key, algorithms=[algorithm], audience=cmd.expected_audience, issuer=idp.issuer,
            options={"leeway": clock_skew},
        )
    except JWTError as exc:
        raise TokenInvalidError(f"Token validation failed: {exc}") from exc

    return {
        "identity_provider_config_id": str(idp.id), "issuer": idp.issuer, "audience": cmd.expected_audience,
        "subject": claims.get("sub"), "claims": claims,
    }


# ---------------------------------------------------------------------------------------------------
# ApplicationSession -- IAMSEC-FR-003/004/006/007/008/009/010/013/022/023.
# ---------------------------------------------------------------------------------------------------


async def create_application_session(
    session: AsyncSession, *, subject_id: uuid.UUID, auth_strength: dict, actor_user_id: uuid.UUID | None = None,
) -> ApplicationSession:
    """Called by the `/auth/token` login callback (IAMSEC-FR-001's permitted password-fallback path).
    Not itself exposed as a public REST command in Document 62 `# 7`'s 6-op list -- `createApplicationSession()`'s
    own caller is literally "Web login callback", not a standalone client-invoked API."""
    now = datetime.now(timezone.utc)
    app_session = ApplicationSession(
        subject_id=subject_id, auth_time=now, auth_strength=auth_strength, expires_at=now + timedelta(minutes=settings.session_absolute_timeout_minutes),
        idle_expires_at=now + timedelta(minutes=settings.session_idle_timeout_minutes), state="ACTIVE", version=1,
    )
    session.add(app_session)
    await session.flush()

    correlation_id = uuid.uuid4()
    await write_audit_event(
        session, site_id=None, aggregate_type="application_session", aggregate_id=app_session.id,
        aggregate_version=app_session.version, action="Created", actor_id=actor_user_id or subject_id,
        correlation_id=correlation_id, new_value={"subject_id": str(subject_id)},
    )
    await write_outbox_event(
        session, event_type="SessionCreated", aggregate_type="application_session", aggregate_id=app_session.id,
        aggregate_version=app_session.version, payload={"session_id": str(app_session.id), "subject_id": str(subject_id)},
        correlation_id=correlation_id,
    )
    return app_session


def evaluate_mfa_requirement_sync(role_names: set[str], context: dict | None = None) -> dict:
    """IAMSEC-FR-003/004: pure decision function -- privileged role class or an elevated `risk` context
    signal requires MFA. `disallowed_methods` always excludes the platform-default weak-factor list
    (IAMSEC-FR-004) plus any deployment-configured exclusions passed via context."""
    context = context or {}
    privileged = bool(role_names & PRIVILEGED_ROLE_NAMES)
    high_risk = context.get("risk") == "high"
    mfa_required = privileged or high_risk
    disallowed = set(DEFAULT_DISALLOWED_MFA_METHODS) | set(context.get("disallowed_methods", []))
    allowed_methods = [m for m in MFA_METHODS if m not in disallowed]
    return {
        "mfa_required": mfa_required, "allowed_methods": allowed_methods,
        "reason": "privileged_role" if privileged else ("elevated_risk_context" if high_risk else "standard"),
    }


async def evaluate_mfa_requirement(session: AsyncSession, user_id: uuid.UUID, site_id: uuid.UUID | None, context: dict | None = None) -> dict:
    role_names = await effective_role_names(session, user_id, site_id)
    return evaluate_mfa_requirement_sync(role_names, context)


class RevokeSessionCommand(CommandEnvelope):
    session_id: uuid.UUID
    reason: str


async def revoke_session(session: AsyncSession, cmd: RevokeSessionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    app_session = await session.get(ApplicationSession, cmd.session_id)
    if app_session is None:
        raise NotFoundError("Application session not found")
    if app_session.state not in ("ACTIVE", "STEP_UP_REQUIRED"):
        raise InvalidTransitionError(f"Cannot revoke a session in state {app_session.state}")

    old_state = app_session.state
    app_session.state = "REVOKED"
    app_session.revoked_reason = cmd.reason
    app_session.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="application_session",
        aggregate_id=app_session.id, version=app_session.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="SessionRevoked",
        event_payload={"session_id": str(app_session.id), "subject_id": str(app_session.subject_id)},
        expected_version=None, command_type="RevokeSession",
    )


class RevokeUserSessionsCommand(CommandEnvelope):
    subject_id: uuid.UUID
    reason: str


async def revoke_user_sessions(
    session: AsyncSession, cmd: RevokeUserSessionsCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """`revokeUserSessions()` -- IAMSEC-FR-010/013 bulk revoke. Called both from
    `POST /security/v1/sessions:revoke-all` and internally by `iam.commands.deactivate_user()`."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    active_sessions = (
        await session.execute(
            select(ApplicationSession).where(
                ApplicationSession.subject_id == cmd.subject_id,
                ApplicationSession.state.in_(("ACTIVE", "STEP_UP_REQUIRED")),
            )
        )
    ).scalars().all()
    session_ids = []
    for s in active_sessions:
        s.state = "REVOKED"
        s.revoked_reason = cmd.reason
        s.version += 1
        session_ids.append(str(s.id))
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="user_sessions", aggregate_id=cmd.subject_id,
        aggregate_version=len(session_ids), action="Changed", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=cmd.reason, new_value={"revoked_session_ids": session_ids},
    )
    await write_outbox_event(
        session, event_type="SessionRevoked", aggregate_type="user_sessions", aggregate_id=cmd.subject_id,
        aggregate_version=len(session_ids), payload={"subject_id": str(cmd.subject_id), "session_ids": session_ids},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="RevokeUserSessions", aggregate_type="user_sessions",
        aggregate_id=cmd.subject_id, expected_version=None, resulting_version=len(session_ids),
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=cmd.subject_id, resulting_version=len(session_ids),
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


async def require_fresh_authentication(
    session: AsyncSession, session_id: uuid.UUID, required_age_seconds: int, required_strength: dict | None = None,
) -> dict:
    """IAMSEC-FR-008: sensitive security/admin operations may require fresh authentication, independent
    of Part 11 signing (IAMSEC-FR-009 -- this never substitutes for a signature ceremony)."""
    app_session = await session.get(ApplicationSession, session_id)
    if app_session is None or app_session.state != "ACTIVE":
        raise FreshAuthenticationRequiredError("No active session")
    age_seconds = (datetime.now(timezone.utc) - app_session.auth_time).total_seconds()
    if age_seconds > required_age_seconds:
        raise FreshAuthenticationRequiredError("Authentication is not fresh enough", age_seconds=age_seconds, required_age_seconds=required_age_seconds)
    if required_strength:
        for key, value in required_strength.items():
            if app_session.auth_strength.get(key) != value:
                raise FreshAuthenticationRequiredError("Authentication strength insufficient", required_strength=required_strength)
    return {"fresh": True, "auth_time": app_session.auth_time.isoformat(), "age_seconds": age_seconds}


# ---------------------------------------------------------------------------------------------------
# SecurityServiceIdentity -- IAMSEC-FR-014/015/016.
# ---------------------------------------------------------------------------------------------------


class ProvisionServiceIdentityCommand(CommandEnvelope):
    service_name: str
    auth_method: str
    credential_ref: str
    site_id: uuid.UUID | None = None
    allowed_audiences: list[str] = []
    allowed_scopes: list[str] = []
    reason: str | None = None


async def provision_service_identity(
    session: AsyncSession, cmd: ProvisionServiceIdentityCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.auth_method not in SERVICE_AUTH_METHODS:
        raise ValidationFailedError("Unrecognized auth_method", allowed=list(SERVICE_AUTH_METHODS))
    dup = (
        await session.execute(select(SecurityServiceIdentity).where(SecurityServiceIdentity.service_name == cmd.service_name))
    ).scalar_one_or_none()
    if dup is not None:
        raise ValidationFailedError("service_name already provisioned", existing_id=str(dup.id))

    identity = SecurityServiceIdentity(
        service_name=cmd.service_name, site_id=cmd.site_id, allowed_audiences=cmd.allowed_audiences,
        allowed_scopes=cmd.allowed_scopes, auth_method=cmd.auth_method, credential_ref=cmd.credential_ref,
        lifecycle_status="ACTIVE", version=1,
    )
    session.add(identity)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="service_identity",
        aggregate_id=identity.id, version=identity.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=None, event_type="ServiceIdentityProvisioned",
        event_payload={"service_identity_id": str(identity.id), "service_name": identity.service_name},
        expected_version=None, command_type="ProvisionServiceIdentity",
    )


class RevokeServiceIdentityCommand(CommandEnvelope):
    service_identity_id: uuid.UUID
    expected_version: int
    reason: str


async def revoke_service_identity(
    session: AsyncSession, cmd: RevokeServiceIdentityCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """Extra op (not in Document 62 `# 7`'s 6-op list, same "named function missing from the terse API
    list" precedent as Document 61's trigger/calculate ops) -- IAMSEC-FR-014's PROVISIONED->ACTIVE->
    ROTATING->REVOKED state model has no reachable REVOKED transition otherwise."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    identity = await session.get(SecurityServiceIdentity, cmd.service_identity_id)
    if identity is None:
        raise NotFoundError("Service identity not found")
    if identity.version != cmd.expected_version:
        raise StaleVersionError("Service identity changed since this request was prepared", current_version=identity.version)
    if identity.lifecycle_status == "REVOKED":
        raise InvalidTransitionError("Service identity is already revoked")

    old_state = identity.lifecycle_status
    identity.lifecycle_status = "REVOKED"
    identity.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="service_identity",
        aggregate_id=identity.id, version=identity.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="ServiceIdentityProvisioned",
        event_payload={"service_identity_id": str(identity.id), "lifecycle_status": identity.lifecycle_status},
        expected_version=cmd.expected_version, command_type="RevokeServiceIdentity",
    )


async def validate_service_registration(
    session: AsyncSession, *, service_name: str, presented_audience: str, presented_scopes: list[str] | None = None,
) -> SecurityServiceIdentity:
    """`validateServiceToken()`'s registry-authorization half -- confirms a service the caller has
    ALREADY authenticated by some other means (mTLS termination, or a real external IdP-issued
    client-credentials token this environment cannot independently re-verify without a live IdP; see
    module docstring) is a registered, active, correctly-scoped identity. Not a bearer-secret verifier."""
    identity = (
        await session.execute(select(SecurityServiceIdentity).where(SecurityServiceIdentity.service_name == service_name))
    ).scalar_one_or_none()
    if identity is None:
        raise NotFoundError("Service identity not registered")
    if identity.lifecycle_status != "ACTIVE":
        raise TokenInvalidError("Service identity is not active", lifecycle_status=identity.lifecycle_status)
    if presented_audience not in identity.allowed_audiences:
        raise TokenInvalidError("Audience not permitted for this service identity")
    if presented_scopes and not set(presented_scopes).issubset(set(identity.allowed_scopes)):
        raise TokenInvalidError("Requested scopes exceed the service identity's allowed_scopes")
    return identity
