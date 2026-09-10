"""Document 62 (SPEC-SEC-002) REST surface, prefix `/security/v1`. `GET /auth/login`/`GET /auth/callback`
are not built this pass (no live external IdP -- see identity_models.py module docstring); the real
`/auth/token` + `/auth/logout` wiring lives in `app/modules/iam/router.py`.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.security import identity_commands as commands
from app.modules.security.identity_models import ApplicationSession, SecurityServiceIdentity
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/security/v1", tags=["security-identity"])


@router.post("/identity-providers", response_model=MutationReceipt)
async def post_create_identity_provider(
    cmd: commands.CreateIdentityProviderConfigCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="identity_provider.create", site_id=None)
        return await commands.create_identity_provider_config(session, cmd, actor.user_id)


@router.post("/identity-providers/{identity_provider_config_id}/mappings", response_model=MutationReceipt)
async def post_map_external_identity(
    identity_provider_config_id: uuid.UUID, cmd: commands.MapExternalIdentityCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.identity_provider_config_id != identity_provider_config_id:
        raise ValidationFailedError("identity_provider_config_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="identity_provider.map_identity", site_id=None)
        return await commands.map_external_identity(session, cmd, actor.user_id)


@router.post("/identity-providers/{identity_provider_config_id}/tokens:validate")
async def post_validate_identity_token(
    identity_provider_config_id: uuid.UUID, cmd: commands.ValidateIdentityTokenCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    if cmd.identity_provider_config_id != identity_provider_config_id:
        raise ValidationFailedError("identity_provider_config_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="identity_provider.validate_token", site_id=None)
        return await commands.validate_identity_token(session, cmd)


@router.get("/mfa-requirement")
async def get_mfa_requirement(
    user_id: uuid.UUID, site_id: uuid.UUID | None = None, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="application_session.view", site_id=None)
        return await commands.evaluate_mfa_requirement(session, user_id, site_id)


@router.post("/sessions/{session_id}/revoke", response_model=MutationReceipt)
async def post_revoke_session(
    session_id: uuid.UUID, cmd: commands.RevokeSessionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.session_id != session_id:
        raise ValidationFailedError("session_id in path and body must match")
    async with session.begin():
        app_session = await session.get(ApplicationSession, session_id)
        if app_session is None:
            raise NotFoundError("Application session not found")
        await evaluate_policy(session, actor.user_id, action="application_session.revoke", site_id=None)
        return await commands.revoke_session(session, cmd, actor.user_id)


@router.post("/sessions:revoke-all", response_model=MutationReceipt)
async def post_revoke_user_sessions(
    cmd: commands.RevokeUserSessionsCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="application_session.revoke", site_id=None)
        return await commands.revoke_user_sessions(session, cmd, actor.user_id)


@router.get("/sessions/{session_id}/freshness")
async def get_session_freshness(
    session_id: uuid.UUID, required_age_seconds: int, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="application_session.view", site_id=None)
        return await commands.require_fresh_authentication(session, session_id, required_age_seconds)


@router.post("/service-identities", response_model=MutationReceipt)
async def post_provision_service_identity(
    cmd: commands.ProvisionServiceIdentityCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="service_identity.provision", site_id=cmd.site_id)
        return await commands.provision_service_identity(session, cmd, actor.user_id)


@router.post("/service-identities/{service_identity_id}/revoke", response_model=MutationReceipt)
async def post_revoke_service_identity(
    service_identity_id: uuid.UUID, cmd: commands.RevokeServiceIdentityCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.service_identity_id != service_identity_id:
        raise ValidationFailedError("service_identity_id in path and body must match")
    async with session.begin():
        identity = await session.get(SecurityServiceIdentity, service_identity_id)
        if identity is None:
            raise NotFoundError("Service identity not found")
        await evaluate_policy(session, actor.user_id, action="service_identity.revoke", site_id=identity.site_id)
        return await commands.revoke_service_identity(session, cmd, actor.user_id)
