import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.referential import find_blocking_reference
from app.modules.recipe.models import Recipe, RecipeStep
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.gateway import (
    check_idempotency,
    record_command_receipt,
    write_audit_event,
    write_outbox_event,
)
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


class RecipeStepInput(BaseModel):
    step_number: int
    name: str
    instructions: str | None = None
    requires_signature: bool = False
    signature_meaning: str | None = None


def _validate_steps(steps: list[RecipeStepInput]) -> None:
    if not steps:
        raise ValidationFailedError("A recipe must declare at least one step")
    step_numbers = [s.step_number for s in steps]
    if sorted(step_numbers) != list(range(1, len(step_numbers) + 1)):
        raise ValidationFailedError("Step numbers must be a contiguous sequence starting at 1")
    for step in steps:
        if step.requires_signature and not step.signature_meaning:
            raise ValidationFailedError(
                "A step requiring a signature must declare its signature meaning",
                step_number=step.step_number,
            )


async def _assert_recipe_unused(session: AsyncSession, recipe_id: uuid.UUID) -> None:
    from app.modules.batch.models import Batch

    blocker = await find_blocking_reference(session, [(Batch, Batch.recipe_id, recipe_id, "batch")])
    if blocker is not None:
        raise ValidationFailedError(
            f"Cannot change this recipe: referenced by {blocker} — create a new version instead"
        )


class CreateRecipeCommand(CommandEnvelope):
    product_id: uuid.UUID
    version: int
    steps: list[RecipeStepInput]


async def create_recipe(
    session: AsyncSession, cmd: CreateRecipeCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    _validate_steps(cmd.steps)

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return MutationReceipt(
            command_id=existing_receipt.id,
            aggregate_id=existing_receipt.aggregate_id,
            resulting_version=existing_receipt.resulting_version,
            audit_event_id=existing_receipt.id,
            correlation_id=existing_receipt.id,
        )

    recipe = Recipe(product_id=cmd.product_id, version=cmd.version, status="active")
    session.add(recipe)
    await session.flush()

    for step in cmd.steps:
        session.add(
            RecipeStep(
                recipe_id=recipe.id,
                step_number=step.step_number,
                name=step.name,
                instructions=step.instructions,
                requires_signature=step.requires_signature,
                signature_meaning=step.signature_meaning,
            )
        )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="recipe",
        aggregate_id=recipe.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"product_id": str(cmd.product_id), "version": cmd.version, "step_count": len(cmd.steps)},
    )
    await write_outbox_event(
        session,
        event_type="RecipeCreated",
        aggregate_type="recipe",
        aggregate_id=recipe.id,
        aggregate_version=1,
        payload={"id": str(recipe.id), "product_id": str(cmd.product_id), "version": cmd.version},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="CreateRecipe",
        aggregate_type="recipe",
        aggregate_id=recipe.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )

    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=recipe.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


# ---------------------------------------------------------------------------
# UpdateRecipe / DeleteRecipe — allowed only while no batch has ever used this recipe version (BAT-FR-003:
# a batch freezes an execution snapshot from its recipe at issue time, so editing a recipe a batch already
# references would silently change what that historical batch appears to have run against). Once used,
# create a new version via CreateRecipe instead — the platform's existing supersession mechanism.
# ---------------------------------------------------------------------------


class UpdateRecipeCommand(CommandEnvelope):
    recipe_id: uuid.UUID
    steps: list[RecipeStepInput]


async def update_recipe(
    session: AsyncSession, cmd: UpdateRecipeCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    _validate_steps(cmd.steps)

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    recipe = await session.get(Recipe, cmd.recipe_id)
    if recipe is None:
        raise NotFoundError("Recipe not found")
    await _assert_recipe_unused(session, recipe.id)

    old_steps = (
        await session.execute(select(RecipeStep).where(RecipeStep.recipe_id == recipe.id))
    ).scalars().all()
    for step in old_steps:
        await session.delete(step)
    await session.flush()

    for step in cmd.steps:
        session.add(
            RecipeStep(
                recipe_id=recipe.id,
                step_number=step.step_number,
                name=step.name,
                instructions=step.instructions,
                requires_signature=step.requires_signature,
                signature_meaning=step.signature_meaning,
            )
        )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="recipe",
        aggregate_id=recipe.id,
        aggregate_version=1,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"step_count": len(cmd.steps)},
    )
    await write_outbox_event(
        session,
        event_type="RecipeChanged",
        aggregate_type="recipe",
        aggregate_id=recipe.id,
        aggregate_version=1,
        payload={"id": str(recipe.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="UpdateRecipe",
        aggregate_type="recipe",
        aggregate_id=recipe.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=recipe.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


class DeleteRecipeCommand(CommandEnvelope):
    recipe_id: uuid.UUID


async def delete_recipe(
    session: AsyncSession, cmd: DeleteRecipeCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    recipe = await session.get(Recipe, cmd.recipe_id)
    if recipe is None:
        raise NotFoundError("Recipe not found")
    await _assert_recipe_unused(session, recipe.id)

    step_rows = (
        await session.execute(select(RecipeStep).where(RecipeStep.recipe_id == recipe.id))
    ).scalars().all()
    for step in step_rows:
        await session.delete(step)
    await session.flush()  # steps must be gone before the recipe delete, no ORM relationship links them

    old_value = {"product_id": str(recipe.product_id), "version": recipe.version}
    recipe_id = recipe.id
    await session.delete(recipe)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="recipe",
        aggregate_id=recipe_id,
        aggregate_version=1,
        action="Deleted",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value=old_value,
    )
    await write_outbox_event(
        session,
        event_type="RecipeDeleted",
        aggregate_type="recipe",
        aggregate_id=recipe_id,
        aggregate_version=1,
        payload={"id": str(recipe_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="DeleteRecipe",
        aggregate_type="recipe",
        aggregate_id=recipe_id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=recipe_id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )
