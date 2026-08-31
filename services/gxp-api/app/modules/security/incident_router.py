"""Document 67 (SPEC-SEC-007) REST surface, prefix `/security/v1`. The 5 operations Document 67 # 7
lists: open an incident, execute containment, preserve evidence, assess GxP impact, close. Only
`close` carries a Part 11 signature (Document 106 row 140 -> Approved, independent QA Releaser).
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.security import incident_commands as commands
from app.modules.security.incident_models import SecurityIncident
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/security/v1", tags=["security-incident"])


@router.post("/incidents", response_model=MutationReceipt)
async def post_open_incident(
    cmd: commands.OpenSecurityIncidentCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="security_incident.open", site_id=None)
        return await commands.open_security_incident(session, cmd, actor.user_id)


@router.post("/incidents/{incident_id}/containment", response_model=MutationReceipt)
async def post_incident_containment(
    incident_id: uuid.UUID, cmd: commands.ExecuteIncidentContainmentCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.incident_id != incident_id:
        raise ValidationFailedError("incident_id in path and body must match")
    async with session.begin():
        if await session.get(SecurityIncident, incident_id) is None:
            raise NotFoundError("Security incident not found")
        await evaluate_policy(session, actor.user_id, action="security_incident.contain", site_id=None)
        return await commands.execute_incident_containment(session, cmd, actor.user_id)


@router.post("/incidents/{incident_id}/evidence", response_model=MutationReceipt)
async def post_incident_evidence(
    incident_id: uuid.UUID, cmd: commands.PreserveForensicEvidenceCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.incident_id != incident_id:
        raise ValidationFailedError("incident_id in path and body must match")
    async with session.begin():
        if await session.get(SecurityIncident, incident_id) is None:
            raise NotFoundError("Security incident not found")
        await evaluate_policy(session, actor.user_id, action="security_incident.evidence", site_id=None)
        return await commands.preserve_forensic_evidence(session, cmd, actor.user_id)


@router.post("/incidents/{incident_id}/gxp-impact", response_model=MutationReceipt)
async def post_incident_gxp_impact(
    incident_id: uuid.UUID, cmd: commands.AssessGxpIncidentImpactCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.incident_id != incident_id:
        raise ValidationFailedError("incident_id in path and body must match")
    async with session.begin():
        if await session.get(SecurityIncident, incident_id) is None:
            raise NotFoundError("Security incident not found")
        await evaluate_policy(session, actor.user_id, action="security_incident.gxp_impact", site_id=None)
        return await commands.assess_gxp_incident_impact(session, cmd, actor.user_id)


@router.post("/incidents/{incident_id}/close", response_model=MutationReceipt)
async def post_close_incident(
    incident_id: uuid.UUID, cmd: commands.CloseSecurityIncidentCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.incident_id != incident_id:
        raise ValidationFailedError("incident_id in path and body must match")
    async with session.begin():
        if await session.get(SecurityIncident, incident_id) is None:
            raise NotFoundError("Security incident not found")
        await evaluate_policy(session, actor.user_id, action="security_incident.close", site_id=None)
        return await commands.close_security_incident(session, cmd, actor.user_id)
