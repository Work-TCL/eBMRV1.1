"""Document 12 — read-side lookups and the minimal release-readiness slice (DHR-FR-021, partial) shared
by commands.py and the router.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.device.models import DeviceUnit
from app.mutation.errors import NotFoundError


async def get_unit(session: AsyncSession, unit_id: uuid.UUID) -> DeviceUnit:
    unit = await session.get(DeviceUnit, unit_id)
    if unit is None:
        raise NotFoundError("Device unit not found")
    return unit


async def get_by_serial(session: AsyncSession, site_id: uuid.UUID, serial_number: str) -> DeviceUnit:
    unit = (
        await session.execute(
            select(DeviceUnit).where(DeviceUnit.site_id == site_id, DeviceUnit.serial_number == serial_number)
        )
    ).scalar_one_or_none()
    if unit is None:
        raise NotFoundError("Device unit not found for that serial_number")
    return unit


async def get_units_for_lot(session: AsyncSession, lot_id: uuid.UUID) -> list[DeviceUnit]:
    return (
        (await session.execute(select(DeviceUnit).where(DeviceUnit.device_lot_id == lot_id)))
        .scalars()
        .all()
    )


async def release_readiness(session: AsyncSession, lot_id: uuid.UUID) -> dict:
    """DHR-FR-021 (partial): only checks what this pass actually tracks -- lot/unit state. The real
    requirement's component/test/label/signature/NCR completeness checks are not evaluated here -- those
    entities don't exist yet (SG-049/SG-050), so this can never be a genuine release decision; it is
    explicitly marked non-authoritative for that purpose.
    """
    lot = await get_unit(session, lot_id)
    units = await get_units_for_lot(session, lot_id)
    blocked = [u for u in ([lot] + units) if u.state == "hold"]
    return {
        "lot_id": str(lot_id),
        "unit_count": len(units),
        "blocked_unit_ids": [str(u.id) for u in blocked],
        "eligible": len(blocked) == 0,
        "note": "Partial check (state only) -- component/test/label/signature/NCR completeness not evaluated (SG-049/SG-050). Not a regulated release decision.",
    }
