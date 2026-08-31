import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qa_review import service as qa_review_service
from app.modules.qa_review.commands import (
    CompleteReviewPackageCommand,
    CreateReviewPackageCommand,
    ReindexReviewPackageCommand,
    complete_review_package,
    create_review_package,
    reindex_review_package,
)
from app.mutation.errors import ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/qa-review/v1", tags=["qa_review"])


def _package_dict(package) -> dict:
    return {
        "package_id": str(package.id),
        "site_id": str(package.site_id),
        "batch_id": str(package.batch_id),
        "batch_version": package.batch_version,
        "record_hash": package.record_hash,
        "exception_index_version": package.exception_index_version,
        "completeness_status": package.completeness_status,
        "state": package.state,
        "version": package.version,
        "completed_at": package.completed_at.isoformat() if package.completed_at else None,
    }


@router.post("/batches/{batch_id}/packages", response_model=MutationReceipt)
async def post_create_package(
    batch_id: uuid.UUID,
    cmd: CreateReviewPackageCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qa_review.create", site_id=None)
        return await create_review_package(session, cmd, actor.user_id)


@router.get("/packages/{package_id}")
async def get_package_detail(
    package_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="qa_review.view", site_id=None)
    package = await qa_review_service.get_package(session, package_id)
    batch = await qa_review_service.get_batch(session, package.batch_id)
    body = _package_dict(package)
    body["stale"] = batch.version != package.batch_version
    return body


@router.get("/packages/{package_id}/exceptions")
async def get_package_exceptions(
    package_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="qa_review.view", site_id=None)
    package = await qa_review_service.get_package(session, package_id)
    return await qa_review_service.get_exceptions_view(session, package)


@router.post("/packages/{package_id}/reindex", response_model=MutationReceipt)
async def post_reindex_package(
    package_id: uuid.UUID,
    cmd: ReindexReviewPackageCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.package_id != package_id:
        raise ValidationFailedError("package_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qa_review.execute", site_id=None)
        return await reindex_review_package(session, cmd, actor.user_id)


@router.post("/packages/{package_id}/complete", response_model=MutationReceipt)
async def post_complete_package(
    package_id: uuid.UUID,
    cmd: CompleteReviewPackageCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.package_id != package_id:
        raise ValidationFailedError("package_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qa_review.execute", site_id=None)
        return await complete_review_package(session, cmd, actor.user_id)


@router.get("/dashboard")
async def get_dashboard(
    site_id: uuid.UUID,
    state: str | None = None,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """RBE-FR-026 (partial): site-scoped package list filterable by state; exception-class/review-age
    filtering is not built -- it would need qa_review_item, SG-053."""
    await evaluate_policy(session, actor.user_id, action="qa_review.view", site_id=None)
    packages = await qa_review_service.list_packages(session, site_id, state=state)
    return {"packages": [_package_dict(p) for p in packages]}
