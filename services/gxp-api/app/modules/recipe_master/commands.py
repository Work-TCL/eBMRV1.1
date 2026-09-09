"""Document 10 (SPEC-EBMR-001) — draft/validate/simulate/submit/release for the real Master Recipe /
Master Manufacturing Record. `app/modules/recipe` (the legacy Batch-facing stub) is untouched -- this
module is net-new and additive (see migration d0a1a1bdfaef's docstring).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.audit.models import AuditEvent
from app.modules.iam.models import Role, User
from app.modules.policy.service import effective_role_names
from app.modules.product_master.models import ProductVersion
from app.modules.recipe_master import service as recipe_master_service
from app.modules.recipe_master.models import (
    ALLOWED_TRANSITIONS,
    RecipeEvidenceRequirement,
    RecipeFamily,
    RecipeParameter,
    RecipeSection,
    RecipeStep,
    RecipeStepDependency,
    RecipeVersion,
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


async def _load_for_update(session: AsyncSession, recipe_version_id: uuid.UUID, expected_version: int) -> RecipeVersion:
    result = await session.execute(select(RecipeVersion).where(RecipeVersion.id == recipe_version_id).with_for_update())
    version = result.scalar_one_or_none()
    if version is None:
        raise NotFoundError("Recipe version not found")
    if version.version != expected_version:
        raise StaleVersionError(
            "Recipe version was modified by another actor since it was read",
            expected_version=expected_version,
            current_version=version.version,
        )
    return version


def _assert_transition(version: RecipeVersion, new_state: str) -> None:
    if new_state not in ALLOWED_TRANSITIONS.get(version.lifecycle_state, set()):
        raise InvalidTransitionError(
            "Illegal recipe-version lifecycle transition", current_state=version.lifecycle_state, requested=new_state
        )


class ParameterInput(BaseModel):
    parameter_code: str
    data_type: str
    uom: str | None = None
    source_type: str
    target_value: Decimal | None = None
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    precision_digits: int | None = None
    required: bool = True
    rule_id: str | None = None
    rule_version: str | None = None
    manual_fallback_policy: str | None = None


class EvidenceRequirementInput(BaseModel):
    evidence_type: str
    required_count: int = 1
    allowed_mime_types: str | None = None
    retention_class: str | None = None


class StepInput(BaseModel):
    stable_step_code: str
    section_code: str
    step_type: str
    instruction_text: str | None = None
    sequence_hint: int
    required_role_code: str | None = None
    qualification_policy_id: uuid.UUID | None = None
    signature_policy_id: uuid.UUID | None = None
    exception_policy_id: uuid.UUID | None = None
    is_critical: bool = False
    parameters: list[ParameterInput] = []
    evidence_requirements: list[EvidenceRequirementInput] = []


class SectionInput(BaseModel):
    stable_section_code: str
    name: str
    sequence: int
    area_requirement_id: uuid.UUID | None = None
    parallel_group: str | None = None
    expected_duration_minutes: int | None = None


class DependencyInput(BaseModel):
    predecessor_step_code: str
    successor_step_code: str
    condition_rule_id: str | None = None
    condition_rule_version: str | None = None


async def _get_or_create_family(
    session: AsyncSession, *, product_business_id: str, recipe_code: str, site_id: uuid.UUID, manufacturing_profile_code: str
) -> RecipeFamily:
    existing = (await session.execute(select(RecipeFamily).where(RecipeFamily.recipe_code == recipe_code))).scalar_one_or_none()
    if existing is not None:
        if existing.product_business_id != product_business_id:
            raise ValidationFailedError(
                "recipe_code is already used by a different product_business_id",
                recipe_code=recipe_code,
                existing_product_business_id=existing.product_business_id,
            )
        return existing
    family = RecipeFamily(
        product_business_id=product_business_id,
        recipe_code=recipe_code,
        site_id=site_id,
        manufacturing_profile_code=manufacturing_profile_code,
    )
    session.add(family)
    await session.flush()
    return family


async def _replace_graph(
    session: AsyncSession, recipe_version_id: uuid.UUID, *, sections: list[SectionInput], steps: list[StepInput], dependencies: list[DependencyInput]
) -> None:
    old_steps = (await session.execute(select(RecipeStep).where(RecipeStep.recipe_version_id == recipe_version_id))).scalars().all()
    old_step_ids = [s.id for s in old_steps]
    if old_step_ids:
        for dep in (await session.execute(select(RecipeStepDependency).where(RecipeStepDependency.predecessor_step_id.in_(old_step_ids)))).scalars().all():
            await session.delete(dep)
        for param in (await session.execute(select(RecipeParameter).where(RecipeParameter.step_id.in_(old_step_ids)))).scalars().all():
            await session.delete(param)
        for ev in (await session.execute(select(RecipeEvidenceRequirement).where(RecipeEvidenceRequirement.step_id.in_(old_step_ids)))).scalars().all():
            await session.delete(ev)
    for step in old_steps:
        await session.delete(step)
    old_sections = (await session.execute(select(RecipeSection).where(RecipeSection.recipe_version_id == recipe_version_id))).scalars().all()
    for section in old_sections:
        await session.delete(section)
    await session.flush()

    section_id_by_code: dict[str, uuid.UUID] = {}
    for s in sections:
        row = RecipeSection(
            recipe_version_id=recipe_version_id,
            stable_section_code=s.stable_section_code,
            name=s.name,
            sequence=s.sequence,
            area_requirement_id=s.area_requirement_id,
            parallel_group=s.parallel_group,
            expected_duration_minutes=s.expected_duration_minutes,
        )
        session.add(row)
        await session.flush()
        section_id_by_code[s.stable_section_code] = row.id

    step_id_by_code: dict[str, uuid.UUID] = {}
    for st in steps:
        if st.section_code not in section_id_by_code:
            raise ValidationFailedError(f"step '{st.stable_step_code}' references unknown section_code '{st.section_code}'")
        row = RecipeStep(
            recipe_version_id=recipe_version_id,
            stable_step_code=st.stable_step_code,
            section_id=section_id_by_code[st.section_code],
            step_type=st.step_type,
            instruction_text=st.instruction_text,
            sequence_hint=st.sequence_hint,
            required_role_code=st.required_role_code,
            qualification_policy_id=st.qualification_policy_id,
            signature_policy_id=st.signature_policy_id,
            exception_policy_id=st.exception_policy_id,
            is_critical=st.is_critical,
        )
        session.add(row)
        await session.flush()
        step_id_by_code[st.stable_step_code] = row.id
        for p in st.parameters:
            session.add(
                RecipeParameter(
                    step_id=row.id,
                    parameter_code=p.parameter_code,
                    data_type=p.data_type,
                    uom=p.uom,
                    uom_id=await _resolve_uom_id(session, p.uom),
                    source_type=p.source_type,
                    target_value=p.target_value,
                    min_value=p.min_value,
                    max_value=p.max_value,
                    precision_digits=p.precision_digits,
                    required=p.required,
                    rule_id=p.rule_id,
                    rule_version=p.rule_version,
                    manual_fallback_policy=p.manual_fallback_policy,
                )
            )
        for e in st.evidence_requirements:
            session.add(
                RecipeEvidenceRequirement(
                    step_id=row.id,
                    evidence_type=e.evidence_type,
                    required_count=e.required_count,
                    allowed_mime_types=e.allowed_mime_types,
                    retention_class=e.retention_class,
                )
            )

    for dep in dependencies:
        if dep.predecessor_step_code not in step_id_by_code or dep.successor_step_code not in step_id_by_code:
            raise ValidationFailedError(
                "dependency references an unknown step_code",
                predecessor_step_code=dep.predecessor_step_code,
                successor_step_code=dep.successor_step_code,
            )
        session.add(
            RecipeStepDependency(
                predecessor_step_id=step_id_by_code[dep.predecessor_step_code],
                successor_step_id=step_id_by_code[dep.successor_step_code],
                condition_rule_id=dep.condition_rule_id,
                condition_rule_version=dep.condition_rule_version,
            )
        )


# ---------------------------------------------------------------------------
# CreateDraft
# ---------------------------------------------------------------------------


class CreateRecipeDraftCommand(CommandEnvelope):
    product_business_id: str
    recipe_code: str
    version_no: int
    product_version_id: uuid.UUID
    site_id: uuid.UUID
    manufacturing_profile_code: str
    batch_size_value: Decimal | None = None
    batch_size_uom: str | None = None
    sections: list[SectionInput] = []
    steps: list[StepInput] = []
    dependencies: list[DependencyInput] = []


async def create_draft(session: AsyncSession, cmd: CreateRecipeDraftCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    # Friendly pre-check: gxp_recipe_version.product_version_id is a real FK, so an unknown UUID would
    # otherwise surface as an opaque IntegrityError/500. A non-released product version is allowed at
    # authoring time (batch creation is where "released" is enforced), but a missing one never is.
    product_version = await session.get(ProductVersion, cmd.product_version_id)
    if product_version is None:
        raise NotFoundError("Product version not found", product_version_id=str(cmd.product_version_id))

    family = await _get_or_create_family(
        session,
        product_business_id=cmd.product_business_id,
        recipe_code=cmd.recipe_code,
        site_id=cmd.site_id,
        manufacturing_profile_code=cmd.manufacturing_profile_code,
    )

    conflict = (
        await session.execute(
            select(RecipeVersion).where(RecipeVersion.recipe_family_id == family.id, RecipeVersion.version_no == cmd.version_no)
        )
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError(
            "A draft or released version already exists at this recipe_family/version_no",
            recipe_family_id=str(family.id),
            version_no=cmd.version_no,
        )

    version = RecipeVersion(
        recipe_family_id=family.id,
        version_no=cmd.version_no,
        product_version_id=cmd.product_version_id,
        site_id=cmd.site_id,
        batch_size_value=cmd.batch_size_value,
        batch_size_uom=cmd.batch_size_uom,
        batch_size_uom_id=await _resolve_uom_id(session, cmd.batch_size_uom),
        lifecycle_state="draft",
    )
    session.add(version)
    await session.flush()
    await _replace_graph(session, version.id, sections=cmd.sections, steps=cmd.steps, dependencies=cmd.dependencies)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.site_id,
        aggregate_type="recipe_version",
        aggregate_id=version.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"recipe_family_id": str(family.id), "version_no": version.version_no, "step_count": len(cmd.steps)},
    )
    await write_outbox_event(
        session,
        event_type="RecipeVersionCreated",
        aggregate_type="recipe_version",
        aggregate_id=version.id,
        aggregate_version=1,
        payload={"id": str(version.id), "recipe_family_id": str(family.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="CreateRecipeDraft",
        aggregate_type="recipe_version",
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
# UpdateDraft — wholesale graph replace, draft state only
# ---------------------------------------------------------------------------


class UpdateRecipeDraftCommand(CommandEnvelope):
    recipe_version_id: uuid.UUID
    expected_version: int
    batch_size_value: Decimal | None = None
    batch_size_uom: str | None = None
    sections: list[SectionInput] = []
    steps: list[StepInput] = []
    dependencies: list[DependencyInput] = []


async def update_draft(session: AsyncSession, cmd: UpdateRecipeDraftCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_for_update(session, cmd.recipe_version_id, cmd.expected_version)
    if version.lifecycle_state != "draft":
        raise ValidationFailedError("Only a draft can be edited", current_state=version.lifecycle_state)

    version.batch_size_value = cmd.batch_size_value
    version.batch_size_uom = cmd.batch_size_uom
    version.version += 1
    await _replace_graph(session, version.id, sections=cmd.sections, steps=cmd.steps, dependencies=cmd.dependencies)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=version.site_id,
        aggregate_type="recipe_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"step_count": len(cmd.steps)},
    )
    await write_outbox_event(
        session,
        event_type="RecipeVersionChanged",
        aggregate_type="recipe_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        payload={"id": str(version.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=version.site_id,
        command_type="UpdateRecipeDraft",
        aggregate_type="recipe_version",
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
# Validate (RCP-FR-030) — audit-logged completeness check, non-lifecycle-affecting
# ---------------------------------------------------------------------------


class ValidateRecipeDraftCommand(CommandEnvelope):
    recipe_version_id: uuid.UUID


async def validate_draft_command(session: AsyncSession, cmd: ValidateRecipeDraftCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await recipe_master_service.get_version(session, cmd.recipe_version_id)
    findings = await recipe_master_service.validate_completeness(session, version.id)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=version.site_id,
        aggregate_type="recipe_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"completeness_findings": findings},
    )
    await write_outbox_event(
        session,
        event_type="RecipeValidationFailed" if findings else "RecipeVersionValidated",
        aggregate_type="recipe_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        payload={"id": str(version.id), "complete": not findings},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=version.site_id,
        command_type="ValidateRecipeDraft",
        aggregate_type="recipe_version",
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
# Simulate (RCP-FR-035) — never writes regulated state, mirrors rules.commands.simulate_rule
# ---------------------------------------------------------------------------


async def simulate_draft(session: AsyncSession, *, recipe_version_id: uuid.UUID) -> dict:
    version = await recipe_master_service.get_version(session, recipe_version_id)
    if version.lifecycle_state not in ("draft", "under_review"):
        raise ValidationFailedError(
            "Only a draft or under-review recipe can be simulated", current_state=version.lifecycle_state
        )
    findings = await recipe_master_service.validate_completeness(session, recipe_version_id)
    return {"recipe_version_id": str(recipe_version_id), "complete": not findings, "findings": findings, "simulated": True}


# ---------------------------------------------------------------------------
# SubmitDraft — draft -> under_review
# ---------------------------------------------------------------------------


class SubmitRecipeDraftCommand(CommandEnvelope):
    recipe_version_id: uuid.UUID
    expected_version: int


async def submit_draft(session: AsyncSession, cmd: SubmitRecipeDraftCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_for_update(session, cmd.recipe_version_id, cmd.expected_version)
    _assert_transition(version, "under_review")
    old_state = version.lifecycle_state
    version.lifecycle_state = "under_review"
    version.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=version.site_id,
        aggregate_type="recipe_version",
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
        event_type="RecipeDraftSubmitted",
        aggregate_type="recipe_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        payload={"id": str(version.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=version.site_id,
        command_type="SubmitRecipeDraft",
        aggregate_type="recipe_version",
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
# Release — under_review -> released. Fails closed pending Document 106 (extends SG-035's scope again).
# ---------------------------------------------------------------------------


class ReleaseRecipeVersionCommand(CommandEnvelope):
    recipe_version_id: uuid.UUID
    expected_version: int
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def release_recipe_version(session: AsyncSession, cmd: ReleaseRecipeVersionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_for_update(session, cmd.recipe_version_id, cmd.expected_version)
    _assert_transition(version, "released")

    findings = await recipe_master_service.validate_completeness(session, version.id)
    if findings:
        raise ValidationFailedError("Recipe version is not release-ready", findings=findings)

    policy = await signature_service.resolve_signature_requirement(session, record_type="recipe_version", action="release")

    # SG-035 further-partial (2026-09-08): resolve_signature_requirement() does not read required_role_id
    # / requires_independent_signer, so enforce them here -- the same bespoke pattern IND-001 (ddcp
    # assembly verify) and CON-FR-014 (inventory adjustment approve) use. The recipe version's author is
    # the actor on its own `Created` audit event.
    if policy.required_role_id is not None:
        required_role_name = await session.scalar(select(Role.name).where(Role.id == policy.required_role_id))
        if required_role_name not in await effective_role_names(session, actor_user_id, version.site_id):
            raise RoleMissingError(
                "Releasing a recipe version requires the signing role named by the signature policy",
                action="recipe.release",
                required_role=required_role_name,
            )
    if policy.requires_independent_signer:
        author_id = await session.scalar(
            select(AuditEvent.actor_id)
            .where(
                AuditEvent.aggregate_type == "recipe_version",
                AuditEvent.aggregate_id == version.id,
                AuditEvent.action == "Created",
            )
            .order_by(AuditEvent.occurred_at)
            .limit(1)
        )
        if author_id is not None and author_id == actor_user_id:
            raise SodConflictError(
                "The author of a recipe version cannot also release it (author != releaser)",
                record_type="recipe_version",
                action="release",
            )

    signature_id = None
    if policy.signature_required:
        if cmd.challenge_id is None or not cmd.reauth_password:
            raise MissingSignatureError("Releasing a recipe version requires a signature", required_meaning=policy.meaning)
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

    graph = await recipe_master_service.get_graph(session, version.id)
    vault_object = await vault_service.release_master(
        session,
        object_type="recipe_version",
        business_id=str(version.recipe_family_id),
        site_id=version.site_id,
        actor_user_id=actor_user_id,
        business_version_label=str(version.version_no),
        canonical_payload={
            "recipe_family_id": str(version.recipe_family_id),
            "version_no": version.version_no,
            "product_version_id": str(version.product_version_id),
            "batch_size_value": str(version.batch_size_value) if version.batch_size_value is not None else None,
            "batch_size_uom": version.batch_size_uom,
            "sections": [{"code": s.stable_section_code, "name": s.name, "sequence": s.sequence} for s in graph["sections"]],
            "steps": [{"code": s.stable_step_code, "step_type": s.step_type, "sequence_hint": s.sequence_hint} for s in graph["steps"]],
            "dependencies": [
                {"predecessor": str(d.predecessor_step_id), "successor": str(d.successor_step_id)}
                for d in graph["dependencies"]
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
        aggregate_type="recipe_version",
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
        event_type="RecipeVersionReleased",
        aggregate_type="recipe_version",
        aggregate_id=version.id,
        aggregate_version=version.version,
        payload={"id": str(version.id), "recipe_family_id": str(version.recipe_family_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=version.site_id,
        command_type="ReleaseRecipeVersion",
        aggregate_type="recipe_version",
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
