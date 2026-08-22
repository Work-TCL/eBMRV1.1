import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.signature.models import Signature, SignatureChallenge, SignaturePolicy
from app.mutation.errors import SignatureChallengeInvalidError


async def resolve_policy(
    session: AsyncSession, *, record_type: str, action: str
) -> SignaturePolicy | None:
    """Signature requirement comes from policy data, never a code conditional (AG-07 / SIG-FR-004)."""
    result = await session.execute(
        select(SignaturePolicy).where(
            SignaturePolicy.record_type == record_type, SignaturePolicy.action == action
        )
    )
    return result.scalar_one_or_none()


async def create_challenge(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    record_type: str,
    record_id: uuid.UUID,
    record_version: int,
    record_hash: str,
    meaning: str,
) -> SignatureChallenge:
    challenge = SignatureChallenge(
        user_id=user_id,
        record_type=record_type,
        record_id=record_id,
        record_version=record_version,
        record_hash=record_hash,
        meaning=meaning,
        nonce=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.signature_challenge_expire_minutes),
    )
    session.add(challenge)
    await session.flush()
    return challenge


async def consume_challenge(
    session: AsyncSession,
    *,
    challenge_id: uuid.UUID,
    user_id: uuid.UUID,
    record_version: int,
    record_hash: str,
) -> SignatureChallenge:
    """Single-use: nonce/challenge cannot complete twice, cannot be completed after expiry, and is
    invalidated if the record changed since the challenge was created (SIG-FR-012/013/014 equivalent).
    """
    challenge = await session.get(SignatureChallenge, challenge_id)
    if challenge is None:
        raise SignatureChallengeInvalidError("Signature challenge not found")
    if challenge.user_id != user_id:
        raise SignatureChallengeInvalidError("Signature challenge does not belong to this actor")
    if challenge.consumed_at is not None:
        raise SignatureChallengeInvalidError("Signature challenge already used")
    if challenge.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise SignatureChallengeInvalidError("Signature challenge expired")
    if challenge.record_version != record_version or challenge.record_hash != record_hash:
        raise SignatureChallengeInvalidError("Record changed after the signature challenge was created")

    challenge.consumed_at = datetime.now(timezone.utc)
    return challenge


async def sign(
    session: AsyncSession, *, challenge: SignatureChallenge, auth_context: dict
) -> Signature:
    signature = Signature(
        challenge_id=challenge.id,
        user_id=challenge.user_id,
        meaning=challenge.meaning,
        record_type=challenge.record_type,
        record_id=challenge.record_id,
        record_version=challenge.record_version,
        record_hash=challenge.record_hash,
        auth_context=auth_context,
    )
    session.add(signature)
    await session.flush()
    return signature
