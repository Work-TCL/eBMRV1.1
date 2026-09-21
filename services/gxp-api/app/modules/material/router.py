import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.batch_execution.models import Batch
from app.modules.iam.models import User
from app.modules.material.commands import (
    ApproveInventoryAdjustmentRequestCommand,
    CancelDispensingCommand,
    CollectSampleCommand,
    CompleteDispensingCommand,
    CreateCycleCountCommand,
    CreateDestructionRequestCommand,
    CreateDispensingOrderCommand,
    CreateInventoryAdjustmentRequestCommand,
    CreateInventoryReservationCommand,
    CreateInventoryTransferCommand,
    CreateMaterialCommand,
    CreateMaterialReceiptCommand,
    CreateSamplingOrderCommand,
    CreateWarehouseLocationCommand,
    DeleteMaterialCommand,
    DispositionMaterialLotCommand,
    EvaluateMaterialReconciliationCommand,
    ExamineReceiptCommand,
    ExecuteDestructionCommand,
    MergeContainersCommand,
    ReceiveMaterialLotCommand,
    RecordConsumptionCommand,
    RecordManualReadingCommand,
    RecordMaterialLossCommand,
    RecordReadingCommand,
    RecordReturnCommand,
    RejectInventoryAdjustmentRequestCommand,
    RejectMaterialLotCommand,
    ReleaseInventoryReservationCommand,
    ReleaseMaterialLotCommand,
    RetestMaterialLotCommand,
    SelectDispensingSourceCommand,
    SplitContainerCommand,
    StartDispensingCommand,
    UpdateMaterialCommand,
    VerifyDispensingCommand,
    approve_inventory_adjustment_request,
    cancel_dispensing,
    collect_sample,
    complete_dispensing,
    create_cycle_count,
    create_destruction_request,
    create_dispensing_order,
    create_inventory_adjustment_request,
    create_inventory_reservation,
    create_inventory_transfer,
    create_material,
    create_material_receipt,
    create_sampling_order,
    create_warehouse_location,
    delete_material,
    destruction_record_hash,
    dispensing_order_record_hash,
    disposition_material_lot,
    evaluate_material_reconciliation,
    examine_receipt,
    execute_destruction,
    get_erp_reconciliation,
    get_inventory_availability,
    get_material_reconciliation,
    get_quality_status,
    get_release_readiness,
    inventory_adjustment_request_record_hash,
    lot_record_hash,
    merge_containers,
    receive_material_lot,
    record_consumption,
    record_manual_reading,
    record_material_loss,
    record_reading,
    record_return,
    reject_inventory_adjustment_request,
    reject_material_lot,
    release_inventory_reservation,
    release_material_lot,
    reservation_record_hash,
    retest_material_lot,
    select_dispensing_source,
    split_container,
    start_dispensing,
    update_material,
    verify_dispensing,
)
from app.modules.material.models import (
    DestructionRecord,
    DispensedContainer,
    DispensingOrder,
    InventoryAdjustmentRequest,
    InventoryReservation,
    InventoryTransaction,
    Material,
    MaterialContainer,
    MaterialLot,
    MaterialReceipt,
    SamplingOrder,
    WarehouseLocation,
)
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import create_challenge
from app.modules.supplier_quality.models import Supplier
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/materials", tags=["material"])
lots_router = APIRouter(prefix="/material-lots", tags=["material"])
v1_router = APIRouter(prefix="/materials/v1", tags=["material"])
sampling_orders_router = APIRouter(prefix="/sampling-orders", tags=["material"])
inventory_v1_router = APIRouter(prefix="/inventory/v1", tags=["inventory"])
dispensing_v1_router = APIRouter(prefix="/dispensing/v1", tags=["dispensing"])
reconciliation_v1_router = APIRouter(prefix="/reconciliation/v1", tags=["reconciliation"])


