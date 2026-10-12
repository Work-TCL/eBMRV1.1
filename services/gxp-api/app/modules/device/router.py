import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.batch_execution.models import Batch
from app.modules.device import service as device_service
from app.modules.device.commands import (
    BulkCreateDeviceUnitsCommand,
    CreateDeviceLotCommand,
    DeviceUnitTransitionCommand,
    bulk_create_device_units,
    create_device_lot,
    hold_device_unit,
)
from app.modules.device.models import DeviceUnit
from app.modules.policy.service import evaluate_policy
from app.modules.product_master.models import ProductVersion
from app.mutation.errors import ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/devices/v1", tags=["device"])


def _unit_dict(unit, refs: dict | None = None) -> dict:
    refs = refs or {}
    return {
        "unit_id": str(unit.id),
        "site_id": str(unit.site_id),
        "product_version_id": str(unit.product_version_id),
        "product_code": refs.get("product_code"),
        "product_name": refs.get("product_name"),
        "batch_id": str(unit.batch_id) if unit.batch_id else None,
        "batch_number": refs.get("batch_number"),
        "device_lot_id": str(unit.device_lot_id) if unit.device_lot_id else None,
        "device_lot_label": refs.get("device_lot_label"),
        "serial_number": unit.serial_number,
        "udi_di": unit.udi_di,
        "udi_pi": unit.udi_pi,
        "state": unit.state,
        "version": unit.version,
        "release_status": unit.release_status,
    }


async def _resolve_unit_refs(session: AsyncSession, units: list[DeviceUnit]) -> dict[uuid.UUID, dict]:
    """Batch-resolves every foreign key `_unit_dict` needs a human-readable label for -- batch/product,
    plus the device_lot (itself a `DeviceUnit` row -- DHR-FR-001/002's own "lot-scope: serial_number is
    null" shape, so a lot has no separate human code beyond its own udi_di/batch/product). Same one-
    query-per-referenced-table shape as every other `_resolve_X_refs` this session."""
    if not units:
        return {}

    batch_ids = {u.batch_id for u in units if u.batch_id}
    product_ids = {u.product_version_id for u in units}
    lot_ids = {u.device_lot_id for u in units if u.device_lot_id}

    batch_by_id: dict[uuid.UUID, str] = {}
    if batch_ids:
        batch_by_id = dict((await session.execute(select(Batch.id, Batch.batch_number).where(Batch.id.in_(batch_ids)))).all())
    product_by_id: dict[uuid.UUID, tuple[str, str]] = {}
    if product_ids:
        product_by_id = {
            row.id: (row.product_code, row.name)
            for row in (
                await session.execute(select(ProductVersion.id, ProductVersion.product_code, ProductVersion.name).where(ProductVersion.id.in_(product_ids)))
            ).all()
        }
    lot_by_id: dict[uuid.UUID, DeviceUnit] = {}
    if lot_ids:
        lot_by_id = {
            row.id: row
            for row in (await session.execute(select(DeviceUnit).where(DeviceUnit.id.in_(lot_ids)))).scalars().all()
        }

    resolved: dict[uuid.UUID, dict] = {}
    for u in units:
        product_code, product_name = product_by_id.get(u.product_version_id, (None, None))
        lot = lot_by_id.get(u.device_lot_id) if u.device_lot_id else None
        lot_label = None
        if lot is not None:
            lot_product_code, _ = product_by_id.get(lot.product_version_id, (None, None))
            lot_label = lot.udi_di or lot_product_code or str(lot.id)[:8]
        resolved[u.id] = {
            "batch_number": batch_by_id.get(u.batch_id) if u.batch_id else None,
            "product_code": product_code,
            "product_name": product_name,
            "device_lot_label": lot_label,
        }
    return resolved


UNIT_SORTABLE = {
    "serial_number": DeviceUnit.serial_number,
    "state": DeviceUnit.state,
    "created_at": DeviceUnit.created_at,
}


