import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.lims_integration.models import LimsInstance, LimsMapping, LimsMessage
from app.modules.policy.service import evaluate_policy
from app.modules.qc import commands as qc_commands
from app.modules.qc.models import QcResult, QcSample, QcTestDefinition, QcTestOrder
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    InvalidTransitionError,
    LimsDuplicateEventError,
    LimsMappingNotFoundError,
    LimsMethodMismatchError,
    LimsResultVersionStaleError,
    LimsSampleUnknownError,
    LimsUomInvalidError,
    MissingSignatureError,
    NotFoundError,
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


def _record_hash(obj, *fields: str, version_field: str = "version") -> str:
    return sha256_hex({f: str(getattr(obj, f)) for f in ("id", version_field, *fields)})


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
        audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _get_instance(session: AsyncSession, instance_id: uuid.UUID) -> LimsInstance:
    instance = await session.get(LimsInstance, instance_id)
    if instance is None:
        raise NotFoundError("LIMS instance not found")
    return instance


async def _record_message(
    session: AsyncSession, *, instance_id: uuid.UUID, direction: str, external_event_id: str,
    internal_correlation_id: uuid.UUID | None, status: str, error_code: str | None = None,
    schema_version: str | None = None, adapter_version: str | None = None,
) -> LimsMessage:
    now = datetime.now(timezone.utc)
    message = LimsMessage(
        instance_id=instance_id, direction=direction, external_event_id=external_event_id,
        internal_correlation_id=internal_correlation_id, status=status, error_code=error_code,
        schema_version=schema_version, adapter_version=adapter_version,
        sent_at=now if direction == "outbound" else None, received_at=now if direction == "inbound" else None,
    )
    session.add(message)
    await session.flush()
    return message


# ---------------------------------------------------------------------------
# RequestLimsSample -- LIMS-FR-004/005: POST /integrations/lims/{instance}/samples. Calls
# qc.commands.create_sample -- this module never writes qc_* tables directly (Document 24 §18).
# ---------------------------------------------------------------------------


class RequestLimsSampleCommand(CommandEnvelope):
    instance_id: uuid.UUID
    external_sample_id: str
    sample_number: str
    sample_type: str
    source_type: str
    source_id: uuid.UUID | None = None
    source_location_ref: str | None = None
    lot_batch_serial_ref: str | None = None
    sample_quantity: str | None = None
    sample_uom: str | None = None


