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
from app.modules.equipment.aseptic_models import AsepticOperation
from app.modules.equipment.cleaning_models import EquipmentArea
from app.modules.equipment.models import EquipmentAsset, EquipmentUseLog
from app.modules.equipment.sterilization_models import ProcessCycle
from app.modules.iam.models import Site, User
from app.modules.material.models import MaterialConsumption, MaterialLot
from app.modules.product_master.models import ProductVersion
from app.modules.qc.models import QcResult, QcSample, QcTestDefinition, QcTestOrder, QcTestSpecification
from app.modules.batch_execution import service as batch_execution_service
from app.modules.qa_review import service as qa_review_service
from app.modules.qms.capa_models import CapaRecord
from app.modules.qms.models import DeviationRecord
from app.modules.recipe_master.models import RecipeFamily, RecipeVersion
from app.modules.release import service as release_service
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

    # 2026-09-22, project-owner-directed: this used to read the retired `MaterialIssue` table, which no
    # frontend page ever wrote to -- the Batch Record's "Materials consumed" section was always empty.
    # `MaterialConsumption` (via Dispensing -> `/dispensing` "Record a consumption") is the real,
    # permission-gated batch-consumption ledger; join through it instead.
    materials_consumed = (
        (
            await session.execute(
                select(MaterialConsumption, MaterialLot)
                .outerjoin(MaterialLot, MaterialLot.id == MaterialConsumption.material_lot_id)
                .where(MaterialConsumption.batch_id == batch_id)
                .order_by(MaterialConsumption.occurred_at)
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
                "material_consumption_id": str(consumption.id),
                "material_lot_id": str(lot.id) if lot else None,
                "internal_lot": lot.internal_lot if lot else None,
                "material_id": str(lot.material_id) if lot else None,
                "step_id": str(consumption.step_id) if consumption.step_id else None,
                "quantity": str(consumption.quantity), "uom": consumption.uom,
                "recorded_by_user_id": str(consumption.recorded_by_user_id),
                "issued_at": consumption.occurred_at.isoformat(),
            }
            for consumption, lot in materials_consumed
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
                "source_type": d.source_type, "source_id": str(d.source_id), "state": d.state,
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


async def build_full_batch_record(session: AsyncSession, batch_id: uuid.UUID) -> dict:
    """Full-parity source for the Batch Record PDF -- composes (does not reimplement) what
    `build_batch_record()`, `batch_execution_service.get_execution_view()`, and this module's own
    product/recipe/site join (mirroring `get_batch_workspace()`'s own `batch_dict`, without that
    function's release/CAPA/aseptic/sterilization scope, which the PDF doesn't need) each already
    provide, since none of the three alone is a complete batch record. Read-only; every row here is
    already gated behind the same `batch_execution.view` policy check the caller (commands.py's
    `generate_batch_record_pdf`) already performs -- this adds no new regulated decision.
    """
    base = await build_batch_record(session, batch_id)
    view = await batch_execution_service.get_execution_view(session, batch_id)

    batch = await session.get(Batch, batch_id)
    product_version = await session.get(ProductVersion, batch.product_version_id)
    site = await session.get(Site, batch.site_id)
    recipe_context = (
        await session.execute(
            select(RecipeFamily.recipe_code, RecipeVersion.version_no)
            .join(RecipeVersion, RecipeVersion.recipe_family_id == RecipeFamily.id)
            .where(RecipeVersion.id == batch.recipe_version_id)
        )
    ).first()
    batch_header = {
        **base["batch"],
        "site_code": site.code if site else None,
        "site_name": site.name if site else None,
        "product_name": product_version.name if product_version else None,
        "product_code": product_version.product_code if product_version else None,
        "recipe_code": recipe_context.recipe_code if recipe_context else None,
        "recipe_version_no": recipe_context.version_no if recipe_context else None,
    }

    user_ids: set[uuid.UUID] = set()
    for comments in view["comments_by_step_id"].values():
        user_ids |= {c.created_by for c in comments}
    for handovers in view["handovers_by_step_id"].values():
        user_ids |= {h.to_subject_id for h in handovers} | {h.from_subject_id for h in handovers if h.from_subject_id}
    for holds in view["holds_by_step_id"].values():
        user_ids |= {h.held_by for h in holds} | {h.released_by for h in holds if h.released_by}
    for corrections in view["corrections_by_step_id"].values():
        user_ids |= {c.requested_by_user_id for c in corrections} | {
            c.approved_by_user_id for c in corrections if c.approved_by_user_id
        }
    users_by_id: dict[uuid.UUID, User] = {}
    if user_ids:
        users_by_id = {u.id: u for u in (await session.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()}

    def _username(user_id):
        u = users_by_id.get(user_id) if user_id else None
        return u.username if u else None

    results_by_id = {r.id: r for rows in view["results_by_step_id"].values() for r in rows}

    step_instructions = []
    comments_flat = []
    handovers_flat = []
    holds_flat = []
    corrections_flat = []
    evidence_links_flat = []
    for s in view["steps"]:
        recipe_step = view["step_by_code"].get(s.recipe_step_code)
        section = view["section_by_id"].get(recipe_step.section_id) if recipe_step else None
        step_instructions.append(
            {
                "recipe_step_code": s.recipe_step_code,
                "section_name": section.name if section else None,
                "instruction_text": recipe_step.instruction_text if recipe_step else None,
                "is_critical": recipe_step.is_critical if recipe_step else None,
            }
        )
        for c in view["comments_by_step_id"].get(s.id, []):
            comments_flat.append(
                {
                    "recipe_step_code": s.recipe_step_code,
                    "comment_text": c.comment_text,
                    "created_by_username": _username(c.created_by),
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
            )
        for h in view["handovers_by_step_id"].get(s.id, []):
            handovers_flat.append(
                {
                    "recipe_step_code": s.recipe_step_code,
                    "from_username": _username(h.from_subject_id),
                    "to_username": _username(h.to_subject_id),
                    "reason": h.reason,
                    "created_at": h.created_at.isoformat() if h.created_at else None,
                }
            )
        for h in view["holds_by_step_id"].get(s.id, []):
            holds_flat.append(
                {
                    "recipe_step_code": s.recipe_step_code,
                    "reason": h.reason,
                    "held_at": h.held_at.isoformat() if h.held_at else None,
                    "held_by_username": _username(h.held_by),
                    "released_at": h.released_at.isoformat() if h.released_at else None,
                    "released_by_username": _username(h.released_by),
                    "release_reason": h.release_reason,
                }
            )
        for c in view["corrections_by_step_id"].get(s.id, []):
            original = results_by_id.get(c.original_result_id)
            corrections_flat.append(
                {
                    "recipe_step_code": s.recipe_step_code,
                    "parameter_code": original.parameter_code if original else None,
                    "requested_by_username": _username(c.requested_by_user_id),
                    "reason_text": c.reason_text,
                    "status": c.status,
                    "approved_by_username": _username(c.approved_by_user_id),
                }
            )
        for e in view["evidence_links_by_step_id"].get(s.id, []):
            evidence_links_flat.append(
                {
                    "recipe_step_code": s.recipe_step_code,
                    "requirement_code": e.requirement_code,
                    "evidence_sha256": e.evidence_sha256,
                    "linked_by_username": _username(e.linked_by),
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
            )

    return {
        **base,
        "batch": batch_header,
        "step_instructions": step_instructions,
        "comments": comments_flat,
        "handovers": handovers_flat,
        "holds": holds_flat,
        "corrections": corrections_flat,
        "evidence_links": evidence_links_flat,
    }


async def get_batch_workspace(session: AsyncSession, batch_id: uuid.UUID) -> dict:
    """Batch Workspace -- one read-only contextual view over a batch's Materials/Lots, QC, Equipment,
    Sterile/Aseptic, Deviations/CAPA, and Release status, so a user doesn't have to visit six separate
    pages to answer "is this batch ready to release, and what's blocking it." Every field here is read
    from an existing authoritative source; nothing here creates or duplicates a mutation path -- each
    section on the frontend links to the real page for the actual action.

    Reuses `build_batch_record()` for materials/equipment/QC/deviations (already built for the batch
    record PDF, client requirement #11) rather than re-querying the same tables a second way. Adds three
    reads that had no batch-scoped path before this: aseptic operations and sterilization cycles (both
    already carry a `batch_id` FK on the row, just never filtered on), and QA review package-by-batch
    (`qa_review_service.get_package_for_batch` already existed, just wasn't wired to a route). CAPAs are
    resolved by matching the batch's own deviations (from build_batch_record) against
    `CapaRecord.source_type == "deviation"` -- CAPA has no direct batch reference, only via its source.
    """
    record = await build_batch_record(session, batch_id)

    # Real labels, not bare UUIDs (same "SG-149/SG-173 cutover" fix batch_execution/router.py's own
    # `_batch_dict()` already applies to the batch list/detail endpoints) -- the Workspace assembles its
    # own batch dict here rather than importing that router helper (a service module doesn't import from
    # its own router).
    batch = await session.get(Batch, batch_id)
    product_version = await session.get(ProductVersion, batch.product_version_id)
    site = await session.get(Site, batch.site_id)
    recipe_context = (
        await session.execute(
            select(RecipeFamily.recipe_code, RecipeVersion.version_no)
            .join(RecipeVersion, RecipeVersion.recipe_family_id == RecipeFamily.id)
            .where(RecipeVersion.id == batch.recipe_version_id)
        )
    ).first()
    batch_dict = {
        **record["batch"],
        "site_code": site.code if site else None,
        "site_name": site.name if site else None,
        "product_name": product_version.name if product_version else None,
        "product_code": product_version.product_code if product_version else None,
        "recipe_code": recipe_context.recipe_code if recipe_context else None,
        "recipe_version_no": recipe_context.version_no if recipe_context else None,
    }

    release_scope = await release_service.get_scope_for_target(session, "batch", batch_id)
    release_evaluation = (
        await release_service.get_current_evaluation(session, release_scope) if release_scope is not None else None
    )

    qa_review_package = await qa_review_service.get_package_for_batch(session, batch_id)

    aseptic_operations = (
        await session.execute(select(AsepticOperation).where(AsepticOperation.batch_id == batch_id))
    ).scalars().all()
    sterilization_cycles = (
        await session.execute(select(ProcessCycle).where(ProcessCycle.batch_id == batch_id))
    ).scalars().all()

    equipment_asset_ids = {uuid.UUID(u["equipment_asset_id"]) for u in record["equipment_used"]} | {
        c.equipment_id for c in sterilization_cycles
    }
    equipment_by_id: dict[uuid.UUID, EquipmentAsset] = {}
    if equipment_asset_ids:
        equipment_by_id = {
            e.id: e
            for e in (
                await session.execute(select(EquipmentAsset).where(EquipmentAsset.id.in_(equipment_asset_ids)))
            ).scalars().all()
        }
    area_ids = {o.area_id for o in aseptic_operations}
    area_by_id: dict[uuid.UUID, EquipmentArea] = {}
    if area_ids:
        area_by_id = {
            a.id: a
            for a in (await session.execute(select(EquipmentArea).where(EquipmentArea.id.in_(area_ids)))).scalars().all()
        }

    deviation_ids = [uuid.UUID(d["id"]) for d in record["deviations"]]
    capas = (
        (
            await session.execute(
                select(CapaRecord).where(CapaRecord.source_type == "deviation", CapaRecord.source_id.in_(deviation_ids))
            )
        )
        .scalars()
        .all()
        if deviation_ids
        else []
    )

    # Step sequence + dependency graph, for a wizard-style progress view. Reuses get_execution_view()'s
    # own predecessor/successor computation (already built for the step Detail modal's "Predecessors"/
    # "Unblocks next" fields) rather than re-deriving it from the recipe graph a second way.
    execution_view = await batch_execution_service.get_execution_view(session, batch_id)
    predecessors_of: dict[str, list[str]] = execution_view["predecessors_of"]

    # Kahn's algorithm -- get_steps() has no ORDER BY (raw DB/insertion order), which isn't guaranteed to
    # match the recipe's actual dependency order. Ties (independent/parallel steps) keep insertion order.
    remaining = list(execution_view["steps"])
    ordered: list = []
    placed_codes: set[str] = set()
    while remaining:
        ready = [s for s in remaining if all(p in placed_codes for p in predecessors_of.get(s.recipe_step_code, []))]
        if not ready:
            # A cycle or an unresolvable predecessor reference -- fall back to whatever is left, in their
            # original order, rather than looping forever or dropping steps from the view.
            ready = remaining
        for s in ready:
            ordered.append(s)
            placed_codes.add(s.recipe_step_code)
        remaining = [s for s in remaining if s.recipe_step_code not in placed_codes]

    steps_with_deps = [
        {
            "step_id": str(s.id),
            "recipe_step_code": s.recipe_step_code,
            "state": s.state,
            "required_role_code": s.required_role_code,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "predecessor_codes": predecessors_of.get(s.recipe_step_code, []),
            "successor_codes": execution_view["successors_of"].get(s.recipe_step_code, []),
        }
        for s in ordered
    ]

    return {
        "batch": batch_dict,
        "steps": steps_with_deps,
        "materials_consumed": record["materials_consumed"],
        "equipment_used": [
            {**u, "equipment_code": (equipment_by_id[uuid.UUID(u["equipment_asset_id"])].equipment_code if uuid.UUID(u["equipment_asset_id"]) in equipment_by_id else None)}
            for u in record["equipment_used"]
        ],
        "qc_results": record["qc_results"],
        "deviations": record["deviations"],
        "capas": [
            {
                "id": str(c.id), "capa_number": c.capa_number, "state": c.state, "risk_class": c.risk_class,
                "source_id": str(c.source_id),
            }
            for c in capas
        ],
        "aseptic_operations": [
            {
                "id": str(o.id), "state": o.state, "area_id": str(o.area_id),
                "area_code": area_by_id[o.area_id].area_code if o.area_id in area_by_id else None,
                "created_at": o.created_at.isoformat(),
            }
            for o in aseptic_operations
        ],
        "sterilization_cycles": [
            {
                "id": str(c.id), "state": c.state, "process_type": c.process_type,
                "equipment_id": str(c.equipment_id),
                "equipment_code": equipment_by_id[c.equipment_id].equipment_code if c.equipment_id in equipment_by_id else None,
                "created_at": c.created_at.isoformat(),
            }
            for c in sterilization_cycles
        ],
        "qa_review_package": (
            {
                "package_id": str(qa_review_package.id), "state": qa_review_package.state,
                "completeness_status": qa_review_package.completeness_status,
            }
            if qa_review_package is not None
            else None
        ),
        "release": {
            "scope_id": str(release_scope.id) if release_scope is not None else None,
            "eligible": release_evaluation.eligible if release_evaluation is not None else None,
            "blockers": release_evaluation.blockers if release_evaluation is not None else [],
            "warnings": release_evaluation.warnings if release_evaluation is not None else [],
        },
    }
