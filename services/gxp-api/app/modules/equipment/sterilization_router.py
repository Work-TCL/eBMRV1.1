import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.batch_execution.models import Batch
from app.modules.equipment.models import EquipmentAsset
from app.modules.equipment.sterilization_commands import (
    CompleteFilterUseCommand,
    CreateProcessCycleCommand,
    CreateProcessCycleProfileVersionCommand,
    InstallFilterCommand,
    RecordCycleDataCommand,
    RecordFilterIntegrityTestCommand,
    ReviewCycleCommand,
    StartCycleCommand,
    complete_filter_use,
    create_process_cycle,
    create_process_cycle_profile_version,
    cycle_record_hash,
    filter_use_record_hash,
    get_item_status,
    install_filter,
    record_cycle_data,
    record_filter_integrity_test,
    review_cycle,
    start_cycle,
)
from app.modules.equipment.sterilization_models import (
    ProcessCycle,
    ProcessCycleProfileVersion,
    SterileFilterUse,
    SterilizationLoadItem,
)
from app.modules.iam.models import User
from app.modules.material.models import Material, MaterialLot
from app.modules.policy.service import evaluate_policy
from app.modules.product_master.models import ProductVersion
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/sterilization/v1", tags=["sterilization"])
cip_sip_router = APIRouter(prefix="/cip-sip/v1", tags=["sterilization"])
filtration_router = APIRouter(prefix="/filtration/v1", tags=["sterilization"])


def _cycle_dict(cycle: ProcessCycle, refs: dict | None = None) -> dict:
    refs = refs or {}
    return {
        "id": str(cycle.id),
        "site_id": str(cycle.site_id),
        "process_type": cycle.process_type,
        "equipment_id": str(cycle.equipment_id),
        "equipment_code": refs.get("equipment_code"),
        "profile_version_id": str(cycle.profile_version_id),
        "profile_number": refs.get("profile_number"),
        "profile_version_no": refs.get("profile_version_no"),
        "batch_id": str(cycle.batch_id) if cycle.batch_id else None,
        "batch_number": refs.get("batch_number"),
        "batch_product_name": refs.get("batch_product_name"),
        "batch_product_code": refs.get("batch_product_code"),
        "controller_cycle_id": cycle.controller_cycle_id,
        "state": cycle.state,
        "critical_alarm": cycle.critical_alarm,
        "indicator_results": cycle.indicator_results,
        "parameter_summary": cycle.parameter_summary,
        "alarm_summary": cycle.alarm_summary,
        "reprocessing_authorization_ref": cycle.reprocessing_authorization_ref,
        "requires_deviation": cycle.requires_deviation,
        "started_at": cycle.started_at.isoformat() if cycle.started_at else None,
        "started_by_user_id": str(cycle.started_by_user_id) if cycle.started_by_user_id else None,
        "started_by_full_name": refs.get("started_by_full_name"),
        "started_by_username": refs.get("started_by_username"),
        "completed_at": cycle.completed_at.isoformat() if cycle.completed_at else None,
        "reviewer_user_id": str(cycle.reviewer_user_id) if cycle.reviewer_user_id else None,
        "reviewer_full_name": refs.get("reviewer_full_name"),
        "reviewer_username": refs.get("reviewer_username"),
        "review_signature_id": str(cycle.review_signature_id) if cycle.review_signature_id else None,
        "deviation_reference_id": str(cycle.deviation_reference_id) if cycle.deviation_reference_id else None,
        "version": cycle.version,
        "created_at": cycle.created_at.isoformat() if cycle.created_at else None,
        "created_at": cycle.created_at.isoformat() if cycle.created_at else None,
    }


