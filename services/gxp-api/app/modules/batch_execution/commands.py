"""Document 11 (SPEC-EBMR-002) — the buildable slice of the Batch Execution Engine: create, issue (with
Vault execution snapshot + step instantiation), start, hold/resume, abort, and step claim/start.
`app/modules/batch` (the legacy Batch-facing stub) is untouched -- this module is net-new and additive
(see migration f264272f2f0b's docstring). Everything gated on gxp_step_result/gxp_step_evidence_link/
gxp_batch_hold or on infrastructure this codebase does not have yet (Temporal, Material Service, Equipment
master, IAM qualification schema, exception/rework/branch entities) is deferred -- SG-047/SG-048.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch_execution import service as batch_execution_service
from app.modules.batch_execution.models import ALLOWED_TRANSITIONS, Batch, BatchStep
from app.modules.product_master.models import ProductVersion
from app.modules.recipe_master import service as recipe_master_service
from app.modules.rules import service as rules_service
from app.modules.vault import service as vault_service
from app.mutation.errors import (
    InvalidTransitionError,
    NotFoundError,
    StaleVersionError,
    UomUnknownError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


async def _resolve_uom_id(session: AsyncSession, uom: str | None) -> uuid.UUID | None:
    """SG-146 (remainder, module 4 of 8), MIG-FR-004 expand step."""
    if not uom:
        return None
    try:
        row = await rules_service.resolve_uom(session, uom)
    except UomUnknownError:
        return None
    return row.uom_id


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


async def _load_batch_for_update(session: AsyncSession, batch_id: uuid.UUID, expected_version: int) -> Batch:
    result = await session.execute(select(Batch).where(Batch.id == batch_id).with_for_update())
    batch = result.scalar_one_or_none()
    if batch is None:
        raise NotFoundError("Batch not found")
    if batch.version != expected_version:
        raise StaleVersionError(
            "Batch was modified by another actor since it was read",
            expected_version=expected_version,
            current_version=batch.version,
        )
    return batch


async def _load_step_for_update(session: AsyncSession, batch_id: uuid.UUID, step_id: uuid.UUID, expected_version: int) -> BatchStep:
    result = await session.execute(select(BatchStep).where(BatchStep.id == step_id).with_for_update())
    step = result.scalar_one_or_none()
    if step is None or step.batch_id != batch_id:
        raise NotFoundError("Batch step not found")
    if step.version != expected_version:
        raise StaleVersionError(
            "Batch step was modified by another actor since it was read",
            expected_version=expected_version,
            current_version=step.version,
        )
    return step


def _assert_transition(batch: Batch, new_state: str) -> None:
    if new_state not in ALLOWED_TRANSITIONS.get(batch.state, set()):
        raise InvalidTransitionError("Illegal batch lifecycle transition", current_state=batch.state, requested=new_state)


# ---------------------------------------------------------------------------
# CreateBatch — BAT-FR-001/002
# ---------------------------------------------------------------------------


class CreateBatchCommand(CommandEnvelope):
    site_id: uuid.UUID
    batch_number: str
    product_version_id: uuid.UUID
    recipe_version_id: uuid.UUID
    target_qty: Decimal
    target_uom: str
    production_order_ref: str | None = None


async def create_batch(session: AsyncSession, cmd: CreateBatchCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    product_version = await session.get(ProductVersion, cmd.product_version_id)
    if product_version is None:
        raise NotFoundError("Product version not found")
    if product_version.lifecycle_state != "released":
        raise ValidationFailedError(
            "Batch can only be created against a released product version", current_state=product_version.lifecycle_state
        )

    recipe_version = await recipe_master_service.get_version(session, cmd.recipe_version_id)
    if recipe_version.lifecycle_state != "released":
        raise ValidationFailedError(
            "Batch can only be created against a released recipe version", current_state=recipe_version.lifecycle_state
        )
    if recipe_version.product_version_id != cmd.product_version_id:
        raise ValidationFailedError(
            "recipe_version_id was not authored against product_version_id",
            recipe_product_version_id=str(recipe_version.product_version_id),
        )

    conflict = (
        await session.execute(select(Batch).where(Batch.site_id == cmd.site_id, Batch.batch_number == cmd.batch_number))
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("batch_number is already in use at this site", site_id=str(cmd.site_id), batch_number=cmd.batch_number)

    batch = Batch(
        site_id=cmd.site_id,
        batch_number=cmd.batch_number,
        product_version_id=cmd.product_version_id,
        recipe_version_id=cmd.recipe_version_id,
        recipe_vault_object_id=recipe_version.released_vault_object_id,
        target_qty=cmd.target_qty,
        target_uom=cmd.target_uom,
        target_uom_id=await _resolve_uom_id(session, cmd.target_uom),
        production_order_ref=cmd.production_order_ref,
        state="planned",
    )
    session.add(batch)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.site_id,
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"batch_number": batch.batch_number, "product_version_id": str(cmd.product_version_id), "recipe_version_id": str(cmd.recipe_version_id)},
    )
    await write_outbox_event(
        session,
        event_type="BatchCreated",
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=1,
        payload={"id": str(batch.id), "batch_number": batch.batch_number},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="CreateBatch",
        aggregate_type="batch",
        aggregate_id=batch.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=batch.id, resulting_version=1, audit_event_id=audit_event.id, correlation_id=correlation_id
    )


# ---------------------------------------------------------------------------
# IssueBatch — BAT-FR-003/004/005/006
# ---------------------------------------------------------------------------


class IssueBatchCommand(CommandEnvelope):
    batch_id: uuid.UUID
    expected_version: int


async def issue_batch(session: AsyncSession, cmd: IssueBatchCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await _load_batch_for_update(session, cmd.batch_id, cmd.expected_version)
    _assert_transition(batch, "issued")

    graph = await recipe_master_service.get_graph(session, batch.recipe_version_id)
    steps = graph["steps"]
    dependencies = graph["dependencies"]
    if not steps:
        raise ValidationFailedError("Recipe version has no steps to instantiate")

    code_by_step_id = {s.id: s.stable_step_code for s in steps}
    initial_states = batch_execution_service.compute_initial_step_states(
        [s.stable_step_code for s in steps], dependencies, code_by_step_id
    )

    vault_object = await vault_service.release_master(
        session,
        object_type="batch_execution_snapshot",
        business_id=str(batch.id),
        site_id=batch.site_id,
        actor_user_id=actor_user_id,
        business_version_label="1",
        canonical_payload={
            "batch_id": str(batch.id),
            "batch_number": batch.batch_number,
            "product_version_id": str(batch.product_version_id),
            "recipe_version_id": str(batch.recipe_version_id),
            "recipe_vault_object_id": str(batch.recipe_vault_object_id) if batch.recipe_vault_object_id else None,
            "target_qty": str(batch.target_qty),
            "target_uom": batch.target_uom,
            "steps": [
                {"code": s.stable_step_code, "step_type": s.step_type, "sequence_hint": s.sequence_hint, "initial_state": initial_states[s.stable_step_code]}
                for s in steps
            ],
            "dependencies": [
                {"predecessor": code_by_step_id.get(d.predecessor_step_id), "successor": code_by_step_id.get(d.successor_step_id)}
                for d in dependencies
            ],
        },
    )
    batch.execution_snapshot_id = vault_object.object_id

    for s in steps:
        session.add(BatchStep(batch_id=batch.id, recipe_step_code=s.stable_step_code, state=initial_states[s.stable_step_code]))

    old_state = batch.state
    batch.state = "issued"
    batch.issued_at = datetime.now(timezone.utc)
    batch.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=batch.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"state": old_state},
        new_value={"state": batch.state, "execution_snapshot_id": str(vault_object.object_id), "step_count": len(steps)},
    )
    await write_outbox_event(
        session,
        event_type="BatchIssued",
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=batch.version,
        payload={"id": str(batch.id), "execution_snapshot_id": str(vault_object.object_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="IssueBatch",
        aggregate_type="batch",
        aggregate_id=batch.id,
        expected_version=cmd.expected_version,
        resulting_version=batch.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=batch.id, resulting_version=batch.version, audit_event_id=audit_event.id, correlation_id=correlation_id
    )


# ---------------------------------------------------------------------------
# Simple batch-state transitions — StartBatch/HoldBatch/ResumeBatch/AbortBatch (BAT-FR-004/019/020/031
# state-machine slice; reason capture goes to the audit event only -- gxp_batch_hold isn't DDL-ready,
# SG-047, so there's no dedicated hold record with its own signature this pass)
# ---------------------------------------------------------------------------


class BatchTransitionCommand(CommandEnvelope):
    batch_id: uuid.UUID
    expected_version: int
    reason: str | None = None


async def _simple_transition(
    session: AsyncSession, cmd: BatchTransitionCommand, actor_user_id: uuid.UUID, *, new_state: str, command_type: str, event_type: str, action: str, timestamp_field: str | None = None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await _load_batch_for_update(session, cmd.batch_id, cmd.expected_version)
    _assert_transition(batch, new_state)
    old_state = batch.state
    batch.state = new_state
    batch.version += 1
    if timestamp_field:
        setattr(batch, timestamp_field, datetime.now(timezone.utc))

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=batch.version,
        action=action,
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        reason=cmd.reason,
        old_value={"state": old_state},
        new_value={"state": batch.state},
    )
    await write_outbox_event(
        session,
        event_type=event_type,
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=batch.version,
        payload={"id": str(batch.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type=command_type,
        aggregate_type="batch",
        aggregate_id=batch.id,
        expected_version=cmd.expected_version,
        resulting_version=batch.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=batch.id, resulting_version=batch.version, audit_event_id=audit_event.id, correlation_id=correlation_id
    )


async def start_batch(session: AsyncSession, cmd: BatchTransitionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    return await _simple_transition(
        session, cmd, actor_user_id, new_state="in_execution", command_type="StartBatch", event_type="BatchStarted", action="Changed", timestamp_field="started_at"
    )


async def hold_batch(session: AsyncSession, cmd: BatchTransitionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    return await _simple_transition(
        session, cmd, actor_user_id, new_state="on_hold", command_type="HoldBatch", event_type="BatchHeld", action="Changed"
    )


async def resume_batch(session: AsyncSession, cmd: BatchTransitionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    return await _simple_transition(
        session, cmd, actor_user_id, new_state="in_execution", command_type="ResumeBatch", event_type="BatchResumed", action="Changed"
    )


async def abort_batch(session: AsyncSession, cmd: BatchTransitionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    return await _simple_transition(
        session, cmd, actor_user_id, new_state="aborted", command_type="AbortBatch", event_type="BatchAborted", action="Changed"
    )


# ---------------------------------------------------------------------------
# StartStep — BAT-FR-007/008
# ---------------------------------------------------------------------------


class StartStepCommand(CommandEnvelope):
    batch_id: uuid.UUID
    step_id: uuid.UUID
    expected_version: int


async def start_step(session: AsyncSession, cmd: StartStepCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await batch_execution_service.get_batch(session, cmd.batch_id)
    if batch.state != "in_execution":
        raise ValidationFailedError("Steps can only be started while the batch is in_execution", current_state=batch.state)

    step = await _load_step_for_update(session, cmd.batch_id, cmd.step_id, cmd.expected_version)
    if step.state != "ready":
        raise InvalidTransitionError("Only a ready step can be claimed/started", current_state=step.state, requested="in_progress")

    step.state = "in_progress"
    step.assigned_subject_id = actor_user_id
    step.started_at = datetime.now(timezone.utc)
    step.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"state": "ready"},
        new_value={"state": "in_progress"},
    )
    await write_outbox_event(
        session,
        event_type="StepStarted",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        payload={"id": str(step.id), "batch_id": str(batch.id), "recipe_step_code": step.recipe_step_code},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="StartStep",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        expected_version=cmd.expected_version,
        resulting_version=step.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=step.id, resulting_version=step.version, audit_event_id=audit_event.id, correlation_id=correlation_id
    )
