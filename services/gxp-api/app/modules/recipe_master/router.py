import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.recipe_master import service as recipe_master_service
from app.modules.recipe_master.commands import (
    CreateRecipeDraftCommand,
    ReleaseRecipeVersionCommand,
    SubmitRecipeDraftCommand,
    UpdateRecipeDraftCommand,
    ValidateRecipeDraftCommand,
    create_draft,
    release_recipe_version,
    simulate_draft,
    submit_draft,
    update_draft,
    validate_draft_command,
)
from app.mutation.errors import ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/recipes/v2", tags=["recipe_master"])


def _version_dict(version) -> dict:
    return {
        "recipe_version_id": str(version.id),
        "recipe_family_id": str(version.recipe_family_id),
        "version_no": version.version_no,
        "product_version_id": str(version.product_version_id),
        "site_id": str(version.site_id),
        "batch_size_value": str(version.batch_size_value) if version.batch_size_value is not None else None,
        "batch_size_uom": version.batch_size_uom,
        "lifecycle_state": version.lifecycle_state,
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
        "is_critical": s.is_critical,
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
        "source_type": p.source_type,
        "target_value": str(p.target_value) if p.target_value is not None else None,
        "min_value": str(p.min_value) if p.min_value is not None else None,
        "max_value": str(p.max_value) if p.max_value is not None else None,
        "required": p.required,
        "rule_id": p.rule_id,
        "rule_version": p.rule_version,
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
        await evaluate_policy(session, actor.user_id, action="recipe.author", site_id=None)
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
        await evaluate_policy(session, actor.user_id, action="recipe.author", site_id=None)
        return await validate_draft_command(session, cmd, actor.user_id)


@router.post("/drafts/{recipe_version_id}/simulate")
async def post_simulate_draft(
    recipe_version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="recipe.author", site_id=None)
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
        await evaluate_policy(session, actor.user_id, action="recipe.author", site_id=None)
        return await submit_draft(session, cmd, actor.user_id)


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
        await evaluate_policy(session, actor.user_id, action="recipe.release", site_id=None)
        return await release_recipe_version(session, cmd, actor.user_id)


@router.get("/{recipe_family_id}/versions")
async def get_versions(
    recipe_family_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    await evaluate_policy(session, actor.user_id, action="recipe.view", site_id=None)
    versions = await recipe_master_service.list_versions_for_family(session, recipe_family_id)
    return [_version_dict(v) for v in versions]


@router.get("/versions/{recipe_version_id}")
async def get_version_detail(
    recipe_version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="recipe.view", site_id=None)
    version = await recipe_master_service.get_version(session, recipe_version_id)
    graph = await recipe_master_service.get_graph(session, recipe_version_id)
    body = _version_dict(version)
    body["sections"] = [_section_dict(s) for s in graph["sections"]]
    body["steps"] = [_step_dict(s) for s in graph["steps"]]
    body["dependencies"] = [_dependency_dict(d) for d in graph["dependencies"]]
    body["parameters"] = [_parameter_dict(p) for p in graph["parameters"]]
    return body


@router.get("/versions/{recipe_version_id}/compare/{other_version_id}")
async def get_compare(
    recipe_version_id: uuid.UUID,
    other_version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="recipe.view", site_id=None)
    return await recipe_master_service.compare_versions(session, recipe_version_id, other_version_id)


@router.get("/versions/{recipe_version_id}/issue-eligibility")
async def get_issue_eligibility(
    recipe_version_id: uuid.UUID,
    site: uuid.UUID | None = None,
    date: str | None = None,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="recipe.view", site_id=None)
    version = await recipe_master_service.get_version(session, recipe_version_id)
    findings = await recipe_master_service.validate_completeness(session, recipe_version_id)
    return recipe_master_service.check_issue_eligibility(version, findings)
