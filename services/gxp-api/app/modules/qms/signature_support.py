"""Shared signature-challenge ceremony entry point for the twelve WP-05 QMS modules (SG-138, engineering
half). Generalizes the reference pattern already proven by every other signing module in this codebase
(see e.g. app/modules/batch/router.py's own `POST /{batch_id}/signature-challenges`): resolve the
Document 106 policy for a (record_type, action) pair, load the record, create a challenge bound to it,
and return the receipt the client presents back to the module's own mutating command.

Every one of the twelve QMS command files' own private `_record_hash()` helper is byte-identical --
`sha256_hex({"id": str(record.id), "version": record.version})` -- so one implementation here replaces
twelve near-duplicate copies for this one purpose. Nothing about resolve/consume/sign itself changes;
this module only adds the missing "obtain a challenge_id" step each router was missing.

Deliberately does NOT seed Document 106 policy rows, and does not invent a `meaning`, signer role,
independence flag or reason-required flag for any (record_type, action) pair -- `meaning` is read
verbatim from the resolved SignaturePolicy row, exactly as every reference implementation does.
`resolve_signature_requirement()` still raises SignaturePolicyUnresolvedError (surfaced as
SIGNATURE_POLICY_UNRESOLVED) when no policy row exists, which is the correct, evidenced behaviour for
every one of the 26 pairs this gap describes until Head of Quality + Regulatory Affairs supply the rows
-- see docs/generated/18_SPEC_GAPS.md SG-138.
"""

import uuid
from collections.abc import Iterable

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.iam.models import Role
from app.modules.policy.service import effective_role_names
from app.modules.signature.models import SignaturePolicy
from app.modules.signature.service import create_challenge, resolve_signature_requirement
from app.mutation.errors import RoleMissingError, SodIndependenceRequiredError, ValidationFailedError
from app.mutation.hashing import sha256_hex


async def enforce_signer_policy(
    session: AsyncSession,
    *,
    policy: SignaturePolicy,
    actor_user_id: uuid.UUID,
    site_id: uuid.UUID | None,
    action_label: str,
    disqualified_subject_ids: Iterable[uuid.UUID | None] = (),
) -> None:
    """SG-138 policy-data half, 2026-09-10 (project-owner-directed, "follow the ebmr-edhr docs").

    `resolve_signature_requirement()` itself does not read `required_role_id` /
    `requires_independent_signer` -- the same limitation `release_recipe_version()` /
    `release_product_version()` / `close_deviation()` each enforce by hand. This helper is the shared
    version of that bespoke block for the WP-05 QMS modules whose Document 106 section 9 rows name a
    required signer role and/or an independence rule:

    * required role -- the signer must hold the role the policy names, at the record's site;
    * independence -- for a `requires_independent_signer` policy, the signer must not be any of the
      record's own disqualifying subjects (investigator / owner / author, per Document 106 section 9's
      Independence column and the matching Document 107 IND rule). The caller passes the concrete
      identity column(s) its record carries; where a record has no stored identity for a given
      "MUST NOT be the performer" clause, the caller passes nothing for that clause and documents the
      gap (same honest limitation already recorded for `qa_review_package/complete`).
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


class SignatureChallengeRequest(BaseModel):
    action: str


def record_hash(record) -> str:
    """Identical to every QMS command file's own private `_record_hash()` -- (id, version) is the whole
    binding surface a signature challenge needs (SIG-FR-012/013/014 equivalent: the challenge is
    invalidated if the record changed since it was issued)."""
    return sha256_hex({"id": str(record.id), "version": record.version})


async def _resolve_and_challenge(
    session: AsyncSession,
    *,
    actor_user_id: uuid.UUID,
    record_type: str,
    record_id: uuid.UUID,
    record_version: int,
    record_hash_value: str,
    action: str,
    allowed_actions: tuple[str, ...],
) -> dict:
    if action not in allowed_actions:
        raise ValidationFailedError("Unknown action", action=action, allowed=list(allowed_actions))
    policy = await resolve_signature_requirement(session, record_type=record_type, action=action)
    challenge = await create_challenge(
        session,
        user_id=actor_user_id,
        record_type=record_type,
        record_id=record_id,
        record_version=record_version,
        record_hash=record_hash_value,
        meaning=policy.meaning,
    )
    return {
        "challenge_id": str(challenge.id),
        "meaning": challenge.meaning,
        "expires_at": challenge.expires_at.isoformat(),
    }


async def create_qms_signature_challenge(
    session: AsyncSession,
    *,
    actor_user_id: uuid.UUID,
    record_type: str,
    record,
    action: str,
    allowed_actions: tuple[str, ...],
) -> dict:
    """Resolve Document 106 policy for `(record_type, action)`, then create a challenge bound to `record`.

    `allowed_actions` is the caller's own fixed action list for its resource (mirrors the explicit
    `if body.action not in (...)` checks every reference implementation uses) -- an unrecognized action
    is a plain 400, not a policy lookup, so a typo doesn't get reported as a signature-policy gap.
    """
    return await _resolve_and_challenge(
        session, actor_user_id=actor_user_id, record_type=record_type, record_id=record.id,
        record_version=record.version, record_hash_value=record_hash(record), action=action,
        allowed_actions=allowed_actions,
    )


async def create_qms_signature_challenge_for_new_record(
    session: AsyncSession,
    *,
    actor_user_id: uuid.UUID,
    record_type: str,
    record_id: uuid.UUID,
    action: str,
    allowed_actions: tuple[str, ...],
) -> dict:
    """Same ceremony as `create_qms_signature_challenge()`, for the one case in this codebase where the
    signed action itself is `create`: the record does not exist yet at challenge time, so there is no
    `record` object to read `.id`/`.version` from. `record_id` is generated by the caller (server-side,
    e.g. `uuid.uuid4()`) *before* calling this function; the challenge is bound to that id at version 1
    -- the version every new row in this codebase starts at (`version: Mapped[int] = mapped_column(...,
    default=1)`). The caller's own create command must then insert its new row using that exact same id,
    so the row that gets flushed matches the (id, version=1) pair the challenge was issued against --
    `consume_challenge()`'s existing version/hash check does the rest, unchanged.

    Discovered and documented as a genuine defect in SG-138 (training_assignment/create): see
    app/modules/qms/training_router.py's own signature-challenges endpoint for the reference caller.
    """
    return await _resolve_and_challenge(
        session, actor_user_id=actor_user_id, record_type=record_type, record_id=record_id,
        record_version=1, record_hash_value=sha256_hex({"id": str(record_id), "version": 1}), action=action,
        allowed_actions=allowed_actions,
    )
