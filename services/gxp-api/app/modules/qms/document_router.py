import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qms import document_service
from app.modules.qms.document_commands import (
    CreateDocumentDraftCommand,
    IssueControlledCopyCommand,
    MakeDocumentVersionEffectiveCommand,
    ObsoleteDocumentVersionCommand,
    ReleaseDocumentDraftCommand,
    SubmitDocumentDraftCommand,
    create_draft,
    issue_controlled_copy,
    make_effective,
    obsolete_version,
    release_draft,
    submit_draft,
)
from app.modules.qms.signature_support import SignatureChallengeRequest, create_qms_signature_challenge
from app.mutation.errors import ValidationFailedError
from app.mutation.schemas import MutationReceipt

document_router = APIRouter(prefix="/documents/v1", tags=["qms-document-control"])

DOCUMENT_VERSION_SIGNATURE_ACTIONS = ("release",)


def _version_dict(version) -> dict:
    return {
        "id": str(version.id), "document_id": str(version.document_id), "version_label": version.version_label,
        "state": version.state, "content_hash": version.content_hash, "rendition_hash": version.rendition_hash,
        "effective_from": version.effective_from.isoformat() if version.effective_from else None,
        "effective_to": version.effective_to.isoformat() if version.effective_to else None,
        "change_control_id": str(version.change_control_id) if version.change_control_id else None,
        "periodic_review_due": version.periodic_review_due.isoformat() if version.periodic_review_due else None,
        "superseded_by_version_id": str(version.superseded_by_version_id) if version.superseded_by_version_id else None,
        "version": version.version,
    }


@document_router.post("/drafts", response_model=MutationReceipt)
async def post_create_draft(
    cmd: CreateDocumentDraftCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="document.create", site_id=cmd.site_id)
        return await create_draft(session, cmd, actor.user_id)


@document_router.post("/drafts/{document_version_id}/submit", response_model=MutationReceipt)
async def post_submit_draft(
    document_version_id: uuid.UUID, cmd: SubmitDocumentDraftCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.document_version_id != document_version_id:
        raise ValidationFailedError("document_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="document.submit", site_id=None)
        return await submit_draft(session, cmd, actor.user_id)


@document_router.post("/drafts/{document_version_id}/release", response_model=MutationReceipt)
async def post_release_draft(
    document_version_id: uuid.UUID, cmd: ReleaseDocumentDraftCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.document_version_id != document_version_id:
        raise ValidationFailedError("document_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="document.release", site_id=None)
        return await release_draft(session, cmd, actor.user_id)


@document_router.post("/drafts/{document_version_id}/signature-challenges")
async def post_signature_challenge(
    document_version_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        version = await document_service.get_version(session, document_version_id)
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="controlled_document_version", record=version,
            action=body.action, allowed_actions=DOCUMENT_VERSION_SIGNATURE_ACTIONS,
        )


@document_router.post("/versions/{document_version_id}/make-effective", response_model=MutationReceipt)
async def post_make_effective(
    document_version_id: uuid.UUID, cmd: MakeDocumentVersionEffectiveCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.document_version_id != document_version_id:
        raise ValidationFailedError("document_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="document.make_effective", site_id=None)
        return await make_effective(session, cmd, actor.user_id)


@document_router.post("/versions/{document_version_id}/obsolete", response_model=MutationReceipt)
async def post_obsolete_version(
    document_version_id: uuid.UUID, cmd: ObsoleteDocumentVersionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.document_version_id != document_version_id:
        raise ValidationFailedError("document_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="document.obsolete", site_id=None)
        return await obsolete_version(session, cmd, actor.user_id)


@document_router.post("/versions/{document_version_id}/controlled-copies", response_model=MutationReceipt)
async def post_issue_controlled_copy(
    document_version_id: uuid.UUID, cmd: IssueControlledCopyCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.document_version_id != document_version_id:
        raise ValidationFailedError("document_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="document.controlled_copy.issue", site_id=None)
        return await issue_controlled_copy(session, cmd, actor.user_id)


@document_router.get("/{document_code}/versions")
async def get_versions(
    document_code: str, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="document.view", site_id=None)
    document = await document_service.get_document_by_code(session, document_code)
    versions = await document_service.get_versions_for_document(session, document.id)
    return {
        "document_code": document.document_code, "document_type": document.document_type, "status": document.status,
        "versions": [_version_dict(v) for v in versions],
    }
