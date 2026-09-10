import secrets
import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.iam.models import Role
from app.modules.policy.service import effective_role_names
from app.modules.signature.models import Signature, SignatureChallenge, SignaturePolicy
from app.mutation.errors import (
    RoleMissingError,
    SignatureChallengeInvalidError,
    SignaturePolicyUnresolvedError,
    SodIndependenceRequiredError,
)


async def enforce_signer_policy(
    session: AsyncSession,
    *,
    policy: SignaturePolicy,
    actor_user_id: uuid.UUID,
    site_id: uuid.UUID | None,
    action_label: str,
    disqualified_subject_ids: Iterable[uuid.UUID | None] = (),
) -> None:
    """SG-138 / SG-035 policy-data half, 2026-09-10 (project-owner-directed, "follow the ebmr-edhr docs").

    `resolve_signature_requirement()` itself does not read `required_role_id` /
    `requires_independent_signer` -- the same limitation `release_recipe_version()` /
    `release_product_version()` / `close_deviation()` each enforce by hand. This is the shared version of
    that bespoke block for the Document 106 section 9 rows that name a required signer role and/or an
    independence rule:

    * required role -- the signer must hold the role the policy names, at the record's site
      (`site_id=None` means "at any site");
    * independence -- for a `requires_independent_signer` policy, the signer must not be any of the
      record's own disqualifying subjects (investigator / owner / author). The caller passes the concrete
      identity column(s) its record carries; where a record has no stored identity for the "MUST NOT be
      the performer" clause, the caller passes nothing and documents the gap (same honest limitation
      recorded for qa_review_package/complete).
    """
    if policy.required_role_id is not None:
        required_role_name = await session.scalar(select(Role.name).where(Role.id == policy.required_role_id))
        if required_role_name not in await effective_role_names(session, actor_user_id, site_id):
            raise RoleMissingError(
                f"{action_label} requires the signing role named by the signature policy",
                action=action_label,
                required_role=required_role_name,
            )
    if policy.requires_independent_signer:
        disqualified = {s for s in disqualified_subject_ids if s is not None}
        if actor_user_id in disqualified:
            raise SodIndependenceRequiredError(
                f"{action_label} must be independent of the record's investigator/owner/author "
                "(Document 106 section 9 / Document 107)",
                action=action_label,
            )


async def resolve_signature_requirement(
    session: AsyncSession, *, record_type: str, action: str
) -> SignaturePolicy:
    """Signature requirement comes from policy data, never a code conditional (AG-07 / SIG-FR-004).

    Fail-closed resolution (Doc 106 SIGP-FR-004): a regulated action with no policy row is an error,
    never an implicit permission to commit unsigned. "This action deliberately needs no signature" must
    be a row with `signature_required=False`, not the absence of a row.
    """
    result = await session.execute(
        select(SignaturePolicy).where(
            SignaturePolicy.record_type == record_type, SignaturePolicy.action == action
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise SignaturePolicyUnresolvedError(
            "No signature policy is defined for this regulated action",
            record_type=record_type,
            action=action,
        )
    return policy


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
