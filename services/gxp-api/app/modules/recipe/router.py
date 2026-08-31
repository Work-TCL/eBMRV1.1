import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.product.models import Product
from app.modules.recipe.commands import (
    CreateRecipeCommand,
    DeleteRecipeCommand,
    UpdateRecipeCommand,
    create_recipe,
    delete_recipe,
    update_recipe,
)
from app.modules.recipe.models import Recipe, RecipeStep
from app.mutation.errors import ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/recipes", tags=["recipe"])

SORTABLE = {
    "version": Recipe.version,
    "status": Recipe.status,
    "created_at": Recipe.created_at,
    "product_code": Product.code,
}


@router.post("", response_model=MutationReceipt)
async def post_create_recipe(
    cmd: CreateRecipeCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        receipt = await create_recipe(session, cmd, actor.user_id)
    return receipt


@router.get("")
async def list_recipes(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params)
) -> dict:
    stmt = select(Recipe, Product.code, Product.name).join(Product, Product.id == Recipe.product_id)
    if params.q:
        needle = f"%{params.q}%"
        stmt = stmt.where(or_(Product.code.ilike(needle), Product.name.ilike(needle)))

    rows, envelope = await paginate(
        session, stmt, params, sortable=SORTABLE, default_sort=Recipe.created_at
    )
    return {
        **envelope,
        "items": [
            {
                "id": str(r.id),
                "product_id": str(r.product_id),
                "product_code": product_code,
                "product_name": product_name,
                "version": r.version,
                "status": r.status,
            }
            for r, product_code, product_name in rows
        ],
    }


@router.get("/{recipe_id}")
async def get_recipe(recipe_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    recipe = await session.get(Recipe, recipe_id)
    steps_result = await session.execute(
        select(RecipeStep).where(RecipeStep.recipe_id == recipe_id).order_by(RecipeStep.step_number)
    )
    steps = steps_result.scalars().all()
    return {
        "id": str(recipe.id),
        "product_id": str(recipe.product_id),
        "version": recipe.version,
        "status": recipe.status,
        "steps": [
            {
                "id": str(s.id),
                "step_number": s.step_number,
                "name": s.name,
                "instructions": s.instructions,
                "requires_signature": s.requires_signature,
                "signature_meaning": s.signature_meaning,
            }
            for s in steps
        ],
    }


@router.patch("/{recipe_id}", response_model=MutationReceipt)
async def patch_recipe(
    recipe_id: uuid.UUID,
    cmd: UpdateRecipeCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.recipe_id != recipe_id:
        raise ValidationFailedError("recipe_id in path and body must match")
    async with session.begin():
        return await update_recipe(session, cmd, actor.user_id)


@router.delete("/{recipe_id}", response_model=MutationReceipt)
async def delete_recipe_endpoint(
    recipe_id: uuid.UUID,
    cmd: DeleteRecipeCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.recipe_id != recipe_id:
        raise ValidationFailedError("recipe_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await delete_recipe(session, cmd, actor.user_id)
