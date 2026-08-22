import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.batch.models import Batch, BatchStep
from app.modules.iam.models import User
from app.modules.iam.service import require_role
from app.modules.material.models import MaterialLot, MaterialLotDisposition, MaterialIssue, Material
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import (
    check_idempotency,
    record_command_receipt,
    write_audit_event,
    write_outbox_event,
)
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def lot_record_hash(lot: MaterialLot) -> str:
    return sha256_hex({"id": str(lot.id), "version": lot.version, "status": lot.status})


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


# ---------------------------------------------------------------------------
# CreateMaterial
# ---------------------------------------------------------------------------


class CreateMaterialCommand(CommandEnvelope):
    site_id: uuid.UUID
    code: str
    name: str
    uom: str


async def create_material(
    session: AsyncSession, cmd: CreateMaterialCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    material = Material(site_id=cmd.site_id, code=cmd.code, name=cmd.name, uom=cmd.uom, status="active", version=1)
    session.add(material)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.site_id,
        aggregate_type="material",
        aggregate_id=material.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"code": material.code, "name": material.name, "uom": material.uom},
    )
    await write_outbox_event(
        session,
        event_type="MaterialCreated",
        aggregate_type="material",
        aggregate_id=material.id,
        aggregate_version=1,
        payload={"id": str(material.id), "code": material.code},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="CreateMaterial",
        aggregate_type="material",
        aggregate_id=material.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=material.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ReceiveMaterialLot — MAT-007/MAT-009: received lot enters quarantine automatically, no signature.
# ---------------------------------------------------------------------------


class ReceiveMaterialLotCommand(CommandEnvelope):
    material_id: uuid.UUID
    site_id: uuid.UUID
    internal_lot: str
    supplier_lot: str | None = None
    manufacturer_lot: str | None = None
    received_quantity: Decimal
    uom: str
    expiry_date: date | None = None
    retest_date: date | None = None


async def receive_material_lot(
    session: AsyncSession, cmd: ReceiveMaterialLotCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.received_quantity <= 0:
        raise ValidationFailedError("received_quantity must be positive")

    lot = MaterialLot(
        material_id=cmd.material_id,
        site_id=cmd.site_id,
        supplier_lot=cmd.supplier_lot,
        manufacturer_lot=cmd.manufacturer_lot,
        internal_lot=cmd.internal_lot,
        received_quantity=cmd.received_quantity,
        available_quantity=cmd.received_quantity,
        uom=cmd.uom,
        status="quarantine",
        expiry_date=cmd.expiry_date,
        retest_date=cmd.retest_date,
        received_by_user_id=actor_user_id,
        version=1,
    )
    session.add(lot)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.site_id,
        aggregate_type="material_lot",
        aggregate_id=lot.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"internal_lot": lot.internal_lot, "status": lot.status, "quantity": str(lot.received_quantity)},
    )
    await write_outbox_event(
        session,
        event_type="MaterialLotReceived",
        aggregate_type="material_lot",
        aggregate_id=lot.id,
        aggregate_version=1,
        payload={"id": str(lot.id), "material_id": str(cmd.material_id), "internal_lot": lot.internal_lot},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="ReceiveMaterialLot",
        aggregate_type="material_lot",
        aggregate_id=lot.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=lot.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# DispositionMaterialLot — MAT-011: QC release/reject, signed, requires QC Reviewer role.
# ---------------------------------------------------------------------------


class DispositionMaterialLotCommand(CommandEnvelope):
    lot_id: uuid.UUID
    expected_version: int
    decision: str  # "released" | "rejected"
    reason: str | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def disposition_material_lot(
    session: AsyncSession, cmd: DispositionMaterialLotCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.decision not in ("released", "rejected"):
        raise ValidationFailedError("decision must be 'released' or 'rejected'")

    result = await session.execute(select(MaterialLot).where(MaterialLot.id == cmd.lot_id).with_for_update())
    lot = result.scalar_one_or_none()
    if lot is None:
        raise NotFoundError("Material lot not found")
    if lot.version != cmd.expected_version:
        raise StaleVersionError(
            "Material lot was modified by another actor since it was read",
            expected_version=cmd.expected_version,
            current_version=lot.version,
        )
    if lot.status != "quarantine":
        raise InvalidTransitionError("Only a lot in quarantine can be dispositioned", current_status=lot.status)

    await require_role(session, actor_user_id, site_id, "QC Reviewer")

    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session,
        challenge_id=cmd.challenge_id,
        user_id=actor_user_id,
        record_version=lot.version,
        record_hash=lot_record_hash(lot),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})

    session.add(
        MaterialLotDisposition(
            material_lot_id=lot.id,
            decision=cmd.decision,
            reason=cmd.reason,
            signature_id=signature.id,
            disposed_by_user_id=actor_user_id,
        )
    )
    old_status = lot.status
    lot.status = cmd.decision
    lot.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="material_lot",
        aggregate_id=lot.id,
        aggregate_version=lot.version,
        action="StatusChanged",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"status": old_status},
        new_value={"status": lot.status},
        signature_id=signature.id,
        reason=cmd.reason,
    )
    await write_outbox_event(
        session,
        event_type="MaterialLotDispositioned",
        aggregate_type="material_lot",
        aggregate_id=lot.id,
        aggregate_version=lot.version,
        payload={"id": str(lot.id), "status": lot.status},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="DispositionMaterialLot",
        aggregate_type="material_lot",
        aggregate_id=lot.id,
        expected_version=cmd.expected_version,
        resulting_version=lot.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=lot.id,
        resulting_version=lot.version,
        audit_event_id=audit_event.id,
        signature_id=signature.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# IssueMaterialToBatch — MAT-013/MAT-015: only released, unexpired lots are eligible.
# ---------------------------------------------------------------------------


class IssueMaterialToBatchCommand(CommandEnvelope):
    lot_id: uuid.UUID
    expected_version: int
    batch_id: uuid.UUID
    batch_step_id: uuid.UUID | None = None
    quantity: Decimal


async def issue_material_to_batch(
    session: AsyncSession, cmd: IssueMaterialToBatchCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.quantity <= 0:
        raise ValidationFailedError("quantity must be positive")

    result = await session.execute(select(MaterialLot).where(MaterialLot.id == cmd.lot_id).with_for_update())
    lot = result.scalar_one_or_none()
    if lot is None:
        raise NotFoundError("Material lot not found")
    if lot.version != cmd.expected_version:
        raise StaleVersionError(
            "Material lot was modified by another actor since it was read",
            expected_version=cmd.expected_version,
            current_version=lot.version,
        )

    # MAT-013 eligibility: released, not expired, sufficient available quantity.
    if lot.status != "released":
        raise InvalidTransitionError(
            "Only a released lot is eligible for issue", current_status=lot.status
        )
    if lot.expiry_date is not None and lot.expiry_date < datetime.now(timezone.utc).date():
        raise InvalidTransitionError("Lot has passed its expiry date and is not eligible for issue")
    if cmd.quantity > lot.available_quantity:
        raise ValidationFailedError(
            "Requested quantity exceeds available lot quantity",
            available=str(lot.available_quantity),
            requested=str(cmd.quantity),
        )

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")
    if cmd.batch_step_id is not None:
        step = await session.get(BatchStep, cmd.batch_step_id)
        if step is None or step.batch_id != batch.id:
            raise NotFoundError("Batch step not found")

    old_available = lot.available_quantity
    lot.available_quantity -= cmd.quantity
    if lot.available_quantity == 0:
        lot.status = "consumed"
    lot.version += 1

    session.add(
        MaterialIssue(
            material_lot_id=lot.id,
            batch_id=cmd.batch_id,
            batch_step_id=cmd.batch_step_id,
            quantity=cmd.quantity,
            uom=lot.uom,
            issued_by_user_id=actor_user_id,
        )
    )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="material_lot",
        aggregate_id=lot.id,
        aggregate_version=lot.version,
        action="Consumed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"available_quantity": str(old_available)},
        new_value={"available_quantity": str(lot.available_quantity), "issued_to_batch_id": str(cmd.batch_id)},
    )
    await write_outbox_event(
        session,
        event_type="MaterialIssued",
        aggregate_type="material_lot",
        aggregate_id=lot.id,
        aggregate_version=lot.version,
        payload={
            "lot_id": str(lot.id),
            "batch_id": str(cmd.batch_id),
            "quantity": str(cmd.quantity),
        },
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="IssueMaterialToBatch",
        aggregate_type="material_lot",
        aggregate_id=lot.id,
        expected_version=cmd.expected_version,
        resulting_version=lot.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=lot.id,
        resulting_version=lot.version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )
