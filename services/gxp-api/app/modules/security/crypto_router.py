"""Document 65 (SPEC-SEC-005) REST surface, prefix `/security/v1`. The 5 operations Document 65 # 7
lists: rotate a secret, issue / rotate / revoke a certificate, read crypto health. Certificate
issue/rotate/revoke each carry a `Released` Part 11 signature (Document 106 rows 137-139); the secret
rotate is RBAC-only; crypto-health is a read-only GET that fails 503 when a critical key/cert is
missing/expired (KEY-FR-028).
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.security import crypto, crypto_commands as commands
from app.modules.security.crypto_models import CertificateMetadata, SecretMetadata
from app.mutation.errors import CryptoHealthFailedError, NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/security/v1", tags=["security-crypto"])


@router.post("/secrets/{secret_id}/rotate", response_model=MutationReceipt)
async def post_rotate_secret(
    secret_id: uuid.UUID, cmd: commands.RotateSecretCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.secret_id != secret_id:
        raise ValidationFailedError("secret_id in path and body must match")
    async with session.begin():
        if await session.get(SecretMetadata, secret_id) is None:
            raise NotFoundError("Secret metadata not found")
        await evaluate_policy(session, actor.user_id, action="secret.rotate", site_id=None)
        return await commands.rotate_secret(session, cmd, actor.user_id)


@router.post("/certificates:issue", response_model=MutationReceipt)
async def post_issue_certificate(
    cmd: commands.IssueServiceCertificateCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="certificate.issue", site_id=None)
        return await commands.issue_service_certificate(session, cmd, actor.user_id)


@router.post("/certificates/{certificate_id}/rotate", response_model=MutationReceipt)
async def post_rotate_certificate(
    certificate_id: uuid.UUID, cmd: commands.RotateCertificateCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.certificate_id != certificate_id:
        raise ValidationFailedError("certificate_id in path and body must match")
    async with session.begin():
        if await session.get(CertificateMetadata, certificate_id) is None:
            raise NotFoundError("Certificate not found")
        await evaluate_policy(session, actor.user_id, action="certificate.rotate", site_id=None)
        return await commands.rotate_certificate(session, cmd, actor.user_id)


@router.post("/certificates/{certificate_id}/revoke", response_model=MutationReceipt)
async def post_revoke_certificate(
    certificate_id: uuid.UUID, cmd: commands.RevokeCertificateCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.certificate_id != certificate_id:
        raise ValidationFailedError("certificate_id in path and body must match")
    async with session.begin():
        if await session.get(CertificateMetadata, certificate_id) is None:
            raise NotFoundError("Certificate not found")
        await evaluate_policy(session, actor.user_id, action="certificate.revoke", site_id=None)
        return await commands.revoke_certificate(session, cmd, actor.user_id)


@router.get("/crypto-health")
async def get_crypto_health(
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="crypto_health.view", site_id=None)
        report = await crypto.check_crypto_health(session)
    if not report["healthy"]:
        # KEY-FR-028 / Document 65 # 10: fail safe rather than serve a green health check with broken crypto.
        from app.modules.security.telemetry import record_security_event
        await record_security_event("CryptoHealthFailed", {
            "checked_at": report["checked_at"], "findings": report["findings"],
        })
        raise CryptoHealthFailedError("Crypto self-test failed", findings=report["findings"])
    return report