@router.post("/lots", response_model=MutationReceipt)
async def post_create_lot(
    cmd: CreateDeviceLotCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="device.create", site_id=cmd.site_id)
        return await create_device_lot(session, cmd, actor.user_id)


@router.post("/units/bulk-create", response_model=list[MutationReceipt])
async def post_bulk_create_units(
    cmd: BulkCreateDeviceUnitsCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[MutationReceipt]:
    async with session.begin():
        lot = await device_service.get_unit(session, cmd.device_lot_id)
        await evaluate_policy(session, actor.user_id, action="device.create", site_id=lot.site_id)
        return await bulk_create_device_units(session, cmd, actor.user_id)


@router.post("/units/{unit_id}/hold", response_model=MutationReceipt)
async def post_hold_unit(
    unit_id: uuid.UUID,
    cmd: DeviceUnitTransitionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.unit_id != unit_id:
        raise ValidationFailedError("unit_id in path and body must match")
    async with session.begin():
        unit = await device_service.get_unit(session, unit_id)
        await evaluate_policy(session, actor.user_id, action="device.execute", site_id=unit.site_id)
        return await hold_device_unit(session, cmd, actor.user_id)


@router.get("/units")
async def list_units(
    site_id: uuid.UUID,
    device_lot_id: uuid.UUID | None = None,
    batch_id: uuid.UUID | None = None,
    lots_only: bool = False,
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """2026-10-09 (real user report): browsable list for `/devices`'s own page -- previously no way to
    see what device units/lots existed at all, only look one up by an already-known serial. Same
    SG-081 read-side precedent as every other list added this session (process_cycle/aseptic_operation/
    sterile_filter_use/...): a plain read-only GET listing doesn't conflict with any future write/CRUD
    contract, it only replaces a hand-typed id with something browsable.

    `lots_only` filters to the lot-header rows themselves (DHR-FR-001/002's own "lot-scope:
    serial_number is null" shape) -- the real data source for a "Device lot" picker, since a lot has no
    separate master table of its own (it's a `DeviceUnit` row like any serialized unit)."""
    await evaluate_policy(session, actor.user_id, action="device.view", site_id=site_id)
    stmt = select(DeviceUnit).where(DeviceUnit.site_id == site_id)
    if device_lot_id is not None:
        stmt = stmt.where(DeviceUnit.device_lot_id == device_lot_id)
    if batch_id is not None:
        stmt = stmt.where(DeviceUnit.batch_id == batch_id)
    if lots_only:
        stmt = stmt.where(DeviceUnit.serial_number.is_(None))
    if params.q:
        stmt = stmt.where(DeviceUnit.serial_number.ilike(f"%{params.q}%"))
    rows, envelope = await paginate(session, stmt, params, sortable=UNIT_SORTABLE, default_sort=DeviceUnit.created_at)
    units = [u for (u,) in rows]
    refs = await _resolve_unit_refs(session, units)
    return {**envelope, "items": [_unit_dict(u, refs.get(u.id)) for u in units]}


@router.get("/units/by-serial/{serial}")
async def get_unit_by_serial(
    serial: str,
    site_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="device.view", site_id=site_id)
    unit = await device_service.get_by_serial(session, site_id, serial)
    refs = await _resolve_unit_refs(session, [unit])
    return _unit_dict(unit, refs.get(unit.id))


@router.get("/units/{unit_id}/history")
async def get_unit_history(
    unit_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """DHR-FR-026 (partial): the current structured device_unit record only -- component/assembly/test/
    inspection/label/genealogy history is not built this pass (SG-049/SG-050)."""
    unit = await device_service.get_unit(session, unit_id)
    await evaluate_policy(session, actor.user_id, action="device.view", site_id=unit.site_id)
    refs = await _resolve_unit_refs(session, [unit])
    return _unit_dict(unit, refs.get(unit.id))


@router.get("/lots/{lot_id}/release-readiness")
async def get_release_readiness(
    lot_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    lot = await device_service.get_unit(session, lot_id)
    await evaluate_policy(session, actor.user_id, action="device.view", site_id=lot.site_id)
    return await device_service.release_readiness(session, lot_id)