async def _resolve_destruction_scope_site_id(
    session: AsyncSession,
    *,
    material_lot_id: uuid.UUID | None,
    container_id: uuid.UUID | None,
    dispensed_container_id: uuid.UUID | None,
) -> uuid.UUID:
    """Document 22 destruction scope is XOR of material_lot_id/container_id/dispensed_container_id --
    none of those carry site_id directly except via MaterialLot/Batch, so site scope is resolved by
    walking to whichever one is actually set. Cardinality is checked here too (not only inside
    create_destruction_request) so an all-absent/all-present scope fails with CON-FR-015's own
    VALIDATION_FAILED rather than a misleading NOT_FOUND from `session.get(..., None)`."""
    scopes = [s for s in (material_lot_id, container_id, dispensed_container_id) if s is not None]
    if len(scopes) != 1:
        raise ValidationFailedError(
            "Exactly one of material_lot_id, container_id, dispensed_container_id must be set (CON-FR-015)"
        )
    if dispensed_container_id is not None:
        container = await session.get(DispensedContainer, dispensed_container_id)
        if container is None:
            raise NotFoundError("Dispensed container not found")
        batch = await session.get(Batch, container.batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        return batch.site_id
    if container_id is not None:
        mc = await session.get(MaterialContainer, container_id)
        if mc is None:
            raise NotFoundError("Material container not found")
        lot = await session.get(MaterialLot, mc.material_lot_id)
        if lot is None:
            raise NotFoundError("Material lot not found")
        return lot.site_id
    lot = await session.get(MaterialLot, material_lot_id)
    if lot is None:
        raise NotFoundError("Material lot not found")
    return lot.site_id

# Document 106 rows 44/45 (SPEC-MAT-002A) meaning per action — distinct from the legacy "disposition"
# challenge below, which stays untouched (Document 18-era, meaning "Disposition").
_QUALITY_DISPOSITION_MEANING = {"release": "Released", "reject": "Rejected"}

MATERIAL_SORTABLE = {
    "code": Material.code,
    "name": Material.name,
    "status": Material.status,
    "created_at": Material.created_at,
}

LOT_SORTABLE = {
    "internal_lot": MaterialLot.internal_lot,
    "status": MaterialLot.status,
    "expiry_date": MaterialLot.expiry_date,
    "received_at": MaterialLot.received_at,
    "released_at": MaterialLot.released_at,
    "material_code": Material.code,
}


@router.post("", response_model=MutationReceipt)
async def post_create_material(
    cmd: CreateMaterialCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        # 2026-09-18, project-owner-directed: create_material() had no evaluate_policy() call at all —
        # same "master-data technical author" role class as material_spec.author/product.author.
        await evaluate_policy(session, actor.user_id, action="material.create", site_id=None)
        return await create_material(session, cmd, actor.user_id)


@router.get("")
async def list_materials(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params)
) -> dict:
    stmt = select(Material)
    if params.q:
        needle = f"%{params.q}%"
        stmt = stmt.where(or_(Material.code.ilike(needle), Material.name.ilike(needle)))
    rows, envelope = await paginate(
        session, stmt, params, sortable=MATERIAL_SORTABLE, default_sort=Material.created_at
    )
    return {
        **envelope,
        "items": [
            {
                "id": str(m.id),
                "site_id": str(m.site_id),
                "code": m.code,
                "name": m.name,
                "uom": m.uom,
                "status": m.status,
                "version": m.version,
            }
            for (m,) in rows
        ],
    }


@router.patch("/{material_id}", response_model=MutationReceipt)
async def patch_material(
    material_id: uuid.UUID,
    cmd: UpdateMaterialCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.material_id != material_id:
        raise ValidationFailedError("material_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="material.update", site_id=None)
        return await update_material(session, cmd, actor.user_id)


@router.delete("/{material_id}", response_model=MutationReceipt)
async def delete_material_endpoint(
    material_id: uuid.UUID,
    cmd: DeleteMaterialCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.material_id != material_id:
        raise ValidationFailedError("material_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await delete_material(session, cmd, actor.user_id)


@router.post("/{material_id}/lots", response_model=MutationReceipt)
async def post_receive_lot(
    material_id: uuid.UUID,
    cmd: ReceiveMaterialLotCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.material_id != material_id:
        raise ValidationFailedError("material_id in path and body must match")
    async with session.begin():
        # 2026-09-19, docs/testing/demo-gujarati/03 gap: this legacy direct-lot-creation path (still
        # actively used by frontend/src/app/material-lots/page.tsx, unlike the retired /batches scaffold)
        # had no evaluate_policy() call at all -- any authenticated user, any role, could receive a lot.
        # Reuses `material_receipt.create`, the permission the real Document 19 receipt flow
        # (POST /materials/v1/receipts) already gates the equivalent action with, rather than inventing a
        # new code. That flow is unsigned too (receipt/receiving is RBAC-only in this codebase; e-signature
        # applies to QC disposition/release, not raw receipt) -- so no signature ceremony is added here either.
        await evaluate_policy(session, actor.user_id, action="material_receipt.create", site_id=cmd.site_id)
        return await receive_material_lot(session, cmd, actor.user_id)


def _lot_dict(lot: MaterialLot, material_code: str, material_name: str) -> dict:
    return {
        "id": str(lot.id),
        "site_id": str(lot.site_id),
        "material_id": str(lot.material_id),
        "material_code": material_code,
        "material_name": material_name,
        "internal_lot": lot.internal_lot,
        "supplier_id": str(lot.supplier_id) if lot.supplier_id else None,
        "supplier_lot": lot.supplier_lot,
        "manufacturer_lot": lot.manufacturer_lot,
        "received_quantity": str(lot.received_quantity),
        "available_quantity": str(lot.available_quantity),
        "uom": lot.uom,
        "uom_id": str(lot.uom_id) if lot.uom_id else None,
        "status": lot.status,
        "received_by_user_id": str(lot.received_by_user_id),
        "received_at": lot.received_at.isoformat() if lot.received_at else None,
        "released_at": lot.released_at.isoformat() if lot.released_at else None,
        "release_signature_id": str(lot.release_signature_id) if lot.release_signature_id else None,
        "expiry_date": lot.expiry_date.isoformat() if lot.expiry_date else None,
        "retest_date": lot.retest_date.isoformat() if lot.retest_date else None,
        "material_spec_version_id": str(lot.material_spec_version_id) if lot.material_spec_version_id else None,
        "receipt_id": str(lot.receipt_id) if lot.receipt_id else None,
        "manufacture_date": lot.manufacture_date.isoformat() if lot.manufacture_date else None,
        "version": lot.version,
    }


@lots_router.get("")
async def list_material_lots(
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    status: str | None = None,
) -> dict:
    stmt = select(MaterialLot, Material.code, Material.name).join(Material, Material.id == MaterialLot.material_id)
    if params.q:
        needle = f"%{params.q}%"
        stmt = stmt.where(
            or_(
                MaterialLot.internal_lot.ilike(needle),
                Material.code.ilike(needle),
                Material.name.ilike(needle),
            )
        )
    if status:
        stmt = stmt.where(MaterialLot.status == status)

    rows, envelope = await paginate(
        session, stmt, params, sortable=LOT_SORTABLE, default_sort=MaterialLot.received_at
    )
    return {
        **envelope,
        "items": [_lot_dict(lot, code, name) for lot, code, name in rows],
    }


@lots_router.get("/{lot_id}")
async def get_material_lot(lot_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(
        select(MaterialLot, Material.code, Material.name)
        .join(Material, Material.id == MaterialLot.material_id)
        .where(MaterialLot.id == lot_id)
    )
    row = result.first()
    if row is None:
        raise NotFoundError("Material lot not found")
    lot, code, name = row
    return _lot_dict(lot, code, name)


def _container_dict(c: MaterialContainer) -> dict:
    return {
        "id": str(c.id),
        "material_lot_id": str(c.material_lot_id),
        "container_code": c.container_code,
        "received_quantity": str(c.received_quantity),
        "current_quantity": str(c.current_quantity),
        "uom": c.uom,
        "uom_id": str(c.uom_id) if c.uom_id else None,
        "location_zone": c.location_zone,
        "container_status": c.container_status,
        "quality_status_override": c.quality_status_override,
        "sampled": c.sampled,
        "seal_status": c.seal_status,
        "parent_container_id": str(c.parent_container_id) if c.parent_container_id else None,
        "source_container_ids": c.source_container_ids,
        "version": c.version,
    }


# 2026-09-07: read-only container listing. No Document 20 API-list entry declares this operation (same
# class of omission as SG-081's warehouse_location), but unlike that case no prior resolution rejected it
# -- this is additive read-model data (container_code/quantity/status only, no mutation, no regulated
# decision), added so the Inventory forms (Transfer/Cycle count/Adjustment) can offer a real dropdown
# instead of requiring an operator to hand-type a container UUID copied out of the database.
@lots_router.get("/{lot_id}/containers")
async def list_lot_containers(lot_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    lot = await session.get(MaterialLot, lot_id)
    if lot is None:
        raise NotFoundError("Material lot not found")
    rows = (
        await session.execute(
            select(MaterialContainer)
            .where(MaterialContainer.material_lot_id == lot_id)
            .order_by(MaterialContainer.container_code)
        )
    ).scalars().all()
    return {"items": [_container_dict(c) for c in rows]}


class LotSignatureChallengeRequest(BaseModel):
    action: str  # "disposition" (legacy, Document 18) | "release" | "reject" (Document 19, RCV-FR-026/027)


_LOT_CHALLENGE_MEANINGS = {"disposition": "Disposition", **_QUALITY_DISPOSITION_MEANING}


@lots_router.post("/{lot_id}/signature-challenges")
async def post_lot_signature_challenge(
    lot_id: uuid.UUID,
    body: LotSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        lot = await session.get(MaterialLot, lot_id)
        if lot is None:
            raise NotFoundError("Material lot not found")
        meaning = _LOT_CHALLENGE_MEANINGS.get(body.action)
        if meaning is None:
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session,
            user_id=actor.user_id,
            record_type="material_lot",
            record_id=lot.id,
            record_version=lot.version,
            record_hash=lot_record_hash(lot),
            meaning=meaning,
        )
        return {
            "challenge_id": str(challenge.id),
            "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


@lots_router.post("/{lot_id}/disposition", response_model=MutationReceipt)
async def post_disposition_lot(
    lot_id: uuid.UUID,
    cmd: DispositionMaterialLotCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.lot_id != lot_id:
        raise ValidationFailedError("lot_id in path and body must match")
    async with session.begin():
        lot = await session.get(MaterialLot, lot_id)
        if lot is None:
            raise NotFoundError("Material lot not found")
        return await disposition_material_lot(session, cmd, actor.user_id, lot.site_id)


# ---------------------------------------------------------------------------
# Document 19 (SPEC-MAT-002A) §5 — exactly the 9 declared operations, no invented endpoints.
# ---------------------------------------------------------------------------


@v1_router.post("/receipts", response_model=MutationReceipt)
async def post_create_receipt(
    cmd: CreateMaterialReceiptCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="material_receipt.create", site_id=cmd.site_id)
        return await create_material_receipt(session, cmd, actor.user_id)


def _receipt_dict(
    receipt_row: MaterialReceipt,
    material_code: str,
    material_name: str,
    supplier_code: str | None,
    supplier_name: str | None,
    manufacturer_code: str | None,
    manufacturer_name: str | None,
) -> dict:
    return {
        "id": str(receipt_row.id),
        "site_id": str(receipt_row.site_id),
        "receipt_number": receipt_row.receipt_number,
        "po_reference": receipt_row.po_reference,
        "material_id": str(receipt_row.material_id),
        "material_code": material_code,
        "material_name": material_name,
        "supplier_id": str(receipt_row.supplier_id) if receipt_row.supplier_id else None,
        "supplier_code": supplier_code,
        "supplier_name": supplier_name,
        "manufacturer_id": str(receipt_row.manufacturer_id) if receipt_row.manufacturer_id else None,
        "manufacturer_code": manufacturer_code,
        "manufacturer_name": manufacturer_name,
        "supplier_lot": receipt_row.supplier_lot,
        "manufacturer_lot": receipt_row.manufacturer_lot,
        "carrier_reference": receipt_row.carrier_reference,
        "received_gross_quantity": str(receipt_row.received_gross_quantity),
        "received_net_quantity": str(receipt_row.received_net_quantity) if receipt_row.received_net_quantity else None,
        "accepted_quantity": str(receipt_row.accepted_quantity) if receipt_row.accepted_quantity else None,
        "uom": receipt_row.uom,
        "uom_id": str(receipt_row.uom_id) if receipt_row.uom_id else None,
        "manufacture_date": receipt_row.manufacture_date.isoformat() if receipt_row.manufacture_date else None,
        "expiry_date": receipt_row.expiry_date.isoformat() if receipt_row.expiry_date else None,
        "retest_date": receipt_row.retest_date.isoformat() if receipt_row.retest_date else None,
        "shipment_condition_status": receipt_row.shipment_condition_status,
        "coa_vault_object_id": str(receipt_row.coa_vault_object_id) if receipt_row.coa_vault_object_id else None,
        "coa_document_hash": receipt_row.coa_document_hash,
        "receiver_subject_id": str(receipt_row.receiver_subject_id),
        "state": receipt_row.state,
        "labeling_ok": receipt_row.labeling_ok,
        "damage_observed": receipt_row.damage_observed,
        "seal_broken": receipt_row.seal_broken,
        "contamination_observed": receipt_row.contamination_observed,
        "examination_notes": receipt_row.examination_notes,
        "examined_by_user_id": str(receipt_row.examined_by_user_id) if receipt_row.examined_by_user_id else None,
        "examined_at": receipt_row.examined_at.isoformat() if receipt_row.examined_at else None,
        "discrepancy_type": receipt_row.discrepancy_type,
        "discrepancy_reason": receipt_row.discrepancy_reason,
        "received_at": receipt_row.received_at.isoformat() if receipt_row.received_at else None,
        "version": receipt_row.version,
    }


RECEIPT_SORTABLE = {
    "receipt_number": MaterialReceipt.receipt_number,
    "state": MaterialReceipt.state,
    "received_at": MaterialReceipt.received_at,
    "material_code": Material.code,
}

# supplier_id and manufacturer_id are two independent, optional FKs into the same Supplier table (a
# receipt's supplier and its manufacturer can be different parties, or the same, or either unset) --
# two aliases so both resolve to a name/code in one query instead of the frontend showing a bare UUID.
_ReceiptSupplier = aliased(Supplier)
_ReceiptManufacturer = aliased(Supplier)


def _receipt_select():
    return (
        select(
            MaterialReceipt, Material.code, Material.name,
            _ReceiptSupplier.supplier_code, _ReceiptSupplier.legal_name,
            _ReceiptManufacturer.supplier_code, _ReceiptManufacturer.legal_name,
        )
        .join(Material, Material.id == MaterialReceipt.material_id)
        .outerjoin(_ReceiptSupplier, _ReceiptSupplier.id == MaterialReceipt.supplier_id)
        .outerjoin(_ReceiptManufacturer, _ReceiptManufacturer.id == MaterialReceipt.manufacturer_id)
    )


# A read the frontend needs (a browsable receipts list — WP-06-style ops screens with no list endpoint
# are the exception, not the rule; every other module's register/lots/etc. already has one) — not one
# of Document 19 §5's 9 declared *mutating* operations, so it carries no signature/authority implication;
# same GET-alongside-the-mutating-set precedent as `list_material_lots` below and `get_migration_legacy_trace`
# in the validation module.
@v1_router.get("/receipts")
async def list_material_receipts(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params)
) -> dict:
    stmt = _receipt_select()
    if params.q:
        needle = f"%{params.q}%"
        stmt = stmt.where(
            or_(
                MaterialReceipt.receipt_number.ilike(needle),
                Material.code.ilike(needle),
                Material.name.ilike(needle),
            )
        )
    rows, envelope = await paginate(
        session, stmt, params, sortable=RECEIPT_SORTABLE, default_sort=MaterialReceipt.received_at
    )
    return {
        **envelope,
        "items": [
            _receipt_dict(r, code, name, s_code, s_name, m_code, m_name)
            for r, code, name, s_code, s_name, m_code, m_name in rows
        ],
    }


@v1_router.get("/receipts/{receipt_id}")
async def get_receipt(receipt_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    row = (
        await session.execute(_receipt_select().where(MaterialReceipt.id == receipt_id))
    ).first()
    if row is None:
        raise NotFoundError("Material receipt not found")
    receipt_row, material_code, material_name, supplier_code, supplier_name, manufacturer_code, manufacturer_name = row
    return _receipt_dict(
        receipt_row, material_code, material_name, supplier_code, supplier_name, manufacturer_code, manufacturer_name
    )


@v1_router.post("/receipts/{receipt_id}/examine", response_model=MutationReceipt)
async def post_examine_receipt(
    receipt_id: uuid.UUID,
    cmd: ExamineReceiptCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.receipt_id != receipt_id:
        raise ValidationFailedError("receipt_id in path and body must match")
    async with session.begin():
        receipt_row = await session.get(MaterialReceipt, receipt_id)
        if receipt_row is None:
            raise NotFoundError("Material receipt not found")
        await evaluate_policy(session, actor.user_id, action="material_receipt.examine", site_id=receipt_row.site_id)
        return await examine_receipt(session, cmd, actor.user_id)


@v1_router.post("/lots/{lot_id}/sampling-orders", response_model=MutationReceipt)
async def post_create_sampling_order(
    lot_id: uuid.UUID,
    cmd: CreateSamplingOrderCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.lot_id != lot_id:
        raise ValidationFailedError("lot_id in path and body must match")
    async with session.begin():
        lot = await session.get(MaterialLot, lot_id)
        if lot is None:
            raise NotFoundError("Material lot not found")
        await evaluate_policy(session, actor.user_id, action="material_lot.sampling_order", site_id=lot.site_id)
        return await create_sampling_order(session, cmd, actor.user_id, lot.site_id)


@sampling_orders_router.post("/{sampling_order_id}/collect", response_model=MutationReceipt)
async def post_collect_sample(
    sampling_order_id: uuid.UUID,
    cmd: CollectSampleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.sampling_order_id != sampling_order_id:
        raise ValidationFailedError("sampling_order_id in path and body must match")
    async with session.begin():
        order = await session.get(SamplingOrder, sampling_order_id)
        if order is None:
            raise NotFoundError("Sampling order not found")
        lot = await session.get(MaterialLot, order.material_lot_id)
        if lot is None:
            raise NotFoundError("Material lot not found")
        await evaluate_policy(session, actor.user_id, action="material_lot.collect_sample", site_id=lot.site_id)
        return await collect_sample(session, cmd, actor.user_id, lot.site_id)


@v1_router.post("/lots/{lot_id}/release", response_model=MutationReceipt)
async def post_release_lot(
    lot_id: uuid.UUID,
    cmd: ReleaseMaterialLotCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.lot_id != lot_id:
        raise ValidationFailedError("lot_id in path and body must match")
    async with session.begin():
        lot = await session.get(MaterialLot, lot_id)
        if lot is None:
            raise NotFoundError("Material lot not found")
        return await release_material_lot(session, cmd, actor.user_id, lot.site_id)


@v1_router.post("/lots/{lot_id}/reject", response_model=MutationReceipt)
async def post_reject_lot(
    lot_id: uuid.UUID,
    cmd: RejectMaterialLotCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.lot_id != lot_id:
        raise ValidationFailedError("lot_id in path and body must match")
    async with session.begin():
        lot = await session.get(MaterialLot, lot_id)
        if lot is None:
            raise NotFoundError("Material lot not found")
        return await reject_material_lot(session, cmd, actor.user_id, lot.site_id)


@v1_router.post("/lots/{lot_id}/retest", response_model=MutationReceipt)
async def post_retest_lot(
    lot_id: uuid.UUID,
    cmd: RetestMaterialLotCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.lot_id != lot_id:
        raise ValidationFailedError("lot_id in path and body must match")
    async with session.begin():
        lot = await session.get(MaterialLot, lot_id)
        if lot is None:
            raise NotFoundError("Material lot not found")
        return await retest_material_lot(session, cmd, actor.user_id, lot.site_id)


@v1_router.get("/lots/{lot_id}/quality-status")
async def get_lot_quality_status(lot_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        return await get_quality_status(session, lot_id)


@v1_router.get("/lots/{lot_id}/release-readiness")
async def get_lot_release_readiness(lot_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        return await get_release_readiness(session, lot_id)


# ---------------------------------------------------------------------------
# Document 20 (SPEC-MAT-002B) §7 declares 9 operations; `warehouse_location` itself has no CRUD entry
# among them (SG-081) -- seed-only data at this module's original build time, same treatment as
# iam.Site/iam.Organization.
#
# 2026-09-07: SG-081 PARTIALLY RESOLVED for the read side -- a read-only GET listing carries no contract
# risk (nothing to conflict with; a future Document 113 addendum's create/update contract can only ever
# add operations, never invalidate a plain listing), and the Inventory Transfer/Cycle-count/Adjustment
# forms otherwise cannot offer a real dropdown for From/To location -- see 18_SPEC_GAPS.md SG-081.
#
# 2026-09-07 (later same day), project-owner-directed: SG-081's *write* side resolved too --
# `POST .../warehouse-locations` below adds create capability, gated by its own new permission code
# (`warehouse_location.create`, Admin/Supervisor only -- scripts/seed.py) rather than left open. This
# still doesn't attempt update/delete/rename (no UI or command exists for those), and still doesn't
# guess at whatever a future formal Document 113 addendum's exact contract would be -- it's this
# project's own considered create contract, not an assumed one, applied because locations were
# genuinely uncreatable through the app otherwise.
# ---------------------------------------------------------------------------


def _warehouse_location_dict(loc: WarehouseLocation) -> dict:
    return {
        "id": str(loc.id),
        "warehouse_code": loc.warehouse_code,
        "location_code": loc.location_code,
        "zone_type": loc.zone_type,
        "status": loc.status,
    }


@inventory_v1_router.get("/warehouse-locations")
async def list_warehouse_locations(site_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    rows = (
        await session.execute(
            select(WarehouseLocation)
            .where(WarehouseLocation.site_id == site_id, WarehouseLocation.status == "active")
            .order_by(WarehouseLocation.warehouse_code, WarehouseLocation.location_code)
        )
    ).scalars().all()
    return {"items": [_warehouse_location_dict(loc) for loc in rows]}


@inventory_v1_router.post("/warehouse-locations", response_model=MutationReceipt)
async def post_create_warehouse_location(
    cmd: CreateWarehouseLocationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="warehouse_location.create", site_id=cmd.site_id)
        return await create_warehouse_location(session, cmd, actor.user_id)


@inventory_v1_router.get("/availability")
async def get_availability(
    material_id: uuid.UUID, site_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> dict:
    async with session.begin():
        return {"items": await get_inventory_availability(session, material_id=material_id, site_id=site_id)}


@inventory_v1_router.post("/reservations", response_model=MutationReceipt)
async def post_create_reservation(
    cmd: CreateInventoryReservationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="inventory_reservation.create", site_id=cmd.site_id)
        return await create_inventory_reservation(session, cmd, actor.user_id)


class ReservationSignatureChallengeRequest(BaseModel):
    action: str = "release"


@inventory_v1_router.post("/reservations/{reservation_id}/signature-challenges")
async def post_reservation_signature_challenge(
    reservation_id: uuid.UUID,
    body: ReservationSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        reservation = await session.get(InventoryReservation, reservation_id)
        if reservation is None:
            raise NotFoundError("Inventory reservation not found")
        if body.action != "release":
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session,
            user_id=actor.user_id,
            record_type="inventory_reservation",
            record_id=reservation.id,
            record_version=reservation.version,
            record_hash=reservation_record_hash(reservation),
            meaning="Released",
        )
        return {
            "challenge_id": str(challenge.id),
            "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


@inventory_v1_router.post("/reservations/{reservation_id}/release", response_model=MutationReceipt)
async def post_release_reservation(
    reservation_id: uuid.UUID,
    cmd: ReleaseInventoryReservationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.reservation_id != reservation_id:
        raise ValidationFailedError("reservation_id in path and body must match")
    async with session.begin():
        reservation = await session.get(InventoryReservation, reservation_id)
        if reservation is None:
            raise NotFoundError("Inventory reservation not found")
        return await release_inventory_reservation(session, cmd, actor.user_id, reservation.site_id)


@inventory_v1_router.post("/transfers", response_model=MutationReceipt)
async def post_create_transfer(
    cmd: CreateInventoryTransferCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        lot = await session.get(MaterialLot, cmd.material_lot_id)
        if lot is None:
            raise NotFoundError("Material lot not found")
        await evaluate_policy(session, actor.user_id, action="inventory_transaction.transfer", site_id=lot.site_id)
        return await create_inventory_transfer(session, cmd, actor.user_id, lot.site_id)


@inventory_v1_router.post("/containers/{container_id}/split", response_model=MutationReceipt)
async def post_split_container(
    container_id: uuid.UUID,
    cmd: SplitContainerCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.container_id != container_id:
        raise ValidationFailedError("container_id in path and body must match")
    async with session.begin():
        container = await session.get(MaterialContainer, container_id)
        if container is None:
            raise NotFoundError("Material container not found")
        lot = await session.get(MaterialLot, container.material_lot_id)
        await evaluate_policy(session, actor.user_id, action="material_container.split", site_id=lot.site_id)
        return await split_container(session, cmd, actor.user_id, lot.site_id)


@inventory_v1_router.post("/containers/merge", response_model=MutationReceipt)
async def post_merge_containers(
    cmd: MergeContainersCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        first = await session.get(MaterialContainer, cmd.source_container_ids[0]) if cmd.source_container_ids else None
        if first is None:
            raise NotFoundError("Source container not found")
        lot = await session.get(MaterialLot, first.material_lot_id)
        await evaluate_policy(session, actor.user_id, action="material_container.merge", site_id=lot.site_id)
        return await merge_containers(session, cmd, actor.user_id, lot.site_id)


@inventory_v1_router.post("/cycle-counts", response_model=MutationReceipt)
async def post_create_cycle_count(
    cmd: CreateCycleCountCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        lot = await session.get(MaterialLot, cmd.material_lot_id)
        if lot is None:
            raise NotFoundError("Material lot not found")
        await evaluate_policy(session, actor.user_id, action="inventory_cycle_count.execute", site_id=lot.site_id)
        return await create_cycle_count(session, cmd, actor.user_id, lot.site_id)


_LedgerFromLocation = aliased(WarehouseLocation)
_LedgerToLocation = aliased(WarehouseLocation)


@inventory_v1_router.get("/lots/{lot_id}/ledger")
async def get_lot_ledger(
    lot_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
) -> dict:
    async with session.begin():
        # container_id/from_location_id/to_location_id are all nullable (a RESERVE txn has no
        # from/to location; a lot-level cycle-count/adjustment can have no container -- §6.4.2) and
        # each references a different row than the transaction itself, so every join here is a LEFT
        # JOIN: showing the container's own code/the locations' own codes instead of raw UUIDs
        # (same class of fix as _receipt_select()'s Supplier/Manufacturer name resolution above),
        # without ever excluding a transaction that legitimately has no container or no from-location.
        stmt = (
            select(InventoryTransaction, MaterialContainer.container_code, _LedgerFromLocation.location_code, _LedgerToLocation.location_code)
            .where(InventoryTransaction.material_lot_id == lot_id)
            .outerjoin(MaterialContainer, MaterialContainer.id == InventoryTransaction.container_id)
            .outerjoin(_LedgerFromLocation, _LedgerFromLocation.id == InventoryTransaction.from_location_id)
            .outerjoin(_LedgerToLocation, _LedgerToLocation.id == InventoryTransaction.to_location_id)
        )
        rows, envelope = await paginate(
            session, stmt, params,
            sortable={"occurred_at": InventoryTransaction.occurred_at},
            default_sort=InventoryTransaction.occurred_at,
        )
        return {
            **envelope,
            "items": [
                {
                    "id": str(t.id),
                    "container_id": str(t.container_id) if t.container_id else None,
                    "container_code": container_code,
                    "transaction_type": t.transaction_type,
                    "quantity": str(t.quantity),
                    "uom": t.uom,
                    "from_location_id": str(t.from_location_id) if t.from_location_id else None,
                    "from_location_code": from_code,
                    "to_location_id": str(t.to_location_id) if t.to_location_id else None,
                    "to_location_code": to_code,
                    "occurred_at": t.occurred_at.isoformat(),
                }
                for t, container_code, from_code, to_code in rows
            ],
        }


@inventory_v1_router.get("/reconciliation/erp")
async def get_reconciliation(lot_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        return await get_erp_reconciliation(session, lot_id)


# ---------------------------------------------------------------------------
# Document 21 (SPEC-MAT-002C) §6 — exactly the 9 declared operations, no invented endpoint. Order
# creation is unsigned (SG-087 — signing a create operation has no established pattern in this codebase);
# the other 7 mutating operations all get a real Document 106 signature via `_dispensing_sign`.
# ---------------------------------------------------------------------------

_DISPENSING_CHALLENGE_MEANINGS = {
    "select_source": "Performed",
    "start": "Performed",
    "readings": "Performed",
    "manual_reading": "Performed",
    "verify": "Verified",
    "complete": "Performed",
    "cancel": "Approved",
}


@dispensing_v1_router.post("/orders", response_model=MutationReceipt)
async def post_create_order(
    cmd: CreateDispensingOrderCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="dispensing_order.create", site_id=cmd.site_id)
        return await create_dispensing_order(session, cmd, actor.user_id)


def _dispensing_dict(order: DispensingOrder) -> dict:
    return {
        "id": str(order.id),
        "site_id": str(order.site_id),
        "batch_id": str(order.batch_id),
        "batch_step_id": str(order.batch_step_id) if order.batch_step_id else None,
        "material_id": str(order.material_id),
        "material_spec_version_id": str(order.material_spec_version_id) if order.material_spec_version_id else None,
        "target_qty": str(order.target_qty),
        "target_uom": order.target_uom,
        "target_uom_id": str(order.target_uom_id) if order.target_uom_id else None,
        "tolerance_low": str(order.tolerance_low),
        "tolerance_high": str(order.tolerance_high),
        "state": order.state,
        "performed_by_user_id": str(order.performed_by_user_id) if order.performed_by_user_id else None,
        "requested_by_user_id": str(order.requested_by_user_id),
        "version": order.version,
    }


@dispensing_v1_router.get("/orders/{order_id}")
async def get_order(order_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    order = await session.get(DispensingOrder, order_id)
    if order is None:
        raise NotFoundError("Dispensing order not found")
    return _dispensing_dict(order)


class DispensingSignatureChallengeRequest(BaseModel):
    action: str  # select_source | start | readings | manual_reading | verify | complete | cancel


@dispensing_v1_router.post("/orders/{order_id}/signature-challenges")
async def post_dispensing_signature_challenge(
    order_id: uuid.UUID,
    body: DispensingSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        order = await session.get(DispensingOrder, order_id)
        if order is None:
            raise NotFoundError("Dispensing order not found")
        meaning = _DISPENSING_CHALLENGE_MEANINGS.get(body.action)
        if meaning is None:
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session,
            user_id=actor.user_id,
            record_type="dispensing_order",
            record_id=order.id,
            record_version=order.version,
            record_hash=dispensing_order_record_hash(order),
            meaning=meaning,
        )
        return {
            "challenge_id": str(challenge.id),
            "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


@dispensing_v1_router.post("/orders/{order_id}/select-source", response_model=MutationReceipt)
async def post_select_source(
    order_id: uuid.UUID,
    cmd: SelectDispensingSourceCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        order = await session.get(DispensingOrder, order_id)
        if order is None:
            raise NotFoundError("Dispensing order not found")
        return await select_dispensing_source(session, order_id, cmd, actor.user_id, order.site_id)


@dispensing_v1_router.post("/orders/{order_id}/start", response_model=MutationReceipt)
async def post_start(
    order_id: uuid.UUID,
    cmd: StartDispensingCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        order = await session.get(DispensingOrder, order_id)
        if order is None:
            raise NotFoundError("Dispensing order not found")
        return await start_dispensing(session, order_id, cmd, actor.user_id, order.site_id)


@dispensing_v1_router.post("/orders/{order_id}/readings", response_model=MutationReceipt)
async def post_readings(
    order_id: uuid.UUID,
    cmd: RecordReadingCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        order = await session.get(DispensingOrder, order_id)
        if order is None:
            raise NotFoundError("Dispensing order not found")
        return await record_reading(session, order_id, cmd, actor.user_id, order.site_id)


@dispensing_v1_router.post("/orders/{order_id}/manual-reading", response_model=MutationReceipt)
async def post_manual_reading(
    order_id: uuid.UUID,
    cmd: RecordManualReadingCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        order = await session.get(DispensingOrder, order_id)
        if order is None:
            raise NotFoundError("Dispensing order not found")
        return await record_manual_reading(session, order_id, cmd, actor.user_id, order.site_id)


@dispensing_v1_router.post("/orders/{order_id}/verify", response_model=MutationReceipt)
async def post_verify(
    order_id: uuid.UUID,
    cmd: VerifyDispensingCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        order = await session.get(DispensingOrder, order_id)
        if order is None:
            raise NotFoundError("Dispensing order not found")
        return await verify_dispensing(session, order_id, cmd, actor.user_id, order.site_id)


@dispensing_v1_router.post("/orders/{order_id}/complete", response_model=MutationReceipt)
async def post_complete(
    order_id: uuid.UUID,
    cmd: CompleteDispensingCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        order = await session.get(DispensingOrder, order_id)
        if order is None:
            raise NotFoundError("Dispensing order not found")
        return await complete_dispensing(session, order_id, cmd, actor.user_id, order.site_id)


@dispensing_v1_router.post("/orders/{order_id}/cancel", response_model=MutationReceipt)
async def post_cancel(
    order_id: uuid.UUID,
    cmd: CancelDispensingCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        order = await session.get(DispensingOrder, order_id)
        if order is None:
            raise NotFoundError("Dispensing order not found")
        return await cancel_dispensing(session, order_id, cmd, actor.user_id, order.site_id)


@dispensing_v1_router.get("/queue")
async def get_queue(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params)
) -> dict:
    stmt = select(DispensingOrder).where(DispensingOrder.state.notin_(("completed", "cancelled")))
    rows, envelope = await paginate(
        session, stmt, params, sortable={"created_at": DispensingOrder.created_at}, default_sort=DispensingOrder.created_at
    )
    return {**envelope, "items": [_dispensing_dict(o) for (o,) in rows]}


# ---------------------------------------------------------------------------
# Document 22 (SPEC-MAT-002D) — Material Consumption, Return, Adjustment, Destruction & Reconciliation.
# 8 endpoints declared in Document 22 §6: consumptions/returns reuse v1_router (/materials/v1);
# adjustments reuse inventory_v1_router (/inventory/v1); reconciliation uses a new
# reconciliation_v1_router (/reconciliation/v1). Losses (SAMPLE/REJECT/SPILL/APPROVED_LOSS) share the
# same "loss/spill/sample" UI concept from Document 22 §7 and are exposed as one endpoint, matching
# `record_material_loss` being one command for all four transaction types.
# ---------------------------------------------------------------------------


@v1_router.post("/consumptions", response_model=MutationReceipt)
async def post_record_consumption(
    cmd: RecordConsumptionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        batch = await session.get(Batch, cmd.batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        return await record_consumption(session, cmd, actor.user_id, batch.site_id)


@v1_router.post("/returns", response_model=MutationReceipt)
async def post_record_return(
    cmd: RecordReturnCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        batch = await session.get(Batch, cmd.batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        return await record_return(session, cmd, actor.user_id, batch.site_id)


@v1_router.post("/losses", response_model=MutationReceipt)
async def post_record_material_loss(
    cmd: RecordMaterialLossCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        batch = await session.get(Batch, cmd.batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        return await record_material_loss(session, cmd, actor.user_id, batch.site_id)


@inventory_v1_router.post("/adjustments", response_model=MutationReceipt)
async def post_create_adjustment_request(
    cmd: CreateInventoryAdjustmentRequestCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        lot = await session.get(MaterialLot, cmd.material_lot_id)
        if lot is None:
            raise NotFoundError("Material lot not found")
        return await create_inventory_adjustment_request(session, cmd, actor.user_id, lot.site_id)


class AdjustmentSignatureChallengeRequest(BaseModel):
    action: str = "approve"


# Was hardcoded to meaning="Approved" regardless of body.action -- harmless while only "approve" existed,
# but adding reject (Rejected meaning) would otherwise have signed a rejection decision with sign()'s own
# challenge.meaning carried onto the immutable Signature row reading "Approved" (SignatureChallenge/sign()
# in app/modules/signature/service.py -- meaning is set at challenge creation, not decision time). Same
# per-action permission/meaning dict shape release/router.py's own signature-challenges endpoint uses.
_ADJUSTMENT_CHALLENGE_PERMISSIONS = {"approve": "inventory_adjustment_request.approve", "reject": "inventory_adjustment_request.reject"}
_ADJUSTMENT_CHALLENGE_MEANINGS = {"approve": "Approved", "reject": "Rejected"}


@inventory_v1_router.post("/adjustments/{request_id}/signature-challenges")
async def post_adjustment_signature_challenge(
    request_id: uuid.UUID,
    body: AdjustmentSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    permission = _ADJUSTMENT_CHALLENGE_PERMISSIONS.get(body.action)
    meaning = _ADJUSTMENT_CHALLENGE_MEANINGS.get(body.action)
    if permission is None or meaning is None:
        raise ValidationFailedError("Unknown or unsigned action", action=body.action)
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action=permission, site_id=None)
        request = await session.get(InventoryAdjustmentRequest, request_id)
        if request is None:
            raise NotFoundError("Inventory adjustment request not found")
        challenge = await create_challenge(
            session,
            user_id=actor.user_id,
            record_type="inventory_adjustment_request",
            record_id=request.id,
            record_version=request.version,
            record_hash=inventory_adjustment_request_record_hash(request),
            meaning=meaning,
        )
        return {
            "challenge_id": str(challenge.id),
            "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


@inventory_v1_router.post("/adjustments/{request_id}/approve", response_model=MutationReceipt)
async def post_approve_adjustment_request(
    request_id: uuid.UUID,
    cmd: ApproveInventoryAdjustmentRequestCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        request = await session.get(InventoryAdjustmentRequest, request_id)
        if request is None:
            raise NotFoundError("Inventory adjustment request not found")
        return await approve_inventory_adjustment_request(session, request_id, cmd, actor.user_id, request.site_id)


@inventory_v1_router.post("/adjustments/{request_id}/reject", response_model=MutationReceipt)
async def post_reject_adjustment_request(
    request_id: uuid.UUID,
    cmd: RejectInventoryAdjustmentRequestCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        request = await session.get(InventoryAdjustmentRequest, request_id)
        if request is None:
            raise NotFoundError("Inventory adjustment request not found")
        return await reject_inventory_adjustment_request(session, request_id, cmd, actor.user_id, request.site_id)


ADJUSTMENT_SORTABLE = {"created_at": InventoryAdjustmentRequest.created_at, "status": InventoryAdjustmentRequest.status}


def _adjustment_dict(
    r: InventoryAdjustmentRequest, internal_lot: str, material_code: str, location_code: str, requested_by: str
) -> dict:
    return {
        "id": str(r.id),
        "material_lot_id": str(r.material_lot_id),
        "internal_lot": internal_lot,
        "material_code": material_code,
        "container_id": str(r.container_id) if r.container_id else None,
        "location_id": str(r.location_id),
        "location_code": location_code,
        "expected_quantity": str(r.expected_quantity),
        "observed_quantity": str(r.observed_quantity),
        "variance": str(r.variance),
        "reason": r.reason,
        "evidence": r.evidence,
        "status": r.status,
        "signature_id": str(r.signature_id) if r.signature_id else None,
        "resulting_transaction_id": str(r.resulting_transaction_id) if r.resulting_transaction_id else None,
        "requested_by": requested_by,
        "requested_by_user_id": str(r.requested_by_user_id),
        "approved_by_user_id": str(r.approved_by_user_id) if r.approved_by_user_id else None,
        "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "version": r.version,
    }


# A read the frontend needs (a browsable pending-adjustments queue for QA Releaser to approve from) --
# not one of Document 22 §6's declared *mutating* operations, so it carries no signature/authority
# implication; same GET-alongside-the-mutating-set precedent as list_material_receipts/list_material_lots
# above. Without this, the only way to discover a request_id to approve was the database.
@inventory_v1_router.get("/adjustments")
async def list_adjustment_requests(
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    status: str | None = None,
) -> dict:
    stmt = (
        select(
            InventoryAdjustmentRequest, MaterialLot.internal_lot, Material.code,
            WarehouseLocation.location_code, User.username,
        )
        .join(MaterialLot, MaterialLot.id == InventoryAdjustmentRequest.material_lot_id)
        .join(Material, Material.id == MaterialLot.material_id)
        .join(WarehouseLocation, WarehouseLocation.id == InventoryAdjustmentRequest.location_id)
        .join(User, User.id == InventoryAdjustmentRequest.requested_by_user_id)
    )
    if status:
        stmt = stmt.where(InventoryAdjustmentRequest.status == status)
    if params.q:
        needle = f"%{params.q}%"
        stmt = stmt.where(or_(MaterialLot.internal_lot.ilike(needle), Material.code.ilike(needle)))

    rows, envelope = await paginate(
        session, stmt, params, sortable=ADJUSTMENT_SORTABLE, default_sort=InventoryAdjustmentRequest.created_at
    )
    return {
        **envelope,
        "items": [_adjustment_dict(r, lot, code, loc, user) for r, lot, code, loc, user in rows],
    }


@v1_router.post("/destructions", response_model=MutationReceipt)
async def post_create_destruction_request(
    cmd: CreateDestructionRequestCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        site_id = await _resolve_destruction_scope_site_id(
            session,
            material_lot_id=cmd.material_lot_id,
            container_id=cmd.container_id,
            dispensed_container_id=cmd.dispensed_container_id,
        )
        return await create_destruction_request(session, cmd, actor.user_id, site_id)


class DestructionSignatureChallengeRequest(BaseModel):
    action: str = "execute"


@v1_router.post("/destructions/{destruction_id}/signature-challenges")
async def post_destruction_signature_challenge(
    destruction_id: uuid.UUID,
    body: DestructionSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        record = await session.get(DestructionRecord, destruction_id)
        if record is None:
            raise NotFoundError("Destruction record not found")
        challenge = await create_challenge(
            session,
            user_id=actor.user_id,
            record_type="destruction_record",
            record_id=record.id,
            record_version=record.version,
            record_hash=destruction_record_hash(record),
            meaning="Performed",
        )
        return {
            "challenge_id": str(challenge.id),
            "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


@v1_router.post("/destructions/{destruction_id}/execute", response_model=MutationReceipt)
async def post_execute_destruction(
    destruction_id: uuid.UUID,
    cmd: ExecuteDestructionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        record = await session.get(DestructionRecord, destruction_id)
        if record is None:
            raise NotFoundError("Destruction record not found")
        return await execute_destruction(session, destruction_id, cmd, actor.user_id, record.site_id)


@reconciliation_v1_router.post("/batches/{batch_id}/materials/evaluate", response_model=MutationReceipt)
async def post_evaluate_material_reconciliation(
    batch_id: uuid.UUID,
    cmd: EvaluateMaterialReconciliationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        batch = await session.get(Batch, batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        return await evaluate_material_reconciliation(session, batch_id, cmd, actor.user_id, batch.site_id)


@reconciliation_v1_router.get("/batches/{batch_id}/materials")
async def get_batch_material_reconciliation(
    batch_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> dict:
    async with session.begin():
        return await get_material_reconciliation(session, batch_id)
