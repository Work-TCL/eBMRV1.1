"""Document 65 (SPEC-SEC-005) Mutation Gateway command handlers.

Signature resolution (Document 106 rows 137-139): `certificate` issue / rotate / revoke each require a
`Released` signature by an independent **QA Releaser** -- the established non-QMS mapping for the
"QA Approver / Batch Release" family (same as batch.release, edge_gateway.certificate_rotation,
privileged_session.close). `secret` rotate has **no** Document 106 row -> RBAC-gated only (Security
Admin), no signature. All four ops are one PostgreSQL transaction = domain row + version + audit event
+ outbox event -> MutationReceipt.
"""

import secrets as _pysecrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.security.crypto import encrypt_sensitive_field, secret_value_key_context
from app.modules.security.crypto_models import CertificateMetadata, SecretMetadata, SecretValue
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    SecretAlreadyExistsError,
    SecretRotationFailedError,
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


_SECRET_PROVIDERS = {"K8S_SECRET", "AWS_SM", "VAULT", "ON_PREM"}


# =================================================================================================
# createSecret() -- KEY-FR-002/003/004. No signature (no Document 106 row, same as secret.rotate).
# SG-126 gap resolution: no create-path existed for `secret_metadata` before this pass -- only
# `rotate_secret()`, which requires the row to already exist.
# =================================================================================================


class CreateSecretCommand(CommandEnvelope):
    secret_ref: str
    provider: str
    purpose: str
    owner: str
    consumer_identities: list[str] = []
    rotation_interval_days: int = 90
    # ON_PREM only: the plaintext value to store, encrypted immediately and never persisted raw or
    # placed in the audit/outbox payload (Document 65 # 14). Rejected for every other provider -- their
    # value lives externally, this build has no client to verify/store it against (SG-126).
    initial_value: str | None = None


async def create_secret(session: AsyncSession, cmd: CreateSecretCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.provider not in _SECRET_PROVIDERS:
        raise ValidationFailedError(f"provider must be one of {sorted(_SECRET_PROVIDERS)}")
    if not cmd.secret_ref or not cmd.purpose or not cmd.owner:
        raise ValidationFailedError("secret_ref, purpose and owner are required")
    if cmd.rotation_interval_days < 1 or cmd.rotation_interval_days > 3650:
        raise ValidationFailedError("rotation_interval_days must be between 1 and 3650")
    if cmd.initial_value is not None and cmd.provider != "ON_PREM":
        raise ValidationFailedError(
            "initial_value is only accepted for provider ON_PREM -- other providers store the value "
            "externally and this build has no live client to write it there (SG-126)"
        )
    if (
        await session.execute(select(SecretMetadata.id).where(SecretMetadata.secret_ref == cmd.secret_ref))
    ).first() is not None:
        raise SecretAlreadyExistsError("A secret with this secret_ref is already registered", secret_ref=cmd.secret_ref)

    row = SecretMetadata(
        id=uuid.uuid4(), secret_ref=cmd.secret_ref, provider=cmd.provider, purpose=cmd.purpose, owner=cmd.owner,
        consumer_identities=list(cmd.consumer_identities), rotation_interval_days=cmd.rotation_interval_days,
        state="ACTIVE", version=1,
    )
    session.add(row)
    await session.flush()

    if cmd.initial_value is not None:
        envelope = encrypt_sensitive_field(
            key_context=secret_value_key_context(row.id), plaintext=cmd.initial_value.encode(),
        )
        session.add(SecretValue(secret_id=row.id, envelope=envelope, version=1, set_by_user_id=actor_user_id))
        await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="secret_metadata",
        aggregate_id=row.id, version=row.version, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state=None, event_type="SecretCreated",
        event_payload={"secret_id": str(row.id), "secret_ref": row.secret_ref, "provider": row.provider,
                       "has_value": cmd.initial_value is not None},
        expected_version=None, command_type="CreateSecret",
    )


# =================================================================================================
# setSecretValue() -- KEY-FR-002/003/004, ON_PREM provider only. No signature (no Document 106 row).
# =================================================================================================


class SetSecretValueCommand(CommandEnvelope):
    secret_id: uuid.UUID
    expected_version: int
    value: str
    reason: str


async def set_secret_value(session: AsyncSession, cmd: SetSecretValueCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    secret = await session.get(SecretMetadata, cmd.secret_id)
    if secret is None:
        raise NotFoundError("Secret metadata not found")
    if secret.provider != "ON_PREM":
        raise ValidationFailedError(
            f"Cannot store a value for provider {secret.provider} -- only ON_PREM secrets are value-managed "
            "in this build (SG-126)"
        )
    if not cmd.reason:
        raise ValidationFailedError("reason is required")

    value_row = (
        await session.execute(select(SecretValue).where(SecretValue.secret_id == cmd.secret_id))
    ).scalar_one_or_none()
    current_version = value_row.version if value_row is not None else 0
    if current_version != cmd.expected_version:
        raise StaleVersionError("Secret value changed since this request was prepared", current_version=current_version)

    envelope = encrypt_sensitive_field(key_context=secret_value_key_context(secret.id), plaintext=cmd.value.encode())
    old_state = "SET" if value_row is not None else "UNSET"
    if value_row is None:
        value_row = SecretValue(secret_id=secret.id, envelope=envelope, version=1, set_by_user_id=actor_user_id)
        session.add(value_row)
    else:
        value_row.envelope = envelope
        value_row.set_by_user_id = actor_user_id
        value_row.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="secret_value",
        aggregate_id=secret.id, version=value_row.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="SecretValueSet",
        event_payload={"secret_id": str(secret.id), "secret_ref": secret.secret_ref, "version": value_row.version},
        expected_version=cmd.expected_version, command_type="SetSecretValue",
    )


