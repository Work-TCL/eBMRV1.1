"""Document 15 — the eligibility computation (REL-FR-003, partial) and read views shared by commands.py
and the router.
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
from app.modules.qa_review import service as qa_review_service
from app.modules.qc.models import OosRecord, QcResult, QcSample, QcTestOrder
from app.modules.qms.capa_models import CapaRecord
from app.modules.qms.models import DeviationRecord
from app.modules.release.models import ReleaseDecision, ReleaseEvaluation, ReleaseScope
from app.modules.vault import service as vault_service
from app.modules.yield_reconciliation.models import ManufacturingCalculation, ReconciliationRecord
from app.mutation.errors import NotFoundError

# yield_reconciliation/commands.py's own `_UNRESOLVED_STATES` -- duplicated here rather than importing
# that module's full commands.py (which pulls in erp/device/packaging/qms transitively for its own
# unrelated commands); this 3-tuple is the entire piece actually needed.
_YIELD_UNRESOLVED_STATES = ("FAILED", "OUT_OF_LIMIT", "OUT_OF_TOLERANCE")


async def get_scope(session: AsyncSession, scope_id: uuid.UUID) -> ReleaseScope:
    scope = await session.get(ReleaseScope, scope_id)
    if scope is None:
        raise NotFoundError("Release scope not found")
    return scope


async def get_scope_for_target(session: AsyncSession, scope_type: str, scope_id: uuid.UUID) -> ReleaseScope | None:
    return (
        await session.execute(
            select(ReleaseScope).where(ReleaseScope.scope_type == scope_type, ReleaseScope.scope_id == scope_id)
        )
    ).scalar_one_or_none()


async def get_batch(session: AsyncSession, batch_id: uuid.UUID) -> Batch:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")
    return batch


async def get_current_evaluation(session: AsyncSession, scope: ReleaseScope) -> ReleaseEvaluation | None:
    if scope.current_evaluation_id is None:
        return None
    return await session.get(ReleaseEvaluation, scope.current_evaluation_id)


async def get_decisions(session: AsyncSession, scope_id: uuid.UUID) -> list[ReleaseDecision]:
    return (
        (
            await session.execute(
                select(ReleaseDecision).where(ReleaseDecision.release_scope_id == scope_id).order_by(ReleaseDecision.decision_time)
            )
        )
        .scalars()
        .all()
    )


def _blocker(code: str, severity: str, source_type: str, source_id: str | None, message_key: str, resolution_action: str) -> dict:
    """Document 15 §6's blocker contract."""
    return {
        "code": code,
        "severity": severity,
        "source_type": source_type,
        "source_id": source_id,
        "message_key": message_key,
        "resolution_action": resolution_action,
    }


def _warning(code: str, source_type: str, source_id: str | None, message_key: str, resolution_action: str) -> dict:
    """Same shape as `_blocker()` (Document 15 §6), `severity="WARNING"` -- visible on the release screen
    via `ReleaseEvaluation.warnings` but never contributes to `eligible`/`blockers` (2026-09-19,
    project-owner-directed, see the wiring note in `evaluate_eligibility()` below)."""
    return {
        "code": code,
        "severity": "WARNING",
        "source_type": source_type,
        "source_id": source_id,
        "message_key": message_key,
        "resolution_action": resolution_action,
    }


async def _qc_signals(session: AsyncSession, batch_id: uuid.UUID) -> tuple[list[dict], list[dict]]:
    """QC results attributed to this batch via `QcSample.source_type="batch"` (the same 4-source_type
    polymorphic pattern `DeviationRecord.source_type`/`source_id` below already uses), restricted to
    `QcTestOrder.blocking` orders (dual-written from `QcTestDefinition.release_blocking` at order-creation
    time -- app/modules/qc/commands.py:744 -- so reading the order's own flag avoids a second join). Only
    the most recently recorded result per test order counts, since `qc_result` is append-only (AG-08) and
    a controlled correction/retest (`approve_result_correction`) always adds a new, later row rather than
    editing the failing one -- a resolved OOS whose retest passed stops blocking; a confirmed true failure
    with no correcting result keeps blocking, correctly, forever. `oos`/`invalid` outcomes block;
    `oot` (out-of-trend) is a QA watch signal, not a confirmed failure -- non-blocking warning only
    (2026-09-19, project-owner-directed)."""
    order_ids = (
        await session.execute(
            select(QcTestOrder.id)
            .join(QcSample, QcSample.id == QcTestOrder.sample_id)
            .where(QcSample.source_type == "batch", QcSample.source_id == batch_id, QcTestOrder.blocking.is_(True))
        )
    ).scalars().all()
    if not order_ids:
        return [], []

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

    blockers: list[dict] = []
    warnings: list[dict] = []
    for result in latest_by_order.values():
        if result.outcome in ("oos", "invalid"):
            blockers.append(
                _blocker(
                    "QC_RESULT_FAILED", "CRITICAL", "qc_result", str(result.id),
                    "release.blocker.qc_result_failed", "RESOLVE_QC_RESULT",
                )
            )
        elif result.outcome == "oot":
            warnings.append(
                _warning("QC_RESULT_OOT", "qc_result", str(result.id), "release.warning.qc_result_oot", "REVIEW_QC_TREND")
            )

    open_oos = (
        await session.execute(select(OosRecord).where(OosRecord.batch_id == batch_id, OosRecord.state != "closed"))
    ).scalars().all()
    for oos in open_oos:
        blockers.append(
            _blocker("OPEN_OOS", "CRITICAL", "oos_record", str(oos.id), "release.blocker.open_oos", "RESOLVE_OOS")
        )
    return blockers, warnings


