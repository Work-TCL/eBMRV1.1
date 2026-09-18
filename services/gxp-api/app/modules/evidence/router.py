"""Document 72 (SPEC-DATA-004) REST surface, prefix `/evidence/v1`. The 6 operations Document 72 # 7
lists: stage an upload, finalize it, authorized download, create a manifest, apply a legal hold
(signed -- Document 106 row 142), run an integrity check.

`GET /evidence/v1/{id}/download` performs `authorize_evidence_download` (subject + resource + purpose,
OBJ-FR-011/012/030 -- no bucket listing is ever exposed) and streams the bytes from the EvidenceStore.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.evidence import commands
from app.modules.evidence.commands import evidence_record_hash
from app.modules.evidence.models import EvidenceObject
from app.modules.evidence.store import get_store
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import create_challenge, resolve_signature_requirement
from app.mutation.errors import EvidenceAccessDeniedError, EvidenceMissingError, NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/evidence/v1", tags=["evidence"])


def _evidence_object_dict(obj: EvidenceObject) -> dict:
    return {
        "id": str(obj.id),
        "site_id": str(obj.site_id) if obj.site_id else None,
        "owner_type": obj.owner_type,
        "owner_id": str(obj.owner_id),
        "owner_version": obj.owner_version,
        "provider": obj.provider,
        "bucket": obj.bucket,
        "object_key": obj.object_key,
        "provider_version_id": obj.provider_version_id,
        "size_bytes": obj.size_bytes,
        "mime_type": obj.mime_type,
        "filename": obj.filename,
        "hash_algorithm": obj.hash_algorithm,
        "expected_hash": obj.expected_hash,
        "content_hash": obj.content_hash,
        "state": obj.state,
        "retention_policy_id": str(obj.retention_policy_id) if obj.retention_policy_id else None,
        "retention_until": obj.retention_until.isoformat() if obj.retention_until else None,
        "legal_hold": obj.legal_hold,
        "legal_hold_ref": obj.legal_hold_ref,
        "provenance": obj.provenance,
        "superseded_by": str(obj.superseded_by) if obj.superseded_by else None,
        "signature_id": str(obj.signature_id) if obj.signature_id else None,
        "version": obj.version,
        "created_at": obj.created_at.isoformat(),
        "updated_at": obj.updated_at.isoformat(),
    }


@router.get("/objects")
async def list_evidence_objects(
    owner_type: str,
    owner_id: uuid.UUID,
    limit: int = 50,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Owner-filtered list, added so a caller (e.g. batch-execution's "Link evidence" step action) can
    offer a picker of evidence already staged for a specific owner instead of requiring a pasted raw
    UUID + hash. Same `evidence.download` read-gate precedent as `get_evidence_object()` below (Document
    72 declares no dedicated view/list operation either) -- always owner-scoped, never an unfiltered
    listing of the whole table."""
    await evaluate_policy(session, actor.user_id, action="evidence.download", site_id=None)
    limit = max(1, min(limit, 200))
    rows = (
        (
            await session.execute(
                select(EvidenceObject)
                .where(EvidenceObject.owner_type == owner_type, EvidenceObject.owner_id == owner_id)
                .order_by(EvidenceObject.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return {"evidence_objects": [_evidence_object_dict(obj) for obj in rows]}


@router.get("/{evidence_id}")
async def get_evidence_object(
    evidence_id: uuid.UUID,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Metadata-only read (no bytes -- see `GET /{evidence_id}/download` for that), gated by the same
    `evidence.download` permission since there is no dedicated `evidence.view` code (Document 72 declares
    no view/list operation of its own -- same SG-081 read-side precedent used elsewhere: a plain read-only
    GET does not conflict with any write/CRUD contract). Not state-restricted, unlike download -- seeing
    *that* an object is STAGED/QUARANTINE/PURGED, and its legal_hold/signature_id, is exactly what a
    caller needs regardless of whether the bytes themselves are downloadable right now."""
    await evaluate_policy(session, actor.user_id, action="evidence.download", site_id=None)
    obj = await session.get(EvidenceObject, evidence_id)
    if obj is None:
        raise NotFoundError("Evidence object not found")
    return _evidence_object_dict(obj)


@router.post("/uploads", response_model=MutationReceipt)
async def post_stage_upload(
    cmd: commands.StageEvidenceUploadCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="evidence.upload", site_id=cmd.site_id)
        return await commands.stage_evidence_upload(session, cmd, actor.user_id)


@router.post("/{evidence_id}:finalize", response_model=MutationReceipt)
async def post_finalize_upload(
    evidence_id: uuid.UUID, cmd: commands.FinalizeEvidenceUploadCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.evidence_id != evidence_id:
        raise ValidationFailedError("evidence_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="evidence.upload", site_id=None)
        return await commands.finalize_evidence_upload(session, cmd, actor.user_id)


@router.get("/{evidence_id}/download")
async def get_download(
    evidence_id: uuid.UUID, purpose: str = "inspection",
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> Response:
    """`authorizeEvidenceDownload()` -- OBJ-FR-011/012. RBAC + object-state check, then stream bytes.
    A STAGED/QUARANTINE/PURGED/MISSING object is never downloadable via the ordinary path."""
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="evidence.download", site_id=None)
        obj = await session.get(EvidenceObject, evidence_id)
    if obj is None:
        raise NotFoundError("Evidence object not found")
    if obj.state not in ("FINALIZED", "ARCHIVED"):
        raise EvidenceAccessDeniedError(
            "Evidence object is not in a downloadable state", evidence_id=str(obj.id), state=obj.state
        )
    store = get_store()
    if not await store.exists(obj.bucket, obj.object_key):
        raise EvidenceMissingError("Backing object is missing", evidence_id=str(obj.id))
    data = await store.get(obj.bucket, obj.object_key)
    return Response(
        content=data,
        media_type=obj.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{(obj.filename or str(obj.id))}"',
            "X-Evidence-Id": str(obj.id),
            "X-Evidence-Content-Hash": obj.content_hash or "",
            "X-Evidence-Purpose": purpose,
        },
    )


@router.post("/manifests", response_model=MutationReceipt)
async def post_create_manifest(
    cmd: commands.CreateEvidenceManifestCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="evidence.manifest", site_id=None)
        return await commands.create_evidence_manifest(session, cmd, actor.user_id)


class EvidenceSignatureChallengeRequest(BaseModel):
    action: str


_EVIDENCE_SIGNATURE_ACTIONS = ("legal_hold",)


@router.post("/{evidence_id}/signature-challenges")
async def post_evidence_signature_challenge(
    evidence_id: uuid.UUID, body: EvidenceSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Same reference pattern as batch_execution's/product_master's own `/signature-challenges`
    endpoints (SG-035 precedent) — resolves the Document 106 row 142 policy for `evidence_object/
    legal_hold`, then issues a challenge bound to the object's exact (id, version, hash) so
    `consume_challenge()` in `apply_evidence_legal_hold()` rejects it if the object changed underneath.
    `apply_evidence_legal_hold()` has always accepted `challenge_id`/`reauth_password` — this endpoint
    was the missing piece that actually produces a `challenge_id` for the client to send back."""
    if body.action not in _EVIDENCE_SIGNATURE_ACTIONS:
        raise ValidationFailedError("Unknown action", action=body.action, allowed=list(_EVIDENCE_SIGNATURE_ACTIONS))
    async with session.begin():
        obj = await session.get(EvidenceObject, evidence_id)
        if obj is None:
            raise NotFoundError("Evidence object not found")
        policy = await resolve_signature_requirement(session, record_type="evidence_object", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="evidence_object", record_id=obj.id,
            record_version=obj.version, record_hash=evidence_record_hash(obj), meaning=policy.meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/{evidence_id}/legal-holds", response_model=MutationReceipt)
async def post_legal_hold(
    evidence_id: uuid.UUID, cmd: commands.ApplyEvidenceLegalHoldCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    """Document 106 row 142 -- `Performed`, "Authorized holder (Production / QA)", reason required.
    Signed step-up ceremony bound to the evidence record id/version/hash."""
    if cmd.evidence_id != evidence_id:
        raise ValidationFailedError("evidence_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="evidence.legal_hold", site_id=None)
        return await commands.apply_evidence_legal_hold(session, cmd, actor.user_id)


@router.post("/integrity-checks")
async def post_integrity_check(
    cmd: commands.VerifyEvidenceIntegrityCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="evidence.integrity_check", site_id=None)
        return await commands.verify_evidence_integrity(session, cmd, actor.user_id)
