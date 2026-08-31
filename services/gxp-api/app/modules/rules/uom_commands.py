"""Document 110 (SPEC-GXP-008) §3 — the UOM/conversion authoring command surface SG-146 raised: until
this pass, `rules.gxp_uom`/`gxp_uom_conversion` (added closing SG-143) had no author/release command,
so a real deployment could not create a released UOM row through the regulated mutation path — only a
controlled migration/seed or a test fixture could write one.

Lifecycle is two states, `draft -> released` (no intermediate `validated` state): unlike a rule's
expression, a UOM/conversion row has no expression to statically check, so the "explicit but not
executable" gap RUL-FR-005/006 close for a rule does not apply here. `code`/`dimension`/`base_unit` and
`from_code`/`to_code` are never checked against a controlled vocabulary — CALC-FR-006/N6 exist to make
the *evaluator* reject an unresolved code, not to invent a closed dimension/code enum nothing in the
approved baseline declares (AG-15).

Release reuses the `rules.author`/`rules.release` policy actions and the Vault (`object_type="uom"`/
`"uom_conversion"`) rather than inventing a parallel authorization/evidence mechanism for what is,
functionally, another kind of released master data (VLT-FR-001/002/004/009) — the same discipline
`release_rule()` already applies to a `RuleDefinition`.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.rules.models import UnitOfMeasure, UomConversion
from app.modules.signature import service as signature_service
from app.modules.vault import service as vault_service
from app.mutation.errors import MissingSignatureError, NotFoundError, ValidationFailedError
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


def _positive_decimal(value: str, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValidationFailedError(f"{field} is not a valid decimal value: {value!r}") from exc
    if parsed <= 0:
        raise ValidationFailedError(f"{field} must be a positive decimal value", value=value)
    return parsed


async def _resolve_release_signature(
    session: AsyncSession, *, record_type: str, actor_user_id: uuid.UUID,
    record_version: int, record_hash: str, challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    """Same fail-closed pattern as `rules.commands.release_rule`: no Document 106 `(record_type,
    release)` policy row means `SIGNATURE_POLICY_UNRESOLVED`, never an implicit unsigned release
    (SIGP-FR-004)."""
    policy = await signature_service.resolve_signature_requirement(session, record_type=record_type, action="release")
    if not policy.signature_required:
        return None
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"Releasing a {record_type} requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=record_version, record_hash=record_hash,
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


# ---------------------------------------------------------------------------
# UOM — draft
# ---------------------------------------------------------------------------


class CreateUomDraftCommand(CommandEnvelope):
    code: str
    dimension: str
    base_unit: str
    factor: str
    offset: str = "0"
    precision_dp: int
    version: int = 1


async def create_uom_draft(
    session: AsyncSession, cmd: CreateUomDraftCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.code.strip() or not cmd.dimension.strip() or not cmd.base_unit.strip():
        raise ValidationFailedError("code, dimension and base_unit are required and cannot be blank")
    if cmd.precision_dp < 0:
        raise ValidationFailedError("precision_dp cannot be negative", precision_dp=cmd.precision_dp)
    factor = _positive_decimal(cmd.factor, "factor")
    try:
        offset = Decimal(cmd.offset)
    except InvalidOperation as exc:
        raise ValidationFailedError(f"offset is not a valid decimal value: {cmd.offset!r}") from exc

    conflict = (
        await session.execute(
            select(UnitOfMeasure).where(UnitOfMeasure.code == cmd.code, UnitOfMeasure.version == cmd.version)
        )
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError(
            "A draft or released UOM already exists at this code/version", code=cmd.code, version=cmd.version
        )

    uom = UnitOfMeasure(
        code=cmd.code, dimension=cmd.dimension, base_unit=cmd.base_unit, factor=factor, offset=offset,
        precision_dp=cmd.precision_dp, version=cmd.version, status="draft",
    )
    session.add(uom)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="uom", aggregate_id=uom.uom_id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"code": uom.code, "version": uom.version, "status": "draft"},
    )
    await write_outbox_event(
        session, event_type="UomDraftCreated", aggregate_type="uom", aggregate_id=uom.uom_id, aggregate_version=1,
        payload={"id": str(uom.uom_id), "code": uom.code}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="CreateUomDraft", aggregate_type="uom", aggregate_id=uom.uom_id,
        expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=uom.uom_id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# UOM — release
# ---------------------------------------------------------------------------


class ReleaseUomCommand(CommandEnvelope):
    uom_id: uuid.UUID
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def release_uom(session: AsyncSession, cmd: ReleaseUomCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    uom = await session.get(UnitOfMeasure, cmd.uom_id)
    if uom is None:
        raise NotFoundError("UOM not found")
    if uom.status != "draft":
        raise ValidationFailedError("Only a draft UOM can be released", current_status=uom.status)

    canonical = {
        "code": uom.code, "dimension": uom.dimension, "base_unit": uom.base_unit,
        "factor": str(uom.factor), "offset": str(uom.offset), "precision_dp": uom.precision_dp,
        "version": uom.version,
    }
    signature_id = await _resolve_release_signature(
        session, record_type="uom", actor_user_id=actor_user_id, record_version=uom.version,
        record_hash=sha256_hex(canonical), challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_status = uom.status
    uom.status = "released"
    vault_object = await vault_service.release_master(
        session, object_type="uom", business_id=uom.code, actor_user_id=actor_user_id,
        business_version_label=str(uom.version), canonical_payload={**canonical, "signature_id": str(signature_id) if signature_id else None},
    )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="uom", aggregate_id=uom.uom_id, aggregate_version=1,
        action="Released", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"status": old_status}, new_value={"status": uom.status}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="UomReleased", aggregate_type="uom", aggregate_id=uom.uom_id, aggregate_version=1,
        payload={"id": str(uom.uom_id), "code": uom.code, "vault_object_id": str(vault_object.object_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="ReleaseUom", aggregate_type="uom", aggregate_id=uom.uom_id,
        expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=uom.uom_id, resulting_version=1,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# UOM conversion — draft
# ---------------------------------------------------------------------------


class CreateUomConversionDraftCommand(CommandEnvelope):
    from_code: str
    to_code: str
    factor: str
    rounding_stage: str
    effective_from: datetime | None = None
    version: int = 1


async def create_uom_conversion_draft(
    session: AsyncSession, cmd: CreateUomConversionDraftCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.from_code.strip() or not cmd.to_code.strip():
        raise ValidationFailedError("from_code and to_code are required and cannot be blank")
    if cmd.from_code == cmd.to_code:
        raise ValidationFailedError("from_code and to_code must differ — no conversion row is needed within one code")
    if not cmd.rounding_stage.strip():
        raise ValidationFailedError("rounding_stage is required (Document 110 §3)")
    factor = _positive_decimal(cmd.factor, "factor")

    # Referential existence only (any status) -- CALC-FR-006's released-only requirement is the
    # evaluator's own gate (resolve_uom/resolve_conversion), not a draft-time restriction on which UOMs a
    # conversion may be authored between before either side is itself released.
    for code in (cmd.from_code, cmd.to_code):
        known = (await session.execute(select(UnitOfMeasure).where(UnitOfMeasure.code == code))).scalar_one_or_none()
        if known is None:
            raise ValidationFailedError(f"No UOM is drafted at code {code!r} yet", code=code)

    conflict = (
        await session.execute(
            select(UomConversion).where(
                UomConversion.from_code == cmd.from_code, UomConversion.to_code == cmd.to_code,
                UomConversion.version == cmd.version,
            )
        )
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError(
            "A draft or released conversion already exists at this from_code/to_code/version",
            from_code=cmd.from_code, to_code=cmd.to_code, version=cmd.version,
        )

    conversion = UomConversion(
        from_code=cmd.from_code, to_code=cmd.to_code, factor=factor, rounding_stage=cmd.rounding_stage,
        version=cmd.version, effective_from=cmd.effective_from or datetime.now(timezone.utc), status="draft",
    )
    session.add(conversion)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="uom_conversion", aggregate_id=conversion.conversion_id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"from_code": conversion.from_code, "to_code": conversion.to_code, "version": conversion.version, "status": "draft"},
    )
    await write_outbox_event(
        session, event_type="UomConversionDraftCreated", aggregate_type="uom_conversion",
        aggregate_id=conversion.conversion_id, aggregate_version=1,
        payload={"id": str(conversion.conversion_id), "from_code": conversion.from_code, "to_code": conversion.to_code},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="CreateUomConversionDraft", aggregate_type="uom_conversion",
        aggregate_id=conversion.conversion_id, expected_version=None, resulting_version=1,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=conversion.conversion_id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# UOM conversion — release
# ---------------------------------------------------------------------------


class ReleaseUomConversionCommand(CommandEnvelope):
    conversion_id: uuid.UUID
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def release_uom_conversion(
    session: AsyncSession, cmd: ReleaseUomConversionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    conversion = await session.get(UomConversion, cmd.conversion_id)
    if conversion is None:
        raise NotFoundError("UOM conversion not found")
    if conversion.status != "draft":
        raise ValidationFailedError("Only a draft UOM conversion can be released", current_status=conversion.status)

    canonical = {
        "from_code": conversion.from_code, "to_code": conversion.to_code, "factor": str(conversion.factor),
        "rounding_stage": conversion.rounding_stage, "version": conversion.version,
        "effective_from": conversion.effective_from.isoformat(),
    }
    signature_id = await _resolve_release_signature(
        session, record_type="uom_conversion", actor_user_id=actor_user_id, record_version=conversion.version,
        record_hash=sha256_hex(canonical), challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_status = conversion.status
    conversion.status = "released"
    business_id = f"{conversion.from_code}->{conversion.to_code}"
    vault_object = await vault_service.release_master(
        session, object_type="uom_conversion", business_id=business_id, actor_user_id=actor_user_id,
        business_version_label=str(conversion.version),
        canonical_payload={**canonical, "signature_id": str(signature_id) if signature_id else None},
    )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="uom_conversion", aggregate_id=conversion.conversion_id, aggregate_version=1,
        action="Released", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"status": old_status}, new_value={"status": conversion.status}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="UomConversionReleased", aggregate_type="uom_conversion",
        aggregate_id=conversion.conversion_id, aggregate_version=1,
        payload={"id": str(conversion.conversion_id), "vault_object_id": str(vault_object.object_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="ReleaseUomConversion", aggregate_type="uom_conversion",
        aggregate_id=conversion.conversion_id, expected_version=None, resulting_version=1,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=conversion.conversion_id, resulting_version=1,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


async def list_uom_versions(session: AsyncSession, code: str) -> list[UnitOfMeasure]:
    return (
        (await session.execute(select(UnitOfMeasure).where(UnitOfMeasure.code == code).order_by(UnitOfMeasure.version)))
        .scalars()
        .all()
    )
