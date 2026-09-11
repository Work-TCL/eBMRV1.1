import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import chain_signatures_so_far, create_challenge, resolve_signature_requirement
from app.modules.vault import service as vault_service
from app.modules.vault.commands import (
    CompleteCorrectionCommand,
    CreateVaultReleaseCommand,
    RequestCorrectionCommand,
    complete_correction,
    create_vault_release,
    request_correction,
)
from app.modules.vault.models import RecordCorrection
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/vault/v1", tags=["vault"])


def _object_dict(obj) -> dict:
    return {
        "object_id": str(obj.object_id),
        "site_id": str(obj.site_id) if obj.site_id else None,
        "object_type": obj.object_type,
        "business_id": obj.business_id,
        "internal_version": obj.internal_version,
        "business_version_label": obj.business_version_label,
        "status": obj.status,
        "digest_algorithm": obj.digest_algorithm,
        "digest": obj.digest,
        "canonical_payload": obj.canonical_payload,
        "effective_from": obj.effective_from.isoformat() if obj.effective_from else None,
        "effective_to": obj.effective_to.isoformat() if obj.effective_to else None,
        "supersedes_object_id": str(obj.supersedes_object_id) if obj.supersedes_object_id else None,
        "corrected_from_object_id": str(obj.corrected_from_object_id) if obj.corrected_from_object_id else None,
        "retention_class": obj.retention_class,
        "released_at": obj.released_at.isoformat(),
        "created_by_subject": str(obj.created_by_subject) if obj.created_by_subject else None,
    }


@router.post("/masters/{object_type}/{business_id}/release", response_model=MutationReceipt)
async def post_release_master(
    object_type: str,
    business_id: str,
    cmd: CreateVaultReleaseCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.object_type != object_type or cmd.business_id != business_id:
        raise ValidationFailedError("object_type/business_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="vault.correct", site_id=None)
        return await create_vault_release(session, cmd, actor.user_id)


class VaultReleaseChallengeRequest(BaseModel):
    action: str = "release"
    canonical_payload: dict


@router.post("/masters/{object_type}/{business_id}/signature-challenges")
async def post_vault_release_signature_challenge(
    object_type: str,
    business_id: str,
    body: VaultReleaseChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """SG-035 (2026-09-10): obtain a challenge for the generic vault master release (Document 106 section
    9 row 2). Bound to `sha256_hex(canonical_payload)` at version 1 -- the same hash `create_vault_
    release()` re-computes at consume time (the vault object does not exist yet, so there is no prior
    record to bind to)."""
    if body.action != "release":
        raise ValidationFailedError("Unknown or unsigned action", action=body.action)
    async with session.begin():
        policy = await resolve_signature_requirement(session, record_type="vault_object", action="release")
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="vault_object", record_id=uuid.uuid4(),
            record_version=1, record_hash=sha256_hex(body.canonical_payload), meaning=policy.meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.get("/objects/{object_id}")
async def get_object(
    object_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="vault.review", site_id=None)
    obj = await vault_service.get_object(session, object_id)
    return _object_dict(obj)


@router.get("/objects/{object_id}/integrity")
async def get_object_integrity(
    object_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="vault.review", site_id=None)
    return await vault_service.verify_integrity(session, object_id)


@router.get("/business/{object_type}/{business_id}/versions")
async def get_versions(
    object_type: str,
    business_id: str,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    await evaluate_policy(session, actor.user_id, action="vault.review", site_id=None)
    objects = await vault_service.list_versions_for_business_id(
        session, object_type=object_type, business_id=business_id
    )
    return [_object_dict(o) for o in objects]


@router.post("/objects/{object_id}/corrections", response_model=MutationReceipt)
async def post_request_correction(
    object_id: uuid.UUID,
    cmd: RequestCorrectionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.record_object_id != object_id:
        raise ValidationFailedError("object_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="vault.correct", site_id=None)
        return await request_correction(session, cmd, actor.user_id)


@router.post("/corrections/{correction_id}/complete", response_model=MutationReceipt)
async def post_complete_correction(
    correction_id: uuid.UUID,
    cmd: CompleteCorrectionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.correction_id != correction_id:
        raise ValidationFailedError("correction_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="vault.correct", site_id=None)
        return await complete_correction(session, cmd, actor.user_id)


class CorrectionSignatureChallengeRequest(BaseModel):
    corrected_canonical_payload: dict


@router.post("/corrections/{correction_id}/signature-challenges")
async def post_correction_signature_challenge(
    correction_id: uuid.UUID,
    body: CorrectionSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """SG-035 pair 4, RESOLVED 2026-09-11 (PHASE_3_DEFERRED_DECISIONS.md item D; Document 106 section 9
    row 1). Never existed before this pass -- `complete_correction()` was always the platform's only
    single-signature 409/428 fail-closed action with no challenge-issuing endpoint at all (SG-035). The
    chain position (1 = corrector, 2 = independent approver) is derived from how many valid signatures
    this correction already carries, never accepted from the caller -- see `complete_correction()`'s own
    docstring for why that structurally rules out "signature 2 issued before signature 1 exists"
    (Document 106 section 13 test #5). Bound to `sha256_hex(corrected_canonical_payload)` at version 1 --
    the same hash `complete_correction()` re-computes at consume time -- and, from position 2 onward,
    checked against the first signer's own hash so a later signer cannot approve different content than
    an earlier signer already saw."""
    async with session.begin():
        correction = await session.get(RecordCorrection, correction_id)
        if correction is None:
            raise NotFoundError("Correction not found")
        if correction.status not in ("requested", "awaiting_second_signature"):
            raise ValidationFailedError("Correction is not awaiting a signature", current_status=correction.status)
        policy = await resolve_signature_requirement(session, record_type="record_correction", action="complete")
        prior_signatures = await chain_signatures_so_far(
            session, record_type="record_correction", record_id=correction.correction_id, record_version=1,
        )
        position = len(prior_signatures) + 1
        if position > policy.signature_count:
            raise ValidationFailedError(
                "This correction has already collected every required signature",
                signature_count=policy.signature_count,
            )
        record_hash = sha256_hex(body.corrected_canonical_payload)
        if prior_signatures and record_hash != prior_signatures[0].record_hash:
            raise ValidationFailedError(
                "corrected_canonical_payload must match what the earlier signer(s) in this chain approved"
            )
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="record_correction", record_id=correction.correction_id,
            record_version=1, record_hash=record_hash, meaning=policy.meaning,
        )
        return {
            "challenge_id": str(challenge.id), "meaning": challenge.meaning,
            "chain_position": position, "signature_count": policy.signature_count,
            "expires_at": challenge.expires_at.isoformat(),
        }