async def _resolve_cycle_refs(session: AsyncSession, cycles: list[ProcessCycle]) -> dict[uuid.UUID, dict]:
    """Batch-resolves every foreign key `_cycle_dict` needs a human-readable label for -- equipment,
    profile version, batch/product and the start/review users -- so the UI never has to show a raw id.
    One query per referenced table regardless of how many cycles are being rendered."""
    if not cycles:
        return {}

    equipment_ids = {c.equipment_id for c in cycles}
    profile_ids = {c.profile_version_id for c in cycles}
    batch_ids = {c.batch_id for c in cycles if c.batch_id}
    user_ids = {c.started_by_user_id for c in cycles if c.started_by_user_id}
    user_ids |= {c.reviewer_user_id for c in cycles if c.reviewer_user_id}

    equipment_by_id = dict(
        (await session.execute(select(EquipmentAsset.id, EquipmentAsset.equipment_code).where(EquipmentAsset.id.in_(equipment_ids)))).all()
    )
    profile_by_id = {
        row.id: (row.profile_number, row.version_no)
        for row in (
            await session.execute(
                select(ProcessCycleProfileVersion.id, ProcessCycleProfileVersion.profile_number, ProcessCycleProfileVersion.version_no)
                .where(ProcessCycleProfileVersion.id.in_(profile_ids))
            )
        ).all()
    }
    batch_by_id: dict[uuid.UUID, tuple[str, str, str]] = {}
    if batch_ids:
        batch_by_id = {
            row.id: (row.batch_number, row.name, row.product_code)
            for row in (
                await session.execute(
                    select(Batch.id, Batch.batch_number, ProductVersion.name, ProductVersion.product_code)
                    .join(ProductVersion, ProductVersion.id == Batch.product_version_id)
                    .where(Batch.id.in_(batch_ids))
                )
            ).all()
        }
    user_by_id: dict[uuid.UUID, tuple[str, str]] = {}
    if user_ids:
        user_by_id = {
            row.id: (row.full_name, row.username)
            for row in (await session.execute(select(User.id, User.full_name, User.username).where(User.id.in_(user_ids)))).all()
        }

    resolved: dict[uuid.UUID, dict] = {}
    for c in cycles:
        profile_number, profile_version_no = profile_by_id.get(c.profile_version_id, (None, None))
        batch_number, product_name, product_code = batch_by_id.get(c.batch_id, (None, None, None)) if c.batch_id else (None, None, None)
        started_by = user_by_id.get(c.started_by_user_id) if c.started_by_user_id else None
        reviewer = user_by_id.get(c.reviewer_user_id) if c.reviewer_user_id else None
        resolved[c.id] = {
            "equipment_code": equipment_by_id.get(c.equipment_id),
            "profile_number": profile_number,
            "profile_version_no": profile_version_no,
            "batch_number": batch_number,
            "batch_product_name": product_name,
            "batch_product_code": product_code,
            "started_by_full_name": started_by[0] if started_by else None,
            "started_by_username": started_by[1] if started_by else None,
            "reviewer_full_name": reviewer[0] if reviewer else None,
            "reviewer_username": reviewer[1] if reviewer else None,
        }
    return resolved


def _load_item_dict(item: SterilizationLoadItem, lot_label: str | None = None) -> dict:
    return {
        "id": str(item.id),
        "item_type": item.item_type,
        "item_reference": item.item_reference,
        # Set only when `item_reference` resolved against a real material lot (see
        # `_resolve_load_item_lot_labels`) -- null for a non-lot item (garment, filter, …), where
        # `item_reference` is already the free-text reference and there is nothing to resolve.
        "item_reference_label": lot_label,
        "position": item.position,
        "sterile_status": item.sterile_status,
        "sterile_status_expiry": item.sterile_status_expiry.isoformat() if item.sterile_status_expiry else None,
    }


async def _resolve_load_item_lot_labels(session: AsyncSession, items: list[SterilizationLoadItem]) -> dict[uuid.UUID, str]:
    """Best-effort human label for `item_reference` when it's a material lot's raw database id rather
    than its `internal_lot` code -- the shape a `SterilizationLoadItem` written before the "Item
    reference" picker was fixed to store the lot's code holds (or any future non-UI caller that passes
    an id). Anything that isn't a valid uuid, or doesn't match a lot, is left unresolved -- it's either
    already the human code the picker now writes, or a genuinely free-text non-lot reference (garment,
    filter, …), neither of which this should touch."""
    candidate_ids: set[uuid.UUID] = set()
    for item in items:
        try:
            candidate_ids.add(uuid.UUID(item.item_reference))
        except (ValueError, AttributeError, TypeError):
            continue
    if not candidate_ids:
        return {}
    rows = (
        await session.execute(
            select(MaterialLot.id, MaterialLot.internal_lot, Material.name)
            .join(Material, Material.id == MaterialLot.material_id)
            .where(MaterialLot.id.in_(candidate_ids))
        )
    ).all()
    return {row.id: f"{row.internal_lot} ({row.name})" for row in rows}


CYCLE_SORTABLE = {
    "process_type": ProcessCycle.process_type,
    "state": ProcessCycle.state,
    "created_at": ProcessCycle.created_at,
}


@router.get("/cycles")
async def list_cycles(
    site_id: uuid.UUID, session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params),
) -> dict:
    """Browsable list for `/sterilization`'s own "Sterilization cycles" section -- the page previously had
    no way to see what cycles existed at all, only look one up by an already-known id. Same SG-081
    read-side precedent as `/items/eligible` and `/profiles` above; a plain listing here doesn't conflict
    with any future write/CRUD contract. Paginated (shared envelope) so the frontend's `DataTable` can
    page/search/sort it the same as every other list page."""
    async with session.begin():
        stmt = select(ProcessCycle).where(ProcessCycle.site_id == site_id)
        if params.q:
            stmt = stmt.where(ProcessCycle.process_type.ilike(f"%{params.q}%"))
        rows, envelope = await paginate(session, stmt, params, sortable=CYCLE_SORTABLE, default_sort=ProcessCycle.created_at)
        cycles = [c for (c,) in rows]
        refs = await _resolve_cycle_refs(session, cycles)
        return {**envelope, "items": [_cycle_dict(c, refs.get(c.id)) for c in cycles]}


PROFILE_SORTABLE = {
    "profile_number": ProcessCycleProfileVersion.profile_number,
    "created_at": ProcessCycleProfileVersion.created_at,
}


def _profile_summary_dict(profile: ProcessCycleProfileVersion) -> dict:
    return {
        "id": str(profile.id),
        "profile_number": profile.profile_number,
        "version": profile.version_no,
        "process_type": profile.process_type,
        "state": profile.state,
        "sterile_status_validity_hours": profile.sterile_status_validity_hours,
    }


@router.get("/profiles")
async def list_profiles(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params), state: str | None = "RELEASED",
) -> dict:
    """Real picker data for `CreateProcessCycleCommand.profile_version_id` -- previously free-text UUID
    entry with no way to discover a valid id, same SG-081 read-side precedent as `/items/eligible` above.
    Defaults to RELEASED only (the only state a real cycle should actually be started against); pass
    `state=` (empty) to see every state, matching the DDCP profile-list precedent (`ddcp/router.py`'s
    `list_profiles`)."""
    async with session.begin():
        stmt = select(ProcessCycleProfileVersion)
        if params.q:
            stmt = stmt.where(ProcessCycleProfileVersion.profile_number.ilike(f"%{params.q}%"))
        if state:
            stmt = stmt.where(ProcessCycleProfileVersion.state == state)
        rows, envelope = await paginate(
            session, stmt, params, sortable=PROFILE_SORTABLE, default_sort=ProcessCycleProfileVersion.created_at
        )
        return {**envelope, "items": [_profile_summary_dict(p) for (p,) in rows]}


@router.post("/profiles", response_model=MutationReceipt)
async def post_create_profile(
    cmd: CreateProcessCycleProfileVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    """SG-203 RESOLVED 2026-09-16, project-owner-directed. See sterilization_commands.py's own docstring
    note above `CreateProcessCycleProfileVersionCommand` for the authoring-role/lifecycle decision."""
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="process_cycle_profile_version.create", site_id=cmd.site_id)
        return await create_process_cycle_profile_version(session, cmd, actor.user_id)


@router.post("/cycles", response_model=MutationReceipt)
async def post_create_cycle(
    cmd: CreateProcessCycleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="process_cycle.create", site_id=cmd.site_id)
        return await create_process_cycle(session, cmd, actor.user_id)


@cip_sip_router.post("/cycles", response_model=MutationReceipt)
async def post_create_cip_sip_cycle(
    cmd: CreateProcessCycleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="process_cycle.create", site_id=cmd.site_id)
        return await create_process_cycle(session, cmd, actor.user_id)


