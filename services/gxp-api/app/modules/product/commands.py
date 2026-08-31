import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.referential import find_blocking_reference
from app.modules.product.models import Product
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.gateway import (
    check_idempotency,
    record_command_receipt,
    write_audit_event,
    write_outbox_event,
)
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


class CreateProductCommand(CommandEnvelope):
    site_id: uuid.UUID
    code: str
    name: str


async def create_product(
    session: AsyncSession, cmd: CreateProductCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    product = Product(site_id=cmd.site_id, code=cmd.code, name=cmd.name, status="active", version=1)
    session.add(product)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.site_id,
        aggregate_type="product",
        aggregate_id=product.id,
        aggregate_version=product.version,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"code": product.code, "name": product.name, "status": product.status},
    )
    await write_outbox_event(
        session,
        event_type="ProductCreated",
        aggregate_type="product",
        aggregate_id=product.id,
        aggregate_version=product.version,
        payload={"id": str(product.id), "code": product.code, "name": product.name},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="CreateProduct",
        aggregate_type="product",
        aggregate_id=product.id,
        expected_version=None,
        resulting_version=product.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )

    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=product.id,
        resulting_version=product.version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# UpdateProduct / DeleteProduct — code and site_id are immutable once created (site-scoped uniqueness
# and downstream references assume they never move); name and status may change.
# ---------------------------------------------------------------------------


class UpdateProductCommand(CommandEnvelope):
    product_id: uuid.UUID
    name: str
    status: str


async def update_product(
    session: AsyncSession, cmd: UpdateProductCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    product = await session.get(Product, cmd.product_id)
    if product is None:
        raise NotFoundError("Product not found")

    old_value = {"name": product.name, "status": product.status}
    product.name = cmd.name
    product.status = cmd.status

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=product.site_id,
        aggregate_type="product",
        aggregate_id=product.id,
        aggregate_version=product.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value=old_value,
        new_value={"name": product.name, "status": product.status},
    )
    await write_outbox_event(
        session,
        event_type="ProductChanged",
        aggregate_type="product",
        aggregate_id=product.id,
        aggregate_version=product.version,
        payload={"id": str(product.id), "name": product.name, "status": product.status},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=product.site_id,
        command_type="UpdateProduct",
        aggregate_type="product",
        aggregate_id=product.id,
        expected_version=None,
        resulting_version=product.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=product.id,
        resulting_version=product.version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


class DeleteProductCommand(CommandEnvelope):
    product_id: uuid.UUID


async def delete_product(
    session: AsyncSession, cmd: DeleteProductCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    from app.modules.batch.models import Batch
    from app.modules.recipe.models import Recipe

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    product = await session.get(Product, cmd.product_id)
    if product is None:
        raise NotFoundError("Product not found")

    blocker = await find_blocking_reference(
        session,
        [
            (Recipe, Recipe.product_id, product.id, "recipe"),
            (Batch, Batch.product_id, product.id, "batch"),
        ],
    )
    if blocker is not None:
        raise ValidationFailedError(f"Cannot delete product: referenced by {blocker}")

    old_value = {"code": product.code, "name": product.name, "status": product.status}
    product_id = product.id
    site_id = product.site_id
    await session.delete(product)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="product",
        aggregate_id=product_id,
        aggregate_version=1,
        action="Deleted",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value=old_value,
    )
    await write_outbox_event(
        session,
        event_type="ProductDeleted",
        aggregate_type="product",
        aggregate_id=product_id,
        aggregate_version=1,
        payload={"id": str(product_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="DeleteProduct",
        aggregate_type="product",
        aggregate_id=product_id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=product_id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )
