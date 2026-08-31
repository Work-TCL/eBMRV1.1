import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.product.commands import (
    CreateProductCommand,
    DeleteProductCommand,
    UpdateProductCommand,
    create_product,
    delete_product,
    update_product,
)
from app.modules.product.models import Product
from app.mutation.errors import ValidationFailedError
from app.mutation.schemas import MutationReceipt

SORTABLE = {
    "code": Product.code,
    "name": Product.name,
    "status": Product.status,
    "created_at": Product.created_at,
}

router = APIRouter(prefix="/products", tags=["product"])


@router.post("", response_model=MutationReceipt)
async def post_create_product(
    cmd: CreateProductCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        receipt = await create_product(session, cmd, actor.user_id)
    return receipt


@router.get("")
async def list_products(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params)
) -> dict:
    stmt = select(Product)
    if params.q:
        needle = f"%{params.q}%"
        stmt = stmt.where(or_(Product.code.ilike(needle), Product.name.ilike(needle)))

    rows, envelope = await paginate(
        session, stmt, params, sortable=SORTABLE, default_sort=Product.created_at
    )
    return {
        **envelope,
        "items": [
            {
                "id": str(p.id),
                "site_id": str(p.site_id),
                "code": p.code,
                "name": p.name,
                "status": p.status,
                "version": p.version,
            }
            for (p,) in rows
        ],
    }


@router.patch("/{product_id}", response_model=MutationReceipt)
async def patch_product(
    product_id: uuid.UUID,
    cmd: UpdateProductCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.product_id != product_id:
        raise ValidationFailedError("product_id in path and body must match")
    async with session.begin():
        return await update_product(session, cmd, actor.user_id)


@router.delete("/{product_id}", response_model=MutationReceipt)
async def delete_product_endpoint(
    product_id: uuid.UUID,
    cmd: DeleteProductCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.product_id != product_id:
        raise ValidationFailedError("product_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await delete_product(session, cmd, actor.user_id)
