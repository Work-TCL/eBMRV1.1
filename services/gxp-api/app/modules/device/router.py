import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.device import service as device_service
from app.modules.device.commands import (
    BulkCreateDeviceUnitsCommand,
    CreateDeviceLotCommand,
    DeviceUnitTransitionCommand,
    bulk_create_device_units,
    create_device_lot,
    hold_device_unit,
)
from app.modules.policy.service import evaluate_policy
from app.mutation.errors import ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/devices/v1", tags=["device"])


def _unit_dict(unit) -> dict:
    return {
        "unit_id": str(unit.id),
        "site_id": str(unit.site_id),
        "product_version_id": str(unit.product_version_id),
        "batch_id": str(unit.batch_id) if unit.batch_id else None,
        "device_lot_id": str(unit.device_lot_id) if unit.device_lot_id else None,
        "serial_number": unit.serial_number,
        "udi_di": unit.udi_di,
        "udi_pi": unit.udi_pi,
        "state": unit.state,
        "version": unit.version,
        "release_status": unit.release_status,
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
        await evaluate_policy(session, actor.user_id, action="device.execute", site_id=None)
        return await hold_device_unit(session, cmd, actor.user_id)


@router.get("/units/by-serial/{serial}")
async def get_unit_by_serial(
    serial: str,
    site_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="device.view", site_id=None)
    unit = await device_service.get_by_serial(session, site_id, serial)
    return _unit_dict(unit)


@router.get("/units/{unit_id}/history")
async def get_unit_history(
    unit_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """DHR-FR-026 (partial): the current structured device_unit record only -- component/assembly/test/
    inspection/label/genealogy history is not built this pass (SG-049/SG-050)."""
    await evaluate_policy(session, actor.user_id, action="device.view", site_id=None)
    unit = await device_service.get_unit(session, unit_id)
    return _unit_dict(unit)


@router.get("/lots/{lot_id}/release-readiness")
async def get_release_readiness(
    lot_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="device.view", site_id=None)
    return await device_service.release_readiness(session, lot_id)
