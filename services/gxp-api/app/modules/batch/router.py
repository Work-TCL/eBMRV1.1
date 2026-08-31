import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.batch.commands import (
    CompleteStepCommand,
    CreateBatchCommand,
    IssueBatchCommand,
    ReleaseBatchCommand,
    ReviewBatchCommand,
    StartStepCommand,
    SubmitForReviewCommand,
    batch_record_hash,
    complete_step,
    create_batch,
    issue_batch,
    release_batch,
    review_batch,
    start_step,
    submit_for_review,
)
from app.modules.batch.models import Batch, BatchStep
from app.modules.material.commands import IssueMaterialToBatchCommand, issue_material_to_batch
from app.modules.material.models import Material, MaterialIssue, MaterialLot
from app.modules.product.models import Product
from app.modules.recipe.models import RecipeStep
from app.modules.signature.service import create_challenge, resolve_signature_requirement
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/batches", tags=["batch"])

SORTABLE = {
    "batch_number": Batch.batch_number,
    "status": Batch.status,
    "created_at": Batch.created_at,
    "target_quantity": Batch.target_quantity,
    "product_code": Product.code,
}

# Every site in this Phase 1 deployment; batches always belong to one site, resolved from the batch
# itself for role checks below rather than trusted from the client.


@router.post("", response_model=MutationReceipt)
async def post_create_batch(
    cmd: CreateBatchCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        return await create_batch(session, cmd, actor.user_id)


@router.post("/{batch_id}/issue", response_model=MutationReceipt)
async def post_issue_batch(
    batch_id: uuid.UUID,
    cmd: IssueBatchCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        return await issue_batch(session, cmd, actor.user_id)


@router.post("/{batch_id}/steps/{batch_step_id}/start", response_model=MutationReceipt)
async def post_start_step(
    batch_id: uuid.UUID,
    batch_step_id: uuid.UUID,
    cmd: StartStepCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id or cmd.batch_step_id != batch_step_id:
        raise ValidationFailedError("batch_id/batch_step_id in path and body must match")
    async with session.begin():
        batch = await session.get(Batch, batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        return await start_step(session, cmd, actor.user_id, batch.site_id)


@router.post("/{batch_id}/submit-for-review", response_model=MutationReceipt)
async def post_submit_for_review(
    batch_id: uuid.UUID,
    cmd: SubmitForReviewCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        return await submit_for_review(session, cmd, actor.user_id)


class SignatureChallengeRequest(BaseModel):
    action: str  # "complete_step" | "review" | "release"
    batch_step_id: uuid.UUID | None = None


@router.post("/{batch_id}/signature-challenges")
async def post_signature_challenge(
    batch_id: uuid.UUID,
    body: SignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        batch = await session.get(Batch, batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")

        if body.action == "complete_step":
            if body.batch_step_id is None:
                raise ValidationFailedError("batch_step_id is required for a complete_step challenge")
            step = await session.get(BatchStep, body.batch_step_id)
            if step is None or step.batch_id != batch.id:
                raise NotFoundError("Batch step not found")
            recipe_step = await session.get(RecipeStep, step.recipe_step_id)
            # A policy-floor requirement can demand a signature even when this recipe step's own flag
            # is False (REMEDIATION_R1 FIX 1) — the recipe flag can only ever raise the requirement, so
            # gating challenge creation on the flag alone would make a policy-required step
            # unsatisfiable. Check the resolved policy too.
            policy = await resolve_signature_requirement(
                session, record_type="batch_step", action="complete_step"
            )
            if not (policy.signature_required or recipe_step.requires_signature):
                raise ValidationFailedError("This step does not require a signature")
            meaning = recipe_step.signature_meaning or policy.meaning
        elif body.action == "review":
            meaning = "Reviewed"
        elif body.action == "release":
            meaning = "Released"
        else:
            raise ValidationFailedError("Unknown action", action=body.action)

        challenge = await create_challenge(
            session,
            user_id=actor.user_id,
            record_type="batch",
            record_id=batch.id,
            record_version=batch.version,
            record_hash=batch_record_hash(batch),
            meaning=meaning,
        )
        return {
            "challenge_id": str(challenge.id),
            "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


@router.post("/{batch_id}/steps/{batch_step_id}/complete", response_model=MutationReceipt)
async def post_complete_step(
    batch_id: uuid.UUID,
    batch_step_id: uuid.UUID,
    cmd: CompleteStepCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id or cmd.batch_step_id != batch_step_id:
        raise ValidationFailedError("batch_id/batch_step_id in path and body must match")
    async with session.begin():
        batch = await session.get(Batch, batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        return await complete_step(session, cmd, actor.user_id, batch.site_id)


@router.post("/{batch_id}/review", response_model=MutationReceipt)
async def post_review_batch(
    batch_id: uuid.UUID,
    cmd: ReviewBatchCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        batch = await session.get(Batch, batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        return await review_batch(session, cmd, actor.user_id, batch.site_id)


@router.post("/{batch_id}/release", response_model=MutationReceipt)
async def post_release_batch(
    batch_id: uuid.UUID,
    cmd: ReleaseBatchCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        batch = await session.get(Batch, batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        return await release_batch(session, cmd, actor.user_id, batch.site_id)


@router.get("")
async def list_batches(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params)
) -> dict:
    stmt = select(Batch, Product.code, Product.name).join(Product, Product.id == Batch.product_id)
    if params.q:
        needle = f"%{params.q}%"
        stmt = stmt.where(
            or_(Batch.batch_number.ilike(needle), Product.code.ilike(needle), Product.name.ilike(needle))
        )

    rows, envelope = await paginate(
        session, stmt, params, sortable=SORTABLE, default_sort=Batch.created_at
    )
    return {
        **envelope,
        "items": [
            {
                "id": str(b.id),
                "batch_number": b.batch_number,
                "status": b.status,
                "product_id": str(b.product_id),
                "product_code": product_code,
                "product_name": product_name,
                "target_quantity": str(b.target_quantity),
                "uom": b.uom,
                "version": b.version,
            }
            for b, product_code, product_name in rows
        ],
    }


@router.get("/{batch_id}")
async def get_batch(batch_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")
    steps = (
        await session.execute(
            select(BatchStep, RecipeStep)
            .join(RecipeStep, RecipeStep.id == BatchStep.recipe_step_id)
            .where(BatchStep.batch_id == batch_id)
            .order_by(RecipeStep.step_number)
        )
    ).all()
    return {
        "id": str(batch.id),
        "site_id": str(batch.site_id),
        "batch_number": batch.batch_number,
        "status": batch.status,
        "version": batch.version,
        "product_id": str(batch.product_id),
        "recipe_id": str(batch.recipe_id),
        "target_quantity": str(batch.target_quantity),
        "uom": batch.uom,
        "steps": [
            {
                "batch_step_id": str(bs.id),
                "recipe_step_id": str(rs.id),
                "step_number": rs.step_number,
                "name": rs.name,
                "status": bs.status,
                "requires_signature": rs.requires_signature,
                "signature_meaning": rs.signature_meaning,
                "data": bs.data,
            }
            for bs, rs in steps
        ],
    }


# --- Material genealogy for this batch (MAT-015/MAT-021 minimal form) ------------------------------


@router.post("/{batch_id}/material-issues", response_model=MutationReceipt)
async def post_issue_material(
    batch_id: uuid.UUID,
    cmd: IssueMaterialToBatchCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        batch = await session.get(Batch, batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        return await issue_material_to_batch(session, cmd, actor.user_id, batch.site_id)


@router.get("/{batch_id}/material-issues")
async def list_material_issues(batch_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        await session.execute(
            select(MaterialIssue, MaterialLot.internal_lot, Material.code, Material.name)
            .join(MaterialLot, MaterialLot.id == MaterialIssue.material_lot_id)
            .join(Material, Material.id == MaterialLot.material_id)
            .where(MaterialIssue.batch_id == batch_id)
            .order_by(MaterialIssue.issued_at)
        )
    ).all()
    return [
        {
            "id": str(issue.id),
            "material_lot_id": str(issue.material_lot_id),
            "internal_lot": internal_lot,
            "material_code": material_code,
            "material_name": material_name,
            "batch_step_id": str(issue.batch_step_id) if issue.batch_step_id else None,
            "quantity": str(issue.quantity),
            "uom": issue.uom,
            "issued_at": issue.issued_at.isoformat(),
        }
        for issue, internal_lot, material_code, material_name in rows
    ]
