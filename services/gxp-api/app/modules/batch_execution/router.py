import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.batch_execution import service as batch_execution_service
from app.modules.batch_execution.commands import (
    AddStepCommentCommand,
    ApproveStepResultCorrectionCommand,
    BatchTransitionCommand,
    CompleteStepCommand,
    CreateBatchCommand,
    HandoverStepCommand,
    HoldStepCommand,
    IssueBatchCommand,
    ProductionCompleteBatchCommand,
    LinkStepEvidenceCommand,
    RecordStepResultsCommand,
    RequestStepResultCorrectionCommand,
    ResumeStepCommand,
    StartStepCommand,
    _batch_record_hash,
    _step_record_hash,
    _step_result_hash,
    abort_batch,
    add_step_comment,
    approve_step_result_correction,
    complete_step,
    create_batch,
    handover_step,
    hold_batch,
    hold_step,
    issue_batch,
    production_complete_batch,
    link_step_evidence,
    record_step_results,
    request_step_result_correction,
    resume_batch,
    resume_step,
    start_batch,
    start_step,
)
from app.modules.batch_execution.models import Batch, BatchStep, StepResult
from app.modules.iam.models import User
from app.modules.material_specification.models import MaterialSpecificationVersion
from app.modules.policy.service import evaluate_policy
from app.modules.product_master.models import ProductVersion
from app.modules.recipe_master.models import RecipeFamily, RecipeParameter, RecipeVersion
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/batches/v1", tags=["batch_execution"])


def _batch_dict(
    batch,
    product_version: ProductVersion | None = None,
    recipe_context: tuple[str, int] | None = None,
) -> dict:
    recipe_code, recipe_version_no = recipe_context if recipe_context else (None, None)
    return {
        "batch_id": str(batch.id),
        "site_id": str(batch.site_id),
        "batch_number": batch.batch_number,
        "product_version_id": str(batch.product_version_id),
        # Real dropdown/detail UX (project-owner-directed, SG-149/SG-173 cutover) -- callers building a
        # batch picker or detail view need human labels, not bare UUIDs, without a second round trip.
        "product_name": product_version.name if product_version else None,
        "product_code": product_version.product_code if product_version else None,
        "recipe_version_id": str(batch.recipe_version_id),
        "recipe_code": recipe_code,
        "recipe_version_no": recipe_version_no,
        "recipe_vault_object_id": str(batch.recipe_vault_object_id) if batch.recipe_vault_object_id else None,
        "execution_snapshot_id": str(batch.execution_snapshot_id) if batch.execution_snapshot_id else None,
        "target_qty": str(batch.target_qty),
        "target_uom": batch.target_uom,
        "state": batch.state,
        "version": batch.version,
        "production_order_ref": batch.production_order_ref,
        "issued_at": batch.issued_at.isoformat() if batch.issued_at else None,
        "started_at": batch.started_at.isoformat() if batch.started_at else None,
    }


async def _product_versions_by_id(session: AsyncSession, batches: list) -> dict[uuid.UUID, ProductVersion]:
    if not batches:
        return {}
    pv_ids = {b.product_version_id for b in batches}
    rows = (await session.execute(select(ProductVersion).where(ProductVersion.id.in_(pv_ids)))).scalars().all()
    return {pv.id: pv for pv in rows}


async def _recipe_context_by_id(session: AsyncSession, batches: list) -> dict[uuid.UUID, tuple[str, int]]:
    """{recipe_version_id: (recipe_code, version_no)} -- same "real label, not a bare UUID" fix as
    `_product_versions_by_id()`, for the batch's other master-data reference."""
    if not batches:
        return {}
    rv_ids = {b.recipe_version_id for b in batches}
    rows = (
        await session.execute(
            select(RecipeVersion.id, RecipeFamily.recipe_code, RecipeVersion.version_no)
            .join(RecipeFamily, RecipeFamily.id == RecipeVersion.recipe_family_id)
            .where(RecipeVersion.id.in_(rv_ids))
        )
    ).all()
    return {row.id: (row.recipe_code, row.version_no) for row in rows}


def _frozen_equipment_requirement_dict(eq) -> dict:
    return {
        "equipment_class": eq.equipment_class,
        "equipment_class_id": str(eq.equipment_class_id) if eq.equipment_class_id else None,
        "exact_equipment_optional": eq.exact_equipment_optional,
        "require_current_calibration": eq.require_current_calibration,
        "require_current_qualification": eq.require_current_qualification,
        "require_current_cleaning": eq.require_current_cleaning,
    }


def _step_dict(step, assigned_user: User | None = None, frozen_equipment_requirements: list | None = None) -> dict:
    return {
        "step_id": str(step.id),
        "batch_id": str(step.batch_id),
        "recipe_step_code": step.recipe_step_code,
        "required_role_code": step.required_role_code,
        "required_qualification_code": step.required_qualification_code,
        # Known-limitations fix (docs/testing/demo-gujarati/08 §8.8): the frozen requirements
        # commands.py::_enforce_step_equipment actually checks at step-start.
        "equipment_requirements": [_frozen_equipment_requirement_dict(eq) for eq in (frozen_equipment_requirements or [])],
        "scope_type": step.scope_type,
        "scope_id": str(step.scope_id) if step.scope_id else None,
        "state": step.state,
        "version": step.version,
        "assigned_subject_id": str(step.assigned_subject_id) if step.assigned_subject_id else None,
        # Real name/username, not a bare UUID -- same "show name and code" fix as the batch's own
        # product/recipe fields above.
        "assigned_full_name": assigned_user.full_name if assigned_user else None,
        "assigned_username": assigned_user.username if assigned_user else None,
        "started_at": step.started_at.isoformat() if step.started_at else None,
        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
    }


def _parameter_dict(p: RecipeParameter) -> dict:
    return {
        "parameter_code": p.parameter_code,
        "data_type": p.data_type,
        "uom": p.uom,
        "target_value": str(p.target_value) if p.target_value is not None else None,
        "min_value": str(p.min_value) if p.min_value is not None else None,
        "max_value": str(p.max_value) if p.max_value is not None else None,
        "precision_digits": p.precision_digits,
        "required": p.required,
    }


def _result_dict(r) -> dict:
    return {
        "result_id": str(r.id),
        "parameter_code": r.parameter_code,
        "data_type": r.data_type,
        "value_numeric": str(r.value_numeric) if r.value_numeric is not None else None,
        "value_text": r.value_text,
        "value_bool": r.value_bool,
        "uom": r.uom,
        "source_type": r.source_type,
        "quality_status": r.quality_status,
        "received_at": r.received_at.isoformat() if r.received_at else None,
        "signature_id": str(r.signature_id) if r.signature_id else None,
        "supersedes_result_id": str(r.supersedes_result_id) if r.supersedes_result_id else None,
    }


def _evidence_requirement_dict(e) -> dict:
    return {
        "evidence_type": e.evidence_type,
        "required_count": e.required_count,
        "allowed_mime_types": e.allowed_mime_types,
        "retention_class": e.retention_class,
    }


def _material_requirement_dict(m, material_spec: MaterialSpecificationVersion | None) -> dict:
    """SG-048 #012/#013's display-only half -- shows what the recipe already declares (SG-045's own
    tolerance/consume-mode/substitution shape) without adding a lot-consumption/reservation capability,
    which stays open pending SG-045's still-unresolved schema question."""
    return {
        "material_spec_version_id": str(m.material_spec_version_id),
        "material_spec_business_id": material_spec.material_spec_business_id if material_spec else None,
        "material_name": material_spec.name if material_spec else None,
        "target_value": str(m.target_value) if m.target_value is not None else None,
        "min_value": str(m.min_value) if m.min_value is not None else None,
        "max_value": str(m.max_value) if m.max_value is not None else None,
        "uom": m.uom,
        "consume_mode": m.consume_mode,
        "substitution_allowed": m.substitution_allowed,
        "genealogy_required": m.genealogy_required,
    }


def _correction_dict(c, original_result, requested_user: User | None, approved_user: User | None) -> dict:
    return {
        "correction_id": str(c.id),
        "original_result_id": str(c.original_result_id),
        "parameter_code": original_result.parameter_code if original_result else None,
        "reason_text": c.reason_text,
        "corrected_value_numeric": str(c.corrected_value_numeric) if c.corrected_value_numeric is not None else None,
        "corrected_value_text": c.corrected_value_text,
        "corrected_value_bool": c.corrected_value_bool,
        "status": c.status,
        "requested_by_user_id": str(c.requested_by_user_id),
        "requested_by_username": requested_user.username if requested_user else None,
        "approved_by_user_id": str(c.approved_by_user_id) if c.approved_by_user_id else None,
        "approved_by_username": approved_user.username if approved_user else None,
        "resulting_result_id": str(c.resulting_result_id) if c.resulting_result_id else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "completed_at": c.completed_at.isoformat() if c.completed_at else None,
    }


def _equipment_requirement_dict(eq) -> dict:
    return {
        "equipment_class": eq.equipment_class,
        "exact_equipment_optional": eq.exact_equipment_optional,
        "require_current_calibration": eq.require_current_calibration,
        "require_current_qualification": eq.require_current_qualification,
        "require_current_cleaning": eq.require_current_cleaning,
    }


# BAT-FR-005 ("execution has immutable parent instruction") + Document 11 §9's execution-UI field list
# (instruction, section, target/limits context) -- the "step detail" view, read from the live recipe
# graph (display-only; not used for any regulated decision -- the frozen execution snapshot in Vault
# remains the authoritative instruction record, VLT-FR-006/007).
def _step_detail_dict(
    step, recipe_step, section, predecessors: list[str], successors: list[str], evidence: list,
    material_requirements: list, equipment_requirements: list, material_specs_by_id: dict,
) -> dict:
    return {
        "step_type": recipe_step.step_type if recipe_step else None,
        "instruction_text": recipe_step.instruction_text if recipe_step else None,
        "is_critical": recipe_step.is_critical if recipe_step else None,
        "sequence_hint": recipe_step.sequence_hint if recipe_step else None,
        "section_code": section.stable_section_code if section else None,
        "section_name": section.name if section else None,
        "expected_hold_duration_minutes": recipe_step.expected_hold_duration_minutes if recipe_step else None,
        "predecessor_codes": predecessors,
        "successor_codes": successors,
        "evidence_requirements": [_evidence_requirement_dict(e) for e in evidence],
        "material_requirements": [
            _material_requirement_dict(m, material_specs_by_id.get(m.material_spec_version_id)) for m in material_requirements
        ],
        "equipment_requirements": [_equipment_requirement_dict(eq) for eq in equipment_requirements],
    }


async def _users_by_id(session: AsyncSession, subject_ids: set[uuid.UUID]) -> dict[uuid.UUID, User]:
    subject_ids = {s for s in subject_ids if s is not None}
    if not subject_ids:
        return {}
    rows = (await session.execute(select(User).where(User.id.in_(subject_ids)))).scalars().all()
    return {u.id: u for u in rows}


@router.post("", response_model=MutationReceipt)
async def post_create_batch(
    cmd: CreateBatchCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.create", site_id=cmd.site_id)
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
        await evaluate_policy(session, actor.user_id, action="batch_execution.issue", site_id=None)
        return await issue_batch(session, cmd, actor.user_id)


@router.post("/{batch_id}/start", response_model=MutationReceipt)
async def post_start_batch(
    batch_id: uuid.UUID,
    cmd: BatchTransitionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await start_batch(session, cmd, actor.user_id)


@router.post("/{batch_id}/hold", response_model=MutationReceipt)
async def post_hold_batch(
    batch_id: uuid.UUID,
    cmd: BatchTransitionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await hold_batch(session, cmd, actor.user_id)


@router.post("/{batch_id}/resume", response_model=MutationReceipt)
async def post_resume_batch(
    batch_id: uuid.UUID,
    cmd: BatchTransitionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await resume_batch(session, cmd, actor.user_id)


@router.post("/{batch_id}/abort", response_model=MutationReceipt)
async def post_abort_batch(
    batch_id: uuid.UUID,
    cmd: BatchTransitionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await abort_batch(session, cmd, actor.user_id)


@router.post("/{batch_id}/steps/{step_id}/start", response_model=MutationReceipt)
async def post_start_step(
    batch_id: uuid.UUID,
    step_id: uuid.UUID,
    cmd: StartStepCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id or cmd.step_id != step_id:
        raise ValidationFailedError("batch_id/step_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await start_step(session, cmd, actor.user_id)


class StepSignatureChallengeRequest(BaseModel):
    action: str  # "results" | "complete" | "hold" | "resume" -- Document 106 rows 21/19/14/17 (nearest
    # analogous shapes; no step-scoped row exists in Document 106 itself for hold/resume)


# Meaning per action -- Document 106 rows 21/19 (batch_step/results, batch_step/complete) are both
# `Performed`; hold reuses row 14's `Performed` (Authorized holder); resume reuses row 17's `Approved`
# (the meaning a QA authority attests when lifting a hold, not merely "performing" a task).
_STEP_CHALLENGE_MEANINGS = {"results": "Performed", "complete": "Performed", "hold": "Performed", "resume": "Approved"}


@router.post("/{batch_id}/steps/{step_id}/signature-challenges")
async def post_step_signature_challenge(
    batch_id: uuid.UUID,
    step_id: uuid.UUID,
    body: StepSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Same shape as product_master's `/{id}/signature-challenges` (SG-035 precedent): the record
    hash matches `_step_record_hash()` in commands.py exactly, so `consume_challenge` rejects the
    signature as "record changed" if the step's version moved between challenge and submission
    (SIG-FR-012/013/014 equivalent)."""
    meaning = _STEP_CHALLENGE_MEANINGS.get(body.action)
    if meaning is None:
        raise ValidationFailedError("Unknown action", action=body.action)
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        step = await session.get(BatchStep, step_id)
        if step is None or step.batch_id != batch_id:
            raise NotFoundError("Batch step not found")
        challenge = await create_challenge(
            session,
            user_id=actor.user_id,
            record_type="batch_step",
            record_id=step.id,
            record_version=step.version,
            record_hash=_step_record_hash(step),
            meaning=meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/{batch_id}/steps/{step_id}/results", response_model=MutationReceipt)
async def post_record_step_results(
    batch_id: uuid.UUID,
    step_id: uuid.UUID,
    cmd: RecordStepResultsCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id or cmd.step_id != step_id:
        raise ValidationFailedError("batch_id/step_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await record_step_results(session, cmd, actor.user_id)


@router.post("/{batch_id}/steps/{step_id}/evidence-links", response_model=MutationReceipt)
async def post_link_step_evidence(
    batch_id: uuid.UUID,
    step_id: uuid.UUID,
    cmd: LinkStepEvidenceCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id or cmd.step_id != step_id:
        raise ValidationFailedError("batch_id/step_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await link_step_evidence(session, cmd, actor.user_id)


@router.post("/{batch_id}/steps/{step_id}/complete", response_model=MutationReceipt)
async def post_complete_step(
    batch_id: uuid.UUID,
    step_id: uuid.UUID,
    cmd: CompleteStepCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id or cmd.step_id != step_id:
        raise ValidationFailedError("batch_id/step_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await complete_step(session, cmd, actor.user_id)


@router.post("/{batch_id}/steps/{step_id}/hold", response_model=MutationReceipt)
async def post_hold_step(
    batch_id: uuid.UUID,
    step_id: uuid.UUID,
    cmd: HoldStepCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id or cmd.step_id != step_id:
        raise ValidationFailedError("batch_id/step_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await hold_step(session, cmd, actor.user_id)


@router.post("/{batch_id}/steps/{step_id}/resume", response_model=MutationReceipt)
async def post_resume_step(
    batch_id: uuid.UUID,
    step_id: uuid.UUID,
    cmd: ResumeStepCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id or cmd.step_id != step_id:
        raise ValidationFailedError("batch_id/step_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await resume_step(session, cmd, actor.user_id)


@router.post("/{batch_id}/steps/{step_id}/comments", response_model=MutationReceipt)
async def post_add_step_comment(
    batch_id: uuid.UUID,
    step_id: uuid.UUID,
    cmd: AddStepCommentCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id or cmd.step_id != step_id:
        raise ValidationFailedError("batch_id/step_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await add_step_comment(session, cmd, actor.user_id)


@router.post("/{batch_id}/steps/{step_id}/handover", response_model=MutationReceipt)
async def post_handover_step(
    batch_id: uuid.UUID,
    step_id: uuid.UUID,
    cmd: HandoverStepCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id or cmd.step_id != step_id:
        raise ValidationFailedError("batch_id/step_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await handover_step(session, cmd, actor.user_id)


class StepResultSignatureChallengeRequest(BaseModel):
    action: str  # "correct_request" | "correct_approve" -- Document 106 row 20, both halves same meaning


@router.post("/{batch_id}/steps/{step_id}/results/{result_id}/signature-challenges")
async def post_step_result_signature_challenge(
    batch_id: uuid.UUID,
    step_id: uuid.UUID,
    result_id: uuid.UUID,
    body: StepResultSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """BAT-FR-023 (SG-048 #023). Same shape as qc's `/results/{id}/signature-challenges` (Document 106
    row 57's identical 2-signature precedent): bound to the *step result's* own version/hash, not the
    owning step's, and ungated by RBAC here -- `request_step_result_correction`/
    `approve_step_result_correction` each enforce `batch_step.correct` themselves before consuming the
    challenge, same division of responsibility qc.router's equivalent endpoint uses."""
    if body.action not in ("correct_request", "correct_approve"):
        raise ValidationFailedError("Unknown action", action=body.action)
    async with session.begin():
        step = await session.get(BatchStep, step_id)
        if step is None or step.batch_id != batch_id:
            raise NotFoundError("Batch step not found")
        result = await session.get(StepResult, result_id)
        if result is None or result.step_id != step.id:
            raise NotFoundError("Step result not found")
        challenge = await create_challenge(
            session,
            user_id=actor.user_id,
            record_type="batch_step_result",
            record_id=result.id,
            record_version=result.result_version,
            record_hash=_step_result_hash(result),
            meaning="Approved",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/{batch_id}/steps/{step_id}/correct", response_model=MutationReceipt)
async def post_request_step_result_correction(
    batch_id: uuid.UUID,
    step_id: uuid.UUID,
    cmd: RequestStepResultCorrectionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id or cmd.step_id != step_id:
        raise ValidationFailedError("batch_id/step_id in path and body must match")
    async with session.begin():
        return await request_step_result_correction(session, cmd, actor.user_id)


@router.post("/{batch_id}/steps/{step_id}/corrections/{correction_id}/approve", response_model=MutationReceipt)
async def post_approve_step_result_correction(
    batch_id: uuid.UUID,
    step_id: uuid.UUID,
    correction_id: uuid.UUID,
    cmd: ApproveStepResultCorrectionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.correction_id != correction_id:
        raise ValidationFailedError("correction_id in path and body must match")
    async with session.begin():
        return await approve_step_result_correction(session, cmd, actor.user_id)


class BatchSignatureChallengeRequest(BaseModel):
    action: str  # "production_complete" -- Document 106 row 16 (batch/production-complete)


_BATCH_CHALLENGE_MEANINGS = {"production_complete": "Performed"}


@router.post("/{batch_id}/signature-challenges")
async def post_batch_signature_challenge(
    batch_id: uuid.UUID,
    body: BatchSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Batch-scoped counterpart to `post_step_signature_challenge` above -- same shape, `record_hash`
    matches `_batch_record_hash()` in commands.py exactly."""
    meaning = _BATCH_CHALLENGE_MEANINGS.get(body.action)
    if meaning is None:
        raise ValidationFailedError("Unknown action", action=body.action)
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        batch = await session.get(Batch, batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        challenge = await create_challenge(
            session,
            user_id=actor.user_id,
            record_type="batch",
            record_id=batch.id,
            record_version=batch.version,
            record_hash=_batch_record_hash(batch),
            meaning=meaning,
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/{batch_id}/production-complete", response_model=MutationReceipt)
async def post_production_complete_batch(
    batch_id: uuid.UUID,
    cmd: ProductionCompleteBatchCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.batch_id != batch_id:
        raise ValidationFailedError("batch_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="batch_execution.execute", site_id=None)
        return await production_complete_batch(session, cmd, actor.user_id)


@router.get("")
async def get_batch_list(
    site_id: uuid.UUID,
    state: str | None = None,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """BAT-FR-035 (partial production dashboard): active batches + hold state at a site. Bottlenecks,
    overdue timers and operator-assignment analytics are not built this pass -- see SG-048."""
    await evaluate_policy(session, actor.user_id, action="batch_execution.view", site_id=None)
    batches = await batch_execution_service.list_batches(session, site_id, state)
    product_versions = await _product_versions_by_id(session, batches)
    recipe_contexts = await _recipe_context_by_id(session, batches)
    return {
        "batches": [
            _batch_dict(b, product_versions.get(b.product_version_id), recipe_contexts.get(b.recipe_version_id))
            for b in batches
        ],
        "on_hold_count": sum(1 for b in batches if b.state == "on_hold"),
    }


@router.get("/{batch_id}")
async def get_batch_detail(
    batch_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="batch_execution.view", site_id=None)
    batch = await batch_execution_service.get_batch(session, batch_id)
    product_version = await session.get(ProductVersion, batch.product_version_id)
    recipe_contexts = await _recipe_context_by_id(session, [batch])
    return _batch_dict(batch, product_version, recipe_contexts.get(batch.recipe_version_id))


@router.get("/{batch_id}/execution-view")
async def get_execution_view(
    batch_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="batch_execution.view", site_id=None)
    view = await batch_execution_service.get_execution_view(session, batch_id)
    product_version = await session.get(ProductVersion, view["batch"].product_version_id)
    recipe_contexts = await _recipe_context_by_id(session, [view["batch"]])
    assigned_users = await _users_by_id(session, {s.assigned_subject_id for s in view["steps"]})
    material_spec_ids = {m.material_spec_version_id for reqs in view["material_requirements_by_code"].values() for m in reqs}
    material_specs_by_id: dict = {}
    if material_spec_ids:
        rows = (
            await session.execute(select(MaterialSpecificationVersion).where(MaterialSpecificationVersion.id.in_(material_spec_ids)))
        ).scalars().all()
        material_specs_by_id = {ms.id: ms for ms in rows}
    results_by_id = {r.id: r for rows in view["results_by_step_id"].values() for r in rows}
    correction_user_ids = {c.requested_by_user_id for cs in view["corrections_by_step_id"].values() for c in cs} | {
        c.approved_by_user_id for cs in view["corrections_by_step_id"].values() for c in cs if c.approved_by_user_id
    }
    correction_users = await _users_by_id(session, correction_user_ids)
    return {
        "batch": _batch_dict(view["batch"], product_version, recipe_contexts.get(view["batch"].recipe_version_id)),
        "steps": [
            _step_dict(
                s,
                assigned_users.get(s.assigned_subject_id),
                view["frozen_equipment_requirements_by_step_id"].get(s.id, []),
            )
            for s in view["steps"]
        ],
        "blockers": view["blockers"],
        # BAT-FR-009 form definition + any already-recorded results, keyed by step_id so the UI can render
        # a per-step results form without a second round trip (SG-047 partial resolution).
        "parameters_by_step_id": {
            str(s.id): [_parameter_dict(p) for p in view["parameters_by_code"].get(s.recipe_step_code, [])]
            for s in view["steps"]
        },
        "results_by_step_id": {
            str(step_id): [_result_dict(r) for r in results] for step_id, results in view["results_by_step_id"].items()
        },
        # "Step detail" view -- instruction, section, dependencies, evidence requirements (2026-09-09,
        # client-requested).
        "step_detail_by_step_id": {
            str(s.id): _step_detail_dict(
                s,
                view["step_by_code"].get(s.recipe_step_code),
                view["section_by_id"].get(view["step_by_code"][s.recipe_step_code].section_id)
                if s.recipe_step_code in view["step_by_code"]
                else None,
                view["predecessors_of"].get(s.recipe_step_code, []),
                view["successors_of"].get(s.recipe_step_code, []),
                view["evidence_by_code"].get(s.recipe_step_code, []),
                view["material_requirements_by_code"].get(s.recipe_step_code, []),
                view["equipment_requirements_by_code"].get(s.recipe_step_code, []),
                material_specs_by_id,
            )
            for s in view["steps"]
        },
        # Active step-level hold, if any (BAT-FR-020 step scope, SG-047 further partial resolution).
        "active_hold_by_step_id": {
            str(step_id): {
                "id": str(h.id), "reason": h.reason, "held_at": h.held_at.isoformat() if h.held_at else None,
                "held_by": str(h.held_by), "hold_signature_id": str(h.hold_signature_id) if h.hold_signature_id else None,
            }
            for step_id, h in view["active_hold_by_step_id"].items()
        },
        # BAT-FR-034, SG-048 #034 partial resolution.
        "comments_by_step_id": {
            str(step_id): [
                {"comment_id": str(c.id), "comment_text": c.comment_text, "created_by": str(c.created_by), "created_at": c.created_at.isoformat() if c.created_at else None}
                for c in comments
            ]
            for step_id, comments in view["comments_by_step_id"].items()
        },
        # BAT-FR-025, SG-048 #025 partial resolution.
        "handovers_by_step_id": {
            str(step_id): [
                {
                    "handover_id": str(h.id),
                    "from_subject_id": str(h.from_subject_id) if h.from_subject_id else None,
                    "to_subject_id": str(h.to_subject_id),
                    "reason": h.reason,
                    "created_at": h.created_at.isoformat() if h.created_at else None,
                }
                for h in handovers
            ]
            for step_id, handovers in view["handovers_by_step_id"].items()
        },
        # SG-047 (gxp_step_evidence_link half) -- written by link_step_evidence(), read internally by
        # complete_step()'s evidence-count gate but never surfaced in this view until now.
        "evidence_links_by_step_id": {
            str(step_id): [
                {
                    "id": str(e.id), "evidence_id": str(e.evidence_id), "evidence_version": e.evidence_version,
                    "evidence_sha256": e.evidence_sha256, "media_type": e.media_type,
                    "requirement_code": e.requirement_code, "linked_by": str(e.linked_by),
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in links
            ]
            for step_id, links in view["evidence_links_by_step_id"].items()
        },
        # SG-048 #023's own gap: the correct/approve flow existed with no read-side visibility at all.
        "corrections_by_step_id": {
            str(step_id): [
                _correction_dict(c, results_by_id.get(c.original_result_id), correction_users.get(c.requested_by_user_id), correction_users.get(c.approved_by_user_id))
                for c in corrections
            ]
            for step_id, corrections in view["corrections_by_step_id"].items()
        },
    }
