import uuid

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.recipe.models import Recipe, RecipeStep
from app.mutation.errors import ValidationFailedError
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


class CreateRecipeCommand(CommandEnvelope):
    product_id: uuid.UUID
    version: int
    steps: list[RecipeStepInput]


async def create_recipe(
    session: AsyncSession, cmd: CreateRecipeCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    if not cmd.steps:
        raise ValidationFailedError("A recipe must declare at least one step")
    step_numbers = [s.step_number for s in cmd.steps]
    if sorted(step_numbers) != list(range(1, len(step_numbers) + 1)):
        raise ValidationFailedError("Step numbers must be a contiguous sequence starting at 1")
    for step in cmd.steps:
        if step.requires_signature and not step.signature_meaning:
            raise ValidationFailedError(
                "A step requiring a signature must declare its signature meaning",
                step_number=step.step_number,
            )

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