async def _material_signals(session: AsyncSession, batch_id: uuid.UUID) -> list[dict]:
    """Materials consumed by this batch (`MaterialIssue.batch_id`, "the batch's material genealogy trace
    for Phase 1" per material/models.py:145) whose lot is not in a released-for-use state
    (`MaterialLot.status`) block -- `quarantine`/`sampling`/`testing`/`qc_disposition_pending`/
    `retest_due`/`rejected`/`expired` all mean the lot was never cleared, or was cleared and then
    withdrawn; only `released`/`consumed` mean it legitimately went into this batch (2026-09-19,
    project-owner-directed)."""
    lots = (
        await session.execute(
            select(MaterialLot)
            .join(MaterialIssue, MaterialIssue.material_lot_id == MaterialLot.id)
            .where(MaterialIssue.batch_id == batch_id, MaterialLot.status.notin_(("released", "consumed")))
            .distinct()
        )
    ).scalars().all()
    return [
        _blocker(
            "MATERIAL_LOT_NOT_RELEASED", "CRITICAL", "material_lot", str(lot.id),
            "release.blocker.material_lot_not_released", "DISPOSITION_MATERIAL_LOT",
        )
        for lot in lots
    ]


async def _em_signals(session: AsyncSession, batch_id: uuid.UUID) -> tuple[list[dict], list[dict]]:
    """Environmental monitoring readings attributed to this batch (`EmSampleOrReading.batch_id`).
    `action_excursion` is a confirmed limit breach -- blocks; `alert` is the lower watch-level threshold --
    non-blocking warning only (2026-09-19, project-owner-directed, same severity split as QC oot above)."""
    readings = (
        await session.execute(
            select(EmSampleOrReading).where(
                EmSampleOrReading.batch_id == batch_id, EmSampleOrReading.alert_action_status.in_(("alert", "action_excursion"))
            )
        )
    ).scalars().all()
    blockers: list[dict] = []
    warnings: list[dict] = []
    for reading in readings:
        if reading.alert_action_status == "action_excursion":
            blockers.append(
                _blocker(
                    "EM_ACTION_EXCURSION", "CRITICAL", "em_sample_or_reading", str(reading.id),
                    "release.blocker.em_action_excursion", "RESOLVE_EM_EXCURSION",
                )
            )
        else:
            warnings.append(
                _warning("EM_ALERT", "em_sample_or_reading", str(reading.id), "release.warning.em_alert", "REVIEW_EM_ALERT")
            )
    return blockers, warnings


async def _equipment_signals(session: AsyncSession, batch_id: uuid.UUID) -> list[dict]:
    """2026-09-19, project-owner-directed follow-up: `batch_execution/commands.py::start_step` now writes
    an `EquipmentUseLog` row (`log_type="production"`) for the asset that satisfied each step's equipment
    requirement -- previously checked live at step-start and discarded, so nothing could ever answer "did
    this batch use equipment that has since gone on hold, fallen out of calibration/qualification, or
    needs cleaning". Re-runs the same `equipment.commands.get_eligibility()` check step-start already uses,
    against the asset's *current* state, for every distinct asset this batch is on record as having used.
    Unlike QC oot/EM alert, equipment eligibility has no separate watch-level tier to carve into a warning
    -- every reason `get_eligibility` returns is a confirmed, present-tense ineligibility, so all of them
    block (same treatment as the other hard blockers above)."""
    asset_ids = (
        await session.execute(
            select(EquipmentUseLog.equipment_asset_id).where(EquipmentUseLog.batch_id == batch_id).distinct()
        )
    ).scalars().all()
    blockers: list[dict] = []
    for asset_id in asset_ids:
        eligibility = await equipment_commands.get_eligibility(session, asset_id)
        for reason in eligibility["reasons"]:
            # reason["code"] reuses the same code vocabulary start_step's own _EQUIPMENT_REASON_ERRORS
            # already raises with (CALIBRATION_EXPIRED, EQUIPMENT_NOT_QUALIFIED, CLEANING_REQUIRED,
            # EQUIPMENT_OUT_OF_SERVICE, POST_MAINTENANCE_VERIFICATION_REQUIRED) -- more informative than a
            # single generic code, and consistent with the "one blocker per real problem" pattern above.
            blockers.append(
                _blocker(
                    reason["code"], "CRITICAL", "equipment_asset", str(asset_id),
                    "release.blocker.equipment_not_eligible", "RESOLVE_EQUIPMENT_INELIGIBILITY",
                )
            )
    return blockers


async def _capa_signals(session: AsyncSession, batch_id: uuid.UUID) -> list[dict]:
    """2026-09-19, project-owner-directed follow-up -- but NOT by adding "batch" to `CAPA_SOURCE_TYPES`:
    Document 27 (CAPA-FR-001) names exactly 11 source types a CAPA may be opened from (deviation/oos/oot/
    ncr/complaint/audit/supplier/risk/trend/security/validation) and "batch" is deliberately not one of
    them -- capa_commands.py's own docstring already records that as a known limitation, and this module's
    docstring used to record the project owner's explicit prior choice not to invent a 12th. Inventing one
    now would reopen a decision already made the other way.

    Instead: a CAPA whose source IS an open-or-closed deviation/OOS that is itself attributed to this batch
    (`source_type="batch"`, the same attribution DEV-FR-002/the OosRecord.batch_id column already define)
    is a real, spec-compliant two-hop relationship -- no new vocabulary, no guessed field. Any such CAPA
    still open (state not in CLOSED/CANCELLED, capa_record's only two terminal states) blocks, same
    "resolve it, one blocker per record" treatment as OPEN_DEVIATION/OPEN_OOS above."""
    deviation_ids = (
        await session.execute(
            select(DeviationRecord.id).where(DeviationRecord.source_type == "batch", DeviationRecord.source_id == batch_id)
        )
    ).scalars().all()
    oos_ids = (await session.execute(select(OosRecord.id).where(OosRecord.batch_id == batch_id))).scalars().all()

    source_ids = list(deviation_ids) + list(oos_ids)
    if not source_ids:
        return []

    open_capas = (
        await session.execute(
            select(CapaRecord).where(
                CapaRecord.source_type.in_(("deviation", "oos")),
                CapaRecord.source_id.in_(source_ids),
                CapaRecord.state.notin_(("CLOSED", "CANCELLED")),
            )
        )
    ).scalars().all()
    return [
        _blocker("OPEN_CAPA", "CRITICAL", "capa_record", str(capa.id), "release.blocker.open_capa", "RESOLVE_CAPA")
        for capa in open_capas
    ]