@router.get("/cycles/{cycle_id}")
async def get_cycle(cycle_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    cycle = await session.get(ProcessCycle, cycle_id)
    if cycle is None:
        raise NotFoundError("Process cycle not found")
    refs = await _resolve_cycle_refs(session, [cycle])
    load_items = (
        (
            await session.execute(
                select(SterilizationLoadItem)
                .where(SterilizationLoadItem.cycle_id == cycle.id)
                .order_by(SterilizationLoadItem.created_at)
            )
        )
        .scalars()
        .all()
    )
    lot_labels = await _resolve_load_item_lot_labels(session, load_items)

    def _lot_label(item: SterilizationLoadItem) -> str | None:
        try:
            return lot_labels.get(uuid.UUID(item.item_reference))
        except (ValueError, AttributeError, TypeError):
            return None

    return {
        **_cycle_dict(cycle, refs.get(cycle.id)),
        "load_items": [_load_item_dict(i, _lot_label(i)) for i in load_items],
    }


class CycleSignatureChallengeRequest(BaseModel):
    action: str  # "start" | "review"


_CYCLE_CHALLENGE_MEANINGS = {"start": "Performed", "review": "Reviewed"}


@router.post("/cycles/{cycle_id}/signature-challenges")
async def post_cycle_signature_challenge(
    cycle_id: uuid.UUID,
    body: CycleSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        cycle = await session.get(ProcessCycle, cycle_id)
        if cycle is None:
            raise NotFoundError("Process cycle not found")
        meaning = _CYCLE_CHALLENGE_MEANINGS.get(body.action)
        if meaning is None:
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="process_cycle", record_id=cycle.id,
            record_version=cycle.version, record_hash=cycle_record_hash(cycle), meaning=meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/cycles/{cycle_id}/start", response_model=MutationReceipt)
async def post_start_cycle(
    cycle_id: uuid.UUID,
    cmd: StartCycleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.cycle_id != cycle_id:
        raise ValidationFailedError("cycle_id in path and body must match")
    async with session.begin():
        cycle = await session.get(ProcessCycle, cycle_id)
        if cycle is None:
            raise NotFoundError("Process cycle not found")
        await evaluate_policy(session, actor.user_id, action="process_cycle.start", site_id=cycle.site_id)
        return await start_cycle(session, cmd, actor.user_id)


@router.post("/cycles/{cycle_id}/data", response_model=MutationReceipt)
async def post_record_data(
    cycle_id: uuid.UUID,
    cmd: RecordCycleDataCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.cycle_id != cycle_id:
        raise ValidationFailedError("cycle_id in path and body must match")
    async with session.begin():
        cycle = await session.get(ProcessCycle, cycle_id)
        if cycle is None:
            raise NotFoundError("Process cycle not found")
        await evaluate_policy(session, actor.user_id, action="process_cycle.start", site_id=cycle.site_id)
        return await record_cycle_data(session, cmd, actor.user_id)


@router.post("/cycles/{cycle_id}/review", response_model=MutationReceipt)
async def post_review_cycle(
    cycle_id: uuid.UUID,
    cmd: ReviewCycleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.cycle_id != cycle_id:
        raise ValidationFailedError("cycle_id in path and body must match")
    async with session.begin():
        cycle = await session.get(ProcessCycle, cycle_id)
        if cycle is None:
            raise NotFoundError("Process cycle not found")
        await evaluate_policy(session, actor.user_id, action="process_cycle.review", site_id=cycle.site_id)
        return await review_cycle(session, cmd, actor.user_id)


@router.get("/items/eligible")
async def get_eligible_items(
    site_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    """Real picker data for any field that references a completed sterilization/depyrogenation
    preparation record by id -- DDCP's constituent-handoff "Sterilization/depyrogenation reference"
    (PFS-FR-005) is the first caller, previously free-text UUID entry with no way to discover a valid id.
    Document 42's own declared API list has no "list eligible items" operation either -- same SG-081
    read-side precedent already used for warehouse locations/material containers: a plain read-only GET
    listing doesn't conflict with any future write/CRUD contract, it only replaces hand-typed UUIDs.

    Lists exactly the two kinds `get_item_status()` (this module's own polymorphic status lookup) would
    report as ready/eligible -- a `SterilizationLoadItem` in `sterile_status` `eligible`, or a
    `SterileFilterUse` in `state` `completed` -- so every id offered here is guaranteed to pass whatever
    check a caller runs against it, not just guaranteed to exist."""
    load_items = (
        await session.execute(
            select(SterilizationLoadItem, ProcessCycle.process_type)
            .join(ProcessCycle, ProcessCycle.id == SterilizationLoadItem.cycle_id)
            .where(ProcessCycle.site_id == site_id, SterilizationLoadItem.sterile_status == "eligible")
            .order_by(SterilizationLoadItem.created_at.desc())
        )
    ).all()
    filter_uses = (
        (
            await session.execute(
                select(SterileFilterUse)
                .where(SterileFilterUse.site_id == site_id, SterileFilterUse.state == "completed")
                .order_by(SterileFilterUse.id.desc())
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(item.id),
            "kind": "load_item",
            "label": (
                f"{item.item_reference} ({item.item_type}) — {process_type} cycle, eligible"
                + (f" until {item.sterile_status_expiry.date().isoformat()}" if item.sterile_status_expiry else "")
            ),
        }
        for item, process_type in load_items
    ] + [
        {"id": str(use.id), "kind": "filter_use", "label": f"Filter {use.filter_serial} — completed"}
        for use in filter_uses
    ]


@router.get("/items/{item_id}/status")
async def get_status(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    async with session.begin():
        return await get_item_status(session, item_id)


def _filter_use_dict(use: SterileFilterUse) -> dict:
    return {
        "id": str(use.id),
        "site_id": str(use.site_id),
        "filter_lot": use.filter_lot,
        "filter_serial": use.filter_serial,
        "filter_type": use.filter_type,
        "manufacturer": use.manufacturer,
        "batch_id": str(use.batch_id) if use.batch_id else None,
        "sterilization_cycle_id": str(use.sterilization_cycle_id) if use.sterilization_cycle_id else None,
        "housing_location": use.housing_location,
        "direction": use.direction,
        "installed_by_user_id": str(use.installed_by_user_id) if use.installed_by_user_id else None,
        "installed_at": use.installed_at.isoformat() if use.installed_at else None,
        "state": use.state,
        "pre_use_integrity_result": use.pre_use_integrity_result,
        "pre_use_integrity_ref": use.pre_use_integrity_ref,
        "post_use_integrity_result": use.post_use_integrity_result,
        "post_use_integrity_ref": use.post_use_integrity_ref,
        "process_parameters": use.process_parameters,
        "reuse_count": use.reuse_count,
        "performer_user_id": str(use.performer_user_id) if use.performer_user_id else None,
        "requires_deviation": use.requires_deviation,
        "deviation_reference_id": str(use.deviation_reference_id) if use.deviation_reference_id else None,
        "version": use.version,
        "created_at": use.created_at.isoformat() if use.created_at else None,
    }


@filtration_router.post("/filters/install", response_model=MutationReceipt)
async def post_install_filter(
    cmd: InstallFilterCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="sterile_filter_use.create", site_id=cmd.site_id)
        return await install_filter(session, cmd, actor.user_id)


@filtration_router.get("/filters/{use_id}")
async def get_filter_use(use_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    use = await session.get(SterileFilterUse, use_id)
    if use is None:
        raise NotFoundError("Sterile filter use not found")
    return _filter_use_dict(use)


@filtration_router.post("/filters/{use_id}/integrity-tests", response_model=MutationReceipt)
async def post_integrity_test(
    use_id: uuid.UUID,
    cmd: RecordFilterIntegrityTestCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.use_id != use_id:
        raise ValidationFailedError("use_id in path and body must match")
    async with session.begin():
        use = await session.get(SterileFilterUse, use_id)
        if use is None:
            raise NotFoundError("Sterile filter use not found")
        await evaluate_policy(session, actor.user_id, action="sterile_filter_use.create", site_id=use.site_id)
        return await record_filter_integrity_test(session, cmd, actor.user_id)


class FilterUseSignatureChallengeRequest(BaseModel):
    action: str = "complete"


@filtration_router.post("/uses/{use_id}/signature-challenges")
async def post_filter_use_signature_challenge(
    use_id: uuid.UUID,
    body: FilterUseSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        use = await session.get(SterileFilterUse, use_id)
        if use is None:
            raise NotFoundError("Sterile filter use not found")
        if body.action != "complete":
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="sterile_filter_use", record_id=use.id,
            record_version=use.version, record_hash=filter_use_record_hash(use), meaning="Performed",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@filtration_router.post("/uses/{use_id}/complete", response_model=MutationReceipt)
async def post_complete_filter_use(
    use_id: uuid.UUID,
    cmd: CompleteFilterUseCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.use_id != use_id:
        raise ValidationFailedError("use_id in path and body must match")
    async with session.begin():
        use = await session.get(SterileFilterUse, use_id)
        if use is None:
            raise NotFoundError("Sterile filter use not found")
        await evaluate_policy(session, actor.user_id, action="sterile_filter_use.complete", site_id=use.site_id)
        return await complete_filter_use(session, cmd, actor.user_id)
