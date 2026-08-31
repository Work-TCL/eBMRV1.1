import uuid

from fastapi import APIRouter, Depends
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
from app.mutation.errors import ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/release/v1", tags=["release"])


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
