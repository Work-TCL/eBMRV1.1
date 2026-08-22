import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.material.commands import (
    CreateMaterialCommand,
    DispositionMaterialLotCommand,
    ReceiveMaterialLotCommand,
    create_material,
    disposition_material_lot,
    lot_record_hash,
    receive_material_lot,
)
from app.modules.material.models import Material, MaterialLot
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/materials", tags=["material"])
lots_router = APIRouter(prefix="/material-lots", tags=["material"])

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
    "material_code": Material.code,
}


@router.post("", response_model=MutationReceipt)
async def post_create_material(
    cmd: CreateMaterialCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
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
        return await receive_material_lot(session, cmd, actor.user_id)


def _lot_dict(lot: MaterialLot, material_code: str, material_name: str) -> dict:
    return {
        "id": str(lot.id),
        "material_id": str(lot.material_id),
        "material_code": material_code,
        "material_name": material_name,
        "internal_lot": lot.internal_lot,
        "supplier_lot": lot.supplier_lot,
        "manufacturer_lot": lot.manufacturer_lot,
        "received_quantity": str(lot.received_quantity),
        "available_quantity": str(lot.available_quantity),
        "uom": lot.uom,
        "status": lot.status,
        "expiry_date": lot.expiry_date.isoformat() if lot.expiry_date else None,
        "retest_date": lot.retest_date.isoformat() if lot.retest_date else None,
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


class LotSignatureChallengeRequest(BaseModel):
    action: str  # "disposition"


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
        if body.action != "disposition":
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session,
            user_id=actor.user_id,
            record_type="material_lot",
            record_id=lot.id,
            record_version=lot.version,
            record_hash=lot_record_hash(lot),
            meaning="Disposition",
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