async def request_lims_sample(
    session: AsyncSession, cmd: RequestLimsSampleCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    instance = await _get_instance(session, cmd.instance_id)

    dup = (
        await session.execute(
            select(LimsMapping).where(
                LimsMapping.instance_id == instance.id, LimsMapping.external_entity_type == "sample",
                LimsMapping.external_entity_id == cmd.external_sample_id,
            )
        )
    ).scalars().first()
    if dup is not None:
        raise LimsDuplicateEventError("A sample with this external_sample_id was already requested")

    sample_receipt = await qc_commands.create_sample(
        session,
        qc_commands.CreateSampleCommand(
            idempotency_key=str(uuid.uuid4()), sample_number=cmd.sample_number, sample_type=cmd.sample_type,
            source_type=cmd.source_type, source_id=cmd.source_id, source_location_ref=cmd.source_location_ref,
            lot_batch_serial_ref=cmd.lot_batch_serial_ref, sample_quantity=cmd.sample_quantity, sample_uom=cmd.sample_uom,
        ),
        actor_user_id,
    )

    mapping = LimsMapping(
        instance_id=instance.id, internal_object_type="qc_sample", internal_object_id=sample_receipt.aggregate_id,
        internal_object_version=sample_receipt.resulting_version, external_entity_type="sample",
        external_entity_id=cmd.external_sample_id, mapping_version=1, status="active",
    )
    session.add(mapping)

    correlation_id = uuid.uuid4()
    await _record_message(
        session, instance_id=instance.id, direction="outbound", external_event_id=cmd.external_sample_id,
        internal_correlation_id=sample_receipt.aggregate_id, status="accepted",
    )
    audit_event = await write_audit_event(
        session, site_id=instance.site_id, aggregate_type="lims_mapping", aggregate_id=mapping.id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"external_sample_id": cmd.external_sample_id, "internal_sample_id": str(sample_receipt.aggregate_id)},
    )
    await write_outbox_event(
        session, event_type="LIMSSampleRequested", aggregate_type="lims_mapping", aggregate_id=mapping.id,
        aggregate_version=1, payload={"external_sample_id": cmd.external_sample_id, "internal_sample_id": str(sample_receipt.aggregate_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=instance.site_id, command_type="RequestLimsSample", aggregate_type="lims_mapping",
        aggregate_id=mapping.id, expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=sample_receipt.aggregate_id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CancelLimsSample -- LIMS-FR-021: POST /integrations/lims/{instance}/samples/{id}/cancel. Signed per
# Document 106 row 64 (meaning Approved, independent of the original requester).
# ---------------------------------------------------------------------------


class CancelLimsSampleCommand(CommandEnvelope):
    instance_id: uuid.UUID
    sample_id: uuid.UUID
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def cancel_lims_sample(
    session: AsyncSession, cmd: CancelLimsSampleCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    instance = await _get_instance(session, cmd.instance_id)
    mapping = (
        await session.execute(
            select(LimsMapping).where(
                LimsMapping.instance_id == instance.id, LimsMapping.internal_object_type == "qc_sample",
                LimsMapping.internal_object_id == cmd.sample_id,
            )
        )
    ).scalars().first()
    if mapping is None:
        raise LimsSampleUnknownError("This sample was not requested through this LIMS instance")

    sample = await session.get(QcSample, cmd.sample_id)
    if sample is None:
        raise NotFoundError("Sample not found")

    await evaluate_policy(session, actor_user_id, action="lims_sample.cancel", site_id=instance.site_id)
    if actor_user_id == sample.sampler_subject_id:
        raise InvalidTransitionError("Canceller must be independent of the original requester (SoD)")

    policy = await signature_service.resolve_signature_requirement(session, record_type="lims_sample", action="cancel")
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
            record_version=sample.version, record_hash=_record_hash(sample, "state"),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    cancel_receipt = await qc_commands.cancel_sample(
        session,
        qc_commands.CancelSampleCommand(
            idempotency_key=str(uuid.uuid4()), sample_id=sample.id, expected_version=sample.version, reason=cmd.reason,
        ),
        actor_user_id,
    )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=instance.site_id, aggregate_type="lims_mapping", aggregate_id=mapping.id,
        aggregate_version=mapping.version, action="Approved", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"cancelled_sample_id": str(sample.id)}, reason=cmd.reason, signature_id=signature_id,
    )
    receipt = await record_command_receipt(
        session, site_id=instance.site_id, command_type="CancelLimsSample", aggregate_type="lims_mapping",
        aggregate_id=mapping.id, expected_version=None, resulting_version=mapping.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=cancel_receipt.aggregate_id, resulting_version=cancel_receipt.resulting_version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# IngestLimsStatus -- LIMS-FR-006: POST /integrations/lims/{instance}/events/status. Inbound; duplicate
# events rejected by external_event_id uniqueness (LIMS-FR-010).
# ---------------------------------------------------------------------------


class IngestLimsStatusCommand(CommandEnvelope):
    instance_id: uuid.UUID
    external_event_id: str
    external_sample_id: str
    status: str  # "received" | "in_progress"


async def ingest_lims_status(
    session: AsyncSession, cmd: IngestLimsStatusCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    instance = await _get_instance(session, cmd.instance_id)

    dup = (
        await session.execute(
            select(LimsMessage).where(LimsMessage.instance_id == instance.id, LimsMessage.external_event_id == cmd.external_event_id)
        )
    ).scalars().first()
    if dup is not None:
        raise LimsDuplicateEventError("This external_event_id was already processed")

    mapping = (
        await session.execute(
            select(LimsMapping).where(
                LimsMapping.instance_id == instance.id, LimsMapping.external_entity_type == "sample",
                LimsMapping.external_entity_id == cmd.external_sample_id,
            )
        )
    ).scalars().first()
    if mapping is None:
        raise LimsSampleUnknownError("No mapped sample for this external_sample_id")

    sample = await session.get(QcSample, mapping.internal_object_id)
    if sample is None:
        raise NotFoundError("Mapped sample no longer exists")

    if cmd.status == "received" and sample.state in ("planned", "collected"):
        status_receipt = await qc_commands.receive_sample(
            session,
            qc_commands.ReceiveSampleCommand(idempotency_key=str(uuid.uuid4()), sample_id=sample.id, expected_version=sample.version),
            actor_user_id,
        )
        result_aggregate_id = status_receipt.aggregate_id
    else:
        result_aggregate_id = sample.id

    correlation_id = uuid.uuid4()
    message = await _record_message(
        session, instance_id=instance.id, direction="inbound", external_event_id=cmd.external_event_id,
        internal_correlation_id=result_aggregate_id, status="accepted",
    )
    await write_outbox_event(
        session, event_type="LIMSStatusReceived", aggregate_type="lims_message", aggregate_id=message.id,
        aggregate_version=1, payload={"external_sample_id": cmd.external_sample_id, "status": cmd.status},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=instance.site_id, command_type="IngestLimsStatus", aggregate_type="lims_message",
        aggregate_id=message.id, expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=result_aggregate_id, resulting_version=1,
        audit_event_id=message.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# IngestLimsResult -- LIMS-FR-007/009/010/011/012/018/019/028/029: POST
# /integrations/lims/{instance}/events/results. Validates mapping/ownership-mode/method/UOM/ordering/
# duplicate, then calls qc.commands.record_raw_data + record_result (reusing acceptance/trend-rule
# PASS/OOS/OOT classification and append-only versioning unmodified).
# ---------------------------------------------------------------------------


class IngestLimsResultCommand(CommandEnvelope):
    instance_id: uuid.UUID
    external_event_id: str
    external_sample_id: str
    test_code: str
    external_result_version: int
    method_version: str
    result_type: str
    value_decimal: str | None = None
    value_text: str | None = None
    uom: str | None = None
    schema_version: str | None = None
    adapter_version: str | None = None


async def ingest_lims_result(
    session: AsyncSession, cmd: IngestLimsResultCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    instance = await _get_instance(session, cmd.instance_id)
    if instance.ownership_mode != "gxp_managed":
        raise ValidationFailedError(
            "Only ownership_mode='gxp_managed' is implemented this pass (SG-070)", ownership_mode=instance.ownership_mode
        )

    dup = (
        await session.execute(
            select(LimsMessage).where(LimsMessage.instance_id == instance.id, LimsMessage.external_event_id == cmd.external_event_id)
        )
    ).scalars().first()
    if dup is not None:
        raise LimsDuplicateEventError("This external_event_id was already processed")

    sample_mapping = (
        await session.execute(
            select(LimsMapping).where(
                LimsMapping.instance_id == instance.id, LimsMapping.external_entity_type == "sample",
                LimsMapping.external_entity_id == cmd.external_sample_id,
            )
        )
    ).scalars().first()
    if sample_mapping is None:
        raise LimsMappingNotFoundError("No sample mapping for this external_sample_id")

    order = (
        await session.execute(
            select(QcTestOrder, QcTestDefinition)
            .join(QcTestDefinition, QcTestDefinition.id == QcTestOrder.test_definition_id)
            .where(QcTestOrder.sample_id == sample_mapping.internal_object_id, QcTestDefinition.test_code == cmd.test_code)
        )
    ).first()
    if order is None:
        raise LimsMappingNotFoundError("No test order for this external_sample_id/test_code")
    test_order, definition = order

    if definition.method_version and definition.method_version != cmd.method_version:
        raise LimsMethodMismatchError(
            "External method_version does not match the test definition's method_version",
            expected=definition.method_version, received=cmd.method_version,
        )
    if definition.uom and cmd.uom and definition.uom != cmd.uom:
        raise LimsUomInvalidError(
            "External uom does not match the test definition's uom (no conversion attempted)",
            expected=definition.uom, received=cmd.uom,
        )

    result_key = f"{cmd.external_sample_id}/{cmd.test_code}"
    result_mapping = (
        await session.execute(
            select(LimsMapping).where(
                LimsMapping.instance_id == instance.id, LimsMapping.external_entity_type == "lims_result",
                LimsMapping.external_entity_id == result_key,
            )
        )
    ).scalars().first()
    if result_mapping is not None and cmd.external_result_version <= result_mapping.mapping_version:
        raise LimsResultVersionStaleError(
            "external_result_version is not newer than the last accepted version",
            last_accepted=result_mapping.mapping_version, received=cmd.external_result_version,
        )

    if test_order.state in ("created", "assigned"):
        await qc_commands.start_test_order(
            session,
            qc_commands.StartTestOrderCommand(idempotency_key=str(uuid.uuid4()), test_order_id=test_order.id, expected_version=test_order.version),
            actor_user_id,
        )
        await session.refresh(test_order)

    run_receipt = await qc_commands.record_raw_data(
        session,
        qc_commands.RecordRawDataCommand(
            idempotency_key=str(uuid.uuid4()), test_order_id=test_order.id, method_version=cmd.method_version,
        ),
        actor_user_id,
    )
    result_receipt = await qc_commands.record_result(
        session,
        qc_commands.RecordResultCommand(
            idempotency_key=str(uuid.uuid4()), test_order_id=test_order.id, test_run_id=run_receipt.aggregate_id,
            result_type=cmd.result_type, value_decimal=cmd.value_decimal, value_text=cmd.value_text, uom=cmd.uom,
        ),
        actor_user_id,
    )
    result = await session.get(QcResult, result_receipt.aggregate_id)

    is_revision = result_mapping is not None
    if result_mapping is None:
        result_mapping = LimsMapping(
            instance_id=instance.id, internal_object_type="qc_result", internal_object_id=result.id,
            internal_object_version=1, external_entity_type="lims_result", external_entity_id=result_key,
            mapping_version=cmd.external_result_version, status="active",
        )
        session.add(result_mapping)
    else:
        result_mapping.internal_object_id = result.id
        result_mapping.mapping_version = cmd.external_result_version
        result_mapping.version += 1

    correlation_id = uuid.uuid4()
    message = await _record_message(
        session, instance_id=instance.id, direction="inbound", external_event_id=cmd.external_event_id,
        internal_correlation_id=result.id, status="accepted", schema_version=cmd.schema_version,
        adapter_version=cmd.adapter_version,
    )
    await write_outbox_event(
        session, event_type="LIMSResultRevised" if is_revision else "LIMSResultAccepted",
        aggregate_type="qc_result", aggregate_id=result.id, aggregate_version=1,
        payload={"external_sample_id": cmd.external_sample_id, "test_code": cmd.test_code, "outcome": result.outcome},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=instance.site_id, command_type="IngestLimsResult", aggregate_type="qc_result",
        aggregate_id=result.id, expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=result.id, resulting_version=1,
        audit_event_id=message.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ReconcileLimsInstance -- LIMS-FR-025/026: POST /integrations/lims/{instance}/reconcile. On-demand
# (no periodic scheduler exists -- SG-070). Not signed (no Document 106 row).
# ---------------------------------------------------------------------------


class ReconcileLimsInstanceCommand(CommandEnvelope):
    instance_id: uuid.UUID


async def reconcile_lims_instance(
    session: AsyncSession, cmd: ReconcileLimsInstanceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    instance = await _get_instance(session, cmd.instance_id)

    sample_mappings = (
        await session.execute(
            select(LimsMapping).where(LimsMapping.instance_id == instance.id, LimsMapping.internal_object_type == "qc_sample")
        )
    ).scalars().all()

    mismatches = []
    correlation_id = uuid.uuid4()
    for mapping in sample_mappings:
        sample = await session.get(QcSample, mapping.internal_object_id)
        if sample is None:
            mismatches.append({"external_sample_id": mapping.external_entity_id, "issue": "internal_sample_missing"})
            continue
        if sample.version != mapping.internal_object_version:
            mismatches.append({
                "external_sample_id": mapping.external_entity_id, "issue": "version_mismatch",
                "mapped_version": mapping.internal_object_version, "current_version": sample.version,
            })

    for mismatch in mismatches:
        await write_outbox_event(
            session, event_type="LIMSReconciliationMismatchDetected", aggregate_type="lims_instance",
            aggregate_id=instance.id, aggregate_version=instance.version, payload=mismatch, correlation_id=correlation_id,
        )

    audit_event = await write_audit_event(
        session, site_id=instance.site_id, aggregate_type="lims_instance", aggregate_id=instance.id,
        aggregate_version=instance.version, action="Reviewed", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"mismatch_count": len(mismatches)},
    )
    receipt = await record_command_receipt(
        session, site_id=instance.site_id, command_type="ReconcileLimsInstance", aggregate_type="lims_instance",
        aggregate_id=instance.id, expected_version=None, resulting_version=instance.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=instance.id, resulting_version=instance.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )
