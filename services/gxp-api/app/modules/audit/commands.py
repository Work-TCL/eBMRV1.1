"""POST /audit/v1/exports (AUD-FR-022) — the one state-changing operation Document 05 owns. An export
is itself an auditable action (AUD-FR-002), so it goes through the same mutation-gateway pattern as every
other command, even though it only *reads* audit_events rather than owning any data of its own.
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.audit.models import AuditEvent
from app.modules.audit.service import actor_accessible_sites, apply_site_scope, event_to_dict
from app.modules.iam.models import User
from app.modules.signature import service as signature_service
from app.mutation.errors import MissingSignatureError
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
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


class AuditExportFilter(BaseModel):
    aggregate_type: str | None = None
    aggregate_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None


class CreateAuditExportCommand(CommandEnvelope):
    filter: AuditExportFilter
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def create_audit_export(
    session: AsyncSession, cmd: CreateAuditExportCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    # Document 106's approved floor has no row for this action — this correctly fails closed
    # (SIGNATURE_POLICY_UNRESOLVED, Doc SIGP-FR-004) until a human decides whether an export needs a
    # signature at all. See SG-029. Everything below is written for when that gap is resolved; it is not
    # reachable today, and no test claims otherwise.
    policy = await signature_service.resolve_signature_requirement(
        session, record_type="audit_export", action="export"
    )

    export_id = uuid.uuid4()
    filter_dict = cmd.filter.model_dump(mode="json")

    signature_id = None
    if policy.signature_required:
        if cmd.challenge_id is None or not cmd.reauth_password:
            raise MissingSignatureError("This export requires a signature", required_meaning=policy.meaning)
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session,
            challenge_id=cmd.challenge_id,
            user_id=actor_user_id,
            record_version=1,
            record_hash=sha256_hex(filter_dict),
        )
        signature = await signature_service.sign(
            session, challenge=challenge, auth_context={"method": "password_reauth"}
        )
        signature_id = signature.id

    accessible = await actor_accessible_sites(session, actor_user_id)
    stmt = select(AuditEvent)
    if cmd.filter.aggregate_type:
        stmt = stmt.where(AuditEvent.aggregate_type == cmd.filter.aggregate_type)
    if cmd.filter.aggregate_id:
        stmt = stmt.where(AuditEvent.aggregate_id == cmd.filter.aggregate_id)
    if cmd.filter.actor_id:
        stmt = stmt.where(AuditEvent.actor_id == cmd.filter.actor_id)
    if cmd.filter.site_id:
        stmt = stmt.where(AuditEvent.site_id == cmd.filter.site_id)
    if cmd.filter.occurred_from:
        stmt = stmt.where(AuditEvent.occurred_at >= cmd.filter.occurred_from)
    if cmd.filter.occurred_to:
        stmt = stmt.where(AuditEvent.occurred_at <= cmd.filter.occurred_to)
    stmt = apply_site_scope(stmt, accessible).order_by(AuditEvent.occurred_at)

    events = (await session.execute(stmt)).scalars().all()
    exported = [await event_to_dict(session, e, {}) for e in events]

    generated_at = datetime.now(timezone.utc)
    manifest = {
        "export_id": str(export_id),
        "generated_at": generated_at.isoformat(),
        "filter": filter_dict,
        "event_count": len(exported),
        "first_event_id": exported[0]["id"] if exported else None,
        "last_event_id": exported[-1]["id"] if exported else None,
    }
    content_hash = sha256_hex({"manifest": manifest, "events": exported})

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.filter.site_id,
        aggregate_type="audit_export",
        aggregate_id=export_id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={**manifest, "content_hash": content_hash},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="AuditExportCreated",
        aggregate_type="audit_export",
        aggregate_id=export_id,
        aggregate_version=1,
        payload={"id": str(export_id), "event_count": len(exported), "content_hash": content_hash},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.filter.site_id,
        command_type="CreateAuditExport",
        aggregate_type="audit_export",
        aggregate_id=export_id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=export_id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )
