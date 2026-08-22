import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.product.models import Product
from app.mutation.gateway import (
    check_idempotency,
    record_command_receipt,
    write_audit_event,
    write_outbox_event,
)
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


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
        return MutationReceipt(
            command_id=existing_receipt.id,
            aggregate_id=existing_receipt.aggregate_id,
            resulting_version=existing_receipt.resulting_version,
            audit_event_id=existing_receipt.id,
            correlation_id=existing_receipt.id,
        )

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
