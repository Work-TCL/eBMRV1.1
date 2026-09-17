"""Document 61 (SPEC-SEC-001) REST surface, prefix `/security/v1`. No `site_id` scoping -- see
models.py's module docstring."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.security import commands
from app.modules.security.commands import _exception_hash, _threat_hash
from app.modules.security.models import SecurityException, SecurityThreat
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/security/v1", tags=["security"])


async def _create_signature_challenge(
    session: AsyncSession, *, actor: AuthenticatedActor, record_type: str, record_id: uuid.UUID,
    record_version: int, record_hash: str, meaning: str,
) -> dict:
    challenge = await create_challenge(
        session, user_id=actor.user_id, record_type=record_type, record_id=record_id,
        record_version=record_version, record_hash=record_hash, meaning=meaning,
    )
    return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/threat-models", response_model=MutationReceipt)
async def post_create_threat_model(
    cmd: commands.CreateThreatModelVersionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="security_threat_model.create", site_id=None)
        return await commands.create_threat_model_version(session, cmd, actor.user_id)


@router.post("/threat-models/{threat_model_version_id}/reviews", response_model=MutationReceipt)
async def post_trigger_threat_model_review(
    threat_model_version_id: uuid.UUID, cmd: commands.TriggerThreatModelReviewCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.threat_model_version_id != threat_model_version_id:
        raise ValidationFailedError("threat_model_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="security_threat_model.trigger_review", site_id=None)
        return await commands.trigger_threat_model_review(session, cmd, actor.user_id)


@router.get("/control-matrix")
async def get_control_matrix(
    threat_model_version_id: uuid.UUID, deployment_profile: str | None = None,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="security_control_matrix.view", site_id=None)
        return await commands.generate_security_control_matrix(session, threat_model_version_id, deployment_profile)


@router.post("/threats", response_model=MutationReceipt)
async def post_register_threat(
    cmd: commands.RegisterThreatCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="security_threat.register", site_id=None)
        return await commands.register_threat(session, cmd, actor.user_id)


@router.post("/threats/{threat_id}/controls", response_model=MutationReceipt)
async def post_map_security_control(
    threat_id: uuid.UUID, cmd: commands.MapSecurityControlCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.threat_id != threat_id:
        raise ValidationFailedError("threat_id in path and body must match")
    async with session.begin():
        threat = await session.get(SecurityThreat, threat_id)
        if threat is None:
            raise NotFoundError("Security threat not found")
        await evaluate_policy(session, actor.user_id, action="security_threat.map_control", site_id=None)
        return await commands.map_security_control(session, cmd, actor.user_id)


@router.post("/threats/{threat_id}/risk-calculations", response_model=MutationReceipt)
async def post_calculate_security_risk(
    threat_id: uuid.UUID, cmd: commands.CalculateSecurityRiskCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.threat_id != threat_id:
        raise ValidationFailedError("threat_id in path and body must match")
    async with session.begin():
        threat = await session.get(SecurityThreat, threat_id)
        if threat is None:
            raise NotFoundError("Security threat not found")
        await evaluate_policy(session, actor.user_id, action="security_threat.calculate_risk", site_id=None)
        return await commands.calculate_security_risk(session, cmd, actor.user_id)


@router.post("/risks/{risk_id}/accept-signature-challenges")
async def post_accept_risk_signature_challenge(
    risk_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        threat = await session.get(SecurityThreat, risk_id)
        if threat is None:
            raise NotFoundError("Security threat not found")
        return await _create_signature_challenge(
            session, actor=actor, record_type="security_threat", record_id=threat.id,
            record_version=threat.version, record_hash=_threat_hash(threat), meaning="Approved",
        )


@router.post("/risks/{risk_id}/accept", response_model=MutationReceipt)
async def post_accept_residual_security_risk(
    risk_id: uuid.UUID, cmd: commands.AcceptResidualSecurityRiskCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.risk_id != risk_id:
        raise ValidationFailedError("risk_id in path and body must match")
    async with session.begin():
        threat = await session.get(SecurityThreat, risk_id)
        if threat is None:
            raise NotFoundError("Security threat not found")
        await evaluate_policy(session, actor.user_id, action="security_threat.accept_risk", site_id=None)
        return await commands.accept_residual_security_risk(session, cmd, actor.user_id)


@router.post("/exceptions", response_model=MutationReceipt)
async def post_request_security_exception(
    cmd: commands.RequestSecurityExceptionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="security_exception.request", site_id=None)
        return await commands.request_security_exception(session, cmd, actor.user_id)


@router.post("/exceptions/{exception_id}/approval-signature-challenges")
async def post_approve_exception_signature_challenge(
    exception_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        exception = await session.get(SecurityException, exception_id)
        if exception is None:
            raise NotFoundError("Security exception not found")
        return await _create_signature_challenge(
            session, actor=actor, record_type="security_exception", record_id=exception.id,
            record_version=exception.version, record_hash=_exception_hash(exception), meaning="Approved",
        )


@router.post("/exceptions/{exception_id}/approve", response_model=MutationReceipt)
async def post_approve_security_exception(
    exception_id: uuid.UUID, cmd: commands.ApproveSecurityExceptionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        exception = await session.get(SecurityException, exception_id)
        if exception is None:
            raise NotFoundError("Security exception not found")
        await evaluate_policy(session, actor.user_id, action="security_exception.approve", site_id=None)
        return await commands.approve_security_exception(session, exception_id, cmd, actor.user_id)


@router.get("/exceptions/{exception_id}")
async def get_security_exception(
    exception_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="security_exception.view", site_id=None)
        exception = await session.get(SecurityException, exception_id)
        if exception is None:
            raise NotFoundError("Security exception not found")
        return {
            "id": str(exception.id), "control_or_requirement": exception.control_or_requirement,
            "risk_assessment_ref": exception.risk_assessment_ref,
            "compensating_controls": exception.compensating_controls,
            "reason": exception.reason,
            "effective_from": exception.effective_from.isoformat(),
            "state": exception.state, "expiry": exception.expiry.isoformat(),
            "approvers": exception.approvers, "remediation_target": exception.remediation_target,
            "signature_id": str(exception.signature_id) if exception.signature_id else None,
            "opened_by": str(exception.opened_by),
            "version": exception.version, "created_at": exception.created_at.isoformat(),
        }
