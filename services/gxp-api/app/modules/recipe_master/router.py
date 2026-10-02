import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.iam.models import Site
from app.modules.material_specification.models import MaterialSpecificationVersion
from app.modules.policy.service import evaluate_policy, resolve_site_scope
from app.modules.product_master.models import ProductVersion
from app.modules.qc.models import QcTestSpecification
from app.modules.recipe_master import service as recipe_master_service
from app.modules.recipe_master.models import EquipmentClass, RecipeFamily
from app.modules.recipe_master.commands import (
    CreateEquipmentClassCommand,
    CreateRecipeDraftCommand,
    ObsoleteRecipeVersionCommand,
    ReinstateRecipeVersionCommand,
    ReleaseRecipeVersionCommand,
    SubmitRecipeDraftCommand,
    SupersedeRecipeVersionCommand,
    SuspendRecipeVersionCommand,
    UpdateRecipeDraftCommand,
    ValidateRecipeDraftCommand,
    create_draft,
    create_equipment_class,
    obsolete_recipe_version,
    reinstate_recipe_version,
    release_recipe_version,
    simulate_draft,
    submit_draft,
    supersede_recipe_version,
    suspend_recipe_version,
    update_draft,
    validate_draft_command,
)
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/recipes/v2", tags=["recipe_master"])


class RecipeSignatureChallengeRequest(BaseModel):
    action: str  # "release" / "suspend" / "reinstate" / "obsolete" / "supersede"


_CHALLENGE_MEANINGS = {
    "release": "Released",
    # Known-limitations fix (docs/testing/demo-gujarati/07 §7.9 item 1): no Document 106 section 9 row
    # exists for any of the four; shape mirrors product_master's equivalent fix exactly (see SG-208).
    "suspend": "Performed",
    "reinstate": "Approved",
    "obsolete": "Approved",
    "supersede": "Approved",
}


def _version_dict(version, product_version: ProductVersion | None = None, site: Site | None = None) -> dict:
    return {
        "recipe_version_id": str(version.id),
        "recipe_family_id": str(version.recipe_family_id),
        "version_no": version.version_no,
        "product_version_id": str(version.product_version_id),
        "product_code": product_version.product_code if product_version else None,
        "product_name": product_version.name if product_version else None,
        "site_id": str(version.site_id),
        "site_code": site.code if site else None,
        "site_name": site.name if site else None,
        "batch_size_value": str(version.batch_size_value) if version.batch_size_value is not None else None,
        "batch_size_uom": version.batch_size_uom,
        "batch_size_uom_id": str(version.batch_size_uom_id) if version.batch_size_uom_id else None,
        "lifecycle_state": version.lifecycle_state,
        "superseded_by_version_id": str(version.superseded_by_version_id) if version.superseded_by_version_id else None,
        "effective_from": version.effective_from.isoformat() if version.effective_from else None,
        "effective_to": version.effective_to.isoformat() if version.effective_to else None,
        "graph_version": version.graph_version,
        "released_vault_object_id": str(version.released_vault_object_id) if version.released_vault_object_id else None,
        "version_hash": version.version_hash,
        "version": version.version,
    }


def _section_dict(s) -> dict:
    return {
        "id": str(s.id),
        "stable_section_code": s.stable_section_code,
        "name": s.name,
        "sequence": s.sequence,
        # No backing entity anywhere in the codebase (tracked SPEC_GAP) -- raw technical value only,
        # never resolved to a name.
        "area_requirement_id": str(s.area_requirement_id) if s.area_requirement_id else None,
        "parallel_group": s.parallel_group,
        "expected_duration_minutes": s.expected_duration_minutes,
    }


def _step_dict(s) -> dict:
    return {
        "id": str(s.id),
        "stable_step_code": s.stable_step_code,
        "section_id": str(s.section_id),
        "step_type": s.step_type,
        "instruction_text": s.instruction_text,
        "sequence_hint": s.sequence_hint,
        "required_role_code": s.required_role_code,
        "required_qualification_code": s.required_qualification_code,
        "is_critical": s.is_critical,
        "expected_hold_duration_minutes": s.expected_hold_duration_minutes,
        # No backing entity anywhere in the codebase (tracked SPEC_GAP) -- raw technical values only,
        # never resolved to a name.
        "qualification_policy_id": str(s.qualification_policy_id) if s.qualification_policy_id else None,
        "signature_policy_id": str(s.signature_policy_id) if s.signature_policy_id else None,
        "exception_policy_id": str(s.exception_policy_id) if s.exception_policy_id else None,
    }


