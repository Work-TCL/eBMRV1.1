"""Document 72 (SPEC-DATA-004) REST surface, prefix `/evidence/v1`. The 6 operations Document 72 # 7
lists: stage an upload, finalize it, authorized download, create a manifest, apply a legal hold
(signed -- Document 106 row 142), run an integrity check.

`GET /evidence/v1/{id}/download` performs `authorize_evidence_download` (subject + resource + purpose,
OBJ-FR-011/012/030 -- no bucket listing is ever exposed) and streams the bytes from the EvidenceStore.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.evidence import commands
from app.modules.evidence.models import EvidenceObject
from app.modules.evidence.store import get_store
from app.modules.policy.service import evaluate_policy
from app.mutation.errors import EvidenceAccessDeniedError, EvidenceMissingError, NotFoundError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/evidence/v1", tags=["evidence"])


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
        from app.mutation.errors import ValidationFailedError

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


@router.post("/{evidence_id}/legal-holds", response_model=MutationReceipt)
async def post_legal_hold(
    evidence_id: uuid.UUID, cmd: commands.ApplyEvidenceLegalHoldCommand,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    """Document 106 row 142 -- `Performed`, "Authorized holder (Production / QA)", reason required.
    Signed step-up ceremony bound to the evidence record id/version/hash."""
    if cmd.evidence_id != evidence_id:
        from app.mutation.errors import ValidationFailedError

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
