import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.release import service as release_service
from app.modules.release.commands import (
    EvaluateReleaseScopeCommand,
    ReleaseDecisionCommand,
    evaluate_release_scope,
    hold_scope,
    reject_scope,
    release_scope_decision,
)
from app.modules.signature.service import create_challenge
from app.mutation.errors import ValidationFailedError
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/release/v1", tags=["release"])

# Document 106 rows 32-34 (SPEC-EBMR-006) -- meaning is literally `Released` for all three actions in
# the spec table (not e.g. `Rejected` for reject), taken verbatim rather than "corrected" per CLAUDE.md's
# no-guessing rule. The RBAC action name each challenge is checked against differs per action so a QA
# Reviewer (who holds `release.hold` but not `release.release`/`release.reject`) can request a hold
# challenge but not a release/reject one.
_CHALLENGE_MEANINGS = {"release": "Released", "hold": "Released", "reject": "Released"}
_CHALLENGE_PERMISSIONS = {"release": "release.release", "hold": "release.hold", "reject": "release.reject"}


class ReleaseSignatureChallengeRequest(BaseModel):
    action: str


def _scope_dict(scope) -> dict:
    return {
        "scope_id": str(scope.id),
        "site_id": str(scope.site_id),
        "scope_type": scope.scope_type,
        "target_id": str(scope.scope_id),
        "product_version_id": str(scope.product_version_id),
        "batch_id": str(scope.batch_id),
        "state": scope.state,
        "version": scope.version,
        "current_evaluation_id": str(scope.current_evaluation_id) if scope.current_evaluation_id else None,
        "released_vault_object_id": str(scope.released_vault_object_id) if scope.released_vault_object_id else None,
        "decision_at": scope.decision_at.isoformat() if scope.decision_at else None,
    }


def _evaluation_dict(evaluation) -> dict:
    return {
        "evaluation_id": str(evaluation.id),
        "scope_version": evaluation.scope_version,
        "evaluated_batch_version": evaluation.evaluated_batch_version,
        "blockers": evaluation.blockers,
        "warnings": evaluation.warnings,
        "eligible": evaluation.eligible,
        "evaluation_time": evaluation.evaluation_time.isoformat(),
    }


def _decision_dict(decision) -> dict:
    return {
        "decision_id": str(decision.id),
        "decision_code": decision.decision_code,
        "reason": decision.reason,
        "signature_id": str(decision.signature_id) if decision.signature_id else None,
        "decision_time": decision.decision_time.isoformat(),
        "release_package_hash": decision.release_package_hash,
    }


@router.post("/scopes/{scope_type}/{target_id}/evaluate", response_model=MutationReceipt)
async def post_evaluate(
    scope_type: str,
    target_id: uuid.UUID,
    cmd: EvaluateReleaseScopeCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.scope_type != scope_type or cmd.scope_id != target_id:
        raise ValidationFailedError("scope_type/target_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="release.evaluate", site_id=None)
        return await evaluate_release_scope(session, cmd, actor.user_id)


@router.get("/scopes/{scope_id}/eligibility")
async def get_eligibility(
    scope_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="release.view", site_id=None)
    scope = await release_service.get_scope(session, scope_id)
    evaluation = await release_service.get_current_evaluation(session, scope)
    return {"scope": _scope_dict(scope), "evaluation": _evaluation_dict(evaluation) if evaluation else None}


@router.post("/scopes/{scope_id}/signature-challenges")
async def post_signature_challenge(
    scope_id: uuid.UUID,
    body: ReleaseSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Issue the Part 11 challenge for `POST .../release|hold|reject`. record_version + record_hash match
    release_scope_decision()/_decide_terminal_or_hold()'s own consume_challenge call exactly
    (SIG-FR-012/013/014) -- same shape as recipe_master's `POST /drafts/{id}/signature-challenges`
    (SG-035 precedent)."""
    permission = _CHALLENGE_PERMISSIONS.get(body.action)
    meaning = _CHALLENGE_MEANINGS.get(body.action)
    if permission is None or meaning is None:
        raise ValidationFailedError("Unknown or unsigned action", action=body.action)
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action=permission, site_id=None)
        scope = await release_service.get_scope(session, scope_id)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="release_scope", record_id=scope.id,
            record_version=scope.version, record_hash=sha256_hex({"id": str(scope.id), "version": scope.version}),
            meaning=meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/scopes/{scope_id}/release", response_model=MutationReceipt)
async def post_release(
    scope_id: uuid.UUID,
    cmd: ReleaseDecisionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.scope_id != scope_id:
        raise ValidationFailedError("scope_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="release.release", site_id=None)
        return await release_scope_decision(session, cmd, actor.user_id)


@router.post("/scopes/{scope_id}/hold", response_model=MutationReceipt)
async def post_hold(
    scope_id: uuid.UUID,
    cmd: ReleaseDecisionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.scope_id != scope_id:
        raise ValidationFailedError("scope_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="release.hold", site_id=None)
        return await hold_scope(session, cmd, actor.user_id)


@router.post("/scopes/{scope_id}/reject", response_model=MutationReceipt)
async def post_reject(
    scope_id: uuid.UUID,
    cmd: ReleaseDecisionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.scope_id != scope_id:
        raise ValidationFailedError("scope_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="release.reject", site_id=None)
        return await reject_scope(session, cmd, actor.user_id)


@router.get("/scopes/{scope_id}/package")
async def get_package(
    scope_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """REL-FR-009/028 (partial): the release package itself (evaluation + decisions); DDCP-specific
    constituent/compatibility detail (Document 15 §8) is not built -- see SG-056."""
    await evaluate_policy(session, actor.user_id, action="release.view", site_id=None)
    scope = await release_service.get_scope(session, scope_id)
    evaluation = await release_service.get_current_evaluation(session, scope)
    decisions = await release_service.get_decisions(session, scope_id)
    return {
        "scope": _scope_dict(scope),
        "evaluation": _evaluation_dict(evaluation) if evaluation else None,
        "decisions": [_decision_dict(d) for d in decisions],
    }


# Registered last, deliberately: this path shape (2 wildcard segments) is structurally identical to
# every /scopes/{scope_id}/<literal> route above it (eligibility/signature-challenges/release/hold/
# reject/package), and FastAPI/Starlette matches routes in registration order, not by specificity --
# putting this first would have swallowed every one of those requests (e.g. GET .../<id>/eligibility
# would bind target_id="eligibility" and 422 on the UUID conversion instead of ever reaching the real
# handler). Registering it last lets every literal-suffix route claim its own requests first.
@router.get("/scopes/{scope_type}/{target_id}")
async def get_scope_by_target(
    scope_type: str,
    target_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict | None:
    """Read-only lookup for a release scope already created against this target, if one exists --
    returns null rather than 404 when none does yet (the UI's own signal to fall back to `POST
    .../evaluate` and create one). Without this, the only way to load a scope was `evaluate_release_
    scope()`, which correctly refuses to re-evaluate a `released`/`rejected` scope
    (InvalidTransitionError) -- meaning a batch that had already been released or rejected became
    permanently unviewable from this page, with no way back in at all."""
    await evaluate_policy(session, actor.user_id, action="release.view", site_id=None)
    scope = await release_service.get_scope_for_target(session, scope_type, target_id)
    return _scope_dict(scope) if scope is not None else None
