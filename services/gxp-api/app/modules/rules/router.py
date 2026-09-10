import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.rules import service as rules_service
from app.modules.rules.commands import (
    CreateRuleDraftCommand,
    EvaluateRuleCommand,
    ReleaseRuleCommand,
    ValidateRuleCommand,
    create_draft,
    evaluate_rule,
    release_rule,
    simulate_rule,
    validate_rule,
)
from app.modules.rules.uom_commands import (
    CreateUomConversionDraftCommand,
    CreateUomDraftCommand,
    ReleaseUomConversionCommand,
    ReleaseUomCommand,
    create_uom_conversion_draft,
    create_uom_draft,
    list_uom_versions,
    release_uom,
    release_uom_conversion,
)
from app.modules.rules.models import RuleDefinition
from app.modules.signature.service import create_challenge, resolve_signature_requirement
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/rules/v1", tags=["rules"])


def _rule_dict(rule) -> dict:
    return {
        "rule_object_id": str(rule.rule_object_id),
        "rule_id": rule.rule_id,
        "rule_type": rule.rule_type,
        "semantic_version": rule.semantic_version,
        "status": rule.status,
        "effective_from": rule.effective_from.isoformat() if rule.effective_from else None,
        "effective_to": rule.effective_to.isoformat() if rule.effective_to else None,
        "expression_ast": rule.expression_ast,
        "input_contract": rule.input_contract,
        "output_contract": rule.output_contract,
        "unit_policy": rule.unit_policy,
        "precision_policy": rule.precision_policy,
        "rounding_policy": rule.rounding_policy,
        "released_vault_object_id": str(rule.released_vault_object_id) if rule.released_vault_object_id else None,
    }


@router.post("/drafts", response_model=MutationReceipt)
async def post_create_draft(
    cmd: CreateRuleDraftCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="rules.author", site_id=None)
        return await create_draft(session, cmd, actor.user_id)


@router.post("/{rule_object_id}/validate", response_model=MutationReceipt)
async def post_validate_rule(
    rule_object_id: uuid.UUID,
    cmd: ValidateRuleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.rule_object_id != rule_object_id:
        raise ValidationFailedError("rule_object_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="rules.author", site_id=None)
        return await validate_rule(session, cmd, actor.user_id)


class SimulateRuleRequest(BaseModel):
    inputs: dict


@router.post("/{rule_object_id}/simulate")
async def post_simulate_rule(
    rule_object_id: uuid.UUID,
    body: SimulateRuleRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="rules.author", site_id=None)
    return await simulate_rule(session, rule_object_id=rule_object_id, inputs=body.inputs)


@router.post("/{rule_object_id}/release", response_model=MutationReceipt)
async def post_release_rule(
    rule_object_id: uuid.UUID,
    cmd: ReleaseRuleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.rule_object_id != rule_object_id:
        raise ValidationFailedError("rule_object_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="rules.release", site_id=None)
        return await release_rule(session, cmd, actor.user_id)


class RuleReleaseChallengeRequest(BaseModel):
    action: str = "release"


@router.post("/{rule_object_id}/signature-challenges")
async def post_rule_release_signature_challenge(
    rule_object_id: uuid.UUID,
    body: RuleReleaseChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """SG-035 (2026-09-10): obtain a challenge for `rule/release` (Document 106 section 9 row 6). Bound
    to the same canonical (rule_id, semantic_version, expression_ast) hash at version 1 that
    `release_rule()` re-computes at consume time."""
    if body.action != "release":
        raise ValidationFailedError("Unknown or unsigned action", action=body.action)
    async with session.begin():
        rule = await session.get(RuleDefinition, rule_object_id)
        if rule is None:
            raise NotFoundError("Rule not found")
        policy = await resolve_signature_requirement(session, record_type="rule", action="release")
        canonical = {
            "rule_id": rule.rule_id,
            "semantic_version": rule.semantic_version,
            "expression_ast": rule.expression_ast,
        }
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="rule", record_id=rule.rule_object_id,
            record_version=1, record_hash=sha256_hex(canonical), meaning=policy.meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.get("")
async def get_released_rules(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    """Picker data for any field that references a rule by its `rule_id` (e.g. Recipe Master's
    dependency `condition_rule_id`). One row per rule with a currently-effective released version.
    Registered ahead of `GET /{rule_id}/versions` so an empty path is never parsed as a rule_id."""
    await evaluate_policy(session, actor.user_id, action="rules.evaluate", site_id=None)
    return await rules_service.list_released_rules(session)


@router.get("/{rule_id}/versions")
async def get_versions(
    rule_id: str,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    await evaluate_policy(session, actor.user_id, action="rules.evaluate", site_id=None)
    versions = await rules_service.list_versions(session, rule_id)
    return [_rule_dict(r) for r in versions]


@router.post("/evaluate", response_model=MutationReceipt)
async def post_evaluate(
    cmd: EvaluateRuleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="rules.evaluate", site_id=None)
        return await evaluate_rule(session, cmd, actor.user_id)


# ---------------------------------------------------------------------------
# Document 110 (SG-146) — the UOM/conversion authoring surface. Reuses the `rules.author`/`rules.release`
# policy actions: authoring released reference data for the calculation engine is the same capability
# area as authoring the rules themselves, not a separate permission concept.
# ---------------------------------------------------------------------------


def _uom_dict(uom) -> dict:
    return {
        "uom_id": str(uom.uom_id),
        "code": uom.code,
        "dimension": uom.dimension,
        "base_unit": uom.base_unit,
        "factor": str(uom.factor),
        "offset": str(uom.offset),
        "precision_dp": uom.precision_dp,
        "status": uom.status,
        "version": uom.version,
    }


@router.post("/uom/drafts", response_model=MutationReceipt)
async def post_create_uom_draft(
    cmd: CreateUomDraftCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="rules.author", site_id=None)
        return await create_uom_draft(session, cmd, actor.user_id)


@router.post("/uom/{uom_id}/release", response_model=MutationReceipt)
async def post_release_uom(
    uom_id: uuid.UUID,
    cmd: ReleaseUomCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.uom_id != uom_id:
        raise ValidationFailedError("uom_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="rules.release", site_id=None)
        return await release_uom(session, cmd, actor.user_id)


@router.get("/uom/{code}/versions")
async def get_uom_versions(
    code: str,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    await evaluate_policy(session, actor.user_id, action="rules.evaluate", site_id=None)
    versions = await list_uom_versions(session, code)
    return [_uom_dict(u) for u in versions]


@router.post("/uom-conversions/drafts", response_model=MutationReceipt)
async def post_create_uom_conversion_draft(
    cmd: CreateUomConversionDraftCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="rules.author", site_id=None)
        return await create_uom_conversion_draft(session, cmd, actor.user_id)


@router.post("/uom-conversions/{conversion_id}/release", response_model=MutationReceipt)
async def post_release_uom_conversion(
    conversion_id: uuid.UUID,
    cmd: ReleaseUomConversionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.conversion_id != conversion_id:
        raise ValidationFailedError("conversion_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="rules.release", site_id=None)
        return await release_uom_conversion(session, cmd, actor.user_id)
