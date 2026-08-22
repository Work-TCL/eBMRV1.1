from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.product.commands import CreateProductCommand, create_product
from app.modules.product.models import Product
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
