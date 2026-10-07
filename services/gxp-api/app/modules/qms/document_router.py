import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy, resolve_site_scope
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
from app.modules.qms.document_models import ControlledDocument, ControlledDocumentVersion
from app.modules.qms.read_support import filtered, iso, sid
from app.modules.qms.signature_support import SignatureChallengeRequest, create_qms_signature_challenge
from app.mutation.errors import ValidationFailedError
from app.mutation.schemas import MutationReceipt

document_router = APIRouter(prefix="/documents/v1", tags=["qms-document-control"])

DOCUMENT_VERSION_SIGNATURE_ACTIONS = ("release",)

DOCUMENT_SORTABLE = {
    "document_code": ControlledDocument.document_code,
    "document_type": ControlledDocument.document_type,
    "status": ControlledDocument.status,
    "created_at": ControlledDocument.created_at,
}


def _document_dict(document: ControlledDocument) -> dict:
    return {
        "id": str(document.id),
        "site_id": sid(document.site_id),
        "document_code": document.document_code,
        "document_type": document.document_type,
        "owner_subject_id": sid(document.owner_subject_id),
        "is_external": document.is_external,
        "external_source": document.external_source,
        "external_revision": document.external_revision,
        "status": document.status,
        "created_at": iso(document.created_at),
    }


def _version_dict(version: ControlledDocumentVersion, document: ControlledDocument) -> dict:
    # Flattens the owning document's identity/classification fields onto each version row -- this is
    # the shape frontend/src/app/documents/page.tsx's `DocumentVersion` interface actually declares
    # (site_id, document_code, document_type, owner_subject_id, is_external, external_source,
    # external_revision all live on `ControlledDocument`, not `ControlledDocumentVersion`).
    return {
        "id": str(version.id), "document_id": str(version.document_id),
        "site_id": sid(document.site_id), "document_code": document.document_code,
        "document_type": document.document_type, "owner_subject_id": sid(document.owner_subject_id),
        "is_external": document.is_external, "external_source": document.external_source,
        "external_revision": document.external_revision,
        "version_label": version.version_label,
        "state": version.state, "content_hash": version.content_hash, "rendition_hash": version.rendition_hash,
        "effective_from": version.effective_from.isoformat() if version.effective_from else None,
        "effective_to": version.effective_to.isoformat() if version.effective_to else None,
        "change_control_id": str(version.change_control_id) if version.change_control_id else None,
        "periodic_review_due": version.periodic_review_due.isoformat() if version.periodic_review_due else None,
        "superseded_by_version_id": str(version.superseded_by_version_id) if version.superseded_by_version_id else None,
        "acknowledgment_required": version.acknowledgment_required,
        "training_impact": version.training_impact,
        "version": version.version,
        "created_at": iso(version.created_at),
    }


def _controlled_copy_dict(c) -> dict:
    return {
        "id": str(c.id), "document_version_id": str(c.document_version_id), "copy_number": c.copy_number,
        "recipient": c.recipient, "location": c.location, "status": c.status,
        "issued_by": str(c.issued_by), "issued_at": c.issued_at.isoformat(),
        "returned_at": c.returned_at.isoformat() if c.returned_at else None,
        "destroyed_at": c.destroyed_at.isoformat() if c.destroyed_at else None,
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
        version = await document_service.get_version(session, document_version_id)
        document = await document_service.get_document(session, version.document_id)
        await evaluate_policy(session, actor.user_id, action="document.submit", site_id=document.site_id)
        return await submit_draft(session, cmd, actor.user_id)


@document_router.post("/drafts/{document_version_id}/release", response_model=MutationReceipt)
async def post_release_draft(
    document_version_id: uuid.UUID, cmd: ReleaseDocumentDraftCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.document_version_id != document_version_id:
        raise ValidationFailedError("document_version_id in path and body must match")
    async with session.begin():
        version = await document_service.get_version(session, document_version_id)
        document = await document_service.get_document(session, version.document_id)
        await evaluate_policy(session, actor.user_id, action="document.release", site_id=document.site_id)
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
        version = await document_service.get_version(session, document_version_id)
        document = await document_service.get_document(session, version.document_id)
        await evaluate_policy(session, actor.user_id, action="document.make_effective", site_id=document.site_id)
        return await make_effective(session, cmd, actor.user_id)


@document_router.post("/versions/{document_version_id}/obsolete", response_model=MutationReceipt)
async def post_obsolete_version(
    document_version_id: uuid.UUID, cmd: ObsoleteDocumentVersionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.document_version_id != document_version_id:
        raise ValidationFailedError("document_version_id in path and body must match")
    async with session.begin():
        version = await document_service.get_version(session, document_version_id)
        document = await document_service.get_document(session, version.document_id)
        await evaluate_policy(session, actor.user_id, action="document.obsolete", site_id=document.site_id)
        return await obsolete_version(session, cmd, actor.user_id)


@document_router.post("/versions/{document_version_id}/controlled-copies", response_model=MutationReceipt)
async def post_issue_controlled_copy(
    document_version_id: uuid.UUID, cmd: IssueControlledCopyCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.document_version_id != document_version_id:
        raise ValidationFailedError("document_version_id in path and body must match")
    async with session.begin():
        version = await document_service.get_version(session, document_version_id)
        document = await document_service.get_document(session, version.document_id)
        await evaluate_policy(session, actor.user_id, action="document.controlled_copy.issue", site_id=document.site_id)
        return await issue_controlled_copy(session, cmd, actor.user_id)


# --- Read side ---------------------------------------------------------------------------------


@document_router.get("")
async def list_documents(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
) -> dict:
    site_scope = await resolve_site_scope(session, actor.user_id, site_id, action="document.view")
    stmt = filtered(ControlledDocument, params, search_column=ControlledDocument.document_code, site_id=site_scope)
    rows, envelope = await paginate(
        session, stmt, params, sortable=DOCUMENT_SORTABLE, default_sort=ControlledDocument.created_at
    )
    return {**envelope, "items": [_document_dict(r) for (r,) in rows]}


@document_router.get("/versions/{document_version_id}/controlled-copies")
async def get_controlled_copies(
    document_version_id: uuid.UUID, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    version = await document_service.get_version(session, document_version_id)
    document = await document_service.get_document(session, version.document_id)
    await evaluate_policy(session, actor.user_id, action="document.view", site_id=document.site_id)
    copies = await document_service.get_controlled_copies(session, document_version_id)
    return [_controlled_copy_dict(c) for c in copies]


@document_router.get("/{document_code}/versions")
async def get_versions(
    document_code: str, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    document = await document_service.get_document_by_code(session, document_code)
    await evaluate_policy(session, actor.user_id, action="document.view", site_id=document.site_id)
    versions = await document_service.get_versions_for_document(session, document.id)
    return [_version_dict(v, document) for v in versions]