def _dependency_dict(d) -> dict:
    return {
        "id": str(d.id),
        "predecessor_step_id": str(d.predecessor_step_id),
        "successor_step_id": str(d.successor_step_id),
        "condition_rule_id": d.condition_rule_id,
        "condition_rule_version": d.condition_rule_version,
    }


def _parameter_dict(p) -> dict:
    return {
        "id": str(p.id),
        "step_id": str(p.step_id),
        "parameter_code": p.parameter_code,
        "data_type": p.data_type,
        "uom": p.uom,
        "uom_id": str(p.uom_id) if p.uom_id else None,
        "source_type": p.source_type,
        "target_value": str(p.target_value) if p.target_value is not None else None,
        "min_value": str(p.min_value) if p.min_value is not None else None,
        "max_value": str(p.max_value) if p.max_value is not None else None,
        "precision_digits": p.precision_digits,
        "required": p.required,
        "rule_id": p.rule_id,
        "rule_version": p.rule_version,
        "manual_fallback_policy": p.manual_fallback_policy,
    }


def _evidence_requirement_dict(e) -> dict:
    return {
        "id": str(e.id),
        "step_id": str(e.step_id),
        "evidence_type": e.evidence_type,
        "required_count": e.required_count,
        "allowed_mime_types": e.allowed_mime_types,
        "retention_class": e.retention_class,
    }


def _material_requirement_dict(m, material_spec: MaterialSpecificationVersion | None = None) -> dict:
    return {
        "id": str(m.id),
        "step_id": str(m.step_id),
        "material_spec_version_id": str(m.material_spec_version_id),
        "material_spec_business_id": material_spec.material_spec_business_id if material_spec else None,
        "material_name": material_spec.name if material_spec else None,
        "target_value": str(m.target_value) if m.target_value is not None else None,
        "min_value": str(m.min_value) if m.min_value is not None else None,
        "max_value": str(m.max_value) if m.max_value is not None else None,
        "uom": m.uom,
        "uom_id": str(m.uom_id) if m.uom_id else None,
        "alternative_material_spec_version_id": (
            str(m.alternative_material_spec_version_id) if m.alternative_material_spec_version_id else None
        ),
        "substitution_allowed": m.substitution_allowed,
        "consume_mode": m.consume_mode,
        "genealogy_required": m.genealogy_required,
    }


def _equipment_requirement_dict(e, equipment_class: EquipmentClass | None = None) -> dict:
    return {
        "id": str(e.id),
        "step_id": str(e.step_id),
        "equipment_class": e.equipment_class,
        "equipment_class_id": str(e.equipment_class_id) if e.equipment_class_id else None,
        "equipment_class_name": equipment_class.name if equipment_class else None,
        "exact_equipment_optional": e.exact_equipment_optional,
        "require_current_calibration": e.require_current_calibration,
        "require_current_qualification": e.require_current_qualification,
        "require_current_cleaning": e.require_current_cleaning,
    }


def _qc_requirement_dict(q, spec: QcTestSpecification | None = None) -> dict:
    return {
        "id": str(q.id),
        "step_id": str(q.step_id),
        "qc_test_specification_id": str(q.qc_test_specification_id),
        "spec_code": spec.spec_code if spec else None,
        "spec_version_no": spec.version_no if spec else None,
        "required": q.required,
    }


@router.post("/drafts", response_model=MutationReceipt)
async def post_create_draft(
    cmd: CreateRecipeDraftCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="recipe.author", site_id=cmd.site_id)
        return await create_draft(session, cmd, actor.user_id)


