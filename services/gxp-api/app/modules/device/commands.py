"""Document 12 (SPEC-EBMR-003) — the buildable slice of eDHR / Device Production History: create a
device lot, bulk-create serial units under it, and hold a unit. Everything gated on
device_component_usage/device_test_result/device_defect/device_evidence_inheritance or on infrastructure
this codebase doesn't have yet (Equipment master, NCR/QMS, sterilization, packaging/labeling, DDCP
profiles) is deferred -- SG-049/SG-050.
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.device import service as device_service
from app.modules.device.models import ALLOWED_TRANSITIONS, DeviceUnit
from app.modules.product_master.models import ProductVersion
from app.mutation.errors import InvalidTransitionError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
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


async def _load_unit_for_update(session: AsyncSession, unit_id: uuid.UUID, expected_version: int) -> DeviceUnit:
    result = await session.execute(select(DeviceUnit).where(DeviceUnit.id == unit_id).with_for_update())
    unit = result.scalar_one_or_none()
    if unit is None:
        raise NotFoundError("Device unit not found")
    if unit.version != expected_version:
        raise StaleVersionError(
            "Device unit was modified by another actor since it was read",
            expected_version=expected_version,
            current_version=unit.version,
        )
    return unit


async def _assert_product_version_released(session: AsyncSession, product_version_id: uuid.UUID) -> ProductVersion:
    product_version = await session.get(ProductVersion, product_version_id)
    if product_version is None:
        raise NotFoundError("Product version not found")
    if product_version.lifecycle_state != "released":
        raise ValidationFailedError(
            "Device history can only be created against a released product version",
            current_state=product_version.lifecycle_state,
        )
    return product_version


# ---------------------------------------------------------------------------
# CreateDeviceLot — DHR-FR-001/002/020 (lot-scope: serial_number is null)
# ---------------------------------------------------------------------------


class CreateDeviceLotCommand(CommandEnvelope):
    site_id: uuid.UUID
    product_version_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    udi_di: str | None = None
    udi_pi: dict | None = None


async def create_device_lot(session: AsyncSession, cmd: CreateDeviceLotCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    await _assert_product_version_released(session, cmd.product_version_id)

    lot = DeviceUnit(
        site_id=cmd.site_id,
        product_version_id=cmd.product_version_id,
        batch_id=cmd.batch_id,
        serial_number=None,
        udi_di=cmd.udi_di,
        udi_pi=cmd.udi_pi,
        state="created",
    )
    session.add(lot)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.site_id,
        aggregate_type="device_unit",
        aggregate_id=lot.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"scope": "lot", "product_version_id": str(cmd.product_version_id), "batch_id": str(cmd.batch_id) if cmd.batch_id else None},
    )
    await write_outbox_event(
        session,
        event_type="DeviceUnitCreated",
        aggregate_type="device_unit",
        aggregate_id=lot.id,
        aggregate_version=1,
        payload={"id": str(lot.id), "scope": "lot"},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="CreateDeviceLot",
        aggregate_type="device_unit",
        aggregate_id=lot.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=lot.id, resulting_version=1, audit_event_id=audit_event.id, correlation_id=correlation_id
    )


# ---------------------------------------------------------------------------
# BulkCreateDeviceUnits — DHR-FR-003/028 (serial-scope units under a lot)
# ---------------------------------------------------------------------------


class UnitInput(BaseModel):
    serial_number: str
    udi_pi: dict | None = None


class BulkCreateDeviceUnitsCommand(CommandEnvelope):
    device_lot_id: uuid.UUID
    units: list[UnitInput]


async def bulk_create_device_units(
    session: AsyncSession, cmd: BulkCreateDeviceUnitsCommand, actor_user_id: uuid.UUID
) -> list[MutationReceipt]:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return [_receipt_from_existing(existing)]

    if not cmd.units:
        raise ValidationFailedError("units must not be empty")

    lot = await device_service.get_unit(session, cmd.device_lot_id)
    if lot.serial_number is not None:
        raise ValidationFailedError("device_lot_id does not reference a lot-scope device_unit (serial_number is already set)")

    serials = [u.serial_number for u in cmd.units]
    if len(serials) != len(set(serials)):
        raise ValidationFailedError("Duplicate serial_number within this bulk request")
    conflict = (
        await session.execute(
            select(DeviceUnit.serial_number).where(DeviceUnit.site_id == lot.site_id, DeviceUnit.serial_number.in_(serials))
        )
    ).scalars().all()
    if conflict:
        raise ValidationFailedError("serial_number already exists at this site", conflicting_serials=list(conflict))

    correlation_id = uuid.uuid4()
    created_units: list[DeviceUnit] = []
    for u in cmd.units:
        unit = DeviceUnit(
            site_id=lot.site_id,
            product_version_id=lot.product_version_id,
            batch_id=lot.batch_id,
            device_lot_id=lot.id,
            serial_number=u.serial_number,
            udi_di=lot.udi_di,
            udi_pi=u.udi_pi,
            state="created",
        )
        session.add(unit)
        created_units.append(unit)
    await session.flush()

    receipts: list[MutationReceipt] = []
    for unit in created_units:
        audit_event = await write_audit_event(
            session,
            site_id=unit.site_id,
            aggregate_type="device_unit",
            aggregate_id=unit.id,
            aggregate_version=1,
            action="Created",
            actor_id=actor_user_id,
            correlation_id=correlation_id,
            new_value={"scope": "serial", "serial_number": unit.serial_number, "device_lot_id": str(lot.id)},
        )
        await write_outbox_event(
            session,
            event_type="DeviceUnitCreated",
            aggregate_type="device_unit",
            aggregate_id=unit.id,
            aggregate_version=1,
            payload={"id": str(unit.id), "scope": "serial", "serial_number": unit.serial_number},
            correlation_id=correlation_id,
        )
        receipts.append((unit, audit_event))

    receipt_row = await record_command_receipt(
        session,
        site_id=lot.site_id,
        command_type="BulkCreateDeviceUnits",
        aggregate_type="device_unit",
        aggregate_id=lot.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return [
        MutationReceipt(
            command_id=receipt_row.id, aggregate_id=unit.id, resulting_version=1, audit_event_id=audit_event.id, correlation_id=correlation_id
        )
        for unit, audit_event in receipts
    ]


# ---------------------------------------------------------------------------
# StartDeviceUnit / HoldDeviceUnit — DHR-FR-014 (created->in_process->hold slice only)
# ---------------------------------------------------------------------------


class DeviceUnitTransitionCommand(CommandEnvelope):
    unit_id: uuid.UUID
    expected_version: int
    reason: str | None = None


async def _simple_transition(
    session: AsyncSession, cmd: DeviceUnitTransitionCommand, actor_user_id: uuid.UUID, *, new_state: str, command_type: str, event_type: str
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    unit = await _load_unit_for_update(session, cmd.unit_id, cmd.expected_version)
    if new_state not in ALLOWED_TRANSITIONS.get(unit.state, set()):
        raise InvalidTransitionError("Illegal device-unit state transition", current_state=unit.state, requested=new_state)
    old_state = unit.state
    unit.state = new_state
    unit.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=unit.site_id,
        aggregate_type="device_unit",
        aggregate_id=unit.id,
        aggregate_version=unit.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        reason=cmd.reason,
        old_value={"state": old_state},
        new_value={"state": unit.state},
    )
    await write_outbox_event(
        session,
        event_type=event_type,
        aggregate_type="device_unit",
        aggregate_id=unit.id,
        aggregate_version=unit.version,
        payload={"id": str(unit.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=unit.site_id,
        command_type=command_type,
        aggregate_type="device_unit",
        aggregate_id=unit.id,
        expected_version=cmd.expected_version,
        resulting_version=unit.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=unit.id, resulting_version=unit.version, audit_event_id=audit_event.id, correlation_id=correlation_id
    )


async def hold_device_unit(session: AsyncSession, cmd: DeviceUnitTransitionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    return await _simple_transition(session, cmd, actor_user_id, new_state="hold", command_type="HoldDeviceUnit", event_type="DeviceUnitHeld")
