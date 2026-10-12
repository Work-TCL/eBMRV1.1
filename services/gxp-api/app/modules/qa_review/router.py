import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.batch_execution.models import Batch
from app.modules.policy.service import evaluate_policy
from app.modules.product_master.models import ProductVersion
from app.modules.qa_review import service as qa_review_service
from app.modules.qa_review.commands import (
    CompleteReviewPackageCommand,
    CreateReviewPackageCommand,
    ReindexReviewPackageCommand,
    complete_review_package,
    create_review_package,
    reindex_review_package,
)
from app.modules.signature.service import create_challenge
from app.mutation.errors import ValidationFailedError
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/qa-review/v1", tags=["qa_review"])

# Document 106 row 29 (SPEC-EBMR-005) -- the only signed qa_review_package action.
_CHALLENGE_MEANINGS = {"complete": "Reviewed"}


class QaReviewSignatureChallengeRequest(BaseModel):
    action: str


def _package_dict(package, refs: dict | None = None) -> dict:
    refs = refs or {}
    return {
        "package_id": str(package.id),
        "site_id": str(package.site_id),
        "batch_id": str(package.batch_id),
        "batch_number": refs.get("batch_number"),
        "product_code": refs.get("product_code"),
        "product_name": refs.get("product_name"),
        "batch_version": package.batch_version,
        "record_hash": package.record_hash,
        "exception_index_version": package.exception_index_version,
        "completeness_status": package.completeness_status,
        "state": package.state,
        "version": package.version,
        "completed_at": package.completed_at.isoformat() if package.completed_at else None,
    }


async def _resolve_package_refs(session: AsyncSession, packages: list) -> dict[uuid.UUID, dict]:
    """Batch-resolves the batch/product foreign key `_package_dict` labels for -- same one-query-per-
    referenced-table shape as packaging's own `_resolve_run_refs`."""
    if not packages:
        return {}

    batch_ids = {p.batch_id for p in packages}
    batch_by_id = {
        row.id: (row.batch_number, row.product_version_id)
        for row in (await session.execute(select(Batch.id, Batch.batch_number, Batch.product_version_id).where(Batch.id.in_(batch_ids)))).all()
    }
    product_ids = {pv_id for (_, pv_id) in batch_by_id.values() if pv_id}
    product_by_id = {
        row.id: (row.product_code, row.name)
        for row in (
            await session.execute(select(ProductVersion.id, ProductVersion.product_code, ProductVersion.name).where(ProductVersion.id.in_(product_ids)))
        ).all()
    } if product_ids else {}

    resolved: dict[uuid.UUID, dict] = {}
    for p in packages:
        batch_number, product_version_id = batch_by_id.get(p.batch_id, (None, None))
        product_code, product_name = product_by_id.get(product_version_id, (None, None)) if product_version_id else (None, None)
        resolved[p.id] = {"batch_number": batch_number, "product_code": product_code, "product_name": product_name}
    return resolved


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
        batch = await qa_review_service.get_batch(session, batch_id)
        await evaluate_policy(session, actor.user_id, action="qa_review.create", site_id=batch.site_id)
        return await create_review_package(session, cmd, actor.user_id)


@router.get("/batches/{batch_id}/package")
async def get_package_for_batch(
    batch_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict | None:
    """Read-only lookup for a QA review package already created against this batch, if one exists --
    returns null rather than 404 when none does yet, same convention as release/router.py's own
    `get_scope_by_target`. Built for the Batch Workspace (client requirement); `qa_review_service.
    get_package_for_batch` already existed, it was just never wired to a route."""
    batch = await qa_review_service.get_batch(session, batch_id)
    await evaluate_policy(session, actor.user_id, action="qa_review.view", site_id=batch.site_id)
    package = await qa_review_service.get_package_for_batch(session, batch_id)
    if package is None:
        return None
    refs = await _resolve_package_refs(session, [package])
    return _package_dict(package, refs.get(package.id))


@router.get("/packages/{package_id}")
async def get_package_detail(
    package_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    package = await qa_review_service.get_package(session, package_id)
    await evaluate_policy(session, actor.user_id, action="qa_review.view", site_id=package.site_id)
    batch = await qa_review_service.get_batch(session, package.batch_id)
    refs = await _resolve_package_refs(session, [package])
    body = _package_dict(package, refs.get(package.id))
    body["stale"] = batch.version != package.batch_version
    return body


@router.get("/packages/{package_id}/exceptions")
async def get_package_exceptions(
    package_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    package = await qa_review_service.get_package(session, package_id)
    await evaluate_policy(session, actor.user_id, action="qa_review.view", site_id=package.site_id)
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
        package = await qa_review_service.get_package(session, package_id)
        await evaluate_policy(session, actor.user_id, action="qa_review.execute", site_id=package.site_id)
        return await reindex_review_package(session, cmd, actor.user_id)


@router.post("/packages/{package_id}/signature-challenges")
async def post_signature_challenge(
    package_id: uuid.UUID,
    body: QaReviewSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Issue the Part 11 challenge for `POST .../complete`. record_version + record_hash match
    complete_review_package()'s own consume_challenge call exactly (SIG-FR-012/013/014) -- same shape as
    recipe_master's `POST /drafts/{id}/signature-challenges` (SG-035 precedent)."""
    async with session.begin():
        package = await qa_review_service.get_package(session, package_id)
        await evaluate_policy(session, actor.user_id, action="qa_review.execute", site_id=package.site_id)
        meaning = _CHALLENGE_MEANINGS.get(body.action)
        if meaning is None:
            raise ValidationFailedError("Unknown or unsigned action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="qa_review_package", record_id=package.id,
            record_version=package.version, record_hash=sha256_hex({"id": str(package.id), "version": package.version}),
            meaning=meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


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
        package = await qa_review_service.get_package(session, package_id)
        await evaluate_policy(session, actor.user_id, action="qa_review.execute", site_id=package.site_id)
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
    await evaluate_policy(session, actor.user_id, action="qa_review.view", site_id=site_id)
    packages = await qa_review_service.list_packages(session, site_id, state=state)
    refs = await _resolve_package_refs(session, packages)
    return {"packages": [_package_dict(p, refs.get(p.id)) for p in packages]}
