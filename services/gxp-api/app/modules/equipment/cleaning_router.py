import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.batch_execution.models import Batch
from app.modules.equipment.cleaning_commands import (
    CompleteCleaningCommand,
    CompleteLineClearanceCommand,
    CreateCleaningExecutionCommand,
    CreateCleaningProcedureVersionCommand,
    CreateLineClearanceCommand,
    RecordCleaningStepCommand,
    VerifyCleaningCommand,
    cleaning_record_hash,
    complete_cleaning,
    complete_line_clearance,
    create_cleaning_execution,
    create_cleaning_procedure_version,
    create_line_clearance,
    get_equipment_cleaning_status,
    line_clearance_record_hash,
    record_cleaning_step,
    verify_cleaning,
)
from app.modules.equipment.cleaning_models import CleaningExecution, CleaningProcedureVersion, EquipmentArea, LineClearance
from app.modules.equipment.models import EquipmentAsset
from app.modules.iam.models import Site, User
from app.modules.policy.service import evaluate_policy
from app.modules.product_master.models import ProductVersion
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/cleaning/v1", tags=["cleaning"])
line_clearance_router = APIRouter(prefix="/line-clearance/v1", tags=["cleaning"])


def _execution_dict(execution: CleaningExecution, refs: dict | None = None) -> dict:
    refs = refs or {}
    return {
        "id": str(execution.id),
        "site_id": str(execution.site_id),
        "equipment_id": str(execution.equipment_id) if execution.equipment_id else None,
        "equipment_code": refs.get("equipment_code"),
        "area_id": str(execution.area_id) if execution.area_id else None,
        "area_code": refs.get("area_code"),
        "procedure_version_id": str(execution.procedure_version_id),
        "procedure_number": refs.get("procedure_number"),
        "procedure_version_no": refs.get("procedure_version_no"),
        "batch_context": execution.batch_context,
        "critical": execution.critical,
        "state": execution.state,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "dirty_since": execution.dirty_since.isoformat(),
        "clean_until": execution.clean_until.isoformat() if execution.clean_until else None,
        "agents_used": execution.agents_used,
        "steps_log": execution.steps_log,
        "previous_batch_identity_removed": execution.previous_batch_identity_removed,
        "disassembly_verified": execution.disassembly_verified,
        "inspection_result": execution.inspection_result,
        "performer_user_id": str(execution.performer_user_id) if execution.performer_user_id else None,
        "performer_username": refs.get("performer_username"),
        "performer_full_name": refs.get("performer_full_name"),
        "reviewer_user_id": str(execution.reviewer_user_id) if execution.reviewer_user_id else None,
        "reviewer_username": refs.get("reviewer_username"),
        "reviewer_full_name": refs.get("reviewer_full_name"),
        "verification_result": execution.verification_result,
        "dirty_hold_exceeded": execution.dirty_hold_exceeded,
        "requires_deviation": execution.requires_deviation,
        "deviation_reference_id": str(execution.deviation_reference_id) if execution.deviation_reference_id else None,
        "swab_sample_id": str(execution.swab_sample_id) if execution.swab_sample_id else None,
        "protection_state": execution.protection_state,
        "sterilization_cycle_id": str(execution.sterilization_cycle_id) if execution.sterilization_cycle_id else None,
        "version": execution.version,
        "created_at": execution.created_at.isoformat() if execution.created_at else None,
    }


