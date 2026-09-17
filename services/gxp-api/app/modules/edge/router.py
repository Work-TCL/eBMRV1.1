"""Document 43 (SPEC-EDGE-001) §8 — exactly the 6 declared server APIs, no invented endpoint.

Human-authenticated routes (`enroll_gateway`, `rotate_gateway_certificate`) go through `get_current_actor`
+ `evaluate_policy` (RBAC/SoD, Document 07) exactly like every other module. The 3 machine-driven routes
(`observations:batch`, `health`, `security-events`) go through `get_service_identity` (SG-120) instead --
there is no `iam.user_site_roles` grant to evaluate for a non-human identity, so the ownership check
`accept_observation_batch`/`report_health`/`report_security_event` already perform (the presented
credential's `subject_ref` must equal the gateway in the URL) *is* this module's authorization decision
for those three, replacing `evaluate_policy` rather than skipping authorization altogether.
"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, AuthenticatedServiceIdentity, get_current_actor, get_service_identity
from app.modules.edge.commands import (
    AcceptObservationBatchCommand,
    EnrollGatewayCommand,
    GatewayEnrollmentResult,
    ObservationBatchResult,
    ReportHealthCommand,
    ReportSecurityEventCommand,
    RotateGatewayCertificateCommand,
    accept_observation_batch,
    enroll_gateway,
    gateway_record_hash,
    get_gateway_configuration,
    report_health,
    report_security_event,
    rotate_gateway_certificate,
)
from app.modules.edge.models import EdgeEnrollmentToken, EdgeGateway
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import create_challenge
from app.mutation.errors import EnrollmentTokenInvalidError, NotFoundError, ValidationFailedError
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/edge/v1", tags=["edge"])


@router.post("/enrollments", response_model=GatewayEnrollmentResult)
async def post_enroll_gateway(
    cmd: EnrollGatewayCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> GatewayEnrollmentResult:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="edge_gateway.enroll", site_id=cmd.site_id)
        return await enroll_gateway(session, cmd, actor.user_id)


class EnrollmentSignatureChallengeRequest(BaseModel):
    bootstrap_token: str
    gateway_fingerprint: str


@router.post("/enrollments/signature-challenges")
async def post_enrollment_signature_challenge(
    body: EnrollmentSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """No gateway row exists yet during enrollment, so the challenge binds to the bootstrap token's own
    row id + the requested fingerprint (`record_version=0`) -- `enroll_gateway` recomputes the identical
    hash from the same two inputs when consuming the challenge."""
    async with session.begin():
        token_hash = sha256_hex(body.bootstrap_token)
        token = (
            await session.execute(select(EdgeEnrollmentToken).where(EdgeEnrollmentToken.token_hash == token_hash))
        ).scalar_one_or_none()
        if token is None or token.status != "unused":
            raise EnrollmentTokenInvalidError("Bootstrap token is invalid, unknown, or already used")
        pre_hash = sha256_hex({"bootstrap_token_id": str(token.id), "gateway_fingerprint": body.gateway_fingerprint})
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="edge_gateway", record_id=token.id, record_version=0,
            record_hash=pre_hash, meaning="Approved",
        )
        return {
            "challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat(),
        }


@router.get("/gateways/{gateway_id}/configuration")
async def get_configuration(gateway_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        return await get_gateway_configuration(session, gateway_id)


@router.post("/gateways/{gateway_id}/observations:batch", response_model=ObservationBatchResult)
async def post_observation_batch(
    gateway_id: uuid.UUID,
    cmd: AcceptObservationBatchCommand,
    session: AsyncSession = Depends(get_session),
    service_identity: AuthenticatedServiceIdentity = Depends(get_service_identity),
) -> ObservationBatchResult:
    async with session.begin():
        return await accept_observation_batch(session, gateway_id, cmd, service_identity)


@router.post("/gateways/{gateway_id}/health", response_model=MutationReceipt)
async def post_health(
    gateway_id: uuid.UUID,
    cmd: ReportHealthCommand,
    session: AsyncSession = Depends(get_session),
    service_identity: AuthenticatedServiceIdentity = Depends(get_service_identity),
) -> MutationReceipt:
    async with session.begin():
        return await report_health(session, gateway_id, cmd, service_identity)


@router.post("/gateways/{gateway_id}/security-events", response_model=MutationReceipt)
async def post_security_event(
    gateway_id: uuid.UUID,
    cmd: ReportSecurityEventCommand,
    session: AsyncSession = Depends(get_session),
    service_identity: AuthenticatedServiceIdentity = Depends(get_service_identity),
) -> MutationReceipt:
    async with session.begin():
        return await report_security_event(session, gateway_id, cmd, service_identity)


class GatewaySignatureChallengeRequest(BaseModel):
    action: str = "certificate_rotation"


_GATEWAY_CHALLENGE_MEANINGS = {"certificate_rotation": "Released"}


@router.post("/gateways/{gateway_id}/signature-challenges")
async def post_gateway_signature_challenge(
    gateway_id: uuid.UUID,
    body: GatewaySignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        gateway = await session.get(EdgeGateway, gateway_id)
        if gateway is None:
            raise NotFoundError("Edge gateway not found")
        meaning = _GATEWAY_CHALLENGE_MEANINGS.get(body.action)
        if meaning is None:
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="edge_gateway", record_id=gateway.id,
            record_version=gateway.version, record_hash=gateway_record_hash(gateway), meaning=meaning,
        )
        return {
            "challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat(),
        }


@router.post("/gateways/{gateway_id}/certificate-rotation", response_model=MutationReceipt)
async def post_rotate_certificate(
    gateway_id: uuid.UUID,
    cmd: RotateGatewayCertificateCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        gateway = await session.get(EdgeGateway, gateway_id)
        if gateway is None:
            raise NotFoundError("Edge gateway not found")
        await evaluate_policy(session, actor.user_id, action="edge_gateway.certificate_rotation", site_id=gateway.site_id)
        return await rotate_gateway_certificate(session, gateway_id, cmd, actor.user_id)


@router.get("/gateways/{gateway_id}")
async def get_gateway(gateway_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    gateway = await session.get(EdgeGateway, gateway_id)
    if gateway is None:
        raise NotFoundError("Edge gateway not found")
    return {
        "id": str(gateway.id),
        "site_id": str(gateway.site_id),
        "host_identity": gateway.host_identity,
        "certificate_fingerprint": gateway.certificate_fingerprint,
        "certificate_expires_at": gateway.certificate_expires_at.isoformat() if gateway.certificate_expires_at else None,
        "enrolled_by_user_id": str(gateway.enrolled_by_user_id),
        "lifecycle_state": gateway.lifecycle_state,
        "last_reported_operational_state": gateway.last_reported_operational_state,
        "active_config_version_id": str(gateway.active_config_version_id) if gateway.active_config_version_id else None,
        "last_health_at": gateway.last_health_at.isoformat() if gateway.last_health_at else None,
        "last_observation_sequence": gateway.last_observation_sequence,
        "version": gateway.version,
        "created_at": gateway.created_at.isoformat(),
    }