async def _yield_signals(session: AsyncSession, batch_id: uuid.UUID) -> tuple[list[dict], list[dict]]:
    """2026-09-19, project-owner-directed follow-up -- correcting a stale claim: this docstring (and
    docs/testing/demo-gujarati/12) used to say Document 17 (yield/reconciliation) "was never built". It
    was: `yield_reconciliation/commands.py::get_batch_summary` already computes a `release_blocked` flag
    from exactly this reasoning (`_UNRESOLVED_STATES = ("FAILED", "OUT_OF_LIMIT", "OUT_OF_TOLERANCE")`,
    YLD-FR-028/029's own "QA/Release visibility + the release-blocker flag") -- it was simply never called
    from here. `ManufacturingCalculation`/`ReconciliationRecord` are both real, batch-attributed
    (`batch_id` NOT NULL FK) tables; a corrected/recalculated row supersedes the old one to `SUPERSEDED`
    (excluded from both blockers and warnings below, same as QC's append-only "latest wins" pattern).
    A calculated-but-not-yet-QA-verified row is a non-blocking warning, matching the OOT/alert severity
    split above -- it is on a path to being fine, just not yet formally signed off."""
    calculations = (
        await session.execute(select(ManufacturingCalculation).where(ManufacturingCalculation.batch_id == batch_id))
    ).scalars().all()
    reconciliations = (
        await session.execute(select(ReconciliationRecord).where(ReconciliationRecord.batch_id == batch_id))
    ).scalars().all()

    blockers: list[dict] = []
    warnings: list[dict] = []
    for calc in calculations:
        if calc.state in _YIELD_UNRESOLVED_STATES:
            blockers.append(
                _blocker(
                    "YIELD_CALCULATION_UNRESOLVED", "CRITICAL", "manufacturing_calculation", str(calc.id),
                    "release.blocker.yield_calculation_unresolved", "RESOLVE_YIELD_CALCULATION",
                )
            )
        elif calc.state not in ("VERIFIED", "SUPERSEDED"):
            warnings.append(
                _warning(
                    "YIELD_CALCULATION_NOT_VERIFIED", "manufacturing_calculation", str(calc.id),
                    "release.warning.yield_calculation_not_verified", "VERIFY_YIELD_CALCULATION",
                )
            )
    for rec in reconciliations:
        if rec.state in _YIELD_UNRESOLVED_STATES:
            blockers.append(
                _blocker(
                    "RECONCILIATION_UNRESOLVED", "CRITICAL", "reconciliation_record", str(rec.id),
                    "release.blocker.reconciliation_unresolved", "RESOLVE_RECONCILIATION",
                )
            )
        elif rec.state not in ("VERIFIED", "SUPERSEDED"):
            warnings.append(
                _warning(
                    "RECONCILIATION_NOT_VERIFIED", "reconciliation_record", str(rec.id),
                    "release.warning.reconciliation_not_verified", "VERIFY_RECONCILIATION",
                )
            )
    return blockers, warnings


async def _packaging_signals(session: AsyncSession, batch_id: uuid.UUID) -> list[dict]:
    """Packaging is deliberately NOT a release gate this pass (2026-09-19, project-owner-directed: batch
    release is the bulk/production disposition; packaging/labeling is tracked independently and happens on
    its own timeline relative to release, matching Document 16's own "post-batch" framing rather than a
    guessed ordering). An incomplete or unbalanced run is surfaced as a non-blocking warning only."""
    runs = (await session.execute(select(PackagingRun).where(PackagingRun.batch_id == batch_id))).scalars().all()
    warnings: list[dict] = []
    for run in runs:
        if run.state != "complete" or run.reconciliation_state == "discrepancy":
            warnings.append(
                _warning(
                    "PACKAGING_INCOMPLETE", "packaging_run", str(run.id),
                    "release.warning.packaging_incomplete", "REVIEW_PACKAGING_RUN",
                )
            )
    return warnings


async def evaluate_eligibility(session: AsyncSession, batch: Batch) -> tuple[list[dict], list[dict]]:
    """REL-FR-003/004/025 (partial, revised 2026-09-19): eight of the nine named eligibility categories now
    have a real, wired data source -- manufacturing completeness (BAT-FR-026's own `production_complete`
    batch state), QA review currency/completeness (Document 14), Vault execution-snapshot integrity
    (Document 06), QMS/deviation (below, SG-059), QC (`_qc_signals`), materials (`_material_signals`),
    environment (`_em_signals`), equipment (`_equipment_signals`, now that `start_step` persists which asset
    satisfied each step's requirement), and yield/reconciliation (`_yield_signals` -- correcting a stale
    claim this docstring used to make: Document 17 was NOT "never built", `yield_reconciliation/
    commands.py::get_batch_summary` already computed a `release_blocked` flag from exactly this reasoning,
    it was just never called from here). Only genealogy still has no usable data source: nodes/edges have
    no completeness rule defined anywhere this pass has authority to invent (SG-054's own reasoning --
    populating the graph, done separately in `genealogy/service.py`, is not the same thing as knowing what
    "complete" means for it). Packaging has a real data source (`_packaging_signals`) but is deliberately
    non-blocking, see that function's docstring. CAPA is now wired too (below,
    2026-09-19) -- deviation's sibling using the same `source_type="batch"` attribution, now that
    `CAPA_SOURCE_TYPES` includes "batch".

    Manufacturing completeness (SG-180, reopened 2026-09-17 project-owner-directed after a live batch
    was reviewed and released with 6 of 9 recipe steps still incomplete): REL-FR-003 names "manufacturing
    completeness" as one of the nine eligibility categories, and BAT-FR-026 already defines what that
    means -- `gxp_batch.state == "production_complete"`, which `complete_production()`
    (batch_execution/commands.py) already refuses to set until every applicable step is `complete`. This
    was simply never read on the release side. Blocking here (and on the final `release_release()` call,
    which re-evaluates via this same function) closes exactly the gap SG-180 documented without touching
    the separate, still-open DDCP/generic-step-sync question (SG-180's options B/C) -- this only reads
    the batch's own already-enforced completeness state, no new step-sync logic."""
    blockers: list[dict] = []

    if batch.state != "production_complete":
        blockers.append(
            _blocker(
                "PRODUCTION_NOT_COMPLETE", "CRITICAL", "batch", str(batch.id),
                "release.blocker.production_not_complete", "MARK_PRODUCTION_COMPLETE",
            )
        )

    package = await qa_review_service.get_package_for_batch(session, batch.id)
    if package is None:
        blockers.append(
            _blocker("QA_REVIEW_MISSING", "CRITICAL", "qa_review_package", None, "release.blocker.qa_review_missing", "CREATE_QA_REVIEW_PACKAGE")
        )
    else:
        if package.state != "REVIEW_COMPLETE":
            blockers.append(
                _blocker(
                    "REVIEW_NOT_CURRENT", "CRITICAL", "qa_review_package", str(package.id),
                    "release.blocker.review_not_complete", "COMPLETE_QA_REVIEW",
                )
            )
        elif package.batch_version != batch.version:
            blockers.append(
                _blocker(
                    "REVIEW_NOT_CURRENT", "CRITICAL", "qa_review_package", str(package.id),
                    "release.blocker.review_stale", "REINDEX_AND_RECOMPLETE_QA_REVIEW",
                )
            )

    if batch.state == "on_hold":
        blockers.append(_blocker("BATCH_ON_HOLD", "CRITICAL", "batch", str(batch.id), "release.blocker.batch_on_hold", "RESOLVE_BATCH_HOLD"))

    if batch.execution_snapshot_id is not None:
        integrity = await vault_service.verify_integrity(session, batch.execution_snapshot_id)
        if not integrity["digest_valid"] or not integrity["link_valid"]:
            blockers.append(
                _blocker(
                    "INTEGRITY_CHECK_FAILED", "CRITICAL", "vault_object", str(batch.execution_snapshot_id),
                    "release.blocker.integrity_failed", "INVESTIGATE_INTEGRITY_FAILURE",
                )
            )

    # SG-059 RESOLVED 2026-09-18, project-owner-directed (asked directly among "any open deviation" /
    # "critical-only" / "don't block" -- chose the first, reading DEV-FR-022's "open... deviations"
    # literally rather than adding an unwritten severity carve-out). Deviations attributed to this batch
    # (`source_type="batch"`, `source_id=batch.id` -- the same attribution DEV-FR-002 defines and the demo
    # walkthrough already uses) block release for as long as they haven't reached the only terminal state
    # `deviation_record` has (`CLOSED` -- there is no CANCELLED for deviations, unlike CAPA). One blocker
    # per open deviation so the caller can see exactly which records need resolving, matching the
    # INTEGRITY_CHECK_FAILED pattern above. CAPA deliberately does NOT get an equivalent gate here --
    # Document 27 has no requirement analogous to DEV-FR-022 to hang one on, and the project owner chose
    # not to invent one.
    open_deviations = (
        await session.execute(
            select(DeviationRecord.id).where(
                DeviationRecord.source_type == "batch",
                DeviationRecord.source_id == batch.id,
                DeviationRecord.state != "CLOSED",
            )
        )
    ).scalars().all()
    for deviation_id in open_deviations:
        blockers.append(
            _blocker(
                "OPEN_DEVIATION", "CRITICAL", "deviation_record", str(deviation_id),
                "release.blocker.open_deviation", "RESOLVE_DEVIATION",
            )
        )

    # 2026-09-19, project-owner-directed (SG-056 follow-up): QC, materials and environment each got a
    # real data source since SG-056 was written -- see the module docstrings above for exactly what each
    # one checks and why. Packaging has data too but is deliberately warning-only, never a blocker.
    warnings: list[dict] = []
    qc_blockers, qc_warnings = await _qc_signals(session, batch.id)
    blockers.extend(qc_blockers)
    warnings.extend(qc_warnings)
    blockers.extend(await _material_signals(session, batch.id))
    em_blockers, em_warnings = await _em_signals(session, batch.id)
    blockers.extend(em_blockers)
    warnings.extend(em_warnings)
    warnings.extend(await _packaging_signals(session, batch.id))
    blockers.extend(await _equipment_signals(session, batch.id))
    blockers.extend(await _capa_signals(session, batch.id))
    yield_blockers, yield_warnings = await _yield_signals(session, batch.id)
    blockers.extend(yield_blockers)
    warnings.extend(yield_warnings)

    return blockers, warnings