async def _resolve_execution_refs(session: AsyncSession, executions: list[CleaningExecution]) -> dict[uuid.UUID, dict]:
    """Batch-resolves every foreign key `_execution_dict` needs a human-readable label for -- equipment,
    area, procedure version and the performer/reviewer users -- so the UI never has to show a raw id.
    Same `_resolve_cycle_refs` shape as sterilization_router.py, one query per referenced table."""
    if not executions:
        return {}

    equipment_ids = {e.equipment_id for e in executions if e.equipment_id}
    area_ids = {e.area_id for e in executions if e.area_id}
    procedure_ids = {e.procedure_version_id for e in executions}
    user_ids = {e.performer_user_id for e in executions if e.performer_user_id}
    user_ids |= {e.reviewer_user_id for e in executions if e.reviewer_user_id}

    equipment_by_id: dict[uuid.UUID, str] = {}
    if equipment_ids:
        equipment_by_id = dict(
            (await session.execute(select(EquipmentAsset.id, EquipmentAsset.equipment_code).where(EquipmentAsset.id.in_(equipment_ids)))).all()
        )
    area_by_id: dict[uuid.UUID, str] = {}
    if area_ids:
        area_by_id = dict(
            (await session.execute(select(EquipmentArea.id, EquipmentArea.area_code).where(EquipmentArea.id.in_(area_ids)))).all()
        )
    procedure_by_id = {
        row.id: (row.procedure_number, row.version_no)
        for row in (
            await session.execute(
                select(CleaningProcedureVersion.id, CleaningProcedureVersion.procedure_number, CleaningProcedureVersion.version_no)
                .where(CleaningProcedureVersion.id.in_(procedure_ids))
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
    for e in executions:
        procedure_number, procedure_version_no = procedure_by_id.get(e.procedure_version_id, (None, None))
        performer = user_by_id.get(e.performer_user_id) if e.performer_user_id else None
        reviewer = user_by_id.get(e.reviewer_user_id) if e.reviewer_user_id else None
        resolved[e.id] = {
            "equipment_code": equipment_by_id.get(e.equipment_id) if e.equipment_id else None,
            "area_code": area_by_id.get(e.area_id) if e.area_id else None,
            "procedure_number": procedure_number,
            "procedure_version_no": procedure_version_no,
            "performer_full_name": performer[0] if performer else None,
            "performer_username": performer[1] if performer else None,
            "reviewer_full_name": reviewer[0] if reviewer else None,
            "reviewer_username": reviewer[1] if reviewer else None,
        }
    return resolved


EXECUTION_SORTABLE = {
    "created_at": CleaningExecution.created_at,
    "dirty_since": CleaningExecution.dirty_since,
    "state": CleaningExecution.state,
}


@router.get("/executions")
async def list_executions(
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Browsable list for /cleaning's own page -- previously no way to see what cleaning executions
    existed at all, only open one already-known by id. Same SG-081 read-side precedent as every other
    list added this pass (e.g. qc.router.list_samples), including that one's "no site scoping on this
    table" call -- Phase 1 is single-site and every existing by-id GET on this table is unscoped too."""
    async with session.begin():
        stmt = select(CleaningExecution)
        if params.q:
            stmt = stmt.where(CleaningExecution.state.ilike(f"%{params.q}%"))
        rows, envelope = await paginate(
            session, stmt, params, sortable=EXECUTION_SORTABLE, default_sort=CleaningExecution.created_at
        )
        executions = [e for (e,) in rows]
        refs = await _resolve_execution_refs(session, executions)
        return {**envelope, "items": [_execution_dict(e, refs.get(e.id)) for e in executions]}


@router.post("/executions", response_model=MutationReceipt)
async def post_create_execution(
    cmd: CreateCleaningExecutionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="cleaning_execution.create", site_id=cmd.site_id)
        return await create_cleaning_execution(session, cmd, actor.user_id)


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    execution = await session.get(CleaningExecution, execution_id)
    if execution is None:
        raise NotFoundError("Cleaning execution not found")
    refs = await _resolve_execution_refs(session, [execution])
    return _execution_dict(execution, refs.get(execution.id))


@router.post("/executions/{execution_id}/steps", response_model=MutationReceipt)
async def post_record_step(
    execution_id: uuid.UUID,
    cmd: RecordCleaningStepCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.execution_id != execution_id:
        raise ValidationFailedError("execution_id in path and body must match")
    async with session.begin():
        execution = await session.get(CleaningExecution, execution_id)
        if execution is None:
            raise NotFoundError("Cleaning execution not found")
        await evaluate_policy(session, actor.user_id, action="cleaning_execution.create", site_id=execution.site_id)
        return await record_cleaning_step(session, cmd, actor.user_id)


class CleaningSignatureChallengeRequest(BaseModel):
    action: str  # "complete" | "verify"


_CLEANING_CHALLENGE_MEANINGS = {"complete": "Performed", "verify": "Verified"}


@router.post("/executions/{execution_id}/signature-challenges")
async def post_cleaning_signature_challenge(
    execution_id: uuid.UUID,
    body: CleaningSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        execution = await session.get(CleaningExecution, execution_id)
        if execution is None:
            raise NotFoundError("Cleaning execution not found")
        meaning = _CLEANING_CHALLENGE_MEANINGS.get(body.action)
        if meaning is None:
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="cleaning_execution", record_id=execution.id,
            record_version=execution.version, record_hash=cleaning_record_hash(execution), meaning=meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/executions/{execution_id}/complete", response_model=MutationReceipt)
async def post_complete_cleaning(
    execution_id: uuid.UUID,
    cmd: CompleteCleaningCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.execution_id != execution_id:
        raise ValidationFailedError("execution_id in path and body must match")
    async with session.begin():
        execution = await session.get(CleaningExecution, execution_id)
        if execution is None:
            raise NotFoundError("Cleaning execution not found")
        await evaluate_policy(session, actor.user_id, action="cleaning_execution.complete", site_id=execution.site_id)
        return await complete_cleaning(session, cmd, actor.user_id)


@router.post("/executions/{execution_id}/verify", response_model=MutationReceipt)
async def post_verify_cleaning(
    execution_id: uuid.UUID,
    cmd: VerifyCleaningCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.execution_id != execution_id:
        raise ValidationFailedError("execution_id in path and body must match")
    async with session.begin():
        execution = await session.get(CleaningExecution, execution_id)
        if execution is None:
            raise NotFoundError("Cleaning execution not found")
        await evaluate_policy(session, actor.user_id, action="cleaning_execution.verify", site_id=execution.site_id)
        return await verify_cleaning(session, cmd, actor.user_id)


def _procedure_summary_dict(procedure: CleaningProcedureVersion) -> dict:
    return {
        "id": str(procedure.id),
        "procedure_number": procedure.procedure_number,
        "version": procedure.version_no,
        "cleaning_type": procedure.cleaning_type,
        "scope_equipment_id": str(procedure.scope_equipment_id) if procedure.scope_equipment_id else None,
        "scope_area_id": str(procedure.scope_area_id) if procedure.scope_area_id else None,
        "state": procedure.state,
    }


def _procedure_detail_dict(procedure: CleaningProcedureVersion, site: Site | None = None) -> dict:
    return {
        **_procedure_summary_dict(procedure),
        "site_id": str(procedure.site_id),
        "site_code": site.code if site else None,
        "site_name": site.name if site else None,
        "agents": procedure.agents,
        "steps": procedure.steps,
        "disassembly_required": procedure.disassembly_required,
        "sample_inspection_requirements": procedure.sample_inspection_requirements,
        "dirty_hold_limit_minutes": procedure.dirty_hold_limit_minutes,
        "clean_hold_limit_minutes": procedure.clean_hold_limit_minutes,
        "validation_reference": procedure.validation_reference,
        "created_at": procedure.created_at.isoformat() if procedure.created_at else None,
    }


PROCEDURE_SORTABLE = {
    "procedure_number": CleaningProcedureVersion.procedure_number,
    "created_at": CleaningProcedureVersion.created_at,
}


@router.get("/procedure-versions")
async def list_procedure_versions(
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    state: str | None = "RELEASED",
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Real picker data for `CreateCleaningExecutionCommand.procedure_version_id` -- previously free-text
    UUID entry with no way to discover a valid id (the user would have to know a database id by heart),
    same SG-081 read-side precedent as `sterilization_router.list_profiles`. `cleaning_procedure_version`
    is still seed-only (module docstring) -- this is a read-only addition, no new create/release
    operation. Defaults to RELEASED only, matching that same precedent."""
    async with session.begin():
        stmt = select(CleaningProcedureVersion)
        if params.q:
            stmt = stmt.where(CleaningProcedureVersion.procedure_number.ilike(f"%{params.q}%"))
        if state:
            stmt = stmt.where(CleaningProcedureVersion.state == state)
        rows, envelope = await paginate(
            session, stmt, params, sortable=PROCEDURE_SORTABLE, default_sort=CleaningProcedureVersion.created_at
        )
        return {**envelope, "items": [_procedure_summary_dict(p) for (p,) in rows]}


@router.get("/procedure-versions/{procedure_id}")
async def get_procedure_version(
    procedure_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Row-click detail for the `/cleaning` page's "Cleaning procedure versions" list -- the list
    endpoint above only returns the summary shape used for the picker."""
    procedure = await session.get(CleaningProcedureVersion, procedure_id)
    if procedure is None:
        raise NotFoundError("Cleaning procedure version not found")
    site = await session.get(Site, procedure.site_id)
    return _procedure_detail_dict(procedure, site)


@router.post("/procedure-versions", response_model=MutationReceipt)
async def post_create_procedure_version(
    cmd: CreateCleaningProcedureVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    """Added 2026-10-08, project-owner-directed, same gap class as SG-203. See
    cleaning_commands.py's own docstring note above `CreateCleaningProcedureVersionCommand` for the
    authoring-role/lifecycle decision."""
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="cleaning_procedure_version.create", site_id=cmd.site_id)
        return await create_cleaning_procedure_version(session, cmd, actor.user_id)


@router.get("/equipment/{equipment_id}/status")
async def get_status(
    equipment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        return await get_equipment_cleaning_status(session, equipment_id)


def _clearance_dict(clearance: LineClearance, refs: dict | None = None) -> dict:
    refs = refs or {}
    return {
        "id": str(clearance.id),
        "site_id": str(clearance.site_id),
        "area_id": str(clearance.area_id) if clearance.area_id else None,
        "area_code": refs.get("area_code"),
        "previous_batch_id": str(clearance.previous_batch_id) if clearance.previous_batch_id else None,
        "previous_batch_number": refs.get("previous_batch_number"),
        "next_batch_id": str(clearance.next_batch_id) if clearance.next_batch_id else None,
        "next_batch_number": refs.get("next_batch_number"),
        "checklist_version": clearance.checklist_version,
        "items": clearance.items,
        "critical": clearance.critical,
        "performer_user_id": str(clearance.performer_user_id) if clearance.performer_user_id else None,
        "performer_username": refs.get("performer_username"),
        "performer_full_name": refs.get("performer_full_name"),
        "verifier_user_id": str(clearance.verifier_user_id) if clearance.verifier_user_id else None,
        "verifier_username": refs.get("verifier_username"),
        "verifier_full_name": refs.get("verifier_full_name"),
        "state": clearance.state,
        "expiry_at": clearance.expiry_at.isoformat() if clearance.expiry_at else None,
        "version": clearance.version,
        "created_at": clearance.created_at.isoformat() if clearance.created_at else None,
    }


async def _resolve_clearance_refs(session: AsyncSession, clearances: list[LineClearance]) -> dict[uuid.UUID, dict]:
    """Batch-resolves the area and previous/next batch foreign keys `_clearance_dict` labels for -- same
    one-query-per-referenced-table shape as sterilization's `_resolve_cycle_refs`."""
    if not clearances:
        return {}

    area_ids = {c.area_id for c in clearances if c.area_id}
    batch_ids = {c.previous_batch_id for c in clearances if c.previous_batch_id}
    batch_ids |= {c.next_batch_id for c in clearances if c.next_batch_id}
    user_ids = {c.performer_user_id for c in clearances if c.performer_user_id}
    user_ids |= {c.verifier_user_id for c in clearances if c.verifier_user_id}

    area_by_id: dict[uuid.UUID, str] = {}
    if area_ids:
        area_by_id = dict(
            (await session.execute(select(EquipmentArea.id, EquipmentArea.area_code).where(EquipmentArea.id.in_(area_ids)))).all()
        )
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
    for c in clearances:
        previous = batch_by_id.get(c.previous_batch_id) if c.previous_batch_id else None
        next_ = batch_by_id.get(c.next_batch_id) if c.next_batch_id else None
        performer = user_by_id.get(c.performer_user_id) if c.performer_user_id else None
        verifier = user_by_id.get(c.verifier_user_id) if c.verifier_user_id else None
        resolved[c.id] = {
            "area_code": area_by_id.get(c.area_id) if c.area_id else None,
            "previous_batch_number": previous[0] if previous else None,
            "next_batch_number": next_[0] if next_ else None,
            "performer_full_name": performer[0] if performer else None,
            "performer_username": performer[1] if performer else None,
            "verifier_full_name": verifier[0] if verifier else None,
            "verifier_username": verifier[1] if verifier else None,
        }
    return resolved


LINE_CLEARANCE_SORTABLE = {
    "state": LineClearance.state,
    "created_at": LineClearance.created_at,
}


@line_clearance_router.get("")
async def list_line_clearances(
    site_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Browsable list for `/line-clearance`'s own page -- previously reachable only by already knowing a
    clearance's id (same SG-081 read-side precedent as sterilization's `/cycles` list)."""
    async with session.begin():
        stmt = select(LineClearance).where(LineClearance.site_id == site_id)
        if params.q:
            stmt = stmt.where(LineClearance.state.ilike(f"%{params.q}%"))
        rows, envelope = await paginate(session, stmt, params, sortable=LINE_CLEARANCE_SORTABLE, default_sort=LineClearance.created_at)
        clearances = [c for (c,) in rows]
        refs = await _resolve_clearance_refs(session, clearances)
        return {**envelope, "items": [_clearance_dict(c, refs.get(c.id)) for c in clearances]}


@line_clearance_router.post("", response_model=MutationReceipt)
async def post_create_line_clearance(
    cmd: CreateLineClearanceCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="line_clearance.create", site_id=cmd.site_id)
        return await create_line_clearance(session, cmd, actor.user_id)


@line_clearance_router.get("/{clearance_id}")
async def get_line_clearance(
    clearance_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    clearance = await session.get(LineClearance, clearance_id)
    if clearance is None:
        raise NotFoundError("Line clearance not found")
    refs = await _resolve_clearance_refs(session, [clearance])
    return _clearance_dict(clearance, refs.get(clearance.id))


class LineClearanceSignatureChallengeRequest(BaseModel):
    action: str = "complete"


@line_clearance_router.post("/{clearance_id}/signature-challenges")
async def post_line_clearance_signature_challenge(
    clearance_id: uuid.UUID,
    body: LineClearanceSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        clearance = await session.get(LineClearance, clearance_id)
        if clearance is None:
            raise NotFoundError("Line clearance not found")
        if body.action != "complete":
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="line_clearance", record_id=clearance.id,
            record_version=clearance.version, record_hash=line_clearance_record_hash(clearance), meaning="Performed",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@line_clearance_router.post("/{clearance_id}/complete", response_model=MutationReceipt)
async def post_complete_line_clearance(
    clearance_id: uuid.UUID,
    cmd: CompleteLineClearanceCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.clearance_id != clearance_id:
        raise ValidationFailedError("clearance_id in path and body must match")
    async with session.begin():
        clearance = await session.get(LineClearance, clearance_id)
        if clearance is None:
            raise NotFoundError("Line clearance not found")
        await evaluate_policy(session, actor.user_id, action="line_clearance.complete", site_id=clearance.site_id)
        return await complete_line_clearance(session, cmd, actor.user_id)
