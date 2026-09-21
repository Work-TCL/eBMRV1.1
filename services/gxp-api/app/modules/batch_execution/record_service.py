"""Client requirement #11 -- a structured Batch Record view aggregating a completed batch's execution
history (steps/results, material consumption, equipment used, operators, deviations, QC results,
signatures/status history) plus a controlled PDF rendering of it. Read-only aggregation; `commands.py`
owns the one write path (`generate_batch_record_pdf`) that stores the rendered PDF as evidence.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent
from app.modules.audit.service import actor_usernames_for, event_to_dict
from app.modules.batch_execution.models import Batch, BatchStep, StepResult
from app.modules.equipment.models import EquipmentUseLog
from app.modules.material.models import MaterialIssue, MaterialLot
from app.modules.qc.models import QcResult, QcSample, QcTestDefinition, QcTestOrder, QcTestSpecification
from app.modules.qms.models import DeviationRecord
from app.mutation.errors import NotFoundError


async def build_batch_record(session: AsyncSession, batch_id: uuid.UUID) -> dict:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    steps = (
        (await session.execute(select(BatchStep).where(BatchStep.batch_id == batch_id).order_by(BatchStep.recipe_step_code)))
        .scalars()
        .all()
    )
    step_ids = [s.id for s in steps]

    results_by_step: dict[uuid.UUID, list[StepResult]] = {}
    if step_ids:
        for result in (
            (await session.execute(select(StepResult).where(StepResult.step_id.in_(step_ids)).order_by(StepResult.received_at)))
            .scalars()
            .all()
        ):
            results_by_step.setdefault(result.step_id, []).append(result)

    materials_consumed = (
        (
            await session.execute(
                select(MaterialIssue, MaterialLot)
                .join(MaterialLot, MaterialLot.id == MaterialIssue.material_lot_id)
                .where(MaterialIssue.batch_id == batch_id)
                .order_by(MaterialIssue.issued_at)
            )
        )
        .all()
    )

    equipment_used = (
        (
            await session.execute(
                select(EquipmentUseLog).where(EquipmentUseLog.batch_id == batch_id).order_by(EquipmentUseLog.occurred_at)
            )
        )
        .scalars()
        .all()
    )

    deviations = (
        (
            await session.execute(
                select(DeviationRecord).where(
                    DeviationRecord.source_type.in_(("batch", "batch_step")), DeviationRecord.source_id == batch_id
                )
            )
        )
        .scalars()
        .all()
    )
    if step_ids:
        deviations = list(deviations) + list(
            (
                await session.execute(
                    select(DeviationRecord).where(
                        DeviationRecord.source_type == "batch_step", DeviationRecord.source_id.in_(step_ids)
                    )
                )
            )
            .scalars()
            .all()
        )

    # QC results attributed to the batch as a whole (finished/final testing) and to individual steps
    # (in-process testing) -- same QcSample.source_type polymorphism release/service.py's own QC gate uses.
    qc_source_ids = [batch_id, *step_ids]
    qc_rows = (
        await session.execute(
            select(QcSample, QcTestOrder, QcTestDefinition, QcTestSpecification, QcResult)
            .join(QcTestOrder, QcTestOrder.sample_id == QcSample.id)
            .join(QcTestDefinition, QcTestDefinition.id == QcTestOrder.test_definition_id)
            .join(QcTestSpecification, QcTestSpecification.id == QcTestDefinition.specification_id)
            .outerjoin(QcResult, QcResult.test_order_id == QcTestOrder.id)
            .where(QcSample.source_type.in_(("batch", "batch_step")), QcSample.source_id.in_(qc_source_ids))
            .order_by(QcSample.sample_number)
        )
    ).all()

    audit_events = (
        (
            await session.execute(
                select(AuditEvent)
                .where(AuditEvent.aggregate_type == "batch", AuditEvent.aggregate_id == batch_id)
                .order_by(AuditEvent.occurred_at)
            )
        )
        .scalars()
        .all()
    )
    usernames = await actor_usernames_for(session, audit_events)
    status_history = [await event_to_dict(session, e, usernames) for e in audit_events]
    signatures = [e for e in status_history if e.get("signature_id")]

    operator_ids = {r.created_by for results in results_by_step.values() for r in results}
    operator_ids |= {u.operator_user_id for u in equipment_used if u.operator_user_id}

    return {
        "batch": {
            "id": str(batch.id), "site_id": str(batch.site_id), "batch_number": batch.batch_number,
            "product_version_id": str(batch.product_version_id), "recipe_version_id": str(batch.recipe_version_id),
            "target_qty": str(batch.target_qty), "target_uom": batch.target_uom, "state": batch.state,
            "version": batch.version, "issued_at": batch.issued_at.isoformat() if batch.issued_at else None,
            "started_at": batch.started_at.isoformat() if batch.started_at else None,
            "production_completed_at": batch.production_completed_at.isoformat() if batch.production_completed_at else None,
            "closed_at": batch.closed_at.isoformat() if batch.closed_at else None,
        },
        "steps": [
            {
                "id": str(s.id), "recipe_step_code": s.recipe_step_code, "state": s.state,
                "assigned_subject_id": str(s.assigned_subject_id) if s.assigned_subject_id else None,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "results": [
                    {
                        "parameter_code": r.parameter_code,
                        "value": str(r.value_numeric) if r.value_numeric is not None else (r.value_text or str(r.value_bool)),
                        "uom": r.uom, "quality_status": r.quality_status,
                        "recorded_by_user_id": str(r.created_by), "received_at": r.received_at.isoformat(),
                    }
                    for r in results_by_step.get(s.id, [])
                ],
            }
            for s in steps
        ],
        "materials_consumed": [
            {
                "material_issue_id": str(issue.id), "material_lot_id": str(lot.id), "internal_lot": lot.internal_lot,
                "material_id": str(lot.material_id), "quantity": str(issue.quantity), "uom": issue.uom,
                "issued_by_user_id": str(issue.issued_by_user_id), "issued_at": issue.issued_at.isoformat(),
            }
            for issue, lot in materials_consumed
        ],
        "equipment_used": [
            {
                "id": str(u.id), "equipment_asset_id": str(u.equipment_asset_id), "log_type": u.log_type,
                "step_id": str(u.step_id) if u.step_id else None,
                "operator_user_id": str(u.operator_user_id) if u.operator_user_id else None,
                "occurred_at": u.occurred_at.isoformat(),
            }
            for u in equipment_used
        ],
        "deviations": [
            {
                "id": str(d.id), "deviation_number": d.deviation_number, "deviation_type": d.deviation_type,
                "source_type": d.source_type, "state": d.state,
            }
            for d in deviations
        ],
        "qc_results": [
            {
                "sample_id": str(sample.id), "sample_number": sample.sample_number, "source_type": sample.source_type,
                "spec_code": spec.spec_code, "scope_type": spec.scope_type, "test_code": definition.test_code,
                "test_order_id": str(order.id), "order_state": order.state,
                "outcome": result.outcome if result else None,
                "value": str(result.value_decimal) if result and result.value_decimal is not None else (result.value_text if result else None),
            }
            for sample, order, definition, spec, result in qc_rows
        ],
        "operator_user_ids": [str(uid) for uid in operator_ids],
        "signatures": signatures,
        "status_history": status_history,
    }
