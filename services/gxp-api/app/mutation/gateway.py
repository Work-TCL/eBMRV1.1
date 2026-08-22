"""The Mutation Gateway kernel: idempotency, the per-aggregate audit hash chain, and the transactional
outbox. Every regulated command handler calls these from *inside* the same DB transaction as its domain
write — see app/modules/batch/commands.py for the pattern in use.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent
from app.modules.mutation.models import CommandReceipt, IdempotencyKey, OutboxEvent
from app.mutation.errors import IdempotencyConflictError
from app.mutation.hashing import sha256_hex


async def check_idempotency(
    session: AsyncSession, idempotency_key: str, command_hash: str
) -> CommandReceipt | None:
    """Returns the original receipt if this exact command was already committed under this key
    (MUT-FR-010 / TC duplicate-click semantics). Raises IdempotencyConflictError if the same key was
    used with a materially different payload.
    """
    existing = await session.get(IdempotencyKey, idempotency_key)
    if existing is None:
        return None
    if existing.command_hash != command_hash:
        raise IdempotencyConflictError(
            "Idempotency key reused with a different payload", idempotency_key=idempotency_key
        )
    return await session.get(CommandReceipt, existing.receipt_id)


async def write_audit_event(
    session: AsyncSession,
    *,
    site_id: uuid.UUID | None,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    aggregate_version: int,
    action: str,
    actor_id: uuid.UUID,
    correlation_id: uuid.UUID,
    actor_type: str = "human",
    reason: str | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    signature_id: uuid.UUID | None = None,
) -> AuditEvent:
    prev = await session.execute(
        select(AuditEvent.event_hash)
        .where(AuditEvent.aggregate_id == aggregate_id)
        .order_by(AuditEvent.aggregate_version.desc())
        .limit(1)
    )
    prev_hash = prev.scalar_one_or_none()

    occurred_at = datetime.now(timezone.utc)
    event_hash = sha256_hex(
        {
            "prev_event_hash": prev_hash,
            "aggregate_type": aggregate_type,
            "aggregate_id": str(aggregate_id),
            "aggregate_version": aggregate_version,
            "action": action,
            "actor_id": str(actor_id),
            "occurred_at": occurred_at.isoformat(),
            "old_value": old_value,
            "new_value": new_value,
        }
    )

    event = AuditEvent(
        site_id=site_id,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        aggregate_version=aggregate_version,
        action=action,
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=occurred_at,
        reason=reason,
        old_value=old_value,
        new_value=new_value,
        signature_id=signature_id,
        correlation_id=correlation_id,
        prev_event_hash=prev_hash,
        event_hash=event_hash,
    )
    session.add(event)
    return event


async def write_outbox_event(
    session: AsyncSession,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    aggregate_version: int,
    payload: dict,
    correlation_id: uuid.UUID,
    causation_id: uuid.UUID | None = None,
) -> OutboxEvent:
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        aggregate_version=aggregate_version,
        payload=payload,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )
    session.add(event)
    return event


async def record_command_receipt(
    session: AsyncSession,
    *,
    site_id: uuid.UUID | None,
    command_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    expected_version: int | None,
    resulting_version: int,
    idempotency_key: str,
    command_hash: str,
    actor_user_id: uuid.UUID,
    payload_hash: str,
) -> CommandReceipt:
    receipt = CommandReceipt(
        site_id=site_id,
        command_type=command_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        expected_version=expected_version,
        resulting_version=resulting_version,
        idempotency_key=idempotency_key,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
        status="committed",
    )
    session.add(receipt)
    await session.flush()  # need receipt.id before writing the idempotency row

    session.add(
        IdempotencyKey(
            idempotency_key=idempotency_key,
            command_hash=command_hash,
            receipt_id=receipt.id,
        )
    )
    return receipt
