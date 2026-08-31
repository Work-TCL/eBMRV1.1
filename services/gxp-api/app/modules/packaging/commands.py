"""Document 16 (SPEC-EBMR-007) — the buildable slice: create a packaging run against a batch, complete
line clearance, issue labels (with duplicate-serial detection), reconcile labels (real quantities in,
Document 16 §10's exact-balance default since no released tolerance rule exists), reconcile packaging
(component/finished-pack balance -- no dedicated entity exists for this, so it updates
packaging_run.reconciliation_state directly rather than a persisted line-item row), complete (gated on
clearance + both reconciliations balanced), and hold. None of Document 16's 10 operations require a
Document 106 signature. Print jobs/reprint/application-verification/inspection are not built -- no entity
exists for any of them -- see SG-056.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.packaging import service as packaging_service
from app.modules.packaging.models import ALLOWED_TRANSITIONS, LabelIssue, LabelReconciliation, PackagingRun
from app.mutation.errors import InvalidTransitionError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
        audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _load_run_for_update(session: AsyncSession, run_id: uuid.UUID, expected_version: int) -> PackagingRun:
    result = await session.execute(select(PackagingRun).where(PackagingRun.id == run_id).with_for_update())
    run = result.scalar_one_or_none()
    if run is None:
        raise NotFoundError("Packaging run not found")
    if run.version != expected_version:
        raise StaleVersionError("Packaging run was modified by another actor since it was read", expected_version=expected_version, current_version=run.version)
    return run


async def _simple_transition(session: AsyncSession, run: PackagingRun, new_state: str) -> None:
    if new_state not in ALLOWED_TRANSITIONS.get(run.state, set()):
        raise InvalidTransitionError("Illegal packaging run transition", current_state=run.state, requested=new_state)
    run.state = new_state


# ---------------------------------------------------------------------------
# CreatePackagingRun — PKG-FR-001
# ---------------------------------------------------------------------------


class CreatePackagingRunCommand(CommandEnvelope):
    batch_id: uuid.UUID
    line_ref: str | None = None


async def create_packaging_run(session: AsyncSession, cmd: CreatePackagingRunCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await packaging_service.get_batch(session, cmd.batch_id)
    run = PackagingRun(site_id=batch.site_id, batch_id=batch.id, product_version_id=batch.product_version_id, line_ref=cmd.line_ref, state="not_ready")
    session.add(run)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=run.site_id, aggregate_type="packaging_run", aggregate_id=run.id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id, new_value={"batch_id": str(batch.id)},
    )
    await write_outbox_event(session, event_type="PackagingRunStarted", aggregate_type="packaging_run", aggregate_id=run.id, aggregate_version=1, payload={"id": str(run.id)}, correlation_id=correlation_id)
    receipt = await record_command_receipt(
        session, site_id=run.site_id, command_type="CreatePackagingRun", aggregate_type="packaging_run", aggregate_id=run.id,
        expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key, command_hash=payload_hash,
        actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(command_id=receipt.id, aggregate_id=run.id, resulting_version=1, audit_event_id=audit_event.id, correlation_id=correlation_id)


# ---------------------------------------------------------------------------
# LineClearance — PKG-FR-009
# ---------------------------------------------------------------------------


class LineClearanceCommand(CommandEnvelope):
    run_id: uuid.UUID
    expected_version: int
    reason: str | None = None


async def complete_line_clearance(session: AsyncSession, cmd: LineClearanceCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    run = await _load_run_for_update(session, cmd.run_id, cmd.expected_version)
    old_state = run.state
    await _simple_transition(session, run, "ready")
    run.line_clearance_completed = True
    run.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=run.site_id, aggregate_type="packaging_run", aggregate_id=run.id, aggregate_version=run.version,
        action="Changed", actor_id=actor_user_id, correlation_id=correlation_id, reason=cmd.reason,
        old_value={"state": old_state}, new_value={"state": run.state, "line_clearance_completed": True},
    )
    await write_outbox_event(session, event_type="LineClearanceCompleted", aggregate_type="packaging_run", aggregate_id=run.id, aggregate_version=run.version, payload={"id": str(run.id)}, correlation_id=correlation_id)
    receipt = await record_command_receipt(
        session, site_id=run.site_id, command_type="LineClearance", aggregate_type="packaging_run", aggregate_id=run.id,
        expected_version=cmd.expected_version, resulting_version=run.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(command_id=receipt.id, aggregate_id=run.id, resulting_version=run.version, audit_event_id=audit_event.id, correlation_id=correlation_id)


# ---------------------------------------------------------------------------
# IssueLabel — PKG-FR-004/008
# ---------------------------------------------------------------------------


class IssueLabelCommand(CommandEnvelope):
    run_id: uuid.UUID
    expected_version: int
    label_version_id: uuid.UUID | None = None
    quantity_issued: int
    serial_range: dict | None = None


async def issue_label(session: AsyncSession, cmd: IssueLabelCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    run = await _load_run_for_update(session, cmd.run_id, cmd.expected_version)
    if run.state not in ("ready", "in_progress"):
        raise ValidationFailedError("Labels can only be issued while the packaging run is ready or in progress", current_state=run.state)
    if cmd.quantity_issued <= 0:
        raise ValidationFailedError("quantity_issued must be positive")

    await packaging_service.assert_no_duplicate_serials(session, run.product_version_id, cmd.serial_range)

    label = LabelIssue(
        packaging_run_id=run.id, label_version_id=cmd.label_version_id, quantity_issued=cmd.quantity_issued,
        serial_range=cmd.serial_range, issued_by=actor_user_id, state="issued",
    )
    session.add(label)

    old_state = run.state
    if run.state == "ready":
        run.state = "in_progress"
        run.started_at = datetime.now(timezone.utc)
    run.version += 1
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=run.site_id, aggregate_type="packaging_run", aggregate_id=run.id, aggregate_version=run.version,
        action="Changed", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": run.state, "label_issue_id": str(label.id), "quantity_issued": cmd.quantity_issued},
    )
    await write_outbox_event(session, event_type="LabelIssued", aggregate_type="packaging_run", aggregate_id=run.id, aggregate_version=run.version, payload={"id": str(run.id), "label_issue_id": str(label.id)}, correlation_id=correlation_id)
    receipt = await record_command_receipt(
        session, site_id=run.site_id, command_type="IssueLabel", aggregate_type="packaging_run", aggregate_id=run.id,
        expected_version=cmd.expected_version, resulting_version=run.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(command_id=receipt.id, aggregate_id=run.id, resulting_version=run.version, audit_event_id=audit_event.id, correlation_id=correlation_id)


# ---------------------------------------------------------------------------
# ReconcileLabels — PKG-FR-013/014
# ---------------------------------------------------------------------------


class ReconcileLabelsCommand(CommandEnvelope):
    run_id: uuid.UUID
    expected_version: int
    applied: int = 0
    returned: int = 0
    destroyed: int = 0
    rejected: int = 0
    samples: int = 0


async def reconcile_labels(session: AsyncSession, cmd: ReconcileLabelsCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    run = await _load_run_for_update(session, cmd.run_id, cmd.expected_version)
    if run.state not in ("in_progress", "reconciliation_pending"):
        raise ValidationFailedError("Labels can only be reconciled while the run is in progress or pending reconciliation", current_state=run.state)

    issues = await packaging_service.get_label_issues(session, run.id)
    issued_total = sum(i.quantity_issued for i in issues)
    variance, result = packaging_service.compute_reconciliation(issued_total, cmd.applied, cmd.returned, cmd.destroyed, cmd.rejected, cmd.samples)

    reconciliation = LabelReconciliation(
        packaging_run_id=run.id, issued=issued_total, applied=cmd.applied, returned=cmd.returned, destroyed=cmd.destroyed,
        rejected=cmd.rejected, samples=cmd.samples, calculated_variance=variance, result=result,
    )
    session.add(reconciliation)

    old_state = run.state
    await _simple_transition(session, run, "reconciliation_pending")
    run.version += 1
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=run.site_id, aggregate_type="packaging_run", aggregate_id=run.id, aggregate_version=run.version,
        action="Changed", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": run.state, "label_reconciliation_result": result, "variance": variance},
    )
    await write_outbox_event(session, event_type="LabelReconciliationCompleted", aggregate_type="packaging_run", aggregate_id=run.id, aggregate_version=run.version, payload={"id": str(run.id), "result": result}, correlation_id=correlation_id)
    receipt = await record_command_receipt(
        session, site_id=run.site_id, command_type="ReconcileLabels", aggregate_type="packaging_run", aggregate_id=run.id,
        expected_version=cmd.expected_version, resulting_version=run.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(command_id=receipt.id, aggregate_id=run.id, resulting_version=run.version, audit_event_id=audit_event.id, correlation_id=correlation_id)


# ---------------------------------------------------------------------------
# ReconcilePackaging — PKG-FR-017 (no dedicated entity -- updates packaging_run.reconciliation_state directly)
# ---------------------------------------------------------------------------


class ReconcilePackagingCommand(CommandEnvelope):
    run_id: uuid.UUID
    expected_version: int
    components_issued: int
    finished_packs: int = 0
    rejects: int = 0
    samples: int = 0
    destroyed: int = 0


async def reconcile_packaging(session: AsyncSession, cmd: ReconcilePackagingCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    run = await _load_run_for_update(session, cmd.run_id, cmd.expected_version)
    if run.state not in ("in_progress", "reconciliation_pending"):
        raise ValidationFailedError("Packaging can only be reconciled while the run is in progress or pending reconciliation", current_state=run.state)

    _variance, result = packaging_service.compute_reconciliation(cmd.components_issued, cmd.finished_packs, 0, cmd.destroyed, cmd.rejects, cmd.samples)

    old_state = run.state
    old_reconciliation_state = run.reconciliation_state
    run.reconciliation_state = result
    await _simple_transition(session, run, "reconciliation_pending")
    run.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=run.site_id, aggregate_type="packaging_run", aggregate_id=run.id, aggregate_version=run.version,
        action="Changed", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state, "reconciliation_state": old_reconciliation_state},
        new_value={"state": run.state, "reconciliation_state": result},
    )
    await write_outbox_event(session, event_type="PackagingReconciliationCompleted", aggregate_type="packaging_run", aggregate_id=run.id, aggregate_version=run.version, payload={"id": str(run.id), "result": result}, correlation_id=correlation_id)
    receipt = await record_command_receipt(
        session, site_id=run.site_id, command_type="ReconcilePackaging", aggregate_type="packaging_run", aggregate_id=run.id,
        expected_version=cmd.expected_version, resulting_version=run.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(command_id=receipt.id, aggregate_id=run.id, resulting_version=run.version, audit_event_id=audit_event.id, correlation_id=correlation_id)


# ---------------------------------------------------------------------------
# CompletePackagingRun — PKG-FR-028
# ---------------------------------------------------------------------------


class CompletePackagingRunCommand(CommandEnvelope):
    run_id: uuid.UUID
    expected_version: int


async def complete_packaging_run(session: AsyncSession, cmd: CompletePackagingRunCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    run = await _load_run_for_update(session, cmd.run_id, cmd.expected_version)
    if "complete" not in ALLOWED_TRANSITIONS.get(run.state, set()):
        raise InvalidTransitionError("Illegal packaging run transition", current_state=run.state, requested="complete")
    if not run.line_clearance_completed:
        raise ValidationFailedError("Packaging run cannot complete before line clearance")
    if run.reconciliation_state != "balanced":
        raise ValidationFailedError("Packaging run cannot complete with unresolved packaging reconciliation", reconciliation_state=run.reconciliation_state)
    reconciliations = await packaging_service.get_reconciliations(session, run.id)
    if not reconciliations or reconciliations[-1].result != "balanced":
        raise ValidationFailedError("Packaging run cannot complete with unresolved label reconciliation")

    old_state = run.state
    run.state = "complete"
    run.ended_at = datetime.now(timezone.utc)
    run.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=run.site_id, aggregate_type="packaging_run", aggregate_id=run.id, aggregate_version=run.version,
        action="Changed", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": "complete"},
    )
    await write_outbox_event(session, event_type="PackagingCompleted", aggregate_type="packaging_run", aggregate_id=run.id, aggregate_version=run.version, payload={"id": str(run.id)}, correlation_id=correlation_id)
    receipt = await record_command_receipt(
        session, site_id=run.site_id, command_type="CompletePackagingRun", aggregate_type="packaging_run", aggregate_id=run.id,
        expected_version=cmd.expected_version, resulting_version=run.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(command_id=receipt.id, aggregate_id=run.id, resulting_version=run.version, audit_event_id=audit_event.id, correlation_id=correlation_id)
