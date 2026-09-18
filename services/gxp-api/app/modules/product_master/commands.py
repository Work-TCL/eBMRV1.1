"""Document 09 (SPEC-EBMR-000) — draft/submit/release/suspend/reinstate for the real Product/Constituent/
Regulatory Profile Master, plus a completeness-check command. `app/modules/product` (the legacy
Batch/Recipe-facing stub) is untouched -- this module is net-new and additive (see migration
d5d48a66187f's docstring).
"""

import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.audit.models import AuditEvent
from app.modules.equipment import aseptic_commands as aseptic_service
from app.modules.iam.models import Role, User
from app.modules.policy.service import effective_role_names
from app.modules.product_master import service as product_master_service
from app.modules.product_master.models import (
    ALLOWED_TRANSITIONS,
    ConstituentCompatibilityVersion,
    ProductConstituent,
    ProductFamily,
    ProductVersion,
)
from app.modules.rules import service as rules_service
from app.modules.signature import service as signature_service
from app.modules.vault import service as vault_service
from app.mutation.errors import (
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    RoleMissingError,
    SodConflictError,
    StaleVersionError,
    UomUnknownError,
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


async def _validate_sterile_profile(
    session: AsyncSession, sterile_profile_id: uuid.UUID | None, site_id: uuid.UUID
) -> None:
    """PRD-FR-010: when a sterile process profile is declared, it must reference a real, RELEASED row in
    the one sterile-profile registry this codebase actually has -- Document 40's
    `equipment.aseptic_profile_versions` (seed-only master data, same as `aseptic_commands.create_operation`
    already validates against). Closes the gap the DDCP client demo guide flagged: the field previously
    took any raw UUID with no existence check at all. Reads through `aseptic_commands`'s own cross-module
    query function (AG-02/AG-05) rather than importing/querying the equipment module's table directly."""
    if sterile_profile_id is None:
        return
    profile = await aseptic_service.get_released_profile_version(session, sterile_profile_id)
    if profile is None:
        raise ValidationFailedError(
            "sterile_profile_id does not reference an existing sterile process profile (PRD-FR-010)",
            sterile_profile_id=str(sterile_profile_id),
        )
    if profile.state != "RELEASED":
        raise ValidationFailedError(
            "sterile_profile_id references a sterile process profile that is not RELEASED (PRD-FR-010)",
            sterile_profile_id=str(sterile_profile_id),
            state=profile.state,
        )
    if profile.site_id != site_id:
        raise ValidationFailedError(
            "sterile_profile_id references a sterile process profile at a different site (PRD-FR-010)",
            sterile_profile_id=str(sterile_profile_id),
        )


# Known-limitations fix (docs/testing/demo-gujarati/06 §6.8 item 3): no controlled taxonomy for
# combination_product_type exists anywhere in this codebase (confirmed by repo-wide search) -- the DDCP
# module distinguishes device types via manufacturing_profile_code / separate routers, not this field.
# This is a provisional value set pending a real regulatory/business decision -- logged as a SPEC_GAP.
# "other" is the escape hatch: free text is still accepted so nothing already stored breaks.
COMBINATION_PRODUCT_TYPES = {
    "prefilled_syringe", "autoinjector", "inhalation_device", "drug_eluting_device", "other",
}


async def _validate_product_family(session: AsyncSession, product_family_id: uuid.UUID | None) -> None:
    """Known-limitations fix (docs/testing/demo-gujarati/06 §6.8 item 2): product_family_id previously
    accepted any UUID with no existence check -- an orphaned FK. `ProductFamily` already had a real
    model/table with no gap in the schema; only this validation (and the create/list API in this file's
    ProductFamily section below) was missing."""
    if product_family_id is None:
        return
    family = await session.get(ProductFamily, product_family_id)
    if family is None:
        raise ValidationFailedError(
            "product_family_id does not reference an existing product family",
            product_family_id=str(product_family_id),
        )


async def _resolve_uom_id(session: AsyncSession, uom: str | None) -> uuid.UUID | None:
    """SG-146 (remainder, module 4 of 8), MIG-FR-004 expand step."""
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


async def _load_for_update(session: AsyncSession, product_version_id: uuid.UUID, expected_version: int) -> ProductVersion:
    result = await session.execute(
        select(ProductVersion).where(ProductVersion.id == product_version_id).with_for_update()
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise NotFoundError("Product version not found")
    if version.version != expected_version:
        raise StaleVersionError(
            "Product version was modified by another actor since it was read",
            expected_version=expected_version,
            current_version=version.version,
        )
    return version


def _assert_transition(version: ProductVersion, new_state: str) -> None:
    if new_state not in ALLOWED_TRANSITIONS.get(version.lifecycle_state, set()):
        raise InvalidTransitionError(
            "Illegal product-version lifecycle transition", current_state=version.lifecycle_state, requested=new_state
        )


async def _replace_constituents(session: AsyncSession, product_version_id: uuid.UUID, items: list["ConstituentInput"]) -> None:
    old = (
        await session.execute(select(ProductConstituent).where(ProductConstituent.product_version_id == product_version_id))
    ).scalars().all()
    for row in old:
        await session.delete(row)
    await session.flush()
    for item in items:
        session.add(
            ProductConstituent(
                product_version_id=product_version_id,
                constituent_type=item.constituent_type,
                role_code=item.role_code,
                constituent_business_id=item.constituent_business_id,
                constituent_version_id=item.constituent_version_id,
                source_site_id=item.source_site_id,
                tracking_strategy=item.tracking_strategy,
                sequence_no=item.sequence_no,
            )
        )


class ConstituentInput(BaseModel):
    constituent_type: str
    role_code: str | None = None
    constituent_business_id: str
    constituent_version_id: uuid.UUID
    source_site_id: uuid.UUID | None = None
    tracking_strategy: str | None = None
    sequence_no: int | None = None


# ---------------------------------------------------------------------------
# ProductFamily — Known-limitations fix (docs/testing/demo-gujarati/06 §6.8 item 2): the model/table
# already existed (migration d5d48a66187f) with zero CRUD -- product_family_id was an orphaned FK,
# rendered nowhere in the UI. Mirrors `equipment.create_equipment_area`'s exact shape: a simple
# controlled code table, create + list only, no release/lifecycle workflow.
# ---------------------------------------------------------------------------


class CreateProductFamilyCommand(CommandEnvelope):
    family_code: str
    name: str
    profile_code: str | None = None


async def create_product_family(
    session: AsyncSession, cmd: CreateProductFamilyCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.family_code.strip():
        raise ValidationFailedError("family_code is required")
    conflict = (
        await session.execute(select(ProductFamily).where(ProductFamily.family_code == cmd.family_code))
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError(
            "family_code is already in use", family_code=cmd.family_code, existing_id=str(conflict.id)
        )

    family = ProductFamily(family_code=cmd.family_code, name=cmd.name, profile_code=cmd.profile_code, status="active")
    session.add(family)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="product_family", aggregate_id=family.id,
        aggregate_version=1, action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"family_code": family.family_code, "name": family.name},
    )
    await write_outbox_event(
        session, event_type="ProductFamilyCreated", aggregate_type="product_family", aggregate_id=family.id,
        aggregate_version=1, payload={"id": str(family.id), "family_code": family.family_code}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="CreateProductFamily", aggregate_type="product_family",
        aggregate_id=family.id, expected_version=None, resulting_version=1,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=family.id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CreateDraft
# ---------------------------------------------------------------------------


class CreateProductDraftCommand(CommandEnvelope):
    product_business_id: str
    product_code: str
    name: str
    version_no: int
    site_id: uuid.UUID
    manufacturing_profile_code: str
    product_family_id: uuid.UUID | None = None
    combination_product_type: str | None = None
    pmoa_reference: str | None = None
    part4_profile_code: str | None = None
    sterile_profile_id: uuid.UUID | None = None
    finished_tracking_strategy: str | None = None
    udi_applicable: bool | None = None
    strength_value: Decimal | None = None
    strength_uom: str | None = None
    device_model_code: str | None = None
    constituents: list[ConstituentInput] = []


async def create_draft(session: AsyncSession, cmd: CreateProductDraftCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    conflict = (
        await session.execute(
            select(ProductVersion).where(
                ProductVersion.product_business_id == cmd.product_business_id,
                ProductVersion.version_no == cmd.version_no,
            )
        )
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError(
            "A draft or released version already exists at this product_business_id/version_no",
            product_business_id=cmd.product_business_id,
            version_no=cmd.version_no,
        )

    # `ProductVersion` also carries a second, independent UniqueConstraint("product_code", "version_no")
    # (migration d5d48a66187f) -- a different product_business_id reusing the same product_code+version_no
    # was previously left to hit that raw DB constraint uncaught, surfacing as an opaque SYSTEM_FAULT
    # ("An internal error occurred") instead of a clear validation message. Pre-checked here the same way
    # as the business_id/version_no conflict above, so it fails closed with an actionable error instead of
    # crashing.
    code_conflict = (
        await session.execute(
            select(ProductVersion).where(
                ProductVersion.product_code == cmd.product_code,
                ProductVersion.version_no == cmd.version_no,
            )
        )
    ).scalar_one_or_none()
    if code_conflict is not None:
        raise ValidationFailedError(
            "A draft or released version already exists at this product_code/version_no",
            product_code=cmd.product_code,
            version_no=cmd.version_no,
            existing_business_id=code_conflict.product_business_id,
        )

    await _validate_sterile_profile(session, cmd.sterile_profile_id, cmd.site_id)
    await _validate_product_family(session, cmd.product_family_id)
    if cmd.combination_product_type and cmd.combination_product_type not in COMBINATION_PRODUCT_TYPES:
        raise ValidationFailedError(
            "combination_product_type must be one of the provisional taxonomy values (or 'other')",
            combination_product_type=cmd.combination_product_type,
            allowed=sorted(COMBINATION_PRODUCT_TYPES),
        )

    version = ProductVersion(
        product_business_id=cmd.product_business_id,
        version_no=cmd.version_no,
        product_code=cmd.product_code,
        name=cmd.name,
        site_id=cmd.site_id,
        product_family_id=cmd.product_family_id,
        manufacturing_profile_code=cmd.manufacturing_profile_code,
        combination_product_type=cmd.combination_product_type,
        pmoa_reference=cmd.pmoa_reference,
        part4_profile_code=cmd.part4_profile_code,
        sterile_profile_id=cmd.sterile_profile_id,
        finished_tracking_strategy=cmd.finished_tracking_strategy,
        udi_applicable=cmd.udi_applicable,
        strength_value=cmd.strength_value,
        strength_uom=cmd.strength_uom,
        strength_uom_id=await _resolve_uom_id(session, cmd.strength_uom),
        device_model_code=cmd.device_model_code,
        lifecycle_state="draft",
    )
    session.add(version)
    await session.flush()
    await _replace_constituents(session, version.id, cmd.constituents)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.site_id,
        aggregate_type="product_version",
        aggregate_id=version.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"product_business_id": version.product_business_id, "version_no": version.version_no},
    )
    await write_outbox_event(
        session,
        event_type="ProductVersionCreated",
        aggregate_type="product_version",
        aggregate_id=version.id,
        aggregate_version=1,
        payload={"id": str(version.id), "product_business_id": version.product_business_id},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="CreateProductDraft",
        aggregate_type="product_version",
        aggregate_id=version.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=version.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# UpdateDraft — wholesale field + constituent replace, draft state only
# ---------------------------------------------------------------------------


class UpdateProductDraftCommand(CommandEnvelope):
    product_version_id: uuid.UUID
    expected_version: int
    name: str
    manufacturing_profile_code: str
    product_family_id: uuid.UUID | None = None
    combination_product_type: str | None = None
    pmoa_reference: str | None = None
    part4_profile_code: str | None = None
    sterile_profile_id: uuid.UUID | None = None
    finished_tracking_strategy: str | None = None
    udi_applicable: bool | None = None
    strength_value: Decimal | None = None
    strength_uom: str | None = None
    device_model_code: str | None = None
    constituents: list[ConstituentInput] = []


async def update_draft(session: AsyncSession, cmd: UpdateProductDraftCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_for_update(session, cmd.product_version_id, cmd.expected_version)
    if version.lifecycle_state != "draft":
        raise ValidationFailedError("Only a draft can be edited", current_state=version.lifecycle_state)

    await _validate_sterile_profile(session, cmd.sterile_profile_id, version.site_id)
    await _validate_product_family(session, cmd.product_family_id)
    if cmd.combination_product_type and cmd.combination_product_type not in COMBINATION_PRODUCT_TYPES:
        raise ValidationFailedError(
            "combination_product_type must be one of the provisional taxonomy values (or 'other')",
            combination_product_type=cmd.combination_product_type,
            allowed=sorted(COMBINATION_PRODUCT_TYPES),
        )

    version.name = cmd.name
    version.manufacturing_profile_code = cmd.manufacturing_profile_code
    version.product_family_id = cmd.product_family_id
    version.combination_product_type = cmd.combination_product_type
    version.pmoa_reference = cmd.pmoa_reference
    version.part4_profile_code = cmd.part4_profile_code
    version.sterile_profile_id = cmd.sterile_profile_id
    version.finished_tracking_strategy = cmd.finished_tracking_strategy
    version.udi_applicable = cmd.udi_applicable
    version.strength_value = cmd.strength_value
    version.strength_uom = cmd.strength_uom
    version.device_model_code = cmd.device_model_code
    version.version += 1
    await _replace_constituents(session, version.id, cmd.constituents)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=version.site_id,
        aggregate_type="product_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"name": version.name, "constituent_count": len(cmd.constituents)},
    )
    await write_outbox_event(
        session,
        event_type="ProductVersionChanged",
        aggregate_type="product_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        payload={"id": str(version.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=version.site_id,
        command_type="UpdateProductDraft",
        aggregate_type="product_version",
        aggregate_id=version.id,
        expected_version=cmd.expected_version,
        resulting_version=version.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=version.id,
        resulting_version=version.version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# SubmitDraft — draft -> under_review
# ---------------------------------------------------------------------------


class SubmitProductDraftCommand(CommandEnvelope):
    product_version_id: uuid.UUID
    expected_version: int


async def submit_draft(session: AsyncSession, cmd: SubmitProductDraftCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_for_update(session, cmd.product_version_id, cmd.expected_version)
    _assert_transition(version, "under_review")
    old_state = version.lifecycle_state
    version.lifecycle_state = "under_review"
    version.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=version.site_id,
        aggregate_type="product_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"lifecycle_state": old_state},
        new_value={"lifecycle_state": version.lifecycle_state},
    )
    await write_outbox_event(
        session,
        event_type="ProductDraftSubmitted",
        aggregate_type="product_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        payload={"id": str(version.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=version.site_id,
        command_type="SubmitProductDraft",
        aggregate_type="product_version",
        aggregate_id=version.id,
        expected_version=cmd.expected_version,
        resulting_version=version.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=version.id,
        resulting_version=version.version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ValidateCompleteness (PRD-FR-031) — non-lifecycle-affecting, but still an auditable inspection action
# ---------------------------------------------------------------------------


class ValidateCompletenessCommand(CommandEnvelope):
    product_version_id: uuid.UUID


async def validate_completeness_command(
    session: AsyncSession, cmd: ValidateCompletenessCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await product_master_service.get_version(session, cmd.product_version_id)
    constituents = await product_master_service.get_constituents(session, version.id)
    findings = product_master_service.validate_completeness(version, constituents)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=version.site_id,
        aggregate_type="product_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"completeness_findings": findings},
    )
    await write_outbox_event(
        session,
        event_type="ProductVersionCompletenessChecked",
        aggregate_type="product_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        payload={"id": str(version.id), "complete": not findings},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=version.site_id,
        command_type="ValidateProductCompleteness",
        aggregate_type="product_version",
        aggregate_id=version.id,
        expected_version=None,
        resulting_version=version.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=version.id,
        resulting_version=version.version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Release — under_review -> released. Fails closed pending Document 106 (extends SG-035's scope: no
# floor row exists for (product_version, release) either).
# ---------------------------------------------------------------------------


class CompatibilityInput(BaseModel):
    compatibility_code: str
    version_no: int
    drug_constituent_version_id: uuid.UUID
    device_constituent_version_id: uuid.UUID
    interface_constraints: dict | None = None


class ReleaseProductVersionCommand(CommandEnvelope):
    product_version_id: uuid.UUID
    expected_version: int
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    compatibility_versions: list[CompatibilityInput] = []
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def release_product_version(
    session: AsyncSession, cmd: ReleaseProductVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_for_update(session, cmd.product_version_id, cmd.expected_version)
    _assert_transition(version, "released")

    constituents = await product_master_service.get_constituents(session, version.id)
    findings = product_master_service.validate_completeness(version, constituents)
    if findings:
        raise ValidationFailedError("Product version is not release-ready", findings=findings)

    policy = await signature_service.resolve_signature_requirement(session, record_type="product_version", action="release")

    # SG-035 / Decision 2 (2026-09-08): resolve_signature_requirement() does not read required_role_id /
    # requires_independent_signer, so enforce them here -- the same bespoke pattern release_recipe_version()
    # (IND-011) and IND-021 use. The product version's author is the actor on its own `Created` audit
    # event.
    if policy.required_role_id is not None:
        required_role_name = await session.scalar(select(Role.name).where(Role.id == policy.required_role_id))
        if required_role_name not in await effective_role_names(session, actor_user_id, version.site_id):
            raise RoleMissingError(
                "Releasing a product version requires the signing role named by the signature policy",
                action="product.release",
                required_role=required_role_name,
            )
    if policy.requires_independent_signer:
        author_id = await session.scalar(
            select(AuditEvent.actor_id)
            .where(
                AuditEvent.aggregate_type == "product_version",
                AuditEvent.aggregate_id == version.id,
                AuditEvent.action == "Created",
            )
            .order_by(AuditEvent.occurred_at)
            .limit(1)
        )
        if author_id is not None and author_id == actor_user_id:
            raise SodConflictError(
                "The author of a product version cannot also release it (author != releaser)",
                record_type="product_version",
                action="release",
            )

    signature_id = None
    if policy.signature_required:
        if cmd.challenge_id is None or not cmd.reauth_password:
            raise MissingSignatureError("Releasing a product version requires a signature", required_meaning=policy.meaning)
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session,
            challenge_id=cmd.challenge_id,
            user_id=actor_user_id,
            record_version=version.version,
            record_hash=sha256_hex({"id": str(version.id), "version": version.version}),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    old_state = version.lifecycle_state
    version.lifecycle_state = "released"
    version.effective_from = cmd.effective_from or datetime.now(timezone.utc)
    version.effective_to = cmd.effective_to
    version.version += 1

    vault_object = await vault_service.release_master(
        session,
        object_type="product_version",
        business_id=version.product_business_id,
        site_id=version.site_id,
        actor_user_id=actor_user_id,
        business_version_label=str(version.version_no),
        canonical_payload={
            "product_business_id": version.product_business_id,
            "product_code": version.product_code,
            "version_no": version.version_no,
            "name": version.name,
            "manufacturing_profile_code": version.manufacturing_profile_code,
            "constituents": [
                {
                    "constituent_type": c.constituent_type,
                    "constituent_business_id": c.constituent_business_id,
                    "constituent_version_id": str(c.constituent_version_id),
                }
                for c in constituents
            ],
            "signature_id": str(signature_id) if signature_id else None,
        },
    )
    version.released_vault_object_id = vault_object.object_id
    version.version_hash = vault_object.digest

    for item in cmd.compatibility_versions:
        await _create_and_release_compatibility(session, item, actor_user_id=actor_user_id, site_id=version.site_id)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=version.site_id,
        aggregate_type="product_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        action="Released",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"lifecycle_state": old_state},
        new_value={"lifecycle_state": version.lifecycle_state},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="ProductVersionReleased",
        aggregate_type="product_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        payload={"id": str(version.id), "product_business_id": version.product_business_id},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=version.site_id,
        command_type="ReleaseProductVersion",
        aggregate_type="product_version",
        aggregate_id=version.id,
        expected_version=cmd.expected_version,
        resulting_version=version.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=version.id,
        resulting_version=version.version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


async def _create_and_release_compatibility(
    session: AsyncSession, item: CompatibilityInput, *, actor_user_id: uuid.UUID, site_id: uuid.UUID
) -> None:
    """PRD-FR-016 — released alongside the parent product_version's own release, since the API catalogue
    declares no independent create/release endpoint for compatibility versions this pass."""
    compat = ConstituentCompatibilityVersion(
        compatibility_code=item.compatibility_code,
        version_no=item.version_no,
        drug_constituent_version_id=item.drug_constituent_version_id,
        device_constituent_version_id=item.device_constituent_version_id,
        interface_constraints=item.interface_constraints,
        status="released",
        effective_from=datetime.now(timezone.utc),
    )
    session.add(compat)
    await session.flush()
    vault_object = await vault_service.release_master(
        session,
        object_type="constituent_compatibility",
        business_id=item.compatibility_code,
        site_id=site_id,
        actor_user_id=actor_user_id,
        business_version_label=str(item.version_no),
        canonical_payload={
            "compatibility_code": item.compatibility_code,
            "version_no": item.version_no,
            "drug_constituent_version_id": str(item.drug_constituent_version_id),
            "device_constituent_version_id": str(item.device_constituent_version_id),
            "interface_constraints": item.interface_constraints,
        },
    )
    compat.vault_object_id = vault_object.object_id


# ---------------------------------------------------------------------------
# Suspend / Reinstate (PRD-FR-029)
# ---------------------------------------------------------------------------


class SuspendProductVersionCommand(CommandEnvelope):
    product_version_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


class ReinstateProductVersionCommand(CommandEnvelope):
    product_version_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def _transition_with_signature(
    session: AsyncSession,
    cmd: "SuspendProductVersionCommand | ReinstateProductVersionCommand | ObsoleteProductVersionCommand | SupersedeProductVersionCommand",
    actor_user_id: uuid.UUID,
    *,
    new_state: str,
    action_name: str,
    event_type: str,
    signature_action: str,
    extra_updates: "Callable[[AsyncSession, ProductVersion, object], Awaitable[dict]] | None" = None,
    # Document 106 §8 gives two different independence targets depending on action family: "resume/
    # unhold/release-hold" (reinstate) is independent of "the person who caused the condition" (whoever
    # set the current pre-transition state); "cancel/abort/void" (obsolete/supersede -- see SG-208) is
    # independent of "the author" (the version's own Created event actor, same target release() uses).
    independence_reference: str = "cause",
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_for_update(session, cmd.product_version_id, cmd.expected_version)
    _assert_transition(version, new_state)

    field_updates: dict = {}
    if extra_updates is not None:
        field_updates = await extra_updates(session, version, cmd)

    policy = await signature_service.resolve_signature_requirement(
        session, record_type="product_version", action=signature_action
    )
    signature_id = None
    if policy.signature_required:
        # product_version/reinstate -- SG-035 pair 5, RESOLVED 2026-09-11 (PHASE_3_DEFERRED_DECISIONS.md
        # item B). Document 106 section 9 has no row for this action; the project owner authored one from
        # the section 8 "resume/unhold/release-hold" family: `Approved`, "QA authority that owns the hold
        # reason" -> `QA Releaser`, independent of "the person who caused the condition" -- resolved here
        # as the actor of this product version's own most recent audit event that set
        # `lifecycle_state` to its *current* (pre-transition) value, the same audit-trail lookup pattern
        # `release_product_version()` uses against the `Created` event. `product_version/suspend` has
        # `required_role_id=None` and `requires_independent_signer=False`, so `enforce_signer_policy()` is
        # a no-op for it -- this block is safe for both actions sharing this helper.
        disqualified_subject_ids: tuple = ()
        if policy.requires_independent_signer:
            if independence_reference == "author":
                cause_actor_id = await session.scalar(
                    select(AuditEvent.actor_id)
                    .where(
                        AuditEvent.aggregate_type == "product_version",
                        AuditEvent.aggregate_id == version.id,
                        AuditEvent.action == "Created",
                    )
                    .order_by(AuditEvent.occurred_at)
                    .limit(1)
                )
            else:
                cause_actor_id = await session.scalar(
                    select(AuditEvent.actor_id)
                    .where(
                        AuditEvent.aggregate_type == "product_version",
                        AuditEvent.aggregate_id == version.id,
                        AuditEvent.action == "Changed",
                        AuditEvent.new_value["lifecycle_state"].astext == version.lifecycle_state,
                    )
                    .order_by(AuditEvent.occurred_at.desc())
                    .limit(1)
                )
            disqualified_subject_ids = (cause_actor_id,) if cause_actor_id else ()
        await signature_service.enforce_signer_policy(
            session, policy=policy, actor_user_id=actor_user_id, site_id=version.site_id,
            action_label=f"product_version.{signature_action}", disqualified_subject_ids=disqualified_subject_ids,
        )
        if cmd.challenge_id is None or not cmd.reauth_password:
            raise MissingSignatureError(f"{action_name} requires a signature", required_meaning=policy.meaning)
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session,
            challenge_id=cmd.challenge_id,
            user_id=actor_user_id,
            record_version=version.version,
            record_hash=sha256_hex({"id": str(version.id), "version": version.version}),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    old_state = version.lifecycle_state
    version.lifecycle_state = new_state
    new_value: dict = {"lifecycle_state": new_state}
    for field_name, field_value in field_updates.items():
        setattr(version, field_name, field_value)
        new_value[field_name] = str(field_value) if field_value is not None else None
    version.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=version.site_id,
        aggregate_type="product_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"lifecycle_state": old_state},
        new_value=new_value,
        reason=cmd.reason,
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type=event_type,
        aggregate_type="product_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        payload={"id": str(version.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=version.site_id,
        command_type=action_name.replace(" ", ""),
        aggregate_type="product_version",
        aggregate_id=version.id,
        expected_version=cmd.expected_version,
        resulting_version=version.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=version.id,
        resulting_version=version.version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


async def suspend_product_version(
    session: AsyncSession, cmd: SuspendProductVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    return await _transition_with_signature(
        session,
        cmd,
        actor_user_id,
        new_state="suspended",
        action_name="Suspend",
        event_type="ProductVersionSuspended",
        signature_action="suspend",
    )


async def reinstate_product_version(
    session: AsyncSession, cmd: ReinstateProductVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    return await _transition_with_signature(
        session,
        cmd,
        actor_user_id,
        new_state="released",
        action_name="Reinstate",
        event_type="ProductVersionReinstated",
        signature_action="reinstate",
    )


# ---------------------------------------------------------------------------
# Obsolete / Supersede -- known-limitations fix (docs/testing/demo-gujarati/06 §6.8 item 1):
# `obsolete`/`superseded` were already legal ALLOWED_TRANSITIONS edges from `released` with no command
# ever reaching them. Both share `_transition_with_signature` exactly like suspend/reinstate above.
# Document 106 section 9 has no row for either; the closest section 8 action-family match is
# "cancel/abort/void" (Approved, QA Releaser, independent of the author) -- see SG-208 in SPEC_GAPS.md.
# `independence_reference="author"` below checks against the version's own `Created` audit event.
# ---------------------------------------------------------------------------


class ObsoleteProductVersionCommand(CommandEnvelope):
    product_version_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


class SupersedeProductVersionCommand(CommandEnvelope):
    product_version_id: uuid.UUID
    expected_version: int
    reason: str
    superseding_version_id: uuid.UUID
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def obsolete_product_version(
    session: AsyncSession, cmd: ObsoleteProductVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    return await _transition_with_signature(
        session,
        cmd,
        actor_user_id,
        new_state="obsolete",
        action_name="Obsolete",
        event_type="ProductVersionObsoleted",
        signature_action="obsolete",
        independence_reference="author",
    )


async def _resolve_supersession(
    session: AsyncSession, version: ProductVersion, cmd: SupersedeProductVersionCommand
) -> dict:
    if cmd.superseding_version_id == version.id:
        raise ValidationFailedError("A product version cannot supersede itself")
    successor = await session.get(ProductVersion, cmd.superseding_version_id)
    if successor is None:
        raise NotFoundError("superseding_version_id does not reference an existing product version")
    if successor.product_business_id != version.product_business_id:
        raise ValidationFailedError(
            "superseding_version_id must reference another version of the same product",
            product_business_id=version.product_business_id,
        )
    if successor.lifecycle_state != "released":
        raise ValidationFailedError(
            "superseding_version_id must reference a released product version",
            state=successor.lifecycle_state,
        )
    return {"superseded_by_version_id": successor.id}


async def supersede_product_version(
    session: AsyncSession, cmd: SupersedeProductVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    return await _transition_with_signature(
        session,
        cmd,
        actor_user_id,
        new_state="superseded",
        action_name="Supersede",
        event_type="ProductVersionSuperseded",
        signature_action="supersede",
        extra_updates=_resolve_supersession,
        independence_reference="author",
    )
