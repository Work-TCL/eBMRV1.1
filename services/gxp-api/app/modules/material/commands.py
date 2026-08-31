import uuid
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.referential import find_blocking_reference
from app.core.security import verify_password
from app.modules.batch.models import Batch, BatchStep
from app.modules.iam.models import Qualification, User
from app.modules.policy.service import evaluate_policy
from app.modules.material.models import (
    PRE_DISPOSITION_LOT_STATES,
    DestructionRecord,
    DispensedContainer,
    DispensingOrder,
    DispensingSource,
    InventoryAdjustmentRequest,
    InventoryBalanceProjection,
    InventoryReservation,
    InventoryTransaction,
    Material,
    MaterialConsumption,
    MaterialContainer,
    MaterialIssue,
    MaterialLot,
    MaterialLotDisposition,
    MaterialQualityDisposition,
    MaterialReceipt,
    MaterialReconciliation,
    MaterialReturn,
    SamplingOrder,
    WarehouseLocation,
    WeighingReading,
    WeighingSession,
)
from app.modules.qc import commands as qc_commands
from app.modules.qms import commands as qms_commands
from app.modules.rules import commands as rules_commands
from app.modules.rules import service as rules_service
from app.modules.signature import service as signature_service
from app.modules.supplier_quality.models import Supplier
from app.modules.vault import service as vault_service
from app.mutation.errors import (
    AdjustmentApprovalRequiredError,
    BalanceIneligibleError,
    BatchMismatchError,
    ContainerIneligibleError,
    DestructionNotAuthorizedError,
    InvalidTransitionError,
    LotIneligibleError,
    ManualFallbackNotAllowedError,
    MissingSignatureError,
    NotFoundError,
    QualificationExpiredError,
    QualificationMissingError,
    QuantityExceedsAvailableError,
    ReadingUnstableError,
    ReconciliationFailedError,
    RoleMissingError,
    SourceQuantityInsufficientError,
    StaleVersionError,
    UomUnknownError,
    ValidationFailedError,
    VerifierRequiredError,
    WeightOutOfToleranceError,
    WrongMaterialError,
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


def reservation_record_hash(reservation: InventoryReservation) -> str:
    return sha256_hex(
        {"id": str(reservation.id), "version": reservation.version, "status": reservation.status}
    )


async def _resolve_uom_id(session: AsyncSession, uom: str | None) -> uuid.UUID | None:
    """SG-146 (remainder), MIG-FR-004 expand step: best-effort dual-write onto the Document 110 §3
    controlled UOM master, same discipline as `app.modules.yield_reconciliation.commands._resolve_uom_id`
    / `app.modules.qc.commands._resolve_uom_id`. The free-text `uom`/`target_uom` column stays
    authoritative; an unresolved code leaves the new `*_id` column NULL rather than rejecting the write."""
    if not uom:
        return None
    try:
        row = await rules_service.resolve_uom(session, uom)
    except UomUnknownError:
        return None
    return row.uom_id


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

    material = Material(
        site_id=cmd.site_id, code=cmd.code, name=cmd.name, uom=cmd.uom, uom_id=await _resolve_uom_id(session, cmd.uom),
        status="active", version=1,
    )
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
        uom_id=await _resolve_uom_id(session, cmd.uom),
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

    await evaluate_policy(session, actor_user_id, action="material_lot.disposition", site_id=site_id)

    # MUT-FR-014/RUL-FR-016: optional release-gating rule. A no-op until a deployment authors and
    # releases a rule at this rule_id -- see app/modules/rules/commands.py::evaluate_release_gate.
    if cmd.decision == "released":
        await rules_commands.evaluate_release_gate(
            session,
            rule_id=f"material-lot-release-eligibility:{lot.material_id}",
            inputs={
                "available_quantity": str(lot.available_quantity),
                "received_quantity": str(lot.received_quantity),
            },
            aggregate_type="material_lot",
            aggregate_id=lot.id,
            aggregate_version=lot.version,
            actor_user_id=actor_user_id,
        )

    policy = await signature_service.resolve_signature_requirement(
        session, record_type="material_lot", action="disposition"
    )
    signature_id = None
    if policy.signature_required:
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
        signature = await signature_service.sign(
            session, challenge=challenge, auth_context={"method": "password_reauth"}
        )
        signature_id = signature.id

    session.add(
        MaterialLotDisposition(
            material_lot_id=lot.id,
            decision=cmd.decision,
            reason=cmd.reason,
            signature_id=signature_id,
            disposed_by_user_id=actor_user_id,
        )
    )
    old_status = lot.status
    lot.status = cmd.decision
    lot.version += 1

    # Document 06 (VLT-FR-001/006): a QC disposition is a "regulated final record" too — same immutable
    # vault snapshot pattern as release_batch, in the same transaction, not itself signature-gated (the
    # disposition's own authorization/signature already happened above).
    await vault_service.release_master(
        session,
        object_type="material_lot",
        business_id=lot.internal_lot,
        site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "lot_id": str(lot.id),
            "internal_lot": lot.internal_lot,
            "material_id": str(lot.material_id),
            "supplier_lot": lot.supplier_lot,
            "manufacturer_lot": lot.manufacturer_lot,
            "received_quantity": str(lot.received_quantity),
            "uom": lot.uom,
            "decision": cmd.decision,
            "reason": cmd.reason,
            "signature_id": str(signature_id) if signature_id else None,
        },
    )

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
        signature_id=signature_id,
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
        signature_id=signature_id,
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
            uom_id=lot.uom_id,  # copied from the lot's own already-resolved value, not re-queried
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


# ---------------------------------------------------------------------------
# UpdateMaterial / DeleteMaterial — code, site_id and uom are immutable once created (uom changes would
# corrupt existing lot quantity semantics); name and status may change.
# ---------------------------------------------------------------------------


class UpdateMaterialCommand(CommandEnvelope):
    material_id: uuid.UUID
    name: str
    status: str


async def update_material(
    session: AsyncSession, cmd: UpdateMaterialCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    material = await session.get(Material, cmd.material_id)
    if material is None:
        raise NotFoundError("Material not found")

    old_value = {"name": material.name, "status": material.status}
    material.name = cmd.name
    material.status = cmd.status

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=material.site_id,
        aggregate_type="material",
        aggregate_id=material.id,
        aggregate_version=material.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value=old_value,
        new_value={"name": material.name, "status": material.status},
    )
    await write_outbox_event(
        session,
        event_type="MaterialChanged",
        aggregate_type="material",
        aggregate_id=material.id,
        aggregate_version=material.version,
        payload={"id": str(material.id), "name": material.name, "status": material.status},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=material.site_id,
        command_type="UpdateMaterial",
        aggregate_type="material",
        aggregate_id=material.id,
        expected_version=None,
        resulting_version=material.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=material.id,
        resulting_version=material.version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


class DeleteMaterialCommand(CommandEnvelope):
    material_id: uuid.UUID


async def delete_material(
    session: AsyncSession, cmd: DeleteMaterialCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    material = await session.get(Material, cmd.material_id)
    if material is None:
        raise NotFoundError("Material not found")

    blocker = await find_blocking_reference(
        session, [(MaterialLot, MaterialLot.material_id, material.id, "material lot")]
    )
    if blocker is not None:
        raise ValidationFailedError(f"Cannot delete material: referenced by {blocker}")

    old_value = {"code": material.code, "name": material.name, "status": material.status}
    material_id = material.id
    site_id = material.site_id
    await session.delete(material)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="material",
        aggregate_id=material_id,
        aggregate_version=1,
        action="Deleted",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value=old_value,
    )
    await write_outbox_event(
        session,
        event_type="MaterialDeleted",
        aggregate_type="material",
        aggregate_id=material_id,
        aggregate_version=1,
        payload={"id": str(material_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="DeleteMaterial",
        aggregate_type="material",
        aggregate_id=material_id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=material_id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Document 19 (SPEC-MAT-002A) — CreateMaterialReceipt
# RCV-FR-001 (partial — no PO/transfer-expectation entity exists yet, SG-057/058)/002/006/007/010/011/
# 012/013 (no autonomous AI extraction — COA stays manual/authoritative evidence, no-op is compliant).
# ---------------------------------------------------------------------------


class CreateMaterialReceiptCommand(CommandEnvelope):
    site_id: uuid.UUID
    receipt_number: str
    material_id: uuid.UUID
    po_reference: str | None = None
    supplier_id: uuid.UUID | None = None
    manufacturer_id: uuid.UUID | None = None
    supplier_lot: str | None = None
    manufacturer_lot: str | None = None
    carrier_reference: str | None = None
    received_gross_quantity: Decimal
    received_net_quantity: Decimal | None = None
    accepted_quantity: Decimal | None = None
    uom: str
    manufacture_date: date | None = None
    expiry_date: date | None = None
    retest_date: date | None = None
    shipment_condition_status: str | None = None
    coa_document_hash: str | None = None


async def create_material_receipt(
    session: AsyncSession, cmd: CreateMaterialReceiptCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.received_gross_quantity <= 0:
        raise ValidationFailedError("received_gross_quantity must be positive")

    material = await session.get(Material, cmd.material_id)
    if material is None:
        raise NotFoundError("Material not found")

    coa_vault_object_id = None
    if cmd.coa_document_hash:
        vault_obj = await vault_service.release_master(
            session,
            object_type="material_coa",
            business_id=f"{cmd.receipt_number}:{cmd.material_id}",
            site_id=cmd.site_id,
            actor_user_id=actor_user_id,
            canonical_payload={"receipt_number": cmd.receipt_number, "document_hash": cmd.coa_document_hash},
            evidence=[
                {
                    "evidence_id": uuid.uuid4(),
                    "evidence_sha256": cmd.coa_document_hash,
                    "media_type": None,
                    "sequence": 1,
                }
            ],
        )
        coa_vault_object_id = vault_obj.object_id

    receipt_row = MaterialReceipt(
        site_id=cmd.site_id,
        receipt_number=cmd.receipt_number,
        po_reference=cmd.po_reference,
        material_id=cmd.material_id,
        supplier_id=cmd.supplier_id,
        manufacturer_id=cmd.manufacturer_id,
        supplier_lot=cmd.supplier_lot,
        manufacturer_lot=cmd.manufacturer_lot,
        carrier_reference=cmd.carrier_reference,
        received_gross_quantity=cmd.received_gross_quantity,
        received_net_quantity=cmd.received_net_quantity,
        accepted_quantity=cmd.accepted_quantity,
        uom=cmd.uom,
        uom_id=await _resolve_uom_id(session, cmd.uom),
        manufacture_date=cmd.manufacture_date,
        expiry_date=cmd.expiry_date,
        retest_date=cmd.retest_date,
        shipment_condition_status=cmd.shipment_condition_status,
        coa_vault_object_id=coa_vault_object_id,
        coa_document_hash=cmd.coa_document_hash,
        receiver_subject_id=actor_user_id,
        state="received",
        version=1,
    )
    session.add(receipt_row)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.site_id,
        aggregate_type="material_receipt",
        aggregate_id=receipt_row.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"receipt_number": receipt_row.receipt_number, "state": receipt_row.state},
    )
    await write_outbox_event(
        session,
        event_type="MaterialReceived",
        aggregate_type="material_receipt",
        aggregate_id=receipt_row.id,
        aggregate_version=1,
        payload={"id": str(receipt_row.id), "receipt_number": receipt_row.receipt_number},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="CreateMaterialReceipt",
        aggregate_type="material_receipt",
        aggregate_id=receipt_row.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=receipt_row.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ExamineReceipt — RCV-FR-003/004/005/014/031: visual examination, identity/supplier check, discrepancy
# hold. A clean examination creates the MaterialLot + MaterialContainer rows (RCV-FR-008/009/015/016/017)
# in automatic quarantine; a mismatch/discrepancy holds the receipt instead of silently remapping it.
# ---------------------------------------------------------------------------


class ExamineReceiptCommand(CommandEnvelope):
    receipt_id: uuid.UUID
    expected_version: int
    labeling_ok: bool
    damage_observed: bool
    seal_broken: bool
    contamination_observed: bool
    examination_notes: str | None = None
    identity_confirmed: bool
    internal_lot: str
    container_count: int = 1
    discrepancy_reason: str | None = None


async def examine_receipt(
    session: AsyncSession, cmd: ExamineReceiptCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(
        select(MaterialReceipt).where(MaterialReceipt.id == cmd.receipt_id).with_for_update()
    )
    receipt_row = result.scalar_one_or_none()
    if receipt_row is None:
        raise NotFoundError("Material receipt not found")
    if receipt_row.version != cmd.expected_version:
        raise StaleVersionError(
            "Material receipt was modified by another actor since it was read",
            expected_version=cmd.expected_version,
            current_version=receipt_row.version,
        )
    if receipt_row.state != "received":
        raise InvalidTransitionError(
            "Only a receipt in 'received' state can be examined", current_status=receipt_row.state
        )
    if cmd.container_count < 1:
        raise ValidationFailedError("container_count must be at least 1")

    # RCV-FR-005: coarse supplier-eligibility check (Supplier.status == "approved"). Validating against
    # a material-specific approved-source matrix needs `approved_supplier_material`, which does not exist
    # yet anywhere in this codebase (SG-057) — not guessed onto this check.
    supplier_not_approved = False
    if receipt_row.supplier_id is not None:
        supplier = await session.get(Supplier, receipt_row.supplier_id)
        if supplier is None or supplier.status != "approved":
            supplier_not_approved = True

    discrepancy_type = None
    if not cmd.identity_confirmed:
        discrepancy_type = "identity_mismatch"
    elif cmd.damage_observed:
        discrepancy_type = "damaged"
    elif cmd.seal_broken:
        discrepancy_type = "seal_broken"
    elif cmd.contamination_observed:
        discrepancy_type = "contamination"
    elif supplier_not_approved:
        discrepancy_type = "source_not_approved"

    old_state = receipt_row.state
    receipt_row.labeling_ok = cmd.labeling_ok
    receipt_row.damage_observed = cmd.damage_observed
    receipt_row.seal_broken = cmd.seal_broken
    receipt_row.contamination_observed = cmd.contamination_observed
    receipt_row.examination_notes = cmd.examination_notes
    receipt_row.examined_by_user_id = actor_user_id
    receipt_row.examined_at = datetime.now(timezone.utc)
    receipt_row.version += 1

    lot_id = None
    if discrepancy_type is not None:
        # identity_mismatch is the one discrepancy type with no other structured signal to explain it
        # (the visual-exam booleans and the supplier-approval check are self-explanatory) -- only that
        # case requires the examiner to supply a free-text reason.
        if discrepancy_type == "identity_mismatch" and not cmd.discrepancy_reason:
            raise ValidationFailedError("discrepancy_reason is required for an identity mismatch")
        receipt_row.state = "discrepancy_hold"
        receipt_row.discrepancy_type = discrepancy_type
        receipt_row.discrepancy_reason = cmd.discrepancy_reason or f"Automatic hold: {discrepancy_type}"
    else:
        receipt_row.state = "examined"
        accepted_qty = receipt_row.accepted_quantity or receipt_row.received_gross_quantity
        lot = MaterialLot(
            material_id=receipt_row.material_id,
            site_id=receipt_row.site_id,
            supplier_lot=receipt_row.supplier_lot,
            manufacturer_lot=receipt_row.manufacturer_lot,
            internal_lot=cmd.internal_lot,
            received_quantity=accepted_qty,
            available_quantity=accepted_qty,
            uom=receipt_row.uom,
            uom_id=receipt_row.uom_id,  # copied from the receipt's own already-resolved value
            status="quarantine",
            expiry_date=receipt_row.expiry_date,
            retest_date=receipt_row.retest_date,
            received_by_user_id=receipt_row.receiver_subject_id,
            version=1,
            receipt_id=receipt_row.id,
            manufacture_date=receipt_row.manufacture_date,
        )
        session.add(lot)
        await session.flush()
        lot_id = lot.id

        precision = Decimal("0.000001")  # Numeric(18, 6) — DATA-FR-019 exact decimal, not binary float
        per_container_qty = (accepted_qty / cmd.container_count).quantize(precision)
        remainder = accepted_qty - (per_container_qty * cmd.container_count)
        for i in range(cmd.container_count):
            qty = per_container_qty + (remainder if i == cmd.container_count - 1 else Decimal("0"))
            session.add(
                MaterialContainer(
                    material_lot_id=lot.id,
                    container_code=f"{cmd.internal_lot}-C{i + 1:03d}",
                    received_quantity=qty,
                    current_quantity=qty,
                    uom=receipt_row.uom,
                    uom_id=receipt_row.uom_id,  # copied from the receipt's own already-resolved value
                    version=1,
                )
            )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=receipt_row.site_id,
        aggregate_type="material_receipt",
        aggregate_id=receipt_row.id,
        aggregate_version=receipt_row.version,
        action="StatusChanged",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"state": old_state},
        new_value={"state": receipt_row.state, "discrepancy_type": discrepancy_type},
    )
    await write_outbox_event(
        session,
        event_type="MaterialQuarantined" if lot_id else "ReceiptDiscrepancyRaised",
        aggregate_type="material_receipt",
        aggregate_id=receipt_row.id,
        aggregate_version=receipt_row.version,
        payload={"id": str(receipt_row.id), "state": receipt_row.state, "lot_id": str(lot_id) if lot_id else None},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=receipt_row.site_id,
        command_type="ExamineReceipt",
        aggregate_type="material_receipt",
        aggregate_id=receipt_row.id,
        expected_version=cmd.expected_version,
        resulting_version=receipt_row.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=receipt_row.id,
        resulting_version=receipt_row.version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CreateSamplingOrder — RCV-FR-018/019.
# ---------------------------------------------------------------------------


class CreateSamplingOrderCommand(CommandEnvelope):
    lot_id: uuid.UUID
    expected_version: int
    sampling_plan_ref: str | None = None
    selected_container_ids: list[uuid.UUID]
    assigned_sampler_user_id: uuid.UUID
    aseptic_evidence_ref: str | None = None


async def create_sampling_order(
    session: AsyncSession, cmd: CreateSamplingOrderCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.selected_container_ids:
        raise ValidationFailedError("selected_container_ids must not be empty")

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
    if lot.status not in ("quarantine", "sampling"):
        raise InvalidTransitionError(
            "Sampling can only be ordered while the lot is in quarantine or already sampling",
            current_status=lot.status,
        )

    for container_id in cmd.selected_container_ids:
        container = await session.get(MaterialContainer, container_id)
        if container is None or container.material_lot_id != lot.id:
            raise NotFoundError("Selected container does not belong to this lot", container_id=str(container_id))

    old_status = lot.status
    lot.status = "sampling"
    lot.version += 1

    order = SamplingOrder(
        material_lot_id=lot.id,
        sampling_plan_ref=cmd.sampling_plan_ref,
        selected_container_ids={"ids": [str(c) for c in cmd.selected_container_ids]},
        assigned_sampler_user_id=cmd.assigned_sampler_user_id,
        status="requested",
        aseptic_evidence_ref=cmd.aseptic_evidence_ref,
        version=1,
    )
    session.add(order)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="sampling_order",
        aggregate_id=order.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"lot_status": old_status},
        new_value={"lot_status": lot.status, "sampling_order_id": str(order.id)},
    )
    await write_outbox_event(
        session,
        event_type="SamplingOrdered",
        aggregate_type="sampling_order",
        aggregate_id=order.id,
        aggregate_version=1,
        payload={"id": str(order.id), "lot_id": str(lot.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="CreateSamplingOrder",
        aggregate_type="sampling_order",
        aggregate_id=order.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=order.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CollectSample — RCV-FR-020/021 (partial: aseptic evidence captured, no equipment-qualification check,
# WP-06 not built)/022. Creates a qc_sample via the existing qc module (QcSample.source_type already
# supports "material_lot" — SG-057/SG-063's scope_type restriction is on QC *test specifications*, not on
# samples, so this call needs no new QC-side change).
# ---------------------------------------------------------------------------


class CollectSampleCommand(CommandEnvelope):
    sampling_order_id: uuid.UUID
    expected_version: int
    sample_quantity: Decimal
    sample_uom: str


async def collect_sample(
    session: AsyncSession, cmd: CollectSampleCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(
        select(SamplingOrder).where(SamplingOrder.id == cmd.sampling_order_id).with_for_update()
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise NotFoundError("Sampling order not found")
    if order.version != cmd.expected_version:
        raise StaleVersionError(
            "Sampling order was modified by another actor since it was read",
            expected_version=cmd.expected_version,
            current_version=order.version,
        )
    if order.status != "requested":
        raise InvalidTransitionError("Only a requested sampling order can be collected", current_status=order.status)

    lot = await session.get(MaterialLot, order.material_lot_id)
    if lot is None:
        raise NotFoundError("Material lot not found")

    sample_receipt = await qc_commands.create_sample(
        session,
        qc_commands.CreateSampleCommand(
            idempotency_key=str(uuid.uuid4()),
            sample_number=f"MAT-{lot.internal_lot}-{order.id.hex[:8]}",
            sample_type="material",
            source_type="material_lot",
            source_id=lot.id,
            lot_batch_serial_ref=lot.internal_lot,
            sample_quantity=str(cmd.sample_quantity),
            sample_uom=cmd.sample_uom,
            sampled_at=datetime.now(timezone.utc),
        ),
        order.assigned_sampler_user_id,
    )

    for raw_id in order.selected_container_ids.get("ids", []):
        container = await session.get(MaterialContainer, uuid.UUID(raw_id))
        if container is not None:
            container.sampled = True
            container.version += 1

    old_status = lot.status
    lot.status = "testing"
    lot.version += 1
    order.status = "collected"
    order.qc_sample_id = sample_receipt.aggregate_id
    order.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="sampling_order",
        aggregate_id=order.id,
        aggregate_version=order.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"status": "requested", "lot_status": old_status},
        new_value={"status": order.status, "lot_status": lot.status, "qc_sample_id": str(order.qc_sample_id)},
    )
    await write_outbox_event(
        session,
        event_type="SampleCollected",
        aggregate_type="sampling_order",
        aggregate_id=order.id,
        aggregate_version=order.version,
        payload={"id": str(order.id), "lot_id": str(lot.id), "qc_sample_id": str(order.qc_sample_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="CollectSample",
        aggregate_type="sampling_order",
        aggregate_id=order.id,
        expected_version=cmd.expected_version,
        resulting_version=order.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=order.id,
        resulting_version=order.version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ReleaseMaterialLot / RejectMaterialLot — RCV-FR-023/024/025 (partial: general "QC evidence exists" gate
# only, via the same rules-engine no-op-until-authored hook `disposition_material_lot` already uses; no
# material-scoped QC specification exists to enforce a specific required test — SG-057/SG-063)/026/027/030.
# Document 106 rows 44/45: signer role "QA Approver / Batch Release" (this codebase's "QA Releaser"),
# independent of every production performer on the record (SIG-FR-018) — reuses the exact equality-check
# pattern `batch.commands.release_batch` uses against its reviewer.
# ---------------------------------------------------------------------------


async def _independence_violation(session: AsyncSession, lot: MaterialLot, actor_user_id: uuid.UUID) -> bool:
    if lot.receipt_id is not None:
        receipt_row = await session.get(MaterialReceipt, lot.receipt_id)
        if receipt_row is not None and receipt_row.receiver_subject_id == actor_user_id:
            return True
    orders = (
        await session.execute(select(SamplingOrder).where(SamplingOrder.material_lot_id == lot.id))
    ).scalars().all()
    return any(o.assigned_sampler_user_id == actor_user_id for o in orders)


async def _disposition_material_lot_v2(
    session: AsyncSession,
    *,
    cmd: "ReleaseMaterialLotCommand | RejectMaterialLotCommand",
    decision: str,
    action: str,
    actor_user_id: uuid.UUID,
    site_id: uuid.UUID,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

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
    if lot.status not in PRE_DISPOSITION_LOT_STATES:
        raise InvalidTransitionError(
            "Lot is not in a state eligible for a quality disposition", current_status=lot.status
        )
    if decision == "rejected" and not cmd.reason:
        raise ValidationFailedError("reason is required to reject a material lot")

    if cmd.container_ids:
        for container_id in cmd.container_ids:
            container = await session.get(MaterialContainer, container_id)
            if container is None or container.material_lot_id != lot.id:
                raise NotFoundError(
                    "Selected container does not belong to this lot", container_id=str(container_id)
                )

    await evaluate_policy(session, actor_user_id, action=f"material_lot.{action}", site_id=site_id)

    if await _independence_violation(session, lot, actor_user_id):
        raise ValidationFailedError(
            "Signer must be independent of every production performer on this record (receiver/sampler)"
        )

    # MUT-FR-014/RUL-FR-016: same no-op-until-authored release-gate hook `disposition_material_lot`
    # already uses — RCV-FR-023/024/025's material-scoped QC requirement stays a SPEC_GAP, not guessed.
    if decision == "released":
        await rules_commands.evaluate_release_gate(
            session,
            rule_id=f"material-lot-release-eligibility:{lot.material_id}",
            inputs={
                "available_quantity": str(lot.available_quantity),
                "received_quantity": str(lot.received_quantity),
            },
            aggregate_type="material_lot",
            aggregate_id=lot.id,
            aggregate_version=lot.version,
            actor_user_id=actor_user_id,
        )

    policy = await signature_service.resolve_signature_requirement(session, record_type="material_lot", action=action)
    signature_id = None
    if policy.signature_required:
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
        signature = await signature_service.sign(
            session, challenge=challenge, auth_context={"method": "password_reauth"}
        )
        signature_id = signature.id

    session.add(
        MaterialQualityDisposition(
            material_lot_id=lot.id,
            container_ids={"ids": [str(c) for c in cmd.container_ids]} if cmd.container_ids else None,
            decision=decision,
            evidence_refs=None,
            reason=cmd.reason,
            signature_id=signature_id,
            disposed_by_user_id=actor_user_id,
        )
    )

    old_status = lot.status
    is_partial = bool(cmd.container_ids)
    if is_partial:
        for container_id in cmd.container_ids:
            container = await session.get(MaterialContainer, container_id)
            container.quality_status_override = decision
            container.version += 1
    else:
        lot.status = decision
        if decision == "released":
            lot.released_at = datetime.now(timezone.utc)
            lot.release_signature_id = signature_id
    lot.version += 1

    await vault_service.release_master(
        session,
        object_type="material_lot",
        business_id=lot.internal_lot,
        site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "lot_id": str(lot.id),
            "internal_lot": lot.internal_lot,
            "decision": decision,
            "container_ids": [str(c) for c in cmd.container_ids] if cmd.container_ids else None,
            "reason": cmd.reason,
            "signature_id": str(signature_id) if signature_id else None,
        },
    )

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
        new_value={"status": lot.status if not is_partial else old_status, "decision": decision},
        signature_id=signature_id,
        reason=cmd.reason,
    )
    await write_outbox_event(
        session,
        event_type="MaterialReleased" if decision == "released" else "MaterialRejected",
        aggregate_type="material_lot",
        aggregate_id=lot.id,
        aggregate_version=lot.version,
        payload={"id": str(lot.id), "decision": decision},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type=f"MaterialLot{action.capitalize()}",
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
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


class ReleaseMaterialLotCommand(CommandEnvelope):
    lot_id: uuid.UUID
    expected_version: int
    reason: str | None = None
    container_ids: list[uuid.UUID] | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def release_material_lot(
    session: AsyncSession, cmd: ReleaseMaterialLotCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    return await _disposition_material_lot_v2(
        session, cmd=cmd, decision="released", action="release",
        actor_user_id=actor_user_id, site_id=site_id,
    )


class RejectMaterialLotCommand(CommandEnvelope):
    lot_id: uuid.UUID
    expected_version: int
    reason: str
    container_ids: list[uuid.UUID] | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def reject_material_lot(
    session: AsyncSession, cmd: RejectMaterialLotCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    return await _disposition_material_lot_v2(
        session, cmd=cmd, decision="rejected", action="reject",
        actor_user_id=actor_user_id, site_id=site_id,
    )


# ---------------------------------------------------------------------------
# RetestMaterialLot — RCV-FR-029. Not in Document 106's two material_lot signature rows (release/reject
# only) — unsigned, matching every other module's precedent that "no Document 106 row = unsigned/
# RBAC-ungated".
# ---------------------------------------------------------------------------


class RetestMaterialLotCommand(CommandEnvelope):
    lot_id: uuid.UUID
    expected_version: int
    reason: str


async def retest_material_lot(
    session: AsyncSession, cmd: RetestMaterialLotCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.reason:
        raise ValidationFailedError("reason is required to place a material lot on retest")

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
    if lot.status not in PRE_DISPOSITION_LOT_STATES:
        raise InvalidTransitionError(
            "Lot is not in a state eligible for a retest decision", current_status=lot.status
        )

    await evaluate_policy(session, actor_user_id, action="material_lot.retest", site_id=site_id)

    session.add(
        MaterialQualityDisposition(
            material_lot_id=lot.id,
            container_ids=None,
            decision="retest_due",
            evidence_refs=None,
            reason=cmd.reason,
            signature_id=None,
            disposed_by_user_id=actor_user_id,
        )
    )

    old_status = lot.status
    lot.status = "retest_due"
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
        reason=cmd.reason,
    )
    await write_outbox_event(
        session,
        event_type="MaterialRetestRequired",
        aggregate_type="material_lot",
        aggregate_id=lot.id,
        aggregate_version=lot.version,
        payload={"id": str(lot.id), "status": lot.status},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="RetestMaterialLot",
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


# ---------------------------------------------------------------------------
# Quality-status engine (RCV-FR-025 read side, §7) and release-readiness — read-only, no CommandEnvelope/
# mutation (GET operations per Document 19 §5). Never derive a regulated decision from raw status text
# alone (§7): both evaluate expiry/retest/hold/QC evidence, not just MaterialLot.status.
# ---------------------------------------------------------------------------


async def get_quality_status(session: AsyncSession, lot_id: uuid.UUID) -> dict:
    lot = await session.get(MaterialLot, lot_id)
    if lot is None:
        raise NotFoundError("Material lot not found")

    today = datetime.now(timezone.utc).date()
    expired = lot.expiry_date is not None and lot.expiry_date < today
    retest_overdue = lot.retest_date is not None and lot.retest_date < today and lot.status not in (
        "rejected",
        "consumed",
    )
    latest_disposition = (
        await session.execute(
            select(MaterialQualityDisposition)
            .where(MaterialQualityDisposition.material_lot_id == lot.id)
            .order_by(MaterialQualityDisposition.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return {
        "lot_id": str(lot.id),
        "status": lot.status,
        "version": lot.version,
        "expired": expired,
        "retest_overdue": retest_overdue,
        "eligible_for_use": lot.status == "released" and not expired,
        "latest_disposition_decision": latest_disposition.decision if latest_disposition else None,
        "latest_disposition_reason": latest_disposition.reason if latest_disposition else None,
    }


async def get_release_readiness(session: AsyncSession, lot_id: uuid.UUID) -> dict:
    lot = await session.get(MaterialLot, lot_id)
    if lot is None:
        raise NotFoundError("Material lot not found")

    receipt_clean = True
    if lot.receipt_id is not None:
        receipt_row = await session.get(MaterialReceipt, lot.receipt_id)
        receipt_clean = receipt_row is None or receipt_row.state != "discrepancy_hold"

    sampling_orders = (
        await session.execute(select(SamplingOrder).where(SamplingOrder.material_lot_id == lot.id))
    ).scalars().all()
    sampling_complete = any(o.status == "collected" for o in sampling_orders) if sampling_orders else None

    today = datetime.now(timezone.utc).date()
    not_expired = lot.expiry_date is None or lot.expiry_date >= today

    return {
        "lot_id": str(lot.id),
        "status": lot.status,
        "version": lot.version,
        "eligible_state": lot.status in PRE_DISPOSITION_LOT_STATES,
        "receipt_discrepancy_clear": receipt_clean,
        "sampling_complete": sampling_complete,
        "not_expired": not_expired,
        # RCV-FR-023/025: whether QC evidence exists cannot be enforced as a required-test rule (no
        # material-scoped QC specification exists, SG-057/SG-063) — surfaced as advisory information only.
        "qc_sample_ids": [str(o.qc_sample_id) for o in sampling_orders if o.qc_sample_id is not None],
    }


# ---------------------------------------------------------------------------
# Document 20 (SPEC-MAT-002B) — Inventory, Lot/Container & Warehouse.
#
# INV-FR-015/016 (quality hold / recall block): reuses MaterialLot.status /
# MaterialContainer.quality_status_override as the hold mechanism — no new hold entity. INV-FR-013/014
# (expiry/retest-due exclusion): reuses MaterialLot.expiry_date/retest_date already enforced by Document
# 19's own eligibility patterns.
# ---------------------------------------------------------------------------

# Section 6 selection algorithm's zone-compatibility rule (INV-FR-002/008): ordinary engineering decision
# -- the spec gives no explicit status->zone_type compatibility table. A zone_type not in this map (return/
# destruction/controlled_temperature/sterile_component/other) has no additional constraint.
_ZONE_STATUS_COMPAT = {
    "released": "released",
    "quarantine": "quarantine",
    "sampling": "quarantine",
    "testing": "quarantine",
    "qc_disposition_pending": "quarantine",
    "retest_due": "quarantine",
    "rejected": "rejected",
}


def _effective_status(lot: MaterialLot, container: MaterialContainer | None) -> str:
    if container is not None and container.quality_status_override:
        return container.quality_status_override
    return lot.status


def _is_eligible(lot: MaterialLot, container: MaterialContainer | None, today: date) -> bool:
    if _effective_status(lot, container) != "released":
        return False
    if lot.expiry_date is not None and lot.expiry_date < today:
        return False
    if lot.retest_date is not None and lot.retest_date < today:
        return False
    return True


async def _lock_or_create_balance(
    session: AsyncSession,
    *,
    site_id: uuid.UUID,
    material_lot_id: uuid.UUID,
    container_id: uuid.UUID | None,
    location_id: uuid.UUID,
) -> InventoryBalanceProjection:
    result = await session.execute(
        select(InventoryBalanceProjection)
        .where(
            InventoryBalanceProjection.material_lot_id == material_lot_id,
            InventoryBalanceProjection.container_id == container_id,
            InventoryBalanceProjection.location_id == location_id,
        )
        .with_for_update()
    )
    balance = result.scalar_one_or_none()
    if balance is None:
        balance = InventoryBalanceProjection(
            site_id=site_id,
            material_lot_id=material_lot_id,
            container_id=container_id,
            location_id=location_id,
            on_hand=Decimal("0"),
            reserved=Decimal("0"),
            available=Decimal("0"),
            version=1,
        )
        session.add(balance)
        await session.flush()
    return balance


async def get_inventory_availability(
    session: AsyncSession, *, material_id: uuid.UUID, site_id: uuid.UUID
) -> list[dict]:
    today = datetime.now(timezone.utc).date()
    rows = (
        await session.execute(
            select(MaterialLot, MaterialContainer, InventoryBalanceProjection, WarehouseLocation)
            .join(MaterialContainer, MaterialContainer.material_lot_id == MaterialLot.id)
            .join(
                InventoryBalanceProjection,
                (InventoryBalanceProjection.material_lot_id == MaterialLot.id)
                & (InventoryBalanceProjection.container_id == MaterialContainer.id),
            )
            .join(WarehouseLocation, WarehouseLocation.id == InventoryBalanceProjection.location_id)
            .where(
                MaterialLot.material_id == material_id,
                MaterialLot.site_id == site_id,
                MaterialContainer.container_status == "active",
                InventoryBalanceProjection.available > 0,
            )
            .order_by(MaterialLot.expiry_date.asc().nullslast(), MaterialLot.received_at.asc())
        )
    ).all()
    return [
        {
            "material_lot_id": str(lot.id),
            "internal_lot": lot.internal_lot,
            "container_id": str(container.id),
            "location_id": str(location.id),
            "location_code": location.location_code,
            "available": str(balance.available),
            "uom": container.uom,
            "expiry_date": lot.expiry_date.isoformat() if lot.expiry_date else None,
        }
        for lot, container, balance, location in rows
        if _is_eligible(lot, container, today)
    ]


# ---------------------------------------------------------------------------
# CreateInventoryReservation — INV-FR-010/012: server-side FEFO selection (baseline only, no deviation-
# override path -- SG-083). Unsigned (no Document 106 row).
# ---------------------------------------------------------------------------


class CreateInventoryReservationCommand(CommandEnvelope):
    batch_id: uuid.UUID
    material_id: uuid.UUID
    site_id: uuid.UUID
    quantity: Decimal
    uom: str


async def create_inventory_reservation(
    session: AsyncSession, cmd: CreateInventoryReservationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.quantity <= 0:
        raise ValidationFailedError("quantity must be positive")

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    today = datetime.now(timezone.utc).date()
    candidates = (
        await session.execute(
            select(MaterialLot, MaterialContainer, InventoryBalanceProjection)
            .join(MaterialContainer, MaterialContainer.material_lot_id == MaterialLot.id)
            .join(
                InventoryBalanceProjection,
                (InventoryBalanceProjection.material_lot_id == MaterialLot.id)
                & (InventoryBalanceProjection.container_id == MaterialContainer.id),
            )
            .where(
                MaterialLot.material_id == cmd.material_id,
                MaterialLot.site_id == cmd.site_id,
                MaterialContainer.container_status == "active",
                InventoryBalanceProjection.available >= cmd.quantity,
            )
            .order_by(MaterialLot.expiry_date.asc().nullslast(), MaterialLot.received_at.asc())
        )
    ).all()

    chosen_balance_id = None
    chosen_lot = None
    chosen_container = None
    for lot, container, balance in candidates:
        if _is_eligible(lot, container, today):
            chosen_balance_id = balance.id
            chosen_lot = lot
            chosen_container = container
            break
    if chosen_balance_id is None:
        raise ValidationFailedError(
            "No eligible released, non-expired, non-retest-due lot/container has sufficient "
            "available quantity for this reservation"
        )

    balance = (
        await session.execute(
            select(InventoryBalanceProjection)
            .where(InventoryBalanceProjection.id == chosen_balance_id)
            .with_for_update()
        )
    ).scalar_one()
    if balance.available < cmd.quantity:
        raise ValidationFailedError(
            "Available quantity changed since selection; resubmit the reservation",
            available=str(balance.available),
            requested=str(cmd.quantity),
        )

    balance.reserved += cmd.quantity
    balance.available -= cmd.quantity
    balance.version += 1

    cmd_uom_id = await _resolve_uom_id(session, cmd.uom)
    txn = InventoryTransaction(
        site_id=cmd.site_id,
        material_lot_id=chosen_lot.id,
        container_id=chosen_container.id,
        transaction_type="RESERVE",
        quantity=cmd.quantity,
        uom=cmd.uom,
        uom_id=cmd_uom_id,
        to_location_id=balance.location_id,
        reference_type="batch",
        reference_id=cmd.batch_id,
        actor_type="human",
        actor_id=str(actor_user_id),
    )
    session.add(txn)
    await session.flush()
    balance.last_transaction_id = txn.id

    reservation = InventoryReservation(
        site_id=cmd.site_id,
        batch_id=cmd.batch_id,
        material_id=cmd.material_id,
        material_lot_id=chosen_lot.id,
        container_id=chosen_container.id,
        location_id=balance.location_id,
        quantity=cmd.quantity,
        uom=cmd.uom,
        uom_id=cmd_uom_id,
        status="active",
        requested_by_user_id=actor_user_id,
        version=1,
    )
    session.add(reservation)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.site_id,
        aggregate_type="inventory_reservation",
        aggregate_id=reservation.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={
            "material_lot_id": str(chosen_lot.id),
            "container_id": str(chosen_container.id),
            "quantity": str(cmd.quantity),
        },
    )
    await write_outbox_event(
        session,
        event_type="InventoryReserved",
        aggregate_type="inventory_reservation",
        aggregate_id=reservation.id,
        aggregate_version=1,
        payload={"id": str(reservation.id), "batch_id": str(cmd.batch_id), "quantity": str(cmd.quantity)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="CreateInventoryReservation",
        aggregate_type="inventory_reservation",
        aggregate_id=reservation.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=reservation.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ReleaseInventoryReservation — INV-FR-011. The one Document 20 signed operation (Document 106 row 46:
# meaning "Released", role QA Releaser, independent of every production performer on the record --
# mirrors app/modules/batch/commands.py::release_batch's independence-check pattern, scoped to the
# reservation's own requester since no broader batch-performer lookup is declared anywhere in Document
# 20). "Release" here means giving the reservation back (INV-FR-011 "released when batch changes"), not
# approving material use. No vault snapshot -- Document 20 never references Document 06, and this isn't a
# "released master record" in that sense (deliberate scoping).
# ---------------------------------------------------------------------------


class ReleaseInventoryReservationCommand(CommandEnvelope):
    reservation_id: uuid.UUID
    expected_version: int
    reason: str | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def release_inventory_reservation(
    session: AsyncSession,
    cmd: ReleaseInventoryReservationCommand,
    actor_user_id: uuid.UUID,
    site_id: uuid.UUID,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(
        select(InventoryReservation)
        .where(InventoryReservation.id == cmd.reservation_id)
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise NotFoundError("Inventory reservation not found")
    if reservation.version != cmd.expected_version:
        raise StaleVersionError(
            "Inventory reservation was modified by another actor since it was read",
            expected_version=cmd.expected_version,
            current_version=reservation.version,
        )
    if reservation.status != "active":
        raise InvalidTransitionError(
            "Only an active reservation can be released", current_status=reservation.status
        )

    await evaluate_policy(session, actor_user_id, action="inventory_reservation.release", site_id=site_id)
    if actor_user_id == reservation.requested_by_user_id:
        raise ValidationFailedError(
            "Signer must be independent of every production performer on this record (requester)"
        )

    policy = await signature_service.resolve_signature_requirement(
        session, record_type="inventory_reservation", action="release"
    )
    # Document 106 row 46: reason_required=True for this action -- AUD-FR-008.
    if policy.reason_required and not cmd.reason:
        raise ValidationFailedError("reason is required to release this reservation")
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session,
            challenge_id=cmd.challenge_id,
            user_id=actor_user_id,
            record_version=reservation.version,
            record_hash=reservation_record_hash(reservation),
        )
        signature = await signature_service.sign(
            session, challenge=challenge, auth_context={"method": "password_reauth"}
        )
        signature_id = signature.id

    balance = (
        await session.execute(
            select(InventoryBalanceProjection)
            .where(
                InventoryBalanceProjection.material_lot_id == reservation.material_lot_id,
                InventoryBalanceProjection.container_id == reservation.container_id,
                InventoryBalanceProjection.location_id == reservation.location_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if balance is not None:
        balance.reserved -= reservation.quantity
        balance.available += reservation.quantity
        balance.version += 1

        txn = InventoryTransaction(
            site_id=site_id,
            material_lot_id=reservation.material_lot_id,
            container_id=reservation.container_id,
            transaction_type="UNRESERVE",
            quantity=reservation.quantity,
            uom=reservation.uom,
            uom_id=reservation.uom_id,  # copied from the reservation's own already-resolved value
            from_location_id=reservation.location_id,
            reference_type="batch",
            reference_id=reservation.batch_id,
            actor_type="human",
            actor_id=str(actor_user_id),
        )
        session.add(txn)
        await session.flush()
        balance.last_transaction_id = txn.id

    old_status = reservation.status
    reservation.status = "released"
    reservation.released_by_user_id = actor_user_id
    reservation.released_at = datetime.now(timezone.utc)
    reservation.release_signature_id = signature_id
    reservation.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="inventory_reservation",
        aggregate_id=reservation.id,
        aggregate_version=reservation.version,
        action="StatusChanged",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"status": old_status},
        new_value={"status": reservation.status},
        signature_id=signature_id,
        reason=cmd.reason,
    )
    await write_outbox_event(
        session,
        event_type="InventoryReservationReleased",
        aggregate_type="inventory_reservation",
        aggregate_id=reservation.id,
        aggregate_version=reservation.version,
        payload={"id": str(reservation.id), "status": reservation.status},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="ReleaseInventoryReservation",
        aggregate_type="inventory_reservation",
        aggregate_id=reservation.id,
        expected_version=cmd.expected_version,
        resulting_version=reservation.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=reservation.id,
        resulting_version=reservation.version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CreateInventoryTransfer — INV-FR-008/009. `from_location_id=None` is this container's first ledger
# entry (put-away after Document 19 quarantine — no dedicated "record receipt into a location" endpoint
# exists in Document 20's own 8-op API list, so the declared /transfers operation carries this dual
# RECEIPT/TRANSFER role rather than inventing a 9th endpoint), written as transaction_type RECEIPT.
# True cross-site inter-site transfer (destination-site container re-identification) is not built --
# same-site only this pass (SG-085).
# ---------------------------------------------------------------------------


class CreateInventoryTransferCommand(CommandEnvelope):
    material_lot_id: uuid.UUID
    container_id: uuid.UUID
    from_location_id: uuid.UUID | None = None
    to_location_id: uuid.UUID
    quantity: Decimal


async def create_inventory_transfer(
    session: AsyncSession, cmd: CreateInventoryTransferCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.quantity <= 0:
        raise ValidationFailedError("quantity must be positive")

    lot = await session.get(MaterialLot, cmd.material_lot_id)
    if lot is None:
        raise NotFoundError("Material lot not found")
    container = await session.get(MaterialContainer, cmd.container_id)
    if container is None or container.material_lot_id != lot.id:
        raise NotFoundError("Container not found for this lot")
    if container.container_status != "active":
        raise InvalidTransitionError(
            "Only an active container can be transferred", current_status=container.container_status
        )
    to_location = await session.get(WarehouseLocation, cmd.to_location_id)
    if to_location is None:
        raise NotFoundError("Destination location not found")
    if to_location.site_id != lot.site_id:
        raise ValidationFailedError(
            "True inter-site transfer with destination-site re-identification is not built this pass "
            "(SG-085) -- destination location must be at the lot's own site"
        )

    effective_status = _effective_status(lot, container)
    required_zone = _ZONE_STATUS_COMPAT.get(effective_status)
    if required_zone is not None and to_location.zone_type != required_zone:
        raise InvalidTransitionError(
            "Destination zone is not compatible with this container's quality status",
            current_status=effective_status,
        )

    from_balance = None
    if cmd.from_location_id is None:
        existing_anywhere = (
            await session.execute(
                select(InventoryBalanceProjection).where(
                    InventoryBalanceProjection.container_id == container.id
                )
            )
        ).first()
        if existing_anywhere is not None:
            raise ValidationFailedError(
                "This container already has a ledger location; from_location_id is required"
            )
        if cmd.quantity != container.current_quantity:
            raise ValidationFailedError(
                "Initial location assignment quantity must equal the container's full current quantity"
            )
        txn_type = "RECEIPT"
    else:
        from_location = await session.get(WarehouseLocation, cmd.from_location_id)
        if from_location is None:
            raise NotFoundError("Source location not found")
        from_balance = await _lock_or_create_balance(
            session,
            site_id=site_id,
            material_lot_id=lot.id,
            container_id=container.id,
            location_id=cmd.from_location_id,
        )
        if from_balance.on_hand < cmd.quantity:
            raise ValidationFailedError(
                "Insufficient on-hand quantity at source location",
                on_hand=str(from_balance.on_hand),
                requested=str(cmd.quantity),
            )
        txn_type = "TRANSFER"

    to_balance = await _lock_or_create_balance(
        session, site_id=site_id, material_lot_id=lot.id, container_id=container.id, location_id=cmd.to_location_id
    )

    if from_balance is not None:
        from_balance.on_hand -= cmd.quantity
        from_balance.available -= cmd.quantity
        from_balance.version += 1
    to_balance.on_hand += cmd.quantity
    to_balance.available += cmd.quantity
    to_balance.version += 1

    txn = InventoryTransaction(
        site_id=site_id,
        material_lot_id=lot.id,
        container_id=container.id,
        transaction_type=txn_type,
        quantity=cmd.quantity,
        uom=container.uom,
        uom_id=container.uom_id,  # copied from the container's own already-resolved value
        from_location_id=cmd.from_location_id,
        to_location_id=cmd.to_location_id,
        actor_type="human",
        actor_id=str(actor_user_id),
    )
    session.add(txn)
    await session.flush()
    to_balance.last_transaction_id = txn.id
    if from_balance is not None:
        from_balance.last_transaction_id = txn.id

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="inventory_balance_projection",
        aggregate_id=to_balance.id,
        aggregate_version=to_balance.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={
            "transaction_type": txn_type,
            "container_id": str(container.id),
            "to_location_id": str(cmd.to_location_id),
            "quantity": str(cmd.quantity),
        },
    )
    await write_outbox_event(
        session,
        event_type="InventoryTransferred",
        aggregate_type="inventory_balance_projection",
        aggregate_id=to_balance.id,
        aggregate_version=to_balance.version,
        payload={"container_id": str(container.id), "transaction_type": txn_type, "quantity": str(cmd.quantity)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="CreateInventoryTransfer",
        aggregate_type="inventory_balance_projection",
        aggregate_id=to_balance.id,
        expected_version=None,
        resulting_version=to_balance.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=to_balance.id,
        resulting_version=to_balance.version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# SplitContainer — INV-FR-023/025. Reuses examine_receipt's Decimal-quantize conservation pattern.
# Bounded to a container with at most one ledger location (balance row) to keep conservation math
# tractable -- a multi-location container must be consolidated via transfer first.
# ---------------------------------------------------------------------------


class SplitContainerCommand(CommandEnvelope):
    container_id: uuid.UUID
    expected_version: int
    split_quantities: list[Decimal]


async def split_container(
    session: AsyncSession, cmd: SplitContainerCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if len(cmd.split_quantities) < 2:
        raise ValidationFailedError("split requires at least two child quantities")
    if any(q <= 0 for q in cmd.split_quantities):
        raise ValidationFailedError("split quantities must be positive")

    result = await session.execute(
        select(MaterialContainer).where(MaterialContainer.id == cmd.container_id).with_for_update()
    )
    container = result.scalar_one_or_none()
    if container is None:
        raise NotFoundError("Material container not found")
    if container.version != cmd.expected_version:
        raise StaleVersionError(
            "Container was modified by another actor since it was read",
            expected_version=cmd.expected_version,
            current_version=container.version,
        )
    if container.container_status != "active":
        raise InvalidTransitionError(
            "Only an active container can be split", current_status=container.container_status
        )
    active_reservation = (
        await session.execute(
            select(InventoryReservation).where(
                InventoryReservation.container_id == container.id, InventoryReservation.status == "active"
            )
        )
    ).first()
    if active_reservation is not None:
        raise ValidationFailedError("Cannot split a container with an active reservation")

    total = sum(cmd.split_quantities)
    if total != container.current_quantity:
        raise ValidationFailedError(
            "Split quantities must exactly conserve the container's current quantity",
            current_quantity=str(container.current_quantity),
            split_total=str(total),
        )

    balances = (
        await session.execute(
            select(InventoryBalanceProjection)
            .where(InventoryBalanceProjection.container_id == container.id)
            .with_for_update()
        )
    ).scalars().all()
    if len(balances) > 1:
        raise ValidationFailedError(
            "Container has ledger presence at more than one location; consolidate via transfer before splitting"
        )
    source_balance = balances[0] if balances else None

    children = []
    for i, qty in enumerate(cmd.split_quantities):
        child = MaterialContainer(
            material_lot_id=container.material_lot_id,
            container_code=f"{container.container_code}-S{i + 1:02d}",
            received_quantity=qty,
            current_quantity=qty,
            uom=container.uom,
            uom_id=container.uom_id,  # copied from the parent container's own already-resolved value
            location_zone=container.location_zone,
            quality_status_override=container.quality_status_override,
            parent_container_id=container.id,
            version=1,
        )
        session.add(child)
        children.append((child, qty))
    await session.flush()

    if source_balance is not None:
        # Same remainder-to-last-child conservation technique as examine_receipt's container split --
        # per-child proportional share, with the rounding remainder assigned to the last child so the
        # total is conserved exactly, never drifted by independent per-child rounding.
        precision = Decimal("0.00000001")  # Numeric(24, 8)
        balance_total = source_balance.on_hand
        allocated = Decimal("0")
        for i, (child, qty) in enumerate(children):
            if i == len(children) - 1:
                share = balance_total - allocated
            else:
                share = (balance_total * qty / total).quantize(precision)
                allocated += share
            session.add(
                InventoryBalanceProjection(
                    site_id=site_id,
                    material_lot_id=container.material_lot_id,
                    container_id=child.id,
                    location_id=source_balance.location_id,
                    on_hand=share,
                    reserved=Decimal("0"),
                    available=share,
                    version=1,
                )
            )
        source_balance.on_hand = Decimal("0")
        source_balance.reserved = Decimal("0")
        source_balance.available = Decimal("0")
        source_balance.version += 1

    container.current_quantity = Decimal("0")
    container.container_status = "split"
    container.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="material_container",
        aggregate_id=container.id,
        aggregate_version=container.version,
        action="StatusChanged",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"current_quantity": str(total), "container_status": "active"},
        new_value={"container_status": "split", "children": [str(c.id) for c, _ in children]},
    )
    await write_outbox_event(
        session,
        event_type="ContainerSplit",
        aggregate_type="material_container",
        aggregate_id=container.id,
        aggregate_version=container.version,
        payload={"container_id": str(container.id), "children": [str(c.id) for c, _ in children]},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="SplitContainer",
        aggregate_type="material_container",
        aggregate_id=container.id,
        expected_version=cmd.expected_version,
        resulting_version=container.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=container.id,
        resulting_version=container.version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# MergeContainers — INV-FR-024. Only same-lot, same-effective-status, active containers merge (spec gives
# no cross-lot merge rule beyond "material/spec/lot/status compatibility rules permit" -- same-lot-only is
# the ordinary engineering reading, since MaterialContainer's material identity is fixed by its lot FK).
# ---------------------------------------------------------------------------


class MergeContainersCommand(CommandEnvelope):
    source_container_ids: list[uuid.UUID]
    new_container_code: str


async def merge_containers(
    session: AsyncSession, cmd: MergeContainersCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if len(cmd.source_container_ids) < 2:
        raise ValidationFailedError("merge requires at least two source containers")

    containers = []
    for cid in cmd.source_container_ids:
        result = await session.execute(
            select(MaterialContainer).where(MaterialContainer.id == cid).with_for_update()
        )
        c = result.scalar_one_or_none()
        if c is None:
            raise NotFoundError("Source container not found", container_id=str(cid))
        containers.append(c)

    lot = await session.get(MaterialLot, containers[0].material_lot_id)
    if lot is None:
        raise NotFoundError("Material lot not found")
    reference_status = _effective_status(lot, containers[0])
    for c in containers:
        if c.material_lot_id != containers[0].material_lot_id:
            raise ValidationFailedError("Containers must belong to the same material lot to merge")
        if c.container_status != "active":
            raise InvalidTransitionError(
                "Only an active container can be merged", current_status=c.container_status
            )
        if _effective_status(lot, c) != reference_status:
            raise ValidationFailedError(
                "Containers must share the same effective quality status to merge (INV-FR-024)"
            )
        active_reservation = (
            await session.execute(
                select(InventoryReservation).where(
                    InventoryReservation.container_id == c.id, InventoryReservation.status == "active"
                )
            )
        ).first()
        if active_reservation is not None:
            raise ValidationFailedError(
                "Cannot merge a container with an active reservation", container_id=str(c.id)
            )

    merged_qty = sum(c.current_quantity for c in containers)
    merged = MaterialContainer(
        material_lot_id=containers[0].material_lot_id,
        container_code=cmd.new_container_code,
        received_quantity=merged_qty,
        current_quantity=merged_qty,
        uom=containers[0].uom,
        uom_id=containers[0].uom_id,  # copied from the first merged container's own already-resolved value
        location_zone=containers[0].location_zone,
        quality_status_override=containers[0].quality_status_override,
        source_container_ids={"ids": [str(c.id) for c in containers]},
        version=1,
    )
    session.add(merged)
    await session.flush()

    for c in containers:
        balances = (
            await session.execute(
                select(InventoryBalanceProjection)
                .where(InventoryBalanceProjection.container_id == c.id)
                .with_for_update()
            )
        ).scalars().all()
        for b in balances:
            target = await _lock_or_create_balance(
                session,
                site_id=site_id,
                material_lot_id=merged.material_lot_id,
                container_id=merged.id,
                location_id=b.location_id,
            )
            target.on_hand += b.on_hand
            target.reserved += b.reserved
            target.available += b.available
            target.version += 1
            b.on_hand = Decimal("0")
            b.reserved = Decimal("0")
            b.available = Decimal("0")
            b.version += 1
        c.current_quantity = Decimal("0")
        c.container_status = "merged"
        c.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="material_container",
        aggregate_id=merged.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"sources": [str(c.id) for c in containers], "quantity": str(merged_qty)},
    )
    await write_outbox_event(
        session,
        event_type="ContainerMerged",
        aggregate_type="material_container",
        aggregate_id=merged.id,
        aggregate_version=1,
        payload={"merged_container_id": str(merged.id), "sources": [str(c.id) for c in containers]},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="MergeContainers",
        aggregate_type="material_container",
        aggregate_id=merged.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=merged.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CreateCycleCount — INV-FR-020/022. No Document 106 row resolves an "adjustment approval" signature
# despite the spec's own prose implying one -- built unsigned/RBAC-gated only (SG-084), matching this
# project's hard "no Document 106 row = unsigned" precedent rather than guessing a role/meaning.
# ---------------------------------------------------------------------------


class CreateCycleCountCommand(CommandEnvelope):
    material_lot_id: uuid.UUID
    container_id: uuid.UUID | None = None
    location_id: uuid.UUID
    counted_quantity: Decimal
    reason: str | None = None


async def create_cycle_count(
    session: AsyncSession, cmd: CreateCycleCountCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.counted_quantity < 0:
        raise ValidationFailedError("counted_quantity cannot be negative (INV-FR-022)")

    balance = await _lock_or_create_balance(
        session,
        site_id=site_id,
        material_lot_id=cmd.material_lot_id,
        container_id=cmd.container_id,
        location_id=cmd.location_id,
    )

    old_on_hand = balance.on_hand
    delta = cmd.counted_quantity - old_on_hand
    txn = None
    if delta != 0:
        new_available = balance.available + delta
        if new_available < 0:
            raise ValidationFailedError(
                "Counted quantity is less than the quantity currently reserved at this location",
                available_after_count=str(new_available),
            )
        txn = InventoryTransaction(
            site_id=site_id,
            material_lot_id=cmd.material_lot_id,
            container_id=cmd.container_id,
            transaction_type="ADJUST_POSITIVE" if delta > 0 else "ADJUST_NEGATIVE",
            quantity=abs(delta),
            uom="unit",
            uom_id=await _resolve_uom_id(session, "unit"),
            to_location_id=cmd.location_id if delta > 0 else None,
            from_location_id=cmd.location_id if delta < 0 else None,
            reference_type="cycle_count",
            actor_type="human",
            actor_id=str(actor_user_id),
        )
        session.add(txn)
        await session.flush()
        balance.on_hand = cmd.counted_quantity
        balance.available = new_available
        balance.last_transaction_id = txn.id
        balance.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="inventory_balance_projection",
        aggregate_id=balance.id,
        aggregate_version=balance.version,
        action="Adjusted" if delta != 0 else "Counted",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"on_hand": str(old_on_hand)},
        new_value={"on_hand": str(balance.on_hand), "delta": str(delta)},
        reason=cmd.reason,
    )
    await write_outbox_event(
        session,
        event_type="InventoryAdjusted" if delta != 0 else "InventoryCounted",
        aggregate_type="inventory_balance_projection",
        aggregate_id=balance.id,
        aggregate_version=balance.version,
        payload={"balance_id": str(balance.id), "delta": str(delta)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="CreateCycleCount",
        aggregate_type="inventory_balance_projection",
        aggregate_id=balance.id,
        expected_version=None,
        resulting_version=balance.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=balance.id,
        resulting_version=balance.version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Read-only: ledger (INV-FR-029/030) and ERP reconciliation (INV-FR-028 — GxP side only, no ERP
# integration exists, WP-07 not built, SG-082).
# ---------------------------------------------------------------------------


async def get_erp_reconciliation(session: AsyncSession, lot_id: uuid.UUID) -> dict:
    lot = await session.get(MaterialLot, lot_id)
    if lot is None:
        raise NotFoundError("Material lot not found")
    balances = (
        await session.execute(
            select(InventoryBalanceProjection).where(InventoryBalanceProjection.material_lot_id == lot.id)
        )
    ).scalars().all()
    gxp_on_hand = sum((b.on_hand for b in balances), Decimal("0"))
    return {
        "material_lot_id": str(lot.id),
        "internal_lot": lot.internal_lot,
        "gxp_on_hand": str(gxp_on_hand),
        # INV-FR-028: mismatches are flagged, never auto-resolved by overwriting the GxP ledger. No ERP
        # integration exists in this codebase (WP-07, not built) -- the ERP side is deliberately null, not
        # guessed (SG-082), rather than a fabricated comparison value.
        "erp_source_configured": False,
        "erp_on_hand": None,
        "mismatch_flagged": None,
    }


# ---------------------------------------------------------------------------
# Document 21 (SPEC-MAT-002C) — Material Dispensing & Weighing.
#
# Order creation (POST /dispensing/v1/orders, Document 106 row 47) is the first signed-by-Document-106
# *create* operation in this codebase — every other signed action mutates an already-existing aggregate,
# because Document 04's ceremony binds to an existing record id/version/hash and every command here lets
# the server mint the aggregate id. Building a challenge-binding scheme for a not-yet-existent record would
# be a signature-architecture guess (SG-087) -- create_dispensing_order is unsigned/RBAC-gated; the other 7
# mutating operations (all acting on an already-created order) get full real signing via `_dispensing_sign`.
# ---------------------------------------------------------------------------


def dispensing_order_record_hash(order: DispensingOrder) -> str:
    return sha256_hex({"id": str(order.id), "version": order.version, "state": order.state})


async def _dispensing_sign(
    session: AsyncSession,
    *,
    actor_user_id: uuid.UUID,
    action: str,
    order: DispensingOrder,
    challenge_id: uuid.UUID,
    reauth_password: str,
    reason: str | None = None,
) -> uuid.UUID | None:
    """Shared challenge-consume-sign ceremony for the 7 signed dispensing_order actions (Document 106 rows
    48-54) -- same three-call sequence every other signed command in this module already uses."""
    policy = await signature_service.resolve_signature_requirement(
        session, record_type="dispensing_order", action=action
    )
    if policy.reason_required and not reason:
        raise ValidationFailedError(f"reason is required for the '{action}' dispensing action")
    if not policy.signature_required:
        return None
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session,
        challenge_id=challenge_id,
        user_id=actor_user_id,
        record_version=order.version,
        record_hash=dispensing_order_record_hash(order),
    )
    signature = await signature_service.sign(
        session, challenge=challenge, auth_context={"method": "password_reauth"}
    )
    return signature.id


async def _check_dispensing_qualification(session: AsyncSession, user_id: uuid.UUID) -> None:
    """DSP-FR-005: `iam.Qualification` (Document 07 / IAM-FR-010's own authoritative execution-time
    qualification gate -- "Execution checks qualification at action time, not only at login") is enforced
    by zero commands anywhere else in this codebase — first real wiring, not a retrofit of other modules.
    Document 07 declares distinct QUALIFICATION_MISSING (no record) and QUALIFICATION_EXPIRED (lapsed
    record) error codes."""
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(Qualification)
        .where(Qualification.user_id == user_id, Qualification.qualification_code == "dispensing_operator")
        .order_by(Qualification.granted_at.desc())
        .limit(1)
    )
    qualification = result.scalar_one_or_none()
    if qualification is None:
        raise QualificationMissingError(
            "Actor has no dispensing_operator qualification record", qualification_code="dispensing_operator"
        )
    if qualification.expires_at is not None and qualification.expires_at.replace(tzinfo=timezone.utc) < now:
        raise QualificationExpiredError(
            "Actor's dispensing_operator qualification has expired", qualification_code="dispensing_operator"
        )


async def _load_dispensing_order_for_update(session: AsyncSession, order_id: uuid.UUID) -> DispensingOrder:
    result = await session.execute(
        select(DispensingOrder).where(DispensingOrder.id == order_id).with_for_update()
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise NotFoundError("Dispensing order not found")
    return order


def _assert_dispensing_version(order: DispensingOrder, expected_version: int) -> None:
    if order.version != expected_version:
        raise StaleVersionError(
            "Dispensing order was modified by another actor since it was read",
            expected_version=expected_version,
            current_version=order.version,
        )


# ---------------------------------------------------------------------------
# CreateDispensingOrder — DSP-FR-001. Unsigned (SG-087). target_qty/tolerance_low/tolerance_high are
# caller-supplied captured values -- no target-calculation or tolerance-rule execution mode exists
# anywhere in this codebase (SG-089), only the rules engine's PASS/FAIL gate evaluation.
# ---------------------------------------------------------------------------


class CreateDispensingOrderCommand(CommandEnvelope):
    site_id: uuid.UUID
    batch_id: uuid.UUID
    batch_step_id: uuid.UUID | None = None
    material_id: uuid.UUID
    material_spec_version_id: uuid.UUID | None = None
    target_qty: Decimal
    target_uom: str
    tolerance_low: Decimal
    tolerance_high: Decimal


async def create_dispensing_order(
    session: AsyncSession, cmd: CreateDispensingOrderCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.target_qty <= 0:
        raise ValidationFailedError("target_qty must be positive")
    if cmd.tolerance_low > cmd.tolerance_high:
        raise ValidationFailedError("tolerance_low must not exceed tolerance_high")

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")
    material = await session.get(Material, cmd.material_id)
    if material is None:
        raise NotFoundError("Material not found")

    order = DispensingOrder(
        site_id=cmd.site_id,
        batch_id=cmd.batch_id,
        batch_step_id=cmd.batch_step_id,
        material_id=cmd.material_id,
        material_spec_version_id=cmd.material_spec_version_id,
        target_qty=cmd.target_qty,
        target_uom=cmd.target_uom,
        target_uom_id=await _resolve_uom_id(session, cmd.target_uom),
        tolerance_low=cmd.tolerance_low,
        tolerance_high=cmd.tolerance_high,
        state="created",
        requested_by_user_id=actor_user_id,
        version=1,
    )
    session.add(order)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.site_id,
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"material_id": str(cmd.material_id), "target_qty": str(cmd.target_qty)},
    )
    await write_outbox_event(
        session,
        event_type="DispensingOrderCreated",
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        aggregate_version=1,
        payload={"id": str(order.id), "batch_id": str(cmd.batch_id), "material_id": str(cmd.material_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="CreateDispensingOrder",
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=order.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# SelectDispensingSource — DSP-FR-002/003/017. Signed (row 52, Performed, Dispensing Operator). Reuses
# Document 20's `_is_eligible`/`_effective_status`; `scanned_container_code` -- when supplied -- is
# verified by server lookup, never trusted as-is (Document 21's own Codex rule).
# ---------------------------------------------------------------------------


class SelectDispensingSourceCommand(CommandEnvelope):
    expected_version: int
    material_lot_id: uuid.UUID | None = None
    container_id: uuid.UUID | None = None
    reservation_id: uuid.UUID | None = None
    scanned_container_code: str | None = None
    quantity: Decimal
    challenge_id: uuid.UUID
    reauth_password: str


async def select_dispensing_source(
    session: AsyncSession,
    order_id: uuid.UUID,
    cmd: SelectDispensingSourceCommand,
    actor_user_id: uuid.UUID,
    site_id: uuid.UUID,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    order = await _load_dispensing_order_for_update(session, order_id)
    _assert_dispensing_version(order, cmd.expected_version)
    # DSP-FR-017 multi-lot dispensing: select-source may be called repeatedly while the order hasn't
    # started, each call adding one more dispensing_source row -- "source_selected" is itself a valid
    # state to select an *additional* source from, not just "created".
    if order.state not in ("created", "source_selected"):
        raise InvalidTransitionError(
            "Source can only be selected before dispensing has started", current_status=order.state
        )
    if cmd.quantity <= 0:
        raise ValidationFailedError("quantity must be positive")

    await evaluate_policy(session, actor_user_id, action="dispensing_order.select_source", site_id=site_id)

    today = datetime.now(timezone.utc).date()
    reservation = None
    if cmd.reservation_id is not None:
        reservation = await session.get(InventoryReservation, cmd.reservation_id)
        if reservation is None or reservation.status != "active":
            raise LotIneligibleError("Reservation is not active", reservation_id=str(cmd.reservation_id))
        if reservation.material_id != order.material_id or reservation.batch_id != order.batch_id:
            raise WrongMaterialError("Reservation does not match this order's material/batch")
        if cmd.quantity > reservation.quantity:
            raise SourceQuantityInsufficientError(
                "Requested quantity exceeds the reservation", reserved=str(reservation.quantity)
            )
        lot = await session.get(MaterialLot, reservation.material_lot_id)
        container = (
            await session.get(MaterialContainer, reservation.container_id) if reservation.container_id else None
        )
    elif cmd.material_lot_id is not None:
        lot = await session.get(MaterialLot, cmd.material_lot_id)
        if lot is None:
            raise NotFoundError("Material lot not found")
        if lot.material_id != order.material_id:
            raise WrongMaterialError("Selected lot does not match this order's material")
        container = await session.get(MaterialContainer, cmd.container_id) if cmd.container_id else None
        if container is not None and container.material_lot_id != lot.id:
            raise ContainerIneligibleError("Selected container does not belong to the selected lot")
        balances = (
            await session.execute(
                select(InventoryBalanceProjection).where(
                    InventoryBalanceProjection.material_lot_id == lot.id,
                    InventoryBalanceProjection.container_id == (container.id if container else None),
                )
            )
        ).scalars().all()
        total_available = sum((b.available for b in balances), Decimal("0"))
        if total_available < cmd.quantity:
            raise SourceQuantityInsufficientError(
                "Insufficient available quantity for this lot/container", available=str(total_available)
            )
    else:
        raise ValidationFailedError("either reservation_id or material_lot_id must be supplied")

    if not _is_eligible(lot, container, today):
        raise LotIneligibleError("Selected lot/container is not eligible", current_status=_effective_status(lot, container))
    if cmd.scanned_container_code is not None and container is not None:
        if cmd.scanned_container_code != container.container_code:
            raise WrongMaterialError("Scanned container code does not match the selected container")

    source = DispensingSource(
        dispensing_order_id=order.id,
        material_lot_id=lot.id,
        container_id=container.id if container else None,
        reservation_id=cmd.reservation_id,
        reserved_quantity=cmd.quantity,
        eligibility_snapshot={"status": _effective_status(lot, container), "evaluated_at": today.isoformat()},
    )
    session.add(source)
    await session.flush()

    # Sign against the pristine pre-transition state/version -- the challenge was created against it,
    # and the record hash embeds both state and version (same ordering every signed command in this
    # module uses: consume the challenge before mutating the aggregate it was bound to).
    signature_id = await _dispensing_sign(
        session, actor_user_id=actor_user_id, action="select_source", order=order,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = order.state
    order.state = "source_selected"
    order.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        aggregate_version=order.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"state": old_state},
        new_value={"state": order.state, "source_id": str(source.id)},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="DispensingSourceSelected",
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        aggregate_version=order.version,
        payload={"order_id": str(order.id), "source_id": str(source.id), "lot_id": str(lot.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="SelectDispensingSource",
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        expected_version=cmd.expected_version,
        resulting_version=order.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=order.id,
        resulting_version=order.version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# StartDispensing — DSP-FR-004/005/006(partial)/007/026(partial). Signed (row 53, Performed, no
# independence). Wires up `iam.Qualification` for real (DSP-FR-005) -- dormant everywhere else in this
# codebase. Booth *status* reuses `warehouse_locations.status`; environmental *condition* itself is the
# WP-06 gap (SG-088).
# ---------------------------------------------------------------------------


class StartDispensingCommand(CommandEnvelope):
    expected_version: int
    booth_location_id: uuid.UUID | None = None
    tare_method: str | None = None
    tare_value: Decimal | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def start_dispensing(
    session: AsyncSession, order_id: uuid.UUID, cmd: StartDispensingCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    order = await _load_dispensing_order_for_update(session, order_id)
    _assert_dispensing_version(order, cmd.expected_version)
    if order.state != "source_selected":
        raise InvalidTransitionError("Dispensing can only start after a source is selected", current_status=order.state)

    await evaluate_policy(session, actor_user_id, action="dispensing_order.start", site_id=site_id)
    await _check_dispensing_qualification(session, actor_user_id)

    if cmd.booth_location_id is not None:
        location = await session.get(WarehouseLocation, cmd.booth_location_id)
        if location is None:
            raise NotFoundError("Booth/dispensing location not found")
        if location.status != "active":
            raise InvalidTransitionError("Booth/dispensing location is not active", current_status=location.status)

    weighing = WeighingSession(
        dispensing_order_id=order.id,
        operator_user_id=actor_user_id,
        booth_location_id=cmd.booth_location_id,
        tare_method=cmd.tare_method,
        tare_value=cmd.tare_value,
        version=1,
    )
    session.add(weighing)
    await session.flush()

    signature_id = await _dispensing_sign(
        session, actor_user_id=actor_user_id, action="start", order=order,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = order.state
    order.state = "started"
    order.performed_by_user_id = actor_user_id
    order.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        aggregate_version=order.version,
        action="StatusChanged",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"state": old_state},
        new_value={"state": order.state, "weighing_session_id": str(weighing.id)},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="DispensingStarted",
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        aggregate_version=order.version,
        payload={"order_id": str(order.id), "weighing_session_id": str(weighing.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="StartDispensing",
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        expected_version=cmd.expected_version,
        resulting_version=order.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=order.id,
        resulting_version=order.version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# RecordReading / RecordManualReading — DSP-FR-009/010/011/013/014. Every reading is kept, including an
# unstable or later-corrected overweight one (append-only, DSP-FR-014 "original overweight reading
# retained" — never hides a failed reading per Document 21's own Codex rule). `source='device'` on the
# `readings` endpoint is captured, not verified — no Edge/Balance adapter exists (SG-088).
# ---------------------------------------------------------------------------


async def _record_reading(
    session: AsyncSession,
    order_id: uuid.UUID,
    *,
    idempotency_key: str,
    payload_hash: str,
    expected_version: int,
    reading_value: Decimal,
    uom: str,
    stable: bool,
    source: str,
    manual_reason: str | None,
    device_id: str | None,
    action: str,
    event_type: str,
    command_type: str,
    challenge_id: uuid.UUID,
    reauth_password: str,
    actor_user_id: uuid.UUID,
    site_id: uuid.UUID,
) -> MutationReceipt:
    existing = await check_idempotency(session, idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    order = await _load_dispensing_order_for_update(session, order_id)
    _assert_dispensing_version(order, expected_version)
    if order.state != "started":
        raise InvalidTransitionError("Readings can only be recorded while dispensing is in progress", current_status=order.state)
    if reading_value < 0:
        raise ValidationFailedError("reading_value cannot be negative")
    if source == "manual" and not manual_reason:
        raise ValidationFailedError("manual_reason is required for a manual reading (DSP-FR-011)")

    await evaluate_policy(session, actor_user_id, action=f"dispensing_order.{action}", site_id=site_id)

    weighing = (
        await session.execute(
            select(WeighingSession).where(WeighingSession.dispensing_order_id == order.id).with_for_update()
        )
    ).scalar_one_or_none()
    if weighing is None:
        raise NotFoundError("Weighing session not found")

    sequence = (
        await session.execute(
            select(WeighingReading).where(WeighingReading.weighing_session_id == weighing.id)
        )
    ).scalars().all()
    next_sequence = len(sequence) + 1

    reading = WeighingReading(
        weighing_session_id=weighing.id,
        sequence=next_sequence,
        reading_value=reading_value,
        uom=uom,
        uom_id=await _resolve_uom_id(session, uom),
        stable=stable,
        source=source,
        manual_reason=manual_reason,
        device_id=device_id,
        recorded_by_user_id=actor_user_id,
        accepted=stable,
    )
    session.add(reading)
    await session.flush()

    if stable:
        accepted_total = sum(
            (r.reading_value for r in sequence if r.accepted), Decimal("0")
        ) + reading_value
        weighing.final_accepted_net = accepted_total
    weighing.version += 1

    signature_id = await _dispensing_sign(
        session, actor_user_id=actor_user_id, action=action, order=order,
        challenge_id=challenge_id, reauth_password=reauth_password,
    )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="weighing_session",
        aggregate_id=weighing.id,
        aggregate_version=weighing.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"reading_id": str(reading.id), "value": str(reading_value), "stable": stable, "source": source},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type=event_type,
        aggregate_type="weighing_session",
        aggregate_id=weighing.id,
        aggregate_version=weighing.version,
        payload={"order_id": str(order.id), "reading_id": str(reading.id), "stable": stable},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type=command_type,
        aggregate_type="weighing_session",
        aggregate_id=weighing.id,
        expected_version=expected_version,
        resulting_version=weighing.version,
        idempotency_key=idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=weighing.id,
        resulting_version=weighing.version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


class RecordReadingCommand(CommandEnvelope):
    expected_version: int
    reading_value: Decimal
    uom: str
    stable: bool
    device_id: str | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def record_reading(
    session: AsyncSession, order_id: uuid.UUID, cmd: RecordReadingCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    return await _record_reading(
        session, order_id,
        idempotency_key=cmd.idempotency_key, payload_hash=payload_hash, expected_version=cmd.expected_version,
        reading_value=cmd.reading_value, uom=cmd.uom, stable=cmd.stable, source="device",
        manual_reason=None, device_id=cmd.device_id, action="readings", event_type="WeighingReadingAccepted",
        command_type="RecordReading", challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
        actor_user_id=actor_user_id, site_id=site_id,
    )


class RecordManualReadingCommand(CommandEnvelope):
    expected_version: int
    reading_value: Decimal
    uom: str
    stable: bool
    manual_reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def record_manual_reading(
    session: AsyncSession, order_id: uuid.UUID, cmd: RecordManualReadingCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    return await _record_reading(
        session, order_id,
        idempotency_key=cmd.idempotency_key, payload_hash=payload_hash, expected_version=cmd.expected_version,
        reading_value=cmd.reading_value, uom=cmd.uom, stable=cmd.stable, source="manual",
        manual_reason=cmd.manual_reason, device_id=None, action="manual_reading",
        event_type="WeighingReadingAccepted", command_type="RecordManualReading",
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
        actor_user_id=actor_user_id, site_id=site_id,
    )


# ---------------------------------------------------------------------------
# VerifyDispensing — DSP-FR-018. Signed (row 54, Verified, MUST NOT be the performer — real, enforceable:
# verifier != dispensing_order.performed_by_user_id, same independence-check shape used twice already in
# this module). Verification is optional per DSP-FR-018 ("where required") — complete() accepts either
# 'started' or 'verified'.
# ---------------------------------------------------------------------------


class VerifyDispensingCommand(CommandEnvelope):
    expected_version: int
    challenge_id: uuid.UUID
    reauth_password: str


async def verify_dispensing(
    session: AsyncSession, order_id: uuid.UUID, cmd: VerifyDispensingCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    order = await _load_dispensing_order_for_update(session, order_id)
    _assert_dispensing_version(order, cmd.expected_version)
    if order.state != "started":
        raise InvalidTransitionError("Only an in-progress dispense can be verified", current_status=order.state)

    await evaluate_policy(session, actor_user_id, action="dispensing_order.verify", site_id=site_id)
    if order.performed_by_user_id is not None and actor_user_id == order.performed_by_user_id:
        raise VerifierRequiredError("Verifier must not be the performer of this dispensing operation")

    signature_id = await _dispensing_sign(
        session, actor_user_id=actor_user_id, action="verify", order=order,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = order.state
    order.state = "verified"
    order.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        aggregate_version=order.version,
        action="Approved",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"state": old_state},
        new_value={"state": order.state},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="DispensingVerified",
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        aggregate_version=order.version,
        payload={"order_id": str(order.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="VerifyDispensing",
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        expected_version=cmd.expected_version,
        resulting_version=order.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=order.id,
        resulting_version=order.version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CompleteDispensing — DSP-FR-012/017/019/022/023(partial)/024/025. Signed (row 49, Performed). Reuses
# Document 20's inventory ledger directly: writes a DISPENSE `inventory_transaction` per source and
# decrements the matching `inventory_balance_projection`, exactly the infrastructure INV-FR-006/007
# already built. Tolerance evaluation blocks completion when outside [tolerance_low, tolerance_high]
# (spec's own rule) rather than creating a separate exception record — no exception/deviation entity
# exists to record into (same root cause as SG-083's missing deviation entity), so an out-of-tolerance
# attempt is rejected like any other validation failure, not silently allowed through.
# ---------------------------------------------------------------------------


class CompleteDispensingCommand(CommandEnvelope):
    expected_version: int
    actual_taken_quantities: dict[str, Decimal]  # dispensing_source_id (str) -> quantity taken
    container_code: str
    challenge_id: uuid.UUID
    reauth_password: str


async def complete_dispensing(
    session: AsyncSession, order_id: uuid.UUID, cmd: CompleteDispensingCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    order = await _load_dispensing_order_for_update(session, order_id)
    _assert_dispensing_version(order, cmd.expected_version)
    if order.state not in ("started", "verified"):
        raise InvalidTransitionError("Dispensing is not ready to complete", current_status=order.state)

    await evaluate_policy(session, actor_user_id, action="dispensing_order.complete", site_id=site_id)

    sources = (
        await session.execute(
            select(DispensingSource).where(DispensingSource.dispensing_order_id == order.id)
        )
    ).scalars().all()
    if not sources:
        raise ValidationFailedError("No source has been selected for this order")

    today = datetime.now(timezone.utc).date()
    total_taken = Decimal("0")
    for source in sources:
        qty = cmd.actual_taken_quantities.get(str(source.id))
        if qty is None or qty <= 0:
            raise ValidationFailedError("actual_taken_quantities must include a positive value for every source", source_id=str(source.id))

        lot = await session.get(MaterialLot, source.material_lot_id)
        container = await session.get(MaterialContainer, source.container_id) if source.container_id else None
        if not _is_eligible(lot, container, today):
            raise LotIneligibleError("Source lot is no longer eligible at completion time (DSP-FR-025)", lot_id=str(lot.id))

        balance = (
            await session.execute(
                select(InventoryBalanceProjection)
                .where(
                    InventoryBalanceProjection.material_lot_id == lot.id,
                    InventoryBalanceProjection.container_id == (container.id if container else None),
                    InventoryBalanceProjection.available >= qty,
                )
                .with_for_update()
            )
        ).scalars().first()
        if balance is None:
            raise SourceQuantityInsufficientError(
                "No location holds sufficient available quantity for this source", source_id=str(source.id)
            )

        reservation_qty = Decimal("0")
        if source.reservation_id is not None:
            reservation = (
                await session.execute(
                    select(InventoryReservation).where(InventoryReservation.id == source.reservation_id).with_for_update()
                )
            ).scalar_one_or_none()
            if reservation is not None and reservation.status == "active":
                reservation_qty = min(reservation.quantity, qty)
                reservation.status = "consumed"
                reservation.released_by_user_id = actor_user_id
                reservation.released_at = datetime.now(timezone.utc)
                reservation.version += 1

        balance.on_hand -= qty
        balance.available -= (qty - reservation_qty)
        balance.reserved -= reservation_qty
        balance.version += 1

        txn = InventoryTransaction(
            site_id=site_id,
            material_lot_id=lot.id,
            container_id=container.id if container else None,
            transaction_type="DISPENSE",
            quantity=qty,
            uom=order.target_uom,
            uom_id=order.target_uom_id,  # copied from the order's own already-resolved value
            from_location_id=balance.location_id,
            reference_type="dispensing_order",
            reference_id=order.id,
            actor_type="human",
            actor_id=str(actor_user_id),
        )
        session.add(txn)
        await session.flush()
        balance.last_transaction_id = txn.id

        source.actual_taken_quantity = qty
        total_taken += qty

    if not (order.tolerance_low <= total_taken <= order.tolerance_high):
        raise WeightOutOfToleranceError(
            "Total dispensed quantity is outside the released tolerance",
            target=str(order.target_qty), actual=str(total_taken),
            tolerance_low=str(order.tolerance_low), tolerance_high=str(order.tolerance_high),
        )

    dispensed = DispensedContainer(
        batch_id=order.batch_id,
        material_id=order.material_id,
        dispensing_order_id=order.id,
        container_code=cmd.container_code,
        actual_quantity=total_taken,
        uom=order.target_uom,
        uom_id=order.target_uom_id,  # copied from the order's own already-resolved value
        status="active",
        # CON-FR-004 (Document 22 session): remaining_quantity starts equal to what was actually taken --
        # the column default of 0 is only correct for a container nothing has ever been dispensed into.
        remaining_quantity=total_taken,
        version=1,
    )
    session.add(dispensed)
    await session.flush()

    signature_id = await _dispensing_sign(
        session, actor_user_id=actor_user_id, action="complete", order=order,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = order.state
    order.state = "completed"
    order.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        aggregate_version=order.version,
        action="Consumed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"state": old_state},
        new_value={"state": order.state, "dispensed_container_id": str(dispensed.id), "total_taken": str(total_taken)},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="MaterialDispensed",
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        aggregate_version=order.version,
        payload={"order_id": str(order.id), "dispensed_container_id": str(dispensed.id), "quantity": str(total_taken)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="CompleteDispensing",
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        expected_version=cmd.expected_version,
        resulting_version=order.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=order.id,
        resulting_version=order.version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CancelDispensing — DSP-FR-030. Signed (row 48, Approved, MUST be independent of the author, reason
# required — this is the one Document 21 row where `reason_required=True`, matching Document 106's own
# Reason column, wired correctly from the start unlike the pre-existing rows SG-086 describes). Returns
# any active reservation via the same reversal Document 20's `release_inventory_reservation` performs.
# ---------------------------------------------------------------------------


class CancelDispensingCommand(CommandEnvelope):
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def cancel_dispensing(
    session: AsyncSession, order_id: uuid.UUID, cmd: CancelDispensingCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    order = await _load_dispensing_order_for_update(session, order_id)
    _assert_dispensing_version(order, cmd.expected_version)
    if order.state in ("completed", "cancelled"):
        raise InvalidTransitionError("Order is already terminal", current_status=order.state)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to cancel a dispensing order")

    await evaluate_policy(session, actor_user_id, action="dispensing_order.cancel", site_id=site_id)
    if actor_user_id == order.requested_by_user_id:
        raise ValidationFailedError("Canceller must be independent of the author of this order")

    sources = (
        await session.execute(
            select(DispensingSource).where(DispensingSource.dispensing_order_id == order.id)
        )
    ).scalars().all()
    for source in sources:
        if source.reservation_id is None:
            continue
        reservation = (
            await session.execute(
                select(InventoryReservation).where(InventoryReservation.id == source.reservation_id).with_for_update()
            )
        ).scalar_one_or_none()
        if reservation is None or reservation.status != "active":
            continue
        balance = (
            await session.execute(
                select(InventoryBalanceProjection)
                .where(
                    InventoryBalanceProjection.material_lot_id == reservation.material_lot_id,
                    InventoryBalanceProjection.container_id == reservation.container_id,
                    InventoryBalanceProjection.location_id == reservation.location_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if balance is not None:
            balance.reserved -= reservation.quantity
            balance.available += reservation.quantity
            balance.version += 1
        reservation.status = "released"
        reservation.released_by_user_id = actor_user_id
        reservation.released_at = datetime.now(timezone.utc)
        reservation.version += 1

    signature_id = await _dispensing_sign(
        session, actor_user_id=actor_user_id, action="cancel", order=order,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password, reason=cmd.reason,
    )

    old_state = order.state
    order.state = "cancelled"
    order.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        aggregate_version=order.version,
        action="StatusChanged",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"state": old_state},
        new_value={"state": order.state},
        signature_id=signature_id,
        reason=cmd.reason,
    )
    await write_outbox_event(
        session,
        event_type="DispensingCancelled",
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        aggregate_version=order.version,
        payload={"order_id": str(order.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="CancelDispensing",
        aggregate_type="dispensing_order",
        aggregate_id=order.id,
        expected_version=cmd.expected_version,
        resulting_version=order.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=order.id,
        resulting_version=order.version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Document 22 (SPEC-MAT-002D) — Material Consumption, Return, Adjustment, Destruction & Reconciliation.
# Extends the post-dispensing lifecycle: every CONSUME/RETURN/SAMPLE/REJECT/SPILL/APPROVED_LOSS/DESTROY/
# ADJUST_* ledger movement reuses Document 20's InventoryTransaction/InventoryBalanceProjection machinery
# (_lock_or_create_balance) and Document 21's DispensedContainer -- the only new balance-tracking shape is
# `dispensed_containers.remaining_quantity` (this session), mutated the same way Document 18/19 already
# mutates `MaterialContainer.current_quantity` directly.
#
# SG-098 (this session): (a) CON-FR-003's automatic/validated-integration consumption source does not
# exist (no edge/rules-engine source, WP-06 not built) -- manual capture only; (b) CON-FR-021's tolerance
# is caller-supplied captured input, not a released Document 08/17 rule (Document 17 is not built in this
# codebase, same treatment SG-094 already established for dispensing tolerance); (c) CON-FR-022/028's
# auto-deviation severity/owner is caller-supplied, and the actual block on batch Production Complete is
# NOT wired into app/modules/batch/commands.py this pass (cross-module gate, same class of decision as the
# SCAR/supplier-suspension SPEC_GAP already on file); (d) CON-FR-025/026 ERP posting has no integration
# (WP-07 not built, same root cause as SG-077/082) -- get_material_reconciliation reports a fixed
# "not_integrated" status.
# ---------------------------------------------------------------------------

LOSS_TRANSACTION_TYPES = ("SAMPLE", "REJECT", "SPILL", "APPROVED_LOSS")
_SIX_DP = Decimal("0.000001")
_TWO_DP = Decimal("0.01")


def inventory_adjustment_request_record_hash(request: InventoryAdjustmentRequest) -> str:
    return sha256_hex({"id": str(request.id), "version": request.version, "status": request.status})


def destruction_record_hash(record: DestructionRecord) -> str:
    return sha256_hex({"id": str(record.id), "version": record.version, "status": record.status})


async def _material_sign(
    session: AsyncSession,
    *,
    record_type: str,
    action: str,
    actor_user_id: uuid.UUID,
    record_version: int,
    record_hash: str,
    challenge_id: uuid.UUID | None,
    reauth_password: str | None,
    reason: str | None = None,
) -> uuid.UUID | None:
    """Shared challenge-consume-sign ceremony for the two Document 106 signed Document 22 actions (rows
    55/56) -- same three-call sequence `_dispensing_sign` (Document 21) and `_disposition_material_lot_v2`
    (Document 19) already use. Called BEFORE the caller mutates its aggregate: the challenge is bound to
    the pre-mutation version/hash (Document 21's session hit the real bug of getting this order wrong)."""
    policy = await signature_service.resolve_signature_requirement(session, record_type=record_type, action=action)
    if policy.reason_required and not reason:
        raise ValidationFailedError(f"reason is required for the '{record_type}.{action}' action")
    if not policy.signature_required:
        return None
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError("This action requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session,
        challenge_id=challenge_id,
        user_id=actor_user_id,
        record_version=record_version,
        record_hash=record_hash,
    )
    signature = await signature_service.sign(
        session, challenge=challenge, auth_context={"method": "password_reauth"}
    )
    return signature.id


async def _lock_dispensed_container(session: AsyncSession, container_id: uuid.UUID) -> DispensedContainer:
    result = await session.execute(
        select(DispensedContainer).where(DispensedContainer.id == container_id).with_for_update()
    )
    container = result.scalar_one_or_none()
    if container is None:
        raise NotFoundError("Dispensed container not found", dispensed_container_id=str(container_id))
    return container


async def _resolve_consumption_lot(
    session: AsyncSession, container: DispensedContainer, requested_lot_id: uuid.UUID | None
) -> uuid.UUID:
    """DSP-FR-017 multi-lot dispensing means a dispensed container can have more than one source lot; a
    CONSUME/RETURN/loss/DESTROY movement against the container as a whole needs exactly one lot to
    attribute the ledger row to (InventoryTransaction.material_lot_id is NOT NULL). Single-source
    containers resolve automatically; multi-source containers require the caller to name one of the
    actual sources."""
    sources = (
        await session.execute(
            select(DispensingSource.material_lot_id)
            .where(DispensingSource.dispensing_order_id == container.dispensing_order_id)
            .distinct()
        )
    ).scalars().all()
    if requested_lot_id is not None:
        if requested_lot_id not in sources:
            raise ValidationFailedError(
                "material_lot_id is not one of this dispensed container's source lots",
                material_lot_id=str(requested_lot_id),
            )
        return requested_lot_id
    if len(sources) == 1:
        return sources[0]
    if not sources:
        raise ValidationFailedError(
            "Dispensed container has no recorded source lot", dispensed_container_id=str(container.id)
        )
    raise ValidationFailedError(
        "This dispensed container has multiple source lots -- material_lot_id must be specified",
        source_lot_ids=[str(s) for s in sources],
    )


def _mark_container_status_after_movement(container: DispensedContainer) -> None:
    """CON-FR-004: resulting status is derived from `remaining_quantity`, never taken from caller input
    (no client-asserted status)."""
    if container.remaining_quantity <= 0:
        container.status = "consumed"
    elif container.remaining_quantity < container.actual_quantity:
        container.status = "partially_consumed"


# ---------------------------------------------------------------------------
# RecordConsumption — CON-FR-001/002/003(manual)/004/027/031. POST /materials/v1/consumptions.
# Unsigned (no Document 106 row) -- RBAC/qualification-gated only, same as create_dispensing_order.
# ---------------------------------------------------------------------------


class RecordConsumptionCommand(CommandEnvelope):
    batch_id: uuid.UUID
    step_id: uuid.UUID | None = None
    dispensed_container_id: uuid.UUID
    material_lot_id: uuid.UUID | None = None
    quantity: Decimal
    uom: str
    source_type: str = "manual"
    source_id: str | None = None


async def record_consumption(
    session: AsyncSession, cmd: RecordConsumptionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.quantity <= 0:
        raise ValidationFailedError("quantity must be positive")
    if cmd.source_type not in ("manual", "automatic"):
        raise ValidationFailedError("source_type must be 'manual' or 'automatic'")
    if cmd.source_type == "automatic":
        # CON-FR-003 (SG-098): no validated integration/rules-engine source exists in this codebase.
        raise ValidationFailedError("Automatic consumption source is not available in this build (SG-098)")

    container = await _lock_dispensed_container(session, cmd.dispensed_container_id)
    if container.batch_id != cmd.batch_id:
        raise BatchMismatchError(
            "Dispensed container belongs to a different batch (CON-FR-031)",
            container_batch_id=str(container.batch_id),
            requested_batch_id=str(cmd.batch_id),
        )
    if container.status in ("consumed", "returned", "destroyed"):
        raise InvalidTransitionError(
            "Dispensed container is no longer available to consume", current_status=container.status
        )
    if cmd.quantity > container.remaining_quantity:
        raise QuantityExceedsAvailableError(
            "Requested quantity exceeds the dispensed container's remaining quantity",
            remaining=str(container.remaining_quantity),
            requested=str(cmd.quantity),
        )

    await evaluate_policy(session, actor_user_id, action="material_consumption.create", site_id=site_id)

    material_lot_id = await _resolve_consumption_lot(session, container, cmd.material_lot_id)
    cmd_uom_id = await _resolve_uom_id(session, cmd.uom)

    txn = InventoryTransaction(
        site_id=site_id,
        material_lot_id=material_lot_id,
        transaction_type="CONSUME",
        quantity=cmd.quantity,
        uom=cmd.uom,
        uom_id=cmd_uom_id,
        reference_type="dispensed_container",
        reference_id=container.id,
        actor_type="human",
        actor_id=str(actor_user_id),
    )
    session.add(txn)
    await session.flush()

    old_remaining = container.remaining_quantity
    container.remaining_quantity -= cmd.quantity
    _mark_container_status_after_movement(container)
    container.version += 1

    consumption = MaterialConsumption(
        site_id=site_id,
        batch_id=cmd.batch_id,
        step_id=cmd.step_id,
        dispensed_container_id=container.id,
        material_lot_id=material_lot_id,
        quantity=cmd.quantity,
        uom=cmd.uom,
        uom_id=cmd_uom_id,
        source_type=cmd.source_type,
        source_id=cmd.source_id,
        transaction_id=txn.id,
        recorded_by_user_id=actor_user_id,
    )
    session.add(consumption)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="material_consumption",
        aggregate_id=consumption.id,
        aggregate_version=1,
        action="Consumed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"remaining_quantity": str(old_remaining)},
        new_value={"remaining_quantity": str(container.remaining_quantity), "quantity_consumed": str(cmd.quantity)},
    )
    await write_outbox_event(
        session,
        event_type="MaterialConsumed",
        aggregate_type="material_consumption",
        aggregate_id=consumption.id,
        aggregate_version=1,
        payload={
            "id": str(consumption.id), "batch_id": str(cmd.batch_id),
            "dispensed_container_id": str(container.id), "quantity": str(cmd.quantity),
        },
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="RecordConsumption",
        aggregate_type="material_consumption",
        aggregate_id=consumption.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=consumption.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# RecordReturn — CON-FR-005/006/007/031. POST /materials/v1/returns. Unsigned.
# ---------------------------------------------------------------------------


class RecordReturnCommand(CommandEnvelope):
    batch_id: uuid.UUID
    dispensed_container_id: uuid.UUID
    material_lot_id: uuid.UUID | None = None
    quantity: Decimal
    uom: str
    container_condition: str
    condition_acceptable: bool
    storage_exposure_evidence: dict | None = None
    target_location_id: uuid.UUID


async def record_return(
    session: AsyncSession, cmd: RecordReturnCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.quantity <= 0:
        raise ValidationFailedError("quantity must be positive")

    container = await _lock_dispensed_container(session, cmd.dispensed_container_id)
    if container.batch_id != cmd.batch_id:
        raise BatchMismatchError(
            "Dispensed container belongs to a different batch (CON-FR-031)",
            container_batch_id=str(container.batch_id),
            requested_batch_id=str(cmd.batch_id),
        )
    if container.status in ("consumed", "returned", "destroyed"):
        raise InvalidTransitionError(
            "Dispensed container is no longer available to return", current_status=container.status
        )
    if cmd.quantity > container.remaining_quantity:
        raise QuantityExceedsAvailableError(
            "Requested quantity exceeds the dispensed container's remaining quantity",
            remaining=str(container.remaining_quantity),
            requested=str(cmd.quantity),
        )

    location = await session.get(WarehouseLocation, cmd.target_location_id)
    if location is None:
        raise NotFoundError("Target warehouse location not found", location_id=str(cmd.target_location_id))

    await evaluate_policy(session, actor_user_id, action="material_return.create", site_id=site_id)

    material_lot_id = await _resolve_consumption_lot(session, container, cmd.material_lot_id)

    # CON-FR-006: unsuitable condition routes to quarantine rather than back to available stock. The
    # caller-supplied `condition_acceptable` flag is a captured classification, not an inferred quality
    # judgment — same treatment as every other captured-not-derived boolean/enum in this module.
    resulting_status = "released" if cmd.condition_acceptable else "quarantine"
    cmd_uom_id = await _resolve_uom_id(session, cmd.uom)

    txn = InventoryTransaction(
        site_id=site_id,
        material_lot_id=material_lot_id,
        transaction_type="RETURN",
        quantity=cmd.quantity,
        uom=cmd.uom,
        uom_id=cmd_uom_id,
        to_location_id=cmd.target_location_id,
        reference_type="dispensed_container",
        reference_id=container.id,
        actor_type="human",
        actor_id=str(actor_user_id),
    )
    session.add(txn)
    await session.flush()

    if resulting_status == "released":
        balance = await _lock_or_create_balance(
            session,
            site_id=site_id,
            material_lot_id=material_lot_id,
            container_id=None,
            location_id=cmd.target_location_id,
        )
        balance.on_hand += cmd.quantity
        balance.available += cmd.quantity
        balance.last_transaction_id = txn.id
        balance.version += 1

    container.remaining_quantity -= cmd.quantity
    container.status = "returned" if container.remaining_quantity <= 0 else "partially_consumed"
    container.version += 1

    ret = MaterialReturn(
        site_id=site_id,
        batch_id=cmd.batch_id,
        dispensed_container_id=container.id,
        material_lot_id=material_lot_id,
        quantity=cmd.quantity,
        uom=cmd.uom,
        uom_id=cmd_uom_id,
        container_condition=cmd.container_condition,
        storage_exposure_evidence=cmd.storage_exposure_evidence,
        target_location_id=cmd.target_location_id,
        resulting_status=resulting_status,
        transaction_id=txn.id,
        returned_by_user_id=actor_user_id,
    )
    session.add(ret)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="material_return",
        aggregate_id=ret.id,
        aggregate_version=1,
        action="Returned",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={
            "quantity": str(cmd.quantity), "resulting_status": resulting_status,
            "container_condition": cmd.container_condition,
        },
    )
    await write_outbox_event(
        session,
        event_type="MaterialReturned",
        aggregate_type="material_return",
        aggregate_id=ret.id,
        aggregate_version=1,
        payload={"id": str(ret.id), "batch_id": str(cmd.batch_id), "resulting_status": resulting_status, "quantity": str(cmd.quantity)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="RecordReturn",
        aggregate_type="material_return",
        aggregate_id=ret.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=ret.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# RecordMaterialLoss — CON-FR-009/010/011/012/031. One function for SAMPLE/REJECT/SPILL/APPROVED_LOSS
# (Document 22's own data model section declares no dedicated table for these -- "All quantity changes
# use inventory_transaction from Document 20"; only the 5 named entities below get their own tables).
# Unsigned.
# ---------------------------------------------------------------------------


class RecordMaterialLossCommand(CommandEnvelope):
    batch_id: uuid.UUID
    dispensed_container_id: uuid.UUID
    loss_type: str
    quantity: Decimal
    uom: str
    reason: str
    location_id: uuid.UUID | None = None
    evidence: dict | None = None


async def record_material_loss(
    session: AsyncSession, cmd: RecordMaterialLossCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.loss_type not in LOSS_TRANSACTION_TYPES:
        raise ValidationFailedError(
            "loss_type must be one of SAMPLE, REJECT, SPILL, APPROVED_LOSS", allowed=list(LOSS_TRANSACTION_TYPES)
        )
    if cmd.quantity <= 0:
        raise ValidationFailedError("quantity must be positive")
    if not cmd.reason:
        raise ValidationFailedError("reason is required to record a material loss")

    container = await _lock_dispensed_container(session, cmd.dispensed_container_id)
    if container.batch_id != cmd.batch_id:
        raise BatchMismatchError(
            "Dispensed container belongs to a different batch (CON-FR-031)",
            container_batch_id=str(container.batch_id),
            requested_batch_id=str(cmd.batch_id),
        )
    if container.status in ("consumed", "returned", "destroyed"):
        raise InvalidTransitionError("Dispensed container is no longer available", current_status=container.status)
    if cmd.quantity > container.remaining_quantity:
        raise QuantityExceedsAvailableError(
            "Requested quantity exceeds the dispensed container's remaining quantity",
            remaining=str(container.remaining_quantity),
            requested=str(cmd.quantity),
        )

    await evaluate_policy(session, actor_user_id, action="material_loss.create", site_id=site_id)

    material_lot_id = await _resolve_consumption_lot(session, container, None)

    txn = InventoryTransaction(
        site_id=site_id,
        material_lot_id=material_lot_id,
        transaction_type=cmd.loss_type,
        quantity=cmd.quantity,
        uom=cmd.uom,
        uom_id=await _resolve_uom_id(session, cmd.uom),
        from_location_id=cmd.location_id,
        reference_type="dispensed_container",
        reference_id=container.id,
        actor_type="human",
        actor_id=str(actor_user_id),
    )
    session.add(txn)
    await session.flush()

    container.remaining_quantity -= cmd.quantity
    _mark_container_status_after_movement(container)
    container.version += 1

    event_type = "MaterialSampled" if cmd.loss_type == "SAMPLE" else "MaterialLossRecorded"
    audit_action = "Sampled" if cmd.loss_type == "SAMPLE" else "LossRecorded"

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="inventory_transaction",
        aggregate_id=txn.id,
        aggregate_version=1,
        action=audit_action,
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"loss_type": cmd.loss_type, "quantity": str(cmd.quantity), "evidence": cmd.evidence},
        reason=cmd.reason,
    )
    await write_outbox_event(
        session,
        event_type=event_type,
        aggregate_type="inventory_transaction",
        aggregate_id=txn.id,
        aggregate_version=1,
        payload={"id": str(txn.id), "batch_id": str(cmd.batch_id), "loss_type": cmd.loss_type, "quantity": str(cmd.quantity)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="RecordMaterialLoss",
        aggregate_type="inventory_transaction",
        aggregate_id=txn.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=txn.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CreateInventoryAdjustmentRequest / ApproveInventoryAdjustmentRequest — CON-FR-013/014. Distinct from
# Document 20's unsigned `create_cycle_count` (routine counting): this is the exceptional, controlled-
# reason, independently-approved adjustment path with its own Document 106 row 55 signature (`approve`,
# `Approved`, MUST be independent of the requester, reason required). Creation is unsigned (Document 106
# has no row for it — same "row absent, not optional" precedent as SG-087).
# ---------------------------------------------------------------------------


class CreateInventoryAdjustmentRequestCommand(CommandEnvelope):
    material_lot_id: uuid.UUID
    container_id: uuid.UUID | None = None
    location_id: uuid.UUID
    expected_quantity: Decimal
    observed_quantity: Decimal
    reason: str
    evidence: dict | None = None


async def create_inventory_adjustment_request(
    session: AsyncSession, cmd: CreateInventoryAdjustmentRequestCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.reason:
        raise ValidationFailedError("reason is required for an inventory adjustment request (CON-FR-013)")
    if cmd.observed_quantity < 0:
        raise ValidationFailedError("observed_quantity cannot be negative")

    lot = await session.get(MaterialLot, cmd.material_lot_id)
    if lot is None:
        raise NotFoundError("Material lot not found")
    location = await session.get(WarehouseLocation, cmd.location_id)
    if location is None:
        raise NotFoundError("Warehouse location not found")

    await evaluate_policy(session, actor_user_id, action="inventory_adjustment_request.create", site_id=site_id)

    variance = cmd.observed_quantity - cmd.expected_quantity
    request = InventoryAdjustmentRequest(
        site_id=site_id,
        material_lot_id=cmd.material_lot_id,
        container_id=cmd.container_id,
        location_id=cmd.location_id,
        expected_quantity=cmd.expected_quantity,
        observed_quantity=cmd.observed_quantity,
        variance=variance,
        reason=cmd.reason,
        evidence=cmd.evidence,
        status="requested",
        requested_by_user_id=actor_user_id,
        version=1,
    )
    session.add(request)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="inventory_adjustment_request",
        aggregate_id=request.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={
            "expected_quantity": str(cmd.expected_quantity), "observed_quantity": str(cmd.observed_quantity),
            "variance": str(variance),
        },
        reason=cmd.reason,
    )
    await write_outbox_event(
        session,
        event_type="InventoryAdjustmentRequested",
        aggregate_type="inventory_adjustment_request",
        aggregate_id=request.id,
        aggregate_version=1,
        payload={"id": str(request.id), "variance": str(variance)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="CreateInventoryAdjustmentRequest",
        aggregate_type="inventory_adjustment_request",
        aggregate_id=request.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=request.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


class ApproveInventoryAdjustmentRequestCommand(CommandEnvelope):
    expected_version: int
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def approve_inventory_adjustment_request(
    session: AsyncSession,
    request_id: uuid.UUID,
    cmd: ApproveInventoryAdjustmentRequestCommand,
    actor_user_id: uuid.UUID,
    site_id: uuid.UUID,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(
        select(InventoryAdjustmentRequest).where(InventoryAdjustmentRequest.id == request_id).with_for_update()
    )
    request = result.scalar_one_or_none()
    if request is None:
        raise NotFoundError("Inventory adjustment request not found")
    if request.version != cmd.expected_version:
        raise StaleVersionError(
            "Inventory adjustment request was modified by another actor since it was read",
            expected_version=cmd.expected_version,
            current_version=request.version,
        )
    if request.status != "requested":
        raise InvalidTransitionError(
            "Only a requested adjustment can be approved (CON-FR-013)", current_status=request.status
        )

    await evaluate_policy(session, actor_user_id, action="inventory_adjustment_request.approve", site_id=site_id)

    # CON-FR-014: user cannot approve their own adjustment.
    if actor_user_id == request.requested_by_user_id:
        raise ValidationFailedError(
            "Approver must be independent of the requester of this adjustment (CON-FR-014)"
        )

    signature_id = await _material_sign(
        session,
        record_type="inventory_adjustment_request",
        action="approve",
        actor_user_id=actor_user_id,
        record_version=request.version,
        record_hash=inventory_adjustment_request_record_hash(request),
        challenge_id=cmd.challenge_id,
        reauth_password=cmd.reauth_password,
        reason=cmd.reason,
    )
    if signature_id is None:
        raise AdjustmentApprovalRequiredError("Adjustment approval requires a signature (Document 106 row 55)")

    balance = await _lock_or_create_balance(
        session,
        site_id=site_id,
        material_lot_id=request.material_lot_id,
        container_id=request.container_id,
        location_id=request.location_id,
    )
    delta = request.variance
    txn = None
    if delta != 0:
        new_available = balance.available + delta
        if new_available < 0:
            raise ValidationFailedError(
                "Approved adjustment would drive available quantity negative at this location",
                available_after_adjustment=str(new_available),
            )
        txn = InventoryTransaction(
            site_id=site_id,
            material_lot_id=request.material_lot_id,
            container_id=request.container_id,
            transaction_type="ADJUST_POSITIVE" if delta > 0 else "ADJUST_NEGATIVE",
            quantity=abs(delta),
            uom="unit",
            uom_id=await _resolve_uom_id(session, "unit"),
            to_location_id=request.location_id if delta > 0 else None,
            from_location_id=request.location_id if delta < 0 else None,
            reference_type="inventory_adjustment_request",
            reference_id=request.id,
            actor_type="human",
            actor_id=str(actor_user_id),
        )
        session.add(txn)
        await session.flush()
        balance.on_hand = request.observed_quantity
        balance.available = new_available
        balance.last_transaction_id = txn.id
        balance.version += 1

    old_status = request.status
    request.status = "approved"
    request.signature_id = signature_id
    request.resulting_transaction_id = txn.id if txn else None
    request.approved_by_user_id = actor_user_id
    request.approved_at = datetime.now(timezone.utc)
    request.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="inventory_adjustment_request",
        aggregate_id=request.id,
        aggregate_version=request.version,
        action="Approved",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"status": old_status},
        new_value={"status": request.status, "variance": str(request.variance)},
        signature_id=signature_id,
        reason=cmd.reason,
    )
    await write_outbox_event(
        session,
        event_type="InventoryAdjustmentApproved",
        aggregate_type="inventory_adjustment_request",
        aggregate_id=request.id,
        aggregate_version=request.version,
        payload={"id": str(request.id), "variance": str(request.variance)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="ApproveInventoryAdjustmentRequest",
        aggregate_type="inventory_adjustment_request",
        aggregate_id=request.id,
        expected_version=cmd.expected_version,
        resulting_version=request.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=request.id,
        resulting_version=request.version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CreateDestructionRequest / ExecuteDestruction — CON-FR-015/016/017/018. Document 106 row 56 registers
# exactly one signer for `execute` (`Performed`, count=1, no independence, no reason) — `witnesses` is
# captured JSONB, not a second regulated signature. Creation is unsigned (no Document 106 row for it).
# ---------------------------------------------------------------------------


class CreateDestructionRequestCommand(CommandEnvelope):
    material_lot_id: uuid.UUID | None = None
    container_id: uuid.UUID | None = None
    dispensed_container_id: uuid.UUID | None = None
    quantity: Decimal
    uom: str
    reason: str
    method: str | None = None
    vendor_name: str | None = None
    manifest_reference: str | None = None
    certificate_vault_object_id: uuid.UUID | None = None
    witnesses: dict | None = None


async def create_destruction_request(
    session: AsyncSession, cmd: CreateDestructionRequestCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    scopes = [s for s in (cmd.material_lot_id, cmd.container_id, cmd.dispensed_container_id) if s is not None]
    if len(scopes) != 1:
        raise ValidationFailedError(
            "Exactly one of material_lot_id, container_id, dispensed_container_id must be set (CON-FR-015)"
        )
    if cmd.quantity <= 0:
        raise ValidationFailedError("quantity must be positive")
    if not cmd.reason:
        raise ValidationFailedError("reason is required to request destruction")

    await evaluate_policy(session, actor_user_id, action="destruction_record.create", site_id=site_id)

    record = DestructionRecord(
        site_id=site_id,
        material_lot_id=cmd.material_lot_id,
        container_id=cmd.container_id,
        dispensed_container_id=cmd.dispensed_container_id,
        quantity=cmd.quantity,
        uom=cmd.uom,
        uom_id=await _resolve_uom_id(session, cmd.uom),
        reason=cmd.reason,
        method=cmd.method,
        vendor_name=cmd.vendor_name,
        manifest_reference=cmd.manifest_reference,
        certificate_vault_object_id=cmd.certificate_vault_object_id,
        witnesses=cmd.witnesses,
        status="requested",
        requested_by_user_id=actor_user_id,
        version=1,
    )
    session.add(record)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="destruction_record",
        aggregate_id=record.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"quantity": str(cmd.quantity), "method": cmd.method},
        reason=cmd.reason,
    )
    await write_outbox_event(
        session,
        event_type="DestructionRequested",
        aggregate_type="destruction_record",
        aggregate_id=record.id,
        aggregate_version=1,
        payload={"id": str(record.id), "quantity": str(cmd.quantity)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="CreateDestructionRequest",
        aggregate_type="destruction_record",
        aggregate_id=record.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=record.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


class ExecuteDestructionCommand(CommandEnvelope):
    expected_version: int
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def execute_destruction(
    session: AsyncSession,
    destruction_id: uuid.UUID,
    cmd: ExecuteDestructionCommand,
    actor_user_id: uuid.UUID,
    site_id: uuid.UUID,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(
        select(DestructionRecord).where(DestructionRecord.id == destruction_id).with_for_update()
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise NotFoundError("Destruction record not found")
    if record.version != cmd.expected_version:
        raise StaleVersionError(
            "Destruction record was modified by another actor since it was read",
            expected_version=cmd.expected_version,
            current_version=record.version,
        )
    if record.status != "requested":
        raise DestructionNotAuthorizedError(
            "Only a requested destruction can be executed", current_status=record.status
        )

    await evaluate_policy(session, actor_user_id, action="destruction_record.execute", site_id=site_id)

    material_lot_id = record.material_lot_id
    container = None
    dispensed_container = None
    balance = None
    lot_for_qty = None

    if record.dispensed_container_id is not None:
        dispensed_container = await _lock_dispensed_container(session, record.dispensed_container_id)
        if record.quantity > dispensed_container.remaining_quantity:
            raise QuantityExceedsAvailableError(
                "Destruction quantity exceeds the dispensed container's remaining quantity",
                remaining=str(dispensed_container.remaining_quantity),
                requested=str(record.quantity),
            )
        material_lot_id = await _resolve_consumption_lot(session, dispensed_container, None)
    elif record.container_id is not None:
        result = await session.execute(
            select(MaterialContainer).where(MaterialContainer.id == record.container_id).with_for_update()
        )
        container = result.scalar_one_or_none()
        if container is None:
            raise NotFoundError("Material container not found")
        if record.quantity > container.current_quantity:
            raise QuantityExceedsAvailableError(
                "Destruction quantity exceeds the container's current quantity",
                remaining=str(container.current_quantity),
                requested=str(record.quantity),
            )
        material_lot_id = container.material_lot_id
        balance = (
            await session.execute(
                select(InventoryBalanceProjection)
                .where(
                    InventoryBalanceProjection.material_lot_id == material_lot_id,
                    InventoryBalanceProjection.container_id == container.id,
                )
                .with_for_update()
            )
        ).scalars().first()
    else:
        lot_result = await session.execute(
            select(MaterialLot).where(MaterialLot.id == record.material_lot_id).with_for_update()
        )
        lot_for_qty = lot_result.scalar_one_or_none()
        if lot_for_qty is None:
            raise NotFoundError("Material lot not found")
        if record.quantity > lot_for_qty.available_quantity:
            raise QuantityExceedsAvailableError(
                "Destruction quantity exceeds the lot's available quantity",
                remaining=str(lot_for_qty.available_quantity),
                requested=str(record.quantity),
            )

    signature_id = await _material_sign(
        session,
        record_type="destruction_record",
        action="execute",
        actor_user_id=actor_user_id,
        record_version=record.version,
        record_hash=destruction_record_hash(record),
        challenge_id=cmd.challenge_id,
        reauth_password=cmd.reauth_password,
    )

    txn = InventoryTransaction(
        site_id=site_id,
        material_lot_id=material_lot_id,
        container_id=container.id if container else None,
        transaction_type="DESTROY",
        quantity=record.quantity,
        uom=record.uom,
        uom_id=record.uom_id,  # copied from the destruction record's own already-resolved value
        reference_type="destruction_record",
        reference_id=record.id,
        actor_type="human",
        actor_id=str(actor_user_id),
    )
    session.add(txn)
    await session.flush()

    if dispensed_container is not None:
        dispensed_container.remaining_quantity -= record.quantity
        dispensed_container.status = (
            "destroyed" if dispensed_container.remaining_quantity <= 0 else "partially_consumed"
        )
        dispensed_container.version += 1
    elif container is not None:
        container.current_quantity -= record.quantity
        if container.current_quantity <= 0:
            container.container_status = "destroyed"
        container.version += 1
        if balance is not None:
            balance.on_hand -= record.quantity
            balance.available -= record.quantity
            balance.last_transaction_id = txn.id
            balance.version += 1
    else:
        lot_for_qty.available_quantity -= record.quantity
        lot_for_qty.version += 1

    old_status = record.status
    record.status = "executed"
    record.transaction_id = txn.id
    record.signature_id = signature_id
    record.executed_by_user_id = actor_user_id
    record.executed_at = datetime.now(timezone.utc)
    record.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="destruction_record",
        aggregate_id=record.id,
        aggregate_version=record.version,
        action="Destroyed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"status": old_status},
        new_value={"status": record.status, "quantity": str(record.quantity)},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="MaterialDestroyed",
        aggregate_type="destruction_record",
        aggregate_id=record.id,
        aggregate_version=record.version,
        payload={"id": str(record.id), "quantity": str(record.quantity)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="ExecuteDestruction",
        aggregate_type="destruction_record",
        aggregate_id=record.id,
        expected_version=cmd.expected_version,
        resulting_version=record.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=record.id,
        resulting_version=record.version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# EvaluateMaterialReconciliation / GetMaterialReconciliation — CON-FR-019/020/021(partial, SG-098)/
# 022(partial, SG-098)/023/024/029/030. Scoped to batch_id (+ optional material_id), not the spec's prose
# "material requirement" — no `material_requirement` entity exists anywhere in this codebase (SG-094
# precedent). Rounding per Document 110 CC-4: 6dp intermediate, 2dp reported, half-up. `tolerance_value`
# is caller-supplied (SG-098). Unsigned — "reconciliation acceptance outside nominal rules" routes through
# the linked deviation's own signature chain, not a new signature on this endpoint.
# ---------------------------------------------------------------------------


class EvaluateMaterialReconciliationCommand(CommandEnvelope):
    material_id: uuid.UUID | None = None
    tolerance_value: Decimal
    variance_severity: str | None = None
    deviation_owner_user_id: uuid.UUID | None = None


def _round6(value: Decimal) -> Decimal:
    return Decimal(value).quantize(_SIX_DP, rounding=ROUND_HALF_UP)


def _round2(value: Decimal) -> Decimal:
    return Decimal(value).quantize(_TWO_DP, rounding=ROUND_HALF_UP)


async def evaluate_material_reconciliation(
    session: AsyncSession,
    batch_id: uuid.UUID,
    cmd: EvaluateMaterialReconciliationCommand,
    actor_user_id: uuid.UUID,
    site_id: uuid.UUID,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.tolerance_value < 0:
        raise ValidationFailedError("tolerance_value cannot be negative")

    await evaluate_policy(session, actor_user_id, action="material_reconciliation.evaluate", site_id=site_id)

    container_filter = [DispensedContainer.batch_id == batch_id]
    if cmd.material_id is not None:
        container_filter.append(DispensedContainer.material_id == cmd.material_id)
    containers = (await session.execute(select(DispensedContainer).where(*container_filter))).scalars().all()
    container_ids = [c.id for c in containers]

    dispensed_total = sum((c.actual_quantity for c in containers), Decimal("0"))

    consumption_filter = [MaterialConsumption.batch_id == batch_id]
    if container_ids:
        consumption_filter.append(MaterialConsumption.dispensed_container_id.in_(container_ids))
    else:
        consumption_filter.append(MaterialConsumption.id == None)  # noqa: E711 -- no containers, no rows
    consumed_total = (
        await session.execute(select(func.coalesce(func.sum(MaterialConsumption.quantity), 0)).where(*consumption_filter))
    ).scalar_one()

    return_filter = [MaterialReturn.batch_id == batch_id]
    if container_ids:
        return_filter.append(MaterialReturn.dispensed_container_id.in_(container_ids))
    else:
        return_filter.append(MaterialReturn.id == None)  # noqa: E711
    returned_total = (
        await session.execute(select(func.coalesce(func.sum(MaterialReturn.quantity), 0)).where(*return_filter))
    ).scalar_one()

    loss_totals = {t: Decimal("0") for t in LOSS_TRANSACTION_TYPES}
    if container_ids:
        rows = (
            await session.execute(
                select(InventoryTransaction.transaction_type, func.coalesce(func.sum(InventoryTransaction.quantity), 0))
                .where(
                    InventoryTransaction.reference_type == "dispensed_container",
                    InventoryTransaction.reference_id.in_(container_ids),
                    InventoryTransaction.transaction_type.in_(list(LOSS_TRANSACTION_TYPES)),
                )
                .group_by(InventoryTransaction.transaction_type)
            )
        ).all()
        for txn_type, total in rows:
            loss_totals[txn_type] = Decimal(total)

    destroyed_total = Decimal("0")
    if container_ids:
        destroyed_total = (
            await session.execute(
                select(func.coalesce(func.sum(DestructionRecord.quantity), 0)).where(
                    DestructionRecord.dispensed_container_id.in_(container_ids),
                    DestructionRecord.status == "executed",
                )
            )
        ).scalar_one()

    dispensed_total = _round6(dispensed_total)
    consumed_total = _round6(consumed_total)
    returned_total = _round6(returned_total)
    sampled_total = _round6(loss_totals["SAMPLE"])
    rejected_total = _round6(loss_totals["REJECT"])
    destroyed_total = _round6(destroyed_total)
    # CON-FR-020's 7 named categories have no separate "spill" bucket -- SPILL rolls into approved_loss.
    approved_loss_total = _round6(loss_totals["SPILL"] + loss_totals["APPROVED_LOSS"])

    accounted = consumed_total + returned_total + sampled_total + rejected_total + destroyed_total + approved_loss_total
    unexplained_variance = _round2(dispensed_total - accounted)
    outcome = "ACCEPTABLE" if abs(unexplained_variance) <= cmd.tolerance_value else "VARIANCE"

    linked_deviation_id = None
    if outcome == "VARIANCE" and cmd.variance_severity and cmd.deviation_owner_user_id:
        # First cross-module owning-command call in this codebase (AG-06): materials calls qms's own
        # create_deviation rather than writing qms.deviation_record directly. severity/owner are caller-
        # supplied, not auto-derived (CON-FR-022 partial, SG-098).
        deviation_receipt = await qms_commands.create_deviation(
            session,
            qms_commands.CreateDeviationCommand(
                idempotency_key=str(uuid.uuid4()),
                site_id=site_id,
                deviation_number=f"MAT-RECON-{batch_id.hex[:8]}-{uuid.uuid4().hex[:6]}",
                deviation_type="material_reconciliation_variance",
                source_type="material",
                source_id=batch_id,
                severity=cmd.variance_severity,
                owner_subject_id=cmd.deviation_owner_user_id,
            ),
            actor_user_id,
        )
        linked_deviation_id = deviation_receipt.aggregate_id

    prior_max_version = (
        await session.execute(
            select(func.max(MaterialReconciliation.version)).where(
                MaterialReconciliation.batch_id == batch_id,
                MaterialReconciliation.material_id == cmd.material_id,
            )
        )
    ).scalar_one()
    next_version = (prior_max_version or 0) + 1

    reconciliation = MaterialReconciliation(
        site_id=site_id,
        batch_id=batch_id,
        material_id=cmd.material_id,
        dispensed_total=dispensed_total,
        consumed_total=consumed_total,
        returned_total=returned_total,
        sampled_total=sampled_total,
        rejected_total=rejected_total,
        destroyed_total=destroyed_total,
        approved_loss_total=approved_loss_total,
        unexplained_variance=unexplained_variance,
        tolerance_value=cmd.tolerance_value,
        outcome=outcome,
        linked_deviation_id=linked_deviation_id,
        version=next_version,
        evaluated_by_user_id=actor_user_id,
    )
    session.add(reconciliation)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="material_reconciliation",
        aggregate_id=reconciliation.id,
        aggregate_version=next_version,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"outcome": outcome, "unexplained_variance": str(unexplained_variance)},
    )
    await write_outbox_event(
        session,
        event_type="MaterialReconciliationCalculated" if outcome == "ACCEPTABLE" else "MaterialReconciliationFailed",
        aggregate_type="material_reconciliation",
        aggregate_id=reconciliation.id,
        aggregate_version=next_version,
        payload={"id": str(reconciliation.id), "batch_id": str(batch_id), "outcome": outcome},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="EvaluateMaterialReconciliation",
        aggregate_type="material_reconciliation",
        aggregate_id=reconciliation.id,
        expected_version=None,
        resulting_version=next_version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=reconciliation.id,
        resulting_version=next_version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


async def get_material_reconciliation(session: AsyncSession, batch_id: uuid.UUID) -> dict:
    result = await session.execute(
        select(MaterialReconciliation)
        .where(MaterialReconciliation.batch_id == batch_id)
        .order_by(MaterialReconciliation.version.desc())
        .limit(1)
    )
    reconciliation = result.scalar_one_or_none()
    if reconciliation is None:
        raise NotFoundError("No reconciliation has been evaluated for this batch")
    return {
        "id": str(reconciliation.id),
        "batch_id": str(reconciliation.batch_id),
        "material_id": str(reconciliation.material_id) if reconciliation.material_id else None,
        "dispensed_total": str(reconciliation.dispensed_total),
        "consumed_total": str(reconciliation.consumed_total),
        "returned_total": str(reconciliation.returned_total),
        "sampled_total": str(reconciliation.sampled_total),
        "rejected_total": str(reconciliation.rejected_total),
        "destroyed_total": str(reconciliation.destroyed_total),
        "approved_loss_total": str(reconciliation.approved_loss_total),
        "unexplained_variance": str(reconciliation.unexplained_variance),
        "tolerance_value": str(reconciliation.tolerance_value),
        "outcome": reconciliation.outcome,
        "version": reconciliation.version,
        "linked_deviation_id": str(reconciliation.linked_deviation_id) if reconciliation.linked_deviation_id else None,
        # CON-FR-025/026 (SG-098): no ERP integration exists in this codebase (WP-07 not built).
        "erp_posting_status": "not_integrated",
        "evaluated_at": reconciliation.created_at.isoformat(),
    }
