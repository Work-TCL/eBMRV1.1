"""SG-057 (architecture rule C-014) — draft/release for MaterialSpecificationVersion, the entity
`approved_supplier_material`/`purchase_requisition`/`purchase_order_ref` (Document 18) and
`recipe_material_requirement` (Document 10, SG-045) key on. Mirrors `product_master.commands`'s
create_draft/release_product_version shape (see migration d2d738c7f191's docstring for why).

Release intentionally has no seeded Document 106 signature policy yet (this record type did not exist
before this pass) -- `resolve_signature_requirement()` therefore fails closed with
SIGNATURE_POLICY_UNRESOLVED (SIGP-FR-004), the same state `product_version/release` and `vault_object/
release` were correctly left in before their own project-owner-directed resolutions (SG-035). See
docs/generated/18_SPEC_GAPS.md SG-185.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.material.models import Material
from app.modules.material_specification.models import MaterialSpecificationVersion
from app.modules.signature import service as signature_service
from app.modules.vault import service as vault_service
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


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=None,
        correlation_id=None,
    )


async def _load_for_update(session: AsyncSession, version_id: uuid.UUID, expected_version: int) -> MaterialSpecificationVersion:
    version = await session.get(MaterialSpecificationVersion, version_id)
    if version is None:
        raise NotFoundError("Material specification version not found")
    if version.version != expected_version:
        raise StaleVersionError(
            "Material specification version has changed since expected_version",
            expected_version=expected_version,
            current_version=version.version,
        )
    return version


class CreateMaterialSpecDraftCommand(CommandEnvelope):
    material_spec_business_id: str
    version_no: int
    material_id: uuid.UUID
    name: str
    site_id: uuid.UUID
    acceptance_criteria: dict | None = None


async def create_draft(
    session: AsyncSession, cmd: CreateMaterialSpecDraftCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    conflict = (
        await session.execute(
            select(MaterialSpecificationVersion).where(
                MaterialSpecificationVersion.material_spec_business_id == cmd.material_spec_business_id,
                MaterialSpecificationVersion.version_no == cmd.version_no,
            )
        )
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError(
            "A draft or released version already exists at this material_spec_business_id/version_no",
            material_spec_business_id=cmd.material_spec_business_id,
            version_no=cmd.version_no,
        )

    material = await session.get(Material, cmd.material_id)
    if material is None:
        raise NotFoundError("Material not found", material_id=str(cmd.material_id))

    version = MaterialSpecificationVersion(
        material_spec_business_id=cmd.material_spec_business_id,
        version_no=cmd.version_no,
        material_id=cmd.material_id,
        name=cmd.name,
        site_id=cmd.site_id,
        acceptance_criteria=cmd.acceptance_criteria,
        lifecycle_state="draft",
    )
    session.add(version)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.site_id,
        aggregate_type="material_specification_version",
        aggregate_id=version.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={
            "material_spec_business_id": version.material_spec_business_id,
            "version_no": version.version_no,
        },
    )
    await write_outbox_event(
        session,
        event_type="MaterialSpecificationVersionCreated",
        aggregate_type="material_specification_version",
        aggregate_id=version.id,
        aggregate_version=1,
        payload={"id": str(version.id), "material_spec_business_id": version.material_spec_business_id},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="CreateMaterialSpecDraft",
        aggregate_type="material_specification_version",
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


class ReleaseMaterialSpecVersionCommand(CommandEnvelope):
    material_spec_version_id: uuid.UUID
    expected_version: int
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def release_material_spec_version(
    session: AsyncSession, cmd: ReleaseMaterialSpecVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_for_update(session, cmd.material_spec_version_id, cmd.expected_version)
    if version.lifecycle_state != "draft":
        raise InvalidTransitionError(
            "Only a draft material specification version can be released",
            current_state=version.lifecycle_state,
            requested="released",
        )

    # SG-185 (2026-09-11): no Document 106 policy row exists yet for this brand-new record type --
    # resolve_signature_requirement() fails closed with SIGNATURE_POLICY_UNRESOLVED (SIGP-FR-004) until a
    # project-owner decision seeds one, matching how product_version/release and vault_object/release were
    # correctly left before SG-035.
    policy = await signature_service.resolve_signature_requirement(
        session, record_type="material_specification_version", action="release"
    )

    signature_id = None
    if policy.signature_required:
        if cmd.challenge_id is None or not cmd.reauth_password:
            raise MissingSignatureError(
                "Releasing a material specification version requires a signature", required_meaning=policy.meaning
            )
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
        object_type="material_specification_version",
        business_id=version.material_spec_business_id,
        site_id=version.site_id,
        actor_user_id=actor_user_id,
        business_version_label=str(version.version_no),
        canonical_payload={
            "material_spec_business_id": version.material_spec_business_id,
            "version_no": version.version_no,
            "material_id": str(version.material_id),
            "name": version.name,
            "acceptance_criteria": version.acceptance_criteria,
            "signature_id": str(signature_id) if signature_id else None,
        },
    )
    version.released_vault_object_id = vault_object.object_id
    version.version_hash = vault_object.digest

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=version.site_id,
        aggregate_type="material_specification_version",
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
        event_type="MaterialSpecificationVersionReleased",
        aggregate_type="material_specification_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        payload={"id": str(version.id), "material_spec_business_id": version.material_spec_business_id},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=version.site_id,
        command_type="ReleaseMaterialSpecVersion",
        aggregate_type="material_specification_version",
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
