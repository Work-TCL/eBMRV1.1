"""SG-057 (architecture rule C-014) — draft/release for MaterialSpecificationVersion, the entity
`approved_supplier_material`/`purchase_requisition`/`purchase_order_ref` (Document 18) and
`recipe_material_requirement` (Document 10, SG-045) key on. Mirrors `product_master.commands`'s
create_draft/release_product_version shape (see migration d2d738c7f191's docstring for why).

SG-185 RESOLVED (2026-09-18, project-owner-directed: option A, "same as product/recipe release" —
scripts/seed.py's SIGNATURE_POLICY_FLOOR now carries `(material_specification_version, release,
Released, QA Releaser, independent=True, signature_required=True, reason_required=False)`, the exact
product_version/release / recipe_version/release shape. `resolve_signature_requirement()` itself still
does not read `required_role_id`/`requires_independent_signer`, so — same bespoke pattern
`release_product_version()`/`release_recipe_version()` use — this command enforces the required role and
independence (drafting author != releaser) itself, against the version's own `Created` audit event.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.audit.models import AuditEvent
from app.modules.iam.models import Role, User
from app.modules.material.models import Material
from app.modules.material_specification.models import (
    FULFILLMENT_PATHS,
    MaterialSpecificationCriterion,
    MaterialSpecificationVersion,
)
from app.modules.policy.service import effective_role_names
from app.modules.qc import commands as qc_commands
from app.modules.signature import service as signature_service
from app.modules.vault import service as vault_service
from app.mutation.errors import (
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    RoleMissingError,
    SodConflictError,
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
    material_id: uuid.UUID
    name: str
    site_id: uuid.UUID
    # Client gap-analysis Phase 5 (2026-10-05): version_no is optional -- when omitted, the next version
    # number for this material's specification is computed automatically, same "stop making callers
    # hand-compute a number the system already knows" reasoning as RecordCalibration's
    # next_calibration_due_date (client requirement #8, Phase 4's equipment work).
    version_no: int | None = None
    acceptance_criteria: dict | None = None


async def create_draft(
    session: AsyncSession, cmd: CreateMaterialSpecDraftCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    material = await session.get(Material, cmd.material_id)
    if material is None:
        raise NotFoundError("Material not found", material_id=str(cmd.material_id))

    # Client gap-analysis Phase 5: material_spec_business_id is no longer a field the caller supplies --
    # the client found a separate, manually-typed "Business ID" confusing and asked for it removed. It is
    # still the real versioning key `UniqueConstraint("material_spec_business_id", "version_no")` and the
    # business-ids picker/URLs depend on, so it's derived deterministically from the material's own code
    # instead of deleted outright -- the same material always produces the same business id.
    business_id = f"{material.code}-SPEC"

    version_no = cmd.version_no
    if version_no is None:
        max_version_no = await session.scalar(
            select(func.max(MaterialSpecificationVersion.version_no)).where(
                MaterialSpecificationVersion.material_spec_business_id == business_id
            )
        )
        version_no = (max_version_no or 0) + 1

    conflict = (
        await session.execute(
            select(MaterialSpecificationVersion).where(
                MaterialSpecificationVersion.material_spec_business_id == business_id,
                MaterialSpecificationVersion.version_no == version_no,
            )
        )
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError(
            "A draft or released version already exists at this material's specification/version_no",
            material_spec_business_id=business_id,
            version_no=version_no,
        )

    version = MaterialSpecificationVersion(
        material_spec_business_id=business_id,
        version_no=version_no,
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

    policy = await signature_service.resolve_signature_requirement(
        session, record_type="material_specification_version", action="release"
    )

    # SG-185 RESOLVED (2026-09-18): same bespoke enforcement release_product_version() uses --
    # resolve_signature_requirement() does not read required_role_id/requires_independent_signer.
    if policy.required_role_id is not None:
        required_role_name = await session.scalar(select(Role.name).where(Role.id == policy.required_role_id))
        if required_role_name not in await effective_role_names(session, actor_user_id, version.site_id):
            raise RoleMissingError(
                "Releasing a material specification version requires the signing role named by the signature policy",
                action="material_spec.release",
                required_role=required_role_name,
            )
    if policy.requires_independent_signer:
        author_id = await session.scalar(
            select(AuditEvent.actor_id)
            .where(
                AuditEvent.aggregate_type == "material_specification_version",
                AuditEvent.aggregate_id == version.id,
                AuditEvent.action == "Created",
            )
            .order_by(AuditEvent.occurred_at)
            .limit(1)
        )
        if author_id is not None and author_id == actor_user_id:
            raise SodConflictError(
                "The author of a material specification version cannot also release it (author != releaser)",
                record_type="material_specification_version",
                action="release",
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

    # Client gap-analysis Phase 5: the immutable release snapshot captures the real structured criteria
    # rows, not the unused `acceptance_criteria` JSONB field (always null now -- see the model's own
    # comment). Once released, these rows are frozen here; add_specification_criterion()/friends below
    # refuse to touch a non-draft version, so this list can never drift from what was actually approved.
    criteria = (
        await session.execute(
            select(MaterialSpecificationCriterion)
            .where(MaterialSpecificationCriterion.material_spec_version_id == version.id)
            .order_by(MaterialSpecificationCriterion.sequence)
        )
    ).scalars().all()

    # Client gap-analysis Phase 6 (2026-10-05): bridges this "spec sheet" to the real QC release-gating
    # pipeline (qc.QcTestSpecification/QcTestDefinition, which `material.commands._missing_required_tests`
    # already reads but which nothing populated from here until now). Every criterion with an explicit
    # in_house/external_lab fulfillment_path becomes a required+release_blocking QcTestDefinition, drafted
    # (not released -- a human QA signature via the existing QC Specifications screen is still required,
    # AG-07/SIG-FR-006) under a QcTestSpecification scoped to this exact released version. A criterion with
    # fulfillment_path == "supplier_coa" (or unset) is deliberately skipped: that case is already covered
    # by the existing lot-level `coa_reliance` override (migration 0126, Client_Decisions_Neededanswers
    # Topic 1/2) -- there is no in-house/external test to schedule for it.
    testable_criteria = [c for c in criteria if c.fulfillment_path in ("in_house", "external_lab")]
    if testable_criteria:
        await qc_commands.create_test_specification_draft(
            session,
            qc_commands.CreateTestSpecificationDraftCommand(
                idempotency_key=str(uuid.uuid4()),
                spec_code=f"{version.material_spec_business_id}-V{version.version_no}-QC",
                scope_type="material",
                scope_version_id=version.id,
                test_definitions=[
                    qc_commands.TestDefinitionInput(
                        test_code=f"CRIT-{c.sequence}",
                        test_name=c.test_name,
                        result_data_type="qualitative",
                        required=True,
                        release_blocking=True,
                    )
                    for c in testable_criteria
                ],
            ),
            actor_user_id,
        )

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
            "criteria": [
                {
                    "sequence": c.sequence,
                    "test_name": c.test_name,
                    "specification_text": c.specification_text,
                    "acceptance_criteria_text": c.acceptance_criteria_text,
                    "fulfillment_path": c.fulfillment_path,
                }
                for c in criteria
            ],
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


# ---------------------------------------------------------------------------
# AddSpecificationCriterion / UpdateSpecificationCriterion / RemoveSpecificationCriterion — client
# gap-analysis Phase 5 (2026-10-05). Specific, intention-revealing commands against a real child table,
# not a generic "replace the whole draft" PATCH (CLAUDE.md §9 forbids a generic CRUD/PATCH-style endpoint
# on a regulated record) -- same reasoning this codebase already applies everywhere else. All three refuse
# to touch a criterion once its parent version has left "draft" (the parent's own lifecycle_state is the
# single source of truth for mutability, not a flag on the row itself).
# ---------------------------------------------------------------------------


async def _load_draft_version(session: AsyncSession, version_id: uuid.UUID) -> MaterialSpecificationVersion:
    version = await session.get(MaterialSpecificationVersion, version_id)
    if version is None:
        raise NotFoundError("Material specification version not found")
    if version.lifecycle_state != "draft":
        raise InvalidTransitionError(
            "Specification criteria can only be added, changed or removed while the version is in draft",
            current_state=version.lifecycle_state,
        )
    return version


def _validate_fulfillment_path(fulfillment_path: str | None) -> None:
    if fulfillment_path is not None and fulfillment_path not in FULFILLMENT_PATHS:
        raise ValidationFailedError(
            "Unrecognized fulfillment_path", fulfillment_path=fulfillment_path, allowed=list(FULFILLMENT_PATHS)
        )


class AddSpecificationCriterionCommand(CommandEnvelope):
    material_spec_version_id: uuid.UUID
    test_name: str
    specification_text: str
    acceptance_criteria_text: str
    fulfillment_path: str | None = None


async def add_specification_criterion(
    session: AsyncSession, cmd: AddSpecificationCriterionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_draft_version(session, cmd.material_spec_version_id)
    _validate_fulfillment_path(cmd.fulfillment_path)

    next_sequence = (
        await session.scalar(
            select(func.max(MaterialSpecificationCriterion.sequence)).where(
                MaterialSpecificationCriterion.material_spec_version_id == version.id
            )
        )
        or 0
    ) + 1

    criterion = MaterialSpecificationCriterion(
        material_spec_version_id=version.id,
        sequence=next_sequence,
        test_name=cmd.test_name,
        specification_text=cmd.specification_text,
        acceptance_criteria_text=cmd.acceptance_criteria_text,
        fulfillment_path=cmd.fulfillment_path,
    )
    session.add(criterion)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=version.site_id,
        aggregate_type="material_specification_criterion",
        aggregate_id=criterion.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={
            "material_spec_version_id": str(version.id),
            "test_name": criterion.test_name,
            "specification_text": criterion.specification_text,
            "acceptance_criteria_text": criterion.acceptance_criteria_text,
            "fulfillment_path": criterion.fulfillment_path,
        },
    )
    await write_outbox_event(
        session,
        event_type="MaterialSpecificationCriterionAdded",
        aggregate_type="material_specification_criterion",
        aggregate_id=criterion.id,
        aggregate_version=1,
        payload={"id": str(criterion.id), "material_spec_version_id": str(version.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=version.site_id,
        command_type="AddSpecificationCriterion",
        aggregate_type="material_specification_criterion",
        aggregate_id=criterion.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=criterion.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


class UpdateSpecificationCriterionCommand(CommandEnvelope):
    criterion_id: uuid.UUID
    expected_version: int
    test_name: str
    specification_text: str
    acceptance_criteria_text: str
    fulfillment_path: str | None = None


async def update_specification_criterion(
    session: AsyncSession, cmd: UpdateSpecificationCriterionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    criterion = await session.get(MaterialSpecificationCriterion, cmd.criterion_id)
    if criterion is None:
        raise NotFoundError("Specification criterion not found")
    if criterion.version != cmd.expected_version:
        raise StaleVersionError(
            "Specification criterion was modified by another actor since it was read",
            expected_version=cmd.expected_version,
            current_version=criterion.version,
        )
    version = await _load_draft_version(session, criterion.material_spec_version_id)
    _validate_fulfillment_path(cmd.fulfillment_path)

    old_value = {
        "test_name": criterion.test_name,
        "specification_text": criterion.specification_text,
        "acceptance_criteria_text": criterion.acceptance_criteria_text,
        "fulfillment_path": criterion.fulfillment_path,
    }
    criterion.test_name = cmd.test_name
    criterion.specification_text = cmd.specification_text
    criterion.acceptance_criteria_text = cmd.acceptance_criteria_text
    criterion.fulfillment_path = cmd.fulfillment_path
    criterion.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=version.site_id,
        aggregate_type="material_specification_criterion",
        aggregate_id=criterion.id,
        aggregate_version=criterion.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value=old_value,
        new_value={
            "test_name": criterion.test_name,
            "specification_text": criterion.specification_text,
            "acceptance_criteria_text": criterion.acceptance_criteria_text,
            "fulfillment_path": criterion.fulfillment_path,
        },
    )
    await write_outbox_event(
        session,
        event_type="MaterialSpecificationCriterionChanged",
        aggregate_type="material_specification_criterion",
        aggregate_id=criterion.id,
        aggregate_version=criterion.version,
        payload={"id": str(criterion.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=version.site_id,
        command_type="UpdateSpecificationCriterion",
        aggregate_type="material_specification_criterion",
        aggregate_id=criterion.id,
        expected_version=cmd.expected_version,
        resulting_version=criterion.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=criterion.id,
        resulting_version=criterion.version,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


class RemoveSpecificationCriterionCommand(CommandEnvelope):
    criterion_id: uuid.UUID


async def remove_specification_criterion(
    session: AsyncSession, cmd: RemoveSpecificationCriterionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    criterion = await session.get(MaterialSpecificationCriterion, cmd.criterion_id)
    if criterion is None:
        raise NotFoundError("Specification criterion not found")
    version = await _load_draft_version(session, criterion.material_spec_version_id)

    old_value = {
        "test_name": criterion.test_name,
        "specification_text": criterion.specification_text,
        "acceptance_criteria_text": criterion.acceptance_criteria_text,
        "fulfillment_path": criterion.fulfillment_path,
    }
    criterion_id = criterion.id
    await session.delete(criterion)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=version.site_id,
        aggregate_type="material_specification_criterion",
        aggregate_id=criterion_id,
        aggregate_version=1,
        action="Deleted",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value=old_value,
    )
    await write_outbox_event(
        session,
        event_type="MaterialSpecificationCriterionRemoved",
        aggregate_type="material_specification_criterion",
        aggregate_id=criterion_id,
        aggregate_version=1,
        payload={"id": str(criterion_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=version.site_id,
        command_type="RemoveSpecificationCriterion",
        aggregate_type="material_specification_criterion",
        aggregate_id=criterion_id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=criterion_id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )
