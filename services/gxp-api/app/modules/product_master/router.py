import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.product_master import service as product_master_service
from app.modules.product_master.commands import (
    CreateProductDraftCommand,
    ReinstateProductVersionCommand,
    ReleaseProductVersionCommand,
    SubmitProductDraftCommand,
    SuspendProductVersionCommand,
    UpdateProductDraftCommand,
    ValidateCompletenessCommand,
    create_draft,
    reinstate_product_version,
    release_product_version,
    submit_draft,
    suspend_product_version,
    update_draft,
    validate_completeness_command,
)
from app.modules.product_master.models import ConstituentCompatibilityVersion
from app.mutation.errors import ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/products/v1", tags=["product_master"])


def _version_dict(version) -> dict:
    return {
        "product_version_id": str(version.id),
        "product_business_id": version.product_business_id,
        "version_no": version.version_no,
        "product_code": version.product_code,
        "name": version.name,
        "product_family_id": str(version.product_family_id) if version.product_family_id else None,
        "lifecycle_state": version.lifecycle_state,
        "manufacturing_profile_code": version.manufacturing_profile_code,
        "combination_product_type": version.combination_product_type,
        "pmoa_reference": version.pmoa_reference,
        "part4_profile_code": version.part4_profile_code,
        "sterile_profile_id": str(version.sterile_profile_id) if version.sterile_profile_id else None,
        "finished_tracking_strategy": version.finished_tracking_strategy,
        "udi_applicable": version.udi_applicable,
        "strength_value": str(version.strength_value) if version.strength_value is not None else None,
        "strength_uom": version.strength_uom,
        "device_model_code": version.device_model_code,
        "effective_from": version.effective_from.isoformat() if version.effective_from else None,
        "effective_to": version.effective_to.isoformat() if version.effective_to else None,
        "released_vault_object_id": str(version.released_vault_object_id) if version.released_vault_object_id else None,
        "version_hash": version.version_hash,
        "version": version.version,
        "site_id": str(version.site_id),
    }


def _constituent_dict(c) -> dict:
    return {
        "id": str(c.id),
        "constituent_type": c.constituent_type,
        "role_code": c.role_code,
        "constituent_business_id": c.constituent_business_id,
        "constituent_version_id": str(c.constituent_version_id),
        "source_site_id": str(c.source_site_id) if c.source_site_id else None,
        "tracking_strategy": c.tracking_strategy,
        "sequence_no": c.sequence_no,
    }


def _compatibility_dict(c) -> dict:
    return {
        "id": str(c.id),
        "compatibility_code": c.compatibility_code,
        "version_no": c.version_no,
        "drug_constituent_version_id": str(c.drug_constituent_version_id),
        "device_constituent_version_id": str(c.device_constituent_version_id),
        "interface_constraints": c.interface_constraints,
        "status": c.status,
        "effective_from": c.effective_from.isoformat() if c.effective_from else None,
        "effective_to": c.effective_to.isoformat() if c.effective_to else None,
        "vault_object_id": str(c.vault_object_id) if c.vault_object_id else None,
    }


@router.post("/drafts", response_model=MutationReceipt)
async def post_create_draft(
    cmd: CreateProductDraftCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="product.author", site_id=cmd.site_id)
        return await create_draft(session, cmd, actor.user_id)


@router.put("/drafts/{product_version_id}", response_model=MutationReceipt)
async def put_update_draft(
    product_version_id: uuid.UUID,
    cmd: UpdateProductDraftCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.product_version_id != product_version_id:
        raise ValidationFailedError("product_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="product.author", site_id=None)
        return await update_draft(session, cmd, actor.user_id)


@router.post("/drafts/{product_version_id}/submit", response_model=MutationReceipt)
async def post_submit_draft(
    product_version_id: uuid.UUID,
    cmd: SubmitProductDraftCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.product_version_id != product_version_id:
        raise ValidationFailedError("product_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="product.author", site_id=None)
        return await submit_draft(session, cmd, actor.user_id)


@router.post("/drafts/{product_version_id}/release", response_model=MutationReceipt)
async def post_release_draft(
    product_version_id: uuid.UUID,
    cmd: ReleaseProductVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.product_version_id != product_version_id:
        raise ValidationFailedError("product_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="product.release", site_id=None)
        return await release_product_version(session, cmd, actor.user_id)


@router.post("/{product_version_id}/suspend", response_model=MutationReceipt)
async def post_suspend(
    product_version_id: uuid.UUID,
    cmd: SuspendProductVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.product_version_id != product_version_id:
        raise ValidationFailedError("product_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="product.suspend", site_id=None)
        return await suspend_product_version(session, cmd, actor.user_id)


@router.post("/{product_version_id}/reinstate", response_model=MutationReceipt)
async def post_reinstate(
    product_version_id: uuid.UUID,
    cmd: ReinstateProductVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.product_version_id != product_version_id:
        raise ValidationFailedError("product_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="product.suspend", site_id=None)
        return await reinstate_product_version(session, cmd, actor.user_id)


@router.get("/{product_business_id}/versions")
async def get_versions(
    product_business_id: str,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    await evaluate_policy(session, actor.user_id, action="product.view", site_id=None)
    versions = await product_master_service.list_versions_for_business_id(session, product_business_id)
    return [_version_dict(v) for v in versions]


@router.get("/{product_version_id}")
async def get_version_detail(
    product_version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="product.view", site_id=None)
    version = await product_master_service.get_version(session, product_version_id)
    constituents = await product_master_service.get_constituents(session, product_version_id)
    body = _version_dict(version)
    body["constituents"] = [_constituent_dict(c) for c in constituents]
    return body


@router.post("/{product_version_id}/validate-completeness", response_model=MutationReceipt)
async def post_validate_completeness(
    product_version_id: uuid.UUID,
    cmd: ValidateCompletenessCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.product_version_id != product_version_id:
        raise ValidationFailedError("product_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="product.author", site_id=None)
        return await validate_completeness_command(session, cmd, actor.user_id)


@router.get("/{product_version_id}/compatibility")
async def get_compatibility(
    product_version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    await evaluate_policy(session, actor.user_id, action="product.view", site_id=None)
    rows = (
        (
            await session.execute(
                select(ConstituentCompatibilityVersion).where(
                    or_(
                        ConstituentCompatibilityVersion.drug_constituent_version_id == product_version_id,
                        ConstituentCompatibilityVersion.device_constituent_version_id == product_version_id,
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    return [_compatibility_dict(c) for c in rows]


@router.get("/{product_version_id}/issue-eligibility")
async def get_issue_eligibility(
    product_version_id: uuid.UUID,
    site: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="product.view", site_id=None)
    version = await product_master_service.get_version(session, product_version_id)
    constituents = await product_master_service.get_constituents(session, product_version_id)
    findings = product_master_service.validate_completeness(version, constituents)
    return product_master_service.check_issue_eligibility(version, findings)
