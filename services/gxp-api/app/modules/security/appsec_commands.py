"""Document 64 (SPEC-SEC-004) Mutation Gateway command handlers. Only two state-changing operations
exist for this module (Document 64 # 7): register an `outbound_destination` and register a
`webhook_profile`. Both are RBAC-gated (Security Admin -- the existing Document 62 role, reused: no
Document 64 actor maps more cleanly and inventing a role would just duplicate it) and carry **no
signature** -- Document 106 has zero rows for any SPEC-SEC-004 action (checked the full register, rows
133-141) and the spec's own API table shows `Signature: —` for all three. `GET /security/v1/api-inventory`
is read-only and lives in the router.

Same `_write_receipt` shape as `privileged_access_commands.py`: one PostgreSQL transaction carrying
domain row + version + audit event + outbox event, MutationReceipt out.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.security.appsec_models import (
    WEBHOOK_AUTH_MECHANISMS,
    OutboundDestination,
    WebhookProfile,
)
from app.mutation.errors import ValidationFailedError
from app.mutation.gateway import (
    check_idempotency,
    record_command_receipt,
    write_audit_event,
    write_outbox_event,
)
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
    command_type: str,
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


# --------------------------------------------------------------------------------------------------
# outbound_destination -- APPSEC-FR-011
# --------------------------------------------------------------------------------------------------


class RegisterOutboundDestinationCommand(CommandEnvelope):
    service_id: str
    schemes_hosts_ports: dict
    purpose: str
    ip_range_rules: dict = {}
    redirect_policy: str = "BLOCK"
    auth_secret_ref: str | None = None


async def register_outbound_destination(
    session: AsyncSession, cmd: RegisterOutboundDestinationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.service_id or not cmd.purpose:
        raise ValidationFailedError("service_id and purpose are required")
    if cmd.redirect_policy not in ("BLOCK", "SAME_HOST", "ALLOWLIST"):
        raise ValidationFailedError("redirect_policy must be BLOCK, SAME_HOST or ALLOWLIST")
    hosts = cmd.schemes_hosts_ports.get("hosts") if isinstance(cmd.schemes_hosts_ports, dict) else None
    if not hosts:
        raise ValidationFailedError("schemes_hosts_ports.hosts must list at least one host")
    # APPSEC-FR-024: a secret must never be inlined -- only a reference.
    if cmd.auth_secret_ref and ("://" in cmd.auth_secret_ref or len(cmd.auth_secret_ref) > 200):
        raise ValidationFailedError("auth_secret_ref must be an opaque reference, not a value")

    dest = OutboundDestination(
        service_id=cmd.service_id, schemes_hosts_ports=cmd.schemes_hosts_ports,
        ip_range_rules=cmd.ip_range_rules, redirect_policy=cmd.redirect_policy,
        auth_secret_ref=cmd.auth_secret_ref, purpose=cmd.purpose, state="ACTIVE", version=1,
    )
    session.add(dest)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="outbound_destination",
        aggregate_id=dest.id, version=dest.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.purpose, old_state=None, event_type="OutboundDestinationRegistered",
        event_payload={"destination_id": str(dest.id), "service_id": dest.service_id,
                       "hosts": hosts, "redirect_policy": dest.redirect_policy},
        expected_version=None, command_type="RegisterOutboundDestination",
    )


# --------------------------------------------------------------------------------------------------
# webhook_profile -- APPSEC-FR-020
# --------------------------------------------------------------------------------------------------


class RegisterWebhookProfileCommand(CommandEnvelope):
    provider: str
    auth_mechanism: str = "HMAC_SHA256"
    replay_window_seconds: int = 300
    schema_version: str = "1.0"
    max_body_bytes: int = 1048576
    signing_secret_ref: str | None = None


async def register_webhook_profile(
    session: AsyncSession, cmd: RegisterWebhookProfileCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.provider:
        raise ValidationFailedError("provider is required")
    if cmd.auth_mechanism not in WEBHOOK_AUTH_MECHANISMS:
        raise ValidationFailedError(f"auth_mechanism must be one of {WEBHOOK_AUTH_MECHANISMS}")
    # APPSEC-FR-015 / no-guessed-numeric: reject nonsense but do not silently substitute a baseline.
    if cmd.replay_window_seconds <= 0 or cmd.replay_window_seconds > 86400:
        raise ValidationFailedError("replay_window_seconds must be between 1 and 86400")
    if cmd.max_body_bytes <= 0 or cmd.max_body_bytes > 67108864:
        raise ValidationFailedError("max_body_bytes must be between 1 and 67108864")
    if cmd.signing_secret_ref and len(cmd.signing_secret_ref) > 200:
        raise ValidationFailedError("signing_secret_ref must be an opaque reference, not a value")

    profile = WebhookProfile(
        provider=cmd.provider, auth_mechanism=cmd.auth_mechanism,
        replay_window_seconds=cmd.replay_window_seconds, schema_version=cmd.schema_version,
        max_body_bytes=cmd.max_body_bytes, signing_secret_ref=cmd.signing_secret_ref,
        state="ACTIVE", version=1,
    )
    session.add(profile)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="webhook_profile",
        aggregate_id=profile.id, version=profile.version, action="Created", actor_user_id=actor_user_id,
        reason=f"register webhook profile for {cmd.provider}", old_state=None,
        event_type="WebhookProfileRegistered",
        event_payload={"profile_id": str(profile.id), "provider": profile.provider,
                       "auth_mechanism": profile.auth_mechanism},
        expected_version=None, command_type="RegisterWebhookProfile",
    )
