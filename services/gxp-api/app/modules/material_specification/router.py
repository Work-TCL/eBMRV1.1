import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.material_specification.commands import (
    CreateMaterialSpecDraftCommand,
    ReleaseMaterialSpecVersionCommand,
    create_draft,
    release_material_spec_version,
)
from app.modules.material_specification.models import MaterialSpecificationVersion
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/material-specifications/v1", tags=["material_specification"])


def _version_dict(version: MaterialSpecificationVersion) -> dict:
    return {
        "material_spec_version_id": str(version.id),
        "material_spec_business_id": version.material_spec_business_id,
        "version_no": version.version_no,
        "material_id": str(version.material_id),
        "name": version.name,
        "lifecycle_state": version.lifecycle_state,
        "acceptance_criteria": version.acceptance_criteria,
        "effective_from": version.effective_from.isoformat() if version.effective_from else None,
        "effective_to": version.effective_to.isoformat() if version.effective_to else None,
        "released_vault_object_id": str(version.released_vault_object_id) if version.released_vault_object_id else None,
        "version_hash": version.version_hash,
        "version": version.version,
        "site_id": str(version.site_id),
    }


@router.post("/drafts", response_model=MutationReceipt)
async def post_create_draft(
    cmd: CreateMaterialSpecDraftCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="material_spec.author", site_id=cmd.site_id)
        return await create_draft(session, cmd, actor.user_id)


@router.get("/{material_spec_business_id}/versions")
async def get_versions(
    material_spec_business_id: str,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    await evaluate_policy(session, actor.user_id, action="material_spec.view", site_id=None)
    versions = (
        await session.execute(
            select(MaterialSpecificationVersion)
            .where(MaterialSpecificationVersion.material_spec_business_id == material_spec_business_id)
            .order_by(MaterialSpecificationVersion.version_no)
        )
    ).scalars().all()
    return [_version_dict(v) for v in versions]


@router.get("/{material_spec_version_id}")
async def get_version_detail(
    material_spec_version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="material_spec.view", site_id=None)
    version = await session.get(MaterialSpecificationVersion, material_spec_version_id)
    if version is None:
        raise NotFoundError("Material specification version not found")
    return _version_dict(version)


class VersionSignatureChallengeRequest(BaseModel):
    action: str  # "release"


def _version_record_hash(version: MaterialSpecificationVersion) -> str:
    return sha256_hex({"id": str(version.id), "version": version.version})


_VERSION_CHALLENGE_MEANINGS = {"release": "Released"}


@router.post("/{material_spec_version_id}/signature-challenges")
async def post_version_signature_challenge(
    material_spec_version_id: uuid.UUID,
    body: VersionSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """SG-185: no Document 106 policy row exists yet for material_specification_version/release --
    the challenge endpoint is real, but resolve_signature_requirement() inside release_material_spec_version
    fails closed until a policy row is seeded."""
    async with session.begin():
        version = await session.get(MaterialSpecificationVersion, material_spec_version_id)
        if version is None:
            raise NotFoundError("Material specification version not found")
        meaning = _VERSION_CHALLENGE_MEANINGS.get(body.action)
        if meaning is None:
            raise ValidationFailedError("Unknown or unsigned action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="material_specification_version", record_id=version.id,
            record_version=version.version, record_hash=_version_record_hash(version), meaning=meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/drafts/{material_spec_version_id}/release", response_model=MutationReceipt)
async def post_release_draft(
    material_spec_version_id: uuid.UUID,
    cmd: ReleaseMaterialSpecVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.material_spec_version_id != material_spec_version_id:
        raise ValidationFailedError("material_spec_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="material_spec.release", site_id=None)
        return await release_material_spec_version(session, cmd, actor.user_id)
