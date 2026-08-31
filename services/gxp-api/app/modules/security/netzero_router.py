"""Document 66 (SPEC-SEC-006) REST surface, prefix `/security/v1`. Exactly the 2 read-only endpoints
Document 66 # 7 lists: the approved network-flow catalogue and the deployment security profile. No
state-changing endpoint (the catalogue is approved-baseline config, seeded and superseded, never edited
through a generic API). No signature. The 6 zero-trust functions are the `netzero.py` library.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.security.netzero_models import DeploymentSecurityProfile, NetworkFlowDefinition
from app.mutation.errors import NotFoundError

router = APIRouter(prefix="/security/v1", tags=["security-netzero"])


@router.get("/network-flows")
async def get_network_flows(
    deployment_profile: str | None = None, state: str = "EFFECTIVE",
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """NET-FR-027: the documented inbound/outbound flow catalogue per deployment profile."""
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="network_flow.view", site_id=None)
        stmt = select(NetworkFlowDefinition).where(NetworkFlowDefinition.state == state)
        if deployment_profile is not None:
            stmt = stmt.where(NetworkFlowDefinition.deployment_profile == deployment_profile)
        rows = (await session.execute(stmt.order_by(NetworkFlowDefinition.source_zone, NetworkFlowDefinition.port))).scalars().all()
    return {
        "count": len(rows),
        "flows": [
            {
                "id": str(r.id), "deployment_profile": r.deployment_profile,
                "source": {"zone": r.source_zone, "service": r.source_service},
                "destination": {"zone": r.destination_zone, "service": r.destination_service},
                "protocol": r.protocol, "port": r.port, "auth_mechanism": r.auth_mechanism,
                "purpose": r.purpose, "owner": r.owner, "state": r.state, "version": r.version,
            }
            for r in rows
        ],
    }


@router.get("/deployment-security-profile")
async def get_deployment_security_profile(
    profile_name: str | None = None,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="deployment_security_profile.view", site_id=None)
        stmt = select(DeploymentSecurityProfile).where(DeploymentSecurityProfile.state == "EFFECTIVE")
        if profile_name is not None:
            stmt = stmt.where(DeploymentSecurityProfile.profile_name == profile_name)
        rows = (await session.execute(stmt)).scalars().all()
    if profile_name is not None and not rows:
        raise NotFoundError("Deployment security profile not found")
    return {
        "count": len(rows),
        "profiles": [
            {
                "id": str(r.id), "profile_name": r.profile_name, "deployment_profile": r.deployment_profile,
                "ingress_policy": r.ingress_policy, "egress_policy": r.egress_policy,
                "private_endpoints": r.private_endpoints, "namespaces": r.namespaces,
                "service_accounts": r.service_accounts, "container_hardening": r.container_hardening,
                "admin_access_pattern": r.admin_access_pattern, "backup_isolation": r.backup_isolation,
                "network_isolation": r.network_isolation, "state": r.state, "version": r.version,
            }
            for r in rows
        ],
    }