@router.put("/drafts/{recipe_version_id}", response_model=MutationReceipt)
async def put_update_draft(
    recipe_version_id: uuid.UUID,
    cmd: UpdateRecipeDraftCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.recipe_version_id != recipe_version_id:
        raise ValidationFailedError("recipe_version_id in path and body must match")
    async with session.begin():
        version = await recipe_master_service.get_version(session, recipe_version_id)
        await evaluate_policy(session, actor.user_id, action="recipe.author", site_id=version.site_id)
        return await update_draft(session, cmd, actor.user_id)


@router.post("/drafts/{recipe_version_id}/validate", response_model=MutationReceipt)
async def post_validate_draft(
    recipe_version_id: uuid.UUID,
    cmd: ValidateRecipeDraftCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.recipe_version_id != recipe_version_id:
        raise ValidationFailedError("recipe_version_id in path and body must match")
    async with session.begin():
        version = await recipe_master_service.get_version(session, recipe_version_id)
        await evaluate_policy(session, actor.user_id, action="recipe.author", site_id=version.site_id)
        return await validate_draft_command(session, cmd, actor.user_id)


@router.post("/drafts/{recipe_version_id}/simulate")
async def post_simulate_draft(
    recipe_version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    version = await recipe_master_service.get_version(session, recipe_version_id)
    await evaluate_policy(session, actor.user_id, action="recipe.author", site_id=version.site_id)
    return await simulate_draft(session, recipe_version_id=recipe_version_id)


@router.post("/drafts/{recipe_version_id}/submit", response_model=MutationReceipt)
async def post_submit_draft(
    recipe_version_id: uuid.UUID,
    cmd: SubmitRecipeDraftCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.recipe_version_id != recipe_version_id:
        raise ValidationFailedError("recipe_version_id in path and body must match")
    async with session.begin():
        version = await recipe_master_service.get_version(session, recipe_version_id)
        await evaluate_policy(session, actor.user_id, action="recipe.author", site_id=version.site_id)
        return await submit_draft(session, cmd, actor.user_id)


@router.post("/drafts/{recipe_version_id}/signature-challenges")
async def post_release_signature_challenge(
    recipe_version_id: uuid.UUID,
    body: RecipeSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Issue the Part 11 challenge for `POST .../release`. record_version + record_hash match
    release_recipe_version()'s own consume_challenge call exactly (SIG-FR-012/013/014)."""
    async with session.begin():
        version = await recipe_master_service.get_version(session, recipe_version_id)
        await evaluate_policy(session, actor.user_id, action="recipe.release", site_id=version.site_id)
        meaning = _CHALLENGE_MEANINGS.get(body.action)
        if meaning is None:
            raise ValidationFailedError("Unknown or unsigned action", action=body.action)
        challenge = await create_challenge(
            session,
            user_id=actor.user_id,
            record_type="recipe_version",
            record_id=version.id,
            record_version=version.version,
            record_hash=sha256_hex({"id": str(version.id), "version": version.version}),
            meaning=meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/drafts/{recipe_version_id}/release", response_model=MutationReceipt)
async def post_release_draft(
    recipe_version_id: uuid.UUID,
    cmd: ReleaseRecipeVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.recipe_version_id != recipe_version_id:
        raise ValidationFailedError("recipe_version_id in path and body must match")
    async with session.begin():
        version = await recipe_master_service.get_version(session, recipe_version_id)
        await evaluate_policy(session, actor.user_id, action="recipe.release", site_id=version.site_id)
        return await release_recipe_version(session, cmd, actor.user_id)


@router.post("/{recipe_version_id}/suspend", response_model=MutationReceipt)
async def post_suspend(
    recipe_version_id: uuid.UUID,
    cmd: SuspendRecipeVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    """Known-limitations fix (docs/testing/demo-gujarati/07 §7.9 item 1)."""
    if cmd.recipe_version_id != recipe_version_id:
        raise ValidationFailedError("recipe_version_id in path and body must match")
    async with session.begin():
        version = await recipe_master_service.get_version(session, recipe_version_id)
        await evaluate_policy(session, actor.user_id, action="recipe.suspend", site_id=version.site_id)
        return await suspend_recipe_version(session, cmd, actor.user_id)


@router.post("/{recipe_version_id}/reinstate", response_model=MutationReceipt)
async def post_reinstate(
    recipe_version_id: uuid.UUID,
    cmd: ReinstateRecipeVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    """Known-limitations fix (docs/testing/demo-gujarati/07 §7.9 item 1)."""
    if cmd.recipe_version_id != recipe_version_id:
        raise ValidationFailedError("recipe_version_id in path and body must match")
    async with session.begin():
        version = await recipe_master_service.get_version(session, recipe_version_id)
        await evaluate_policy(session, actor.user_id, action="recipe.suspend", site_id=version.site_id)
        return await reinstate_recipe_version(session, cmd, actor.user_id)


@router.post("/{recipe_version_id}/obsolete", response_model=MutationReceipt)
async def post_obsolete(
    recipe_version_id: uuid.UUID,
    cmd: ObsoleteRecipeVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    """Known-limitations fix (docs/testing/demo-gujarati/07 §7.9 item 1)."""
    if cmd.recipe_version_id != recipe_version_id:
        raise ValidationFailedError("recipe_version_id in path and body must match")
    async with session.begin():
        version = await recipe_master_service.get_version(session, recipe_version_id)
        await evaluate_policy(session, actor.user_id, action="recipe.suspend", site_id=version.site_id)
        return await obsolete_recipe_version(session, cmd, actor.user_id)


@router.post("/{recipe_version_id}/supersede", response_model=MutationReceipt)
async def post_supersede(
    recipe_version_id: uuid.UUID,
    cmd: SupersedeRecipeVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    """Known-limitations fix (docs/testing/demo-gujarati/07 §7.9 item 1). `superseding_version_id` must
    reference another RELEASED version of the same recipe family; enforced in supersede_recipe_version()."""
    if cmd.recipe_version_id != recipe_version_id:
        raise ValidationFailedError("recipe_version_id in path and body must match")
    async with session.begin():
        version = await recipe_master_service.get_version(session, recipe_version_id)
        await evaluate_policy(session, actor.user_id, action="recipe.suspend", site_id=version.site_id)
        return await supersede_recipe_version(session, cmd, actor.user_id)


@router.get("/families")
async def get_families(
    site_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    """Top-level Recipe Master listing (recipe_master/service.py::list_recipe_families). Registered ahead
    of `/{recipe_family_id}/versions` so "families" is never parsed as a recipe_family_id UUID.

    SG-213 fix: `gxp_recipe_family.site_id` is a non-nullable per-row site, so this was gating on
    "holds recipe.view anywhere" and then returning every site's recipe families. resolve_site_scope
    turns an omitted site_id into only the sites the actor actually holds the action at."""
    site_scope = await resolve_site_scope(session, actor.user_id, site_id, action="recipe.view")
    return await recipe_master_service.list_recipe_families(session, site_scope)


def _equipment_class_dict(k) -> dict:
    return {"id": str(k.id), "class_code": k.class_code, "name": k.name, "description": k.description, "status": k.status}


@router.get("/equipment-classes")
async def get_equipment_classes(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    """Known-limitations fix (docs/testing/demo-gujarati/07 §7.9 item 4) -- registered ahead of
    `/{recipe_family_id}/versions` so "equipment-classes" is never parsed as a recipe_family_id UUID.

    SG-213 reviewed: gxp_equipment_class (models.py) has no site_id column -- it is a global controlled
    vocabulary shared across sites (same table equipment/router.py's SG-218 comment documents as
    cross-module master data), not a per-site record. site_id=None is correct."""
    await evaluate_policy(session, actor.user_id, action="recipe.view", site_id=None)
    classes = await recipe_master_service.list_equipment_classes(session)
    return [_equipment_class_dict(k) for k in classes]


@router.post("/equipment-classes", response_model=MutationReceipt)
async def post_create_equipment_class(
    cmd: CreateEquipmentClassCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        # SG-213 reviewed: gxp_equipment_class has no site_id column and CreateEquipmentClassCommand has
        # no site_id field -- same global-vocabulary reasoning as get_equipment_classes above.
        # site_id=None is correct.
        await evaluate_policy(session, actor.user_id, action="recipe.author", site_id=None)
        return await create_equipment_class(session, cmd, actor.user_id)


@router.get("/{recipe_family_id}/versions")
async def get_versions(
    recipe_family_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    family = await session.get(RecipeFamily, recipe_family_id)
    if family is None:
        raise NotFoundError("Recipe family not found")
    await evaluate_policy(session, actor.user_id, action="recipe.view", site_id=family.site_id)
    versions = await recipe_master_service.list_versions_for_family(session, recipe_family_id)
    return [_version_dict(v) for v in versions]


@router.get("/versions/{recipe_version_id}")
async def get_version_detail(
    recipe_version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    version = await recipe_master_service.get_version(session, recipe_version_id)
    await evaluate_policy(session, actor.user_id, action="recipe.view", site_id=version.site_id)
    graph = await recipe_master_service.get_graph(session, recipe_version_id)

    product_version = await session.get(ProductVersion, version.product_version_id)
    site = await session.get(Site, version.site_id)

    material_spec_ids = {m.material_spec_version_id for m in graph["material_requirements"]}
    material_specs_by_id: dict = {}
    if material_spec_ids:
        rows = (
            await session.execute(
                select(MaterialSpecificationVersion).where(MaterialSpecificationVersion.id.in_(material_spec_ids))
            )
        ).scalars().all()
        material_specs_by_id = {ms.id: ms for ms in rows}

    equipment_class_ids = {e.equipment_class_id for e in graph["equipment_requirements"] if e.equipment_class_id}
    equipment_classes_by_id: dict = {}
    if equipment_class_ids:
        rows = (
            await session.execute(select(EquipmentClass).where(EquipmentClass.id.in_(equipment_class_ids)))
        ).scalars().all()
        equipment_classes_by_id = {k.id: k for k in rows}

    qc_spec_ids = {q.qc_test_specification_id for q in graph["qc_requirements"]}
    qc_specs_by_id: dict = {}
    if qc_spec_ids:
        rows = (
            await session.execute(select(QcTestSpecification).where(QcTestSpecification.id.in_(qc_spec_ids)))
        ).scalars().all()
        qc_specs_by_id = {q.id: q for q in rows}

    body = _version_dict(version, product_version, site)
    body["sections"] = [_section_dict(s) for s in graph["sections"]]
    body["steps"] = [_step_dict(s) for s in graph["steps"]]
    body["dependencies"] = [_dependency_dict(d) for d in graph["dependencies"]]
    body["parameters"] = [_parameter_dict(p) for p in graph["parameters"]]
    body["evidence_requirements"] = [_evidence_requirement_dict(e) for e in graph["evidence"]]
    body["material_requirements"] = [
        _material_requirement_dict(m, material_specs_by_id.get(m.material_spec_version_id))
        for m in graph["material_requirements"]
    ]
    body["equipment_requirements"] = [
        _equipment_requirement_dict(e, equipment_classes_by_id.get(e.equipment_class_id))
        for e in graph["equipment_requirements"]
    ]
    body["qc_requirements"] = [
        _qc_requirement_dict(q, qc_specs_by_id.get(q.qc_test_specification_id)) for q in graph["qc_requirements"]
    ]
    return body


@router.get("/versions/{recipe_version_id}/compare/{other_version_id}")
async def get_compare(
    recipe_version_id: uuid.UUID,
    other_version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    version = await recipe_master_service.get_version(session, recipe_version_id)
    await evaluate_policy(session, actor.user_id, action="recipe.view", site_id=version.site_id)
    return await recipe_master_service.compare_versions(session, recipe_version_id, other_version_id)


@router.get("/versions/{recipe_version_id}/issue-eligibility")
async def get_issue_eligibility(
    recipe_version_id: uuid.UUID,
    site: uuid.UUID | None = None,
    date: str | None = None,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    version = await recipe_master_service.get_version(session, recipe_version_id)
    await evaluate_policy(session, actor.user_id, action="recipe.view", site_id=version.site_id)
    findings = await recipe_master_service.validate_completeness(session, recipe_version_id)
    return recipe_master_service.check_issue_eligibility(version, findings)
