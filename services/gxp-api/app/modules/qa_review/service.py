"""Document 14 — the completeness computation (RBE-FR-005, partial) and the computed exceptions/dashboard
read views shared by commands.py and the router.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch_execution.models import Batch
from app.modules.equipment import commands as equipment_commands
from app.modules.equipment.em_models import EmSampleOrReading
from app.modules.equipment.models import EquipmentUseLog
from app.modules.material.models import MaterialIssue, MaterialLot
from app.modules.packaging.models import PackagingRun
from app.modules.qa_review.models import QaReviewPackage
from app.modules.qc.models import OosRecord, QcResult, QcSample, QcTestOrder
from app.modules.vault import service as vault_service
from app.modules.yield_reconciliation.models import ManufacturingCalculation, ReconciliationRecord
from app.mutation.errors import NotFoundError

# Same reasoning as release/service.py's own copy of this constant (yield_reconciliation/commands.py's
# private `_UNRESOLVED_STATES`, duplicated to avoid pulling in that module's full commands.py).
_YIELD_UNRESOLVED_STATES = ("FAILED", "OUT_OF_LIMIT", "OUT_OF_TOLERANCE")


async def get_package(session: AsyncSession, package_id: uuid.UUID) -> QaReviewPackage:
    package = await session.get(QaReviewPackage, package_id)
    if package is None:
        raise NotFoundError("QA review package not found")
    return package


async def get_package_for_batch(session: AsyncSession, batch_id: uuid.UUID) -> QaReviewPackage | None:
    return (
        await session.execute(select(QaReviewPackage).where(QaReviewPackage.batch_id == batch_id))
    ).scalar_one_or_none()


async def list_packages(session: AsyncSession, site_id: uuid.UUID, *, state: str | None = None) -> list[QaReviewPackage]:
    stmt = select(QaReviewPackage).where(QaReviewPackage.site_id == site_id)
    if state is not None:
        stmt = stmt.where(QaReviewPackage.state == state)
    return (await session.execute(stmt.order_by(QaReviewPackage.created_at.desc()))).scalars().all()


async def get_batch(session: AsyncSession, batch_id: uuid.UUID) -> Batch:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")
    return batch


async def get_batch_corrections(session: AsyncSession, batch_id: uuid.UUID) -> list[dict]:
    """RBE-FR-003/006/008 (partial): the 'corrections/audit-trail' slice of the exception index, drawn
    directly from real audit_events for the batch aggregate -- not persisted as its own qa_review_item
    rows. Filters on action == "Corrected" specifically (the vocabulary genealogy's correct_edge() also
    uses) -- ordinary lifecycle transitions (issue/start/hold/resume/abort) use action == "Changed" and
    are not exceptions. batch_execution has no correction command yet (BAT-FR-023 is gapped, SG-047/048),
    so this genuinely returns empty today; it's a forward-compatible hook, not a dead branch -- once a
    real correction command exists anywhere that writes "Corrected" against a "batch" aggregate, it
    surfaces here automatically. Only batch-level events are covered this pass; step-level audit events
    are not joined in -- see SG-054.
    """
    from app.modules.audit.models import AuditEvent

    rows = (
        await session.execute(
            select(AuditEvent)
            .where(AuditEvent.aggregate_type == "batch", AuditEvent.aggregate_id == batch_id, AuditEvent.action == "Corrected")
            .order_by(AuditEvent.occurred_at)
        )
    ).scalars().all()
    return [
        {
            "audit_event_id": str(r.id),
            "occurred_at": r.occurred_at.isoformat(),
            "actor_id": str(r.actor_id),
            "reason": r.reason,
            "old_value": r.old_value,
            "new_value": r.new_value,
        }
        for r in rows
    ]


async def _qc_signals(session: AsyncSession, batch_id: uuid.UUID) -> tuple[list[str], list[str]]:
    """Same QC attribution/severity reasoning as `release/service.py::_qc_signals` (2026-09-19,
    project-owner-directed) -- `QcSample.source_type="batch"`, `QcTestOrder.blocking` orders only, most
    recent `qc_result` per order (append-only, AG-08, so a corrected/retested row naturally supersedes by
    being later). `oos`/`invalid` block; `oot` is a non-blocking warning."""
    order_ids = (
        await session.execute(
            select(QcTestOrder.id)
            .join(QcSample, QcSample.id == QcTestOrder.sample_id)
            .where(QcSample.source_type == "batch", QcSample.source_id == batch_id, QcTestOrder.blocking.is_(True))
        )
    ).scalars().all()
    blockers: list[str] = []
    warnings: list[str] = []
    if order_ids:
        results = (
            await session.execute(
                select(QcResult)
                .where(QcResult.test_order_id.in_(order_ids))
                .order_by(QcResult.test_order_id, QcResult.created_at.desc(), QcResult.id.desc())
            )
        ).scalars().all()
        latest_by_order: dict[uuid.UUID, QcResult] = {}
        for result in results:
            latest_by_order.setdefault(result.test_order_id, result)
        for result in latest_by_order.values():
            if result.outcome in ("oos", "invalid"):
                blockers.append(f"QC result {result.id} outcome is '{result.outcome}' for a release-blocking test")
            elif result.outcome == "oot":
                warnings.append(f"QC result {result.id} outcome is 'oot' (out of trend)")

    open_oos = (
        await session.execute(select(OosRecord).where(OosRecord.batch_id == batch_id, OosRecord.state != "closed"))
    ).scalars().all()
    for oos in open_oos:
        blockers.append(f"OOS record {oos.oos_number} is open for this batch")
    return blockers, warnings


async def _material_signals(session: AsyncSession, batch_id: uuid.UUID) -> list[str]:
    """Same reasoning as `release/service.py::_material_signals` (2026-09-19, project-owner-directed)."""
    lots = (
        await session.execute(
            select(MaterialLot)
            .join(MaterialIssue, MaterialIssue.material_lot_id == MaterialLot.id)
            .where(MaterialIssue.batch_id == batch_id, MaterialLot.status.notin_(("released", "consumed")))
            .distinct()
        )
    ).scalars().all()
    return [f"Material lot {lot.internal_lot} consumed by this batch is '{lot.status}', not released" for lot in lots]


async def _em_signals(session: AsyncSession, batch_id: uuid.UUID) -> tuple[list[str], list[str]]:
    """Same reasoning as `release/service.py::_em_signals` (2026-09-19, project-owner-directed)."""
    readings = (
        await session.execute(
            select(EmSampleOrReading).where(
                EmSampleOrReading.batch_id == batch_id, EmSampleOrReading.alert_action_status.in_(("alert", "action_excursion"))
            )
        )
    ).scalars().all()
    blockers: list[str] = []
    warnings: list[str] = []
    for reading in readings:
        if reading.alert_action_status == "action_excursion":
            blockers.append(f"Environmental monitoring action-excursion recorded for this batch (sample {reading.id})")
        else:
            warnings.append(f"Environmental monitoring alert recorded for this batch (sample {reading.id})")
    return blockers, warnings


async def _equipment_signals(session: AsyncSession, batch_id: uuid.UUID) -> list[str]:
    """Same reasoning as `release/service.py::_equipment_signals` (2026-09-19, project-owner-directed
    follow-up) -- every distinct asset `EquipmentUseLog` records this batch as having used, re-checked
    against its *current* eligibility."""
    asset_ids = (
        await session.execute(
            select(EquipmentUseLog.equipment_asset_id).where(EquipmentUseLog.batch_id == batch_id).distinct()
        )
    ).scalars().all()
    blockers: list[str] = []
    for asset_id in asset_ids:
        eligibility = await equipment_commands.get_eligibility(session, asset_id)
        for reason in eligibility["reasons"]:
            blockers.append(f"Equipment asset {asset_id} used by this batch is currently ineligible: {reason['message']}")
    return blockers


async def _yield_signals(session: AsyncSession, batch_id: uuid.UUID) -> tuple[list[str], list[str]]:
    """Same reasoning as `release/service.py::_yield_signals` (2026-09-19, project-owner-directed follow-
    up, correcting a stale "Document 17 was never built" claim)."""
    calculations = (
        await session.execute(select(ManufacturingCalculation).where(ManufacturingCalculation.batch_id == batch_id))
    ).scalars().all()
    reconciliations = (
        await session.execute(select(ReconciliationRecord).where(ReconciliationRecord.batch_id == batch_id))
    ).scalars().all()
    blockers: list[str] = []
    warnings: list[str] = []
    for calc in calculations:
        if calc.state in _YIELD_UNRESOLVED_STATES:
            blockers.append(f"Manufacturing calculation {calc.id} ({calc.calculation_type}) is '{calc.state}'")
        elif calc.state not in ("VERIFIED", "SUPERSEDED"):
            warnings.append(f"Manufacturing calculation {calc.id} ({calc.calculation_type}) not yet verified (state '{calc.state}')")
    for rec in reconciliations:
        if rec.state in _YIELD_UNRESOLVED_STATES:
            blockers.append(f"Reconciliation record {rec.id} ({rec.reconciliation_type}) is '{rec.state}'")
        elif rec.state not in ("VERIFIED", "SUPERSEDED"):
            warnings.append(f"Reconciliation record {rec.id} ({rec.reconciliation_type}) not yet verified (state '{rec.state}')")
    return blockers, warnings


async def _packaging_signals(session: AsyncSession, batch_id: uuid.UUID) -> list[str]:
    """Non-blocking only, same reasoning as `release/service.py::_packaging_signals` (2026-09-19,
    project-owner-directed: packaging is not a review/release gate this pass)."""
    runs = (await session.execute(select(PackagingRun).where(PackagingRun.batch_id == batch_id))).scalars().all()
    return [
        f"Packaging run {run.id} is '{run.state}' (reconciliation: {run.reconciliation_state})"
        for run in runs
        if run.state != "complete" or run.reconciliation_state == "discrepancy"
    ]


async def _extra_signals(session: AsyncSession, batch_id: uuid.UUID) -> tuple[list[str], list[str]]:
    """The 2026-09-19 wiring: QC/materials/environment/equipment/yield-reconciliation as hard blockers,
    plus their own and packaging's softer-severity signals as non-blocking warnings. See each
    `_*_signals()` docstring for exactly what is (and, for genealogy, still is not -- SG-054) checked and
    why."""
    blockers: list[str] = []
    warnings: list[str] = []
    qc_blockers, qc_warnings = await _qc_signals(session, batch_id)
    blockers.extend(qc_blockers)
    warnings.extend(qc_warnings)
    blockers.extend(await _material_signals(session, batch_id))
    em_blockers, em_warnings = await _em_signals(session, batch_id)
    blockers.extend(em_blockers)
    warnings.extend(em_warnings)
    warnings.extend(await _packaging_signals(session, batch_id))
    blockers.extend(await _equipment_signals(session, batch_id))
    yield_blockers, yield_warnings = await _yield_signals(session, batch_id)
    blockers.extend(yield_blockers)
    warnings.extend(yield_warnings)
    return blockers, warnings


async def compute_completeness(session: AsyncSession, batch: Batch, corrections: list[dict]) -> tuple[str, list[str]]:
    """RBE-FR-005/029 (partial, revised 2026-09-19): batch hold state, manufacturing completeness, Vault
    execution-snapshot integrity, plus QC/materials/environment/equipment/yield-reconciliation
    (`_extra_signals`) as real hard blockers. Genealogy completeness still depends on a regulated rule
    this pass doesn't build (or, for packaging, is deliberately non-blocking) -- see SG-054.

    RBE-FR-001's own "Production-Complete trigger" (SG-054, reopened 2026-09-17 project-owner-directed
    after the matching release/service.py gap was hit live): originally left unbuilt because the
    `production_complete` batch state it depends on didn't exist yet (SG-048 was still open). SG-048 is
    long since resolved -- `gxp_batch.state` reaches `production_complete` today -- so this half of
    SG-054 no longer has a real blocker, and skipping it any further would just be an oversight, not a
    documented decision.
    """
    blockers: list[str] = []
    if batch.state != "production_complete":
        blockers.append("batch is not production_complete")
    if batch.state == "on_hold":
        blockers.append("batch is on_hold")
    if batch.execution_snapshot_id is not None:
        integrity = await vault_service.verify_integrity(session, batch.execution_snapshot_id)
        if not integrity["digest_valid"] or not integrity["link_valid"]:
            blockers.append("execution snapshot integrity check failed")
    extra_blockers, _extra_warnings = await _extra_signals(session, batch.id)
    blockers.extend(extra_blockers)
    if blockers:
        return "blocked", blockers
    if corrections:
        return "has_exceptions", []
    return "complete", []


async def get_exceptions_view(session: AsyncSession, package: QaReviewPackage) -> dict:
    batch = await get_batch(session, package.batch_id)
    corrections = await get_batch_corrections(session, package.batch_id)
    integrity = None
    if batch.execution_snapshot_id is not None:
        integrity = await vault_service.verify_integrity(session, batch.execution_snapshot_id)
    extra_blockers, warnings = await _extra_signals(session, batch.id)
    return {
        "package_id": str(package.id),
        "batch_id": str(package.batch_id),
        "corrections": corrections,
        "integrity_check": integrity,
        "batch_on_hold": batch.state == "on_hold",
        "blockers": extra_blockers,
        "warnings": warnings,
    }