# =================================================================================================
# rotateSecret() -- KEY-FR-005/006. No signature (no Document 106 row).
# =================================================================================================


class RotateSecretCommand(CommandEnvelope):
    secret_id: uuid.UUID
    expected_version: int
    reason: str
    overlap_minutes: int = 60
    incident_ref: str | None = None


async def rotate_secret(session: AsyncSession, cmd: RotateSecretCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    row = await session.get(SecretMetadata, cmd.secret_id)
    if row is None:
        raise NotFoundError("Secret metadata not found")
    if row.version != cmd.expected_version:
        raise StaleVersionError("Secret changed since this request was prepared", current_version=row.version)
    if row.state not in ("ACTIVE", "ROTATING"):
        raise SecretRotationFailedError(f"Cannot rotate a secret in state {row.state}")
    if not cmd.reason:
        raise ValidationFailedError("reason is required for a secret rotation (KEY-FR-006)")
    if cmd.overlap_minutes < 0 or cmd.overlap_minutes > 43200:
        raise ValidationFailedError("overlap_minutes must be between 0 and 43200")

    now = datetime.now(timezone.utc)
    old_state = row.state
    row.last_rotated_at = now
    row.next_rotation_at = now + timedelta(days=row.rotation_interval_days)
    row.incident_ref = cmd.incident_ref or row.incident_ref
    row.state = "ACTIVE"
    row.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="secret_metadata",
        aggregate_id=row.id, version=row.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="SecretRotated",
        event_payload={"secret_id": str(row.id), "secret_ref": row.secret_ref, "version": row.version,
                       "emergency": bool(cmd.incident_ref)},
        expected_version=cmd.expected_version, command_type="RotateSecret",
    )


# =================================================================================================
# issueServiceCertificate() -- KEY-FR-007/008. Signature: certificate/issue (Document 106 row 139).
# =================================================================================================


class IssueServiceCertificateCommand(CommandEnvelope):
    subject_sans: dict
    profile: str
    validity_days: int
    issuer_ref: str
    identity_id: uuid.UUID | None = None
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


def issue_request_hash(cmd: "IssueServiceCertificateCommand") -> str:
    """Canonical hash of a certificate-issue *request* -- the challenge for a signed CREATE binds to
    this (there is no prior record id/version). Stable across the challenge and the command call."""
    return sha256_hex({
        "subject_sans": cmd.subject_sans, "profile": cmd.profile, "validity_days": cmd.validity_days,
        "issuer_ref": cmd.issuer_ref,
    })


def _validate_cert_request(subject_sans: dict, profile: str, validity_days: int) -> None:
    if not isinstance(subject_sans, dict) or not subject_sans.get("subject"):
        raise ValidationFailedError("subject_sans.subject is required (KEY-FR-008)")
    sans = subject_sans.get("sans")
    if not sans or not isinstance(sans, list):
        raise ValidationFailedError("subject_sans.sans must list at least one SAN (KEY-FR-008)")
    if profile not in ("SERVICE_MTLS", "EDGE_GATEWAY", "ADMIN", "INTEGRATION"):
        raise ValidationFailedError("profile must be SERVICE_MTLS, EDGE_GATEWAY, ADMIN or INTEGRATION")
    if validity_days < 1 or validity_days > 825:  # CA/Browser Forum max for TLS server certs
        raise ValidationFailedError("validity_days must be between 1 and 825")


