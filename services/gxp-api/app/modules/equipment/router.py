import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.equipment.cleaning_models import EquipmentArea
from app.modules.equipment.commands import (
    BulkImportEquipmentCommand,
    BulkImportEquipmentResult,
    BulkImportEquipmentRow,
    BulkImportEquipmentRowValidation,
    CreateEquipmentAreaCommand,
    CreateEquipmentAssetCommand,
    HoldEquipmentCommand,
    RecordCalibrationCommand,
    RecordMaintenanceCommand,
    RecordQualificationCommand,
    RelocateEquipmentCommand,
    ReserveEquipmentCommand,
    RetireEquipmentCommand,
    ReturnToServiceCommand,
    bulk_import_equipment,
    create_equipment_area,
    create_equipment_asset,
    equipment_record_hash,
    get_dashboard,
    get_eligibility,
    get_equipment_history,
    hold_equipment,
    record_calibration,
    record_maintenance,
    record_qualification,
    relocate_equipment,
    reserve_equipment,
    retire_equipment,
    return_to_service,
    validate_bulk_import_equipment_rows,
)
from app.modules.equipment.models import EquipmentAsset
from app.modules.policy.service import evaluate_policy, resolve_site_scope
from app.modules.recipe_master.service import list_equipment_classes
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/equipment/v1", tags=["equipment"])

ASSET_SORTABLE = {
    "equipment_code": EquipmentAsset.equipment_code,
    "state": EquipmentAsset.state,
    "created_at": EquipmentAsset.created_at,
}


def _asset_dict(asset: EquipmentAsset) -> dict:
    return {
        "id": str(asset.id),
        "site_id": str(asset.site_id),
        "equipment_code": asset.equipment_code,
        "equipment_class_id": str(asset.equipment_class_id) if asset.equipment_class_id else None,
        "manufacturer": asset.manufacturer,
        "model": asset.model,
        "serial_no": asset.serial_no,
        "location_id": str(asset.location_id) if asset.location_id else None,
        "state": asset.state,
        "qualification_status": asset.qualification_status,
        "qualification_effective_date": asset.qualification_effective_date.isoformat() if asset.qualification_effective_date else None,
        "qualification_expiry_date": asset.qualification_expiry_date.isoformat() if asset.qualification_expiry_date else None,
        "qualification_scope": asset.qualification_scope,
        "calibration_status": asset.calibration_status,
        "next_calibration_due_date": asset.next_calibration_due_date.isoformat() if asset.next_calibration_due_date else None,
        "maintenance_status": asset.maintenance_status,
        "next_maintenance_due_date": asset.next_maintenance_due_date.isoformat() if asset.next_maintenance_due_date else None,
        "cleanliness_status": asset.cleanliness_status,
        "hold_flag": asset.hold_flag,
        "hold_reason": asset.hold_reason,
        "hold_source": asset.hold_source,
        "dedicated": asset.dedicated,
        "firmware_version": asset.firmware_version,
        "is_computer_operated": asset.is_computer_operated,
        "recalibration_required": asset.recalibration_required,
        "change_control_id": str(asset.change_control_id) if asset.change_control_id else None,
        "version": asset.version,
    }


@router.post("/assets", response_model=MutationReceipt)
async def post_create_asset(
    cmd: CreateEquipmentAssetCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="equipment_asset.create", site_id=cmd.site_id)
        return await create_equipment_asset(session, cmd, actor.user_id)


class BulkImportEquipmentPreviewRequest(BaseModel):
    rows: list[BulkImportEquipmentRow]


@router.post("/assets/bulk-import/preview")
async def post_bulk_import_equipment_preview(
    body: BulkImportEquipmentPreviewRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[BulkImportEquipmentRowValidation]:
    """Read-only -- validates every row (unknown equipment_class_code, duplicate/existing equipment_code)
    and reports per-row errors without creating anything, same shape as the user bulk-import preview."""
    await evaluate_policy(session, actor.user_id, action="equipment_asset.create", site_id=None)
    return await validate_bulk_import_equipment_rows(session, body.rows)


@router.post("/assets/bulk-import/commit", response_model=BulkImportEquipmentResult)
async def post_bulk_import_equipment_commit(
    cmd: BulkImportEquipmentCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> BulkImportEquipmentResult:
    """All-or-nothing: if any row fails validation the whole batch is rejected with the per-row reasons
    and nothing is created."""
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="equipment_asset.create", site_id=cmd.site_id)
        return await bulk_import_equipment(session, cmd, actor.user_id)


# Client Topic 15 fix (2026-10-02, project-owner-directed): this router's reads held an `actor`
# dependency but never called evaluate_policy() or filtered by site -- any authenticated actor, any
# role, any site, could list/fetch any other site's equipment (the module docstring's own prior
# "no RBAC gate here ... same precedent" note is superseded by the client's explicit Topic 15 answer
# that cross-site access must be controlled, full stop). `equipment_asset.view`/`equipment_area.view`
# are new permission codes (seed.py), granted to every role that already touches equipment plus the
# standard "view" roleset.
@router.get("/assets")
async def list_assets(
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    state: str | None = None,
    site_id: uuid.UUID | None = None,
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    site_scope = await resolve_site_scope(session, actor.user_id, site_id, action="equipment_asset.view")
    stmt = select(EquipmentAsset).where(EquipmentAsset.site_id.in_(site_scope))
    if params.q:
        stmt = stmt.where(EquipmentAsset.equipment_code.ilike(f"%{params.q}%"))
    if state:
        stmt = stmt.where(EquipmentAsset.state == state)
    rows, envelope = await paginate(session, stmt, params, sortable=ASSET_SORTABLE, default_sort=EquipmentAsset.created_at)
    return {**envelope, "items": [_asset_dict(a) for (a,) in rows]}


@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    asset = await session.get(EquipmentAsset, asset_id)
    if asset is None:
        raise NotFoundError("Equipment asset not found")
    await evaluate_policy(session, actor.user_id, action="equipment_asset.view", site_id=asset.site_id)
    return _asset_dict(asset)


AREA_SORTABLE = {
    "area_code": EquipmentArea.area_code,
    "created_at": EquipmentArea.created_at,
}


def _area_dict(area: EquipmentArea) -> dict:
    return {
        "id": str(area.id),
        "site_id": str(area.site_id),
        "area_code": area.area_code,
        "area_type": area.area_type,
        "classification": area.classification,
        "criticality": area.criticality,
        "cleanliness_status": area.cleanliness_status,
        "status": area.status,
    }


# Read-only master-data list — `EquipmentArea` (`equipment.equipment_areas`) is referenced by
# `area_id`/`line_id` fields across cleaning, EM, aseptic and DDCP, all of which previously had no way
# to look one up except a raw UUID the operator had to already know. This mirrors `/assets`'s read-only
# list shape.
#
# **2026-09-07, project-owner-directed** — write capability (`POST /areas` below) was added too, same
# "own considered create contract, not a guessed one" precedent as `warehouse_location.create`/
# `aseptic_profile_version.create`: areas were genuinely uncreatable through the app otherwise (seed-only,
# `EquipmentArea`'s own docstring called it "provisioned outside the app today"), found while building
# this same picker for `/aseptic`'s "Create aseptic operation" form. Gated by a new
# `equipment_area.create` permission code (Admin + Equipment Administrator — same roles as
# `equipment_asset.create`). No qualification/release workflow exists for an area, so create enters
# directly at `status="active"`.
@router.post("/areas", response_model=MutationReceipt)
async def post_create_area(
    cmd: CreateEquipmentAreaCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="equipment_area.create", site_id=cmd.site_id)
        return await create_equipment_area(session, cmd, actor.user_id)


@router.get("/areas")
async def list_areas(
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    site_scope = await resolve_site_scope(session, actor.user_id, site_id, action="equipment_area.view")
    stmt = select(EquipmentArea).where(EquipmentArea.site_id.in_(site_scope))
    if params.q:
        stmt = stmt.where(EquipmentArea.area_code.ilike(f"%{params.q}%"))
    rows, envelope = await paginate(session, stmt, params, sortable=AREA_SORTABLE, default_sort=EquipmentArea.created_at)
    return {**envelope, "items": [_area_dict(a) for (a,) in rows]}


@router.get("/areas/{area_id}")
async def get_area(
    area_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    area = await session.get(EquipmentArea, area_id)
    if area is None:
        raise NotFoundError("Equipment area not found")
    await evaluate_policy(session, actor.user_id, action="equipment_area.view", site_id=area.site_id)
    return _area_dict(area)


@router.get("/equipment-classes")
async def list_equipment_classes_for_assets(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    """SG-218: equipment-module-native read of `gxp_equipment_class` (owned by recipe_master, read via its
    own service function per AG-02 -- never this module's tables reached into directly) so "New equipment
    asset" can offer a class picker without requiring the recipe.view permission recipe_master's own
    `/recipes/v2/equipment-classes` endpoint requires. Equipment Administrator (this module's own
    asset-creating role, seed.py) never held recipe.view and has no reason to need visibility into
    unrelated recipe/product data just to classify an asset. No RBAC gate here, matching this router's own
    other plain read endpoints (list_assets/list_areas/get_dashboard) -- additive, non-regulated read
    data, same precedent."""
    classes = await list_equipment_classes(session)
    return [
        {"id": str(c.id), "class_code": c.class_code, "name": c.name, "description": c.description, "status": c.status}
        for c in classes
    ]


@router.post("/{asset_id}/qualifications", response_model=MutationReceipt)
async def post_record_qualification(
    asset_id: uuid.UUID,
    cmd: RecordQualificationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.asset_id != asset_id:
        raise ValidationFailedError("asset_id in path and body must match")
    async with session.begin():
        asset = await session.get(EquipmentAsset, asset_id)
        if asset is None:
            raise NotFoundError("Equipment asset not found")
        await evaluate_policy(session, actor.user_id, action="equipment_asset.qualify", site_id=asset.site_id)
        return await record_qualification(session, cmd, actor.user_id)


@router.post("/{asset_id}/calibrations", response_model=MutationReceipt)
async def post_record_calibration(
    asset_id: uuid.UUID,
    cmd: RecordCalibrationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.asset_id != asset_id:
        raise ValidationFailedError("asset_id in path and body must match")
    async with session.begin():
        asset = await session.get(EquipmentAsset, asset_id)
        if asset is None:
            raise NotFoundError("Equipment asset not found")
        # Client gap-analysis Phase 4: approving/rejecting an existing calibration is a distinct
        # authority from recording one in the first place (the whole point is SoD between the two) --
        # gate it on its own permission, held by QA Releaser, not Calibration Technician.
        action = "equipment_asset.approve_calibration" if cmd.calibration_id is not None else "equipment_asset.calibrate"
        await evaluate_policy(session, actor.user_id, action=action, site_id=asset.site_id)
        return await record_calibration(session, cmd, actor.user_id)


@router.post("/{asset_id}/maintenance", response_model=MutationReceipt)
async def post_record_maintenance(
    asset_id: uuid.UUID,
    cmd: RecordMaintenanceCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.asset_id != asset_id:
        raise ValidationFailedError("asset_id in path and body must match")
    async with session.begin():
        asset = await session.get(EquipmentAsset, asset_id)
        if asset is None:
            raise NotFoundError("Equipment asset not found")
        await evaluate_policy(session, actor.user_id, action="equipment_asset.maintain", site_id=asset.site_id)
        return await record_maintenance(session, cmd, actor.user_id)


class EquipmentSignatureChallengeRequest(BaseModel):
    action: str = "hold"


_EQUIPMENT_CHALLENGE_MEANINGS = {"hold": "Performed", "retire": "Approved"}


@router.post("/{asset_id}/signature-challenges")
async def post_equipment_signature_challenge(
    asset_id: uuid.UUID,
    body: EquipmentSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        asset = await session.get(EquipmentAsset, asset_id)
        if asset is None:
            raise NotFoundError("Equipment asset not found")
        meaning = _EQUIPMENT_CHALLENGE_MEANINGS.get(body.action)
        if meaning is None:
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="equipment_asset", record_id=asset.id,
            record_version=asset.version, record_hash=equipment_record_hash(asset), meaning=meaning,
        )
        return {
            "challenge_id": str(challenge.id),
            "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


@router.post("/{asset_id}/hold", response_model=MutationReceipt)
async def post_hold_equipment(
    asset_id: uuid.UUID,
    cmd: HoldEquipmentCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.asset_id != asset_id:
        raise ValidationFailedError("asset_id in path and body must match")
    async with session.begin():
        asset = await session.get(EquipmentAsset, asset_id)
        if asset is None:
            raise NotFoundError("Equipment asset not found")
        await evaluate_policy(session, actor.user_id, action="equipment_asset.hold", site_id=asset.site_id)
        return await hold_equipment(session, cmd, actor.user_id)


@router.post("/{asset_id}/return-to-service", response_model=MutationReceipt)
async def post_return_to_service(
    asset_id: uuid.UUID,
    cmd: ReturnToServiceCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.asset_id != asset_id:
        raise ValidationFailedError("asset_id in path and body must match")
    async with session.begin():
        asset = await session.get(EquipmentAsset, asset_id)
        if asset is None:
            raise NotFoundError("Equipment asset not found")
        await evaluate_policy(session, actor.user_id, action="equipment_asset.return_to_service", site_id=asset.site_id)
        return await return_to_service(session, cmd, actor.user_id)


@router.post("/{asset_id}/reserve", response_model=MutationReceipt)
async def post_reserve_equipment(
    asset_id: uuid.UUID,
    cmd: ReserveEquipmentCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.asset_id != asset_id:
        raise ValidationFailedError("asset_id in path and body must match")
    async with session.begin():
        asset = await session.get(EquipmentAsset, asset_id)
        if asset is None:
            raise NotFoundError("Equipment asset not found")
        await evaluate_policy(session, actor.user_id, action="equipment_asset.reserve", site_id=asset.site_id)
        return await reserve_equipment(session, cmd, actor.user_id)


@router.post("/{asset_id}/retire", response_model=MutationReceipt)
async def post_retire_equipment(
    asset_id: uuid.UUID,
    cmd: RetireEquipmentCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.asset_id != asset_id:
        raise ValidationFailedError("asset_id in path and body must match")
    async with session.begin():
        asset = await session.get(EquipmentAsset, asset_id)
        if asset is None:
            raise NotFoundError("Equipment asset not found")
        await evaluate_policy(session, actor.user_id, action="equipment_asset.retire", site_id=asset.site_id)
        return await retire_equipment(session, cmd, actor.user_id)


@router.post("/{asset_id}/relocate", response_model=MutationReceipt)
async def post_relocate_equipment(
    asset_id: uuid.UUID,
    cmd: RelocateEquipmentCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.asset_id != asset_id:
        raise ValidationFailedError("asset_id in path and body must match")
    async with session.begin():
        asset = await session.get(EquipmentAsset, asset_id)
        if asset is None:
            raise NotFoundError("Equipment asset not found")
        await evaluate_policy(session, actor.user_id, action="equipment_asset.relocate", site_id=asset.site_id)
        return await relocate_equipment(session, cmd, actor.user_id)


@router.get("/{asset_id}/eligibility")
async def get_asset_eligibility(
    asset_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        return await get_eligibility(session, asset_id)


@router.get("/{asset_id}/history")
async def get_asset_history(
    asset_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        return await get_equipment_history(session, asset_id)


@router.get("/dashboard")
async def get_equipment_dashboard(
    site_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        return await get_dashboard(session, site_id)
