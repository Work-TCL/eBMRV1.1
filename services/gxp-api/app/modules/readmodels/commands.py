"""Document 75 (SPEC-DATA-007) Mutation Gateway command handlers -- READ-FR-014/016/017/023.

All three state-changing operations share the `ReadModelCheckpoint` aggregate shape Document 69's
`rebuild_projection()` established: the first call for a `model_name` creates the checkpoint (omit
`expected_version`), later calls require the current version. **No signature anywhere** -- Document 106
has no SPEC-DATA-007 row, and Document 106 # 10 exempts "Projection rebuilds and cache invalidation"
and reads generally; the same exemption applies to a search-index rebuild, a read-model refresh and a
report export by the same reasoning.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent
from app.modules.readmodels.models import ProjectionDocumentMetadata, ReadModelCheckpoint
from app.modules.readmodels.search import index_authoritative_projection
from app.mutation.errors import InvalidTransitionError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version, audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _load_or_create_checkpoint(
    session: AsyncSession, *, model_name: str, source_stream: str | None, expected_version: int | None,
) -> tuple[ReadModelCheckpoint, bool]:
    checkpoint = (
        await session.execute(select(ReadModelCheckpoint).where(ReadModelCheckpoint.model_name == model_name))
    ).scalar_one_or_none()
    created = checkpoint is None
    if created:
        if not source_stream:
            raise ValidationFailedError("source_stream is required when first registering a model_name")
        if expected_version not in (None, 0):
            raise StaleVersionError("Read-model checkpoint does not exist yet", current_version=0)
        checkpoint = ReadModelCheckpoint(
            model_name=model_name, source_stream=source_stream, state="REFRESHING", version=1,
        )
        session.add(checkpoint)
        await session.flush()
    else:
        if expected_version is None or checkpoint.version != expected_version:
            raise StaleVersionError(
                "Read-model checkpoint changed since this request was prepared", current_version=checkpoint.version,
            )
        if checkpoint.state == "REFRESHING":
            raise InvalidTransitionError("A refresh/rebuild is already in progress for this model")
    return checkpoint, created


async def _finalize(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, checkpoint: ReadModelCheckpoint,
    action: str, actor_user_id: uuid.UUID, reason: str | None, old_value: dict | None, new_value: dict,
    event_type: str, expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="read_model_checkpoint", aggregate_id=checkpoint.id,
        aggregate_version=checkpoint.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value=old_value, new_value=new_value,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="read_model_checkpoint", aggregate_id=checkpoint.id,
        aggregate_version=checkpoint.version, payload=new_value, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type=command_type, aggregate_type="read_model_checkpoint",
        aggregate_id=checkpoint.id, expected_version=expected_version, resulting_version=checkpoint.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=checkpoint.id, resulting_version=checkpoint.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# =================================================================================================
# rebuildSearchIndex() -- READ-FR-014. Re-indexes every distinct aggregate_id for `source_stream` from
# the audit ledger's latest new_value snapshot, filtered by `allowed_fields` (READ-FR-009).
# =================================================================================================


class RebuildSearchIndexCommand(CommandEnvelope):
    index_type: str
    source_stream: str | None = None
    allowed_fields: list[str] = []
    expected_version: int | None = None
    reason: str | None = None


async def rebuild_search_index(
    session: AsyncSession, cmd: RebuildSearchIndexCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if not cmd.index_type:
        raise ValidationFailedError("index_type is required")

    model_name = f"search.{cmd.index_type}"
    checkpoint, created = await _load_or_create_checkpoint(
        session, model_name=model_name, source_stream=cmd.source_stream, expected_version=cmd.expected_version,
    )
    old_value = {"state": checkpoint.state, "version": checkpoint.version}

    allowed = set(cmd.allowed_fields)
    latest_per_aggregate = (
        await session.execute(
            select(
                AuditEvent.aggregate_id,
                func.max(AuditEvent.aggregate_version).label("max_version"),
            )
            .where(AuditEvent.aggregate_type == checkpoint.source_stream)
            .group_by(AuditEvent.aggregate_id)
        )
    ).all()
    reindexed = 0
    for aggregate_id, max_version in latest_per_aggregate:
        row = (
            await session.execute(
                select(AuditEvent.new_value).where(
                    AuditEvent.aggregate_id == aggregate_id, AuditEvent.aggregate_version == max_version
                ).limit(1)
            )
        ).scalar_one_or_none()
        await index_authoritative_projection(
            session, index_type=cmd.index_type, entity_type=checkpoint.source_stream,
            entity_id=aggregate_id, source_version=max_version, allowed_fields=allowed,
            source_payload=row or {},
        )
        reindexed += 1

    checkpoint.state = "FRESH"
    checkpoint.refreshed_at = datetime.now(timezone.utc)
    checkpoint.source_cutoff = checkpoint.refreshed_at
    checkpoint.version += 1

    new_value = {
        "model_name": model_name, "index_type": cmd.index_type, "state": checkpoint.state,
        "documents_reindexed": reindexed, "refreshed_at": checkpoint.refreshed_at.isoformat(),
    }
    return await _finalize(
        session, cmd=cmd, payload_hash=payload_hash, checkpoint=checkpoint,
        action="Created" if created else "Rebuilt", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value=None if created else old_value, new_value=new_value, event_type="SearchIndexRebuilt",
        expected_version=None if created else cmd.expected_version, command_type="RebuildSearchIndex",
    )


# =================================================================================================
# refreshReadModel() -- READ-FR-015/016. Advances a materialized-view-style checkpoint's cutoff.
# =================================================================================================


class RefreshReadModelCommand(CommandEnvelope):
    model_name: str
    source_stream: str | None = None
    expected_version: int | None = None
    reason: str | None = None


async def refresh_read_model(
    session: AsyncSession, cmd: RefreshReadModelCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if not cmd.model_name:
        raise ValidationFailedError("model_name is required")

    checkpoint, created = await _load_or_create_checkpoint(
        session, model_name=cmd.model_name, source_stream=cmd.source_stream, expected_version=cmd.expected_version,
    )
    old_value = {"state": checkpoint.state, "version": checkpoint.version}

    max_version = (
        await session.execute(
            select(func.max(AuditEvent.aggregate_version)).where(AuditEvent.aggregate_type == checkpoint.source_stream)
        )
    ).scalar_one_or_none() or 0

    checkpoint.state = "FRESH"
    checkpoint.refreshed_at = datetime.now(timezone.utc)
    checkpoint.source_cutoff = checkpoint.refreshed_at
    checkpoint.version += 1

    new_value = {
        "model_name": cmd.model_name, "state": checkpoint.state, "source_max_version": max_version,
        "refreshed_at": checkpoint.refreshed_at.isoformat(),
    }
    return await _finalize(
        session, cmd=cmd, payload_hash=payload_hash, checkpoint=checkpoint,
        action="Created" if created else "Rebuilt", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value=None if created else old_value, new_value=new_value, event_type="ReadModelRefreshed",
        expected_version=None if created else cmd.expected_version, command_type="RefreshReadModel",
    )


# =================================================================================================
# generateAsyncExport() -- READ-FR-017/019/023. Snapshots a frozen cutoff for a report definition.
# =================================================================================================


class GenerateAsyncExportCommand(CommandEnvelope):
    report_name: str
    source_stream: str
    expected_version: int | None = None
    reason: str


async def generate_async_export(
    session: AsyncSession, cmd: GenerateAsyncExportCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if not cmd.report_name or not cmd.reason:
        raise ValidationFailedError("report_name and reason are required")

    model_name = f"export.{cmd.report_name}"
    checkpoint, created = await _load_or_create_checkpoint(
        session, model_name=model_name, source_stream=cmd.source_stream, expected_version=cmd.expected_version,
    )
    old_value = {"state": checkpoint.state, "version": checkpoint.version}

    cutoff = datetime.now(timezone.utc)
    row_count = (
        await session.execute(
            select(func.count(func.distinct(AuditEvent.aggregate_id))).where(
                AuditEvent.aggregate_type == cmd.source_stream, AuditEvent.occurred_at <= cutoff,
            )
        )
    ).scalar_one()
    manifest_hash = sha256_hex({"report_name": cmd.report_name, "cutoff": cutoff.isoformat(), "row_count": row_count})

    checkpoint.state = "FRESH"
    checkpoint.refreshed_at = cutoff
    checkpoint.source_cutoff = cutoff
    checkpoint.version += 1

    new_value = {
        "report_name": cmd.report_name, "source_cutoff": cutoff.isoformat(), "row_count": row_count,
        "manifest_hash": manifest_hash,
    }
    return await _finalize(
        session, cmd=cmd, payload_hash=payload_hash, checkpoint=checkpoint,
        action="Created" if created else "Changed", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value=None if created else old_value, new_value=new_value, event_type="ExportGenerated",
        expected_version=None if created else cmd.expected_version, command_type="GenerateAsyncExport",
    )