async def issue_service_certificate(
    session: AsyncSession, cmd: IssueServiceCertificateCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    _validate_cert_request(cmd.subject_sans, cmd.profile, cmd.validity_days)
    if not cmd.reason:
        raise ValidationFailedError("reason is required")

    # A signed CREATE: there is no prior record, so the challenge binds to a canonical hash of the
    # *request* (subject/SANs/profile/validity) at version 1 -- the client creates the challenge with
    # `issue_request_hash(cmd)` before calling this endpoint. Same effect as binding to a record
    # id/version for an update: the signature cannot be reused for a different request.
    request_hash = issue_request_hash(cmd)
    signature_id = await _resolve_signature(
        session, record_type="certificate", action="issue", actor_user_id=actor_user_id,
        record_version=1, record_hash=request_hash,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    serial = _pysecrets.token_hex(16)
    now = datetime.now(timezone.utc)
    cert = CertificateMetadata(
        serial=serial, subject_sans=cmd.subject_sans, identity_id=cmd.identity_id, profile=cmd.profile,
        issued_at=now, expires_at=now + timedelta(days=cmd.validity_days), state="ACTIVE",
        issuer_ref=cmd.issuer_ref, signature_id=signature_id, version=1,
    )
    session.add(cert)
    await session.flush()
    old_state = None

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="certificate_metadata",
        aggregate_id=cert.id, version=cert.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="CertificateIssued",
        event_payload={"certificate_id": str(cert.id), "serial": serial, "profile": cert.profile,
                       "expires_at": cert.expires_at.isoformat()},
        expected_version=None, command_type="IssueServiceCertificate", signature_id=signature_id,
    )


# =================================================================================================
# rotateCertificate() -- KEY-FR-009. Signature: certificate/rotate (Document 106 row 138).
# =================================================================================================


class RotateCertificateCommand(CommandEnvelope):
    certificate_id: uuid.UUID
    expected_version: int
    validity_days: int
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def rotate_certificate(
    session: AsyncSession, cmd: RotateCertificateCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    old_cert = await session.get(CertificateMetadata, cmd.certificate_id)
    if old_cert is None:
        raise NotFoundError("Certificate not found")
    if old_cert.version != cmd.expected_version:
        raise StaleVersionError("Certificate changed since this request was prepared", current_version=old_cert.version)
    if old_cert.state != "ACTIVE":
        raise InvalidTransitionError(f"Only an ACTIVE certificate can be rotated (state {old_cert.state})")
    if cmd.validity_days < 1 or cmd.validity_days > 825:
        raise ValidationFailedError("validity_days must be between 1 and 825")
    if not cmd.reason:
        raise ValidationFailedError("reason is required")

    now = datetime.now(timezone.utc)
    new_serial = _pysecrets.token_hex(16)
    new_cert = CertificateMetadata(
        serial=new_serial, subject_sans=old_cert.subject_sans, identity_id=old_cert.identity_id,
        profile=old_cert.profile, issued_at=now, expires_at=now + timedelta(days=cmd.validity_days),
        state="REQUESTED", issuer_ref=old_cert.issuer_ref, supersedes_id=old_cert.id, version=1,
    )
    session.add(new_cert)
    await session.flush()

    signature_id = await _resolve_signature(
        session, record_type="certificate", action="rotate", actor_user_id=actor_user_id,
        record_version=old_cert.version, record_hash=sha256_hex({"id": str(old_cert.id), "version": old_cert.version}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = old_cert.state
    new_cert.state = "ACTIVE"
    new_cert.signature_id = signature_id
    new_cert.version += 1
    # KEY-FR-009: old cert enters the overlap window, not immediately revoked.
    old_cert.state = "ROTATING"
    old_cert.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="certificate_metadata",
        aggregate_id=new_cert.id, version=new_cert.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="CertificateRotated",
        event_payload={"certificate_id": str(new_cert.id), "serial": new_serial,
                       "supersedes_id": str(old_cert.id), "supersedes_serial": old_cert.serial},
        expected_version=cmd.expected_version, command_type="RotateCertificate", signature_id=signature_id,
    )


# =================================================================================================
# revokeCertificate() -- KEY-FR-010. Signature: certificate/revoke (Document 106 row 137).
# =================================================================================================


class RevokeCertificateCommand(CommandEnvelope):
    certificate_id: uuid.UUID
    expected_version: int
    revocation_reason: str
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


_REVOCATION_REASONS = {
    "KEY_COMPROMISE", "CA_COMPROMISE", "AFFILIATION_CHANGED", "SUPERSEDED",
    "CESSATION_OF_OPERATION", "PRIVILEGE_WITHDRAWN", "UNSPECIFIED",
}


async def revoke_certificate(
    session: AsyncSession, cmd: RevokeCertificateCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    cert = await session.get(CertificateMetadata, cmd.certificate_id)
    if cert is None:
        raise NotFoundError("Certificate not found")
    if cert.version != cmd.expected_version:
        raise StaleVersionError("Certificate changed since this request was prepared", current_version=cert.version)
    if cert.state not in ("ACTIVE", "ROTATING", "REQUESTED"):
        raise InvalidTransitionError(f"Cannot revoke a certificate in state {cert.state}")
    if cmd.revocation_reason not in _REVOCATION_REASONS:
        raise ValidationFailedError(f"revocation_reason must be one of {sorted(_REVOCATION_REASONS)}")
    if not cmd.reason:
        raise ValidationFailedError("reason is required")

    signature_id = await _resolve_signature(
        session, record_type="certificate", action="revoke", actor_user_id=actor_user_id,
        record_version=cert.version, record_hash=sha256_hex({"id": str(cert.id), "version": cert.version}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = cert.state
    cert.state = "REVOKED"
    cert.revocation_reason = cmd.revocation_reason
    cert.revoked_at = datetime.now(timezone.utc)
    cert.signature_id = signature_id
    cert.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="certificate_metadata",
        aggregate_id=cert.id, version=cert.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="CertificateRevoked",
        event_payload={"certificate_id": str(cert.id), "serial": cert.serial,
                       "revocation_reason": cmd.revocation_reason},
        expected_version=cmd.expected_version, command_type="RevokeCertificate", signature_id=signature_id,
    )
